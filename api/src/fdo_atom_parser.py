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

    # Maximum hex data length before splitting idb_append_data (hex chars are 2 per byte, so ~100 hex chars = 50 bytes)
    MAX_IDB_APPEND_DATA_HEX_LENGTH = 400

    @classmethod
    def preprocess_script(cls, fdo_script: str) -> str:
        """
        Preprocess FDO script to split long man_append_data blocks into smaller chunks.

        Args:
            fdo_script: Original FDO script

        Returns:
            Modified FDO script with long text blocks split
        """
        lines = fdo_script.split('\n')
        processed_lines = []

        for line in lines:
            if cls._is_long_append_data(line):
                # Split this line into multiple man_append_data statements
                split_lines = cls._split_append_data_line(line)
                processed_lines.extend(split_lines)
                logger.debug(f"Split long man_append_data into {len(split_lines)} parts")
            elif cls._is_long_idb_append_data(line):
                # Split this line into multiple idb_append_data statements
                split_lines = cls._split_idb_append_data_line(line)
                processed_lines.extend(split_lines)
                logger.debug(f"Split long idb_append_data into {len(split_lines)} parts")
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
    def _extract_text_from_append_data(cls, line: str) -> str:
        """Extract text content from man_append_data <"text"> format."""
        match = re.search(r'man_append_data\s*<\s*"([^"]*)"', line)
        if match:
            return match.group(1)
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
    def _split_text_smartly(cls, text: str) -> List[str]:
        """Split text at semantic boundaries (sentences, then words)."""
        chunks = []
        remaining_text = text.strip()

        while remaining_text:
            if len(remaining_text) <= cls.MAX_APPEND_DATA_TEXT_LENGTH:
                # Remaining text fits in one chunk
                chunks.append(remaining_text)
                break

            # Find a good place to split within the limit
            chunk_end = cls._find_good_split_point(remaining_text, cls.MAX_APPEND_DATA_TEXT_LENGTH)
            chunk = remaining_text[:chunk_end].strip()

            if chunk:
                chunks.append(chunk)

            remaining_text = remaining_text[chunk_end:].strip()

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
    def _extract_hex_from_idb_append_data(cls, line: str) -> str:
        """Extract hex content from idb_append_data <hex_data> format."""
        # Look for hex data in angle brackets (without quotes, direct hex)
        match = re.search(r'idb_append_data\s*<\s*([A-Fa-f0-9]+)\s*>', line)
        if match:
            return match.group(1)
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

        # Split hex data into chunks that fit within the limit
        hex_chunks = cls._split_hex_data(hex_content)

        # Generate idb_append_data lines for each chunk
        split_lines = []
        for chunk in hex_chunks:
            split_line = f'{indent}idb_append_data <{chunk}>'
            split_lines.append(split_line)

        return split_lines

    @classmethod
    def _split_hex_data(cls, hex_data: str) -> List[str]:
        """Split hex data into chunks that fit within the byte limit."""
        chunks = []
        remaining_hex = hex_data.strip()

        while remaining_hex:
            if len(remaining_hex) <= cls.MAX_IDB_APPEND_DATA_HEX_LENGTH:
                # Remaining hex fits in one chunk
                chunks.append(remaining_hex)
                break

            # Split at an even boundary (hex pairs)
            chunk_size = cls.MAX_IDB_APPEND_DATA_HEX_LENGTH
            # Ensure we split on hex byte boundaries (even positions)
            if chunk_size % 2 == 1:
                chunk_size -= 1

            chunk = remaining_hex[:chunk_size]
            chunks.append(chunk)
            remaining_hex = remaining_hex[chunk_size:]

        return chunks

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
                # Regular single atom
                atom_units.append({
                    'content': line,
                    'is_action': False,
                    'type': 'single_atom',
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
                    # Also track stream nesting
                    elif 'uni_start_stream' in curr_line:
                        depth += 1
                    elif 'uni_end_stream' in curr_line:
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