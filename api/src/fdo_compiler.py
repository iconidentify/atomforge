#!/usr/bin/env python3
"""
Shared FDO Compiler Module
Reusable compiler logic for both CLI and HTTP API with ASCII text support
"""

import os
import subprocess
import tempfile
import re
from pathlib import Path
from typing import Tuple, Optional, Union

# Import ASCII transformation support
try:
    from ascii_transformers import ascii_to_hex
    ASCII_SUPPORT_AVAILABLE = True
except ImportError:
    ASCII_SUPPORT_AVAILABLE = False


class CompileResult:
    """Result of FDO compilation with detailed error information"""
    
    def __init__(self, success: bool, output_data: Optional[bytes] = None, 
                 error_message: Optional[str] = None, output_size: int = 0,
                 stdout: Optional[str] = None, stderr: Optional[str] = None):
        self.success = success
        self.output_data = output_data
        self.error_message = error_message
        self.output_size = output_size
        # Optional subprocess logs for diagnostics
        self.stdout = stdout
        self.stderr = stderr


class FDOCompiler:
    """Shared FDO compilation logic using Docker + Ada32.dll"""

    def __init__(self):
        self.container_name = "ada32-compiler"
        self.docker_image = "build_tools-ada32-wine"

    def escape_special_chars(self, text: str) -> str:
        """Escape special characters that cause issues with Ada32.dll"""
        return text.replace('&', '26x')

    def prepare_input_content(self, content: str) -> str:
        """Prepare FDO source content with ASCII transformation, escaping and cleanup"""
        # Remove GID headers if present (multiple formats)
        content = re.sub(r'<+\s*GID:\s*[^>]+\s*>+.*\n?', '', content)

        # Transform ASCII text to hex for supported atoms
        if ASCII_SUPPORT_AVAILABLE:
            try:
                content = ascii_to_hex(content)
            except Exception as e:
                # If ASCII transformation fails, log but continue with original content
                print(f"Warning: ASCII transformation failed: {e}")

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
        """Internal compilation logic - uses direct Wine execution"""
        return self._wine_compile_direct(prepared_input, output_path, return_binary)

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
                
                return CompileResult(False, error_message=error_msg, stdout=stdout, stderr=stderr)

        except Exception as e:
            return CompileResult(False, error_message="Internal execution error")
        finally:
            # Clean up temporary output file
            try:
                if os.path.exists(container_output):
                    os.unlink(container_output)
            except:
                pass

