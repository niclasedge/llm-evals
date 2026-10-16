"""Test execution and evaluation services."""

import asyncio
import time
from datetime import datetime
from typing import List, Optional
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import async_session_maker
from app.core.llm_client import llm_client, LLMMessage
from app.models.tests import TestConfig
from app.models.providers import Model, Provider
from app.models.results import TestRun, TestResult, TestStatus, Evaluation, EvaluationStatus
from app.core.config import settings


logger = structlog.get_logger()


async def run_tests_async(
    test_run_id: int,
    test_config_ids: List[int],
    model_ids: List[int]
):
    """Run tests asynchronously in background."""
    async with async_session_maker() as session:
        # Get test run
        test_run = await session.get(TestRun, test_run_id)
        if not test_run:
            logger.error("Test run not found", test_run_id=test_run_id)
            return

        try:
            # Update status to running
            test_run.status = TestStatus.RUNNING
            test_run.started_at = datetime.utcnow()
            await session.commit()

            # Get test configs and models
            test_configs = []
            for config_id in test_config_ids:
                config = await session.get(TestConfig, config_id)
                if config:
                    test_configs.append(config)

            models = []
            for model_id in model_ids:
                model = await session.get(Model, model_id)
                if model:
                    models.append(model)

            # Create test results for each test config + model combination
            test_results = []
            for test_config in test_configs:
                for model in models:
                    test_result = TestResult(
                        test_run_id=test_run_id,
                        test_config_id=test_config.id,
                        model_id=model.id,
                        prompt=test_config.prompt,
                        status=TestStatus.PENDING
                    )
                    session.add(test_result)
                    test_results.append(test_result)

            await session.commit()

            # Separate tests by provider type for different concurrency handling
            ollama_test_results = []
            openrouter_test_results = []

            for test_result in test_results:
                # Get the provider for this test result
                model = await session.get(Model, test_result.model_id)
                provider = await session.get(Provider, model.provider_id)

                if provider.name.lower() == "ollama":
                    ollama_test_results.append(test_result)
                else:
                    openrouter_test_results.append(test_result)

            # Run OpenRouter tests in parallel (with concurrency limit)
            openrouter_tasks = []
            if openrouter_test_results:
                semaphore = asyncio.Semaphore(settings.max_concurrent_tests)
                for test_result in openrouter_test_results:
                    task = asyncio.create_task(
                        run_single_test(semaphore, test_result.id)
                    )
                    openrouter_tasks.append(task)

            # Run Ollama tests sequentially (one at a time to avoid conflicts)
            ollama_tasks = []
            if ollama_test_results:
                # Use a semaphore with limit 1 to ensure sequential execution
                ollama_semaphore = asyncio.Semaphore(1)
                for test_result in ollama_test_results:
                    task = asyncio.create_task(
                        run_single_test(ollama_semaphore, test_result.id)
                    )
                    ollama_tasks.append(task)

            # Wait for all tests to complete
            all_tasks = openrouter_tasks + ollama_tasks
            if all_tasks:
                await asyncio.gather(*all_tasks, return_exceptions=True)

            # Update test run status
            async with async_session_maker() as final_session:
                test_run = await final_session.get(TestRun, test_run_id)
                result = await final_session.execute(
                    select(TestResult).where(TestResult.test_run_id == test_run_id)
                )
                results = result.scalars().all()

                test_run.completed_tests = len([r for r in results if r.status == TestStatus.COMPLETED])
                test_run.failed_tests = len([r for r in results if r.status == TestStatus.FAILED])
                test_run.completed_at = datetime.utcnow()
                test_run.duration = (test_run.completed_at - test_run.started_at).total_seconds()

                if test_run.failed_tests == 0:
                    test_run.status = TestStatus.COMPLETED
                else:
                    test_run.status = TestStatus.COMPLETED  # Consider partial completion as completed

                await final_session.commit()

            logger.info("Test run completed", test_run_id=test_run_id, completed=test_run.completed_tests, failed=test_run.failed_tests)

        except Exception as e:
            logger.error("Test run failed", test_run_id=test_run_id, error=str(e))
            test_run.status = TestStatus.FAILED
            test_run.completed_at = datetime.utcnow()
            await session.commit()


