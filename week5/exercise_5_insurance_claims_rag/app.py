import gradio as gr
from dotenv import load_dotenv

from implementation.answer import answer_question

load_dotenv(override=True)


def _history_to_messages(history: list[dict]) -> list[dict]:
    return history or []


def _format_sources(chunks, max_items: int = 5) -> str:
    if not chunks:
        return "_No sources found._"
    lines = []
    for chunk in chunks[:max_items]:
        source = chunk.metadata.get("source", "unknown")
        lines.append(f"- {source}")
    return "Top sources:\n" + "\n".join(lines)


def chat(user_message: str, history: list[dict]):
    history = history or []
    messages = _history_to_messages(history)
    if user_message:
        messages = messages + [{"role": "user", "content": user_message}]
    answer, chunks = answer_question(user_message, history=messages)
    history = messages + [{"role": "assistant", "content": answer}]
    return history, _format_sources(chunks)


def main():
    with gr.Blocks(title="Insurellm Chat") as app:
        gr.Markdown("# 💬 Insurellm RAG Chat")
        gr.Markdown("Ask questions about claims policies and procedures.")

        chatbot = gr.Chatbot(height=420)
        sources = gr.Markdown("_Sources will appear here._")

        with gr.Row():
            message = gr.Textbox(
                placeholder="Ask a question...",
                show_label=False,
                scale=5,
            )
            send = gr.Button("Send", variant="primary", scale=1)

        clear = gr.Button("Clear")

        send.click(chat, inputs=[message, chatbot], outputs=[chatbot, sources])
        message.submit(chat, inputs=[message, chatbot], outputs=[chatbot, sources])
        clear.click(lambda: ([], "_Sources will appear here._"), outputs=[chatbot, sources])

    app.launch(inbrowser=True)


if __name__ == "__main__":
    main()