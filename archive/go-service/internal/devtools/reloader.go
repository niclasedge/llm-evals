package devtools

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"go-service/internal/logging"
)

// ServiceReloader manages the lifecycle of the Go service with auto-reload capabilities
type ServiceReloader struct {
	cmd          *exec.Cmd
	ctx          context.Context
	cancel       context.CancelFunc
	watcher      *FileWatcher
	buildPath    string
	restartChan  chan []string
	shutdownChan chan os.Signal
	config       *ReloadConfig
	logger       *logging.Logger
	mu           sync.RWMutex
	running      bool
	startTime    time.Time
}

// ReloadConfig defines configuration for the service reloader
type ReloadConfig struct {
	BuildCommand    []string      `default:"go,build,-o,bin/server,cmd/server/main.go"`
	StartCommand    []string      `default:"./bin/server"`
	GracefulTimeout time.Duration `default:"10s"`
	RestartDelay    time.Duration `default:"1s"`
	WorkingDir      string        `default:"go-service"`
	ShowOutput      bool          `default:"true"`
	BuildDir        string        `default:"bin"`
	ServerBinary    string        `default:"bin/server"`
}

// NewServiceReloader creates a new service reloader with the provided configuration
func NewServiceReloader(config *ReloadConfig, logger *logging.Logger) (*ServiceReloader, error) {
	if config == nil {
		config = DefaultReloadConfig()
	}

	if logger == nil {
		logger = logging.NewDefaultLogger()
	}

	ctx, cancel := context.WithCancel(context.Background())

	// Create file watcher
	watchConfig := &WatchConfig{
		RootDir:    config.WorkingDir,
		Patterns:   []string{"**/*.go", "**/go.mod", "**/go.sum"},
		Excludes:   []string{"**/bin/**", "**/tmp/**", "**/.git/**", "**/vendor/**", "**/*_test.go"},
		DebounceMs: 500,
	}

	watcher, err := NewFileWatcher(watchConfig, logger)
	if err != nil {
		cancel()
		return nil, fmt.Errorf("failed to create file watcher: %w", err)
	}

	sr := &ServiceReloader{
		ctx:          ctx,
		cancel:       cancel,
		watcher:      watcher,
		config:       config,
		logger:       logger,
		restartChan:  make(chan []string, 10),
		shutdownChan: make(chan os.Signal, 1),
		running:      false,
	}

	// Setup signal handling for graceful shutdown
	signal.Notify(sr.shutdownChan, syscall.SIGINT, syscall.SIGTERM)

	return sr, nil
}

// DefaultReloadConfig returns default configuration for service reloader
func DefaultReloadConfig() *ReloadConfig {
	return &ReloadConfig{
		BuildCommand:    []string{"go", "build", "-o", "bin/server", "cmd/server/main.go"},
		StartCommand:    []string{"./bin/server"},
		GracefulTimeout: 10 * time.Second,
		RestartDelay:    1 * time.Second,
		WorkingDir:      ".",
		ShowOutput:      true,
		BuildDir:        "bin",
		ServerBinary:    "bin/server",
	}
}

// Start begins the service reloader lifecycle
func (sr *ServiceReloader) Start() error {
	sr.mu.Lock()
	defer sr.mu.Unlock()

	if sr.running {
		return fmt.Errorf("service reloader is already running")
	}

	correlationID := logging.NewCorrelationID()
	ctx := logging.WithCorrelationID(sr.ctx, correlationID)
	logger := logging.LogWithContext(ctx, sr.logger.Logger)

	logger.Info("Starting service reloader",
		"component", "devtools.reloader",
		"working_dir", sr.config.WorkingDir,
		"build_command", strings.Join(sr.config.BuildCommand, " "),
		"start_command", strings.Join(sr.config.StartCommand, " "),
	)

	// Ensure build directory exists
	if err := os.MkdirAll(sr.config.BuildDir, 0755); err != nil {
		return fmt.Errorf("failed to create build directory: %w", err)
	}

	// Initial build and start
	if err := sr.initialBuildAndStart(ctx); err != nil {
		return fmt.Errorf("initial build and start failed: %w", err)
	}

	// Start file watcher
	if err := sr.watcher.Start(); err != nil {
		return fmt.Errorf("failed to start file watcher: %w", err)
	}

	sr.running = true
	sr.startTime = time.Now()

	// Start monitoring goroutines
	go sr.watchForChanges(ctx)
	go sr.watchForShutdown(ctx)

	logger.Info("Service reloader started successfully",
		"component", "devtools.reloader",
	)

	sr.displayStartupMessage()

	return nil
}

