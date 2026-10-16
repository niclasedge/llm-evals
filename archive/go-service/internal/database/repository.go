package database

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	"go-service/internal/database/validation"
	"go-service/internal/logging"
	"go-service/internal/models"
)

// Error definitions
var (
	ErrTestExecutionNotFound = errors.New("test execution not found")
	ErrTestResultNotFound    = errors.New("test result not found")
	ErrTestCategoryNotFound  = errors.New("test category not found")
)

// DBInterface defines the database operations interface
type DBInterface interface {
	Exec(query string, args ...interface{}) (sql.Result, error)
	Query(query string, args ...interface{}) (*sql.Rows, error)
	QueryRow(query string, args ...interface{}) *sql.Row
	Begin() (*sql.Tx, error)
	BeginTx(ctx context.Context, opts *sql.TxOptions) (*sql.Tx, error)
}

// Repository provides database operations for evaluation results
type Repository struct {
	db     DBInterface
	logger *logging.Logger
}

// NewRepository creates a new repository instance
func NewRepository(db *DB, logger *logging.Logger) *Repository {
	return &Repository{
		db:     db,
		logger: logger,
	}
}

// newRepositoryWithInterface creates a new repository instance with a DBInterface
func newRepositoryWithInterface(db DBInterface, logger *logging.Logger) *Repository {
	return &Repository{
		db:     db,
		logger: logger,
	}
}

// SaveResult saves an evaluation result to the database
func (r *Repository) SaveResult(ctx context.Context, result *models.EvaluationResult) error {
	contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
	contextLogger.Debug("Saving evaluation result to database",
		"test_name", result.TestName,
		"model", result.ModelName,
	)

	if err := result.PrepareForDB(); err != nil {
		contextLogger.Error("Failed to prepare result for database", "error", err)
		return fmt.Errorf("failed to prepare result for database: %w", err)
	}

	query := `
		INSERT INTO evaluation_results (
			timestamp, model_provider, model_name, test_name, test_type, query, response,
			expected_response, metrics, score, passed, execution_time, error_message, metadata
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`

	// Set timestamp if not already set
	if result.Timestamp == nil {
		now := time.Now()
		result.Timestamp = &now
	}

	res, err := r.db.Exec(query,
		result.Timestamp.Format(time.RFC3339),
		result.ModelProvider,
		result.ModelName,
		result.TestName,
		result.TestType,
		result.Query,
		result.Response,
		result.ExpectedResponse,
		result.MetricsJSON,
		result.Score,
		result.Passed,
		result.ExecutionTime,
		result.ErrorMessage,
		result.MetadataJSON,
	)

	if err != nil {
		contextLogger.Error("Failed to save result to database", "error", err)
		return fmt.Errorf("failed to save result: %w", err)
	}

	id, err := res.LastInsertId()
	if err != nil {
		contextLogger.Error("Failed to get last insert ID", "error", err)
		return fmt.Errorf("failed to get last insert ID: %w", err)
	}

	idInt := int(id)
	result.ID = &idInt
	contextLogger.Debug("Successfully saved evaluation result", "id", idInt)
	return nil
}

// SaveResultsBatch saves multiple evaluation results in a transaction
func (r *Repository) SaveResultsBatch(ctx context.Context, results []*models.EvaluationResult) error {
	contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
	contextLogger.Debug("Saving batch of evaluation results", "count", len(results))
	tx, err := r.db.Begin()
	if err != nil {
		contextLogger.Error("Failed to begin transaction", "error", err)
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()

	query := `
		INSERT INTO evaluation_results (
			timestamp, model_provider, model_name, test_name, test_type, query, response,
			expected_response, metrics, score, passed, execution_time, error_message, metadata
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`

	stmt, err := tx.Prepare(query)
	if err != nil {
		return fmt.Errorf("failed to prepare statement: %w", err)
	}
	defer stmt.Close()

	for _, result := range results {
		if err := result.PrepareForDB(); err != nil {
			return fmt.Errorf("failed to prepare result for database: %w", err)
		}

		// Set timestamp if not already set
		if result.Timestamp == nil {
			now := time.Now()
			result.Timestamp = &now
		}

		res, err := stmt.Exec(
			result.Timestamp.Format(time.RFC3339),
			result.ModelProvider,
			result.ModelName,
			result.TestName,
			result.TestType,
			result.Query,
			result.Response,
			result.ExpectedResponse,
			result.MetricsJSON,
			result.Score,
			result.Passed,
			result.ExecutionTime,
			result.ErrorMessage,
			result.MetadataJSON,
		)

		if err != nil {
			return fmt.Errorf("failed to execute statement: %w", err)
		}

		id, err := res.LastInsertId()
		if err != nil {
			return fmt.Errorf("failed to get last insert ID: %w", err)
		}

		idInt := int(id)
		result.ID = &idInt
	}

	if err := tx.Commit(); err != nil {
		contextLogger.Error("Failed to commit transaction", "error", err)
		return err
	}

	contextLogger.Debug("Successfully saved batch of evaluation results", "count", len(results))
	return nil
}

// GetResult retrieves an evaluation result by ID
func (r *Repository) GetResult(ctx context.Context, id int) (*models.EvaluationResult, error) {
	contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
	contextLogger.Debug("Retrieving evaluation result", "id", id)
	query := `
		SELECT id, timestamp, model_provider, model_name, test_name, test_type, query, response,
		       expected_response, metrics, score, passed, execution_time, error_message, metadata
		FROM evaluation_results WHERE id = ?
	`

	result := &models.EvaluationResult{}
	err := r.db.QueryRow(query, id).Scan(
		&result.ID,
		&result.Timestamp,
		&result.ModelProvider,
		&result.ModelName,
		&result.TestName,
		&result.TestType,
		&result.Query,
		&result.Response,
		&result.ExpectedResponse,
		&result.MetricsJSON,
		&result.Score,
		&result.Passed,
		&result.ExecutionTime,
		&result.ErrorMessage,
		&result.MetadataJSON,
	)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get result: %w", err)
	}

	if err := result.LoadFromDB(); err != nil {
		return nil, fmt.Errorf("failed to load result from database: %w", err)
	}

	return result, nil
}

