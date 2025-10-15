#!/usr/bin/env python3
"""
Test script to check available Gemini models
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def test_gemini_models():
    """Test which Gemini models are currently available"""
    
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ No GOOGLE_API_KEY found")
        return
    
    genai.configure(api_key=api_key)
    
    print("🔍 Listing available Gemini models...")
    
    try:
        # List all available models
        models = genai.list_models()
        print("\n📋 Available models:")
        
        vision_models = []
        text_models = []
        
        for model in models:
            model_name = model.name.replace('models/', '')
            print(f"   - {model_name}")
            
            # Check if it supports vision (generateContent with images)
            if 'vision' in model_name.lower() or 'pro' in model_name.lower() or 'flash' in model_name.lower():
                vision_models.append(model_name)
            else:
                text_models.append(model_name)
        
        print(f"\n🎯 Vision-capable models found: {len(vision_models)}")
        for model in vision_models[:3]:  # Show first 3
            print(f"   - {model}")
        
        # Test the first vision model
        if vision_models:
            test_model = vision_models[0]
            print(f"\n🧪 Testing model: {test_model}")
            
            try:
                model = genai.GenerativeModel(test_model)
                response = model.generate_content("Hello, can you analyze images?")
                print(f"✅ {test_model}: Working!")
                print(f"   Response: {response.text[:100]}...")
                return test_model
            except Exception as e:
                print(f"❌ {test_model}: {str(e)[:100]}...")
        
        return None
        
    except Exception as e:
        print(f"❌ Error listing models: {e}")
        return None

if __name__ == '__main__':
    working_model = test_gemini_models()