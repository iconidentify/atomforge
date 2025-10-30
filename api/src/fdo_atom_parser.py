#!/usr/bin/env python3
"""
FDO Atom Parser
Parses FDO scripts while preserving action blocks as atomic units
Based on reverse engineering of AOLBUF.AOL chunking logic
"""

import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class FdoAtomParser:
    """
    Parser for FDO scripts that preserves action blocks as atomic units.
    Critical for proper P3 chunking where action blocks should not be split.
    """

    # Action atoms that contain nested streams and should be treated atomically
    ACTION_ATOMS = {
        'act_replace_select_action',
        'act_replace_action',
        'act_set_criterion',
        'act_do_action',
        'act_append_select_action',
        'act_append_action',
        'act_prepend_select_action',
        'act_insert_select_action'
    }

    # Maximum text length before splitting man_append_data (conservative estimate for 255-byte limit)
    MAX_APPEND_DATA_TEXT_LENGTH = 200

    # Maximum hex pairs before splitting man_append_data hex format
    # Each pair compiles to 1 byte, so 150 pairs = 150 bytes compiled
    # Conservative to stay under 255-byte limit with overhead
    MAX_MAN_APPEND_DATA_HEX_PAIRS = 150

    # Maximum hex data length before splitting idb_append_data (hex chars are 2 per byte, so ~100 hex chars = 50 bytes)
    MAX_IDB_APPEND_DATA_HEX_LENGTH = 400

    # Maximum hex pairs before splitting idb_append_data hex-pair format (PREFERRED over continuous hex)
    # Each pair = 1 byte, so 200 pairs = 200 bytes compiled
    MAX_IDB_APPEND_DATA_HEX_PAIRS = 200

    # Maximum hex data length before splitting dod_data (same as idb_append_data - ~200 bytes when compiled)
    MAX_DOD_DATA_HEX_LENGTH = 400

    # Maximum hex pairs before splitting dod_data hex-pair format (PREFERRED over continuous hex)
    # Each pair = 1 byte, so 200 pairs = 200 bytes compiled
    MAX_DOD_DATA_HEX_PAIRS = 200

    # Maximum hex data length for raw_data (112 bytes = 224 hex chars, max for AT token NON-FDO frames)
    MAX_RAW_DATA_HEX_LENGTH = 224

    @classmethod
    def preprocess_script(cls, fdo_script: str) -> str:
        """
        Preprocess FDO script to split long data atoms into smaller chunks.

        Args:
            fdo_script: Original FDO script

        Returns:
            Modified FDO script with long data blocks split
        """
        lines = fdo_script.split('\n')
        processed_lines = []

        for line in lines:
            if cls._is_long_append_data(line):
                # Split quoted text format: man_append_data <"text">
                split_lines = cls._split_append_data_line(line)
                processed_lines.extend(split_lines)
                logger.debug(f"Split long man_append_data (quoted) into {len(split_lines)} parts")
            elif cls._is_long_append_data_hex(line):
                # Split hex-pair format: man_append_data <2Ax, 3Bx, ...>
                split_lines = cls._split_append_data_hex_line(line)
                processed_lines.extend(split_lines)
                logger.debug(f"Split long man_append_data (hex) into {len(split_lines)} parts")
            elif cls._is_long_idb_append_data(line):
                # Split continuous hex format: idb_append_data <AABBCC...> (LEGACY)
                split_lines = cls._split_idb_append_data_line(line)
                processed_lines.extend(split_lines)
                logger.debug(f"Split long idb_append_data (continuous hex - legacy) into {len(split_lines)} parts")
            elif cls._is_long_idb_append_data_hex(line):
                # Split hex-pair format: idb_append_data <2Ax, 3Bx, ...> (PREFERRED)
                split_lines = cls._split_idb_append_data_hex_line(line)
                processed_lines.extend(split_lines)
                logger.debug(f"Split long idb_append_data (hex pairs) into {len(split_lines)} parts")
            elif cls._is_long_dod_data(line):
                # Split continuous hex format: dod_data <AABBCC...> (LEGACY)
                split_lines = cls._split_dod_data_line(line)
                processed_lines.extend(split_lines)
                logger.debug(f"Split long dod_data (continuous hex - legacy) into {len(split_lines)} parts")
            elif cls._is_long_dod_data_hex(line):
                # Split hex-pair format: dod_data <2Ax, 3Bx, ...> (PREFERRED)
                split_lines = cls._split_dod_data_hex_line(line)
                processed_lines.extend(split_lines)
                logger.debug(f"Split long dod_data (hex pairs) into {len(split_lines)} parts")
            else:
                processed_lines.append(line)

        return '\n'.join(processed_lines)

    @classmethod
    def _is_long_append_data(cls, line: str) -> bool:
        """Check if a line contains a man_append_data with long text."""
        line_clean = line.strip()
        if not line_clean.startswith('man_append_data'):
            return False

        # Extract text content from angle brackets
        text_content = cls._extract_text_from_append_data(line_clean)
        return text_content and len(text_content) > cls.MAX_APPEND_DATA_TEXT_LENGTH

    @classmethod
    def _is_long_append_data_hex(cls, line: str) -> bool:
        """Check if a line contains man_append_data with long hex pairs."""
        line_clean = line.strip()
        if not line_clean.startswith('man_append_data'):
            return False

        # Check for hex-pair format: <2Ax, 3Bx, ...>
        hex_content = cls._extract_hex_from_man_append_data(line_clean)
        if not hex_content:
            return False

        # Count comma-separated hex pairs
        pairs = [p.strip() for p in hex_content.split(',') if p.strip()]
        return len(pairs) > cls.MAX_MAN_APPEND_DATA_HEX_PAIRS

    @classmethod
    def _extract_text_from_append_data(cls, line: str) -> str:
        """Extract text content from man_append_data <"text"> format."""
        match = re.search(r'man_append_data\s*<\s*"([^"]*)"', line)
        if match:
            return match.group(1)
        return ""

    @classmethod
    def _extract_hex_from_man_append_data(cls, line: str) -> str:
        """Extract hex content from man_append_data <hex> format (no quotes)."""
        # Match hex-pair format: <2Ax, 3Bx, ...> (no quotes)
        match = re.search(r'man_append_data\s*<\s*([0-9A-Fa-fx, ]+)\s*>', line)
        if match:
            content = match.group(1)
            # Verify it looks like hex pairs (contains 'x')
            if 'x' in content.lower():
                return content
        return ""

    @classmethod
    def _split_append_data_line(cls, line: str) -> List[str]:
        """Split a long man_append_data line into multiple smaller ones."""
        # Extract the indentation and text content
        indent_match = re.match(r'^(\s*)', line)
        indent = indent_match.group(1) if indent_match else ""

        text_content = cls._extract_text_from_append_data(line)
        if not text_content:
            return [line]  # Fallback if we can't parse it

        # Split text at sentence boundaries, then word boundaries if needed
        text_chunks = cls._split_text_smartly(text_content)

        # Generate man_append_data lines for each chunk
        split_lines = []
        for chunk in text_chunks:
            # Escape quotes in the chunk text
            escaped_chunk = chunk.replace('"', '\\"')
            split_line = f'{indent}man_append_data <"{escaped_chunk}">'
            split_lines.append(split_line)

        return split_lines

    @classmethod
    def _split_append_data_hex_line(cls, line: str) -> List[str]:
        """Split a long man_append_data hex-pair line into multiple smaller ones."""
        # Extract indentation and hex content
        indent_match = re.match(r'^(\s*)', line)
        indent = indent_match.group(1) if indent_match else ""

        hex_content = cls._extract_hex_from_man_append_data(line)
        if not hex_content:
            return [line]  # Fallback

        # Split into individual hex pairs
        pairs = [p.strip() for p in hex_content.split(',') if p.strip()]

        # Chunk into groups of MAX_MAN_APPEND_DATA_HEX_PAIRS
        split_lines = []
        for i in range(0, len(pairs), cls.MAX_MAN_APPEND_DATA_HEX_PAIRS):
            chunk = pairs[i:i + cls.MAX_MAN_APPEND_DATA_HEX_PAIRS]
            chunk_str = ', '.join(chunk)
            split_line = f'{indent}man_append_data <{chunk_str}>'
            split_lines.append(split_line)

        return split_lines

    @classmethod
    def _split_text_smartly(cls, text: str) -> List[str]:
        """
        Split text at semantic boundaries (sentences, then words).
        Preserves spaces at chunk boundaries to prevent word concatenation.
        """
        chunks = []
        remaining_text = text.strip()  # Only strip the original input

        while remaining_text:
            if len(remaining_text) <= cls.MAX_APPEND_DATA_TEXT_LENGTH:
                # Remaining text fits in one chunk
                chunks.append(remaining_text)
                break

            # Find a good place to split within the limit
            chunk_end = cls._find_good_split_point(remaining_text, cls.MAX_APPEND_DATA_TEXT_LENGTH)

            # Extract chunk WITHOUT stripping to preserve boundary spaces
            chunk = remaining_text[:chunk_end]

            if chunk:
                chunks.append(chunk)

            # Continue from chunk_end WITHOUT stripping to preserve spaces
            remaining_text = remaining_text[chunk_end:]

        return chunks

    @classmethod
    def _find_good_split_point(cls, text: str, max_length: int) -> int:
        """Find a good place to split text within max_length."""
        if len(text) <= max_length:
            return len(text)

        # Look for sentence endings (period, exclamation, question mark + space)
        sentence_pattern = r'[.!?]\s+'
        sentence_matches = list(re.finditer(sentence_pattern, text[:max_length]))
        if sentence_matches:
            return sentence_matches[-1].end()

        # Look for word boundaries (spaces)
        last_space = text[:max_length].rfind(' ')
        if last_space > 0:
            return last_space + 1

        # Last resort: split at max_length (not ideal but prevents infinite loops)
        return max_length

    @classmethod
    def _is_long_idb_append_data(cls, line: str) -> bool:
        """Check if a line contains an idb_append_data with long hex data."""
        line_clean = line.strip()
        if not line_clean.startswith('idb_append_data'):
            return False

        # Extract hex content from angle brackets
        hex_content = cls._extract_hex_from_idb_append_data(line_clean)
        return hex_content and len(hex_content) > cls.MAX_IDB_APPEND_DATA_HEX_LENGTH

    @classmethod
    def _is_long_idb_append_data_hex(cls, line: str) -> bool:
        """Check if line contains idb_append_data with long hex pairs."""
        line_clean = line.strip()
        if not line_clean.startswith('idb_append_data'):
            return False

        # Check for hex-pair format: <2Ax, 3Bx, ...>
        hex_content = cls._extract_hex_pairs_from_idb_append_data(line_clean)
        if not hex_content:
            return False

        # Count comma-separated hex pairs
        pairs = [p.strip() for p in hex_content.split(',') if p.strip()]
        return len(pairs) > cls.MAX_IDB_APPEND_DATA_HEX_PAIRS

    @classmethod
    def _extract_hex_from_idb_append_data(cls, line: str) -> str:
        """Extract hex content from idb_append_data <hex_data> format (continuous hex only, LEGACY)."""
        # Look for continuous hex data (no commas, no 'x' suffix - legacy format)
        match = re.search(r'idb_append_data\s*<\s*([0-9A-Fa-f\s]+)\s*>', line)
        if match:
            content = match.group(1)
            # Verify it's continuous hex (no 'x' or commas)
            if 'x' not in content.lower() and ',' not in content:
                return content
        return ""

    @classmethod
    def _extract_hex_pairs_from_idb_append_data(cls, line: str) -> str:
        """Extract hex-pair content from idb_append_data <2Ax, 3Bx, ...> format."""
        match = re.search(r'idb_append_data\s*<\s*([0-9A-Fa-fx, ]+)\s*>', line)
        if match:
            content = match.group(1)
            # Verify it looks like hex pairs (contains 'x' and commas)
            if 'x' in content.lower() and ',' in content:
                return content
        return ""

    @classmethod
    def _split_idb_append_data_line(cls, line: str) -> List[str]:
        """Split a long idb_append_data line into multiple smaller ones."""
        # Extract the indentation and hex content
        indent_match = re.match(r'^(\s*)', line)
        indent = indent_match.group(1) if indent_match else ""

        hex_content = cls._extract_hex_from_idb_append_data(line)
        if not hex_content:
            return [line]  # Fallback if we can't parse it

        # Clean hex content - remove all whitespace
        cleaned_hex = re.sub(r'\s+', '', hex_content)

        # Split hex data into chunks that fit within the limit
        hex_chunks = cls._split_hex_data(cleaned_hex)

        # Generate idb_append_data lines for each chunk
        split_lines = []
        for chunk in hex_chunks:
            split_line = f'{indent}idb_append_data <{chunk}>'
            split_lines.append(split_line)

        return split_lines

    @classmethod
    def _split_idb_append_data_hex_line(cls, line: str) -> List[str]:
        """Split a long idb_append_data hex-pair line into multiple smaller ones."""
        indent_match = re.match(r'^(\s*)', line)
        indent = indent_match.group(1) if indent_match else ""

        hex_content = cls._extract_hex_pairs_from_idb_append_data(line)
        if not hex_content:
            return [line]  # Fallback

        # Split into individual hex pairs
        pairs = [p.strip() for p in hex_content.split(',') if p.strip()]

        # Chunk into groups
        split_lines = []
        for i in range(0, len(pairs), cls.MAX_IDB_APPEND_DATA_HEX_PAIRS):
            chunk = pairs[i:i + cls.MAX_IDB_APPEND_DATA_HEX_PAIRS]
            chunk_str = ', '.join(chunk)
            split_line = f'{indent}idb_append_data <{chunk_str}>'
            split_lines.append(split_line)

        return split_lines

    @classmethod
    def _split_hex_data(cls, hex_data: str) -> List[str]:
        """Split hex data into chunks that fit within the byte limit, preferring comma boundaries."""
        chunks = []
        remaining_hex = hex_data.strip()

        while remaining_hex:
            if len(remaining_hex) <= cls.MAX_IDB_APPEND_DATA_HEX_LENGTH:
                # Remaining hex fits in one chunk
                chunks.append(remaining_hex)
                break

            # Find a good split point (prefer splitting at comma boundaries)
            chunk_size = cls.MAX_IDB_APPEND_DATA_HEX_LENGTH

            # Look for the last comma within the chunk
            chunk_candidate = remaining_hex[:chunk_size]
            last_comma = chunk_candidate.rfind(',')

            if last_comma > 0:
                # Split before the comma
                chunks.append(remaining_hex[:last_comma])
                # Skip the comma when advancing (last_comma + 1)
                remaining_hex = remaining_hex[last_comma + 1:]
            else:
                # No comma found, split at character boundary
                chunks.append(remaining_hex[:chunk_size])
                remaining_hex = remaining_hex[chunk_size:]

        return chunks

    @classmethod
    def _is_long_dod_data(cls, line: str) -> bool:
        """Check if a line contains a dod_data with long hex data."""
        line_clean = line.strip()
        if not line_clean.startswith('dod_data'):
            return False

        # Extract hex content from angle brackets (single-line only)
        hex_content = cls._extract_hex_from_dod_data(line_clean)
        return hex_content and len(hex_content) > cls.MAX_DOD_DATA_HEX_LENGTH

    @classmethod
    def _is_long_dod_data_hex(cls, line: str) -> bool:
        """Check if line contains dod_data with long hex pairs."""
        line_clean = line.strip()
        if not line_clean.startswith('dod_data'):
            return False

        # Check for hex-pair format: <2Ax, 3Bx, ...>
        hex_content = cls._extract_hex_pairs_from_dod_data(line_clean)
        if not hex_content:
            return False

        # Count comma-separated hex pairs
        pairs = [p.strip() for p in hex_content.split(',') if p.strip()]
        return len(pairs) > cls.MAX_DOD_DATA_HEX_PAIRS

    @classmethod
    def _extract_hex_from_dod_data(cls, line: str) -> str:
        """Extract hex content from dod_data <hex_data> format (continuous hex only, LEGACY)."""
        # Look for continuous hex data (no commas, no 'x' suffix - legacy format)
        match = re.search(r'dod_data\s*<\s*([0-9A-Fa-f\s]+)\s*>', line)
        if match:
            content = match.group(1)
            # Verify it's continuous hex (no 'x' or commas)
            if 'x' not in content.lower() and ',' not in content:
                return content
        return ""

    @classmethod
    def _extract_hex_pairs_from_dod_data(cls, line: str) -> str:
        """Extract hex-pair content from dod_data <2Ax, 3Bx, ...> format."""
        match = re.search(r'dod_data\s*<\s*([0-9A-Fa-fx, ]+)\s*>', line)
        if match:
            content = match.group(1)
            # Verify it looks like hex pairs (contains 'x' and commas)
            if 'x' in content.lower() and ',' in content:
                return content
        return ""

    @classmethod
    def _split_dod_data_line(cls, line: str) -> List[str]:
        """Split a long dod_data line into multiple smaller ones."""
        # Extract the indentation and hex content
        indent_match = re.match(r'^(\s*)', line)
        indent = indent_match.group(1) if indent_match else ""

        hex_content = cls._extract_hex_from_dod_data(line)
        if not hex_content:
            return [line]  # Fallback if we can't parse it

        # Clean hex content - remove all whitespace
        cleaned_hex = re.sub(r'\s+', '', hex_content)

        # Split hex data into chunks that fit within the limit
        hex_chunks = []
        remaining_hex = cleaned_hex

        while remaining_hex:
            if len(remaining_hex) <= cls.MAX_DOD_DATA_HEX_LENGTH:
                # Remaining hex fits in one chunk
                hex_chunks.append(remaining_hex)
                break

            # Find a good split point (prefer splitting at comma boundaries)
            chunk_size = cls.MAX_DOD_DATA_HEX_LENGTH

            # Look for the last comma within the chunk
            chunk_candidate = remaining_hex[:chunk_size]
            last_comma = chunk_candidate.rfind(',')

            if last_comma > 0:
                # Split before the comma
                hex_chunks.append(remaining_hex[:last_comma])
                # Skip the comma when advancing (last_comma + 1)
                remaining_hex = remaining_hex[last_comma + 1:]
            else:
                # No comma found, split at character boundary
                hex_chunks.append(remaining_hex[:chunk_size])
                remaining_hex = remaining_hex[chunk_size:]

        # Generate dod_data lines for each chunk
        split_lines = []
        for chunk in hex_chunks:
            split_line = f'{indent}dod_data <{chunk}>'
            split_lines.append(split_line)

        return split_lines

    @classmethod
    def _split_dod_data_hex_line(cls, line: str) -> List[str]:
        """Split a long dod_data hex-pair line into multiple smaller ones."""
        indent_match = re.match(r'^(\s*)', line)
        indent = indent_match.group(1) if indent_match else ""

        hex_content = cls._extract_hex_pairs_from_dod_data(line)
        if not hex_content:
            return [line]  # Fallback

        # Split into individual hex pairs
        pairs = [p.strip() for p in hex_content.split(',') if p.strip()]

        # Chunk into groups
        split_lines = []
        for i in range(0, len(pairs), cls.MAX_DOD_DATA_HEX_PAIRS):
            chunk = pairs[i:i + cls.MAX_DOD_DATA_HEX_PAIRS]
            chunk_str = ', '.join(chunk)
            split_line = f'{indent}dod_data <{chunk_str}>'
            split_lines.append(split_line)

        return split_lines

    @classmethod
    def _is_raw_data(cls, line: str) -> bool:
        """Check if a line contains a raw_data atom."""
        line_clean = line.strip()
        return line_clean.startswith('raw_data')

    @classmethod
    def _validate_raw_data(cls, line: str) -> bool:
        """
        Validate raw_data format: raw_data <"hex">

        Args:
            line: Line to validate

        Returns:
            True if valid, False otherwise
        """
        line_clean = line.strip()

        # Check format: raw_data <"hex_content">
        match = re.search(r'raw_data\s*<\s*"([A-Fa-f0-9]+)"\s*>', line_clean)
        if not match:
            logger.warning(f"Invalid raw_data format (expected: raw_data <\"HEX\">): {line_clean[:100]}")
            return False

        hex_content = match.group(1)

        # Check length constraint
        if len(hex_content) > cls.MAX_RAW_DATA_HEX_LENGTH:
            logger.warning(
                f"raw_data hex exceeds max length: {len(hex_content)} > {cls.MAX_RAW_DATA_HEX_LENGTH} "
                f"(max {cls.MAX_RAW_DATA_HEX_LENGTH // 2} bytes)"
            )
            return False

        return True

    @classmethod
    def parse_preserving_actions(cls, fdo_script: str) -> List[Dict[str, Any]]:
        """
        Parse FDO script preserving action blocks as atomic units.
        Automatically splits long man_append_data and idb_append_data blocks to prevent P3 segmentation issues.

        Args:
            fdo_script: FDO script text with atoms/action blocks

        Returns:
            List of atom units with metadata:
            {
                'content': str,      # The atom content (single line or full block)
                'is_action': bool,   # True if this is an action block
                'type': str,         # 'action_block' or 'single_atom'
                'line_start': int,   # Starting line number (0-indexed)
                'line_end': int      # Ending line number (0-indexed)
            }
        """
        # Preprocess script to split long man_append_data blocks
        preprocessed_script = cls.preprocess_script(fdo_script)

        atom_units = []
        lines = preprocessed_script.strip().split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Check if this is an action atom with nested content
            if cls._is_action_atom(line):
                block_result = cls._parse_action_block(lines, i)
                if block_result:
                    atom_units.append(block_result)
                    i = block_result['line_end'] + 1
                else:
                    # Fallback - treat as single atom if parsing failed
                    atom_units.append({
                        'content': line,
                        'is_action': False,
                        'type': 'single_atom',
                        'line_start': i,
                        'line_end': i
                    })
                    i += 1
            else:
                # Check if this is a raw_data atom
                is_raw_data = cls._is_raw_data(line)

                # Regular single atom (including raw_data)
                atom_units.append({
                    'content': line,
                    'is_action': False,
                    'is_raw_data': is_raw_data,
                    'type': 'raw_data_atom' if is_raw_data else 'single_atom',
                    'line_start': i,
                    'line_end': i
                })
                i += 1

        logger.info(f"Parsed {len(atom_units)} atom units ({sum(1 for u in atom_units if u['is_action'])} action blocks)")
        return atom_units

    @classmethod
    def _is_action_atom(cls, line: str) -> bool:
        """Check if a line starts an action atom that may have nested content."""
        line_clean = line.strip()
        return any(action in line_clean for action in cls.ACTION_ATOMS)

    @classmethod
    def _parse_action_block(cls, lines: List[str], start_idx: int) -> Dict[str, Any]:
        """
        Parse an action block starting at start_idx.

        Returns:
            Dict with parsed action block or None if parsing failed
        """
        if start_idx >= len(lines):
            return None

        action_line = lines[start_idx].strip()
        block_lines = [action_line]
        current_idx = start_idx + 1

        # Look for opening bracket or nested content
        if current_idx < len(lines):
            next_line = lines[current_idx].strip()

            # Handle explicit bracket opening
            if next_line == '<':
                block_lines.append(next_line)
                current_idx += 1

                # Parse bracketed content with depth tracking
                depth = 1
                while current_idx < len(lines) and depth > 0:
                    curr_line = lines[current_idx].strip()
                    block_lines.append(curr_line)

                    # Track bracket nesting depth
                    if curr_line == '<':
                        depth += 1
                    elif curr_line == '>':
                        depth -= 1

                    current_idx += 1

            # Handle implicit nested atoms (no explicit brackets)
            elif cls._looks_like_nested_atom(next_line):
                # Collect atoms until we hit something that doesn't look nested
                while (current_idx < len(lines) and
                       lines[current_idx].strip() and
                       cls._looks_like_nested_atom(lines[current_idx].strip())):
                    block_lines.append(lines[current_idx].strip())
                    current_idx += 1

        # Only consider it an action block if we found nested content
        if len(block_lines) > 1:
            return {
                'content': '\n'.join(block_lines),
                'is_action': True,
                'type': 'action_block',
                'line_start': start_idx,
                'line_end': current_idx - 1
            }
        else:
            # Single line action - treat as regular atom
            return {
                'content': action_line,
                'is_action': False,
                'type': 'single_atom',
                'line_start': start_idx,
                'line_end': start_idx
            }

    @classmethod
    def _looks_like_nested_atom(cls, line: str) -> bool:
        """
        Determine if a line looks like it could be nested content within an action.
        """
        line_clean = line.strip()
        if not line_clean:
            return False

        # Common nested patterns
        nested_patterns = [
            r'^\s*\w+_\w+\s*<',  # Atom with parameters like "sm_send_k1 <8-50934>"
            r'^\s*uni_start_stream',
            r'^\s*uni_end_stream',
            r'^\s*man_\w+',      # Management atoms
            r'^\s*mat_\w+',      # Material atoms
            r'^\s*sm_\w+',       # State machine atoms
            r'^\s*<$',           # Opening bracket
            r'^\s*>$'            # Closing bracket
        ]

        return any(re.match(pattern, line_clean) for pattern in nested_patterns)

    @classmethod
    def validate_fdo_syntax(cls, fdo_script: str) -> Dict[str, Any]:
        """
        Basic validation of FDO script syntax.

        Returns:
            {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'stats': Dict[str, int]
            }
        """
        errors = []
        warnings = []
        stats = {
            'total_lines': 0,
            'atom_count': 0,
            'action_blocks': 0,
            'empty_lines': 0
        }

        lines = fdo_script.strip().split('\n')
        stats['total_lines'] = len(lines)

        bracket_depth = 0
        stream_depth = 0

        for i, line in enumerate(lines, 1):
            line_clean = line.strip()

            if not line_clean:
                stats['empty_lines'] += 1
                continue

            stats['atom_count'] += 1

            # Check bracket balance
            if line_clean == '<':
                bracket_depth += 1
            elif line_clean == '>':
                bracket_depth -= 1
                if bracket_depth < 0:
                    errors.append(f"Line {i}: Unmatched closing bracket '>'")

            # Check stream balance
            if 'uni_start_stream' in line_clean:
                stream_depth += 1
            elif 'uni_end_stream' in line_clean:
                stream_depth -= 1
                if stream_depth < 0:
                    errors.append(f"Line {i}: Unmatched uni_end_stream")

            # Check for action blocks
            if cls._is_action_atom(line_clean):
                stats['action_blocks'] += 1

        # Final balance checks
        if bracket_depth != 0:
            errors.append(f"Unbalanced brackets: {bracket_depth} unclosed")
        if stream_depth != 0:
            errors.append(f"Unbalanced streams: {stream_depth} unclosed")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'stats': stats
        }