// GetResultsFilter represents filter options for querying results
type GetResultsFilter struct {
	ModelProvider *string
	ModelName     *string
	TestType      *string
	StartTime     *time.Time
	EndTime       *time.Time
	Limit         int
	Offset        int
}

// GetResults retrieves evaluation results with optional filtering
func (r *Repository) GetResults(ctx context.Context, filter GetResultsFilter) ([]*models.EvaluationResult, error) {
	contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
	contextLogger.Debug("Retrieving evaluation results", "filter", filter)
	query := `
		SELECT id, timestamp, model_provider, model_name, test_name, test_type, query, response,
		       expected_response, metrics, score, passed, execution_time, error_message, metadata
		FROM evaluation_results WHERE 1=1
	`

	var args []interface{}
	var conditions []string

	if filter.ModelProvider != nil {
		conditions = append(conditions, "model_provider = ?")
		args = append(args, *filter.ModelProvider)
	}

	if filter.ModelName != nil {
		conditions = append(conditions, "model_name = ?")
		args = append(args, *filter.ModelName)
	}

	if filter.TestType != nil {
		conditions = append(conditions, "test_type = ?")
		args = append(args, *filter.TestType)
	}

	if filter.StartTime != nil {
		conditions = append(conditions, "timestamp >= ?")
		args = append(args, filter.StartTime.Format(time.RFC3339))
	}

	if filter.EndTime != nil {
		conditions = append(conditions, "timestamp <= ?")
		args = append(args, filter.EndTime.Format(time.RFC3339))
	}

	if len(conditions) > 0 {
		query += " AND " + strings.Join(conditions, " AND ")
	}

	query += " ORDER BY timestamp DESC"

	if filter.Limit > 0 {
		query += fmt.Sprintf(" LIMIT %d", filter.Limit)
	}

	if filter.Offset > 0 {
		query += fmt.Sprintf(" OFFSET %d", filter.Offset)
	}

	rows, err := r.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query results: %w", err)
	}
	defer rows.Close()

	var results []*models.EvaluationResult
	for rows.Next() {
		result := &models.EvaluationResult{}
		err := rows.Scan(
			&result.ID,
			&result.Timestamp,
			&result.ModelProvider,
			&result.ModelName,
			&result.TestName,
			&result.TestType,
			&result.Query,
			&result.Response,
			&result.ExpectedResponse,
			&result.MetricsJSON,
			&result.Score,
			&result.Passed,
			&result.ExecutionTime,
			&result.ErrorMessage,
			&result.MetadataJSON,
		)

		if err != nil {
			return nil, fmt.Errorf("failed to scan result: %w", err)
		}

		if err := result.LoadFromDB(); err != nil {
			return nil, fmt.Errorf("failed to load result from database: %w", err)
		}

		results = append(results, result)
	}

	return results, rows.Err()
}

// GetSummary calculates evaluation summary statistics
func (r *Repository) GetSummary(ctx context.Context, filter GetResultsFilter) (*models.EvaluationSummary, error) {
	contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
	contextLogger.Debug("Calculating evaluation summary statistics")
	query := `
		SELECT 
			COUNT(*) as total_evaluations,
			SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passed_evaluations,
			SUM(CASE WHEN passed = 0 AND error_message IS NULL THEN 1 ELSE 0 END) as failed_evaluations,
			SUM(CASE WHEN error_message IS NOT NULL THEN 1 ELSE 0 END) as error_evaluations,
			AVG(score) as average_score,
			AVG(execution_time) as average_execution_time
		FROM evaluation_results WHERE 1=1
	`

	var args []interface{}
	var conditions []string

	if filter.ModelProvider != nil {
		conditions = append(conditions, "model_provider = ?")
		args = append(args, *filter.ModelProvider)
	}

	if filter.ModelName != nil {
		conditions = append(conditions, "model_name = ?")
		args = append(args, *filter.ModelName)
	}

	if filter.TestType != nil {
		conditions = append(conditions, "test_type = ?")
		args = append(args, *filter.TestType)
	}

	if filter.StartTime != nil {
		conditions = append(conditions, "timestamp >= ?")
		args = append(args, filter.StartTime.Format(time.RFC3339))
	}

	if filter.EndTime != nil {
		conditions = append(conditions, "timestamp <= ?")
		args = append(args, filter.EndTime.Format(time.RFC3339))
	}

	if len(conditions) > 0 {
		query += " AND " + strings.Join(conditions, " AND ")
	}

	summary := &models.EvaluationSummary{}
	var avgScore, avgTime sql.NullFloat64
	err := r.db.QueryRow(query, args...).Scan(
		&summary.TotalEvaluations,
		&summary.PassedEvaluations,
		&summary.FailedEvaluations,
		&summary.ErrorEvaluations,
		&avgScore,
		&avgTime,
	)

	if err != nil {
		return nil, fmt.Errorf("failed to get summary: %w", err)
	}

	// Handle NULL values from AVG functions
	if avgScore.Valid {
		summary.AverageScore = avgScore.Float64
	}
	if avgTime.Valid {
		summary.AverageExecutionTime = avgTime.Float64
	}

	if summary.TotalEvaluations > 0 {
		summary.SuccessRate = float64(summary.PassedEvaluations) / float64(summary.TotalEvaluations)
	}

	// Get unique models and test types
	modelsQuery := `
		SELECT DISTINCT model_provider || '/' || model_name as model
		FROM evaluation_results WHERE 1=1
	`
	typesQuery := `
		SELECT DISTINCT test_type
		FROM evaluation_results WHERE 1=1
	`

	if len(conditions) > 0 {
		modelsQuery += " AND " + strings.Join(conditions, " AND ")
		typesQuery += " AND " + strings.Join(conditions, " AND ")
	}

	// Get models
	rows, err := r.db.Query(modelsQuery, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query models: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var model string
		if err := rows.Scan(&model); err != nil {
			return nil, fmt.Errorf("failed to scan model: %w", err)
		}
		summary.ModelsTested = append(summary.ModelsTested, model)
	}

	// Get test types
	rows, err = r.db.Query(typesQuery, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query test types: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var testType string
		if err := rows.Scan(&testType); err != nil {
			return nil, fmt.Errorf("failed to scan test type: %w", err)
		}
		summary.TestTypes = append(summary.TestTypes, testType)
	}

	return summary, nil
}

