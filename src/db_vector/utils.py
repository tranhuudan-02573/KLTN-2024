from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

from src.config.app_config import get_settings


def generate_embeddings(text):
    embeddings = HuggingFaceInferenceAPIEmbeddings(
        api_key=get_settings().HUGGINGFACE_API_KEY,
        model_name="dangvantuan/vietnamese-embedding"
    )
    return embeddings.embed_query(text)


def get_recursive_token_chunk(chunk_size=256):
    MARKDOWN_SEPARATORS = [
        "\n#{1,6} ",
        "```\n",
        "\n\\*\\*\\*+\n",
        "\n---+\n",
        "\n___+\n",
        "\n\n",
        "\n",
        " ",
        "",
    ]
    EMBEDDING_MODEL_NAME = "dangvantuan/vietnamese-embedding"
    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        AutoTokenizer.from_pretrained(EMBEDDING_MODEL_NAME),
        chunk_size=chunk_size,
        chunk_overlap=int(chunk_size / 10),
        add_start_index=True,
        strip_whitespace=True,
        separators=MARKDOWN_SEPARATORS,
    )
    return text_splitter
