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
3. 下载 `XiangXiangInput-0.1.7-user` artifact。
4. 保持解压后的文件夹完整，双击 `Install XiangXiangInput.command`。

当前产物是无签名测试版，安装到 `~/Library/Input Methods/`，不需管理员密码。
安装器不覆盖现有配置；如果已有旧 App，会先移到 `~/Library/XiangXiangInput/Backups/`。
公开发布前仍需增加 Apple Developer ID 签名和公证。

## 句子库

- 实时数据唯一保存在 `~/Library/Application Support/personal-english-lexicon/`。
- 向向输入法的记录器直接使用这个本地目录，不维护第二份可分叉数据库。
- 现有 Rime 个人词库只在向向目录缺失时复制，不会覆盖。

## 上游与许可证

构建时从 `rime/squirrel` 的 `master` 分支拉取源码。Squirrel 使用 GPL-3.0，本项目同样使用 GPL-3.0，并保留上游版权和许可证文件。
