"""
Schemas for Farm AI Copilot Chat service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatAction(BaseModel):
    """Suggested quick action or navigation for the farmer."""
    label: str
    action_type: str = Field(description="Action type: 'navigate', 'prompt', 'modal', 'tutorial', 'confirm_action'")
    payload: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    """Single conversational turn in chat history."""
    role: str = Field(description="'user' or 'assistant'")
    content: str


class ChatRequest(BaseModel):
    """Incoming user chat prompt."""
    message: str = Field(min_length=1, max_length=1000)
    crop_id: Optional[int] = None
    language: Optional[str] = Field(default="en", description="Language code: 'en', 'mr', 'hi'")
    current_path: Optional[str] = Field(default="/", description="Current screen/route in the frontend")
    workflow_state: Optional[Dict[str, Any]] = Field(default=None, description="Active conversational workflow state")
    history: Optional[List[ChatMessage]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Structured response from Farm AI Copilot."""
    reply: str
    intent: str
    crop_id: Optional[int] = None
    crop_name: Optional[str] = None
    farm_name: Optional[str] = None
    action_type: Optional[str] = None
    action_payload: Optional[Dict[str, Any]] = None
    tutorial_steps: Optional[List[Dict[str, Any]]] = None
    confirmation_needed: Optional[bool] = False
    confirmation_data: Optional[Dict[str, Any]] = None
    suggested_actions: List[ChatAction] = Field(default_factory=list)
    data_grounding: Dict[str, Any] = Field(default_factory=dict)
