XiangXiang Input Method 0.1.10 (unsigned test build)

1. Keep this folder intact; the app archive and entitlements are required.
2. Double-click "Install XiangXiangInput.command".
3. If macOS blocks it, right-click the file and choose Open.

This test installer uses ~/Library/Input Methods and does not require an
administrator password. Existing XiangXiang YAML configuration is not overwritten.
An existing app is moved to ~/Library/XiangXiangInput/Backups before replacement.
Managed Lua modules are backed up there before an update.

To import a bilingual CSV/TSV, choose 上传词库 from the input-method menu.
This opens a local GUI importer without Terminal. The manual command remains at:
  ~/Library/XiangXiangInput/Tools/导入词库.command
The file needs Chinese and English columns. Personal translations take priority.

The input-method menu opens local sentence and vocabulary reports or imports a
dictionary. To process sentences with AI, run the personal-english-lexicon
skill directly in Codex; the input-method menu does not start it.

Public distribution still requires Developer ID signing and notarization.
