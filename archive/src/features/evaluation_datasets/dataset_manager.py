"""
Dataset Manager for LLM Evaluation System
Centralized management of evaluation datasets with versioning and validation
"""

import json
import hashlib
import os
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class DatasetConfig:
    """Configuration for dataset management"""
    name: str
    version: str
    description: str
    dataset_type: str  # 'text', 'code', 'reasoning', 'vision', etc.
    source: str
    license: str
    created_date: str
    tags: List[str]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DatasetSample:
    """Single dataset sample"""
    id: str
    input: str
    expected_output: Optional[str] = None
    context: Optional[str] = None
    difficulty: Optional[str] = None  # 'easy', 'medium', 'hard'
    category: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DatasetMetrics:
    """Metrics for dataset quality"""
    total_samples: int
    avg_input_length: float
    avg_output_length: float
    difficulty_distribution: Dict[str, int]
    category_distribution: Dict[str, int]
    quality_score: float
    coverage_score: float
    diversity_score: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DatasetManager:
    """Manages evaluation datasets with versioning and validation"""
    
    def __init__(self, datasets_dir: str = "datasets"):
        self.datasets_dir = Path(datasets_dir)
        self.datasets_dir.mkdir(exist_ok=True)
        self.datasets: Dict[str, DatasetConfig] = {}
        self.loaded_datasets: Dict[str, List[DatasetSample]] = {}
        self._load_existing_datasets()
    
    def _load_existing_datasets(self):
        """Load existing datasets from storage"""
        config_file = self.datasets_dir / "datasets.yaml"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = yaml.safe_load(f)
                    for name, config_data in data.items():
                        self.datasets[name] = DatasetConfig(**config_data)
            except Exception as e:
                logger.warning(f"Failed to load existing datasets: {e}")
    
    def _save_datasets_config(self):
        """Save datasets configuration"""
        config_file = self.datasets_dir / "datasets.yaml"
        try:
            with open(config_file, 'w') as f:
                data = {name: asdict(config) for name, config in self.datasets.items()}
                yaml.dump(data, f, default_flow_style=False)
        except Exception as e:
            logger.error(f"Failed to save datasets config: {e}")
    
    def create_dataset(self, name: str, dataset_type: str, description: str,
                      source: str = "custom", license: str = "unknown",
                      tags: List[str] = None) -> DatasetConfig:
        """Create a new dataset"""
        if name in self.datasets:
            raise ValueError(f"Dataset {name} already exists")
        
        config = DatasetConfig(
            name=name,
            version="1.0.0",
            description=description,
            dataset_type=dataset_type,
            source=source,
            license=license,
            created_date=datetime.now().isoformat(),
            tags=tags or []
        )
        
        self.datasets[name] = config
        self._save_datasets_config()
        
        # Create dataset directory
        dataset_dir = self.datasets_dir / name
        dataset_dir.mkdir(exist_ok=True)
        
        logger.info(f"Created dataset: {name}")
        return config
    
    def add_samples(self, dataset_name: str, samples: List[DatasetSample]):
        """Add samples to a dataset"""
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        dataset_dir = self.datasets_dir / dataset_name
        dataset_dir.mkdir(exist_ok=True)
        
        # Load existing samples
        existing_samples = self.load_dataset(dataset_name)
        
        # Add new samples
        all_samples = existing_samples + samples
        
        # Save updated samples
        samples_file = dataset_dir / "samples.json"
        try:
            with open(samples_file, 'w') as f:
                json.dump([asdict(sample) for sample in all_samples], f, indent=2)
            
            # Update loaded cache
            self.loaded_datasets[dataset_name] = all_samples
            
            logger.info(f"Added {len(samples)} samples to dataset {dataset_name}")
            
        except Exception as e:
            logger.error(f"Failed to save samples to {dataset_name}: {e}")
            raise
    
    def load_dataset(self, dataset_name: str) -> List[DatasetSample]:
        """Load dataset samples"""
        if dataset_name in self.loaded_datasets:
            return self.loaded_datasets[dataset_name]
        
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        dataset_dir = self.datasets_dir / dataset_name
        samples_file = dataset_dir / "samples.json"
        
        samples = []
        if samples_file.exists():
            try:
                with open(samples_file, 'r') as f:
                    data = json.load(f)
                    samples = [DatasetSample(**sample_data) for sample_data in data]
            except Exception as e:
                logger.error(f"Failed to load samples from {dataset_name}: {e}")
                raise
        
        self.loaded_datasets[dataset_name] = samples
        return samples
    
    def get_dataset_info(self, dataset_name: str) -> Dict[str, Any]:
        """Get comprehensive dataset information"""
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        config = self.datasets[dataset_name]
        samples = self.load_dataset(dataset_name)
        metrics = self.calculate_dataset_metrics(samples)
        
        return {
            'config': asdict(config),
            'metrics': asdict(metrics),
            'sample_count': len(samples),
            'last_updated': datetime.now().isoformat()
        }
    
    def calculate_dataset_metrics(self, samples: List[DatasetSample]) -> DatasetMetrics:
        """Calculate quality metrics for a dataset"""
        if not samples:
            return DatasetMetrics(
                total_samples=0,
                avg_input_length=0.0,
                avg_output_length=0.0,
                difficulty_distribution={},
                category_distribution={},
                quality_score=0.0,
                coverage_score=0.0,
                diversity_score=0.0
            )
        
        # Basic statistics
        total_samples = len(samples)
        input_lengths = [len(sample.input) for sample in samples]
        output_lengths = [len(sample.expected_output or "") for sample in samples]
        
        avg_input_length = sum(input_lengths) / len(input_lengths)
        avg_output_length = sum(output_lengths) / len(output_lengths)
        
        # Distribution analysis
        difficulty_dist = {}
        category_dist = {}
        
        for sample in samples:
            if sample.difficulty:
                difficulty_dist[sample.difficulty] = difficulty_dist.get(sample.difficulty, 0) + 1
            if sample.category:
                category_dist[sample.category] = category_dist.get(sample.category, 0) + 1
        
        # Quality scores (simplified)
        quality_score = self._calculate_quality_score(samples)
        coverage_score = self._calculate_coverage_score(samples)
        diversity_score = self._calculate_diversity_score(samples)
        
        return DatasetMetrics(
            total_samples=total_samples,
            avg_input_length=avg_input_length,
            avg_output_length=avg_output_length,
            difficulty_distribution=difficulty_dist,
            category_distribution=category_dist,
            quality_score=quality_score,
            coverage_score=coverage_score,
            diversity_score=diversity_score
        )
    
    def _calculate_quality_score(self, samples: List[DatasetSample]) -> float:
        """Calculate dataset quality score"""
        if not samples:
            return 0.0
        
        score = 0.0
        
        # Check for completeness
        complete_samples = sum(1 for s in samples if s.expected_output)
        completeness = complete_samples / len(samples)
        score += completeness * 0.3
        
        # Check for metadata richness
        metadata_rich = sum(1 for s in samples if s.difficulty and s.category)
        metadata_score = metadata_rich / len(samples)
        score += metadata_score * 0.3
        
        # Check for reasonable length distribution
        input_lengths = [len(s.input) for s in samples]
        length_variety = len(set(input_lengths)) / len(samples)
        score += length_variety * 0.2
        
        # Check for ID uniqueness
        unique_ids = len(set(s.id for s in samples))
        id_uniqueness = unique_ids / len(samples)
        score += id_uniqueness * 0.2
        
        return score
    
    def _calculate_coverage_score(self, samples: List[DatasetSample]) -> float:
        """Calculate coverage score based on category distribution"""
        if not samples:
            return 0.0
        
        categories = set(s.category for s in samples if s.category)
        if not categories:
            return 0.0
        
        # Calculate evenness of distribution
        category_counts = {}
        for sample in samples:
            if sample.category:
                category_counts[sample.category] = category_counts.get(sample.category, 0) + 1
        
        # Shannon entropy for evenness
        total = sum(category_counts.values())
        entropy = -sum((count/total) * math.log2(count/total) for count in category_counts.values())
        max_entropy = math.log2(len(categories))
        
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def _calculate_diversity_score(self, samples: List[DatasetSample]) -> float:
        """Calculate diversity score based on text similarity"""
        if not samples:
            return 0.0
        
        # Simple diversity measure based on unique words
        all_words = set()
        for sample in samples:
            words = sample.input.lower().split()
            all_words.update(words)
        
        total_words = sum(len(sample.input.split()) for sample in samples)
        unique_words = len(all_words)
        
        return unique_words / total_words if total_words > 0 else 0.0
    
    def stratified_sample(self, dataset_name: str, sample_size: int, 
                         stratify_by: str = 'difficulty') -> List[DatasetSample]:
        """Create stratified sample from dataset"""
        samples = self.load_dataset(dataset_name)
        
        if not samples:
            return []
        
        if sample_size >= len(samples):
            return samples
        
        # Group by stratification key
        groups = {}
        for sample in samples:
            key = getattr(sample, stratify_by, 'unknown')
            if key not in groups:
                groups[key] = []
            groups[key].append(sample)
        
        # Calculate samples per group
        stratified_samples = []
        total_groups = len(groups)
        remaining_sample_size = sample_size
        
        for i, (key, group) in enumerate(groups.items()):
            if i == total_groups - 1:  # Last group gets remaining samples
                group_sample_size = remaining_sample_size
            else:
                group_sample_size = min(len(group), sample_size // total_groups)
            
            # Random sample from group
            import random
            group_samples = random.sample(group, min(group_sample_size, len(group)))
            stratified_samples.extend(group_samples)
            remaining_sample_size -= len(group_samples)
        
        return stratified_samples
    
    def split_dataset(self, dataset_name: str, train_ratio: float = 0.8, 
                     val_ratio: float = 0.1, test_ratio: float = 0.1) -> Tuple[List[DatasetSample], List[DatasetSample], List[DatasetSample]]:
        """Split dataset into train/validation/test sets"""
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
            raise ValueError("Ratios must sum to 1.0")
        
        samples = self.load_dataset(dataset_name)
        
        if not samples:
            return [], [], []
        
        # Shuffle samples
        import random
        shuffled_samples = samples.copy()
        random.shuffle(shuffled_samples)
        
        # Calculate split points
        total_samples = len(shuffled_samples)
        train_end = int(total_samples * train_ratio)
        val_end = train_end + int(total_samples * val_ratio)
        
        train_samples = shuffled_samples[:train_end]
        val_samples = shuffled_samples[train_end:val_end]
        test_samples = shuffled_samples[val_end:]
        
        return train_samples, val_samples, test_samples
    
    def export_dataset(self, dataset_name: str, format: str = 'json') -> str:
        """Export dataset to specified format"""
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        config = self.datasets[dataset_name]
        samples = self.load_dataset(dataset_name)
        
        export_data = {
            'config': asdict(config),
            'samples': [asdict(sample) for sample in samples]
        }
        
        if format.lower() == 'json':
            return json.dumps(export_data, indent=2)
        elif format.lower() == 'yaml':
            return yaml.dump(export_data, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def import_dataset(self, data: str, format: str = 'json') -> str:
        """Import dataset from string data"""
        try:
            if format.lower() == 'json':
                import_data = json.loads(data)
            elif format.lower() == 'yaml':
                import_data = yaml.safe_load(data)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            config_data = import_data['config']
            samples_data = import_data['samples']
            
            # Create dataset
            config = DatasetConfig(**config_data)
            dataset_name = config.name
            
            if dataset_name in self.datasets:
                raise ValueError(f"Dataset {dataset_name} already exists")
            
            self.datasets[dataset_name] = config
            
            # Add samples
            samples = [DatasetSample(**sample_data) for sample_data in samples_data]
            self.add_samples(dataset_name, samples)
            
            self._save_datasets_config()
            
            logger.info(f"Imported dataset: {dataset_name}")
            return dataset_name
            
        except Exception as e:
            logger.error(f"Failed to import dataset: {e}")
            raise
    
    def get_dataset_hash(self, dataset_name: str) -> str:
        """Get hash of dataset for versioning"""
        samples = self.load_dataset(dataset_name)
        data_str = json.dumps([asdict(sample) for sample in samples], sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """List all available datasets"""
        dataset_list = []
        for name, config in self.datasets.items():
            samples = self.load_dataset(name)
            dataset_list.append({
                'name': name,
                'version': config.version,
                'description': config.description,
                'type': config.dataset_type,
                'sample_count': len(samples),
                'created_date': config.created_date,
                'tags': config.tags
            })
        return dataset_list
    
    def delete_dataset(self, dataset_name: str):
        """Delete a dataset"""
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        # Remove from memory
        del self.datasets[dataset_name]
        if dataset_name in self.loaded_datasets:
            del self.loaded_datasets[dataset_name]
        
        # Remove from disk
        dataset_dir = self.datasets_dir / dataset_name
        if dataset_dir.exists():
            import shutil
            shutil.rmtree(dataset_dir)
        
        self._save_datasets_config()
        logger.info(f"Deleted dataset: {dataset_name}")
    
    def validate_dataset(self, dataset_name: str) -> Dict[str, Any]:
        """Validate dataset integrity and quality"""
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        samples = self.load_dataset(dataset_name)
        validation_results = {
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        # Check for duplicate IDs
        ids = [sample.id for sample in samples]
        if len(ids) != len(set(ids)):
            validation_results['errors'].append("Duplicate sample IDs found")
        
        # Check for empty inputs
        empty_inputs = sum(1 for sample in samples if not sample.input.strip())
        if empty_inputs > 0:
            validation_results['errors'].append(f"{empty_inputs} samples have empty inputs")
        
        # Check for missing expected outputs
        missing_outputs = sum(1 for sample in samples if not sample.expected_output)
        if missing_outputs > 0:
            validation_results['warnings'].append(f"{missing_outputs} samples missing expected outputs")
        
        # Check dataset size
        if len(samples) < 10:
            validation_results['warnings'].append("Dataset has fewer than 10 samples")
        
        # Check for metadata completeness
        missing_metadata = sum(1 for sample in samples if not sample.difficulty or not sample.category)
        if missing_metadata > 0:
            validation_results['info'].append(f"{missing_metadata} samples missing metadata")
        
        validation_results['total_samples'] = len(samples)
        validation_results['is_valid'] = len(validation_results['errors']) == 0
        
        return validation_results