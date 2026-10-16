"""
Performance tests for LLM evaluation.
Tests response time, consistency, and resource usage.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from src.features.llm_evaluation.test_framework.base_test import BaseTest, TestResult, TestStatus


class ResponseTimeTest(BaseTest):
    """Test response time performance."""
    
    async def run(self, client: Any, model: str, **kwargs) -> TestResult:
        """Run response time test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        iterations = self.config.get('iterations', 3)
        
        # Run multiple iterations
        response_times = []
        responses = []
        
        for i in range(iterations):
            start_time = time.time()
            response = await self._get_response(client, prompt, system_prompt, model)
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            responses.append(response)
        
        # Calculate statistics
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        
        # Validate and score
        is_valid = all(self.validate_result(r) for r in responses)
        score = self.calculate_score(avg_time, responses)
        
        status = TestStatus.PASSED if is_valid and score > 0.6 else TestStatus.FAILED
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=score,
            details={
                'prompt': prompt,
                'model': model,
                'iterations': iterations,
                'response_times': response_times,
                'avg_response_time': avg_time,
                'min_response_time': min_time,
                'max_response_time': max_time,
                'time_variance': max_time - min_time,
                'responses': responses[:2]  # Only store first 2 responses
            }
        )
    
    def validate_result(self, result: str) -> bool:
        """Validate response time result."""
        if not result or not isinstance(result, str):
            return False
        
        # Check minimum length
        min_length = self.config.get('min_length', 10)
        if len(result.strip()) < min_length:
            return False
        
        return True
    
    def calculate_score(self, avg_time: float, responses: List[str]) -> float:
        """Calculate performance score based on response time."""
        score = 0.0
        
        # Time score (70%)
        target_time = self.config.get('target_time', 5.0)  # 5 seconds
        if avg_time <= target_time:
            time_score = 1.0
        else:
            # Penalize slower responses
            time_score = max(0.0, 1.0 - (avg_time - target_time) / target_time)
        
        score += time_score * 0.7
        
        # Quality score (30%)
        valid_responses = sum(1 for r in responses if self.validate_result(r))
        quality_score = valid_responses / len(responses) if responses else 0
        score += quality_score * 0.3
        
        return min(score, 1.0)
    
    async def _get_response(self, client: Any, prompt: str, system_prompt: str, model: str) -> str:
        """Get response from different client types."""
        try:
            if hasattr(client, 'generate'):
                # Ollama client
                response = await client.generate(
                    model=model,
                    prompt=prompt,
                    system_prompt=system_prompt
                )
                return response.get('response', '') if response else ''
            
            elif hasattr(client, 'run_prompt'):
                # LLM CLI client
                response = await client.run_prompt(
                    prompt=prompt,
                    model=model,
                    system_prompt=system_prompt
                )
                return response.get('response', '') if response else ''
            
            else:
                # PydanticAI agent
                from src.features.llm_evaluation.llm_service import run_query
                response = await run_query(client, prompt)
                return str(response) if response else ''
                
        except Exception as e:
            print(f"Error getting response: {e}")
            return ''


