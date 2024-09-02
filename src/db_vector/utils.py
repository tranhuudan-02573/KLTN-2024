import time
from itertools import cycle

from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings

from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

from src.config.app_config import get_settings

settings = get_settings()


def generate_embeddings(text, max_retries=3, retry_delay=2):
    api_keys = [
        "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",
        "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",
        "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",
        "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",
        "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"
        "hf_kSiUugxacRkoRRHKRIGPjJXzHfwsevbGMMs"
    ]
    api_key_cycle = cycle(api_keys)
    for _ in range(max_retries):
        try:
            current_api_key = next(api_key_cycle)
            embeddings = HuggingFaceInferenceAPIEmbeddings(
                api_key=current_api_key,
                model_name=settings.MODEL_EMBEDDING_NAME
            )
            return embeddings.embed_query(text)
        except Exception as e:
            print(f"API key {current_api_key} failed. Error: {str(e)}. Trying the next one...")
            time.sleep(retry_delay)
    raise Exception("All API keys failed. Please check your keys or try again later.")


def generate_embeddings2(text):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(settings.MODEL_EMBEDDING_PATH)
    return model.encode(text)


def get_recursive_token_chunk(chunk_size=250):
    MARKDOWN_SEPARATORS = ["\n\n", "\n", "\t", ". ", "; ", ", ", " "]
    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        AutoTokenizer.from_pretrained(settings.MODEL_EMBEDDING_NAME),
        chunk_size=chunk_size,
        chunk_overlap=int(chunk_size / 10),
        add_start_index=True,
        strip_whitespace=True,
        separators=MARKDOWN_SEPARATORS,
    )
    return text_splitter
