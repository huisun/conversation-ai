"""
Example: Using OpenAI Chat Completions API with TAC Memory Injection

Demonstrates how to use with_tac_memory with the Chat Completions API.
For the Responses API, see responses_api.py.
"""

import os
import asyncio
import json
import time
from collections import OrderedDict

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from tac import TAC, TACConfig
from tac.adapters.openai import with_tac_memory
from tac.channels.sms import SMSChannel, SMSChannelConfig
from tac.channels.voice import VoiceChannel, VoiceChannelConfig
from tac.core.logging import get_logger
from tac.models.session import ConversationSession, AuthorInfo
from tac.models.tac import TACMemoryResponse
from tac.server import TACFastAPIServer
from tac.channels.whatsapp import WhatsAppChannel, WhatsAppChannelConfig
from tac.tools import create_knowledge_tool
from fastapi import Request
from fastapi.responses import JSONResponse

from tac.models.conversation import (
    ParticipantRequest,
    ParticipantAddress,
    CommunicationRequest,
    CommunicationParticipant,
    CommunicationContent,
)

load_dotenv()

logger = get_logger(__name__)

# Initialize TAC with configuration from environment variables
tac = TAC(config=TACConfig.from_env())

# Create channel handlers for Voice and SMS
voice_channel = VoiceChannel(tac, config=VoiceChannelConfig(memory_mode="once"))
sms_channel = SMSChannel(tac, config=SMSChannelConfig(memory_mode="always"))
whatsapp_channel = WhatsAppChannel(tac, config=WhatsAppChannelConfig(memory_mode="always"))

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Store conversation history per conversation
conversation_history: dict[str, list[ChatCompletionMessageParam]] = {}

SYSTEM_MESSAGE: ChatCompletionSystemMessageParam = {
    "role": "system",
    "content": (
        "You are a customer service agent speaking with a user over voice or SMS. "
        "Keep responses short and conversational — a sentence or two. "
        "Do not use markdown, asterisks, bullets, or emojis; your words will be "
        "spoken aloud or sent as plain text."
    ),
}

knowledge_tool = asyncio.run(
    create_knowledge_tool(
        knowledge_client=tac.knowledge_client,
        knowledge_base_id=tac.config.knowledge_base_id,
        name="search_knowledge_base",
        description="Search the company knowledge base for product info, policies, and FAQs. Input must be a question string.",
        top_k=5,
    )
)


async def handle_message_ready(
    user_message: str,
    context: ConversationSession,
    memory_response: TACMemoryResponse | None,
) -> str:
    """
    Callback invoked when a message is ready to be processed.

    This example uses the Chat Completions API with automatic memory injection.

    Args:
        user_message: The customer's message text
        context: Session data (conversation_id, channel, profile, etc.)
        memory_response: Optional retrieved memories (observations, summaries, communications)

    Returns:
        Response string to send to the channel
    """
    print(f" CALLBACK FIRED | channel={context.channel} | msg={user_message} | context={context}")
    conv_id = context.conversation_id

    try:
        # Initialize conversation history for new conversations
        if conv_id not in conversation_history:
            conversation_history[conv_id] = [SYSTEM_MESSAGE]

        print(f"PROFILE: {context.profile.traits if context.profile else None}")

        # Add user message to conversation history
        user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": user_message}
        conversation_history[conv_id].append(user_msg)

        # Wrap OpenAI client with TAC adapter for automatic memory injection
        # The adapter injects memory as a system message at the start of the messages array
        client = with_tac_memory(openai_client, memory_response, context)

        # Call OpenAI Chat Completions API - memory is automatically injected
        # Expose the knowledge base search tool to the model
        tools = [knowledge_tool.to_openai_format()]

        response = await client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=conversation_history[conv_id],
            tools=tools,
        )
        msg = response.choices[0].message

        # Tool-call loop: run KB searches until the model produces a final answer
        while msg.tool_calls:
            conversation_history[conv_id].append(msg)

            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                print("KB SEARCH:", args)  # remove once verified
                results = await knowledge_tool(**args)
                conversation_history[conv_id].append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(
                        [r.model_dump(mode="json") for r in results]
                    ),
                })

            response = await client.chat.completions.create(
                model="gpt-5.4-mini",
                messages=conversation_history[conv_id],
                tools=tools,
            )
            msg = response.choices[0].message

        llm_response = msg.content or ""

        # Save assistant response to conversation history
        assistant_msg: ChatCompletionAssistantMessageParam = {
            "role": "assistant",
            "content": llm_response,
        }
        conversation_history[conv_id].append(assistant_msg)

        return llm_response

    except Exception as e:
        logger.error("Error processing message", conversation_id=conv_id, error=str(e))
        return "Sorry, I encountered an error processing your message."


