"""
Unit tests for modem_utils module, specifically testing the manage_sim function's
retry behavior with different PIN values.
"""

import sys
from pathlib import Path

# Add parent directory to path to import modem_utils
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import Mock, patch, call
import serial

import modem_utils


class TestManageSim:
    """Test suite for the manage_sim function."""

    @pytest.fixture
    def mock_serial(self):
        """Create a mock serial connection."""
        mock = Mock(spec=serial.Serial)
        return mock

    def test_manage_sim_ready_not_locked_first_pin_success(self, mock_serial):
        """
        Test manage_sim when SIM is READY, not locked, and first PIN attempt (1111) succeeds.
        Should NOT retry with alternate PIN.
        """
        with patch('modem_utils.check_sim_pin_status') as mock_pin_status, \
             patch('modem_utils.check_sim_lock_status') as mock_lock_status, \
             patch('modem_utils.set_sim_password_and_lock') as mock_set_pw:

            # Configure mocks
            mock_pin_status.return_value = "READY"
            mock_lock_status.return_value = (True, "0")  # Not locked
            mock_set_pw.return_value = True  # First attempt succeeds

            # Execute
            result = modem_utils.manage_sim(mock_serial, "test_pw", verbose=False)

            # Assertions
            assert result is True
            mock_pin_status.assert_called_once_with(mock_serial, verbose=False)
            mock_lock_status.assert_called_once_with(mock_serial, verbose=False)

            # Should only call set_sim_password_and_lock once with default PIN "1111"
            mock_set_pw.assert_called_once_with(
                mock_serial, "1111", "test_pw", verbose=False
            )

    def test_manage_sim_ready_not_locked_first_pin_fails_second_succeeds(self, mock_serial):
        """
        Test manage_sim when SIM is READY, not locked, first PIN (1111) fails,
        but second PIN (1234) succeeds.
        """
        with patch('modem_utils.check_sim_pin_status') as mock_pin_status, \
             patch('modem_utils.check_sim_lock_status') as mock_lock_status, \
             patch('modem_utils.set_sim_password_and_lock') as mock_set_pw:

            # Configure mocks
            mock_pin_status.return_value = "READY"
            mock_lock_status.return_value = (True, "0")  # Not locked
            mock_set_pw.side_effect = [False, True]  # First fails, second succeeds

            # Execute
            result = modem_utils.manage_sim(mock_serial, "test_pw", verbose=False)

            # Assertions
            assert result is True
            mock_pin_status.assert_called_once_with(mock_serial, verbose=False)
            mock_lock_status.assert_called_once_with(mock_serial, verbose=False)

            # Should call set_sim_password_and_lock twice
            assert mock_set_pw.call_count == 2
            expected_calls = [
                call(mock_serial, "1111", "test_pw", verbose=False),
                call(mock_serial, "1234", "test_pw", verbose=False),
            ]
            mock_set_pw.assert_has_calls(expected_calls)

    def test_manage_sim_ready_not_locked_both_pins_fail(self, mock_serial):
        """
        Test manage_sim when SIM is READY, not locked, and both PIN attempts fail.
        """
        with patch('modem_utils.check_sim_pin_status') as mock_pin_status, \
             patch('modem_utils.check_sim_lock_status') as mock_lock_status, \
             patch('modem_utils.set_sim_password_and_lock') as mock_set_pw:

            # Configure mocks
            mock_pin_status.return_value = "READY"
            mock_lock_status.return_value = (True, "0")  # Not locked
            mock_set_pw.return_value = False  # Both attempts fail

            # Execute
            result = modem_utils.manage_sim(mock_serial, "test_pw", verbose=False)

            # Assertions
            assert result is False
            mock_pin_status.assert_called_once_with(mock_serial, verbose=False)
            mock_lock_status.assert_called_once_with(mock_serial, verbose=False)

            # Should call set_sim_password_and_lock twice (1111, then 1234)
            assert mock_set_pw.call_count == 2
            expected_calls = [
                call(mock_serial, "1111", "test_pw", verbose=False),
                call(mock_serial, "1234", "test_pw", verbose=False),
            ]
            mock_set_pw.assert_has_calls(expected_calls)

    def test_manage_sim_ready_already_locked(self, mock_serial):
        """
        Test manage_sim when SIM is READY and already locked.
        Should NOT attempt to set password.
        """
        with patch('modem_utils.check_sim_pin_status') as mock_pin_status, \
             patch('modem_utils.check_sim_lock_status') as mock_lock_status, \
             patch('modem_utils.set_sim_password_and_lock') as mock_set_pw:

            # Configure mocks
            mock_pin_status.return_value = "READY"
            mock_lock_status.return_value = (True, "1")  # Already locked

            # Execute
            result = modem_utils.manage_sim(mock_serial, "test_pw", verbose=False)

            # Assertions
            assert result is True
            mock_pin_status.assert_called_once_with(mock_serial, verbose=False)
            mock_lock_status.assert_called_once_with(mock_serial, verbose=False)

            # Should NOT call set_sim_password_and_lock
            mock_set_pw.assert_not_called()

    def test_manage_sim_requires_pin_unlock_success(self, mock_serial):
        """
        Test manage_sim when SIM requires PIN and unlock succeeds.
        """
        with patch('modem_utils.check_sim_pin_status') as mock_pin_status, \
             patch('modem_utils.unlock_sim_with_pin') as mock_unlock:

            # Configure mocks
            mock_pin_status.return_value = "SIM PIN"
            mock_unlock.return_value = True

            # Execute
            result = modem_utils.manage_sim(mock_serial, "test_pw", verbose=False)

            # Assertions
            assert result is True
            mock_pin_status.assert_called_once_with(mock_serial, verbose=False)
            mock_unlock.assert_called_once_with(mock_serial, "test_pw", verbose=False)

    def test_manage_sim_requires_pin_unlock_fails(self, mock_serial):
        """
        Test manage_sim when SIM requires PIN and unlock fails.
        """
        with patch('modem_utils.check_sim_pin_status') as mock_pin_status, \
             patch('modem_utils.unlock_sim_with_pin') as mock_unlock:

            # Configure mocks
            mock_pin_status.return_value = "SIM PIN"
            mock_unlock.return_value = False

            # Execute
            result = modem_utils.manage_sim(mock_serial, "test_pw", verbose=False)

            # Assertions
            assert result is False
            mock_pin_status.assert_called_once_with(mock_serial, verbose=False)
            mock_unlock.assert_called_once_with(mock_serial, "test_pw", verbose=False)

    def test_manage_sim_unexpected_state(self, mock_serial):
        """
        Test manage_sim when SIM is in an unexpected state (e.g., PUK required).
        """
        with patch('modem_utils.check_sim_pin_status') as mock_pin_status:

            # Configure mocks
            mock_pin_status.return_value = "SIM PUK"

            # Execute
            result = modem_utils.manage_sim(mock_serial, "test_pw", verbose=False)

            # Assertions
            assert result is False
            mock_pin_status.assert_called_once_with(mock_serial, verbose=False)

    def test_manage_sim_lock_status_check_fails(self, mock_serial):
        """
        Test manage_sim when checking lock status fails.
        """
        with patch('modem_utils.check_sim_pin_status') as mock_pin_status, \
             patch('modem_utils.check_sim_lock_status') as mock_lock_status:

            # Configure mocks
            mock_pin_status.return_value = "READY"
            mock_lock_status.return_value = (False, None)  # Failed to check

            # Execute
            result = modem_utils.manage_sim(mock_serial, "test_pw", verbose=False)

            # Assertions
            assert result is False
            mock_pin_status.assert_called_once_with(mock_serial, verbose=False)
            mock_lock_status.assert_called_once_with(mock_serial, verbose=False)

    def test_manage_sim_exception_handling(self, mock_serial):
        """
        Test manage_sim exception handling when an unexpected error occurs.
        """
        with patch('modem_utils.check_sim_pin_status') as mock_pin_status:

            # Configure mocks to raise exception
            mock_pin_status.side_effect = Exception("Unexpected error")

            # Execute
            result = modem_utils.manage_sim(mock_serial, "test_pw", verbose=False)

            # Assertions
            assert result is False