// SaveSession saves an evaluation session
func (r *Repository) SaveSession(ctx context.Context, session *models.EvaluationSession) error {
	contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
	contextLogger.Debug("Saving evaluation session", "session_id", session.SessionID)
	if err := session.PrepareForDB(); err != nil {
		return fmt.Errorf("failed to prepare session for database: %w", err)
	}

	query := `
		INSERT INTO evaluation_sessions (session_id, started_at, completed_at, status, total_tests, completed_tests, metadata)
		VALUES (?, ?, ?, ?, ?, ?, ?)
	`

	res, err := r.db.Exec(query,
		session.SessionID,
		session.StartedAt,
		session.CompletedAt,
		session.Status,
		session.TotalTests,
		session.CompletedTests,
		session.MetadataJSON,
	)

	if err != nil {
		return fmt.Errorf("failed to save session: %w", err)
	}

	id, err := res.LastInsertId()
	if err != nil {
		return fmt.Errorf("failed to get last insert ID: %w", err)
	}

	session.ID = int(id)
	return nil
}

// UpdateSession updates an evaluation session
func (r *Repository) UpdateSession(ctx context.Context, session *models.EvaluationSession) error {
	contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
	contextLogger.Debug("Updating evaluation session", "session_id", session.SessionID)
	if err := session.PrepareForDB(); err != nil {
		return fmt.Errorf("failed to prepare session for database: %w", err)
	}

	query := `
		UPDATE evaluation_sessions 
		SET completed_at = ?, status = ?, total_tests = ?, completed_tests = ?, metadata = ?
		WHERE session_id = ?
	`

	_, err := r.db.Exec(query,
		session.CompletedAt,
		session.Status,
		session.TotalTests,
		session.CompletedTests,
		session.MetadataJSON,
		session.SessionID,
	)

	if err != nil {
		return fmt.Errorf("failed to update session: %w", err)
	}

	return nil
}

// GetSession retrieves an evaluation session by session ID
func (r *Repository) GetSession(ctx context.Context, sessionID string) (*models.EvaluationSession, error) {
	contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
	contextLogger.Debug("Retrieving evaluation session", "session_id", sessionID)
	query := `
		SELECT id, session_id, started_at, completed_at, status, total_tests, completed_tests, metadata
		FROM evaluation_sessions WHERE session_id = ?
	`

	session := &models.EvaluationSession{}
	err := r.db.QueryRow(query, sessionID).Scan(
		&session.ID,
		&session.SessionID,
		&session.StartedAt,
		&session.CompletedAt,
		&session.Status,
		&session.TotalTests,
		&session.CompletedTests,
		&session.MetadataJSON,
	)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get session: %w", err)
	}

	if err := session.LoadFromDB(); err != nil {
		return nil, fmt.Errorf("failed to load session from database: %w", err)
	}

	return session, nil
}

// TestExecution repository methods

// CreateTestExecution creates a new test execution record
func (r *Repository) CreateTestExecution(ctx context.Context, execution *models.TestExecution) error {
	// Validation
	if err := validation.ValidateTestExecution(execution); err != nil {
		contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
		contextLogger.Error("Test execution validation failed",
			"component", "database.repository",
			"error", err.Error(),
			"test_type", execution.TestType,
		)
		return err
	}

	correlationID := logging.GetCorrelationID(ctx)

	query := `
		INSERT INTO test_executions (
			test_type, test_category, test_name,
			model_name, model_provider, model_version,
			prompt, parameters, expected_output,
			status, correlation_id, user_id, session_id, environment,
			retry_count
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`

	result, err := r.db.Exec(query,
		execution.TestType, execution.TestCategory, execution.TestName,
		execution.ModelName, execution.ModelProvider, execution.ModelVersion,
		execution.Prompt, execution.Parameters, execution.ExpectedOutput,
		execution.Status, execution.CorrelationID, execution.UserID,
		execution.SessionID, execution.Environment, execution.RetryCount,
	)

	if err != nil {
		contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
		contextLogger.Error("Failed to create test execution",
			"component", "database.repository",
			"error", err.Error(),
			"correlation_id", correlationID,
		)
		return fmt.Errorf("failed to create test execution: %w", err)
	}

	execution.ID, _ = result.LastInsertId()
	contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
	contextLogger.Info("Test execution created",
		"component", "database.repository",
		"execution_id", execution.ID,
		"test_type", execution.TestType,
		"model_name", execution.ModelName,
	)

	return nil
}

