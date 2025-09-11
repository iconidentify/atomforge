#!/usr/bin/env python3
"""
Windows-specific Ada32.dll interface using ctypes
This module provides direct access to the real Ada32.dll functions on Windows
"""

import ctypes
import logging
import struct
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class Ada32WindowsInterface:
    """Direct interface to Ada32.dll on Windows using ctypes"""
    
    def __init__(self, dll_path: str = "Ada32.dll"):
        self.dll_path = Path(dll_path)
        self.dll = None
        self.initialized = False
        
        if not self.dll_path.exists():
            raise FileNotFoundError(f"Ada32.dll not found at {dll_path}")
        
        try:
            # Load 32-bit DLL - use CDLL for proper calling convention
            self.dll = ctypes.CDLL(str(self.dll_path))
            self._setup_function_signatures()
            logger.info(f"Successfully loaded 32-bit Ada32.dll from {dll_path}")
        except Exception as e:
            logger.error(f"Failed to load 32-bit Ada32.dll: {e}")
            raise RuntimeError(f"Could not load Ada32.dll at {dll_path}: {e}")
    
    def _setup_function_signatures(self):
        """Setup function signatures for Ada32.dll functions"""
        
        # AdaInitialize() -> int
        self.dll.AdaInitialize.restype = ctypes.c_int32
        self.dll.AdaInitialize.argtypes = []
        
        # AdaGetErrorText(int errorCode) -> char*
        self.dll.AdaGetErrorText.restype = ctypes.c_char_p
        self.dll.AdaGetErrorText.argtypes = [ctypes.c_int32]
        
        # AdaLookupAtomEnum(char* atomName) -> int
        self.dll.AdaLookupAtomEnum.restype = ctypes.c_int32
        self.dll.AdaLookupAtomEnum.argtypes = [ctypes.c_char_p]
        
        # AdaAssembleAtomStream(void* input, int inputSize, void* output, int* outputSize) -> int
        self.dll.AdaAssembleAtomStream.restype = ctypes.c_int32
        self.dll.AdaAssembleAtomStream.argtypes = [
            ctypes.c_void_p,    # input buffer
            ctypes.c_int32,     # input size
            ctypes.c_void_p,    # output buffer
            ctypes.POINTER(ctypes.c_int32)  # output size pointer
        ]
        
        # AdaDisassembleAtomStream(void* input, int inputSize) -> int
        self.dll.AdaDisassembleAtomStream.restype = ctypes.c_int32
        self.dll.AdaDisassembleAtomStream.argtypes = [
            ctypes.c_void_p,    # input buffer
            ctypes.c_int32      # input size
        ]
        
        # AdaNormalizeAtomStream(void* stream, int streamSize) -> int
        self.dll.AdaNormalizeAtomStream.restype = ctypes.c_int32
        self.dll.AdaNormalizeAtomStream.argtypes = [
            ctypes.c_void_p,    # stream buffer
            ctypes.c_int32      # stream size
        ]
        
        # AdaAssembleFragment(void* fragment, int fragmentSize) -> int
        self.dll.AdaAssembleFragment.restype = ctypes.c_int32
        self.dll.AdaAssembleFragment.argtypes = [
            ctypes.c_void_p,    # fragment buffer
            ctypes.c_int32      # fragment size
        ]
        
        # AdaDoAtomCallbacks(void* context) -> int
        self.dll.AdaDoAtomCallbacks.restype = ctypes.c_int32
        self.dll.AdaDoAtomCallbacks.argtypes = [ctypes.c_void_p]
    
    def initialize(self) -> bool:
        """Initialize Ada32 library"""
        try:
            result = self.dll.AdaInitialize()
            self.initialized = (result != 0)
            logger.info(f"Ada32 initialized: {self.initialized} (returned {result})")
            return self.initialized
        except Exception as e:
            logger.error(f"Failed to initialize Ada32: {e}")
            return False
    
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
        """Assemble atom stream text to binary format using real Ada32.dll"""
        if not self.initialized:
            raise RuntimeError("Ada32 not initialized")
        
        logger.info(f"Assembling atom stream: {len(atom_stream_text)} chars")
        
        try:
            # Prepare input buffer
            input_data = atom_stream_text.encode('utf-8')
            input_size = len(input_data)
            
            # Create input buffer
            input_buffer = ctypes.create_string_buffer(input_data)
            
            # Prepare output buffer (allocate generous size)
            max_output_size = input_size * 4  # Allow for expansion
            output_buffer = ctypes.create_string_buffer(max_output_size)
            output_size = ctypes.c_int32(max_output_size)
            
            # Call Ada32 assembly function
            logger.info(f"Calling AdaAssembleAtomStream with {input_size} bytes")
            result = self.dll.AdaAssembleAtomStream(
                ctypes.cast(input_buffer, ctypes.c_void_p),
                input_size,
                ctypes.cast(output_buffer, ctypes.c_void_p),
                ctypes.byref(output_size)
            )
            
            if result <= 0:
                error_text = self.get_error_text()
                raise RuntimeError(f"Ada32 assembly failed: {error_text}")
            
            # Extract the assembled binary data
            actual_size = min(result, output_size.value)
            binary_data = output_buffer.raw[:actual_size]
            
            logger.info(f"Ada32 assembled {len(binary_data)} bytes (result: {result})")
            return binary_data
            
        except Exception as e:
            logger.error(f"Failed to assemble atom stream: {e}")
            raise
    
    def disassemble_atom_stream(self, binary_data: bytes) -> int:
        """Disassemble binary data - returns decompressed size"""
        if not self.initialized:
            raise RuntimeError("Ada32 not initialized")
        
        logger.info(f"Disassembling {len(binary_data)} bytes")
        
        try:
            # Create input buffer
            input_buffer = ctypes.create_string_buffer(binary_data)
            
            # Call Ada32 disassembly function
            result = self.dll.AdaDisassembleAtomStream(
                ctypes.cast(input_buffer, ctypes.c_void_p),
                len(binary_data)
            )
            
            logger.info(f"Ada32 disassembled to {result} bytes")
            return result
            
        except Exception as e:
            logger.error(f"Failed to disassemble atom stream: {e}")
            raise
    
    def normalize_atom_stream(self, stream_data: bytes) -> int:
        """Normalize atom stream data"""
        if not self.initialized:
            raise RuntimeError("Ada32 not initialized")
        
        try:
            stream_buffer = ctypes.create_string_buffer(stream_data)
            result = self.dll.AdaNormalizeAtomStream(
                ctypes.cast(stream_buffer, ctypes.c_void_p),
                len(stream_data)
            )
            
            logger.info(f"Ada32 normalized stream: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to normalize atom stream: {e}")
            raise
    
    def do_atom_callbacks(self, context_ptr: int = 0) -> int:
        """Execute atom callbacks"""
        if not self.initialized:
            raise RuntimeError("Ada32 not initialized")
        
        try:
            result = self.dll.AdaDoAtomCallbacks(ctypes.c_void_p(context_ptr))
            logger.info(f"Ada32 callbacks executed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute atom callbacks: {e}")
            raise

# Factory function to create the appropriate interface
def create_ada32_interface(dll_path: str = "Ada32.dll"):
    """Create Ada32 interface - Windows version with real DLL"""
    return Ada32WindowsInterface(dll_path)