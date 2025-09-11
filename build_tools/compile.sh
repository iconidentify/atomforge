#!/bin/bash
# Compile atom stream files using Ada32.dll in Docker

set -e

if [ $# -lt 1 ]; then
    echo "Usage: ./compile.sh <input.txt> [output.str]"
    echo "Example: ./compile.sh golden_tests/32-16.txt output.str"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="${2:-$(basename "$INPUT_FILE" .txt).str}"

echo "🚀 Starting Ada32 Docker compilation..."
echo "   Input:  $INPUT_FILE"
echo "   Output: $OUTPUT_FILE"

# Ensure output directory exists
mkdir -p output

# Run compilation in Docker Windows container
docker-compose run --rm ada32-windows python atom_stream_compiler_windows.py "$INPUT_FILE" "output/$OUTPUT_FILE"

echo "✅ Compilation completed: output/$OUTPUT_FILE"