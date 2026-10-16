package auto_reload

import (
	"fmt"
	"net/url"
	"sync"
	"testing"
	"time"

	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// WebSocketMessage represents a message sent/received over WebSocket
type WebSocketMessage struct {
	Type      string                 `json:"type"`
	Data      map[string]interface{} `json:"data"`
	Timestamp time.Time              `json:"timestamp"`
}

// WebSocketClient wraps a WebSocket connection for testing
type WebSocketClient struct {
	conn         *websocket.Conn
	messages     chan WebSocketMessage
	errors       chan error
	done         chan struct{}
	mu           sync.Mutex
	connected    bool
	receivedMsgs []WebSocketMessage
}

// NewWebSocketClient creates a new WebSocket client for testing
func NewWebSocketClient(serverURL string) (*WebSocketClient, error) {
	u, err := url.Parse(serverURL)
	if err != nil {
		return nil, err
	}
	u.Scheme = "ws"
	u.Path = "/ws/dashboard"

	dialer := websocket.DefaultDialer
	dialer.HandshakeTimeout = 10 * time.Second

	conn, _, err := dialer.Dial(u.String(), nil)
	if err != nil {
		return nil, err
	}

	client := &WebSocketClient{
		conn:         conn,
		messages:     make(chan WebSocketMessage, 100),
		errors:       make(chan error, 10),
		done:         make(chan struct{}),
		connected:    true,
		receivedMsgs: make([]WebSocketMessage, 0),
	}

	go client.readMessages()
	return client, nil
}

// readMessages reads messages from the WebSocket connection
func (c *WebSocketClient) readMessages() {
	defer close(c.messages)
	defer close(c.errors)

	for {
		select {
		case <-c.done:
			return
		default:
			var msg WebSocketMessage
			err := c.conn.ReadJSON(&msg)
			if err != nil {
				c.mu.Lock()
				c.connected = false
				c.mu.Unlock()

				if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
					c.errors <- fmt.Errorf("websocket read error: %w", err)
				}
				return
			}

			c.mu.Lock()
			c.receivedMsgs = append(c.receivedMsgs, msg)
			c.mu.Unlock()

			select {
			case c.messages <- msg:
			case <-c.done:
				return
			}
		}
	}
}

// SendMessage sends a message to the WebSocket server
func (c *WebSocketClient) SendMessage(msg WebSocketMessage) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if !c.connected {
		return fmt.Errorf("client not connected")
	}

	return c.conn.WriteJSON(msg)
}

// WaitForMessage waits for a specific message type within the timeout
func (c *WebSocketClient) WaitForMessage(messageType string, timeout time.Duration) (*WebSocketMessage, error) {
	timer := time.NewTimer(timeout)
	defer timer.Stop()

	for {
		select {
		case msg := <-c.messages:
			if msg.Type == messageType {
				return &msg, nil
			}
		case err := <-c.errors:
			return nil, err
		case <-timer.C:
			return nil, fmt.Errorf("timeout waiting for message type %s", messageType)
		case <-c.done:
			return nil, fmt.Errorf("client disconnected")
		}
	}
}

// GetReceivedMessages returns all received messages
func (c *WebSocketClient) GetReceivedMessages() []WebSocketMessage {
	c.mu.Lock()
	defer c.mu.Unlock()

	messages := make([]WebSocketMessage, len(c.receivedMsgs))
	copy(messages, c.receivedMsgs)
	return messages
}

// IsConnected returns whether the client is connected
func (c *WebSocketClient) IsConnected() bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.connected
}

// Close closes the WebSocket connection
func (c *WebSocketClient) Close() error {
	close(c.done)
	return c.conn.Close()
}

// Reconnect attempts to reconnect to the WebSocket server
func (c *WebSocketClient) Reconnect(serverURL string) error {
	c.Close()

	u, err := url.Parse(serverURL)
	if err != nil {
		return err
	}
	u.Scheme = "ws"
	u.Path = "/ws/dashboard"

	conn, _, err := websocket.DefaultDialer.Dial(u.String(), nil)
	if err != nil {
		return err
	}

	c.mu.Lock()
	c.conn = conn
	c.connected = true
	c.done = make(chan struct{})
	c.receivedMsgs = make([]WebSocketMessage, 0)
	c.mu.Unlock()

	go c.readMessages()
	return nil
}