// UpdateTestExecutionStatus updates the status of a test execution
func (r *Repository) UpdateTestExecutionStatus(ctx context.Context, id int64, status string) error {
	query := `UPDATE test_executions SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?`
	_, err := r.db.Exec(query, status, id)
	if err != nil {
		r.logger.Debug("Failed to update test execution status",
			"execution_id", id,
			"status", status,
			"error", err.Error(),
		)
		return fmt.Errorf("failed to update test execution status: %w", err)
	}
	return nil
}

// CompleteTestExecution marks a test execution as completed with results
func (r *Repository) CompleteTestExecution(ctx context.Context, id int64, response string, score *float64, executionTimeMS int64) error {
	query := `
		UPDATE test_executions 
		SET status = 'completed', 
			raw_response = ?,
			score = ?,
			execution_time_ms = ?,
			completed_at = CURRENT_TIMESTAMP,
			updated_at = CURRENT_TIMESTAMP
		WHERE id = ?
	`
	_, err := r.db.Exec(query, response, score, executionTimeMS, id)
	if err != nil {
		r.logger.Debug("Failed to complete test execution",
			"execution_id", id,
			"error", err.Error(),
		)
		return fmt.Errorf("failed to complete test execution: %w", err)
	}
	return nil
}

// FailTestExecution marks a test execution as failed with error details
func (r *Repository) FailTestExecution(ctx context.Context, id int64, errorMessage string) error {
	query := `
		UPDATE test_executions 
		SET status = 'failed', 
			error_message = ?,
			completed_at = CURRENT_TIMESTAMP,
			updated_at = CURRENT_TIMESTAMP
		WHERE id = ?
	`
	_, err := r.db.Exec(query, errorMessage, id)
	if err != nil {
		r.logger.Debug("Failed to mark test execution as failed",
			"execution_id", id,
			"error", err.Error(),
		)
		return fmt.Errorf("failed to mark test execution as failed: %w", err)
	}
	return nil
}

// GetTestExecution retrieves a test execution by ID
func (r *Repository) GetTestExecution(ctx context.Context, id int64) (*models.TestExecution, error) {
	query := `
		SELECT id, test_type, test_category, test_name,
		       model_name, model_provider, model_version,
		       prompt, parameters, expected_output,
		       status, started_at, completed_at, execution_time_ms,
		       raw_response, score, score_breakdown,
		       correlation_id, user_id, session_id, environment,
		       error_message, retry_count, created_at, updated_at
		FROM test_executions WHERE id = ?
	`

	execution := &models.TestExecution{}
	err := r.db.QueryRow(query, id).Scan(
		&execution.ID, &execution.TestType, &execution.TestCategory, &execution.TestName,
		&execution.ModelName, &execution.ModelProvider, &execution.ModelVersion,
		&execution.Prompt, &execution.Parameters, &execution.ExpectedOutput,
		&execution.Status, &execution.StartedAt, &execution.CompletedAt, &execution.ExecutionTimeMS,
		&execution.RawResponse, &execution.Score, &execution.ScoreBreakdown,
		&execution.CorrelationID, &execution.UserID, &execution.SessionID, &execution.Environment,
		&execution.ErrorMessage, &execution.RetryCount, &execution.CreatedAt, &execution.UpdatedAt,
	)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get test execution: %w", err)
	}

	if err := execution.LoadFromDB(); err != nil {
		return nil, fmt.Errorf("failed to load test execution from database: %w", err)
	}

	return execution, nil
}

// GetTestExecutionFilter represents filter options for querying test executions
type GetTestExecutionFilter struct {
	ModelName     *string
	TestType      *string
	Status        *string
	CorrelationID *string
	SessionID     *string
	StartTime     *time.Time
	EndTime       *time.Time
	Limit         int
	Offset        int
}

