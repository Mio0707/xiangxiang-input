#!/bin/bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
source_archive="${script_dir}/XiangXiangInput.app.zip"
helper_archive="${script_dir}/XiangXiangDictionaryImporter.app.zip"
entitlements="${script_dir}/adhoc-entitlements.plist"
maintenance_entitlements="${script_dir}/maintenance-entitlements.plist"
target_dir="${HOME}/Library/Input Methods"
target_app="${target_dir}/XiangXiangInput.app"
user_dir="${HOME}/Library/XiangXiangInput"
backup_root="${user_dir}/Backups"
timestamp="$(date +%Y%m%d-%H%M%S)"
executable="${target_app}/Contents/MacOS/XiangXiangInput"
deployer="${target_app}/Contents/MacOS/rime_deployer"
defaults_dir="${target_app}/Contents/SharedSupport/XiangXiangDefaults"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/xiangxiang-install.XXXXXX")"
staged_app="${work_dir}/XiangXiangInput.app"
staged_helper="${work_dir}/XiangXiangDictionaryImporter.app"

cleanup() {
  rm -rf "${work_dir}"
}
trap cleanup EXIT

if [ ! -f "${source_archive}" ] || [ ! -f "${helper_archive}" ] ||
   [ ! -f "${entitlements}" ] || [ ! -f "${maintenance_entitlements}" ] ||
   [ ! -f "${script_dir}/dictionary_import.py" ] || [ ! -f "${script_dir}/导入词库.command" ] ||
   [ ! -f "${script_dir}/词库模板.csv" ]; then
  echo "Missing the app archive or entitlements beside this installer."
  exit 1
fi

if [ -d "/Library/Input Methods/XiangXiangInput.app" ]; then
  echo "A system-wide test copy already exists at:"
  echo "  /Library/Input Methods/XiangXiangInput.app"
  echo "Move that copy to a backup first, then run this installer again."
  exit 2
fi

mkdir -p "${target_dir}" "${user_dir}/lua" "${backup_root}"

killall XiangXiangInput >/dev/null 2>&1 || true

ditto -x -k "${source_archive}" "${work_dir}"
ditto -x -k "${helper_archive}" "${work_dir}"
xattr -dr com.apple.quarantine "${staged_app}" 2>/dev/null || true
xattr -dr com.apple.quarantine "${staged_helper}" 2>/dev/null || true
codesign --force --deep --sign - --entitlements "${maintenance_entitlements}" "${staged_app}"
codesign --verify --deep --strict "${staged_app}"
codesign --force --sign - "${staged_helper}"
codesign --verify --deep --strict "${staged_helper}"

if [ -d "${target_app}" ]; then
  backup_app="${backup_root}/XiangXiangInput-${timestamp}.app"
  mv "${target_app}" "${backup_app}"
  echo "Previous app backed up to: ${backup_app}"
fi

ditto "${staged_app}" "${target_app}"

copy_if_missing() {
  source_path="$1"
  destination_path="$2"
  if [ ! -e "${destination_path}" ]; then
    cp "${source_path}" "${destination_path}"
  fi
}

install_managed_lua() {
  source_path="$1"
  destination_path="${user_dir}/lua/$(basename "${source_path}")"
  if [ -f "${destination_path}" ] && ! cmp -s "${source_path}" "${destination_path}"; then
    cp -p "${destination_path}" "${backup_root}/$(basename "${source_path}")-${timestamp}"
  fi
  cp "${source_path}" "${destination_path}"
}

install_managed_lua "${defaults_dir}/lua/sentence_recorder.lua"
install_managed_lua "${defaults_dir}/lua/personal_translate.lua"
copy_if_missing "${defaults_dir}/default.custom.yaml" "${user_dir}/default.custom.yaml"
copy_if_missing "${defaults_dir}/luna_pinyin.custom.yaml" "${user_dir}/luna_pinyin.custom.yaml"

mkdir -p "${user_dir}/Tools"
helper_app="${user_dir}/Tools/XiangXiangDictionaryImporter.app"
if [ -e "${helper_app}" ]; then
  helper_backup="${backup_root}/XiangXiangDictionaryImporter-${timestamp}.app"
  mv "${helper_app}" "${helper_backup}"
  echo "Previous dictionary importer backed up to: ${helper_backup}"
fi
ditto "${staged_helper}" "${helper_app}"
install_tool() {
  source_path="$1"
  destination_path="${user_dir}/Tools/$(basename "${source_path}")"
  if [ -f "${destination_path}" ] && ! cmp -s "${source_path}" "${destination_path}"; then
    cp "${destination_path}" "${backup_root}/$(basename "${source_path}")-${timestamp}"
  fi
  cp "${source_path}" "${destination_path}"
}
install_tool "${script_dir}/dictionary_import.py"
install_tool "${script_dir}/导入词库.command"
copy_if_missing "${script_dir}/词库模板.csv" "${user_dir}/Tools/词库模板.csv"
chmod +x "${user_dir}/Tools/导入词库.command"

if [ ! -e "${user_dir}/personal_translate.tsv" ]; then
  old_lexicon="${HOME}/Library/Rime/personal_translate.tsv"
  if [ -e "${old_lexicon}" ]; then
    cp "${old_lexicon}" "${user_dir}/personal_translate.tsv"
  else
    cp "${defaults_dir}/personal_translate.tsv" "${user_dir}/personal_translate.tsv"
  fi
fi

if [ -d "${user_dir}/build" ]; then
  build_backup="${backup_root}/build-${timestamp}"
  ditto "${user_dir}/build" "${build_backup}"
  echo "Previous Rime build backed up to: ${build_backup}"
fi

lsregister="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
"${lsregister}" -f "${target_app}"
"${executable}" --register-input-source
"${deployer}" --build \
  "${user_dir}" \
  "${target_app}/Contents/SharedSupport" \
  "${user_dir}/build"
"${executable}" --enable-input-source

# The installed input method itself is sandboxed. Registration and deployment
# run before this final signature because TIS maintenance is denied inside the
# app sandbox on current macOS releases.
codesign --force --deep --sign - --entitlements "${entitlements}" "${target_app}"
codesign --verify --deep --strict "${target_app}"
"${lsregister}" -f "${target_app}"

echo "Installed XiangXiang Input Method for ${USER}."
echo "Select 向向输入法 from the input menu."
echo "Import your own CSV/TSV at: ${user_dir}/Tools/导入词库.command"
echo "After an upgrade, log out and back in once if macOS still shows an older name."
