#!/bin/bash
# Generate version from git tags or commit info

if [ -d ".git" ]; then
    # Try to get latest tag
    VERSION=$(git describe --tags --always --dirty 2>/dev/null)

    # If no tags exist, use branch and short commit
    if [ -z "$VERSION" ]; then
        BRANCH=$(git rev-parse --abbrev-ref HEAD)
        COMMIT=$(git rev-parse --short HEAD)
        VERSION="${BRANCH}-${COMMIT}"
    fi

    BUILD_DATE=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
    BUILD_USER=$(whoami)
    GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
else
    VERSION="unknown"
    BUILD_DATE="unknown"
    BUILD_USER="unknown"
    GIT_COMMIT="unknown"
    GIT_BRANCH="unknown"
fi

# Create version info file
cat > VERSION_INFO << EOF
VERSION=$VERSION
BUILD_DATE=$BUILD_DATE
BUILD_USER=$BUILD_USER
GIT_COMMIT=$GIT_COMMIT
GIT_BRANCH=$GIT_BRANCH
EOF

echo "Generated version: $VERSION"
cat VERSION_INFO
