package devtools

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/fsnotify/fsnotify"
	"go-service/internal/logging"
)

// FileWatcher provides file system monitoring with debouncing and filtering
type FileWatcher struct {
	watcher        *fsnotify.Watcher
	config         *WatchConfig
	logger         *logging.Logger
	changesChan    chan []string
	ctx            context.Context
	cancel         context.CancelFunc
	mu             sync.RWMutex
	running        bool
	watchMatcher   *PatternMatcher
	excludeMatcher *PatternMatcher
}

// WatchConfig defines file watching configuration
type WatchConfig struct {
	RootDir    string   // Root directory to watch
	Patterns   []string // File patterns to watch
	Excludes   []string // Patterns to exclude
	DebounceMs int      // Debounce time in milliseconds
}

// NewFileWatcher creates a new file watcher with the provided configuration
func NewFileWatcher(config *WatchConfig, logger *logging.Logger) (*FileWatcher, error) {
	if config == nil {
		config = DefaultWatchConfig()
	}

	if logger == nil {
		logger = logging.NewDefaultLogger()
	}

	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		return nil, fmt.Errorf("failed to create fsnotify watcher: %w", err)
	}

	ctx, cancel := context.WithCancel(context.Background())

	fw := &FileWatcher{
		watcher:        watcher,
		config:         config,
		logger:         logger,
		changesChan:    make(chan []string, 10),
		ctx:            ctx,
		cancel:         cancel,
		running:        false,
		watchMatcher:   NewPatternMatcher(config.Patterns),
		excludeMatcher: NewPatternMatcher(config.Excludes),
	}

	return fw, nil
}

// DefaultWatchConfig returns default configuration for file watching
func DefaultWatchConfig() *WatchConfig {
	return &WatchConfig{
		RootDir:    ".",
		Patterns:   DefaultWatchPatterns,
		Excludes:   DefaultExcludePatterns,
		DebounceMs: 500,
	}
}

// Start begins file watching in a goroutine
func (fw *FileWatcher) Start() error {
	fw.mu.Lock()
	defer fw.mu.Unlock()

	if fw.running {
		return fmt.Errorf("file watcher is already running")
	}

	correlationID := logging.NewCorrelationID()
	ctx := logging.WithCorrelationID(fw.ctx, correlationID)
	logger := logging.LogWithContext(ctx, fw.logger.Logger)

	logger.Info("Starting file watcher",
		"component", "devtools.watcher",
		"root_dir", fw.config.RootDir,
		"patterns", fw.config.Patterns,
		"excludes", fw.config.Excludes,
		"debounce_ms", fw.config.DebounceMs,
	)

	// Add root directory and subdirectories to watcher
	err := fw.addDirectoriesToWatcher(fw.config.RootDir)
	if err != nil {
		logger.Error("Failed to add directories to watcher",
			"component", "devtools.watcher",
			"error", err,
		)
		return fmt.Errorf("failed to add directories: %w", err)
	}

	fw.running = true

	// Start watching goroutine
	go fw.watchLoop(ctx)

	logger.Info("File watcher started successfully",
		"component", "devtools.watcher",
	)

	return nil
}

// Stop gracefully stops the file watcher
func (fw *FileWatcher) Stop() error {
	fw.mu.Lock()
	defer fw.mu.Unlock()

	if !fw.running {
		return nil
	}

	correlationID := logging.NewCorrelationID()
	ctx := logging.WithCorrelationID(context.Background(), correlationID)
	logger := logging.LogWithContext(ctx, fw.logger.Logger)

	logger.Info("Stopping file watcher",
		"component", "devtools.watcher",
	)

	fw.cancel()
	fw.running = false

	err := fw.watcher.Close()
	if err != nil {
		logger.Error("Error closing file watcher",
			"component", "devtools.watcher",
			"error", err,
		)
		return err
	}

	close(fw.changesChan)

	logger.Info("File watcher stopped successfully",
		"component", "devtools.watcher",
	)

	return nil
}

