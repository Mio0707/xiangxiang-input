#!/bin/bash
set -euo pipefail

data_dir="${HOME}/Library/Application Support/personal-english-lexicon"
skill_file="${HOME}/.codex/skills/personal-english-lexicon/SKILL.md"
codex_cli="$(command -v codex || true)"
if [ -z "${codex_cli}" ] && [ -x "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex" ]; then
  codex_cli="/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex"
fi

status=0
if [ ! -s "${data_dir}/sentences.tsv" ]; then
  echo "还没有记录到中文句子。"
  status=1
elif [ ! -f "${skill_file}" ]; then
  echo "未找到 personal-english-lexicon skill：${skill_file}"
  status=1
elif [ -z "${codex_cli}" ]; then
  echo "未找到 Codex CLI。请先安装并登录 Codex。"
  status=1
else
  "${codex_cli}" exec \
    --skip-git-repo-check \
    -C "${HOME}/Library/XiangXiangInput/Tools" \
    --add-dir "${data_dir}" \
    - <<'PROMPT' || status=$?
使用 $personal-english-lexicon skill 处理本地尚未处理的中文句子：先校对明显错字，再翻译成自然、口语化的英文，生成句子翻译和个人词库报告。严格按 skill 的隐私与质量要求操作。不要执行 publish，不要更新输入法候选词词库；先让我检查报告并明确批准。完成后告诉我两份报告的路径。
PROMPT
fi

echo
echo "按回车键关闭此窗口。"
if [ -t 0 ]; then read -r _; fi
exit "${status}"
