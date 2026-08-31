#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

APP_PATH="dist/TranscriptSanitizer.app"
PKG_ROOT="packaging/pkgroot"
COMPONENT_PKG="dist/TranscriptSanitizer-component.pkg"
FINAL_PKG="dist/TranscriptSanitizer-macOS.pkg"

if [ ! -d "$APP_PATH" ]; then
  packaging/build_mac_app.sh
fi

rm -rf "$PKG_ROOT" "$COMPONENT_PKG" "$FINAL_PKG"
mkdir -p "$PKG_ROOT/Applications"
cp -R "$APP_PATH" "$PKG_ROOT/Applications/"

pkgbuild \
  --root "$PKG_ROOT" \
  --identifier "com.transcriptsanitizer.app" \
  --version "${APP_VERSION:-1.0.0}" \
  --install-location "/" \
  "$COMPONENT_PKG"

if [ -n "${MACOS_INSTALLER_IDENTITY:-}" ]; then
  productbuild \
    --sign "$MACOS_INSTALLER_IDENTITY" \
    --package "$COMPONENT_PKG" \
    "$FINAL_PKG"
else
  productbuild \
    --package "$COMPONENT_PKG" \
    "$FINAL_PKG"
fi

echo "Built macOS installer at $FINAL_PKG"
