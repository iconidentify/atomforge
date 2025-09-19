#!/usr/bin/env python3
"""
ASCII Atom Registry System
Centralized configuration for FDO atoms that support bidirectional ASCII text conversion
"""

import json
import re
from typing import Dict, List, Optional, Any
from pathlib import Path


class AtomParameter:
    """Represents a parameter that supports ASCII text conversion"""

    def __init__(self, index: int, name: str, param_type: str = "ascii_text",
                 max_length: int = 1024, encoding: str = "utf-8",
                 validation_pattern: Optional[str] = None):
        self.index = index
        self.name = name
        self.type = param_type
        self.max_length = max_length
        self.encoding = encoding
        self.validation_pattern = validation_pattern

    def validate_text(self, text: str) -> tuple[bool, Optional[str]]:
        """Validate ASCII text input"""
        if len(text) > self.max_length:
            return False, f"Text exceeds maximum length of {self.max_length} characters"

        if self.validation_pattern:
            if not re.match(self.validation_pattern, text):
                return False, f"Text does not match required pattern"

        try:
            text.encode(self.encoding)
        except UnicodeEncodeError as e:
            return False, f"Text contains invalid characters for {self.encoding} encoding"

        return True, None


class AtomDefinition:
    """Represents an FDO atom that supports ASCII text parameters"""

    def __init__(self, name: str, description: str = "", parameters: List[AtomParameter] = None):
        self.name = name
        self.description = description
        self.parameters = parameters or []

    def get_ascii_parameter(self, index: int) -> Optional[AtomParameter]:
        """Get ASCII parameter by index"""
        for param in self.parameters:
            if param.index == index:
                return param
        return None

    def has_ascii_parameters(self) -> bool:
        """Check if atom has any ASCII parameters"""
        return len(self.parameters) > 0


class ASCIIAtomRegistry:
    """Registry for managing atoms that support ASCII text conversion"""

    def __init__(self):
        self.atoms: Dict[str, AtomDefinition] = {}
        self._load_default_atoms()

    def _load_default_atoms(self):
        """Load default atom definitions"""
        # chat_add_user - the example from the user
        chat_add_user = AtomDefinition(
            name="chat_add_user",
            description="Add user message to chat with ASCII text support",
            parameters=[
                AtomParameter(
                    index=0,
                    name="message",
                    param_type="ascii_text",
                    max_length=1024,
                    encoding="utf-8"
                )
            ]
        )
        self.atoms["chat_add_user"] = chat_add_user

        # Add more atoms as they are discovered
        # Example template for future additions:
        # new_atom = AtomDefinition(
        #     name="atom_name",
        #     description="Description of what this atom does",
        #     parameters=[
        #         AtomParameter(index=0, name="text_param", max_length=512)
        #     ]
        # )
        # self.atoms["atom_name"] = new_atom

    def register_atom(self, atom: AtomDefinition):
        """Register a new atom definition"""
        self.atoms[atom.name] = atom

    def get_atom(self, name: str) -> Optional[AtomDefinition]:
        """Get atom definition by name"""
        return self.atoms.get(name)

    def is_ascii_atom(self, name: str) -> bool:
        """Check if atom supports ASCII text conversion"""
        atom = self.get_atom(name)
        return atom is not None and atom.has_ascii_parameters()

    def get_all_ascii_atoms(self) -> List[str]:
        """Get list of all atom names that support ASCII text"""
        return [name for name, atom in self.atoms.items() if atom.has_ascii_parameters()]

    def export_to_json(self) -> str:
        """Export registry to JSON format"""
        data = {
            "atoms": {}
        }

        for name, atom in self.atoms.items():
            data["atoms"][name] = {
                "description": atom.description,
                "parameters": [
                    {
                        "index": param.index,
                        "name": param.name,
                        "type": param.type,
                        "max_length": param.max_length,
                        "encoding": param.encoding,
                        "validation_pattern": param.validation_pattern
                    }
                    for param in atom.parameters
                ]
            }

        return json.dumps(data, indent=2)

    def import_from_json(self, json_data: str):
        """Import registry from JSON format"""
        try:
            data = json.loads(json_data)

            for name, atom_data in data.get("atoms", {}).items():
                parameters = []
                for param_data in atom_data.get("parameters", []):
                    param = AtomParameter(
                        index=param_data["index"],
                        name=param_data["name"],
                        param_type=param_data.get("type", "ascii_text"),
                        max_length=param_data.get("max_length", 1024),
                        encoding=param_data.get("encoding", "utf-8"),
                        validation_pattern=param_data.get("validation_pattern")
                    )
                    parameters.append(param)

                atom = AtomDefinition(
                    name=name,
                    description=atom_data.get("description", ""),
                    parameters=parameters
                )
                self.register_atom(atom)

        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid JSON registry format: {e}")

    def save_to_file(self, file_path: str):
        """Save registry to JSON file"""
        Path(file_path).write_text(self.export_to_json(), encoding='utf-8')

    def load_from_file(self, file_path: str):
        """Load registry from JSON file"""
        if Path(file_path).exists():
            json_data = Path(file_path).read_text(encoding='utf-8')
            self.import_from_json(json_data)


# Global registry instance
_registry = None

def get_registry() -> ASCIIAtomRegistry:
    """Get the global ASCII atom registry instance"""
    global _registry
    if _registry is None:
        _registry = ASCIIAtomRegistry()
    return _registry


# Convenience functions
def is_ascii_atom(atom_name: str) -> bool:
    """Check if an atom supports ASCII text conversion"""
    return get_registry().is_ascii_atom(atom_name)


def get_ascii_atoms() -> List[str]:
    """Get list of all atoms that support ASCII text"""
    return get_registry().get_all_ascii_atoms()


def get_atom_definition(atom_name: str) -> Optional[AtomDefinition]:
    """Get atom definition by name"""
    return get_registry().get_atom(atom_name)