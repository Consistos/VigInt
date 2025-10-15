#!/usr/bin/env python3
"""
Example script demonstrating token counting for RTSP stream analysis

This script shows how to:
1. Track token usage during video analysis
2. Access token counts from analysis results
3. Calculate costs based on token usage
4. Monitor token consumption over time

Usage:
    python3 example_token_counting.py --video-path /path/to/video.mp4
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from video_analyzer import VideoAnalyzer
from multi_source_video_analyzer import MultiSourceVideoAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_video_with_token_tracking(video_path):
    """
    Analyze a video and track token usage
    
    Args:
        video_path: Path to video file for analysis
    """
    logger.info("=" * 60)
    logger.info("Token Counting Example - Video Analysis")
    logger.info("=" * 60)
    
    # Create video analyzer
    analyzer = VideoAnalyzer()
    
    # Track total tokens across all analyses
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    analysis_count = 0
    
    logger.info(f"\n📹 Analyzing video: {video_path}")
    logger.info(f"🔍 Token usage will be tracked for each frame analysis\n")
    
    # For demonstration, we'll analyze a few frames manually
    import cv2
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        logger.error(f"Failed to open video: {video_path}")
        return
    
    # Analyze first 3 frames as example
    frame_count = 0
    max_frames = 3
    
    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        analyzer.frame_count = frame_count + 1
        
        logger.info(f"📊 Analyzing frame {analyzer.frame_count}...")
        result = analyzer.analyze_frame(frame)
        
        if result and 'token_usage' in result:
            tokens = result['token_usage']
            analysis_count += 1
            
            # Accumulate token counts
            total_prompt_tokens += tokens['prompt_tokens']
            total_completion_tokens += tokens['completion_tokens']
            total_tokens += tokens['total_tokens']
            
            logger.info(f"  ✅ Frame {analyzer.frame_count} analyzed")
            logger.info(f"  📝 Prompt tokens: {tokens['prompt_tokens']}")
            logger.info(f"  💬 Completion tokens: {tokens['completion_tokens']}")
            logger.info(f"  🔢 Total tokens: {tokens['total_tokens']}")
            
            if result.get('incident_detected'):
                logger.warning(f"  🚨 Incident detected: {result['incident_type']}")
            else:
                logger.info(f"  ✓ No incident detected")
            
            logger.info("")
        
        frame_count += 1
    
    cap.release()
    
    # Print summary
    logger.info("=" * 60)
    logger.info("Token Usage Summary")
    logger.info("=" * 60)
    logger.info(f"Frames analyzed: {analysis_count}")
    logger.info(f"Total prompt tokens: {total_prompt_tokens}")
    logger.info(f"Total completion tokens: {total_completion_tokens}")
    logger.info(f"Total tokens used: {total_tokens}")
    
    # Calculate average tokens per analysis
    if analysis_count > 0:
        avg_tokens = total_tokens / analysis_count
        logger.info(f"Average tokens per frame: {avg_tokens:.1f}")
    
    # Estimate cost (Gemini pricing example - update with actual rates)
    # Note: These are example rates, check current Gemini API pricing
    COST_PER_1K_PROMPT_TOKENS = 0.000125  # $0.125 per 1M tokens
    COST_PER_1K_COMPLETION_TOKENS = 0.000375  # $0.375 per 1M tokens
    
    prompt_cost = (total_prompt_tokens / 1000) * COST_PER_1K_PROMPT_TOKENS
    completion_cost = (total_completion_tokens / 1000) * COST_PER_1K_COMPLETION_TOKENS
    total_cost = prompt_cost + completion_cost
    
    logger.info(f"\n💰 Estimated Cost:")
    logger.info(f"  Prompt cost: ${prompt_cost:.6f}")
    logger.info(f"  Completion cost: ${completion_cost:.6f}")
    logger.info(f"  Total cost: ${total_cost:.6f}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Token counting example completed!")
    logger.info("=" * 60)


def demonstrate_multi_source_token_tracking():
    """
    Demonstrate token tracking with multi-source video analyzer
    """
    logger.info("\n" + "=" * 60)
    logger.info("Multi-Source Token Tracking")
    logger.info("=" * 60)
    
    logger.info("""
Token counting is also available for multi-source video analysis:

1. Each camera source tracks its own token usage
2. Aggregated analyses (4+ cameras) also track tokens
3. Token usage is included in analysis results
4. Tokens are logged with camera/group identifiers

Example output:
  🔢 [Camera_1] Token usage - Prompt: 1247, Completion: 89, Total: 1336
  🔢 [group_1] Token usage - Prompt: 2891, Completion: 156, Total: 3047

Token data structure in analysis results:
  {
    'token_usage': {
      'prompt_tokens': 1247,
      'completion_tokens': 89,
      'total_tokens': 1336
    },
    'source_name': 'Camera_1',
    'incident_detected': false,
    ...
  }
""")


def show_token_tracking_features():
    """Display token tracking features"""
    logger.info("\n" + "=" * 60)
    logger.info("Token Tracking Features")
    logger.info("=" * 60)
    
    features = """
✅ Real-time Token Counting
   - Tracks tokens for every Gemini API call
   - Separate counts for prompt and completion
   - Logged immediately after each analysis

✅ Database Integration
   - Token counts stored in APIUsage table
   - Fields: prompt_tokens, completion_tokens, total_tokens
   - Available for billing and analytics

✅ Cost Calculation
   - Calculate costs based on token usage
   - Support for different pricing tiers
   - Include in invoices and reports

✅ Usage Analytics
   - Track token consumption over time
   - Identify high-usage periods
   - Optimize prompts to reduce tokens

✅ Multi-Source Support
   - Token tracking for individual cameras
   - Token tracking for aggregated analyses
   - Per-source and group-level metrics

📊 Token Data Usage:
   1. Billing: Include token counts in client invoices
   2. Monitoring: Track API usage and costs
   3. Optimization: Identify opportunities to reduce tokens
   4. Analytics: Understand usage patterns
   5. Budgeting: Forecast costs based on historical data
"""
    
    logger.info(features)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Demonstrate token counting for RTSP stream analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--video-path',
        type=str,
        help='Path to video file for analysis (optional)'
    )
    
    parser.add_argument(
        '--show-features',
        action='store_true',
        help='Show token tracking features'
    )
    
    args = parser.parse_args()
    
    # Show features
    show_token_tracking_features()
    
    # Demonstrate multi-source tracking
    demonstrate_multi_source_token_tracking()
    
    # Analyze video if path provided
    if args.video_path:
        if os.path.exists(args.video_path):
            analyze_video_with_token_tracking(args.video_path)
        else:
            logger.error(f"Video file not found: {args.video_path}")
    else:
        logger.info("\n💡 To analyze a video with token tracking, run:")
        logger.info("   python3 example_token_counting.py --video-path /path/to/video.mp4")
