"""
Creative intelligence tests for LLM evaluation.
Tests creative thinking, problem-solving, and divergent thinking capabilities.
"""

import re
from typing import Dict, Any, List, Optional, Set
from ..base_test import IntelligenceTestBase, IntelligenceTestResult, IntelligenceCategory, TestStatus


class CreativeProblemSolvingTest(IntelligenceTestBase):
    """Test creative problem-solving abilities."""
    
    def __init__(self, name: str, description: str, config: Dict[str, Any], complexity_level: int = 1):
        super().__init__(name, description, config, IntelligenceCategory.CREATIVE_THINKING, complexity_level)
    
    async def run(self, client: Any, model: str, **kwargs) -> IntelligenceTestResult:
        """Run creative problem-solving test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        
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
        
        # Analyze creative elements
        creative_analysis = self.analyze_creative_elements(response)
        
        # Calculate scores
        creativity_score = self.analyze_creativity(response)
        originality_score = self.analyze_originality(response)
        feasibility_score = self.analyze_feasibility(response)
        coherence_score = self.analyze_logical_coherence(response)
        
        # Overall score
        overall_score = (creativity_score * 0.3 + originality_score * 0.3 + 
                        feasibility_score * 0.2 + coherence_score * 0.2)
        
        status = TestStatus.PASSED if overall_score > 0.6 else TestStatus.FAILED
        
        return IntelligenceTestResult(
            test_name=self.name,
            status=status,
            score=overall_score,
            details={
                'prompt': prompt,
                'response': response,
                'model': model,
                'creative_analysis': creative_analysis,
                'originality_score': originality_score,
                'feasibility_score': feasibility_score,
                'solution_count': self.count_solutions(response),
                'uses_analogies': self.uses_analogies(response),
                'shows_innovation': self.shows_innovation(response),
                'key_concepts': self.extract_key_concepts(response),
                'complexity_measure': self.measure_complexity(response)
            },
            intelligence_category=self.intelligence_category,
            complexity_level=self.complexity_level,
            creativity_score=creativity_score,
            logical_coherence=coherence_score
        )
    
    def analyze_creative_elements(self, response: str) -> Dict[str, Any]:
        """Analyze creative elements in response."""
        analysis = {
            'novelty_indicators': self.count_novelty_indicators(response),
            'alternative_solutions': self.count_solutions(response),
            'uses_metaphors': self.uses_metaphors(response),
            'shows_flexibility': self.shows_flexibility(response),
            'demonstrates_fluency': self.demonstrates_fluency(response),
            'shows_elaboration': self.shows_elaboration(response)
        }
        return analysis
    
    def analyze_originality(self, response: str) -> float:
        """Analyze originality of response."""
        score = 0.0
        
        # Novelty indicators
        novelty_words = [
            'unique', 'original', 'innovative', 'creative', 'novel',
            'unconventional', 'unusual', 'different', 'new', 'fresh'
        ]
        
        novelty_count = 0
        for word in novelty_words:
            if re.search(f'\\b{word}\\b', response, re.IGNORECASE):
                novelty_count += 1
        
        score += min(novelty_count / 5, 0.3)
        
        # Unusual combinations
        if self.has_unusual_combinations(response):
            score += 0.4
        
        # Breaks conventional thinking
        if self.breaks_conventional_thinking(response):
            score += 0.3
        
        return min(score, 1.0)
    
    def analyze_feasibility(self, response: str) -> float:
        """Analyze feasibility of proposed solutions."""
        score = 0.0
        
        # Considers practical aspects
        practical_indicators = [
            'practical', 'feasible', 'realistic', 'viable', 'workable',
            'implementable', 'achievable', 'possible', 'doable'
        ]
        
        for indicator in practical_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                score += 0.2
        
        # Considers constraints
        if self.considers_constraints(response):
            score += 0.3
        
        # Provides implementation details
        if self.provides_implementation_details(response):
            score += 0.3
        
        return min(score, 1.0)
    
    def count_solutions(self, response: str) -> int:
        """Count number of solutions provided."""
        solution_indicators = [
            r'solution \d+', r'option \d+', r'alternative \d+',
            r'approach \d+', r'method \d+', r'way \d+',
            r'first[,\s]', r'second[,\s]', r'third[,\s]', r'fourth[,\s]'
        ]
        
        solution_count = 0
        for pattern in solution_indicators:
            solution_count += len(re.findall(pattern, response, re.IGNORECASE))
        
        return solution_count
    
    def count_novelty_indicators(self, response: str) -> int:
        """Count novelty indicators in response."""
        novelty_indicators = [
            'creative', 'innovative', 'original', 'unique', 'novel',
            'unconventional', 'unusual', 'different', 'alternative',
            'breakthrough', 'revolutionary', 'groundbreaking'
        ]
        
        count = 0
        for indicator in novelty_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                count += 1
        
        return count
    
    def uses_metaphors(self, response: str) -> bool:
        """Check if response uses metaphors."""
        metaphor_indicators = [
            'like', 'as if', 'similar to', 'reminds me of',
            'metaphor', 'analogy', 'symbolize', 'represent'
        ]
        
        for indicator in metaphor_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                return True
        
        return False
    
    def shows_flexibility(self, response: str) -> bool:
        """Check if response shows flexibility in thinking."""
        flexibility_indicators = [
            'alternatively', 'however', 'on the other hand',
            'different approach', 'another way', 'various methods',
            'multiple solutions', 'different perspective'
        ]
        
        for indicator in flexibility_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                return True
        
        return False
    
    def demonstrates_fluency(self, response: str) -> bool:
        """Check if response demonstrates fluency (many ideas)."""
        # Count distinct ideas or solutions
        idea_count = self.count_solutions(response)
        return idea_count >= 3
    
    def shows_elaboration(self, response: str) -> bool:
        """Check if response shows elaboration on ideas."""
        elaboration_indicators = [
            'specifically', 'in detail', 'furthermore', 'moreover',
            'additionally', 'for example', 'such as', 'including'
        ]
        
        for indicator in elaboration_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                return True
        
        return False
    
    def has_unusual_combinations(self, response: str) -> bool:
        """Check for unusual combinations of concepts."""
        # Simple heuristic: look for unexpected word combinations
        unusual_patterns = [
            r'combine.*with', r'merge.*and', r'blend.*together',
            r'mix.*with', r'fusion.*of', r'hybrid.*approach'
        ]
        
        for pattern in unusual_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                return True
        
        return False
    
    def breaks_conventional_thinking(self, response: str) -> bool:
        """Check if response breaks conventional thinking."""
        unconventional_indicators = [
            'unconventional', 'outside the box', 'think differently',
            'challenge assumptions', 'break rules', 'question norms',
            'rebel against', 'defy expectations'
        ]
        
        for indicator in unconventional_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                return True
        
        return False
    
    def considers_constraints(self, response: str) -> bool:
        """Check if response considers constraints."""
        constraint_indicators = [
            'constraint', 'limitation', 'restriction', 'boundary',
            'limit', 'budget', 'time', 'resource', 'challenge'
        ]
        
        for indicator in constraint_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def provides_implementation_details(self, response: str) -> bool:
        """Check if response provides implementation details."""
        implementation_indicators = [
            'implement', 'execute', 'carry out', 'put into practice',
            'step by step', 'process', 'procedure', 'method'
        ]
        
        for indicator in implementation_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                return True
        
        return False
    
    def uses_analogies(self, response: str) -> bool:
        """Check if response uses analogies."""
        analogy_indicators = [
            'like', 'similar to', 'analogous to', 'comparable to',
            'reminds me of', 'parallel to', 'corresponds to'
        ]
        
        for indicator in analogy_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                return True
        
        return False
    
    def shows_innovation(self, response: str) -> bool:
        """Check if response shows innovation."""
        innovation_indicators = [
            'innovative', 'groundbreaking', 'revolutionary', 'cutting-edge',
            'state-of-the-art', 'breakthrough', 'pioneering', 'novel'
        ]
        
        for indicator in innovation_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False


class DivergentThinkingTest(IntelligenceTestBase):
    """Test divergent thinking abilities."""
    
    def __init__(self, name: str, description: str, config: Dict[str, Any], complexity_level: int = 1):
        super().__init__(name, description, config, IntelligenceCategory.CREATIVE_THINKING, complexity_level)
    
    async def run(self, client: Any, model: str, **kwargs) -> IntelligenceTestResult:
        """Run divergent thinking test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        
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
        
        # Analyze divergent thinking
        divergent_analysis = self.analyze_divergent_thinking(response)
        
        # Calculate scores
        fluency_score = self.calculate_fluency_score(response)
        flexibility_score = self.calculate_flexibility_score(response)
        originality_score = self.analyze_originality(response)
        elaboration_score = self.calculate_elaboration_score(response)
        
        # Overall score (Torrance Test of Creative Thinking dimensions)
        overall_score = (fluency_score * 0.25 + flexibility_score * 0.25 + 
                        originality_score * 0.25 + elaboration_score * 0.25)
        
        status = TestStatus.PASSED if overall_score > 0.6 else TestStatus.FAILED
        
        return IntelligenceTestResult(
            test_name=self.name,
            status=status,
            score=overall_score,
            details={
                'prompt': prompt,
                'response': response,
                'model': model,
                'divergent_analysis': divergent_analysis,
                'fluency_score': fluency_score,
                'flexibility_score': flexibility_score,
                'originality_score': originality_score,
                'elaboration_score': elaboration_score,
                'idea_count': self.count_ideas(response),
                'category_count': self.count_categories(response),
                'unique_ideas': self.count_unique_ideas(response),
                'key_concepts': self.extract_key_concepts(response),
                'complexity_measure': self.measure_complexity(response)
            },
            intelligence_category=self.intelligence_category,
            complexity_level=self.complexity_level,
            creativity_score=originality_score
        )
    
    def analyze_divergent_thinking(self, response: str) -> Dict[str, Any]:
        """Analyze divergent thinking dimensions."""
        analysis = {
            'fluency': self.count_ideas(response),
            'flexibility': self.count_categories(response),
            'originality': self.count_unique_ideas(response),
            'elaboration': self.count_elaborated_ideas(response)
        }
        return analysis
    
    def calculate_fluency_score(self, response: str) -> float:
        """Calculate fluency score (number of ideas)."""
        idea_count = self.count_ideas(response)
        expected_ideas = self.config.get('expected_ideas', 5)
        return min(idea_count / expected_ideas, 1.0)
    
    def calculate_flexibility_score(self, response: str) -> float:
        """Calculate flexibility score (number of categories)."""
        category_count = self.count_categories(response)
        expected_categories = self.config.get('expected_categories', 3)
        return min(category_count / expected_categories, 1.0)
    
    def calculate_elaboration_score(self, response: str) -> float:
        """Calculate elaboration score (detail in ideas)."""
        elaboration_count = self.count_elaborated_ideas(response)
        total_ideas = self.count_ideas(response)
        
        if total_ideas == 0:
            return 0.0
        
        return elaboration_count / total_ideas
    
    def count_ideas(self, response: str) -> int:
        """Count total number of ideas."""
        idea_patterns = [
            r'\d+\.',  # Numbered lists
            r'•',      # Bullet points
            r'-\s',    # Dashes
            r'idea\s*\d+',  # Explicit idea numbering
            r'option\s*\d+',
            r'possibility\s*\d+',
            r'alternative\s*\d+'
        ]
        
        idea_count = 0
        for pattern in idea_patterns:
            idea_count += len(re.findall(pattern, response, re.IGNORECASE))
        
        # If no explicit formatting, count sentences as potential ideas
        if idea_count == 0:
            sentences = re.split(r'[.!?]+', response)
            idea_count = len([s for s in sentences if len(s.strip()) > 10])
        
        return idea_count
    
    def count_categories(self, response: str) -> int:
        """Count number of different categories of ideas."""
        # This is a simplified heuristic - in practice, would need semantic analysis
        category_indicators = [
            'category', 'type', 'kind', 'approach', 'method',
            'strategy', 'technique', 'way', 'style', 'mode'
        ]
        
        categories = set()
        for indicator in category_indicators:
            matches = re.findall(f'{indicator}\\s*\\d+', response, re.IGNORECASE)
            categories.update(matches)
        
        # Fallback: estimate based on topic diversity
        if len(categories) == 0:
            # Count distinct topics/domains mentioned
            key_concepts = self.extract_key_concepts(response)
            return min(len(key_concepts) // 3, 5)  # Rough estimate
        
        return len(categories)
    
    def count_unique_ideas(self, response: str) -> int:
        """Count number of unique/original ideas."""
        # Simplified heuristic: look for originality indicators
        unique_indicators = [
            'unique', 'original', 'creative', 'innovative', 'novel',
            'unusual', 'different', 'unconventional', 'unexpected'
        ]
        
        unique_count = 0
        for indicator in unique_indicators:
            unique_count += len(re.findall(f'\\b{indicator}\\b', response, re.IGNORECASE))
        
        return min(unique_count, self.count_ideas(response))
    
    def count_elaborated_ideas(self, response: str) -> int:
        """Count number of elaborated ideas."""
        elaboration_indicators = [
            'specifically', 'in detail', 'furthermore', 'moreover',
            'for example', 'such as', 'including', 'namely'
        ]
        
        elaboration_count = 0
        for indicator in elaboration_indicators:
            elaboration_count += len(re.findall(indicator, response, re.IGNORECASE))
        
        return elaboration_count
    
    def analyze_originality(self, response: str) -> float:
        """Analyze originality of ideas."""
        # Reuse from CreativeProblemSolvingTest
        return super().analyze_creativity(response)


class MetaphorGenerationTest(IntelligenceTestBase):
    """Test metaphor generation abilities."""
    
    def __init__(self, name: str, description: str, config: Dict[str, Any], complexity_level: int = 1):
        super().__init__(name, description, config, IntelligenceCategory.CREATIVE_THINKING, complexity_level)
    
    async def run(self, client: Any, model: str, **kwargs) -> IntelligenceTestResult:
        """Run metaphor generation test."""
        prompt = self.get_test_prompt()
        system_prompt = self.get_system_prompt()
        
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
        
        # Analyze metaphor quality
        metaphor_analysis = self.analyze_metaphor_quality(response)
        
        # Calculate scores
        metaphor_score = self.calculate_metaphor_score(response)
        creativity_score = self.analyze_creativity(response)
        coherence_score = self.analyze_logical_coherence(response)
        
        # Overall score
        overall_score = (metaphor_score * 0.5 + creativity_score * 0.3 + coherence_score * 0.2)
        
        status = TestStatus.PASSED if overall_score > 0.6 else TestStatus.FAILED
        
        return IntelligenceTestResult(
            test_name=self.name,
            status=status,
            score=overall_score,
            details={
                'prompt': prompt,
                'response': response,
                'model': model,
                'metaphor_analysis': metaphor_analysis,
                'metaphor_score': metaphor_score,
                'metaphor_count': self.count_metaphors(response),
                'uses_similes': self.uses_similes(response),
                'explains_connection': self.explains_metaphor_connection(response),
                'key_concepts': self.extract_key_concepts(response),
                'complexity_measure': self.measure_complexity(response)
            },
            intelligence_category=self.intelligence_category,
            complexity_level=self.complexity_level,
            creativity_score=creativity_score,
            logical_coherence=coherence_score
        )
    
    def analyze_metaphor_quality(self, response: str) -> Dict[str, Any]:
        """Analyze quality of metaphors."""
        analysis = {
            'metaphor_count': self.count_metaphors(response),
            'uses_similes': self.uses_similes(response),
            'explains_connection': self.explains_metaphor_connection(response),
            'creative_metaphors': self.has_creative_metaphors(response),
            'coherent_metaphors': self.has_coherent_metaphors(response)
        }
        return analysis
    
    def calculate_metaphor_score(self, response: str) -> float:
        """Calculate metaphor quality score."""
        score = 0.0
        
        # Has metaphors
        if self.count_metaphors(response) > 0:
            score += 0.3
        
        # Creative metaphors
        if self.has_creative_metaphors(response):
            score += 0.3
        
        # Explains connection
        if self.explains_metaphor_connection(response):
            score += 0.2
        
        # Coherent metaphors
        if self.has_coherent_metaphors(response):
            score += 0.2
        
        return min(score, 1.0)
    
    def count_metaphors(self, response: str) -> int:
        """Count metaphors in response."""
        metaphor_patterns = [
            r'is like', r'is a', r'represents', r'symbolizes',
            r'embodies', r'mirrors', r'reflects', r'resembles'
        ]
        
        metaphor_count = 0
        for pattern in metaphor_patterns:
            metaphor_count += len(re.findall(pattern, response, re.IGNORECASE))
        
        return metaphor_count
    
    def uses_similes(self, response: str) -> bool:
        """Check if response uses similes."""
        simile_indicators = [
            'like', 'as', 'similar to', 'comparable to',
            'reminds me of', 'such as'
        ]
        
        for indicator in simile_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                return True
        
        return False
    
    def explains_metaphor_connection(self, response: str) -> bool:
        """Check if response explains metaphor connection."""
        explanation_indicators = [
            'because', 'since', 'the connection is', 'this works because',
            'the similarity is', 'both have', 'they share'
        ]
        
        for indicator in explanation_indicators:
            if re.search(indicator, response, re.IGNORECASE):
                return True
        
        return False
    
    def has_creative_metaphors(self, response: str) -> bool:
        """Check for creative metaphors."""
        # Look for unusual or creative metaphor constructions
        creative_indicators = [
            'creative', 'original', 'unique', 'innovative',
            'unusual', 'unexpected', 'surprising'
        ]
        
        for indicator in creative_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return False
    
    def has_coherent_metaphors(self, response: str) -> bool:
        """Check for coherent metaphors."""
        # Simple heuristic: metaphors that make logical sense
        coherence_indicators = [
            'makes sense', 'logical', 'clear', 'obvious',
            'understandable', 'coherent', 'consistent'
        ]
        
        for indicator in coherence_indicators:
            if re.search(f'\\b{indicator}\\b', response, re.IGNORECASE):
                return True
        
        return True  # Default to coherent unless proven otherwise


class CreativeTests:
    """Collection of creative intelligence tests."""
    
    @staticmethod
    def get_creative_problem_solving_test() -> CreativeProblemSolvingTest:
        """Get creative problem solving test."""
        config = {
            'prompt': '''You need to transport a elephant across a river, but the bridge can only hold half its weight. 
            The elephant cannot swim and there are no boats large enough. Think of creative solutions to this problem. 
            Provide at least 3 different approaches.''',
            'system_prompt': 'You are a creative problem solver. Think outside the box and provide innovative solutions.',
            'min_length': 150
        }
        return CreativeProblemSolvingTest(
            name='creative_problem_elephant_river',
            description='Creative problem solving with unusual constraints',
            config=config,
            complexity_level=3
        )
    
    @staticmethod
    def get_divergent_thinking_test() -> DivergentThinkingTest:
        """Get divergent thinking test."""
        config = {
            'prompt': 'List as many creative uses as possible for a paper clip. Think beyond the obvious uses.',
            'system_prompt': 'You are a creative thinking expert. Generate many diverse and original ideas.',
            'expected_ideas': 10,
            'expected_categories': 4,
            'min_length': 100
        }
        return DivergentThinkingTest(
            name='divergent_thinking_paperclip',
            description='Divergent thinking with alternative uses task',
            config=config,
            complexity_level=2
        )
    
    @staticmethod
    def get_metaphor_generation_test() -> MetaphorGenerationTest:
        """Get metaphor generation test."""
        config = {
            'prompt': 'Create metaphors to explain the concept of "artificial intelligence" to a child. Use at least 3 different metaphors and explain why each one works.',
            'system_prompt': 'You are an expert at creating clear, creative metaphors. Make complex concepts understandable through comparison.',
            'min_length': 120
        }
        return MetaphorGenerationTest(
            name='metaphor_generation_ai',
            description='Metaphor generation for complex concepts',
            config=config,
            complexity_level=3
        )
    
    @staticmethod
    def get_innovation_test() -> CreativeProblemSolvingTest:
        """Get innovation test."""
        config = {
            'prompt': '''Design a new social media platform that solves the problems of current platforms 
            (misinformation, addiction, privacy issues, etc.). What innovative features would it have? 
            How would it work differently?''',
            'system_prompt': 'You are a product innovation expert. Create truly innovative solutions to complex social problems.',
            'min_length': 200
        }
        return CreativeProblemSolvingTest(
            name='innovation_social_media',
            description='Innovation in social media platform design',
            config=config,
            complexity_level=4
        )
    
    @staticmethod
    def get_all_tests() -> List[IntelligenceTestBase]:
        """Get all creative intelligence tests."""
        return [
            CreativeTests.get_creative_problem_solving_test(),
            CreativeTests.get_divergent_thinking_test(),
            CreativeTests.get_metaphor_generation_test(),
            CreativeTests.get_innovation_test()
        ]