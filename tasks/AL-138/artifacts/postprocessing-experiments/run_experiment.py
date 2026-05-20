#!/usr/bin/env python3
"""
Tool for running post-processing experiments with LLM models.
Supports caching, latency measurement, and cost tracking.
"""

import asyncio
import hashlib
import json
import os
import re

# Add parent directory to path to import from src
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from openai import Client

# Load environment variables from src/.env
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent.parent.parent
env_file = project_root / "src" / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    # Fallback to root .env if src/.env doesn't exist
    root_env = project_root / ".env"
    if root_env.exists():
        load_dotenv(root_env)

# Add src directory to path
# File is at: tasks/AL-138/artifacts/postprocessing-experiments/run_experiment.py
# Need to go up 4 levels to reach project root
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent.parent.parent  # Go up 5 levels
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from translator.llm_client_uri import UriLLMClient


class ExperimentRunner:
    def __init__(self, base_dir: Path, experiment_base_dir: Path):
        self.base_dir = base_dir  # Корень postprocessing-experiments/
        self.experiment_base_dir = experiment_base_dir  # Папка класса экспериментов (например, context_detection/)
        self.cache_dir = experiment_base_dir / "results" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize OpenRouter client for cost tracking
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            self.openrouter_client = Client(
                api_key=api_key, base_url="https://openrouter.ai/api/v1", timeout=60.0
            )
        else:
            self.openrouter_client = None
            print(
                "Warning: OPENROUTER_API_KEY not found, cost tracking will be limited"
            )

    def _get_cache_key(
        self, prompt_content: str, input_content: str, model_url: str
    ) -> str:
        """Generate cache key from prompt + input + model"""
        content = f"{prompt_content}\n\n{input_content}\n\n{model_url}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path using tree structure: a/b/c/abc2doiwpnfdp23n.json"""
        # Use first 3 characters as directory structure
        if len(cache_key) < 3:
            # Fallback for short keys
            subdir = cache_key
        else:
            subdir = cache_key[:3]
            # Create path: first char / second char / third char
            cache_path = self.cache_dir / subdir[0] / subdir[1] / subdir[2]
            cache_path.mkdir(parents=True, exist_ok=True)
            return cache_path / f"{cache_key}.json"

        # Fallback for very short keys
        return self.cache_dir / f"{cache_key}.json"

    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load result from cache if exists"""
        cache_file = self._get_cache_path(cache_key)
        if cache_file.exists():
            with open(cache_file, "r") as f:
                return json.load(f)
        return None

    def _save_to_cache(self, cache_key: str, result: Dict[str, Any]):
        """Save result to cache"""
        cache_file = self._get_cache_path(cache_key)
        with open(cache_file, "w") as f:
            json.dump(result, f, indent=2)

    def _extract_cost_from_response(self, response: Any, model_url: str) -> float:
        """Extract cost from OpenRouter response or estimate"""
        cost = 0.0

        # Try to get cost from OpenRouter response
        if hasattr(response, "usage") and response.usage:
            if (
                hasattr(response.usage, "estimated_cost")
                and response.usage.estimated_cost
            ):
                cost = response.usage.estimated_cost
            elif hasattr(response.usage, "prompt_tokens") and hasattr(
                response.usage, "completion_tokens"
            ):
                # Estimate cost if we have token counts (rough estimate)
                # This is a fallback - actual cost should come from API
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                # Very rough estimate: $0.0001 per 1K tokens
                cost = (prompt_tokens + completion_tokens) * 0.0000001

        return cost

    async def _run_llm_request(
        self,
        model_url: str,
        prompt: str,
        input_text: str,
        parse_field: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run LLM request and measure latency/cost"""
        cache_key = self._get_cache_key(prompt, input_text, model_url)

        # Check cache first
        cached = self._load_from_cache(cache_key)
        if cached:
            print(f"  [CACHED] {model_url.split('/')[-1]}")
            # Mark as cache hit
            cached["_cache_hit"] = True
            return cached

        # Prepare messages - substitute {dialogue_text} or {message_text} in prompt
        full_prompt = prompt.replace("{dialogue_text}", input_text).replace(
            "{message_text}", input_text
        )

        # Substitute additional parameters if provided (e.g., {scene_type}, {param1}, etc.)
        if params:
            for key, value in params.items():
                full_prompt = full_prompt.replace(f"{{{key}}}", str(value))

        # Split prompt into system and user parts if it has ## sections
        if "## " in full_prompt:
            parts = full_prompt.split("## ", 1)
            system_content = parts[0].strip()
            user_content = parts[1] if len(parts) > 1 else input_text
        else:
            system_content = None
            user_content = full_prompt

        # Build messages
        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": user_content})

        start_time = time.time()
        error = None
        response_text = ""
        cost = 0.0

        try:
            # Use UriLLMClient for flexible model configuration
            # Wrap in asyncio.to_thread since chat() is synchronous
            client = UriLLMClient(model_url)
            response_text = await asyncio.to_thread(client.chat, messages)
            latency = time.time() - start_time

            # Try to get cost from OpenRouter if available
            # For accurate cost, make a direct call to OpenRouter
            if "openrouter" in model_url.lower() and self.openrouter_client:
                try:
                    # Extract model name from URL
                    model_name = model_url.replace("openrouter://", "").split("?")[0]
                    # Make a direct call to get cost info (same request)
                    response = await asyncio.to_thread(
                        self.openrouter_client.chat.completions.create,
                        model=model_name,
                        messages=messages,
                    )
                    cost = self._extract_cost_from_response(response, model_url)
                except Exception as e:
                    # Fallback: estimate from response length (very rough)
                    cost = len(response_text) * 0.0000001

        except Exception as e:
            latency = time.time() - start_time
            error = str(e)
            print(f"  [ERROR] {model_url.split('/')[-1]}: {error}")

        # Parse XML response if parse_field is specified
        # Also try to parse <result> tag if parse_field is not specified (for transformation prompts)
        parsed_value = None
        if response_text and not error:
            if parse_field:
                # Try to extract <field_name>value</field_name> from response
                pattern = rf"<{re.escape(parse_field)}>(.*?)</{re.escape(parse_field)}>"
                match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
                if match:
                    parsed_value = match.group(1).strip()
            else:
                # Try to extract <result> tag (for transformation prompts with chain-of-thought)
                pattern = r"<result>(.*?)</result>"
                match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
                if match:
                    parsed_value = match.group(1).strip()

        result = {
            "model": model_url,
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "input": input_text,  # Full input text for tooltip display
            "input_preview": input_text[:200] + "..."
            if len(input_text) > 200
            else input_text,  # Short preview
            "response": response_text,
            "parsed_value": parsed_value,  # Extracted value from XML field
            "parse_field": parse_field,  # Field name used for parsing
            "latency": latency,
            "cost": cost,
            "error": error,
            "timestamp": time.time(),
            "_cache_hit": False,  # Mark as cache miss (new request)
        }

        # Save to cache
        if not error:
            self._save_to_cache(cache_key, result)

        return result

    async def run_experiment(self, experiment_file: Path, limit: Optional[int] = None):
        """Run experiment from YAML file"""
        print(f"\n{'=' * 80}")
        print(f"Running experiment: {experiment_file.name}")
        if limit:
            print(f"LIMITED MODE: Processing first {limit} test items only")
        print(f"{'=' * 80}\n")

        # Load experiment config
        with open(experiment_file, "r") as f:
            config = yaml.safe_load(f)

        name = config.get("name", "Unnamed Experiment")
        parse_field = config.get("parse_field")  # XML field to parse from responses
        models = config.get("models", [])
        prompts = config.get("prompts", [])
        dialogs = config.get("dialogs", [])
        messages = config.get("messages", [])
        # Get additional parameters for prompt substitution (e.g., params: {scene_type: "explicit"})
        params = config.get("params", {})

        # Apply limit if specified
        if limit:
            dialogs = dialogs[:limit]
            messages = messages[:limit]

        print(f"Experiment: {name}")
        print(f"Models: {len(models)}")
        print(f"Prompts: {len(prompts)}")
        print(f"Dialogs: {len(dialogs)}")
        print(f"Messages: {len(messages)}\n")

        # Load prompts (paths are relative to experiment_base_dir)
        prompt_contents = {}
        for prompt_path in prompts:
            prompt_file = self.experiment_base_dir / prompt_path
            if prompt_file.exists():
                with open(prompt_file, "r") as f:
                    prompt_contents[prompt_path] = f.read()
            else:
                print(f"Warning: Prompt file not found: {prompt_file}")

        # Load test data (paths are relative to experiment_base_dir)
        test_dialogs = []
        for dialog_path in dialogs:
            dialog_file = self.experiment_base_dir / dialog_path
            if dialog_file.exists():
                with open(dialog_file, "r") as f:
                    test_dialogs.append(
                        {
                            "path": dialog_path,
                            "content": f.read(),
                            "params": params,  # Add params for prompt substitution
                        }
                    )
            else:
                print(f"Warning: Dialog file not found: {dialog_file}")

        test_messages = []
        for message_path in messages:
            message_file = self.experiment_base_dir / message_path
            if message_file.exists():
                with open(message_file, "r") as f:
                    test_messages.append(
                        {
                            "path": message_path,
                            "content": f.read(),
                            "params": params,  # Add params for prompt substitution
                        }
                    )
            else:
                print(f"Warning: Message file not found: {message_file}")

        # Run experiments in parallel (max 5 concurrent requests)
        semaphore = asyncio.Semaphore(5)
        counter_lock = asyncio.Lock()
        all_results = []
        total_tests = (
            len(models) * len(prompts) * (len(test_dialogs) + len(test_messages))
        )
        if limit:
            total_tests = min(total_tests, limit)
        current_test = 0
        cache_hits = 0
        cache_misses = 0

        async def run_single_test(
            model: str,
            prompt_path: str,
            prompt_content: str,
            input_data: Dict[str, str],
            input_type: str,
        ):
            """Run a single test with semaphore limiting"""
            async with semaphore:
                nonlocal current_test, cache_hits, cache_misses
                async with counter_lock:
                    current_test += 1
                    test_num = current_test

                model_short = model.split("/")[-1]
                input_short = input_data["path"].split("/")[-1]
                start_time_str = time.strftime("%H:%M:%S", time.localtime())

                print(
                    f"[{test_num}/{total_tests}] [{start_time_str}] START: {model_short} × {input_short}"
                )

                result = await self._run_llm_request(
                    model,
                    prompt_content,
                    input_data["content"],
                    parse_field=parse_field,
                    params=input_data.get("params", {}),  # Pass params for substitution
                )
                result["prompt_path"] = prompt_path
                result["input_path"] = input_data["path"]
                result["input_type"] = input_type

                end_time_str = time.strftime("%H:%M:%S", time.localtime())
                latency = result.get("latency", 0)
                status = "CACHED" if result.get("_cache_hit") else "DONE"

                print(
                    f"[{test_num}/{total_tests}] [{end_time_str}] {status}: {model_short} × {input_short} ({latency:.2f}s)"
                )

                async with counter_lock:
                    if result.get("_cache_hit"):
                        cache_hits += 1
                    else:
                        cache_misses += 1

                return result

        # Collect all tasks
        tasks = []
        test_count = 0

        for model in models:
            for prompt_path, prompt_content in prompt_contents.items():
                # Test on dialogs
                for dialog in test_dialogs:
                    if limit and test_count >= limit:
                        break
                    tasks.append(
                        run_single_test(
                            model,
                            prompt_path,
                            prompt_content,
                            dialog,
                            "dialog",
                        )
                    )
                    test_count += 1
                    if limit and test_count >= limit:
                        break

                if limit and test_count >= limit:
                    break

                # Test on messages
                for message in test_messages:
                    if limit and test_count >= limit:
                        break
                    tasks.append(
                        run_single_test(
                            model,
                            prompt_path,
                            prompt_content,
                            message,
                            "message",
                        )
                    )
                    test_count += 1
                    if limit and test_count >= limit:
                        break

                if limit and test_count >= limit:
                    break
            if limit and test_count >= limit:
                break

        # Run all tasks in parallel
        print(f"\nRunning {len(tasks)} tests in parallel (max 5 concurrent)...\n")
        all_results = await asyncio.gather(*tasks)

        # Save results (in experiment_base_dir/results/)
        results_file = (
            self.experiment_base_dir
            / "results"
            / f"{experiment_file.stem}_results.json"
        )
        results_file.parent.mkdir(parents=True, exist_ok=True)

        output = {
            "experiment": name,
            "config": config,
            "results": all_results,
            "summary": self._calculate_summary(all_results),
        }

        with open(results_file, "w") as f:
            json.dump(output, f, indent=2)

        print(f"\n{'=' * 80}")
        print("EXPERIMENT COMPLETE")
        print(f"{'=' * 80}\n")
        print(f"Results saved to: {results_file}")
        print(f"\nSummary:")
        print(f"  Total tests: {len(all_results)}")
        print(f"  Successful: {len([r for r in all_results if not r.get('error')])}")
        print(f"  Errors: {len([r for r in all_results if r.get('error')])}")
        # Count cached entries (recursively in tree structure)
        cache_count = len(list(self.cache_dir.rglob("*.json")))

        print(f"\nCache statistics:")
        print(f"  Cache hits: {cache_hits} (from {cache_count} cached entries)")
        print(f"  Cache misses: {cache_misses} (new requests to LLM)")
        print(f"  Cache directory: {self.cache_dir}")
        print(f"\nPerformance:")
        print(
            f"  Avg latency: {self._calculate_summary(all_results)['avg_latency']:.2f}s"
        )
        print(
            f"  Total cost: ${self._calculate_summary(all_results)['total_cost']:.6f}"
        )

        return results_file

    def _calculate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics"""
        valid_results = [r for r in results if not r.get("error")]

        if not valid_results:
            return {
                "avg_latency": 0.0,
                "total_cost": 0.0,
                "total_tests": len(results),
                "successful_tests": 0,
                "error_tests": len(results),
            }

        avg_latency = sum(r["latency"] for r in valid_results) / len(valid_results)
        total_cost = sum(r.get("cost", 0.0) for r in valid_results)

        return {
            "avg_latency": avg_latency,
            "total_cost": total_cost,
            "total_tests": len(results),
            "successful_tests": len(valid_results),
            "error_tests": len([r for r in results if r.get("error")]),
        }


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run post-processing experiments")
    parser.add_argument(
        "experiment",
        type=str,
        help="Path to experiment YAML file (relative to postprocessing-experiments/)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of test items (dialogs/messages) to process (useful for quick testing)",
    )

    args = parser.parse_args()

    base_dir = Path(__file__).parent

    # Determine experiment file path
    experiment_file = base_dir / args.experiment
    if not experiment_file.exists():
        # Try old format: experiments/experiment_name.yaml
        experiment_file = base_dir / "experiments" / args.experiment
        if not experiment_file.exists():
            print(f"Error: Experiment file not found: {experiment_file}")
            return

    # Determine experiment base directory (class folder)
    # If path is like "context_detection/experiments/exp.yaml",
    # then experiment_base_dir is "context_detection/"
    experiment_path = Path(args.experiment)
    if len(experiment_path.parts) > 1:
        # Path contains subdirectory, use first part as experiment class
        experiment_base_dir = base_dir / experiment_path.parts[0]
    else:
        # Old format: just filename, use base_dir
        experiment_base_dir = base_dir

    runner = ExperimentRunner(base_dir, experiment_base_dir)
    await runner.run_experiment(experiment_file, limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
