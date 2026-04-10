from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from .ai import ChatMessage

class SmartPanelChatRequest(BaseModel):
    """Schema for lateral AI chat within the contract generation flow."""
    message: str
    history: List[ChatMessage] = []
    template_name: Optional[str] = "Generic Contract"
    form_data: Dict[str, Any] = {}
