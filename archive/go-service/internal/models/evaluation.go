package models

import (
	"database/sql/driver"
	"encoding/json"
	"time"
)

// EvaluationResult represents an evaluation result exactly matching the Python format
type EvaluationResult struct {
	ID               *int                   `json:"id" db:"id"`
	Timestamp        *time.Time             `json:"timestamp" db:"timestamp"`
	ModelProvider    string                 `json:"model_provider" db:"model_provider"`
	ModelName        string                 `json:"model_name" db:"model_name"`
	TestName         string                 `json:"test_name" db:"test_name"`
	TestType         string                 `json:"test_type" db:"test_type"`
	Query            string                 `json:"query" db:"query"`
	Response         string                 `json:"response" db:"response"`
	ExpectedResponse *string                `json:"expected_response" db:"expected_response"`
	Metrics          map[string]float64     `json:"metrics" db:"-"`
	MetricsJSON      *string                `json:"-" db:"metrics"`
	Score            float64                `json:"score" db:"score"`
	Passed           bool                   `json:"passed" db:"passed"`
	ExecutionTime    float64                `json:"execution_time" db:"execution_time"`
	ErrorMessage     *string                `json:"error_message" db:"error_message"`
	Metadata         map[string]interface{} `json:"metadata" db:"-"`
	MetadataJSON     *string                `json:"-" db:"metadata"`
}

// EvaluationSession represents a session for tracking evaluations
type EvaluationSession struct {
	ID             int                    `json:"id" db:"id"`
	SessionID      string                 `json:"session_id" db:"session_id"`
	StartedAt      time.Time              `json:"started_at" db:"started_at"`
	CompletedAt    *time.Time             `json:"completed_at" db:"completed_at"`
	Status         string                 `json:"status" db:"status"`
	TotalTests     int                    `json:"total_tests" db:"total_tests"`
	CompletedTests int                    `json:"completed_tests" db:"completed_tests"`
	Metadata       map[string]interface{} `json:"metadata" db:"-"`
	MetadataJSON   *string                `json:"-" db:"metadata"`
}

// PerformanceMetrics represents performance tracking data
type PerformanceMetrics struct {
	ID               int                    `json:"id" db:"id"`
	Timestamp        time.Time              `json:"timestamp" db:"timestamp"`
	ModelName        string                 `json:"model_name" db:"model_name"`
	TestType         string                 `json:"test_type" db:"test_type"`
	AvgExecutionTime *float64               `json:"avg_execution_time" db:"avg_execution_time"`
	SuccessRate      *float64               `json:"success_rate" db:"success_rate"`
	TotalRequests    *int                   `json:"total_requests" db:"total_requests"`
	Metadata         map[string]interface{} `json:"metadata" db:"-"`
	MetadataJSON     *string                `json:"-" db:"metadata"`
}

// ModelPerformanceSummary represents aggregated performance data
type ModelPerformanceSummary struct {
	ID               int       `json:"id" db:"id"`
	ModelProvider    string    `json:"model_provider" db:"model_provider"`
	ModelName        string    `json:"model_name" db:"model_name"`
	TestType         string    `json:"test_type" db:"test_type"`
	PeriodStart      time.Time `json:"period_start" db:"period_start"`
	PeriodEnd        time.Time `json:"period_end" db:"period_end"`
	TotalTests       int       `json:"total_tests" db:"total_tests"`
	PassedTests      int       `json:"passed_tests" db:"passed_tests"`
	FailedTests      int       `json:"failed_tests" db:"failed_tests"`
	AvgScore         float64   `json:"avg_score" db:"avg_score"`
	AvgExecutionTime float64   `json:"avg_execution_time" db:"avg_execution_time"`
	SuccessRate      float64   `json:"success_rate" db:"success_rate"`
	CreatedAt        time.Time `json:"created_at" db:"created_at"`
}

