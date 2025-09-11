# Repository Organization Plan

## Current Status
The ada32_toolkit repository contains a mix of:
- Python research scripts (20+ files)
- Legacy directories (Dbview, docker_dbview)
- Configuration files
- Test data (golden_tests)
- Partially organized structure (bin/, src/, tests/, docs/)

## Organization Strategy

### 1. Keep As-Is (Working State)
Since the repository is in an active research state with many Python scripts, we'll organize by creating clear structure while preserving functionality:

```
ada32_toolkit/
├── research/           # Current root-level research files
│   ├── python/        # Python research scripts
│   ├── c_programs/    # C program research (in Docker container)
│   └── archives/      # Old test outputs
├── production/        # Stable, working tools
├── reference/         # Immutable data
│   ├── golden_tests_immutable/  # Protected reference files ✅
│   └── docs/          # Documentation ✅
├── legacy/            # Archive old directories
│   ├── Dbview/
│   └── docker_dbview/
└── tools/             # Configuration and build tools
```

### 2. Current Working Files (To Keep in Root)
Keep these in root for easy access during active development:
- docker-compose.yml ✅
- README.md ✅
- Key Python research scripts
- Build scripts

### 3. Immediate Actions Taken
✅ Created golden_tests_immutable/ with protection documentation
✅ Created docs/ directory with comprehensive research findings
✅ Created basic bin/, src/, tests/ structure
✅ Preserved all research work

## Key Findings Preserved
- **Working 413-byte compiler** documented and preserved
- **All research attempts** archived for future reference
- **Format analysis** showing compression requirements
- **Development environment** fully functional

## Next Steps (Optional)
1. Move Python scripts to research/python/ when ready
2. Archive legacy directories to legacy/
3. Consolidate build scripts in tools/

## Priority: Preserve Functionality
The current organization maintains all working capabilities while adding structure for future development.