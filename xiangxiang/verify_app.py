#!/usr/bin/env python3
"""Verify the identity of a built XiangXiang input method bundle."""

from __future__ import annotations

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

    print(f"Verified {EXPECTED_NAME}: {EXPECTED_BUNDLE_ID}; architectures: {' '.join(archs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
