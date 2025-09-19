#!/usr/bin/env python3
"""
Shared FDO Compiler Module
Reusable compiler logic for both CLI and HTTP API
"""

import os
import subprocess
import tempfile
import re
from pathlib import Path
from typing import Tuple, Optional, Union


class CompileResult:
    """Result of FDO compilation with detailed error information"""
    
    def __init__(self, success: bool, output_data: Optional[bytes] = None, 
                 error_message: Optional[str] = None, output_size: int = 0):
        self.success = success
        self.output_data = output_data
        self.error_message = error_message
        self.output_size = output_size


class FDOCompiler:
    """Shared FDO compilation logic using Docker + Ada32.dll"""

    def __init__(self):
        self.container_name = "ada32-compiler"
        self.docker_image = "build_tools-ada32-wine"

    def escape_special_chars(self, text: str) -> str:
        """Escape special characters that cause issues with Ada32.dll"""
        return text.replace('&', '26x')

    def prepare_input_content(self, content: str) -> str:
        """Prepare FDO source content with necessary escaping and cleanup"""
        # Remove GID headers if present (multiple formats)
        content = re.sub(r'<+\s*GID:\s*[^>]+\s*>+.*\n?', '', content)
        
        # Escape special characters
        return self.escape_special_chars(content)

    def prepare_input_file(self, input_path: str) -> str:
        """Prepare input file with necessary escaping and cleanup"""
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = self.prepare_input_content(content)

        # Write prepared content to temp file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.txt')
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                f.write(content)
        except:
            os.close(temp_fd)
            raise

        return temp_path

    def prepare_input_from_string(self, content: str) -> str:
        """Create temp file from string content"""
        content = self.prepare_input_content(content)
        
        temp_fd, temp_path = tempfile.mkstemp(suffix='.txt')
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                f.write(content)
        except:
            os.close(temp_fd)
            raise

        return temp_path

    def build_docker_image_silent(self) -> bool:
        """Build Docker image without output for API use"""
        # Check if we're running inside Docker (API service)
        if os.path.exists('/atomforge/build_tools'):
            build_tools_dir = Path('/atomforge/build_tools')
        else:
            # Running from host - check multiple possible locations
            possible_paths = [
                Path(os.getcwd()) / "build_tools",
                Path(os.getcwd()).parent / "build_tools",
                Path(__file__).parent.parent.parent / "build_tools"  # From api/src/ up to project root
            ]
            
            build_tools_dir = None
            for path in possible_paths:
                if path.exists():
                    build_tools_dir = path
                    break
            
            if build_tools_dir is None:
                raise FileNotFoundError(f"build_tools directory not found. Searched: {[str(p) for p in possible_paths]}")
        
        result = subprocess.run([
            "docker-compose", "build"
        ], cwd=str(build_tools_dir), capture_output=True, text=True)
        
        return result.returncode == 0

    def compile_from_file(self, input_path: str, output_path: str = None) -> CompileResult:
        """Compile FDO from file path - CLI version"""
        if output_path is None:
            input_stem = Path(input_path).stem
            output_path = f"{input_stem}.fdo"

        try:
            prepared_input = self.prepare_input_file(input_path)
            return self._docker_compile(prepared_input, output_path)
        except Exception as e:
            return CompileResult(False, error_message=f"Failed to prepare input: {e}")
        finally:
            try:
                os.unlink(prepared_input)
            except:
                pass

    def compile_from_string(self, content: str) -> CompileResult:
        """Compile FDO from string content - API version"""
        if not content or not content.strip():
            return CompileResult(False, error_message="Empty or invalid input content")
        
        prepared_input = None
        try:
            prepared_input = self.prepare_input_from_string(content)
            return self._docker_compile(prepared_input, None, return_binary=True)
        except Exception as e:
            return CompileResult(False, error_message=f"Failed to prepare input: {e}")
        finally:
            if prepared_input:
                try:
                    os.unlink(prepared_input)
                except:
                    pass

    def _docker_compile(self, prepared_input: str, output_path: Optional[str] = None, 
                       return_binary: bool = False) -> CompileResult:
        """Internal compilation logic - handles both Docker and direct Wine execution"""
        
        # Check if we're running inside the API container (has Wine available)
        if os.path.exists('/atomforge/bin/fdo_compiler.exe'):
            return self._wine_compile_direct(prepared_input, output_path, return_binary)
        else:
            return self._docker_compile_external(prepared_input, output_path, return_binary)

    def _wine_compile_direct(self, prepared_input: str, output_path: Optional[str] = None,
                            return_binary: bool = False) -> CompileResult:
        """Direct Wine compilation (when running inside API container)"""
        # Create unique temporary output file to avoid collisions
        temp_fd, container_output = tempfile.mkstemp(suffix='.fdo', dir='/tmp')
        os.close(temp_fd)  # Close the file descriptor but keep the path

        try:
            # Use /tmp as working directory since /atomforge might be read-only
            wine_cmd = [
                "bash", "-c",
                f"cd /tmp && "
                f"export WINEPATH='/atomforge/bin' && "
                f"wine /atomforge/bin/fdo_compiler.exe --force --verbose {prepared_input} {container_output}"
            ]
            
            result = subprocess.run(wine_cmd, capture_output=True)
            
            if result.returncode == 0 and os.path.exists(container_output):
                if return_binary:
                    # Read and return binary data
                    with open(container_output, 'rb') as f:
                        output_data = f.read()
                    return CompileResult(True, output_data=output_data, 
                                       output_size=len(output_data))
                else:
                    # Copy to output file
                    if output_path:
                        import shutil
                        shutil.copy(container_output, output_path)
                        return CompileResult(True, output_size=os.path.getsize(output_path))
                    else:
                        return CompileResult(False, error_message="No output path specified")
            else:
                stderr = result.stderr.decode('utf-8') if result.stderr else ""
                stdout = result.stdout.decode('utf-8') if result.stdout else ""
                
                error_msg = "Compilation failed"
                if "Failed to load Ada32.dll" in stdout:
                    error_msg = "Internal error: compiler library not found"
                elif "Compilation failed" in stdout:
                    error_msg = "Invalid FDO syntax"
                elif "Cannot open input file" in stdout:
                    error_msg = "Input file could not be read"
                # New: extract Ada error text
                ada_match = re.search(r"Ada32 error rc=0x[0-9A-F]+ \(\d+\): (.*)", stdout or stderr)
                if ada_match:
                    error_msg = f"Syntax error: {ada_match.group(1)}"  # e.g., "Syntax error: missing parameter"
                else:
                    error_msg = "Internal compilation error"  # generic for UI
                
                return CompileResult(False, error_message=error_msg)

        except Exception as e:
            return CompileResult(False, error_message="Internal execution error")
        finally:
            # Clean up temporary output file
            try:
                if os.path.exists(container_output):
                    os.unlink(container_output)
            except:
                pass

    def _docker_compile_external(self, prepared_input: str, output_path: Optional[str] = None, 
                                return_binary: bool = False) -> CompileResult:
        """External Docker compilation (when running from host CLI)"""
        
        # Build Docker image if needed
        if not self.build_docker_image_silent():
            return CompileResult(False, error_message="Docker build failed")

        container_input = "/tmp/input.txt"
        container_output = "/tmp/output.fdo"

        try:
            if return_binary:
                # For API: return binary data directly
                docker_cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{prepared_input}:{container_input}:ro",
                    self.docker_image,
                    "bash", "-c",
                    f"cd /atomforge && cp bin/GIDINFO.INF . && cp bin/Ada.bin . && cp bin/Ada32.dll . && cp bin/mfc42.dll . 2>/dev/null || true && "
                    f"export WINEPATH='/atomforge/bin' && "
                    f"wine bin/fdo_compiler.exe {container_input} {container_output} && "
                    f"cat {container_output}"
                ]
            else:
                # For CLI: write to output file
                docker_cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{prepared_input}:{container_input}:ro",
                    "-v", f"{os.getcwd()}:/output:rw",
                    self.docker_image,
                    "bash", "-c",
                    f"cd /atomforge && cp bin/GIDINFO.INF . && cp bin/Ada.bin . && cp bin/Ada32.dll . && cp bin/mfc42.dll . 2>/dev/null || true && "
                    f"export WINEPATH='/atomforge/bin' && "
                    f"wine bin/fdo_compiler.exe {container_input} {container_output} && "
                    f"cp {container_output} /output/{Path(output_path).name}"
                ]

            result = subprocess.run(docker_cmd, capture_output=True)

            if result.returncode == 0:
                if return_binary:
                    return CompileResult(True, output_data=result.stdout, 
                                       output_size=len(result.stdout))
                else:
                    if os.path.exists(output_path):
                        size = os.path.getsize(output_path)
                        return CompileResult(True, output_size=size)
                    else:
                        return CompileResult(False, error_message="Output file not created")
            else:
                stderr = result.stderr.decode('utf-8') if result.stderr else ""
                stdout = result.stdout.decode('utf-8') if result.stdout else ""
                
                # Extract meaningful error from compiler output
                error_msg = "Compilation failed"
                if "❌ Failed to load Ada32.dll" in stdout:
                    error_msg = "Ada32.dll could not be loaded"
                elif "❌ Compilation failed" in stdout:
                    error_msg = "Ada32 compilation failed - invalid FDO syntax"
                elif "Cannot open input file" in stdout:
                    error_msg = "Input file could not be read"
                elif stderr:
                    error_msg = f"Docker error: {stderr.strip()}"
                
                return CompileResult(False, error_message=error_msg)

        except Exception as e:
            return CompileResult(False, error_message=f"Docker execution failed: {e}")