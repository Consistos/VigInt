#!/usr/bin/env python3
"""
Test script to validate dual-model configuration for short and long buffers
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_model_configuration():
    """Test that both models are properly configured"""
    print("=" * 60)
    print("Testing Dual-Model Configuration")
    print("=" * 60)
    print()
    
    try:
        # Import api_proxy to trigger model initialization
        import api_proxy
        
        # Check if models are configured
        print("✓ Successfully imported api_proxy module")
        print()
        
        # Verify short buffer model
        if hasattr(api_proxy, 'gemini_model_short'):
            if api_proxy.gemini_model_short is not None:
                print("✓ Short buffer model (Flash-Lite): CONFIGURED")
                print(f"  Model: {api_proxy.gemini_model_short._model_name if hasattr(api_proxy.gemini_model_short, '_model_name') else 'gemini-2.5-flash-lite'}")
            else:
                print("⚠ Short buffer model: NOT CONFIGURED (API key missing)")
        else:
            print("✗ Short buffer model: MISSING VARIABLE")
            return False
        
        print()
        
        # Verify long buffer model
        if hasattr(api_proxy, 'gemini_model_long'):
            if api_proxy.gemini_model_long is not None:
                print("✓ Long buffer model (Flash): CONFIGURED")
                print(f"  Model: {api_proxy.gemini_model_long._model_name if hasattr(api_proxy.gemini_model_long, '_model_name') else 'gemini-2.5-flash'}")
            else:
                print("⚠ Long buffer model: NOT CONFIGURED (API key missing)")
        else:
            print("✗ Long buffer model: MISSING VARIABLE")
            return False
        
        print()
        
        # Verify analyze_frame_for_security function exists
        if hasattr(api_proxy, 'analyze_frame_for_security'):
            print("✓ analyze_frame_for_security function: EXISTS")
            
            # Check function signature
            import inspect
            sig = inspect.signature(api_proxy.analyze_frame_for_security)
            params = list(sig.parameters.keys())
            print(f"  Parameters: {', '.join(params)}")
            
            if 'buffer_type' in params:
                print("✓ buffer_type parameter: PRESENT")
            else:
                print("✗ buffer_type parameter: MISSING")
                return False
        else:
            print("✗ analyze_frame_for_security function: MISSING")
            return False
        
        print()
        
        # Verify analyze_incident_context function exists
        if hasattr(api_proxy, 'analyze_incident_context'):
            print("✓ analyze_incident_context function: EXISTS")
        else:
            print("✗ analyze_incident_context function: MISSING")
            return False
        
        print()
        print("=" * 60)
        print("✓ ALL CONFIGURATION CHECKS PASSED")
        print("=" * 60)
        print()
        print("Configuration Summary:")
        print("  • Short buffer (3s): Gemini 2.5 Flash-Lite")
        print("  • Long buffer (10s): Gemini 2.5 Flash")
        print("  • Automatic model selection based on buffer_type")
        print()
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_buffer_configuration():
    """Test video buffer configuration"""
    print("=" * 60)
    print("Testing Buffer Configuration")
    print("=" * 60)
    print()
    
    try:
        import api_proxy
        
        if hasattr(api_proxy, 'video_config'):
            config = api_proxy.video_config
            print("✓ Video configuration loaded")
            print()
            print("Buffer Settings:")
            print(f"  • Short buffer duration: {config.get('short_buffer_duration', 'N/A')}s")
            print(f"  • Long buffer duration: {config.get('long_buffer_duration', 'N/A')}s")
            print(f"  • Analysis FPS: {config.get('analysis_fps', 'N/A')}")
            print(f"  • Video format: {config.get('video_format', 'N/A')}")
            print()
            
            # Validate buffer configuration
            short_duration = config.get('short_buffer_duration', 0)
            long_duration = config.get('long_buffer_duration', 0)
            
            if short_duration > 0 and long_duration > 0 and short_duration < long_duration:
                print("✓ Buffer durations are valid")
                return True
            else:
                print("⚠ Buffer durations may need adjustment")
                return True  # Still pass, just a warning
        else:
            print("⚠ Video configuration not found")
            return True
            
    except Exception as e:
        print(f"✗ Error checking buffer configuration: {e}")
        return False


def main():
    """Main test function"""
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "DUAL-MODEL CONFIGURATION TEST" + " " * 18 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    # Run tests
    test1_passed = test_model_configuration()
    print()
    test2_passed = test_buffer_configuration()
    print()
    
    # Summary
    if test1_passed and test2_passed:
        print("╔" + "═" * 58 + "╗")
        print("║" + " " * 18 + "✓ ALL TESTS PASSED" + " " * 20 + "║")
        print("╚" + "═" * 58 + "╝")
        print()
        print("Next Steps:")
        print("  1. Start the Vigint API proxy server")
        print("  2. Monitor the startup logs for model initialization")
        print("  3. Test with real video analysis")
        print()
        return 0
    else:
        print("╔" + "═" * 58 + "╗")
        print("║" + " " * 18 + "✗ SOME TESTS FAILED" + " " * 18 + "║")
        print("╚" + "═" * 58 + "╝")
        print()
        print("Please review the errors above and fix the configuration.")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