class TestGetMsisdn:
    """Test suite for the get_msisdn function."""

    @pytest.fixture
    def mock_serial(self):
        """Create a mock serial connection."""
        mock = Mock(spec=serial.Serial)
        return mock

    def test_get_msisdn_success_simple_format(self, mock_serial):
        """
        Test get_msisdn with successful response in simple format.
        Response: +CNUM: "","15551234567",129
        """
        with patch('modem_utils.sbc_cmd_with_timeout') as mock_cmd:
            # Configure mock - simple format without name
            mock_cmd.return_value = '+CNUM: "","15551234567",129'

            # Execute
            success, msisdn = modem_utils.get_msisdn(mock_serial, verbose=False)

            # Assertions
            assert success is True
            assert msisdn == "15551234567"
            mock_cmd.assert_called_once_with(
                "AT+CNUM\r", mock_serial, verbose=False
            )

    def test_get_msisdn_success_with_name(self, mock_serial):
        """
        Test get_msisdn with successful response including subscriber name.
        Response: +CNUM: "Voice Line 1","+15551234567",145
        """
        with patch('modem_utils.sbc_cmd_with_timeout') as mock_cmd:
            # Configure mock - format with name and + prefix
            mock_cmd.return_value = '+CNUM: "Voice Line 1","+15551234567",145'

            # Execute
            success, msisdn = modem_utils.get_msisdn(mock_serial, verbose=False)

            # Assertions
            assert success is True
            assert msisdn == "+15551234567"
            mock_cmd.assert_called_once_with(
                "AT+CNUM\r", mock_serial, verbose=False
            )

    def test_get_msisdn_success_international_format(self, mock_serial):
        """
        Test get_msisdn with international format phone number.
        Response: +CNUM: "My Phone","+441234567890",145
        """
        with patch('modem_utils.sbc_cmd_with_timeout') as mock_cmd:
            # Configure mock - international format
            mock_cmd.return_value = '+CNUM: "My Phone","+441234567890",145'

            # Execute
            success, msisdn = modem_utils.get_msisdn(mock_serial, verbose=False)

            # Assertions
            assert success is True
            assert msisdn == "+441234567890"

    def test_get_msisdn_no_number_stored_ok_response(self, mock_serial):
        """
        Test get_msisdn when SIM has no MSISDN stored (OK response only).
        This happens when the SIM doesn't have a phone number programmed.
        """
        with patch('modem_utils.sbc_cmd_with_timeout') as mock_cmd:
            # Configure mock - command succeeds but no number
            mock_cmd.return_value = 'OK'

            # Execute
            success, msisdn = modem_utils.get_msisdn(mock_serial, verbose=False)

            # Assertions
            assert success is False
            assert msisdn is None
            mock_cmd.assert_called_once_with(
                "AT+CNUM\r", mock_serial, verbose=False
            )

    def test_get_msisdn_empty_number_field(self, mock_serial):
        """
        Test get_msisdn when response has empty number field.
        Response: +CNUM: "","",129
        """
        with patch('modem_utils.sbc_cmd_with_timeout') as mock_cmd:
            # Configure mock - empty number field
            mock_cmd.return_value = '+CNUM: "","",129'

            # Execute
            success, msisdn = modem_utils.get_msisdn(mock_serial, verbose=False)

            # Assertions
            assert success is False
            assert msisdn is None

    def test_get_msisdn_error_response(self, mock_serial):
        """
        Test get_msisdn when modem returns ERROR.
        """
        with patch('modem_utils.sbc_cmd_with_timeout') as mock_cmd:
            # Configure mock - ERROR response
            mock_cmd.return_value = 'ERROR'

            # Execute
            success, msisdn = modem_utils.get_msisdn(mock_serial, verbose=False)

            # Assertions
            assert success is False
            assert msisdn is None

    def test_get_msisdn_cme_error_response(self, mock_serial):
        """
        Test get_msisdn when modem returns CME ERROR.
        """
        with patch('modem_utils.sbc_cmd_with_timeout') as mock_cmd:
            # Configure mock - CME ERROR response
            mock_cmd.return_value = '+CME ERROR: 10'

            # Execute
            success, msisdn = modem_utils.get_msisdn(mock_serial, verbose=False)

            # Assertions
            assert success is False
            assert msisdn is None

    def test_get_msisdn_malformed_response(self, mock_serial):
        """
        Test get_msisdn with malformed response (unexpected format).
        """
        with patch('modem_utils.sbc_cmd_with_timeout') as mock_cmd:
            # Configure mock - malformed response
            mock_cmd.return_value = '+CNUM: malformed'

            # Execute
            success, msisdn = modem_utils.get_msisdn(mock_serial, verbose=False)

            # Assertions
            assert success is False
            assert msisdn is None

    def test_get_msisdn_exception_handling(self, mock_serial):
        """
        Test get_msisdn exception handling when an unexpected error occurs.
        """
        with patch('modem_utils.sbc_cmd_with_timeout') as mock_cmd:
            # Configure mock to raise exception
            mock_cmd.side_effect = Exception("Serial communication error")

            # Execute
            success, msisdn = modem_utils.get_msisdn(mock_serial, verbose=False)

            # Assertions
            assert success is False
            assert msisdn is None

    def test_get_msisdn_multiline_response(self, mock_serial):
        """
        Test get_msisdn with multiline response (some modems return multiple lines).
        Should extract the first valid MSISDN found.
        """
        with patch('modem_utils.sbc_cmd_with_timeout') as mock_cmd:
            # Configure mock - multiline response
            mock_cmd.return_value = 'AT+CNUM\n+CNUM: "","15551234567",129\nOK'

            # Execute
            success, msisdn = modem_utils.get_msisdn(mock_serial, verbose=False)

            # Assertions
            assert success is True
            assert msisdn == "15551234567"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
