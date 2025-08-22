#!/usr/bin/env python3
"""
Gemini API Setup Script
Helps users configure their Gemini API key for the Smart Job Tracker.
"""

import os
import sys
from pathlib import Path

def main():
    print("🚀 Gemini API Setup for Smart Job Tracker")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file already exists")
        with open(env_file, 'r') as f:
            content = f.read()
            if 'GEMINI_API_KEY' in content:
                print("✅ GEMINI_API_KEY already configured")
                return
    else:
        print("📝 Creating .env file...")
    
    print("\n🔑 To get your Gemini API key:")
    print("1. Visit: https://makersuite.google.com/app/apikey")
    print("2. Sign in with your Google account")
    print("3. Click 'Create API Key'")
    print("4. Copy the generated key (starts with 'AIzaSyC...')")
    
    # Get API key from user
    api_key = input("\n📋 Enter your Gemini API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Setup cancelled.")
        return
    
    if not api_key.startswith('AIzaSy'):
        print("⚠️  Warning: API key doesn't look like a valid Gemini key")
        print("   Valid keys usually start with 'AIzaSy'")
        proceed = input("   Continue anyway? (y/N): ").strip().lower()
        if proceed != 'y':
            print("❌ Setup cancelled.")
            return
    
    # Write to .env file
    try:
        with open(env_file, 'a') as f:
            f.write(f"\n# Gemini API Configuration\n")
            f.write(f"GEMINI_API_KEY={api_key}\n")
        
        print(f"✅ API key saved to {env_file}")
        print("\n🔧 Next steps:")
        print("1. Restart your backend: docker compose restart backend")
        print("2. Test the setup: curl http://localhost:8000/gemini/status")
        print("3. Check the frontend for Gemini AI controls")
        
    except Exception as e:
        print(f"❌ Error saving API key: {e}")
        return
    
    print("\n🎉 Gemini API setup complete!")
    print("   Your Smart Job Tracker now supports AI-powered email analysis!")

if __name__ == "__main__":
    main()
