# AOL Ada32 Toolkit

A comprehensive toolkit for working with AOL's Ada32.dll atom stream compilation system.

## Overview

This project provides tools and research for converting AOL atom stream text files (.txt) to binary stream files (.str) using the original Ada32.dll functions. Our research has successfully created a functional compiler that produces 413-byte binary files containing complete atom stream data.

## Repository Structure

```
ada32_toolkit/
├── bin/                    # Executables and DLLs
│   ├── dlls/              # Ada32.dll, Dbaol32.dll, and related DLLs
│   └── executables/       # Production-ready executables
├── src/                   # Source code (C programs)
│   ├── production/        # Working, production-ready code
│   ├── research/          # Experimental research code (57 files)
│   └── analysis/          # Binary analysis and format tools
├── research/              # Python research scripts
│   └── python/           # 20+ Python analysis and encoding scripts
├── research_materials/   # Original reference implementations and research materials
├── tests/                 # Test data and archived outputs
│   ├── fixtures/          # Test input files
│   └── output_archive/    # Historical test outputs (106 files)
├── docs/                  # Documentation
├── golden_tests_immutable/ # Reference data (DO NOT MODIFY)
├── build_tools/           # Docker, build scripts, configuration
└── docker-compose.yml     # Development environment
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Running the Compiler

1. **Start the development environment:**
   ```bash
   docker-compose run --rm ada32-wine bash
   ```

2. **Compile the production tool:**
   ```bash
   cd /ada32_toolkit
   i686-w64-mingw32-gcc -o bin/executables/atom_compiler.exe src/production/ada32_production_test.c
   ```

3. **Run the compiler:**
   ```bash
   wine bin/executables/atom_compiler.exe
   ```

This will convert `tests/fixtures/clean_32-105.txt` to a 413-byte binary .str file.

## Current Capabilities

### ✅ Working Features
- **Complete .txt to .str compilation** - Produces 413-byte binary files
- **Ada32.dll integration** - All major functions mapped and working
- **Content validation** - Output contains all UI elements and text data
- **Cross-platform development** - Works on macOS/Linux via Docker + Wine
- **Format analysis** - Comprehensive understanding of binary structures

### ⚠️ Limitations
- **413-byte vs 356-byte format** - Cannot produce the compressed 356-byte FDO format
- **Database functions** - Dbaol32.dll functions crash in current environment

## File Formats

### Input Format (.txt)
Text-based atom stream format:
```
uni_start_stream <00x>
  man_start_object <independent, "Public Rooms in People Connection">
  ...
```

### Output Format (.str)
- **413-byte format**: Complete binary atom stream (✅ Working)
- **356-byte format**: Compressed FDO format (❌ Target, not yet achievable)

## Key Files

### Production Code
- `src/production/ada32_production_test.c` - Main compiler implementation
- `src/production/atom_compiler.c` - Simplified compiler interface

### Research Code
- `src/research/test_refined_chaining.c` - Advanced function chaining experiments
- `src/research/test_reverse_chaining.c` - Alternative compilation approaches

### Analysis Tools
- `src/analysis/analyze_format_differences.c` - Binary format comparison
- `src/analysis/manual_compression.c` - Compression algorithm research

### Reference Data
- `golden_tests_immutable/32-105.str` - 356-byte target format (IMMUTABLE)
- `tests/fixtures/clean_32-105.txt` - Working input file

### Research Materials
- `research_materials/star_tool/` - Original STAR tool implementation
- `research_materials/dbviewer_original/` - Original DBViewer application
- `research_materials/dbviewer_docker/` - Docker-compatible DBViewer version
- `research_materials/README.md` - Documentation of research materials

## Development

### Environment Setup
The project uses Docker with Wine emulation to run Windows DLLs on Linux/macOS:

```bash
# Start development environment
docker-compose run --rm ada32-wine bash

# Compile Windows executable
i686-w64-mingw32-gcc -o output.exe source.c

# Run with Wine
wine output.exe
```

### Testing
Test fixtures are located in `tests/fixtures/` and should not be modified. All test outputs are archived in `tests/output_archive/` for historical reference.

## Documentation

- **[Research Findings](docs/RESEARCH_FINDINGS.md)** - Comprehensive analysis of Ada32.dll and related DLLs
- **[Golden Tests README](golden_tests_immutable/README.md)** - Information about immutable reference data

## Contributing

When working on this project:

1. **Test data is immutable** - Never modify files in `golden_tests_immutable/`
2. **Archive outputs** - Save test results to `tests/output_archive/` with descriptive names
3. **Document findings** - Update `docs/RESEARCH_FINDINGS.md` with new discoveries
4. **Preserve functionality** - Ensure the 413-byte compilation capability is maintained

## License

This project is for educational and research purposes, working with legacy AOL software components.