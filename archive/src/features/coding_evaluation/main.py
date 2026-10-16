"""
Main entry point for the coding evaluation feature
"""

import asyncio
import sys
import argparse
from typing import List, Optional
import uvicorn

from .service import CodingEvaluationService
from .endpoints import create_app
# from .llm_integration import CodingEvaluationRunner  # Commented out for now
from .tests.test_coding_evaluation import run_all_tests

def run_server(host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
    """Run the FastAPI server"""
    app = create_app()
    
    print(f"🚀 Starting Coding Evaluation Server on {host}:{port}")
    print(f"📖 API Documentation: http://{host}:{port}/docs")
    print(f"🌐 Web Interface: http://{host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=debug,
        log_level="info" if debug else "warning"
    )

def run_tests():
    """Run all tests for the coding evaluation feature"""
    print("🧪 Running Coding Evaluation Tests...")
    try:
        run_all_tests()
        print("\n✅ All tests passed!")
        return True
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        return False

async def run_llm_evaluation(problems: Optional[List[str]] = None,
                           languages: Optional[List[str]] = None,
                           difficulty: Optional[str] = None):
    """Run LLM coding evaluation"""
    print("🤖 LLM Coding Evaluation is not yet implemented in this demo.")
    print("This feature requires integration with the existing LLM evaluation framework.")
    print("For now, you can:")
    print("  1. Use the web interface to manually test code")
    print("  2. Run the coding evaluation tests")
    print("  3. Start the web server")
    
    return {"summary": {"message": "LLM evaluation not implemented yet"}}

def create_sample_problems():
    """Create additional sample problems"""
    from .models import CodingProblem, TestCase, ProgrammingLanguage, ProblemDifficulty
    import json
    import os
    
    print("📝 Creating additional sample problems...")
    
    # Factorial problem
    factorial_problem = CodingProblem(
        id="factorial",
        title="Factorial Calculation",
        description="Write a function that calculates the factorial of a non-negative integer n. Factorial of n (n!) is the product of all positive integers less than or equal to n.",
        difficulty=ProblemDifficulty.EASY,
        languages=[ProgrammingLanguage.PYTHON, ProgrammingLanguage.JAVASCRIPT, ProgrammingLanguage.JAVA],
        test_cases=[
            TestCase("1", "0", "1", description="Factorial of 0 is 1"),
            TestCase("2", "1", "1", description="Factorial of 1 is 1"),
            TestCase("3", "5", "120", description="Factorial of 5 is 120"),
            TestCase("4", "7", "5040", description="Factorial of 7 is 5040")
        ],
        starter_code={
            "python": "def factorial(n):\\n    # Write your solution here\\n    pass\\n\\nif __name__ == '__main__':\\n    import sys\\n    n = int(sys.argv[1]) if len(sys.argv) > 1 else int(input())\\n    print(factorial(n))",
            "javascript": "function factorial(n) {\\n    // Write your solution here\\n}\\n\\nconst n = parseInt(process.argv[2]) || parseInt(require('readline-sync').question());\\nconsole.log(factorial(n));",
            "java": "public class Factorial {\\n    public static int factorial(int n) {\\n        // Write your solution here\\n        return 0;\\n    }\\n    \\n    public static void main(String[] args) {\\n        int n = args.length > 0 ? Integer.parseInt(args[0]) : new java.util.Scanner(System.in).nextInt();\\n        System.out.println(factorial(n));\\n    }\\n}"
        },
        tags=["math", "recursion", "basic"]
    )
    
    # Array sum problem
    array_sum_problem = CodingProblem(
        id="array_sum",
        title="Array Sum",
        description="Write a function that calculates the sum of all elements in an array of integers.",
        difficulty=ProblemDifficulty.EASY,
        languages=[ProgrammingLanguage.PYTHON, ProgrammingLanguage.JAVASCRIPT],
        test_cases=[
            TestCase("1", "[1,2,3,4,5]", "15", description="Sum of [1,2,3,4,5] is 15"),
            TestCase("2", "[10,20,30]", "60", description="Sum of [10,20,30] is 60"),
            TestCase("3", "[]", "0", description="Sum of empty array is 0"),
            TestCase("4", "[-1,1,-2,2]", "0", description="Sum with negative numbers")
        ],
        starter_code={
            "python": "def array_sum(arr):\\n    # Write your solution here\\n    pass\\n\\nif __name__ == '__main__':\\n    import sys\\n    import json\\n    arr = json.loads(sys.argv[1]) if len(sys.argv) > 1 else json.loads(input())\\n    print(array_sum(arr))",
            "javascript": "function arraySum(arr) {\\n    // Write your solution here\\n}\\n\\nconst arr = JSON.parse(process.argv[2]) || JSON.parse(require('readline-sync').question());\\nconsole.log(arraySum(arr));"
        },
        tags=["array", "basic", "math"]
    )
    
    # Save problems
    problems_dir = "data/coding_evaluation/problems"
    os.makedirs(problems_dir, exist_ok=True)
    
    problems = [factorial_problem, array_sum_problem]
    
    for problem in problems:
        filename = f"{problems_dir}/{problem.id}.json"
        with open(filename, 'w') as f:
            # Convert to dict for JSON serialization
            problem_dict = {
                "id": problem.id,
                "title": problem.title,
                "description": problem.description,
                "difficulty": problem.difficulty.value,
                "languages": [lang.value for lang in problem.languages],
                "test_cases": [
                    {
                        "id": tc.id,
                        "input_data": tc.input_data,
                        "expected_output": tc.expected_output,
                        "time_limit": tc.time_limit,
                        "memory_limit": tc.memory_limit,
                        "description": tc.description,
                        "hidden": tc.hidden
                    }
                    for tc in problem.test_cases
                ],
                "starter_code": problem.starter_code,
                "solution": problem.solution,
                "tags": problem.tags,
                "time_limit": problem.time_limit,
                "memory_limit": problem.memory_limit,
                "created_at": problem.created_at.isoformat(),
                "updated_at": problem.updated_at.isoformat()
            }
            json.dump(problem_dict, f, indent=2)
        
        print(f"✅ Created problem: {problem.title}")
    
    print(f"📁 Problems saved to {problems_dir}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Coding Evaluation Platform")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Run the web server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    server_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    server_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    
    # LLM evaluation command
    llm_parser = subparsers.add_parser("llm-eval", help="Run LLM coding evaluation")
    llm_parser.add_argument("--problems", nargs="*", help="Specific problems to test")
    llm_parser.add_argument("--languages", nargs="*", help="Languages to test")
    llm_parser.add_argument("--difficulty", help="Difficulty filter")
    
    # Create problems command
    create_parser = subparsers.add_parser("create-problems", help="Create sample problems")
    
    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run a complete demo")
    
    args = parser.parse_args()
    
    if args.command == "server":
        run_server(args.host, args.port, args.debug)
    
    elif args.command == "test":
        success = run_tests()
        sys.exit(0 if success else 1)
    
    elif args.command == "llm-eval":
        asyncio.run(run_llm_evaluation(
            problems=args.problems,
            languages=args.languages,
            difficulty=args.difficulty
        ))
    
    elif args.command == "create-problems":
        create_sample_problems()
    
    elif args.command == "demo":
        print("🎯 Running Coding Evaluation Demo...")
        
        # 1. Create sample problems
        create_sample_problems()
        
        # 2. Run tests
        print("\\n" + "="*50)
        success = run_tests()
        
        if not success:
            print("❌ Tests failed. Demo stopped.")
            sys.exit(1)
        
        # 3. Show available problems
        print("\\n" + "="*50)
        print("📚 Available Problems:")
        service = CodingEvaluationService()
        problems = service.get_problems()
        
        for problem in problems:
            print(f"  - {problem.title} ({problem.difficulty.value}) - {', '.join([lang.value for lang in problem.languages])}")
        
        service.cleanup()
        
        print("\\n🎉 Demo completed successfully!")
        print("\\nTo start the web server, run:")
        print("  python -m src.features.coding_evaluation.main server")
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()