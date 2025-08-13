"""RAG Ingest Module - Document ingestion with BM25 + FAISS hybrid search."""

import os
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from rank_bm25 import BM25Okapi
import tiktoken


@dataclass
class Document:
    """Document dataclass for storing document metadata."""
    id: str
    content: str
    title: str
    source: str
    chunk_index: int
    metadata: Dict[str, Any]
    created_at: str
    embeddings: Optional[np.ndarray] = None


class DocumentProcessor:
    """Handles document chunking and preprocessing."""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def chunk_document(self, content: str, title: str, source: str, metadata: Dict[str, Any] = None) -> List[Document]:
        """Split document into overlapping chunks."""
        if metadata is None:
            metadata = {}
        
        tokens = self.tokenizer.encode(content)
        chunks = []
        
        for i in range(0, len(tokens), self.chunk_size - self.overlap):
            chunk_tokens = tokens[i:i + self.chunk_size]
            chunk_content = self.tokenizer.decode(chunk_tokens)
            
            chunk_id = hashlib.md5(f"{source}_{i}".encode()).hexdigest()
            
            doc = Document(
                id=chunk_id,
                content=chunk_content,
                title=title,
                source=source,
                chunk_index=i // (self.chunk_size - self.overlap),
                metadata=metadata,
                created_at=datetime.now().isoformat()
            )
            chunks.append(doc)
        
        return chunks


class HybridIndex:
    """Hybrid BM25 + FAISS vector index for document retrieval."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", index_path: str = "./rag_index"):
        self.model_name = model_name
        self.index_path = Path(index_path)
        self.index_path.mkdir(exist_ok=True)
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(model_name)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        
        # Initialize indices
        self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
        self.bm25_index = None
        
        # Document storage
        self.documents: List[Document] = []
        self.doc_texts: List[str] = []
        
        # Load existing index if available
        self._load_index()
    
    def add_documents(self, documents: List[Document]):
        """Add documents to both BM25 and FAISS indices."""
        if not documents:
            return
        
        # Generate embeddings
        contents = [doc.content for doc in documents]
        embeddings = self.embedding_model.encode(contents, convert_to_numpy=True)
        
        # Normalize embeddings for cosine similarity
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        # Add embeddings to documents
        for doc, embedding in zip(documents, embeddings):
            doc.embeddings = embedding
        
        # Add to FAISS index
        self.faiss_index.add(embeddings.astype(np.float32))
        
        # Update document storage
        self.documents.extend(documents)
        self.doc_texts.extend(contents)
        
        # Rebuild BM25 index with all documents
        tokenized_docs = [doc.split() for doc in self.doc_texts]
        self.bm25_index = BM25Okapi(tokenized_docs)
        
        print(f"Added {len(documents)} documents to index. Total: {len(self.documents)} documents.")
    
    def save_index(self):
        """Save the hybrid index to disk."""
        # Save FAISS index
        faiss.write_index(self.faiss_index, str(self.index_path / "faiss_index.bin"))
        
        # Save BM25 index
        with open(self.index_path / "bm25_index.pkl", "wb") as f:
            pickle.dump(self.bm25_index, f)
        
        # Save documents metadata (without embeddings to save space)
        docs_metadata = []
        for doc in self.documents:
            doc_dict = asdict(doc)
            doc_dict.pop('embeddings', None)  # Remove embeddings to save space
            docs_metadata.append(doc_dict)
        
        with open(self.index_path / "documents.json", "w") as f:
            json.dump(docs_metadata, f, indent=2)
        
        # Save configuration
        config = {
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "total_documents": len(self.documents)
        }
        
        with open(self.index_path / "config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        print(f"Index saved to {self.index_path}")
    
    def _load_index(self):
        """Load existing index from disk."""
        try:
            # Load FAISS index
            faiss_path = self.index_path / "faiss_index.bin"
            if faiss_path.exists():
                self.faiss_index = faiss.read_index(str(faiss_path))
            
            # Load BM25 index
            bm25_path = self.index_path / "bm25_index.pkl"
            if bm25_path.exists():
                with open(bm25_path, "rb") as f:
                    self.bm25_index = pickle.load(f)
            
            # Load documents
            docs_path = self.index_path / "documents.json"
            if docs_path.exists():
                with open(docs_path, "r") as f:
                    docs_metadata = json.load(f)
                
                self.documents = [Document(**doc) for doc in docs_metadata]
                self.doc_texts = [doc.content for doc in self.documents]
            
            if self.documents:
                print(f"Loaded existing index with {len(self.documents)} documents.")
        
        except Exception as e:
            print(f"Warning: Could not load existing index: {e}")
            # Reset to empty state
            self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)
            self.bm25_index = None
            self.documents = []
            self.doc_texts = []


def ingest_documents(file_paths: List[str], index_path: str = "./rag_index", 
                    chunk_size: int = 1000, overlap: int = 200) -> HybridIndex:
    """Main ingestion function to process and index documents."""
    
    processor = DocumentProcessor(chunk_size=chunk_size, overlap=overlap)
    index = HybridIndex(index_path=index_path)
    
    all_chunks = []
    
    for file_path in file_paths:
        file_path = Path(file_path)
        
        if not file_path.exists():
            print(f"Warning: File {file_path} does not exist.")
            continue
        
        print(f"Processing {file_path}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata
            metadata = {
                "file_size": file_path.stat().st_size,
                "file_extension": file_path.suffix,
                "processed_at": datetime.now().isoformat()
            }
            
            # Chunk document
            chunks = processor.chunk_document(
                content=content,
                title=file_path.stem,
                source=str(file_path),
                metadata=metadata
            )
            
            all_chunks.extend(chunks)
            print(f"Created {len(chunks)} chunks from {file_path}")
        
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    # Add all chunks to index
    if all_chunks:
        index.add_documents(all_chunks)
        index.save_index()
        print(f"Successfully ingested {len(all_chunks)} chunks from {len(file_paths)} files.")
    else:
        print("No documents were successfully processed.")
    
    return index


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest documents into RAG index")
    parser.add_argument("files", nargs="+", help="Files to ingest")
    parser.add_argument("--index-path", default="./rag_index", help="Path to store index")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size in tokens")
    parser.add_argument("--overlap", type=int, default=200, help="Chunk overlap in tokens")
    
    args = parser.parse_args()
    
    index = ingest_documents(
        file_paths=args.files,
        index_path=args.index_path,
        chunk_size=args.chunk_size,
        overlap=args.overlap
    )
    
    print(f"Ingestion complete. Index available at {args.index_path}")
