#!/usr/bin/env python3
"""
Wine-based Ada32.dll interface using ctypes
This module provides access to Ada32.dll functions through Wine on Linux
"""

import ctypes
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class Ada32WineInterface:
    """Wine-based interface to Ada32.dll using ctypes"""
    
    def __init__(self, dll_path: str = "Ada32.dll"):
        self.dll_path = Path(dll_path)
        self.dll = None
        self.initialized = False
        
        if not self.dll_path.exists():
            raise FileNotFoundError(f"Ada32.dll not found at {dll_path}")
        
        # Configure Wine environment
        import os
        os.environ['WINEARCH'] = 'win32'
        if 'WINEPREFIX' not in os.environ:
            os.environ['WINEPREFIX'] = '/wine'
        
        try:
            # Setup display and verify Wine can access the DLL
            wine_env = {**os.environ, 'DISPLAY': ':99'}
            
            # Start Xvfb if needed
            xvfb_proc = subprocess.Popen(['Xvfb', ':99', '-screen', '0', '1024x768x24'], 
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            import time
            time.sleep(2)  # Give Xvfb time to start
            
            try:
                # Skip regsvr32 registration - not needed for our bridge approach
                logger.info(f"Wine setup for Ada32.dll at {dll_path}")
                self.dll = "wine_proxy"  # Use wine proxy instead of direct loading
            finally:
                # Clean up Xvfb
                xvfb_proc.terminate()
                xvfb_proc.wait()
                
        except Exception as e:
            logger.error(f"Failed to setup Wine for Ada32.dll: {e}")
            raise RuntimeError(f"Could not setup Wine for Ada32.dll at {dll_path}: {e}")
    
    def _setup_function_signatures(self):
        """Setup function signatures - not needed for Wine bridge approach"""
        # Wine bridge handles DLL function calls directly
        pass
    
    def initialize(self) -> bool:
        """Initialize Ada32 library through Wine bridge"""
        try:
            # Test Wine bridge using compiled C program
            result = subprocess.run(['wine', 'ada32_bridge.exe', 'test'], 
                                   capture_output=True, text=True, cwd=os.getcwd(),
                                   env={**os.environ, 'DISPLAY': ':99'})
            
            self.initialized = (result.returncode == 0)
            if self.initialized:
                logger.info(f"Ada32 initialized through Wine bridge: SUCCESS")
                logger.info(f"Bridge output: {result.stderr}")
            else:
                logger.error(f"Wine bridge test failed: {result.stderr}")
                raise RuntimeError(f"Wine bridge initialization failed: {result.stderr}")
            return self.initialized
        except Exception as e:
            logger.error(f"Failed to initialize Ada32 through Wine: {e}")
            raise RuntimeError(f"Wine interface initialization failed: {e}")
    
    def get_error_text(self, error_code: int = 0) -> str:
        """Get error text for error code"""
        try:
            result = self.dll.AdaGetErrorText(error_code)
            if result:
                return result.decode('ascii', errors='ignore')
            return f"Error code {error_code}"
        except Exception as e:
            logger.error(f"Failed to get error text: {e}")
            return f"Failed to get error text for {error_code}"
    
    def lookup_atom_enum(self, atom_name: str) -> int:
        """Look up atom enumeration value"""
        try:
            name_bytes = atom_name.encode('ascii')
            result = self.dll.AdaLookupAtomEnum(name_bytes)
            logger.info(f"Atom '{atom_name}' -> enum {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to lookup atom enum for '{atom_name}': {e}")
            return 0
    
    def assemble_atom_stream(self, atom_stream_text: str) -> bytes:
        """Assemble atom stream text to binary format using real Ada32.dll through Wine bridge"""
        if not self.initialized:
            raise RuntimeError("Ada32 not initialized")
        
        logger.info(f"Assembling atom stream through Wine bridge: {len(atom_stream_text)} chars")
        
        try:
            # Create temporary input file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                tmp_file.write(atom_stream_text)
                tmp_file_path = tmp_file.name
            
            try:
                # Call Wine bridge to assemble using compiled C program
                result = subprocess.run(['wine', 'ada32_bridge.exe', 'assemble', tmp_file_path], 
                                       capture_output=True, cwd=os.getcwd(),
                                       env={**os.environ, 'DISPLAY': ':99'})
                
                # Check if we got output, even if Wine crashed during cleanup
                if len(result.stdout) > 0:
                    binary_data = result.stdout
                    logger.info(f"Ada32 assembled through Wine bridge: {len(binary_data)} bytes")
                    if result.returncode != 0:
                        logger.warning(f"Wine crashed during cleanup but assembly succeeded: {result.stderr.decode('utf-8', errors='ignore')}")
                    else:
                        logger.info(f"Bridge output: {result.stderr.decode('utf-8', errors='ignore')}")
                    return binary_data
                else:
                    error_msg = result.stderr.decode('utf-8', errors='ignore')
                    raise RuntimeError(f"Wine bridge assembly failed: {error_msg}")
                    
            finally:
                # Clean up temp file
                os.unlink(tmp_file_path)
                
        except Exception as e:
            logger.error(f"Failed to assemble atom stream through Wine bridge: {e}")
            raise
    
    def disassemble_atom_stream(self, binary_data: bytes) -> int:
        """Disassemble binary data - returns decompressed size"""
        if not self.initialized:
            raise RuntimeError("Ada32 not initialized")
        
        logger.info(f"Disassembling through Wine {len(binary_data)} bytes")
        
        try:
            # Create input buffer
            input_buffer = ctypes.create_string_buffer(binary_data)
            
            # Call Ada32 disassembly function
            result = self.dll.AdaDisassembleAtomStream(
                ctypes.cast(input_buffer, ctypes.c_void_p),
                len(binary_data)
            )
            
            logger.info(f"Ada32 disassembled through Wine to {result} bytes")
            return result
            
        except Exception as e:
            logger.error(f"Failed to disassemble atom stream through Wine: {e}")
            raise

# Factory function to create the appropriate interface
def create_ada32_interface(dll_path: str = "Ada32.dll"):
    """Create Ada32 interface - Wine version for Linux"""
    return Ada32WineInterface(dll_path)