class ConsistencyTest(BaseTest):
    """Test response consistency across multiple runs."""
    
    async def run(self, client: Any, model: str, **kwargs) -> TestResult:
        """Run consistency test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        iterations = self.config.get('iterations', 5)
        
        # Run multiple iterations
        responses = []
        for i in range(iterations):
            response = await self._get_response(client, prompt, system_prompt, model)
            responses.append(response)
        
        # Calculate consistency metrics
        consistency_score = self._calculate_consistency_score(responses)
        avg_length = sum(len(r) for r in responses) / len(responses)
        length_variance = self._calculate_length_variance(responses)
        
        # Validate and score
        is_valid = all(self.validate_result(r) for r in responses)
        score = self.calculate_score(consistency_score, responses)
        
        status = TestStatus.PASSED if is_valid and score > 0.6 else TestStatus.FAILED
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=score,
            details={
                'prompt': prompt,
                'model': model,
                'iterations': iterations,
                'consistency_score': consistency_score,
                'avg_length': avg_length,
                'length_variance': length_variance,
                'responses': responses[:3]  # Only store first 3 responses
            }
        )
    
    def _calculate_consistency_score(self, responses: List[str]) -> float:
        """Calculate consistency score between responses."""
        if len(responses) < 2:
            return 1.0
        
        # Simple word overlap consistency
        all_words = []
        for response in responses:
            words = set(response.lower().split())
            all_words.append(words)
        
        # Calculate pairwise similarity
        similarities = []
        for i in range(len(all_words)):
            for j in range(i + 1, len(all_words)):
                overlap = len(all_words[i] & all_words[j])
                union = len(all_words[i] | all_words[j])
                similarity = overlap / union if union > 0 else 0
                similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _calculate_length_variance(self, responses: List[str]) -> float:
        """Calculate length variance between responses."""
        if len(responses) < 2:
            return 0.0
        
        lengths = [len(r) for r in responses]
        avg_length = sum(lengths) / len(lengths)
        variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
        
        return variance ** 0.5  # Standard deviation
    
    def validate_result(self, result: str) -> bool:
        """Validate consistency result."""
        if not result or not isinstance(result, str):
            return False
        
        # Check minimum length
        min_length = self.config.get('min_length', 10)
        if len(result.strip()) < min_length:
            return False
        
        return True
    
    def calculate_score(self, consistency_score: float, responses: List[str]) -> float:
        """Calculate consistency test score."""
        score = 0.0
        
        # Consistency score (60%)
        score += consistency_score * 0.6
        
        # Quality score (40%)
        valid_responses = sum(1 for r in responses if self.validate_result(r))
        quality_score = valid_responses / len(responses) if responses else 0
        score += quality_score * 0.4
        
        return min(score, 1.0)
    
    async def _get_response(self, client: Any, prompt: str, system_prompt: str, model: str) -> str:
        """Get response from different client types."""
        try:
            if hasattr(client, 'generate'):
                # Ollama client
                response = await client.generate(
                    model=model,
                    prompt=prompt,
                    system_prompt=system_prompt
                )
                return response.get('response', '') if response else ''
            
            elif hasattr(client, 'run_prompt'):
                # LLM CLI client
                response = await client.run_prompt(
                    prompt=prompt,
                    model=model,
                    system_prompt=system_prompt
                )
                return response.get('response', '') if response else ''
            
            else:
                # PydanticAI agent
                from src.features.llm_evaluation.llm_service import run_query
                response = await run_query(client, prompt)
                return str(response) if response else ''
                
        except Exception as e:
            print(f"Error getting response: {e}")
            return ''


class ConcurrentPerformanceTest(BaseTest):
    """Test performance under concurrent load."""
    
    async def run(self, client: Any, model: str, **kwargs) -> TestResult:
        """Run concurrent performance test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        concurrent_requests = self.config.get('concurrent_requests', 3)
        
        # Create concurrent tasks
        tasks = []
        start_time = time.time()
        
        for i in range(concurrent_requests):
            task = asyncio.create_task(
                self._get_response(client, prompt, system_prompt, model)
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Process results
        successful_responses = []
        errors = []
        
        for response in responses:
            if isinstance(response, Exception):
                errors.append(str(response))
            else:
                successful_responses.append(response)
        
        total_time = end_time - start_time
        success_rate = len(successful_responses) / len(responses)
        
        # Validate and score
        is_valid = len(successful_responses) > 0
        score = self.calculate_score(success_rate, total_time, successful_responses)
        
        status = TestStatus.PASSED if is_valid and score > 0.6 else TestStatus.FAILED
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=score,
            details={
                'prompt': prompt,
                'model': model,
                'concurrent_requests': concurrent_requests,
                'total_time': total_time,
                'success_rate': success_rate,
                'successful_responses': len(successful_responses),
                'errors': errors,
                'responses': successful_responses[:2]  # Only store first 2 responses
            }
        )
    
    def calculate_score(self, success_rate: float, total_time: float, responses: List[str]) -> float:
        """Calculate concurrent performance score."""
        score = 0.0
        
        # Success rate (50%)
        score += success_rate * 0.5
        
        # Time performance (30%)
        target_time = self.config.get('target_time', 10.0)
        if total_time <= target_time:
            time_score = 1.0
        else:
            time_score = max(0.0, 1.0 - (total_time - target_time) / target_time)
        score += time_score * 0.3
        
        # Quality score (20%)
        valid_responses = sum(1 for r in responses if self.validate_result(r))
        quality_score = valid_responses / len(responses) if responses else 0
        score += quality_score * 0.2
        
        return min(score, 1.0)
    
    def validate_result(self, result: str) -> bool:
        """Validate concurrent performance result."""
        if not result or not isinstance(result, str):
            return False
        
        # Check minimum length
        min_length = self.config.get('min_length', 10)
        if len(result.strip()) < min_length:
            return False
        
        return True
    
    async def _get_response(self, client: Any, prompt: str, system_prompt: str, model: str) -> str:
        """Get response from different client types."""
        try:
            if hasattr(client, 'generate'):
                # Ollama client
                response = await client.generate(
                    model=model,
                    prompt=prompt,
                    system_prompt=system_prompt
                )
                return response.get('response', '') if response else ''
            
            elif hasattr(client, 'run_prompt'):
                # LLM CLI client
                response = await client.run_prompt(
                    prompt=prompt,
                    model=model,
                    system_prompt=system_prompt
                )
                return response.get('response', '') if response else ''
            
            else:
                # PydanticAI agent
                from src.features.llm_evaluation.llm_service import run_query
                response = await run_query(client, prompt)
                return str(response) if response else ''
                
        except Exception as e:
            print(f"Error getting response: {e}")
            return ''