// Stop gracefully stops the service reloader
func (sr *ServiceReloader) Stop() error {
	sr.mu.Lock()
	defer sr.mu.Unlock()

	if !sr.running {
		return nil
	}

	correlationID := logging.NewCorrelationID()
	ctx := logging.WithCorrelationID(context.Background(), correlationID)
	logger := logging.LogWithContext(ctx, sr.logger.Logger)

	logger.Info("Stopping service reloader",
		"component", "devtools.reloader",
	)

	sr.running = false

	// Stop file watcher
	if err := sr.watcher.Stop(); err != nil {
		logger.Error("Error stopping file watcher",
			"component", "devtools.reloader",
			"error", err,
		)
	}

	// Gracefully shutdown service
	if err := sr.gracefulShutdown(ctx); err != nil {
		logger.Error("Error during graceful shutdown",
			"component", "devtools.reloader",
			"error", err,
		)
	}

	sr.cancel()

	logger.Info("Service reloader stopped successfully",
		"component", "devtools.reloader",
	)

	return nil
}

// IsRunning returns whether the reloader is currently running
func (sr *ServiceReloader) IsRunning() bool {
	sr.mu.RLock()
	defer sr.mu.RUnlock()
	return sr.running
}

// initialBuildAndStart performs the initial build and start of the service
func (sr *ServiceReloader) initialBuildAndStart(ctx context.Context) error {
	logger := logging.LogWithContext(ctx, sr.logger.Logger)

	logger.Info("Performing initial build",
		"component", "devtools.reloader",
	)

	start := time.Now()

	// Build the service
	if err := sr.buildService(ctx); err != nil {
		return fmt.Errorf("initial build failed: %w", err)
	}

	// Start the service
	if err := sr.startService(ctx); err != nil {
		return fmt.Errorf("initial start failed: %w", err)
	}

	duration := time.Since(start)
	logger.Info("Initial build and start completed",
		"component", "devtools.reloader",
		"duration_ms", duration.Milliseconds(),
	)

	return nil
}

// buildService builds the Go service binary
func (sr *ServiceReloader) buildService(ctx context.Context) error {
	logger := logging.LogWithContext(ctx, sr.logger.Logger)

	logger.Info("Building service",
		"component", "devtools.reloader",
		"command", strings.Join(sr.config.BuildCommand, " "),
	)

	buildCmd := exec.CommandContext(ctx, sr.config.BuildCommand[0], sr.config.BuildCommand[1:]...)
	buildCmd.Dir = sr.config.WorkingDir

	if sr.config.ShowOutput {
		buildCmd.Stdout = os.Stdout
		buildCmd.Stderr = os.Stderr
	}

	if err := buildCmd.Run(); err != nil {
		logger.Error("Build failed",
			"component", "devtools.reloader",
			"error", err.Error(),
		)
		return fmt.Errorf("build command failed: %w", err)
	}

	logger.Info("Build completed successfully",
		"component", "devtools.reloader",
	)

	return nil
}

