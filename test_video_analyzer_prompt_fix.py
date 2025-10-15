#!/usr/bin/env python3
"""
Test to verify that video_analyzer.py prompt now requests incident_type
"""

import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_video_analyzer_prompt():
    """Test that video_analyzer.py prompt requests incident_type"""
    
    print("🧪 Testing video_analyzer.py prompt for incident_type...\n")
    
    # Read the video_analyzer.py file
    try:
        with open('video_analyzer.py', 'r') as f:
            content = f.read()
        
        # Find the prompt section
        prompt_match = re.search(r'prompt = f"""(.*?)"""', content, re.DOTALL)
        
        if not prompt_match:
            print("❌ Could not find prompt in video_analyzer.py")
            return False
        
        prompt_text = prompt_match.group(1)
        print("📝 Found prompt in video_analyzer.py:")
        print("=" * 50)
        print(prompt_text[:500] + "..." if len(prompt_text) > 500 else prompt_text)
        print("=" * 50)
        
        # Check if incident_type is requested
        if 'incident_type' in prompt_text:
            print("✅ incident_type is requested in the prompt")
            
            # Check if it's in the JSON structure
            json_structure_match = re.search(r'\{\{.*?\}\}', prompt_text, re.DOTALL)
            if json_structure_match:
                json_structure = json_structure_match.group(0)
                print(f"\n📋 JSON structure requested:")
                print(json_structure)
                
                if 'incident_type' in json_structure:
                    print("✅ incident_type is included in JSON structure")
                    return True
                else:
                    print("❌ incident_type is mentioned but not in JSON structure")
                    return False
            else:
                print("⚠️  Could not find JSON structure in prompt")
                return False
        else:
            print("❌ incident_type is NOT requested in the prompt")
            return False
            
    except Exception as e:
        print(f"❌ Error reading video_analyzer.py: {e}")
        return False

def test_api_proxy_prompt():
    """Test that api_proxy.py prompt requests incident_type"""
    
    print("\n🧪 Testing api_proxy.py prompt for incident_type...\n")
    
    try:
        with open('api_proxy.py', 'r') as f:
            content = f.read()
        
        # Find the analyze_frame_for_security function
        func_match = re.search(r'def analyze_frame_for_security.*?return.*?}', content, re.DOTALL)
        
        if not func_match:
            print("❌ Could not find analyze_frame_for_security function")
            return False
        
        func_content = func_match.group(0)
        
        # Find the prompt in this function
        prompt_match = re.search(r'prompt = f"""(.*?)"""', func_content, re.DOTALL)
        
        if not prompt_match:
            print("❌ Could not find prompt in analyze_frame_for_security")
            return False
        
        prompt_text = prompt_match.group(1)
        print("📝 Found prompt in api_proxy.py analyze_frame_for_security:")
        print("=" * 50)
        print(prompt_text[:500] + "..." if len(prompt_text) > 500 else prompt_text)
        print("=" * 50)
        
        # Check if incident_type is requested
        if 'incident_type' in prompt_text:
            print("✅ incident_type is requested in the API proxy prompt")
            
            # Check if it's in the JSON structure
            json_structure_match = re.search(r'\{\{.*?\}\}', prompt_text, re.DOTALL)
            if json_structure_match:
                json_structure = json_structure_match.group(0)
                print(f"\n📋 JSON structure requested:")
                print(json_structure)
                
                if 'incident_type' in json_structure:
                    print("✅ incident_type is included in JSON structure")
                    return True
                else:
                    print("❌ incident_type is mentioned but not in JSON structure")
                    return False
            else:
                print("⚠️  Could not find JSON structure in prompt")
                return False
        else:
            print("❌ incident_type is NOT requested in the API proxy prompt")
            return False
            
    except Exception as e:
        print(f"❌ Error reading api_proxy.py: {e}")
        return False

def compare_prompts():
    """Compare prompts between video_analyzer.py and api_proxy.py"""
    
    print("\n🔍 Comparing prompts between files...\n")
    
    try:
        # Read both files
        with open('video_analyzer.py', 'r') as f:
            video_analyzer_content = f.read()
        
        with open('api_proxy.py', 'r') as f:
            api_proxy_content = f.read()
        
        # Extract prompts
        va_prompt_match = re.search(r'prompt = f"""(.*?)"""', video_analyzer_content, re.DOTALL)
        ap_prompt_match = re.search(r'def analyze_frame_for_security.*?prompt = f"""(.*?)"""', api_proxy_content, re.DOTALL)
        
        if not va_prompt_match or not ap_prompt_match:
            print("❌ Could not extract prompts from both files")
            return False
        
        va_prompt = va_prompt_match.group(1).strip()
        ap_prompt = ap_prompt_match.group(1).strip()
        
        # Compare JSON structures
        va_json_match = re.search(r'\{\{.*?\}\}', va_prompt, re.DOTALL)
        ap_json_match = re.search(r'\{\{.*?\}\}', ap_prompt, re.DOTALL)
        
        if va_json_match and ap_json_match:
            va_json = va_json_match.group(0)
            ap_json = ap_json_match.group(0)
            
            print("📋 video_analyzer.py JSON structure:")
            print(va_json)
            print("\n📋 api_proxy.py JSON structure:")
            print(ap_json)
            
            # Check if both include incident_type
            va_has_incident_type = 'incident_type' in va_json
            ap_has_incident_type = 'incident_type' in ap_json
            
            print(f"\n✅ video_analyzer.py includes incident_type: {va_has_incident_type}")
            print(f"✅ api_proxy.py includes incident_type: {ap_has_incident_type}")
            
            if va_has_incident_type and ap_has_incident_type:
                print("🎯 Both prompts now request incident_type!")
                return True
            else:
                print("❌ Prompts are inconsistent")
                return False
        else:
            print("❌ Could not extract JSON structures")
            return False
            
    except Exception as e:
        print(f"❌ Error comparing prompts: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Testing video_analyzer.py prompt fix...\n")
    
    # Test 1: video_analyzer.py prompt
    va_result = test_video_analyzer_prompt()
    
    # Test 2: api_proxy.py prompt
    ap_result = test_api_proxy_prompt()
    
    # Test 3: Compare prompts
    compare_result = compare_prompts()
    
    print(f"\n📋 Results:")
    print(f"  video_analyzer.py prompt: {'✅ PASS' if va_result else '❌ FAIL'}")
    print(f"  api_proxy.py prompt: {'✅ PASS' if ap_result else '❌ FAIL'}")
    print(f"  Prompt consistency: {'✅ PASS' if compare_result else '❌ FAIL'}")
    
    if va_result and ap_result and compare_result:
        print(f"\n🎉 SUCCESS: Both prompts now request incident_type!")
        print(f"   The incident_type should now appear in email subjects.")
    else:
        print(f"\n❌ ISSUES FOUND: Check the prompts and fix inconsistencies.")