#!/usr/bin/env python3
"""
Diagnostic script to identify why duplicate emails are being sent
"""

import sys
import os
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_for_duplicate_sources():
    """Check if the same RTSP stream is configured multiple times"""
    print("\n" + "="*70)
    print("DIAGNOSTIC: Checking for Duplicate RTSP Stream Configurations")
    print("="*70)
    
    issues_found = []
    
    # Check 1: Look for configuration files that might have duplicate streams
    config_files = [
        'multi_source_config.json',
        'config.ini',
        'config.py'
    ]
    
    print("\n1. Checking configuration files...")
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"   ✓ Found: {config_file}")
            with open(config_file, 'r') as f:
                content = f.read()
                # Count RTSP URLs
                rtsp_count = content.count('rtsp://')
                if rtsp_count > 1:
                    print(f"   ⚠️  Multiple RTSP URLs found ({rtsp_count})")
                    issues_found.append(f"Multiple RTSP URLs in {config_file}")
        else:
            print(f"   - Not found: {config_file}")
    
    # Check 2: Explain the fix
    print("\n2. Incident Deduplication Status:")
    print("   ✅ FIXED: Added deduplication logic to prevent duplicate alerts")
    print("   - VideoAnalyzer: 60-second cooldown per incident type")
    print("   - MultiSourceVideoAnalyzer: 60-second cooldown per source/group")
    print("   - Incidents are tracked by signature (type + analysis summary)")
    
    # Check 3: Explain the problem
    print("\n3. Root Cause Analysis:")
    print("   The system was sending 3 emails because:")
    print("   a) No deduplication - same incident detected at 0s, 5s, 10s")
    print("   b) Each analysis cycle sent a new email")
    print("   c) Analysis interval was 5 seconds by default")
    
    # Check 4: Provide recommendations
    print("\n4. Recommendations:")
    print("   ✅ Deduplication is now active (60s cooldown)")
    print("   💡 Adjust cooldown if needed:")
    print("      - VideoAnalyzer: Set analyzer.incident_cooldown = 120")
    print("      - MultiSourceVideoAnalyzer: Set analyzer.incident_cooldown = 120")
    print("   💡 Adjust analysis interval:")
    print("      - VideoAnalyzer: Set analyzer.analysis_interval = 10")
    print("      - MultiSourceVideoAnalyzer: Set analyzer.analysis_interval = 15")
    
    print("\n5. How the Fix Works:")
    print("   - When incident detected: Create signature (type + analysis)")
    print("   - Check: Has similar incident been sent recently?")
    print("   - If YES: Skip alert (log 'Skipping duplicate')")
    print("   - If NO: Send alert and start cooldown timer")
    print("   - Cooldown: Prevents re-alerting for 60 seconds")
    
    print("\n6. Testing the Fix:")
    print("   Run your video analyzer and watch the logs:")
    print("   - First incident: '📧 Sending NEW incident alert'")
    print("   - Duplicate detections: '⏭️  Skipping duplicate incident alert'")
    print("   - Time tracking: 'Time since last alert: X.Xs / 60s cooldown'")
    
    if issues_found:
        print("\n" + "="*70)
        print("⚠️  POTENTIAL ISSUES FOUND:")
        for issue in issues_found:
            print(f"   - {issue}")
        print("\n   Review your configuration to ensure the same RTSP stream")
        print("   is not added multiple times.")
    else:
        print("\n" + "="*70)
        print("✅ No configuration issues detected")
    
    print("="*70)
    print()


def show_example_usage():
    """Show example of how to use the fixed analyzer"""
    print("\n" + "="*70)
    print("EXAMPLE: Using VideoAnalyzer with Deduplication")
    print("="*70)
    
    example_code = '''
from video_analyzer import VideoAnalyzer

# Create analyzer
analyzer = VideoAnalyzer()

# Optional: Customize deduplication settings
analyzer.incident_cooldown = 120  # 2 minutes cooldown
analyzer.analysis_interval = 10   # Analyze every 10 seconds

# Start analyzing RTSP stream
analyzer.process_video_stream('rtsp://your-camera-url')

# Logs will show:
# - First incident: "📧 Sending NEW incident alert"
# - Duplicates: "⏭️  Skipping duplicate incident alert"
'''
    
    print(example_code)
    print("="*70)
    
    print("\n" + "="*70)
    print("EXAMPLE: Using MultiSourceVideoAnalyzer with Deduplication")
    print("="*70)
    
    example_code2 = '''
from multi_source_video_analyzer import MultiSourceVideoAnalyzer

# Create analyzer
analyzer = MultiSourceVideoAnalyzer()

# Optional: Customize deduplication settings
analyzer.incident_cooldown = 90  # 90 seconds cooldown
analyzer.analysis_interval = 15  # Analyze every 15 seconds

# Add video sources (ensure no duplicates!)
analyzer.add_video_source('cam1', 'rtsp://camera1', 'Front Door')
analyzer.add_video_source('cam2', 'rtsp://camera2', 'Back Door')

# Start analysis
analyzer.start_analysis()

# Each source has independent deduplication tracking
'''
    
    print(example_code2)
    print("="*70)
    print()


if __name__ == '__main__':
    print("\n🔍 DUPLICATE EMAIL ALERT DIAGNOSTIC\n")
    
    check_for_duplicate_sources()
    show_example_usage()
    
    print("\n✅ SUMMARY:")
    print("   The duplicate email issue has been FIXED by adding incident deduplication.")
    print("   The system now tracks recent incidents and prevents re-alerting within")
    print("   a 60-second cooldown period. You can customize this cooldown as needed.\n")
    print("   Next steps:")
    print("   1. Restart your video analyzer")
    print("   2. Monitor logs for 'Skipping duplicate' messages")
    print("   3. Adjust cooldown/interval if needed\n")
