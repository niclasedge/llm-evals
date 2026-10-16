#!/usr/bin/env python3
"""
Integration test for the modular LLM evaluation system.
Tests core components without external dependencies.
"""

import asyncio
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Import modules to test
from src.core.config_manager import ConfigManager, LLMEvaluationConfig
from src.core.database import DatabaseManager, EvaluationResult
from src.core.monitoring import EvaluationMonitor
from src.features.evaluation_metrics import MetricsManager, RelevanceMetric, AccuracyMetric
from src.features.benchmarks import DatasetManager


async def test_config_manager():
    """Test configuration management."""
    print("🔧 Testing ConfigManager...")
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config_content = """
evaluation:
  enable_ollama: false
  enable_openrouter: true
  ollama_models: ['llama3']
  openrouter_models: ['meta-llama/llama-3.3-8b-instruct:free']

metrics:
  enabled_metrics: ['relevance', 'accuracy']
  accuracy_threshold: 0.7

dashboard:
  enabled: true
  port: 8080

database:
  database_type: 'sqlite'
  database_path: 'test_results.db'
"""
        f.write(config_content)
        temp_config_path = f.name
    
    try:
        # Test config loading
        config_manager = ConfigManager(temp_config_path)
        config = config_manager.get_config()
        
        assert isinstance(config, LLMEvaluationConfig)
        assert config.evaluation.enable_ollama is False
        assert config.evaluation.enable_openrouter is True
        assert config.metrics.accuracy_threshold == 0.7
        assert config.dashboard.port == 8080
        
        # Test validation (should fail due to missing API key)
        is_valid = config_manager.validate_config()
        # We expect this to fail due to missing OpenRouter API key
        # Let's disable OpenRouter for this test
        config.evaluation.enable_openrouter = False
        is_valid = config_manager.validate_config()
        assert is_valid is True  # Should be valid when OpenRouter is disabled
        
        print("  ✅ ConfigManager tests passed!")
        return True
        
    finally:
        # Cleanup
        Path(temp_config_path).unlink(missing_ok=True)


