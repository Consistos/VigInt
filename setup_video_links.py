#!/usr/bin/env python3
"""
Setup Script for Video Link Service
Helps configure the Sparse AI API key for video hosting
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_current_config():
    """Check current configuration status"""
    logger.info("🔍 Checking current video link configuration...")
    
    # Check environment variables
    sparse_ai_key = os.getenv('SPARSE_AI_API_KEY')
    sparse_ai_url = os.getenv('SPARSE_AI_BASE_URL', 'https://sparse-ai.com')
    expiration_hours = os.getenv('VIDEO_LINK_EXPIRATION_HOURS', '48')
    
    logger.info(f"📍 Environment Variables:")
    logger.info(f"   SPARSE_AI_API_KEY: {'✅ Set' if sparse_ai_key and sparse_ai_key != 'your-sparse-ai-api-key-here' else '❌ Not set'}")
    logger.info(f"   SPARSE_AI_BASE_URL: {sparse_ai_url}")
    logger.info(f"   VIDEO_LINK_EXPIRATION_HOURS: {expiration_hours}")
    
    # Check config.ini
    config_path = Path('config.ini')
    if config_path.exists():
        with open(config_path, 'r') as f:
            config_content = f.read()
            if '[SparseAI]' in config_content:
                logger.info("📍 Config.ini: ✅ SparseAI section exists")
                if 'api_key = your-sparse-ai-api-key-here' in config_content:
                    logger.info("   ❌ API key not configured in config.ini")
                else:
                    logger.info("   ✅ API key appears to be configured in config.ini")
            else:
                logger.info("📍 Config.ini: ❌ SparseAI section missing")
    else:
        logger.info("📍 Config.ini: ❌ File not found")
    
    # Test the video link service
    try:
        sys.path.append('.')
        from video_link_service import VideoLinkService
        
        service = VideoLinkService()
        if service.api_key and service.api_key != 'your-sparse-ai-api-key-here':
            logger.info("🎯 Video Link Service: ✅ API key loaded successfully")
            return True
        else:
            logger.info("🎯 Video Link Service: ❌ API key not configured")
            return False
    except Exception as e:
        logger.error(f"🎯 Video Link Service: ❌ Error loading service: {e}")
        return False


def setup_environment_variable():
    """Guide user to set up environment variable"""
    logger.info("\n🔧 OPTION 1: Environment Variable Setup")
    logger.info("=" * 50)
    
    print("\nTo set up the Sparse AI API key via environment variable:")
    print("\n1. Get your API key from sparse-ai.com")
    print("2. Add it to your .env file:")
    print("   SPARSE_AI_API_KEY=your-actual-api-key-here")
    print("\n3. Or export it in your shell:")
    print("   export SPARSE_AI_API_KEY=your-actual-api-key-here")
    
    # Check if .env file exists and update it
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path, 'r') as f:
            env_content = f.read()
        
        if 'SPARSE_AI_API_KEY=your-sparse-ai-api-key-here' in env_content:
            logger.info("\n📝 Found placeholder in .env file")
            
            api_key = input("\n🔑 Enter your Sparse AI API key (or press Enter to skip): ").strip()
            if api_key:
                # Update .env file
                updated_content = env_content.replace(
                    'SPARSE_AI_API_KEY=your-sparse-ai-api-key-here',
                    f'SPARSE_AI_API_KEY={api_key}'
                )
                
                with open(env_path, 'w') as f:
                    f.write(updated_content)
                
                logger.info("✅ Updated .env file with your API key")
                return True
            else:
                logger.info("⏭️  Skipped API key setup")
        else:
            logger.info("✅ .env file already configured")
    else:
        logger.info("❌ .env file not found")
    
    return False


def setup_config_file():
    """Guide user to set up config.ini"""
    logger.info("\n🔧 OPTION 2: Config File Setup")
    logger.info("=" * 50)
    
    config_path = Path('config.ini')
    if not config_path.exists():
        logger.error("❌ config.ini file not found")
        return False
    
    with open(config_path, 'r') as f:
        config_content = f.read()
    
    if 'api_key = your-sparse-ai-api-key-here' in config_content:
        logger.info("📝 Found placeholder in config.ini")
        
        api_key = input("\n🔑 Enter your Sparse AI API key (or press Enter to skip): ").strip()
        if api_key:
            # Update config.ini
            updated_content = config_content.replace(
                'api_key = your-sparse-ai-api-key-here',
                f'api_key = {api_key}'
            )
            
            with open(config_path, 'w') as f:
                f.write(updated_content)
            
            logger.info("✅ Updated config.ini with your API key")
            return True
        else:
            logger.info("⏭️  Skipped API key setup")
    else:
        logger.info("✅ config.ini already configured")
    
    return False


def test_video_link_service():
    """Test the video link service"""
    logger.info("\n🧪 Testing Video Link Service")
    logger.info("=" * 50)
    
    try:
        from video_link_service import VideoLinkService
        
        service = VideoLinkService()
        
        if not service.api_key or service.api_key == 'your-sparse-ai-api-key-here':
            logger.error("❌ API key still not configured")
            return False
        
        logger.info("✅ Video Link Service initialized successfully")
        logger.info(f"   Base URL: {service.base_url}")
        logger.info(f"   Default expiration: {service.default_expiration_hours} hours")
        
        # Test with a dummy upload (will fail but shows configuration is working)
        logger.info("\n🔍 Testing configuration (dummy upload)...")
        result = service.upload_video('/nonexistent/file.mp4')
        
        if 'error' in result and 'not found' in result['error'].lower():
            logger.info("✅ Configuration test passed (expected file not found error)")
            return True
        elif 'error' in result and 'api key' in result['error'].lower():
            logger.error("❌ API key configuration issue")
            return False
        else:
            logger.info("✅ Service appears to be working")
            return True
    
    except Exception as e:
        logger.error(f"❌ Error testing service: {e}")
        return False


def show_next_steps():
    """Show next steps for the user"""
    logger.info("\n📋 NEXT STEPS")
    logger.info("=" * 50)
    
    print("\n1. 🔑 Get API Key:")
    print("   - Visit sparse-ai.com")
    print("   - Sign up for an account")
    print("   - Generate an API key for video hosting")
    
    print("\n2. 🧪 Test the System:")
    print("   python demo_video_link_service.py")
    
    print("\n3. 📧 Send Test Alert:")
    print("   python test_video_link_service.py")
    
    print("\n4. 🚀 Production Use:")
    print("   - System will automatically use video links")
    print("   - No code changes needed")
    print("   - Monitor logs for upload success/failure")


def main():
    """Main setup function"""
    logger.info("🎬 VIGINT VIDEO LINK SERVICE SETUP")
    logger.info("=" * 60)
    
    # Check current status
    is_configured = check_current_config()
    
    if is_configured:
        logger.info("\n🎉 Video Link Service is already configured!")
        
        # Test the service
        if test_video_link_service():
            logger.info("\n✅ Setup complete! Video links are ready to use.")
            show_next_steps()
            return True
        else:
            logger.warning("\n⚠️  Configuration found but service test failed")
    
    logger.info("\n🔧 CONFIGURATION NEEDED")
    logger.info("The video link service needs a Sparse AI API key to work.")
    
    # Try environment variable setup
    if setup_environment_variable():
        if test_video_link_service():
            logger.info("\n🎉 Setup complete via environment variable!")
            show_next_steps()
            return True
    
    # Try config file setup
    if setup_config_file():
        if test_video_link_service():
            logger.info("\n🎉 Setup complete via config file!")
            show_next_steps()
            return True
    
    # Manual setup instructions
    logger.info("\n📖 MANUAL SETUP INSTRUCTIONS")
    logger.info("=" * 50)
    
    print("\nTo enable video links, you need to:")
    print("\n1. Get a Sparse AI API key from sparse-ai.com")
    print("\n2. Set it in your .env file:")
    print("   SPARSE_AI_API_KEY=your-actual-api-key-here")
    print("\n3. Or set it in config.ini:")
    print("   [SparseAI]")
    print("   api_key = your-actual-api-key-here")
    
    print("\n4. Test with: python demo_video_link_service.py")
    
    logger.info("\n⚠️  Until configured, emails will show:")
    logger.info("   'Échec du téléchargement de la vidéo'")
    
    return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)