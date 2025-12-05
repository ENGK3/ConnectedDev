#!/bin/bash
# Display version information

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
VERSION=$(cat "${SCRIPT_DIR}/VERSION" 2>/dev/null || echo "unknown")

echo "========================================"
echo "  King3 Build Package"
echo "========================================"
echo "Version: ${VERSION}"
echo ""

if [ -f "${SCRIPT_DIR}/VERSION_INFO" ]; then
    echo "Build Information:"
    cat "${SCRIPT_DIR}/VERSION_INFO"
else
    echo "No build information available"
    echo "(Run generate_version.sh to create)"
fi

echo "========================================"
