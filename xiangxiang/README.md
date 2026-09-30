# 向向输入法构建

本目录保存最小化的品牌补丁和 GitHub Actions 构建配置，不复制 Squirrel 源码。

## 当前身份

- 系统显示名：`向向输入法`
- App：`XiangXiangInput.app`
- Bundle ID：`com.xiangxiang.inputmethod.XiangXiangInput`
- 用户数据：`~/Library/XiangXiangInput/`
- 初始输入方案：`朙月拼音·简化字`
- 候选词英文：仅使用用户的 `personal_translate.tsv`
- 记录：中文及鼠鬚管内部英文模式的混合句子

## 构建

1. 将整个项目推送到 GitHub。
2. 打开 **Actions → Build XiangXiang Input → Run workflow**。
3. 下载 `XiangXiangInput-unsigned` artifact。

当前产物是无签名测试包，仅用于开发验证。公开发布前需增加 Apple Developer ID 签名和公证。

## 上游与许可证

构建时从 `rime/squirrel` 的 `master` 分支拉取源码。Squirrel 使用 GPL-3.0，本项目同样使用 GPL-3.0，并保留上游版权和许可证文件。
