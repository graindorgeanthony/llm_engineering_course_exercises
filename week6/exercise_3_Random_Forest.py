"""
Exercise 3: Random Forest with Bag of Words

This script implements a Random Forest model for price prediction using
bag-of-words features extracted from product descriptions using CountVectorizer.

Random Forest is an ensemble algorithm that combines multiple decision trees,
each trained on a different random subset of the data and features.
"""

import random
import numpy as np
from sklearn.ensemble import RandomForestRegressor
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

# Optional: for saving/loading models
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    print("Note: joblib not available. Model saving/loading will be disabled.")


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


def train_random_forest(X, prices, subset_size=None, n_estimators=100, random_state=42, n_jobs=4):
    """
    Train a Random Forest model on bag-of-words features.
    
    Note: Random Forest can be slow on large datasets. Using a subset is recommended
    for initial experimentation. The notebook uses 15,000 samples by default.
    
    Args:
        X: Sparse matrix of bag-of-words features
        prices: Array of target prices
        subset_size: Number of samples to use for training (None = use all)
        n_estimators: Number of trees in the forest
        random_state: Random seed for reproducibility
        n_jobs: Number of parallel jobs to run
        
    Returns:
        Trained RandomForestRegressor model
    """
    np.random.seed(random_state)
    
    # Use subset if specified (Random Forest can be slow on large datasets)
    if subset_size is not None:
        print(f"\nUsing subset of {subset_size:,} samples for training (Random Forest can be slow on large datasets)")
        X_train = X[:subset_size]
        prices_train = prices[:subset_size]
    else:
        print(f"\nUsing all {X.shape[0]:,} samples for training")
        X_train = X
        prices_train = prices
    
    print(f"Training Random Forest model with {n_estimators} trees...")
    print("This may take a while...")
    
    rf_model = RandomForestRegressor(
        n_estimators=n_estimators,
        random_state=random_state,
        n_jobs=n_jobs
    )
    
    rf_model.fit(X_train, prices_train)
    
    print("Model training complete!")
    print(f"Number of trees: {len(rf_model.estimators_)}")
    print(f"Number of features: {rf_model.n_features_in_}")
    
    return rf_model


def create_pricer_function(vectorizer, rf_model):
    """
    Create a pricer function that uses the trained Random Forest model to predict prices.
    
    Args:
        vectorizer: Fitted CountVectorizer
        rf_model: Trained RandomForestRegressor model
        
    Returns:
        Function that takes an Item and returns a predicted price
    """
    def random_forest_pricer(item):
        """
        Predict price for an item using Random Forest with bag-of-words.
        
        Args:
            item: Item object with summary text
            
        Returns:
            Predicted price (non-negative)
        """
        # Transform the item's summary into bag-of-words features
        x = vectorizer.transform([item.summary])
        
        # Predict price
        prediction = rf_model.predict(x)[0]
        
        # Ensure non-negative price
        return max(0, prediction)
    
    return random_forest_pricer


def evaluate_model(rf_model, vectorizer, test_items):
    """
    Evaluate the Random Forest model on test data using sklearn metrics.
    
    Args:
        rf_model: Trained RandomForestRegressor model
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
    y_pred = rf_model.predict(X_test)
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
    print("Random Forest Model Evaluation Metrics:")
    print("="*50)
    print(f"Mean Squared Error (MSE): {mse:.2f}")
    print(f"Root Mean Squared Error (RMSE): ${rmse:.2f}")
    print(f"Mean Absolute Error (MAE): ${mae:.2f}")
    print(f"R-squared Score (R²): {r2:.4f}")
    print("="*50)
    
    return metrics


def save_model(rf_model, filepath="random_forest.joblib"):
    """
    Save the trained Random Forest model to disk.
    
    Args:
        rf_model: Trained RandomForestRegressor model
        filepath: Path where to save the model
    """
    if not JOBLIB_AVAILABLE:
        print("Warning: joblib not available. Cannot save model.")
        return
    
    joblib.dump(rf_model, filepath)
    print(f"Model saved to {filepath}")


def load_model(filepath="random_forest.joblib"):
    """
    Load a saved Random Forest model from disk.
    
    Args:
        filepath: Path to the saved model file
        
    Returns:
        Loaded RandomForestRegressor model
    """
    if not JOBLIB_AVAILABLE:
        raise ImportError("joblib not available. Cannot load model.")
    
    return joblib.load(filepath)


def main(lite_mode=True, username="ed-donner", random_seed=42, subset_size=15000, 
         n_estimators=100, n_jobs=4, save_model_file=None):
    """
    Main function to run the complete Random Forest pipeline.
    
    Args:
        lite_mode: If True, use the lite dataset
        username: HuggingFace username for the dataset
        random_seed: Random seed for reproducibility
        subset_size: Number of training samples to use (None = use all)
        n_estimators: Number of trees in the Random Forest
        n_jobs: Number of parallel jobs for training
        save_model_file: If provided, save the model to this filepath
    """
    # Set random seeds for reproducibility
    random.seed(random_seed)
    np.random.seed(random_seed)
    
    print("="*50)
    print("Random Forest with Bag of Words")
    print("="*50)
    
    # Load data
    print("\n1. Loading data...")
    train, val, test = load_data(lite_mode=lite_mode, username=username)
    
    # Prepare bag-of-words features
    print("\n2. Preparing bag-of-words features...")
    vectorizer, X, prices = prepare_bag_of_words_features(train)
    
    # Train model
    print("\n3. Training Random Forest model...")
    rf_model = train_random_forest(
        X, prices, 
        subset_size=subset_size,
        n_estimators=n_estimators,
        random_state=random_seed,
        n_jobs=n_jobs
    )
    
    # Evaluate using sklearn metrics
    print("\n4. Evaluating model (sklearn metrics)...")
    metrics = evaluate_model(rf_model, vectorizer, test)
    
    # Create pricer function
    print("\n5. Creating pricer function...")
    pricer = create_pricer_function(vectorizer, rf_model)
    
    # Evaluate using the custom evaluator (if available)
    if evaluate is not None:
        print("\n6. Evaluating model (custom evaluator)...")
        evaluate(pricer, test)
    else:
        print("\n6. Custom evaluator not available, skipping...")
    
    # Save model if requested
    if save_model_file:
        print(f"\n7. Saving model to {save_model_file}...")
        save_model(rf_model, save_model_file)
    
    print("\n" + "="*50)
    print("Pipeline complete!")
    print("="*50)
    
    return {
        'vectorizer': vectorizer,
        'rf_model': rf_model,
        'pricer': pricer,
        'metrics': metrics
    }


if __name__ == "__main__":
    # Run with lite mode by default for faster execution
    # Set lite_mode=False to use the full dataset
    # Note: Random Forest can be slow on large datasets, so subset_size is set to 15,000 by default
    # Set subset_size=None to use all training data (will be much slower)
    
    results = main(
        lite_mode=True, 
        username="ed-donner", 
        random_seed=42,
        subset_size=15000,  # Use subset for faster training (set to None for full dataset)
        n_estimators=100,   # Number of trees in the forest
        n_jobs=4,           # Number of parallel jobs
        save_model_file=None  # Set to "random_forest.joblib" to save the model
    )
    
    # The results dictionary contains:
    # - 'vectorizer': The fitted CountVectorizer (can be saved/reused)
    # - 'rf_model': The trained RandomForestRegressor model
    # - 'pricer': The pricer function ready to use
    # - 'metrics': Evaluation metrics dictionary
    
    # Example: To use the saved model later:
    # rf_model = load_model("random_forest.joblib")
    # pricer = create_pricer_function(results['vectorizer'], rf_model)
