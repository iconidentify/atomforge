#!/usr/bin/env python3
"""
Working Compiler - Based on our successful atom stream compilation discoveries
This creates a simple bridge to the exact working Ada32.dll functionality
"""

import subprocess
import sys
import os
from pathlib import Path

def compile_txt_to_str(txt_file, str_file):
    """Compile .txt to .str using our working Ada32 bridge"""
    
    # Use our working bridge that we know produces consistent output
    cmd = ['docker-compose', 'run', '--rm', 'ada32-wine', 
           'wine', 'ada32_bridge.exe', 'assemble', txt_file]
    
    print(f"Compiling {txt_file} -> {str_file}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Run the bridge and capture binary output
        result = subprocess.run(cmd, 
                              capture_output=True, 
                              cwd=os.getcwd())
        
        if len(result.stdout) > 0:
            # Save the binary output
            output_path = Path(str_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(result.stdout)
            
            print(f"✅ Compiled successfully: {len(result.stdout)} bytes")
            print(f"📁 Output: {str_file}")
            
            # Show first few bytes
            if len(result.stdout) >= 16:
                hex_preview = ' '.join(f'{b:02x}' for b in result.stdout[:16])
                print(f"🔍 First 16 bytes: {hex_preview}")
            
            return True
        else:
            print(f"❌ No output generated")
            if result.stderr:
                print(f"Error: {result.stderr.decode('utf-8', errors='ignore')}")
            return False
            
    except Exception as e:
        print(f"❌ Compilation failed: {e}")
        return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 working_compiler.py <input.txt> <output.str>")
        sys.exit(1)
    
    txt_file = sys.argv[1]
    str_file = sys.argv[2]
    
    print("🔧 Ada32 Working Compiler")
    print("=" * 40)
    
    if not Path(txt_file).exists():
        print(f"❌ Input file not found: {txt_file}")
        sys.exit(1)
    
    success = compile_txt_to_str(txt_file, str_file)
    
    if success:
        print("\n🎉 Compilation completed successfully!")
        
        # Compare with golden file if it exists
        golden_file = txt_file.replace('.txt', '.str')
        if Path(golden_file).exists():
            our_size = Path(str_file).stat().st_size
            golden_size = Path(golden_file).stat().st_size
            print(f"\n📊 Size comparison:")
            print(f"   Our output: {our_size:,} bytes")
            print(f"   Golden file: {golden_size:,} bytes")
            print(f"   Ratio: {our_size/golden_size:.1f}x")
    else:
        print("\n❌ Compilation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()