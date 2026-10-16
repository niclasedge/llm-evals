package ollama

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"time"

	"go-service/internal/logging"
	"go-service/internal/models"
)

// Config holds configuration for the Ollama client
type Config struct {
	BaseURL       string
	PoolSize      int
	RetryAttempts int
	Timeout       time.Duration
}

// Client wraps HTTP client with connection pooling and retry logic
type Client struct {
	config     Config
	httpClient *http.Client
	pool       *Pool
	logger     *logging.Logger
}

// NewClient creates a new Ollama client with configuration from environment
func NewClient() *Client {
	config := Config{
		BaseURL:       getEnvOrDefault("OLLAMA_BASE_URL", "http://localhost:11434"),
		PoolSize:      getEnvIntOrDefault("OLLAMA_POOL_SIZE", 10),
		RetryAttempts: getEnvIntOrDefault("OLLAMA_RETRY_ATTEMPTS", 3),
		Timeout:       time.Duration(getEnvIntOrDefault("OLLAMA_TIMEOUT", 30)) * time.Second,
	}

	httpClient := &http.Client{
		Timeout: config.Timeout,
		Transport: &http.Transport{
			MaxIdleConns:        config.PoolSize,
			MaxIdleConnsPerHost: config.PoolSize,
			IdleConnTimeout:     90 * time.Second,
		},
	}

	return &Client{
		config:     config,
		httpClient: httpClient,
		pool:       NewPool(config.PoolSize),
		logger:     logging.NewDefaultLogger(),
	}
}

// Generate makes a request to the /api/generate endpoint
func (c *Client) Generate(ctx context.Context, req models.GenerateRequest) (*models.GenerateResponse, error) {
	startTime := time.Now()
	contextLogger := logging.LogWithContext(ctx, c.logger.Logger)

	contextLogger.Debug("Making Ollama generate request",
		"model", req.Model,
		"prompt_length", len(req.Prompt),
	)

	url := c.config.BaseURL + "/api/generate"
	body, err := json.Marshal(req)
	if err != nil {
		contextLogger.Error("Failed to marshal generate request", "error", err)
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	var response models.GenerateResponse
	err = c.makeRequest(ctx, "POST", url, body, &response)
	if err != nil {
		contextLogger.Error("Ollama generate request failed", "error", err, "model", req.Model)
		return nil, err
	}

	// Add timing information as expected by Python client
	response.Timing = models.TimingInfo{
		ResponseTime: time.Since(startTime).Seconds(),
		Timestamp:    float64(time.Now().UnixMilli()) / 1000.0,
	}

	contextLogger.Debug("Ollama generate request completed",
		"model", req.Model,
		"response_time_ms", time.Since(startTime).Milliseconds(),
	)

	return &response, nil
}

// Chat makes a request to the /api/chat endpoint
func (c *Client) Chat(ctx context.Context, req models.ChatRequest) (*models.ChatResponse, error) {
	startTime := time.Now()
	contextLogger := logging.LogWithContext(ctx, c.logger.Logger)

	contextLogger.Debug("Making Ollama chat request",
		"model", req.Model,
		"messages_count", len(req.Messages),
	)

	url := c.config.BaseURL + "/api/chat"
	body, err := json.Marshal(req)
	if err != nil {
		contextLogger.Error("Failed to marshal chat request", "error", err)
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	var response models.ChatResponse
	err = c.makeRequest(ctx, "POST", url, body, &response)
	if err != nil {
		contextLogger.Error("Ollama chat request failed", "error", err, "model", req.Model)
		return nil, err
	}

	// Add timing information as expected by Python client
	response.Timing = models.TimingInfo{
		ResponseTime: time.Since(startTime).Seconds(),
		Timestamp:    float64(time.Now().UnixMilli()) / 1000.0,
	}

	contextLogger.Debug("Ollama chat request completed",
		"model", req.Model,
		"response_time_ms", time.Since(startTime).Milliseconds(),
	)

	return &response, nil
}

// ListModels makes a request to the /api/tags endpoint
func (c *Client) ListModels(ctx context.Context) (*models.TagsResponse, error) {
	url := c.config.BaseURL + "/api/tags"

	var response models.TagsResponse
	err := c.makeRequest(ctx, "GET", url, nil, &response)
	if err != nil {
		return nil, err
	}

	return &response, nil
}

// PullModel makes a request to the /api/pull endpoint
func (c *Client) PullModel(ctx context.Context, req models.PullRequest) error {
	url := c.config.BaseURL + "/api/pull"
	body, err := json.Marshal(req)
	if err != nil {
		return fmt.Errorf("failed to marshal request: %w", err)
	}

	// For pull operations, we don't parse the response as it's streaming
	return c.makeRequest(ctx, "POST", url, body, nil)
}

// ShowModel makes a request to the /api/show endpoint
func (c *Client) ShowModel(ctx context.Context, req models.ShowRequest) (*models.ShowResponse, error) {
	url := c.config.BaseURL + "/api/show"
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	var response models.ShowResponse
	err = c.makeRequest(ctx, "POST", url, body, &response)
	if err != nil {
		return nil, err
	}

	return &response, nil
}

// HealthCheck performs a simple health check by listing models
func (c *Client) HealthCheck(ctx context.Context) error {
	_, err := c.ListModels(ctx)
	return err
}

// makeRequest handles the HTTP request with retry logic
func (c *Client) makeRequest(ctx context.Context, method, url string, body []byte, response interface{}) error {
	var lastErr error
	contextLogger := logging.LogWithContext(ctx, c.logger.Logger)

	for attempt := 0; attempt < c.config.RetryAttempts; attempt++ {
		if attempt > 0 {
			// Exponential backoff
			backoff := time.Duration(attempt*attempt) * 100 * time.Millisecond
			contextLogger.Debug("Retrying Ollama request",
				"attempt", attempt,
				"backoff_ms", backoff.Milliseconds(),
				"url", url,
			)
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(backoff):
			}
		}

		err := c.doRequest(ctx, method, url, body, response)
		if err == nil {
			if attempt > 0 {
				contextLogger.Info("Ollama request succeeded after retry",
					"attempt", attempt+1,
					"url", url,
				)
			}
			return nil
		}

		lastErr = err

		// Don't retry on context cancellation or certain HTTP errors
		if ctx.Err() != nil {
			return ctx.Err()
		}

		contextLogger.Debug("Ollama request attempt failed",
			"attempt", attempt+1,
			"error", err,
			"url", url,
		)
	}

	contextLogger.Error("Ollama request failed after all retries",
		"attempts", c.config.RetryAttempts,
		"error", lastErr,
		"url", url,
	)
	return fmt.Errorf("request failed after %d attempts: %w", c.config.RetryAttempts, lastErr)
}

// doRequest performs a single HTTP request
func (c *Client) doRequest(ctx context.Context, method, url string, body []byte, response interface{}) error {
	var bodyReader io.Reader
	if body != nil {
		bodyReader = bytes.NewReader(body)
	}

	req, err := http.NewRequestWithContext(ctx, method, url, bodyReader)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	// Add correlation ID to request headers for tracing
	if correlationID := logging.GetCorrelationID(ctx); correlationID != "" {
		req.Header.Set("X-Correlation-ID", correlationID)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(bodyBytes))
	}

	if response != nil {
		if err := json.NewDecoder(resp.Body).Decode(response); err != nil {
			return fmt.Errorf("failed to decode response: %w", err)
		}
	}

	return nil
}

// Helper functions for environment variable parsing
func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvIntOrDefault(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if parsed, err := strconv.Atoi(value); err == nil {
			return parsed
		}
	}
	return defaultValue
}
