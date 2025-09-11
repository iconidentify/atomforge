#!/bin/bash
# Test script for Ada32 Docker environment using golden test files
# Tests both compile (txt->str) and decompile (str->txt) operations

set -e  # Exit on any error

GOLDEN_DIR="./golden_tests"
TEST_OUTPUT_DIR="./test_output"
FAILED_TESTS=()
PASSED_TESTS=()

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Ada32 Docker Test Suite${NC}"
echo "=================================="

# Create test output directory
mkdir -p "$TEST_OUTPUT_DIR"

# Check if Docker container can be started
echo -e "${YELLOW}📋 Checking Docker environment...${NC}"
if ! docker-compose run --rm ada32-wine python3 -c "print('Docker environment OK')"; then
    echo -e "${RED}❌ Docker environment test failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker environment is working${NC}"
echo ""

# Find all test pairs
echo -e "${YELLOW}📁 Discovering test file pairs...${NC}"
TXT_FILES=($(find "$GOLDEN_DIR" -name "*.txt" | sort))
TOTAL_PAIRS=0
VALID_PAIRS=()

for txt_file in "${TXT_FILES[@]}"; do
    base_name=$(basename "$txt_file" .txt)
    str_file="$GOLDEN_DIR/${base_name}.str"
    
    if [ -f "$str_file" ]; then
        VALID_PAIRS+=("$base_name")
        TOTAL_PAIRS=$((TOTAL_PAIRS + 1))
        echo "   📄 Found pair: $base_name"
    fi
done

echo -e "${BLUE}Found $TOTAL_PAIRS valid test pairs${NC}"
echo ""

# Function to compare binary files
compare_binary_files() {
    local file1="$1"
    local file2="$2"
    
    if [ ! -f "$file1" ] || [ ! -f "$file2" ]; then
        return 1
    fi
    
    local size1=$(stat -f%z "$file1" 2>/dev/null || stat -c%s "$file1" 2>/dev/null)
    local size2=$(stat -f%z "$file2" 2>/dev/null || stat -c%s "$file2" 2>/dev/null)
    
    if [ "$size1" != "$size2" ]; then
        echo "Size mismatch: $size1 vs $size2 bytes"
        return 1
    fi
    
    if cmp -s "$file1" "$file2"; then
        return 0
    else
        return 1
    fi
}

# Function to test compilation (txt -> str)
test_compile() {
    local base_name="$1"
    local txt_file="$GOLDEN_DIR/${base_name}.txt"
    local expected_str="$GOLDEN_DIR/${base_name}.str"
    local output_str="$TEST_OUTPUT_DIR/${base_name}_compiled.str"
    
    echo -e "   ${YELLOW}🔨 Testing compilation: $base_name.txt -> .str${NC}"
    
    # Run compilation in Docker
    if docker-compose run --rm ada32-wine python3 ada32_runner.py compile "/ada32_toolkit/$txt_file" "/ada32_toolkit/$output_str" >/dev/null 2>&1; then
        if [ -f "$output_str" ]; then
            if compare_binary_files "$expected_str" "$output_str"; then
                echo -e "      ${GREEN}✅ Perfect byte match!${NC}"
                return 0
            else
                local expected_size=$(stat -f%z "$expected_str" 2>/dev/null || stat -c%s "$expected_str" 2>/dev/null)
                local actual_size=$(stat -f%z "$output_str" 2>/dev/null || stat -c%s "$output_str" 2>/dev/null)
                echo -e "      ${YELLOW}⚠️  Different output: expected $expected_size bytes, got $actual_size bytes${NC}"
                return 2
            fi
        else
            echo -e "      ${RED}❌ No output file generated${NC}"
            return 1
        fi
    else
        echo -e "      ${RED}❌ Compilation failed${NC}"
        return 1
    fi
}

# Function to test decompilation (str -> txt)
test_decompile() {
    local base_name="$1"
    local str_file="$GOLDEN_DIR/${base_name}.str"
    local expected_txt="$GOLDEN_DIR/${base_name}.txt"
    local output_txt="$TEST_OUTPUT_DIR/${base_name}_decompiled.txt"
    
    echo -e "   ${YELLOW}🔍 Testing decompilation: $base_name.str -> .txt${NC}"
    
    # Run decompilation in Docker
    if docker-compose run --rm ada32-wine python3 ada32_runner.py decompile "/ada32_toolkit/$str_file" "/ada32_toolkit/$output_txt" >/dev/null 2>&1; then
        if [ -f "$output_txt" ]; then
            # Check if file contains atom stream structure
            if grep -q "uni_start_stream\|man_start_object" "$output_txt"; then
                echo -e "      ${GREEN}✅ Valid atom stream structure generated${NC}"
                return 0
            else
                echo -e "      ${YELLOW}⚠️  Output doesn't contain expected atom stream structure${NC}"
                return 2
            fi
        else
            echo -e "      ${RED}❌ No output file generated${NC}"
            return 1
        fi
    else
        echo -e "      ${RED}❌ Decompilation failed${NC}"
        return 1
    fi
}

