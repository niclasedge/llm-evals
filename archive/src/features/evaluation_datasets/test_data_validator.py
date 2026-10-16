"""
Test Data Validator for LLM Evaluation System
Validates test data quality and identifies potential issues
"""

import re
import json
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from collections import Counter
import logging
from .dataset_manager import DatasetSample

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    quality_score: float
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    statistics: Dict[str, Any]


class TestDataValidator:
    """Validates test data quality and identifies issues"""
    
    def __init__(self):
        self.min_input_length = 5
        self.max_input_length = 10000
        self.min_output_length = 1
        self.max_output_length = 10000
        self.min_dataset_size = 10
        self.quality_thresholds = {
            'excellent': 0.9,
            'good': 0.7,
            'fair': 0.5,
            'poor': 0.3
        }
    
    def validate_dataset(self, samples: List[DatasetSample]) -> ValidationResult:
        """Validate entire dataset"""
        errors = []
        warnings = []
        suggestions = []
        
        # Basic validation
        if not samples:
            errors.append("Dataset is empty")
            return ValidationResult(
                is_valid=False,
                quality_score=0.0,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions,
                statistics={}
            )
        
        # Size validation
        if len(samples) < self.min_dataset_size:
            warnings.append(f"Dataset has only {len(samples)} samples (minimum recommended: {self.min_dataset_size})")
        
        # Individual sample validation
        sample_errors = []
        sample_warnings = []
        sample_suggestions = []
        
        for i, sample in enumerate(samples):
            sample_result = self.validate_sample(sample, sample_index=i)
            sample_errors.extend(sample_result.errors)
            sample_warnings.extend(sample_result.warnings)
            sample_suggestions.extend(sample_result.suggestions)
        
        errors.extend(sample_errors)
        warnings.extend(sample_warnings)
        suggestions.extend(sample_suggestions)
        
        # Dataset-level validation
        dataset_validation = self._validate_dataset_structure(samples)
        errors.extend(dataset_validation['errors'])
        warnings.extend(dataset_validation['warnings'])
        suggestions.extend(dataset_validation['suggestions'])
        
        # Calculate statistics
        statistics = self._calculate_statistics(samples)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(samples, errors, warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            quality_score=quality_score,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            statistics=statistics
        )
    
    def validate_sample(self, sample: DatasetSample, sample_index: int = None) -> ValidationResult:
        """Validate individual sample"""
        errors = []
        warnings = []
        suggestions = []
        
        prefix = f"Sample {sample_index}: " if sample_index is not None else ""
        
        # ID validation
        if not sample.id or not sample.id.strip():
            errors.append(f"{prefix}Sample ID is empty")
        elif not re.match(r'^[a-zA-Z0-9_-]+$', sample.id):
            warnings.append(f"{prefix}Sample ID contains special characters")
        
        # Input validation
        if not sample.input or not sample.input.strip():
            errors.append(f"{prefix}Input is empty")
        else:
            input_length = len(sample.input)
            if input_length < self.min_input_length:
                warnings.append(f"{prefix}Input is very short ({input_length} characters)")
            elif input_length > self.max_input_length:
                warnings.append(f"{prefix}Input is very long ({input_length} characters)")
        
        # Expected output validation
        if sample.expected_output is not None:
            if not sample.expected_output.strip():
                warnings.append(f"{prefix}Expected output is empty")
            else:
                output_length = len(sample.expected_output)
                if output_length < self.min_output_length:
                    warnings.append(f"{prefix}Expected output is very short ({output_length} characters)")
                elif output_length > self.max_output_length:
                    warnings.append(f"{prefix}Expected output is very long ({output_length} characters)")
        else:
            suggestions.append(f"{prefix}Consider adding expected output for better evaluation")
        
        # Context validation
        if sample.context and len(sample.context) > 5000:
            warnings.append(f"{prefix}Context is very long ({len(sample.context)} characters)")
        
        # Metadata validation
        if not sample.difficulty:
            suggestions.append(f"{prefix}Consider adding difficulty level")
        elif sample.difficulty not in ['easy', 'medium', 'hard']:
            warnings.append(f"{prefix}Unknown difficulty level: {sample.difficulty}")
        
        if not sample.category:
            suggestions.append(f"{prefix}Consider adding category")
        
        # Content quality checks
        content_issues = self._check_content_quality(sample.input, sample.expected_output)
        warnings.extend([f"{prefix}{issue}" for issue in content_issues])
        
        # Calculate sample quality score
        quality_score = self._calculate_sample_quality_score(sample, errors, warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            quality_score=quality_score,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            statistics={}
        )
    
    def _validate_dataset_structure(self, samples: List[DatasetSample]) -> Dict[str, List[str]]:
        """Validate dataset structure and consistency"""
        errors = []
        warnings = []
        suggestions = []
        
        # Check for duplicate IDs
        ids = [sample.id for sample in samples]
        id_counts = Counter(ids)
        duplicates = [id for id, count in id_counts.items() if count > 1]
        if duplicates:
            errors.append(f"Duplicate sample IDs found: {', '.join(duplicates)}")
        
        # Check for duplicate content
        content_hashes = {}
        for i, sample in enumerate(samples):
            content = sample.input + (sample.expected_output or "")
            content_hash = hash(content)
            if content_hash in content_hashes:
                warnings.append(f"Sample {i} appears to be duplicate of sample {content_hashes[content_hash]}")
            else:
                content_hashes[content_hash] = i
        
        # Check distribution balance
        categories = [sample.category for sample in samples if sample.category]
        if categories:
            category_counts = Counter(categories)
            total_samples = len(samples)
            
            # Check for imbalanced categories
            for category, count in category_counts.items():
                percentage = (count / total_samples) * 100
                if percentage < 5:
                    warnings.append(f"Category '{category}' has very few samples ({count}, {percentage:.1f}%)")
                elif percentage > 80:
                    warnings.append(f"Category '{category}' dominates the dataset ({count}, {percentage:.1f}%)")
        
        # Check difficulty distribution
        difficulties = [sample.difficulty for sample in samples if sample.difficulty]
        if difficulties:
            difficulty_counts = Counter(difficulties)
            total_samples = len(samples)
            
            for difficulty, count in difficulty_counts.items():
                percentage = (count / total_samples) * 100
                if percentage < 10:
                    suggestions.append(f"Consider adding more '{difficulty}' samples ({count}, {percentage:.1f}%)")
        
        # Check for missing expected outputs
        missing_outputs = sum(1 for sample in samples if not sample.expected_output)
        if missing_outputs > 0:
            percentage = (missing_outputs / len(samples)) * 100
            if percentage > 50:
                warnings.append(f"Many samples missing expected outputs ({missing_outputs}, {percentage:.1f}%)")
            elif percentage > 20:
                suggestions.append(f"Consider adding expected outputs for more samples ({missing_outputs}, {percentage:.1f}%)")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'suggestions': suggestions
        }
    
    def _check_content_quality(self, input_text: str, expected_output: Optional[str] = None) -> List[str]:
        """Check content quality issues"""
        issues = []
        
        # Check for placeholder text
        placeholders = ['lorem ipsum', 'placeholder', 'todo', 'tbd', 'xxx', 'yyy']
        for placeholder in placeholders:
            if placeholder.lower() in input_text.lower():
                issues.append(f"Input contains placeholder text: '{placeholder}'")
        
        # Check for encoding issues
        if '�' in input_text:
            issues.append("Input contains encoding issues (replacement characters)")
        
        # Check for excessive whitespace
        if len(input_text) != len(input_text.strip()):
            issues.append("Input has leading/trailing whitespace")
        
        if '  ' in input_text:
            issues.append("Input contains multiple consecutive spaces")
        
        # Check for very repetitive content
        words = input_text.lower().split()
        if len(words) > 10:
            word_counts = Counter(words)
            most_common = word_counts.most_common(1)[0]
            if most_common[1] > len(words) * 0.3:
                issues.append(f"Input is very repetitive ('{most_common[0]}' appears {most_common[1]} times)")
        
        # Check expected output if provided
        if expected_output:
            # Check for placeholder text in output
            for placeholder in placeholders:
                if placeholder.lower() in expected_output.lower():
                    issues.append(f"Expected output contains placeholder text: '{placeholder}'")
            
            # Check for encoding issues in output
            if '�' in expected_output:
                issues.append("Expected output contains encoding issues")
        
        return issues
    
    def _calculate_statistics(self, samples: List[DatasetSample]) -> Dict[str, Any]:
        """Calculate dataset statistics"""
        if not samples:
            return {}
        
        # Length statistics
        input_lengths = [len(sample.input) for sample in samples]
        output_lengths = [len(sample.expected_output or "") for sample in samples]
        
        # Category distribution
        categories = [sample.category for sample in samples if sample.category]
        category_distribution = dict(Counter(categories))
        
        # Difficulty distribution
        difficulties = [sample.difficulty for sample in samples if sample.difficulty]
        difficulty_distribution = dict(Counter(difficulties))
        
        # Completeness metrics
        has_output = sum(1 for sample in samples if sample.expected_output)
        has_context = sum(1 for sample in samples if sample.context)
        has_difficulty = sum(1 for sample in samples if sample.difficulty)
        has_category = sum(1 for sample in samples if sample.category)
        
        return {
            'total_samples': len(samples),
            'input_length': {
                'mean': sum(input_lengths) / len(input_lengths),
                'min': min(input_lengths),
                'max': max(input_lengths),
                'median': sorted(input_lengths)[len(input_lengths) // 2]
            },
            'output_length': {
                'mean': sum(output_lengths) / len(output_lengths),
                'min': min(output_lengths),
                'max': max(output_lengths),
                'median': sorted(output_lengths)[len(output_lengths) // 2]
            },
            'category_distribution': category_distribution,
            'difficulty_distribution': difficulty_distribution,
            'completeness': {
                'has_output': has_output,
                'has_context': has_context,
                'has_difficulty': has_difficulty,
                'has_category': has_category,
                'output_percentage': (has_output / len(samples)) * 100,
                'context_percentage': (has_context / len(samples)) * 100,
                'difficulty_percentage': (has_difficulty / len(samples)) * 100,
                'category_percentage': (has_category / len(samples)) * 100
            }
        }
    
    def _calculate_quality_score(self, samples: List[DatasetSample], errors: List[str], warnings: List[str]) -> float:
        """Calculate overall quality score"""
        if not samples:
            return 0.0
        
        # Start with base score
        score = 1.0
        
        # Penalize errors heavily
        error_penalty = len(errors) * 0.1
        score -= error_penalty
        
        # Penalize warnings moderately
        warning_penalty = len(warnings) * 0.02
        score -= warning_penalty
        
        # Bonus for completeness
        completeness_bonus = 0.0
        
        # Check for expected outputs
        has_output = sum(1 for sample in samples if sample.expected_output)
        output_ratio = has_output / len(samples)
        completeness_bonus += output_ratio * 0.2
        
        # Check for metadata
        has_difficulty = sum(1 for sample in samples if sample.difficulty)
        difficulty_ratio = has_difficulty / len(samples)
        completeness_bonus += difficulty_ratio * 0.1
        
        has_category = sum(1 for sample in samples if sample.category)
        category_ratio = has_category / len(samples)
        completeness_bonus += category_ratio * 0.1
        
        score += completeness_bonus
        
        # Bonus for size
        if len(samples) >= 100:
            score += 0.1
        elif len(samples) >= 50:
            score += 0.05
        
        # Bonus for balance
        if len(samples) > 1:
            categories = [sample.category for sample in samples if sample.category]
            if categories:
                category_counts = Counter(categories)
                # Calculate entropy for balance
                total = len(categories)
                entropy = -sum((count/total) * math.log2(count/total) for count in category_counts.values())
                max_entropy = math.log2(len(category_counts))
                balance_score = entropy / max_entropy if max_entropy > 0 else 0
                score += balance_score * 0.1
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))
    
    def _calculate_sample_quality_score(self, sample: DatasetSample, errors: List[str], warnings: List[str]) -> float:
        """Calculate quality score for individual sample"""
        score = 1.0
        
        # Penalize errors and warnings
        score -= len(errors) * 0.2
        score -= len(warnings) * 0.1
        
        # Bonus for completeness
        if sample.expected_output:
            score += 0.2
        if sample.difficulty:
            score += 0.1
        if sample.category:
            score += 0.1
        if sample.context:
            score += 0.1
        
        # Bonus for reasonable length
        input_length = len(sample.input)
        if 50 <= input_length <= 1000:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def get_quality_label(self, quality_score: float) -> str:
        """Get human-readable quality label"""
        if quality_score >= self.quality_thresholds['excellent']:
            return 'Excellent'
        elif quality_score >= self.quality_thresholds['good']:
            return 'Good'
        elif quality_score >= self.quality_thresholds['fair']:
            return 'Fair'
        elif quality_score >= self.quality_thresholds['poor']:
            return 'Poor'
        else:
            return 'Very Poor'
    
    def suggest_improvements(self, validation_result: ValidationResult) -> List[str]:
        """Generate improvement suggestions based on validation results"""
        suggestions = validation_result.suggestions.copy()
        
        # Add specific suggestions based on quality score
        if validation_result.quality_score < 0.7:
            suggestions.append("Consider reviewing and improving data quality")
        
        if validation_result.quality_score < 0.5:
            suggestions.append("Dataset needs significant improvement before use")
        
        # Add suggestions based on statistics
        if 'completeness' in validation_result.statistics:
            completeness = validation_result.statistics['completeness']
            
            if completeness['output_percentage'] < 50:
                suggestions.append("Add expected outputs for better evaluation accuracy")
            
            if completeness['category_percentage'] < 50:
                suggestions.append("Add categories for better organization and analysis")
            
            if completeness['difficulty_percentage'] < 50:
                suggestions.append("Add difficulty levels for stratified evaluation")
        
        return suggestions
    
    def generate_report(self, validation_result: ValidationResult) -> str:
        """Generate comprehensive validation report"""
        report = []
        
        # Header
        report.append("=" * 60)
        report.append("DATA VALIDATION REPORT")
        report.append("=" * 60)
        report.append()
        
        # Summary
        report.append(f"Overall Quality: {self.get_quality_label(validation_result.quality_score)}")
        report.append(f"Quality Score: {validation_result.quality_score:.3f}")
        report.append(f"Is Valid: {'Yes' if validation_result.is_valid else 'No'}")
        report.append()
        
        # Statistics
        if validation_result.statistics:
            report.append("STATISTICS")
            report.append("-" * 30)
            stats = validation_result.statistics
            
            if 'total_samples' in stats:
                report.append(f"Total Samples: {stats['total_samples']}")
            
            if 'input_length' in stats:
                il = stats['input_length']
                report.append(f"Input Length - Mean: {il['mean']:.1f}, Min: {il['min']}, Max: {il['max']}")
            
            if 'completeness' in stats:
                comp = stats['completeness']
                report.append(f"Completeness - Outputs: {comp['output_percentage']:.1f}%, Categories: {comp['category_percentage']:.1f}%")
            
            report.append()
        
        # Errors
        if validation_result.errors:
            report.append("ERRORS")
            report.append("-" * 30)
            for error in validation_result.errors:
                report.append(f"❌ {error}")
            report.append()
        
        # Warnings
        if validation_result.warnings:
            report.append("WARNINGS")
            report.append("-" * 30)
            for warning in validation_result.warnings:
                report.append(f"⚠️ {warning}")
            report.append()
        
        # Suggestions
        all_suggestions = self.suggest_improvements(validation_result)
        if all_suggestions:
            report.append("SUGGESTIONS")
            report.append("-" * 30)
            for suggestion in all_suggestions:
                report.append(f"💡 {suggestion}")
            report.append()
        
        return "\n".join(report)