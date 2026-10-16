"""
Judge Manager for LLM-as-a-Judge Framework
Central coordination for LLM judges with calibration and bias correction
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class JudgeType(Enum):
    """Types of LLM judges"""
    REASONING = "reasoning"
    CREATIVITY = "creativity"
    FACTUAL = "factual"
    SAFETY = "safety"
    GENERAL = "general"
    CUSTOM = "custom"


@dataclass
class JudgeConfig:
    """Configuration for LLM judge"""
    name: str
    model_provider: str  # "openai", "anthropic", "local", etc.
    model_name: str
    judge_type: JudgeType
    temperature: float = 0.0
    max_tokens: int = 1000
    enable_calibration: bool = True
    enable_bias_correction: bool = True
    cost_per_token: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class JudgeResult:
    """Result from LLM judge evaluation"""
    judge_name: str
    score: float
    reasoning: str
    confidence: float
    bias_indicators: Dict[str, Any]
    calibration_info: Dict[str, Any]
    raw_response: str
    tokens_used: int
    cost: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class JudgeManager:
    """Manages LLM judges with calibration and bias correction"""
    
    def __init__(self):
        self.judges: Dict[str, JudgeConfig] = {}
        self.judge_history: Dict[str, List[JudgeResult]] = {}
        self.calibration_data: Dict[str, Dict[str, Any]] = {}
        self.bias_correction_factors: Dict[str, Dict[str, float]] = {}
        self._initialize_default_judges()
    
    def _initialize_default_judges(self):
        """Initialize default judge configurations"""
        default_judges = {
            'gpt4_reasoning': JudgeConfig(
                name="GPT-4 Reasoning Judge",
                model_provider="openai",
                model_name="gpt-4",
                judge_type=JudgeType.REASONING,
                temperature=0.0,
                cost_per_token=0.00003
            ),
            'claude_creativity': JudgeConfig(
                name="Claude Creative Judge",
                model_provider="anthropic",
                model_name="claude-3-opus",
                judge_type=JudgeType.CREATIVITY,
                temperature=0.1,
                cost_per_token=0.000015
            ),
            'gpt4_factual': JudgeConfig(
                name="GPT-4 Factual Judge",
                model_provider="openai",
                model_name="gpt-4",
                judge_type=JudgeType.FACTUAL,
                temperature=0.0,
                cost_per_token=0.00003
            ),
            'claude_safety': JudgeConfig(
                name="Claude Safety Judge",
                model_provider="anthropic",
                model_name="claude-3-opus",
                judge_type=JudgeType.SAFETY,
                temperature=0.0,
                cost_per_token=0.000015
            )
        }
        
        for name, config in default_judges.items():
            self.register_judge(name, config)
    
    def register_judge(self, name: str, config: JudgeConfig):
        """Register a new judge"""
        self.judges[name] = config
        self.judge_history[name] = []
        self.calibration_data[name] = {}
        self.bias_correction_factors[name] = {}
        logger.info(f"Registered judge: {name}")
    
    def unregister_judge(self, name: str):
        """Unregister a judge"""
        if name in self.judges:
            del self.judges[name]
            del self.judge_history[name]
            del self.calibration_data[name]
            del self.bias_correction_factors[name]
            logger.info(f"Unregistered judge: {name}")
    
    def get_judge(self, name: str) -> Optional[JudgeConfig]:
        """Get judge configuration"""
        return self.judges.get(name)
    
    def list_judges(self) -> List[Dict[str, Any]]:
        """List all registered judges"""
        judges_list = []
        for name, config in self.judges.items():
            judges_list.append({
                'name': name,
                'config': asdict(config),
                'evaluation_count': len(self.judge_history[name]),
                'is_calibrated': bool(self.calibration_data[name]),
                'has_bias_correction': bool(self.bias_correction_factors[name])
            })
        return judges_list
    
    async def evaluate_with_judge(self, judge_name: str, query: str, response: str,
                                 ground_truth: Optional[str] = None,
                                 evaluation_criteria: Optional[str] = None) -> JudgeResult:
        """Evaluate using a specific judge"""
        if judge_name not in self.judges:
            raise ValueError(f"Judge {judge_name} not found")
        
        judge_config = self.judges[judge_name]
        
        # Import judge prompts
        from .judge_prompts import JudgePrompts
        prompt_generator = JudgePrompts()
        
        # Generate appropriate prompt
        judge_prompt = prompt_generator.get_judge_prompt(
            judge_config.judge_type,
            query=query,
            response=response,
            ground_truth=ground_truth,
            evaluation_criteria=evaluation_criteria
        )
        
        # Call LLM judge
        raw_response, tokens_used = await self._call_llm_judge(judge_config, judge_prompt)
        
        # Parse judge response
        parsed_result = self._parse_judge_response(raw_response)
        
        # Apply calibration if enabled
        if judge_config.enable_calibration and judge_name in self.calibration_data:
            parsed_result = self._apply_calibration(judge_name, parsed_result)
        
        # Apply bias correction if enabled
        if judge_config.enable_bias_correction and judge_name in self.bias_correction_factors:
            parsed_result = self._apply_bias_correction(judge_name, parsed_result)
        
        # Detect bias indicators
        bias_indicators = self._detect_bias_indicators(raw_response, query, response)
        
        # Calculate cost
        cost = tokens_used * judge_config.cost_per_token
        
        # Create result
        result = JudgeResult(
            judge_name=judge_name,
            score=parsed_result.get('score', 0.0),
            reasoning=parsed_result.get('reasoning', ''),
            confidence=parsed_result.get('confidence', 0.5),
            bias_indicators=bias_indicators,
            calibration_info=self.calibration_data.get(judge_name, {}),
            raw_response=raw_response,
            tokens_used=tokens_used,
            cost=cost,
            metadata={
                'judge_type': judge_config.judge_type.value,
                'model_provider': judge_config.model_provider,
                'model_name': judge_config.model_name
            }
        )
        
        # Store in history
        self.judge_history[judge_name].append(result)
        
        return result
    
    async def _call_llm_judge(self, config: JudgeConfig, prompt: str) -> Tuple[str, int]:
        """Call the actual LLM judge"""
        # This is a simplified implementation
        # In practice, you'd integrate with actual LLM APIs
        
        if config.model_provider == "openai":
            return await self._call_openai_judge(config, prompt)
        elif config.model_provider == "anthropic":
            return await self._call_anthropic_judge(config, prompt)
        elif config.model_provider == "local":
            return await self._call_local_judge(config, prompt)
        else:
            # Mock response for testing
            mock_response = {
                "score": 0.8,
                "reasoning": "The response demonstrates good understanding and provides accurate information.",
                "confidence": 0.9
            }
            return json.dumps(mock_response), 100
    
    async def _call_openai_judge(self, config: JudgeConfig, prompt: str) -> Tuple[str, int]:
        """Call OpenAI API for judging"""
        try:
            # This would use the actual OpenAI API
            # For now, return mock response
            mock_response = {
                "score": 0.85,
                "reasoning": "OpenAI judge response: Good quality response with accurate information.",
                "confidence": 0.9
            }
            return json.dumps(mock_response), 120
        except Exception as e:
            logger.error(f"OpenAI judge call failed: {e}")
            raise
    
    async def _call_anthropic_judge(self, config: JudgeConfig, prompt: str) -> Tuple[str, int]:
        """Call Anthropic API for judging"""
        try:
            # This would use the actual Anthropic API
            # For now, return mock response
            mock_response = {
                "score": 0.82,
                "reasoning": "Anthropic judge response: Well-structured response with clear reasoning.",
                "confidence": 0.85
            }
            return json.dumps(mock_response), 110
        except Exception as e:
            logger.error(f"Anthropic judge call failed: {e}")
            raise
    
    async def _call_local_judge(self, config: JudgeConfig, prompt: str) -> Tuple[str, int]:
        """Call local model for judging"""
        try:
            # This would integrate with local models (Ollama, etc.)
            # For now, return mock response
            mock_response = {
                "score": 0.75,
                "reasoning": "Local judge response: Adequate response with some room for improvement.",
                "confidence": 0.7
            }
            return json.dumps(mock_response), 95
        except Exception as e:
            logger.error(f"Local judge call failed: {e}")
            raise
    
    def _parse_judge_response(self, raw_response: str) -> Dict[str, Any]:
        """Parse judge response to extract score, reasoning, and confidence"""
        try:
            # Try to parse as JSON first
            parsed = json.loads(raw_response)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        
        # If not JSON, try to extract information using patterns
        import re
        
        result = {
            'score': 0.5,
            'reasoning': raw_response,
            'confidence': 0.5
        }
        
        # Extract score
        score_patterns = [
            r'score[:\s]*([0-9.]+)',
            r'rating[:\s]*([0-9.]+)',
            r'([0-9.]+)\s*out\s*of\s*[0-9]+',
            r'([0-9.]+)/[0-9]+'
        ]
        
        for pattern in score_patterns:
            match = re.search(pattern, raw_response.lower())
            if match:
                try:
                    score = float(match.group(1))
                    # Normalize to [0, 1] if needed
                    if score > 1:
                        score = score / 10.0 if score <= 10 else score / 100.0
                    result['score'] = max(0.0, min(1.0, score))
                    break
                except ValueError:
                    continue
        
        # Extract confidence
        confidence_patterns = [
            r'confidence[:\s]*([0-9.]+)',
            r'certainty[:\s]*([0-9.]+)',
            r'sure[:\s]*([0-9.]+)'
        ]
        
        for pattern in confidence_patterns:
            match = re.search(pattern, raw_response.lower())
            if match:
                try:
                    confidence = float(match.group(1))
                    if confidence > 1:
                        confidence = confidence / 100.0
                    result['confidence'] = max(0.0, min(1.0, confidence))
                    break
                except ValueError:
                    continue
        
        return result
    
    def _apply_calibration(self, judge_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply calibration to judge result"""
        calibration_data = self.calibration_data[judge_name]
        
        if 'score_calibration' in calibration_data:
            calibration_func = calibration_data['score_calibration']
            original_score = result['score']
            calibrated_score = self._calibrate_score(original_score, calibration_func)
            result['score'] = calibrated_score
            result['original_score'] = original_score
        
        return result
    
    def _calibrate_score(self, score: float, calibration_func: Dict[str, Any]) -> float:
        """Apply calibration function to score"""
        # Simple linear calibration for now
        slope = calibration_func.get('slope', 1.0)
        intercept = calibration_func.get('intercept', 0.0)
        
        calibrated = slope * score + intercept
        return max(0.0, min(1.0, calibrated))
    
    def _apply_bias_correction(self, judge_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply bias correction to judge result"""
        correction_factors = self.bias_correction_factors[judge_name]
        
        # Apply various bias corrections
        if 'length_bias' in correction_factors:
            # Correct for length bias
            length_factor = correction_factors['length_bias']
            result['score'] = result['score'] * (1 + length_factor)
        
        if 'position_bias' in correction_factors:
            # Correct for position bias
            position_factor = correction_factors['position_bias']
            result['score'] = result['score'] * (1 + position_factor)
        
        # Ensure score stays in [0, 1] range
        result['score'] = max(0.0, min(1.0, result['score']))
        
        return result
    
    def _detect_bias_indicators(self, raw_response: str, query: str, response: str) -> Dict[str, Any]:
        """Detect potential bias indicators in judge response"""
        indicators = {}
        
        # Length bias
        response_length = len(response)
        if response_length < 50:
            indicators['short_response_bias'] = True
        elif response_length > 1000:
            indicators['long_response_bias'] = True
        
        # Keyword bias
        positive_keywords = ['excellent', 'perfect', 'outstanding', 'brilliant']
        negative_keywords = ['poor', 'terrible', 'awful', 'horrible']
        
        positive_count = sum(1 for keyword in positive_keywords if keyword in raw_response.lower())
        negative_count = sum(1 for keyword in negative_keywords if keyword in raw_response.lower())
        
        if positive_count > 2:
            indicators['positive_keyword_bias'] = True
        if negative_count > 2:
            indicators['negative_keyword_bias'] = True
        
        # Repetition bias
        import re
        words = re.findall(r'\w+', raw_response.lower())
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        most_frequent = max(word_freq.values()) if word_freq else 0
        if most_frequent > len(words) * 0.1:
            indicators['repetition_bias'] = True
        
        return indicators
    
    async def evaluate_with_multiple_judges(self, judge_names: List[str], query: str, response: str,
                                          ground_truth: Optional[str] = None,
                                          evaluation_criteria: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate using multiple judges"""
        tasks = []
        
        for judge_name in judge_names:
            if judge_name in self.judges:
                task = self.evaluate_with_judge(
                    judge_name, query, response, ground_truth, evaluation_criteria
                )
                tasks.append((judge_name, task))
        
        if not tasks:
            raise ValueError("No valid judges found")
        
        # Run evaluations concurrently
        results = {}
        for judge_name, task in tasks:
            try:
                result = await task
                results[judge_name] = result
            except Exception as e:
                logger.error(f"Judge {judge_name} evaluation failed: {e}")
                results[judge_name] = None
        
        # Calculate ensemble metrics
        valid_results = [r for r in results.values() if r is not None]
        
        if not valid_results:
            return {'error': 'All judge evaluations failed'}
        
        scores = [r.score for r in valid_results]
        confidences = [r.confidence for r in valid_results]
        
        ensemble_score = sum(scores) / len(scores)
        ensemble_confidence = sum(confidences) / len(confidences)
        score_variance = sum((s - ensemble_score) ** 2 for s in scores) / len(scores)
        
        return {
            'individual_results': results,
            'ensemble_metrics': {
                'score': ensemble_score,
                'confidence': ensemble_confidence,
                'score_variance': score_variance,
                'agreement_level': 'high' if score_variance < 0.01 else 'medium' if score_variance < 0.05 else 'low',
                'judge_count': len(valid_results)
            }
        }
    
    def get_judge_statistics(self, judge_name: str) -> Dict[str, Any]:
        """Get statistics for a specific judge"""
        if judge_name not in self.judge_history:
            return {'error': 'Judge not found'}
        
        history = self.judge_history[judge_name]
        
        if not history:
            return {'warning': 'No evaluation history'}
        
        scores = [r.score for r in history]
        confidences = [r.confidence for r in history]
        costs = [r.cost for r in history]
        
        return {
            'total_evaluations': len(history),
            'average_score': sum(scores) / len(scores),
            'score_std_dev': (sum((s - sum(scores) / len(scores)) ** 2 for s in scores) / len(scores)) ** 0.5,
            'average_confidence': sum(confidences) / len(confidences),
            'total_cost': sum(costs),
            'average_cost_per_evaluation': sum(costs) / len(costs),
            'total_tokens': sum(r.tokens_used for r in history),
            'bias_indicators_frequency': self._calculate_bias_frequency(history)
        }
    
    def _calculate_bias_frequency(self, history: List[JudgeResult]) -> Dict[str, float]:
        """Calculate frequency of bias indicators"""
        bias_counts = {}
        total_evaluations = len(history)
        
        for result in history:
            for bias_type, present in result.bias_indicators.items():
                if present:
                    bias_counts[bias_type] = bias_counts.get(bias_type, 0) + 1
        
        return {
            bias_type: count / total_evaluations
            for bias_type, count in bias_counts.items()
        }
    
    def export_judge_data(self, judge_name: Optional[str] = None) -> str:
        """Export judge data and history"""
        if judge_name:
            if judge_name not in self.judges:
                return json.dumps({'error': 'Judge not found'})
            
            data = {
                'judge_config': asdict(self.judges[judge_name]),
                'history': [asdict(r) for r in self.judge_history[judge_name]],
                'calibration_data': self.calibration_data.get(judge_name, {}),
                'bias_correction_factors': self.bias_correction_factors.get(judge_name, {}),
                'statistics': self.get_judge_statistics(judge_name)
            }
        else:
            data = {
                'judges': {name: asdict(config) for name, config in self.judges.items()},
                'history': {name: [asdict(r) for r in history] for name, history in self.judge_history.items()},
                'calibration_data': self.calibration_data,
                'bias_correction_factors': self.bias_correction_factors
            }
        
        return json.dumps(data, indent=2)
    
    def clear_judge_history(self, judge_name: Optional[str] = None):
        """Clear judge evaluation history"""
        if judge_name:
            if judge_name in self.judge_history:
                self.judge_history[judge_name].clear()
        else:
            for history in self.judge_history.values():
                history.clear()