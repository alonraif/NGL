#!/usr/bin/env python3
"""
Test that the actual parser module has the timestamp normalization code
"""
import sys
import os
import inspect

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("=" * 80)
print("PARSER MODULE VERIFICATION TEST")
print("=" * 80)
print()

# Import the parser modules
try:
    from parsers import get_parser
    from parsers.lula_wrapper import LulaWrapperParser, BandwidthParser
    print("✓ Successfully imported parser modules")
except Exception as e:
    print(f"✗ Failed to import parser modules: {e}")
    sys.exit(1)

print()

# Check that the process method has timestamp normalization
print("Checking LulaWrapperParser.process() method:")
print("-" * 80)

try:
    source = inspect.getsource(LulaWrapperParser.process)

    # Check for key indicators that normalization is present
    checks = [
        ('dateutil import', 'from dateutil import parser as date_parser' in source),
        ('begin_date normalization', 'normalized_begin_date' in source),
        ('end_date normalization', 'normalized_end_date' in source),
        ('strftime formatting', 'strftime' in source and '%Y-%m-%d %H:%M:%S%z' in source),
        ('Timezone colon fix', '[:-2]' in source and '[-2:]' in source),
        ('Logging added', 'logging' in source or 'logger' in source),
    ]

    all_present = True
    for check_name, check_result in checks:
        status = "✓" if check_result else "✗"
        print(f"  {status} {check_name}")
        if not check_result:
            all_present = False

    print()
    if all_present:
        print("✓ All timestamp normalization code is present")
    else:
        print("✗ Some normalization code is missing!")
        print()
        print("Method source preview:")
        print("-" * 80)
        lines = source.split('\n')[:30]
        for i, line in enumerate(lines, 1):
            print(f"{i:3}: {line}")

except Exception as e:
    print(f"✗ Error inspecting source code: {e}")

print()

# Check BandwidthParser
print("Checking BandwidthParser class:")
print("-" * 80)

try:
    # Check that BandwidthParser inherits from LulaWrapperParser
    if issubclass(BandwidthParser, LulaWrapperParser):
        print("✓ BandwidthParser inherits from LulaWrapperParser")
    else:
        print("✗ BandwidthParser does not inherit from LulaWrapperParser")

    # Check that it has process method
    if hasattr(BandwidthParser, 'process'):
        print("✓ BandwidthParser has process() method")
    else:
        print("✗ BandwidthParser missing process() method")

    # Check parse_output method
    if hasattr(BandwidthParser, 'parse_output'):
        print("✓ BandwidthParser has parse_output() method")

        source = inspect.getsource(BandwidthParser.parse_output)
        if 'forward filled to end_date' in source:
            print("✓ BandwidthParser has forward-fill logic")
        else:
            print("✗ BandwidthParser missing forward-fill logic")
    else:
        print("✗ BandwidthParser missing parse_output() method")

except Exception as e:
    print(f"✗ Error checking BandwidthParser: {e}")

print()

# Test instantiation
print("Testing parser instantiation:")
print("-" * 80)

try:
    parser = get_parser('md-bw')
    print(f"✓ Successfully created parser: {type(parser).__name__}")

    if isinstance(parser, BandwidthParser):
        print("✓ Parser is instance of BandwidthParser")
    else:
        print(f"✗ Parser is {type(parser).__name__}, expected BandwidthParser")

    if hasattr(parser, 'mode'):
        print(f"✓ Parser mode: {parser.mode}")
    else:
        print("✗ Parser missing 'mode' attribute")

except Exception as e:
    print(f"✗ Failed to instantiate parser: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
print()
print("Next Steps:")
print("  1. Restart the backend: docker compose restart backend")
print("  2. Test with actual session drill-down in the UI")
print("  3. Check backend logs for normalization messages")
print()
