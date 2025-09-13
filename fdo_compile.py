#!/usr/bin/env python3
"""
FDO Compiler Harness
Simple Python wrapper for FDO compilation using Ada32.dll in Docker/Wine

Usage:
    python fdo_compile.py input.txt [output.str]

Features:
- Automatically handles Docker container startup
- Escapes special characters (& → 26x) required by Ada32.dll
- Runs compilation and returns .str binary output
- Cross-platform (works on Mac ARM, Linux, Windows)
"""

import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
import re

class FDOCompiler:
    """Simple FDO compilation harness using Docker + Ada32.dll"""

    def __init__(self):
        self.container_name = "ada32-compiler"
        self.docker_image = "build_tools-ada32-wine"  # Built from docker-compose

    def escape_special_chars(self, text: str) -> str:
        """Escape special characters that cause issues with Ada32.dll"""
        # Convert & to hex encoding that Ada32.dll expects
        escaped = text.replace('&', '26x')
        return escaped

    def prepare_input_file(self, input_path: str) -> str:
        """Prepare input file with necessary escaping and cleanup"""
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove GID headers if present (multiple formats)
        content = re.sub(r'<+\s*GID:\s*[^>]+\s*>+.*\n?', '', content)

        # Escape special characters
        content = self.escape_special_chars(content)

        # Write prepared content to temp file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.txt')
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                f.write(content)
        except:
            os.close(temp_fd)
            raise

        return temp_path

    def build_docker_image(self):
        """Build the Docker image if it doesn't exist"""
        print("🔨 Building Docker image...")
        build_tools_dir = Path(os.getcwd()) / "build_tools"
        result = subprocess.run([
            "docker-compose", "build"
        ], cwd=str(build_tools_dir), capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Docker build failed: {result.stderr}")
            return False

        print("✅ Docker image built successfully")
        return True

    def compile_fdo(self, input_path: str, output_path: str = None) -> bool:
        """Compile FDO file using Docker + Ada32.dll"""

        if output_path is None:
            input_stem = Path(input_path).stem
            output_path = f"{input_stem}.str"

        print(f"🚀 Starting FDO compilation...")
        print(f"   Input:  {input_path}")
        print(f"   Output: {output_path}")

        # Prepare input file with escaping
        try:
            prepared_input = self.prepare_input_file(input_path)
            print(f"   Prepared input: {prepared_input}")
        except Exception as e:
            print(f"❌ Failed to prepare input file: {e}")
            return False

        try:
            # Build Docker image if needed
            if not self.build_docker_image():
                return False

            # Copy prepared input to a location Docker can access
            container_input = "/tmp/input.txt"
            container_output = "/tmp/output.str"

            # Run compilation in Docker
            print("🔧 Running compilation in Docker...")
            docker_cmd = [
                "docker", "run", "--rm",
                "-v", f"{prepared_input}:{container_input}:ro",
                "-v", f"{os.getcwd()}:/output:rw",
                "--name", self.container_name,
                "build_tools-ada32-wine",
                "bash", "-c",
                f"cd /ada32_toolkit && cp bin/dlls/GIDINFO.INF . && cp bin/dlls/Ada.bin . && export WINEPATH='/ada32_toolkit/bin/dlls' && wine bin/atomforge.exe {container_input} {container_output} && cp {container_output} /output/{Path(output_path).name}"
            ]

            result = subprocess.run(docker_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ Compilation successful!")
                print(f"   Output saved to: {output_path}")

                # Verify output file exists
                if os.path.exists(output_path):
                    size = os.path.getsize(output_path)
                    print(f"   Output size: {size} bytes")
                else:
                    print("❌ Output file was not created")
                    return False

                return True
            else:
                print(f"❌ Compilation failed:")
                if result.stdout:
                    print(f"   STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"   STDERR: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Compilation error: {e}")
            return False

        finally:
            # Clean up temp file
            try:
                os.unlink(prepared_input)
            except:
                pass

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print("  python fdo_compile.py myfile.txt")
        print("  python fdo_compile.py input.txt output.str")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)

    compiler = FDOCompiler()
    success = compiler.compile_fdo(input_file, output_file)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