# Register the message handler callback
tac.on_message_ready(handle_message_ready)

if __name__ == "__main__":
    # The path TAC mounts its Conversation Orchestrator webhook on. Not configurable
    # in this SDK version — this constant only has to match what TAC actually
    # registers, so the echo-suppression middleware below can recognise it.
    WEBHOOK_PATH = "/webhook"

    # TACFastAPIServer creates a FastAPI app with all required endpoints:
    # - /twiml: Voice call webhook (returns TwiML with ConversationRelay)
    # - /ws: WebSocket endpoint for Voice channel
    # - /webhook: Conversation webhook for all channels
    server = TACFastAPIServer(
        tac=tac, voice_channel=voice_channel, messaging_channels=[sms_channel, whatsapp_channel]
    )

    # Confirm the mounted paths at startup — if TAC's webhook is not on
    # WEBHOOK_PATH, the middleware silently stops suppressing echoes.
    print("ROUTES |", sorted(getattr(r, "path", "") for r in server.app.routes))

    # No conversation-id cache: CO's conversation list is the source of truth and
    # is looked up per request. Only LLM-side state is held locally, keyed by
    # conv_id, so a rotation needs no invalidation.
    agent_sessions: dict[str, ConversationSession] = {}
    conv_locks: dict[str, asyncio.Lock] = {}

    CHANNEL_MAP = {"whatsapp": "WHATSAPP", "sms": "SMS", "chat": "CHAT"}
    AGENT_ADDRESS = "agent-endpoint"

    # GET /v2/Conversations has no participant-address filter, so matching happens
    # client-side over ACTIVE conversations. Bounded so a large account can't turn
    # one inbound message into an unbounded pagination walk.
    LOOKUP_PAGE_SIZE = 50
    MAX_LOOKUP_PAGES = 5

    # =========================================================================
    # Echo suppression. Communications written by /agent come straight back as
    # CO webhook events; without this the messaging channels reprocess them and
    # send a real SMS/WhatsApp. Safe to delete this whole block if /agent only
    # ever runs with channel="chat".
    # =========================================================================
    _self_written: OrderedDict[str, float] = OrderedDict()

    def _mark_self_written(comm) -> None:
        sid = getattr(comm, "sid", None) or getattr(comm, "id", None)
        if not sid:
            return
        _self_written[sid] = time.monotonic()
        while len(_self_written) > 2000:
            _self_written.popitem(last=False)

    @server.app.middleware("http")
    async def skip_agent_echoes(request: Request, call_next):
        if request.method == "POST" and request.url.path == WEBHOOK_PATH:
            body = await request.body()
            try:
                evt = json.loads(body)
            except json.JSONDecodeError:
                evt = {}
            sid = (evt.get("communication") or {}).get("sid") or evt.get("communicationSid")
            author = (evt.get("author") or {}).get("address")
            if (sid and sid in _self_written) or author == AGENT_ADDRESS:
                return JSONResponse({"status": "ignored", "reason": "written by /agent"})

            # Re-inject the consumed body so TAC's handler (and signature
            # validation) still sees the exact original bytes.
            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            request._receive = receive
        return await call_next(request)

    # =========================================================================
    # Conversation lookup
    # =========================================================================
    def _attr(obj, *names, default=None):
        """Read a field whether the SDK returns models or plain dicts, snake or camel."""
        for n in names:
            if isinstance(obj, dict):
                if n in obj:
                    return obj[n]
            elif hasattr(obj, n):
                return getattr(obj, n)
        return default

    def _participants(address: str, co_channel: str) -> list[ParticipantRequest]:
        return [
            ParticipantRequest(
                type="CUSTOMER",
                addresses=[ParticipantAddress(channel=co_channel, address=address)],
            ),
            ParticipantRequest(
                type="AI_AGENT",
                name=AGENT_ADDRESS,
                addresses=[ParticipantAddress(channel=co_channel, address=AGENT_ADDRESS)],
            ),
        ]

    def _match_participant(conv, ptype: str, address: str, co_channel: str) -> str | None:
        """Return the participant id matching this type/address/channel, if present."""
        for p in _attr(conv, "participants", default=[]) or []:
            if _attr(p, "type") != ptype:
                continue
            for a in _attr(p, "addresses", default=[]) or []:
                if _attr(a, "channel") == co_channel and _attr(a, "address") == address:
                    return _attr(p, "id")
        return None

    async def find_active_conversation(
        address: str, co_channel: str, avoid: set[str] | None = None
    ) -> tuple[str | None, dict | None]:
        """Find this customer's most recent ACTIVE conversation.

        Returns (conv_id, parts) where parts is None if the conversation exists but
        our AI_AGENT participant has not joined it yet.
        """
        avoid = avoid or set()
        matches: list[tuple[str, str, dict | None]] = []  # (sort_key, conv_id, parts)
        page_token = None

        for _ in range(MAX_LOOKUP_PAGES):
            try:
                page = await tac.conversation_orchestrator_client.list_conversations(
                    status=["ACTIVE"], page_size=LOOKUP_PAGE_SIZE, page_token=page_token
                )
            except Exception as e:
                logger.warning(f"/agent conversation lookup failed: {e}")
                return None, None

            for conv in _attr(page, "conversations", default=[]) or []:
                conv_id = _attr(conv, "id")
                if not conv_id or conv_id in avoid:
                    continue
                cust_id = _match_participant(conv, "CUSTOMER", address, co_channel)
                if not cust_id:
                    continue
                bot_id = _match_participant(conv, "AI_AGENT", AGENT_ADDRESS, co_channel)
                parts = None
                if bot_id:
                    parts = {
                        "cust": {"address": address, "channel": co_channel, "participantId": cust_id},
                        "bot": {"address": AGENT_ADDRESS, "channel": co_channel, "participantId": bot_id},
                    }
                sort_key = _attr(conv, "updated_at", "updatedAt") or _attr(
                    conv, "created_at", "createdAt"
                ) or ""
                matches.append((str(sort_key), conv_id, parts))

            meta = _attr(page, "meta")
            page_token = _attr(meta, "next_token", "nextToken") if meta is not None else None
            if not page_token:
                break

        if not matches:
            return None, None
        # Most recently updated wins if the account has several open for this address.
        matches.sort(key=lambda m: m[0], reverse=True)
        _, conv_id, parts = matches[0]
        return conv_id, parts

    async def resolve_conversation(
        address: str, co_channel: str, avoid: set[str] | None = None
    ) -> tuple[str, dict]:
        """Look up the live conversation; create one only if there isn't a usable one."""
        avoid = avoid or set()

        conv_id, parts = await find_active_conversation(address, co_channel, avoid=avoid)
        if conv_id and parts:
            return conv_id, parts
        if conv_id:
            logger.info(f"/agent {conv_id} is active but {AGENT_ADDRESS} has not joined; joining")

        conv_id, reused = await tac.conversation_orchestrator_client.create_or_reuse_conversation(
            participants=_participants(address, co_channel),
        )
        if conv_id in avoid:
            raise RuntimeError(f"CO returned unusable conversation {conv_id} again")

        participants = await tac.conversation_orchestrator_client.list_participants(conv_id)
        cust = next(p for p in participants if p.type == "CUSTOMER")
        bot = next(p for p in participants if p.type == "AI_AGENT")
        logger.info(f"/agent conversation ready: {conv_id} (reused={reused})")
        return conv_id, {
            "cust": {"address": address, "channel": co_channel, "participantId": cust.id},
            "bot": {"address": AGENT_ADDRESS, "channel": co_channel, "participantId": bot.id},
        }

    def _drop_local_state(conv_id: str) -> None:
        agent_sessions.pop(conv_id, None)
        conversation_history.pop(conv_id, None)
        conv_locks.pop(conv_id, None)

    async def log_communication(conv_id: str, author: dict, recipient: dict, text: str):
        """Write one message into the CO conversation (memory source of truth).

        Returns the created communication, or None if the write failed — a failure
        means the conversation closed between the lookup and now.
        """
        try:
            comm = await tac.conversation_orchestrator_client.create_communication(
                conversation_id=conv_id,
                communication_request=CommunicationRequest(
                    author=CommunicationParticipant(**author),
                    recipients=[CommunicationParticipant(**recipient)],
                    content=CommunicationContent(type="TEXT", text=text),
                ),
            )
            _mark_self_written(comm)
            return comm
        except Exception as e:
            logger.warning(f"/agent communication log failed on {conv_id}: {e}")
            return None

    # =========================================================================
    # Endpoint
    # =========================================================================
    @server.app.post("/agent")
    async def agent_endpoint(request: Request):
        raw_body = await request.body()
        print(f"AGENT BODY | {raw_body.decode('utf-8', errors='replace')}")
        try:
            data = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            return JSONResponse({"error": "invalid JSON"}, status_code=400)

        message = data.get("message", "")
        address = data.get("address") or data.get("From") or ""
        channel = data.get("channel", "chat").lower()
        if not message.strip() or not address.strip():
            return JSONResponse({"error": "message and address are required"}, status_code=400)
        co_channel = CHANNEL_MAP.get(channel, "CHAT")
        print(f"CO Channel | {co_channel} | Address | {address}")

        conv_id, parts = await resolve_conversation(address, co_channel)

        # --- Log the user's message (this is what becomes memory). The lookup can
        # --- still race a close, so a failed write rotates and retries once.
        if await log_communication(conv_id, parts["cust"], parts["bot"], message) is None:
            _drop_local_state(conv_id)
            try:
                conv_id, parts = await resolve_conversation(
                    address, co_channel, avoid={conv_id}
                )
            except RuntimeError as e:
                logger.error(f"/agent could not open a writable conversation: {e}")
                return JSONResponse({"error": "conversation unavailable"}, status_code=503)
            if await log_communication(conv_id, parts["cust"], parts["bot"], message) is None:
                logger.error(f"/agent write failed on fresh conversation {conv_id}")
                return JSONResponse({"error": "conversation unavailable"}, status_code=503)

        # --- Session tied to the conversation id we actually wrote to ---
        session = agent_sessions.get(conv_id)
        if session is None:
            session = ConversationSession(
                conversation_id=conv_id,
                channel=channel,
                author_info=AuthorInfo(
                    address=address, participant_id=parts["cust"]["participantId"]
                ),
            )
            agent_sessions[conv_id] = session

        # --- Memory + handler. Locked because conversation_history[conv_id] is
        # --- also written by the webhook path, and the tool-call loop appends
        # --- across awaits — interleaving orphans tool messages from tool_calls.
        async with conv_locks.setdefault(conv_id, asyncio.Lock()):
            try:
                memory_response = await tac.retrieve_memory(session, query=message)
            except Exception as e:
                logger.warning(f"/agent memory retrieval failed: {e}")
                memory_response = TACMemoryResponse([])

            reply = await handle_message_ready(message, session, memory_response)

        # --- Log the bot's reply into CO too. Awaited, not fire-and-forget:
        # --- backgrounding it hides write failures and races the echo guard.
        await log_communication(conv_id, parts["bot"], parts["cust"], reply)

        return JSONResponse({"reply": reply, "conversation_id": conv_id})

    server.start()