"""
Exercise 5: Neural Network with Bag of Words

This script implements a PyTorch neural network for price prediction using
bag-of-words features extracted from product descriptions using HashingVectorizer.

The neural network uses binary=True with the vectorizer, which creates one-hot
vectors - this is better for neural networks compared to count-based vectors.

Note: This is a sneak preview of neural networks. The course will go deeper
into how neural networks work and how to train them later.
"""

import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.model_selection import train_test_split
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

# Optional: for progress bars
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("Note: tqdm not available. Progress bars will be disabled.")
    # Create a dummy tqdm function
    def tqdm(iterable, *args, **kwargs):
        return iterable

# Optional: for saving/loading models
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("Error: PyTorch is required for this exercise. Please install it with: pip install torch")


class NeuralNetwork(nn.Module):
    """
    An 8-layer neural network for price prediction.
    
    Architecture:
    - Input: 5000 features (from HashingVectorizer)
    - Layer 1: 5000 -> 128
    - Layer 2-7: 64 -> 64 (6 hidden layers)
    - Layer 8: 64 -> 1 (output layer)
    - Activation: ReLU for all hidden layers, linear output
    """
    
    def __init__(self, input_size):
        super(NeuralNetwork, self).__init__()
        self.layer1 = nn.Linear(input_size, 128)
        self.layer2 = nn.Linear(128, 64)
        self.layer3 = nn.Linear(64, 64)
        self.layer4 = nn.Linear(64, 64)
        self.layer5 = nn.Linear(64, 64)
        self.layer6 = nn.Linear(64, 64)
        self.layer7 = nn.Linear(64, 64)
        self.layer8 = nn.Linear(64, 1)
        self.relu = nn.ReLU()

    def forward(self, x):
        """
        Forward pass through the network.
        
        Args:
            x: Input tensor of shape (batch_size, input_size)
            
        Returns:
            Output tensor of shape (batch_size, 1)
        """
        output1 = self.relu(self.layer1(x))
        output2 = self.relu(self.layer2(output1))
        output3 = self.relu(self.layer3(output2))
        output4 = self.relu(self.layer4(output3))
        output5 = self.relu(self.layer5(output4))
        output6 = self.relu(self.layer6(output5))
        output7 = self.relu(self.layer7(output6))
        output8 = self.layer8(output7)  # No activation on output layer
        return output8


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


def prepare_bag_of_words_features(train_items, n_features=5000, binary=True):
    """
    Prepare bag-of-words features from product summaries using HashingVectorizer.
    
    Note: Uses HashingVectorizer with binary=True, which creates one-hot vectors.
    This is better for neural networks compared to count-based vectors.
    
    Args:
        train_items: List of Item objects for training
        n_features: Number of features (vocabulary size)
        binary: If True, use binary (one-hot) encoding instead of counts
        
    Returns:
        Tuple of (vectorizer, X, prices) where:
            - vectorizer: Fitted HashingVectorizer
            - X: Sparse matrix of bag-of-words features
            - prices: Array of prices
    """
    # Extract prices and summaries
    prices = np.array([float(item.price) for item in train_items])
    documents = [item.summary for item in train_items]
    
    # Create bag-of-words features using HashingVectorizer
    # binary=True: Creates one-hot vectors (better for neural networks)
    # n_features=5000: Number of features in the hash space
    # stop_words='english': Remove common English stop words
    vectorizer = HashingVectorizer(n_features=n_features, stop_words='english', binary=binary)
    X = vectorizer.fit_transform(documents)
    
    print(f"Created bag-of-words features with {n_features:,} features (hash space size)")
    print(f"Number of training examples: {X.shape[0]:,}")
    print(f"Using binary encoding: {binary}")
    
    return vectorizer, X, prices


