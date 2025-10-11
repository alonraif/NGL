#!/bin/bash
# Test script to verify parallel decompression doesn't break parsers

set -e  # Exit on error

echo "========================================="
echo "Testing Parallel Decompression (Phase 1)"
echo "========================================="
echo ""

# Check if test file exists
TEST_FILE="${1:-/Users/alonraif/Code/ngl/test_data/unitLogs_16.bz2}"

if [ ! -f "$TEST_FILE" ]; then
    echo "❌ Test file not found: $TEST_FILE"
    echo "Usage: $0 [path/to/test_file.tar.bz2]"
    exit 1
fi

echo "📁 Test file: $TEST_FILE"
echo "📊 File size: $(du -h "$TEST_FILE" | cut -f1)"
echo ""

# Array of parsers to test
PARSERS=("sessions" "bw" "md" "known" "grading" "memory" "id")
TIMEZONE="UTC"

echo "Testing parsers: ${PARSERS[@]}"
echo ""

# Counter for passed/failed tests
PASSED=0
FAILED=0
TOTAL=${#PARSERS[@]}

# Test each parser
for PARSER in "${PARSERS[@]}"; do
    echo "----------------------------------------"
    echo "Testing parser: $PARSER"
    echo "----------------------------------------"

    # Run parser and measure time
    START_TIME=$(date +%s)

    if docker-compose exec -T backend python3 /app/lula2.py "$TEST_FILE" -p "$PARSER" -t "$TIMEZONE" > /tmp/ngl_test_${PARSER}.txt 2>&1; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))

        # Check if output has content
        OUTPUT_SIZE=$(wc -c < /tmp/ngl_test_${PARSER}.txt)

        if [ "$OUTPUT_SIZE" -gt 10 ]; then
            echo "✅ PASSED - Duration: ${DURATION}s - Output: ${OUTPUT_SIZE} bytes"
            PASSED=$((PASSED + 1))

            # Show first few lines of output
            echo "   Sample output:"
            head -3 /tmp/ngl_test_${PARSER}.txt | sed 's/^/   /'
        else
            echo "❌ FAILED - Output too small (${OUTPUT_SIZE} bytes)"
            FAILED=$((FAILED + 1))
        fi
    else
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        echo "❌ FAILED - Parser crashed - Duration: ${DURATION}s"
        echo "   Error output:"
        tail -5 /tmp/ngl_test_${PARSER}.txt | sed 's/^/   /'
        FAILED=$((FAILED + 1))
    fi

    echo ""
done

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "Total parsers tested: $TOTAL"
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 All tests passed!"
    echo ""
    echo "Next steps:"
    echo "1. Test with a larger file to measure performance improvement"
    echo "2. Monitor CPU usage during parsing (should use multiple cores now)"
    echo "3. Compare timing with baseline measurements"
    exit 0
else
    echo "⚠️  Some tests failed. Please review the errors above."
    exit 1
fi
