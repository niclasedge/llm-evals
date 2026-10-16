"""
Standardized test prompts for image generation model evaluation
"""

from typing import Dict, List, Any

# Test prompts categorized by type and complexity
IMAGE_TEST_PROMPTS = [
    # Realistic Human Subjects
    {
        "category": "realistic_human",
        "prompt": "A professional headshot of a smiling person in business attire",
        "description": "Tests realistic human representation and professional context",
        "complexity": "basic",
        "expected_elements": ["human face", "business attire", "smile", "professional lighting"]
    },
    {
        "category": "realistic_human",
        "prompt": "An elderly person reading a book in a cozy library setting",
        "description": "Tests age representation and environmental context",
        "complexity": "intermediate",
        "expected_elements": ["elderly person", "book", "library", "cozy atmosphere"]
    },
    {
        "category": "realistic_human",
        "prompt": "A diverse group of people collaborating in a modern office environment",
        "description": "Tests diversity representation and group dynamics",
        "complexity": "advanced",
        "expected_elements": ["multiple people", "diversity", "collaboration", "modern office"]
    },
    
    # Artistic and Creative
    {
        "category": "artistic",
        "prompt": "A surreal landscape with floating islands and waterfalls",
        "description": "Tests creative and artistic capabilities",
        "complexity": "intermediate",
        "expected_elements": ["floating islands", "waterfalls", "surreal elements", "landscape"]
    },
    {
        "category": "artistic",
        "prompt": "An abstract painting in the style of Kandinsky with vibrant colors",
        "description": "Tests artistic style mimicry and abstraction",
        "complexity": "advanced",
        "expected_elements": ["abstract forms", "vibrant colors", "artistic style", "composition"]
    },
    {
        "category": "artistic",
        "prompt": "A minimalist geometric composition with primary colors",
        "description": "Tests understanding of artistic movements and color theory",
        "complexity": "intermediate",
        "expected_elements": ["geometric shapes", "primary colors", "minimalist style", "composition"]
    },
    
    # Objects and Scenes
    {
        "category": "objects",
        "prompt": "A red sports car on a mountain road during sunset",
        "description": "Tests object recognition and scene composition",
        "complexity": "basic",
        "expected_elements": ["red sports car", "mountain road", "sunset", "scenic composition"]
    },
    {
        "category": "objects",
        "prompt": "A vintage typewriter on a wooden desk with scattered papers",
        "description": "Tests vintage object representation and scene detail",
        "complexity": "intermediate",
        "expected_elements": ["vintage typewriter", "wooden desk", "scattered papers", "detailed textures"]
    },
    {
        "category": "objects",
        "prompt": "A futuristic robot serving coffee in a cyberpunk café",
        "description": "Tests futuristic concepts and complex scene creation",
        "complexity": "advanced",
        "expected_elements": ["futuristic robot", "coffee service", "cyberpunk aesthetic", "café setting"]
    },
    
    # Nature and Animals
    {
        "category": "nature",
        "prompt": "A majestic lion in the African savanna at golden hour",
        "description": "Tests animal representation and natural lighting",
        "complexity": "basic",
        "expected_elements": ["lion", "African savanna", "golden hour lighting", "natural habitat"]
    },
    {
        "category": "nature",
        "prompt": "A underwater coral reef scene with tropical fish",
        "description": "Tests underwater environment and marine life",
        "complexity": "intermediate",
        "expected_elements": ["coral reef", "tropical fish", "underwater lighting", "marine ecosystem"]
    },
    {
        "category": "nature",
        "prompt": "A misty forest path with ancient trees and filtered sunlight",
        "description": "Tests atmospheric effects and natural environments",
        "complexity": "intermediate",
        "expected_elements": ["misty atmosphere", "forest path", "ancient trees", "filtered sunlight"]
    },
    
    # Architecture and Urban
    {
        "category": "architecture",
        "prompt": "A modern glass skyscraper reflecting the sky",
        "description": "Tests architectural representation and reflective surfaces",
        "complexity": "basic",
        "expected_elements": ["glass skyscraper", "sky reflection", "modern architecture", "urban setting"]
    },
    {
        "category": "architecture",
        "prompt": "An ancient Roman amphitheater at twilight with dramatic lighting",
        "description": "Tests historical architecture and atmospheric lighting",
        "complexity": "advanced",
        "expected_elements": ["Roman amphitheater", "twilight lighting", "ancient architecture", "dramatic atmosphere"]
    },
    {
        "category": "architecture",
        "prompt": "A cozy cottage with a thatched roof in an English countryside",
        "description": "Tests traditional architecture and rural settings",
        "complexity": "intermediate",
        "expected_elements": ["cottage", "thatched roof", "English countryside", "rural charm"]
    },
    
    # Fantasy and Sci-Fi
    {
        "category": "fantasy",
        "prompt": "A dragon flying over a medieval castle",
        "description": "Tests fantasy creature representation and medieval settings",
        "complexity": "intermediate",
        "expected_elements": ["dragon", "medieval castle", "fantasy elements", "flying creature"]
    },
    {
        "category": "fantasy",
        "prompt": "A wizard casting a spell in a magical forest with glowing mushrooms",
        "description": "Tests magical themes and fantastical environments",
        "complexity": "advanced",
        "expected_elements": ["wizard", "spell casting", "magical forest", "glowing mushrooms"]
    },
    {
        "category": "sci_fi",
        "prompt": "A spaceship landing on an alien planet with multiple moons",
        "description": "Tests science fiction concepts and alien environments",
        "complexity": "advanced",
        "expected_elements": ["spaceship", "alien planet", "multiple moons", "sci-fi elements"]
    },
    
    # Technical and Detailed
    {
        "category": "technical",
        "prompt": "A detailed technical diagram of a mechanical watch",
        "description": "Tests technical accuracy and detailed mechanical representation",
        "complexity": "advanced",
        "expected_elements": ["mechanical watch", "technical detail", "diagram style", "precision"]
    },
    {
        "category": "technical",
        "prompt": "A cutaway view of a modern electric car showing the battery system",
        "description": "Tests technical visualization and modern technology",
        "complexity": "advanced",
        "expected_elements": ["electric car", "cutaway view", "battery system", "technical accuracy"]
    },
    
    # Food and Still Life
    {
        "category": "food",
        "prompt": "A gourmet meal plated elegantly on a fine dining table",
        "description": "Tests food presentation and fine dining aesthetics",
        "complexity": "intermediate",
        "expected_elements": ["gourmet meal", "elegant plating", "fine dining", "food styling"]
    },
    {
        "category": "food",
        "prompt": "A rustic bread loaf with fresh ingredients on a wooden cutting board",
        "description": "Tests food textures and rustic styling",
        "complexity": "basic",
        "expected_elements": ["bread loaf", "fresh ingredients", "wooden cutting board", "rustic style"]
    }
]

