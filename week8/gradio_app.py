"""
Gradio UI for the Agentic AI Framework
"""
import gradio as gr
import logging
import queue
import threading
import time
import plotly.graph_objects as go
import numpy as np
from sklearn.manifold import TSNE
from agent_framework import AgentFramework
from utils import reformat_for_html


class QueueHandler(logging.Handler):
    """
    Custom logging handler that puts log messages in a queue
    """
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        self.log_queue.put(self.format(record))


def html_for_logs(log_data: list) -> str:
    """
    Convert log data to HTML for display
    
    Args:
        log_data: List of log messages
        
    Returns:
        HTML string
    """
    output = "<br>".join(log_data[-20:])  # Show last 20 lines
    return f"""
    <div id="scrollContent" style="height: 450px; overflow-y: auto; border: 1px solid #ccc; 
         background-color: #1a1a1a; padding: 15px; font-family: monospace; font-size: 12px;">
    {output}
    </div>
    """


def setup_logging(log_queue):
    """
    Setup logging to use the queue handler
    
    Args:
        log_queue: Queue for log messages
    """
    handler = QueueHandler(log_queue)
    formatter = logging.Formatter(
        "[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class GradioApp:
    """
    Gradio application for the Agentic AI Framework
    """
    
    def __init__(self):
        """
        Initialize the Gradio app
        """
        self.framework = None
        self.categories = [
            "Electronics",
            "Computers",
            "Smart Home",
            "Accessories",
            "Wearables",
            "Home",
        ]
        self.colors = ["red", "blue", "green", "orange", "purple", "cyan"]
    
    def get_framework(self, use_modal: bool = True) -> AgentFramework:
        """
        Get or create the framework instance
        
        Args:
            use_modal: Whether to use Modal for HF pricer
            
        Returns:
            AgentFramework instance
        """
        # Don't cache - create fresh instance based on use_modal setting
        # This ensures the Modal setting is respected
        if not self.framework or self.framework.use_modal != use_modal:
            self.framework = AgentFramework(use_modal=use_modal, test_mode=False)
            
            # Load full dataset if vector store is empty
            self.framework.vector_store.ensure_full_dataset_loaded()
        
        return self.framework
    
    def opportunities_to_table(self, opportunities: list) -> list:
        """
        Convert opportunities to table format
        
        Args:
            opportunities: List of Opportunity objects
            
        Returns:
            List of rows for dataframe
        """
        return [
            [
                opp.deal.product_description[:100] + "..." if len(opp.deal.product_description) > 100 else opp.deal.product_description,
                f"${opp.deal.price:.2f}",
                f"${opp.estimate:.2f}",
                f"${opp.discount:.2f}",
                opp.deal.url,
            ]
            for opp in opportunities
        ]
    
    def run_framework(self, log_data: list, use_modal: bool):
        """
        Run the framework and yield updates
        
        Args:
            log_data: Existing log data
            use_modal: Whether to use Modal
            
        Yields:
            Tuple of (log_data, html, table)
        """
        log_queue = queue.Queue()
        result_queue = queue.Queue()
        setup_logging(log_queue)
        
        def worker():
            """Worker thread that runs the framework"""
            try:
                framework = self.get_framework(use_modal=use_modal)
                opportunities = framework.run()
                result_queue.put(self.opportunities_to_table(opportunities))
            except Exception as e:
                logging.error(f"Error in framework: {e}")
                result_queue.put([])
        
        # Start worker thread
        thread = threading.Thread(target=worker)
        thread.start()
        
        # Initial table
        framework = self.get_framework(use_modal=use_modal)
        initial_table = self.opportunities_to_table(framework.memory)
        final_result = None
        
        # Poll for updates
        while True:
            try:
                message = log_queue.get_nowait()
                log_data.append(reformat_for_html(message))
                yield log_data, html_for_logs(log_data), final_result or initial_table
            except queue.Empty:
                try:
                    final_result = result_queue.get_nowait()
                    yield log_data, html_for_logs(log_data), final_result
                except queue.Empty:
                    if final_result is not None:
                        break
                    time.sleep(0.1)
        
        thread.join()
    
    def get_initial_plot(self) -> go.Figure:
        """
        Get initial placeholder plot
        
        Returns:
            Plotly figure
        """
        fig = go.Figure()
        fig.update_layout(
            title="Loading vector database...",
            height=500,
        )
        return fig
    
    def get_vector_plot(self, use_modal: bool) -> go.Figure:
        """
        Create 3D visualization of vector store
        
        Args:
            use_modal: Whether to use Modal
            
        Returns:
            Plotly figure
        """
        framework = self.get_framework(use_modal=use_modal)
        
        if framework.vector_store.count() == 0:
            return self.get_initial_plot()
        
        # Get embeddings
        documents, embeddings, categories = framework.vector_store.get_all_embeddings(max_items=800)
        
        if len(embeddings) == 0:
            return self.get_initial_plot()
        
        # Reduce to 3D using t-SNE
        tsne = TSNE(n_components=3, random_state=42, n_jobs=-1)
        reduced = tsne.fit_transform(embeddings)
        
        # Map categories to colors
        color_map = {cat: self.colors[i % len(self.colors)] for i, cat in enumerate(self.categories)}
        colors = [color_map.get(cat, "gray") for cat in categories]
        
        # Create 3D scatter plot
        fig = go.Figure(
            data=[
                go.Scatter3d(
                    x=reduced[:, 0],
                    y=reduced[:, 1],
                    z=reduced[:, 2],
                    mode="markers",
                    marker=dict(size=3, color=colors, opacity=0.7),
                    text=documents,
                    hovertemplate="<b>%{text}</b><extra></extra>",
                )
            ]
        )
        
        fig.update_layout(
            scene=dict(
                xaxis_title="Dimension 1",
                yaxis_title="Dimension 2",
                zaxis_title="Dimension 3",
                aspectmode="manual",
                aspectratio=dict(x=2, y=2, z=1),
                camera=dict(eye=dict(x=1.5, y=1.5, z=0.8)),
            ),
            height=500,
            margin=dict(r=5, b=5, l=5, t=30),
            title="Product Embeddings Visualization (t-SNE)",
        )
        
        return fig
    
    def handle_row_select(self, selected_index: gr.SelectData, use_modal: bool):
        """
        Handle row selection in the table
        
        Args:
            selected_index: Selected row index
            use_modal: Whether to use Modal
        """
        framework = self.get_framework(use_modal=use_modal)
        row = selected_index.index[0]
        
        if row < len(framework.memory):
            opportunity = framework.memory[row]
            framework.messenger.alert(opportunity)
    
    def load_full_dataset(self, use_modal: bool):
        """
        Load the full dataset into the vector store
        
        Args:
            use_modal: Whether to use Modal
            
        Returns:
            Status message
        """
        framework = self.get_framework(use_modal=use_modal)
        framework.vector_store.ensure_full_dataset_loaded()
        return "Loaded full dataset", self.get_vector_plot(use_modal)
    
    def get_stats(self, use_modal: bool) -> str:
        """
        Get framework statistics
        
        Args:
            use_modal: Whether to use Modal
            
        Returns:
            Stats as markdown string
        """
        framework = self.get_framework(use_modal=use_modal)
        stats = framework.get_stats()
        
        return f"""
### Framework Statistics

- **Memory Items:** {stats['memory_items']}
- **Vector Store Items:** {stats['vector_store_items']}
- **Best Discount:** ${stats['best_discount']:.2f}
- **Total Savings:** ${stats['total_savings']:.2f}
"""
    
    def create_app(self):
        """
        Create and configure the Gradio interface
        
        Args:
            share: Whether to create a public link
        """
        with gr.Blocks(title="Agentic AI Deal Finder", theme=gr.themes.Soft()) as ui:
            log_data = gr.State([])
            use_modal_state = gr.State(False)
            
            # Header
            gr.Markdown(
                """
                # 🤖 Agentic AI Deal Finder
                
                An autonomous multi-agent system that hunts for amazing deals using:
                - **Scanner Agent**: Finds deals from RSS feeds
                - **RAG Pricer**: Estimates prices using vector search + frontier model
                - **HF Pricer**: Uses fine-tuned Hugging Face model (via Modal)
                - **Planning Agent**: Coordinates workflow using LangGraph
                - **Messaging Agent**: Sends push notifications
                """
            )
            
            with gr.Row():
                with gr.Column(scale=2):
                    # Controls
                    with gr.Row():
                        run_btn = gr.Button("🚀 Run Agent Framework", variant="primary", size="lg")
                        use_modal_checkbox = gr.Checkbox(
                            label="Use Modal for HF Pricer (uncheck to use mock)",
                            value=True
                        )
                    
                    with gr.Row():
                        load_data_btn = gr.Button("📊 Load Full Dataset", size="sm")
                
                with gr.Column(scale=1):
                    stats_display = gr.Markdown("### Framework Statistics\n\nRun the framework to see stats...")
                    stats_btn = gr.Button("📈 Refresh Stats", size="sm")
            
            # Opportunities Table
            gr.Markdown("## 💰 Discovered Opportunities")
            opportunities_table = gr.Dataframe(
                headers=["Product", "Price", "Estimate", "Discount", "URL"],
                wrap=True,
                column_widths=[50, 10, 10, 10, 20],
            )
            
            # Logs and Visualization
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("## 📋 Agent Logs")
                    logs_html = gr.HTML()
                
                with gr.Column(scale=1):
                    gr.Markdown("## 🎨 Vector Store Visualization")
                    plot = gr.Plot()
            
            # Event handlers
            run_btn.click(
                fn=self.run_framework,
                inputs=[log_data, use_modal_checkbox],
                outputs=[log_data, logs_html, opportunities_table],
            )
            
            load_data_btn.click(
                fn=self.load_full_dataset,
                inputs=[use_modal_checkbox],
                outputs=[gr.Textbox(label="Status", visible=True), plot],
            )
            
            stats_btn.click(
                fn=self.get_stats,
                inputs=[use_modal_checkbox],
                outputs=[stats_display],
            )
            
            opportunities_table.select(
                fn=self.handle_row_select,
                inputs=[use_modal_checkbox],
            )
            
            # Load initial data (use Modal by default)
            ui.load(
                fn=lambda: (self.get_vector_plot(True), self.get_stats(True)),
                outputs=[plot, stats_display],
            )
        
        return ui

    def launch(self):
        """
        Launch the Gradio interface
        
        Args:
            share: Whether to create a public link
        """
        ui = self.create_app()
        ui.launch()


if __name__ == "__main__":
    app = GradioApp()
    app.launch()
else:
    app = GradioApp()