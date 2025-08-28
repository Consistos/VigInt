"""RTSP Server implementation for Vigint video streaming"""

import os
import subprocess
import signal
import time
import logging
from pathlib import Path
from config import config


class RTSPServer:
    """RTSP Server manager using MediaMTX"""
    
    def __init__(self):
        self.process = None
        self.config_file = "mediamtx_no_auth.yml"
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start the RTSP server"""
        try:
            # Check if MediaMTX binary exists
            mediamtx_path = self._find_mediamtx_binary()
            if not mediamtx_path:
                raise FileNotFoundError("MediaMTX binary not found")
            
            # Start MediaMTX with configuration
            cmd = [mediamtx_path, self.config_file]
            self.logger.info(f"Starting RTSP server with command: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            # Wait a moment to check if it started successfully
            time.sleep(3)
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                self.logger.error(f"MediaMTX stdout: {stdout.decode()}")
                self.logger.error(f"MediaMTX stderr: {stderr.decode()}")
                raise RuntimeError(f"RTSP server failed to start: {stderr.decode()}")
            
            self.logger.info(f"RTSP server started with PID: {self.process.pid}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start RTSP server: {e}")
            return False
    
    def stop(self):
        """Stop the RTSP server"""
        if self.process:
            try:
                if os.name == 'nt':  # Windows
                    self.process.terminate()
                else:  # Unix-like
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't stop gracefully
                    if os.name == 'nt':
                        self.process.kill()
                    else:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                
                self.logger.info("RTSP server stopped")
                self.process = None
                return True
                
            except Exception as e:
                self.logger.error(f"Error stopping RTSP server: {e}")
                return False
        
        return True
    
    def is_running(self):
        """Check if the RTSP server is running"""
        if self.process:
            return self.process.poll() is None
        return False
    
    def restart(self):
        """Restart the RTSP server"""
        self.logger.info("Restarting RTSP server")
        self.stop()
        time.sleep(2)
        return self.start()
    
    def get_status(self):
        """Get server status information"""
        return {
            'running': self.is_running(),
            'pid': self.process.pid if self.process else None,
            'config_file': self.config_file
        }
    
    def _find_mediamtx_binary(self):
        """Find MediaMTX binary in common locations"""
        possible_paths = [
            './mediamtx',
            './bin/mediamtx',
            '/usr/local/bin/mediamtx',
            '/usr/bin/mediamtx',
            'mediamtx'  # In PATH
        ]
        
        for path in possible_paths:
            if Path(path).exists() or self._command_exists(path):
                return path
        
        return None
    
    def _command_exists(self, command):
        """Check if a command exists in PATH"""
        try:
            subprocess.run([command, '--help'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, 
                         check=False)
            return True
        except FileNotFoundError:
            return False


def create_stream_endpoint(stream_name, source_url):
    """Create a new stream endpoint"""
    # This would typically update the MediaMTX configuration
    # For now, we'll just log the action
    logging.info(f"Creating stream endpoint: {stream_name} -> {source_url}")
    return True


def remove_stream_endpoint(stream_name):
    """Remove a stream endpoint"""
    logging.info(f"Removing stream endpoint: {stream_name}")
    return True


def list_active_streams():
    """List all active streams"""
    # This would query MediaMTX API for active streams
    # For now, return a placeholder
    return {
        'streams': [],
        'total': 0
    }


def get_stream_stats(stream_name):
    """Get statistics for a specific stream"""
    # This would query MediaMTX API for stream statistics
    return {
        'stream_name': stream_name,
        'viewers': 0,
        'bitrate': 0,
        'uptime': 0
    }


# Global RTSP server instance
rtsp_server = RTSPServer()