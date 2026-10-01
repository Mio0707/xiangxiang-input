#!/bin/bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
source_app="${script_dir}/XiangXiangInput.app"
target_dir="${HOME}/Library/Input Methods"
target_app="${target_dir}/XiangXiangInput.app"
user_dir="${HOME}/Library/XiangXiangInput"
backup_root="${user_dir}/Backups"
timestamp="$(date +%Y%m%d-%H%M%S)"
executable="${target_app}/Contents/MacOS/XiangXiangInput"
defaults_dir="${target_app}/Contents/SharedSupport/XiangXiangDefaults"

if [ ! -d "${source_app}" ]; then
  echo "Missing XiangXiangInput.app beside this installer."
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

if [ -d "${target_app}" ]; then
  backup_app="${backup_root}/XiangXiangInput-${timestamp}.app"
  mv "${target_app}" "${backup_app}"
  echo "Previous app backed up to: ${backup_app}"
fi

ditto "${source_app}" "${target_app}"
xattr -dr com.apple.quarantine "${target_app}" 2>/dev/null || true

copy_if_missing() {
  source_path="$1"
  destination_path="$2"
  if [ ! -e "${destination_path}" ]; then
    cp "${source_path}" "${destination_path}"
  fi
}

copy_if_missing "${defaults_dir}/lua/sentence_recorder.lua" "${user_dir}/lua/sentence_recorder.lua"
copy_if_missing "${defaults_dir}/lua/personal_translate.lua" "${user_dir}/lua/personal_translate.lua"
copy_if_missing "${defaults_dir}/default.custom.yaml" "${user_dir}/default.custom.yaml"
copy_if_missing "${defaults_dir}/luna_pinyin.custom.yaml" "${user_dir}/luna_pinyin.custom.yaml"

if [ ! -e "${user_dir}/personal_translate.tsv" ]; then
  old_lexicon="${HOME}/Library/Rime/personal_translate.tsv"
  if [ -e "${old_lexicon}" ]; then
    cp "${old_lexicon}" "${user_dir}/personal_translate.tsv"
  else
    cp "${defaults_dir}/personal_translate.tsv" "${user_dir}/personal_translate.tsv"
  fi
fi

lsregister="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
"${lsregister}" -f "${target_app}"
"${executable}" --register-input-source
"${executable}" --build
"${executable}" --enable-input-source
"${executable}" --select-input-source

echo "Installed XiangXiang Input Method for ${USER}."
echo "If it does not appear immediately, log out and back in once."
