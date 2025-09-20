#!/usr/bin/env python3
"""
Startup script to run both the REST API server and web client.
"""
import subprocess
import sys
import time
import os
import signal
import threading
from pathlib import Path


def run_api_server():
    """Run the FastAPI REST API server."""
    print("🚀 Starting REST API server on http://localhost:8000")
    try:
        subprocess.run([sys.executable, "-m", "openbankingmcp.server", "api"], check=True)
    except KeyboardInterrupt:
        print("\n🛑 REST API server stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ REST API server failed: {e}")


def run_web_client():
    """Run the Next.js web client."""
    web_dir = Path("web")
    if not web_dir.exists():
        print("❌ Web directory not found")
        return

    print("🚀 Starting web client on http://localhost:3000")
    try:
        # Change to web directory and run npm dev
        subprocess.run(["npm", "run", "dev"], cwd=web_dir, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Web client stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Web client failed: {e}")
    except FileNotFoundError:
        print("❌ npm not found. Please install Node.js and npm")


def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")

    # Check Python dependencies
    try:
        import fastapi
        import uvicorn
        print("✅ FastAPI dependencies installed")
    except ImportError:
        print("❌ FastAPI dependencies missing. Run: pip install -r requirements.txt")
        return False

    # Check Node.js dependencies
    web_dir = Path("web")
    if not web_dir.exists():
        print("❌ Web directory not found")
        return False

    node_modules = web_dir / "node_modules"
    if not node_modules.exists():
        print("❌ Node.js dependencies missing. Run: cd web && npm install")
        return False

    print("✅ Node.js dependencies installed")
    return True


def main():
    """Main function to start both servers."""
    print("🎯 OpenBanking MCP Web Integration Startup")
    print("=" * 50)

    if not check_dependencies():
        print("\n❌ Please install missing dependencies before continuing")
        sys.exit(1)

    print("\n📋 Starting servers...")
    print("   - REST API: http://localhost:8000")
    print("   - Web Client: http://localhost:3000")
    print("\n💡 Press Ctrl+C to stop both servers")
    print("=" * 50)

    # Start API server in a separate thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()

    # Wait a moment for API server to start
    time.sleep(2)

    # Start web client in main thread
    try:
        run_web_client()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")


if __name__ == "__main__":
    main()
