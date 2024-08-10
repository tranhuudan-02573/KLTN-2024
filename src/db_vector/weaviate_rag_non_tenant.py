import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from typing import List, Callable
import weaviate
import weaviate.classes as wvc
from fastapi import HTTPException
from langchain.docstore.document import Document as LangchainDocument
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, Docx2txtLoader, DirectoryLoader
from minio import Minio
from weaviate.auth import Auth
from weaviate.classes.config import Property, DataType
from weaviate.classes.query import Filter
from weaviate.classes.query import Sort
from weaviate.collections.classes.aggregate import GroupByAggregate
from weaviate.config import Timeout, AdditionalConfig
from weaviate.util import generate_uuid5

from src.config.app_config import get_settings
from src.db_vector.utils import generate_embeddings, get_recursive_token_chunk
from src.dtos.schema_out.knowledge import ChunkOut
from src.models.all_models import ChunkSchema
from src.utils.app_util import count_token
from src.utils.minio_util import delete_from_minio, delete_folder_from_minio

CUSTOM_PROPERTIES = [
    "chunks", "url", "chunk_id", "file_type",
    "knowledge_name", "file_name",
    "after_clean", "source",
    "page_label"
]

settings = get_settings()
import tempfile

from weaviate.config import ConnectionConfig

connection_config = ConnectionConfig(
    session_pool_connections=30,  # Tăng số lượng kết nối mặc định
    session_pool_maxsize=150,  # Tăng số lượng kết nối tối đa
    session_pool_max_retries=5  # Tăng số lần thử lại
)


def get_weaviate_client():
    weaviate_client = weaviate.connect_to_weaviate_cloud(
        cluster_url=settings.WEAVIATE_CLUSTER_URL,
        auth_credentials=Auth.api_key(settings.WEAVIATE_API_KEY),
        headers={
            "X-HuggingFace-Api-Key": settings.HUGGINGFACE_API_KEY,
            "X-Cohere-Api-Key": settings.COHERE_API_KEY,
            "X-OpenAI-Api-Key": settings.OPENAI_API_KEY
        },
        additional_config=AdditionalConfig(
            timeout=Timeout(init=2, query=120, insert=300),
            connection=connection_config
        ),
    )
    return weaviate_client


def create_for_user(document):
    with get_weaviate_client() as client:
        collection = client.collections.create(
            name=document,
            vector_index_config=wvc.config.Configure.VectorIndex.hnsw(
                    distance_metric=weaviate.classes.config.VectorDistances.COSINE,
                    ef_construction=128,
                    cleanup_interval_seconds=300,
                    ef=-1,
                    max_connections=32,
                    dynamic_ef_min=5,
                    dynamic_ef_max=500,
                    dynamic_ef_factor=8,
                    vector_cache_max_objects=1000000,
                    flat_search_cutoff=40000,
                    quantizer=wvc.config.Configure.VectorIndex.Quantizer.bq(
                        rescore_limit=200,
                        cache=True,
                    ),
                ),
            inverted_index_config=wvc.config.Configure.inverted_index(
                index_timestamps=True,
                index_null_state=True,
                index_property_length=True,
                bm25_k1=1.25,
                bm25_b=0.75,
            ),
            properties=[
                Property(name="chunks", data_type=DataType.TEXT, index_searchable=True),
                Property(name="page_label", data_type=DataType.TEXT),
                Property(name="url", data_type=DataType.TEXT),
                Property(name="source", data_type=DataType.TEXT, index_filterable=True),
                Property(name="chunk_id", data_type=DataType.NUMBER),
                Property(name="file_type", data_type=DataType.TEXT, index_filterable=True),
                Property(name="after_clean", data_type=DataType.TEXT),
                Property(name="knowledge_name", data_type=DataType.TEXT, index_filterable=True),
                Property(name="file_name", data_type=DataType.TEXT, index_filterable=True),
            ],
            # generative_config=wvc.config.Configure.Generative.ollama(
            #     api_endpoint="http://host.docker.internal:11434",
            #     model="llama3"
            # ),
            # generative_config=wvc.config.Configure.Generative.openai(
            #     model="gpt-3.5-turbo",
            #     max_tokens="",
            #     temperature=1,
            #     frequency_penalty=1,
            #     presence_penalty=1,
            #     top_p=1,
            # ),
            # reranker_config=wvc.config.Configure.Reranker.cohere(
            #     model="rerank-multilingual-v3.0"
            # ) ,
            reranker_config=wvc.config.Configure.Reranker.transformers(
            ),
            vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_huggingface(
                model=settings.MODEL_EMBEDDING_NAME,
                use_cache=True,
                use_gpu=False,
                wait_for_model=True,
                vectorize_collection_name=True,
            ),
        )
        return collection


