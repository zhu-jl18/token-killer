"""Internal data structures for thinking process."""
from typing import List, Optional
from pydantic import BaseModel


class ThinkingStep(BaseModel):
    """A single thinking step."""
    step_num: int
    content: str
    is_complete: bool = False
    validation_passed: Optional[bool] = None
    char_count: int = 0


class ValidationResult(BaseModel):
    """Result of validation for a thinking step."""
    passed: bool
    counterexamples: List[str] = []
    vote_reasons: List[str] = []
    main_votes: int = 0
    counter_votes: int = 0


class ThreadResult(BaseModel):
    """Result from a single thinking thread."""
    thread_id: int
    steps: List[ThinkingStep]
    total_steps: int
    final_content: str


class ContextSnapshot(BaseModel):
    """A snapshot of context for a thinking step."""
    step_num: int
    full_context: str
    context_length: int
    has_summary: bool = False