// TestExecution represents comprehensive test execution tracking
type TestExecution struct {
	ID int64 `json:"id" db:"id"`

	// Test identification
	TestType     string  `json:"test_type" db:"test_type"`
	TestCategory *string `json:"test_category" db:"test_category"`
	TestName     *string `json:"test_name" db:"test_name"`

	// Model configuration
	ModelName     string  `json:"model_name" db:"model_name"`
	ModelProvider *string `json:"model_provider" db:"model_provider"`
	ModelVersion  *string `json:"model_version" db:"model_version"`

	// Test content
	Prompt         string   `json:"prompt" db:"prompt"`
	Parameters     *JSONMap `json:"parameters" db:"parameters"`
	ExpectedOutput *string  `json:"expected_output" db:"expected_output"`

	// Execution tracking
	Status          string     `json:"status" db:"status"`
	StartedAt       time.Time  `json:"started_at" db:"started_at"`
	CompletedAt     *time.Time `json:"completed_at" db:"completed_at"`
	ExecutionTimeMS *int64     `json:"execution_time_ms" db:"execution_time_ms"`

	// Results
	RawResponse    *string  `json:"raw_response" db:"raw_response"`
	Score          *float64 `json:"score" db:"score"`
	ScoreBreakdown *JSONMap `json:"score_breakdown" db:"score_breakdown"`

	// Context
	CorrelationID string  `json:"correlation_id" db:"correlation_id"`
	UserID        *string `json:"user_id" db:"user_id"`
	SessionID     *string `json:"session_id" db:"session_id"`
	Environment   string  `json:"environment" db:"environment"`

	// Error handling
	ErrorMessage *string `json:"error_message" db:"error_message"`
	RetryCount   int     `json:"retry_count" db:"retry_count"`

	// Audit
	CreatedAt time.Time `json:"created_at" db:"created_at"`
	UpdatedAt time.Time `json:"updated_at" db:"updated_at"`
}

// JSONMap handles JSON field marshaling for test execution metadata
type JSONMap map[string]interface{}

func (j JSONMap) Value() (driver.Value, error) {
	if j == nil {
		return nil, nil
	}
	return json.Marshal(j)
}

func (j *JSONMap) Scan(value interface{}) error {
	if value == nil {
		*j = nil
		return nil
	}
	switch v := value.(type) {
	case []byte:
		return json.Unmarshal(v, j)
	case string:
		return json.Unmarshal([]byte(v), j)
	}
	return nil
}

// EvaluationSummary represents summary statistics matching Python format
type EvaluationSummary struct {
	TotalEvaluations     int      `json:"total_evaluations"`
	PassedEvaluations    int      `json:"passed_evaluations"`
	FailedEvaluations    int      `json:"failed_evaluations"`
	ErrorEvaluations     int      `json:"error_evaluations"`
	AverageScore         float64  `json:"average_score"`
	AverageExecutionTime float64  `json:"average_execution_time"`
	SuccessRate          float64  `json:"success_rate"`
	ModelsTested         []string `json:"models_tested"`
	TestTypes            []string `json:"test_types"`
}

// PrepareForDB converts JSON fields to strings for database storage
func (e *EvaluationResult) PrepareForDB() error {
	if e.Metrics != nil {
		metricsBytes, err := json.Marshal(e.Metrics)
		if err != nil {
			return err
		}
		metricsStr := string(metricsBytes)
		e.MetricsJSON = &metricsStr
	}

	if e.Metadata != nil {
		metadataBytes, err := json.Marshal(e.Metadata)
		if err != nil {
			return err
		}
		metadataStr := string(metadataBytes)
		e.MetadataJSON = &metadataStr
	}

	return nil
}

// LoadFromDB converts string fields from database to Go types
func (e *EvaluationResult) LoadFromDB() error {
	if e.MetricsJSON != nil && *e.MetricsJSON != "" {
		if err := json.Unmarshal([]byte(*e.MetricsJSON), &e.Metrics); err != nil {
			return err
		}
	}

	if e.MetadataJSON != nil && *e.MetadataJSON != "" {
		if err := json.Unmarshal([]byte(*e.MetadataJSON), &e.Metadata); err != nil {
			return err
		}
	}

	return nil
}

// PrepareForDB converts JSON fields to strings for database storage
func (s *EvaluationSession) PrepareForDB() error {
	if s.Metadata != nil {
		metadataBytes, err := json.Marshal(s.Metadata)
		if err != nil {
			return err
		}
		metadataStr := string(metadataBytes)
		s.MetadataJSON = &metadataStr
	}

	return nil
}

// LoadFromDB converts string fields from database to Go types
func (s *EvaluationSession) LoadFromDB() error {
	if s.MetadataJSON != nil && *s.MetadataJSON != "" {
		if err := json.Unmarshal([]byte(*s.MetadataJSON), &s.Metadata); err != nil {
			return err
		}
	}

	return nil
}

// PrepareForDB converts JSON fields to strings for database storage
func (p *PerformanceMetrics) PrepareForDB() error {
	if p.Metadata != nil {
		metadataBytes, err := json.Marshal(p.Metadata)
		if err != nil {
			return err
		}
		metadataStr := string(metadataBytes)
		p.MetadataJSON = &metadataStr
	}

	return nil
}

// LoadFromDB converts string fields from database to Go types
func (p *PerformanceMetrics) LoadFromDB() error {
	if p.MetadataJSON != nil && *p.MetadataJSON != "" {
		if err := json.Unmarshal([]byte(*p.MetadataJSON), &p.Metadata); err != nil {
			return err
		}
	}

	return nil
}

