#!/usr/bin/env python3
"""
FDO Decompiler Module
Elegant decompilation of binary FDO files to source code
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Union


class DecompileResult:
    """Result of FDO decompilation with detailed error information"""

    def __init__(self, success: bool, source_code: Optional[str] = None,
                 error_message: Optional[str] = None, output_size: int = 0):
        self.success = success
        self.source_code = source_code
        self.error_message = error_message
        self.output_size = output_size


class FDODecompiler:
    """FDO decompilation logic using Wine + fdo_decompiler.exe"""

    def __init__(self):
        self.container_name = "atomforge-decompiler"

    def decompile_from_bytes(self, binary_data: bytes) -> DecompileResult:
        """Decompile FDO from binary data - API version"""
        if not binary_data:
            return DecompileResult(False, error_message="Empty binary data provided")

        temp_input = None
        try:
            # Create temporary file for binary input
            temp_fd, temp_input = tempfile.mkstemp(suffix='.fdo')
            with os.fdopen(temp_fd, 'wb') as f:
                f.write(binary_data)

            return self._wine_decompile_direct(temp_input, return_source=True)
        except Exception as e:
            return DecompileResult(False, error_message=f"Failed to prepare binary input: {e}")
        finally:
            if temp_input and os.path.exists(temp_input):
                try:
                    os.unlink(temp_input)
                except:
                    pass

    def decompile_from_file(self, input_path: str, output_path: str = None) -> DecompileResult:
        """Decompile FDO from file path - CLI version"""
        if not os.path.exists(input_path):
            return DecompileResult(False, error_message=f"Input file not found: {input_path}")

        if output_path is None:
            input_stem = Path(input_path).stem
            output_path = f"{input_stem}_decompiled.txt"

        try:
            return self._wine_decompile_direct(input_path, output_path, return_source=False)
        except Exception as e:
            return DecompileResult(False, error_message=f"Failed to decompile: {e}")

    def _wine_decompile_direct(self, input_path: str, output_path: Optional[str] = None,
                              return_source: bool = False) -> DecompileResult:
        """Direct Wine decompilation (when running inside API container)"""
        # Create unique temporary output file to avoid collisions
        temp_fd, container_output = tempfile.mkstemp(suffix='.txt', dir='/tmp')
        os.close(temp_fd)  # Close the file descriptor but keep the path

        try:
            # Use /tmp as working directory since /atomforge might be read-only
            wine_cmd = [
                "bash", "-c",
                f"cd /tmp && "
                f"cp /atomforge/bin/GIDINFO.INF . && "
                f"cp /atomforge/bin/Ada.bin . && "
                f"cp /atomforge/bin/Ada32.dll . && "
                f"cp /atomforge/bin/mfc42.dll . 2>/dev/null || true && "
                f"export WINEPATH='/atomforge/bin' && "
                f"wine /atomforge/bin/fdo_decompiler.exe --force {input_path} {container_output}"
            ]

            result = subprocess.run(wine_cmd, capture_output=True, text=True)

            if result.returncode == 0 and os.path.exists(container_output):
                if return_source:
                    # Read and return source code
                    with open(container_output, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    return DecompileResult(True, source_code=source_code,
                                         output_size=len(source_code))
                else:
                    # Copy to output file
                    if output_path:
                        import shutil
                        shutil.copy(container_output, output_path)
                        with open(output_path, 'r', encoding='utf-8') as f:
                            source_code = f.read()
                        return DecompileResult(True, source_code=source_code,
                                             output_size=len(source_code))
                    else:
                        return DecompileResult(False, error_message="No output path specified")
            else:
                stderr = result.stderr if result.stderr else ""
                stdout = result.stdout if result.stdout else ""

                # Extract meaningful error
                error_msg = "Wine decompilation failed"
                if "❌ Failed to load Ada32.dll" in stdout:
                    error_msg = "Ada32.dll could not be loaded"
                elif "❌ Decompilation failed" in stdout:
                    error_msg = "Ada32 decompilation failed - invalid FDO binary format"
                elif "Cannot open input file" in stdout:
                    error_msg = "Input file could not be read or is not a valid FDO binary"
                elif stderr:
                    error_msg = f"Wine error: {stderr.strip()}"

                return DecompileResult(False, error_message=error_msg)

        except Exception as e:
            return DecompileResult(False, error_message=f"Wine execution failed: {e}")
        finally:
            # Clean up temporary output file
            try:
                if os.path.exists(container_output):
                    os.unlink(container_output)
            except:
                pass

    def _docker_decompile_external(self, input_path: str, output_path: Optional[str] = None,
                                  return_source: bool = False) -> DecompileResult:
        """External Docker decompilation (when running from host CLI)"""
        container_input = "/tmp/input.fdo"
        container_output = "/tmp/decompiled.txt"

        try:
            if return_source:
                # For API: return source code directly
                docker_cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{input_path}:{container_input}:ro",
                    "atomforge:latest",
                    "bash", "-c",
                    f"cd /atomforge && cp bin/GIDINFO.INF . && cp bin/Ada.bin . && cp bin/Ada32.dll . && cp bin/mfc42.dll . 2>/dev/null || true && "
                    f"export WINEPATH='/atomforge/bin' && "
                    f"wine bin/fdo_decompiler.exe --force {container_input} {container_output} && "
                    f"cat {container_output}"
                ]
            else:
                # For CLI: write to output file
                docker_cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{input_path}:{container_input}:ro",
                    "-v", f"{os.getcwd()}:/output:rw",
                    "atomforge:latest",
                    "bash", "-c",
                    f"cd /atomforge && cp bin/GIDINFO.INF . && cp bin/Ada.bin . && cp bin/Ada32.dll . && cp bin/mfc42.dll . 2>/dev/null || true && "
                    f"export WINEPATH='/atomforge/bin' && "
                    f"wine bin/fdo_decompiler.exe --force {container_input} {container_output} && "
                    f"cp {container_output} /output/{Path(output_path).name}"
                ]

            result = subprocess.run(docker_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                if return_source:
                    return DecompileResult(True, source_code=result.stdout,
                                         output_size=len(result.stdout))
                else:
                    if os.path.exists(output_path):
                        with open(output_path, 'r', encoding='utf-8') as f:
                            source_code = f.read()
                        return DecompileResult(True, source_code=source_code,
                                             output_size=len(source_code))
                    else:
                        return DecompileResult(False, error_message="Output file not created")
            else:
                stderr = result.stderr if result.stderr else ""
                stdout = result.stdout if result.stdout else ""

                # Extract meaningful error from decompiler output
                error_msg = "Decompilation failed"
                if "❌ Failed to load Ada32.dll" in stdout:
                    error_msg = "Ada32.dll could not be loaded"
                elif "❌ Decompilation failed" in stdout:
                    error_msg = "Ada32 decompilation failed - invalid FDO binary format"
                elif "Cannot open input file" in stdout:
                    error_msg = "Input file could not be read"
                elif stderr:
                    error_msg = f"Docker error: {stderr.strip()}"

                return DecompileResult(False, error_message=error_msg)

        except Exception as e:
            return DecompileResult(False, error_message=f"Docker execution failed: {e}")