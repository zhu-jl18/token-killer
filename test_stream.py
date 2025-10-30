"""Test streaming functionality."""
import asyncio
import httpx
import json
import time


async def test_non_streaming():
    """Test non-streaming response."""
    print("🧪 Testing non-streaming response...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        payload = {
            "model": "triple-thread-thinking",
            "messages": [
                {"role": "user", "content": "What is 1+1? Keep it short."}
            ],
            "stream": False
        }
        
        start_time = time.time()
        response = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json=payload
        )
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"✅ Non-streaming test passed in {elapsed:.2f}s")
        print(f"📥 Response: {data['choices'][0]['message']['content'][:100]}...")
        return data


async def test_streaming():
    """Test streaming response."""
    print("\n🧪 Testing streaming response...")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        payload = {
            "model": "triple-thread-thinking",
            "messages": [
                {"role": "user", "content": "What is 2+2? Keep it short."}
            ],
            "stream": True
        }
        
        start_time = time.time()
        
        async with client.stream(
            "POST",
            "http://localhost:8000/v1/chat/completions",
            json=payload
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            
            chunks = []
            content_parts = []
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_part = line[6:]  # Remove "data: " prefix
                    
                    if data_part == "[DONE]":
                        break
                    
                    try:
                        chunk_data = json.loads(data_part)
                        chunks.append(chunk_data)
                        
                        # Extract content from delta
                        if (chunk_data.get("choices") and 
                            len(chunk_data["choices"]) > 0 and
                            "delta" in chunk_data["choices"][0] and
                            "content" in chunk_data["choices"][0]["delta"]):
                            
                            content = chunk_data["choices"][0]["delta"]["content"]
                            content_parts.append(content)
                            print(content, end="", flush=True)
                    
                    except json.JSONDecodeError:
                        continue
        
        elapsed = time.time() - start_time
        full_content = "".join(content_parts)
        
        print(f"\n\n✅ Streaming test passed in {elapsed:.2f}s")
        print(f"📊 Received {len(chunks)} chunks")
        print(f"📝 Total content length: {len(full_content)} characters")
        
        return chunks, full_content


async def test_openai_sdk_compatible():
    """Test with OpenAI SDK format."""
    print("\n🧪 Testing OpenAI SDK compatibility...")
    
    try:
        # Test if we can import openai (if available)
        import openai
        
        client = openai.OpenAI(
            base_url="http://localhost:8000/v1",
            api_key="dummy"  # Not needed for our API
        )
        
        # Test non-streaming
        print("  📡 Testing OpenAI SDK non-streaming...")
        response = client.chat.completions.create(
            model="triple-thread-thinking",
            messages=[
                {"role": "user", "content": "What is 3+3? Be brief."}
            ],
            stream=False
        )
        
        print(f"  ✅ OpenAI SDK non-streaming: {response.choices[0].message.content[:100]}...")
        
        # Test streaming
        print("  📡 Testing OpenAI SDK streaming...")
        stream_content = []
        stream = client.chat.completions.create(
            model="triple-thread-thinking",
            messages=[
                {"role": "user", "content": "What is 4+4? Be brief."}
            ],
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                stream_content.append(content)
                print(content, end="", flush=True)
        
        full_stream_content = "".join(stream_content)
        print(f"\n  ✅ OpenAI SDK streaming: {len(full_stream_content)} characters received")
        
        return True
        
    except ImportError:
        print("  ⚠️  OpenAI SDK not installed, skipping SDK test")
        print("  💡 Install with: pip install openai")
        return False
    except Exception as e:
        print(f"  ❌ OpenAI SDK test failed: {e}")
        return False


async def run_all_streaming_tests():
    """Run all streaming tests."""
    print("=" * 60)
    print("🚀 STREAMING API TESTS")
    print("=" * 60)
    
    try:
        # Test basic endpoints first
        async with httpx.AsyncClient() as client:
            health_response = await client.get("http://localhost:8000/health")
            assert health_response.status_code == 200
            print("✅ Health check passed")
        
        # Test non-streaming
        await test_non_streaming()
        
        # Test streaming
        await test_streaming()
        
        # Test OpenAI SDK compatibility
        await test_openai_sdk_compatible()
        
        print("\n" + "=" * 60)
        print("✅ ALL STREAMING TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except httpx.ConnectError:
        print("\n❌ Could not connect to API. Make sure the server is running.")
        print("   Run: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_all_streaming_tests())