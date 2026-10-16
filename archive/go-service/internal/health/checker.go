package health

import (
	"runtime"
	"time"

	"go-service/internal/models"
)

var startTime = time.Now()

// GetHealth returns the current health status
func GetHealth() models.HealthResponse {
	return models.HealthResponse{
		Status:    "healthy",
		Timestamp: time.Now(),
		Uptime:    time.Since(startTime).String(),
	}
}

// GetVersion returns version information
func GetVersion() models.VersionResponse {
	return models.VersionResponse{
		Version:   "1.0.0",
		BuildTime: "development",
		GoVersion: runtime.Version(),
	}
}

// GetStatus returns detailed service status
func GetStatus() models.StatusResponse {
	var memStats runtime.MemStats
	runtime.ReadMemStats(&memStats)

	return models.StatusResponse{
		Service:   "llm-eval-go-service",
		Status:    "running",
		Version:   "1.0.0",
		Timestamp: time.Now(),
		Uptime:    time.Since(startTime).String(),
		Memory:    formatBytes(memStats.Alloc),
	}
}

func formatBytes(bytes uint64) string {
	const unit = 1024
	if bytes < unit {
		return "< 1KB"
	}

	units := []string{"KB", "MB", "GB", "TB"}
	div := uint64(unit)
	exp := 0

	for n := bytes / unit; n >= unit && exp < len(units)-1; n /= unit {
		div *= unit
		exp++
	}

	value := float64(bytes) / float64(div)
	if value < 10 {
		return "~" + string(rune('0'+int(value))) + units[exp]
	}
	return "~" + string(rune('0'+int(value/10))) + string(rune('0'+int(value)%10)) + units[exp]
}
