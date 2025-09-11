#!/bin/bash
# Decompile binary stream files using Docker
# Usage: ./run_decompile.sh input_file.str [output_file.txt]

if [ $# -eq 0 ]; then
    echo "Usage: $0 <input_file.str> [output_file.txt]"
    echo "Example: $0 input/test.str output/test.txt"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="${2:-$(echo "$1" | sed 's/\.str$/.txt/')}"

# Ensure input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' not found"
    exit 1
fi

# Create output directory if needed
mkdir -p "$(dirname "$OUTPUT_FILE")"

echo "🚀 Starting Docker container for decompilation..."
echo "   Input:  $INPUT_FILE"
echo "   Output: $OUTPUT_FILE"

docker-compose run --rm ada32-wine python3 ada32_runner.py decompile "/ada32_toolkit/$INPUT_FILE" "/ada32_toolkit/$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Decompilation completed successfully!"
    if [ -f "$OUTPUT_FILE" ]; then
        echo "📄 Output file size: $(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null) bytes"
    fi
else
    echo "❌ Decompilation failed!"
    exit 1
fi