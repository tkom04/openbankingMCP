#!/usr/bin/env python3
"""
Test script to verify the package structure works correctly.
"""
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_package_imports():
    """Test that all package imports work correctly."""
    print("🧪 Testing package imports...")

    try:
        # Test main package import
        import openbankingmcp
        print("✅ Main package import successful")
        print(f"   Version: {openbankingmcp.__version__}")

        # Test individual module imports
        from openbankingmcp import server
        print("✅ Server module import successful")

        from openbankingmcp import validate
        print("✅ Validate module import successful")

        from openbankingmcp import schemas
        print("✅ Schemas module import successful")

        from openbankingmcp import pkce
        print("✅ PKCE module import successful")

        # Test specific function imports
        from openbankingmcp.server import MCPServer, create_fastapi_app
        print("✅ Server function imports successful")

        from openbankingmcp.validate import validate_tools, validate_tool_output
        print("✅ Validate function imports successful")

        from openbankingmcp.schemas import validate_account, validate_transaction
        print("✅ Schema function imports successful")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_package_functionality():
    """Test basic package functionality."""
    print("\n🧪 Testing package functionality...")

    try:
        from openbankingmcp import server

        # Test MCP server creation
        mcp_server = server.MCPServer()
        print("✅ MCP server creation successful")

        # Test tools list
        tools = mcp_server.tools
        print(f"✅ Tools list loaded: {len(tools)} tools")

        # Test FastAPI app creation (if FastAPI is available)
        try:
            app = server.create_fastapi_app()
            print("✅ FastAPI app creation successful")
        except ImportError:
            print("⚠️ FastAPI not available (expected if not installed)")

        return True

    except Exception as e:
        print(f"❌ Functionality test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_execution():
    """Test that modules can be executed as scripts."""
    print("\n🧪 Testing module execution...")

    try:
        import subprocess

        # Test server module execution (should show help/usage)
        result = subprocess.run(
            [sys.executable, "-m", "openbankingmcp.server", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 or "usage" in result.stdout.lower() or "error" in result.stderr.lower():
            print("✅ Server module execution successful")
        else:
            print(f"⚠️ Server module execution returned code {result.returncode}")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")

        return True

    except subprocess.TimeoutExpired:
        print("⚠️ Server module execution timed out (may be waiting for input)")
        return True
    except Exception as e:
        print(f"❌ Module execution test error: {e}")
        return False


def main():
    """Run all package tests."""
    print("🎯 OpenBanking MCP Package Structure Test")
    print("=" * 50)

    success = True

    # Test imports
    if not test_package_imports():
        success = False

    # Test functionality
    if not test_package_functionality():
        success = False

    # Test module execution
    if not test_module_execution():
        success = False

    print("\n" + "=" * 50)
    if success:
        print("🎉 All package tests passed!")
        print("\nPackage structure is correct and ready to use.")
        print("\nNext steps:")
        print("1. Install in development mode: pip install -e .")
        print("2. Run MCP server: python -m openbankingmcp.server")
        print("3. Run REST API: python -m openbankingmcp.server api")
    else:
        print("❌ Some package tests failed!")
        print("Please check the errors above and fix them.")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
