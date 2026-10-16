"""
Logic and reasoning tests for intelligence evaluation.
Tests mathematical, verbal, and abstract reasoning capabilities.
"""

import re
from typing import Dict, Any, List, Optional
from ..base_test import IntelligenceTestBase, IntelligenceTestResult, IntelligenceCategory, TestStatus


class MathematicalLogicTest(IntelligenceTestBase):
    """Test mathematical logic and reasoning."""
    
    def __init__(self, name: str, description: str, config: Dict[str, Any], complexity_level: int = 1):
        super().__init__(name, description, config, IntelligenceCategory.MATHEMATICAL_REASONING, complexity_level)
    
    async def run(self, client: Any, model: str, **kwargs) -> IntelligenceTestResult:
        """Run mathematical logic test."""
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
        
        # Extract numerical answer
        extracted_answer = self.extract_numerical_answer(response)
        
        # Calculate scores
        accuracy_score = self.calculate_accuracy(extracted_answer, expected_answer)
        method_score = self.analyze_solution_method(response)
        coherence_score = self.analyze_logical_coherence(response)
        
        # Overall score
        overall_score = (accuracy_score * 0.5 + method_score * 0.3 + coherence_score * 0.2)
        
        status = TestStatus.PASSED if overall_score > 0.7 else TestStatus.FAILED
        
        return IntelligenceTestResult(
            test_name=self.name,
            status=status,
            score=overall_score,
            details={
                'prompt': prompt,
                'response': response,
                'model': model,
                'extracted_answer': extracted_answer,
                'expected_answer': expected_answer,
                'accuracy_score': accuracy_score,
                'method_score': method_score,
                'shows_work': self.shows_mathematical_work(response),
                'logical_steps': self.count_logical_steps(response),
                'key_concepts': self.extract_key_concepts(response),
                'complexity_measure': self.measure_complexity(response)
            },
            intelligence_category=self.intelligence_category,
            complexity_level=self.complexity_level,
            logical_coherence=coherence_score
        )
    
    def extract_numerical_answer(self, response: str) -> Optional[float]:
        """Extract numerical answer from response."""
        if not response:
            return None
        
        # Look for explicit answer statements
        answer_patterns = [
            r'answer is\s*(-?\d+\.?\d*)',
            r'solution is\s*(-?\d+\.?\d*)',
            r'result is\s*(-?\d+\.?\d*)',
            r'equals?\s*(-?\d+\.?\d*)',
            r'=\s*(-?\d+\.?\d*)',
            r'final answer:\s*(-?\d+\.?\d*)'
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        # Look for numbers at the end of response
        numbers = re.findall(r'-?\d+\.?\d*', response)
        if numbers:
            try:
                return float(numbers[-1])
            except ValueError:
                pass
        
        return None
    
    def calculate_accuracy(self, extracted: Optional[float], expected: Any) -> float:
        """Calculate accuracy score."""
        if extracted is None or expected is None:
            return 0.0
        
        try:
            expected_num = float(expected)
            if abs(extracted - expected_num) < 0.001:
                return 1.0
            elif abs(extracted - expected_num) / max(abs(expected_num), 1) < 0.05:
                return 0.8
            elif abs(extracted - expected_num) / max(abs(expected_num), 1) < 0.1:
                return 0.6
            else:
                return 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def shows_mathematical_work(self, response: str) -> bool:
        """Check if response shows mathematical work."""
        work_indicators = [
            r'\d+\s*[+\-*/]\s*\d+',
            r'step\s*\d+',
            r'first[,\s].*calculate',
            r'then[,\s].*find',
            r'substitute',
            r'solve for',
            r'equation',
            r'formula'
        ]
        
        for pattern in work_indicators:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        
        return False
    
    def count_logical_steps(self, response: str) -> int:
        """Count logical steps in solution."""
        step_patterns = [
            r'step\s*\d+',
            r'first[,\s]',
            r'then[,\s]',
            r'next[,\s]',
            r'finally[,\s]',
            r'\d+\.\s*[A-Z]',
            r'therefore[,\s]',
            r'so[,\s]'
        ]
        
        steps = 0
        for pattern in step_patterns:
            steps += len(re.findall(pattern, response, re.IGNORECASE))
        
        return steps
    
    def analyze_solution_method(self, response: str) -> float:
        """Analyze quality of solution method."""
        method_score = 0.0
        
        # Shows work
        if self.shows_mathematical_work(response):
            method_score += 0.4
        
        # Logical progression
        step_count = self.count_logical_steps(response)
        if step_count >= 3:
            method_score += 0.3
        elif step_count >= 2:
            method_score += 0.2
        elif step_count >= 1:
            method_score += 0.1
        
        # Uses appropriate terminology
        math_terms = [
            'calculate', 'solve', 'equation', 'formula', 'variable',
            'substitute', 'simplify', 'factor', 'multiply', 'divide'
        ]
        
        term_count = 0
        for term in math_terms:
            if re.search(term, response, re.IGNORECASE):
                term_count += 1
        
        method_score += min(term_count / len(math_terms), 0.3)
        
        return min(method_score, 1.0)


class VerbalLogicTest(IntelligenceTestBase):
    """Test verbal logic and reasoning."""
    
    def __init__(self, name: str, description: str, config: Dict[str, Any], complexity_level: int = 1):
        super().__init__(name, description, config, IntelligenceCategory.LOGICAL_REASONING, complexity_level)
    
    async def run(self, client: Any, model: str, **kwargs) -> IntelligenceTestResult:
        """Run verbal logic test."""
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
        
        # Analyze logical structure
        logical_structure = self.analyze_logical_structure(response)
        
        # Calculate scores
        logic_score = self.calculate_logic_score(response, expected_answer)
        structure_score = self.calculate_structure_score(logical_structure)
        coherence_score = self.analyze_logical_coherence(response)
        
        # Overall score
        overall_score = (logic_score * 0.4 + structure_score * 0.3 + coherence_score * 0.3)
        
        status = TestStatus.PASSED if overall_score > 0.7 else TestStatus.FAILED
        
        return IntelligenceTestResult(
            test_name=self.name,
            status=status,
            score=overall_score,
            details={
                'prompt': prompt,
                'response': response,
                'model': model,
                'expected_answer': expected_answer,
                'logical_structure': logical_structure,
                'logic_score': logic_score,
                'structure_score': structure_score,
                'uses_premises': self.uses_premises(response),
                'identifies_fallacies': self.identifies_fallacies(response),
                'key_concepts': self.extract_key_concepts(response),
                'complexity_measure': self.measure_complexity(response)
            },
            intelligence_category=self.intelligence_category,
            complexity_level=self.complexity_level,
            logical_coherence=coherence_score
        )
    
    def analyze_logical_structure(self, response: str) -> Dict[str, Any]:
        """Analyze logical structure of response."""
        structure = {
            'has_premises': False,
            'has_reasoning': False,
            'has_conclusion': False,
            'uses_connectives': False,
            'identifies_assumptions': False,
            'considers_alternatives': False
        }
        
        # Check for premises
        premise_indicators = ['given', 'if', 'assume', 'premise', 'since', 'because']
        for indicator in premise_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                structure['has_premises'] = True
                break
        
        # Check for reasoning
        reasoning_indicators = ['therefore', 'thus', 'hence', 'consequently', 'so', 'leads to']
        for indicator in reasoning_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                structure['has_reasoning'] = True
                break
        
        # Check for conclusion
        conclusion_indicators = ['conclusion', 'answer', 'result', 'therefore', 'in summary']
        for indicator in conclusion_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                structure['has_conclusion'] = True
                break
        
        # Check for logical connectives
        connectives = ['and', 'or', 'not', 'if.*then', 'only if', 'unless', 'either.*or']
        for connective in connectives:
            if re.search(connective, response, re.IGNORECASE):
                structure['uses_connectives'] = True
                break
        
        # Check for assumption identification
        assumption_indicators = ['assume', 'assumption', 'presume', 'take for granted']
        for indicator in assumption_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                structure['identifies_assumptions'] = True
                break
        
        # Check for alternative considerations
        alternative_indicators = ['however', 'alternatively', 'on the other hand', 'but', 'although']
        for indicator in alternative_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                structure['considers_alternatives'] = True
                break
        
        return structure
    
    def calculate_logic_score(self, response: str, expected: Any) -> float:
        """Calculate logic reasoning score."""
        score = 0.0
        
        # Correct conclusion
        if expected and isinstance(expected, str):
            if expected.lower() in response.lower():
                score += 0.5
        
        # Identifies key logical elements
        if self.identifies_fallacies(response):
            score += 0.3
        
        # Uses premises correctly
        if self.uses_premises(response):
            score += 0.2
        
        return min(score, 1.0)
    
    def calculate_structure_score(self, structure: Dict[str, Any]) -> float:
        """Calculate score based on logical structure."""
        return sum(structure.values()) / len(structure)
    
    def uses_premises(self, response: str) -> bool:
        """Check if response uses given premises."""
        premise_keywords = self.config.get('premise_keywords', [])
        if not premise_keywords:
            return True
        
        response_lower = response.lower()
        for keyword in premise_keywords:
            if keyword.lower() in response_lower:
                return True
        
        return False
    
    def identifies_fallacies(self, response: str) -> bool:
        """Check if response identifies logical fallacies."""
        fallacy_indicators = [
            'fallacy', 'invalid', 'unsound', 'incorrect', 'false premise',
            'assumption', 'contradiction', 'inconsistent', 'flawed logic'
        ]
        
        for indicator in fallacy_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False


class AbstractReasoningTest(IntelligenceTestBase):
    """Test abstract reasoning capabilities."""
    
    def __init__(self, name: str, description: str, config: Dict[str, Any], complexity_level: int = 1):
        super().__init__(name, description, config, IntelligenceCategory.ABSTRACT_REASONING, complexity_level)
    
    async def run(self, client: Any, model: str, **kwargs) -> IntelligenceTestResult:
        """Run abstract reasoning test."""
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
        
        # Analyze abstract thinking
        abstraction_level = self.analyze_abstraction_level(response)
        
        # Calculate scores
        reasoning_score = self.calculate_abstract_reasoning_score(response, expected_answer)
        creativity_score = self.analyze_creativity(response)
        coherence_score = self.analyze_logical_coherence(response)
        
        # Overall score
        overall_score = (reasoning_score * 0.5 + creativity_score * 0.3 + coherence_score * 0.2)
        
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
                'abstraction_level': abstraction_level,
                'reasoning_score': reasoning_score,
                'uses_analogies': self.uses_analogies(response),
                'identifies_patterns': self.identifies_abstract_patterns(response),
                'generalizes_concepts': self.generalizes_concepts(response),
                'key_concepts': self.extract_key_concepts(response),
                'complexity_measure': self.measure_complexity(response)
            },
            intelligence_category=self.intelligence_category,
            complexity_level=self.complexity_level,
            creativity_score=creativity_score,
            logical_coherence=coherence_score
        )
    
    def analyze_abstraction_level(self, response: str) -> int:
        """Analyze level of abstraction in response."""
        abstraction_level = 0
        
        # Abstract concept indicators
        abstract_indicators = [
            'concept', 'principle', 'theory', 'model', 'framework',
            'paradigm', 'abstract', 'generalize', 'categorize', 'classify'
        ]
        
        for indicator in abstract_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                abstraction_level += 1
        
        # Metaphorical thinking
        metaphor_indicators = [
            'like', 'similar to', 'analogous', 'metaphor', 'represents',
            'symbolizes', 'embodies', 'exemplifies'
        ]
        
        for indicator in metaphor_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                abstraction_level += 1
        
        return min(abstraction_level, 5)
    
    def calculate_abstract_reasoning_score(self, response: str, expected: Any) -> float:
        """Calculate abstract reasoning score."""
        score = 0.0
        
        # Correct reasoning
        if expected and isinstance(expected, str):
            if expected.lower() in response.lower():
                score += 0.4
        
        # Uses analogies
        if self.uses_analogies(response):
            score += 0.3
        
        # Identifies patterns
        if self.identifies_abstract_patterns(response):
            score += 0.2
        
        # Generalizes concepts
        if self.generalizes_concepts(response):
            score += 0.1
        
        return min(score, 1.0)
    
    def uses_analogies(self, response: str) -> bool:
        """Check if response uses analogies."""
        analogy_indicators = [
            'like', 'similar to', 'analogous', 'comparable to', 'reminds me of',
            'parallel to', 'corresponds to', 'mirrors', 'reflects'
        ]
        
        for indicator in analogy_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                return True
        
        return False
    
    def identifies_abstract_patterns(self, response: str) -> bool:
        """Check if response identifies abstract patterns."""
        pattern_indicators = [
            'pattern', 'structure', 'relationship', 'connection', 'link',
            'correlation', 'association', 'tendency', 'trend', 'rule'
        ]
        
        for indicator in pattern_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def generalizes_concepts(self, response: str) -> bool:
        """Check if response generalizes concepts."""
        generalization_indicators = [
            'generally', 'typically', 'usually', 'often', 'tends to',
            'in general', 'as a rule', 'broadly speaking', 'overall',
            'category', 'class', 'type', 'kind'
        ]
        
        for indicator in generalization_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                return True
        
        return False


