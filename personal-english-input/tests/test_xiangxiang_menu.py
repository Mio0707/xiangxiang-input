import tempfile
import unittest
from pathlib import Path

from xiangxiang.brand_upstream import patch_menu


class XiangXiangMenuTest(unittest.TestCase):
    def test_replaces_upstream_maintenance_menu(self):
        source = '''final class SquirrelInputController {
  override func menu() -> NSMenu! {
    let menu = NSMenu()
    menu.addItem(NSMenuItem(title: "Deploy", action: nil, keyEquivalent: ""))
    return menu
  }
  @objc func deploy() {}
  private(set) var specialCommentIndices: [Int: Set<Int>] = [:]
}
'''
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "SquirrelInputController.swift"
            path.write_text(source, encoding="utf-8")
            patch_menu(path)
            output = path.read_text(encoding="utf-8")
        for title in (
            "打开本地记录的句子", "打开句子翻译", "打开词库", "上传词库",
        ):
            self.assertIn(title, output)
        self.assertNotIn("使用 Skill 校对并翻译句子", output)
        self.assertIn('Tools/XiangXiangDictionaryImporter.app', output)
        self.assertNotIn('Tools/导入词库.command', output)
        self.assertNotIn('title: "Deploy"', output)
        self.assertIn("private(set) var specialCommentIndices:", output)


if __name__ == "__main__":
    unittest.main()
