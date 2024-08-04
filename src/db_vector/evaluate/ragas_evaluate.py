import warnings
import os
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)
from weaviate.collections.classes.filters import Filter
import weaviate.classes as wvc
from src.db_vector.chat_model import call_llm
from src.db_vector.utils import generate_embeddings
from src.db_vector.weaviate_rag_non_tenant import get_weaviate_client, CUSTOM_PROPERTIES

warnings.filterwarnings('ignore')

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = "your-openai-key"

# Define prompt template
template = """
You are an assistant for question-answering tasks. 
Use the following pieces of retrieved context to answer the question. 
If you don't know the answer, just say that you don't know. 
Use three sentences maximum and keep the answer concise.
Question: {question} 
Context: {context} 
Answer:
"""

# Define questions and ground truths
questions = [
    "What did the president say about Justice Breyer?",
    "What did the president say about Intel's CEO?",
    "What did the president say about gun violence?"
]
ground_truths = [
    [
        "The president said that Justice Breyer has dedicated his life to serve the country and thanked him for his service."],
    ["The president said that Pat Gelsinger is ready to increase Intel's investment to $100 billion."],
    ["The president asked Congress to pass proven measures to reduce gun violence."]
]


def get_context(query, document_name):
    retrieved_docs_text = []
    query_vector = generate_embeddings(query)
    with get_weaviate_client() as client:
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
            filters=Filter.by_property("knowledge_name")
        )
        for item in response.objects:
            retrieved_docs_text.append({"content": item.properties['chunks'], "source": item.metadata})
    return retrieved_docs_text


def get_answers_and_contexts(questions, docname):
    answers = []
    contexts = []
    for query in questions:
        retrieved_contexts = get_context(query, docname)
        context_text = [item["content"] for item in retrieved_contexts]
        contexts.append(context_text)
        context_string = ' '.join(context_text)
        response = call_llm(template.format(context=context_string, question=query))
        answers.append(response.choices[0].message.content)
    return answers, contexts


def main():
    docname = "English_toeic"
    answers, contexts = get_answers_and_contexts(questions, docname)

    # Prepare data for evaluation
    data = {
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truths": ground_truths
    }

    # Convert dict to dataset
    dataset = Dataset.from_dict(data)

    # Evaluate the model
    result = evaluate(
        dataset=dataset,
        metrics=[
            context_precision,
            context_recall,
            faithfulness,
            answer_relevancy,
        ],
    )

    # Display results
    pd.set_option("display.max_colwidth", None)
    df = result.to_pandas()
    print(df)


if __name__ == "__main__":
    main()
