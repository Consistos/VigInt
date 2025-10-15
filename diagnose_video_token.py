#!/usr/bin/env python3
"""
Diagnose Video Token Issues
Helps identify token generation and validation problems
"""

import os
import sys
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def diagnose_token_issue():
    """Diagnose video token validation issues"""
    
    print("=" * 70)
    print("🔍 VIDEO TOKEN DIAGNOSTIC TOOL")
    print("=" * 70)
    print()
    
    # Check environment variables
    print("📍 STEP 1: Environment Configuration")
    print("-" * 70)
    
    sparse_ai_key = os.getenv('SPARSE_AI_API_KEY')
    sparse_ai_url = os.getenv('SPARSE_AI_BASE_URL', 'https://sparse-ai.com')
    
    print(f"SPARSE_AI_BASE_URL: {sparse_ai_url}")
    print(f"SPARSE_AI_API_KEY: {'✅ Set' if sparse_ai_key and sparse_ai_key != 'your-sparse-ai-api-key-here' else '❌ Not configured'}")
    print()
    
    if not sparse_ai_key or sparse_ai_key == 'your-sparse-ai-api-key-here':
        print("⚠️  WARNING: API key not configured!")
        print("   Please set SPARSE_AI_API_KEY in your .env file")
        print()
    
    # Check for URL mismatch
    print("🔗 STEP 2: URL Configuration Check")
    print("-" * 70)
    
    known_urls = [
        'https://sparse-ai.com',
        'https://sparse-ai-video-server.onrender.com',
        'http://127.0.0.1:9999'
    ]
    
    print(f"Current URL: {sparse_ai_url}")
    print()
    print("Known valid URLs:")
    for url in known_urls:
        status = "✅ CURRENT" if url == sparse_ai_url else "  "
        print(f"{status} {url}")
    print()
    
    if 'onrender.com' not in sparse_ai_url and 'sparse-ai-video-server.onrender.com' in sys.argv:
        print("⚠️  URL MISMATCH DETECTED!")
        print(f"   Your .env has: {sparse_ai_url}")
        print(f"   But you're accessing: https://sparse-ai-video-server.onrender.com")
        print(f"   → This will cause 'Invalid token' errors!")
        print()
    
    # Parse the problematic link if provided
    if len(sys.argv) > 1:
        print("🔍 STEP 3: Analyzing Provided Link")
        print("-" * 70)
        
        problem_link = sys.argv[1]
        print(f"Link: {problem_link}")
        print()
        
        parsed = urlparse(problem_link)
        query = parse_qs(parsed.query)
        
        link_video_id = parsed.path.split('/')[-1]
        link_token = query.get('token', [''])[0]
        link_base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        print(f"Extracted Information:")
        print(f"  Base URL: {link_base_url}")
        print(f"  Video ID: {link_video_id}")
        print(f"  Token: {link_token[:16]}...")
        print()
        
        # Check URL match
        if link_base_url != sparse_ai_url:
            print("❌ URL MISMATCH DETECTED!")
            print(f"   Link uses: {link_base_url}")
            print(f"   .env has:  {sparse_ai_url}")
            print()
            print("🔧 FIX: Update your .env file:")
            print(f"   SPARSE_AI_BASE_URL={link_base_url}")
            print()
        else:
            print("✅ URL matches configuration")
            print()
    
    # Generate sample token
    print("🔑 STEP 4: Sample Token Generation")
    print("-" * 70)
    
    sample_video_id = "ebabccfb-44e1-4ef1-a195-1cc69b1b1135"
    sample_expiration = datetime.now() + timedelta(hours=48)
    
    if sparse_ai_key and sparse_ai_key != 'your-sparse-ai-api-key-here':
        # Generate token using current configuration
        token_data = f"{sample_video_id}:{sample_expiration.isoformat()}:{sparse_ai_key}"
        generated_token = hashlib.sha256(token_data.encode()).hexdigest()[:32]
        
        print(f"Sample Video ID: {sample_video_id}")
        print(f"Sample Expiration: {sample_expiration.isoformat()}")
        print(f"Generated Token: {generated_token}")
        print()
        print(f"Sample Link:")
        print(f"{sparse_ai_url}/video/{sample_video_id}?token={generated_token}")
        print()
    else:
        print("❌ Cannot generate sample token - API key not configured")
        print()
    
    # Summary
    print("=" * 70)
    print("📋 DIAGNOSTIC SUMMARY")
    print("=" * 70)
    print()
    
    issues = []
    fixes = []
    
    if not sparse_ai_key or sparse_ai_key == 'your-sparse-ai-api-key-here':
        issues.append("API key not configured")
        fixes.append("Set SPARSE_AI_API_KEY in .env file")
    
    if len(sys.argv) > 1:
        problem_link = sys.argv[1]
        parsed = urlparse(problem_link)
        link_base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        if link_base_url != sparse_ai_url:
            issues.append(f"URL mismatch: Link uses {link_base_url} but .env has {sparse_ai_url}")
            fixes.append(f"Update .env: SPARSE_AI_BASE_URL={link_base_url}")
    
    if issues:
        print("❌ ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
        print()
        print("🔧 RECOMMENDED FIXES:")
        for i, fix in enumerate(fixes, 1):
            print(f"{i}. {fix}")
        print()
    else:
        print("✅ No obvious issues detected")
        print()
        print("If you're still getting 'Invalid token' errors:")
        print("1. Ensure video server is using the same API key")
        print("2. Verify video hasn't expired")
        print("3. Check server logs for detailed error messages")
        print()
    
    print("=" * 70)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage: python diagnose_video_token.py [problem_link]")
        print()
        print("Examples:")
        print("  python diagnose_video_token.py")
        print("  python diagnose_video_token.py 'https://sparse-ai-video-server.onrender.com/video/abc123?token=xyz'")
        sys.exit(0)
    
    diagnose_token_issue()
