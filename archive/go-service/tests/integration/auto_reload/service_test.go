package auto_reload

import (
	"fmt"
	"strings"
	"testing"
	"time"
)

// TestAutoReloadServiceLifecycle tests the complete service lifecycle with auto-reload
func TestAutoReloadServiceLifecycle(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	// Setup test helper
	helper := NewTestHelper(t)
	defer helper.Cleanup()

	// Wait for initial service startup
	helper.WaitForServiceReady()

	t.Run("BasicFileChangeTriggersReload", func(t *testing.T) {
		// Make a change to trigger reload
		helper.ModifyFile("internal/api/handlers.go")

		// Wait for reload to complete
		helper.WaitForReload()

		// Verify service is responsive
		helper.VerifyServiceResponsive()
	})

	t.Run("GoModChangeTriggersReload", func(t *testing.T) {
		// Make a change to go.mod
		helper.ModifyFile("go.mod")

		// Wait for reload to complete
		helper.WaitForReload()

		// Verify service is responsive
		helper.VerifyServiceResponsive()
	})

	t.Run("MultipleRapidChangesDebouncing", func(t *testing.T) {
		// Make multiple rapid changes
		helper.MakeMultipleChanges()

		// Wait for reload(s) to complete - should be debounced to single reload
		time.Sleep(2 * time.Second) // Allow debouncing window
		helper.WaitForReload()

		// Verify service is responsive
		helper.VerifyServiceResponsive()
	})

	t.Run("ServiceEndpointsWorkAfterReload", func(t *testing.T) {
		// Trigger a reload
		helper.ModifyFile("internal/api/handlers.go")
		helper.WaitForReload()

		// Test all major endpoints
		endpoints := []string{
			"/health",
			"/api/version",
			"/api/status",
			"/api/tags",
		}

		for _, endpoint := range endpoints {
			t.Run(fmt.Sprintf("Endpoint_%s", strings.ReplaceAll(endpoint, "/", "_")), func(t *testing.T) {
				helper.TestEndpoint(endpoint)
			})
		}
	})
}

// TestAutoReloadErrorHandling tests how the reloader handles build and startup errors
func TestAutoReloadErrorHandling(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test in short mode")
	}

	// Setup test helper
	helper := NewTestHelper(t)
	defer helper.Cleanup()

	// Wait for initial service startup
	helper.WaitForServiceReady()

	t.Run("BuildErrorRecovery", func(t *testing.T) {
		// Introduce a build error
		helper.IntroduceBuildError("internal/api/handlers.go")

		// Wait briefly to ensure the error is processed
		time.Sleep(2 * time.Second)

		// Service should still be running from previous successful build
		helper.VerifyServiceResponsive()

		// Fix the build error
		helper.FixBuildError("internal/api/handlers.go")

		// Wait for successful reload
		helper.WaitForReload()

		// Verify service is still responsive
		helper.VerifyServiceResponsive()
	})
}
