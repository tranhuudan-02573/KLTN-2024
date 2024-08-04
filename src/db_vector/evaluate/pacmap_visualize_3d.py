import matplotlib.pyplot as plt
import numpy as np
import pacmap
import pandas as pd
import plotly.express as px
import weaviate.classes as wvc
from langchain.docstore.document import Document as LangchainDocument
from weaviate.classes.query import Sort

from src.db_vector.utils import generate_embeddings
from src.db_vector.weaviate_rag import get_weaviate_client, CUSTOM_PROPERTIES


def fetch_weaviate_data(collection_name: str, query: str):
    query_embedding = generate_embeddings(query)
    docs_processed = []
    vectors = []

    with get_weaviate_client() as client:
        collection = client.collections.get(collection_name)
        response = collection.query.fetch_objects(
            offset=0,
            return_properties=CUSTOM_PROPERTIES,
            include_vector=True,
            return_metadata=wvc.query.MetadataQuery(
                certainty=True, creation_time=True,
                distance=True, score=True,
                is_consistent=True, explain_score=True
            ),
            sort=Sort.by_property(name="chunk_id", ascending=True)
            .by_property(name="source", ascending=True)
            .by_property(name="chunk_id", ascending=True)
            .by_property(name="page_label", ascending=True),
        )

        for o in response.objects:
            docs_processed.append(
                LangchainDocument(page_content=o.properties['chunks'], metadata={'source': o.properties['source']}))

            data_object = collection.query.fetch_object_by_id(
                o.uuid,
                include_vector=True
            )
            vectors.append(data_object.vector["default"])

    return docs_processed, vectors, query_embedding


def pacmap_show(collection_name: str, user_query: str):
    # Fetch data from Weaviate
    docs_processed, vectors, query_vector = fetch_weaviate_data(collection_name, user_query)

    # Add query vector to the list of vectors
    embeddings = vectors + [query_vector]

    # Initialize PaCMAP
    embedding_projector = pacmap.PaCMAP(
        n_components=2, n_neighbors=None, MN_ratio=0.5, FP_ratio=2.0, random_state=1
    )

    # Fit and transform the data
    documents_projected = embedding_projector.fit_transform(
        np.array(embeddings), init="pca"
    )

    # Create DataFrame for visualization
    df_data = [
        {
            "x": documents_projected[i, 0],
            "y": documents_projected[i, 1],
            "source": docs_processed[i].metadata["source"].split("/")[-1],
            "extract": docs_processed[i].page_content[:100] + "...",
            "symbol": "circle",
            "size_col": 4,
        }
        for i in range(len(docs_processed))
    ]
    df_data.append({
        "x": documents_projected[-1, 0],
        "y": documents_projected[-1, 1],
        "source": "User query",
        "extract": user_query,
        "size_col": 100,
        "symbol": "star",
    })
    df = pd.DataFrame(df_data)

    # Create and show the plot
    fig = px.scatter(
        df,
        x="x",
        y="y",
        color="source",
        hover_data="extract",
        size="size_col",
        symbol="symbol",
        color_discrete_map={"User query": "black"},
        width=1000,
        height=700,
    )
    fig.update_traces(
        marker=dict(opacity=1, line=dict(width=0, color="DarkSlateGrey")),
        selector=dict(mode="markers"),
    )
    fig.update_layout(
        legend_title_text="<b>Chunk source</b>",
        title="<b>2D Projection of Chunk Embeddings via PaCMAP</b>",
    )
    fig.show()


from sklearn.decomposition import PCA


def pca_3d_show(collection_name: str, user_query: str):
    # Fetch data from Weaviate
    docs_processed, vectors, query_vector = fetch_weaviate_data(collection_name, user_query)

    # Add query vector to the list of vectors
    all_vectors = vectors + [query_vector]

    # Perform PCA
    pca = PCA(n_components=3)
    vis_dims = pca.fit_transform(all_vectors)

    # Create DataFrame for visualization
    df = pd.DataFrame(vis_dims, columns=['x', 'y', 'z'])
    df['category'] = [doc.metadata["source"].split('/')[-1] for doc in docs_processed] + ['User Query']
    df['content'] = [doc.page_content[:100] + '...' for doc in docs_processed] + [user_query]

    # Create 3D plot
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Plot each category
    categories = df['category'].unique()
    cmap = plt.get_cmap("tab20")
    scatter_plots = []
    for i, cat in enumerate(categories):
        sub_df = df[df['category'] == cat]
        color = cmap(i / len(categories))
        scatter = ax.scatter(sub_df['x'], sub_df['y'], sub_df['z'], c=[color], label=cat)
        scatter_plots.append(scatter)

    # Customize the plot
    ax.set_xlabel('PCA Component 1')
    ax.set_ylabel('PCA Component 2')
    ax.set_zlabel('PCA Component 3')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.title('3D PCA Projection of Document Embeddings')

    # Add hover annotations
    annot = ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="w"),
                        arrowprops=dict(arrowstyle="->"))
    annot.set_visible(False)

    def update_annot(ind, sc):
        pos = sc.get_offsets()[ind["ind"][0]]
        annot.xy = pos
        text = df.iloc[ind["ind"][0]]['content']
        annot.set_text(text)

    def hover(event):
        if event.inaxes == ax:
            for sc in scatter_plots:
                cont, ind = sc.contains(event)
                if cont:
                    update_annot(ind, sc)
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                    return
            annot.set_visible(False)
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", hover)

    plt.tight_layout()
    plt.show()


def scatter3d_show(collection_name: str, user_query: str):
    # Fetch data from Weaviate
    docs_processed, vectors, query_vector = fetch_weaviate_data(collection_name, user_query)

    # Add query vector to the list of vectors
    all_vectors = vectors + [query_vector]

    # Perform PCA
    pca = PCA(n_components=3)
    vis_dims = pca.fit_transform(all_vectors)

    # Create DataFrame for visualization
    df = pd.DataFrame(vis_dims, columns=['x', 'y', 'z'])
    df['category'] = [doc.metadata["source"].split('/')[-1] for doc in docs_processed] + ['User Query']
    df['content'] = [doc.page_content[:100] + '...' for doc in docs_processed] + [user_query]

    # Create 3D plot
    fig = px.scatter_3d(
        df, x='x', y='y', z='z',
        color='category', hover_data=['content'],
        symbol='category', size=[10 if c == 'User Query' else 5 for c in df['category']],
        title='3D PCA Projection of Document Embeddings'
    )

    fig.update_layout(legend_title_text='<b>Chunk source</b>')
    fig.show()


# Usage
scatter3d_show("huudan", "cấu trúc ngữ pháp số 10 là gì?")
