"""Context management for thinking threads."""
from typing import List, Optional
from app.config import app_config
from app.models.internal import ThinkingStep
from app.core.client import ModelClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ContextManager:
    """Manage context for thinking process with smart summarization."""
    
    def __init__(self, client: ModelClient):
        """Initialize with a model client for summarization."""
        self.client = client
        self.config = app_config.context
    
    async def build_context(
        self,
        all_steps: List[ThinkingStep],
        current_step_num: int,
        user_message: str,
    ) -> str:
        """Build context for current step using smart strategy."""
        
        if current_step_num == 1:
            logger.info("context_build", step=1, strategy="empty")
            return ""
        
        if current_step_num == 2:
            logger.info("context_build", step=2, strategy="full_first")
            if all_steps:
                return f"【第1轮思考】\n{all_steps[0].content}"
            return ""
        
        if current_step_num == 3:
            logger.info("context_build", step=3, strategy="full_first_two")
            context_parts = []
            if len(all_steps) >= 1:
                context_parts.append(f"【第1轮思考】\n{all_steps[0].content}")
            if len(all_steps) >= 2:
                context_parts.append(f"【第2轮思考】\n{all_steps[1].content}")
            return "\n\n".join(context_parts)
        
        # Step 4+: Smart context with summarization
        if self.config.strategy == "smart":
            return await self._build_smart_context(
                all_steps, current_step_num, user_message
            )
        elif self.config.strategy == "full":
            return self._build_full_context(all_steps, current_step_num)
        else:  # minimal
            return self._build_minimal_context(all_steps, current_step_num)
    
    async def _build_smart_context(
        self,
        all_steps: List[ThinkingStep],
        current_step_num: int,
        user_message: str,
    ) -> str:
        """Build smart context with summarization."""
        context_parts = []
        
        # 1. Preserve first step
        if self.config.preserve_first_step and len(all_steps) >= 1:
            context_parts.append(f"【第1轮思考】\n{all_steps[0].content}")
            logger.info("context_preserve_first", length=len(all_steps[0].content))
        
        # 2. Summarize middle steps if needed
        if current_step_num > 4 and self.config.enable_summary:
            middle_start = 1
            middle_end = max(1, current_step_num - 1 - self.config.preserve_recent_steps)
            
            if middle_end > middle_start:
                summary = await self._generate_summary(
                    all_steps[middle_start:middle_end],
                    user_message
                )
                if summary:
                    context_parts.append(f"【中间轮次摘要】\n{summary}")
                    logger.info(
                        "context_summary",
                        start=middle_start+1,
                        end=middle_end,
                        summary_length=len(summary)
                    )
        
        # 3. Preserve recent steps
        recent_start = max(0, current_step_num - 1 - self.config.preserve_recent_steps)
        for i in range(recent_start, min(current_step_num - 1, len(all_steps))):
            if i < len(all_steps):
                context_parts.append(f"【第{i+1}轮思考】\n{all_steps[i].content}")
                logger.info("context_preserve_recent", step=i+1, length=len(all_steps[i].content))
        
        final_context = "\n\n".join(context_parts)
        logger.info("context_built", total_length=len(final_context))
        return final_context
    
    def _build_full_context(
        self,
        all_steps: List[ThinkingStep],
        current_step_num: int,
    ) -> str:
        """Build full context without summarization."""
        context_parts = []
        for i in range(min(current_step_num - 1, len(all_steps))):
            context_parts.append(f"【第{i+1}轮思考】\n{all_steps[i].content}")
        return "\n\n".join(context_parts)
    
    def _build_minimal_context(
        self,
        all_steps: List[ThinkingStep],
        current_step_num: int,
    ) -> str:
        """Build minimal context with only recent steps."""
        if not all_steps:
            return ""
        # Only return the last step
        return f"【上一轮思考】\n{all_steps[-1].content}"
    
    async def _generate_summary(
        self,
        steps: List[ThinkingStep],
        user_message: str,
    ) -> Optional[str]:
        """Generate summary for middle steps."""
        if not steps:
            return None
        
        # Combine middle content
        middle_content = []
        total_chars = 0
        for i, step in enumerate(steps):
            middle_content.append(f"第{step.step_num}轮：{step.content}")
            total_chars += len(step.content)
        
        combined = "\n\n".join(middle_content)
        
        # Load prompts
        from app.config import prompts
        summary_prompts = prompts.get("summary", {})
        
        messages = [
            {"role": "system", "content": summary_prompts.get("system", "")},
            {"role": "user", "content": summary_prompts.get("user_template", "").format(
                question=user_message,
                content=combined
            )}
        ]
        
        # Call summarizer model
        from app.config import app_config, settings
        summarizer = app_config.models["summarizer"]
        
        result = await self.client.call_model(
            summarizer,
            messages,
            settings.summary_model_api_key,
            call_id=f"summary_{steps[0].step_num}_{steps[-1].step_num}",
        )
        
        if result.get("success"):
            summary = result["content"].strip()
            compression = (1 - len(summary) / total_chars) * 100 if total_chars > 0 else 0
            logger.info(
                "summary_generated",
                original_chars=total_chars,
                summary_chars=len(summary),
                compression_rate=compression
            )
            return summary
        else:
            logger.error("summary_failed", error=result.get("error"))
            return f"【中间轮次摘要】第{steps[0].step_num}-{steps[-1].step_num}轮的关键内容"