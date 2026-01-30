import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import gradio as gr
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

MODEL_NAME = "google/gemini-2.5-flash"
openrouter_client = None

def _build_messages(dataset_type, count, batch_index=None, total_batches=None):
    batch_hint = ""
    if batch_index is not None and total_batches is not None:
        batch_hint = (
            f" This is batch {batch_index} of {total_batches}. "
            f"Ensure diversity from other batches by using different names, locations, "
            f"categories, and value ranges than typical."
        )
    return [
        {
            "role": "system",
            "content": (
                "You are a data generation expert. Create realistic, diverse synthetic data in JSON format. "
                "Ensure records are meaningfully varied and avoid near-duplicates."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Generate {count} synthetic {dataset_type} records in JSON format.{batch_hint}"
                "Output only a JSON object with the key \"records\" whose value is an array of objects. "
                "Make each record distinct with varied values, not just small changes. "
                "Use unique identifiers where applicable. "
                "Do not include any other text or formatting."
            ),
        },
    ]


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("Failed to parse JSON from model output.")


def _generate_records(dataset_type, count, batch_index=None, total_batches=None):
    messages = _build_messages(dataset_type, count, batch_index, total_batches)

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("Missing OPENROUTER_API_KEY.")
    global openrouter_client
    if openrouter_client is None:
        openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    response = openrouter_client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.9,
        top_p=0.95,
    )
    payload = json.loads(response.choices[0].message.content)
    return payload.get("records", [])


def generate_synthetic_data(dataset_type, num_records):
    """Generate synthetic data using batching for large requests."""
    max_per_batch = 200
    remaining = num_records
    all_records = []
    batch_sizes = []

    while remaining > 0:
        batch_size = min(max_per_batch, remaining)
        batch_sizes.append(batch_size)
        remaining -= batch_size
    total_batches = len(batch_sizes)

    if len(batch_sizes) > 1:
        max_workers = min(6, len(batch_sizes))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    _generate_records,
                    dataset_type,
                    size,
                    index + 1,
                    total_batches,
                )
                for index, size in enumerate(batch_sizes)
            ]
            for future in as_completed(futures):
                all_records.extend(future.result())
    else:
        for index, size in enumerate(batch_sizes):
            batch_records = _generate_records(
                dataset_type,
                size,
                index + 1,
                total_batches,
            )
            all_records.extend(batch_records)

    return {"records": all_records}

def generate_data_gradio(dataset_type, num_records):
    """Wrapper function for Gradio interface."""
    try:
        result = generate_synthetic_data(
            dataset_type=dataset_type,
            num_records=int(num_records),
        )
        # Format JSON for better readability
        formatted_json = json.dumps(result, indent=2)
        return formatted_json, "✅ Generation successful!"
    except Exception as e:
        return "", f"❌ Error: {str(e)}"

# Define example inputs
examples = [
    [
        "employees (employee_id, first_name, last_name, email, phone, department, salary, hire_date, address, city, state, country)",
        5
    ],
    [
        "customers (customer_id, name, email, phone, registration_date, loyalty_points)",
        3
    ],
    [
        "products (product_id, name, description, price, category, stock_quantity)",
        4
    ],
]

def create_app():
    """Create and configure the Gradio app."""
    with gr.Blocks(title="Synthetic Data Generator", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
            # 🎲 Synthetic Data Generator
            Generate realistic synthetic datasets with OpenRouter (Gemini 2.5 Flash).
            Specify the data structure, and let AI create the data!
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ Configuration")

                dataset_type = gr.Textbox(
                    label="Dataset Schema",
                    value="employees (employee_id, first_name, last_name, email, department, salary)",
                    placeholder="e.g., users (id, name, email, age)",
                    lines=3,
                    info="Describe the fields you want in your dataset",
                )

                num_records = gr.Slider(
                    minimum=1,
                    maximum=500,
                    value=5,
                    step=1,
                    label="Number of Records",
                    info="How many records to generate",
                )

                generate_btn = gr.Button("🚀 Generate Data", variant="primary", size="lg")

                gr.Markdown("### 📚 Examples")
                gr.Examples(
                    examples=examples,
                    inputs=[dataset_type, num_records],
                    label="Try these examples:",
                )

            with gr.Column(scale=2):
                gr.Markdown("### 📊 Generated Data")

                status_box = gr.Textbox(
                    label="Status",
                    value="Ready to generate",
                    interactive=False,
                )

                output_json = gr.Code(
                    label="JSON Output",
                    language="json",
                    lines=20,
                    value="",
                )

                gr.Markdown(
                    """
                    ### 💡 Tips
                    - **Model**: Fixed to OpenRouter Gemini 2.5 Flash
                    - Describe your schema clearly for best results
                    - Start with fewer records for testing
                    """
                )

        # Connect the button to the function
        generate_btn.click(
            fn=generate_data_gradio,
            inputs=[dataset_type, num_records],
            outputs=[output_json, status_box],
        )

    return demo


if __name__ == "__main__":
    app = create_app()
    app.launch()
else:
    app = create_app()
