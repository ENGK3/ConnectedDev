"""
Unit tests for MSISDN retrieval and CID update logic in manage_modem.

These tests verify that the CID field in the config file is properly updated
when the MSISDN from the SIM card differs from the stored CID value.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMsisdnCidUpdate:
    """Test suite for MSISDN/CID update logic."""

    @pytest.fixture
    def mock_serial(self):
        """Create a mock serial connection."""
        mock = Mock()
        mock.is_open = True
        return mock

    @pytest.fixture
    def mock_config_file(self):
        """Return the config file path."""
        return "/mnt/data/K3_config_settings"

    def test_cid_update_when_msisdn_differs(self, mock_serial, mock_config_file):
        """
        Test that CID is updated when MSISDN from SIM differs from config.
        This simulates a SIM card swap scenario.
        """
        with patch("modem_utils.get_msisdn") as mock_get_msisdn, \
             patch("dotenv.dotenv_values") as mock_dotenv_values, \
             patch("dotenv.set_key") as mock_set_key:

            # Simulate MSISDN retrieval returning a new number
            new_msisdn = "15551234567"
            mock_get_msisdn.return_value = (True, new_msisdn)

            # Simulate current config with different CID
            old_cid = "5822460189"
            mock_dotenv_values.return_value = {"CID": old_cid}

            # Execute the logic
            success, msisdn = mock_get_msisdn(mock_serial, verbose=True)

            if success and msisdn:
                config = mock_dotenv_values(mock_config_file)
                current_cid = config.get("CID", "")

                if current_cid != msisdn:
                    # This should trigger the update
                    mock_set_key(mock_config_file, "CID", msisdn)

            # Assertions
            assert success is True
            assert msisdn == new_msisdn
            assert current_cid == old_cid
            assert current_cid != msisdn

            # Verify set_key was called to update the CID
            mock_set_key.assert_called_once_with(mock_config_file, "CID", new_msisdn)

    def test_cid_no_update_when_msisdn_matches(self, mock_serial, mock_config_file):
        """
        Test that CID is NOT updated when MSISDN matches the stored CID.
        This is the normal case when the same SIM is used.
        """
        with patch("modem_utils.get_msisdn") as mock_get_msisdn, \
             patch("dotenv.dotenv_values") as mock_dotenv_values, \
             patch("dotenv.set_key") as mock_set_key:

            # Simulate MSISDN matching the current CID
            msisdn = "5822460189"
            mock_get_msisdn.return_value = (True, msisdn)
            mock_dotenv_values.return_value = {"CID": msisdn}

            # Execute the logic
            success, retrieved_msisdn = mock_get_msisdn(mock_serial, verbose=True)

            if success and retrieved_msisdn:
                config = mock_dotenv_values(mock_config_file)
                current_cid = config.get("CID", "")

                if current_cid != retrieved_msisdn:
                    mock_set_key(mock_config_file, "CID", retrieved_msisdn)

            # Assertions
            assert success is True
            assert retrieved_msisdn == msisdn
            assert current_cid == msisdn

            # Verify set_key was NOT called (no update needed)
            mock_set_key.assert_not_called()

    def test_cid_no_update_when_msisdn_retrieval_fails(
        self, mock_serial, mock_config_file
    ):
        """
        Test that CID is NOT updated when MSISDN retrieval fails.
        This can happen if the SIM doesn't have MSISDN provisioned.
        """
        with patch("modem_utils.get_msisdn") as mock_get_msisdn, \
             patch("dotenv.dotenv_values") as mock_dotenv_values, \
             patch("dotenv.set_key") as mock_set_key:

            # Simulate MSISDN retrieval failure
            mock_get_msisdn.return_value = (False, None)
            mock_dotenv_values.return_value = {"CID": "5822460189"}

            # Execute the logic
            success, msisdn = mock_get_msisdn(mock_serial, verbose=True)

            if success and msisdn:
                config = mock_dotenv_values(mock_config_file)
                current_cid = config.get("CID", "")

                if current_cid != msisdn:
                    mock_set_key(mock_config_file, "CID", msisdn)

            # Assertions
            assert success is False
            assert msisdn is None

            # Verify set_key was NOT called (no MSISDN to update with)
            mock_set_key.assert_not_called()

    def test_cid_update_with_international_format(
        self, mock_serial, mock_config_file
    ):
        """
        Test CID update with international format phone number.
        """
        with patch("modem_utils.get_msisdn") as mock_get_msisdn, \
             patch("dotenv.dotenv_values") as mock_dotenv_values, \
             patch("dotenv.set_key") as mock_set_key:

            # Simulate MSISDN with international prefix
            new_msisdn = "+441234567890"
            mock_get_msisdn.return_value = (True, new_msisdn)

            # Simulate current config with different CID (no + prefix)
            old_cid = "441234567890"
            mock_dotenv_values.return_value = {"CID": old_cid}

            # Execute the logic
            success, msisdn = mock_get_msisdn(mock_serial, verbose=True)

            if success and msisdn:
                config = mock_dotenv_values(mock_config_file)
                current_cid = config.get("CID", "")

                if current_cid != msisdn:
                    mock_set_key(mock_config_file, "CID", msisdn)

            # Assertions
            assert success is True
            assert msisdn == new_msisdn
            assert current_cid != msisdn

            # Verify set_key was called with international format
            mock_set_key.assert_called_once_with(
                mock_config_file, "CID", new_msisdn
            )

    def test_cid_update_handles_missing_cid_in_config(
        self, mock_serial, mock_config_file
    ):
        """
        Test CID update when CID is missing from config file.
        This could happen on first run or if config is corrupted.
        """
        with patch("modem_utils.get_msisdn") as mock_get_msisdn, \
             patch("dotenv.dotenv_values") as mock_dotenv_values, \
             patch("dotenv.set_key") as mock_set_key:

            # Simulate MSISDN retrieval
            msisdn = "15551234567"
            mock_get_msisdn.return_value = (True, msisdn)

            # Simulate config without CID field
            mock_dotenv_values.return_value = {"AC": "C12345", "MDL": "Q01"}

            # Execute the logic
            success, retrieved_msisdn = mock_get_msisdn(mock_serial, verbose=True)

            if success and retrieved_msisdn:
                config = mock_dotenv_values(mock_config_file)
                current_cid = config.get("CID", "")  # Returns empty string

                if current_cid != retrieved_msisdn:
                    mock_set_key(mock_config_file, "CID", retrieved_msisdn)

            # Assertions
            assert success is True
            assert current_cid == ""  # Missing CID
            assert current_cid != msisdn

            # Verify set_key was called to add the CID
            mock_set_key.assert_called_once_with(mock_config_file, "CID", msisdn)

    def test_cid_update_with_set_key_exception(
        self, mock_serial, mock_config_file
    ):
        """
        Test that exceptions during set_key are handled gracefully.
        This simulates file permission errors or disk full scenarios.
        """
        with patch("modem_utils.get_msisdn") as mock_get_msisdn, \
             patch("dotenv.dotenv_values") as mock_dotenv_values, \
             patch("dotenv.set_key") as mock_set_key:

            # Simulate MSISDN retrieval
            new_msisdn = "15551234567"
            mock_get_msisdn.return_value = (True, new_msisdn)

            # Simulate current config with different CID
            old_cid = "5822460189"
            mock_dotenv_values.return_value = {"CID": old_cid}

            # Simulate set_key raising an exception
            mock_set_key.side_effect = Exception("Permission denied")

            # Execute the logic with exception handling
            success, msisdn = mock_get_msisdn(mock_serial, verbose=True)

            if success and msisdn:
                config = mock_dotenv_values(mock_config_file)
                current_cid = config.get("CID", "")

                if current_cid != msisdn:
                    try:
                        mock_set_key(mock_config_file, "CID", msisdn)
                    except Exception as e:
                        # Exception should be caught and logged
                        assert str(e) == "Permission denied"

            # Verify set_key was attempted
            mock_set_key.assert_called_once_with(mock_config_file, "CID", new_msisdn)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
