"""
Vector store setup using ChromaDB for storing and retrieving product embeddings
"""
import os
import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Optional
import numpy as np
from datasets import load_dataset
from utils import BaseAgent, GREEN


class VectorStore(BaseAgent):
    """
    Manages the ChromaDB vector store for product embeddings
    """
    name = "VectorStore"
    color = GREEN
    DB_PATH = "products_vectorstore"
    COLLECTION_NAME = "products"
    
    DEFAULT_DATASET = "ed-donner/items_lite"

    def __init__(self, db_path: str = None, dataset_name: Optional[str] = None):
        """
        Initialize the vector store with ChromaDB and embedding model
        """
        self.log("Initializing VectorStore")
        self.db_path = db_path or self.DB_PATH
        self.dataset_name = dataset_name or os.getenv("RAG_DATASET_NAME", self.DEFAULT_DATASET)
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(self.COLLECTION_NAME)
        self.embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.log(f"VectorStore initialized with {self.collection.count()} items")
    
    def add_products(
        self,
        descriptions: List[str],
        prices: List[float],
        categories: List[str] = None,
        batch_size: int = 5000,
    ):
        """
        Add products to the vector store
        
        Args:
            descriptions: List of product descriptions
            prices: List of product prices
            categories: Optional list of product categories
        """
        if not descriptions:
            return
        
        self.log(f"Adding {len(descriptions)} products to vector store")
        
        total = len(descriptions)
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch_descriptions = descriptions[start:end]
            batch_prices = prices[start:end]
            batch_categories = categories[start:end] if categories else None

            # Generate embeddings for batch
            embeddings = self.embedding_model.encode(batch_descriptions)

            # Prepare metadata
            metadatas = [{"price": float(price)} for price in batch_prices]
            if batch_categories:
                for i, category in enumerate(batch_categories):
                    metadatas[i]["category"] = category

            # Generate IDs
            ids = [
                f"product_{start + i}_{hash(desc)}"
                for i, desc in enumerate(batch_descriptions)
            ]

            # Add to collection
            self.collection.add(
                embeddings=embeddings.astype(float).tolist(),
                documents=batch_descriptions,
                metadatas=metadatas,
                ids=ids,
            )

            self.log(
                f"Added batch {start + 1}-{end} of {total} "
                f"(collection size: {self.collection.count()})"
            )

        self.log(f"Successfully added products. Total count: {self.collection.count()}")

    def _build_description(self, item: dict) -> str:
        """
        Build a text description from a dataset item.
        """
        title = (item.get("title") or "").strip()
        summary = (item.get("summary") or "").strip()
        full = (item.get("full") or "").strip()
        category = (item.get("category") or "").strip()

        base = full or summary or title
        if category and base:
            return f"{title}. {base} Category: {category}."
        if title and base and title != base:
            return f"{title}. {base}"
        return base or title or "Unknown product"

    def load_full_dataset(self):
        """
        Load the full dataset from Hugging Face and index it in the vector store.
        """
        self.log(f"Loading full dataset: {self.dataset_name}")

        dataset = load_dataset(self.dataset_name)
        descriptions: List[str] = []
        prices: List[float] = []
        categories: List[str] = []

        for split_name, split in dataset.items():
            self.log(f"Processing split '{split_name}' with {len(split)} items")
            for item in split:
                description = self._build_description(item)
                price = float(item.get("price", 0.0) or 0.0)
                category = (item.get("category") or "Unknown").strip()
                if description and price > 0:
                    descriptions.append(description)
                    prices.append(price)
                    categories.append(category)

        self.add_products(descriptions, prices, categories)
        self.log(f"Full dataset loaded into vector store: {len(descriptions)} items")

    def ensure_full_dataset_loaded(self):
        """
        Ensure the vector store is populated with the full dataset.
        """
        if self.count() == 0:
            self.load_full_dataset()
    
    def search_similar(self, query: str, n_results: int = 5) -> Tuple[List[str], List[float]]:
        """
        Search for similar products in the vector store
        
        Args:
            query: Product description to search for
            n_results: Number of results to return
            
        Returns:
            Tuple of (descriptions, prices)
        """
        self.log(f"Searching for {n_results} similar products")
        
        # Generate embedding for query
        query_embedding = self.embedding_model.encode([query])
        
        # Search in collection
        results = self.collection.query(
            query_embeddings=query_embedding.astype(float).tolist(),
            n_results=n_results
        )
        
        documents = results["documents"][0] if results["documents"] else []
        prices = [m["price"] for m in results["metadatas"][0]] if results["metadatas"] else []
        
        self.log(f"Found {len(documents)} similar products")
        return documents, prices
    
    def get_all_embeddings(self, max_items: int = 2000) -> Tuple[List[str], np.ndarray, List[str]]:
        """
        Get all embeddings for visualization
        
        Args:
            max_items: Maximum number of items to retrieve
            
        Returns:
            Tuple of (documents, embeddings, categories)
        """
        self.log(f"Retrieving up to {max_items} embeddings for visualization")
        
        result = self.collection.get(
            include=["embeddings", "documents", "metadatas"],
            limit=max_items
        )
        
        documents = result["documents"]
        embeddings = np.array(result["embeddings"])
        categories = [m.get("category", "Unknown") for m in result["metadatas"]]
        
        self.log(f"Retrieved {len(documents)} embeddings")
        return documents, embeddings, categories
    
    def count(self) -> int:
        """
        Get the number of items in the collection
        """
        return self.collection.count()
