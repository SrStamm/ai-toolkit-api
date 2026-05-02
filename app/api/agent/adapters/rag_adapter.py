"""
Adapter to make RAGService/QueryService compatible with the agent's tool interface.

The agent's retrieve_context tool expects an object with:
    get_context(query, top_k, domain, topic) -> (context_str, list[Citation])

This adapter wraps QueryService and provides that interface.
"""

from collections.abc import Iterable
from typing import Optional

from app.api.retrieval_engine.query_service import QueryService
from app.api.retrieval_engine.schemas import Citation


class QueryServiceAdapter:
    """
    Adapts QueryService to the interface expected by the agent's tools.
    
    The agent tool expects: get_context() -> (str, list[Citation])
    QueryService provides: retrieve() -> list[scored chunks]
    """
    
    def __init__(self, query_service: QueryService) -> None:
        self._query_service = query_service
    
    def get_context(
        self, 
        query: str, 
        top_k: int = 5, 
        domain: Optional[str] = None, 
        topic: Optional[str] = None
    ) -> tuple[str, list[Citation]]:
        """
        Retrieve relevant context and format it for the agent tool.
        
        Args:
            query: User's query string
            top_k: Number of results to return (note: actual retrieval 
                   uses a higher limit for reranking, but we return top_k)
            domain: Optional domain filter
            topic: Optional topic filter
            
        Returns:
            Tuple of (context_string, list_of_citations)
        """
        # QueryService.retrieve() returns list of scored chunks (from vector store)
        chunks = self._query_service.retrieve(
            text=query,
            domain=domain,
            topic=topic
        )
        
        # Limit to top_k after retrieval (reranking happens inside retrieve)
        top_chunks = chunks[:top_k]
        
        # Build context string: "[1]\n{text}\n\n[2]\n{text}..."
        context_parts = []
        citations = []
        
        seen_sources = set()
        
        for i, chunk in enumerate(top_chunks):
            # Extract text from chunk payload
            chunk_text = chunk.payload.get("text", "")
            chunk_source = chunk.payload.get("source", "unknown")
            chunk_index = chunk.payload.get("chunk_index", i)
            
            # Add to context
            context_parts.append(f"[{i + 1}]\n{chunk_text}")
            
            # Build citation (avoid duplicates by source)
            if chunk_source not in seen_sources:
                seen_sources.add(chunk_source)
                citations.append(
                    Citation(
                        source=chunk_source,
                        chunk_index=chunk_index,
                        text=chunk_text
                    )
                )
        
        context_str = "\n\n".join(context_parts)
        
        return context_str, citations


def create_query_adapter(rag_service) -> QueryServiceAdapter:
    """
    Factory function to create an adapter from RAGService or QueryService.
    
    Args:
        rag_service: Either a RAGService instance or a QueryService instance.
                      If RAGService, uses its internal query service.
                      
    Returns:
        QueryServiceAdapter ready to use with the agent.
    """
    # Check if it's RAGService (has .query attribute) or QueryService directly
    if hasattr(rag_service, 'query'):
        # It's RAGService, extract the QueryService
        query_service = rag_service.query
    else:
        # Assume it's already a QueryService
        query_service = rag_service
    
    return QueryServiceAdapter(query_service=query_service)
