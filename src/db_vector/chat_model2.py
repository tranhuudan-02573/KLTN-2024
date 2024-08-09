import groq
from huggingface_hub import InferenceClient
import json


def call_llm(prompt: str):
    repo_id = "mistralai/Mistral-7B-Instruct-v0.3"
    inference_client = InferenceClient(
        model=repo_id,
        timeout=120,
        token="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",
    )
    response = inference_client.post(
        json={
            "inputs": prompt,
            "parameters": {"max_new_tokens": 1000},
            "task": "text-generation",
        },
    )
    return json.loads(response.decode())[0]["generated_text"]


def groq_chat_completion(user_str: str, system_str: str = "You are a helpful assistant.") -> str:
    try:
        client = groq.Groq(
            api_key="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",
        )

        chat_completion = client.with_options(max_retries=5).chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_str
                },
                {
                    "role": "user",
                    "content": user_str
                },
            ],
            model="llama3-8b-8192",
        )
        return chat_completion.choices[0].message.content
    except groq.APIConnectionError as e:
        return f"The server could not be reached: {e.__cause__}"
    except groq.RateLimitError as e:
        return "A 429 status code was received; we should back off a bit."
    except groq.APIStatusError as e:
        return f"Another non-200-range status code was received: {e.status_code}\n{e.response}"


async def groq_chat_completion_async(user_str: str, system_str: str = "You are a helpful assistant.") -> str:
    try:
        client = groq.AsyncGroq(
            api_key="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",
        )

        chat_completion = await client.with_options(max_retries=5).chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_str
                },
                {
                    "role": "user",
                    "content": user_str
                },
            ],
            model="llama3-8b-8192",
        )
        return chat_completion.choices[0].message.content
    except groq.APIConnectionError as e:
        return f"The server could not be reached: {e.__cause__}"
    except groq.RateLimitError as e:
        return "A 429 status code was received; we should back off a bit."
    except groq.APIStatusError as e:
        return f"Another non-200-range status code was received: {e.status_code}\n{e.response}"


def groq_chat_completion_stream(user_str: str, system_str: str = "You are a helpful assistant.") -> str:
    try:
        client = groq.Groq(
            api_key="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",
        )
        with client.with_options(max_retries=5).chat.completions.with_streaming_response.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_str
                    },
                    {
                        "role": "user",
                        "content": user_str
                    },
                ],
                model="llama3-8b-8192",
        ) as response:
            content = []
            for line in response.iter_lines():
                content.append(line)
            return "".join(content)
    except groq.APIConnectionError as e:
        return f"The server could not be reached: {e.__cause__}"
    except groq.RateLimitError as e:
        return "A 429 status code was received; we should back off a bit."
    except groq.APIStatusError as e:
        return f"Another non-200-range status code was received: {e.status_code}\n{e.response}"
