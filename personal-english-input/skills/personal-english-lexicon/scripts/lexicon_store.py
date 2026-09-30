#!/usr/bin/env python3
"""Deterministic local storage for the personal English lexicon workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import time
from pathlib import Path


DEFAULT_DATA_DIR = Path.home() / "Library/Application Support/personal-english-lexicon"
DEFAULT_RIME_LEXICON = Path.home() / "Library/Rime/personal_translate.tsv"
CJK_RE = re.compile(r"[\u3400-\u9fff]")
SPACE_RE = re.compile(r"\s+")
TRIVIAL_SENTENCES = {"好", "好的", "谢谢", "你好", "再见", "嗯", "哦", "是", "不是"}
PRIVATE_PATTERN = re.compile(r"(?:https?://|www\.|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})", re.I)
LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2", "specialized"}
TYPES = {"word", "phrase"}


def normalize(text: str) -> str:
    return SPACE_RE.sub(" ", text.replace("\u3000", " ")).strip()


def db_connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS events (
          source_key TEXT PRIMARY KEY,
          captured_at INTEGER NOT NULL,
          sentence TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sentences (
          id INTEGER PRIMARY KEY,
          normalized TEXT NOT NULL UNIQUE,
          representative TEXT NOT NULL,
          occurrence_count INTEGER NOT NULL DEFAULT 1,
          first_seen INTEGER NOT NULL,
          last_seen INTEGER NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending'
            CHECK(status IN ('pending','processed','ignored'))
        );
        CREATE TABLE IF NOT EXISTS analyses (
          sentence_id INTEGER PRIMARY KEY REFERENCES sentences(id),
          english TEXT NOT NULL,
          processed_at INTEGER NOT NULL,
          corrected_zh TEXT
        );
        CREATE TABLE IF NOT EXISTS alignments (
          id INTEGER PRIMARY KEY,
          sentence_id INTEGER NOT NULL REFERENCES sentences(id),
          zh TEXT NOT NULL,
          en TEXT NOT NULL,
          item_type TEXT NOT NULL CHECK(item_type IN ('word','phrase')),
          level TEXT NOT NULL,
          UNIQUE(sentence_id, zh, en)
        );
        """
    )
    analysis_columns = {
        row[1] for row in db.execute("PRAGMA table_info(analyses)").fetchall()
    }
    if "corrected_zh" not in analysis_columns:
        db.execute("ALTER TABLE analyses ADD COLUMN corrected_zh TEXT")
        db.commit()
    return db


def ingest(db: sqlite3.Connection, log_path: Path) -> dict[str, int]:
    stats = {"read": 0, "new_events": 0, "new_sentences": 0, "ignored": 0}
    if not log_path.exists():
        return stats

    with log_path.open("r", encoding="utf-8", errors="replace") as stream:
        for line_no, raw in enumerate(stream, 1):
            stats["read"] += 1
            raw = raw.rstrip("\n")
            if "\t" not in raw:
                continue
            timestamp_raw, sentence_raw = raw.split("\t", 1)
            try:
                captured_at = int(timestamp_raw)
            except ValueError:
                continue
            sentence = normalize(sentence_raw)
            if not sentence or not CJK_RE.search(sentence):
                continue
            source_key = hashlib.sha256(
                f"{line_no}\0{captured_at}\0{sentence}".encode("utf-8")
            ).hexdigest()
            inserted = db.execute(
                "INSERT OR IGNORE INTO events VALUES (?,?,?)",
                (source_key, captured_at, sentence),
            ).rowcount
            if not inserted:
                continue
            stats["new_events"] += 1

            row = db.execute(
                "SELECT id FROM sentences WHERE normalized=?", (sentence,)
            ).fetchone()
            if row:
                db.execute(
                    """UPDATE sentences
                       SET occurrence_count=occurrence_count+1, last_seen=?
                       WHERE id=?""",
                    (captured_at, row["id"]),
                )
            else:
                status = (
                    "ignored"
                    if sentence in TRIVIAL_SENTENCES or PRIVATE_PATTERN.search(sentence)
                    else "pending"
                )
                db.execute(
                    """INSERT INTO sentences
                       (normalized, representative, first_seen, last_seen, status)
                       VALUES (?,?,?,?,?)""",
                    (sentence, sentence, captured_at, captured_at, status),
                )
                stats["new_sentences"] += 1
                if status == "ignored":
                    stats["ignored"] += 1
    db.commit()
    return stats


