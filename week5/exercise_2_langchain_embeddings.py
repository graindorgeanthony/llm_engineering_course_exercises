from __future__ import annotations

import os
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage, convert_to_messages
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


load_dotenv(override=True)

MODEL = "gpt-4.1-nano"
BASE_DIR = Path(__file__).resolve().parent
DB_NAME = BASE_DIR / "course_content/vector_db"
RETRIEVAL_K = 10

SYSTEM_PROMPT = """
You are a knowledgeable, friendly assistant representing the company Insurellm.
You are chatting with a user about Insurellm.
If relevant, use the given context to answer any question.
If you don't know the answer, say so.
Context:
{context}
"""

embeddings = OpenAIEmbeddings(
    base_url="https://openrouter.ai/api/v1",
    model="text-embedding-3-large",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)
vectorstore = Chroma(persist_directory=str(DB_NAME), embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVAL_K})
llm = ChatOpenAI(base_url="https://openrouter.ai/api/v1", temperature=0, model=MODEL, api_key=os.getenv("OPENROUTER_API_KEY"))


def normalize_content(content: object) -> str:
    """Normalize Gradio message content into a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, (list, tuple)):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                if isinstance(part.get("text"), str):
                    parts.append(part["text"])
                elif isinstance(part.get("content"), str):
                    parts.append(part["content"])
                else:
                    parts.append(str(part))
            else:
                parts.append(str(part))
        return " ".join(piece for piece in parts if piece)
    return str(content)


def normalize_history(history: list[dict] | None) -> list[dict]:
    """Normalize message history to ensure string content."""
    if not history:
        return []
    normalized: list[dict] = []
    for message in history:
        if not isinstance(message, dict):
            normalized.append({"role": "user", "content": normalize_content(message)})
            continue
        normalized.append(
            {
                "role": message.get("role", "user"),
                "content": normalize_content(message.get("content", "")),
            }
        )
    return normalized


def fetch_context(question: str) -> list[Document]:
    """Retrieve relevant context documents for a question."""
    return retriever.invoke(question)


def combined_question(question: str, history: list[dict] | None = None) -> str:
    """Combine all the user's messages into a single string for retrieval."""
    normalized_history = normalize_history(history)
    if not normalized_history:
        return question
    prior = "\n".join(
        m["content"] for m in normalized_history if m.get("role") == "user"
    )
    return f"{prior}\n{question}"


def answer_question(
    question: str, history: list[dict] | None = None
) -> tuple[str, list[Document]]:
    """Answer the given question with RAG; return the answer and context docs."""
    normalized_history = normalize_history(history)
    normalized_question = normalize_content(question)
    combined = combined_question(normalized_question, normalized_history)
    docs = fetch_context(combined)
    context = "\n\n".join(doc.page_content for doc in docs)
    system_prompt = SYSTEM_PROMPT.format(context=context)
    messages = [SystemMessage(content=system_prompt)]
    if normalized_history:
        messages.extend(convert_to_messages(normalized_history))
    messages.append(HumanMessage(content=normalized_question))
    response = llm.invoke(messages)
    return response.content, docs


def format_context(context: list[Document]) -> str:
    result = "<h2 style='color: #ff7800;'>Relevant Context</h2>\n\n"
    for doc in context:
        source = doc.metadata.get("source", "unknown")
        result += f"<span style='color: #ff7800;'>Source: {source}</span>\n\n"
        result += doc.page_content + "\n\n"
    return result


def chat(history: list[dict]) -> tuple[list[dict], str]:
    last_message = normalize_content(history[-1]["content"])
    prior = history[:-1]
    answer, context = answer_question(last_message, prior)
    history.append({"role": "assistant", "content": answer})
    return history, format_context(context)


def main() -> None:
    def put_message_in_chatbot(message: str, history: list[dict]) -> tuple[str, list[dict]]:
        return "", history + [{"role": "user", "content": message}]

    theme = gr.themes.Soft(font=["Inter", "system-ui", "sans-serif"])

    with gr.Blocks(title="Insurellm Expert Assistant", theme=theme) as ui:
        gr.Markdown("# 🏢 Insurellm Expert Assistant\nAsk me anything about Insurellm!")

        with gr.Row():
            with gr.Column(scale=1):
                chatbot = gr.Chatbot(
                    label="💬 Conversation",
                    height=600,
                )
                message = gr.Textbox(
                    label="Your Question",
                    placeholder="Ask anything about Insurellm...",
                    show_label=False,
                )

            with gr.Column(scale=1):
                context_markdown = gr.Markdown(
                    label="📚 Retrieved Context",
                    value="*Retrieved context will appear here*",
                    container=True,
                    height=600,
                )

        message.submit(
            put_message_in_chatbot,
            inputs=[message, chatbot],
            outputs=[message, chatbot],
        ).then(chat, inputs=chatbot, outputs=[chatbot, context_markdown])

    ui.launch(inbrowser=True)


if __name__ == "__main__":
    main()
