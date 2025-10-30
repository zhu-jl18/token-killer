"""Validation script to check if everything is set up correctly."""
import sys
import os
from pathlib import Path

def validate_structure():
    """Validate project structure."""
    print("🔍 Validating project structure...")
    
    required_files = [
        "app/main.py",
        "app/config.py",
        "app/core/client.py",
        "app/core/thinking.py",
        "app/core/validation.py",
        "app/core/fusion.py",
        "app/core/context.py",
        "app/models/openai.py",
        "app/models/internal.py",
        "config.yaml",
        ".env",
        "prompts/thinking.yaml",
        "prompts/validation.yaml",
        "prompts/fusion.yaml",
        "prompts/summary.yaml",
    ]
    
    all_exist = True
    for file in required_files:
        path = Path(file)
        if path.exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING")
            all_exist = False
    
    return all_exist

def validate_imports():
    """Validate all imports work."""
    print("\n🔍 Validating imports...")
    
    try:
        import fastapi
        print("  ✅ fastapi")
    except ImportError as e:
        print(f"  ❌ fastapi - {e}")
        return False
    
    try:
        import uvicorn
        print("  ✅ uvicorn")
    except ImportError as e:
        print(f"  ❌ uvicorn - {e}")
        return False
    
    try:
        import aiohttp
        print("  ✅ aiohttp")
    except ImportError as e:
        print(f"  ❌ aiohttp - {e}")
        return False
    
    try:
        import structlog
        print("  ✅ structlog")
    except ImportError as e:
        print(f"  ❌ structlog - {e}")
        return False
    
    try:
        from app.config import app_config, settings
        print("  ✅ app.config")
    except Exception as e:
        print(f"  ❌ app.config - {e}")
        return False
    
    try:
        from app.core import ThinkingOrchestrator
        print("  ✅ app.core")
    except Exception as e:
        print(f"  ❌ app.core - {e}")
        return False
    
    try:
        from app.models import ChatCompletionRequest
        print("  ✅ app.models")
    except Exception as e:
        print(f"  ❌ app.models - {e}")
        return False
    
    return True

def validate_config():
    """Validate configuration."""
    print("\n🔍 Validating configuration...")
    
    try:
        from app.config import app_config, settings
        
        # Check models
        assert "main_thinker" in app_config.models
        print("  ✅ Main thinker model configured")
        
        assert "fusion" in app_config.models
        print("  ✅ Fusion model configured")
        
        assert "summarizer" in app_config.models
        print("  ✅ Summarizer model configured")
        
        # Check API keys
        assert settings.main_model_api_key != ""
        print("  ✅ Main model API key set")
        
        assert settings.fusion_model_api_key != ""
        print("  ✅ Fusion model API key set")
        
        # Check thinking config
        assert app_config.thinking.num_threads > 0
        print(f"  ✅ Thinking threads: {app_config.thinking.num_threads}")
        
        # Check validation config
        print(f"  ✅ Validation enabled: {app_config.validation.enabled}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False

def validate_app():
    """Try to import the FastAPI app."""
    print("\n🔍 Validating FastAPI app...")
    
    try:
        from app.main import app
        print("  ✅ FastAPI app imported successfully")
        
        # Check endpoints
        routes = [route.path for route in app.routes]
        required_routes = ["/health", "/v1/chat/completions", "/v1/models"]
        
        for route in required_routes:
            if route in routes:
                print(f"  ✅ Route {route} registered")
            else:
                print(f"  ❌ Route {route} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to import app: {e}")
        return False

def main():
    """Main validation."""
    print("=" * 60)
    print("🚀 FASTAPI REFACTORED PROJECT VALIDATION")
    print("=" * 60)
    
    results = []
    
    # Run validations
    results.append(("Project Structure", validate_structure()))
    results.append(("Python Imports", validate_imports()))
    results.append(("Configuration", validate_config()))
    results.append(("FastAPI App", validate_app()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✅ ALL VALIDATIONS PASSED!")
        print("\n📝 Next steps:")
        print("1. Run the server: .\\start.ps1")
        print("2. Or manually: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        print("3. Test API: python test_api.py")
        print("4. View docs: http://localhost:8000/docs")
    else:
        print("\n❌ SOME VALIDATIONS FAILED!")
        print("Please fix the issues above before running the server.")
        sys.exit(1)

if __name__ == "__main__":
    main()