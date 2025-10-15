"""Configuration management for Vigint application"""

import os
import configparser
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class"""
    
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """Load configuration from files"""
        # Determine which config file to use
        config_path = os.environ.get('VIGINT_CONFIG_PATH')
        server_config_path = os.environ.get('VIGINT_SERVER_CONFIG_PATH')
        
        if server_config_path and os.path.exists(server_config_path):
            self.config.read(server_config_path)
        elif config_path and os.path.exists(config_path):
            self.config.read(config_path)
        else:
            # Default paths
            script_dir = Path(__file__).parent
            server_config = script_dir / 'server_config.ini'
            dev_config = script_dir / 'config.ini'
            
            if server_config.exists():
                self.config.read(server_config)
            elif dev_config.exists():
                self.config.read(dev_config)
            else:
                raise FileNotFoundError("No configuration file found. Please create config.ini or server_config.ini")
    
    def get(self, section, key, fallback=None):
        """Get configuration value"""
        return self.config.get(section, key, fallback=fallback)
    
    def getint(self, section, key, fallback=None):
        """Get integer configuration value"""
        return self.config.getint(section, key, fallback=fallback)
    
    def getboolean(self, section, key, fallback=None):
        """Get boolean configuration value"""
        return self.config.getboolean(section, key, fallback=fallback)
    
    @property
    def database_url(self):
        """Get database URL"""
        return self.get('Database', 'database_url', 'sqlite:///vigint.db')
    
    @property
    def secret_key(self):
        """Get API secret key"""
        return self.get('API', 'secret_key', 'dev-secret-key')
    
    @property
    def debug(self):
        """Get debug mode"""
        return self.getboolean('API', 'debug', False)
    
    @property
    def host(self):
        """Get host"""
        return self.get('API', 'host', '0.0.0.0')
    
    @property
    def port(self):
        """Get port"""
        return self.getint('API', 'port', 5000)


# Global config instance
config = Config()