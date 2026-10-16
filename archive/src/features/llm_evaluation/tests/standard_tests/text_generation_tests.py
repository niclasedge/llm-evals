"""
Text generation tests for LLM evaluation.
Based on Simon Willison's LLM CLI patterns and standardized evaluation criteria.
"""

import re
from typing import Dict, Any, List
from src.features.llm_evaluation.test_framework.base_test import BaseTest, TestResult, TestStatus


class CreativeWritingTest(BaseTest):
    """Test creative writing capabilities."""
    
    async def run(self, client: Any, model: str, **kwargs) -> TestResult:
        """Run creative writing test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        
        # Get response from client
        response = await self._get_response(client, prompt, system_prompt, model)
        
        if not response:
            return TestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No response from model"
            )
        
        # Validate and score
        is_valid = self.validate_result(response)
        score = self.calculate_score(response)
        
        status = TestStatus.PASSED if is_valid and score > 0.6 else TestStatus.FAILED
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=score,
            details={
                'prompt': prompt,
                'response': response,
                'response_length': len(response),
                'model': model,
                'creativity_score': self._calculate_creativity_score(response),
                'coherence_score': self._calculate_coherence_score(response)
            }
        )
    
    def _calculate_creativity_score(self, text: str) -> float:
        """Calculate creativity score based on vocabulary diversity and uniqueness."""
        if not text:
            return 0.0
        
        words = text.lower().split()
        unique_words = len(set(words))
        total_words = len(words)
        
        # Vocabulary diversity
        diversity = unique_words / total_words if total_words > 0 else 0
        
        # Check for creative elements (metaphors, unusual word combinations)
        creative_patterns = [
            r'like\s+a\s+\w+',  # similes
            r'as\s+\w+\s+as',   # comparisons
            r'\w+ly\s+\w+',     # adverb-adjective combinations
        ]
        
        creative_elements = 0
        for pattern in creative_patterns:
            creative_elements += len(re.findall(pattern, text, re.IGNORECASE))
        
        creativity_bonus = min(creative_elements / 10, 0.3)  # Up to 30% bonus
        
        return min(diversity + creativity_bonus, 1.0)
    
    def _calculate_coherence_score(self, text: str) -> float:
        """Calculate coherence score based on sentence structure and flow."""
        if not text:
            return 0.0
        
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) < 2:
            return 0.5
        
        # Check for proper sentence structure
        proper_sentences = 0
        for sentence in sentences:
            if len(sentence.split()) >= 3:  # At least 3 words
                proper_sentences += 1
        
        structure_score = proper_sentences / len(sentences)
        
        # Check for transition words
        transition_words = ['however', 'therefore', 'meanwhile', 'furthermore', 'additionally']
        transitions = sum(1 for word in transition_words if word in text.lower())
        transition_score = min(transitions / 5, 0.3)
        
        return min(structure_score + transition_score, 1.0)
    
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


class SummarizationTest(BaseTest):
    """Test text summarization capabilities."""
    
    async def run(self, client: Any, model: str, **kwargs) -> TestResult:
        """Run summarization test."""
        # Get the text to summarize from config
        source_text = self.config.get('source_text', '')
        if not source_text:
            return TestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No source text provided for summarization"
            )
        
        prompt = f"Summarize the following text in 2-3 sentences:\n\n{source_text}"
        system_prompt = self.get_system_prompt()
        
        # Get response from client
        response = await self._get_response(client, prompt, system_prompt, model)
        
        if not response:
            return TestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No response from model"
            )
        
        # Validate and score
        is_valid = self.validate_result(response, source_text)
        score = self.calculate_score(response, source_text)
        
        status = TestStatus.PASSED if is_valid and score > 0.6 else TestStatus.FAILED
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=score,
            details={
                'prompt': prompt,
                'response': response,
                'source_length': len(source_text),
                'summary_length': len(response),
                'compression_ratio': len(response) / len(source_text) if source_text else 0,
                'model': model
            }
        )
    
    def validate_result(self, result: str, source_text: str = '') -> bool:
        """Validate summarization result."""
        if not result or not isinstance(result, str):
            return False
        
        # Check if summary is significantly shorter than source
        if len(result) >= len(source_text) * 0.8:
            return False
        
        # Check minimum length
        if len(result.strip()) < 50:
            return False
        
        # Check if it's not just the first sentences
        source_start = source_text[:len(result)]
        if result.strip().lower() == source_start.strip().lower():
            return False
        
        return True
    
    def calculate_score(self, result: str, source_text: str = '') -> float:
        """Calculate summarization score."""
        if not self.validate_result(result, source_text):
            return 0.0
        
        # Compression ratio score
        compression_ratio = len(result) / len(source_text) if source_text else 0
        ideal_ratio = 0.2  # 20% of original length
        ratio_score = 1.0 - abs(compression_ratio - ideal_ratio) / ideal_ratio
        ratio_score = max(0, min(1.0, ratio_score))
        
        # Content preservation score (simple overlap check)
        source_words = set(source_text.lower().split())
        result_words = set(result.lower().split())
        overlap = len(source_words & result_words)
        preservation_score = min(overlap / 20, 1.0)  # Up to 20 key words
        
        return (ratio_score + preservation_score) / 2
    
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


class QuestionAnsweringTest(BaseTest):
    """Test question answering capabilities."""
    
    async def run(self, client: Any, model: str, **kwargs) -> TestResult:
        """Run question answering test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        expected_answer = self.get_expected_result()
        
        # Get response from client
        response = await self._get_response(client, prompt, system_prompt, model)
        
        if not response:
            return TestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No response from model"
            )
        
        # Validate and score
        is_valid = self.validate_result(response)
        score = self.calculate_score(response, expected_answer)
        
        status = TestStatus.PASSED if is_valid and score > 0.7 else TestStatus.FAILED
        
        return TestResult(
            test_name=self.name,
            status=status,
            score=score,
            details={
                'prompt': prompt,
                'response': response,
                'expected_answer': expected_answer,
                'model': model,
                'accuracy_score': self._calculate_accuracy_score(response, expected_answer),
                'completeness_score': self._calculate_completeness_score(response)
            }
        )
    
    def _calculate_accuracy_score(self, response: str, expected: str) -> float:
        """Calculate accuracy score based on expected answer."""
        if not expected:
            return 0.8  # Default score if no expected answer
        
        # Simple keyword matching
        expected_keywords = set(expected.lower().split())
        response_keywords = set(response.lower().split())
        
        matches = len(expected_keywords & response_keywords)
        return min(matches / len(expected_keywords), 1.0) if expected_keywords else 0.0
    
    def _calculate_completeness_score(self, response: str) -> float:
        """Calculate completeness score based on response structure."""
        if not response:
            return 0.0
        
        # Check for complete sentences
        sentences = re.split(r'[.!?]+', response)
        complete_sentences = [s for s in sentences if s.strip() and len(s.split()) >= 3]
        
        if not complete_sentences:
            return 0.3
        
        # Check for explanatory elements
        explanatory_words = ['because', 'since', 'therefore', 'due to', 'as a result']
        explanations = sum(1 for word in explanatory_words if word in response.lower())
        
        completeness = min(len(complete_sentences) / 3, 1.0)  # Up to 3 sentences
        explanation_bonus = min(explanations / 5, 0.2)  # Up to 20% bonus
        
        return min(completeness + explanation_bonus, 1.0)
    
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


