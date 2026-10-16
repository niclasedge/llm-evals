"""Initialize the database with sample data."""

import asyncio
import json
from pathlib import Path
from app.core.database import init_db, async_session_maker
from app.models.tests import TestCategory, TestConfig, TestType, DifficultyLevel
from app.services.providers import sync_providers_from_config


async def load_test_configurations():
    """Load test configurations from JSON files."""
    async with async_session_maker() as session:
        # Create test categories
        categories_data = [
            {"name": "Reasoning", "description": "Logical reasoning and problem-solving tests", "test_type": TestType.REASONING},
            {"name": "Coding", "description": "Programming and code generation tests", "test_type": TestType.CODE_GENERATION},
            {"name": "Text Generation", "description": "Creative writing and text generation tests", "test_type": TestType.TEXT_GENERATION},
            {"name": "Vision", "description": "Image analysis and understanding tests", "test_type": TestType.VISION},
        ]

        for cat_data in categories_data:
            category = TestCategory(**cat_data)
            session.add(category)

        await session.commit()

        # Load test configurations from JSON files
        test_dirs = [
            ("tests/reasoning", "Reasoning"),
            ("tests/coding", "Coding"),
            ("tests/text", "Text Generation"),
            ("tests/vision", "Vision")
        ]

        for test_dir, category_name in test_dirs:
            # Find the category
            from sqlmodel import select
            result = await session.execute(select(TestCategory).where(TestCategory.name == category_name))
            category = result.scalar_one_or_none()

            if not category:
                print(f"Category '{category_name}' not found, skipping {test_dir}")
                continue

            # Load JSON files from the directory
            test_path = Path(test_dir)
            if test_path.exists():
                for json_file in test_path.glob("*.json"):
                    try:
                        with open(json_file, 'r') as f:
                            test_data = json.load(f)

                        for test in test_data.get("tests", []):
                            # Map difficulty string to enum
                            difficulty_map = {
                                "easy": DifficultyLevel.EASY,
                                "medium": DifficultyLevel.MEDIUM,
                                "hard": DifficultyLevel.HARD,
                                "expert": DifficultyLevel.EXPERT
                            }

                            test_config = TestConfig(
                                name=test["name"],
                                category_id=category.id,
                                prompt=test["prompt"],
                                expected_output=test.get("expected_output"),
                                difficulty=difficulty_map.get(test.get("difficulty", "medium"), DifficultyLevel.MEDIUM),
                                tags=test.get("tags", []),
                                evaluation_prompt=test.get("evaluation_prompt"),
                                evaluation_criteria=test.get("evaluation_criteria", {}),
                                timeout=30,
                                temperature=0.7
                            )
                            session.add(test_config)

                        print(f"Loaded {len(test_data.get('tests', []))} tests from {json_file}")

                    except Exception as e:
                        print(f"Error loading {json_file}: {e}")

        await session.commit()


async def main():
    """Initialize database with sample data."""
    print("Initializing database...")
    await init_db()
    print("Database tables created.")

    print("Syncing providers from configuration...")
    async with async_session_maker() as session:
        result = await sync_providers_from_config(session)
        print(f"Synced {result['providers']} providers and {result['models']} models.")

    print("Loading test configurations...")
    await load_test_configurations()
    print("Test configurations loaded.")

    print("Database initialization complete!")


if __name__ == "__main__":
    asyncio.run(main())