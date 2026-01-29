#!/usr/bin/env python3
"""
Test dial_code_utils module
"""

import os
import sys

# Add common directory to path for local testing
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "common"),
)

from dial_code_utils import parse_special_dial_code


def test_parse_special_dial_code():
    """Test the parse_special_dial_code function"""

    tests = [
        # (input, expected_output)
        ("*509723256826", ("9723256826", False, None)),  # *50: No EDC
        ("*549723256826", ("9723256826", True, "DC")),  # *54: DC code
        ("*559723256826", ("9723256826", True, None)),  # *55: Normal EDC
        ("9723256826", ("9723256826", True, None)),  # No prefix: Normal EDC
    ]

    print("Testing parse_special_dial_code()...")
    print("=" * 60)

    for input_num, expected in tests:
        result = parse_special_dial_code(input_num)

        status = "✓ PASS" if result == expected else "✗ FAIL"
        print(f"\n{status}")
        print(f"  Input:    {input_num}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")

        if result == expected:
            number, send_edc, edc_code = result
            print(f"  → Dial: {number}, Send EDC: {send_edc}, Code: {edc_code}")

        # Use assertion instead of return value
        assert (
            result == expected
        ), f"Failed for input {input_num}: expected {expected}, got {result}"

    print("\n" + "=" * 60)
    print("✓ All tests passed!")


if __name__ == "__main__":
    sys.exit(test_parse_special_dial_code())
