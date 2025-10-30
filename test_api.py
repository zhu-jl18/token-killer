"""Test script for the API."""
import asyncio
import httpx
import json
import time
from typing import Dict, Any


async def test_health_check(base_url: str):
    """Test health check endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✅ Health check passed")
        return data


async def test_models_list(base_url: str):
    """Test models list endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0
        print(f"✅ Models list passed: {data['data'][0]['id']}")
        return data


async def test_chat_completion(base_url: str, test_message: str):
    """Test chat completion endpoint."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        payload = {
            "model": "triple-thread-thinking",
            "messages": [
                {"role": "user", "content": test_message}
            ]
        }
        
        print(f"\n📤 Sending request: {test_message}")
        start_time = time.time()
        
        response = await client.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
        )
        
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "message" in data["choices"][0]
        assert "content" in data["choices"][0]["message"]
        
        content = data["choices"][0]["message"]["content"]
        print(f"✅ Chat completion passed in {elapsed:.2f}s")
        print(f"📥 Response preview: {content[:200]}...")
        
        return data


async def test_error_handling(base_url: str):
    """Test error handling."""
    async with httpx.AsyncClient() as client:
        # Test missing messages
        response = await client.post(
            f"{base_url}/v1/chat/completions",
            json={"model": "test"}
        )
        assert response.status_code == 422  # Validation error from Pydantic
        print("✅ Error handling for missing messages passed")
        
        # Test empty messages
        response = await client.post(
            f"{base_url}/v1/chat/completions",
            json={"model": "test", "messages": []}
        )
        assert response.status_code == 400
        print("✅ Error handling for empty messages passed")


async def run_all_tests():
    """Run all tests."""
    base_url = "http://localhost:8000"
    
    print("🧪 Starting API tests...")
    print(f"📍 Base URL: {base_url}")
    print("-" * 50)
    
    try:
        # Test health check
        await test_health_check(base_url)
        
        # Test models list
        await test_models_list(base_url)
        
        # Test error handling
        await test_error_handling(base_url)
        
        # Test chat completion with different messages
        test_messages = [
            "What is 2+2?",
            # "解释一下递归是什么",  # Uncomment for longer test
        ]
        
        for msg in test_messages:
            await test_chat_completion(base_url, msg)
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        
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
    asyncio.run(run_all_tests())