// GetTestExecutions retrieves test executions with optional filtering
func (r *Repository) GetTestExecutions(ctx context.Context, filter GetTestExecutionFilter) ([]*models.TestExecution, error) {
	query := `
		SELECT id, test_type, test_category, test_name,
		       model_name, model_provider, model_version,
		       prompt, parameters, expected_output,
		       status, started_at, completed_at, execution_time_ms,
		       raw_response, score, score_breakdown,
		       correlation_id, user_id, session_id, environment,
		       error_message, retry_count, created_at, updated_at
		FROM test_executions WHERE 1=1
	`

	var args []interface{}
	var conditions []string

	if filter.ModelName != nil {
		conditions = append(conditions, "model_name = ?")
		args = append(args, *filter.ModelName)
	}

	if filter.TestType != nil {
		conditions = append(conditions, "test_type = ?")
		args = append(args, *filter.TestType)
	}

	if filter.Status != nil {
		conditions = append(conditions, "status = ?")
		args = append(args, *filter.Status)
	}

	if filter.CorrelationID != nil {
		conditions = append(conditions, "correlation_id = ?")
		args = append(args, *filter.CorrelationID)
	}

	if filter.SessionID != nil {
		conditions = append(conditions, "session_id = ?")
		args = append(args, *filter.SessionID)
	}

	if filter.StartTime != nil {
		conditions = append(conditions, "created_at >= ?")
		args = append(args, filter.StartTime.Format(time.RFC3339))
	}

	if filter.EndTime != nil {
		conditions = append(conditions, "created_at <= ?")
		args = append(args, filter.EndTime.Format(time.RFC3339))
	}

	if len(conditions) > 0 {
		query += " AND " + strings.Join(conditions, " AND ")
	}

	query += " ORDER BY created_at DESC"

	if filter.Limit > 0 {
		query += fmt.Sprintf(" LIMIT %d", filter.Limit)
	}

	if filter.Offset > 0 {
		query += fmt.Sprintf(" OFFSET %d", filter.Offset)
	}

	rows, err := r.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query test executions: %w", err)
	}
	defer rows.Close()

	var executions []*models.TestExecution
	for rows.Next() {
		execution := &models.TestExecution{}
		err := rows.Scan(
			&execution.ID, &execution.TestType, &execution.TestCategory, &execution.TestName,
			&execution.ModelName, &execution.ModelProvider, &execution.ModelVersion,
			&execution.Prompt, &execution.Parameters, &execution.ExpectedOutput,
			&execution.Status, &execution.StartedAt, &execution.CompletedAt, &execution.ExecutionTimeMS,
			&execution.RawResponse, &execution.Score, &execution.ScoreBreakdown,
			&execution.CorrelationID, &execution.UserID, &execution.SessionID, &execution.Environment,
			&execution.ErrorMessage, &execution.RetryCount, &execution.CreatedAt, &execution.UpdatedAt,
		)

		if err != nil {
			return nil, fmt.Errorf("failed to scan test execution: %w", err)
		}

		if err := execution.LoadFromDB(); err != nil {
			return nil, fmt.Errorf("failed to load test execution from database: %w", err)
		}

		executions = append(executions, execution)
	}

	return executions, rows.Err()
}

// TestResult repository methods

// CreateTestResult creates a new test result record
func (r *Repository) CreateTestResult(ctx context.Context, result *models.TestResult) error {
	// Validation
	if err := validation.ValidateTestResult(result); err != nil {
		contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
		contextLogger.Error("Test result validation failed",
			"component", "database.repository",
			"error", err.Error(),
			"execution_id", result.ExecutionID,
		)
		return err
	}

	correlationID := logging.GetCorrelationID(ctx)

	query := `
		INSERT INTO test_results (
			execution_id, result_type, result_name,
			score, max_score, weight,
			expected_value, actual_value, normalized_value,
			evaluation_criteria, scoring_breakdown, comparison_metrics,
			accuracy, relevance, completeness, creativity,
			evaluation_method, evaluator, confidence_level,
			validation_errors, parsing_errors
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`

	res, err := r.db.Exec(query,
		result.ExecutionID, result.ResultType, result.ResultName,
		result.Score, result.MaxScore, result.Weight,
		result.ExpectedValue, result.ActualValue, result.NormalizedValue,
		result.EvaluationCriteria, result.ScoringBreakdown, result.ComparisonMetrics,
		result.Accuracy, result.Relevance, result.Completeness, result.Creativity,
		result.EvaluationMethod, result.Evaluator, result.ConfidenceLevel,
		result.ValidationErrors, result.ParsingErrors,
	)

	if err != nil {
		contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
		contextLogger.Error("Failed to create test result",
			"component", "database.repository",
			"error", err.Error(),
			"correlation_id", correlationID,
			"execution_id", result.ExecutionID,
		)
		return fmt.Errorf("failed to create test result: %w", err)
	}

	result.ID, _ = res.LastInsertId()
	contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
	contextLogger.Info("Test result created",
		"component", "database.repository",
		"result_id", result.ID,
		"execution_id", result.ExecutionID,
		"correlation_id", correlationID,
	)
	return nil
}

// GetTestResultsByExecution retrieves all test results for a given execution
func (r *Repository) GetTestResultsByExecution(ctx context.Context, executionID int64) ([]*models.TestResult, error) {
	query := `
		SELECT id, execution_id, result_type, result_name,
		       score, max_score, weight,
		       expected_value, actual_value, normalized_value,
		       evaluation_criteria, scoring_breakdown, comparison_metrics,
		       accuracy, relevance, completeness, creativity,
		       evaluation_method, evaluator, confidence_level,
		       validation_errors, parsing_errors,
		       created_at, updated_at
		FROM test_results 
		WHERE execution_id = ? 
		ORDER BY created_at
	`

	rows, err := r.db.Query(query, executionID)
	if err != nil {
		return nil, fmt.Errorf("failed to query test results: %w", err)
	}
	defer rows.Close()

	var results []*models.TestResult
	for rows.Next() {
		result := &models.TestResult{}
		err := rows.Scan(
			&result.ID, &result.ExecutionID, &result.ResultType, &result.ResultName,
			&result.Score, &result.MaxScore, &result.Weight,
			&result.ExpectedValue, &result.ActualValue, &result.NormalizedValue,
			&result.EvaluationCriteria, &result.ScoringBreakdown, &result.ComparisonMetrics,
			&result.Accuracy, &result.Relevance, &result.Completeness, &result.Creativity,
			&result.EvaluationMethod, &result.Evaluator, &result.ConfidenceLevel,
			&result.ValidationErrors, &result.ParsingErrors,
			&result.CreatedAt, &result.UpdatedAt,
		)

		if err != nil {
			return nil, fmt.Errorf("failed to scan test result: %w", err)
		}

		if err := result.LoadFromDB(); err != nil {
			return nil, fmt.Errorf("failed to load test result from database: %w", err)
		}

		results = append(results, result)
	}

	return results, rows.Err()
}

