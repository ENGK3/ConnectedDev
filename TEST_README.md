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
| `test_modem_utils.py::TestManageSim` | Python/pytest | Unit tests for the `modem_utils.manage_sim()` function, testing retry behavior with different PIN values and SIM states |
| `test_modem_utils.py::TestGetMsisdn` | Python/pytest | Unit tests for the `modem_utils.get_msisdn()` function, testing MSISDN (phone number) extraction from SIM using AT+CNUM command with various response formats and error conditions |
| `test_edit_phone_numbers.sh` | Bash/Integration | Integration test for DTMF phone number editing features (01#, 02#, 03#). Tests the edit_config.sh script, Asterisk configuration, validation logic, and backup functionality |

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

## Test Coverage

### test_modem_utils.py::TestManageSim

Tests the following scenarios for the `manage_sim()` function:
- SIM READY state with unlocked SIM and successful PIN setup (first attempt)
- SIM READY state with PIN retry logic (1111 fails, 1234 succeeds)
- SIM READY state with both PINs failing
- SIM already locked (no action needed)
- SIM requiring PIN unlock (success and failure cases)
- Unexpected SIM states (e.g., PUK required)
- Lock status check failures
- Exception handling

### test_modem_utils.py::TestGetMsisdn

Tests the following scenarios for the `get_msisdn()` function:
- Successful MSISDN extraction with simple format (e.g., `+CNUM: "","15551234567",129`)
- Successful MSISDN extraction with subscriber name (e.g., `+CNUM: "Voice Line 1","+15551234567",145`)
- International phone number format (e.g., `+441234567890`)
- No MSISDN stored on SIM (OK response only)
- Empty number field in response
- ERROR response handling
- CME ERROR response handling
- Malformed response parsing
- Exception handling for serial communication errors
- Multiline response parsing

### test_edit_phone_numbers.sh

Tests the following features:
- SSH connectivity to target device
- Reading current phone number values from config
- Asterisk configuration validation (confbridge.conf and extensions.conf)
- Phone number editing for FIRST_NUMBER, SECOND_NUMBER, and THIRD_NUMBER
- Input validation (non-numeric, too long, empty, invalid variable names)
- Backup file creation
- Restoration of original values

The test also provides manual testing instructions for interactive DTMF testing using baresip.

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
