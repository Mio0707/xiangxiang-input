import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "xiangxiang"))
from dictionary_import import import_dictionary, read_normalized  # noqa: E402


class DictionaryImportTest(unittest.TestCase):
    def test_imports_both_directions_without_touching_personal_lexicon(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            user_dir = root / "XiangXiangInput"
            user_dir.mkdir()
            personal = user_dir / "personal_translate.tsv"
            personal.write_text("#rev=1\n学习\tmy preferred word\n", encoding="utf-8")

            cet = root / "四六级.csv"
            cet.write_text(
                "word,translation\n"
                "study,学习；研究\n"
                "learn,学习\n"
                "memorize,学习\n"
                "invalid,no Chinese here\n",
                encoding="utf-8",
            )
            first = import_dictionary(cet, user_dir)
            self.assertEqual(first["entries"], 2)
            self.assertEqual(first["skipped"], 1)
            self.assertEqual(read_normalized(user_dir / "imported_translate.tsv")["学习"], ["study", "learn"])

            ielts = root / "雅思.tsv"
            ielts.write_text("中文\t英文\n项目进度\tproject progress\n学习\tstudy|practice\n", encoding="utf-8")
            second = import_dictionary(ielts, user_dir)
            self.assertEqual(second["active_entries"], 3)
            self.assertEqual(read_normalized(user_dir / "imported_translate.tsv")["项目进度"], ["project progress"])
            self.assertEqual(personal.read_text(encoding="utf-8"), "#rev=1\n学习\tmy preferred word\n")

            cet.write_text("word,translation\nrevise,复习\n", encoding="utf-8")
            import_dictionary(cet, user_dir)
            self.assertIn("复习", read_normalized(user_dir / "imported_translate.tsv"))
            self.assertNotIn("研究", read_normalized(user_dir / "imported_translate.tsv"))
            backups = list((user_dir / "Backups/ImportedDictionaries").glob("*.tsv"))
            self.assertGreaterEqual(len(backups), 2)

    def test_invalid_file_does_not_change_existing_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            user_dir = root / "XiangXiangInput"
            good = root / "good.csv"
            good.write_text("中文,英文\n电脑,computer\n", encoding="utf-8")
            import_dictionary(good, user_dir)
            before = (user_dir / "imported_translate.tsv").read_text(encoding="utf-8")
            bad = root / "bad.csv"
            bad.write_text("term,answer\n电脑,computer\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                import_dictionary(bad, user_dir)
            self.assertEqual((user_dir / "imported_translate.tsv").read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