# Complexity-based prompt sets
BASIC_PROMPTS = [p for p in IMAGE_TEST_PROMPTS if p["complexity"] == "basic"]
INTERMEDIATE_PROMPTS = [p for p in IMAGE_TEST_PROMPTS if p["complexity"] == "intermediate"]
ADVANCED_PROMPTS = [p for p in IMAGE_TEST_PROMPTS if p["complexity"] == "advanced"]

# Category-based prompt sets
PROMPT_CATEGORIES = {
    "realistic_human": [p for p in IMAGE_TEST_PROMPTS if p["category"] == "realistic_human"],
    "artistic": [p for p in IMAGE_TEST_PROMPTS if p["category"] == "artistic"],
    "objects": [p for p in IMAGE_TEST_PROMPTS if p["category"] == "objects"],
    "nature": [p for p in IMAGE_TEST_PROMPTS if p["category"] == "nature"],
    "architecture": [p for p in IMAGE_TEST_PROMPTS if p["category"] == "architecture"],
    "fantasy": [p for p in IMAGE_TEST_PROMPTS if p["category"] == "fantasy"],
    "sci_fi": [p for p in IMAGE_TEST_PROMPTS if p["category"] == "sci_fi"],
    "technical": [p for p in IMAGE_TEST_PROMPTS if p["category"] == "technical"],
    "food": [p for p in IMAGE_TEST_PROMPTS if p["category"] == "food"]
}


def get_prompts_by_category(category: str) -> List[Dict[str, Any]]:
    """Get prompts filtered by category"""
    return PROMPT_CATEGORIES.get(category, [])


def get_prompts_by_complexity(complexity: str) -> List[Dict[str, Any]]:
    """Get prompts filtered by complexity level"""
    return [p for p in IMAGE_TEST_PROMPTS if p["complexity"] == complexity]


def get_random_prompt_set(count: int = 5) -> List[Dict[str, Any]]:
    """Get a random subset of prompts for testing"""
    import random
    return random.sample(IMAGE_TEST_PROMPTS, min(count, len(IMAGE_TEST_PROMPTS)))


def get_balanced_prompt_set() -> List[Dict[str, Any]]:
    """Get a balanced set of prompts across categories and complexities"""
    balanced_set = []
    
    # Get one prompt from each category
    for category in PROMPT_CATEGORIES:
        category_prompts = PROMPT_CATEGORIES[category]
        if category_prompts:
            balanced_set.append(category_prompts[0])
    
    # Add some variety in complexity
    for complexity in ["basic", "intermediate", "advanced"]:
        complexity_prompts = get_prompts_by_complexity(complexity)
        if complexity_prompts and len(balanced_set) < 15:
            # Add one more from each complexity level if not already included
            for prompt in complexity_prompts:
                if prompt not in balanced_set and len(balanced_set) < 15:
                    balanced_set.append(prompt)
                    break
    
    return balanced_set


def get_evaluation_criteria() -> Dict[str, List[str]]:
    """Get evaluation criteria for different aspects of image generation"""
    return {
        "technical_quality": [
            "Image resolution and clarity",
            "Color accuracy and vibrancy",
            "Composition and framing",
            "Lighting and shadows",
            "Absence of artifacts or distortions"
        ],
        "prompt_adherence": [
            "Accuracy to prompt description",
            "Inclusion of specified elements",
            "Correct style interpretation",
            "Appropriate context and setting",
            "Proper object relationships"
        ],
        "artistic_merit": [
            "Visual appeal and aesthetics",
            "Creative interpretation",
            "Color harmony and balance",
            "Interesting composition",
            "Emotional impact"
        ],
        "realism": [
            "Photorealistic quality (where applicable)",
            "Accurate proportions and anatomy",
            "Realistic textures and materials",
            "Natural lighting and physics",
            "Believable environments"
        ],
        "creativity": [
            "Original interpretation",
            "Unique visual elements",
            "Innovative composition",
            "Unexpected but relevant details",
            "Artistic flair"
        ]
    }