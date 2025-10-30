"""Fusion logic for combining multiple thread outputs."""
from typing import List
from app.config import app_config, settings
from app.models.internal import ThreadResult
from app.core.client import ModelClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


class Fusion:
    """Fuse outputs from multiple thinking threads."""
    
    def __init__(self, client: ModelClient):
        """Initialize with model client."""
        self.client = client
        self.config = app_config.fusion
    
    async def fuse_threads(
        self,
        thread_results: List[ThreadResult],
        user_message: str,
    ) -> str:
        """Fuse multiple thread results into final answer."""
        
        if not self.config.enabled:
            # Simple concatenation
            return self._simple_concat(thread_results)
        
        if self.config.strategy == "intelligent":
            return await self._intelligent_fusion(thread_results, user_message)
        else:
            return self._simple_concat(thread_results)
    
    def _simple_concat(self, thread_results: List[ThreadResult]) -> str:
        """Simple concatenation of thread results."""
        parts = []
        for result in thread_results:
            parts.append(f"\n{'='*60}")
            parts.append(f"【思考线程 {result.thread_id}】")
            parts.append(f"{'='*60}\n")
            parts.append(result.final_content)
        
        return "\n".join(parts)
    
    async def _intelligent_fusion(
        self,
        thread_results: List[ThreadResult],
        user_message: str,
    ) -> str:
        """Intelligent fusion using fusion model."""
        
        logger.info("fusion_start", num_threads=len(thread_results))
        
        # Prepare thread contents
        thread_contents = {}
        for i, result in enumerate(thread_results[:3]):  # Max 3 threads
            # Combine all steps from this thread
            thread_content = "\n\n".join([
                f"步骤{step.step_num}: {step.content}"
                for step in result.steps
            ])
            thread_contents[f"thread{i+1}_content"] = thread_content
            logger.info(
                "fusion_thread_prepared",
                thread_id=result.thread_id,
                steps=len(result.steps),
                content_length=len(thread_content)
            )
        
        # Ensure we have 3 thread contents (pad with empty if needed)
        for i in range(1, 4):
            key = f"thread{i}_content"
            if key not in thread_contents:
                thread_contents[key] = "（该线程未产生输出）"
        
        # Load fusion prompt
        from app.config import prompts
        fusion_prompts = prompts.get("fusion", {})
        
        messages = [
            {"role": "system", "content": fusion_prompts.get("system", "")},
            {"role": "user", "content": fusion_prompts.get("user_template", "").format(
                question=user_message,
                **thread_contents
            )}
        ]
        
        # Call fusion model
        fusion_model = app_config.models["fusion"]
        result = await self.client.call_model(
            fusion_model,
            messages,
            settings.fusion_model_api_key,
            call_id="fusion_final",
        )
        
        if result.get("success"):
            fused_content = result["content"].strip()
            logger.info("fusion_complete", output_length=len(fused_content))
            return fused_content
        else:
            logger.error("fusion_failed", error=result.get("error"))
            # Fallback to simple concatenation
            return self._simple_concat(thread_results)