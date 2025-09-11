#!/bin/bash
# Quick test for a single golden test file pair
# Usage: ./test_single.sh <base_name> (e.g., ./test_single.sh 32-105)

if [ $# -eq 0 ]; then
    echo "Usage: $0 <base_name>"
    echo "Example: $0 32-105"
    echo ""
    echo "Available test files:"
    find golden_tests -name "*.txt" | sed 's/golden_tests\///g' | sed 's/\.txt$//g' | sort | head -10
    exit 1
fi

BASE_NAME="$1"
TXT_FILE="golden_tests/${BASE_NAME}.txt"
STR_FILE="golden_tests/${BASE_NAME}.str"
OUTPUT_DIR="test_output"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧪 Testing $BASE_NAME${NC}"
echo "=================================="

# Check if files exist
if [ ! -f "$TXT_FILE" ]; then
    echo -e "${RED}❌ $TXT_FILE not found${NC}"
    exit 1
fi

if [ ! -f "$STR_FILE" ]; then
    echo -e "${RED}❌ $STR_FILE not found${NC}"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# Show file info
echo -e "${YELLOW}📄 Input files:${NC}"
TXT_SIZE=$(stat -f%z "$TXT_FILE" 2>/dev/null || stat -c%s "$TXT_FILE" 2>/dev/null)
STR_SIZE=$(stat -f%z "$STR_FILE" 2>/dev/null || stat -c%s "$STR_FILE" 2>/dev/null)
echo "   $TXT_FILE: $TXT_SIZE bytes"
echo "   $STR_FILE: $STR_SIZE bytes"
echo ""

# Preview the text file
echo -e "${YELLOW}📖 Text file preview (first 10 lines):${NC}"
head -10 "$TXT_FILE"
echo ""

# Test 1: Compile txt -> str
echo -e "${BLUE}🔨 Test 1: Compiling $BASE_NAME.txt -> .str${NC}"
COMPILED_STR="$OUTPUT_DIR/${BASE_NAME}_compiled.str"
if docker-compose run --rm ada32-wine python3 ada32_runner.py compile "/ada32_toolkit/$TXT_FILE" "/ada32_toolkit/$COMPILED_STR"; then
    if [ -f "$COMPILED_STR" ]; then
        COMPILED_SIZE=$(stat -f%z "$COMPILED_STR" 2>/dev/null || stat -c%s "$COMPILED_STR" 2>/dev/null)
        echo -e "${GREEN}✅ Compilation successful: $COMPILED_SIZE bytes${NC}"
        
        # Compare with expected
        if cmp -s "$STR_FILE" "$COMPILED_STR"; then
            echo -e "${GREEN}🎯 Perfect match with expected binary!${NC}"
        else
            echo -e "${YELLOW}⚠️  Different from expected (expected: $STR_SIZE bytes, got: $COMPILED_SIZE bytes)${NC}"
        fi
    else
        echo -e "${RED}❌ Compilation produced no output file${NC}"
    fi
else
    echo -e "${RED}❌ Compilation failed${NC}"
fi
echo ""

# Test 2: Decompile str -> txt
echo -e "${BLUE}🔍 Test 2: Decompiling $BASE_NAME.str -> .txt${NC}"
DECOMPILED_TXT="$OUTPUT_DIR/${BASE_NAME}_decompiled.txt"
if docker-compose run --rm ada32-wine python3 ada32_runner.py decompile "/ada32_toolkit/$STR_FILE" "/ada32_toolkit/$DECOMPILED_TXT"; then
    if [ -f "$DECOMPILED_TXT" ]; then
        DECOMPILED_SIZE=$(stat -f%z "$DECOMPILED_TXT" 2>/dev/null || stat -c%s "$DECOMPILED_TXT" 2>/dev/null)
        echo -e "${GREEN}✅ Decompilation successful: $DECOMPILED_SIZE bytes${NC}"
        
        # Show preview
        echo -e "${YELLOW}📖 Decompiled output preview:${NC}"
        head -10 "$DECOMPILED_TXT"
        echo ""
    else
        echo -e "${RED}❌ Decompilation produced no output file${NC}"
    fi
else
    echo -e "${RED}❌ Decompilation failed${NC}"
fi
echo ""

# Test 3: Round-trip (if compilation worked)
if [ -f "$COMPILED_STR" ]; then
    echo -e "${BLUE}🔄 Test 3: Round-trip test (txt -> str -> txt)${NC}"
    ROUNDTRIP_TXT="$OUTPUT_DIR/${BASE_NAME}_roundtrip.txt"
    if docker-compose run --rm ada32-wine python3 ada32_runner.py decompile "/ada32_toolkit/$COMPILED_STR" "/ada32_toolkit/$ROUNDTRIP_TXT"; then
        if [ -f "$ROUNDTRIP_TXT" ]; then
            ROUNDTRIP_SIZE=$(stat -f%z "$ROUNDTRIP_TXT" 2>/dev/null || stat -c%s "$ROUNDTRIP_TXT" 2>/dev/null)
            echo -e "${GREEN}✅ Round-trip successful: $ROUNDTRIP_SIZE bytes${NC}"
            
            # Show preview
            echo -e "${YELLOW}📖 Round-trip output preview:${NC}"
            head -10 "$ROUNDTRIP_TXT"
        else
            echo -e "${RED}❌ Round-trip produced no output file${NC}"
        fi
    else
        echo -e "${RED}❌ Round-trip failed${NC}"
    fi
else
    echo -e "${YELLOW}⏭️  Skipping round-trip test (compilation failed)${NC}"
fi

echo ""
echo -e "${BLUE}📋 Output files created in $OUTPUT_DIR/:${NC}"
ls -la "$OUTPUT_DIR"/${BASE_NAME}* 2>/dev/null || echo "   No output files created"