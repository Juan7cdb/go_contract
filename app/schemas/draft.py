from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime

class ContractDraftBase(BaseModel):
    template_id: int
    current_step: int = 1
    form_data: Dict[str, Any] = Field(default_factory=dict)

class ContractDraftCreate(ContractDraftBase):
    pass

class ContractDraftUpdate(BaseModel):
    current_step: Optional[int] = None
    form_data: Optional[Dict[str, Any]] = None

class ContractDraftResponse(ContractDraftBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
