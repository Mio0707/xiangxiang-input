#!/usr/bin/env python3
"""Import a user-selected bilingual CSV/TSV into XiangXiang's local lookup."""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import sys
import time
from pathlib import Path


DEFAULT_USER_DIR = Path.home() / "Library/XiangXiangInput"
CHINESE_HEADERS = {"中文", "汉语", "释义", "词义", "翻译", "chinese", "zh", "meaning", "translation", "definition"}
ENGLISH_HEADERS = {"英文", "英语", "单词", "词汇", "english", "en", "word", "headword"}
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_ROWS = 200_000
MAX_ZH_LENGTH = 20
MAX_EN_LENGTH = 100
CHINESE_RE = re.compile(r"[\u3400-\u9fff]")
ENGLISH_RE = re.compile(r"[A-Za-z]")
POS_PREFIX = re.compile(r"^(?:(?:n|v|adj|adv|prep|pron|conj|interj)\.|[①-⑳]|\d+[.)、])\s*", re.I)


def normalized(value: str) -> str:
    return " ".join(value.replace("\u3000", " ").split()).strip()


def header_index(headers: list[str], candidates: set[str]) -> int | None:
    for index, header in enumerate(headers):
        if normalized(header).casefold() in candidates:
            return index
    return None


def parse_file(path: Path) -> tuple[dict[str, list[str]], int, int]:
    if path.suffix.lower() not in {".csv", ".tsv"}:
        raise ValueError("只支持带表头的 .csv 或 .tsv 文件")
    if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("文件不存在或超过 20 MB")

    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    entries: dict[str, list[str]] = {}
    skipped = 0
    rows_read = 0
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, delimiter=delimiter)
        headers = next(reader, None)
        if not headers:
            raise ValueError("词库文件为空")
        zh_index = header_index(headers, CHINESE_HEADERS)
        en_index = header_index(headers, ENGLISH_HEADERS)
        if zh_index is None or en_index is None or zh_index == en_index:
            raise ValueError("表头需要中文和英文两列，例如：中文,英文 或 word,translation")

        for row_number, row in enumerate(reader, 2):
            rows_read += 1
            if row_number > MAX_ROWS + 1:
                raise ValueError("词库超过 20 万行，请拆分文件")
            if len(row) <= max(zh_index, en_index):
                skipped += 1
                continue
            english_values = [normalized(part) for part in re.split(r"[|；;]", row[en_index])]
            chinese_values = [normalized(POS_PREFIX.sub("", part)) for part in re.split(r"[|；;、]", row[zh_index])]
            valid_english = [
                value for value in english_values
                if value and len(value) <= MAX_EN_LENGTH and ENGLISH_RE.search(value)
                and not any(char in value for char in "\t\r\n")
            ][:2]
            valid_chinese = [
                value for value in chinese_values
                if value and len(value) <= MAX_ZH_LENGTH and CHINESE_RE.search(value)
                and not any(char in value for char in "\t\r\n")
            ]
            if not valid_english or not valid_chinese:
                skipped += 1
                continue
            for chinese in valid_chinese:
                translations = entries.setdefault(chinese, [])
                for english in valid_english:
                    if english not in translations and len(translations) < 2:
                        translations.append(english)
    if not entries:
        raise ValueError("没有可用的中英词条；请检查列名和内容")
    return entries, rows_read, skipped


def safe_name(name: str) -> str:
    value = re.sub(r"[^\w-]+", "-", name, flags=re.UNICODE).strip("-_")[:80]
    if not value:
        raise ValueError("词库名称无效")
    return value


def read_normalized(path: Path) -> dict[str, list[str]]:
    entries: dict[str, list[str]] = {}
    with path.open("r", encoding="utf-8") as stream:
        for raw in stream:
            if raw.startswith("#") or "\t" not in raw:
                continue
            chinese, english = raw.rstrip("\n").split("\t", 1)
            if chinese and english:
                entries[chinese] = english.split("|")[:2]
    return entries


def render(entries: dict[str, list[str]]) -> str:
    lines = [f"#rev={time.time_ns()}"]
    for chinese in sorted(entries):
        lines.append(f"{chinese}\t{'|'.join(entries[chinese][:2])}")
    return "\n".join(lines) + "\n"


def build_index(sources: dict[str, dict[str, list[str]]]) -> dict[str, list[str]]:
    combined: dict[str, list[str]] = {}
    for name in sorted(sources):
        for chinese, english_values in sources[name].items():
            translations = combined.setdefault(chinese, [])
            for english in english_values:
                if english not in translations and len(translations) < 2:
                    translations.append(english)
    return combined


def atomic_write(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def import_dictionary(path: Path, user_dir: Path, name: str | None = None) -> dict[str, object]:
    parsed, lines, skipped = parse_file(path)
    dictionary_name = safe_name(name or path.stem)
    source_dir = user_dir / "imported_dictionaries"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_path = source_dir / f"{dictionary_name}.tsv"
    index_path = user_dir / "imported_translate.tsv"
    sources = {
        item.stem: read_normalized(item)
        for item in source_dir.glob("*.tsv") if item != source_path
    }
    sources[dictionary_name] = parsed
    index = build_index(sources)

    backup_dir = user_dir / "Backups" / "ImportedDictionaries"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{time.time_ns() % 1_000_000_000:09d}"
    for existing in (source_path, index_path):
        if existing.exists():
            shutil.copy2(existing, backup_dir / f"{stamp}-{existing.name}")

    atomic_write(source_path, render(parsed))
    atomic_write(index_path, render(index))
    return {
        "name": dictionary_name,
        "rows": lines,
        "skipped": skipped,
        "entries": len(parsed),
        "active_entries": len(index),
        "source": str(source_path),
        "index": str(index_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="带表头的 CSV 或 TSV 词库")
    parser.add_argument("--name", help="词库名称，默认使用文件名")
    parser.add_argument("--user-dir", type=Path, default=DEFAULT_USER_DIR)
    args = parser.parse_args()
    try:
        result = import_dictionary(args.file, args.user_dir, args.name)
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        print(f"导入失败：{error}", file=sys.stderr)
        return 1
    print(f"已导入「{result['name']}」：{result['entries']} 个中文词条，跳过 {result['skipped']} 行。")
    print(f"当前启用的导入词条：{result['active_entries']} 个。个人词库释义优先。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
