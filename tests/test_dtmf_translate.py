#!/usr/bin/env python3
"""
Unit tests for DTMF translation dialplan subroutine.

This test suite validates the sub_dtmf_translate function in Asterisk's
dialplan by executing test calls and parsing the Asterisk logs.

Requirements:
    - SSH access to target device (root@GWorks2 by default)
    - Asterisk running on target
    - sub_dtmf_translate subroutine in extensions.conf

Usage:
    ./test_dtmf_translate.py
    python3 test_dtmf_translate.py
    python3 -m pytest test_dtmf_translate.py -v
"""

import os
import re
import subprocess
import sys
import time
import unittest
from typing import Optional, Tuple


class DTMFTranslationTest(unittest.TestCase):
    """Test DTMF translation dialplan subroutine via Asterisk CLI."""

    # Configuration
    TARGET_HOST = os.environ.get("TARGET_HOST", "root@GWorks2")
    TEST_CONTEXT = "test_dtmf_inline"
    ASTERISK_CLI = "asterisk -rx"
    VERBOSE_MODE = os.environ.get("VERBOSE", "0") == "1"

    @classmethod
    def setUpClass(cls):
        """Set up test environment - add test context to Asterisk."""
        print(f"\n{'=' * 70}")
        print("DTMF Translation Test Suite")
        print(f"Target: {cls.TARGET_HOST}")
        print(f"{'=' * 70}\n")

        # Create a temporary test context in Asterisk
        cls._create_test_context()

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment - remove test context."""
        cls._remove_test_context()
        print(f"\n{'=' * 70}")
        print("Test suite completed")
        print(f"{'=' * 70}\n")

    @classmethod
    def _create_test_context(cls):
        """Create test dialplan context on target Asterisk."""
        test_dialplan = f"""
[{cls.TEST_CONTEXT}]
exten => test,1,NoOp(=== DTMF Test Runner ===)
 same => n,Set(TEST_INPUT=${{ARG1}})
 same => n,Gosub(sub_dtmf_translate,s,1(${{TEST_INPUT}}))
 same => n,NoOp(DTMF_TEST_RESULT:${{DTMF_TRANSLATED}})
 same => n,Hangup()
