import asyncio
import random
import time

import openai
from openai import OpenAI, AsyncOpenAI

from src.config.app_config import get_settings
from src.dtos.schema_in.query import ChunkPayload, ConversationItem

settings = get_settings()
from functools import wraps

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def prepare_messages(queries: str, context: list[ChunkPayload], conversation: list[ConversationItem]):
    messages = [
        {
            "role": "system",
            "content": "You are Verba, The Golden RAGtriever, a chatbot for Retrieval Augmented Generation (RAG). You will receive a user query and context pieces that have a semantic similarity to that specific query. Please answer these user queries only their provided context. If the provided documentation does not provide enough information, say so. If the user asks questions about you as a chatbot specifically, answer them naturally. If the answer requires code examples encapsulate them with ```programming-language-name ```. Don't do pseudo-code.",
        }
    ]

    for message in conversation:
        if isinstance(message, dict):
            message = ConversationItem(**message)
        messages.append({"role": message.role, "content": message.message})

    context2 = [chunk.to_custom_string() for chunk in context]
    user_context = " ".join(context2)

    messages.append(
        {
            "role": "user",
            "content": f"Please answer this query: '{queries}' with this provided context: {user_context}",
        }
    )

    return messages


def async_retry_with_exponential_backoff(
        initial_delay: float = 1,
        exponential_base: float = 2,
        jitter: bool = True,
        max_retries: int = 10,
        errors: tuple = (Exception,),
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            num_retries = 0
            delay = initial_delay
            while True:
                try:
                    return await func(*args, **kwargs)
                except errors as e:
                    print(f"Error: {e}")
                    num_retries += 1
                    if num_retries > max_retries:
                        raise Exception(f"Maximum number of retries ({max_retries}) exceeded.")
                    delay *= exponential_base * (1 + jitter * random.random())
                    await asyncio.sleep(delay)
                except Exception as e:
                    raise e

        return wrapper

    return decorator


@async_retry_with_exponential_backoff()
async def completions_with_backoff(**kwargs):
    return await client.chat.completions.create(**kwargs)


async def generate_stream(queries: str, context: list, conversation: list):
    messages = prepare_messages(queries, context, conversation)
    print(messages)
    try:
        stream = await completions_with_backoff(
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in stream:
            yield chunk
    except Exception as e:
        print(f"An error occurred in generate_stream: {e}")
        raise e
