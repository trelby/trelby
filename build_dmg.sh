#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Trelby"
VERSION="${1:-2.4.16.2}"
DIST_DIR="dist"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"

echo "Building ${APP_NAME} macOS DMG..."

# Ensure clean build
echo " Cleaning old builds..."
rm -rf build "${DIST_DIR}"

# Build app bundle
make dist
echo "Building .app with py2app..."
python3 setup.py py2app

APP_PATH="${DIST_DIR}/${APP_NAME}.app"

if [ ! -d "${APP_PATH}" ]; then
  echo " ERROR: ${APP_NAME}.app not found!"
  exit 1
fi

# Prepare DMG staging
echo "Preparing DMG staging..."
STAGING="${DIST_DIR}/dmg"
mkdir -p "${STAGING}"

ditto "${APP_PATH}" "${STAGING}/${APP_NAME}.app"
ln -sf /Applications "${STAGING}/Applications"

# Build DMG
echo "Creating DMG..."
hdiutil create \
  -volname "${APP_NAME}" \
  -srcfolder "${STAGING}" \
  -ov \
  -format UDZO \
  -imagekey zlib-level=9 \
  "${DIST_DIR}/${DMG_NAME}"

# Cleanup
rm -rf "${STAGING}"

# Verify
echo "Verifying DMG..."
hdiutil verify "${DIST_DIR}/${DMG_NAME}"

echo "DMG created successfully:"
echo "➡️  ${DIST_DIR}/${DMG_NAME}"

echo ""
echo "Install instructions:"
echo "1. Open the DMG"
echo "2. Drag ${APP_NAME}.app to Applications"
echo "3. Eject the DMG"
echo "4. Launch ${APP_NAME} from Applications"