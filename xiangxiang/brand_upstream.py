#!/usr/bin/env python3
"""Apply deterministic XiangXiang branding to a clean Squirrel checkout."""

from __future__ import annotations

import json
import plistlib
import sys
from pathlib import Path


APP_NAME = "XiangXiangInput"
DISPLAY_NAME = "向向输入法"
BUNDLE_ID = "com.xiangxiang.inputmethod.XiangXiangInput"
HANS_ID = f"{BUNDLE_ID}.Hans"
HANT_ID = f"{BUNDLE_ID}.Hant"


def replace_required(path: Path, old: str, new: str, minimum: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count < minimum:
        raise RuntimeError(f"Expected at least {minimum} occurrence(s) of {old!r} in {path}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def patch_user_directory(path: Path) -> None:
    """Patch whichever user-directory spelling exists in this Squirrel revision."""
    text = path.read_text(encoding="utf-8")
    replacements = (
        ('"Library", "Rime"', '"Library", "XiangXiangInput"'),
        ('appendPathComponent("Rime",', 'appendPathComponent("XiangXiangInput",'),
    )
    count = 0
    for old, new in replacements:
        occurrences = text.count(old)
        if occurrences:
            text = text.replace(old, new)
            count += occurrences
    if count == 0:
        raise RuntimeError(f"Could not find a supported Rime user-directory declaration in {path}")
    path.write_text(text, encoding="utf-8")


def patch_registration(path: Path) -> None:
    """Make an in-place upgrade refresh the macOS input-source registration."""
    text = path.read_text(encoding="utf-8")
    start_marker = "  func register() {"
    end_marker = "  func enable(modes: [InputMode] = []) {"
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError(f"Could not find the input-source registration function in {path}")
    replacement = '''  func register() {
    // Always refresh the registration. Returning early here leaves macOS
    // pointing at an older app after an in-place upgrade.
    let error = TISRegisterInputSource(SquirrelApp.appDir as CFURL)
    print("Registration \(error == noErr ? \"succeeds\" : \"fails\") from \(SquirrelApp.appDir)")
  }
'''
    path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")


def patch_menu(path: Path) -> None:
    """Replace Squirrel's maintenance menu with XiangXiang's user actions."""
    text = path.read_text(encoding="utf-8")
    start_marker = "  override func menu() -> NSMenu! {"
    end_marker = "  private(set) var specialCommentIndices:"
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError(f"Could not find the input menu in {path}")
    replacement = '''  private var xiangXiangDataDir: URL {
    SquirrelApp.userDir.deletingLastPathComponent()
      .appendingPathComponent("Application Support/personal-english-lexicon", isDirectory: true)
  }

  private func xiangXiangItem(_ title: String, _ action: Selector) -> NSMenuItem {
    let item = NSMenuItem(title: title, action: action, keyEquivalent: "")
    item.target = self
    return item
  }

  override func menu() -> NSMenu! {
    let menu = NSMenu()
    menu.addItem(xiangXiangItem("打开本地记录的句子", #selector(openRecordedSentences)))
    menu.addItem(xiangXiangItem("打开句子翻译", #selector(openSentenceTranslations)))
    menu.addItem(xiangXiangItem("打开词库", #selector(openVocabulary)))
    menu.addItem(xiangXiangItem("上传词库", #selector(importDictionary)))
    return menu
  }

  private func xiangXiangOpen(_ url: URL, missingMessage: String) {
    guard FileManager.default.fileExists(atPath: url.path) else {
      let alert = NSAlert()
      alert.messageText = missingMessage
      alert.informativeText = "文件尚未生成。"
      alert.runModal()
      return
    }
    NSWorkspace.shared.open(url)
  }

  @objc func openRecordedSentences() {
    xiangXiangOpen(xiangXiangDataDir.appendingPathComponent("sentences.tsv"),
                  missingMessage: "还没有本地记录的句子")
  }

  @objc func openSentenceTranslations() {
    xiangXiangOpen(xiangXiangDataDir.appendingPathComponent("reports/sentences.md"),
                  missingMessage: "还没有句子翻译报告")
  }

  @objc func openVocabulary() {
    xiangXiangOpen(xiangXiangDataDir.appendingPathComponent("reports/vocabulary.md"),
                  missingMessage: "还没有个人词库报告")
  }

  @objc func importDictionary() {
    xiangXiangOpen(SquirrelApp.userDir.appendingPathComponent("Tools/XiangXiangDictionaryImporter.app"),
                  missingMessage: "词库导入工具未安装")
  }

'''
    path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")


def patch_info_plist(root: Path) -> None:
    path = root / "resources" / "Info.plist"
    with path.open("rb") as handle:
        info = plistlib.load(handle)

    info["TISInputSourceID"] = BUNDLE_ID
    info["CFBundleExecutable"] = APP_NAME
    info["CFBundleName"] = DISPLAY_NAME
    info["CFBundleDisplayName"] = DISPLAY_NAME
    # Newer macOS releases require this exact bundle-ID-derived name. A short
    # app-name-derived value can leave the input source visible but unusable.
    info["InputMethodConnectionName"] = f"{BUNDLE_ID}_Connection"
    controller = f"{APP_NAME}.SquirrelInputController"
    info["InputMethodServerControllerClass"] = controller
    info["InputMethodServerDelegateClass"] = controller
    info["SUEnableAutomaticChecks"] = False
    info.pop("SUFeedURL", None)
    info.pop("SUPublicEDKey", None)

    modes = info["ComponentInputModeDict"]["tsInputModeListKey"]
    hans = modes.pop("im.rime.inputmethod.Squirrel.Hans")
    modes.pop("im.rime.inputmethod.Squirrel.Hant")
    hans["TISInputSourceID"] = HANS_ID
    modes[HANS_ID] = hans
    info["ComponentInputModeDict"]["tsVisibleInputModeOrderedArrayKey"] = [HANS_ID]

    with path.open("wb") as handle:
        plistlib.dump(info, handle, sort_keys=False)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: brand_upstream.py /path/to/squirrel", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    required = [
        root / "Squirrel.xcodeproj" / "project.pbxproj",
        root / "resources" / "Info.plist",
        root / "sources" / "Main.swift",
        root / "sources" / "InputSource.swift",
        root / "sources" / "SquirrelApplicationDelegate.swift",
        root / "sources" / "SquirrelInputController.swift",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("Missing upstream files: " + ", ".join(missing))

    project = required[0]
    replace_required(project, "path = Squirrel.app;", f"path = {APP_NAME}.app;")
    replace_required(
        project,
        "INFOPLIST_KEY_CFBundleDisplayName = \"Squirrel Input Method\";",
        f'INFOPLIST_KEY_CFBundleDisplayName = "{DISPLAY_NAME}";',
        minimum=2,
    )
    replace_required(
        project,
        "PRODUCT_BUNDLE_IDENTIFIER = im.rime.inputmethod.Squirrel;",
        f"PRODUCT_BUNDLE_IDENTIFIER = {BUNDLE_ID};",
        minimum=2,
    )
    replace_required(project, "PRODUCT_NAME = Squirrel;", f"PRODUCT_NAME = {APP_NAME};", minimum=2)
    replace_required(project, "productName = Squirrel;", f"productName = {APP_NAME};")

    patch_info_plist(root)

    main_swift = root / "sources" / "Main.swift"
    patch_user_directory(main_swift)
    replace_required(
        main_swift,
        '''  static let appDir = "/Library/Input Methods/Squirrel.app".withCString { dir in
    URL(fileURLWithFileSystemRepresentation: dir, isDirectory: false, relativeTo: nil)
  }''',
        "  static let appDir = Bundle.main.bundleURL",
    )
    replace_required(main_swift, '"rime.squirrel-builder"', '"xiangxiang.input-builder"')
    replace_required(main_swift, '"rime.squirrel"', '"xiangxiang.input"')

    input_source = root / "sources" / "InputSource.swift"
    replace_required(input_source, '"im.rime.inputmethod.Squirrel.Hans"', f'"{HANS_ID}"')
    replace_required(input_source, '"im.rime.inputmethod.Squirrel.Hant"', f'"{HANT_ID}"')
    patch_registration(input_source)

    patch_menu(required[5])

    delegate = root / "sources" / "SquirrelApplicationDelegate.swift"
    replace_required(delegate, '"Squirrel"', f'"{APP_NAME}"')
    replace_required(delegate, '"\u9f20\u9b1a\u7ba1"', f'"{DISPLAY_NAME}"')
    replace_required(delegate, '"rime.squirrel"', '"xiangxiang.input"')
    replace_required(delegate, '"squirrel_launch.json"', '"xiangxiang_launch.json"')

    for source in root.glob("sources/*.swift"):
        text = source.read_text(encoding="utf-8")
        text = text.replace("SquirrelReloadNotification", "XiangXiangReloadNotification")
        text = text.replace("SquirrelSyncNotification", "XiangXiangSyncNotification")
        text = text.replace("SquirrelToggleASCIIModeNotification", "XiangXiangToggleASCIIModeNotification")
        text = text.replace("SquirrelGetASCIIModeNotification", "XiangXiangGetASCIIModeNotification")
        text = text.replace("SquirrelASCIIModeResponse", "XiangXiangASCIIModeResponse")
        source.write_text(text, encoding="utf-8")

    strings = root / "resources" / "InfoPlist.xcstrings"
    if strings.is_file():
        catalog = json.loads(strings.read_text(encoding="utf-8"))
        entries = catalog["strings"]
        renamed_entries = {
            "im.rime.inputmethod.Squirrel": BUNDLE_ID,
            "im.rime.inputmethod.Squirrel.Hans": HANS_ID,
            "im.rime.inputmethod.Squirrel.Hant": HANT_ID,
        }
        for old, new in renamed_entries.items():
            if old in entries:
                entries[new] = entries.pop(old)
        for key in ("CFBundleDisplayName", "CFBundleName", BUNDLE_ID, HANS_ID, HANT_ID):
            for localization in entries.get(key, {}).get("localizations", {}).values():
                localization["stringUnit"]["value"] = DISPLAY_NAME
        strings.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Branded Squirrel as {DISPLAY_NAME} ({BUNDLE_ID})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