// GetTestResult retrieves a test result by ID
func (r *Repository) GetTestResult(ctx context.Context, id int64) (*models.TestResult, error) {
	query := `
		SELECT id, execution_id, result_type, result_name,
		       score, max_score, weight,
		       expected_value, actual_value, normalized_value,
		       evaluation_criteria, scoring_breakdown, comparison_metrics,
		       accuracy, relevance, completeness, creativity,
		       evaluation_method, evaluator, confidence_level,
		       validation_errors, parsing_errors,
		       created_at, updated_at
		FROM test_results WHERE id = ?
	`

	result := &models.TestResult{}
	err := r.db.QueryRow(query, id).Scan(
		&result.ID, &result.ExecutionID, &result.ResultType, &result.ResultName,
		&result.Score, &result.MaxScore, &result.Weight,
		&result.ExpectedValue, &result.ActualValue, &result.NormalizedValue,
		&result.EvaluationCriteria, &result.ScoringBreakdown, &result.ComparisonMetrics,
		&result.Accuracy, &result.Relevance, &result.Completeness, &result.Creativity,
		&result.EvaluationMethod, &result.Evaluator, &result.ConfidenceLevel,
		&result.ValidationErrors, &result.ParsingErrors,
		&result.CreatedAt, &result.UpdatedAt,
	)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get test result: %w", err)
	}

	if err := result.LoadFromDB(); err != nil {
		return nil, fmt.Errorf("failed to load test result from database: %w", err)
	}

	return result, nil
}

// TestCategory repository methods

// CreateTestCategory creates a new test category record
func (r *Repository) CreateTestCategory(ctx context.Context, category *models.TestCategory) error {
	// Validation
	if err := validation.ValidateTestCategory(category); err != nil {
		contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
		contextLogger.Error("Test category validation failed",
			"component", "database.repository",
			"error", err.Error(),
			"category_name", category.Name,
		)
		return err
	}

	correlationID := logging.GetCorrelationID(ctx)

	query := `
		INSERT INTO test_categories (
			name, display_name, description,
			parent_category_id, category_path, sort_order,
			template_prompt, default_parameters, scoring_criteria,
			allowed_models, min_execution_time, max_execution_time, timeout_seconds,
			icon, color, tags, status, version
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`

	res, err := r.db.Exec(query,
		category.Name, category.DisplayName, category.Description,
		category.ParentCategoryID, category.CategoryPath, category.SortOrder,
		category.TemplatePrompt, category.DefaultParameters, category.ScoringCriteria,
		category.AllowedModels, category.MinExecutionTime, category.MaxExecutionTime, category.TimeoutSeconds,
		category.Icon, category.Color, category.Tags, category.Status, category.Version,
	)

	if err != nil {
		contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
		contextLogger.Error("Failed to create test category",
			"component", "database.repository",
			"error", err.Error(),
			"correlation_id", correlationID,
			"category_name", category.Name,
		)
		return fmt.Errorf("failed to create test category: %w", err)
	}

	category.ID, _ = res.LastInsertId()
	contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
	contextLogger.Info("Test category created",
		"component", "database.repository",
		"category_id", category.ID,
		"category_name", category.Name,
		"correlation_id", correlationID,
	)
	return nil
}

// GetTestCategory retrieves a test category by ID
func (r *Repository) GetTestCategory(ctx context.Context, id int64) (*models.TestCategory, error) {
	query := `
		SELECT id, name, display_name, description,
		       parent_category_id, category_path, sort_order,
		       template_prompt, default_parameters, scoring_criteria,
		       allowed_models, min_execution_time, max_execution_time, timeout_seconds,
		       icon, color, tags, status, version,
		       created_at, updated_at
		FROM test_categories WHERE id = ?
	`

	category := &models.TestCategory{}
	err := r.db.QueryRow(query, id).Scan(
		&category.ID, &category.Name, &category.DisplayName, &category.Description,
		&category.ParentCategoryID, &category.CategoryPath, &category.SortOrder,
		&category.TemplatePrompt, &category.DefaultParameters, &category.ScoringCriteria,
		&category.AllowedModels, &category.MinExecutionTime, &category.MaxExecutionTime, &category.TimeoutSeconds,
		&category.Icon, &category.Color, &category.Tags, &category.Status, &category.Version,
		&category.CreatedAt, &category.UpdatedAt,
	)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get test category: %w", err)
	}

	if err := category.LoadFromDB(); err != nil {
		return nil, fmt.Errorf("failed to load test category from database: %w", err)
	}

	return category, nil
}

// GetTestCategoryByName retrieves a test category by name
func (r *Repository) GetTestCategoryByName(ctx context.Context, name string) (*models.TestCategory, error) {
	query := `
		SELECT id, name, display_name, description,
		       parent_category_id, category_path, sort_order,
		       template_prompt, default_parameters, scoring_criteria,
		       allowed_models, min_execution_time, max_execution_time, timeout_seconds,
		       icon, color, tags, status, version,
		       created_at, updated_at
		FROM test_categories WHERE name = ? AND status = 'active'
	`

	category := &models.TestCategory{}
	err := r.db.QueryRow(query, name).Scan(
		&category.ID, &category.Name, &category.DisplayName, &category.Description,
		&category.ParentCategoryID, &category.CategoryPath, &category.SortOrder,
		&category.TemplatePrompt, &category.DefaultParameters, &category.ScoringCriteria,
		&category.AllowedModels, &category.MinExecutionTime, &category.MaxExecutionTime, &category.TimeoutSeconds,
		&category.Icon, &category.Color, &category.Tags, &category.Status, &category.Version,
		&category.CreatedAt, &category.UpdatedAt,
	)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get test category by name: %w", err)
	}

	if err := category.LoadFromDB(); err != nil {
		return nil, fmt.Errorf("failed to load test category from database: %w", err)
	}

	return category, nil
}