def train_neural_network(X, prices, epochs=2, batch_size=64, learning_rate=0.001, 
                         validation_split=0.01, random_state=42, device=None):
    """
    Train a neural network on bag-of-words features.
    
    Args:
        X: Sparse matrix of bag-of-words features
        prices: Array of target prices
        epochs: Number of training epochs
        batch_size: Batch size for training
        learning_rate: Learning rate for Adam optimizer
        validation_split: Fraction of data to use for validation
        random_state: Random seed for reproducibility
        device: PyTorch device (None = auto-detect)
        
    Returns:
        Trained NeuralNetwork model
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is required. Please install it with: pip install torch")
    
    # Set random seeds for reproducibility
    np.random.seed(random_state)
    torch.manual_seed(random_state)
    random.seed(random_state)
    
    # Set device (GPU if available, else CPU)
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nUsing device: {device}")
    
    # Convert data to PyTorch tensors
    X_tensor = torch.FloatTensor(X.toarray())
    y_tensor = torch.FloatTensor(prices).unsqueeze(1)
    
    # Split the data into training and validation sets
    X_train, X_val, y_train, y_val = train_test_split(
        X_tensor, y_tensor, 
        test_size=validation_split, 
        random_state=random_state
    )
    
    print(f"Training set size: {len(X_train):,}")
    print(f"Validation set size: {len(X_val):,}")
    
    # Create the data loader
    train_dataset = TensorDataset(X_train, y_train)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    # Initialize the model
    input_size = X_tensor.shape[1]
    model = NeuralNetwork(input_size)
    model = model.to(device)
    
    # Count trainable parameters
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\nNumber of trainable parameters: {trainable_params:,}")
    
    # Define loss function and optimizer
    loss_function = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    print(f"\nTraining for {epochs} epochs...")
    print("The 4 stages of training: forward pass, loss calculation, backward pass, optimize")
    
    # Training loop
    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        num_batches = 0
        
        for batch_X, batch_y in tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}"):
            # Move batch to device
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)
            
            # Zero gradients
            optimizer.zero_grad()
            
            # Forward pass: compute predictions
            outputs = model(batch_X)
            
            # Loss calculation: compute loss
            loss = loss_function(outputs, batch_y)
            
            # Backward pass: compute gradients
            loss.backward()
            
            # Optimize: update weights
            optimizer.step()
            
            epoch_loss += loss.item()
            num_batches += 1
        
        # Validation
        model.eval()
        with torch.no_grad():
            X_val_device = X_val.to(device)
            val_outputs = model(X_val_device)
            val_loss = loss_function(val_outputs, y_val.to(device))
        
        avg_train_loss = epoch_loss / num_batches if num_batches > 0 else 0.0
        print(f'Epoch [{epoch+1}/{epochs}], Train Loss: {avg_train_loss:.3f}, Val Loss: {val_loss.item():.3f}')
    
    print("Model training complete!")
    
    return model, device


def create_pricer_function(vectorizer, model, device):
    """
    Create a pricer function that uses the trained neural network to predict prices.
    
    Args:
        vectorizer: Fitted HashingVectorizer
        model: Trained NeuralNetwork model
        device: PyTorch device
        
    Returns:
        Function that takes an Item and returns a predicted price
    """
    def neural_network_pricer(item):
        """
        Predict price for an item using the neural network.
        
        Args:
            item: Item object with summary text
            
        Returns:
            Predicted price (non-negative)
        """
        model.eval()
        with torch.no_grad():
            # Transform the item's summary into bag-of-words features
            vector = vectorizer.transform([item.summary])
            vector_tensor = torch.FloatTensor(vector.toarray()).to(device)
            
            # Predict price
            result = model(vector_tensor)[0].item()
        
        # Ensure non-negative price
        return max(0, result)
    
    return neural_network_pricer


def evaluate_model(model, vectorizer, test_items, device):
    """
    Evaluate the neural network model on test data using sklearn metrics.
    
    Args:
        model: Trained NeuralNetwork model
        vectorizer: Fitted HashingVectorizer
        test_items: List of Item objects for testing
        device: PyTorch device
        
    Returns:
        Dictionary with evaluation metrics
    """
    # Prepare test data
    test_documents = [item.summary for item in test_items]
    test_prices = np.array([item.price for item in test_items])
    
    # Transform test documents
    X_test = vectorizer.transform(test_documents)
    X_test_tensor = torch.FloatTensor(X_test.toarray()).to(device)
    
    # Make predictions
    model.eval()
    with torch.no_grad():
        y_pred_tensor = model(X_test_tensor)
        y_pred = y_pred_tensor.cpu().numpy().flatten()
    
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
    print("Neural Network Model Evaluation Metrics:")
    print("="*50)
    print(f"Mean Squared Error (MSE): {mse:.2f}")
    print(f"Root Mean Squared Error (RMSE): ${rmse:.2f}")
    print(f"Mean Absolute Error (MAE): ${mae:.2f}")
    print(f"R-squared Score (R²): {r2:.4f}")
    print("="*50)
    
    return metrics


def save_model(model, filepath="neural_network.pth"):
    """
    Save the trained neural network model to disk.
    
    Args:
        model: Trained NeuralNetwork model
        filepath: Path where to save the model
    """
    torch.save(model.state_dict(), filepath)
    print(f"Model saved to {filepath}")


def load_model(filepath="neural_network.pth", input_size=5000, device=None):
    """
    Load a saved neural network model from disk.
    
    Args:
        filepath: Path to the saved model file
        input_size: Input size of the model (must match training)
        device: PyTorch device
        
    Returns:
        Loaded NeuralNetwork model
    """
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    model = NeuralNetwork(input_size)
    model.load_state_dict(torch.load(filepath, map_location=device))
    model = model.to(device)
    model.eval()
    
    return model


def main(lite_mode=True, username="ed-donner", random_seed=42, 
         n_features=5000, binary=True, epochs=2, batch_size=64, 
         learning_rate=0.001, validation_split=0.01, save_model_file=None):
    """
    Main function to run the complete neural network pipeline.
    
    Args:
        lite_mode: If True, use the lite dataset
        username: HuggingFace username for the dataset
        random_seed: Random seed for reproducibility
        n_features: Number of features for HashingVectorizer
        binary: If True, use binary encoding (one-hot vectors)
        epochs: Number of training epochs
        batch_size: Batch size for training
        learning_rate: Learning rate for Adam optimizer
        validation_split: Fraction of data to use for validation
        save_model_file: If provided, save the model to this filepath
    """
    if not TORCH_AVAILABLE:
        print("="*50)
        print("ERROR: PyTorch is not available!")
        print("="*50)
        print("Please install PyTorch with: pip install torch")
        print("="*50)
        return None
    
    # Set random seeds for reproducibility
    random.seed(random_seed)
    np.random.seed(random_seed)
    torch.manual_seed(random_seed)
    
    print("="*50)
    print("Neural Network with Bag of Words")
    print("="*50)
    print("Note: This is a sneak preview of neural networks.")
    print("The course will go deeper into how they work later.")
    print("="*50)
    
    # Load data
    print("\n1. Loading data...")
    train, val, test = load_data(lite_mode=lite_mode, username=username)
    
    # Prepare bag-of-words features
    print("\n2. Preparing bag-of-words features...")
    print("Using HashingVectorizer with binary=True (one-hot vectors)")
    vectorizer, X, prices = prepare_bag_of_words_features(
        train, 
        n_features=n_features, 
        binary=binary
    )
    
    # Train model
    print("\n3. Training neural network...")
    model, device = train_neural_network(
        X, prices,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        validation_split=validation_split,
        random_state=random_seed
    )
    
    # Evaluate using sklearn metrics
    print("\n4. Evaluating model (sklearn metrics)...")
    metrics = evaluate_model(model, vectorizer, test, device)
    
    # Create pricer function
    print("\n5. Creating pricer function...")
    pricer = create_pricer_function(vectorizer, model, device)
    
    # Evaluate using the custom evaluator (if available)
    if evaluate is not None:
        print("\n6. Evaluating model (custom evaluator)...")
        evaluate(pricer, test)
    else:
        print("\n6. Custom evaluator not available, skipping...")
    
    # Save model if requested
    if save_model_file:
        print(f"\n7. Saving model to {save_model_file}...")
        save_model(model, save_model_file)
    
    print("\n" + "="*50)
    print("Pipeline complete!")
    print("="*50)
    
    return {
        'vectorizer': vectorizer,
        'model': model,
        'device': device,
        'pricer': pricer,
        'metrics': metrics,
        'input_size': n_features
    }


if __name__ == "__main__":
    # Run with lite mode by default for faster execution
    # Set lite_mode=False to use the full dataset
    
    results = main(
        lite_mode=False, 
        username="ed-donner", 
        random_seed=42,
        n_features=5000,       # Number of features (hash space size for the word vectorizer)
        binary=True,           # Use binary encoding (one-hot vectors) - better for neural networks
        epochs=2,              # Number of training epochs (as in notebook)
        batch_size=64,         # Batch size for training
        learning_rate=0.001,   # Learning rate for Adam optimizer
        validation_split=0.01, # Fraction of data for validation
        save_model_file=None   # Set to "neural_network.pth" to save the model
    )
    
    # The results dictionary contains:
    # - 'vectorizer': The fitted HashingVectorizer (can be saved/reused)
    # - 'model': The trained NeuralNetwork model
    # - 'device': The PyTorch device used
    # - 'pricer': The pricer function ready to use
    # - 'metrics': Evaluation metrics dictionary
    # - 'input_size': The input size (needed for loading saved models)
    
    # Example: To use the saved model later:
    # model = load_model("neural_network.pth", input_size=5000)
    # pricer = create_pricer_function(results['vectorizer'], model, results['device'])
