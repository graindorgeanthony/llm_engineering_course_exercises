"""
Evaluator for freight rate prediction models.

Adapted from pricer/evaluator.py to work with FreightBooking objects.
Provides evaluation metrics, visualization, and comparison tools.
"""

import re
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from itertools import accumulate
import math
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
COLOR_MAP = {"red": RED, "orange": YELLOW, "green": GREEN}

WORKERS = 5
DEFAULT_SIZE = 200


class FreightTester:
    """
    Test and evaluate freight rate prediction models.
    
    Similar to the Tester class from pricer/evaluator.py but adapted for
    freight bookings.
    """
    
    def __init__(self, predictor, data, title=None, size=DEFAULT_SIZE, workers=WORKERS):
        """
        Initialize the tester.
        
        Args:
            predictor: Function that takes a data item and returns a price prediction
            data: List of data items (dataset with 'prompt' field or FreightBooking objects)
            title: Optional title for the evaluation
            size: Number of items to evaluate
            workers: Number of parallel workers for evaluation
        """
        self.predictor = predictor
        self.data = data
        self.title = title or self.make_title(predictor)
        self.size = min(size, len(data))  # Don't exceed available data
        self.route_descriptions = []
        self.guesses = []
        self.truths = []
        self.errors = []
        self.colors = []
        self.workers = workers

    @staticmethod
    def make_title(predictor) -> str:
        """Generate a title from the predictor function name."""
        return predictor.__name__.replace("__", ".").replace("_", " ").title().replace("Gpt", "GPT")

    @staticmethod
    def post_process(value):
        """
        Extract a numeric price from model output.
        
        Handles various formats like "$1,234.56", "1234.56 USD", etc.
        
        Args:
            value: Raw model output (string or number)
            
        Returns:
            Float price value
        """
        if isinstance(value, str):
            # Remove currency symbols and commas
            value = value.replace("$", "").replace(",", "").replace("€", "").replace("¥", "")
            # Extract first number found
            match = re.search(r"[-+]?\d*\.\d+|\d+", value)
            return float(match.group()) if match else 0
        else:
            return float(value)

    def color_for(self, error, truth):
        """
        Determine color based on error magnitude.
        
        Green: < $1000 or < 20% error
        Orange: < $3000 or < 40% error  
        Red: >= $3000 or >= 40% error
        
        Args:
            error: Absolute error
            truth: Actual price
            
        Returns:
            Color string: "green", "orange", or "red"
        """
        percentage_error = error / truth if truth > 0 else 1.0
        
        if error < 1000 or percentage_error < 0.2:
            return "green"
        elif error < 3000 or percentage_error < 0.4:
            return "orange"
        else:
            return "red"

    def run_datapoint(self, i):
        """
        Evaluate a single data point.
        
        Args:
            i: Index of the data point
            
        Returns:
            Tuple of (route_desc, guess, truth, error, color)
        """
        datapoint = self.data[i]
        
        # Get prediction
        value = self.predictor(datapoint)
        guess = self.post_process(value)
        
        # Get actual price
        # Handle both dataset dict format and FreightBooking objects
        if hasattr(datapoint, 'price'):
            truth = datapoint.price
            route_desc = f"{datapoint.pol}→{datapoint.pod}"
        elif isinstance(datapoint, dict):
            # Extract price from completion string
            completion = datapoint.get('completion', '0')
            truth = self.post_process(completion)
            # Create route description from prompt
            prompt = datapoint.get('prompt', '')
            route_match = re.search(r'Route: (\w+) to (\w+)', prompt)
            if route_match:
                route_desc = f"{route_match.group(1)}→{route_match.group(2)}"
            else:
                route_desc = f"Route {i+1}"
        else:
            truth = 0
            route_desc = f"Unknown {i+1}"
        
        error = abs(guess - truth)
        color = self.color_for(error, truth)
        
        # Truncate route description if too long
        if len(route_desc) > 40:
            route_desc = route_desc[:40] + "..."
        
        return route_desc, guess, truth, error, color

    def chart(self, title):
        """
        Create scatter plot of predicted vs actual prices.
        
        Args:
            title: Chart title
        """
        df = pd.DataFrame(
            {
                "truth": self.truths,
                "guess": self.guesses,
                "route": self.route_descriptions,
                "error": self.errors,
                "color": self.colors,
            }
        )

        # Pre-format hover text
        df["hover"] = [
            f"{r}\nPredicted=${g:,.2f} Actual=${t:,.2f}"
            for r, g, t in zip(df["route"], df["guess"], df["truth"])
        ]

        max_val = float(max(df["truth"].max(), df["guess"].max()))

        fig = px.scatter(
            df,
            x="truth",
            y="guess",
            color="color",
            color_discrete_map={"green": "green", "orange": "orange", "red": "red"},
            title=title,
            labels={"truth": "Actual Freight Rate ($)", "guess": "Predicted Freight Rate ($)"},
            width=1000,
            height=800,
        )

        # Assign customdata per trace (one color/category = one trace)
        for tr in fig.data:
            mask = df["color"] == tr.name
            tr.customdata = df.loc[mask, ["hover"]].to_numpy()
            tr.hovertemplate = "%{customdata[0]}<extra></extra>"
            tr.marker.update(size=6)

        # Reference line y=x (perfect prediction)
        fig.add_trace(
            go.Scatter(
                x=[0, max_val],
                y=[0, max_val],
                mode="lines",
                line=dict(width=2, dash="dash", color="deepskyblue"),
                name="Perfect Prediction",
                hoverinfo="skip",
                showlegend=False,
            )
        )

        fig.update_xaxes(range=[0, max_val])
        fig.update_yaxes(range=[0, max_val])
        fig.update_layout(showlegend=False)
        fig.show()

    def error_trend_chart(self):
        """
        Create cumulative error trend chart showing convergence.
        """
        n = len(self.errors)

        # Running mean and std (pure Python)
        running_sums = list(accumulate(self.errors))
        x = list(range(1, n + 1))
        running_means = [s / i for s, i in zip(running_sums, x)]

        running_squares = list(accumulate(e * e for e in self.errors))
        running_stds = [
            math.sqrt((sq_sum / i) - (mean**2)) if i > 1 else 0
            for i, sq_sum, mean in zip(x, running_squares, running_means)
        ]

        # 95% confidence interval for mean
        ci = [1.96 * (sd / math.sqrt(i)) if i > 1 else 0 for i, sd in zip(x, running_stds)]
        upper = [m + c for m, c in zip(running_means, ci)]
        lower = [m - c for m, c in zip(running_means, ci)]

        # Plot
        fig = go.Figure()

        # Shaded confidence interval band
        fig.add_trace(
            go.Scatter(
                x=x + x[::-1],
                y=upper + lower[::-1],
                fill="toself",
                fillcolor="rgba(128,128,128,0.2)",
                line=dict(color="rgba(255,255,255,0)"),
                hoverinfo="skip",
                showlegend=False,
                name="95% CI",
            )
        )

        # Main line with hover text showing CI
        fig.add_trace(
            go.Scatter(
                x=x,
                y=running_means,
                mode="lines",
                line=dict(width=3, color="firebrick"),
                name="Cumulative Avg Error",
                customdata=list(
                    zip(
                        ci,
                    )
                ),
                hovertemplate=(
                    "n=%{x}<br>"
                    "Avg Error=$%{y:,.2f}<br>"
                    "±95% CI=$%{customdata[0]:,.2f}<extra></extra>"
                ),
            )
        )

        # Title with final stats
        final_mean = running_means[-1]
        final_ci = ci[-1]
        title = f"{self.title} - Cumulative Error: ${final_mean:,.2f} ± ${final_ci:,.2f}"

        fig.update_layout(
            title=title,
            xaxis_title="Number of Predictions",
            yaxis_title="Average Absolute Error ($)",
            width=1000,
            height=360,
            template="plotly_white",
            showlegend=False,
        )

        fig.show()

    def report(self):
        """Generate and display evaluation report with metrics and charts."""
        average_error = sum(self.errors) / self.size
        mse = mean_squared_error(self.truths, self.guesses)
        r2 = r2_score(self.truths, self.guesses) * 100
        
        # Calculate MAPE (Mean Absolute Percentage Error)
        mape = sum([abs(g - t) / t for g, t in zip(self.guesses, self.truths) if t > 0]) / len(self.truths) * 100
        
        print("\n" + "="*60)
        print(f"📊 {self.title} - Evaluation Results")
        print("="*60)
        print(f"Mean Absolute Error (MAE): ${average_error:,.2f}")
        print(f"Mean Squared Error (MSE): ${mse:,.0f}")
        print(f"R² Score: {r2:.1f}%")
        print(f"Mean Absolute Percentage Error (MAPE): {mape:.1f}%")
        print("="*60)
        
        title = f"{self.title}<br><b>MAE:</b> ${average_error:,.2f} | <b>MSE:</b> {mse:,.0f} | <b>R²:</b> {r2:.1f}% | <b>MAPE:</b> {mape:.1f}%"
        self.error_trend_chart()
        self.chart(title)

    def run(self):
        """Run the evaluation with progress tracking."""
        print(f"\nEvaluating {self.title} on {self.size} bookings...")
        print("Color guide: 🟢 Green=Good (<20% error), 🟡 Orange=OK (<40% error), 🔴 Red=Poor (>=40% error)\n")
        
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            for route_desc, guess, truth, error, color in tqdm(
                ex.map(self.run_datapoint, range(self.size)), 
                total=self.size,
                desc="Processing"
            ):
                self.route_descriptions.append(route_desc)
                self.guesses.append(guess)
                self.truths.append(truth)
                self.errors.append(error)
                self.colors.append(color)
                # Print colored error feedback
                # print(f"{COLOR_MAP[color]}${error:.0f} ", end="")
        
        self.report()


def evaluate(function, data, size=DEFAULT_SIZE, workers=WORKERS):
    """
    Evaluate a freight rate prediction function.
    
    Args:
        function: Prediction function that takes a data item and returns a price
        data: List of test data items
        size: Number of items to evaluate (default: 200)
        workers: Number of parallel workers (default: 5)
    """
    FreightTester(function, data, size=size, workers=workers).run()
