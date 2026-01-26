"""
Exercise 1: Data Visualization

This script creates various visualizations for the Amazon product dataset,
including distributions of prices, text lengths, categories, and correlations.
"""

import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
from typing import List

# Import Item and ItemLoader if available
try:
    from pricer.items import Item
    from pricer.loaders import ItemLoader
except ImportError:
    # Fallback for different import paths
    try:
        from items import Item
        from loaders import ItemLoader
    except ImportError:
        print("Warning: Could not import Item or ItemLoader. Using sample data.")
        Item = None
        ItemLoader = None


def plot_text_length_distribution(items: List[Item], figsize=(15, 6)):
    """
    Plot the distribution of text lengths (character counts) in the dataset.
    
    Args:
        items: List of Item objects
        figsize: Figure size tuple
    """
    lengths = [len(item.full) if item.full else 0 for item in items]
    
    plt.figure(figsize=figsize)
    avg_length = sum(lengths) / len(lengths) if lengths else 0
    max_length = max(lengths) if lengths else 0
    
    plt.title(f"Text length: Avg {avg_length:,.1f} and highest {max_length:,}\n")
    plt.xlabel('Length (characters)')
    plt.ylabel('Count')
    plt.hist(lengths, rwidth=0.7, color="skyblue", bins=range(0, 4050, 50))
    plt.show()


def plot_price_distribution(items: List[Item], figsize=(15, 6)):
    """
    Plot the distribution of prices in the dataset.
    
    Args:
        items: List of Item objects
        figsize: Figure size tuple
    """
    prices = [item.price for item in items]
    
    plt.figure(figsize=figsize)
    avg_price = sum(prices) / len(prices) if prices else 0
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0
    
    plt.title(f"Prices: Avg {avg_price:,.1f} lowest {min_price:,.1f} and highest {max_price:,.1f}\n")
    plt.xlabel('Price ($)')
    plt.ylabel('Count')
    plt.hist(prices, rwidth=0.7, color="blueviolet", bins=range(0, 1000, 10))
    plt.show()


def plot_category_bar_chart(items: List[Item], figsize=(15, 6)):
    """
    Plot a bar chart showing the count of items in each category.
    
    Args:
        items: List of Item objects
        figsize: Figure size tuple
    """
    category_counts = Counter([item.category for item in items])
    
    categories = list(category_counts.keys())
    counts = [category_counts[category] for category in categories]
    
    plt.figure(figsize=figsize)
    plt.bar(categories, counts, color="goldenrod")
    plt.title('How many in each category')
    plt.xlabel('Categories')
    plt.ylabel('Count')
    plt.xticks(rotation=30, ha='right')
    
    # Add value labels on top of each bar
    for i, v in enumerate(counts):
        plt.text(i, v, f"{v:,}", ha='center', va='bottom')
    
    plt.show()


def plot_category_pie_chart(items: List[Item], figsize=(12, 10)):
    """
    Plot a donut chart (pie chart with center circle) showing category distribution.
    
    Args:
        items: List of Item objects
        figsize: Figure size tuple
    """
    category_counts = Counter([item.category for item in items])
    
    categories = list(category_counts.keys())
    counts = [category_counts[category] for category in categories]
    
    plt.figure(figsize=figsize)
    plt.pie(counts, labels=categories, autopct='%1.0f%%', startangle=90)
    
    # Add a circle at the center to create a donut chart
    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    plt.title('Categories')
    
    # Equal aspect ratio ensures that pie is drawn as a circle
    plt.axis('equal')
    
    plt.show()


def plot_price_vs_text_length(items: List[Item], figsize=(15, 8)):
    """
    Create a scatter plot showing the relationship between price and text length.
    
    Args:
        items: List of Item objects
        figsize: Figure size tuple
    """
    sizes = [len(item.full) if item.full else 0 for item in items]
    prices = [item.price for item in items]
    
    plt.figure(figsize=figsize)
    plt.scatter(sizes, prices, s=0.2, color="red")
    
    plt.xlabel('Size (characters)')
    plt.ylabel('Price ($)')
    plt.title('Is there a simple correlation with text length?')
    
    plt.show()


def plot_price_vs_weight(items: List[Item], figsize=(15, 8), xlim=(0, 400)):
    """
    Create a scatter plot showing the relationship between price and weight.
    
    Args:
        items: List of Item objects
        figsize: Figure size tuple
        xlim: Tuple for x-axis limits
    """
    ounces = [item.weight if item.weight else 0 for item in items]
    prices = [item.price for item in items]
    
    plt.figure(figsize=figsize)
    plt.scatter(ounces, prices, s=0.2, color="darkorange")
    
    plt.xlabel('Weight (ounces)')
    plt.ylabel('Price ($)')
    plt.xlim(xlim)
    plt.title('Is there a simple correlation with weight?')
    
    plt.show()


def load_sample_data():
    """
    Load sample data from the dataset.
    For this exercise, we'll try to load from a pre-existing dataset or use ItemLoader.
    
    Returns:
        List of Item objects
    """
    # Try to load from a pre-existing dataset on HuggingFace Hub
    try:
        train, val, test = Item.from_hub("ed-donner/items_raw_lite")
        # Combine all splits for visualization
        return train + val + test
    except Exception as e:
        print(f"Could not load from Hub: {e}")
        print("Trying to load from ItemLoader...")
        
        # Try loading a small dataset using ItemLoader
        try:
            loader = ItemLoader("Appliances")
            items = loader.load()
            return items
        except Exception as e2:
            print(f"Could not load from ItemLoader: {e2}")
            print("Please ensure you have data loaded or use the provided dataset.")
            return []


def main():
    """
    Main function to run all visualizations.
    """
    print("Loading data...")
    items = load_sample_data()
    
    if not items:
        print("No data available. Please load data first.")
        return
    
    print(f"Loaded {len(items):,} items")
    print("\nCreating visualizations...\n")
    
    # 1. Text length distribution
    print("1. Plotting text length distribution...")
    plot_text_length_distribution(items)
    
    # 2. Price distribution
    print("2. Plotting price distribution...")
    plot_price_distribution(items)
    
    # 3. Category bar chart
    print("3. Plotting category bar chart...")
    plot_category_bar_chart(items)
    
    # 4. Category pie chart
    print("4. Plotting category pie chart...")
    plot_category_pie_chart(items)
    
    # 5. Price vs text length scatter plot
    print("5. Plotting price vs text length correlation...")
    plot_price_vs_text_length(items)
    
    # 6. Price vs weight scatter plot
    print("6. Plotting price vs weight correlation...")
    plot_price_vs_weight(items)
    
    print("\nAll visualizations complete!")


if __name__ == "__main__":
    main()
