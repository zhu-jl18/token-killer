"""Thinking thread logic."""
import asyncio
from typing import List, Optional
import aiohttp
from app.config import app_config, settings
from app.models.internal import ThinkingStep, ThreadResult
from app.core.client import ModelClient
from app.core.context import ContextManager
from app.core.validation import Validator
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ThinkingThread:
    """A single thinking thread."""
    
    def __init__(
        self,
        thread_id: int,
        client: ModelClient,
        context_manager: ContextManager,
        validator: Validator,
    ):
        """Initialize thinking thread."""
        self.thread_id = thread_id
        self.client = client
        self.context_manager = context_manager
        self.validator = validator
        self.config = app_config.thinking
    
    async def think(self, user_message: str) -> ThreadResult:
        """Run thinking process for this thread."""
        
        logger.info("thread_start", thread_id=self.thread_id)
        
        all_steps: List[ThinkingStep] = []
        step_num = 0
        is_complete = False
        
        # Background validation tasks
        validation_tasks = {}
        
        while not is_complete and step_num < self.config.max_steps:
            step_num += 1
            
            logger.info(
                "thinking_step_start",
                thread_id=self.thread_id,
                step=step_num
            )
            
            # Build context
            context = await self.context_manager.build_context(
                all_steps,
                step_num,
                user_message
            )
            
            # Think one step
            step_result = await self._think_step(
                step_num,
                context,
                user_message
            )
            
            if not step_result:
                logger.error(
                    "thinking_step_failed",
                    thread_id=self.thread_id,
                    step=step_num
                )
                continue
            
            # Add step to history
            all_steps.append(step_result)
            
            # Start background validation
            validation_task = asyncio.create_task(
                self.validator.validate_step(
                    step_result.content,
                    user_message,
                    step_num
                )
            )
            validation_tasks[step_num] = validation_task
            
            # Check if complete
            is_complete = step_result.is_complete
            
            logger.info(
                "thinking_step_complete",
                thread_id=self.thread_id,
                step=step_num,
                is_complete=is_complete
            )
        
        # Wait for all validations to complete
        if validation_tasks:
            validation_results = await asyncio.gather(
                *validation_tasks.values(),
                return_exceptions=True
            )
            
            # Update validation status
            for step_idx, result in enumerate(validation_results):
                if not isinstance(result, Exception) and step_idx < len(all_steps):
                    all_steps[step_idx].validation_passed = result.passed if hasattr(result, 'passed') else None
        
        # Combine all steps for final content
        final_content = "\n\n".join([
            f"【第{step.step_num}步】\n{step.content}"
            for step in all_steps
        ])
        
        logger.info(
            "thread_complete",
            thread_id=self.thread_id,
            total_steps=len(all_steps)
        )
        
        return ThreadResult(
            thread_id=self.thread_id,
            steps=all_steps,
            total_steps=len(all_steps),
            final_content=final_content
        )
    
    async def _think_step(
        self,
        step_num: int,
        context: str,
        user_message: str,
    ) -> Optional[ThinkingStep]:
        """Think one step."""
        
        # Load prompts
        from app.config import prompts
        thinking_prompts = prompts.get("thinking", {})
        
        # Build user content
        context_text = f"\n\n【之前的思考摘要】：\n{context}" if context else ""
        
        messages = [
            {"role": "system", "content": thinking_prompts.get("system", "")},
            {"role": "user", "content": thinking_prompts.get("user_template", "").format(
                question=user_message,
                context=context_text,
                step_num=step_num
            )}
        ]
        
        # Call main thinker model
        main_thinker = app_config.models["main_thinker"]
        result = await self.client.call_model(
            main_thinker,
            messages,
            settings.main_model_api_key,
            call_id=f"thread_{self.thread_id}_step_{step_num}",
            use_cache=self.config.enable_cache
        )
        
        if not result.get("success"):
            return None
        
        content = result["content"]
        
        # Check for completion markers
        is_complete = "【完成】" in content
        
        # Clean content
        clean_content = content.replace("【继续】", "").replace("【完成】", "").strip()
        
        return ThinkingStep(
            step_num=step_num,
            content=clean_content,
            is_complete=is_complete,
            char_count=len(clean_content)
        )


class ThinkingOrchestrator:
    """Orchestrate multiple thinking threads."""
    
    def __init__(self, http_session: aiohttp.ClientSession):
        """Initialize with HTTP session."""
        self.client = ModelClient(http_session)
        self.context_manager = ContextManager(self.client)
        self.validator = Validator(self.client)
        self.config = app_config.thinking
    
    async def think_parallel(self, user_message: str) -> List[ThreadResult]:
        """Run multiple thinking threads in parallel."""
        
        logger.info(
            "orchestrator_start",
            num_threads=self.config.num_threads,
            message=user_message[:100]
        )
        
        # Create thinking threads
        threads = []
        for i in range(1, self.config.num_threads + 1):
            thread = ThinkingThread(
                thread_id=i,
                client=self.client,
                context_manager=self.context_manager,
                validator=self.validator
            )
            threads.append(thread)
        
        # Run threads in parallel
        tasks = [thread.think(user_message) for thread in threads]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "thread_exception",
                    thread_id=i+1,
                    error=str(result)
                )
            else:
                valid_results.append(result)
        
        logger.info(
            "orchestrator_complete",
            successful_threads=len(valid_results),
            total_api_calls=self.client.total_calls
        )
        
        return valid_results