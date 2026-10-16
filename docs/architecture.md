# Architecture

This document outlines the general architecture of the `llm-evals` project.

**Note:** Ideally, this file should be in a `docs/` subdirectory. There were issues creating files in subdirectories automatically.

## Core Principles

- **Feature-Driven Development:** The project is organized around business features. Each feature resides in its own directory under `src/features/`.
- **Strict Feature Isolation:** Modules within a feature directory should not directly import from other feature directories. Shared logic should be placed in `src/core/` or `src/shared/` (with a preference for duplication over complex shared dependencies).
- **Modularity:** Code should be broken down into logical components.

## Directory Structure (Intended)

- `docs/`: Contains project documentation, including this file, `conventions.md`, and `TASKS.md`.
- `src/`: Contains all source code.
  - `src/core/`: Core infrastructure, utilities, and base classes used across multiple features.
  - `src/features/`: Contains individual feature modules.
    - `src/features/<feature_name>/`:
      - `models.py` / `schemas.py`: Data models and schemas.
      - `service.py` / `logic.py` / `handler.py`: Core business logic.
      - `endpoints.py` / `controller.py` / `routes.py`: API endpoints or entry points.
      - `tests/`: Unit and integration tests for the feature.
  - `src/shared/`: Code shared by multiple features (use sparingly).
- `go-service/`: Go-based LLM evaluation service (see Go Service Architecture section).
- `tests/`: Global tests or test utilities (if any, feature tests are preferred within `src/features/<feature_name>/tests/`).
- `TASKS.md`: Tracks project tasks.
- `CHANGELOG.md`: Records changes to the project.
- `requirements.txt`: Python package dependencies.
- `README.md`: Project overview.

---

## Go Service Architecture

The `go-service/` directory contains a standalone Go service that provides LLM evaluation capabilities with monitoring, analytics, and testing interfaces.

### Core Architecture Principles

- **Clean Architecture:** Separation of concerns with distinct layers (API, business logic, data access)
- **Dependency Injection:** Components are loosely coupled and easily testable
- **Event-Driven:** Real-time updates via WebSocket connections
- **Observability:** Comprehensive metrics, monitoring, and structured logging

### Go Service Directory Structure

```
go-service/
├── cmd/
│   ├── server/main.go          # Application entry point
│   └── migrate/main.go         # Database migration utility
├── internal/
│   ├── api/                    # HTTP handlers and routing
│   │   ├── handlers.go         # Core HTTP handlers
│   │   ├── ollama.go          # Ollama LLM integration endpoints
│   │   ├── dashboard.go        # Dashboard and UI endpoints
│   │   ├── metrics.go         # Metrics collection endpoints
│   │   ├── middleware.go       # HTTP middleware (CORS, logging, recovery)
│   │   └── validation.go       # Request validation
│   ├── database/               # Data persistence layer
│   │   ├── sqlite.go          # SQLite connection management
│   │   ├── repository.go       # Data access patterns
│   │   ├── migrations.go       # Schema migration system
│   │   └── migrations/         # SQL migration files
│   ├── models/                 # Data models and types
│   │   ├── evaluation.go       # Evaluation result models
│   │   ├── requests.go         # API request structures
│   │   ├── responses.go        # API response structures
│   │   └── types.go           # Common types and constants
│   ├── ollama/                 # Ollama client integration
│   │   ├── client.go          # HTTP client for Ollama API
│   │   ├── pool.go            # Connection pooling
│   │   └── retry.go           # Retry logic and error handling
│   ├── monitoring/             # Observability and analytics
│   │   ├── metrics.go         # Prometheus metrics collection
│   │   ├── analytics.go       # Performance analytics
│   │   └── load_testing.go    # Load testing capabilities
│   └── health/                 # Health checking
│       └── checker.go         # Health check implementations
├── tests/                      # Test suites
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   ├── database/              # Database-specific tests
│   └── monitoring/            # Monitoring and performance tests
├── docker/                     # Docker configuration
├── go.mod                      # Go module definition
└── go.sum                      # Go module checksums
```

### Enhancement Architecture (Brownfield Additions)

