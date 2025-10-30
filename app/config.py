"""Configuration management using Pydantic settings."""
from typing import Dict, Any, Literal
from pathlib import Path
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseModel):
    """Configuration for a single model."""
    name: str
    model: str
    api_url: str
    role: str
    temperature: float = 0.7
    max_tokens: int = 2000


class ThinkingConfig(BaseModel):
    """Configuration for thinking process."""
    num_threads: int = Field(default=3, ge=1, le=10)
    max_steps: int = Field(default=20, ge=1)
    step_max_length: int = Field(default=400, ge=100)
    enable_cache: bool = True


class ValidationConfig(BaseModel):
    """Configuration for validation mechanism."""
    enabled: bool = True
    num_counterexamples: int = Field(default=3, ge=1, le=5)
    num_validators: int = Field(default=3, ge=1, le=5)
    pass_threshold: int = Field(default=2, ge=1)
    timeout: int = Field(default=30, ge=10)


class ContextConfig(BaseModel):
    """Configuration for context management."""
    strategy: Literal["smart", "full", "minimal"] = "smart"
    enable_summary: bool = True
    preserve_first_step: bool = True
    preserve_recent_steps: int = Field(default=2, ge=0)
    summary_compression_target: float = Field(default=0.3, ge=0.1, le=0.9)


class FusionConfig(BaseModel):
    """Configuration for fusion strategy."""
    enabled: bool = True
    strategy: Literal["intelligent", "simple_concat"] = "intelligent"


class ServiceConfig(BaseModel):
    """Configuration for service metadata."""
    model_name: str = "triple-thread-thinking"
    description: str = "Multi-threaded thinking with validation"


class AppConfig(BaseModel):
    """Main application configuration from YAML."""
    models: Dict[str, ModelConfig]
    thinking: ThinkingConfig
    validation: ValidationConfig
    context: ContextConfig
    fusion: FusionConfig
    service: ServiceConfig


class Settings(BaseSettings):
    """Environment-based settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    log_level: str = "info"

    # HTTP Client
    http_timeout: int = 120
    http_max_connections: int = 100
    http_retry_attempts: int = 3

    # API Keys
    main_model_api_key: str = ""
    fusion_model_api_key: str = ""
    summary_model_api_key: str = ""
    validation_model_api_key: str = ""

    # Monitoring
    enable_metrics: bool = True
    enable_tracing: bool = False

    # Config file path
    config_file: str = "config.yaml"


def load_yaml_config(config_path: str = "config.yaml") -> AppConfig:
    """Load configuration from YAML file."""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    
    return AppConfig(**config_data)


def load_prompts(prompt_dir: str = "prompts") -> Dict[str, str]:
    """Load prompt templates from YAML files."""
    prompts = {}
    prompt_path = Path(prompt_dir)
    
    if not prompt_path.exists():
        return prompts
    
    for yaml_file in prompt_path.glob("*.yaml"):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            prompts[yaml_file.stem] = data
    
    return prompts


# Global configuration instances
settings = Settings()
app_config = load_yaml_config(settings.config_file)
prompts = load_prompts()
