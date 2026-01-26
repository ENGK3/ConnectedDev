"""
Unit tests for modem_utils module, specifically testing the manage_sim function's
retry behavior with different PIN values.
"""

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