#### 1. Development Environment Enhancement

**File Watching System:**
```
go-service/
├── internal/
│   └── devtools/               # NEW: Development tooling
│       ├── watcher.go         # File system monitoring
│       ├── reloader.go        # Service lifecycle management
│       └── config.go          # Development configuration
└── scripts/
    └── dev-watch.sh           # NEW: Auto-reload wrapper script
```

**Components:**
- **File Watcher:** Uses `fsnotify` to monitor Go source files
- **Graceful Restart:** Manages service shutdown and startup
- **State Preservation:** Maintains database connections across restarts
- **Error Recovery:** Handles compilation errors gracefully

#### 2. Centralized Logging Architecture

**Logging System Structure:**
```
go-service/
├── internal/
│   └── logging/               # NEW: Centralized logging
│       ├── logger.go         # Structured logger configuration
│       ├── middleware.go     # HTTP request logging
│       ├── rotation.go       # Log file rotation
│       └── context.go        # Request correlation
├── logs/                      # NEW: Log file storage
│   ├── go-service.log        # Main application log
│   ├── go-service.log.1      # Rotated logs
│   └── error.log             # Error-only log
└── Makefile                   # ENHANCED: Log management commands
```

**Logging Features:**
- **Structured JSON:** Consistent log format with fields
- **Multiple Outputs:** File + stdout for development
- **Log Rotation:** Daily rotation, 10 files max, 100MB limit
- **Request Correlation:** Unique IDs tracking requests across services
- **Log Levels:** DEBUG, INFO, WARN, ERROR with filtering

#### 3. Enhanced Test Execution UI

**UI Architecture Extension:**
```
go-service/
├── internal/
│   ├── api/
│   │   ├── testing.go         # NEW: Test execution endpoints
│   │   ├── categories.go      # NEW: Test categorization
│   │   └── results.go         # NEW: Result management
│   ├── testing/               # NEW: Test execution engine
│   │   ├── executor.go        # Test runner and orchestration
│   │   ├── categories.go      # Test type definitions
│   │   ├── templates.go       # Predefined test templates
│   │   └── progress.go        # Real-time progress tracking
│   └── websocket/             # NEW: Real-time communication
│       ├── hub.go            # WebSocket connection management
│       ├── client.go         # Client connection handling
│       └── messages.go       # Message type definitions
└── web/                       # NEW: Enhanced UI assets
    ├── static/
    │   ├── js/
    │   │   ├── test-runner.js # Test execution interface
    │   │   ├── results.js     # Results display and filtering
    │   │   └── websocket.js   # Real-time updates
    │   └── css/
    │       └── testing.css    # Test UI styling
    └── templates/
        └── testing.html       # Test execution UI
```

**UI Components:**
- **Test Runner Panel:** Model selection, test type, parameters
- **Progress Indicators:** Real-time test execution feedback
- **Results Grid:** Categorized display with filtering/sorting
- **Comparison View:** Side-by-side model comparison
- **Export Functions:** JSON/CSV download capabilities

#### 4. Database Schema Enhancements

**New Tables and Relationships:**
```sql
-- Test execution tracking
CREATE TABLE test_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_type VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    prompt TEXT NOT NULL,
    parameters JSON,
    status VARCHAR(20) DEFAULT 'running',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    execution_time_ms INTEGER
);

-- Test results with categorization
CREATE TABLE test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id INTEGER REFERENCES test_executions(id),
    category VARCHAR(50) NOT NULL,
    score REAL,
    response TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Test categories and templates
CREATE TABLE test_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    template_prompt TEXT,
    default_parameters JSON
);
```

### Integration Patterns

#### 1. WebSocket Integration
**Real-time Updates:** Extends existing WebSocket system for test progress
```go
type TestProgressMessage struct {
    Type        string  `json:"type"`
    ExecutionID int64   `json:"execution_id"`
    Progress    float64 `json:"progress"`
    Status      string  `json:"status"`
    Message     string  `json:"message,omitempty"`
}
```