async def run_single_test(semaphore: asyncio.Semaphore, test_result_id: int):
    """Run a single test with concurrency control."""
    async with semaphore:
        async with async_session_maker() as session:
            # Get test result and related data
            test_result = await session.get(TestResult, test_result_id)
            if not test_result:
                return

            test_config = await session.get(TestConfig, test_result.test_config_id)
            model = await session.get(Model, test_result.model_id)

            if not test_config or not model:
                test_result.status = TestStatus.FAILED
                test_result.error_message = "Test config or model not found"
                await session.commit()
                return

            # Get provider
            provider = await session.get(Provider, model.provider_id)
            if not provider:
                test_result.status = TestStatus.FAILED
                test_result.error_message = "Provider not found"
                await session.commit()
                return

            try:
                # Update status to running
                test_result.status = TestStatus.RUNNING
                test_result.started_at = datetime.utcnow()
                await session.commit()

                # Prepare messages
                messages = []
                if test_config.system_prompt:
                    messages.append(LLMMessage(role="system", content=test_config.system_prompt))
                messages.append(LLMMessage(role="user", content=test_config.prompt))

                # Generate response
                start_time = time.time()
                response = await llm_client.generate_response(
                    provider_name=provider.name,
                    model=model.model_id,
                    messages=messages,
                    temperature=test_config.temperature,
                    max_tokens=test_config.max_tokens
                )
                end_time = time.time()

                # Update test result
                test_result.response = response.content
                test_result.response_time = end_time - start_time
                test_result.tokens_used = response.usage.get('total_tokens') if response.usage else None
                test_result.raw_response = response.metadata
                test_result.status = TestStatus.COMPLETED
                test_result.completed_at = datetime.utcnow()

                await session.commit()

                # Start evaluation in background if evaluation prompt is provided
                if test_config.evaluation_prompt:
                    asyncio.create_task(evaluate_test_result(test_result.id))

                logger.info("Test completed", test_result_id=test_result_id, model=model.name, response_time=test_result.response_time)

            except asyncio.TimeoutError:
                test_result.status = TestStatus.TIMEOUT
                test_result.error_message = "Test timed out"
                test_result.completed_at = datetime.utcnow()
                await session.commit()
                logger.warning("Test timed out", test_result_id=test_result_id, model=model.name)

            except Exception as e:
                test_result.status = TestStatus.FAILED
                test_result.error_message = str(e)
                test_result.completed_at = datetime.utcnow()
                await session.commit()
                logger.error("Test failed", test_result_id=test_result_id, model=model.name, error=str(e))


