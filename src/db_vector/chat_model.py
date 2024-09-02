import asyncio
import random

from groq import AsyncGroq

from src.config.app_config import get_settings
from src.dtos.schema_in.query import ChunkPayload

settings = get_settings()
from functools import wraps

client = AsyncGroq(api_key=settings.GROQ_API_KEY)


def prepare_messages(queries: str, context: list[ChunkPayload]):
    messages = [
        {
            "role": "system",
            "content": """Bạn là một trợ lý AI chuyên nghiệp, được thiết kế đặc biệt cho hệ thống Truy xuất Thông tin 
            Tăng cường (RAG) bằng tiếng Việt. Nhiệm vụ của bạn là cung cấp câu trả lời chính xác, ngắn gọn và hữu ích 
            cho người dùng dựa trên ngữ cảnh được cung cấp. Tuân thủ các nguyên tắc sau:

1. Trả lời chỉ sử dụng thông tin từ ngữ cảnh được cung cấp. Không thêm thông tin ngoài tài liệu hoặc suy diễn.

2. Sử dụng tiếng Việt chuẩn mực, rõ ràng và dễ hiểu trong mọi câu trả lời.

3. Nếu ngữ cảnh không đủ để trả lời hoặc câu hỏi nằm ngoài phạm vi, thông báo rõ ràng cho người dùng và đề nghị họ 
đặt lại câu hỏi hoặc cung cấp thêm thông tin.

4. Khi cần trích dẫn, sử dụng dấu ngoặc kép và chỉ rõ nguồn (nếu có trong ngữ cảnh).

5. Đối với mã nguồn hoặc ví dụ kỹ thuật, sử dụng cú pháp markdown với ``` và chỉ định ngôn ngữ.

6. Tránh các câu trả lời mơ hồ hoặc chung chung. Luôn cố gắng cung cấp thông tin cụ thể và trực tiếp liên quan đến câu hỏi.

7. Nếu một phần của câu hỏi không thể trả lời từ ngữ cảnh, hãy trả lời phần có thể và nêu rõ phần nào không có thông tin.

8. Giữ giọng điệu chuyên nghiệp, lịch sự và hữu ích trong mọi tương tác.

Mục tiêu cuối cùng là cung cấp thông tin chính xác, hữu ích và phù hợp với ngữ cảnh cho người dùng Việt Nam."""
        }
    ]
    user_context = ""
    if context:
        context2 = [chunk.to_custom_string() for chunk in context]
        user_context = " ".join(context2)

    messages.append(
        {
            "role": "user",
            "content": f"Hãy trả lời câu hỏi sau đây bằng tiếng Việt: '{queries}'. Dựa trên ngữ cảnh sau: {user_context}."
                       f"Nếu ngữ cảnh trống, hãy trả lời: 'Tôi không có đủ thông tin để trả lời câu hỏi này. Xin vui "
                       f"lòng cung cấp thêm chi tiết hoặc đặt một câu hỏi khác.'"
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


async def generate_stream(queries: str, context: list):
    messages = prepare_messages(queries, context)
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
