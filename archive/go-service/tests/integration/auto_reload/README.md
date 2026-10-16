# Auto-Reload Integration Tests

This directory contains comprehensive integration tests for the auto-reload functionality implemented in Stories 2.01-2.03.

## Test Structure

- `service_test.go` - Service lifecycle and basic auto-reload functionality
- `database_test.go` - Database persistence and transaction handling during reloads
- `websocket_test.go` - WebSocket connection handling and real-time features during reloads
- `monitoring_test.go` - Monitoring, health checks, and observability during reloads
- `ollama_test.go` - External service integration and connection management during reloads
- `helpers_test.go` - Common test utilities and setup functions

## Test Coverage

### AC-2.04.1: Test auto-reload with all existing service endpoints and functionality

**File:** `service_test.go`

**Tests:**
- `TestAutoReloadServiceLifecycle` - Tests complete service lifecycle with auto-reload
  - `BasicFileChangeTriggersReload` - Verifies file changes trigger service reload
  - `GoModChangeTriggersReload` - Verifies go.mod changes trigger service reload  
  - `MultipleRapidChangesDebouncing` - Tests debouncing of multiple rapid changes
  - `ServiceEndpointsWorkAfterReload` - Verifies all endpoints work after reload

- `TestAutoReloadErrorHandling` - Tests error handling during reload
  - `BuildErrorRecovery` - Tests recovery from build errors

### AC-2.04.2: Verify database connections and data persistence across reloads

**File:** `database_test.go`

**Tests:**
- `TestDatabasePersistenceAcrossReloads` - Tests data persistence through reload cycles
- `TestDatabaseConnectionHandling` - Tests connection pooling and management
- `TestTransactionHandlingDuringReload` - Tests graceful transaction completion
- `TestDatabaseMigrationWithReload` - Tests schema changes with auto-reload

### AC-2.04.3: Test WebSocket connections and real-time features during reloads

**File:** `websocket_test.go`

**Tests:**
- `TestWebSocketHandlingDuringReload` - Tests WebSocket behavior during service reloads
- `TestWebSocketClientReconnection` - Tests automatic client reconnection logic
- `TestWebSocketStateRecovery` - Tests state recovery after reconnection
- `TestRealtimeDashboardUpdates` - Tests real-time dashboard updates across reloads
- `TestWebSocketConcurrentConnections` - Tests handling of multiple concurrent connections

### AC-2.04.4: Validate Ollama client integration continues working after reloads

**File:** `ollama_test.go`

**Tests:**
- `TestOllamaClientDuringReload` - Tests Ollama client behavior during service reloads
- `TestOllamaConnectionPooling` - Tests connection pooling behavior during reloads
- `TestOllamaRetryLogicDuringReload` - Tests retry logic when service is reloading
- `TestOllamaGracefulShutdown` - Tests graceful completion of ongoing requests

### AC-2.04.5: Ensure monitoring, metrics, and health checks function correctly

**File:** `monitoring_test.go`

**Tests:**
- `TestMonitoringContinuityAcrossReloads` - Tests monitoring and health checks across reloads
- `TestHealthCheckEndpointDuringReload` - Tests health check behavior during reload cycles
- `TestMetricsEndpointReloadResilience` - Tests metrics endpoint availability
- `TestLoggingContinuityDuringReload` - Tests logging continuity before, during, and after reload
- `TestPerformanceImpactOfReload` - Measures performance impact of reload cycles

**Helper Functions:** `helpers_test.go`
- `TestHelper` - Comprehensive test helper for setting up test environment
- File modification utilities for triggering reloads
- Service monitoring and verification utilities
- WebSocket connection helper methods
- Mock external service setup utilities

## Running Tests

### Prerequisites

1. Ensure Go service dependencies are installed:
   ```bash
   cd go-service
   go mod tidy
   ```

2. Ensure the auto-reload system is built (from Stories 2.01-2.03):
   ```bash
   go build -o bin/reloader cmd/reloader/main.go
   ```

### Run Auto-Reload Tests

```bash
# Run all auto-reload integration tests
cd go-service
go test -v ./tests/integration/auto_reload/

# Run specific test
go test -v ./tests/integration/auto_reload/ -run TestAutoReloadServiceLifecycle

# Run with timeout (these are longer-running integration tests)
go test -v -timeout 5m ./tests/integration/auto_reload/

# Run in short mode (skips integration tests)
go test -short ./tests/integration/auto_reload/
```

### Test Environment

- Tests run on port 8080 (ensure this port is available)
- Tests create temporary directories for isolated service instances
- Each test gets its own service instance to avoid conflicts
- Tests automatically clean up temporary files and processes

### Troubleshooting

**Port already in use:**
- Ensure no other services are running on port 8080
- Kill any existing test processes: `pkill -f test-server`

**Build failures:**
- Ensure all dependencies are installed: `go mod tidy`
- Check that source files exist in the expected locations

**Test timeouts:**
- Increase timeout with `-timeout` flag
- Check system resources if tests are slow

## Test Architecture

### TestHelper Pattern

The tests use a `TestHelper` pattern that:

1. **Setup:** Creates isolated test environment with temporary directories
2. **Service Management:** Starts/stops auto-reload service instances
3. **File Operations:** Provides utilities for triggering file changes
4. **Verification:** Offers methods to verify service state and responsiveness
5. **Cleanup:** Automatically cleans up resources when tests complete

### Test Isolation

Each test:
- Gets its own temporary directory
- Runs its own service instance on a unique port
- Has isolated file system changes
- Cleans up completely after execution

This ensures tests can run in parallel without interfering with each other.

## Integration with Existing Test Infrastructure

These tests integrate with:
- Existing Go service build system
- Structured logging framework
- Service health check endpoints
- Existing test patterns and utilities

The tests validate that the auto-reload system works correctly with all existing service components without breaking functionality.