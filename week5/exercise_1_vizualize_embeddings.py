from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import gradio as gr
import numpy as np
import plotly.graph_objects as go
from chromadb import PersistentClient
from dotenv import load_dotenv
from sklearn.manifold import TSNE


load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent
PREPROCESSED_DB = BASE_DIR / "course_content/preprocessed_db"
VECTOR_DB = BASE_DIR / "course_content/vector_db"


def select_db_path(db_choice: str) -> Path:
    if db_choice == "preprocessed_db":
        return PREPROCESSED_DB
    if db_choice == "vector_db":
        return VECTOR_DB
    # "auto"
    if PREPROCESSED_DB.exists():
        return PREPROCESSED_DB
    return VECTOR_DB


def get_collection(client: PersistentClient, collection_name: str | None) -> Any:
    collections = client.list_collections()
    if not collections:
        raise ValueError("No collections found. Run 'uv run course_content/implementation/ingest.py' first to create embeddings.")
    if collection_name:
        return client.get_or_create_collection(collection_name)
    # Default: use the first available collection
    return client.get_or_create_collection(collections[0].name)


def load_embeddings(db_path: Path, collection_name: str | None) -> tuple[np.ndarray, list, list]:
    client = PersistentClient(path=str(db_path))
    collection = get_collection(client, collection_name)
    result = collection.get(include=["embeddings", "documents", "metadatas"])
    vectors = np.array(result["embeddings"])
    documents = result["documents"] or []
    metadatas = result["metadatas"] or []
    return vectors, documents, metadatas


def make_labels(metadatas: Iterable[dict]) -> list[str]:
    labels = []
    for metadata in metadatas:
        if not metadata:
            labels.append("unknown")
        elif "type" in metadata:
            labels.append(metadata["type"])
        elif "doc_type" in metadata:
            labels.append(metadata["doc_type"])
        else:
            labels.append("unknown")
    return labels


def build_plot(
    db_choice: str,
    collection_name: str,
    dimensions: int,
    perplexity: int,
    max_points: int,
) -> tuple[go.Figure, str]:
    db_path = select_db_path(db_choice)
    vectors, documents, metadatas = load_embeddings(
        db_path, collection_name or None
    )
    if vectors.size == 0:
        raise ValueError("No embeddings found in the selected collection.")

    count = vectors.shape[0]
    sample_count = min(count, max_points)
    if sample_count < count:
        indices = np.random.RandomState(42).choice(count, sample_count, replace=False)
        vectors = vectors[indices]
        documents = [documents[i] for i in indices]
        metadatas = [metadatas[i] for i in indices]

    labels = make_labels(metadatas)
    unique_labels = sorted(set(labels))
    label_to_color = {label: idx for idx, label in enumerate(unique_labels)}
    colors = [label_to_color[label] for label in labels]

    tsne = TSNE(n_components=dimensions, random_state=42, perplexity=perplexity)
    reduced = tsne.fit_transform(vectors)

    hover_text = [
        f"Type: {label}<br>Text: {doc[:120]}..."
        for label, doc in zip(labels, documents)
    ]

    if dimensions == 3:
        fig = go.Figure(
            data=[
                go.Scatter3d(
                    x=reduced[:, 0],
                    y=reduced[:, 1],
                    z=reduced[:, 2],
                    mode="markers",
                    marker=dict(size=4, color=colors, opacity=0.85),
                    text=hover_text,
                    hoverinfo="text",
                )
            ]
        )
        fig.update_layout(
            title="3D Embedding Visualization (t-SNE)",
            scene=dict(xaxis_title="x", yaxis_title="y", zaxis_title="z"),
            height=700,
            margin=dict(r=10, b=10, l=10, t=40),
        )
    else:
        fig = go.Figure(
            data=[
                go.Scatter(
                    x=reduced[:, 0],
                    y=reduced[:, 1],
                    mode="markers",
                    marker=dict(size=6, color=colors, opacity=0.85),
                    text=hover_text,
                    hoverinfo="text",
                )
            ]
        )
        fig.update_layout(
            title="2D Embedding Visualization (t-SNE)",
            xaxis_title="x",
            yaxis_title="y",
            height=650,
            margin=dict(r=10, b=10, l=10, t=40),
        )

    summary = (
        f"Loaded {sample_count:,} embeddings from `{db_path.name}`"
        f"{' (sampled)' if sample_count < count else ''}."
    )
    return fig, summary


def main() -> None:
    with gr.Blocks(title="Embedding Visualizer") as demo:
        gr.Markdown("# 🔎 Embedding Visualizer\nVisualize your Chroma embeddings with t-SNE.")

        with gr.Row():
            with gr.Column(scale=1):
                db_choice = gr.Dropdown(
                    label="Database",
                    choices=["auto", "preprocessed_db", "vector_db"],
                    value="auto",
                )
                collection_name = gr.Textbox(
                    label="Collection name (optional)",
                    placeholder="Leave empty to auto-select the first collection",
                )
                dimensions = gr.Radio(
                    label="Dimensions",
                    choices=[2, 3],
                    value=2,
                )
                perplexity = gr.Slider(
                    label="t-SNE Perplexity",
                    minimum=5,
                    maximum=50,
                    value=30,
                    step=1,
                )
                max_points = gr.Slider(
                    label="Max points (sampling)",
                    minimum=200,
                    maximum=5000,
                    value=1500,
                    step=100,
                )
                render = gr.Button("Render Plot")
                status = gr.Markdown()
            with gr.Column(scale=2):
                plot = gr.Plot()

        render.click(
            build_plot,
            inputs=[db_choice, collection_name, dimensions, perplexity, max_points],
            outputs=[plot, status],
        )

    demo.launch(inbrowser=True)


if __name__ == "__main__":
    main()