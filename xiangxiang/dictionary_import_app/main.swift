import AppKit
import UniformTypeIdentifiers

final class DictionaryImportDelegate: NSObject, NSApplicationDelegate {
  func applicationDidFinishLaunching(_ notification: Notification) {
    NSApplication.shared.activate(ignoringOtherApps: true)
    DispatchQueue.main.async { self.chooseAndImport() }
  }

  private func chooseAndImport() {
    let panel = NSOpenPanel()
    panel.title = "上传词库"
    panel.message = "选择 UTF-8 编码、包含中文和英文表头的 CSV 或 TSV 文件"
    panel.allowedContentTypes = [.commaSeparatedText, .tabSeparatedText]
    panel.allowsMultipleSelection = false
    panel.canChooseDirectories = false
    guard panel.runModal() == .OK, let selectedFile = panel.url else {
      NSApplication.shared.terminate(nil)
      return
    }

    let importer = Bundle.main.bundleURL.deletingLastPathComponent()
      .appendingPathComponent("dictionary_import.py")
    let task = Process()
    task.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
    task.arguments = [importer.path, selectedFile.path]
    let output = Pipe()
    task.standardOutput = output
    task.standardError = output

    var message: String
    var succeeded = false
    do {
      try task.run()
      let data = output.fileHandleForReading.readDataToEndOfFile()
      task.waitUntilExit()
      message = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines)
        ?? "无法读取导入结果。"
      succeeded = task.terminationStatus == 0
    } catch {
      message = error.localizedDescription
    }

    let alert = NSAlert()
    alert.messageText = succeeded ? "词库导入成功" : "词库导入失败"
    alert.informativeText = message
    alert.alertStyle = succeeded ? .informational : .warning
    alert.runModal()
    NSApplication.shared.terminate(nil)
  }
}

let app = NSApplication.shared
let delegate = DictionaryImportDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