// startService starts the Go service as a subprocess
func (sr *ServiceReloader) startService(ctx context.Context) error {
	logger := logging.LogWithContext(ctx, sr.logger.Logger)

	logger.Info("Starting service",
		"component", "devtools.reloader",
		"command", strings.Join(sr.config.StartCommand, " "),
	)

	sr.cmd = exec.CommandContext(ctx, sr.config.StartCommand[0], sr.config.StartCommand[1:]...)
	sr.cmd.Dir = sr.config.WorkingDir

	if sr.config.ShowOutput {
		sr.cmd.Stdout = os.Stdout
		sr.cmd.Stderr = os.Stderr
	}

	if err := sr.cmd.Start(); err != nil {
		logger.Error("Failed to start service",
			"component", "devtools.reloader",
			"error", err.Error(),
		)
		return fmt.Errorf("failed to start service: %w", err)
	}

	logger.Info("Service started successfully",
		"component", "devtools.reloader",
		"pid", sr.cmd.Process.Pid,
	)

	return nil
}

// gracefulShutdown gracefully shuts down the service
func (sr *ServiceReloader) gracefulShutdown(ctx context.Context) error {
	if sr.cmd == nil || sr.cmd.Process == nil {
		return nil
	}

	logger := logging.LogWithContext(ctx, sr.logger.Logger)

	logger.Info("Initiating graceful service shutdown",
		"component", "devtools.reloader",
		"pid", sr.cmd.Process.Pid,
		"timeout", sr.config.GracefulTimeout.String(),
	)

	// Send SIGTERM for graceful shutdown
	if err := sr.cmd.Process.Signal(syscall.SIGTERM); err != nil {
		logger.Error("Failed to send SIGTERM",
			"component", "devtools.reloader",
			"error", err.Error(),
		)
		return err
	}

	// Wait for graceful shutdown with timeout
	done := make(chan error, 1)
	go func() {
		done <- sr.cmd.Wait()
	}()

	select {
	case err := <-done:
		logger.Info("Service shutdown completed",
			"component", "devtools.reloader",
			"graceful", true,
		)
		sr.cmd = nil
		return err
	case <-time.After(sr.config.GracefulTimeout):
		// Force kill if graceful shutdown times out
		logger.Warn("Graceful shutdown timeout, forcing termination",
			"component", "devtools.reloader",
			"timeout", sr.config.GracefulTimeout.String(),
		)
		err := sr.cmd.Process.Kill()
		sr.cmd = nil
		return err
	}
}

// buildAndRestart builds and restarts the service
func (sr *ServiceReloader) buildAndRestart(ctx context.Context, changedFiles []string) error {
	start := time.Now()
	logger := logging.LogWithContext(ctx, sr.logger.Logger)

	logger.Info("Starting service rebuild",
		"component", "devtools.reloader",
		"changed_files", changedFiles,
		"build_command", strings.Join(sr.config.BuildCommand, " "),
	)

	sr.displayReloadStart(changedFiles)

	// Stop current service
	if err := sr.gracefulShutdown(ctx); err != nil {
		logger.Error("Shutdown failed",
			"component", "devtools.reloader",
			"error", err.Error(),
		)
	}

	// Wait for restart delay
	if sr.config.RestartDelay > 0 {
		time.Sleep(sr.config.RestartDelay)
	}

	// Build new binary
	if err := sr.buildService(ctx); err != nil {
		logger.Error("Build failed",
			"component", "devtools.reloader",
			"error", err.Error(),
		)
		sr.displayBuildError(err)
		return err
	}

	// Start new service
	if err := sr.startService(ctx); err != nil {
		logger.Error("Start failed",
			"component", "devtools.reloader",
			"error", err.Error(),
		)
		return err
	}

	duration := time.Since(start)
	logger.Info("Service reload completed",
		"component", "devtools.reloader",
		"reload_duration_ms", duration.Milliseconds(),
		"success", true,
	)

	sr.displayReloadSuccess(duration)
	return nil
}

