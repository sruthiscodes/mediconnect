import logging
from typing import List, Dict, Any, Optional
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings

# Try to import ML dependencies, but make them optional
ML_AVAILABLE = False
try:
    import chromadb
    from chromadb import Documents, EmbeddingFunction, Embeddings
    from sentence_transformers import SentenceTransformer
    ML_AVAILABLE = True
except ImportError:
    logging.warning("ML dependencies (chromadb, sentence-transformers) not available. RAG features will be disabled.")

class SentenceTransformerEmbeddingFunction:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if ML_AVAILABLE:
            self.model = SentenceTransformer(model_name)
        else:
            self.model = None

    def __call__(self, input: Documents) -> Embeddings:
        if self.model:
            return self.model.encode(input).tolist()
        else:
            # Return dummy embeddings
            return [[0.0] * 384 for _ in input]

class EmbeddingService:
    def __init__(self):
        if ML_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
                self.embedding_function = SentenceTransformerEmbeddingFunction()
                self.executor = ThreadPoolExecutor(max_workers=4)
                self._initialize_collections()
            except Exception as e:
                logging.error(f"Failed to initialize ChromaDB: {e}")
                self.client = None
                self.embedding_function = None
                self.executor = None
        else:
            self.client = None
            self.embedding_function = None
            self.executor = None

    def _initialize_collections(self):
        """Initialize ChromaDB collections for user history and clinical knowledge"""
        if not ML_AVAILABLE or not self.client:
            return
            
        try:
            self.user_history_collection = self.client.get_or_create_collection(
                name="user_history",
                embedding_function=self.embedding_function
            )
            
            self.clinical_knowledge_collection = self.client.get_or_create_collection(
                name="clinical_knowledge",
                embedding_function=self.embedding_function
            )
        except Exception as e:
            logging.error(f"Error initializing collections: {e}")

    async def add_user_symptom(self, user_id: str, symptoms: str, metadata: Optional[Dict] = None) -> str:
        """Add user symptom to user_history collection"""
        if not ML_AVAILABLE or not self.client:
            return f"user_{user_id}_{uuid.uuid4().hex[:8]}"
            
        def _add_symptom():
            doc_id = f"user_{user_id}_{uuid.uuid4().hex[:8]}"
            
            meta = {
                "user_id": user_id,
                "type": "symptom",
                **(metadata or {})
            }
            
            self.user_history_collection.add(
                documents=[symptoms],
                metadatas=[meta],
                ids=[doc_id]
            )
            return doc_id

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _add_symptom)

    async def add_clinical_guideline(self, guideline_text: str, metadata: Optional[Dict] = None) -> str:
        """Add clinical guideline to clinical_knowledge collection"""
        if not ML_AVAILABLE or not self.client:
            return f"clinical_{uuid.uuid4().hex[:8]}"
            
        def _add_guideline():
            doc_id = f"clinical_{uuid.uuid4().hex[:8]}"
            
            meta = {
                "type": "clinical_guideline",
                **(metadata or {})
            }
            
            self.clinical_knowledge_collection.add(
                documents=[guideline_text],
                metadatas=[meta],
                ids=[doc_id]
            )
            return doc_id

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _add_guideline)

    async def search_user_history(self, user_id: str, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search user's symptom history"""
        if not ML_AVAILABLE or not self.client:
            return []
            
        def _search():
            results = self.user_history_collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"user_id": user_id}
            )
            
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        "document": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 0
                    })
            
            return formatted_results

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _search)

    async def search_clinical_knowledge(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search clinical knowledge base"""
        if not ML_AVAILABLE or not self.client:
            return []
            
        def _search():
            results = self.clinical_knowledge_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        "document": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 0
                    })
            
            return formatted_results

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _search)

    async def get_rag_context(self, user_id: str, current_symptoms: str) -> Dict[str, List[str]]:
        """Get combined RAG context from user history and clinical knowledge"""
        if not ML_AVAILABLE:
            return {
                "user_history": [],
                "clinical_knowledge": []
            }
            
        user_history_results = await self.search_user_history(user_id, current_symptoms, n_results=2)
        clinical_results = await self.search_clinical_knowledge(current_symptoms, n_results=3)
        
        user_history_context = [result["document"] for result in user_history_results]
        clinical_context = [result["document"] for result in clinical_results]
        
        return {
            "user_history": user_history_context,
            "clinical_knowledge": clinical_context
        }

    async def clear_collection(self, collection_name: str):
        """Clear all documents from a collection"""
        if not ML_AVAILABLE or not self.client:
            return
            
        def _clear():
            if collection_name == "user_history":
                # Delete and recreate the collection
                try:
                    if self.client:
                        self.client.delete_collection("user_history")
                except:
                    pass  # Collection might not exist
                if self.client:
                    self.user_history_collection = self.client.get_or_create_collection(
                        name="user_history",
                        embedding_function=self.embedding_function
                    )
            elif collection_name == "clinical_knowledge":
                # Delete and recreate the collection
                try:
                    if self.client:
                        self.client.delete_collection("clinical_knowledge")
                except:
                    pass  # Collection might not exist
                if self.client:
                    self.clinical_knowledge_collection = self.client.get_or_create_collection(
                        name="clinical_knowledge",
                        embedding_function=self.embedding_function
                    )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _clear)

    async def add_documents(self, collection_name: str, documents: List[str], metadatas: List[Dict], ids: List[str]):
        """Add multiple documents to a collection"""
        if not ML_AVAILABLE or not self.client:
            return
            
        def _add_documents():
            if collection_name == "clinical_knowledge":
                self.clinical_knowledge_collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            elif collection_name == "user_history":
                self.user_history_collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _add_documents)

# Create singleton instance
embedding_service = EmbeddingService() 