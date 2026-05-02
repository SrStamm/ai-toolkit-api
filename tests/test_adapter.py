"""
Quick test to verify QueryServiceAdapter works with the agent's tool.

This script:
1. Creates a RAGService (from retrieval_engine)
2. Wraps it with QueryServiceAdapter
3. Creates an Agent that uses the adapter instead of LlamaIndexOrchestrator
4. Runs a sample query to verify it works
"""

import asyncio
import sys
import os
import tempfile

# Setup Prometheus env BEFORE any imports
prom_dir = tempfile.mkdtemp()
os.environ["PROMETHEUS_MULTIPROC_DIR"] = prom_dir

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.api.retrieval_engine.service import get_rag_service
from app.api.agent.adapters.rag_adapter import create_query_adapter
from app.application.llm.client import get_llm_client


async def test_agent_with_adapter():
    """Test that the agent works with the RAG manual service via adapter."""
    
    print("=" * 60)
    print("TEST: Agent with QueryServiceAdapter")
    print("=" * 60)
    
    try:
        # 1. Get RAG service (from retrieval_engine)
        print("\n1. Creating RAGService...")
        rag_service = get_rag_service()
        print("   ✅ RAGService created")
        
        # 2. Create adapter
        print("\n2. Creating QueryServiceAdapter...")
        adapter = create_query_adapter(rag_service)
        print("   ✅ Adapter created")
        
        # 3. Verify adapter has get_context method
        print("\n3. Verifying adapter interface...")
        if not hasattr(adapter, 'get_context'):
            print("   ❌ Adapter missing get_context method!")
            return False
        print("   ✅ Adapter has get_context() method")
        
        # 4. Test adapter directly (without agent)
        print("\n4. Testing adapter.get_context() directly...")
        try:
            context_str, citations = adapter.get_context(
                query="test query about documents",
                top_k=3,
                domain=None,
                topic=None
            )
            print(f"   ✅ get_context() returned:")
            print(f"      - context length: {len(context_str)} chars")
            print(f"      - citations count: {len(citations)}")
        except Exception as e:
            print(f"   ❌ get_context() failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n" + "=" * 60)
        print("RESULT: Adapter works correctly! ✅")
        print("=" * 60)
        print("\nNext step: Create an Agent that uses this adapter")
        print("Instead of LlamaIndexOrchestrator")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Need to set PROMETHEUS_MULTIPROC_DIR for retrieval_engine
    os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", "/tmp/prometheus_multiproc")
    
    success = asyncio.run(test_agent_with_adapter())
    sys.exit(0 if success else 1)
