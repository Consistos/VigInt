#!/usr/bin/env python3
"""
Debug configuration reading issue
"""

import os
import sys
import configparser
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_direct_config_reading():
    """Test reading config.ini directly"""
    print("🔧 Testing Direct Config Reading")
    print("=" * 50)
    
    config_path = Path("config.ini")
    if not config_path.exists():
        print(f"❌ config.ini not found at {config_path.absolute()}")
        return False
    
    print(f"✅ Found config.ini at {config_path.absolute()}")
    
    # Read with configparser directly
    parser = configparser.ConfigParser()
    parser.read(config_path)
    
    print(f"\nSections found: {parser.sections()}")
    
    if 'Email' in parser.sections():
        print(f"\nEmail section keys: {list(parser['Email'].keys())}")
        
        for key in parser['Email']:
            value = parser['Email'][key]
            if 'password' in key.lower():
                display_value = '*' * len(value) if value else 'EMPTY'
            else:
                display_value = value if value else 'EMPTY'
            print(f"  {key}: {display_value}")
    else:
        print("❌ No Email section found")
        return False
    
    return True


def test_config_module():
    """Test the config module"""
    print("\n🔧 Testing Config Module")
    print("=" * 50)
    
    try:
        from config import config
        
        print(f"Config file loaded from: {config.config._sections}")
        
        # Test direct access to config parser
        if hasattr(config.config, '_sections') and 'Email' in config.config._sections:
            email_section = config.config._sections['Email']
            print(f"\nEmail section from config parser:")
            for key, value in email_section.items():
                if 'password' in key.lower():
                    display_value = '*' * len(value) if value else 'EMPTY'
                else:
                    display_value = value if value else 'EMPTY'
                print(f"  {key}: {display_value}")
        
        # Test get method
        print(f"\nTesting config.get() method:")
        test_keys = ['sender_email', 'sender_password', 'admin_email']
        for key in test_keys:
            value = config.get('Email', key, 'NOT_FOUND')
            if 'password' in key.lower():
                display_value = '*' * len(str(value)) if value != 'NOT_FOUND' else 'NOT_FOUND'
            else:
                display_value = value
            print(f"  {key}: {display_value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing config module: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_file_paths():
    """Test which config file is being loaded"""
    print("\n🔧 Testing Config File Paths")
    print("=" * 50)
    
    # Check environment variables
    config_path = os.environ.get('VIGINT_CONFIG_PATH')
    server_config_path = os.environ.get('VIGINT_SERVER_CONFIG_PATH')
    
    print(f"VIGINT_CONFIG_PATH: {config_path or 'NOT_SET'}")
    print(f"VIGINT_SERVER_CONFIG_PATH: {server_config_path or 'NOT_SET'}")
    
    # Check file existence
    script_dir = Path(__file__).parent
    server_config = script_dir / 'server_config.ini'
    dev_config = script_dir / 'config.ini'
    
    print(f"\nConfig file paths:")
    print(f"  server_config.ini: {'✅ EXISTS' if server_config.exists() else '❌ NOT FOUND'}")
    print(f"  config.ini: {'✅ EXISTS' if dev_config.exists() else '❌ NOT FOUND'}")
    
    # Determine which file would be loaded
    if server_config_path and os.path.exists(server_config_path):
        loaded_file = server_config_path
    elif config_path and os.path.exists(config_path):
        loaded_file = config_path
    elif server_config.exists():
        loaded_file = str(server_config)
    elif dev_config.exists():
        loaded_file = str(dev_config)
    else:
        loaded_file = "NONE"
    
    print(f"\nConfig file that would be loaded: {loaded_file}")
    
    return loaded_file != "NONE"


def fix_config_issue():
    """Attempt to fix the config issue"""
    print("\n🔧 Attempting to Fix Config Issue")
    print("=" * 50)
    
    # Force reload the config module
    try:
        import importlib
        import config
        importlib.reload(config)
        
        # Test again
        from config import config as reloaded_config
        
        sender_email = reloaded_config.get('Email', 'sender_email', 'NOT_FOUND')
        sender_password = reloaded_config.get('Email', 'sender_password', 'NOT_FOUND')
        admin_email = reloaded_config.get('Email', 'admin_email', 'NOT_FOUND')
        
        print(f"After reload:")
        print(f"  sender_email: {sender_email}")
        print(f"  sender_password: {'*' * len(sender_password) if sender_password != 'NOT_FOUND' else 'NOT_FOUND'}")
        print(f"  admin_email: {admin_email}")
        
        if sender_email != 'NOT_FOUND' and sender_password != 'NOT_FOUND' and admin_email != 'NOT_FOUND':
            print("✅ Config issue appears to be fixed!")
            return True
        else:
            print("❌ Config issue persists after reload")
            return False
            
    except Exception as e:
        print(f"❌ Error during config reload: {e}")
        return False


def main():
    """Main debug function"""
    print("🔍 Configuration Debug Tool")
    print("=" * 60)
    
    tests = [
        test_direct_config_reading,
        test_config_file_paths,
        test_config_module,
        fix_config_issue
    ]
    
    for test_func in tests:
        try:
            result = test_func()
            if not result:
                print(f"❌ {test_func.__name__} failed")
        except Exception as e:
            print(f"❌ {test_func.__name__} failed with exception: {e}")


if __name__ == '__main__':
    main()