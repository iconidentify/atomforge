#!/usr/bin/env python3
"""
ASCII Text Transformation Engine
Bidirectional conversion between ASCII text and hex encoding for FDO atoms
"""

import re
from typing import List, Tuple, Optional
from ascii_atom_registry import get_registry, AtomDefinition, AtomParameter


class ASCIITransformer:
    """Handles bidirectional conversion between ASCII text and hex encoding"""

    def __init__(self):
        self.registry = get_registry()

    def text_to_hex(self, text: str, encoding: str = "utf-8") -> List[str]:
        """Convert ASCII text to hex format used by FDO"""
        try:
            # Encode text to bytes using specified encoding
            text_bytes = text.encode(encoding)

            # Convert each byte to hex format (e.g., "47x")
            hex_values = [f"{byte:02x}x" for byte in text_bytes]

            return hex_values
        except UnicodeEncodeError as e:
            raise ValueError(f"Cannot encode text '{text}' using {encoding}: {e}")

    def hex_to_text(self, hex_values: List[str], encoding: str = "utf-8") -> str:
        """Convert hex format back to ASCII text"""
        try:
            # Parse hex values (handle both "47x" and "47" formats)
            bytes_list = []
            for hex_val in hex_values:
                # Remove 'x' suffix if present
                clean_hex = hex_val.rstrip('x').strip()
                if clean_hex:
                    bytes_list.append(int(clean_hex, 16))

            # Convert bytes back to text
            text_bytes = bytes(bytes_list)
            return text_bytes.decode(encoding)
        except (ValueError, UnicodeDecodeError) as e:
            raise ValueError(f"Cannot decode hex values {hex_values} as {encoding}: {e}")

    def parse_atom_call(self, line: str) -> Optional[Tuple[str, List[str]]]:
        """
        Parse an FDO atom call and extract atom name and parameters
        Returns (atom_name, parameters) or None if not a valid atom call
        """
        # Match patterns like: atom_name <param1, param2, param3>
        pattern = r'(\w+)\s*<([^>]*)>'
        match = re.match(pattern.strip(), line.strip())

        if not match:
            return None

        atom_name = match.group(1)
        params_str = match.group(2).strip()

        if not params_str:
            return atom_name, []

        # Split parameters by comma, handling quoted strings and nested structures
        parameters = self._parse_parameters(params_str)

        return atom_name, parameters

    def _parse_parameters(self, params_str: str) -> List[str]:
        """Parse parameter string, handling quotes and nested structures"""
        parameters = []
        current_param = ""
        in_quotes = False
        quote_char = None
        bracket_depth = 0

        i = 0
        while i < len(params_str):
            char = params_str[i]

            if char in ['"', "'"] and not in_quotes:
                in_quotes = True
                quote_char = char
                current_param += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current_param += char
            elif char == '<' and not in_quotes:
                bracket_depth += 1
                current_param += char
            elif char == '>' and not in_quotes:
                bracket_depth -= 1
                current_param += char
            elif char == ',' and not in_quotes and bracket_depth == 0:
                # End of parameter
                parameters.append(current_param.strip())
                current_param = ""
            else:
                current_param += char

            i += 1

        # Add final parameter
        if current_param.strip():
            parameters.append(current_param.strip())

        return parameters

    def transform_source_to_hex(self, source_code: str) -> str:
        """
        Transform FDO source code, converting ASCII text to hex for supported atoms
        """
        lines = source_code.split('\n')
        transformed_lines = []

        for line in lines:
            transformed_line = self._transform_line_to_hex(line)
            transformed_lines.append(transformed_line)

        return '\n'.join(transformed_lines)

    def _transform_line_to_hex(self, line: str) -> str:
        """Transform a single line, converting ASCII text to hex if applicable"""
        # Preserve original indentation
        stripped_line = line.lstrip()
        indent = line[:len(line) - len(stripped_line)]

        parsed = self.parse_atom_call(stripped_line)
        if not parsed:
            return line

        atom_name, parameters = parsed
        atom_def = self.registry.get_atom(atom_name)

        if not atom_def or not atom_def.has_ascii_parameters():
            return line

        # Transform parameters that support ASCII
        transformed_params = []
        for i, param in enumerate(parameters):
            ascii_param = atom_def.get_ascii_parameter(i)
            if ascii_param:
                transformed_param = self._transform_parameter_to_hex(param, ascii_param)
                transformed_params.append(transformed_param)
            else:
                transformed_params.append(param)

        # Reconstruct the line
        params_str = ', '.join(transformed_params)
        transformed_line = f"{atom_name} <{params_str}>"

        return indent + transformed_line

    def _transform_parameter_to_hex(self, param: str, ascii_param: AtomParameter) -> str:
        """Transform a single parameter from ASCII text to hex"""
        # Check if parameter is a quoted string (ASCII text)
        if param.startswith('"') and param.endswith('"'):
            # Extract text content
            text_content = param[1:-1]  # Remove quotes

            # Validate the text
            is_valid, error_msg = ascii_param.validate_text(text_content)
            if not is_valid:
                raise ValueError(f"Invalid ASCII text for {ascii_param.name}: {error_msg}")

            # Convert to hex
            hex_values = self.text_to_hex(text_content, ascii_param.encoding)
            return ', '.join(hex_values)

        # Not a quoted string, return as-is (might already be hex)
        return param

    def transform_source_to_ascii(self, source_code: str) -> str:
        """
        Transform FDO source code, converting hex to ASCII text for supported atoms
        """
        lines = source_code.split('\n')
        transformed_lines = []

        for line in lines:
            transformed_line = self._transform_line_to_ascii(line)
            transformed_lines.append(transformed_line)

        return '\n'.join(transformed_lines)

    def _transform_line_to_ascii(self, line: str) -> str:
        """Transform a single line, converting hex to ASCII text if applicable"""
        # Preserve original indentation
        stripped_line = line.lstrip()
        indent = line[:len(line) - len(stripped_line)]

        parsed = self.parse_atom_call(stripped_line)
        if not parsed:
            return line

        atom_name, parameters = parsed
        atom_def = self.registry.get_atom(atom_name)

        if not atom_def or not atom_def.has_ascii_parameters():
            return line

        # Special handling for ASCII atoms - check if all parameters look like hex values
        # and if we have an ASCII parameter at index 0
        ascii_param = atom_def.get_ascii_parameter(0)
        if ascii_param and len(parameters) > 1:
            # Check if all parameters are hex values (this indicates they represent one ASCII text)
            all_hex = all(self._is_single_hex_value(param) for param in parameters)
            if all_hex:
                try:
                    # Convert all hex values to text
                    text_content = self.hex_to_text(parameters, ascii_param.encoding)
                    return f'{indent}{atom_name} <"{text_content}">'
                except ValueError:
                    # If conversion fails, return original
                    return line

        # Normal parameter transformation (for single parameters)
        transformed_params = []
        for i, param in enumerate(parameters):
            ascii_param = atom_def.get_ascii_parameter(i)
            if ascii_param:
                transformed_param = self._transform_parameter_to_ascii(param, ascii_param)
                transformed_params.append(transformed_param)
            else:
                transformed_params.append(param)

        # Reconstruct the line
        params_str = ', '.join(transformed_params)
        transformed_line = f"{atom_name} <{params_str}>"

        return indent + transformed_line

    def _is_single_hex_value(self, param: str) -> bool:
        """Check if a single parameter is a hex value (e.g., '47x')"""
        param = param.strip()
        if not param.endswith('x'):
            return False
        hex_part = param[:-1]
        try:
            int(hex_part, 16)
            return True
        except ValueError:
            return False

    def _transform_parameter_to_ascii(self, param: str, ascii_param: AtomParameter) -> str:
        """Transform a single parameter from hex to ASCII text"""
        # Check if parameter looks like hex values
        if self._is_hex_parameter(param):
            try:
                # Split hex values
                hex_values = [v.strip() for v in param.split(',')]

                # Convert to text
                text_content = self.hex_to_text(hex_values, ascii_param.encoding)

                # Return as quoted string
                return f'"{text_content}"'
            except ValueError:
                # If conversion fails, return original parameter
                return param

        # Not hex format, return as-is
        return param

    def _is_hex_parameter(self, param: str) -> bool:
        """Check if parameter looks like hex values (e.g., '47x, 75x, 65x')"""
        # Simple heuristic: contains 'x' and comma-separated values
        if 'x' not in param:
            return False

        # Split by comma and check if each part looks like hex
        parts = [p.strip() for p in param.split(',')]
        if len(parts) < 2:  # Need at least 2 hex values to be considered hex parameter
            return False

        for part in parts:
            # Check if it's a hex value (with or without 'x' suffix)
            clean_part = part.rstrip('x').strip()
            if not clean_part:
                return False
            try:
                int(clean_part, 16)
            except ValueError:
                return False

        return True


# Global transformer instance
_transformer = None

def get_transformer() -> ASCIITransformer:
    """Get the global ASCII transformer instance"""
    global _transformer
    if _transformer is None:
        _transformer = ASCIITransformer()
    return _transformer


# Convenience functions
def ascii_to_hex(source_code: str) -> str:
    """Convert ASCII text to hex in FDO source code"""
    return get_transformer().transform_source_to_hex(source_code)


def hex_to_ascii(source_code: str) -> str:
    """Convert hex to ASCII text in FDO source code"""
    return get_transformer().transform_source_to_ascii(source_code)