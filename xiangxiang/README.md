# 向向输入法构建

本目录保存最小化的品牌补丁和 GitHub Actions 构建配置，不复制 Squirrel 源码。

## 当前身份

- 系统显示名：`向向输入法`
- App：`XiangXiangInput.app`
- Bundle ID：`com.xiangxiang.inputmethod.XiangXiangInput`
- 用户数据：`~/Library/XiangXiangInput/`
- 初始输入方案：`朙月拼音·简化字`
- 候选词英文：个人词库优先，导入词库后备
- 记录：中文及鼠鬚管内部英文模式的混合句子

## 构建

1. 将整个项目推送到 GitHub。
2. 打开 **Actions → Build XiangXiang Input → Run workflow**。
3. 下载 `XiangXiangInput-0.1.10-user` artifact。
4. 保持解压后的文件夹完整，双击 `Install XiangXiangInput.command`。

当前产物是无签名测试版，安装到 `~/Library/Input Methods/`，不需管理员密码。
安装器不覆盖现有 YAML 配置；如果已有旧 App，会先移到 `~/Library/XiangXiangInput/Backups/`。更新本项目管理的两个 Lua 模块前，也会备份旧文件。
公开发布前仍需增加 Apple Developer ID 签名和公证。

## 句子库

- 实时数据唯一保存在 `~/Library/Application Support/personal-english-lexicon/`。
- 向向输入法的记录器直接使用这个本地目录，不维护第二份可分叉数据库。
- 现有 Rime 个人词库只在向向目录缺失时复制，不会覆盖。

## 输入法菜单

选中向向输入法后，菜单提供四个本地入口：打开原始句子记录、句子翻译报告、个人词库报告，以及上传词库。句子校对翻译仍可在 Codex 中主动运行 `personal-english-lexicon` skill；输入法菜单不会启动它。

## 导入自己的词库

在输入法菜单点击“上传词库”，独立的本地图形导入工具会让你选择 UTF-8 编码的 CSV 或 TSV 文件，不需要打开终端。也可以手动双击 `~/Library/XiangXiangInput/Tools/导入词库.command`。可以复制旁边的 `词库模板.csv` 填写；文件需要表头，例如：

```csv
中文,英文
项目进度,project progress
学习,study|learn
```

英语词表也可以用 `word,translation` 两列，例如 `apple,苹果`。中文一栏用 `；` 分隔的多个释义会分别建立词条。雅思、四六级词库由用户自行提供，本项目不附带第三方词表。

导入的词库会立即加入本地候选词释义；已有个人词库优先，每个候选最多显示两个英文释义。导入前会备份原文件。导入只增加候选词旁的英文注释，不改变拼音候选词本身。

## 上游与许可证

构建时从 `rime/squirrel` 的 `master` 分支拉取源码。Squirrel 使用 GPL-3.0，本项目同样使用 GPL-3.0，并保留上游版权和许可证文件。
