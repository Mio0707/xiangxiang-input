#!/usr/bin/env python3
"""Apply deterministic XiangXiang branding to a clean Squirrel checkout."""

from __future__ import annotations

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


def patch_info_plist(root: Path) -> None:
    path = root / "resources" / "Info.plist"
    with path.open("rb") as handle:
        info = plistlib.load(handle)

    info["TISInputSourceID"] = BUNDLE_ID
    info["CFBundleExecutable"] = APP_NAME
    info["CFBundleName"] = DISPLAY_NAME
    info["CFBundleDisplayName"] = DISPLAY_NAME
    info["InputMethodConnectionName"] = f"{APP_NAME}_Connection"
    controller = f"{APP_NAME}.SquirrelInputController"
    info["InputMethodServerControllerClass"] = controller
    info["InputMethodServerDelegateClass"] = controller
    info["SUEnableAutomaticChecks"] = False
    info.pop("SUFeedURL", None)
    info.pop("SUPublicEDKey", None)

    modes = info["ComponentInputModeDict"]["tsInputModeListKey"]
    hans = modes.pop("im.rime.inputmethod.Squirrel.Hans")
    hant = modes.pop("im.rime.inputmethod.Squirrel.Hant")
    hans["TISInputSourceID"] = HANS_ID
    hant["TISInputSourceID"] = HANT_ID
    modes[HANS_ID] = hans
    modes[HANT_ID] = hant
    info["ComponentInputModeDict"]["tsVisibleInputModeOrderedArrayKey"] = [HANS_ID, HANT_ID]

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
    replace_required(main_swift, '"/Library/Input Methods/Squirrel.app"', '"/Library/Input Methods/XiangXiangInput.app"')
    replace_required(main_swift, '"rime.squirrel-builder"', '"xiangxiang.input-builder"')
    replace_required(main_swift, '"rime.squirrel"', '"xiangxiang.input"')

    input_source = root / "sources" / "InputSource.swift"
    replace_required(input_source, '"im.rime.inputmethod.Squirrel.Hans"', f'"{HANS_ID}"')
    replace_required(input_source, '"im.rime.inputmethod.Squirrel.Hant"', f'"{HANT_ID}"')

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
        text = strings.read_text(encoding="utf-8")
        text = text.replace("Squirrel Input Method", DISPLAY_NAME).replace("\u9f20\u9b1a\u7ba1", DISPLAY_NAME)
        strings.write_text(text, encoding="utf-8")

    print(f"Branded Squirrel as {DISPLAY_NAME} ({BUNDLE_ID})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
