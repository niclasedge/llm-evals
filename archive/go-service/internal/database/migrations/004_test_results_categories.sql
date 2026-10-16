-- Test results and categories migration
-- Adds detailed test results and predefined test categories for enhanced organization

-- Test Results Table
CREATE TABLE test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Foreign key to test execution
    execution_id INTEGER NOT NULL REFERENCES test_executions(id) ON DELETE CASCADE,
    
    -- Result identification
    result_type VARCHAR(50) NOT NULL,              -- primary, secondary, validation, comparison
    result_name VARCHAR(100),                      -- specific result identifier
    
    -- Scoring and evaluation
    score REAL,                                    -- individual result score (0.0 - 1.0)
    max_score REAL DEFAULT 1.0,                   -- maximum possible score
    weight REAL DEFAULT 1.0,                      -- weight in overall scoring
    
    -- Result content
    expected_value TEXT,                           -- expected result for comparison
    actual_value TEXT,                             -- actual result from model
    normalized_value TEXT,                         -- processed/normalized result
    
    -- Detailed analysis (stored as TEXT for SQLite compatibility)
    evaluation_criteria TEXT,                      -- JSON: criteria used for evaluation
    scoring_breakdown TEXT,                        -- JSON: detailed scoring information
    comparison_metrics TEXT,                       -- JSON: similarity, accuracy, etc.
    
    -- Quality assessment
    accuracy REAL,                                 -- accuracy score (if applicable)
    relevance REAL,                               -- relevance score (if applicable)
    completeness REAL,                            -- completeness score (if applicable)
    creativity REAL,                              -- creativity score (if applicable)
    
    -- Metadata and context
    evaluation_method VARCHAR(100),                -- manual, automated, hybrid
    evaluator VARCHAR(100),                       -- who/what performed evaluation
    confidence_level REAL,                        -- confidence in the evaluation
    
    -- Error and validation
    validation_errors TEXT,                       -- JSON: validation issues found
    parsing_errors TEXT,                          -- result parsing problems
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Test Categories Table
CREATE TABLE test_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Category identification
    name VARCHAR(50) UNIQUE NOT NULL,              -- coding, reasoning, creative, tool-calling
    display_name VARCHAR(100) NOT NULL,            -- human-readable name
    description TEXT,                              -- category description
    
    -- Category hierarchy
    parent_category_id INTEGER REFERENCES test_categories(id) ON DELETE SET NULL,
    category_path VARCHAR(500),                    -- hierarchical path (e.g., "coding/algorithms/sorting")
    sort_order INTEGER DEFAULT 0,                 -- display order
    
    -- Test configuration
    template_prompt TEXT,                          -- default prompt template
    default_parameters TEXT,                       -- JSON: default model parameters
    scoring_criteria TEXT,                         -- JSON: scoring methodology
    
    -- Validation and constraints
    allowed_models TEXT,                           -- JSON: compatible models list
    min_execution_time INTEGER,                    -- minimum expected execution time (ms)
    max_execution_time INTEGER,                    -- maximum expected execution time (ms)
    timeout_seconds INTEGER DEFAULT 300,          -- test timeout
    
    -- UI and display
    icon VARCHAR(50),                              -- category icon identifier
    color VARCHAR(20),                            -- UI color scheme
    tags TEXT,                                    -- JSON: searchable tags
    
    -- Status and lifecycle
    status VARCHAR(20) DEFAULT 'active',          -- active, inactive, deprecated
    version VARCHAR(20) DEFAULT '1.0',            -- category version
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for test_results
CREATE INDEX idx_test_results_execution_id ON test_results(execution_id);
CREATE INDEX idx_test_results_type_score ON test_results(result_type, score);
CREATE INDEX idx_test_results_score ON test_results(score) WHERE score IS NOT NULL;
CREATE INDEX idx_test_results_created_at ON test_results(created_at);

-- Indexes for test_categories
CREATE INDEX idx_test_categories_name ON test_categories(name);
CREATE INDEX idx_test_categories_parent ON test_categories(parent_category_id);
CREATE INDEX idx_test_categories_path ON test_categories(category_path);
CREATE INDEX idx_test_categories_status ON test_categories(status);

-- Composite indexes for complex queries
CREATE INDEX idx_test_results_execution_type ON test_results(execution_id, result_type);
CREATE INDEX idx_test_categories_parent_order ON test_categories(parent_category_id, sort_order);

-- Link test_executions to test_categories
ALTER TABLE test_executions ADD COLUMN category_id INTEGER 
    REFERENCES test_categories(id) ON DELETE SET NULL;

-- Index for the new foreign key
CREATE INDEX idx_test_executions_category_id ON test_executions(category_id);