class TextGenerationTests:
    """Collection of text generation tests."""
    
    @staticmethod
    def get_creative_writing_test() -> CreativeWritingTest:
        """Get creative writing test."""
        config = {
            'prompt': 'Write a short story about a robot who discovers it can dream.',
            'system_prompt': 'You are a creative writing assistant. Write engaging, imaginative stories.',
            'expected_length': 300,
            'min_length': 100
        }
        return CreativeWritingTest(
            name='creative_writing_robot_dreams',
            description='Creative writing test - robot dreams story',
            config=config
        )
    
    @staticmethod
    def get_summarization_test() -> SummarizationTest:
        """Get summarization test."""
        source_text = """
        Artificial intelligence (AI) is intelligence demonstrated by machines, 
        in contrast to the natural intelligence displayed by humans and animals. 
        Leading AI textbooks define the field as the study of "intelligent agents": 
        any device that perceives its environment and takes actions that maximize 
        its chance of successfully achieving its goals. Colloquially, the term 
        "artificial intelligence" is often used to describe machines that mimic 
        "cognitive" functions that humans associate with the human mind, such as 
        "learning" and "problem solving". As machines become increasingly capable, 
        tasks considered to require "intelligence" are often removed from the 
        definition of AI, a phenomenon known as the AI effect.
        """
        
        config = {
            'source_text': source_text.strip(),
            'system_prompt': 'You are a skilled summarization assistant. Provide concise, accurate summaries.',
            'expected_length': 100,
            'min_length': 50
        }
        return SummarizationTest(
            name='summarization_ai_definition',
            description='Summarization test - AI definition',
            config=config
        )
    
    @staticmethod
    def get_question_answering_test() -> QuestionAnsweringTest:
        """Get question answering test."""
        config = {
            'prompt': 'What is the capital of France and what are three major landmarks located there?',
            'system_prompt': 'You are a knowledgeable geography assistant. Provide accurate, helpful answers.',
            'expected_result': 'Paris Eiffel Tower Louvre Museum Arc de Triomphe',
            'min_length': 50
        }
        return QuestionAnsweringTest(
            name='question_answering_france_capital',
            description='Question answering test - France capital and landmarks',
            config=config
        )
    
    @staticmethod
    def get_all_tests() -> List[BaseTest]:
        """Get all text generation tests."""
        return [
            TextGenerationTests.get_creative_writing_test(),
            TextGenerationTests.get_summarization_test(),
            TextGenerationTests.get_question_answering_test()
        ]