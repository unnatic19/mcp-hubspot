import os
import logging
import glob
from datetime import datetime, timedelta
import faiss
import numpy as np
import json
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger("mcp_hubspot_faiss_manager")

class FaissManager:
    """Manager for FAISS indexes that handles rolling storage by day."""
    
    def __init__(self, storage_dir: str = "/storage", max_days: int = 7):
        """Initialize the FAISS manager.
        
        Args:
            storage_dir: Directory to store FAISS index files
            max_days: Maximum number of days to keep in storage
        """
        self.storage_dir = storage_dir
        self.max_days = max_days
        self.indexes: Dict[str, faiss.Index] = {}
        self.metadata: Dict[str, List[Dict[str, Any]]] = {}
        
        # Ensure storage directory exists
        self._ensure_storage_dir()
        
        # Load existing indexes or create new ones
        self._initialize_indexes()
    
    def _ensure_storage_dir(self) -> None:
        """Create storage directory if it doesn't exist."""
        if not os.path.exists(self.storage_dir):
            logger.info(f"Creating storage directory: {self.storage_dir}")
            os.makedirs(self.storage_dir, exist_ok=True)
    
    def _get_index_path(self, date_str: str) -> str:
        """Get the path for a specific index file.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Path to the index file
        """
        return os.path.join(self.storage_dir, f"index_{date_str}.faiss")
    
    def _get_metadata_path(self, date_str: str) -> str:
        """Get the path for a specific metadata file.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Path to the metadata file
        """
        return os.path.join(self.storage_dir, f"metadata_{date_str}.json")
    
    def _get_today_date_str(self) -> str:
        """Get today's date as a string in YYYY-MM-DD format."""
        return datetime.now().strftime("%Y-%m-%d")
    
    def _initialize_indexes(self) -> None:
        """Initialize indexes by loading existing ones or creating new ones."""
        # Get list of existing index files
        index_files = glob.glob(os.path.join(self.storage_dir, "index_*.faiss"))
        
        if index_files:
            logger.info(f"Found {len(index_files)} existing index files")
            
            # Extract dates from filenames and sort them
            dates = []
            for file_path in index_files:
                filename = os.path.basename(file_path)
                # Extract date from filename (format: index_YYYY-MM-DD.faiss)
                date_str = filename[6:-6]  # Remove "index_" prefix and ".faiss" suffix
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    dates.append((date, date_str))
                except ValueError:
                    logger.warning(f"Skipping invalid index filename: {filename}")
            
            # Sort dates in descending order (newest first)
            dates.sort(reverse=True)
            
            # Keep only the most recent max_days indexes
            recent_dates = dates[:self.max_days]
            
            # Remove older index files
            for date, date_str in dates[self.max_days:]:
                self._remove_index(date_str)
            
            # Load the recent indexes
            for _, date_str in recent_dates:
                self._load_index(date_str)
                
        # Create today's index if it doesn't exist
        today = self._get_today_date_str()
        if today not in self.indexes:
            self._create_new_index(today)
    
    def _load_index(self, date_str: str) -> None:
        """Load an index and its metadata from disk.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
        """
        index_path = self._get_index_path(date_str)
        metadata_path = self._get_metadata_path(date_str)
        
        try:
            # Load FAISS index
            index = faiss.read_index(index_path)
            
            # Load metadata
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = []
            
            # Store in memory
            self.indexes[date_str] = index
            self.metadata[date_str] = metadata
            
            logger.info(f"Loaded index for {date_str} with {index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Failed to load index for {date_str}: {str(e)}")
    
    def _create_new_index(self, date_str: str) -> None:
        """Create a new empty index.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
        """
        # Create a new index with 768 dimensions (standard for many embeddings)
        dimension = 768
        index = faiss.IndexFlatL2(dimension)
        
        # Store in memory
        self.indexes[date_str] = index
        self.metadata[date_str] = []
        
        logger.info(f"Created new empty index for {date_str}")
    
    def _remove_index(self, date_str: str) -> None:
        """Remove an index and its metadata from disk and memory.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
        """
        index_path = self._get_index_path(date_str)
        metadata_path = self._get_metadata_path(date_str)
        
        # Remove files
        try:
            if os.path.exists(index_path):
                os.remove(index_path)
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            logger.info(f"Removed old index for {date_str}")
        except Exception as e:
            logger.error(f"Failed to remove index for {date_str}: {str(e)}")
        
        # Remove from memory
        self.indexes.pop(date_str, None)
        self.metadata.pop(date_str, None)
    
    def save_all_indexes(self) -> None:
        """Save all indexes and metadata to disk."""
        for date_str in self.indexes:
            self._save_index(date_str)
    
    def _save_index(self, date_str: str) -> None:
        """Save an index and its metadata to disk.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
        """
        if date_str not in self.indexes:
            logger.warning(f"Cannot save non-existent index for {date_str}")
            return
        
        index_path = self._get_index_path(date_str)
        metadata_path = self._get_metadata_path(date_str)
        
        try:
            # Save FAISS index
            faiss.write_index(self.indexes[date_str], index_path)
            
            # Save metadata
            with open(metadata_path, 'w') as f:
                json.dump(self.metadata[date_str], f)
            
            logger.info(f"Saved index for {date_str} with {self.indexes[date_str].ntotal} vectors")
        except Exception as e:
            logger.error(f"Failed to save index for {date_str}: {str(e)}")
    
    def add_data(self, vectors: np.ndarray, metadata_list: List[Dict[str, Any]]) -> None:
        """Add data to today's index.
        
        Args:
            vectors: NumPy array of vectors to add
            metadata_list: List of metadata dictionaries
        """
        today = self._get_today_date_str()
        
        # Create today's index if it doesn't exist
        if today not in self.indexes:
            self._create_new_index(today)
        
        # Add vectors to the index
        self.indexes[today].add(vectors)
        
        # Add metadata
        self.metadata[today].extend(metadata_list)
        
        # Save the updated index
        self._save_index(today)
        
        logger.info(f"Added {len(vectors)} vectors to index for {today}")
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> Tuple[List[Dict[str, Any]], List[float]]:
        """Search across all indexes for the most similar vectors.
        
        Args:
            query_vector: Query vector
            k: Number of results to return
            
        Returns:
            Tuple of (metadata_list, distances)
        """
        all_results = []
        
        # Ensure query_vector is properly shaped (1 x dim)
        if len(query_vector.shape) == 1:
            query_vector = query_vector.reshape(1, -1)
        
        for date_str, index in self.indexes.items():
            if index.ntotal == 0:
                continue
                
            # Search in this index
            distances, indices = index.search(query_vector, min(k, index.ntotal))
            
            # Get metadata for results
            for i, idx in enumerate(indices[0]):
                if idx != -1:  # -1 indicates no match found
                    result = {
                        "metadata": self.metadata[date_str][idx],
                        "distance": float(distances[0][i]),
                        "date": date_str
                    }
                    all_results.append(result)
        
        # Sort by distance (ascending)
        all_results.sort(key=lambda x: x["distance"])
        
        # Return top k results
        top_results = all_results[:k]
        
        # Separate metadata and distances
        metadata_list = [result["metadata"] for result in top_results]
        distances = [result["distance"] for result in top_results]
        
        return metadata_list, distances 