#!/bin/bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
if [ "$#" -gt 0 ]; then
  selected_file="$1"
  shift
else
  selected_file="$(/usr/bin/osascript -e 'POSIX path of (choose file with prompt "选择 CSV 或 TSV 词库文件")')" || exit 0
fi

status=0
/usr/bin/python3 "${script_dir}/dictionary_import.py" "${selected_file}" "$@" || status=$?
echo
echo "按回车键关闭此窗口。"
if [ -t 0 ]; then read -r _; fi
exit "${status}"