compiled_patterns = [
    (re.compile(r'\n\s*\n'), '\n'),
    (re.compile(r'[ ]+'), ' '),
    (re.compile(r'\.{2,}'), '.'),
    (re.compile(r',{2,}'), ','),
    (re.compile(r'-{2,}'), '-'),
    (re.compile(r'_{2,}'), '_'),
    (re.compile(r'!{2,}'), '!'),
    (re.compile(r'\?{2,}'), '?'),
    (re.compile(r'(\d)([A-Za-z])'), r'\1 \2'),
    (re.compile(r'([A-Za-z])(\d)'), r'\1 \2'),
    (re.compile(r'[^\w\s\[\]\(\)\$\\.\n\/:#<>{},_"!@\\-\\*=\\]'), ''),
    (re.compile(r'\s+'), ' ')
]


def clean_input(input_text: str) -> str:
    text = input_text
    for pattern, replacement in compiled_patterns:
        text = pattern.sub(replacement, text)
    return unescape(text.strip())


def load_file(minio_client: Minio, file_type: str, path: str, temp_dir: str) -> List[LangchainDocument]:
    file_path = os.path.join(temp_dir, os.path.basename(path))
    minio_client.fget_object(settings.BUCKET_NAME, path, file_path)

    loaders = {
        "pdf": PyMuPDFLoader,
        "txt": TextLoader,
        "docx": Docx2txtLoader
    }

    loader_class = loaders.get(file_type)
    if not loader_class:
        raise ValueError(f"Invalid file type: {file_type}")
    if file_type == "txt":
        return TextLoader(file_path, encoding='UTF-8').load()
    else:
        return loader_class(file_path).load()


def clean_file_content(index: int, pages: int, page: LangchainDocument, file_path: str, url: str) -> LangchainDocument:
    content = page.page_content
    clean_text = clean_input(content)
    properties = {
        'source': file_path,
        'url': url,
        'page_label': f"{index + 1}/{pages}",
        'after_clean': f"{len(clean_text)}/{len(content)}",
    }
    return LangchainDocument(page_content=clean_text, metadata=properties)


def load_and_clean_file(file_type: str, file_path: str, url: str):
    minio_client = Minio(
        f"{settings.MINIO_HOST}:{settings.MINIO_PORT}",
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_ACCESS_KEY,
        secure=False,
        region=settings.REGION_NAME,
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        pages = load_file(minio_client, file_type, file_path, temp_dir)
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(clean_file_content, len(pages), index, page, file_path, url)
                for index, page in enumerate(pages)
            ]
            results = [future.result() for future in as_completed(futures)]

    return get_recursive_token_chunk(chunk_size=250).split_documents(results), len(pages)


def batch_import_knowledge_in_user(document_name: str, knowledge_name: str, file_type: str, file_path: str,
                                   url: str):
    chunks, pages = load_and_clean_file(file_type, file_path, url)
    file_name = os.path.basename(file_path)
    file_type2 = file_name.split(".")[-1]

    with get_weaviate_client() as weaviate_client:
        collection = weaviate_client.collections.get(document_name)
        data_rows = [
            {
                "chunks": chunk.page_content,
                "source": chunk.metadata.get('source'),
                "url": chunk.metadata.get('url'),
                "chunk_id": index,
                "file_type": file_type2,
                "page_label": chunk.metadata.get('page_label'),
                "after_clean": chunk.metadata.get('after_clean'),
                "knowledge_name": knowledge_name,
                "file_name": file_name
            } for index, chunk in enumerate(chunks)
        ]

        def add_object_to_batch(batch_run: Callable, data_row: dict) -> None:
            batch_run.add_object(
                properties=data_row,
                uuid=generate_uuid5(data_row),
                vector=generate_embeddings(data_row["chunks"])
            )

        with collection.batch.dynamic() as batch_run:
            with ThreadPoolExecutor() as executor:
                list(executor.map(lambda row: add_object_to_batch(batch_run, row), data_rows))

    return len(chunks), pages


def search_in_knowledge_user(document_name: str, query: str, knowledge_name: List[str]) -> List[ChunkSchema]:
    if count_token(query) > 258:
        raise HTTPException(status_code=400, detail="Query too long")

    query_vector = generate_embeddings(query)

    with get_weaviate_client() as client:
        if not client.collections.exists(document_name):
            raise HTTPException(status_code=400, detail="Document not found")

        collection = client.collections.get(document_name)

        response = collection.query.hybrid(
            query=query,
            alpha=0.8,
            limit=30,
            offset=0,
            fusion_type=wvc.query.HybridFusion.RELATIVE_SCORE,
            return_metadata=wvc.query.MetadataQuery(
                certainty=True, creation_time=True, distance=True,
                score=True, is_consistent=True, explain_score=True
            ),
            target_vector=document_name,
            vector=wvc.query.HybridVector.near_vector(query_vector, distance=0.75),
            return_properties=CUSTOM_PROPERTIES,
            query_properties=["chunks"],
            auto_limit=20,
            filters=Filter.by_property("knowledge_name").contains_any(knowledge_name),
        )

        results = [
            ChunkSchema(
                **item.properties,
                score=item.metadata.score,
                explain_score=item.metadata.explain_score,
                creation_time=item.metadata.creation_time,
                chunk_uuid=item.uuid,
                rerank_score=item.metadata.rerank_score
            )
            for item in response.objects
        ]

        return results


