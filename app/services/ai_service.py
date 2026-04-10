"""AI Service for contract generation and agent-based chat."""
import google.generativeai as genai
from app.core.config import settings
from app.schemas.ai import ChatMessage, Attachment
from typing import AsyncGenerator, Optional, TYPE_CHECKING, List, Any
import json
import logging

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

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
6. **Alcance Estricto:** Si el usuario hace preguntas fuera de lo comercial, legal, contractual o regulatorio, responde exactamente: *"Este modelo de IA creado por Go Contracto Inc. solo responde a preguntas jurídicas, revisión de contratos y análisis legal."*"""

        def search_user_contracts(status: str = None, date_range: str = None, contract_id: str = None):
            """
            Search and retrieve the user's contracts from the database. Use this tool autonomously when the user asks about their contracts, summaries, or recent activity.
            Args:
                status: Filter by contract status (e.g., 'completed', 'in_progress', 'draft').
                date_range: Optional date range or relative time (e.g., 'last 30 days').
                contract_id: Optional specific contract ID.
            """
            pass

        self.model_chat = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=self.generation_config,
        )

        self.model_lexia = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config=self.generation_config,
            system_instruction=self.lexia_prompt,
            tools=[search_user_contracts]
        )

        self.model_contract = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config=self.generation_config,
        )

    async def chat(self, message: str, history: list[ChatMessage]) -> str:
        """Standard chat with full response. (Deprecated in favor of chat_lexia)"""
        contents = [{"role": "user", "parts": [self.legal_chat_instruction + "\n\nUser question: " + message]}]
        if history:
            for msg in history:
                contents.append({"role": msg.role, "parts": msg.parts})
            contents.append({"role": "user", "parts": [message]})
        response = await self.model_chat.generate_content_async(contents)
        return response.text

    async def chat_lexia(self, message: str, history: list[ChatMessage], db: "AsyncSession", user_id: int) -> str:
        """Chat specifically with the LexIA agent, supporting tool calls."""
        contents = []
        for msg in history:
            # map history role to 'user' or 'model'
            role = "user" if msg.role in ["user", "user"] else "model"
            contents.append({"role": role, "parts": msg.parts})
            
        chat = self.model_lexia.start_chat(history=contents)
        
        # We don't stream here, just get full response
        response = await chat.send_message_async(message)
        
        # Check if the model decided to call the tool
        if response.function_call:
            fc = response.function_call
            if fc.name == "search_user_contracts":
                tool_data = await self._execute_search_contracts(fc.args, db, user_id)
                
                # Feed Tool result back to the model
                response = await chat.send_message_async(
                    {"role": "function", "parts": [{"function_response": {"name": fc.name, "response": tool_data}}]}
                )
                
        return response.text

    async def chat_lexia_stream(
        self, message: str, history: List[ChatMessage], db: "AsyncSession", user_id: int, attachments: List[Attachment] = []
    ) -> AsyncGenerator[str, None]:
        contents = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": msg.parts})
            
        chat = self.model_lexia.start_chat(history=contents)
        
        # Prepare current message parts (Multimodal)
        msg_parts = [message]
        if attachments:
            for att in attachments:
                # Use the dict format that Gemini SDK expects for inline data
                msg_parts.append({
                    "mime_type": att.mime_type,
                    "data": att.base64_data
                })
        
        response = await chat.send_message_async(msg_parts, stream=True)
        
        has_func_call = False
        fc_name = None
        fc_args = None
        
        async for chunk in response:
            if chunk.function_call:
                has_func_call = True
                fc = chunk.function_call
                fc_name = fc.name
                fc_args = getattr(fc, 'args', {})
                # For streaming, the function call part arrives, we must stop yielding text and execute it
                break
            if chunk.text:
                yield chunk.text
                
        if has_func_call and fc_name == "search_user_contracts":
            # 1. Provide visual feedback (Optional but good UX)
            yield "\n*Consultando tus contratos en la base de datos...*\n"
            
            tool_data = await self._execute_search_contracts(fc_args, db, user_id)
            
            # Send result and stream the followup
            followup = await chat.send_message_async(
                {"role": "function", "parts": [{"function_response": {"name": fc_name, "response": tool_data}}]},
                stream=True
            )
            async for follow_chunk in followup:
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
            contents.append({"role": "user", "parts": [context_prompt + "\n\nHola, necesito ayuda con este contrato."]})
            contents.append({"role": "model", "parts": [f"Entendido. Te ayudaré con tu contrato de {template_name}. ¿Qué duda tienes?"]})
        else:
            for msg in history:
                role = "user" if msg.role == "user" else "model"
                contents.append({"role": role, "parts": msg.parts})
        
        # Prepare multimodal query
        query_parts = [f"{context_prompt}\n\nPregunta del usuario: {message}"]
        if attachments:
            for att in attachments:
                query_parts.append({
                    "mime_type": att.mime_type,
                    "data": att.base64_data
                })
        
        chat = self.model_lexia.start_chat(history=contents)
        response = await chat.send_message_async(query_parts, stream=True)
        
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def _execute_search_contracts(self, args: dict, db: "AsyncSession", user_id: int) -> dict:
        """Internal helper to execute the DB query safely."""
        from app.models import Contract
        from sqlalchemy import select
        
        try:
            stmt = select(Contract).where(Contract.user_id == user_id)
            
            # Additional filters (AI might pass them differently, check dict safely)
            if args:
                if args.get("status"):
                    stmt = stmt.where(Contract.status == args["status"])
                # Limit might be implemented, but force max 10 to protect memory
                
            res = await db.execute(stmt)
            contracts = res.scalars().all()
            
            context_data = []
            for c in contracts[:10]:
                content_preview = ""
                if c.generated_content:
                    # provide up to 2500 chars to avoid prompt overflow but give meaningful context
                    content_preview = c.generated_content[:2500] + "..."
                
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
        """Streaming chat for real-time responses. (Deprecated in favor of chat_lexia_stream)"""
        contents = [{"role": "user", "parts": [self.legal_chat_instruction + "\n\nUser question: " + message]}]
        if history:
            for msg in history:
                contents.append({"role": msg.role, "parts": msg.parts})
            contents.append({"role": "user", "parts": [message]})

        response = await self.model_chat.generate_content_async(contents, stream=True)
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

# Use get_ai_service() for lazy initialization.
# Do NOT create a module-level instance — it will crash the app
# if GOOGLE_API_KEY is missing or invalid at import time.
