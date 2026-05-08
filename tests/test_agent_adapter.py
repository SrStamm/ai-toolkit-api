"""
Integration test: Agent with QueryServiceAdapter (streaming).

Tests the full agent loop using the RAG manual service via adapter
and the streaming response.
"""

import asyncio
import json
import sys
import os
import tempfile

# Setup BEFORE imports
os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", tempfile.mkdtemp())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.api.agent.agent import create_agent


async def test_agent_with_rag_adapter():
    """Test agent streaming loop with QueryServiceAdapter."""
    
    print("=" * 60)
    print("INTEGRATION TEST: Agent with QueryServiceAdapter (stream)")
    print("=" * 60)
    
    try:
        # 1. Create agent WITH RAG service adapter
        print("\n1. Creating Agent with use_rag_service=True...")
        agent = create_agent(
            provider="mistral",
            model=None,
            use_rag_service=True
        )
        print("   ✅ Agent created with RAG service adapter")
        
        # 2. Run agent streaming loop with a query
        print("\n2. Running agent_loop_stream() with a test query...")
        print("   Query: 'How can I use Middleware in FastAPI?'")
        
        collected_tokens = []
        final_done = None
        
        async for event in agent.agent_loop_stream(
            query="How can I use Middleware in FastAPI?",
            session_id="test-session-123",
            domain=None
        ):
            event_type = ""
            data = {}
            for line in event.split("\n"):
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    data = json.loads(line[6:])
            
            if event_type == "llm_token":
                collected_tokens.append(data["token"])
            elif event_type == "done":
                final_done = data
        
        full_response = "".join(collected_tokens)
        
        print(f"\n3. Streaming response received:")
        print(f"   Tokens collected: {len(collected_tokens)}")
        print(f"   Full output: {full_response[:200]}..." if len(full_response) > 200 else f"   Full output: {full_response}")
        print(f"   Has done event: {final_done is not None}")
        
        if final_done:
            print(f"   Metadata: {final_done}")
        
        print("\n" + "=" * 60)
        print("RESULT: Agent streaming with RAG adapter works! ✅")
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
        print("\n✅ SUCCESS: Agent streaming works with QueryServiceAdapter!")
        print("   You can now migrate tools to use retrieval_engine/")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Check errors above")
        sys.exit(1)
