# Vision Test Cases for LLM Vision Testing

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

from . import config


@dataclass
class VisionTestCase:
    """Container for vision test case definition."""
    name: str
    category: str
    image_path: str
    query: str
    expected_elements: List[str]
    description: Optional[str] = None
    difficulty: Optional[str] = "medium"  # easy, medium, hard
    metadata: Optional[Dict[str, Any]] = None


class VisionTestCaseFactory:
    """Factory class to create vision test cases."""
    
    @staticmethod
    def get_object_recognition_tests() -> List[VisionTestCase]:
        """Get object recognition test cases."""
        base_path = Path(config.VISION_TEST_IMAGES_PATH) / "object_recognition"
        
        return [
            VisionTestCase(
                name="simple_car_recognition",
                category="object_recognition",
                image_path=str(base_path / "car_red.jpg"),
                query="What object do you see in this image? Describe its color and type.",
                expected_elements=["car", "red", "vehicle", "automobile"],
                description="Identify a simple red car object",
                difficulty="easy"
            ),
            VisionTestCase(
                name="cat_sitting_identification",
                category="object_recognition",
                image_path=str(base_path / "cat_sitting.jpg"),
                query="What animal is shown in this image? What is it doing?",
                expected_elements=["cat", "sitting", "animal", "pet"],
                description="Identify a cat in sitting position",
                difficulty="easy"
            ),
            VisionTestCase(
                name="multiple_fruits_counting",
                category="object_recognition",
                image_path=str(base_path / "multiple_fruits.jpg"),
                query="How many different types of fruits can you see? List them.",
                expected_elements=["apple", "banana", "orange", "fruit", "bowl"],
                description="Count and identify multiple fruits in a bowl",
                difficulty="medium"
            ),
            VisionTestCase(
                name="desk_setup_items",
                category="object_recognition",
                image_path=str(base_path / "desk_setup.jpg"),
                query="What items are visible on this desk? List as many as you can see.",
                expected_elements=["computer", "monitor", "keyboard", "mouse", "desk"],
                description="Identify multiple objects on a computer desk",
                difficulty="medium"
            ),
            VisionTestCase(
                name="kitchen_tools_identification",
                category="object_recognition",
                image_path=str(base_path / "kitchen_tools.jpg"),
                query="What kitchen utensils and tools can you identify in this image?",
                expected_elements=["knife", "spoon", "fork", "cutting board", "utensils"],
                description="Identify various kitchen tools and utensils",
                difficulty="medium"
            )
        ]
    
    @staticmethod
    def get_scene_description_tests() -> List[VisionTestCase]:
        """Get scene description test cases."""
        base_path = Path(config.VISION_TEST_IMAGES_PATH) / "scene_description"
        
        return [
            VisionTestCase(
                name="living_room_scene",
                category="scene_description",
                image_path=str(base_path / "living_room.jpg"),
                query="Describe this room in detail. What type of room is it and what can you see?",
                expected_elements=["living room", "sofa", "furniture", "room", "comfortable"],
                description="Describe a furnished living room scene",
                difficulty="medium"
            ),
            VisionTestCase(
                name="kitchen_cooking_activity",
                category="scene_description",
                image_path=str(base_path / "kitchen_cooking.jpg"),
                query="What is happening in this kitchen scene? Describe the activity and setting.",
                expected_elements=["cooking", "kitchen", "person", "preparation", "food"],
                description="Describe cooking activity in kitchen",
                difficulty="medium"
            ),
            VisionTestCase(
                name="park_playground_scene",
                category="scene_description",
                image_path=str(base_path / "park_playground.jpg"),
                query="Describe this outdoor scene. What kind of place is this and what activities are happening?",
                expected_elements=["park", "playground", "children", "playing", "outdoor"],
                description="Describe children playing in park",
                difficulty="medium"
            ),
            VisionTestCase(
                name="busy_street_scene",
                category="scene_description",
                image_path=str(base_path / "street_busy.jpg"),
                query="Describe this urban scene. What can you observe about the activity and environment?",
                expected_elements=["street", "city", "busy", "people", "urban"],
                description="Describe a busy city street scene",
                difficulty="hard"
            ),
            VisionTestCase(
                name="beach_sunset_atmosphere",
                category="scene_description",
                image_path=str(base_path / "beach_sunset.jpg"),
                query="Describe the atmosphere and setting of this beach scene. What time of day is it?",
                expected_elements=["beach", "sunset", "evening", "ocean", "peaceful"],
                description="Describe beach scene at sunset",
                difficulty="medium"
            )
        ]
    
    @staticmethod
    def get_text_in_image_tests() -> List[VisionTestCase]:
        """Get text-in-image test cases."""
        base_path = Path(config.VISION_TEST_IMAGES_PATH) / "text_in_image"
        
        return [
            VisionTestCase(
                name="restaurant_sign_reading",
                category="text_in_image",
                image_path=str(base_path / "sign_restaurant.jpg"),
                query="What text can you read on this restaurant sign?",
                expected_elements=["restaurant", "sign", "text", "name"],
                description="Read text from restaurant sign",
                difficulty="easy"
            ),
            VisionTestCase(
                name="book_cover_title",
                category="text_in_image",
                image_path=str(base_path / "book_cover.jpg"),
                query="What is the title of this book? Can you read any other text on the cover?",
                expected_elements=["book", "title", "author", "cover"],
                description="Read book title and author from cover",
                difficulty="easy"
            ),
            VisionTestCase(
                name="menu_prices_reading",
                category="text_in_image",
                image_path=str(base_path / "menu_prices.jpg"),
                query="What menu items and prices can you read from this menu?",
                expected_elements=["menu", "price", "food", "restaurant"],
                description="Read menu items and prices",
                difficulty="medium"
            ),
            VisionTestCase(
                name="handwritten_note_reading",
                category="text_in_image",
                image_path=str(base_path / "note_handwritten.jpg"),
                query="Can you read the handwritten text in this note? What does it say?",
                expected_elements=["note", "handwritten", "text", "message"],
                description="Read handwritten note text",
                difficulty="hard"
            ),
            VisionTestCase(
                name="newspaper_headline_reading",
                category="text_in_image",
                image_path=str(base_path / "newspaper_headline.jpg"),
                query="What is the main headline of this newspaper? Can you read any other text?",
                expected_elements=["newspaper", "headline", "news", "article"],
                description="Read newspaper headline and text",
                difficulty="medium"
            )
        ]
    
    @staticmethod
    def get_visual_reasoning_tests() -> List[VisionTestCase]:
        """Get visual reasoning test cases."""
        base_path = Path(config.VISION_TEST_IMAGES_PATH) / "visual_reasoning"
        
        return [
            VisionTestCase(
                name="shape_sequence_pattern",
                category="visual_reasoning",
                image_path=str(base_path / "sequence_shapes.jpg"),
                query="What pattern do you see in this sequence of shapes? What would come next?",
                expected_elements=["pattern", "sequence", "shapes", "next", "logic"],
                description="Identify pattern in geometric shapes",
                difficulty="medium"
            ),
            VisionTestCase(
                name="color_pattern_puzzle",
                category="visual_reasoning",
                image_path=str(base_path / "pattern_colors.jpg"),
                query="Analyze this color pattern. What is the rule or logic behind the arrangement?",
                expected_elements=["color", "pattern", "rule", "arrangement", "logic"],
                description="Identify color pattern logic",
                difficulty="medium"
            ),
            VisionTestCase(
                name="jigsaw_missing_piece",
                category="visual_reasoning",
                image_path=str(base_path / "jigsaw_piece.jpg"),
                query="What shape would the missing jigsaw piece be? Describe what you see.",
                expected_elements=["jigsaw", "puzzle", "missing", "piece", "shape"],
                description="Determine missing jigsaw piece shape",
                difficulty="hard"
            ),
            VisionTestCase(
                name="maze_solution_path",
                category="visual_reasoning",
                image_path=str(base_path / "maze_solution.jpg"),
                query="Can you trace the solution path through this maze? Describe the route.",
                expected_elements=["maze", "path", "solution", "route", "direction"],
                description="Find solution path through maze",
                difficulty="hard"
            ),
            VisionTestCase(
                name="optical_illusion_analysis",
                category="visual_reasoning",
                image_path=str(base_path / "optical_illusion.jpg"),
                query="What do you see in this optical illusion? Can you describe the visual effect?",
                expected_elements=["illusion", "visual", "effect", "perception", "image"],
                description="Analyze optical illusion effect",
                difficulty="medium"
            )
        ]
    
    @staticmethod
    def get_chart_analysis_tests() -> List[VisionTestCase]:
        """Get chart analysis test cases."""
        base_path = Path(config.VISION_TEST_IMAGES_PATH) / "chart_analysis"
        
        return [
            VisionTestCase(
                name="quarterly_sales_chart",
                category="chart_analysis",
                image_path=str(base_path / "sales_quarterly.jpg"),
                query="What does this sales chart show? What are the quarterly trends?",
                expected_elements=["sales", "quarterly", "chart", "trend", "data"],
                description="Analyze quarterly sales bar chart",
                difficulty="medium"
            ),
            VisionTestCase(
                name="population_comparison_chart",
                category="chart_analysis",
                image_path=str(base_path / "population_cities.jpg"),
                query="Which cities have the highest and lowest population according to this chart?",
                expected_elements=["population", "cities", "highest", "lowest", "comparison"],
                description="Compare city populations from chart",
                difficulty="medium"
            ),
            VisionTestCase(
                name="temperature_trend_graph",
                category="chart_analysis",
                image_path=str(base_path / "temperature_months.jpg"),
                query="What does this temperature graph show? Describe the seasonal patterns.",
                expected_elements=["temperature", "months", "seasonal", "pattern", "trend"],
                description="Analyze monthly temperature trends",
                difficulty="medium"
            ),
            VisionTestCase(
                name="stock_price_line_graph",
                category="chart_analysis",
                image_path=str(base_path / "stock_price.jpg"),
                query="What trend does this stock price graph show? Is it increasing or decreasing?",
                expected_elements=["stock", "price", "trend", "increasing", "decreasing"],
                description="Analyze stock price trend from line graph",
                difficulty="medium"
            ),
            VisionTestCase(
                name="market_share_pie_chart",
                category="chart_analysis",
                image_path=str(base_path / "market_share.jpg"),
                query="What does this pie chart show about market share? Which segment is largest?",
                expected_elements=["market", "share", "pie chart", "segment", "largest"],
                description="Analyze market share distribution",
                difficulty="easy"
            )
        ]
    
    @staticmethod
    def get_all_test_cases() -> List[VisionTestCase]:
        """Get all vision test cases."""
        all_tests = []
        all_tests.extend(VisionTestCaseFactory.get_object_recognition_tests())
        all_tests.extend(VisionTestCaseFactory.get_scene_description_tests())
        all_tests.extend(VisionTestCaseFactory.get_text_in_image_tests())
        all_tests.extend(VisionTestCaseFactory.get_visual_reasoning_tests())
        all_tests.extend(VisionTestCaseFactory.get_chart_analysis_tests())
        return all_tests
    
    @staticmethod
    def get_test_cases_by_category(category: str) -> List[VisionTestCase]:
        """Get test cases for a specific category."""
        category_map = {
            "object_recognition": VisionTestCaseFactory.get_object_recognition_tests,
            "scene_description": VisionTestCaseFactory.get_scene_description_tests,
            "text_in_image": VisionTestCaseFactory.get_text_in_image_tests,
            "visual_reasoning": VisionTestCaseFactory.get_visual_reasoning_tests,
            "chart_analysis": VisionTestCaseFactory.get_chart_analysis_tests
        }
        
        if category in category_map:
            return category_map[category]()
        else:
            print(f"Warning: Unknown category '{category}'. Available categories: {list(category_map.keys())}")
            return []
    
    @staticmethod
    def get_test_cases_by_difficulty(difficulty: str) -> List[VisionTestCase]:
        """Get test cases filtered by difficulty level."""
        all_tests = VisionTestCaseFactory.get_all_test_cases()
        return [test for test in all_tests if test.difficulty == difficulty]
    
    @staticmethod
    def get_sample_test_cases(count: int = 5) -> List[VisionTestCase]:
        """Get a sample of test cases for quick testing."""
        all_tests = VisionTestCaseFactory.get_all_test_cases()
        
        # Select one test from each category if possible
        sample_tests = []
        categories = set(test.category for test in all_tests)
        
        for category in categories:
            category_tests = [test for test in all_tests if test.category == category]
            if category_tests:
                sample_tests.append(category_tests[0])
            if len(sample_tests) >= count:
                break
        
        return sample_tests[:count]


def main():
    """Main function for testing vision test cases."""
    print("Vision Test Cases")
    print("="*50)
    
    # Test each category
    for category in config.VISION_TEST_CATEGORIES:
        print(f"\n{category.replace('_', ' ').title()} Tests:")
        tests = VisionTestCaseFactory.get_test_cases_by_category(category)
        for test in tests:
            print(f"  - {test.name}: {test.description}")
    
    # Show total counts
    all_tests = VisionTestCaseFactory.get_all_test_cases()
    print(f"\nTotal test cases: {len(all_tests)}")
    
    # Show sample tests
    sample_tests = VisionTestCaseFactory.get_sample_test_cases(3)
    print(f"\nSample tests for quick testing:")
    for test in sample_tests:
        print(f"  - {test.name} ({test.category}): {test.description}")


if __name__ == "__main__":
    main()