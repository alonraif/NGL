#!/usr/bin/env python3
"""
Test script for modular parsers
"""
import sys
from parsers import get_parser, PARSERS

def test_parser_registry():
    """Test that all parsers are registered"""
    print("Testing parser registry...")
    print(f"Registered parsers: {list(PARSERS.keys())}")

    for mode in PARSERS.keys():
        try:
            parser = get_parser(mode)
            print(f"  ✓ {mode}: {parser.__class__.__name__}")
        except Exception as e:
            print(f"  ✗ {mode}: ERROR - {e}")
            return False

    return True

def test_invalid_mode():
    """Test that invalid mode raises error"""
    print("\nTesting invalid mode...")
    try:
        parser = get_parser('invalid_mode')
        print("  ✗ Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"  ✓ Correctly raised ValueError: {e}")
        return True

if __name__ == '__main__':
    print("=" * 60)
    print("MODULAR PARSER TEST SUITE")
    print("=" * 60)

    success = True

    # Test parser registry
    if not test_parser_registry():
        success = False

    # Test invalid mode
    if not test_invalid_mode():
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✓ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        sys.exit(1)
