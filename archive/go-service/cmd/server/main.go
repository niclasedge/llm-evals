package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go-service/internal/api"
	"go-service/internal/database"
	"go-service/internal/logging"
	"go-service/internal/monitoring"
)

func main() {
	// Create context with correlation ID for application startup
	ctx := context.Background()
	ctx = logging.WithCorrelationID(ctx, logging.NewCorrelationID())

	// Initialize logging first
	logConfig := getLoggingConfig()
	logger, err := logging.NewLogger(logConfig)
	if err != nil {
		// If we can't create logger, we have to use standard log as last resort
		// In production, this would be a critical system failure
		os.Stderr.WriteString("CRITICAL: Failed to initialize logger: " + err.Error() + "\n")
		os.Exit(1)
	}
	defer logger.Close()

	// Use context-aware logging from this point forward
	contextLogger := logging.LogWithContext(ctx, logger.Logger)
	contextLogger.Info("Logger initialized successfully",
		"component", "server.main",
		"log_file", logConfig.LogFile,
		"dev_mode", logConfig.DevMode)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	contextLogger.Info("Starting server initialization",
		"component", "server.main",
		"port", port)

	// Initialize database
	db, err := database.NewDBFromEnv()
	if err != nil {
		contextLogger.Error("Database initialization failed",
			"component", "server.main",
			"error", err.Error())
		os.Exit(1)
	}
	defer db.Close()

	contextLogger.Info("Database initialized successfully",
		"component", "server.main")

	// Initialize monitoring
	metricsCollector := monitoring.NewMetricsCollector()
	analyticsService := monitoring.NewAnalyticsService(db.DB, metricsCollector)

	contextLogger.Info("Monitoring system initialized",
		"component", "server.main")

	// Create router with database and monitoring
	router := api.NewRouterWithDatabase(db, logger)

	// Add monitoring handlers
	metricsHandler := api.NewMetricsHandler(metricsCollector, analyticsService)
	dashboardHandler := api.NewDashboardHandler(metricsCollector, analyticsService)

	// Register monitoring routes
	metricsHandler.RegisterMetricsRoutes(router)
	dashboardHandler.RegisterDashboardRoutes(router)

	// Add Prometheus metrics endpoint
	router.Handle("/metrics", promhttp.Handler())

	// Add metrics middleware to all routes
	router.Use(metricsHandler.MetricsMiddleware)

	// Create HTTP server with graceful shutdown support
	server := &http.Server{
		Addr:    ":" + port,
		Handler: router,
	}

	// Setup graceful shutdown
	serverCtx, serverCancel := context.WithCancel(ctx)
	defer serverCancel()

	// Handle shutdown signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-sigChan
		contextLogger.Info("Shutdown signal received",
			"component", "server.main",
			"signal", sig.String())

		// Graceful shutdown with timeout
		shutdownCtx, shutdownCancel := context.WithTimeout(ctx, 10*time.Second)
		defer shutdownCancel()

		if err := server.Shutdown(shutdownCtx); err != nil {
			contextLogger.Error("Server shutdown error",
				"component", "server.main",
				"error", err.Error())
		}
		serverCancel()
	}()

	contextLogger.Info("Go service with monitoring starting",
		"component", "server.main",
		"port", port,
		"dashboard_url", "http://localhost:"+port+"/dashboard",
		"metrics_url", "http://localhost:"+port+"/metrics")

	// Start server
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		contextLogger.Error("Server error",
			"component", "server.main",
			"error", err.Error(),
			"port", port)
		os.Exit(1)
	}

	// Wait for graceful shutdown
	<-serverCtx.Done()
	contextLogger.Info("Server stopped gracefully",
		"component", "server.main")
}

// getLoggingConfig reads logging configuration from environment variables
func getLoggingConfig() logging.Config {
	config := logging.Config{
		LogLevel:       getEnvString("LOG_LEVEL", "info"),
		DevMode:        getEnvBool("DEV_MODE", false),
		LogFile:        getEnvString("LOG_FILE", "logs/go-service.log"),
		LogRotateSize:  getEnvInt("LOG_ROTATE_SIZE", 100),
		LogRotateCount: getEnvInt("LOG_ROTATE_COUNT", 10),
		LogRotateAge:   getEnvInt("LOG_ROTATE_AGE", 1),
	}
	return config
}

// getEnvString gets string from environment with default value
func getEnvString(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// getEnvBool gets boolean from environment with default value
func getEnvBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if parsed, err := strconv.ParseBool(value); err == nil {
			return parsed
		}
	}
	return defaultValue
}

// getEnvInt gets integer from environment with default value
func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if parsed, err := strconv.Atoi(value); err == nil {
			return parsed
		}
	}
	return defaultValue
}