class LogicTests:
    """Collection of logic and reasoning tests."""
    
    @staticmethod
    def get_mathematical_logic_test() -> MathematicalLogicTest:
        """Get mathematical logic test."""
        config = {
            'prompt': 'A car travels 120 miles in 2 hours, then 180 miles in 3 hours. What is the average speed for the entire journey? Show your work step by step.',
            'system_prompt': 'You are a mathematics tutor. Solve problems systematically, showing all calculations and reasoning.',
            'expected_result': 60.0,  # (120 + 180) / (2 + 3) = 300 / 5 = 60
            'min_length': 100
        }
        return MathematicalLogicTest(
            name='mathematical_logic_average_speed',
            description='Mathematical logic with average speed calculation',
            config=config,
            complexity_level=2
        )
    
    @staticmethod
    def get_verbal_logic_test() -> VerbalLogicTest:
        """Get verbal logic test."""
        config = {
            'prompt': 'All roses are flowers. Some flowers are red. Therefore, some roses are red. Is this logical reasoning valid? Explain your analysis.',
            'system_prompt': 'You are a logic teacher. Analyze arguments for validity and identify any logical fallacies.',
            'expected_result': 'invalid',
            'premise_keywords': ['roses', 'flowers', 'red'],
            'min_length': 80
        }
        return VerbalLogicTest(
            name='verbal_logic_syllogism',
            description='Verbal logic syllogism analysis',
            config=config,
            complexity_level=3
        )
    
    @staticmethod
    def get_abstract_reasoning_test() -> AbstractReasoningTest:
        """Get abstract reasoning test."""
        config = {
            'prompt': 'Time is to clock as temperature is to what? Explain the relationship and reasoning behind your answer.',
            'system_prompt': 'You are an expert in analogical reasoning. Analyze relationships between abstract concepts.',
            'expected_result': 'thermometer',
            'min_length': 60
        }
        return AbstractReasoningTest(
            name='abstract_reasoning_analogy',
            description='Abstract reasoning with analogical thinking',
            config=config,
            complexity_level=2
        )
    
    @staticmethod
    def get_complex_logic_test() -> VerbalLogicTest:
        """Get complex logic test."""
        config = {
            'prompt': '''Consider this scenario: "If it rains, then the ground gets wet. The ground is wet. Therefore, it rained." 
            Is this reasoning valid? What logical fallacy, if any, is present? Provide a detailed analysis.''',
            'system_prompt': 'You are a critical thinking instructor. Identify logical fallacies and explain formal logic principles.',
            'expected_result': 'affirming the consequent',
            'premise_keywords': ['rain', 'ground', 'wet'],
            'min_length': 120
        }
        return VerbalLogicTest(
            name='complex_logic_fallacy',
            description='Complex logical fallacy identification',
            config=config,
            complexity_level=4
        )
    
    @staticmethod
    def get_all_tests() -> List[IntelligenceTestBase]:
        """Get all logic tests."""
        return [
            LogicTests.get_mathematical_logic_test(),
            LogicTests.get_verbal_logic_test(),
            LogicTests.get_abstract_reasoning_test(),
            LogicTests.get_complex_logic_test()
        ]