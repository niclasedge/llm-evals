"""
Pattern recognition tests for intelligence evaluation.
Tests ability to identify and continue various types of patterns.
"""

import re
from typing import Dict, Any, List, Optional
from ..base_test import IntelligenceTestBase, IntelligenceTestResult, IntelligenceCategory, TestStatus


class SequencePatternTest(IntelligenceTestBase):
    """Test sequence pattern recognition."""
    
    def __init__(self, name: str, description: str, config: Dict[str, Any], complexity_level: int = 1):
        super().__init__(name, description, config, IntelligenceCategory.PATTERN_RECOGNITION, complexity_level)
    
    async def run(self, client: Any, model: str, **kwargs) -> IntelligenceTestResult:
        """Run sequence pattern test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        expected_answer = self.get_expected_result()
        
        # Get response from client
        response = await self._get_response(client, prompt, system_prompt, model)
        
        if not response:
            return IntelligenceTestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No response from model",
                intelligence_category=self.intelligence_category,
                complexity_level=self.complexity_level
            )
        
        # Extract pattern and next value
        identified_pattern = self.extract_pattern_description(response)
        next_value = self.extract_next_value(response)
        
        # Calculate scores
        pattern_score = self.calculate_pattern_score(response, expected_answer)
        explanation_score = self.analyze_explanation_quality(response)
        coherence_score = self.analyze_logical_coherence(response)
        
        # Overall score
        overall_score = (pattern_score * 0.5 + explanation_score * 0.3 + coherence_score * 0.2)
        
        status = TestStatus.PASSED if overall_score > 0.7 else TestStatus.FAILED
        
        return IntelligenceTestResult(
            test_name=self.name,
            status=status,
            score=overall_score,
            details={
                'prompt': prompt,
                'response': response,
                'model': model,
                'identified_pattern': identified_pattern,
                'next_value': next_value,
                'expected_answer': expected_answer,
                'pattern_score': pattern_score,
                'explanation_score': explanation_score,
                'identifies_rule': self.identifies_pattern_rule(response),
                'shows_reasoning': self.shows_pattern_reasoning(response),
                'key_concepts': self.extract_key_concepts(response),
                'complexity_measure': self.measure_complexity(response)
            },
            intelligence_category=self.intelligence_category,
            complexity_level=self.complexity_level,
            logical_coherence=coherence_score
        )
    
    def extract_pattern_description(self, response: str) -> Optional[str]:
        """Extract pattern description from response."""
        pattern_indicators = [
            r'pattern is\s*([^.]+)',
            r'sequence\s*(?:follows|is)\s*([^.]+)',
            r'rule is\s*([^.]+)',
            r'formula is\s*([^.]+)',
            r'each term\s*([^.]+)'
        ]
        
        for pattern in pattern_indicators:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_next_value(self, response: str) -> Optional[str]:
        """Extract the next value in sequence."""
        # Look for explicit next value statements
        next_patterns = [
            r'next\s*(?:term|value|number)\s*is\s*([^.]+)',
            r'answer is\s*([^.]+)',
            r'therefore\s*([^.]+)',
            r'so\s*([^.]+)'
        ]
        
        for pattern in next_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Look for numbers that might be the answer
        numbers = re.findall(r'\d+', response)
        if numbers:
            return numbers[-1]
        
        return None
    
    def calculate_pattern_score(self, response: str, expected: Any) -> float:
        """Calculate pattern recognition score."""
        score = 0.0
        
        # Correct next value
        next_value = self.extract_next_value(response)
        if next_value and expected:
            try:
                if str(expected).lower() in next_value.lower():
                    score += 0.5
            except:
                pass
        
        # Identifies pattern rule
        if self.identifies_pattern_rule(response):
            score += 0.3
        
        # Shows reasoning
        if self.shows_pattern_reasoning(response):
            score += 0.2
        
        return min(score, 1.0)
    
    def analyze_explanation_quality(self, response: str) -> float:
        """Analyze quality of pattern explanation."""
        score = 0.0
        
        # Uses mathematical terms
        math_terms = [
            'multiply', 'divide', 'add', 'subtract', 'increase', 'decrease',
            'factor', 'ratio', 'difference', 'sum', 'product', 'quotient'
        ]
        
        term_count = 0
        for term in math_terms:
            if re.search(f'\\b{term}\\b', response, re.IGNORECASE):
                term_count += 1
        
        score += min(term_count / 5, 0.4)
        
        # Explains the process
        if self.explains_process(response):
            score += 0.3
        
        # Gives examples
        if self.gives_examples(response):
            score += 0.3
        
        return min(score, 1.0)
    
    def identifies_pattern_rule(self, response: str) -> bool:
        """Check if response identifies the pattern rule."""
        rule_indicators = [
            'rule', 'pattern', 'formula', 'sequence', 'progression',
            'multiply', 'divide', 'add', 'subtract', 'increase', 'decrease'
        ]
        
        for indicator in rule_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def shows_pattern_reasoning(self, response: str) -> bool:
        """Check if response shows pattern reasoning."""
        reasoning_indicators = [
            'because', 'since', 'therefore', 'thus', 'hence',
            'notice', 'observe', 'see that', 'looking at',
            'from.*to', 'each.*is'
        ]
        
        for indicator in reasoning_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                return True
        
        return False
    
    def explains_process(self, response: str) -> bool:
        """Check if response explains the process."""
        process_indicators = [
            'step', 'first', 'then', 'next', 'finally',
            'process', 'method', 'way', 'how'
        ]
        
        for indicator in process_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def gives_examples(self, response: str) -> bool:
        """Check if response gives examples."""
        example_indicators = [
            'example', 'instance', 'case', 'illustration',
            'for example', 'such as', 'like', 'e.g.'
        ]
        
        for indicator in example_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                return True
        
        return False


class SpatialPatternTest(IntelligenceTestBase):
    """Test spatial pattern recognition."""
    
    def __init__(self, name: str, description: str, config: Dict[str, Any], complexity_level: int = 1):
        super().__init__(name, description, config, IntelligenceCategory.SPATIAL_REASONING, complexity_level)
    
    async def run(self, client: Any, model: str, **kwargs) -> IntelligenceTestResult:
        """Run spatial pattern test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        expected_answer = self.get_expected_result()
        
        # Get response from client
        response = await self._get_response(client, prompt, system_prompt, model)
        
        if not response:
            return IntelligenceTestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No response from model",
                intelligence_category=self.intelligence_category,
                complexity_level=self.complexity_level
            )
        
        # Analyze spatial reasoning
        spatial_analysis = self.analyze_spatial_reasoning(response)
        
        # Calculate scores
        spatial_score = self.calculate_spatial_score(response, expected_answer)
        visualization_score = self.analyze_visualization_ability(response)
        coherence_score = self.analyze_logical_coherence(response)
        
        # Overall score
        overall_score = (spatial_score * 0.5 + visualization_score * 0.3 + coherence_score * 0.2)
        
        status = TestStatus.PASSED if overall_score > 0.6 else TestStatus.FAILED
        
        return IntelligenceTestResult(
            test_name=self.name,
            status=status,
            score=overall_score,
            details={
                'prompt': prompt,
                'response': response,
                'model': model,
                'expected_answer': expected_answer,
                'spatial_analysis': spatial_analysis,
                'spatial_score': spatial_score,
                'visualization_score': visualization_score,
                'uses_spatial_terms': self.uses_spatial_terms(response),
                'describes_transformations': self.describes_transformations(response),
                'key_concepts': self.extract_key_concepts(response),
                'complexity_measure': self.measure_complexity(response)
            },
            intelligence_category=self.intelligence_category,
            complexity_level=self.complexity_level,
            logical_coherence=coherence_score
        )
    
    def analyze_spatial_reasoning(self, response: str) -> Dict[str, Any]:
        """Analyze spatial reasoning in response."""
        analysis = {
            'uses_spatial_terms': self.uses_spatial_terms(response),
            'describes_position': self.describes_position(response),
            'describes_movement': self.describes_movement(response),
            'describes_transformation': self.describes_transformations(response),
            'uses_directions': self.uses_directions(response)
        }
        return analysis
    
    def calculate_spatial_score(self, response: str, expected: Any) -> float:
        """Calculate spatial reasoning score."""
        score = 0.0
        
        # Correct answer
        if expected and isinstance(expected, str):
            if expected.lower() in response.lower():
                score += 0.4
        
        # Uses spatial terms
        if self.uses_spatial_terms(response):
            score += 0.3
        
        # Describes transformations
        if self.describes_transformations(response):
            score += 0.2
        
        # Uses directions
        if self.uses_directions(response):
            score += 0.1
        
        return min(score, 1.0)
    
    def analyze_visualization_ability(self, response: str) -> float:
        """Analyze visualization ability in response."""
        score = 0.0
        
        # Visualization terms
        viz_terms = [
            'visualize', 'imagine', 'picture', 'see', 'look',
            'view', 'perspective', 'angle', 'dimension'
        ]
        
        term_count = 0
        for term in viz_terms:
            if re.search(f'\\b{term}\\b', response, re.IGNORECASE):
                term_count += 1
        
        score += min(term_count / 5, 0.5)
        
        # Describes mental imagery
        if self.describes_mental_imagery(response):
            score += 0.3
        
        # Uses comparative descriptions
        if self.uses_comparative_descriptions(response):
            score += 0.2
        
        return min(score, 1.0)
    
    def uses_spatial_terms(self, response: str) -> bool:
        """Check if response uses spatial terms."""
        spatial_terms = [
            'left', 'right', 'up', 'down', 'above', 'below',
            'inside', 'outside', 'center', 'corner', 'edge',
            'horizontal', 'vertical', 'diagonal', 'parallel'
        ]
        
        for term in spatial_terms:
            if re.search(f'\\b{term}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def describes_position(self, response: str) -> bool:
        """Check if response describes position."""
        position_indicators = [
            'position', 'location', 'place', 'situated', 'located',
            'placed', 'positioned', 'at', 'on', 'in'
        ]
        
        for indicator in position_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def describes_movement(self, response: str) -> bool:
        """Check if response describes movement."""
        movement_indicators = [
            'move', 'shift', 'rotate', 'turn', 'flip', 'slide',
            'translate', 'transform', 'change', 'motion'
        ]
        
        for indicator in movement_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def describes_transformations(self, response: str) -> bool:
        """Check if response describes transformations."""
        transformation_indicators = [
            'rotate', 'flip', 'mirror', 'reflect', 'scale',
            'resize', 'transform', 'change', 'modify'
        ]
        
        for indicator in transformation_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def uses_directions(self, response: str) -> bool:
        """Check if response uses directional terms."""
        direction_terms = [
            'north', 'south', 'east', 'west', 'clockwise', 'counterclockwise',
            'forward', 'backward', 'upward', 'downward'
        ]
        
        for term in direction_terms:
            if re.search(f'\\b{term}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def describes_mental_imagery(self, response: str) -> bool:
        """Check if response describes mental imagery."""
        imagery_indicators = [
            'imagine', 'picture', 'visualize', 'see in mind',
            'mental image', 'envision', 'conceive'
        ]
        
        for indicator in imagery_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                return True
        
        return False
    
    def uses_comparative_descriptions(self, response: str) -> bool:
        """Check if response uses comparative descriptions."""
        comparative_indicators = [
            'bigger', 'smaller', 'larger', 'wider', 'narrower',
            'taller', 'shorter', 'similar', 'different', 'same'
        ]
        
        for indicator in comparative_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False


class ConceptualPatternTest(IntelligenceTestBase):
    """Test conceptual pattern recognition."""
    
    def __init__(self, name: str, description: str, config: Dict[str, Any], complexity_level: int = 1):
        super().__init__(name, description, config, IntelligenceCategory.ABSTRACT_REASONING, complexity_level)
    
    async def run(self, client: Any, model: str, **kwargs) -> IntelligenceTestResult:
        """Run conceptual pattern test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        expected_answer = self.get_expected_result()
        
        # Get response from client
        response = await self._get_response(client, prompt, system_prompt, model)
        
        if not response:
            return IntelligenceTestResult(
                test_name=self.name,
                status=TestStatus.ERROR,
                error="No response from model",
                intelligence_category=self.intelligence_category,
                complexity_level=self.complexity_level
            )
        
        # Analyze conceptual reasoning
        conceptual_analysis = self.analyze_conceptual_reasoning(response)
        
        # Calculate scores
        concept_score = self.calculate_conceptual_score(response, expected_answer)
        creativity_score = self.analyze_creativity(response)
        coherence_score = self.analyze_logical_coherence(response)
        
        # Overall score
        overall_score = (concept_score * 0.5 + creativity_score * 0.3 + coherence_score * 0.2)
        
        status = TestStatus.PASSED if overall_score > 0.6 else TestStatus.FAILED
        
        return IntelligenceTestResult(
            test_name=self.name,
            status=status,
            score=overall_score,
            details={
                'prompt': prompt,
                'response': response,
                'model': model,
                'expected_answer': expected_answer,
                'conceptual_analysis': conceptual_analysis,
                'concept_score': concept_score,
                'identifies_themes': self.identifies_themes(response),
                'makes_connections': self.makes_conceptual_connections(response),
                'key_concepts': self.extract_key_concepts(response),
                'complexity_measure': self.measure_complexity(response)
            },
            intelligence_category=self.intelligence_category,
            complexity_level=self.complexity_level,
            creativity_score=creativity_score,
            logical_coherence=coherence_score
        )
    
    def analyze_conceptual_reasoning(self, response: str) -> Dict[str, Any]:
        """Analyze conceptual reasoning in response."""
        analysis = {
            'identifies_themes': self.identifies_themes(response),
            'makes_connections': self.makes_conceptual_connections(response),
            'uses_categories': self.uses_categories(response),
            'shows_abstraction': self.shows_abstraction(response),
            'identifies_relationships': self.identifies_relationships(response)
        }
        return analysis
    
    def calculate_conceptual_score(self, response: str, expected: Any) -> float:
        """Calculate conceptual reasoning score."""
        score = 0.0
        
        # Correct concept identification
        if expected and isinstance(expected, str):
            if expected.lower() in response.lower():
                score += 0.4
        
        # Identifies themes
        if self.identifies_themes(response):
            score += 0.3
        
        # Makes connections
        if self.makes_conceptual_connections(response):
            score += 0.2
        
        # Shows abstraction
        if self.shows_abstraction(response):
            score += 0.1
        
        return min(score, 1.0)
    
    def identifies_themes(self, response: str) -> bool:
        """Check if response identifies themes."""
        theme_indicators = [
            'theme', 'topic', 'subject', 'concept', 'idea',
            'notion', 'principle', 'element', 'aspect'
        ]
        
        for indicator in theme_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def makes_conceptual_connections(self, response: str) -> bool:
        """Check if response makes conceptual connections."""
        connection_indicators = [
            'connect', 'relate', 'link', 'associate', 'bind',
            'relationship', 'connection', 'association', 'correlation'
        ]
        
        for indicator in connection_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def uses_categories(self, response: str) -> bool:
        """Check if response uses categories."""
        category_indicators = [
            'category', 'type', 'kind', 'class', 'group',
            'classification', 'taxonomy', 'family'
        ]
        
        for indicator in category_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def shows_abstraction(self, response: str) -> bool:
        """Check if response shows abstraction."""
        abstraction_indicators = [
            'abstract', 'concept', 'generalize', 'universal',
            'principle', 'theory', 'model', 'framework'
        ]
        
        for indicator in abstraction_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def identifies_relationships(self, response: str) -> bool:
        """Check if response identifies relationships."""
        relationship_indicators = [
            'relationship', 'relation', 'interaction', 'dependence',
            'correlation', 'causation', 'influence', 'effect'
        ]
        
        for indicator in relationship_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False


class PatternTests:
    """Collection of pattern recognition tests."""
    
    @staticmethod
    def get_sequence_pattern_test() -> SequencePatternTest:
        """Get sequence pattern test."""
        config = {
            'prompt': 'What comes next in this sequence: 3, 6, 12, 24, 48, ? Explain the pattern and your reasoning.',
            'system_prompt': 'You are a pattern recognition expert. Identify patterns clearly and explain your reasoning step by step.',
            'expected_result': '96',
            'min_length': 50
        }
        return SequencePatternTest(
            name='sequence_pattern_doubling',
            description='Sequence pattern with doubling rule',
            config=config,
            complexity_level=2
        )
    
    @staticmethod
    def get_spatial_pattern_test() -> SpatialPatternTest:
        """Get spatial pattern test."""
        config = {
            'prompt': 'Imagine a 3x3 grid. In the first row, there are circles in positions 1 and 3. In the second row, there are squares in positions 2 and 3. What should be in the third row to complete the pattern?',
            'system_prompt': 'You are a spatial reasoning expert. Analyze patterns in spatial arrangements and describe your visualization process.',
            'expected_result': 'triangle',
            'min_length': 80
        }
        return SpatialPatternTest(
            name='spatial_pattern_grid',
            description='Spatial pattern in grid arrangement',
            config=config,
            complexity_level=3
        )
    
    @staticmethod
    def get_conceptual_pattern_test() -> ConceptualPatternTest:
        """Get conceptual pattern test."""
        config = {
            'prompt': 'What do these have in common: Democracy, Recipe, Orchestra, Ecosystem? Identify the underlying concept that connects them.',
            'system_prompt': 'You are an expert in conceptual analysis. Identify abstract patterns and relationships between different concepts.',
            'expected_result': 'system',
            'min_length': 70
        }
        return ConceptualPatternTest(
            name='conceptual_pattern_systems',
            description='Conceptual pattern recognition with systems thinking',
            config=config,
            complexity_level=4
        )
    
    @staticmethod
    def get_complex_sequence_test() -> SequencePatternTest:
        """Get complex sequence test."""
        config = {
            'prompt': 'Find the pattern: 1, 4, 9, 16, 25, 36, ? What comes next and what is the underlying mathematical relationship?',
            'system_prompt': 'You are a mathematics expert. Identify complex patterns and explain the mathematical principles involved.',
            'expected_result': '49',
            'min_length': 60
        }
        return SequencePatternTest(
            name='complex_sequence_squares',
            description='Complex sequence with perfect squares',
            config=config,
            complexity_level=3
        )
    
    @staticmethod
    def get_all_tests() -> List[IntelligenceTestBase]:
        """Get all pattern recognition tests."""
        return [
            PatternTests.get_sequence_pattern_test(),
            PatternTests.get_spatial_pattern_test(),
            PatternTests.get_conceptual_pattern_test(),
            PatternTests.get_complex_sequence_test()
        ]