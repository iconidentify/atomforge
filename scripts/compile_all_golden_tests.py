#!/usr/bin/env python3
"""
Compile all golden test files using the restored Ada32.dll functionality.
Creates .program.output.bin files for each .txt file in golden_tests_immutable/
"""
import os
import subprocess
import sys
from pathlib import Path

def remove_gid_header(content):
    """Remove GID header from FDO script content."""
    lines = content.split('\n')
    if lines and lines[0].startswith('<') and 'GID:' in lines[0]:
        return '\n'.join(lines[1:])
    return content

def hex_encode_special_chars(content):
    """Convert special characters in token parameters to hex encoding.
    
    Ada32.dll requires ampersands in token parameters to be hex-encoded.
    For example: sm_send_token_arg <L&> becomes sm_send_token_arg <L26x>
    """
    import re
    
    def replace_ampersand_in_token(match):
        """Replace & with 26x in token parameters."""
        token_content = match.group(1)
        # Convert & to hex (26x)
        hex_encoded = token_content.replace('&', '26x')
        return f'<{hex_encoded}>'
    
    # Pattern to match token parameters: <anything>
    # But only replace & characters within angle brackets
    pattern = r'<([^>]*&[^>]*)>'
    result = re.sub(pattern, replace_ampersand_in_token, content)
    
    return result

def compile_golden_test(txt_file):
    """Compile a single golden test file and save the output."""
    txt_path = Path(txt_file)
    output_path = txt_path.with_suffix('.program.output.bin')
    
    print(f"🔄 Compiling {txt_path.name}...")
    
    # Read and clean the input file
    with open(txt_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Remove GID header if present
    clean_content = remove_gid_header(content)
    
    # Apply hex encoding for special characters
    hex_encoded_content = hex_encode_special_chars(clean_content)
    
    # Write processed content to temporary file
    temp_file = 'temp_clean_input.txt'
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(hex_encoded_content)
    
    try:
        # Run the Ada32 compiler with the cleaned input
        result = subprocess.run([
            'docker', 'run', '--rm', 
            '-v', f'{os.getcwd()}:/workspace',
            '-v', f'{os.getcwd()}/bin/runtime:/workspace/runtime',
            'ada32_toolkit-ada32-wine',
            'bash', '-c', 
            f'cd /workspace/runtime && wine ../bin/ada32_compiler.exe ../{temp_file} ../{output_path}'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_path):
            # Get file size for reporting
            size = os.path.getsize(output_path)
            print(f"   ✅ Success: {size} bytes -> {output_path}")
            return True
        else:
            print(f"   ❌ Failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ Timeout during compilation")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    finally:
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)

def main():
    """Compile all golden test files."""
    print("🚀 Compiling All Golden Tests with Restored Ada32.dll")
    print("=" * 55)
    
    # Ensure we have the supporting files required by Ada32.dll
    runtime_dir = Path('bin/runtime')
    if not (runtime_dir / 'GIDINFO.INF').exists() or not (runtime_dir / 'Ada.bin').exists():
        print("⚠️  Missing supporting files required by Ada32.dll. Copying from research_materials...")
        subprocess.run(['cp', 'research_materials/dbviewer_original/GIDINFO.INF', str(runtime_dir)])
        subprocess.run(['cp', 'research_materials/dbviewer_original/Ada.bin', str(runtime_dir)])
        print("✅ Supporting files restored")
    
    golden_dir = Path('golden_tests_immutable')
    if not golden_dir.exists():
        print(f"❌ Golden tests directory not found: {golden_dir}")
        return 1
    
    # Find all .txt files
    txt_files = list(golden_dir.glob('*.txt'))
    if not txt_files:
        print(f"❌ No .txt files found in {golden_dir}")
        return 1
    
    print(f"📁 Found {len(txt_files)} golden test files")
    print()
    
    successful = 0
    failed = 0
    
    for txt_file in sorted(txt_files):
        if compile_golden_test(txt_file):
            successful += 1
        else:
            failed += 1
    
    print()
    print("📊 Compilation Summary")
    print("=" * 20)
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📁 Total: {len(txt_files)}")
    
    if successful > 0:
        print(f"\n🎉 Generated {successful} .program.output.bin files!")
        print("These files contain the raw Ada32.dll compiled output for analysis.")
    
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())