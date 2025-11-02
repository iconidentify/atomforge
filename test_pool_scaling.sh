#!/bin/bash
# Automated pool scaling performance test
# Tests the /compile-chunk endpoint with different pool sizes

set -e

FDO_FILE="/Users/chrisk/Documents/aol_lfg/source/atomforge/large_dod_test.fdo.txt"
URL="http://localhost:8000/compile-chunk"
ITERATIONS=3
POOL_SIZES=(1 5 30)
RESULTS_DIR="/tmp/pool_test_results_$$"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create results directory
mkdir -p "$RESULTS_DIR"

echo "=========================================="
echo "AtomForge Pool Scaling Performance Test"
echo "=========================================="
echo ""
echo "Test file: $FDO_FILE"
echo "Pool sizes: ${POOL_SIZES[@]}"
echo "Iterations per size: $ITERATIONS"
echo ""

test_pool_size() {
    local pool_size=$1
    echo ""
    echo -e "${BLUE}=========================================="
    echo -e "Testing with POOL_SIZE=${pool_size}"
    echo -e "==========================================${NC}"

    # Stop existing container
    echo -e "${YELLOW}Stopping Docker container...${NC}"
    docker compose down > /dev/null 2>&1 || true
    sleep 2

    # Start with new pool size
    echo -e "${YELLOW}Starting with FDO_DAEMON_POOL_SIZE=${pool_size}...${NC}"
    FDO_DAEMON_POOL_SIZE=${pool_size} docker compose up -d > /dev/null 2>&1

    # Wait for service to be ready
    echo -e "${YELLOW}Waiting for service to be ready...${NC}"
    max_wait=60
    count=0
    while [ $count -lt $max_wait ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            # Additional wait for pool to fully initialize
            sleep 5
            break
        fi
        sleep 2
        count=$((count + 2))
        echo -n "."
    done
    echo ""

    if [ $count -ge $max_wait ]; then
        echo -e "${RED}Service failed to start!${NC}"
        return 1
    fi

    # Verify pool status
    echo -e "${YELLOW}Verifying pool status...${NC}"
    pool_info=$(curl -s http://localhost:8000/health | jq -r '.pool')
    echo "$pool_info" | jq '.'

    # Read the FDO file
    FDO_SOURCE=$(cat "$FDO_FILE")

    # Create JSON payload
    cat > /tmp/chunk_payload_${pool_size}.json << PAYLOAD
{
  "source": $(echo "$FDO_SOURCE" | jq -Rs .),
  "enable_parallel": true
}
PAYLOAD

    echo ""
    echo -e "${GREEN}Running $ITERATIONS test iterations...${NC}"

    local chunks=""
    rm -f "$RESULTS_DIR/times_${pool_size}.txt"

    for i in $(seq 1 $ITERATIONS); do
        echo -n "  Iteration $i/$ITERATIONS: "

        START=$(python3 -c 'import time; print(time.time())')
        RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$URL" \
            -H "Content-Type: application/json" \
            -d @/tmp/chunk_payload_${pool_size}.json)
        END=$(python3 -c 'import time; print(time.time())')

        HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
        ELAPSED=$(python3 -c "print(f'{$END - $START:.2f}')")

        if [ "$HTTP_CODE" = "200" ]; then
            if [ -z "$chunks" ]; then
                chunks=$(echo "$RESPONSE" | head -n-1 | jq -r '.total_chunks // "N/A"')
            fi
            echo "$ELAPSED" >> "$RESULTS_DIR/times_${pool_size}.txt"
            echo -e "${GREEN}${ELAPSED}s${NC}"
        else
            echo -e "${RED}Error $HTTP_CODE${NC}"
            echo "$RESPONSE" | head -n-1 | jq -r '.detail.error // .detail // "Unknown error"' | head -c 200
        fi
    done

    # Calculate statistics
    if [ -f "$RESULTS_DIR/times_${pool_size}.txt" ]; then
        local times=$(cat "$RESULTS_DIR/times_${pool_size}.txt")
        local avg=$(python3 -c "times = [float(t) for t in '''$times'''.split()]; print(f'{sum(times)/len(times):.2f}')")
        local min=$(python3 -c "times = [float(t) for t in '''$times'''.split()]; print(f'{min(times):.2f}')")
        local max=$(python3 -c "times = [float(t) for t in '''$times'''.split()]; print(f'{max(times):.2f}')")

        # Store results
        echo "$avg" > "$RESULTS_DIR/avg_${pool_size}.txt"
        echo "$min" > "$RESULTS_DIR/min_${pool_size}.txt"
        echo "$max" > "$RESULTS_DIR/max_${pool_size}.txt"
        echo "$chunks" > "$RESULTS_DIR/chunks_${pool_size}.txt"

        echo ""
        echo -e "${GREEN}Results for pool_size=${pool_size}:${NC}"
        echo "  Average: ${avg}s"
        echo "  Min:     ${min}s"
        echo "  Max:     ${max}s"
        echo "  Chunks:  ${chunks}"
    fi

    # Clean up payload file
    rm -f /tmp/chunk_payload_${pool_size}.json
}

# Run tests for each pool size
for size in "${POOL_SIZES[@]}"; do
    test_pool_size $size
done

# Print comparison table
echo ""
echo ""
echo -e "${BLUE}=========================================="
echo "PERFORMANCE COMPARISON"
echo -e "==========================================${NC}"
echo ""
printf "%-12s %-12s %-12s %-12s %-12s\n" "Pool Size" "Avg Time" "Min Time" "Max Time" "Chunks"
printf "%-12s %-12s %-12s %-12s %-12s\n" "----------" "--------" "--------" "--------" "------"

for size in "${POOL_SIZES[@]}"; do
    if [ -f "$RESULTS_DIR/avg_${size}.txt" ]; then
        avg=$(cat "$RESULTS_DIR/avg_${size}.txt")
        min=$(cat "$RESULTS_DIR/min_${size}.txt")
        max=$(cat "$RESULTS_DIR/max_${size}.txt")
        chunks=$(cat "$RESULTS_DIR/chunks_${size}.txt")
        printf "%-12s %-12s %-12s %-12s %-12s\n" "$size" "${avg}s" "${min}s" "${max}s" "$chunks"
    else
        printf "%-12s %-12s %-12s %-12s %-12s\n" "$size" "N/A" "N/A" "N/A" "N/A"
    fi
done

# Calculate speedup
if [ -f "$RESULTS_DIR/avg_1.txt" ] && [ -f "$RESULTS_DIR/avg_30.txt" ]; then
    avg_1=$(cat "$RESULTS_DIR/avg_1.txt")
    avg_30=$(cat "$RESULTS_DIR/avg_30.txt")
    speedup=$(python3 -c "print(f'{$avg_1 / $avg_30:.2f}')")
    echo ""
    echo -e "${GREEN}Speedup (1 daemon -> 30 daemons): ${speedup}x${NC}"
fi

echo ""
echo -e "${BLUE}Test complete!${NC}"

# Clean up results directory
rm -rf "$RESULTS_DIR"
