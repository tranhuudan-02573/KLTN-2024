from typing import List, Optional
import matplotlib.pyplot as plt
import pandas as pd
from tqdm import tqdm
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer
from langchain.docstore.document import Document as LangchainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from functools import lru_cache

from src.db_vector.evaluate.chunk_sermantic_visualize import chunk_semantic
from src.db_vector.weaviate_rag_non_tenant import load_file

pd.set_option("display.max_colwidth", None)

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


@lru_cache(maxsize=1)
def get_tokenizer():
    return AutoTokenizer.from_pretrained(EMBEDDING_MODEL_NAME)


def process_documents(raw_knowledge_base: List[LangchainDocument], chunk_size: int = 1000, chunk_overlap: int = 100) -> \
        List[LangchainDocument]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
        strip_whitespace=True,
        separators=MARKDOWN_SEPARATORS,
    )
    return [chunk for doc in raw_knowledge_base for chunk in text_splitter.split_documents([doc])]


def plot_distribution(lengths: List[int], title: str):
    pd.Series(lengths).hist()
    plt.title(title)
    plt.show()


def show_1(raw_knowledge_base: List[LangchainDocument]):
    docs_processed = process_documents(raw_knowledge_base)
    print(f"Model's maximum sequence length: {SentenceTransformer(EMBEDDING_MODEL_NAME).max_seq_length}")
    tokenizer = get_tokenizer()
    lengths = [len(tokenizer.encode(doc.page_content)) for doc in tqdm(docs_processed)]
    plot_distribution(lengths, "Distribution of document lengths in the knowledge base (in count of tokens)")


def split_documents(
        chunk_size: int,
        knowledge_base: List[LangchainDocument],
        tokenizer_name: Optional[str] = EMBEDDING_MODEL_NAME,
) -> List[LangchainDocument]:
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size=chunk_size,
        chunk_overlap=int(chunk_size / 10),
        add_start_index=True,
        strip_whitespace=True,
        separators=MARKDOWN_SEPARATORS,
    )

    docs_processed = [chunk for doc in knowledge_base for chunk in text_splitter.split_documents([doc])]
    return list({doc.page_content: doc for doc in docs_processed}.values())


def split_documents_tiktoken(
        chunk_size: int,
        knowledge_base: List[LangchainDocument],
) -> List[LangchainDocument]:
    text_splitter = RecursiveCharacterTextSplitter().from_tiktoken_encoder(model_name="gpt-3.5-turbo",
                                                                           chunk_size=chunk_size,
                                                                           chunk_overlap=int(chunk_size / 10))

    docs_processed = [chunk for doc in knowledge_base for chunk in text_splitter.split_documents([doc])]
    return list({doc.page_content: doc for doc in docs_processed}.values())


def show_2(docs_processed: List[LangchainDocument]):
    tokenizer = get_tokenizer()
    lengths = [len(tokenizer.encode(doc.page_content)) for doc in tqdm(docs_processed)]
    plot_distribution(lengths, "Distribution of document lengths in the knowledge base (in count of tokens)")


if __name__ == '__main__':
    raw_knowledge_base = load_file("pdf", "../a.pdf")
    show_1(raw_knowledge_base)

    docs_processed = split_documents(
        256,
        raw_knowledge_base,
        tokenizer_name=EMBEDDING_MODEL_NAME,
    )
    show_2(docs_processed)
    docs_processed2 = split_documents_tiktoken(
        256,
        raw_knowledge_base,
    )
    show_2(docs_processed2)
