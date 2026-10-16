# Auto-Reload Wrapper for Go Service

## Overview

The auto-reload wrapper provides automatic service restarting when Go source files change, enabling rapid development cycles without manual intervention.

## Quick Start

### Using the Development Script (Recommended)

```bash
# From the project root
./go-service/scripts/dev-watch.sh
```

### Manual Usage

```bash
# Build and run the reloader
cd go-service
go run cmd/reloader/main.go
```

## Features

### 🔄 **Automatic Reloading**
- Monitors `**/*.go`, `**/go.mod`, and `**/go.sum` files
- 500ms debouncing to prevent excessive restarts
- Intelligent filtering to exclude temporary files and build artifacts

### 🛑 **Graceful Shutdown**
- SIGTERM signal handling with 10-second timeout
- Database connection draining
- In-flight request completion
- Fallback to force kill if graceful shutdown fails

### 🎨 **Developer-Friendly Output**
- Colorized terminal output
- Real-time reload status and timing
- Clear compilation error messages
- Service startup confirmation

### 🔧 **Error Recovery**
- Compilation errors don't terminate the wrapper
- Automatic retry on file changes
- Maintains service availability during error conditions

## Configuration

### Environment Variables

```bash
# Logging configuration
LOG_LEVEL=info                    # Log level (debug, info, warn, error)
DEV_MODE=true                     # Enable development mode
LOG_FILE=logs/reloader.log        # Log file path

# File watching configuration
WATCH_ENABLED=true                # Enable file watching
WATCH_DIR=go-service              # Directory to watch
WATCH_DEBOUNCE_MS=500            # Debounce time in milliseconds
WATCH_PATTERNS="**/*.go,**/go.mod,**/go.sum"  # Files to watch
WATCH_EXCLUDES="*.tmp,*~,.#*,*.swp,*.swo,**/bin/**,**/tmp/**,**/.git/**,**/vendor/**"

# Reload configuration
GRACEFUL_TIMEOUT_SEC=10          # Graceful shutdown timeout
RESTART_DELAY_MS=1000            # Delay between stop and start
```

### Default Behavior

- **Build Command**: `go build -o bin/server cmd/server/main.go`
- **Start Command**: `./bin/server`
- **Working Directory**: Current directory (`.`)
- **Graceful Timeout**: 10 seconds
- **Restart Delay**: 1 second

## File Structure

```
go-service/
├── cmd/
│   ├── reloader/main.go          # Auto-reload wrapper command
│   └── server/main.go            # Main server (enhanced with graceful shutdown)
├── internal/devtools/
│   ├── reloader.go               # Service lifecycle management
│   ├── watcher.go                # File watching (from Story 2.01)
│   ├── config.go                 # Configuration management
│   └── patterns.go               # File pattern matching
├── scripts/
│   └── dev-watch.sh              # Development wrapper script
└── tests/unit/devtools/
    └── reloader_test.go          # Unit tests
```

## Usage Examples

### Basic Development Workflow

1. **Start auto-reload**:
   ```bash
   ./go-service/scripts/dev-watch.sh
   ```

2. **Edit Go files** - the service will automatically rebuild and restart

3. **View logs** in real-time for both the reloader and service

4. **Stop with Ctrl+C** - graceful shutdown of both reloader and service

### Custom Configuration

```bash
# Use custom timeout and delay
GRACEFUL_TIMEOUT_SEC=15 RESTART_DELAY_MS=2000 go run cmd/reloader/main.go

# Enable debug logging
LOG_LEVEL=debug DEV_MODE=true go run cmd/reloader/main.go
```

## Integration with IDE

### VS Code

Add to `.vscode/tasks.json`:

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Start Auto-Reload",
            "type": "shell",
            "command": "./go-service/scripts/dev-watch.sh",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "new"
            },
            "runOptions": {
                "runOn": "folderOpen"
            }
        }
    ]
}
```

### Terminal Output

```
🚀 Go Service Auto-Reload Started
📁 Watching: go-service/**/*.go
🔄 Auto-reload enabled with 500ms debounce
⚡ Press Ctrl+C to stop

🔄 Reloading service...
📝 Changed files: internal/api/handlers.go
✅ Reload completed in 1.2s
🟢 Service ready

❌ Build failed:
./internal/api/handlers.go:45:2: undefined: someFunction
🔧 Waiting for fixes...
```

## Troubleshooting

### Common Issues

1. **Build Fails**
   - Check compilation errors in terminal output
   - Verify Go module dependencies are up to date
   - Ensure working directory is correct

2. **Service Won't Start**
   - Check if port is already in use
   - Verify binary permissions in `bin/` directory
   - Review service logs for startup errors

3. **File Changes Not Detected**
   - Verify file patterns in `WATCH_PATTERNS`
   - Check if files are in excluded directories
   - Ensure file watcher has proper permissions

### Debug Mode

Enable debug logging to see detailed information:

```bash
LOG_LEVEL=debug DEV_MODE=true go run cmd/reloader/main.go
```

## Dependencies

- **File Watching**: `github.com/fsnotify/fsnotify v1.7.0`
- **Logging**: `gopkg.in/natefinch/lumberjack.v2 v2.2.1`
- **UUID Generation**: `github.com/google/uuid v1.6.0`
- **System Calls**: `golang.org/x/sys v0.22.0`

## Testing

Run the unit tests:

```bash
cd go-service
go test ./tests/unit/devtools/reloader_test.go -v
```

## Related Stories

- **Story 2.01**: File watching foundation (dependency)
- **Epic 1**: Structured logging system (used for reloader logs)