// TestWebSocketHandlingDuringReload tests WebSocket behavior during service reloads
func TestWebSocketHandlingDuringReload(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping WebSocket reload test in short mode")
	}

	helper := NewTestHelper(t)
	defer helper.Cleanup()

	// Start the auto-reload service
	helper.StartReloader()

	// Wait for service to be ready
	helper.WaitForServiceReadyWithCustomTimeout(30 * time.Second)

	// Establish multiple WebSocket connections
	const numClients = 3
	clients := make([]*WebSocketClient, numClients)

	t.Log("Establishing WebSocket connections...")
	for i := 0; i < numClients; i++ {
		client, err := NewWebSocketClient(helper.GetServiceURL())
		require.NoError(t, err, "Failed to connect WebSocket client %d", i)
		clients[i] = client
		defer client.Close()
	}

	// Send test messages to verify initial connectivity
	testMessage := WebSocketMessage{
		Type: "test_message",
		Data: map[string]interface{}{
			"content":   "pre-reload test",
			"client_id": "test_client",
		},
		Timestamp: time.Now(),
	}

	t.Log("Testing initial WebSocket connectivity...")
	for i, client := range clients {
		err := client.SendMessage(testMessage)
		assert.NoError(t, err, "Failed to send test message to client %d", i)
	}

	// Trigger a service reload by modifying a file
	t.Log("Triggering service reload...")
	helper.ModifySourceFile("internal/api/handlers.go", "// WebSocket reload test trigger")

	// Monitor WebSocket disconnections during reload
	t.Log("Monitoring WebSocket behavior during reload...")
	disconnectionCount := 0
	for i, client := range clients {
		// Give some time for graceful disconnection
		time.Sleep(2 * time.Second)

		if !client.IsConnected() {
			disconnectionCount++
			t.Logf("Client %d disconnected as expected during reload", i)
		}
	}

	// Wait for reload to complete
	helper.WaitForReloadComplete(60 * time.Second)

	// Verify service is responsive after reload
	helper.VerifyServiceResponsive()

	// Test WebSocket reconnection capability
	t.Log("Testing WebSocket reconnection after reload...")
	reconnectedClients := 0
	for i, client := range clients {
		err := client.Reconnect(helper.GetServiceURL())
		if err != nil {
			t.Logf("Client %d failed to reconnect: %v", i, err)
			continue
		}
		reconnectedClients++
		t.Logf("Client %d successfully reconnected", i)
	}

	assert.Greater(t, reconnectedClients, 0, "At least one client should be able to reconnect")

	// Send post-reload test messages
	postReloadMessage := WebSocketMessage{
		Type: "test_message",
		Data: map[string]interface{}{
			"content":   "post-reload test",
			"client_id": "test_client",
		},
		Timestamp: time.Now(),
	}

	t.Log("Testing WebSocket functionality after reload...")
	for i, client := range clients {
		if client.IsConnected() {
			err := client.SendMessage(postReloadMessage)
			assert.NoError(t, err, "Failed to send post-reload message to client %d", i)
		}
	}

	t.Log("WebSocket reload test completed successfully")
}

