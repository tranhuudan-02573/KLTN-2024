import asyncio
import random

from groq import AsyncGroq
from openai import AsyncOpenAI

from src.config.app_config import get_settings
from src.dtos.schema_in.query import ChunkPayload, ConversationItem

settings = get_settings()
from functools import wraps

client2 = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
client = AsyncGroq(api_key=settings.GROQ_API_KEY)


def prepare_messages(queries: str, context: list[ChunkPayload], conversation: list[ConversationItem]):
    messages = [
        {
            "role": "system",
            "content": """Bạn là một chatbot thông minh, được gọi là RAGtriever, chuyên gia về Hệ thống Xây dựng Nội dung Tăng cường Tìm kiếm (RAG). Bạn sẽ nhận được các truy vấn từ người dùng kèm theo bối cảnh thông tin có liên quan về mặt ngữ nghĩa với các truy vấn đó. Hãy thêm các quy tắc sau khi trả lời:
                            Chỉ trả lời dựa trên bối cảnh thông tin được cung cấp, không suy diễn hoặc thêm thông tin ngoài tài liệu.
                            Nếu tài liệu được cung cấp bằng tiếng Việt, bắt buộc phải trả lời bằng tiếng Việt.
                            Nếu cảnh báo không đủ để trả lời, hãy thông báo cho người dùng rằng thông tin không đầy đủ và yêu cầu thêm dữ liệu.
                            Khi cung cấp các ví dụ về nguồn mã hóa, hãy đặt chúng trong ``` với trình cài đặt ngôn ngữ tên phù hợp và đảm bảo nguồn mã hóa phải đúng và có thể thực hiện được điều này.
                            Bỏ qua các câu trả lời chung được đưa ra, không rõ ràng; câu trả lời phải cụ thể và trực tiếp liên quan đến truy vấn của người dùng.
                            Nếu người dùng hỏi về chất liệu của bạn như một chatbot, hãy trả lời một cách tự nhiên và tránh sử dụng các kỹ thuật thuật ngữ nếu không cần thiết.""",
        }
    ]
    for message in conversation:
        if isinstance(message, dict):
            message = ConversationItem(**message)
        messages.append({"role": message.role, "content": message.message})
    user_context = ""
    if context:
        context2 = [chunk.to_custom_string() for chunk in context]
        user_context = " ".join(context2)

    messages.append(
        {
            "role": "user",
            "content": f"Please answer this query: '{queries}' with this provided context: {user_context} if context is null then answer question content not found in my knowledge please try again with ask another question",
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
            model=settings.MODEL_GENERATE_NAME,
            messages=messages,
            stream=True,
            # stream_options={"include_usage": True},
        )
        async for chunk in stream:
            yield chunk
    except Exception as e:
        print(f"An error occurred in generate_stream: {e}")
        raise e