def pending(db: sqlite3.Connection, limit: int) -> list[dict[str, object]]:
    rows = db.execute(
        """SELECT id, representative AS zh, occurrence_count, first_seen, last_seen
           FROM sentences WHERE status='pending'
           ORDER BY occurrence_count DESC, first_seen ASC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def ignore_sentences(db: sqlite3.Connection, ids: list[int]) -> int:
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    changed = db.execute(
        f"UPDATE sentences SET status='ignored' WHERE status='pending' AND id IN ({placeholders})",
        ids,
    ).rowcount
    db.commit()
    return changed


def clean_translation(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("translation must be a string")
    value = normalize(value)
    if not value or "\t" in value or "\n" in value:
        raise ValueError("translation is empty or contains control characters")
    return value


def apply_results(db: sqlite3.Connection, result_path: Path) -> int:
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("result file must contain a JSON array")

    applied = 0
    now = int(time.time())
    for result in payload:
        if not isinstance(result, dict) or not isinstance(result.get("id"), int):
            raise ValueError("each result needs an integer id")
        row = db.execute(
            "SELECT representative, status FROM sentences WHERE id=?", (result["id"],)
        ).fetchone()
        if not row or row["status"] != "pending":
            raise ValueError(f"sentence {result['id']} is missing or not pending")
        if normalize(result.get("zh", "")) != row["representative"]:
            raise ValueError(f"sentence {result['id']} text does not match")

        corrected_zh = normalize(result.get("corrected_zh", row["representative"]))
        if not corrected_zh or not CJK_RE.search(corrected_zh):
            raise ValueError(f"sentence {result['id']} has invalid corrected Chinese")
        english = clean_translation(result.get("en"))
        items = result.get("items", [])
        if not isinstance(items, list) or len(items) > 20:
            raise ValueError(f"sentence {result['id']} has invalid items")

        validated: list[tuple[str, str, str, str]] = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("alignment must be an object")
            if item.get("keep") is not True:
                continue
            zh = normalize(item.get("zh", ""))
            if not zh or zh not in corrected_zh:
                raise ValueError(f"alignment '{zh}' is not in corrected sentence")
            item_type = item.get("type")
            level = item.get("level")
            if item_type not in TYPES or level not in LEVELS:
                raise ValueError(f"alignment '{zh}' has invalid type or level")
            if level in {"A1", "A2"}:
                continue
            translations = item.get("en")
            if not isinstance(translations, list) or not 1 <= len(translations) <= 2:
                raise ValueError(f"alignment '{zh}' needs one or two translations")
            for en in translations:
                validated.append((zh, clean_translation(en), item_type, level))

        db.execute(
            """INSERT INTO analyses
               (sentence_id, english, processed_at, corrected_zh)
               VALUES (?,?,?,?)""",
            (result["id"], english, now, corrected_zh),
        )
        db.executemany(
            """INSERT OR IGNORE INTO alignments
               (sentence_id, zh, en, item_type, level) VALUES (?,?,?,?,?)""",
            [(result["id"], *item) for item in validated],
        )
        db.execute("UPDATE sentences SET status='processed' WHERE id=?", (result["id"],))
        applied += 1
    db.commit()
    return applied


def markdown_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def write_reports(db: sqlite3.Connection, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sentence_path = output_dir / "sentences.md"
    vocabulary_path = output_dir / "vocabulary.md"

    sentence_lines = [
        "# 句子翻译",
        "",
        "| 次数 | 原文 | 校正文 | 英文 |",
        "|---:|---|---|---|",
    ]
    for row in db.execute(
        """SELECT s.occurrence_count, s.representative,
                  COALESCE(a.corrected_zh, s.representative) AS corrected_zh,
                  a.english
           FROM sentences s JOIN analyses a ON a.sentence_id=s.id
           ORDER BY s.occurrence_count DESC, s.last_seen DESC"""
    ):
        sentence_lines.append(
            f"| {row['occurrence_count']} | {markdown_cell(row['representative'])} | "
            f"{markdown_cell(row['corrected_zh'])} | {markdown_cell(row['english'])} |"
        )
    sentence_path.write_text("\n".join(sentence_lines) + "\n", encoding="utf-8")

    aggregates: dict[str, dict[str, object]] = {}
    for row in db.execute(
        """SELECT al.zh, al.en, al.item_type, al.level,
                  s.occurrence_count,
                  COALESCE(a.corrected_zh, s.representative) AS representative
           FROM alignments al
           JOIN sentences s ON s.id=al.sentence_id
           JOIN analyses a ON a.sentence_id=s.id"""
    ):
        entry = aggregates.setdefault(
            row["zh"],
            {"type": row["item_type"], "senses": {}, "example": row["representative"]},
        )
        senses = entry["senses"]
        senses[row["en"]] = senses.get(row["en"], 0) + row["occurrence_count"]

    vocabulary_lines = [
        "# 个人英语词汇",
        "",
        "| 中文 | 类型 | 英文 | 次数 | 例句 |",
        "|---|---|---|---:|---|",
    ]
    ranked = []
    for zh, entry in aggregates.items():
        senses = sorted(entry["senses"].items(), key=lambda item: (-item[1], item[0]))[:2]
        ranked.append((sum(count for _, count in senses), zh, entry, senses))
    for total, zh, entry, senses in sorted(ranked, key=lambda item: (-item[0], item[1])):
        english = " / ".join(en for en, _ in senses)
        vocabulary_lines.append(
            f"| {markdown_cell(zh)} | {entry['type']} | {markdown_cell(english)} | "
            f"{total} | {markdown_cell(entry['example'])} |"
        )
    vocabulary_path.write_text("\n".join(vocabulary_lines) + "\n", encoding="utf-8")
    return sentence_path, vocabulary_path


def publish(db: sqlite3.Connection, output_path: Path, backup_dir: Path) -> int:
    backup_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        backup = backup_dir / (
            f"personal_translate-{time.strftime('%Y%m%d-%H%M%S')}.tsv"
        )
        shutil.copy2(output_path, backup)

    rows = db.execute(
        """SELECT al.zh, al.en, SUM(s.occurrence_count) AS weight
           FROM alignments al JOIN sentences s ON s.id=al.sentence_id
           GROUP BY al.zh, al.en ORDER BY al.zh, weight DESC, al.en"""
    ).fetchall()
    grouped: dict[str, list[str]] = {}
    for row in rows:
        values = grouped.setdefault(row["zh"], [])
        if row["en"] not in values and len(values) < 2:
            values.append(row["en"])

    now = int(time.time())
    lines = [f"#rev={now}"]
    for zh in sorted(grouped):
        values = [value.replace("|", " / ") for value in grouped[zh]]
        lines.append(f"{zh}\t{'|'.join(values)}")
    temporary = output_path.with_name(output_path.name + ".tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(temporary, output_path)
    return len(grouped)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest")
    pending_parser = sub.add_parser("pending")
    pending_parser.add_argument("--limit", type=int, default=100)
    ignore_parser = sub.add_parser("ignore")
    ignore_parser.add_argument("ids", type=int, nargs="+")
    apply_parser = sub.add_parser("apply-results")
    apply_parser.add_argument("result", type=Path)
    report_parser = sub.add_parser("report")
    report_parser.add_argument("--output", type=Path)
    publish_parser = sub.add_parser("publish")
    publish_parser.add_argument(
        "--rime-output", type=Path, default=DEFAULT_RIME_LEXICON
    )
    args = parser.parse_args()

    db_path = args.data_dir / "lexicon.sqlite3"
    log_path = args.data_dir / "sentences.tsv"
    db = db_connect(db_path)
    try:
        if args.command == "ingest":
            print(json.dumps(ingest(db, log_path), ensure_ascii=False))
        elif args.command == "pending":
            print(json.dumps(pending(db, args.limit), ensure_ascii=False, indent=2))
        elif args.command == "ignore":
            print(json.dumps({"ignored": ignore_sentences(db, args.ids)}))
        elif args.command == "apply-results":
            print(json.dumps({"applied": apply_results(db, args.result)}))
        elif args.command == "report":
            output = args.output or (args.data_dir / "reports")
            paths = write_reports(db, output)
            print(json.dumps({"reports": [str(path) for path in paths]}, ensure_ascii=False))
        elif args.command == "publish":
            count = publish(db, args.rime_output, args.data_dir / "backups")
            print(json.dumps({"published": count}, ensure_ascii=False))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
