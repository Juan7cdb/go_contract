"""AI Service for contract generation and agent-based chat using the new google-genai SDK."""
from google import genai
from google.genai import types
from app.core.config import settings
from app.schemas.ai import ChatMessage, Attachment
from typing import AsyncGenerator, Optional, TYPE_CHECKING, List, Any
import json
import logging
import base64

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Lazy initialization
_ai_service_instance = None


class AIService:
    def __init__(self):
        if not settings.GOOGLE_API_KEY or "change_me" in settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY is not set correctly. AI features will fail.")
        
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        
        # Generation config optimized for legal accuracy
        self.config_base = types.GenerateContentConfig(
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

        # Tool definition for the new SDK
        self.search_tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="search_user_contracts",
                    description="Search and retrieve the user's contracts from the database. Use this tool autonomously when the user asks about their contracts, summaries, or recent activity.",
                    parameters=types.Schema(
                        type="OBJECT",
                        properties={
                            "status": types.Schema(type="STRING", description="Filter by contract status (e.g., 'completed', 'in_progress', 'draft')"),
                            "date_range": types.Schema(type="STRING", description="Optional date range or relative time (e.g., 'last 30 days')"),
                            "contract_id": types.Schema(type="STRING", description="Optional specific contract ID")
                        }
                    )
                )
            ]
        )

        self.lexia_config = types.GenerateContentConfig(
            temperature=0.2,
            system_instruction=self.lexia_prompt,
            tools=[self.search_tool]
        )

    def _map_history(self, history: list[ChatMessage]) -> list[types.Content]:
        """Maps ChatMessage history to the format expected by the new SDK."""
        mapped = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            parts = []
            for p in msg.parts:
                if isinstance(p, str):
                    parts.append(types.Part.from_text(text=p))
                elif isinstance(p, dict):
                    # Handle multimodal or function calling parts in history if needed
                    if "text" in p:
                        parts.append(types.Part.from_text(text=p["text"]))
                    elif "inline_data" in p:
                        # Assuming structure compatible with types.Part.from_bytes
                        pass
            if parts:
                mapped.append(types.Content(role=role, parts=parts))
        return mapped

    async def chat(self, message: str, history: list[ChatMessage]) -> str:
        """Standard chat with full response."""
        contents = self._map_history(history)
        
        # Add current message with instruction
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=f"{self.legal_chat_instruction}\n\nUser question: {message}")]))
        
        response = await self.client.aio.models.generate_content(
            model="gemini-1.5-flash",
            contents=contents,
            config=self.config_base
        )
        return response.text

    async def chat_lexia(self, message: str, history: list[ChatMessage], db: "AsyncSession", user_id: int) -> str:
        """Chat specifically with the LexIA agent, supporting tool calls."""
        contents = self._map_history(history)
            
        # FIX: client.aio.chats.create is NOT a coroutine, do not await it.
        chat = self.client.aio.chats.create(
            model="gemini-1.5-pro",
            history=contents,
            config=self.lexia_config
        )
        
        response = await chat.send_message(message)
        
        # Handle function calls
        if response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    fc = part.function_call
                    if fc.name == "search_user_contracts":
                        tool_data = await self._execute_search_contracts(fc.args, db, user_id)
                        
                        # Feed Tool result back
                        response = await chat.send_message(
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part.from_function_response(
                                        name=fc.name,
                                        response=tool_data
                                    )
                                ]
                            )
                        )
                        break
                        
        return response.text

    async def chat_lexia_stream(
        self, message: str, history: List[ChatMessage], db: "AsyncSession", user_id: int, attachments: List[Attachment] = []
    ) -> AsyncGenerator[str, None]:
        """Streaming chat for LexIA with corrected SDK usage."""
        contents = self._map_history(history)
            
        # FIX: client.aio.chats.create is NOT a coroutine, do not await it.
        chat = self.client.aio.chats.create(
            model="gemini-1.5-pro",
            history=contents,
            config=self.lexia_config
        )
        
        # Prepare message parts
        msg_parts = [types.Part.from_text(text=message)]
        if attachments:
            for att in attachments:
                try:
                    raw_data = base64.b64decode(att.base64_data)
                    msg_parts.append(types.Part.from_bytes(data=raw_data, mime_type=att.mime_type))
                except Exception as e:
                    logger.error(f"Error decoding attachment: {e}")

        response_stream = await chat.send_message_stream(msg_parts)
        
        has_func_call = False
        fc_name = None
        fc_args = None
        
        # Note: In current google-genai aio, we iterate over the .stream property synchronously
        for chunk in response_stream.stream:
            if chunk.candidates and chunk.candidates[0].content.parts:
                for part in chunk.candidates[0].content.parts:
                    if part.function_call:
                        has_func_call = True
                        fc_name = part.function_call.name
                        fc_args = part.function_call.args
                        break
                    if part.text:
                        yield part.text
            if has_func_call:
                break
                
        if has_func_call and fc_name == "search_user_contracts":
            yield "\n*Consultando tus contratos en la base de datos...*\n"
            tool_data = await self._execute_search_contracts(fc_args, db, user_id)
            
            followup_stream = await chat.send_message_stream(
                types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(name=fc_name, response=tool_data)]
                )
            )
            for follow_chunk in followup_stream.stream:
                if follow_chunk.text:
                    yield follow_chunk.text

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
        contents = []
        if not history:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=context_prompt + "\n\nHola, necesito ayuda con este contrato.")]))
            contents.append(types.Content(role="model", parts=[types.Part.from_text(text=f"Entendido. Te ayudaré con tu contrato de {template_name}. ¿Qué duda tienes?")]))
        else:
            contents = self._map_history(history)
        
        msg_parts = [types.Part.from_text(text=f"{context_prompt}\n\nPregunta del usuario: {message}")]
        if attachments:
            for att in attachments:
                try:
                    raw_data = base64.b64decode(att.base64_data)
                    msg_parts.append(types.Part.from_bytes(data=raw_data, mime_type=att.mime_type))
                except Exception:
                    pass
        
        # FIX: client.aio.chats.create is NOT a coroutine
        chat = self.client.aio.chats.create(model="gemini-1.5-pro", history=contents)
        response_stream = await chat.send_message_stream(msg_parts)
        
        for chunk in response_stream.stream:
            if chunk.text:
                yield chunk.text

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

    async def chat_stream(self, message: str, history: list[ChatMessage]) -> AsyncGenerator[str, None]:
        """Streaming chat for real-time responses."""
        contents = self._map_history(history)
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=f"{self.legal_chat_instruction}\n\nUser question: {message}")]))

        response_stream = await self.client.aio.models.generate_content_stream(
            model="gemini-1.5-flash",
            contents=contents,
            config=self.config_base
        )
        for chunk in response_stream.stream:
            if chunk.text:
                yield chunk.text

    async def chat_with_agent(self, message: str, agent_prompt: str, history: Optional[list[dict]] = None) -> str:
        """Chat with a specific AI agent using its custom prompt."""
        full_prompt = f"{agent_prompt}\n\n---\nUser message: {message}"
        if history:
            history_text = "\n".join([f"{h.get('role', 'user')}: {h.get('content', '')}" for h in history[-5:]])
            full_prompt = f"{agent_prompt}\n\n---\nRecent conversation:\n{history_text}\n\nUser message: {message}"
        
        response = await self.client.aio.models.generate_content(
            model="gemini-1.5-flash",
            contents=full_prompt,
            config=self.config_base
        )
        return response.text

    async def chat_with_agent_stream(self, message: str, agent_prompt: str, history: Optional[list[dict]] = None) -> AsyncGenerator[str, None]:
        """Streaming chat with a specific AI agent."""
        full_prompt = f"{agent_prompt}\n\n---\nUser message: {message}"
        if history:
            history_text = "\n".join([f"{h.get('role', 'user')}: {h.get('content', '')}" for h in history[-5:]])
            full_prompt = f"{agent_prompt}\n\n---\nRecent conversation:\n{history_text}\n\nUser message: {message}"
        
        response_stream = await self.client.aio.models.generate_content_stream(
            model="gemini-1.5-flash",
            contents=full_prompt,
            config=self.config_base
        )
        for chunk in response_stream.stream:
            if chunk.text:
                yield chunk.text

    async def generate_contract(self, contract_type: str, inputs: dict, rules: Optional[str] = None, agent_prompt: Optional[str] = None) -> str:
        """Generate a complete contract document."""
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
        response = await self.client.aio.models.generate_content(
            model="gemini-1.5-pro",
            contents=prompt,
            config=self.config_base
        )
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
    """Lazy initialization of AI service."""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance
