"""
Exercise 4: XGBoost with Bag of Words

This script implements an XGBoost model for price prediction using
bag-of-words features extracted from product descriptions using CountVectorizer.

XGBoost is an ensemble algorithm that combines multiple decision trees,
building one tree after another, with each next tree correcting for errors
in the prior trees using gradient descent. It's faster than Random Forest
and typically better at generalizing.

Note: If XGBoost import fails, you may need to install it:
    pip install xgboost

On Mac, you might also need to run:
    brew install libomp
"""

import random
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import mean_squared_error, r2_score

# Import XGBoost
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("Warning: xgboost not available. Please install it with: pip install xgboost")
    print("On Mac, you may also need to run: brew install libomp")
    xgb = None

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


def train_xgboost(X, prices, n_estimators=1000, learning_rate=0.1, random_state=42, n_jobs=4):
    """
    Train an XGBoost model on bag-of-words features.
    
    Note: Unlike Random Forest, XGBoost is fast enough to train on the full dataset.
    The notebook uses the full dataset with 1000 estimators.
    
    Args:
        X: Sparse matrix of bag-of-words features
        prices: Array of target prices
        n_estimators: Number of boosting rounds (trees)
        learning_rate: Step size shrinkage used in update to prevent overfitting
        random_state: Random seed for reproducibility
        n_jobs: Number of parallel threads to run
        
    Returns:
        Trained XGBRegressor model
    """
    if not XGBOOST_AVAILABLE:
        raise ImportError("XGBoost is not available. Please install it first.")
    
    np.random.seed(random_state)
    
    print(f"\nTraining XGBoost model with {n_estimators} estimators...")
    print("XGBoost is faster than Random Forest, so we can use the full dataset.")
    print("This may still take a while depending on dataset size...")
    
    xgb_model = xgb.XGBRegressor(
        n_estimators=n_estimators,
        random_state=random_state,
        n_jobs=n_jobs,
        learning_rate=learning_rate
    )
    
    xgb_model.fit(X, prices)
    
    print("Model training complete!")
    print(f"Number of boosting rounds: {n_estimators}")
    print(f"Learning rate: {learning_rate}")
    
    return xgb_model


def create_pricer_function(vectorizer, xgb_model):
    """
    Create a pricer function that uses the trained XGBoost model to predict prices.
    
    Args:
        vectorizer: Fitted CountVectorizer
        xgb_model: Trained XGBRegressor model
        
    Returns:
        Function that takes an Item and returns a predicted price
    """
    def xgboost_pricer(item):
        """
        Predict price for an item using XGBoost with bag-of-words.
        
        Args:
            item: Item object with summary text
            
        Returns:
            Predicted price (non-negative)
        """
        # Transform the item's summary into bag-of-words features
        x = vectorizer.transform([item.summary])
        
        # Predict price
        prediction = xgb_model.predict(x)[0]
        
        # Ensure non-negative price
        return max(0, prediction)
    
    return xgboost_pricer