// watchForChanges monitors file changes and triggers rebuilds
func (sr *ServiceReloader) watchForChanges(ctx context.Context) {
	logger := logging.LogWithContext(ctx, sr.logger.Logger)

	for {
		select {
		case changes := <-sr.watcher.Changes():
			if len(changes) > 0 {
				correlationID := logging.NewCorrelationID()
				reloadCtx := logging.WithCorrelationID(ctx, correlationID)

				if err := sr.buildAndRestart(reloadCtx, changes); err != nil {
					logger.Error("Reload failed",
						"component", "devtools.reloader",
						"error", err.Error(),
					)
				}
			}

		case <-ctx.Done():
			return
		}
	}
}

// watchForShutdown monitors shutdown signals
func (sr *ServiceReloader) watchForShutdown(ctx context.Context) {
	logger := logging.LogWithContext(ctx, sr.logger.Logger)

	select {
	case sig := <-sr.shutdownChan:
		logger.Info("Shutdown signal received",
			"component", "devtools.reloader",
			"signal", sig.String(),
		)
		sr.displayShutdownMessage()
		sr.Stop()

	case <-ctx.Done():
		return
	}
}

// Color constants for terminal output
const (
	colorReset  = "\033[0m"
	colorRed    = "\033[31m"
	colorGreen  = "\033[32m"
	colorYellow = "\033[33m"
	colorBlue   = "\033[34m"
	colorPurple = "\033[35m"
	colorCyan   = "\033[36m"
	colorWhite  = "\033[37m"
)

// displayStartupMessage shows the initial startup message
func (sr *ServiceReloader) displayStartupMessage() {
	if !sr.config.ShowOutput {
		return
	}

	fmt.Printf("\n🚀 %sGo Service Auto-Reload Started%s\n", colorGreen, colorReset)
	fmt.Printf("📁 %sWatching: %s%s\n", colorBlue, sr.config.WorkingDir, colorReset)
	fmt.Printf("🔄 %sAuto-reload enabled with 500ms debounce%s\n", colorBlue, colorReset)
	fmt.Printf("⚡ %sPress Ctrl+C to stop%s\n\n", colorYellow, colorReset)
}

// displayReloadStart shows reload initiation message
func (sr *ServiceReloader) displayReloadStart(changedFiles []string) {
	if !sr.config.ShowOutput {
		return
	}

	fmt.Printf("\n🔄 %sReloading service...%s\n", colorYellow, colorReset)
	if len(changedFiles) > 0 {
		fmt.Printf("📝 %sChanged files: %s%s\n", colorCyan, strings.Join(changedFiles, ", "), colorReset)
	}
}

// displayReloadSuccess shows successful reload message
func (sr *ServiceReloader) displayReloadSuccess(duration time.Duration) {
	if !sr.config.ShowOutput {
		return
	}

	fmt.Printf("✅ %sReload completed in %v%s\n", colorGreen, duration.Round(time.Millisecond), colorReset)
	fmt.Printf("🟢 %sService ready%s\n\n", colorGreen, colorReset)
}

// displayBuildError shows build error message
func (sr *ServiceReloader) displayBuildError(err error) {
	if !sr.config.ShowOutput {
		return
	}

	fmt.Printf("\n❌ %sBuild failed:%s\n", colorRed, colorReset)
	fmt.Printf("%s%s%s\n", colorYellow, err.Error(), colorReset)
	fmt.Printf("🔧 %sWaiting for fixes...%s\n\n", colorBlue, colorReset)
}

// displayShutdownMessage shows shutdown message
func (sr *ServiceReloader) displayShutdownMessage() {
	if !sr.config.ShowOutput {
		return
	}

	uptime := time.Since(sr.startTime)
	fmt.Printf("\n🛑 %sShutting down service reloader...%s\n", colorYellow, colorReset)
	fmt.Printf("⏱️  %sUptime: %v%s\n", colorCyan, uptime.Round(time.Second), colorReset)
	fmt.Printf("👋 %sGoodbye!%s\n\n", colorGreen, colorReset)
}