// PrepareForDB converts JSON fields to strings for database storage
func (t *TestExecution) PrepareForDB() error {
	// JSONMap fields are handled automatically by the driver interfaces
	return nil
}

// LoadFromDB converts string fields from database to Go types
func (t *TestExecution) LoadFromDB() error {
	// JSONMap fields are handled automatically by the driver interfaces
	return nil
}

// TestResult represents detailed test result data linked to test executions
type TestResult struct {
	ID          int64 `json:"id" db:"id"`
	ExecutionID int64 `json:"execution_id" db:"execution_id"`

	// Result identification
	ResultType string  `json:"result_type" db:"result_type"`
	ResultName *string `json:"result_name" db:"result_name"`

	// Scoring
	Score    *float64 `json:"score" db:"score"`
	MaxScore float64  `json:"max_score" db:"max_score"`
	Weight   float64  `json:"weight" db:"weight"`

	// Content
	ExpectedValue   *string `json:"expected_value" db:"expected_value"`
	ActualValue     *string `json:"actual_value" db:"actual_value"`
	NormalizedValue *string `json:"normalized_value" db:"normalized_value"`

	// Analysis (stored as TEXT in database)
	EvaluationCriteria *JSONMap `json:"evaluation_criteria" db:"evaluation_criteria"`
	ScoringBreakdown   *JSONMap `json:"scoring_breakdown" db:"scoring_breakdown"`
	ComparisonMetrics  *JSONMap `json:"comparison_metrics" db:"comparison_metrics"`

	// Quality scores
	Accuracy     *float64 `json:"accuracy" db:"accuracy"`
	Relevance    *float64 `json:"relevance" db:"relevance"`
	Completeness *float64 `json:"completeness" db:"completeness"`
	Creativity   *float64 `json:"creativity" db:"creativity"`

	// Metadata
	EvaluationMethod *string  `json:"evaluation_method" db:"evaluation_method"`
	Evaluator        *string  `json:"evaluator" db:"evaluator"`
	ConfidenceLevel  *float64 `json:"confidence_level" db:"confidence_level"`

	// Validation
	ValidationErrors *JSONMap `json:"validation_errors" db:"validation_errors"`
	ParsingErrors    *string  `json:"parsing_errors" db:"parsing_errors"`

	// Audit
	CreatedAt time.Time `json:"created_at" db:"created_at"`
	UpdatedAt time.Time `json:"updated_at" db:"updated_at"`
}

// TestCategory represents predefined test categories and templates
type TestCategory struct {
	ID          int64   `json:"id" db:"id"`
	Name        string  `json:"name" db:"name"`
	DisplayName string  `json:"display_name" db:"display_name"`
	Description *string `json:"description" db:"description"`

	// Hierarchy
	ParentCategoryID *int64  `json:"parent_category_id" db:"parent_category_id"`
	CategoryPath     *string `json:"category_path" db:"category_path"`
	SortOrder        int     `json:"sort_order" db:"sort_order"`

	// Configuration
	TemplatePrompt    *string  `json:"template_prompt" db:"template_prompt"`
	DefaultParameters *JSONMap `json:"default_parameters" db:"default_parameters"`
	ScoringCriteria   *JSONMap `json:"scoring_criteria" db:"scoring_criteria"`

	// Constraints
	AllowedModels    *JSONMap `json:"allowed_models" db:"allowed_models"`
	MinExecutionTime *int     `json:"min_execution_time" db:"min_execution_time"`
	MaxExecutionTime *int     `json:"max_execution_time" db:"max_execution_time"`
	TimeoutSeconds   int      `json:"timeout_seconds" db:"timeout_seconds"`

	// UI
	Icon  *string  `json:"icon" db:"icon"`
	Color *string  `json:"color" db:"color"`
	Tags  *JSONMap `json:"tags" db:"tags"`

	// Status
	Status  string `json:"status" db:"status"`
	Version string `json:"version" db:"version"`

	// Audit
	CreatedAt time.Time `json:"created_at" db:"created_at"`
	UpdatedAt time.Time `json:"updated_at" db:"updated_at"`
}

// PrepareForDB converts JSON fields to strings for database storage
func (tr *TestResult) PrepareForDB() error {
	// JSONMap fields are handled automatically by the driver interfaces
	return nil
}

// LoadFromDB converts string fields from database to Go types
func (tr *TestResult) LoadFromDB() error {
	// JSONMap fields are handled automatically by the driver interfaces
	return nil
}

// PrepareForDB converts JSON fields to strings for database storage
func (tc *TestCategory) PrepareForDB() error {
	// JSONMap fields are handled automatically by the driver interfaces
	return nil
}

// LoadFromDB converts string fields from database to Go types
func (tc *TestCategory) LoadFromDB() error {
	// JSONMap fields are handled automatically by the driver interfaces
	return nil
}
