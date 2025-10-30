"""Quick test for streaming."""
import asyncio
import httpx
import json
import sys


async def test_health():
    """Test health endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Server is healthy")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False


async def test_streaming_simple():
    """Test streaming with a simple question."""
    print("\n🧪 Testing streaming response...")
    print("📝 Question: What is 1+1? Answer briefly.")
    print("-" * 60)
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        payload = {
            "model": "triple-thread-thinking",
            "messages": [
                {"role": "user", "content": "What is 1+1? Answer briefly."}
            ],
            "stream": True
        }
        
        try:
            async with client.stream(
                "POST",
                "http://localhost:8000/v1/chat/completions",
                json=payload
            ) as response:
                if response.status_code != 200:
                    print(f"❌ Error: HTTP {response.status_code}")
                    body = await response.aread()
                    print(body.decode())
                    return False
                
                print("📡 Receiving stream...\n")
                
                content_parts = []
                chunk_count = 0
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_part = line[6:]
                        
                        if data_part == "[DONE]":
                            print("\n\n✅ Stream completed with [DONE]")
                            break
                        
                        try:
                            chunk_data = json.loads(data_part)
                            chunk_count += 1
                            
                            # Extract content
                            if (chunk_data.get("choices") and 
                                len(chunk_data["choices"]) > 0 and
                                "delta" in chunk_data["choices"][0]):
                                
                                delta = chunk_data["choices"][0]["delta"]
                                
                                if "content" in delta:
                                    content = delta["content"]
                                    content_parts.append(content)
                                    print(content, end="", flush=True)
                                elif "role" in delta:
                                    print(f"[Role: {delta['role']}] ", end="", flush=True)
                        
                        except json.JSONDecodeError as e:
                            print(f"\n⚠️ JSON decode error: {e}")
                            continue
                
                full_content = "".join(content_parts)
                print(f"\n\n📊 Statistics:")
                print(f"   Chunks received: {chunk_count}")
                print(f"   Total characters: {len(full_content)}")
                print(f"\n✅ Streaming test passed!")
                return True
                
        except Exception as e:
            print(f"\n❌ Error during streaming: {e}")
            return False


async def test_non_streaming_simple():
    """Test non-streaming response."""
    print("\n🧪 Testing non-streaming response...")
    print("📝 Question: What is 2+2? Answer briefly.")
    print("-" * 60)
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        payload = {
            "model": "triple-thread-thinking",
            "messages": [
                {"role": "user", "content": "What is 2+2? Answer briefly."}
            ],
            "stream": False
        }
        
        try:
            response = await client.post(
                "http://localhost:8000/v1/chat/completions",
                json=payload
            )
            
            if response.status_code != 200:
                print(f"❌ Error: HTTP {response.status_code}")
                print(response.text)
                return False
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            print(f"📥 Response:\n{content}\n")
            print(f"✅ Non-streaming test passed!")
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🚀 QUICK STREAMING TEST")
    print("=" * 60)
    
    # Test health
    if not await test_health():
        print("\n❌ Server is not running. Please start it first:")
        print("   .\\start.ps1")
        sys.exit(1)
    
    # Test non-streaming
    result1 = await test_non_streaming_simple()
    
    # Test streaming
    result2 = await test_streaming_simple()
    
    print("\n" + "=" * 60)
    if result1 and result2:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
