# 向向输入法

基于 Rime / Squirrel 的 macOS 本地优先输入法实验项目。

当前目标：

- 中文候选词旁仅显示个人英语词库的翻译。
- 按回车后在本地记录完整句子。
- 支持鼠鬚管内部中英文模式的混合输入记录。
- 由用户主动运行工作流，生成口语化句子翻译和个人词库。
- 不在打字路径上调用云端翻译。

## 构建

GitHub Actions 会拉取官方 Squirrel 源码，应用“向向输入法”品牌补丁，生成支持 Apple Silicon 和 Intel Mac 的无签名测试包。

详见 [构建说明](xiangxiang/README.md) 和 [个人英语词库原型](personal-english-input/README.md)。

## 隐私

仓库不包含用户输入的句子、数据库或个人词库。这些数据默认仅保存在本机。

## 许可证

本项目使用 [GPL-3.0](personal-english-input/LICENSE)。Squirrel 及其依赖仍遵循各自的上游许可证。
