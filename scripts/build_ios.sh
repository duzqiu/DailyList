#!/usr/bin/env bash
#
# 一键生成签名好的 iOS .ipa（免费 Personal Team 可用）。
#
# 用法：
#   scripts/build_ios.sh              # 正常出包
#   scripts/build_ios.sh --clean      # 先清构建缓存，再出包（遇到“启动即退”时用）
#
# 请在你自己登录的桌面终端里运行（签名需要访问钥匙串），不要加 sudo。
# 想要别的输出位置/团队，可以用环境变量覆盖：
#   TEAM_ID=XXXX  ARCHIVE=/tmp/x.xcarchive  EXPORT_DIR=/tmp/x  scripts/build_ios.sh
#
set -euo pipefail

TEAM_ID="${TEAM_ID:-346PNWC777}"
# 免费 Personal Team 只能用 debugging（旧版 Xcode 叫 Development）
EXPORT_METHOD="${EXPORT_METHOD:-debugging}"
APP_NAME="${APP_NAME:-dailylist}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
IOS_DIR="$BUILD_DIR/flutter/ios"
# 注意：`flet build` 每次都会清空 build/ipa，所以产物放在 build/ios-build 下
BUILD_OUT="$BUILD_DIR/ios-build"
ARCHIVE="${ARCHIVE:-$BUILD_OUT/$APP_NAME-signed.xcarchive}"
EXPORT_DIR="${EXPORT_DIR:-$BUILD_OUT/export}"
LOG="$BUILD_OUT/build.log"

# CocoaPods 在非 UTF-8 locale 下会以 Encoding::CompatibilityError 失败
export LANG="${LANG_OVERRIDE:-en_US.UTF-8}"
export LC_ALL="${LC_ALL_OVERRIDE:-en_US.UTF-8}"

SP_DIST="${PUB_CACHE:-$HOME/.pub-cache}/hosted/pub.dev/serious_python_darwin-4.7.1/darwin/dist_ios"

if [[ "${1:-}" == "--clean" ]]; then
  echo "== 清理构建缓存（可自动重建）=="
  rm -rf "$BUILD_DIR/.hash" "$BUILD_DIR/site-packages" \
         "$BUILD_DIR/.serious_python_spm_key" "$SP_DIST"
fi

mkdir -p "$(dirname "$ARCHIVE")" "$(dirname "$LOG")"

echo "== 1/3 打包 Python 应用与 iOS 运行时 =="
( cd "$PROJECT_ROOT" && flet build ipa -v ) >"$LOG" 2>&1 \
  || { echo "❌ 打包失败，详情见 $LOG"; exit 1; }

APP_PATH="$(ls -d "$BUILD_DIR"/flutter/build/ios/Release-iphoneos/*.app 2>/dev/null | head -1 || true)"

echo "== 2/3 签名归档（Xcode 自动签名）=="
rm -rf "$ARCHIVE"
( cd "$IOS_DIR" && xcodebuild -workspace Runner.xcworkspace -scheme Runner \
    -configuration Release -destination 'generic/platform=iOS' \
    -archivePath "$ARCHIVE" -allowProvisioningUpdates \
    archive DEVELOPMENT_TEAM="$TEAM_ID" CODE_SIGN_STYLE=Automatic \
    PROVISIONING_PROFILE_SPECIFIER="" ) >>"$LOG" 2>&1 \
  || { echo "❌ 归档失败，详情见 $LOG"; exit 1; }

ARCHIVED_APP="$ARCHIVE/Products/Applications/$APP_NAME.app"
if [[ ! -d "$ARCHIVED_APP/Frameworks/_ctypes.framework" ]]; then
  echo "❌ App 里缺少 _ctypes.framework —— 这是“启动即退”的典型症状。"
  echo "   请用: scripts/build_ios.sh --clean"
  exit 1
fi

echo "== 3/3 导出 ipa =="
STAGING_EXPORT="$BUILD_OUT/export.tmp"
rm -rf "$STAGING_EXPORT"
OPTIONS="$(mktemp -t exportOptions).plist"
cat >"$OPTIONS" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>method</key>
	<string>$EXPORT_METHOD</string>
	<key>teamID</key>
	<string>$TEAM_ID</string>
	<key>signingStyle</key>
	<string>automatic</string>
	<key>destination</key>
	<string>export</string>
	<key>stripSwiftSymbols</key>
	<true/>
	<key>uploadSymbols</key>
	<false/>
</dict>
</plist>
PLIST

( cd "$IOS_DIR" && xcodebuild -exportArchive -archivePath "$ARCHIVE" \
    -exportPath "$STAGING_EXPORT" -exportOptionsPlist "$OPTIONS" \
    -allowProvisioningUpdates ) >>"$LOG" 2>&1 \
  || { echo "❌ 导出失败，详情见 $LOG"; exit 1; }
rm -f "$OPTIONS"

# 导出成功后才替换上一次的产物，失败时旧包仍在
rm -rf "$EXPORT_DIR"
mv "$STAGING_EXPORT" "$EXPORT_DIR"

IPA="$EXPORT_DIR/$APP_NAME.ipa"
echo
echo "✅ 完成：$IPA"
echo "   bundle id: $(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$ARCHIVED_APP/Info.plist")"
codesign -dv --verbose=2 "$ARCHIVED_APP" 2>&1 | grep -m1 "Authority" | sed 's/^/   /' || true
echo "   安装：Xcode → Window → Devices and Simulators → 选中 iPhone → 把 ipa 拖进 Installed Apps"
