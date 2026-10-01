#!/usr/bin/env python3
"""Verify the identity of a built XiangXiang input method bundle."""

from __future__ import annotations

import json
import plistlib
import subprocess
import sys
from pathlib import Path


EXPECTED_BUNDLE_ID = "com.xiangxiang.inputmethod.XiangXiangInput"
EXPECTED_NAME = "向向输入法"
EXPECTED_EXECUTABLE = "XiangXiangInput"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_app.py /path/to/XiangXiangInput.app", file=sys.stderr)
        return 2

    app = Path(sys.argv[1])
    info_path = app / "Contents" / "Info.plist"
    with info_path.open("rb") as handle:
        info = plistlib.load(handle)

    expected = {
        "CFBundleIdentifier": EXPECTED_BUNDLE_ID,
        "CFBundleDisplayName": EXPECTED_NAME,
        "CFBundleExecutable": EXPECTED_EXECUTABLE,
        "TISInputSourceID": EXPECTED_BUNDLE_ID,
    }
    for key, value in expected.items():
        actual = info.get(key)
        if actual != value:
            raise RuntimeError(f"{key}: expected {value!r}, got {actual!r}")

    executable = app / "Contents" / "MacOS" / EXPECTED_EXECUTABLE
    if not executable.is_file():
        raise RuntimeError(f"Missing executable: {executable}")

    archs = subprocess.check_output(["lipo", "-archs", str(executable)], text=True).split()
    if set(archs) != {"arm64", "x86_64"}:
        raise RuntimeError(f"Expected universal binary, got: {' '.join(archs)}")

    defaults = app / "Contents" / "SharedSupport" / "XiangXiangDefaults"
    for relative in (
        "lua/sentence_recorder.lua",
        "lua/personal_translate.lua",
        "default.custom.yaml",
        "luna_pinyin.custom.yaml",
        "personal_translate.tsv",
    ):
        if not (defaults / relative).is_file():
            raise RuntimeError(f"Missing bundled default: {relative}")

    localized_info = list((app / "Contents" / "Resources").glob("*.lproj/InfoPlist.strings"))
    if not localized_info:
        raise RuntimeError("Missing localized InfoPlist.strings files")
    for path in localized_info:
        localized = json.loads(
            subprocess.check_output(["plutil", "-convert", "json", "-o", "-", str(path)], text=True)
        )
        for key in ("CFBundleDisplayName", "CFBundleName", EXPECTED_BUNDLE_ID, f"{EXPECTED_BUNDLE_ID}.Hans"):
            if localized.get(key) != EXPECTED_NAME:
                raise RuntimeError(f"{path.name}:{key} is not branded as {EXPECTED_NAME}")

    visible_modes = info["ComponentInputModeDict"]["tsVisibleInputModeOrderedArrayKey"]
    if visible_modes != [f"{EXPECTED_BUNDLE_ID}.Hans"]:
        raise RuntimeError(f"Expected one Simplified Chinese input mode, got: {visible_modes}")

    entitlement_output = subprocess.check_output(
        ["codesign", "-d", "--entitlements", ":-", str(app)], stderr=subprocess.STDOUT
    )
    plist_start = entitlement_output.find(b"<?xml")
    if plist_start < 0:
        raise RuntimeError("Missing app entitlements")
    entitlements = plistlib.loads(entitlement_output[plist_start:])
    if entitlements.get("com.apple.security.cs.disable-library-validation") is not True:
        raise RuntimeError("Missing disable-library-validation entitlement")
    if entitlements.get("com.apple.security.app-sandbox") is not False:
        raise RuntimeError("Unexpected app sandbox entitlement")

    print(f"Verified {EXPECTED_NAME}: {EXPECTED_BUNDLE_ID}; architectures: {' '.join(archs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
