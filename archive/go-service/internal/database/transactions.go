package database

import (
	"context"
	"database/sql"

	"go-service/internal/logging"
	"go-service/internal/models"
)

// txDBWrapper wraps a transaction to implement the same interface as DB
type txDBWrapper struct {
	tx *sql.Tx
}

// Exec implements the Exec method for transactions
func (w *txDBWrapper) Exec(query string, args ...interface{}) (sql.Result, error) {
	return w.tx.Exec(query, args...)
}

// Query implements the Query method for transactions
func (w *txDBWrapper) Query(query string, args ...interface{}) (*sql.Rows, error) {
	return w.tx.Query(query, args...)
}

// QueryRow implements the QueryRow method for transactions
func (w *txDBWrapper) QueryRow(query string, args ...interface{}) *sql.Row {
	return w.tx.QueryRow(query, args...)
}

// Begin is not implemented for transactions (would be nested transactions)
func (w *txDBWrapper) Begin() (*sql.Tx, error) {
	panic("nested transactions not supported")
}

// BeginTx is not implemented for transactions (would be nested transactions)
func (w *txDBWrapper) BeginTx(ctx context.Context, opts *sql.TxOptions) (*sql.Tx, error) {
	panic("nested transactions not supported")
}

// TxRepository wraps a transaction with repository methods
type TxRepository struct {
	tx     *sql.Tx
	repo   *Repository
	logger *logging.Logger
}

// BeginTransaction starts a new database transaction
func (r *Repository) BeginTransaction(ctx context.Context) (*TxRepository, error) {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		contextLogger := logging.LogWithContext(ctx, r.logger.Logger)
		contextLogger.Error("Failed to begin transaction",
			"component", "database.transactions",
			"error", err.Error(),
		)
		return nil, err
	}

	// Create a wrapper that implements the DB interface for the transaction
	txDB := &txDBWrapper{tx: tx}
	
	// Create a new repository instance that uses the transaction
	txRepo := newRepositoryWithInterface(txDB, r.logger)

	return &TxRepository{
		tx:     tx,
		repo:   txRepo,
		logger: r.logger,
	}, nil
}

// Commit commits the transaction
func (tr *TxRepository) Commit(ctx context.Context) error {
	err := tr.tx.Commit()
	contextLogger := logging.LogWithContext(ctx, tr.logger.Logger)
	if err != nil {
		contextLogger.Error("Failed to commit transaction",
			"component", "database.transactions",
			"error", err.Error(),
		)
	} else {
		contextLogger.Debug("Transaction committed successfully",
			"component", "database.transactions",
		)
	}
	return err
}

// Rollback rolls back the transaction
func (tr *TxRepository) Rollback(ctx context.Context) error {
	err := tr.tx.Rollback()
	contextLogger := logging.LogWithContext(ctx, tr.logger.Logger)
	if err != nil && err != sql.ErrTxDone {
		contextLogger.Error("Failed to rollback transaction",
			"component", "database.transactions",
			"error", err.Error(),
		)
	} else {
		contextLogger.Debug("Transaction rolled back",
			"component", "database.transactions",
		)
	}
	return err
}

// Repository returns the transaction-scoped repository
func (tr *TxRepository) Repository() *Repository {
	return tr.repo
}

// CreateTestExecutionWithResults creates a test execution and its related results atomically
func (r *Repository) CreateTestExecutionWithResults(ctx context.Context, execution *models.TestExecution, results []*models.TestResult) error {
	tx, err := r.BeginTransaction(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx) // Will be no-op if committed

	// Create execution
	if err := tx.Repository().CreateTestExecution(ctx, execution); err != nil {
		return err
	}

	// Create results
	for _, result := range results {
		result.ExecutionID = execution.ID
		if err := tx.Repository().CreateTestResult(ctx, result); err != nil {
			return err
		}
	}

	return tx.Commit(ctx)
}

// CreateTestExecutionWithCategory creates a test execution and associates it with a category atomically
func (r *Repository) CreateTestExecutionWithCategory(ctx context.Context, execution *models.TestExecution, categoryID int64) error {
	tx, err := r.BeginTransaction(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	// Verify category exists
	category, err := tx.Repository().GetTestCategoryByID(ctx, categoryID)
	if err != nil {
		return err
	}
	if category == nil {
		return ErrTestCategoryNotFound
	}

	// Set the category name in execution
	execution.TestCategory = &category.Name

	// Create execution
	if err := tx.Repository().CreateTestExecution(ctx, execution); err != nil {
		return err
	}

	return tx.Commit(ctx)
}