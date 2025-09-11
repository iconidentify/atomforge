#!/bin/bash
# Compile atom stream files using Docker
# Usage: ./run_compile.sh input_file.txt [output_file.str]

if [ $# -eq 0 ]; then
    echo "Usage: $0 <input_file.txt> [output_file.str]"
    echo "Example: $0 input/test.txt output/test.str"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="${2:-$(echo "$1" | sed 's/\.txt$/.str/')}"

# Ensure input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' not found"
    exit 1
fi

# Create output directory if needed
mkdir -p "$(dirname "$OUTPUT_FILE")"

echo "🚀 Starting Docker container for compilation..."
echo "   Input:  $INPUT_FILE"
echo "   Output: $OUTPUT_FILE"

docker-compose run --rm ada32-wine python3 ada32_runner.py compile "/ada32_toolkit/$INPUT_FILE" "/ada32_toolkit/$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Compilation completed successfully!"
    if [ -f "$OUTPUT_FILE" ]; then
        echo "📦 Output file size: $(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null) bytes"
    fi
else
    echo "❌ Compilation failed!"
    exit 1
fi