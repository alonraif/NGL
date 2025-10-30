#!/usr/bin/env python3
"""
Test script to verify timestamp normalization for lula2.py
"""
from dateutil import parser as date_parser

def normalize_timestamp(timestamp_str):
    """Normalize timestamp to remove microseconds (lula2.py compatible format)"""
    if not timestamp_str:
        return None

    try:
        dt = date_parser.parse(timestamp_str)
        # Format: YYYY-MM-DD HH:MM:SS+TZ (no microseconds)
        if dt.tzinfo:
            normalized = dt.strftime('%Y-%m-%d %H:%M:%S%z')
            # Add colon in timezone offset (e.g., +00:00 instead of +0000)
            if len(normalized) > 19:
                normalized = normalized[:-2] + ':' + normalized[-2:]
        else:
            normalized = dt.strftime('%Y-%m-%d %H:%M:%S')
        return normalized
    except Exception as e:
        print(f"Error parsing timestamp: {e}")
        return timestamp_str

# Test cases
test_cases = [
    # MediaCorp session case
    {
        'name': 'MediaCorp Session Start',
        'input': '2025-10-28 09:44:07.163363+00:00',
        'expected': '2025-10-28 09:44:07+00:00'
    },
    {
        'name': 'MediaCorp Session End',
        'input': '2025-10-28 10:05:14.218108+00:00',
        'expected': '2025-10-28 10:05:14+00:00'
    },
    # Edge cases
    {
        'name': 'No microseconds',
        'input': '2025-10-28 10:00:00+00:00',
        'expected': '2025-10-28 10:00:00+00:00'
    },
    {
        'name': 'No timezone',
        'input': '2025-10-28 10:00:00.123456',
        'expected': '2025-10-28 10:00:00'
    },
    {
        'name': 'Different timezone',
        'input': '2025-10-28 10:00:00.999999-05:00',
        'expected': '2025-10-28 10:00:00-05:00'
    },
]

print("=" * 80)
print("TIMESTAMP NORMALIZATION TEST")
print("=" * 80)
print()

all_passed = True

for test in test_cases:
    input_ts = test['input']
    expected = test['expected']
    result = normalize_timestamp(input_ts)

    passed = result == expected
    all_passed = all_passed and passed

    status = "✓ PASS" if passed else "✗ FAIL"

    print(f"{status} - {test['name']}")
    print(f"  Input:    {input_ts}")
    print(f"  Expected: {expected}")
    print(f"  Got:      {result}")

    if not passed:
        print(f"  ERROR: Result does not match expected!")
    print()

print("=" * 80)
if all_passed:
    print("✓ ALL TESTS PASSED")
else:
    print("✗ SOME TESTS FAILED")
print("=" * 80)
print()

# Test that the normalization preserves time accuracy
print("ACCURACY TEST:")
print("-" * 80)
original = '2025-10-28 10:05:14.218108+00:00'
normalized = normalize_timestamp(original)

dt_original = date_parser.parse(original)
dt_normalized = date_parser.parse(normalized)

time_diff = abs((dt_original - dt_normalized).total_seconds())

print(f"Original:   {original}")
print(f"Normalized: {normalized}")
print(f"Time difference: {time_diff} seconds")

if time_diff < 1.0:
    print("✓ Time accuracy preserved (difference < 1 second)")
else:
    print("✗ Time accuracy lost (difference >= 1 second)")
print()
