# Research Materials

This directory contains the original research materials and reference implementations that form the foundation of the ADA32 toolkit development.

## Contents

### star_tool/
Original STAR tool implementation (US 50/32 version)
- **ADA.BIN**: Core ADA binary
- **ADA32.DLL**: Main ADA32 library (103KB, 1999) - **Ada32.dll v1**
- **DIAG.EXE**: Diagnostic executable
- **ATOMS.ADA**: Atom definitions
- **MASTER.TOL**: Master tolerance file
- **README.txt**: Original documentation

### dbviewer_original/
Original DBViewer application and supporting libraries
- **Dbview.exe**: Main DBViewer executable
- **Ada32.dll**: ADA32 runtime library (239KB, 1997) - **Ada32.dll v2**
- **Supporting DLLs**: Image processing and system libraries

### Additional Files
- **Ada.bin**: Additional ADA binary for research
- **Ada32_exports.json**: Exported function definitions from ADA32 libraries

## Purpose

These materials serve as:
1. **Reference implementations** for understanding the original ADA32 format
2. **Testing baselines** for validating our own implementations
3. **Research artifacts** documenting the evolution of the toolkit
4. **Compatibility references** for ensuring our tools work with legacy systems

## Usage

These files are primarily for research and reference purposes. They should not be modified as they represent the original implementations we're building upon.

For development work, see the main `src/`, `research/`, and `bin/` directories.
