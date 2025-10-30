"""Validation mechanism with counterexample generation."""
import asyncio
from typing import List, Tuple
from app.config import app_config, settings
from app.models.internal import ValidationResult
from app.core.client import ModelClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


class Validator:
    """Validator with counterexample generation and voting."""
    
    def __init__(self, client: ModelClient):
        """Initialize with model client."""
        self.client = client
        self.config = app_config.validation
        self.enabled = self.config.enabled
    
    async def validate_step(
        self,
        step_content: str,
        user_message: str,
        step_num: int,
    ) -> ValidationResult:
        """Validate a thinking step with counterexamples and voting."""
        
        if not self.enabled:
            logger.info("validation_skipped", step=step_num)
            return ValidationResult(passed=True)
        
        logger.info("validation_start", step=step_num)
        
        # Phase 1: Generate counterexamples
        counterexamples = await self._generate_counterexamples(
            step_content, user_message, step_num
        )
        
        if not counterexamples:
            logger.warning("validation_no_counterexamples", step=step_num)
            return ValidationResult(passed=True)
        
        # Phase 2: Voting
        result = await self._vote_on_counterexamples(
            step_content, counterexamples, user_message, step_num
        )
        
        logger.info(
            "validation_complete",
            step=step_num,
            passed=result.passed,
            main_votes=result.main_votes,
            counter_votes=result.counter_votes
        )
        
        return result
    
    async def _generate_counterexamples(
        self,
        step_content: str,
        user_message: str,
        step_num: int,
    ) -> List[str]:
        """Generate counterexamples in parallel."""
        
        from app.config import prompts
        validation_prompts = prompts.get("validation", {})
        counterexample_prompts = validation_prompts.get("counterexample", {})
        
        messages = [
            {"role": "system", "content": counterexample_prompts.get("system", "")},
            {"role": "user", "content": counterexample_prompts.get("user_template", "").format(
                question=user_message,
                thinking_content=step_content
            )}
        ]
        
        # Generate counterexamples in parallel
        tasks = []
        for i in range(self.config.num_counterexamples):
            task = self.client.call_model(
                app_config.models["counterexample_generator"],
                messages,
                settings.validation_model_api_key,
                call_id=f"counterexample_{step_num}_{i+1}",
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        counterexamples = []
        for i, result in enumerate(results):
            if result.get("success"):
                content = result["content"].strip()
                counterexamples.append(content)
                logger.info(
                    "counterexample_generated",
                    step=step_num,
                    index=i+1,
                    length=len(content)
                )
            else:
                logger.error(
                    "counterexample_failed",
                    step=step_num,
                    index=i+1,
                    error=result.get("error")
                )
        
        return counterexamples
    
    async def _vote_on_counterexamples(
        self,
        step_content: str,
        counterexamples: List[str],
        user_message: str,
        step_num: int,
    ) -> ValidationResult:
        """Vote on main thread vs counterexamples."""
        
        from app.config import prompts
        validation_prompts = prompts.get("validation", {})
        voting_prompts = validation_prompts.get("voting", {})
        
        # Format counterexamples
        counterexamples_text = "\n\n".join([
            f"【反例{i+1}】\n{ce}" for i, ce in enumerate(counterexamples)
        ])
        
        messages = [
            {"role": "system", "content": voting_prompts.get("system", "")},
            {"role": "user", "content": voting_prompts.get("user_template", "").format(
                question=user_message,
                thinking_content=step_content,
                counterexamples=counterexamples_text
            )}
        ]
        
        # Vote in parallel
        tasks = []
        for i in range(self.config.num_validators):
            task = self.client.call_model(
                app_config.models["validator"],
                messages,
                settings.validation_model_api_key,
                call_id=f"vote_{step_num}_{i+1}",
            )
            tasks.append(task)
        
        voting_results = await asyncio.gather(*tasks)
        
        # Count votes
        main_votes = 0
        counter_votes = 0
        vote_reasons = []
        
        for i, result in enumerate(voting_results):
            if result.get("success"):
                content = result["content"]
                if "主线程" in content and "反例" not in content.split("投票：")[1].split("\n")[0]:
                    main_votes += 1
                    logger.info("vote_main", step=step_num, voter=i+1)
                else:
                    counter_votes += 1
                    logger.info("vote_counter", step=step_num, voter=i+1)
                    if "理由：" in content:
                        reason = content.split("理由：")[1].strip()
                        vote_reasons.append(f"投票器{i+1}: {reason}")
        
        passed = main_votes >= self.config.pass_threshold
        
        return ValidationResult(
            passed=passed,
            counterexamples=counterexamples,
            vote_reasons=vote_reasons,
            main_votes=main_votes,
            counter_votes=counter_votes
        )