// GetTestCategories retrieves all active test categories
func (r *Repository) GetTestCategories(ctx context.Context) ([]*models.TestCategory, error) {
	query := `
		SELECT id, name, display_name, description,
		       parent_category_id, category_path, sort_order,
		       template_prompt, default_parameters, scoring_criteria,
		       allowed_models, min_execution_time, max_execution_time, timeout_seconds,
		       icon, color, tags, status, version,
		       created_at, updated_at
		FROM test_categories 
		WHERE status = 'active'
		ORDER BY sort_order, display_name
	`

	rows, err := r.db.Query(query)
	if err != nil {
		return nil, fmt.Errorf("failed to query test categories: %w", err)
	}
	defer rows.Close()

	var categories []*models.TestCategory
	for rows.Next() {
		category := &models.TestCategory{}
		err := rows.Scan(
			&category.ID, &category.Name, &category.DisplayName, &category.Description,
			&category.ParentCategoryID, &category.CategoryPath, &category.SortOrder,
			&category.TemplatePrompt, &category.DefaultParameters, &category.ScoringCriteria,
			&category.AllowedModels, &category.MinExecutionTime, &category.MaxExecutionTime, &category.TimeoutSeconds,
			&category.Icon, &category.Color, &category.Tags, &category.Status, &category.Version,
			&category.CreatedAt, &category.UpdatedAt,
		)

		if err != nil {
			return nil, fmt.Errorf("failed to scan test category: %w", err)
		}

		if err := category.LoadFromDB(); err != nil {
			return nil, fmt.Errorf("failed to load test category from database: %w", err)
		}

		categories = append(categories, category)
	}

	return categories, rows.Err()
}

// GetTestCategoryByID is an alias for GetTestCategory for interface compatibility
func (r *Repository) GetTestCategoryByID(ctx context.Context, id int64) (*models.TestCategory, error) {
	return r.GetTestCategory(ctx, id)
}

// Enhanced repository methods for Story 3.04

// GetTestExecutionByCorrelationID retrieves a test execution by correlation ID
func (r *Repository) GetTestExecutionByCorrelationID(ctx context.Context, correlationID string) (*models.TestExecution, error) {
	query := `
		SELECT id, test_type, test_category, test_name,
		       model_name, model_provider, model_version,
		       prompt, parameters, expected_output,
		       status, started_at, completed_at, execution_time_ms,
		       raw_response, score, score_breakdown,
		       correlation_id, user_id, session_id, environment,
		       error_message, retry_count, created_at, updated_at
		FROM test_executions WHERE correlation_id = ?
	`

	execution := &models.TestExecution{}
	err := r.db.QueryRow(query, correlationID).Scan(
		&execution.ID, &execution.TestType, &execution.TestCategory, &execution.TestName,
		&execution.ModelName, &execution.ModelProvider, &execution.ModelVersion,
		&execution.Prompt, &execution.Parameters, &execution.ExpectedOutput,
		&execution.Status, &execution.StartedAt, &execution.CompletedAt, &execution.ExecutionTimeMS,
		&execution.RawResponse, &execution.Score, &execution.ScoreBreakdown,
		&execution.CorrelationID, &execution.UserID, &execution.SessionID, &execution.Environment,
		&execution.ErrorMessage, &execution.RetryCount, &execution.CreatedAt, &execution.UpdatedAt,
	)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, ErrTestExecutionNotFound
		}
		return nil, fmt.Errorf("failed to get test execution by correlation ID: %w", err)
	}

	if err := execution.LoadFromDB(); err != nil {
		return nil, fmt.Errorf("failed to load test execution from database: %w", err)
	}

	return execution, nil
}

// GetTestExecutionsBySessionID retrieves test executions by session ID
func (r *Repository) GetTestExecutionsBySessionID(ctx context.Context, sessionID string) ([]*models.TestExecution, error) {
	query := `
		SELECT id, test_type, test_category, test_name,
		       model_name, model_provider, model_version,
		       prompt, parameters, expected_output,
		       status, started_at, completed_at, execution_time_ms,
		       raw_response, score, score_breakdown,
		       correlation_id, user_id, session_id, environment,
		       error_message, retry_count, created_at, updated_at
		FROM test_executions 
		WHERE session_id = ?
		ORDER BY created_at DESC
	`

	rows, err := r.db.Query(query, sessionID)
	if err != nil {
		return nil, fmt.Errorf("failed to query test executions by session ID: %w", err)
	}
	defer rows.Close()

	var executions []*models.TestExecution
	for rows.Next() {
		execution := &models.TestExecution{}
		err := rows.Scan(
			&execution.ID, &execution.TestType, &execution.TestCategory, &execution.TestName,
			&execution.ModelName, &execution.ModelProvider, &execution.ModelVersion,
			&execution.Prompt, &execution.Parameters, &execution.ExpectedOutput,
			&execution.Status, &execution.StartedAt, &execution.CompletedAt, &execution.ExecutionTimeMS,
			&execution.RawResponse, &execution.Score, &execution.ScoreBreakdown,
			&execution.CorrelationID, &execution.UserID, &execution.SessionID, &execution.Environment,
			&execution.ErrorMessage, &execution.RetryCount, &execution.CreatedAt, &execution.UpdatedAt,
		)

		if err != nil {
			return nil, fmt.Errorf("failed to scan test execution: %w", err)
		}

		if err := execution.LoadFromDB(); err != nil {
			return nil, fmt.Errorf("failed to load test execution from database: %w", err)
		}

		executions = append(executions, execution)
	}

	return executions, rows.Err()
}