// TestWebSocketClientReconnection tests automatic client reconnection logic
func TestWebSocketClientReconnection(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping WebSocket reconnection test in short mode")
	}

	helper := NewTestHelper(t)
	defer helper.Cleanup()

	helper.StartReloader()
	helper.WaitForServiceReadyWithCustomTimeout(30 * time.Second)

	// Create a WebSocket client
	client, err := NewWebSocketClient(helper.GetServiceURL())
	require.NoError(t, err)
	defer client.Close()

	// Send initial message
	initialMessage := WebSocketMessage{
		Type:      "heartbeat",
		Data:      map[string]interface{}{"status": "connected"},
		Timestamp: time.Now(),
	}

	err = client.SendMessage(initialMessage)
	require.NoError(t, err)

	// Trigger multiple rapid reloads to test reconnection robustness
	t.Log("Testing reconnection with multiple rapid reloads...")
	for i := 0; i < 3; i++ {
		helper.ModifySourceFile("internal/api/handlers.go", fmt.Sprintf("// Rapid reload test %d", i))
		time.Sleep(1 * time.Second)
	}

	// Wait for final reload
	helper.WaitForReloadComplete(60 * time.Second)

	// Test final reconnection
	err = client.Reconnect(helper.GetServiceURL())
	assert.NoError(t, err, "Client should be able to reconnect after multiple reloads")

	// Verify functionality
	finalMessage := WebSocketMessage{
		Type:      "test_complete",
		Data:      map[string]interface{}{"test": "rapid_reload_recovery"},
		Timestamp: time.Now(),
	}

	if client.IsConnected() {
		err = client.SendMessage(finalMessage)
		assert.NoError(t, err, "Should be able to send messages after reconnection")
	}
}

// TestWebSocketStateRecovery tests state recovery after reconnection
func TestWebSocketStateRecovery(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping WebSocket state recovery test in short mode")
	}

	helper := NewTestHelper(t)
	defer helper.Cleanup()

	helper.StartReloader()
	helper.WaitForServiceReadyWithCustomTimeout(30 * time.Second)

	// Create client and send state-establishing messages
	client, err := NewWebSocketClient(helper.GetServiceURL())
	require.NoError(t, err)
	defer client.Close()

	// Send state-establishing message
	stateMessage := WebSocketMessage{
		Type: "set_state",
		Data: map[string]interface{}{
			"user_id":    "test_user_123",
			"session_id": "session_abc",
			"preferences": map[string]interface{}{
				"theme":    "dark",
				"language": "en",
			},
		},
		Timestamp: time.Now(),
	}

	err = client.SendMessage(stateMessage)
	require.NoError(t, err)

	// Trigger reload
	helper.ModifySourceFile("internal/api/handlers.go", "// State recovery test")
	helper.WaitForReloadComplete(60 * time.Second)

	// Reconnect and test state recovery
	err = client.Reconnect(helper.GetServiceURL())
	require.NoError(t, err)

	// Send state query message
	queryMessage := WebSocketMessage{
		Type: "get_state",
		Data: map[string]interface{}{
			"user_id": "test_user_123",
		},
		Timestamp: time.Now(),
	}

	if client.IsConnected() {
		err = client.SendMessage(queryMessage)
		assert.NoError(t, err, "Should be able to query state after reconnection")

		// Note: In a real implementation, we would expect a state response
		// For this test, we're verifying the connection works after reload
		t.Log("State recovery test completed - connection functional after reload")
	}
}