async def test_database_manager():
    """Test database management."""
    print("💾 Testing DatabaseManager...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db_path = f.name
    
    try:
        db_manager = DatabaseManager(temp_db_path)
        await db_manager.initialize()
        
        # Test saving a result
        result = EvaluationResult(
            model_provider="test_provider",
            model_name="test_model",
            test_name="test_evaluation",
            test_type="integration_test",
            query="Test query",
            response="Test response",
            score=0.85,
            passed=True,
            execution_time=1.5,
            metadata={"test": True}
        )
        
        result_id = await db_manager.save_result(result)
        assert result_id is not None
        
        # Test retrieving the result
        retrieved_result = await db_manager.get_result(result_id)
        assert retrieved_result is not None
        assert retrieved_result.model_provider == "test_provider"
        assert retrieved_result.score == 0.85
        
        # Test getting summary
        summary = await db_manager.get_summary()
        assert summary.total_evaluations == 1
        assert summary.passed_evaluations == 1
        assert summary.success_rate == 1.0
        
        print("  ✅ DatabaseManager tests passed!")
        return True
        
    finally:
        # Cleanup
        Path(temp_db_path).unlink(missing_ok=True)


def test_monitoring():
    """Test monitoring system."""
    print("📊 Testing EvaluationMonitor...")
    
    # Create temporary log file
    with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as f:
        temp_log_path = f.name
    
    try:
        monitor = EvaluationMonitor(temp_log_path)
        
        # Test session management
        session_id = "test_session"
        config = {"test_config": True}
        
        monitor.start_session(session_id, config)
        
        # Test evaluation logging
        monitor.log_evaluation_start("test_provider", "test_model", "test_evaluation")
        monitor.log_evaluation_end("test_provider", "test_model", "test_evaluation", 1.5, True)
        
        # Test metrics
        metrics = monitor.get_performance_metrics()
        assert metrics.requests_count == 1
        assert metrics.errors_count == 0
        
        monitor.end_session(session_id)
        
        print("  ✅ EvaluationMonitor tests passed!")
        return True
        
    finally:
        # Cleanup
        Path(temp_log_path).unlink(missing_ok=True)


async def test_metrics_manager():
    """Test metrics management."""
    print("📏 Testing MetricsManager...")
    
    metrics_manager = MetricsManager()
    
    # Test metric registration
    all_metrics = metrics_manager.get_all_metrics()
    assert len(all_metrics) > 0
    assert 'relevance' in all_metrics
    assert 'accuracy' in all_metrics
    
    # Test individual metric evaluation
    query = "What is the capital of France?"
    response = "The capital of France is Paris."
    ground_truth = "Paris"
    
    relevance_result = await metrics_manager.evaluate_single('relevance', query, response)
    assert relevance_result is not None
    assert 0 <= relevance_result.score <= 1
    
    # Test batch evaluation
    results = await metrics_manager.evaluate_all(query, response, ground_truth)
    assert len(results) > 0
    assert 'relevance' in results
    
    # Test composite score calculation
    composite_score = metrics_manager.calculate_composite_score(results)
    assert 0 <= composite_score <= 1
    
    print("  ✅ MetricsManager tests passed!")
    return True


async def test_dataset_manager():
    """Test dataset management."""
    print("📚 Testing DatasetManager...")
    
    # Create temporary datasets directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        dataset_manager = DatasetManager(temp_dir)
        await dataset_manager.initialize()
        
        # Test dataset creation
        test_data = [
            {"id": "1", "query": "Test query 1", "expected_response": "Test response 1"},
            {"id": "2", "query": "Test query 2", "expected_response": "Test response 2"}
        ]
        
        created = await dataset_manager.create_dataset("test_dataset", test_data, "Test dataset")
        assert created is True
        
        # Test dataset loading
        loaded_data = await dataset_manager.load_dataset("test_dataset")
        assert loaded_data is not None
        assert len(loaded_data) == 2
        assert loaded_data[0]["query"] == "Test query 1"
        
        # Test dataset listing
        datasets = dataset_manager.list_datasets()
        assert len(datasets) > 0
        
        # Test dataset validation
        validation = await dataset_manager.validate_dataset("test_dataset")
        assert validation["valid"] is True
        assert validation["size"] == 2
        
        print("  ✅ DatasetManager tests passed!")
        return True
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


async def test_metrics_implementation():
    """Test individual metric implementations."""
    print("🎯 Testing Metric Implementations...")
    
    # Test data
    query = "What is the capital of France?"
    good_response = "The capital of France is Paris."
    bad_response = "I don't know about geography."
    ground_truth = "Paris"
    
    # Test RelevanceMetric
    relevance_metric = RelevanceMetric()
    relevance_result = await relevance_metric.evaluate(query, good_response)
    assert relevance_result is not None
    assert hasattr(relevance_result, 'score')
    assert 0 <= relevance_result.score <= 1  # Should be between 0 and 1
    
    bad_relevance_result = await relevance_metric.evaluate(query, bad_response)
    assert bad_relevance_result is not None
    assert hasattr(bad_relevance_result, 'score')
    assert 0 <= bad_relevance_result.score <= 1
    
    # Test AccuracyMetric
    accuracy_metric = AccuracyMetric()
    accuracy_result = await accuracy_metric.evaluate(query, good_response, ground_truth)
    assert accuracy_result is not None
    assert hasattr(accuracy_result, 'score')
    assert 0 <= accuracy_result.score <= 1
    
    print("  ✅ Metric implementations tests passed!")
    return True


async def run_integration_tests():
    """Run all integration tests."""
    print("🚀 Running Integration Tests for Modular LLM Evaluation System")
    print("=" * 70)
    
    tests = [
        test_config_manager,
        test_database_manager,
        test_monitoring,
        test_metrics_manager,
        test_dataset_manager,
        test_metrics_implementation,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            
            if result:
                passed += 1
            else:
                failed += 1
                print(f"  ❌ {test.__name__} failed!")
                
        except Exception as e:
            failed += 1
            print(f"  ❌ {test.__name__} failed with error: {e}")
    
    print("\n" + "=" * 70)
    print(f"Integration Tests Summary:")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📊 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All integration tests PASSED!")
        return True
    else:
        print(f"\n💥 {failed} integration tests FAILED!")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_integration_tests())
    sys.exit(0 if success else 1)