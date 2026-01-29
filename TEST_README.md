# Testing Guide

This document describes the tests available in the K3-Qseries-POC project and how to run them.

## Prerequisites

### Python Environment

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package management and virtual environment handling.

#### Install uv

If you don't have uv installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or using pip:

```bash
pip install uv
```

### Python Modules

To run the Python unit tests, you need the following modules installed:

- **pytest** - Testing framework for Python unit tests
- **pyserial** - Serial port library required by the modem utilities being tested
- **python-dotenv** - For loading environment variables (used by tested modules)
- **aiohttp** - Async HTTP client/server framework (used by ARI monitor)

### Development Dependencies

Create a virtual environment and install all testing dependencies:

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Linux/macOS
# or
.venv\Scripts\activate     # On Windows

# Install dependencies
uv pip install -r requirements.dev.txt
```

### System Requirements

For the integration tests (shell scripts):
- SSH access to the target device
- Bash shell
- Target system must have:
  - Asterisk PBX running
  - baresip VoIP client installed
  - Configured conference extension (9877)
  - Admin extensions (200 or 201)

## Available Tests

| Test Name | Type | Description |
|-----------|------|-------------|
| `test_dial_code_utils.py` | Python/pytest | Unit tests for `parse_special_dial_code()` function that parses special dial code prefixes (*50, *54, *55) |
| `test_edc_dial_codes.py` | Python/pytest | Integration tests verifying special dial code prefix stripping and call placement behavior in `manage_modem` |
| `test_manage_modem.py` | Python/pytest | Integration tests for modem state machine, TCP server, call placement, incoming calls with ring count/answer count logic, using fake serial modem |
| `test_modem_utils.py` | Python/pytest | Unit tests for SIM management (`manage_sim()`) with PIN retry logic and MSISDN extraction (`get_msisdn()`) from SIM cards |
| `test_msisdn_cid_update.py` | Python/pytest | Unit tests for automatic CID update logic that synchronizes config file with MSISDN from SIM card |
| `test_dtmf_translate.py` | Python/unittest | Integration tests for Asterisk DTMF escape sequence translation (*1→A, *2→B, etc.). Requires SSH access to target device |
| `test_edit_phone_numbers.sh` | Bash/Integration | Integration test for DTMF phone number editing features (01#, 02#, 03#). Requires SSH access to target device |

## Running the Tests

### Python Unit Tests

Ensure your virtual environment is activated first:

```bash
source .venv/bin/activate
```

Run all Python unit tests:

```bash
pytest tests/
```

Run a specific test file with verbose output:

```bash
pytest tests/test_modem_utils.py -v
```

Run a specific test case:

```bash
pytest tests/test_modem_utils.py::TestManageSim::test_manage_sim_ready_not_locked_first_pin_success -v
```

Run the manage_modem integration tests:

```bash
pytest tests/test_manage_modem.py -v
```

Run the DTMF translation tests (requires SSH to target):

```bash
python3 tests/test_dtmf_translate.py
# or
pytest tests/test_dtmf_translate.py -v
# Set custom target:
TARGET_HOST=root@192.168.80.10 python3 tests/test_dtmf_translate.py
```

### Shell Integration Tests

Run the phone number editing integration test:

```bash
./tests/test_edit_phone_numbers.sh [TARGET_HOST]
```

Example:
```bash
./tests/test_edit_phone_numbers.sh root@192.168.80.10
```

Default target (if not specified): `root@GWorks2`


## Operational Test Table

The following is a table showing which tests currently run, if they run locally or on the remote system.

|Status|Rem:Loc|Name|
|----|-----|--------|
|P|L|tests/test_dial_code_utils.py|
|X|R|tests/test_dtmf_translate.py|
|P|L|tests/test_edc_dial_codes.py|
|F|R|tests/test_edit_phone_numbers.sh|
|P|L|tests/test_manage_modem.py|
|P|L|tests/test_modem_utils.py|
|P|L|tests/test_msisdn_cid_update.py|
|F|R|tests/test_restore_factory_defaults.py|
|F|R|tests/test_restore_factory_defaults.sh|

|KEY | Meaning |
|----|---------|
|P | Pass|
|W | Warnings.|
|F | Failure|
|X | NOT READY - Incomplete |
|L | Local|
|R | Remote|

## Test Descriptions

### tests/test_dial_code_utils.py
Tests the `parse_special_dial_code()` utility function that parses special dial code prefixes (*50, *54, *55) and returns the actual number to dial along with EDC control flags.

### tests/test_edc_dial_codes.py
Integration tests verifying that `manage_modem` correctly strips special dial code prefixes (*50, *54, *55) before sending ATD commands to the modem. Tests both the parsing logic and actual call placement behavior.

### tests/test_manage_modem.py
Integration tests for the modem manager's state machine and TCP server, including call placement, incoming call handling with ring count/answer count logic, state transitions, and command/response protocol using a fake serial modem.

### tests/test_modem_utils.py
Unit tests for modem utility functions including SIM management (`manage_sim()`) with PIN retry logic, and MSISDN extraction (`get_msisdn()`) from SIM cards with various AT+CNUM response formats.

### tests/test_msisdn_cid_update.py
Tests the automatic CID (Caller ID) update logic in `manage_modem` that synchronizes the config file's CID field with the MSISDN retrieved from the SIM card, handling SIM swaps and missing values.

## Continuous Integration

**Note:** Only Python unit tests should run in standard CI/CD pipelines. Shell integration tests (e.g., `test_edit_phone_numbers.sh`) require SSH access to the target hardware and should only be run on external/self-hosted runners with network access to the target devices.

To run tests in a CI/CD pipeline:

```bash
# Install uv (if not already available)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.dev.txt

# Run Python unit tests only (integration tests excluded)
pytest tests/ -k "not integration" --verbose --tb=short

# Or run specific test files
pytest tests/test_modem_utils.py --verbose --tb=short

# Run linting (if configured)
ruff check .
```

## Writing New Tests

### Python Unit Tests

1. Create test files in the `tests/` directory with the prefix `test_`
2. Use pytest fixtures and parametrization for test organization
3. Mock external dependencies (serial connections, file I/O, etc.)
4. Follow the existing naming convention: `test_<module_name>.py`

### Shell Integration Tests

1. Create test scripts in the `tests/` directory with the prefix `test_`
2. Make scripts executable: `chmod +x tests/test_*.sh`
3. Include usage instructions and prerequisites in script comments
4. Use proper exit codes (0 for success, non-zero for failure)
5. Provide clear logging with color-coded output

## Troubleshooting

### Common Issues

**Import errors when running tests:**
- Ensure you're in the project root directory
- Verify virtual environment is activated: `source .venv/bin/activate`
- Install all dependencies: `uv pip install -r requirements.dev.txt`

**SSH connection failures in integration tests:**
- Verify SSH access to the target device
- Check SSH key configuration or password authentication
- Ensure the target hostname/IP is correct

**Asterisk configuration tests fail:**
- Verify Asterisk is running on the target device
- Check that configuration files exist in `/etc/asterisk/`
- Ensure the target has the latest configuration deployed
