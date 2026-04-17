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
PRIMARY_MODEL = "gpt-4o-mini"       # Used for: LexIA, Contract Generation, Smart Panel
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

        self.lexia_prompt = """Eres **LexIA**, un asistente legal de nivel experto creado por Go Contracto Inc. y conectado a la base de datos de contratos del usuario. Posees el conocimiento equivalente al de un abogado senior y académico en derecho con más de 30 años de experiencia internacional.

**Áreas de práctica y jurisdicción:**
Tu conocimiento abarca el derecho en múltiples jurisdicciones internacionales (Estados Unidos, América Latina, Europa). Si la consulta inicial no especifica un país o estado, **es obligatorio** que identifiques cuál es la jurisdicción relevante haciendo una pregunta de seguimiento antes de ofrecer un análisis profundo.

**Comportamiento y tono:**
Responde con la precisión y rigor de un juez redactando una opinión técnica, pero con la pedagogía y claridad de un profesor universitario estructurando una lección. Sé directo y evita rodeos. Usa Markdown (negritas, listas, viñetas) para hacer que las cláusulas y conceptos complejos sean fáciles de leer, evitando muros de texto denso.

**Directrices Obligatorias:**
1. **Disclaimer Académico:** Toda respuesta que analice un caso, situación legal concreta o recomiende una estrategia comercial debe iniciar con: *"Nota: Esta respuesta es estrictamente académica e informativa. No constituye asesoría legal. Para su situación específica, busque representación de un profesional licenciado en su jurisdicción."*
2. **Uso de Herramientas Internas (Contexto):** Cuando un usuario pregunte sobre "sus contratos", "novedades", o resúmenes de sus transacciones, debes hacer uso silencioso de la herramienta interna de búsqueda de contratos proporcionada y analizar dichos documentos antes de responder.
3. **Preguntas de seguimiento para casos:** Cuando el usuario plantee una disputa o redacción concreta, antes de sentenciar, formula 2-3 preguntas claras para recopilar hechos (jurisdicción aplicable, partes, plazos involucrados).
4. **Citas y Fuentes (OBLIGATORIO):** Toda respuesta teórica o sustantiva debe incluir al final referencias en la medida de lo posible, con el formato: `Fuente: [Nombre de ley, código, estatuto o caso]. [Año].` No inventes citas. Si no estás seguro de la referencia técnica exacta, confía en los principios generales (e.g. Código Civil, Common Law) y aclara este hecho.
5. **Idioma congruente:** Responde siempre en el mismo idioma en el que se te formule la pregunta. Mantén los latinismos y clasificaciones legales en su idioma de origen si son universales.
6. **Alcance Estricto:** If the user asks questions outside of legal, commercial, contractual, or regulatory scope, respond: *"Este modelo de IA creado por Go Contracto Inc. solo responde a preguntas jurídicas, revisión de contratos y análisis legal."*"""

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
    # ========================================================================
    async def generate_contract(self, contract_type: str, inputs: dict, rules: Optional[str] = None, agent_prompt: Optional[str] = None) -> str:
        """Generate a complete contract document."""
        system_context = self.contract_instruction
        if agent_prompt:
            system_context = f"{self.contract_instruction}\n\nADDITIONAL AGENT INSTRUCTIONS:\n{agent_prompt}"

        user_prompt = f"""Generate a **{contract_type}**.

**Party and Contract Details**:
{self._format_inputs(inputs)}

**Template Rules**:
{rules if rules else "None - use standard clauses."}

Ensure the contract is complete and legally sound. Include all standard protective clauses.
"""
        response = await self.client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[
                {"role": "system", "content": system_context},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=8192,
        )
        return response.choices[0].message.content

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
