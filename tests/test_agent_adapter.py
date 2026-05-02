"""
Integration test: Agent with QueryServiceAdapter.

Tests the full agent loop using the RAG manual service via adapter.
"""

import asyncio
import sys
import os
import tempfile

# Setup BEFORE imports
os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", tempfile.mkdtemp())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.api.agent.agent import create_agent


async def test_agent_with_rag_adapter():
    """Test agent loop with QueryServiceAdapter."""
    
    print("=" * 60)
    print("INTEGRATION TEST: Agent with QueryServiceAdapter")
    print("=" * 60)
    
    try:
        # 1. Create agent WITH RAG service adapter
        print("\n1. Creating Agent with use_rag_service=True...")
        agent = create_agent(
            provider="mistral",  # or your preferred provider
            model=None,
            use_rag_service=True
        )
        print("   ✅ Agent created with RAG service adapter")
        
        # 2. Run agent loop with a query
        print("\n2. Running agent_loop() with a test query...")
        print("   Query: 'What is RAG in AI?'")
        
        # Note: This requires documents to be ingested in Qdrant
        # If no docs, agent should still respond (maybe without context)
        response = await agent.agent_loop(
            query="How can I use Middleware in FastAPI?",
            session_id="test-session-123",
            domain=None
        )
        
        print(f"\n3. Response received:")
        print(f"   Output: {response.output[:200]}..." if len(response.output) > 200 else f"   Output: {response.output}")
        print(f"   Session ID: {response.session_id}")
        
        if response.metadata:
            print(f"   Metadata: {response.metadata}")
        
        print("\n" + "=" * 60)
        print("RESULT: Agent with RAG adapter works! ✅")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 Starting integration test...")
    print("NOTE: Requires Qdrant running on localhost:6333")
    print("      and documents ingested for meaningful context.\n")
    
    success = asyncio.run(test_agent_with_rag_adapter())
    
    if success:
        print("\n✅ SUCCESS: Agent works with QueryServiceAdapter!")
        print("   You can now migrate tools to use retrieval_engine/")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Check errors above")
        sys.exit(1)