"""
        # Add to extensions.conf on target
        cmd = [
            "ssh",
            cls.TARGET_HOST,
            f"cat >> /etc/asterisk/extensions.conf <<'EOF_TEST'\n{test_dialplan}\nEOF_TEST\n",
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=False)

        # Reload dialplan
        cls._asterisk_cli("dialplan reload")
        time.sleep(1)  # Give Asterisk time to reload

    @classmethod
    def _remove_test_context(cls):
        """Remove test dialplan context from target Asterisk."""
        # Remove the test context from extensions.conf
        cmd = [
            "ssh",
            cls.TARGET_HOST,
            f"sed -i '/\\[{cls.TEST_CONTEXT}\\]/,/^$/d' /etc/asterisk/extensions.conf",
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=False)

        # Reload dialplan
        cls._asterisk_cli("dialplan reload")

    @classmethod
    def _asterisk_cli(cls, command: str) -> str:
        """Execute Asterisk CLI command on target."""
        cmd = ["ssh", cls.TARGET_HOST, f"{cls.ASTERISK_CLI} '{command}'"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.stdout

    def _translate_via_asterisk(self, input_str: str) -> Optional[str]:
        """
        Execute DTMF translation via Asterisk and return result.

        Args:
            input_str: Raw DTMF input string

        Returns:
            Translated string or None if test failed
        """
        # Originate a call to the test extension
        # We'll pass the input as a channel variable and read the result from logs
        timestamp = int(time.time() * 1000)  # Unique timestamp for this test

        # Use Asterisk originate with variable passing
        originate_cmd = (
            f"channel originate "
            f'Local/test@{self.TEST_CONTEXT} '
            f"application NoOp "
            f'"{input_str}"'
        )

        # Execute and capture output
        output = self._asterisk_cli(originate_cmd)

        # Alternative: Use Asterisk log parsing
        # Get recent logs and look for our test result marker
        log_cmd = [
            "ssh",
            self.TARGET_HOST,
            f"tail -100 /var/log/asterisk/messages | grep 'DTMF_TEST_RESULT' | tail -1",
        ]
        result = subprocess.run(log_cmd, capture_output=True, text=True, check=False)
        log_output = result.stdout.strip()

        if self.VERBOSE_MODE:
            print(f"  Input: {input_str!r}")
            print(f"  Log: {log_output}")

        # Parse the result from log
        # Expected format: NoOp(DTMF_TEST_RESULT:ABC)
        match = re.search(r"DTMF_TEST_RESULT:(.*)$", log_output)
        if match:
            translated = match.group(1).strip()
            # Clean up any trailing quotes or parentheses
            translated = re.sub(r"[)\"]$", "", translated)
            return translated

        # Fallback: Try to get from verbose output
        if "DTMF_TEST_RESULT:" in output:
            match = re.search(r"DTMF_TEST_RESULT:(\S+)", output)
            if match:
                return match.group(1)

        return None

    def _assert_translation(self, input_str: str, expected: str, msg: str = ""):
        """Helper to test translation with better error messages."""
        result = self._translate_via_asterisk(input_str)

        error_msg = f"\nTranslation failed: {input_str!r}\n  Expected: {expected!r}\n  Got: {result!r}"
        if msg:
            error_msg = f"{msg}\n{error_msg}"

        self.assertEqual(result, expected, error_msg)

    # Test cases
    def test_single_letter_A(self):
        """Test: *1 should translate to A"""
        self._assert_translation("*1", "A", "Single letter A")

    def test_single_letter_B(self):
        """Test: *2 should translate to B"""
        self._assert_translation("*2", "B", "Single letter B")

    def test_single_letter_C(self):
        """Test: *3 should translate to C"""
        self._assert_translation("*3", "C", "Single letter C")

    def test_single_letter_D(self):
        """Test: *4 should translate to D"""
        self._assert_translation("*4", "D", "Single letter D")

    def test_single_letter_E(self):
        """Test: *5 should translate to E"""
        self._assert_translation("*5", "E", "Single letter E")

    def test_single_letter_F(self):
        """Test: *6 should translate to F"""
        self._assert_translation("*6", "F", "Single letter F")

    def test_literal_star(self):
        """Test: *8 should translate to *"""
        self._assert_translation("*8", "*", "Literal asterisk")

    def test_literal_hash(self):
        """Test: *9 should translate to #"""
        self._assert_translation("*9", "#", "Literal hash/pound")

    def test_multiple_letters_ABC(self):
        """Test: *1*2*3 should translate to ABC"""
        self._assert_translation("*1*2*3", "ABC", "Multiple letters ABC")

    def test_all_letters_ABCDEF(self):
        """Test: *1*2*3*4*5*6 should translate to ABCDEF"""
        self._assert_translation("*1*2*3*4*5*6", "ABCDEF", "All letters A-F")

    def test_digits_only_passthrough(self):
        """Test: 9725551234 should pass through unchanged"""
        self._assert_translation("9725551234", "9725551234", "Digits only")

    def test_mixed_digits_and_letters(self):
        """Test: 123*4*5*6 should translate to 123DEF"""
        self._assert_translation("123*4*5*6", "123DEF", "Mixed digits and letters")

    def test_both_literals(self):
        """Test: *8*9 should translate to *#"""
        self._assert_translation("*8*9", "*#", "Both literal characters")

    def test_trailing_asterisk(self):
        """Test: 123* should keep trailing asterisk"""
        self._assert_translation("123*", "123*", "Trailing asterisk")

    def test_empty_string(self):
        """Test: Empty string should remain empty"""
        self._assert_translation("", "", "Empty string")

    def test_complex_account_code(self):
        """Test: *312*445 should translate to C12D45"""
        self._assert_translation("*312*445", "C12D45", "Complex account code")

    def test_leading_digits(self):
        """Test: 555*1*2 should translate to 555AB"""
        self._assert_translation("555*1*2", "555AB", "Leading digits")

    def test_interleaved(self):
        """Test: *11*22*3 should translate to A1B2C"""
        self._assert_translation("*11*22*3", "A1B2C", "Interleaved")

    def test_consecutive_escapes(self):
        """Test: *1*2*3*4*5*6*8*9 should translate to ABCDEF*#"""
        self._assert_translation("*1*2*3*4*5*6*8*9", "ABCDEF*#", "All escapes")

    def test_unknown_escape_sequence(self):
        """Test: *7 should pass through as *7 (unknown escape)"""
        self._assert_translation("*7", "*7", "Unknown escape sequence")

    def test_realistic_phone_with_pause(self):
        """Test: 9725551234*8*8 should translate to 9725551234** (pause codes)"""
        self._assert_translation("9725551234*8*8", "9725551234**", "Phone with pauses")

    def test_account_code_example_1(self):
        """Test: *312345 should translate to C12345"""
        self._assert_translation("*312345", "C12345", "Account code C12345")

    def test_account_code_example_2(self):
        """Test: *11*2*3456 should translate to AB3456"""
        self._assert_translation("*11*2*3456", "AB3456", "Account code AB3456")


def main():
    """Main entry point for running tests."""
    # Check if target is reachable
    try:
        result = subprocess.run(
            ["ssh", DTMFTranslationTest.TARGET_HOST, "echo OK"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0 or "OK" not in result.stdout:
            print(f"ERROR: Cannot connect to {DTMFTranslationTest.TARGET_HOST}")
            print("Please ensure SSH access is configured and target is running.")
            sys.exit(1)
    except subprocess.TimeoutExpired:
        print(f"ERROR: Connection timeout to {DTMFTranslationTest.TARGET_HOST}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Run tests
    unittest.main(argv=sys.argv[:1], verbosity=2)


if __name__ == "__main__":
    main()
