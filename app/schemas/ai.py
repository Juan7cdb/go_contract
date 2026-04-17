from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Attachment(BaseModel):
    mime_type: str
    base64_data: str

class ChatMessage(BaseModel):
    role: str # 'user' or 'assistant' (OpenAI convention)
    parts: List[Any] # Can be List[str] or List[Dict] (for multimodal)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    attachments: Optional[List[Attachment]] = []

class ChatResponse(BaseModel):
    response: str

class ContractRequest(BaseModel):
    contract_type: str
    user_inputs: Dict[str, Any] # Dynamic inputs based on conversation
    additional_instructions: Optional[str] = None

class ContractResponse(BaseModel):
    contract_text: str
    format: str = "markdown"
