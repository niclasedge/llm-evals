"""
Accuracy Metric for LLM Evaluation System
Evaluates factual accuracy of the response
"""

import re
from typing import Dict, Any, Optional, List
from .base_metric import BaseMetric, MetricResult, MetricConfig, MetricType


class AccuracyMetric(BaseMetric):
    """Evaluates the factual accuracy of the response"""
    
    def __init__(self, config: Optional[MetricConfig] = None):
        super().__init__(config)
        self._metric_type = MetricType.ACCURACY
        self._name = "AccuracyMetric"
        self._description = "Evaluates factual accuracy of the response"
        self._version = "1.0.0"
    
    async def evaluate(self, query: str, response: str, ground_truth: Optional[str] = None) -> MetricResult:
        """
        Evaluate the factual accuracy of the response
        
        Args:
            query: The original query/prompt
            response: The LLM response to evaluate
            ground_truth: Optional ground truth for comparison
            
        Returns:
            MetricResult with accuracy score and details
        """
        if not self.validate_inputs(query, response, ground_truth):
            return self.create_result(
                score=0.0,
                details={'error': 'Invalid inputs'},
                error_message="Invalid input parameters"
            )
        
        try:
            if ground_truth:
                # If ground truth is provided, compare against it
                accuracy_score = self._calculate_ground_truth_accuracy(response, ground_truth)
                evaluation_method = "ground_truth_comparison"
            else:
                # If no ground truth, use heuristic-based accuracy assessment
                accuracy_score = self._calculate_heuristic_accuracy(query, response)
                evaluation_method = "heuristic_assessment"
            
            # Additional accuracy checks
            factual_consistency = self._check_factual_consistency(response)
            logical_consistency = self._check_logical_consistency(response)
            common_errors = self._detect_common_errors(response)
            
            # Combine scores
            weights = self.config.parameters.get('weights', {
                'primary': 0.6,
                'factual_consistency': 0.2,
                'logical_consistency': 0.2
            })
            
            final_score = (
                accuracy_score * weights['primary'] +
                factual_consistency * weights['factual_consistency'] +
                logical_consistency * weights['logical_consistency']
            )
            
            details = {
                'primary_accuracy': accuracy_score,
                'factual_consistency': factual_consistency,
                'logical_consistency': logical_consistency,
                'final_score': final_score,
                'evaluation_method': evaluation_method,
                'common_errors': common_errors,
                'weights': weights,
                'has_ground_truth': ground_truth is not None
            }
            
            return self.create_result(final_score, details)
            
        except Exception as e:
            return self.create_result(
                score=0.0,
                details={'error': str(e)},
                error_message=f"Accuracy evaluation failed: {str(e)}"
            )
    
    def _calculate_ground_truth_accuracy(self, response: str, ground_truth: str) -> float:
        """Calculate accuracy by comparing with ground truth"""
        # Simple text similarity approach
        response_clean = self._clean_text(response)
        ground_truth_clean = self._clean_text(ground_truth)
        
        # Exact match
        if response_clean == ground_truth_clean:
            return 1.0
        
        # Partial match based on key information
        key_info_match = self._calculate_key_information_match(response_clean, ground_truth_clean)
        
        # Semantic similarity (simplified)
        semantic_similarity = self._calculate_text_similarity(response_clean, ground_truth_clean)
        
        # Combine scores
        return max(key_info_match, semantic_similarity)
    
    def _calculate_heuristic_accuracy(self, query: str, response: str) -> float:
        """Calculate accuracy using heuristic methods"""
        accuracy_score = 0.0
        
        # Check for specific answer patterns
        if self._is_factual_query(query):
            accuracy_score += self._assess_factual_response(response) * 0.5
        
        # Check for mathematical accuracy
        if self._contains_math(query) or self._contains_math(response):
            accuracy_score += self._assess_mathematical_accuracy(query, response) * 0.3
        
        # Check for logical accuracy
        accuracy_score += self._assess_logical_accuracy(response) * 0.2
        
        return min(1.0, accuracy_score)
    
    def _check_factual_consistency(self, response: str) -> float:
        """Check for factual consistency within the response"""
        # Check for contradictions
        contradictions = self._detect_contradictions(response)
        
        # Check for uncertain language
        uncertainty_score = self._assess_uncertainty_language(response)
        
        # Check for specific facts
        specific_facts_score = self._assess_specific_facts(response)
        
        consistency_score = 1.0 - (contradictions * 0.5) + (uncertainty_score * 0.3) + (specific_facts_score * 0.2)
        
        return max(0.0, min(1.0, consistency_score))
    
    def _check_logical_consistency(self, response: str) -> float:
        """Check for logical consistency in the response"""
        # Check for logical flow
        logical_flow_score = self._assess_logical_flow(response)
        
        # Check for reasoning quality
        reasoning_quality_score = self._assess_reasoning_quality(response)
        
        # Combine scores
        return (logical_flow_score + reasoning_quality_score) / 2
    
    def _detect_common_errors(self, response: str) -> List[str]:
        """Detect common accuracy errors"""
        errors = []
        
        # Check for hedging language that might indicate uncertainty
        hedging_patterns = [
            r'\b(might|maybe|perhaps|possibly|probably|likely|seems|appears)\b',
            r'\b(i think|i believe|i assume|i guess)\b',
            r'\b(not sure|not certain|uncertain)\b'
        ]
        
        for pattern in hedging_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                errors.append(f"Hedging language detected: {pattern}")
        
        # Check for contradictory statements
        if self._has_contradictions(response):
            errors.append("Contradictory statements detected")
        
        # Check for unsupported claims
        if self._has_unsupported_claims(response):
            errors.append("Unsupported claims detected")
        
        return errors
    
    def _clean_text(self, text: str) -> str:
        """Clean text for comparison"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        # Convert to lowercase
        text = text.lower()
        # Remove punctuation for comparison
        text = re.sub(r'[^\w\s]', '', text)
        return text
    
    def _calculate_key_information_match(self, response: str, ground_truth: str) -> float:
        """Calculate match of key information"""
        # Extract potential key information (numbers, dates, names, etc.)
        response_keys = self._extract_key_information(response)
        ground_truth_keys = self._extract_key_information(ground_truth)
        
        if not ground_truth_keys:
            return 0.5  # No key information to compare
        
        matches = len(set(response_keys) & set(ground_truth_keys))
        return matches / len(ground_truth_keys)
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using word overlap"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_key_information(self, text: str) -> List[str]:
        """Extract key information from text"""
        keys = []
        
        # Numbers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        keys.extend(numbers)
        
        # Dates
        dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)
        keys.extend(dates)
        
        # Years
        years = re.findall(r'\b(19|20)\d{2}\b', text)
        keys.extend(years)
        
        # Proper nouns (simplified)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', text)
        keys.extend(proper_nouns)
        
        return keys
    
    def _is_factual_query(self, query: str) -> bool:
        """Check if query is asking for factual information"""
        factual_indicators = [
            'what is', 'who is', 'when did', 'where is', 'how many',
            'capital of', 'population of', 'founded in', 'located in',
            'definition of', 'meaning of'
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in factual_indicators)
    
    def _assess_factual_response(self, response: str) -> float:
        """Assess if response appears factual"""
        # Check for specific facts vs. vague statements
        specific_indicators = len(re.findall(r'\b\d+\b', response))  # Numbers
        specific_indicators += len(re.findall(r'\b[A-Z][a-z]+\b', response))  # Proper nouns
        
        # Normalize by response length
        response_words = len(response.split())
        if response_words == 0:
            return 0.0
        
        specificity_score = min(1.0, specific_indicators / (response_words / 10))
        return specificity_score
    
    def _contains_math(self, text: str) -> bool:
        """Check if text contains mathematical content"""
        math_patterns = [
            r'\b\d+\s*[+\-*/=]\s*\d+\b',
            r'\b\d+\s*%\b',
            r'\b\d+\s*degrees?\b',
            r'\b\d+\s*(?:plus|minus|times|divided by)\s*\d+\b'
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in math_patterns)
    
    def _assess_mathematical_accuracy(self, query: str, response: str) -> float:
        """Assess mathematical accuracy (simplified)"""
        # This is a simplified implementation
        # In a real system, you'd want to parse and verify mathematical expressions
        
        # Check for mathematical expressions in response
        math_expressions = re.findall(r'\b\d+\s*[+\-*/=]\s*\d+\b', response)
        
        correct_expressions = 0
        total_expressions = len(math_expressions)
        
        for expr in math_expressions:
            # Very basic check - would need proper math parsing in production
            if '=' in expr:
                try:
                    left, right = expr.split('=')
                    left_result = eval(left.strip())
                    right_result = float(right.strip())
                    if abs(left_result - right_result) < 0.001:
                        correct_expressions += 1
                except:
                    pass
        
        return correct_expressions / total_expressions if total_expressions > 0 else 0.5
    
    def _assess_logical_accuracy(self, response: str) -> float:
        """Assess logical accuracy of the response"""
        # Check for logical indicators
        logical_indicators = [
            'because', 'therefore', 'thus', 'hence', 'consequently',
            'if', 'then', 'since', 'as a result'
        ]
        
        logical_score = 0.0
        for indicator in logical_indicators:
            if indicator in response.lower():
                logical_score += 0.1
        
        return min(1.0, logical_score)
    
    def _detect_contradictions(self, response: str) -> float:
        """Detect contradictions in the response"""
        # Simple contradiction detection
        contradiction_patterns = [
            (r'\bnot\b', r'\bis\b'),
            (r'\byes\b', r'\bno\b'),
            (r'\btrue\b', r'\bfalse\b'),
            (r'\balways\b', r'\bnever\b')
        ]
        
        contradictions = 0
        for pos_pattern, neg_pattern in contradiction_patterns:
            if re.search(pos_pattern, response, re.IGNORECASE) and re.search(neg_pattern, response, re.IGNORECASE):
                contradictions += 1
        
        return contradictions / len(contradiction_patterns)
    
    def _assess_uncertainty_language(self, response: str) -> float:
        """Assess uncertainty language in response"""
        uncertainty_words = ['maybe', 'perhaps', 'possibly', 'might', 'could', 'seem', 'appear']
        
        uncertainty_count = sum(1 for word in uncertainty_words if word in response.lower())
        total_words = len(response.split())
        
        return 1.0 - min(0.5, uncertainty_count / max(1, total_words / 10))
    
    def _assess_specific_facts(self, response: str) -> float:
        """Assess presence of specific facts"""
        # Count specific elements
        numbers = len(re.findall(r'\b\d+\b', response))
        proper_nouns = len(re.findall(r'\b[A-Z][a-z]+\b', response))
        dates = len(re.findall(r'\b\d{4}\b', response))
        
        specificity_score = (numbers + proper_nouns + dates) / max(1, len(response.split()) / 10)
        return min(1.0, specificity_score)
    
    def _assess_logical_flow(self, response: str) -> float:
        """Assess logical flow of the response"""
        # Check for logical connectors
        connectors = ['first', 'second', 'then', 'next', 'finally', 'therefore', 'because', 'since']
        
        connector_count = sum(1 for connector in connectors if connector in response.lower())
        sentences = len(response.split('.'))
        
        return min(1.0, connector_count / max(1, sentences / 3))
    
    def _assess_reasoning_quality(self, response: str) -> float:
        """Assess quality of reasoning"""
        # Check for reasoning patterns
        reasoning_patterns = [
            r'\bbecause\b',
            r'\bsince\b',
            r'\btherefore\b',
            r'\bas a result\b',
            r'\bdue to\b',
            r'\bconsequently\b'
        ]
        
        reasoning_score = 0.0
        for pattern in reasoning_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                reasoning_score += 0.2
        
        return min(1.0, reasoning_score)
    
    def _has_contradictions(self, response: str) -> bool:
        """Check if response has contradictions"""
        return self._detect_contradictions(response) > 0.1
    
    def _has_unsupported_claims(self, response: str) -> bool:
        """Check for unsupported claims"""
        # Simple check for claims without evidence
        claim_patterns = [
            r'\bstudies show\b',
            r'\bresearch indicates\b',
            r'\bexperts say\b',
            r'\bit is proven\b'
        ]
        
        return any(re.search(pattern, response, re.IGNORECASE) for pattern in claim_patterns)
    
    def get_requirements(self) -> List[str]:
        """Get requirements for this metric"""
        return []  # No external dependencies for basic implementation
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for this metric"""
        base_schema = super().get_config_schema()
        
        base_schema["properties"]["parameters"] = {
            "type": "object",
            "properties": {
                "weights": {
                    "type": "object",
                    "properties": {
                        "primary": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.6},
                        "factual_consistency": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.2},
                        "logical_consistency": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.2}
                    },
                    "description": "Weights for different accuracy components"
                }
            }
        }
        
        return base_schema