def get_all_chunk_in_file(doc_name, knowledge, source) -> list[ChunkOut]:
    rs = []
    print(doc_name, knowledge, source)
    with get_weaviate_client() as client:
        collection = client.collections.get(doc_name)
        response = collection.query.fetch_objects(
            offset=0,
            return_properties=CUSTOM_PROPERTIES, include_vector=True,
            return_metadata=wvc.query.MetadataQuery(certainty=True, creation_time=True,
                                                    distance=True, score=True,
                                                    is_consistent=True, explain_score=True),
            sort=Sort.by_property(name="chunk_id", ascending=True).by_property(
                name="chunk_id",
                ascending=True).by_property(
                name="page_label",
                ascending=True),
            filters=Filter.by_property("source").equal(source) & Filter.by_property("knowledge_name").equal(knowledge)
        )
        for o in response.objects:
            rs.append(ChunkOut(**o.properties))
    return rs


def delete_one_knowledge_user(document_name, key_name):
    with get_weaviate_client() as client:
        if not client.collections.exists(document_name):
            raise HTTPException(status_code=400, detail="Document not found")
        collection = client.collections.get(document_name)
        rsa = collection.data.delete_many(
            where=Filter.by_property("knowledge_name").equal(key_name),
            dry_run=True,
            verbose=True
        )
        delete_folder_from_minio(f"{document_name}/knowledge/{key_name}/")
        print(rsa)


def delete_one_file_knowledge(document_name, key_name, file):
    with get_weaviate_client() as client:
        if not client.collections.exists(document_name):
            raise HTTPException(status_code=400, detail="Document not found")
        collection = client.collections.get(document_name)
        rsa = collection.data.delete_many(
            where=Filter.by_property("knowledge_name").equal(key_name) & Filter.by_property("source").equal(file),
            dry_run=True,
            verbose=True
        )
        delete_from_minio(file)
        print(rsa)


def delete_many_knowledge_user(document_name, key_name, source):
    with get_weaviate_client() as client:
        if not client.collections.exists(document_name):
            raise HTTPException(status_code=400, detail="Document not found ")
        collection = client.collections.get(document_name)
        rsa = collection.data.delete_many(
            where=Filter.by_property("source").contains_all(source) & Filter.by_property("knowledge_name").equal(
                key_name),
            dry_run=True,
            verbose=True
        )
        for a in source:
            delete_from_minio(a)
        print(rsa)


def get_all_knowledge_in_user(doc_name):
    with get_weaviate_client() as client:
        collection = client.collections.get(doc_name)
        response = collection.query.fetch_objects(
            offset=0,
            return_properties=CUSTOM_PROPERTIES, include_vector=True,
            return_metadata=wvc.query.MetadataQuery(certainty=True, creation_time=True,
                                                    distance=True, score=True,
                                                    is_consistent=True, explain_score=True),
            sort=Sort.by_property(name="chunk_id", ascending=True).by_property(name="source",
                                                                               ascending=True).by_property(
                name="chunk_id",
                ascending=True).by_property(
                name="page_label",
                ascending=True),
        )
        for o in response.objects:
            print(o.properties)
        return response.objects


def get_all_user():
    with get_weaviate_client() as client:
        response = client.collections.list_all(simple=False)
        print(response.keys())


def aggregate_for_user(document_name):
    with get_weaviate_client() as client:
        collection = client.collections.get(document_name)
        response3 = collection.aggregate.over_all(
            group_by=GroupByAggregate(prop="source"),
            total_count=True,
            return_metrics=[
                wvc.query.Metrics("chunk_id").number(
                    count=True,
                    maximum=True,
                    mean=True,
                    median=True,
                    minimum=True,
                    mode=True,
                    sum_=True,
                ), wvc.query.Metrics("chunks").text(
                    top_occurrences_count=True,
                    top_occurrences_value=True,
                    min_occurrences=5
                )
            ]
        )
        return response3


def read_object_by_id(docname, id):
    with get_weaviate_client() as client:
        collection = client.collections.get(docname)
        if collection.data.exists(id):
            data_object = collection.query.fetch_object_by_id(
                id,
                # include_vector=True
            )
            # print(data_object)
            return data_object.properties
