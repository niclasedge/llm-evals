package database

import (
	"context"
	"time"

	"go-service/internal/models"
)

// TestExecutionRepository defines methods for test execution operations
type TestExecutionRepository interface {
	// Basic CRUD
	Create(ctx context.Context, execution *models.TestExecution) error
	GetByID(ctx context.Context, id int64) (*models.TestExecution, error)
	Update(ctx context.Context, execution *models.TestExecution) error
	Delete(ctx context.Context, id int64) error

	// Status management
	UpdateStatus(ctx context.Context, id int64, status string) error
	CompleteExecution(ctx context.Context, id int64, response string, score *float64, duration int64) error
	FailExecution(ctx context.Context, id int64, errorMsg string) error

	// Query methods
	GetByCorrelationID(ctx context.Context, correlationID string) (*models.TestExecution, error)
	GetBySessionID(ctx context.Context, sessionID string) ([]*models.TestExecution, error)
	GetByDateRange(ctx context.Context, start, end time.Time, options *QueryOptions) ([]*models.TestExecution, error)
	GetByModel(ctx context.Context, modelName string, options *QueryOptions) ([]*models.TestExecution, error)
	GetByCategory(ctx context.Context, categoryID int64, options *QueryOptions) ([]*models.TestExecution, error)

	// Analytics
	GetExecutionStats(ctx context.Context, filters *ExecutionFilters) (*ExecutionStats, error)
	GetModelPerformance(ctx context.Context, modelName string, timeRange *TimeRange) (*ModelPerformance, error)
}

// TestResultRepository defines methods for test result operations
type TestResultRepository interface {
	// Basic CRUD
	Create(ctx context.Context, result *models.TestResult) error
	GetByID(ctx context.Context, id int64) (*models.TestResult, error)
	Update(ctx context.Context, result *models.TestResult) error
	Delete(ctx context.Context, id int64) error

	// Query methods
	GetByExecutionID(ctx context.Context, executionID int64) ([]*models.TestResult, error)
	GetByResultType(ctx context.Context, resultType string, options *QueryOptions) ([]*models.TestResult, error)
	GetByScoreRange(ctx context.Context, minScore, maxScore float64, options *QueryOptions) ([]*models.TestResult, error)

	// Batch operations
	CreateBatch(ctx context.Context, results []*models.TestResult) error
	UpdateBatch(ctx context.Context, results []*models.TestResult) error

	// Analytics
	GetAverageScores(ctx context.Context, filters *ResultFilters) (map[string]float64, error)
	GetScoreDistribution(ctx context.Context, filters *ResultFilters) (*ScoreDistribution, error)
}

// TestCategoryRepository defines methods for test category operations
type TestCategoryRepository interface {
	// Basic CRUD
	Create(ctx context.Context, category *models.TestCategory) error
	GetByID(ctx context.Context, id int64) (*models.TestCategory, error)
	GetByName(ctx context.Context, name string) (*models.TestCategory, error)
	Update(ctx context.Context, category *models.TestCategory) error
	Delete(ctx context.Context, id int64) error

	// Hierarchy methods
	GetAll(ctx context.Context) ([]*models.TestCategory, error)
	GetRootCategories(ctx context.Context) ([]*models.TestCategory, error)
	GetSubcategories(ctx context.Context, parentID int64) ([]*models.TestCategory, error)
	GetCategoryHierarchy(ctx context.Context) (*CategoryHierarchy, error)

	// Status management
	ActivateCategory(ctx context.Context, id int64) error
	DeactivateCategory(ctx context.Context, id int64) error
}

// Supporting types for query operations
type QueryOptions struct {
	Limit    int
	Offset   int
	OrderBy  string
	OrderDir string // ASC, DESC
	Filters  map[string]interface{}
}

// ExecutionFilters for complex filtering
type ExecutionFilters struct {
	ModelNames  []string
	TestTypes   []string
	CategoryIDs []int64
	Status      []string
	DateRange   *TimeRange
	UserID      *string
	Environment *string
}

// ResultFilters for test result filtering
type ResultFilters struct {
	ExecutionIDs []int64
	ResultTypes  []string
	CategoryIDs  []int64
	ScoreRange   *ScoreRange
	DateRange    *TimeRange
}

// TimeRange for date filtering
type TimeRange struct {
	Start time.Time
	End   time.Time
}

// ScoreRange for score filtering
type ScoreRange struct {
	Min float64
	Max float64
}

// ExecutionStats for analytics
type ExecutionStats struct {
	TotalExecutions      int64   `json:"total_executions"`
	CompletedExecutions  int64   `json:"completed_executions"`
	FailedExecutions     int64   `json:"failed_executions"`
	PendingExecutions    int64   `json:"pending_executions"`
	AverageScore         float64 `json:"average_score"`
	AverageExecutionTime float64 `json:"average_execution_time"`
	SuccessRate          float64 `json:"success_rate"`
}

// ModelPerformance for model analytics
type ModelPerformance struct {
	ModelName            string    `json:"model_name"`
	TotalExecutions      int64     `json:"total_executions"`
	AverageScore         float64   `json:"average_score"`
	AverageExecutionTime float64   `json:"average_execution_time"`
	SuccessRate          float64   `json:"success_rate"`
	PeriodStart          time.Time `json:"period_start"`
	PeriodEnd            time.Time `json:"period_end"`
}

// ScoreDistribution for analytics
type ScoreDistribution struct {
	Buckets    []ScoreBucket `json:"buckets"`
	TotalCount int64         `json:"total_count"`
}

// ScoreBucket represents a score range bucket
type ScoreBucket struct {
	MinScore float64 `json:"min_score"`
	MaxScore float64 `json:"max_score"`
	Count    int64   `json:"count"`
}

// CategoryHierarchy represents the category tree structure
type CategoryHierarchy struct {
	RootCategories []*models.TestCategory `json:"root_categories"`
}