// GetTestExecutionsByDateRange retrieves test executions within a date range with options
func (r *Repository) GetTestExecutionsByDateRange(ctx context.Context, start, end time.Time, options *QueryOptions) ([]*models.TestExecution, error) {
	query := `
		SELECT id, test_type, test_category, test_name,
		       model_name, model_provider, model_version,
		       prompt, parameters, expected_output,
		       status, started_at, completed_at, execution_time_ms,
		       raw_response, score, score_breakdown,
		       correlation_id, user_id, session_id, environment,
		       error_message, retry_count, created_at, updated_at
		FROM test_executions 
		WHERE created_at BETWEEN ? AND ?
	`
	args := []interface{}{start, end}

	// Add optional filters
	if options != nil {
		if modelName, ok := options.Filters["model_name"]; ok {
			query += " AND model_name = ?"
			args = append(args, modelName)
		}

		if testType, ok := options.Filters["test_type"]; ok {
			query += " AND test_type = ?"
			args = append(args, testType)
		}

		if status, ok := options.Filters["status"]; ok {
			query += " AND status = ?"
			args = append(args, status)
		}

		// Add ordering
		if options.OrderBy != "" {
			direction := "ASC"
			if options.OrderDir == "DESC" {
				direction = "DESC"
			}
			query += fmt.Sprintf(" ORDER BY %s %s", options.OrderBy, direction)
		} else {
			query += " ORDER BY created_at DESC"
		}

		// Add pagination
		if options.Limit > 0 {
			query += " LIMIT ?"
			args = append(args, options.Limit)

			if options.Offset > 0 {
				query += " OFFSET ?"
				args = append(args, options.Offset)
			}
		}
	}

	rows, err := r.db.Query(query, args...)
	if err != nil {
		contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
		contextLogger.Error("Failed to query test executions",
			"component", "database.repository",
			"error", err.Error(),
			"start_date", start,
			"end_date", end,
		)
		return nil, err
	}
	defer rows.Close()

	var executions []*models.TestExecution
	for rows.Next() {
		execution := &models.TestExecution{}
		err := r.scanTestExecution(rows, execution)
		if err != nil {
			return nil, err
		}
		executions = append(executions, execution)
	}

	return executions, nil
}

// scanTestExecution is a helper method to scan test execution rows
func (r *Repository) scanTestExecution(rows *sql.Rows, execution *models.TestExecution) error {
	err := rows.Scan(
		&execution.ID, &execution.TestType, &execution.TestCategory, &execution.TestName,
		&execution.ModelName, &execution.ModelProvider, &execution.ModelVersion,
		&execution.Prompt, &execution.Parameters, &execution.ExpectedOutput,
		&execution.Status, &execution.StartedAt, &execution.CompletedAt, &execution.ExecutionTimeMS,
		&execution.RawResponse, &execution.Score, &execution.ScoreBreakdown,
		&execution.CorrelationID, &execution.UserID, &execution.SessionID, &execution.Environment,
		&execution.ErrorMessage, &execution.RetryCount, &execution.CreatedAt, &execution.UpdatedAt,
	)
	if err != nil {
		return fmt.Errorf("failed to scan test execution: %w", err)
	}

	if err := execution.LoadFromDB(); err != nil {
		return fmt.Errorf("failed to load test execution from database: %w", err)
	}

	return nil
}

// GetExecutionStats calculates execution statistics based on filters
func (r *Repository) GetExecutionStats(ctx context.Context, filters *ExecutionFilters) (*ExecutionStats, error) {
	query := `
		SELECT 
			COUNT(*) as total_executions,
			COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_executions,
			COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_executions,
			COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_executions,
			AVG(CASE WHEN score IS NOT NULL THEN score END) as average_score,
			AVG(CASE WHEN execution_time_ms IS NOT NULL THEN execution_time_ms END) as average_execution_time
		FROM test_executions
		WHERE 1=1
	`

	args := []interface{}{}

	if filters != nil {
		if len(filters.ModelNames) > 0 {
			placeholders := make([]string, len(filters.ModelNames))
			for i, model := range filters.ModelNames {
				placeholders[i] = "?"
				args = append(args, model)
			}
			query += fmt.Sprintf(" AND model_name IN (%s)", strings.Join(placeholders, ","))
		}

		if filters.DateRange != nil {
			query += " AND created_at BETWEEN ? AND ?"
			args = append(args, filters.DateRange.Start, filters.DateRange.End)
		}
	}

	row := r.db.QueryRow(query, args...)

	stats := &ExecutionStats{}
	var avgScore, avgTime sql.NullFloat64
	err := row.Scan(
		&stats.TotalExecutions,
		&stats.CompletedExecutions,
		&stats.FailedExecutions,
		&stats.PendingExecutions,
		&avgScore,
		&avgTime,
	)

	if err != nil {
		contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
		contextLogger.Error("Failed to get execution stats",
			"component", "database.repository",
			"error", err.Error(),
		)
		return nil, err
	}

	// Handle NULL values from AVG functions
	if avgScore.Valid {
		stats.AverageScore = avgScore.Float64
	}
	if avgTime.Valid {
		stats.AverageExecutionTime = avgTime.Float64
	}

	// Calculate success rate
	if stats.TotalExecutions > 0 {
		stats.SuccessRate = float64(stats.CompletedExecutions) / float64(stats.TotalExecutions)
	}

	return stats, nil
}
