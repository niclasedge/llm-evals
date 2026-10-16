"""
Database Management for LLM Evaluation Results
"""

import sqlite3
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import aiosqlite


@dataclass
class EvaluationResult:
    """Data class for evaluation results"""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    model_provider: str = ""
    model_name: str = ""
    test_name: str = ""
    test_type: str = ""
    query: str = ""
    response: str = ""
    expected_response: Optional[str] = None
    metrics: Dict[str, float] = None
    score: float = 0.0
    passed: bool = False
    execution_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metrics is None:
            self.metrics = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class EvaluationSummary:
    """Summary statistics for evaluations"""
    total_evaluations: int = 0
    passed_evaluations: int = 0
    failed_evaluations: int = 0
    error_evaluations: int = 0
    average_score: float = 0.0
    average_execution_time: float = 0.0
    success_rate: float = 0.0
    models_tested: List[str] = None
    test_types: List[str] = None
    
    def __post_init__(self):
        if self.models_tested is None:
            self.models_tested = []
        if self.test_types is None:
            self.test_types = []


class DatabaseManager:
    """Async database manager for evaluation results"""
    
    def __init__(self, db_path: str = "data/evaluation_results.db"):
        self.db_path = db_path
        self._ensure_data_directory()
    
    def _ensure_data_directory(self):
        """Ensure data directory exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS evaluation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    model_provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    test_name TEXT NOT NULL,
                    test_type TEXT NOT NULL,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    expected_response TEXT,
                    metrics TEXT,
                    score REAL DEFAULT 0.0,
                    passed BOOLEAN DEFAULT FALSE,
                    execution_time REAL DEFAULT 0.0,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS evaluation_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    config TEXT,
                    summary TEXT,
                    status TEXT DEFAULT 'running'
                )
            ''')
            
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON evaluation_results(timestamp)
            ''')
            
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_model ON evaluation_results(model_provider, model_name)
            ''')
            
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_test_type ON evaluation_results(test_type)
            ''')
            
            await db.commit()
    
    async def save_result(self, result: EvaluationResult) -> int:
        """Save evaluation result to database"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO evaluation_results (
                    model_provider, model_name, test_name, test_type, query, response,
                    expected_response, metrics, score, passed, execution_time, error_message, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.model_provider,
                result.model_name,
                result.test_name,
                result.test_type,
                result.query,
                result.response,
                result.expected_response,
                json.dumps(result.metrics),
                result.score,
                result.passed,
                result.execution_time,
                result.error_message,
                json.dumps(result.metadata)
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def save_results_batch(self, results: List[EvaluationResult]) -> List[int]:
        """Save multiple evaluation results in a batch"""
        async with aiosqlite.connect(self.db_path) as db:
            result_ids = []
            for result in results:
                cursor = await db.execute('''
                    INSERT INTO evaluation_results (
                        model_provider, model_name, test_name, test_type, query, response,
                        expected_response, metrics, score, passed, execution_time, error_message, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.model_provider,
                    result.model_name,
                    result.test_name,
                    result.test_type,
                    result.query,
                    result.response,
                    result.expected_response,
                    json.dumps(result.metrics),
                    result.score,
                    result.passed,
                    result.execution_time,
                    result.error_message,
                    json.dumps(result.metadata)
                ))
                result_ids.append(cursor.lastrowid)
            await db.commit()
            return result_ids
    
    async def get_result(self, result_id: int) -> Optional[EvaluationResult]:
        """Get evaluation result by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM evaluation_results WHERE id = ?
            ''', (result_id,))
            row = await cursor.fetchone()
            
            if row:
                return self._row_to_result(row)
            return None
    
    async def get_results(self, 
                         model_provider: Optional[str] = None,
                         model_name: Optional[str] = None,
                         test_type: Optional[str] = None,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         limit: int = 100,
                         offset: int = 0) -> List[EvaluationResult]:
        """Get evaluation results with optional filtering"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            query = "SELECT * FROM evaluation_results WHERE 1=1"
            params = []
            
            if model_provider:
                query += " AND model_provider = ?"
                params.append(model_provider)
            
            if model_name:
                query += " AND model_name = ?"
                params.append(model_name)
            
            if test_type:
                query += " AND test_type = ?"
                params.append(test_type)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
            return [self._row_to_result(row) for row in rows]
    
    async def get_summary(self,
                         model_provider: Optional[str] = None,
                         model_name: Optional[str] = None,
                         test_type: Optional[str] = None,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None) -> EvaluationSummary:
        """Get evaluation summary statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            query = '''
                SELECT 
                    COUNT(*) as total_evaluations,
                    SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passed_evaluations,
                    SUM(CASE WHEN passed = 0 AND error_message IS NULL THEN 1 ELSE 0 END) as failed_evaluations,
                    SUM(CASE WHEN error_message IS NOT NULL THEN 1 ELSE 0 END) as error_evaluations,
                    AVG(score) as average_score,
                    AVG(execution_time) as average_execution_time
                FROM evaluation_results WHERE 1=1
            '''
            params = []
            
            if model_provider:
                query += " AND model_provider = ?"
                params.append(model_provider)
            
            if model_name:
                query += " AND model_name = ?"
                params.append(model_name)
            
            if test_type:
                query += " AND test_type = ?"
                params.append(test_type)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            cursor = await db.execute(query, params)
            row = await cursor.fetchone()
            
            summary = EvaluationSummary(
                total_evaluations=row[0] or 0,
                passed_evaluations=row[1] or 0,
                failed_evaluations=row[2] or 0,
                error_evaluations=row[3] or 0,
                average_score=row[4] or 0.0,
                average_execution_time=row[5] or 0.0
            )
            
            if summary.total_evaluations > 0:
                summary.success_rate = summary.passed_evaluations / summary.total_evaluations
            
            # Get unique models and test types
            models_query = '''
                SELECT DISTINCT model_provider || '/' || model_name as model
                FROM evaluation_results WHERE 1=1
            '''
            types_query = '''
                SELECT DISTINCT test_type
                FROM evaluation_results WHERE 1=1
            '''
            
            if model_provider:
                models_query += " AND model_provider = ?"
                types_query += " AND model_provider = ?"
            
            if model_name:
                models_query += " AND model_name = ?"
                types_query += " AND model_name = ?"
            
            if test_type:
                models_query += " AND test_type = ?"
                types_query += " AND test_type = ?"
            
            if start_time:
                models_query += " AND timestamp >= ?"
                types_query += " AND timestamp >= ?"
            
            if end_time:
                models_query += " AND timestamp <= ?"
                types_query += " AND timestamp <= ?"
            
            cursor = await db.execute(models_query, params)
            models = await cursor.fetchall()
            summary.models_tested = [row[0] for row in models]
            
            cursor = await db.execute(types_query, params)
            types = await cursor.fetchall()
            summary.test_types = [row[0] for row in types]
            
            return summary
    
    async def compare_models(self, model_names: List[str], test_type: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Compare performance between multiple models"""
        comparison = {}
        
        for model_name in model_names:
            # Split model_name if it contains provider
            if '/' in model_name:
                provider, name = model_name.split('/', 1)
                summary = await self.get_summary(model_provider=provider, model_name=name, test_type=test_type)
            else:
                summary = await self.get_summary(model_name=model_name, test_type=test_type)
            
            comparison[model_name] = {
                'total_evaluations': summary.total_evaluations,
                'success_rate': summary.success_rate,
                'average_score': summary.average_score,
                'average_execution_time': summary.average_execution_time
            }
        
        return comparison
    
    async def get_recent_results(self, limit: int = 50) -> List[EvaluationResult]:
        """Get most recent evaluation results"""
        return await self.get_results(limit=limit, offset=0)
    
    async def delete_old_results(self, older_than_days: int = 30) -> int:
        """Delete results older than specified days"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                DELETE FROM evaluation_results 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(older_than_days))
            await db.commit()
            return cursor.rowcount
    
    def _row_to_result(self, row) -> EvaluationResult:
        """Convert database row to EvaluationResult"""
        return EvaluationResult(
            id=row['id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            model_provider=row['model_provider'],
            model_name=row['model_name'],
            test_name=row['test_name'],
            test_type=row['test_type'],
            query=row['query'],
            response=row['response'],
            expected_response=row['expected_response'],
            metrics=json.loads(row['metrics']) if row['metrics'] else {},
            score=row['score'],
            passed=bool(row['passed']),
            execution_time=row['execution_time'],
            error_message=row['error_message'],
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise


# Global database manager instance
_db_manager = None


async def get_database_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.initialize()
    return _db_manager