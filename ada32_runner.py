import sys
import os
sys.path.insert(0, os.getcwd())

def run_compile(input_file, output_file=None):
    from atom_stream_compiler_windows import compile_file
    return compile_file(input_file, output_file)

def run_decompile(input_file, output_file=None):
    from atom_stream_decompiler_windows import decompile_file
    return decompile_file(input_file, output_file)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ada32_runner.py <compile|decompile> <input_file> [output_file]")
        sys.exit(1)
    
    command = sys.argv[1]
    input_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    if command == "compile":
        run_compile(input_file, output_file)
    elif command == "decompile":
        run_decompile(input_file, output_file)
    else:
        print("Unknown command. Use 'compile' or 'decompile'")