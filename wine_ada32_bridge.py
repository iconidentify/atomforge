#!/usr/bin/env python3
"""
Wine bridge script for Ada32.dll
This script runs under Wine and provides Ada32.dll function access
"""
import ctypes
import sys
import json
import os
from pathlib import Path

def load_ada32_dll():
    """Load Ada32.dll directly under Wine"""
    try:
        # Try to load the DLL - under Wine this should work
        dll_path = "Ada32.dll"
        dll = ctypes.WinDLL(dll_path)
        
        # Setup function signatures
        dll.AdaInitialize.restype = ctypes.c_int32
        dll.AdaInitialize.argtypes = []
        
        dll.AdaAssembleAtomStream.restype = ctypes.c_int32
        dll.AdaAssembleAtomStream.argtypes = [
            ctypes.c_void_p,    # input buffer
            ctypes.c_int32,     # input size
            ctypes.c_void_p,    # output buffer
            ctypes.POINTER(ctypes.c_int32)  # output size pointer
        ]
        
        dll.AdaDisassembleAtomStream.restype = ctypes.c_int32
        dll.AdaDisassembleAtomStream.argtypes = [
            ctypes.c_void_p,    # input buffer
            ctypes.c_int32      # input size
        ]
        
        return dll
    except Exception as e:
        print(f"ERROR: Failed to load Ada32.dll under Wine: {e}", file=sys.stderr)
        return None

def initialize_ada32(dll):
    """Initialize Ada32"""
    try:
        result = dll.AdaInitialize()
        return result != 0
    except Exception as e:
        print(f"ERROR: Failed to initialize Ada32: {e}", file=sys.stderr)
        return False

def assemble_atom_stream(dll, text_data):
    """Assemble atom stream text to binary"""
    try:
        # Convert text to bytes
        input_data = text_data.encode('utf-8')
        input_size = len(input_data)
        
        # Create buffers
        input_buffer = ctypes.create_string_buffer(input_data)
        max_output_size = input_size * 4
        output_buffer = ctypes.create_string_buffer(max_output_size)
        output_size = ctypes.c_int32(max_output_size)
        
        # Call Ada32 function
        result = dll.AdaAssembleAtomStream(
            ctypes.cast(input_buffer, ctypes.c_void_p),
            input_size,
            ctypes.cast(output_buffer, ctypes.c_void_p),
            ctypes.byref(output_size)
        )
        
        if result > 0:
            # Return successful binary data
            binary_data = output_buffer.raw[:result]
            return binary_data
        else:
            print(f"ERROR: Ada32 assembly failed with result: {result}", file=sys.stderr)
            return None
            
    except Exception as e:
        print(f"ERROR: Failed to assemble atom stream: {e}", file=sys.stderr)
        return None

def main():
    """Main bridge function"""
    if len(sys.argv) < 2:
        print("Usage: wine_ada32_bridge.py <command> [args...]", file=sys.stderr)
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Load DLL
    dll = load_ada32_dll()
    if not dll:
        sys.exit(1)
    
    # Initialize
    if not initialize_ada32(dll):
        print("ERROR: Failed to initialize Ada32", file=sys.stderr)
        sys.exit(1)
    
    if command == "assemble":
        if len(sys.argv) < 3:
            print("Usage: wine_ada32_bridge.py assemble <input_file>", file=sys.stderr)
            sys.exit(1)
        
        input_file = sys.argv[2]
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                text_data = f.read()
            
            binary_data = assemble_atom_stream(dll, text_data)
            if binary_data:
                # Write binary data to stdout
                sys.stdout.buffer.write(binary_data)
                print(f"SUCCESS: Assembled {len(binary_data)} bytes", file=sys.stderr)
            else:
                sys.exit(1)
                
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif command == "test":
        print("SUCCESS: Ada32.dll loaded and initialized under Wine", file=sys.stderr)
    
    else:
        print(f"ERROR: Unknown command: {command}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()