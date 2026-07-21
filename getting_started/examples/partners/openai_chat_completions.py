"""
Example: Using OpenAI Chat Completions API with TAC Memory Injection

Demonstrates how to use with_tac_memory with the Chat Completions API.
For the Responses API, see responses_api.py.
"""

import os
import asyncio
import json

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
from tac.models.session import ConversationSession
from tac.models.tac import TACMemoryResponse
from tac.server import TACFastAPIServer
from tac.channels.whatsapp import WhatsAppChannel, WhatsAppChannelConfig
from tac.tools import create_knowledge_tool

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
    print(f" CALLBACK FIRED | channel={context.channel} | msg={user_message}")
    conv_id = context.conversation_id

    try:
        # Initialize conversation history for new conversations
        if conv_id not in conversation_history:
            conversation_history[conv_id] = [SYSTEM_MESSAGE]

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
    # TACFastAPIServer creates a FastAPI app with all required endpoints:
    # - /twiml: Voice call webhook (returns TwiML with ConversationRelay)
    # - /ws: WebSocket endpoint for Voice channel
    # - /webhook: Conversation webhook for all channels
    server = TACFastAPIServer(
        tac=tac, voice_channel=voice_channel, messaging_channels=[sms_channel, whatsapp_channel]
    )
    server.start()
