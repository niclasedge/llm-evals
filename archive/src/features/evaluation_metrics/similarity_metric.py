"""
Similarity Metric for LLM Evaluation System
Evaluates semantic similarity between response and ground truth
"""

import re
from typing import Dict, Any, Optional, List, Set
from .base_metric import BaseMetric, MetricResult, MetricConfig, MetricType
import math


class SimilarityMetric(BaseMetric):
    """Evaluates semantic similarity between response and ground truth"""
    
    def __init__(self, config: Optional[MetricConfig] = None):
        super().__init__(config)
        self._metric_type = MetricType.SIMILARITY
        self._name = "SimilarityMetric"
        self._description = "Evaluates semantic similarity between response and ground truth"
        self._version = "1.0.0"
    
    async def evaluate(self, query: str, response: str, ground_truth: Optional[str] = None) -> MetricResult:
        """
        Evaluate the similarity between response and ground truth
        
        Args:
            query: The original query/prompt
            response: The LLM response to evaluate
            ground_truth: Ground truth for comparison (required for this metric)
            
        Returns:
            MetricResult with similarity score and details
        """
        if not self.validate_inputs(query, response, ground_truth):
            return self.create_result(
                score=0.0,
                details={'error': 'Invalid inputs'},
                error_message="Invalid input parameters"
            )
        
        if not ground_truth:
            return self.create_result(
                score=0.0,
                details={'error': 'Ground truth is required for similarity metric'},
                error_message="Ground truth is required for similarity evaluation"
            )
        
        try:
            # Calculate different types of similarity
            lexical_similarity = self._calculate_lexical_similarity(response, ground_truth)
            semantic_similarity = self._calculate_semantic_similarity(response, ground_truth)
            structural_similarity = self._calculate_structural_similarity(response, ground_truth)
            
            # Combine scores with weights
            weights = self.config.parameters.get('weights', {
                'lexical': 0.4,
                'semantic': 0.4,
                'structural': 0.2
            })
            
            final_score = (
                lexical_similarity * weights['lexical'] +
                semantic_similarity * weights['semantic'] +
                structural_similarity * weights['structural']
            )
            
            details = {
                'lexical_similarity': lexical_similarity,
                'semantic_similarity': semantic_similarity,
                'structural_similarity': structural_similarity,
                'final_score': final_score,
                'weights': weights,
                'response_length': len(response),
                'ground_truth_length': len(ground_truth),
                'word_overlap': self._calculate_word_overlap(response, ground_truth),
                'n_gram_similarities': self._calculate_n_gram_similarities(response, ground_truth)
            }
            
            return self.create_result(final_score, details)
            
        except Exception as e:
            return self.create_result(
                score=0.0,
                details={'error': str(e)},
                error_message=f"Similarity evaluation failed: {str(e)}"
            )
    
    def _calculate_lexical_similarity(self, text1: str, text2: str) -> float:
        """Calculate lexical similarity using various methods"""
        # Jaccard similarity
        jaccard_score = self._jaccard_similarity(text1, text2)
        
        # Cosine similarity
        cosine_score = self._cosine_similarity(text1, text2)
        
        # Dice coefficient
        dice_score = self._dice_coefficient(text1, text2)
        
        # Combine lexical similarity scores
        lexical_score = (jaccard_score + cosine_score + dice_score) / 3
        
        return lexical_score
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity (simplified implementation)"""
        # This is a simplified semantic similarity calculation
        # In a production system, you'd use word embeddings or transformer models
        
        # Synonym-aware similarity
        synonym_score = self._synonym_aware_similarity(text1, text2)
        
        # Context-aware similarity
        context_score = self._context_aware_similarity(text1, text2)
        
        # Concept-based similarity
        concept_score = self._concept_based_similarity(text1, text2)
        
        # Combine semantic similarity scores
        semantic_score = (synonym_score + context_score + concept_score) / 3
        
        return semantic_score
    
    def _calculate_structural_similarity(self, text1: str, text2: str) -> float:
        """Calculate structural similarity"""
        # Length similarity
        length_score = self._length_similarity(text1, text2)
        
        # Sentence structure similarity
        sentence_score = self._sentence_structure_similarity(text1, text2)
        
        # Punctuation similarity
        punctuation_score = self._punctuation_similarity(text1, text2)
        
        # Combine structural similarity scores
        structural_score = (length_score + sentence_score + punctuation_score) / 3
        
        return structural_score
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity"""
        words1 = set(self._tokenize(text1))
        words2 = set(self._tokenize(text2))
        
        if not words1 and not words2:
            return 1.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _cosine_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity"""
        words1 = self._tokenize(text1)
        words2 = self._tokenize(text2)
        
        # Create word frequency vectors
        all_words = set(words1 + words2)
        if not all_words:
            return 0.0
        
        vector1 = [words1.count(word) for word in all_words]
        vector2 = [words2.count(word) for word in all_words]
        
        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        magnitude1 = math.sqrt(sum(a * a for a in vector1))
        magnitude2 = math.sqrt(sum(b * b for b in vector2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _dice_coefficient(self, text1: str, text2: str) -> float:
        """Calculate Dice coefficient"""
        words1 = set(self._tokenize(text1))
        words2 = set(self._tokenize(text2))
        
        if not words1 and not words2:
            return 1.0
        
        intersection = len(words1 & words2)
        total = len(words1) + len(words2)
        
        return 2 * intersection / total if total > 0 else 0.0
    
    def _synonym_aware_similarity(self, text1: str, text2: str) -> float:
        """Calculate synonym-aware similarity"""
        # Simple synonym mapping (in production, use WordNet or similar)
        synonyms = {
            'good': ['excellent', 'great', 'fine', 'nice', 'wonderful'],
            'bad': ['poor', 'terrible', 'awful', 'horrible'],
            'big': ['large', 'huge', 'enormous', 'massive'],
            'small': ['little', 'tiny', 'minute', 'compact'],
            'fast': ['quick', 'rapid', 'swift', 'speedy'],
            'slow': ['sluggish', 'gradual', 'leisurely']
        }
        
        words1 = set(self._tokenize(text1))
        words2 = set(self._tokenize(text2))
        
        # Expand words with synonyms
        expanded_words1 = set(words1)
        expanded_words2 = set(words2)
        
        for word in words1:
            if word in synonyms:
                expanded_words1.update(synonyms[word])
        
        for word in words2:
            if word in synonyms:
                expanded_words2.update(synonyms[word])
        
        # Calculate similarity with expanded sets
        intersection = len(expanded_words1 & expanded_words2)
        union = len(expanded_words1 | expanded_words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _context_aware_similarity(self, text1: str, text2: str) -> float:
        """Calculate context-aware similarity"""
        # Simple context analysis based on surrounding words
        bigrams1 = self._get_bigrams(text1)
        bigrams2 = self._get_bigrams(text2)
        
        if not bigrams1 and not bigrams2:
            return 1.0
        
        common_bigrams = len(set(bigrams1) & set(bigrams2))
        total_bigrams = len(set(bigrams1) | set(bigrams2))
        
        return common_bigrams / total_bigrams if total_bigrams > 0 else 0.0
    
    def _concept_based_similarity(self, text1: str, text2: str) -> float:
        """Calculate concept-based similarity"""
        # Simple concept extraction based on keywords
        concepts1 = self._extract_concepts(text1)
        concepts2 = self._extract_concepts(text2)
        
        if not concepts1 and not concepts2:
            return 1.0
        
        common_concepts = len(set(concepts1) & set(concepts2))
        total_concepts = len(set(concepts1) | set(concepts2))
        
        return common_concepts / total_concepts if total_concepts > 0 else 0.0
    
    def _length_similarity(self, text1: str, text2: str) -> float:
        """Calculate length-based similarity"""
        len1 = len(text1)
        len2 = len(text2)
        
        if len1 == 0 and len2 == 0:
            return 1.0
        
        max_len = max(len1, len2)
        min_len = min(len1, len2)
        
        return min_len / max_len if max_len > 0 else 0.0
    
    def _sentence_structure_similarity(self, text1: str, text2: str) -> float:
        """Calculate sentence structure similarity"""
        sentences1 = self._split_sentences(text1)
        sentences2 = self._split_sentences(text2)
        
        if not sentences1 and not sentences2:
            return 1.0
        
        # Compare sentence count
        count_similarity = min(len(sentences1), len(sentences2)) / max(len(sentences1), len(sentences2)) if max(len(sentences1), len(sentences2)) > 0 else 0.0
        
        # Compare average sentence length
        avg_len1 = sum(len(s.split()) for s in sentences1) / len(sentences1) if sentences1 else 0
        avg_len2 = sum(len(s.split()) for s in sentences2) / len(sentences2) if sentences2 else 0
        
        if avg_len1 == 0 and avg_len2 == 0:
            length_similarity = 1.0
        else:
            length_similarity = min(avg_len1, avg_len2) / max(avg_len1, avg_len2) if max(avg_len1, avg_len2) > 0 else 0.0
        
        return (count_similarity + length_similarity) / 2
    
    def _punctuation_similarity(self, text1: str, text2: str) -> float:
        """Calculate punctuation similarity"""
        punct1 = re.findall(r'[^\w\s]', text1)
        punct2 = re.findall(r'[^\w\s]', text2)
        
        if not punct1 and not punct2:
            return 1.0
        
        common_punct = len(set(punct1) & set(punct2))
        total_punct = len(set(punct1) | set(punct2))
        
        return common_punct / total_punct if total_punct > 0 else 0.0
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words"""
        # Simple tokenization
        words = re.findall(r'\b\w+\b', text.lower())
        return words
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_bigrams(self, text: str) -> List[str]:
        """Get bigrams from text"""
        words = self._tokenize(text)
        return [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    
    def _extract_concepts(self, text: str) -> List[str]:
        """Extract concepts from text"""
        # Simple concept extraction based on POS patterns
        words = self._tokenize(text)
        
        # Extract nouns and adjectives as concepts (simplified)
        concepts = []
        for word in words:
            if len(word) > 3:  # Filter short words
                concepts.append(word)
        
        return concepts
    
    def _calculate_word_overlap(self, text1: str, text2: str) -> Dict[str, float]:
        """Calculate word overlap statistics"""
        words1 = set(self._tokenize(text1))
        words2 = set(self._tokenize(text2))
        
        if not words1 and not words2:
            return {'overlap_ratio': 1.0, 'unique_words1': 0, 'unique_words2': 0}
        
        intersection = words1 & words2
        union = words1 | words2
        
        return {
            'overlap_ratio': len(intersection) / len(union) if union else 0.0,
            'unique_words1': len(words1 - words2),
            'unique_words2': len(words2 - words1),
            'common_words': len(intersection)
        }
    
    def _calculate_n_gram_similarities(self, text1: str, text2: str) -> Dict[str, float]:
        """Calculate n-gram similarities"""
        # Unigram similarity
        unigrams1 = set(self._tokenize(text1))
        unigrams2 = set(self._tokenize(text2))
        unigram_sim = len(unigrams1 & unigrams2) / len(unigrams1 | unigrams2) if unigrams1 | unigrams2 else 0.0
        
        # Bigram similarity
        bigrams1 = set(self._get_bigrams(text1))
        bigrams2 = set(self._get_bigrams(text2))
        bigram_sim = len(bigrams1 & bigrams2) / len(bigrams1 | bigrams2) if bigrams1 | bigrams2 else 0.0
        
        # Trigram similarity
        trigrams1 = set(self._get_trigrams(text1))
        trigrams2 = set(self._get_trigrams(text2))
        trigram_sim = len(trigrams1 & trigrams2) / len(trigrams1 | trigrams2) if trigrams1 | trigrams2 else 0.0
        
        return {
            'unigram_similarity': unigram_sim,
            'bigram_similarity': bigram_sim,
            'trigram_similarity': trigram_sim
        }
    
    def _get_trigrams(self, text: str) -> List[str]:
        """Get trigrams from text"""
        words = self._tokenize(text)
        return [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words) - 2)]
    
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
                        "lexical": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.4},
                        "semantic": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.4},
                        "structural": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.2}
                    },
                    "description": "Weights for different similarity components"
                }
            }
        }
        
        return base_schema