def evaluate_model(xgb_model, vectorizer, test_items):
    """
    Evaluate the XGBoost model on test data using sklearn metrics.
    
    Args:
        xgb_model: Trained XGBRegressor model
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
    y_pred = xgb_model.predict(X_test)
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
    print("XGBoost Model Evaluation Metrics:")
    print("="*50)
    print(f"Mean Squared Error (MSE): {mse:.2f}")
    print(f"Root Mean Squared Error (RMSE): ${rmse:.2f}")
    print(f"Mean Absolute Error (MAE): ${mae:.2f}")
    print(f"R-squared Score (R²): {r2:.4f}")
    print("="*50)
    
    return metrics


def save_model(xgb_model, filepath="xgboost_model.joblib"):
    """
    Save the trained XGBoost model to disk.
    
    Args:
        xgb_model: Trained XGBRegressor model
        filepath: Path where to save the model
    """
    if not JOBLIB_AVAILABLE:
        print("Warning: joblib not available. Cannot save model.")
        return
    
    joblib.dump(xgb_model, filepath)
    print(f"Model saved to {filepath}")


def load_model(filepath="xgboost_model.joblib"):
    """
    Load a saved XGBoost model from disk.
    
    Args:
        filepath: Path to the saved model file
        
    Returns:
        Loaded XGBRegressor model
    """
    if not JOBLIB_AVAILABLE:
        raise ImportError("joblib not available. Cannot load model.")
    
    return joblib.load(filepath)


def main(lite_mode=True, username="ed-donner", random_seed=42, 
         n_estimators=1000, learning_rate=0.1, n_jobs=4, save_model_file=None):
    """
    Main function to run the complete XGBoost pipeline.
    
    Args:
        lite_mode: If True, use the lite dataset
        username: HuggingFace username for the dataset
        random_seed: Random seed for reproducibility
        n_estimators: Number of boosting rounds (trees)
        learning_rate: Step size shrinkage used in update
        n_jobs: Number of parallel threads for training
        save_model_file: If provided, save the model to this filepath
    """
    if not XGBOOST_AVAILABLE:
        print("="*50)
        print("ERROR: XGBoost is not available!")
        print("="*50)
        print("Please install XGBoost with: pip install xgboost")
        print("On Mac, you may also need to run: brew install libomp")
        print("="*50)
        return None
    
    # Set random seeds for reproducibility
    random.seed(random_seed)
    np.random.seed(random_seed)
    
    print("="*50)
    print("XGBoost with Bag of Words")
    print("="*50)
    
    # Load data
    print("\n1. Loading data...")
    train, val, test = load_data(lite_mode=lite_mode, username=username)
    
    # Prepare bag-of-words features
    print("\n2. Preparing bag-of-words features...")
    vectorizer, X, prices = prepare_bag_of_words_features(train)
    
    # Train model
    print("\n3. Training XGBoost model...")
    xgb_model = train_xgboost(
        X, prices,
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        random_state=random_seed,
        n_jobs=n_jobs
    )
    
    # Evaluate using sklearn metrics
    print("\n4. Evaluating model (sklearn metrics)...")
    metrics = evaluate_model(xgb_model, vectorizer, test)
    
    # Create pricer function
    print("\n5. Creating pricer function...")
    pricer = create_pricer_function(vectorizer, xgb_model)
    
    # Evaluate using the custom evaluator (if available)
    if evaluate is not None:
        print("\n6. Evaluating model (custom evaluator)...")
        evaluate(pricer, test)
    else:
        print("\n6. Custom evaluator not available, skipping...")
    
    # Save model if requested
    if save_model_file:
        print(f"\n7. Saving model to {save_model_file}...")
        save_model(xgb_model, save_model_file)
    
    print("\n" + "="*50)
    print("Pipeline complete!")
    print("="*50)
    
    return {
        'vectorizer': vectorizer,
        'xgb_model': xgb_model,
        'pricer': pricer,
        'metrics': metrics
    }


if __name__ == "__main__":
    # Run with lite mode by default for faster execution
    # Set lite_mode=False to use the full dataset
    # Note: XGBoost is faster than Random Forest, so we can use the full dataset
    
    results = main(
        lite_mode=False, 
        username="ed-donner", 
        random_seed=42,
        n_estimators=1000,    # Number of boosting rounds (as in notebook)
        learning_rate=0.1,   # Step size shrinkage
        n_jobs=4,            # Number of parallel threads
        save_model_file=None  # Set to "xgboost_model.joblib" to save the model
    )
    
    # The results dictionary contains:
    # - 'vectorizer': The fitted CountVectorizer (can be saved/reused)
    # - 'xgb_model': The trained XGBRegressor model
    # - 'pricer': The pricer function ready to use
    # - 'metrics': Evaluation metrics dictionary
    
    # Example: To use the saved model later:
    # xgb_model = load_model("xgboost_model.joblib")
    # pricer = create_pricer_function(results['vectorizer'], xgb_model)