class PerformanceTests:
    """Collection of performance tests."""
    
    @staticmethod
    def get_response_time_test() -> ResponseTimeTest:
        """Get response time test."""
        config = {
            'prompt': 'Write a short paragraph about the benefits of renewable energy.',
            'system_prompt': 'You are a helpful assistant.',
            'iterations': 3,
            'target_time': 5.0,
            'min_length': 50
        }
        return ResponseTimeTest(
            name='response_time_renewable_energy',
            description='Response time test with renewable energy topic',
            config=config
        )
    
    @staticmethod
    def get_consistency_test() -> ConsistencyTest:
        """Get consistency test."""
        config = {
            'prompt': 'Explain the concept of machine learning in simple terms.',
            'system_prompt': 'You are an educational assistant.',
            'iterations': 5,
            'min_length': 30
        }
        return ConsistencyTest(
            name='consistency_machine_learning',
            description='Consistency test with machine learning explanation',
            config=config
        )
    
    @staticmethod
    def get_concurrent_performance_test() -> ConcurrentPerformanceTest:
        """Get concurrent performance test."""
        config = {
            'prompt': 'What are the main advantages of cloud computing?',
            'system_prompt': 'You are a technology expert.',
            'concurrent_requests': 3,
            'target_time': 10.0,
            'min_length': 40
        }
        return ConcurrentPerformanceTest(
            name='concurrent_cloud_computing',
            description='Concurrent performance test with cloud computing topic',
            config=config
        )
    
    @staticmethod
    def get_stress_test() -> ResponseTimeTest:
        """Get stress test with longer prompt."""
        config = {
            'prompt': 'Analyze the following complex scenario: A company is planning to migrate their legacy system to a modern cloud-based architecture. They need to consider security, scalability, cost, and minimal downtime. Provide a detailed analysis with recommendations.',
            'system_prompt': 'You are a senior technical consultant.',
            'iterations': 2,
            'target_time': 15.0,
            'min_length': 200
        }
        return ResponseTimeTest(
            name='stress_test_complex_scenario',
            description='Stress test with complex migration scenario',
            config=config
        )
    
    @staticmethod
    def get_all_tests() -> List[BaseTest]:
        """Get all performance tests."""
        return [
            PerformanceTests.get_response_time_test(),
            PerformanceTests.get_consistency_test(),
            PerformanceTests.get_concurrent_performance_test(),
            PerformanceTests.get_stress_test()
        ]