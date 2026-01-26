"""
Exercise 2: Linear Regression with Bag of Words

This script implements a linear regression model for price prediction using
bag-of-words features extracted from product descriptions using CountVectorizer.
"""

import random
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import mean_squared_error, r2_score

# Import Item and evaluator if available
try:
    from pricer.items import Item
    from pricer.evaluator import evaluate
except ImportError:
    # Fallback for different import paths
    try:
        from items import Item
        from evaluator import evaluate
    except ImportError:
        print("Warning: Could not import Item or evaluate. Some functionality may be limited.")
        Item = None
        evaluate = None


def load_data(lite_mode=False, username="ed-donner"):
    """
    Load the dataset from HuggingFace Hub.
    
    Args:
        lite_mode: If True, use the lite dataset, otherwise use full dataset
        username: HuggingFace username for the dataset
        
    Returns:
        Tuple of (train, val, test) lists of Item objects
    """
    dataset = f"{username}/items_lite" if lite_mode else f"{username}/items_full"
    
    if Item is None:
        raise ImportError("Item class not available. Cannot load data.")
    
    train, val, test = Item.from_hub(dataset)
    
    print(f"Loaded {len(train):,} training items, {len(val):,} validation items, {len(test):,} test items")
    
    return train, val, test


def prepare_bag_of_words_features(train_items):
    """
    Prepare bag-of-words features from product summaries using CountVectorizer.
    
    Args:
        train_items: List of Item objects for training
        
    Returns:
        Tuple of (vectorizer, X, prices) where:
            - vectorizer: Fitted CountVectorizer
            - X: Sparse matrix of bag-of-words features
            - prices: Array of prices
    """
    # Extract prices and summaries
    prices = np.array([float(item.price) for item in train_items])
    documents = [item.summary for item in train_items]
    
    # Create bag-of-words features using CountVectorizer
    # max_features=2000: Use top 2000 most frequent words
    # stop_words='english': Remove common English stop words
    vectorizer = CountVectorizer(max_features=2000, stop_words='english')
    X = vectorizer.fit_transform(documents)
    
    print(f"Created bag-of-words features with {X.shape[1]:,} features (vocabulary size)")
    print(f"Number of training examples: {X.shape[0]:,}")
    
    # Show some example words from the vocabulary
    selected_words = vectorizer.get_feature_names_out()
    print(f"\nSample words from vocabulary: {selected_words[1000:1020]}")
    
    return vectorizer, X, prices


def train_linear_regression(X, prices, random_seed=42):
    """
    Train a linear regression model on bag-of-words features.
    
    Args:
        X: Sparse matrix of bag-of-words features
        prices: Array of target prices
        random_seed: Random seed for reproducibility
        
    Returns:
        Trained LinearRegression model
    """
    np.random.seed(random_seed)
    
    print("\nTraining Linear Regression model...")
    regressor = LinearRegression()
    regressor.fit(X, prices)
    
    print("Model training complete!")
    print(f"Model coefficients shape: {regressor.coef_.shape}")
    print(f"Model intercept: {regressor.intercept_:.2f}")
    
    return regressor


def create_pricer_function(vectorizer, regressor):
    """
    Create a pricer function that uses the trained model to predict prices.
    
    Args:
        vectorizer: Fitted CountVectorizer
        regressor: Trained LinearRegression model
        
    Returns:
        Function that takes an Item and returns a predicted price
    """
    def natural_language_linear_regression_pricer(item):
        """
        Predict price for an item using bag-of-words linear regression.
        
        Args:
            item: Item object with summary text
            
        Returns:
            Predicted price (non-negative)
        """
        # Transform the item's summary into bag-of-words features
        x = vectorizer.transform([item.summary])
        
        # Predict price
        prediction = regressor.predict(x)[0]
        
        # Ensure non-negative price
        return max(prediction, 0)
    
    return natural_language_linear_regression_pricer


def evaluate_model(regressor, vectorizer, test_items):
    """
    Evaluate the model on test data using sklearn metrics.
    
    Args:
        regressor: Trained LinearRegression model
        vectorizer: Fitted CountVectorizer
        test_items: List of Item objects for testing
        
    Returns:
        Dictionary with evaluation metrics
    """
    # Prepare test data
    test_documents = [item.summary for item in test_items]
    test_prices = np.array([item.price for item in test_items])
    
    # Transform test documents
    X_test = vectorizer.transform(test_documents)
    
    # Make predictions
    y_pred = regressor.predict(X_test)
    y_pred = np.maximum(y_pred, 0)  # Ensure non-negative
    
    # Calculate metrics
    mse = mean_squared_error(test_prices, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(test_prices, y_pred)
    
    # Calculate mean absolute error
    mae = np.mean(np.abs(test_prices - y_pred))
    
    metrics = {
        'MSE': mse,
        'RMSE': rmse,
        'MAE': mae,
        'R²': r2
    }
    
    print("\n" + "="*50)
    print("Model Evaluation Metrics:")
    print("="*50)
    print(f"Mean Squared Error (MSE): {mse:.2f}")
    print(f"Root Mean Squared Error (RMSE): ${rmse:.2f}")
    print(f"Mean Absolute Error (MAE): ${mae:.2f}")
    print(f"R-squared Score (R²): {r2:.4f}")
    print("="*50)
    
    return metrics


def main(lite_mode=True, username="ed-donner", random_seed=42):
    """
    Main function to run the complete linear regression pipeline.
    
    Args:
        lite_mode: If True, use the lite dataset
        username: HuggingFace username for the dataset
        random_seed: Random seed for reproducibility
    """
    # Set random seeds for reproducibility
    random.seed(random_seed)
    np.random.seed(random_seed)
    
    print("="*50)
    print("Linear Regression with Bag of Words")
    print("="*50)
    
    # Load data
    print("\n1. Loading data...")
    train, val, test = load_data(lite_mode=lite_mode, username=username)
    
    # Prepare bag-of-words features
    print("\n2. Preparing bag-of-words features...")
    vectorizer, X, prices = prepare_bag_of_words_features(train)
    
    # Train model
    print("\n3. Training model...")
    regressor = train_linear_regression(X, prices, random_seed=random_seed)
    
    # Evaluate using sklearn metrics
    print("\n4. Evaluating model (sklearn metrics)...")
    metrics = evaluate_model(regressor, vectorizer, test)
    
    # Create pricer function
    print("\n5. Creating pricer function...")
    pricer = create_pricer_function(vectorizer, regressor)
    
    # Evaluate using the custom evaluator (if available)
    if evaluate is not None:
        print("\n6. Evaluating model (custom evaluator)...")
        evaluate(pricer, test)
    else:
        print("\n6. Custom evaluator not available, skipping...")
    
    print("\n" + "="*50)
    print("Pipeline complete!")
    print("="*50)
    
    return {
        'vectorizer': vectorizer,
        'regressor': regressor,
        'pricer': pricer,
        'metrics': metrics
    }


if __name__ == "__main__":
    # Run with lite mode by default for faster execution
    # Set lite_mode=False to use the full dataset
    results = main(lite_mode=True, username="ed-donner", random_seed=42)
    
    # The results dictionary contains:
    # - 'vectorizer': The fitted CountVectorizer (can be saved/reused)
    # - 'regressor': The trained LinearRegression model
    # - 'pricer': The pricer function ready to use
    # - 'metrics': Evaluation metrics dictionary