async def evaluate_test_result(test_result_id: int, evaluator_model_name: str = "gemini-2.5-flash-lite"):
    """Evaluate a test result using Gemini LLM with structured JSON output."""
    async with async_session_maker() as session:
        test_result = await session.get(TestResult, test_result_id)
        if not test_result:
            return

        test_config = await session.get(TestConfig, test_result.test_config_id)
        if not test_config or not test_config.evaluation_prompt:
            return

        # Find Gemini evaluator model
        evaluator_result = await session.execute(
            select(Model)
            .join(Provider)
            .where(Model.model_id == "google/gemini-2.5-flash-lite", Model.is_enabled == True)
        )
        evaluator = evaluator_result.scalars().first()

        if not evaluator:
            logger.warning("Gemini evaluator model not found", model_name=evaluator_model_name)
            return

        evaluator_provider = await session.get(Provider, evaluator.provider_id)

        try:
            # Create evaluation record
            evaluation = Evaluation(
                test_result_id=test_result_id,
                evaluator_model_id=evaluator.id,
                evaluation_prompt=test_config.evaluation_prompt,
                status=EvaluationStatus.PENDING,
                evaluation_criteria=test_config.evaluation_criteria
            )
            session.add(evaluation)
            await session.commit()
            # Remove refresh to avoid session issues
            # await session.refresh(evaluation)

            # Prepare structured evaluation prompt for JSON output
            optimal_answer = test_config.expected_output or "The answer should correctly address the prompt with accuracy and clarity."

            evaluation_prompt = f"""You are an expert AI evaluator. Evaluate the following AI model response and provide a structured JSON assessment.

**Original Prompt:**
{test_result.prompt}

**AI Model Response:**
{test_result.response}

**Optimal Answer/Expected Output:**
{optimal_answer}

**Evaluation Task:**
{test_config.evaluation_prompt}

Please evaluate the AI model's response and provide your assessment in the following JSON format:

{{
  "score": [integer from 1-10],
  "reasoning": "[detailed explanation of why you gave this score]",
  "strengths": ["list", "of", "response", "strengths"],
  "weaknesses": ["list", "of", "response", "weaknesses"],
  "accuracy": [float 0.0-1.0],
  "relevance": [float 0.0-1.0],
  "clarity": [float 0.0-1.0],
  "suggestions": ["list", "of", "improvement", "suggestions"]
}}

Respond ONLY with the JSON object, no additional text."""

            messages = [
                LLMMessage(role="system", content="You are an expert AI evaluator. Provide only JSON responses in the exact format requested."),
                LLMMessage(role="user", content=evaluation_prompt)
            ]

            # Generate evaluation
            response = await llm_client.generate_response(
                provider_name=evaluator_provider.name,
                model=evaluator.model_id,
                messages=messages,
                temperature=0.1  # Low temperature for consistent evaluation
            )

            # Parse JSON response (handle markdown code blocks)
            import json
            import re
            try:
                # Clean the response - remove markdown code blocks if present
                content = response.content.strip()

                # Remove markdown code blocks
                if content.startswith("```"):
                    # Extract content between code blocks
                    match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
                    if match:
                        content = match.group(1).strip()
                    else:
                        # Fallback: remove first and last lines if they contain ```
                        lines = content.split('\n')
                        if lines[0].startswith('```'):
                            lines = lines[1:]
                        if lines and lines[-1].startswith('```'):
                            lines = lines[:-1]
                        content = '\n'.join(lines).strip()

                evaluation_data = json.loads(content)

                # Store the raw JSON response
                evaluation.evaluation_response = response.content
                evaluation.status = EvaluationStatus.COMPLETED

                # Extract and store structured data
                evaluation.overall_score = evaluation_data.get("score", 5) / 10.0  # Convert 1-10 to 0.0-1.0
                evaluation.accuracy_score = evaluation_data.get("accuracy", 0.5)
                evaluation.relevance_score = evaluation_data.get("relevance", 0.5)
                evaluation.strengths = evaluation_data.get("strengths", [])
                evaluation.weaknesses = evaluation_data.get("weaknesses", [])
                evaluation.suggestions = evaluation_data.get("suggestions", [])

                # Store reasoning in metadata
                evaluation.metadata_ = {
                    "reasoning": evaluation_data.get("reasoning", ""),
                    "clarity_score": evaluation_data.get("clarity", 0.5),
                    "raw_score": evaluation_data.get("score", 5)
                }

                logger.info("JSON evaluation completed",
                           test_result_id=test_result_id,
                           score=evaluation.overall_score,
                           raw_score=evaluation_data.get("score", 5))

            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON evaluation response",
                           test_result_id=test_result_id,
                           error=str(e),
                           response=response.content[:500],
                           cleaned_content=content[:500] if 'content' in locals() else "N/A")

                # Fallback: store as failed but keep the response
                evaluation.evaluation_response = response.content
                evaluation.status = EvaluationStatus.FAILED
                evaluation.overall_score = 0.5  # Default score
                evaluation.metadata_ = {
                    "error": "JSON parsing failed",
                    "raw_response": response.content
                }

            await session.commit()

        except Exception as e:
            try:
                evaluation.status = EvaluationStatus.FAILED
                evaluation.evaluation_response = f"Evaluation failed: {str(e)}"
                evaluation.overall_score = 0.0
                await session.commit()
            except:
                pass  # Avoid nested exceptions
            logger.error("Evaluation failed", test_result_id=test_result_id, error=str(e))