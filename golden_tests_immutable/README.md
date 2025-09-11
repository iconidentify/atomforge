# Golden Test Data - IMMUTABLE

⚠️ **WARNING: This directory contains immutable reference data. DO NOT MODIFY these files.** ⚠️

## Purpose

This directory contains the original, unmodified reference files extracted from AOL's main.IDX database. These files serve as the target format for our compilation research and must never be changed to preserve the integrity of our testing and analysis.

## Files

### 32-105.str
- **Size**: 356 bytes
- **Format**: FDO (Flap Data Object) compressed binary format
- **Header**: `40 01 01 00 22 01`
- **Source**: Extracted from main.IDX at position 23057 (record 32)
- **Content**: Public Rooms in People Connection atom stream
- **Status**: **IMMUTABLE - DO NOT MODIFY**

### Other Reference Files
This directory contains 60+ additional .str/.txt pairs extracted from the main.IDX database, representing various AOL atom stream formats and UI elements.

## Usage

These files are used for:
1. **Accuracy validation** - Comparing our generated output against known-good data
2. **Format analysis** - Understanding the target binary structure
3. **Regression testing** - Ensuring our tools maintain compatibility
4. **Research reference** - Studying the compressed FDO format

## Data Integrity Rules

1. **Never edit** these files directly
2. **Never replace** with modified versions
3. **Always backup** before any repository changes
4. **Verify checksums** if integrity is questioned
5. **Use copies** for any analysis that might modify data

## Analysis Workflow

When analyzing these files:

1. **Copy to analysis directory**:
   ```bash
   cp golden_tests_immutable/32-105.str tests/analysis_copy_32-105.str
   ```

2. **Work with the copy** in your analysis tools

3. **Reference the original** only for comparison

## Historical Note

These files represent the working binary format produced by the original AOL atom stream compilation tools circa 1999-2001. They are the target we aim to reproduce programmatically through our Ada32.dll research.

## Contact

If you believe these files have been corrupted or need to be replaced, document the issue thoroughly and ensure you have the original source data before making any changes.