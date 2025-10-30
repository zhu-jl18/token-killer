"""HTTP client for model API calls."""
import aiohttp
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import ModelConfig, settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ModelClient:
    """Async HTTP client for calling model APIs."""
    
    def __init__(self, session: aiohttp.ClientSession):
        """Initialize client with a shared session."""
        self.session = session
        self._call_count = 0
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def call_model(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, Any]],
        api_key: str,
        call_id: str = "",
        use_cache: bool = False,
    ) -> Dict[str, Any]:
        """Call a model API with retry logic."""
        self._call_count += 1
        
        # Add cache control if enabled
        if use_cache and messages:
            for msg in messages:
                if msg.get("role") == "system":
                    msg["cache_control"] = {"type": "ephemeral"}
                if msg.get("role") == "user":
                    msg["cache_control"] = {"type": "ephemeral"}
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": model_config.model,
            "messages": messages,
            "temperature": model_config.temperature,
            "max_tokens": model_config.max_tokens
        }
        
        try:
            logger.info(
                "calling_model",
                call_id=call_id,
                model=model_config.name,
                use_cache=use_cache,
            )
            
            async with self.session.post(
                model_config.api_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=settings.http_timeout)
            ) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    import json
                    data = json.loads(response_text)
                    content = data["choices"][0]["message"].get("content", "")
                    
                    # Log cache usage
                    usage = data.get("usage", {})
                    if use_cache and "cache_read_input_tokens" in usage:
                        cache_hit = usage.get("cache_read_input_tokens", 0)
                        if cache_hit > 0:
                            logger.info("cache_hit", call_id=call_id, tokens=cache_hit)
                    
                    logger.info(
                        "model_success",
                        call_id=call_id,
                        content_length=len(content),
                    )
                    
                    return {
                        "success": True,
                        "content": content,
                        "usage": usage,
                    }
                else:
                    logger.error(
                        "model_error",
                        call_id=call_id,
                        status=response.status,
                        response=response_text[:200],
                    )
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}: {response_text[:200]}"
                    }
        
        except Exception as e:
            logger.exception("model_exception", call_id=call_id, error=str(e))
            return {"success": False, "error": str(e)}
    
    @property
    def total_calls(self) -> int:
        """Get total number of API calls made."""
        return self._call_count
