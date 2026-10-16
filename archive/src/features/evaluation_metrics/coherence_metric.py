"""
Coherence Metric for LLM Evaluation System
Evaluates the coherence and logical flow of the response
"""

import re
from typing import Dict, Any, Optional, List
from .base_metric import BaseMetric, MetricResult, MetricConfig, MetricType


class CoherenceMetric(BaseMetric):
    """Evaluates the coherence and logical flow of the response"""
    
    def __init__(self, config: Optional[MetricConfig] = None):
        super().__init__(config)
        self._metric_type = MetricType.COHERENCE
        self._name = "CoherenceMetric"
        self._description = "Evaluates coherence and logical flow of the response"
        self._version = "1.0.0"
    
    async def evaluate(self, query: str, response: str, ground_truth: Optional[str] = None) -> MetricResult:
        """
        Evaluate the coherence of the response
        
        Args:
            query: The original query/prompt
            response: The LLM response to evaluate
            ground_truth: Optional ground truth for comparison (not used in this metric)
            
        Returns:
            MetricResult with coherence score and details
        """
        if not self.validate_inputs(query, response, ground_truth):
            return self.create_result(
                score=0.0,
                details={'error': 'Invalid inputs'},
                error_message="Invalid input parameters"
            )
        
        try:
            # Calculate different aspects of coherence
            structural_coherence = self._calculate_structural_coherence(response)
            semantic_coherence = self._calculate_semantic_coherence(response)
            logical_flow = self._calculate_logical_flow(response)
            readability = self._calculate_readability(response)
            
            # Combine scores with weights
            weights = self.config.parameters.get('weights', {
                'structural': 0.3,
                'semantic': 0.3,
                'logical': 0.25,
                'readability': 0.15
            })
            
            final_score = (
                structural_coherence * weights['structural'] +
                semantic_coherence * weights['semantic'] +
                logical_flow * weights['logical'] +
                readability * weights['readability']
            )
            
            details = {
                'structural_coherence': structural_coherence,
                'semantic_coherence': semantic_coherence,
                'logical_flow': logical_flow,
                'readability': readability,
                'final_score': final_score,
                'weights': weights,
                'sentence_count': len(self._split_sentences(response)),
                'paragraph_count': len(self._split_paragraphs(response)),
                'avg_sentence_length': self._calculate_avg_sentence_length(response),
                'transition_words': self._count_transition_words(response)
            }
            
            return self.create_result(final_score, details)
            
        except Exception as e:
            return self.create_result(
                score=0.0,
                details={'error': str(e)},
                error_message=f"Coherence evaluation failed: {str(e)}"
            )
    
    def _calculate_structural_coherence(self, response: str) -> float:
        """Calculate structural coherence of the response"""
        score = 0.0
        
        # Check for proper paragraph structure
        paragraphs = self._split_paragraphs(response)
        if len(paragraphs) > 1:
            score += 0.2
        
        # Check for proper sentence structure
        sentences = self._split_sentences(response)
        if len(sentences) > 1:
            score += 0.2
        
        # Check for appropriate length distribution
        if self._has_balanced_structure(sentences):
            score += 0.3
        
        # Check for proper formatting
        if self._has_proper_formatting(response):
            score += 0.3
        
        return min(1.0, score)
    
    def _calculate_semantic_coherence(self, response: str) -> float:
        """Calculate semantic coherence of the response"""
        sentences = self._split_sentences(response)
        
        if len(sentences) < 2:
            return 0.5  # Single sentence, moderate coherence
        
        # Calculate topic consistency
        topic_consistency = self._calculate_topic_consistency(sentences)
        
        # Calculate vocabulary consistency
        vocabulary_consistency = self._calculate_vocabulary_consistency(sentences)
        
        # Calculate reference consistency
        reference_consistency = self._calculate_reference_consistency(sentences)
        
        # Combine semantic coherence scores
        semantic_score = (
            topic_consistency * 0.5 +
            vocabulary_consistency * 0.3 +
            reference_consistency * 0.2
        )
        
        return semantic_score
    
    def _calculate_logical_flow(self, response: str) -> float:
        """Calculate logical flow of the response"""
        sentences = self._split_sentences(response)
        
        if len(sentences) < 2:
            return 0.5  # Single sentence, moderate flow
        
        # Check for logical connectors
        connector_score = self._assess_logical_connectors(response)
        
        # Check for proper sequencing
        sequence_score = self._assess_sequence_logic(sentences)
        
        # Check for argument structure
        argument_score = self._assess_argument_structure(response)
        
        # Combine logical flow scores
        logical_score = (
            connector_score * 0.4 +
            sequence_score * 0.3 +
            argument_score * 0.3
        )
        
        return logical_score
    
    def _calculate_readability(self, response: str) -> float:
        """Calculate readability of the response"""
        # Simple readability assessment
        sentences = self._split_sentences(response)
        words = response.split()
        
        if not sentences or not words:
            return 0.0
        
        # Average sentence length
        avg_sentence_length = len(words) / len(sentences)
        sentence_length_score = self._score_sentence_length(avg_sentence_length)
        
        # Word complexity
        word_complexity_score = self._assess_word_complexity(words)
        
        # Punctuation usage
        punctuation_score = self._assess_punctuation(response)
        
        # Combine readability scores
        readability_score = (
            sentence_length_score * 0.4 +
            word_complexity_score * 0.3 +
            punctuation_score * 0.3
        )
        
        return readability_score
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _calculate_avg_sentence_length(self, text: str) -> float:
        """Calculate average sentence length"""
        sentences = self._split_sentences(text)
        if not sentences:
            return 0.0
        
        total_words = sum(len(sentence.split()) for sentence in sentences)
        return total_words / len(sentences)
    
    def _count_transition_words(self, text: str) -> int:
        """Count transition words in the text"""
        transition_words = [
            'however', 'therefore', 'moreover', 'furthermore', 'additionally',
            'consequently', 'nevertheless', 'meanwhile', 'subsequently',
            'first', 'second', 'third', 'finally', 'next', 'then',
            'also', 'besides', 'similarly', 'likewise', 'in contrast',
            'on the other hand', 'for example', 'for instance', 'in fact',
            'in conclusion', 'as a result', 'due to', 'because of'
        ]
        
        text_lower = text.lower()
        return sum(1 for word in transition_words if word in text_lower)
    
    def _has_balanced_structure(self, sentences: List[str]) -> bool:
        """Check if sentences have balanced structure"""
        if len(sentences) < 2:
            return False
        
        lengths = [len(sentence.split()) for sentence in sentences]
        avg_length = sum(lengths) / len(lengths)
        
        # Check if most sentences are within reasonable range of average
        balanced_count = sum(1 for length in lengths if 0.5 * avg_length <= length <= 1.5 * avg_length)
        return balanced_count / len(lengths) >= 0.7
    
    def _has_proper_formatting(self, text: str) -> bool:
        """Check for proper formatting"""
        # Check for proper capitalization
        sentences = self._split_sentences(text)
        if not sentences:
            return False
        
        properly_capitalized = sum(1 for sentence in sentences if sentence and sentence[0].isupper())
        return properly_capitalized / len(sentences) >= 0.8
    
    def _calculate_topic_consistency(self, sentences: List[str]) -> float:
        """Calculate topic consistency across sentences"""
        if len(sentences) < 2:
            return 1.0
        
        # Simple topic consistency based on word overlap
        all_words = set()
        sentence_words = []
        
        for sentence in sentences:
            words = set(word.lower() for word in sentence.split() if len(word) > 3)
            sentence_words.append(words)
            all_words.update(words)
        
        if not all_words:
            return 0.5
        
        # Calculate average overlap between adjacent sentences
        overlaps = []
        for i in range(len(sentence_words) - 1):
            overlap = len(sentence_words[i] & sentence_words[i + 1])
            union = len(sentence_words[i] | sentence_words[i + 1])
            if union > 0:
                overlaps.append(overlap / union)
        
        return sum(overlaps) / len(overlaps) if overlaps else 0.5
    
    def _calculate_vocabulary_consistency(self, sentences: List[str]) -> float:
        """Calculate vocabulary consistency"""
        if len(sentences) < 2:
            return 1.0
        
        # Check for consistent vocabulary level
        word_lengths = []
        for sentence in sentences:
            words = sentence.split()
            if words:
                avg_word_length = sum(len(word) for word in words) / len(words)
                word_lengths.append(avg_word_length)
        
        if not word_lengths:
            return 0.5
        
        # Calculate coefficient of variation
        if len(word_lengths) > 1:
            mean_length = sum(word_lengths) / len(word_lengths)
            variance = sum((length - mean_length) ** 2 for length in word_lengths) / len(word_lengths)
            std_dev = variance ** 0.5
            
            if mean_length > 0:
                cv = std_dev / mean_length
                return max(0.0, 1.0 - cv)
        
        return 0.7
    
    def _calculate_reference_consistency(self, sentences: List[str]) -> float:
        """Calculate reference consistency (pronouns, entities)"""
        # Simple reference consistency check
        pronouns = ['he', 'she', 'it', 'they', 'this', 'that', 'these', 'those']
        
        reference_score = 0.0
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(pronoun in sentence_lower for pronoun in pronouns):
                reference_score += 0.1
        
        return min(1.0, reference_score)
    
    def _assess_logical_connectors(self, text: str) -> float:
        """Assess use of logical connectors"""
        connectors = [
            'because', 'since', 'therefore', 'thus', 'hence', 'consequently',
            'however', 'nevertheless', 'nonetheless', 'although', 'though',
            'while', 'whereas', 'moreover', 'furthermore', 'additionally',
            'first', 'second', 'third', 'finally', 'next', 'then'
        ]
        
        text_lower = text.lower()
        connector_count = sum(1 for connector in connectors if connector in text_lower)
        
        # Normalize by number of sentences
        sentences = self._split_sentences(text)
        if not sentences:
            return 0.0
        
        connector_ratio = connector_count / len(sentences)
        return min(1.0, connector_ratio * 2)  # Scale appropriately
    
    def _assess_sequence_logic(self, sentences: List[str]) -> float:
        """Assess logical sequence of sentences"""
        # Check for sequence indicators
        sequence_indicators = [
            'first', 'second', 'third', 'fourth', 'fifth',
            'initially', 'then', 'next', 'after', 'before',
            'subsequently', 'finally', 'lastly', 'in conclusion'
        ]
        
        sequence_score = 0.0
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in sequence_indicators):
                sequence_score += 0.2
        
        return min(1.0, sequence_score)
    
    def _assess_argument_structure(self, text: str) -> float:
        """Assess argument structure"""
        # Check for argument patterns
        argument_patterns = [
            r'\b(claim|argument|point|reason|evidence|support|conclusion)\b',
            r'\b(prove|demonstrate|show|indicate|suggest|imply)\b',
            r'\b(because|since|due to|as a result|therefore|thus)\b'
        ]
        
        argument_score = 0.0
        for pattern in argument_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                argument_score += 0.3
        
        return min(1.0, argument_score)
    
    def _score_sentence_length(self, avg_length: float) -> float:
        """Score sentence length appropriateness"""
        # Optimal sentence length is around 15-20 words
        if 15 <= avg_length <= 20:
            return 1.0
        elif 10 <= avg_length < 15 or 20 < avg_length <= 25:
            return 0.8
        elif 5 <= avg_length < 10 or 25 < avg_length <= 30:
            return 0.6
        else:
            return 0.3
    
    def _assess_word_complexity(self, words: List[str]) -> float:
        """Assess word complexity"""
        if not words:
            return 0.0
        
        # Count syllables (simplified)
        complex_words = 0
        for word in words:
            if len(word) > 6:  # Rough complexity measure
                complex_words += 1
        
        complexity_ratio = complex_words / len(words)
        
        # Moderate complexity is good
        if 0.1 <= complexity_ratio <= 0.3:
            return 1.0
        elif complexity_ratio < 0.1:
            return 0.7  # Too simple
        else:
            return 0.5  # Too complex
    
    def _assess_punctuation(self, text: str) -> float:
        """Assess punctuation usage"""
        sentences = self._split_sentences(text)
        if not sentences:
            return 0.0
        
        # Check for proper punctuation
        punctuation_marks = ['.', '!', '?', ',', ';', ':']
        punctuation_count = sum(1 for char in text if char in punctuation_marks)
        
        # Reasonable punctuation ratio
        word_count = len(text.split())
        if word_count == 0:
            return 0.0
        
        punctuation_ratio = punctuation_count / word_count
        
        # Good punctuation ratio is around 0.1-0.2
        if 0.1 <= punctuation_ratio <= 0.2:
            return 1.0
        elif 0.05 <= punctuation_ratio < 0.1 or 0.2 < punctuation_ratio <= 0.3:
            return 0.8
        else:
            return 0.6
    
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
                        "structural": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.3},
                        "semantic": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.3},
                        "logical": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.25},
                        "readability": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.15}
                    },
                    "description": "Weights for different coherence components"
                }
            }
        }
        
        return base_schema