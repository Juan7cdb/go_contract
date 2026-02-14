"""AI Service for contract generation and agent-based chat."""
import google.generativeai as genai
from app.core.config import settings
from app.schemas.ai import ChatMessage
from typing import AsyncGenerator, Optional
import logging

logger = logging.getLogger(__name__)

# Lazy initialization
_ai_service_instance = None


class AIService:
    def __init__(self):
        if not settings.GOOGLE_API_KEY or "change_me" in settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY is not set correctly. AI features will fail.")
        
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        
        # Generation config optimized for legal accuracy
        self.generation_config = genai.GenerationConfig(
            temperature=0.2,  # Low temperature for legal accuracy
            top_p=0.95,
            top_k=64,
            max_output_tokens=8192,
        )

        # Default system instructions
        self.legal_chat_instruction = """You are an expert legal assistant specializing in Colombian and International law. 
Your goal is to provide accurate, professional, and helpful legal information.
Always clarify that you provide information, not legal advice, and recommend consulting a licensed attorney for specific cases.
Be concise but thorough. Cite relevant laws or articles when applicable."""

        self.contract_instruction = """You are an expert legal drafter specializing in contract creation.
Create precise, legally binding contracts based on the provided details.
Output ONLY the contract text in proper Markdown format, ready to be converted to PDF.
Include standard clauses for: parties, definitions, obligations, payment terms (if applicable), 
confidentiality, termination, governing law, and dispute resolution.
Use formal legal language appropriate for Colombian jurisdiction unless specified otherwise."""

        self.model_chat = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=self.generation_config,
        )

        self.model_contract = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config=self.generation_config,
        )

    async def chat(self, message: str, history: list[ChatMessage]) -> str:
        """Standard chat with full response."""
        # Build conversation with system instruction as first message
        contents = [{"role": "user", "parts": [self.legal_chat_instruction + "\n\nUser question: " + message]}]
        
        if history:
            # Include history
            for msg in history:
                contents.append({"role": msg.role, "parts": msg.parts})
            contents.append({"role": "user", "parts": [message]})
        
        response = await self.model_chat.generate_content_async(contents)
        return response.text

    async def chat_stream(self, message: str, history: list[ChatMessage]) -> AsyncGenerator[str, None]:
        """Streaming chat for real-time responses."""
        full_prompt = f"{self.legal_chat_instruction}\n\nUser question: {message}"
        
        response = await self.model_chat.generate_content_async(full_prompt, stream=True)
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def chat_with_agent(
        self, 
        message: str, 
        agent_prompt: str, 
        history: Optional[list[dict]] = None
    ) -> str:
        """Chat with a specific AI agent using its custom prompt."""
        # Combine agent prompt with user message
        full_prompt = f"""{agent_prompt}

---
User message: {message}
"""
        
        if history:
            history_text = "\n".join([f"{h.get('role', 'user')}: {h.get('content', '')}" for h in history[-5:]])
            full_prompt = f"""{agent_prompt}

---
Recent conversation:
{history_text}

User message: {message}
"""
        
        response = await self.model_chat.generate_content_async(full_prompt)
        return response.text

    async def chat_with_agent_stream(
        self, 
        message: str, 
        agent_prompt: str, 
        history: Optional[list[dict]] = None
    ) -> AsyncGenerator[str, None]:
        """Streaming chat with a specific AI agent."""
        full_prompt = f"""{agent_prompt}

---
User message: {message}
"""
        
        if history:
            history_text = "\n".join([f"{h.get('role', 'user')}: {h.get('content', '')}" for h in history[-5:]])
            full_prompt = f"""{agent_prompt}

---
Recent conversation:
{history_text}

User message: {message}
"""
        
        response = await self.model_chat.generate_content_async(full_prompt, stream=True)
        
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def generate_contract(
        self, 
        contract_type: str, 
        inputs: dict, 
        rules: Optional[str] = None,
        agent_prompt: Optional[str] = None
    ) -> str:
        """Generate a complete contract document using template rules and optional agent prompt."""
        
        system_context = self.contract_instruction
        if agent_prompt:
            system_context = f"{self.contract_instruction}\n\nADDITIONAL AGENT INSTRUCTIONS:\n{agent_prompt}"
        
        prompt = f"""{system_context}

---

Generate a **{contract_type}**.

**Party and Contract Details**:
{self._format_inputs(inputs)}

**Template Rules**:
{rules if rules else "None - use standard clauses."}

Ensure the contract is complete and legally sound. Include all standard protective clauses.
"""
        
        response = await self.model_contract.generate_content_async(prompt)
        return response.text

    def _format_inputs(self, inputs: dict, indent: int = 0) -> str:
        """Format inputs dictionary into readable string for prompt."""
        lines = []
        prefix = "  " * indent
        for key, value in inputs.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}- **{key}**:")
                lines.append(self._format_inputs(value, indent + 1))
            else:
                lines.append(f"{prefix}- **{key}**: {value}")
        return "\n".join(lines)


def get_ai_service() -> AIService:
    """
    Lazy initialization of AI service.
    Prevents initialization errors at import time if API key is missing.
    """
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance


# Singleton for direct import
ai_service = get_ai_service()
