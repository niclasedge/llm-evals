"""
Base intelligence test class for LLM evaluation.
Extends the base test framework with intelligence-specific features.
"""

import re
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from enum import Enum
try:
    from ..test_framework.base_test import BaseTest, TestResult, TestStatus
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from src.features.llm_evaluation.test_framework.base_test import BaseTest, TestResult, TestStatus


class IntelligenceCategory(Enum):
    """Categories of intelligence tests."""
    LOGICAL_REASONING = "logical_reasoning"
    MATHEMATICAL_REASONING = "mathematical_reasoning"
    PATTERN_RECOGNITION = "pattern_recognition"
    SPATIAL_REASONING = "spatial_reasoning"
    CREATIVE_THINKING = "creative_thinking"
    ABSTRACT_REASONING = "abstract_reasoning"
    GRAPHICAL_REPRESENTATION = "graphical_representation"
    PROBLEM_SOLVING = "problem_solving"


class IntelligenceTestResult(TestResult):
    """Extended test result for intelligence tests."""
    
    def __init__(self, test_name: str, status: TestStatus, 
                 score: Optional[float] = None, 
                 details: Optional[Dict[str, Any]] = None,
                 error: Optional[str] = None,
                 execution_time: Optional[float] = None,
                 intelligence_category: Optional[IntelligenceCategory] = None,
                 complexity_level: Optional[int] = None,
                 creativity_score: Optional[float] = None,
                 logical_coherence: Optional[float] = None):
        super().__init__(test_name, status, score, details, error, execution_time)
        self.intelligence_category = intelligence_category
        self.complexity_level = complexity_level
        self.creativity_score = creativity_score
        self.logical_coherence = logical_coherence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        base_dict = super().to_dict()
        base_dict.update({
            'intelligence_category': self.intelligence_category.value if self.intelligence_category else None,
            'complexity_level': self.complexity_level,
            'creativity_score': self.creativity_score,
            'logical_coherence': self.logical_coherence
        })
        return base_dict


class IntelligenceTestBase(BaseTest):
    """Base class for intelligence tests."""
    
    def __init__(self, name: str, description: str, config: Dict[str, Any],
                 intelligence_category: IntelligenceCategory,
                 complexity_level: int = 1):
        super().__init__(name, description, config)
        self.intelligence_category = intelligence_category
        self.complexity_level = complexity_level
    
    @abstractmethod
    async def run(self, client: Any, model: str, **kwargs) -> IntelligenceTestResult:
        """Execute the intelligence test."""
        pass
    
    def analyze_creativity(self, response: str) -> float:
        """Analyze creativity in response."""
        if not response:
            return 0.0
        
        creativity_score = 0.0
        
        # Novelty indicators
        novelty_indicators = [
            r'creative', r'innovative', r'original', r'unique', r'novel',
            r'alternative', r'different', r'unusual', r'unconventional'
        ]
        
        for indicator in novelty_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                creativity_score += 0.1
        
        # Variety in vocabulary
        words = response.split()
        unique_words = len(set(words))
        vocabulary_diversity = unique_words / len(words) if words else 0
        creativity_score += vocabulary_diversity * 0.3
        
        # Metaphorical language
        metaphor_indicators = [
            r'like', r'as if', r'imagine', r'picture', r'visualize',
            r'metaphor', r'analogy', r'symbolize', r'represent'
        ]
        
        for indicator in metaphor_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                creativity_score += 0.05
        
        return min(creativity_score, 1.0)
    
    def analyze_logical_coherence(self, response: str) -> float:
        """Analyze logical coherence in response."""
        if not response:
            return 0.0
        
        coherence_score = 0.0
        
        # Logical connectors
        logical_connectors = [
            r'therefore', r'because', r'since', r'thus', r'hence',
            r'consequently', r'as a result', r'due to', r'given that',
            r'if.*then', r'assuming', r'provided that'
        ]
        
        for connector in logical_connectors:
            if re.search(connector, response, re.IGNORECASE):
                coherence_score += 0.1
        
        # Structured reasoning
        structure_indicators = [
            r'first', r'second', r'third', r'step \d+', r'next',
            r'finally', r'in conclusion', r'to summarize'
        ]
        
        for indicator in structure_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                coherence_score += 0.05
        
        # Consistency (no contradictions)
        contradiction_indicators = [
            r'however.*but', r'although.*yet', r'despite.*still',
            r'on the other hand.*contradicts'
        ]
        
        contradiction_penalty = 0.0
        for indicator in contradiction_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                contradiction_penalty += 0.1
        
        coherence_score = max(0.0, coherence_score - contradiction_penalty)
        
        return min(coherence_score, 1.0)
    
    def extract_key_concepts(self, response: str) -> List[str]:
        """Extract key concepts from response."""
        if not response:
            return []
        
        # Simple keyword extraction
        words = re.findall(r'\w+', response.lower())
        
        # Filter out common words
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'can', 'may', 'might', 'must', 'shall'
        }
        
        key_concepts = []
        for word in words:
            if len(word) > 3 and word not in common_words:
                key_concepts.append(word)
        
        # Return unique concepts
        return list(set(key_concepts))
    
    def measure_complexity(self, response: str) -> int:
        """Measure complexity of response."""
        if not response:
            return 0
        
        complexity = 0
        
        # Sentence length complexity
        sentences = re.split(r'[.!?]+', response)
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        if avg_sentence_length > 20:
            complexity += 2
        elif avg_sentence_length > 15:
            complexity += 1
        
        # Vocabulary complexity
        long_words = len([word for word in response.split() if len(word) > 7])
        total_words = len(response.split())
        
        if total_words > 0:
            long_word_ratio = long_words / total_words
            if long_word_ratio > 0.3:
                complexity += 2
            elif long_word_ratio > 0.2:
                complexity += 1
        
        # Nested reasoning complexity
        nested_indicators = [
            r'because.*since', r'if.*then.*but', r'although.*however',
            r'while.*still', r'despite.*nevertheless'
        ]
        
        for indicator in nested_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                complexity += 1
        
        return complexity
    
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
                from ..llm_service import run_query
                response = await run_query(client, prompt)
                return str(response) if response else ''
                
        except Exception as e:
            print(f"Error getting response: {e}")
            return ''