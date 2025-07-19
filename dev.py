#!/usr/bin/env python3
"""
Development helper script to generate database and start local webserver
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False
        if result.stdout:
            print(result.stdout)
        return True
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def main():
    print("🚀 Starting development environment...\n")

    # Check if we're in the right directory
    if not Path("scraper/scraper.py").exists():
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)

    # Check if database exists and when it was last modified
    db_path = Path("data/games.db")
    should_rebuild = True

    if db_path.exists():
        # Check if any JSON files are newer than the database
        json_files = list(Path("data").glob("*.json"))
        if json_files:
            newest_json = max(json_files, key=lambda p: p.stat().st_mtime)
            if db_path.stat().st_mtime > newest_json.stat().st_mtime:
                should_rebuild = False
                print("✅ Database is up to date")

    # Build database if needed
    if should_rebuild:
        if not run_command("uv run python scraper/scraper.py build-db", "Building SQLite database from JSON files"):
            print("\n❌ Failed to build database")
            sys.exit(1)
        print("✅ Database built successfully")

    # Start the web server
    port = 8000
    print(f"\n🌐 Starting web server on http://localhost:{port}/")
    print("Press Ctrl+C to stop the server\n")

    try:
        # Use os.system for the web server so it can be interrupted properly
        os.system(f"uv run python -m http.server {port}")
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")

if __name__ == "__main__":
    main()
