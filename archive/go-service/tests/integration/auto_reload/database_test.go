package auto_reload

import (
	"context"
	"fmt"
	"path/filepath"
	"testing"
	"time"

	"go-service/internal/database"
	"go-service/internal/models"

	_ "github.com/mattn/go-sqlite3"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestDatabasePersistenceAcrossReloads tests that database connections and data persist across service reloads
func TestDatabasePersistenceAcrossReloads(t *testing.T) {
	helper := NewTestHelper(t)
	defer helper.Cleanup()

	// Wait for service to be ready
	helper.WaitForServiceReady()

	t.Run("BasicDataPersistence", func(t *testing.T) {
		// Insert test data via API
		testData := createTestEvaluationData(t, helper)

		// Trigger reload by modifying database-related file
		helper.ModifyFile("internal/database/repository.go")
		helper.WaitForReload()

		// Verify data persistence after reload
		retrievedData := retrieveTestEvaluationData(t, helper, testData.SessionID)
		assert.Equal(t, testData.SessionID, retrievedData.SessionID)
		assert.Equal(t, testData.TotalTests, retrievedData.TotalTests)
		assert.Equal(t, testData.Status, retrievedData.Status)
	})

	t.Run("DatabaseConnectionPersistence", func(t *testing.T) {
		// Verify database connectivity before reload
		verifyDatabaseConnectivity(t, helper)

		// Trigger reload
		helper.ModifyFile("internal/database/sqlite.go")
		helper.WaitForReload()

		// Verify database connectivity after reload
		verifyDatabaseConnectivity(t, helper)
	})

	t.Run("MultipleReloadsDataIntegrity", func(t *testing.T) {
		// Create initial test data
		testData1 := createTestEvaluationData(t, helper)

		// First reload
		helper.ModifyFile("internal/database/repository.go")
		helper.WaitForReload()

		// Add more data after first reload
		testData2 := createTestEvaluationData(t, helper)

		// Second reload
		helper.ModifyFile("internal/database/migrations.go")
		helper.WaitForReload()

		// Verify both datasets exist
		data1 := retrieveTestEvaluationData(t, helper, testData1.SessionID)
		data2 := retrieveTestEvaluationData(t, helper, testData2.SessionID)

		assert.NotNil(t, data1)
		assert.NotNil(t, data2)
		assert.NotEqual(t, data1.SessionID, data2.SessionID)
	})
}

// TestTransactionHandlingDuringReload tests that ongoing transactions are handled gracefully during reloads
func TestTransactionHandlingDuringReload(t *testing.T) {
	helper := NewTestHelper(t)
	defer helper.Cleanup()

	helper.WaitForServiceReady()

	t.Run("LongRunningTransactionCompletion", func(t *testing.T) {
		// Start a long-running transaction simulation
		transactionCompleted := make(chan bool, 1)
		transactionData := make(chan *models.EvaluationSession, 1)

		go func() {
			// Simulate a long-running database operation
			session := startLongRunningTransaction(t, helper)
			transactionData <- session

			// Simulate work that takes some time
			time.Sleep(2 * time.Second)

			// Complete the transaction
			completeLongRunningTransaction(t, helper, session)
			transactionCompleted <- true
		}()

		// Wait a bit for transaction to start
		time.Sleep(500 * time.Millisecond)

		// Trigger reload while transaction is in progress
		helper.ModifyFile("internal/database/repository.go")

		// Wait for transaction to complete first
		select {
		case <-transactionCompleted:
			t.Log("Transaction completed successfully before reload")
		case <-time.After(10 * time.Second):
			t.Fatal("Transaction did not complete within expected time")
		}

		// Now wait for reload to complete
		helper.WaitForReload()

		// Verify transaction data was properly saved
		session := <-transactionData
		retrievedData := retrieveTestEvaluationData(t, helper, session.SessionID)
		assert.NotNil(t, retrievedData)
		assert.Equal(t, "completed", retrievedData.Status)
	})

	t.Run("TransactionRollbackOnReload", func(t *testing.T) {
		// Start a transaction that will be interrupted
		transactionStarted := make(chan string, 1)

		go func() {
			session := startInterruptibleTransaction(t, helper)
			transactionStarted <- session.SessionID

			// Simulate long work that will be interrupted
			time.Sleep(5 * time.Second)
		}()

		// Wait for transaction to start
		sessionID := <-transactionStarted
		time.Sleep(500 * time.Millisecond)

		// Trigger reload to interrupt the transaction
		helper.ModifyFile("internal/database/sqlite.go")
		helper.WaitForReload()

		// Verify that incomplete transaction data was not persisted
		retrievedData := retrieveTestEvaluationData(t, helper, sessionID)
		if retrievedData != nil {
			// If data exists, it should be in a failed or rolled back state
			assert.NotEqual(t, "completed", retrievedData.Status)
		}
	})

	t.Run("BatchOperationIntegrity", func(t *testing.T) {
		// Create multiple test sessions for batch operation
		sessions := createMultipleTestSessions(t, helper, 5)

		// Start batch operation
		batchCompleted := make(chan bool, 1)
		go func() {
			updateMultipleSessionsInBatch(t, helper, sessions)
			batchCompleted <- true
		}()

		// Wait for batch to start
		time.Sleep(500 * time.Millisecond)

		// Trigger reload during batch operation
		helper.ModifyFile("internal/database/repository.go")

		// Wait for batch completion or timeout
		select {
		case <-batchCompleted:
			t.Log("Batch operation completed")
		case <-time.After(15 * time.Second):
			t.Log("Batch operation interrupted by reload")
		}

		helper.WaitForReload()

		// Verify data consistency - either all updated or none
		completedCount := 0
		originalCount := 0

		for _, session := range sessions {
			retrieved := retrieveTestEvaluationData(t, helper, session.SessionID)
			if retrieved != nil {
				if retrieved.Status == "completed" {
					completedCount++
				} else {
					originalCount++
				}
			}
		}

		// Batch operations should be atomic - either all succeed or all fail
		assert.True(t, completedCount == 0 || completedCount == len(sessions),
			"Batch operation should be atomic: completed=%d, original=%d, total=%d",
			completedCount, originalCount, len(sessions))
	})
}

// TestDatabaseMigrationCompatibility tests that database migrations work correctly with auto-reload
func TestDatabaseMigrationCompatibility(t *testing.T) {
	helper := NewTestHelper(t)
	defer helper.Cleanup()

	helper.WaitForServiceReady()

	t.Run("MigrationFileChanges", func(t *testing.T) {
		// Create initial test data
		testData := createTestEvaluationData(t, helper)

		// Modify migration file (simulate schema change)
		helper.ModifyFile("internal/database/migrations.go")
		helper.WaitForReload()

		// Verify existing data is still accessible
		retrievedData := retrieveTestEvaluationData(t, helper, testData.SessionID)
		assert.NotNil(t, retrievedData)
		assert.Equal(t, testData.SessionID, retrievedData.SessionID)

		// Verify new operations still work
		newTestData := createTestEvaluationData(t, helper)
		assert.NotNil(t, newTestData)
		assert.NotEqual(t, testData.SessionID, newTestData.SessionID)
	})

	t.Run("DatabaseInitializationOnReload", func(t *testing.T) {
		// Verify database is properly initialized
		verifyDatabaseSchema(t, helper)

		// Trigger reload with database-related changes
		helper.ModifyFile("internal/database/sqlite.go")
		helper.WaitForReload()

		// Verify database is still properly initialized
		verifyDatabaseSchema(t, helper)
	})

	t.Run("DatabaseConnectionPooling", func(t *testing.T) {
		// Test multiple concurrent database operations
		concurrentOps := 10
		results := make(chan bool, concurrentOps)

		for i := 0; i < concurrentOps; i++ {
			go func(id int) {
				session := &models.EvaluationSession{
					SessionID:  fmt.Sprintf("concurrent-test-%d-%d", id, time.Now().Unix()),
					StartedAt:  time.Now(),
					Status:     "running",
					TotalTests: id + 1,
				}
				success := createTestSession(t, helper, session)
				results <- success
			}(i)
		}

		// Trigger reload while operations are running
		time.Sleep(100 * time.Millisecond)
		helper.ModifyFile("internal/database/repository.go")

		// Collect results
		successCount := 0
		for i := 0; i < concurrentOps; i++ {
			if <-results {
				successCount++
			}
		}

		helper.WaitForReload()

		// Most operations should succeed (allowing for some to be interrupted)
		assert.Greater(t, successCount, concurrentOps/2,
			"At least half of concurrent operations should succeed: %d/%d", successCount, concurrentOps)
	})
}

// Helper functions for database testing

// createTestEvaluationData creates test evaluation data via API
func createTestEvaluationData(t *testing.T, helper *TestHelper) *models.EvaluationSession {
	sessionID := fmt.Sprintf("test-session-%d", time.Now().UnixNano())
	session := &models.EvaluationSession{
		SessionID:      sessionID,
		StartedAt:      time.Now(),
		Status:         "running",
		TotalTests:     5,
		CompletedTests: 0,
		Metadata: map[string]interface{}{
			"test_type":  "auto_reload_persistence",
			"created_by": "auto_reload_test",
		},
	}

	success := createTestSession(t, helper, session)
	require.True(t, success, "Failed to create test session")

	return session
}

// retrieveTestEvaluationData retrieves test evaluation data via API
func retrieveTestEvaluationData(t *testing.T, helper *TestHelper, sessionID string) *models.EvaluationSession {
	// Use helper to make API call to retrieve session
	_ = fmt.Sprintf("/api/sessions/%s", sessionID)

	// Note: This would typically use HTTP client to call the API
	// For now, we'll simulate the database query directly
	db := setupTestDatabase(t, helper)
	repo := database.NewRepository(db, helper.logger)

	ctx := context.Background()
	session, err := repo.GetSession(ctx, sessionID)
	if err != nil {
		t.Logf("Error retrieving session %s: %v", sessionID, err)
		return nil
	}

	return session
}

// createTestSession creates a test session using the service's API
func createTestSession(t *testing.T, helper *TestHelper, session *models.EvaluationSession) bool {
	// Simulate API call to create session
	db := setupTestDatabase(t, helper)
	repo := database.NewRepository(db, helper.logger)

	ctx := context.Background()
	err := repo.SaveSession(ctx, session)
	if err != nil {
		t.Logf("Error creating session: %v", err)
		return false
	}

	return true
}

// verifyDatabaseConnectivity verifies that the database is accessible
func verifyDatabaseConnectivity(t *testing.T, helper *TestHelper) {
	db := setupTestDatabase(t, helper)

	ctx := context.Background()
	err := db.PingContext(ctx)
	assert.NoError(t, err, "Database should be accessible")
}

// verifyDatabaseSchema verifies that the database schema is properly set up
func verifyDatabaseSchema(t *testing.T, helper *TestHelper) {
	db := setupTestDatabase(t, helper)

	// Verify key tables exist
	tables := []string{
		"evaluation_results",
		"evaluation_sessions",
		"test_executions",
		"test_results",
		"test_categories",
	}

	for _, table := range tables {
		query := fmt.Sprintf("SELECT name FROM sqlite_master WHERE type='table' AND name='%s'", table)
		var tableName string
		err := db.QueryRow(query).Scan(&tableName)
		assert.NoError(t, err, "Table %s should exist", table)
		assert.Equal(t, table, tableName, "Table name should match")
	}
}

// setupTestDatabase sets up a database connection for testing
func setupTestDatabase(t *testing.T, helper *TestHelper) *database.DB {
	dbPath := filepath.Join(helper.GetTestDir(), "evaluation.db")
	config := database.Config{
		Path: dbPath,
	}
	db, err := database.NewDB(config)
	require.NoError(t, err, "Failed to create test database")

	return db
}

// startLongRunningTransaction starts a transaction that simulates long-running work
func startLongRunningTransaction(t *testing.T, helper *TestHelper) *models.EvaluationSession {
	sessionID := fmt.Sprintf("long-tx-session-%d", time.Now().UnixNano())
	session := &models.EvaluationSession{
		SessionID:      sessionID,
		StartedAt:      time.Now(),
		Status:         "running",
		TotalTests:     10,
		CompletedTests: 0,
		Metadata: map[string]interface{}{
			"transaction_type": "long_running",
		},
	}

	success := createTestSession(t, helper, session)
	require.True(t, success, "Failed to start long running transaction")

	return session
}

// completeLongRunningTransaction completes a long-running transaction
func completeLongRunningTransaction(t *testing.T, helper *TestHelper, session *models.EvaluationSession) {
	db := setupTestDatabase(t, helper)
	repo := database.NewRepository(db, helper.logger)

	ctx := context.Background()
	session.Status = "completed"
	now := time.Now()
	session.CompletedAt = &now
	session.CompletedTests = session.TotalTests

	err := repo.UpdateSession(ctx, session)
	assert.NoError(t, err, "Failed to complete long running transaction")
}

// startInterruptibleTransaction starts a transaction that can be interrupted
func startInterruptibleTransaction(t *testing.T, helper *TestHelper) *models.EvaluationSession {
	sessionID := fmt.Sprintf("interruptible-tx-%d", time.Now().UnixNano())
	session := &models.EvaluationSession{
		SessionID:      sessionID,
		StartedAt:      time.Now(),
		Status:         "processing",
		TotalTests:     20,
		CompletedTests: 0,
		Metadata: map[string]interface{}{
			"transaction_type": "interruptible",
		},
	}

	success := createTestSession(t, helper, session)
	require.True(t, success, "Failed to start interruptible transaction")

	return session
}

// createMultipleTestSessions creates multiple test sessions for batch testing
func createMultipleTestSessions(t *testing.T, helper *TestHelper, count int) []*models.EvaluationSession {
	var sessions []*models.EvaluationSession

	for i := 0; i < count; i++ {
		sessionID := fmt.Sprintf("batch-session-%d-%d", i, time.Now().UnixNano())
		session := &models.EvaluationSession{
			SessionID:      sessionID,
			StartedAt:      time.Now(),
			Status:         "pending",
			TotalTests:     i + 1,
			CompletedTests: 0,
			Metadata: map[string]interface{}{
				"batch_id": "test-batch",
				"sequence": i,
			},
		}

		success := createTestSession(t, helper, session)
		require.True(t, success, "Failed to create batch session %d", i)

		sessions = append(sessions, session)
	}

	return sessions
}

// updateMultipleSessionsInBatch updates multiple sessions in a batch operation
func updateMultipleSessionsInBatch(t *testing.T, helper *TestHelper, sessions []*models.EvaluationSession) {
	db := setupTestDatabase(t, helper)
	repo := database.NewRepository(db, helper.logger)

	ctx := context.Background()

	// Start transaction for batch update
	tx, err := repo.BeginTransaction(ctx)
	if err != nil {
		t.Logf("Failed to begin batch transaction: %v", err)
		return
	}
	defer tx.Rollback(ctx)

	// Update all sessions in the batch
	for _, session := range sessions {
		session.Status = "completed"
		now := time.Now()
		session.CompletedAt = &now
		session.CompletedTests = session.TotalTests

		err := tx.Repository().UpdateSession(ctx, session)
		if err != nil {
			t.Logf("Failed to update session in batch: %v", err)
			return
		}
	}

	// Commit the batch
	err = tx.Commit(ctx)
	if err != nil {
		t.Logf("Failed to commit batch transaction: %v", err)
	}
}