#### 2. API Pattern Consistency
**RESTful Endpoints:** Following existing API patterns
```
GET    /api/testing/categories          # List test categories
POST   /api/testing/execute             # Execute new test
GET    /api/testing/results             # Get test results
GET    /api/testing/history             # Test execution history
POST   /api/testing/compare             # Compare test results
```

#### 3. Middleware Integration
**Enhanced Middleware Stack:**
```go
router.Use(LoggingMiddleware)           // Enhanced with structured logging
router.Use(CORSMiddleware)              // Existing
router.Use(ContentTypeMiddleware)       // Existing
router.Use(RecoveryMiddleware)          // Enhanced with logging
router.Use(MetricsMiddleware)           // Enhanced with test metrics
router.Use(CorrelationIDMiddleware)     // NEW: Request correlation
```

### Technology Stack Additions

#### New Dependencies
```go
// File watching
"github.com/fsnotify/fsnotify"

// Structured logging
"github.com/sirupsen/logrus"
// OR
"github.com/rs/zerolog"

// Log rotation
"gopkg.in/natefinch/lumberjack.v2"

// WebSocket (already present)
"github.com/gorilla/websocket"

// JSON handling (already present)
"encoding/json"
```

#### Configuration Management
**Environment-based Configuration:**
```go
type Config struct {
    // Existing
    Port           string
    DatabaseURL    string
    OllamaURL      string
    
    // NEW: Development
    DevMode        bool   `env:"DEV_MODE" default:"false"`
    WatchFiles     bool   `env:"WATCH_FILES" default:"true"`
    
    // NEW: Logging
    LogLevel       string `env:"LOG_LEVEL" default:"info"`
    LogFile        string `env:"LOG_FILE" default:"logs/go-service.log"`
    LogRotateSize  int    `env:"LOG_ROTATE_SIZE" default:"100"`
    LogRotateCount int    `env:"LOG_ROTATE_COUNT" default:"10"`
}
```

### Deployment and Operations

#### Enhanced Makefile Commands
```makefile
# Development
dev-watch:          # Start service with file watching
logs:               # Show latest 50 log entries
logs-tail:          # Follow logs in real-time
logs-clean:         # Clean old log files

# Testing
test-ui:            # Run UI functionality tests
test-integration:   # Run enhanced integration tests
```

#### Docker Integration
**Development Container Support:**
```dockerfile
# Multi-stage build with development tools
FROM golang:1.21-alpine AS development
RUN apk add --no-cache git
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
# Install file watching tools for development
RUN go install github.com/cosmtrek/air@latest
```

### Security Considerations

#### 1. Input Validation
- **Request Sanitization:** All test inputs validated and sanitized
- **Prompt Injection Prevention:** Filtering of malicious prompt patterns
- **Rate Limiting:** Test execution rate limits per client

#### 2. Resource Management
- **Memory Limits:** Test execution memory boundaries
- **Timeout Controls:** Maximum test execution time limits
- **Concurrent Limits:** Maximum simultaneous test executions

#### 3. Data Privacy
- **Log Sanitization:** Sensitive data filtering in logs
- **Test Data Retention:** Configurable data retention policies
- **Access Controls:** Basic authentication for test execution

### Monitoring and Observability

#### Enhanced Metrics
```go
// Existing metrics extended with test-specific metrics
testExecutionTotal := prometheus.NewCounterVec(
    prometheus.CounterOpts{
        Name: "test_executions_total",
        Help: "Total number of test executions",
    },
    []string{"model", "category", "status"},
)

testExecutionDuration := prometheus.NewHistogramVec(
    prometheus.HistogramOpts{
        Name: "test_execution_duration_seconds",
        Help: "Test execution duration",
    },
    []string{"model", "category"},
)
```

#### Health Checks
**Enhanced Health Monitoring:**
- Service health (existing)
- Ollama connectivity (existing)
- Database connectivity (existing)
- **NEW:** Log file write permissions
- **NEW:** File watcher status
- **NEW:** WebSocket connection health

This architecture ensures the Go service enhancements integrate seamlessly with the existing system while providing robust testing capabilities, improved developer experience, and comprehensive observability.
