import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/personal-english-lexicon/scripts/lexicon_store.py"


class LexiconStoreTest(unittest.TestCase):
    def run_cli(self, data_dir, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--data-dir", str(data_dir), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def test_ingest_apply_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / "sentences.tsv").write_text(
                "100\t我们需要确认项目近度\n"
                "101\t我们需要确认项目近度\n"
                "102\t好的\n",
                encoding="utf-8",
            )
            stats = json.loads(self.run_cli(data, "ingest"))
            self.assertEqual(stats["new_events"], 3)
            self.assertEqual(stats["new_sentences"], 2)

            rows = json.loads(self.run_cli(data, "pending"))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["occurrence_count"], 2)

            result = data / "results.json"
            result.write_text(
                json.dumps([
                    {
                        "id": rows[0]["id"],
                        "zh": rows[0]["zh"],
                        "corrected_zh": "我们需要确认项目进度",
                        "en": "We need to check the project progress.",
                        "items": [
                            {
                                "zh": "项目进度",
                                "en": ["project progress"],
                                "type": "phrase",
                                "level": "B1",
                                "keep": True,
                            },
                            {
                                "zh": "我们",
                                "en": ["we"],
                                "type": "word",
                                "level": "A1",
                                "keep": True,
                            },
                        ],
                    }
                ], ensure_ascii=False),
                encoding="utf-8",
            )
            applied = json.loads(self.run_cli(data, "apply-results", str(result)))
            self.assertEqual(applied["applied"], 1)

            report_dir = data / "reports"
            self.run_cli(data, "report", "--output", str(report_dir))
            sentences = (report_dir / "sentences.md").read_text(encoding="utf-8")
            vocabulary = (report_dir / "vocabulary.md").read_text(encoding="utf-8")
            self.assertIn("我们需要确认项目近度", sentences)
            self.assertIn("我们需要确认项目进度", sentences)
            self.assertIn("project progress", vocabulary)
            self.assertNotIn("| 我们 |", vocabulary)

            rime_lexicon = data / "personal_translate.tsv"
            published = json.loads(
                self.run_cli(
                    data, "publish", "--rime-output", str(rime_lexicon)
                )
            )
            self.assertEqual(published["published"], 1)
            lexicon_text = rime_lexicon.read_text(encoding="utf-8")
            self.assertRegex(lexicon_text.splitlines()[0], r"^#rev=\d+$")
            self.assertIn("项目进度\tproject progress", lexicon_text)
            self.assertNotIn("我们\t", lexicon_text)

            db = sqlite3.connect(data / "lexicon.sqlite3")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events").fetchone()[0], 3)
            db.close()


if __name__ == "__main__":
    unittest.main()
