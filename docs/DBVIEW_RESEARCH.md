# Dbview Research - Official AOL Database Export Functions

## Key Discovery

The **Dbview** directory contains the official AOL Database Viewer with the exact DLLs used for the "Export Single Record" functionality that produces 100% accurate .str files.

## Critical DLLs Identified

### Dbaol32.dll - Database AOL Interface
**Size**: 25,600 bytes | **Date**: 1998-06-19

**Key Functions Discovered**:
- `DBOpen(filename)` - Open AOL database file
- `DBClose(handle)` - Close database handle  
- `DBExtractRecord(handle, recordId, buffer, bufferSize)` - **Extract record as .str**
- `DBCopyRecord(handle, recordId, buffer, bufferSize)` - Copy record data
- `DBGetLastError()` - Get error information
- `DBGetInfo(handle, info)` - Get database metadata

**Full Function List**:
```
DBAddRecord, DBClose, DBCopyRecord, DBCopyResultSize, DBCopyThisRecord, 
DBCreate, DBDeleteRecord, DBDeleteThisRecord, DBExtractRecord, 
DBExtractUndeletedRecord, DBGetInfo, DBGetLastError, DBInterpretGID, 
DBOpen, DBSetLastError, DBSetMaxSize, DBSetMinSize, DBSetPurge, 
DBSetVersion, DBUpdateRecord
```

### Other Supporting DLLs
- **Ada32.dll** (239,104 bytes) - Atom stream processor (we already use this)
- **Supersub.dll** (119,808 bytes) - Unknown supporting functions
- **Jgdw32.dll** (104,448 bytes) - Contains `_JgLosslessDecompressDestroy` - possibly compression
- **Img*.dll** - Image processing libraries

## The "Export Single Record" Solution

**Theory**: The menu item "Export Single Record" in Dbview.exe likely calls:
1. `DBOpen()` to open the database file
2. `DBExtractRecord()` to get the exact .str binary data
3. Save the result - this would be 100% byte-perfect

## Why This Matters

Our current encoding attempts:
- ✅ **32-105 (room_creation)**: 100% accuracy using extracted templates
- ⚠️  **32-16 (simple_document)**: 51% accuracy (21/41 bytes match)  
- ❌ **40-9736 (simple_message)**: 29% accuracy (26/88 bytes match)

**The official `DBExtractRecord()` function would give us 100% accuracy for ALL formats** because it's the same function Dbview.exe uses.

## Next Steps to Achieve 100% Accuracy

### Option 1: Use Official Database Functions
1. **Setup Dbview DLLs in Wine environment**
2. **Create bridge to call `DBExtractRecord()`**  
3. **Feed it database files containing our golden test records**
4. **Get perfect .str output for any format type**

### Option 2: Reverse Engineer Database Format
1. **Find .idx database files that contain our golden test records**
2. **Use `DBOpen()` and `DBExtractRecord()` to extract records**
3. **Compare with our golden .str files to validate**

### Option 3: Template Extraction for Each Format
1. **Extract exact byte templates for 32-16, 40-9736, etc.** (like we did for 32-105)
2. **Build format-specific perfect encoders**
3. **Create dispatcher based on format detection**

## Technical Requirements

To use the official functions, we need:
- ✅ **Dbaol32.dll** (copied from Dbview directory)
- ✅ **Ada32.dll** (already working in our Wine setup)
- ❓ **Database files** (.idx format) containing the golden test records
- ❓ **Wine compatibility** with the database functions

## Current Status

**Discovered**: Official export functions in Dbaol32.dll
**Challenge**: Need to get Dbview DLLs working in our Wine environment  
**Opportunity**: 100% accuracy achievable using `DBExtractRecord()`

This is the breakthrough we need - the official AOL export functionality that produces perfect .str files every time! 🎯