// Changes returns a channel that receives batched file changes
func (fw *FileWatcher) Changes() <-chan []string {
	return fw.changesChan
}

// IsRunning returns whether the watcher is currently running
func (fw *FileWatcher) IsRunning() bool {
	fw.mu.RLock()
	defer fw.mu.RUnlock()
	return fw.running
}

// addDirectoriesToWatcher recursively adds directories to the file watcher
func (fw *FileWatcher) addDirectoriesToWatcher(rootDir string) error {
	return filepath.Walk(rootDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() {
			// Skip excluded directories
			if fw.excludeMatcher.Matches(path) || !ShouldWatchDirectory(path) {
				return filepath.SkipDir
			}

			err := fw.watcher.Add(path)
			if err != nil {
				return fmt.Errorf("failed to add directory %s to watcher: %w", path, err)
			}
		}

		return nil
	})
}

// watchLoop is the main event processing loop
func (fw *FileWatcher) watchLoop(ctx context.Context) {
	logger := logging.LogWithContext(ctx, fw.logger.Logger)

	rawChanges := make(chan string, 100)
	debouncedChanges := fw.debounce(rawChanges)

	for {
		select {
		case event, ok := <-fw.watcher.Events:
			if !ok {
				return
			}

			fw.handleFileEvent(ctx, event, rawChanges)

		case err, ok := <-fw.watcher.Errors:
			if !ok {
				return
			}

			logger.Error("File watcher error",
				"component", "devtools.watcher",
				"error", err,
			)

		case changes := <-debouncedChanges:
			if len(changes) > 0 {
				logger.Info("Batched file changes detected",
					"component", "devtools.watcher",
					"file_count", len(changes),
					"files", changes,
					"trigger", "auto_reload",
				)

				select {
				case fw.changesChan <- changes:
				case <-ctx.Done():
					return
				}
			}

		case <-ctx.Done():
			return
		}
	}
}

// handleFileEvent processes individual file system events
func (fw *FileWatcher) handleFileEvent(ctx context.Context, event fsnotify.Event, changes chan<- string) {
	logger := logging.LogWithContext(ctx, fw.logger.Logger)

	// Skip if file should be excluded
	if fw.excludeMatcher.Matches(event.Name) || IsTemporaryFile(event.Name) {
		return
	}

	// Skip if file doesn't match watched patterns
	if !fw.watchMatcher.Matches(event.Name) {
		// Additional check for specific file types
		if !IsGoSourceFile(event.Name) && !IsGoModFile(event.Name) {
			return
		}
	}

	logger.Debug("File change detected",
		"component", "devtools.watcher",
		"file", event.Name,
		"operation", event.Op.String(),
		"timestamp", time.Now().Unix(),
	)

	select {
	case changes <- event.Name:
	case <-ctx.Done():
		return
	}
}

// debounce implements timer-based batching to prevent excessive triggers
func (fw *FileWatcher) debounce(changes <-chan string) <-chan []string {
	debounced := make(chan []string)

	go func() {
		defer close(debounced)

		var timer *time.Timer
		var batch []string
		seen := make(map[string]bool)

		for {
			select {
			case change, ok := <-changes:
				if !ok {
					// Send final batch if exists
					if len(batch) > 0 {
						debounced <- batch
					}
					return
				}

				// Deduplicate changes
				if !seen[change] {
					batch = append(batch, change)
					seen[change] = true
				}

				// Reset timer
				if timer != nil {
					timer.Stop()
				}

				timer = time.AfterFunc(time.Duration(fw.config.DebounceMs)*time.Millisecond, func() {
					if len(batch) > 0 {
						debounced <- batch
						batch = nil
						seen = make(map[string]bool)
					}
				})

			case <-fw.ctx.Done():
				return
			}
		}
	}()

	return debounced
}
