"""
Relevance Metric for LLM Evaluation System
Evaluates how relevant the response is to the query
"""

import re
from typing import Dict, Any, Optional, List
from .base_metric import BaseMetric, MetricResult, MetricConfig, MetricType


class RelevanceMetric(BaseMetric):
    """Evaluates the relevance of the response to the query"""
    
    def __init__(self, config: Optional[MetricConfig] = None):
        super().__init__(config)
        self._metric_type = MetricType.RELEVANCE
        self._name = "RelevanceMetric"
        self._description = "Evaluates how relevant the response is to the query"
        self._version = "1.0.0"
    
    async def evaluate(self, query: str, response: str, ground_truth: Optional[str] = None) -> MetricResult:
        """
        Evaluate the relevance of the response to the query
        
        Args:
            query: The original query/prompt
            response: The LLM response to evaluate
            ground_truth: Optional ground truth for comparison (not used in this metric)
            
        Returns:
            MetricResult with relevance score and details
        """
        if not self.validate_inputs(query, response, ground_truth):
            return self.create_result(
                score=0.0,
                details={'error': 'Invalid inputs'},
                error_message="Invalid input parameters"
            )
        
        try:
            # Calculate relevance score using multiple approaches
            keyword_score = self._calculate_keyword_relevance(query, response)
            semantic_score = self._calculate_semantic_relevance(query, response)
            structure_score = self._calculate_structure_relevance(query, response)
            
            # Combine scores with weights
            weights = self.config.parameters.get('weights', {
                'keyword': 0.4,
                'semantic': 0.4,
                'structure': 0.2
            })
            
            final_score = (
                keyword_score * weights['keyword'] +
                semantic_score * weights['semantic'] +
                structure_score * weights['structure']
            )
            
            details = {
                'keyword_score': keyword_score,
                'semantic_score': semantic_score,
                'structure_score': structure_score,
                'final_score': final_score,
                'weights': weights,
                'query_length': len(query),
                'response_length': len(response),
                'keyword_matches': self._get_keyword_matches(query, response)
            }
            
            return self.create_result(final_score, details)
            
        except Exception as e:
            return self.create_result(
                score=0.0,
                details={'error': str(e)},
                error_message=f"Relevance evaluation failed: {str(e)}"
            )
    
    def _calculate_keyword_relevance(self, query: str, response: str) -> float:
        """Calculate relevance based on keyword matching"""
        # Extract keywords from query
        query_keywords = self._extract_keywords(query)
        response_keywords = self._extract_keywords(response)
        
        if not query_keywords:
            return 0.0
        
        # Calculate overlap
        matches = len(set(query_keywords) & set(response_keywords))
        keyword_score = matches / len(query_keywords)
        
        return min(1.0, keyword_score)
    
    def _calculate_semantic_relevance(self, query: str, response: str) -> float:
        """Calculate semantic relevance (simplified implementation)"""
        # Simple semantic relevance based on common patterns
        query_lower = query.lower()
        response_lower = response.lower()
        
        # Check for question-answer patterns
        if self._is_question(query_lower):
            if self._contains_answer_indicators(response_lower):
                return 0.8
        
        # Check for instruction-following patterns
        if self._is_instruction(query_lower):
            if self._follows_instruction_pattern(query_lower, response_lower):
                return 0.9
        
        # Default semantic similarity based on word overlap
        query_words = set(query_lower.split())
        response_words = set(response_lower.split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words & response_words)
        return overlap / len(query_words)
    
    def _calculate_structure_relevance(self, query: str, response: str) -> float:
        """Calculate relevance based on response structure"""
        score = 0.0
        
        # Check if response addresses the query type
        if self._is_question(query):
            if self._provides_answer(response):
                score += 0.5
        
        # Check response completeness
        if len(response.strip()) > 10:  # Non-trivial response
            score += 0.3
        
        # Check for proper formatting
        if self._has_proper_structure(response):
            score += 0.2
        
        return min(1.0, score)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'what', 'which', 'who', 'when', 'where', 'why', 'how'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords
    
    def _get_keyword_matches(self, query: str, response: str) -> List[str]:
        """Get list of matching keywords"""
        query_keywords = set(self._extract_keywords(query))
        response_keywords = set(self._extract_keywords(response))
        
        return list(query_keywords & response_keywords)
    
    def _is_question(self, text: str) -> bool:
        """Check if text is a question"""
        question_words = ['what', 'who', 'when', 'where', 'why', 'how', 'which', 'whose', 'whom']
        text_lower = text.lower().strip()
        
        return (text_lower.endswith('?') or 
                any(text_lower.startswith(word) for word in question_words))
    
    def _is_instruction(self, text: str) -> bool:
        """Check if text is an instruction"""
        instruction_words = ['write', 'explain', 'describe', 'list', 'create', 'generate', 'tell', 'show', 'give', 'provide', 'make', 'calculate', 'find', 'solve']
        text_lower = text.lower().strip()
        
        return any(text_lower.startswith(word) for word in instruction_words)
    
    def _contains_answer_indicators(self, response: str) -> bool:
        """Check if response contains answer indicators"""
        answer_patterns = [
            r'\b(the answer is|answer:|solution:|result:)',
            r'\b(because|since|due to|therefore|thus|hence)',
            r'\b(first|second|third|finally|in conclusion)',
            r'\b(yes|no|true|false)\b'
        ]
        
        return any(re.search(pattern, response, re.IGNORECASE) for pattern in answer_patterns)
    
    def _follows_instruction_pattern(self, query: str, response: str) -> bool:
        """Check if response follows instruction pattern"""
        if 'write' in query and len(response) > 50:
            return True
        if 'explain' in query and ('because' in response or 'since' in response):
            return True
        if 'list' in query and ('-' in response or '1.' in response or '•' in response):
            return True
        
        return False
    
    def _provides_answer(self, response: str) -> bool:
        """Check if response provides an answer"""
        return (len(response.strip()) > 5 and 
                not response.lower().startswith('i don\'t know') and
                not response.lower().startswith('i cannot') and
                not response.lower().startswith('sorry'))
    
    def _has_proper_structure(self, response: str) -> bool:
        """Check if response has proper structure"""
        # Check for proper capitalization
        if response and response[0].isupper():
            return True
        
        # Check for proper punctuation
        if response.strip().endswith(('.', '!', '?')):
            return True
        
        return False
    
    def get_requirements(self) -> List[str]:
        """Get requirements for this metric"""
        return []  # No external dependencies
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for this metric"""
        base_schema = super().get_config_schema()
        
        base_schema["properties"]["parameters"] = {
            "type": "object",
            "properties": {
                "weights": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.4},
                        "semantic": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.4},
                        "structure": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.2}
                    },
                    "description": "Weights for different relevance components"
                }
            }
        }
        
        return base_schema