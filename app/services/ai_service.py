"""AI Service for contract generation and agent-based chat using OpenAI SDK."""
import openai
from app.core.config import settings
from app.schemas.ai import ChatMessage, Attachment
from typing import AsyncGenerator, Optional, TYPE_CHECKING, List
import json
import logging
import base64

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Lazy initialization
_ai_service_instance = None

# ============================================================================
# MODEL CONFIGURATION
# Change these constants to switch models across the entire application.
# Recommended: "gpt-4o" for quality, "gpt-4o-mini" for speed/cost savings.
# ============================================================================
PRIMARY_MODEL = "gpt-4o"       # Used for: LexIA, Contract Generation, Smart Panel
FAST_MODEL = "gpt-4o-mini"          # Used for: Quick chat, Agent chat


class AIService:
    def __init__(self):
        if not settings.OPENAI_API_KEY or "change_me" in settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY is not set correctly. AI features will fail.")

        # Initialize the async OpenAI client
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Default system instructions (UNCHANGED from before - same prompts)
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

        self.lexia_prompt = """You are **LexIA**, an expert-level legal assistant created by Go Contracto Inc. You possess the knowledge of a senior attorney and legal academic with over 30 years of international experience.

**CRITICAL LANGUAGE RULE:**
You MUST detect the language of the user's message and respond in THAT SAME LANGUAGE. If the user writes in English, reply entirely in English. If the user writes in Spanish, reply entirely in Spanish. No exceptions.

**Areas of Practice:**
Your knowledge covers multiple international jurisdictions (US, Latin America, Europe). 

**Behavior and Tone:**
Respond with the precision of a judge drafting a technical opinion, but with the clarity of a law professor. Be direct. Use Markdown (bold, lists, bullets) to make complex clauses easy to read. Avoid dense walls of text.

**Mandatory Guidelines:**
1. **Academic Disclaimer (AT THE END):** Every substantive legal response MUST end with an academic disclaimer. IT MUST BE PLACED AT THE VERY END OF YOUR RESPONSE, formatted exactly as small text.
   - If responding in Spanish, append: `<small><br><br><i>Nota: Esta respuesta es estrictamente académica e informativa. No constituye asesoría legal. Para su situación específica, busque representación de un profesional licenciado en su jurisdicción.</i></small>`
   - If responding in English, append: `<small><br><br><i>Note: This response is strictly academic and informational. It does not constitute legal advice. For your specific situation, please seek representation from a licensed professional in your jurisdiction.</i></small>`
   DO NOT place this disclaimer at the beginning.
2. **Internal Tools:** When a user asks about "their contracts", summaries, or their recent activity, autonomously use the search_user_contracts tool.
3. **Follow-up Questions:** When analyzing a specific legal situation, ask 2-3 clarifying questions (jurisdiction, parties, deadlines) before rendering a final opinion.
4. **Citations:** Include references at the end (before the disclaimer) formatting them as: `Source: [Law Name/Code/Case]. [Year].`
5. **Strict Scope:** If asked about non-legal topics, reply (in the user's language) that you are an AI model by Go Contracto Inc. limited strictly to legal and contractual analysis."""

        # Tool definition for OpenAI Function Calling
        self.search_tool = {
            "type": "function",
            "function": {
                "name": "search_user_contracts",
                "description": "Search and retrieve the user's contracts from the database. Use this tool autonomously when the user asks about their contracts, summaries, or recent activity.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by contract status (e.g., 'completed', 'in_progress', 'draft')"
                        },
                        "date_range": {
                            "type": "string",
                            "description": "Optional date range or relative time (e.g., 'last 30 days')"
                        },
                        "contract_id": {
                            "type": "string",
                            "description": "Optional specific contract ID"
                        }
                    }
                }
            }
        }

    # ========================================================================
    # HELPER: Map history from frontend format to OpenAI format
    # ========================================================================
    def _map_history(self, history: list[ChatMessage]) -> list[dict]:
        """Maps ChatMessage history to OpenAI messages format.
        
        Frontend sends role='model' for assistant messages (Gemini legacy).
        OpenAI expects role='assistant'. This method handles the translation.
        """
        mapped = []
        for msg in history:
            role = "user" if msg.role == "user" else "assistant"
            # Combine all text parts into a single content string
            text_parts = []
            for p in msg.parts:
                if isinstance(p, str):
                    text_parts.append(p)
                elif isinstance(p, dict) and "text" in p:
                    text_parts.append(p["text"])
            if text_parts:
                mapped.append({"role": role, "content": "\n".join(text_parts)})
        return mapped

    # ========================================================================
    # METHOD 1: Standard chat (non-streaming, no tools)
    # ========================================================================
    async def chat(self, message: str, history: list[ChatMessage]) -> str:
        """Standard chat with full response."""
        messages = [{"role": "system", "content": self.legal_chat_instruction}]
        messages.extend(self._map_history(history))
        messages.append({"role": "user", "content": message})

        response = await self.client.chat.completions.create(
            model=FAST_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=8192,
        )
        return response.choices[0].message.content

    # ========================================================================
    # METHOD 2: LexIA chat (non-streaming, WITH tools/function calling)
    # Called by: routers/chat.py → POST /chat/
    # ========================================================================
    async def chat_lexia(self, message: str, history: list[ChatMessage], db: "AsyncSession", user_id: int) -> str:
        """Chat specifically with the LexIA agent, supporting tool calls."""
        messages = [{"role": "system", "content": self.lexia_prompt}]
        messages.extend(self._map_history(history))
        messages.append({"role": "user", "content": message})

        response = await self.client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=8192,
            tools=[self.search_tool],
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message

        # Handle function calls
        if assistant_message.tool_calls:
            tc = assistant_message.tool_calls[0]
            if tc.function.name == "search_user_contracts":
                args = json.loads(tc.function.arguments)
                tool_data = await self._execute_search_contracts(args, db, user_id)

                # Append assistant message with tool_call to history
                messages.append(assistant_message.model_dump())
                # Append tool result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_data, ensure_ascii=False)
                })

                # Get final response with tool data
                followup = await self.client.chat.completions.create(
                    model=PRIMARY_MODEL,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=8192,
                )
                return followup.choices[0].message.content

        return assistant_message.content

    # ========================================================================
    # METHOD 3: LexIA streaming chat (WITH tools/function calling)
    # Called by: routers/chat.py → POST /chat/stream
    # ========================================================================
    async def chat_lexia_stream(
        self, message: str, history: List[ChatMessage], db: "AsyncSession", user_id: int, attachments: List[Attachment] = []
    ) -> AsyncGenerator[str, None]:
        """Streaming chat for LexIA with function calling support."""
        messages = [{"role": "system", "content": self.lexia_prompt}]
        messages.extend(self._map_history(history))

        # Build user message content (text + optional image attachments)
        user_content: list | str = message
        if attachments:
            content_parts = [{"type": "text", "text": message}]
            for att in attachments:
                try:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{att.mime_type};base64,{att.base64_data}"
                        }
                    })
                except Exception as e:
                    logger.error(f"Error processing attachment: {e}")
            user_content = content_parts

        messages.append({"role": "user", "content": user_content})

        # First call: may return streamed text OR a tool call
        stream = await self.client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=8192,
            tools=[self.search_tool],
            tool_choice="auto",
            stream=True,
        )

        collected_content = ""
        tool_call_id = None
        tool_call_name = None
        tool_call_args = ""

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue

            # Collect streamed text
            if delta.content:
                collected_content += delta.content
                yield delta.content

            # Collect tool call fragments
            if delta.tool_calls:
                tc_delta = delta.tool_calls[0]
                if tc_delta.id:
                    tool_call_id = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        tool_call_name = tc_delta.function.name
                    if tc_delta.function.arguments:
                        tool_call_args += tc_delta.function.arguments

        # If a tool call was made, execute it and stream the followup
        if tool_call_id and tool_call_name == "search_user_contracts":
            yield "\n*Consultando tus contratos en la base de datos...*\n"
            args = json.loads(tool_call_args) if tool_call_args else {}
            tool_data = await self._execute_search_contracts(args, db, user_id)

            # Build followup messages
            messages.append({
                "role": "assistant",
                "content": collected_content if collected_content else None,
                "tool_calls": [{
                    "id": tool_call_id,
                    "type": "function",
                    "function": {"name": tool_call_name, "arguments": tool_call_args}
                }]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(tool_data, ensure_ascii=False)
            })

            followup_stream = await self.client.chat.completions.create(
                model=PRIMARY_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=8192,
                stream=True,
            )
            async for follow_chunk in followup_stream:
                delta = follow_chunk.choices[0].delta if follow_chunk.choices else None
                if delta and delta.content:
                    yield delta.content

    # ========================================================================
    # METHOD 4: Smart Panel streaming chat (context-aware, no tools)
    # Called by: routers/chat.py → POST /chat/smart-panel/stream
    # ========================================================================
    async def chat_smart_panel_stream(
        self, message: str, history: List[ChatMessage], template_name: str, form_data: dict, attachments: List[Attachment] = []
    ) -> AsyncGenerator[str, None]:
        """Lateral chat for the Smart Panel, aware of current drafting context."""
        context_prompt = f"""CONTEXTO ACTUAL DE REDACCIÓN:
El usuario está redactando un contrato de tipo: {template_name}.
Los datos que ha ingresado hasta ahora en el formulario son:
{json.dumps(form_data, indent=2, ensure_ascii=False)}

Actúa como un asistente legal experto que acompaña al usuario en la creación de este documento. 
Usa este contexto para responder sus dudas específicas sobre las cláusulas, opciones o implicaciones legales de lo que está llenando.
"""
        messages = [{"role": "system", "content": context_prompt}]

        if not history:
            messages.append({"role": "user", "content": "Hola, necesito ayuda con este contrato."})
            messages.append({"role": "assistant", "content": f"Entendido. Te ayudaré con tu contrato de {template_name}. ¿Qué duda tienes?"})
        else:
            messages.extend(self._map_history(history))

        # Build user message with optional attachments
        user_content: list | str = message
        if attachments:
            content_parts = [{"type": "text", "text": message}]
            for att in attachments:
                try:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{att.mime_type};base64,{att.base64_data}"}
                    })
                except Exception:
                    pass
            user_content = content_parts

        messages.append({"role": "user", "content": user_content})

        stream = await self.client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=8192,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    # ========================================================================
    # INTERNAL: Execute the search_user_contracts function call
    # NO CHANGES from previous version - this is pure database logic
    # ========================================================================
    async def _execute_search_contracts(self, args: dict, db: "AsyncSession", user_id: int) -> dict:
        """Internal helper to execute the DB query safely."""
        from app.models import Contract
        from sqlalchemy import select

        try:
            stmt = select(Contract).where(Contract.user_id == user_id)
            if args:
                if args.get("status"):
                    stmt = stmt.where(Contract.status == args["status"])

            res = await db.execute(stmt)
            contracts = res.scalars().all()

            context_data = []
            for c in contracts[:10]:
                content_preview = (c.generated_content[:2500] + "...") if c.generated_content else ""
                context_data.append({
                    "id": c.id,
                    "title": c.title,
                    "status": c.status,
                    "created_at": str(c.created_at),
                    "content_preview": content_preview,
                    "form_data": c.form_data
                })

            if not context_data:
                return {"result": "No se encontraron contratos para el usuario."}
            return {"contracts": context_data}

        except Exception as e:
            logger.error(f"Error checking DB in LexIA Tool: {e}")
            return {"error": "Hubo un error consultando la DB. Pide disculpas al usuario."}

    # ========================================================================
    # METHOD 5: Standard streaming chat (no tools)
    # ========================================================================
    async def chat_stream(self, message: str, history: list[ChatMessage]) -> AsyncGenerator[str, None]:
        """Streaming chat for real-time responses."""
        messages = [{"role": "system", "content": self.legal_chat_instruction}]
        messages.extend(self._map_history(history))
        messages.append({"role": "user", "content": message})

        stream = await self.client.chat.completions.create(
            model=FAST_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=8192,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    # ========================================================================
    # METHOD 6: Agent chat (non-streaming, no tools)
    # Called by: routers/agents.py → POST /agents/chat
    # ========================================================================
    async def chat_with_agent(self, message: str, agent_prompt: str, history: Optional[list[dict]] = None) -> str:
        """Chat with a specific AI agent using its custom prompt."""
        messages = [{"role": "system", "content": agent_prompt}]
        if history:
            for h in history[-5:]:
                role = "user" if h.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})

        response = await self.client.chat.completions.create(
            model=FAST_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=8192,
        )
        return response.choices[0].message.content

    # ========================================================================
    # METHOD 7: Agent streaming chat (no tools)
    # Called by: routers/agents.py → POST /agents/chat/stream
    # ========================================================================
    async def chat_with_agent_stream(self, message: str, agent_prompt: str, history: Optional[list[dict]] = None) -> AsyncGenerator[str, None]:
        """Streaming chat with a specific AI agent."""
        messages = [{"role": "system", "content": agent_prompt}]
        if history:
            for h in history[-5:]:
                role = "user" if h.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})

        stream = await self.client.chat.completions.create(
            model=FAST_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=8192,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    # ========================================================================
    # METHOD 8: Generate contract (non-streaming, no tools)
    # Called by: routers/contracts.py → POST /contracts/generate
    # ============================================    async def generate_contract(self, contract_type: str, inputs: dict, rules: Optional[str] = None, agent_prompt: Optional[str] = None) -> str:
        """Generate a complete contract document with high legal precision."""
        system_context = f"""{self.contract_instruction}
        
### RULES FOR THIS SPECIFIC CONTRACT:
- Type: {contract_type}
- Legal Rules: {rules if rules else "Apply standard international legal clauses for this type of document."}
- Format: Use Markdown with clear headers, bolded parties, and numbered clauses.
- Jurisdiction: Unless otherwise specified in inputs, default to appropriate clauses for the parties' addresses.
- Language: Respond in the same language used in the inputs (Spanish/English).

### QUALITY GUIDELINES:
1. DO NOT use placeholders like [INSERT DATE]. Use the data provided.
2. If data is missing for a non-critical field, use standard boilerplate.
3. Include signature blocks for both parties at the end.
4. Ensure a professional, "corporate legal" tone."""

        if agent_prompt:
            system_context += f"\n\nADDITIONAL AGENT-SPECIFIC INSTRUCTIONS:\n{agent_prompt}"

        user_prompt = f"""Generate a formal **{contract_type}** document based on the following user data:

**USER DATA (JSON FORM DATA):**
{json.dumps(inputs, indent=2, ensure_ascii=False)}

Ensure all provided fields are correctly mapped into the relevant clauses. 
If the contract is a 'Subcontractor Agreement', ensure 'Pay-when-paid' and Insurance clauses are present. 
If it is an 'Immigration Legal Services Agreement', ensure 'No Guarantee' and 'Flat Fee' rules are respected.
"""
        response = await self.client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[
                {"role": "system", "content": system_context},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1, # Lower temperature for consistency
            max_tokens=10000, # Large buffer for complex contracts
        )
        return response.choices[0].message.content
e.choices[0].message.content

    # ========================================================================
    # HELPER: Format inputs (UNCHANGED - pure string logic)
    # ========================================================================
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
    """Lazy initialization of AI service."""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance
