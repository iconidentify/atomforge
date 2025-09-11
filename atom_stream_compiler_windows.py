#!/usr/bin/env python3
"""
Windows Ada32 Atom Stream Compiler
Uses real Ada32.dll for compilation on Windows platform
"""

import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class AtomStreamCompiler:
    """Compile AOL atom stream text files to binary format using real Ada32.dll"""
    
    def __init__(self, dll_path: str = "Ada32.dll"):
        try:
            # Try interfaces in order: Windows (native) -> Wine (Linux)
            interface_loaded = False
            
            if not interface_loaded:
                try:
                    from dll_interface_windows import create_ada32_interface
                    self.ada32 = create_ada32_interface(dll_path)
                    logger.info("Using Windows-based Ada32 interface")
                    interface_loaded = True
                except (ImportError, RuntimeError) as e:
                    logger.warning(f"Windows interface failed: {e}")
            
            if not interface_loaded:
                try:
                    from dll_interface_wine import create_ada32_interface
                    self.ada32 = create_ada32_interface(dll_path)
                    logger.info("Using Wine-based Ada32 interface")
                    interface_loaded = True
                except (ImportError, RuntimeError) as e:
                    logger.warning(f"Wine interface failed: {e}")
            
            if not interface_loaded:
                raise RuntimeError("Failed to load Ada32.dll - ensure the DLL is present and compatible")
            
            self.initialized = False
        except Exception as e:
            logger.error(f"Failed to initialize any Ada32 interface: {e}")
            raise
    
    def initialize(self) -> bool:
        """Initialize Ada32 for compilation"""
        if not self.initialized:
            self.initialized = self.ada32.initialize()
            logger.info(f"Ada32 initialized: {self.initialized}")
            if not self.initialized:
                raise RuntimeError("Failed to initialize Ada32.dll - DLL may be incompatible or missing dependencies")
        return self.initialized
    
    def compile_txt_to_str(self, txt_filepath: str) -> bytes:
        """Compile .txt atom stream file to binary .str format using real Ada32.dll"""
        
        if not self.initialize():
            raise RuntimeError("Failed to initialize Ada32")
        
        # Read the source .txt file
        txt_path = Path(txt_filepath)
        if not txt_path.exists():
            raise FileNotFoundError(f"File not found: {txt_filepath}")
        
        with open(txt_path, "r", encoding='utf-8') as f:
            source_text = f.read()
        
        logger.info(f"🔍 Compiling {txt_path.name} ({len(source_text)} chars)")
        
        try:
            # Use real Ada32.dll to assemble the atom stream
            binary_data = self.ada32.assemble_atom_stream(source_text)
            
            logger.info(f"✅ Ada32.dll compiled to {len(binary_data)} bytes")
            return binary_data
            
        except Exception as e:
            logger.error(f"Compilation failed: {e}")
            raise

def compile_file(input_file: str, output_file: str = None) -> None:
    """Compile a single atom stream file"""
    
    if output_file is None:
        output_file = str(Path(input_file).with_suffix('.str'))
    
    try:
        compiler = AtomStreamCompiler()
        binary_data = compiler.compile_txt_to_str(input_file)
        
        with open(output_file, 'wb') as f:
            f.write(binary_data)
        
        print(f"✅ Compiled {input_file} -> {output_file} ({len(binary_data)} bytes)")
        
    except Exception as e:
        print(f"❌ Compilation failed: {e}")
        sys.exit(1)

def main():
    """Command line interface"""
    if len(sys.argv) < 2:
        print("Usage: python atom_stream_compiler_windows.py <input.txt> [output.str]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    compile_file(input_file, output_file)

if __name__ == "__main__":
    main()