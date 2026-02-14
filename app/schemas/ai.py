from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    role: str # 'user' or 'model'
    parts: List[str]

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []

class ChatResponse(BaseModel):
    response: str

class ContractRequest(BaseModel):
    contract_type: str
    user_inputs: Dict[str, Any] # Dynamic inputs based on conversation
    additional_instructions: Optional[str] = None

class ContractResponse(BaseModel):
    contract_text: str
    format: str = "markdown"
