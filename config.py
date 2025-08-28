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
        """Get configuration value with environment variable substitution"""
        value = self.config.get(section, key, fallback=fallback)
        if value and isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]  # Remove ${ and }
            return os.getenv(env_var, fallback)
        return value
    
    def getint(self, section, key, fallback=None):
        """Get integer configuration value"""
        return self.config.getint(section, key, fallback=fallback)
    
    def getboolean(self, section, key, fallback=None):
        """Get boolean configuration value"""
        return self.config.getboolean(section, key, fallback=fallback)
    
    def getfloat(self, section, key, fallback=None):
        """Get float configuration value"""
        return self.config.getfloat(section, key, fallback=fallback)
    
    @property
    def database_url(self):
        """Get database URL"""
        return self.get('Database', 'database_url', 'sqlite:///vigint.db')
    
    @property
    def secret_key(self):
        """Get API secret key"""
        return os.getenv('SECRET_KEY') or self.get('API', 'secret_key', 'dev-secret-key')
    
    @property
    def gemini_api_key(self):
        """Get Gemini API key"""
        return os.getenv('GOOGLE_API_KEY') or self.get('AI', 'gemini_api_key', None)
    
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
    
    # VideoAnalysis configuration properties
    @property
    def short_buffer_duration(self):
        """Get short buffer duration in seconds"""
        return self.getint('VideoAnalysis', 'short_buffer_duration', 3)
    
    @property
    def long_buffer_duration(self):
        """Get long buffer duration in seconds"""
        return self.getint('VideoAnalysis', 'long_buffer_duration', 10)
    
    @property
    def analysis_fps(self):
        """Get analysis FPS"""
        return self.getint('VideoAnalysis', 'analysis_fps', 25)
    
    @property
    def video_format(self):
        """Get video format"""
        return self.get('VideoAnalysis', 'video_format', 'mp4')
    
    @property
    def compression_quality(self):
        """Get compression quality (0.1 = high compression, 0.9 = minimal compression)"""
        return self.getfloat('VideoAnalysis', 'compression_quality', 0.85)
    
    @property
    def max_email_size_mb(self):
        """Get maximum email attachment size in MB"""
        return self.getint('VideoAnalysis', 'max_email_size_mb', 20)
    
    @property
    def preferred_codec(self):
        """Get preferred video codec"""
        return self.get('VideoAnalysis', 'preferred_codec', 'H264')
    
    def get_buffer_config(self):
        """Get buffer configuration as a dictionary"""
        return {
            'short_buffer_duration': self.short_buffer_duration,
            'long_buffer_duration': self.long_buffer_duration,
            'analysis_fps': self.analysis_fps,
            'video_format': self.video_format,
            'compression_quality': self.compression_quality,
            'max_email_size_mb': self.max_email_size_mb,
            'preferred_codec': self.preferred_codec
        }
    
    def validate_buffer_config(self):
        """Validate buffer configuration settings"""
        errors = []
        
        short_duration = self.short_buffer_duration
        long_duration = self.long_buffer_duration
        fps = self.analysis_fps
        video_format = self.video_format
        compression_quality = self.compression_quality
        max_email_size_mb = self.max_email_size_mb
        preferred_codec = self.preferred_codec
        
        # Validate buffer durations
        if short_duration <= 0:
            errors.append("short_buffer_duration must be greater than 0")
        
        if long_duration <= 0:
            errors.append("long_buffer_duration must be greater than 0")
        
        if short_duration >= long_duration:
            errors.append("short_buffer_duration must be less than long_buffer_duration")
        
        # Validate FPS
        if fps <= 0:
            errors.append("analysis_fps must be greater than 0")
        
        if fps > 60:
            errors.append("analysis_fps should not exceed 60 for optimal performance")
        
        # Validate video format
        supported_formats = ['mp4', 'avi', 'mov', 'mkv']
        if video_format.lower() not in supported_formats:
            errors.append(f"video_format must be one of: {', '.join(supported_formats)}")
        
        # Validate compression quality
        if compression_quality <= 0 or compression_quality > 1:
            errors.append("compression_quality must be between 0.1 and 1.0")
        
        # Validate email size limit
        if max_email_size_mb <= 0:
            errors.append("max_email_size_mb must be greater than 0")
        
        if max_email_size_mb > 100:
            errors.append("max_email_size_mb should not exceed 100 MB for email compatibility")
        
        # Validate codec
        supported_codecs = ['H264', 'avc1', 'X264', 'mp4v', 'XVID']
        if preferred_codec not in supported_codecs:
            errors.append(f"preferred_codec must be one of: {', '.join(supported_codecs)}")
        
        if errors:
            raise ValueError(f"Buffer configuration validation failed: {'; '.join(errors)}")
        
        return True


# Global config instance
config = Config()