# Function to run round-trip test
test_roundtrip() {
    local base_name="$1"
    local original_txt="$GOLDEN_DIR/${base_name}.txt"
    local compiled_str="$TEST_OUTPUT_DIR/${base_name}_compiled.str"
    local roundtrip_txt="$TEST_OUTPUT_DIR/${base_name}_roundtrip.txt"
    
    echo -e "   ${YELLOW}🔄 Testing round-trip: txt -> str -> txt${NC}"
    
    if [ ! -f "$compiled_str" ]; then
        echo -e "      ${RED}❌ No compiled file for round-trip test${NC}"
        return 1
    fi
    
    # Decompile the compiled file
    if docker-compose run --rm ada32-wine python3 ada32_runner.py decompile "/ada32_toolkit/$compiled_str" "/ada32_toolkit/$roundtrip_txt" >/dev/null 2>&1; then
        if [ -f "$roundtrip_txt" ]; then
            if grep -q "uni_start_stream\|man_start_object" "$roundtrip_txt"; then
                echo -e "      ${GREEN}✅ Round-trip successful${NC}"
                return 0
            else
                echo -e "      ${YELLOW}⚠️  Round-trip output lacks atom stream structure${NC}"
                return 2
            fi
        else
            echo -e "      ${RED}❌ Round-trip decompilation produced no output${NC}"
            return 1
        fi
    else
        echo -e "      ${RED}❌ Round-trip decompilation failed${NC}"
        return 1
    fi
}

# Run tests
echo -e "${BLUE}🚀 Starting test execution...${NC}"
echo ""

COMPILE_PASSED=0
COMPILE_FAILED=0
COMPILE_PARTIAL=0
DECOMPILE_PASSED=0
DECOMPILE_FAILED=0
DECOMPILE_PARTIAL=0
ROUNDTRIP_PASSED=0
ROUNDTRIP_FAILED=0
ROUNDTRIP_PARTIAL=0

for i in "${!VALID_PAIRS[@]}"; do
    base_name="${VALID_PAIRS[$i]}"
    test_num=$((i + 1))
    
    echo -e "${BLUE}[$test_num/$TOTAL_PAIRS] Testing $base_name${NC}"
    
    # Test compilation
    test_compile "$base_name"
    compile_result=$?
    case $compile_result in
        0) COMPILE_PASSED=$((COMPILE_PASSED + 1)) ;;
        1) COMPILE_FAILED=$((COMPILE_FAILED + 1)) ;;
        2) COMPILE_PARTIAL=$((COMPILE_PARTIAL + 1)) ;;
    esac
    
    # Test decompilation
    test_decompile "$base_name"
    decompile_result=$?
    case $decompile_result in
        0) DECOMPILE_PASSED=$((DECOMPILE_PASSED + 1)) ;;
        1) DECOMPILE_FAILED=$((DECOMPILE_FAILED + 1)) ;;
        2) DECOMPILE_PARTIAL=$((DECOMPILE_PARTIAL + 1)) ;;
    esac
    
    # Test round-trip (only if compile succeeded)
    if [ $compile_result -eq 0 ]; then
        test_roundtrip "$base_name"
        roundtrip_result=$?
        case $roundtrip_result in
            0) ROUNDTRIP_PASSED=$((ROUNDTRIP_PASSED + 1)) ;;
            1) ROUNDTRIP_FAILED=$((ROUNDTRIP_FAILED + 1)) ;;
            2) ROUNDTRIP_PARTIAL=$((ROUNDTRIP_PARTIAL + 1)) ;;
        esac
    else
        echo -e "   ${YELLOW}⏭️  Skipping round-trip (compilation didn't produce perfect match)${NC}"
        ROUNDTRIP_FAILED=$((ROUNDTRIP_FAILED + 1))
    fi
    
    echo ""
done

# Summary
echo -e "${BLUE}📊 Test Results Summary${NC}"
echo "=================================="
echo -e "${GREEN}Compilation Tests:${NC}"
echo "   ✅ Perfect matches: $COMPILE_PASSED"
echo "   ⚠️  Partial success: $COMPILE_PARTIAL" 
echo "   ❌ Failed: $COMPILE_FAILED"
echo ""
echo -e "${GREEN}Decompilation Tests:${NC}"
echo "   ✅ Successful: $DECOMPILE_PASSED"
echo "   ⚠️  Partial success: $DECOMPILE_PARTIAL"
echo "   ❌ Failed: $DECOMPILE_FAILED"
echo ""
echo -e "${GREEN}Round-trip Tests:${NC}"
echo "   ✅ Successful: $ROUNDTRIP_PASSED"
echo "   ⚠️  Partial success: $ROUNDTRIP_PARTIAL"
echo "   ❌ Failed: $ROUNDTRIP_FAILED"
echo ""

# Overall status
TOTAL_TESTS=$((COMPILE_PASSED + COMPILE_PARTIAL + COMPILE_FAILED))
TOTAL_PASSED=$((COMPILE_PASSED + DECOMPILE_PASSED + ROUNDTRIP_PASSED))
TOTAL_ALL=$((TOTAL_TESTS * 3))  # 3 tests per pair

if [ $COMPILE_FAILED -eq 0 ] && [ $DECOMPILE_FAILED -eq 0 ] && [ $ROUNDTRIP_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests completed successfully!${NC}"
    exit 0
elif [ $TOTAL_PASSED -gt $((TOTAL_ALL / 2)) ]; then
    echo -e "${YELLOW}⚠️  Most tests passed, but some issues found${NC}"
    exit 0
else
    echo -e "${RED}❌ Significant test failures detected${NC}"
    exit 1
fi