"""
Data Augmentation for LLM Evaluation System
Generates synthetic test data and augments existing datasets
"""

import re
import random
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging
from .dataset_manager import DatasetSample

logger = logging.getLogger(__name__)


@dataclass
class AugmentationConfig:
    """Configuration for data augmentation"""
    paraphrase_probability: float = 0.3
    negation_probability: float = 0.2
    complexity_variation: float = 0.4
    generate_adversarial: bool = True
    max_augmentations_per_sample: int = 3
    preserve_meaning: bool = True


class DataAugmentation:
    """Generates synthetic test data and augments existing datasets"""
    
    def __init__(self, config: Optional[AugmentationConfig] = None):
        self.config = config or AugmentationConfig()
        self.paraphrase_templates = self._load_paraphrase_templates()
        self.complexity_modifiers = self._load_complexity_modifiers()
        self.adversarial_patterns = self._load_adversarial_patterns()
    
    def _load_paraphrase_templates(self) -> Dict[str, List[str]]:
        """Load paraphrase templates for different question types"""
        return {
            'question': [
                "Can you tell me {content}?",
                "What is {content}?",
                "Could you explain {content}?",
                "I need to know about {content}.",
                "Please describe {content}.",
                "Help me understand {content}."
            ],
            'instruction': [
                "Please {content}",
                "I want you to {content}",
                "Could you {content}",
                "You should {content}",
                "I need you to {content}",
                "Would you {content}"
            ],
            'completion': [
                "Complete this: {content}",
                "Finish the following: {content}",
                "Continue from: {content}",
                "What comes next: {content}"
            ]
        }
    
    def _load_complexity_modifiers(self) -> Dict[str, List[str]]:
        """Load complexity modifiers"""
        return {
            'increase': [
                "Provide a detailed explanation of",
                "Give a comprehensive analysis of",
                "Thoroughly examine",
                "Provide an in-depth discussion of",
                "Analyze in detail"
            ],
            'decrease': [
                "Briefly explain",
                "Summarize",
                "Give a simple answer for",
                "Quickly describe",
                "In short"
            ],
            'context_add': [
                "In the context of machine learning,",
                "Considering modern technology,",
                "From a practical perspective,",
                "In real-world applications,",
                "For a general audience,"
            ]
        }
    
    def _load_adversarial_patterns(self) -> List[Dict[str, Any]]:
        """Load adversarial test patterns"""
        return [
            {
                'name': 'negation',
                'pattern': lambda x: f"What is NOT {x}?",
                'description': 'Negation pattern'
            },
            {
                'name': 'comparison',
                'pattern': lambda x: f"How does {x} differ from similar concepts?",
                'description': 'Comparison pattern'
            },
            {
                'name': 'edge_case',
                'pattern': lambda x: f"What happens in edge cases when {x}?",
                'description': 'Edge case pattern'
            },
            {
                'name': 'contradiction',
                'pattern': lambda x: f"Some claim {x} is false. How would you respond?",
                'description': 'Contradiction pattern'
            }
        ]
    
    def augment_dataset(self, samples: List[DatasetSample], 
                       target_size: Optional[int] = None) -> List[DatasetSample]:
        """Augment dataset with synthetic samples"""
        if not samples:
            return samples
        
        augmented_samples = samples.copy()
        
        if target_size is None:
            target_size = len(samples) * 2  # Double the dataset by default
        
        samples_to_generate = max(0, target_size - len(samples))
        
        if samples_to_generate > 0:
            logger.info(f"Generating {samples_to_generate} augmented samples")
            
            for i in range(samples_to_generate):
                # Select random source sample
                source_sample = random.choice(samples)
                
                # Generate augmented sample
                augmented_sample = self.augment_sample(source_sample, f"aug_{i}")
                if augmented_sample:
                    augmented_samples.append(augmented_sample)
        
        return augmented_samples
    
    def augment_sample(self, sample: DatasetSample, 
                      new_id: Optional[str] = None) -> Optional[DatasetSample]:
        """Augment a single sample"""
        try:
            # Determine augmentation type
            augmentation_type = self._select_augmentation_type(sample)
            
            # Generate augmented content
            if augmentation_type == 'paraphrase':
                augmented_input = self._paraphrase_input(sample.input)
            elif augmentation_type == 'complexity':
                augmented_input = self._modify_complexity(sample.input)
            elif augmentation_type == 'adversarial':
                augmented_input = self._generate_adversarial(sample.input)
            else:
                augmented_input = sample.input
            
            # Create new sample
            new_sample = DatasetSample(
                id=new_id or f"{sample.id}_aug_{random.randint(1000, 9999)}",
                input=augmented_input,
                expected_output=sample.expected_output,  # May need modification
                context=sample.context,
                difficulty=sample.difficulty,
                category=sample.category,
                metadata={
                    **sample.metadata,
                    'augmentation_type': augmentation_type,
                    'source_sample_id': sample.id,
                    'is_augmented': True
                }
            )
            
            return new_sample
            
        except Exception as e:
            logger.error(f"Failed to augment sample {sample.id}: {e}")
            return None
    
    def _select_augmentation_type(self, sample: DatasetSample) -> str:
        """Select appropriate augmentation type"""
        # Simple selection based on random choice and configuration
        choices = []
        
        if random.random() < self.config.paraphrase_probability:
            choices.append('paraphrase')
        
        if random.random() < self.config.complexity_variation:
            choices.append('complexity')
        
        if self.config.generate_adversarial and random.random() < 0.3:
            choices.append('adversarial')
        
        return random.choice(choices) if choices else 'paraphrase'
    
    def _paraphrase_input(self, input_text: str) -> str:
        """Generate paraphrase of input text"""
        # Simple paraphrasing - in practice, this would use more sophisticated NLP
        
        # Detect input type
        input_type = self._detect_input_type(input_text)
        
        # Get appropriate templates
        templates = self.paraphrase_templates.get(input_type, [])
        
        if not templates:
            return input_text
        
        # Simple template-based paraphrasing
        if '{content}' in templates[0]:
            # Extract core content
            core_content = self._extract_core_content(input_text)
            template = random.choice(templates)
            return template.format(content=core_content)
        
        # If no template matching, try simple transformations
        return self._apply_simple_transformations(input_text)
    
    def _detect_input_type(self, input_text: str) -> str:
        """Detect the type of input text"""
        text_lower = input_text.lower().strip()
        
        # Check for questions
        if text_lower.startswith(('what', 'how', 'why', 'when', 'where', 'who')) or text_lower.endswith('?'):
            return 'question'
        
        # Check for instructions
        if text_lower.startswith(('please', 'can you', 'could you', 'would you', 'i want you to')):
            return 'instruction'
        
        # Check for completion tasks
        if 'complete' in text_lower or 'finish' in text_lower or 'continue' in text_lower:
            return 'completion'
        
        return 'question'  # Default
    
    def _extract_core_content(self, input_text: str) -> str:
        """Extract core content from input text"""
        # Remove common question words and phrases
        text = input_text.strip()
        
        # Remove question marks
        text = text.rstrip('?')
        
        # Remove common question starters
        question_starters = [
            'what is', 'what are', 'how do', 'how does', 'why do', 'why does',
            'when do', 'when does', 'where do', 'where does', 'who is', 'who are',
            'please', 'can you', 'could you', 'would you', 'i want you to'
        ]
        
        text_lower = text.lower()
        for starter in question_starters:
            if text_lower.startswith(starter):
                # Remove the starter and return the rest
                return text[len(starter):].strip()
        
        return text
    
    def _apply_simple_transformations(self, input_text: str) -> str:
        """Apply simple text transformations"""
        transformations = [
            lambda x: x.replace('you', 'one'),
            lambda x: x.replace('your', 'one\'s'),
            lambda x: x.replace('Can you', 'Could you'),
            lambda x: x.replace('What is', 'What would be'),
            lambda x: x.replace('How do', 'How would'),
        ]
        
        # Apply random transformation
        transformation = random.choice(transformations)
        try:
            return transformation(input_text)
        except:
            return input_text
    
    def _modify_complexity(self, input_text: str) -> str:
        """Modify complexity of input text"""
        # Randomly increase or decrease complexity
        if random.random() < 0.5:
            # Increase complexity
            modifiers = self.complexity_modifiers['increase']
            prefix = random.choice(modifiers)
            return f"{prefix} {input_text.lower()}"
        else:
            # Decrease complexity or add context
            if random.random() < 0.5:
                modifiers = self.complexity_modifiers['decrease']
                prefix = random.choice(modifiers)
                return f"{prefix} {input_text.lower()}"
            else:
                modifiers = self.complexity_modifiers['context_add']
                prefix = random.choice(modifiers)
                return f"{prefix} {input_text.lower()}"
    
    def _generate_adversarial(self, input_text: str) -> str:
        """Generate adversarial test case"""
        # Select random adversarial pattern
        pattern_info = random.choice(self.adversarial_patterns)
        pattern_func = pattern_info['pattern']
        
        # Extract core concept
        core_concept = self._extract_core_content(input_text)
        
        try:
            return pattern_func(core_concept)
        except:
            return input_text
    
    def generate_synthetic_samples(self, category: str, difficulty: str, 
                                 count: int = 10) -> List[DatasetSample]:
        """Generate synthetic samples for specific category and difficulty"""
        samples = []
        
        # Template-based generation
        templates = self._get_templates_for_category(category)
        
        for i in range(count):
            template = random.choice(templates)
            
            # Generate sample
            sample = DatasetSample(
                id=f"synthetic_{category}_{difficulty}_{i}",
                input=template['input'],
                expected_output=template.get('expected_output'),
                context=template.get('context'),
                difficulty=difficulty,
                category=category,
                metadata={
                    'is_synthetic': True,
                    'generation_method': 'template',
                    'template_id': template.get('id', 'unknown')
                }
            )
            
            samples.append(sample)
        
        return samples
    
    def _get_templates_for_category(self, category: str) -> List[Dict[str, str]]:
        """Get templates for specific category"""
        templates = {
            'reasoning': [
                {
                    'id': 'logical_reasoning_1',
                    'input': 'If all A are B, and all B are C, then what can we conclude about A and C?',
                    'expected_output': 'All A are C (transitive property)',
                    'context': 'Logical reasoning'
                },
                {
                    'id': 'logical_reasoning_2',
                    'input': 'What is the logical fallacy in: "Everyone I know likes pizza, therefore everyone likes pizza"?',
                    'expected_output': 'Hasty generalization fallacy',
                    'context': 'Logical fallacies'
                }
            ],
            'mathematics': [
                {
                    'id': 'basic_math_1',
                    'input': 'What is 2 + 2?',
                    'expected_output': '4',
                    'context': 'Basic arithmetic'
                },
                {
                    'id': 'algebra_1',
                    'input': 'Solve for x: 2x + 5 = 15',
                    'expected_output': 'x = 5',
                    'context': 'Basic algebra'
                }
            ],
            'language': [
                {
                    'id': 'grammar_1',
                    'input': 'What is the past tense of "run"?',
                    'expected_output': 'ran',
                    'context': 'English grammar'
                },
                {
                    'id': 'vocabulary_1',
                    'input': 'What does "ubiquitous" mean?',
                    'expected_output': 'Present everywhere or very common',
                    'context': 'Vocabulary'
                }
            ]
        }
        
        return templates.get(category, [])
    
    def create_edge_cases(self, samples: List[DatasetSample]) -> List[DatasetSample]:
        """Create edge case variants of existing samples"""
        edge_cases = []
        
        for sample in samples:
            # Generate different types of edge cases
            edge_case_types = [
                'empty_input',
                'very_long_input',
                'special_characters',
                'multilingual',
                'ambiguous'
            ]
            
            for edge_type in edge_case_types:
                edge_case = self._create_edge_case(sample, edge_type)
                if edge_case:
                    edge_cases.append(edge_case)
        
        return edge_cases
    
    def _create_edge_case(self, sample: DatasetSample, edge_type: str) -> Optional[DatasetSample]:
        """Create specific type of edge case"""
        try:
            if edge_type == 'empty_input':
                return DatasetSample(
                    id=f"{sample.id}_edge_empty",
                    input="",
                    expected_output="Input cannot be empty",
                    difficulty=sample.difficulty,
                    category=sample.category,
                    metadata={**sample.metadata, 'edge_case_type': edge_type}
                )
            
            elif edge_type == 'very_long_input':
                long_input = sample.input + " " + "very " * 100 + "long input"
                return DatasetSample(
                    id=f"{sample.id}_edge_long",
                    input=long_input,
                    expected_output=sample.expected_output,
                    difficulty=sample.difficulty,
                    category=sample.category,
                    metadata={**sample.metadata, 'edge_case_type': edge_type}
                )
            
            elif edge_type == 'special_characters':
                special_input = sample.input + " !@#$%^&*()_+-=[]{}|;':\",./<>?"
                return DatasetSample(
                    id=f"{sample.id}_edge_special",
                    input=special_input,
                    expected_output=sample.expected_output,
                    difficulty=sample.difficulty,
                    category=sample.category,
                    metadata={**sample.metadata, 'edge_case_type': edge_type}
                )
            
            elif edge_type == 'multilingual':
                multilingual_input = sample.input + " (How would you answer this in Spanish?)"
                return DatasetSample(
                    id=f"{sample.id}_edge_multilingual",
                    input=multilingual_input,
                    expected_output=sample.expected_output,
                    difficulty=sample.difficulty,
                    category=sample.category,
                    metadata={**sample.metadata, 'edge_case_type': edge_type}
                )
            
            elif edge_type == 'ambiguous':
                ambiguous_input = f"This could mean multiple things: {sample.input}"
                return DatasetSample(
                    id=f"{sample.id}_edge_ambiguous",
                    input=ambiguous_input,
                    expected_output=sample.expected_output,
                    difficulty=sample.difficulty,
                    category=sample.category,
                    metadata={**sample.metadata, 'edge_case_type': edge_type}
                )
            
        except Exception as e:
            logger.error(f"Failed to create edge case {edge_type} for sample {sample.id}: {e}")
            return None
    
    def balance_dataset(self, samples: List[DatasetSample]) -> List[DatasetSample]:
        """Balance dataset by generating samples for underrepresented categories"""
        if not samples:
            return samples
        
        # Analyze current distribution
        category_counts = {}
        difficulty_counts = {}
        
        for sample in samples:
            if sample.category:
                category_counts[sample.category] = category_counts.get(sample.category, 0) + 1
            if sample.difficulty:
                difficulty_counts[sample.difficulty] = difficulty_counts.get(sample.difficulty, 0) + 1
        
        # Find target count (average of current counts)
        if category_counts:
            target_category_count = sum(category_counts.values()) // len(category_counts)
        else:
            target_category_count = 10
        
        if difficulty_counts:
            target_difficulty_count = sum(difficulty_counts.values()) // len(difficulty_counts)
        else:
            target_difficulty_count = 10
        
        balanced_samples = samples.copy()
        
        # Generate samples for underrepresented categories
        for category, count in category_counts.items():
            if count < target_category_count:
                needed = target_category_count - count
                
                # Try different difficulty levels
                for difficulty in ['easy', 'medium', 'hard']:
                    samples_per_difficulty = needed // 3
                    if samples_per_difficulty > 0:
                        synthetic_samples = self.generate_synthetic_samples(
                            category, difficulty, samples_per_difficulty
                        )
                        balanced_samples.extend(synthetic_samples)
        
        return balanced_samples
    
    def get_augmentation_report(self, original_samples: List[DatasetSample], 
                              augmented_samples: List[DatasetSample]) -> Dict[str, Any]:
        """Generate report on augmentation results"""
        original_count = len(original_samples)
        augmented_count = len(augmented_samples)
        new_samples = augmented_count - original_count
        
        # Count augmentation types
        augmentation_types = {}
        for sample in augmented_samples:
            if sample.metadata.get('is_augmented') or sample.metadata.get('is_synthetic'):
                aug_type = sample.metadata.get('augmentation_type', 'unknown')
                augmentation_types[aug_type] = augmentation_types.get(aug_type, 0) + 1
        
        return {
            'original_count': original_count,
            'augmented_count': augmented_count,
            'new_samples': new_samples,
            'augmentation_ratio': new_samples / original_count if original_count > 0 else 0,
            'augmentation_types': augmentation_types,
            'improvement_percentage': (new_samples / original_count) * 100 if original_count > 0 else 0
        }