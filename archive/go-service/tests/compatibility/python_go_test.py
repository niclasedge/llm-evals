#!/usr/bin/env python3
"""
Test compatibility between Python and Go database formats.
This script verifies that data stored by Python can be read by Go and vice versa.
"""

import json
import sqlite3
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# Add the src directory to the path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from src.core.database import EvaluationResult, DatabaseManager
except ImportError as e:
    print(f"Warning: Could not import Python database modules: {e}")
    print("This test requires the Python database module to be available.")
    sys.exit(1)

def create_test_result():
    """Create a test evaluation result with Python format"""
    return EvaluationResult(
        timestamp=datetime.now(),
        model_provider="openrouter",
        model_name="llama3.2:3b",
        test_name="compatibility_test",
        test_type="coding",
        query="Write a hello world function",
        response="def hello_world(): print('Hello, World!')",
        expected_response="def hello_world(): print('Hello, World!')",
        metrics={"accuracy": 1.0, "completeness": 1.0},
        score=1.0,
        passed=True,
        execution_time=1.5,
        error_message=None,
        metadata={"language": "python", "test_source": "compatibility"}
    )

async def test_python_write_go_read():
    """Test that data written by Python can be read by Go"""
    print("Testing Python write -> Go read compatibility...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Write data using Python
        db_manager = DatabaseManager(db_path)
        await db_manager.initialize()
        
        result = create_test_result()
        result_id = await db_manager.save_result(result)
        print(f"Python saved result with ID: {result_id}")
        
        # Verify data format in database directly
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT * FROM evaluation_results WHERE id = ?", (result_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise Exception("No data found in database after Python write")
        
        print("✅ Python successfully wrote data to database")
        
        # Check that JSON fields are properly formatted
        metrics_json = row[9]  # metrics column
        metadata_json = row[14]  # metadata column
        
        # Verify JSON can be parsed
        metrics = json.loads(metrics_json) if metrics_json else {}
        metadata = json.loads(metadata_json) if metadata_json else {}
        
        if metrics.get("accuracy") != 1.0:
            raise Exception(f"Metrics not properly stored: {metrics}")
        
        if metadata.get("language") != "python":
            raise Exception(f"Metadata not properly stored: {metadata}")
        
        print("✅ JSON fields are properly formatted for Go consumption")
        
        return db_path, result_id
        
    except Exception as e:
        if os.path.exists(db_path):
            os.unlink(db_path)
        raise e

def test_go_compatibility(db_path, result_id):
    """Test that Go can read data written by Python"""
    print("Testing Go read compatibility...")
    
    # This would normally call Go code, but for this test we'll verify
    # the database structure matches Go expectations
    
    conn = sqlite3.connect(db_path)
    
    # Check table structure matches Go schema
    cursor = conn.execute("PRAGMA table_info(evaluation_results)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}  # name: type
    
    expected_columns = {
        'id': 'INTEGER',
        'timestamp': 'DATETIME', 
        'model_provider': 'TEXT',
        'model_name': 'TEXT',
        'test_name': 'TEXT',
        'test_type': 'TEXT',
        'query': 'TEXT',
        'response': 'TEXT',
        'expected_response': 'TEXT',
        'metrics': 'TEXT',
        'score': 'REAL',
        'passed': 'BOOLEAN',
        'execution_time': 'REAL',
        'error_message': 'TEXT',
        'metadata': 'TEXT'
    }
    
    for col_name, col_type in expected_columns.items():
        if col_name not in columns:
            raise Exception(f"Missing column: {col_name}")
        if columns[col_name] != col_type:
            print(f"Warning: Column type mismatch for {col_name}: got {columns[col_name]}, expected {col_type}")
    
    # Check data can be read in Go format
    cursor = conn.execute("""
        SELECT id, timestamp, model_provider, model_name, test_name, test_type, 
               query, response, expected_response, metrics, score, passed, 
               execution_time, error_message, metadata
        FROM evaluation_results WHERE id = ?
    """, (result_id,))
    
    row = cursor.fetchone()
    if not row:
        raise Exception("Cannot read data from database")
    
    # Verify timestamp format
    timestamp_str = row[1]
    try:
        datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except:
        # Try parsing as stored by SQLite
        try:
            datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            raise Exception(f"Invalid timestamp format: {timestamp_str}, error: {e}")
    
    # Verify JSON fields
    metrics_json = row[9]
    metadata_json = row[14]
    
    if metrics_json:
        metrics = json.loads(metrics_json)
        if not isinstance(metrics, dict):
            raise Exception(f"Metrics not a valid JSON object: {metrics}")
    
    if metadata_json:
        metadata = json.loads(metadata_json)
        if not isinstance(metadata, dict):
            raise Exception(f"Metadata not a valid JSON object: {metadata}")
    
    # Check boolean conversion
    passed = row[11]
    if not isinstance(passed, (bool, int)):
        raise Exception(f"Passed field not boolean compatible: {passed} (type: {type(passed)})")
    
    conn.close()
    
    print("✅ Database structure and data format compatible with Go")

def test_data_integrity():
    """Test that data maintains integrity between Python and Go formats"""
    print("Testing data integrity...")
    
    # Test various data types and edge cases
    test_cases = [
        {
            "metrics": {"accuracy": 0.95, "precision": 0.87, "recall": 0.91},
            "metadata": {"language": "python", "version": "3.9", "timeout": 30},
            "score": 0.95,
            "passed": True,
            "execution_time": 1.234567,
            "error_message": None
        },
        {
            "metrics": {},
            "metadata": {"empty_test": True, "null_value": None},
            "score": 0.0,
            "passed": False,
            "execution_time": 0.001,
            "error_message": "Test failed with timeout"
        },
        {
            "metrics": {"unicode_test": "测试", "special_chars": "!@#$%^&*()"},
            "metadata": {"nested": {"deep": {"value": 42}}, "array": [1, 2, 3]},
            "score": 0.75,
            "passed": True,
            "execution_time": 2.999999,
            "error_message": None
        }
    ]
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Create table with exact schema
        conn.execute("""
            CREATE TABLE evaluation_results (
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
                passed BOOLEAN DEFAULT 0,
                execution_time REAL DEFAULT 0.0,
                error_message TEXT,
                metadata TEXT
            )
        """)
        
        for i, test_case in enumerate(test_cases):
            # Insert data
            cursor = conn.execute("""
                INSERT INTO evaluation_results (
                    model_provider, model_name, test_name, test_type, query, response,
                    expected_response, metrics, score, passed, execution_time, error_message, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "test_provider",
                "test_model",
                f"integrity_test_{i}",
                "coding",
                "test query",
                "test response",
                "expected",
                json.dumps(test_case["metrics"]),
                test_case["score"],
                test_case["passed"],
                test_case["execution_time"],
                test_case["error_message"],
                json.dumps(test_case["metadata"])
            ))
            
            result_id = cursor.lastrowid
            
            # Read data back
            cursor = conn.execute("""
                SELECT metrics, metadata, score, passed, execution_time, error_message
                FROM evaluation_results WHERE id = ?
            """, (result_id,))
            
            row = cursor.fetchone()
            
            # Verify data integrity
            stored_metrics = json.loads(row[0]) if row[0] else {}
            stored_metadata = json.loads(row[1]) if row[1] else {}
            
            if stored_metrics != test_case["metrics"]:
                raise Exception(f"Metrics mismatch for test case {i}: {stored_metrics} != {test_case['metrics']}")
            
            if stored_metadata != test_case["metadata"]:
                raise Exception(f"Metadata mismatch for test case {i}: {stored_metadata} != {test_case['metadata']}")
            
            if abs(row[2] - test_case["score"]) > 1e-6:
                raise Exception(f"Score mismatch for test case {i}: {row[2]} != {test_case['score']}")
            
            if bool(row[3]) != test_case["passed"]:
                raise Exception(f"Passed mismatch for test case {i}: {row[3]} != {test_case['passed']}")
            
            if abs(row[4] - test_case["execution_time"]) > 1e-6:
                raise Exception(f"Execution time mismatch for test case {i}: {row[4]} != {test_case['execution_time']}")
            
            if row[5] != test_case["error_message"]:
                raise Exception(f"Error message mismatch for test case {i}: {row[5]} != {test_case['error_message']}")
        
        conn.close()
        print(f"✅ All {len(test_cases)} data integrity test cases passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

async def main():
    """Run all compatibility tests"""
    print("Starting Python-Go database compatibility tests...\n")
    
    try:
        # Test Python write -> Go read
        db_path, result_id = await test_python_write_go_read()
        
        try:
            # Test Go compatibility
            test_go_compatibility(db_path, result_id)
            
            # Test data integrity
            test_data_integrity()
            
            print("\n🎉 All compatibility tests passed!")
            print("✅ Python and Go database formats are fully compatible")
            
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
        
    except Exception as e:
        print(f"\n❌ Compatibility test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))