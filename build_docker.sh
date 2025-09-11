#!/bin/bash
# Build the Ada32 Docker environment
# This script builds the Windows container for Ada32 DLL operations

echo "🐳 Building Ada32 Docker environment..."
echo "   Platform: windows/amd64"
echo "   Using Apple Virtualization Framework"

docker-compose build --no-cache

if [ $? -eq 0 ]; then
    echo "✅ Docker environment built successfully!"
    echo ""
    echo "Next steps:"
    echo "  • Place .txt files in the ./input/ directory"
    echo "  • Run: ./run_compile.sh input/file.txt"
    echo "  • Run: ./run_decompile.sh input/file.str"
else
    echo "❌ Docker build failed!"
    exit 1
fi