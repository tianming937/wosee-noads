# Wosee 去广告实验版

关闭 **Wosee 3.53.4** 广告相关调用的开源补丁工具，附已签名 APK。普通用户直接下载 APK，无需 Python、电脑、Root 或自行编译。

## 安卓手机直接下载

### [⬇️ 点击下载去广告 APK（约 108MB）](https://github.com/tianming937/wosee-noads/releases/latest/download/wosee_3.53.4_noads_signed.apk)

[备用：打开 Releases 下载页](https://github.com/tianming937/wosee-noads/releases/latest) · [安装图文说明](docs/INSTALL.md) · [文件校验记录](docs/VERIFICATION.md)

1. 用安卓手机打开上面的下载链接，下载以 **`.apk`** 结尾的文件。
2. 下载完成后点开文件，按照 Android 提示允许此次来源安装，再点击安装。
3. 打开 Wosee，登录自己的账号，检查摄像头连接和通知。

**已装官方版时：** 本包与官方版签名不同，不能直接覆盖。先备份需要保留的本地数据并确认账号可重新登录，再自行卸载官方版、安装本包。卸载会清除该应用的本地数据，本项目不会替你自动卸载。

下载链接直接指向 APK；安装仍需 Android 系统确认。无需下载 `Source code.zip`，也不要关闭手机系统防护来强行安装。

## 目前验证到了哪里

这是**实验版**，不保证所有设备、账号和广告位都已覆盖。

| 项目 | 已确认的结果 |
| --- | --- |
| 基础版本 | Wosee 3.53.4，版本号 271，包名 `com.tange365.wosee` |
| 修改 | 移除 234 个广告组件声明，连同权限和元数据共 238 项；修改 8 个广告管理方法 |
| 文件范围 | APK 内只有 `AndroidManifest.xml` 和 `classes8.dex` 的内容变化 |
| 签名与文件 | v2/v3 签名、ZIP CRC、对齐、包信息解析及方法检查通过 |
| 模拟器，2026-10-24 | MuMu / Android API 32，安装成功，两次冷启动到登录及隐私确认界面 |
| 真机，2026-10-24 | 三星 SM-S9180 / Android API 36，安装成功，启动到登录页 |
| 发布前复核，2026-11-10 | APK 哈希与原测试成品相同，重新通过静态、签名和结构检查 |
| 尚未完成 | 账号登录后的摄像头监控、推送、第三方登录和各页面广告效果的完整实测 |

补丁保留了大量原 SDK 代码和资源，APK 并未做体积瘦身；安装和首次启动通过，不等于已经验证全部监控功能。欢迎提交带版本、手机型号和复现步骤的问题反馈，请勿上传账号密码、设备二维码或私人监控画面。

## 为什么 APK 放在 Release

安装包为 113,104,788 字节，超过普通 Git 文件的大小限制，因此二进制放在本仓库 **Releases 附件**。仓库保存补丁源码、说明和校验清单，首页按钮直接下载真实 APK。

发布文件 SHA-256：

```text
59647098a860c93659d255b798ec372f06224f95b23811bbec01ac860951c6fe
```

完整签名证书指纹、大小和历史验证范围见 [release-manifest.json](release-manifest.json)。GitHub 关于大文件和 Release 的说明见 [官方文档](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)。

## 开发者：自己构建

需要 Python 3.10+、JDK 17+、Android SDK Build Tools 35.0.0+。Python 部分仅用标准库，无需 `pip install`。

自行准备**精确匹配**的原始 Wosee 3.53.4 APK。当前仅支持以下原包 SHA-256，其他版本会在修改前被拒绝：

```text
e3af142bce99fc71b8e64e2568333f689aeca9e10f16c562a6cd5b5731dc0d7f
```

```powershell
python build.py --input "C:\path\wosee_original.apk" --android-sdk "C:\path\Android\Sdk" --java-home "C:\path\jdk-17"
```

也可通过 `ANDROID_SDK_ROOT`、`JAVA_HOME` 指定工具路径。默认输出 `dist/wosee_3.53.4_noads_signed.apk`，以及同目录的校验报告和 SHA-256 文件。源码不再依赖作者的磁盘路径、用户名或 ADB 设备编号。

首次构建会在被 Git 忽略的 `.local/keys/` 生成**你自己的**签名密钥，后续更新需保留它。该密钥与本仓库 Release 使用的签名密钥不同。原作者的私钥和密码不公开。

需要使用已有密钥时，通过 `--keystore`、`--key-alias` 和 `--password-env` 指定；密码从环境变量或交互输入读取，**不要把密码写进命令参数或提交到仓库**。运行 `python build.py --help` 查看参数。

## 校验下载的 APK

完整校验（需要上述 SDK/JDK）：

```powershell
python verify.py "C:\path\wosee_3.53.4_noads_signed.apk" --published-release --android-sdk "C:\path\Android\Sdk" --java-home "C:\path\jdk-17"
```

只有 Python 时可运行 `python verify.py 文件路径 --published-release --no-sdk`。此模式检查发布哈希、ZIP、对齐、Manifest 和修改方法，**不执行 Android 签名验证**。

持有原包时添加 `--original 原包路径`，会逐项对比，要求仅两个预期条目的内容变化。不要使用 `python -O`；工具会拒绝关闭校验断言的运行方式。

## 源码和测试

| 文件 | 作用 |
| --- | --- |
| `build.py` | 校验原包、局部修改、封装、对齐、签名及成品检查 |
| `verify.py` | 检查发布 APK 或本地构建产物 |
| `policy.py` | 支持版本、原包哈希、组件前缀和 8 个方法的精确目标 |
| `axml.py` | 读取二进制 Manifest，删除完整节点块 |
| `dexpatch.py` | 保持方法长度及偏移，更新 DEX 校验值 |
| `tests/` | 核心二进制处理、错误输入和版本锁定的测试 |

```text
python -m unittest discover -s tests -v
```

构建过程不重新编译 `res` 或重新组装其他 dex，避免经过先前失败的资源构建步骤。详细实现和限制见 [技术说明](docs/TECHNICAL.md)。当前原始 APK 未随仓库分发，发布前没有重新从原包构建；发布的是已测试、哈希保持一致的既有成品。

## 许可证与第三方内容

本仓库自行编写的补丁和校验工具使用 [MIT License](LICENSE)。Wosee APK 及其中第三方 SDK 的原有权利归各自权利人，MIT 许可证不覆盖这些第三方内容，见 [NOTICE](NOTICE.md)。这是社区修改包，非 Wosee 官方发布。