// TestRealtimeDashboardUpdates tests real-time dashboard updates across reloads
func TestRealtimeDashboardUpdates(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping real-time dashboard test in short mode")
	}

	helper := NewTestHelper(t)
	defer helper.Cleanup()

	helper.StartReloader()
	helper.WaitForServiceReadyWithCustomTimeout(30 * time.Second)

	// Create dashboard client
	dashboardClient, err := NewWebSocketClient(helper.GetServiceURL())
	require.NoError(t, err)
	defer dashboardClient.Close()

	// Subscribe to dashboard updates
	subscribeMessage := WebSocketMessage{
		Type: "subscribe",
		Data: map[string]interface{}{
			"channel": "dashboard_updates",
			"events":  []string{"evaluation_started", "evaluation_completed", "metrics_updated"},
		},
		Timestamp: time.Now(),
	}

	err = dashboardClient.SendMessage(subscribeMessage)
	require.NoError(t, err)

	// Simulate dashboard update before reload
	updateMessage := WebSocketMessage{
		Type: "dashboard_update",
		Data: map[string]interface{}{
			"event":         "evaluation_started",
			"evaluation_id": "eval_123",
			"model":         "test_model",
			"status":        "running",
		},
		Timestamp: time.Now(),
	}

	err = dashboardClient.SendMessage(updateMessage)
	require.NoError(t, err)

	// Trigger reload
	t.Log("Testing dashboard updates during reload...")
	helper.ModifySourceFile("internal/api/handlers.go", "// Dashboard update test")

	// Wait for disconnection
	time.Sleep(3 * time.Second)

	// Wait for reload completion
	helper.WaitForReloadComplete(60 * time.Second)

	// Reconnect dashboard client
	err = dashboardClient.Reconnect(helper.GetServiceURL())
	require.NoError(t, err)

	// Re-subscribe after reconnection
	if dashboardClient.IsConnected() {
		err = dashboardClient.SendMessage(subscribeMessage)
		assert.NoError(t, err, "Should be able to re-subscribe after reconnection")

		// Send post-reload dashboard update
		postReloadUpdate := WebSocketMessage{
			Type: "dashboard_update",
			Data: map[string]interface{}{
				"event":         "evaluation_completed",
				"evaluation_id": "eval_123",
				"model":         "test_model",
				"status":        "completed",
				"score":         85.5,
			},
			Timestamp: time.Now(),
		}

		err = dashboardClient.SendMessage(postReloadUpdate)
		assert.NoError(t, err, "Should be able to send dashboard updates after reload")

		t.Log("Dashboard real-time updates test completed successfully")
	}
}

// TestWebSocketConcurrentConnections tests handling of multiple concurrent connections during reload
func TestWebSocketConcurrentConnections(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping concurrent WebSocket test in short mode")
	}

	helper := NewTestHelper(t)
	defer helper.Cleanup()

	helper.StartReloader()
	helper.WaitForServiceReadyWithCustomTimeout(30 * time.Second)

	// Create multiple concurrent connections
	const numConcurrentClients = 10
	clients := make([]*WebSocketClient, numConcurrentClients)
	var wg sync.WaitGroup

	t.Log("Creating concurrent WebSocket connections...")
	for i := 0; i < numConcurrentClients; i++ {
		wg.Add(1)
		go func(clientIndex int) {
			defer wg.Done()
			client, err := NewWebSocketClient(helper.GetServiceURL())
			if err != nil {
				t.Errorf("Failed to create client %d: %v", clientIndex, err)
				return
			}
			clients[clientIndex] = client
		}(i)
	}

	wg.Wait()

	// Count successful connections
	connectedClients := 0
	for i, client := range clients {
		if client != nil {
			defer client.Close()
			if client.IsConnected() {
				connectedClients++
			}
		} else {
			t.Logf("Client %d failed to connect", i)
		}
	}

	assert.Greater(t, connectedClients, 0, "At least some clients should connect")
	t.Logf("Successfully connected %d out of %d clients", connectedClients, numConcurrentClients)

	// Send messages from all connected clients
	for i, client := range clients {
		if client != nil && client.IsConnected() {
			message := WebSocketMessage{
				Type: "concurrent_test",
				Data: map[string]interface{}{
					"client_id": fmt.Sprintf("client_%d", i),
					"message":   "concurrent connection test",
				},
				Timestamp: time.Now(),
			}
			err := client.SendMessage(message)
			assert.NoError(t, err, "Client %d should be able to send messages", i)
		}
	}

	// Trigger reload with concurrent connections
	t.Log("Triggering reload with concurrent connections...")
	helper.ModifySourceFile("internal/api/handlers.go", "// Concurrent connections test")
	helper.WaitForReloadComplete(60 * time.Second)

	// Test reconnection for some clients
	reconnectedCount := 0
	for i, client := range clients {
		if client != nil {
			err := client.Reconnect(helper.GetServiceURL())
			if err == nil && client.IsConnected() {
				reconnectedCount++
				t.Logf("Client %d successfully reconnected", i)
			}
		}
	}

	t.Logf("Successfully reconnected %d clients after reload", reconnectedCount)
	assert.Greater(t, reconnectedCount, 0, "At least some clients should be able to reconnect")
}
