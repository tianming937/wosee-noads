# 安卓手机安装说明

## 直接下载 APK

[点击下载已签名 APK，约 108MB](https://github.com/tianming937/wosee-noads/releases/latest/download/wosee_3.53.4_noads_signed.apk)

若链接暂时无法打开，进入 [Release 页面](https://github.com/tianming937/wosee-noads/releases/latest)，展开 Assets，选择 **wosee_3.53.4_noads_signed.apk**。`Source code.zip` 是开发源码，不能当安卓 App 安装。

## 在手机上安装

下载完成后，在浏览器下载列表或手机文件管理器中点开 APK。Android 若询问是否允许该浏览器/文件管理器安装应用，按需允许这个来源，然后返回安装界面确认。

这个步骤必须由手机使用者确认。项目不会绕过 Android 的安装授权，也不要求关闭系统防护。遇到系统阻止时，先记录准确提示，勿按网上不明命令修改系统设置。

若手机已有官方版，两个版本签名不同，不能覆盖安装。先备份需要保留的本地内容，确认知道自己的登录方式，再自行卸载官方版、安装本包。卸载会清除应用本地数据；此项目不提供自动迁移账号或数据的功能。

安装后登录自己的账号，检查摄像头连接、监控画面和通知。不要将仅到登录页的历史验证当成所有设备都能使用的保证。

## 常见情况

| 提示/现象 | 处理 |
| --- | --- |
| “应用未安装”“与现有软件包冲突” | 检查是否还有官方版或其他签名版本，包括应用分身；不要自动删除分身的数据 |
| 文件下载后无法打开 | 确认下载的是 `.apk`，大小为 113,104,788 字节，重新下载排除损坏 |
| CPU 不兼容 | 包含 arm64-v8a 和 armeabi-v7a 原生库；普通安装目标为 ARM 安卓设备 |
| 账号、推送或摄像头异常 | 提交手机型号、系统版本和操作步骤；这类功能尚未完成全面验证 |
| 还有广告 | 记录具体页面、触发步骤和应用版本，勿把摄像头私人画面直接公开 |

本包最低 Android API 24（Android 7.0），原应用目标 API 35。不是 iOS、Windows 或电视通用安装包。

## 核对下载文件

文件 SHA-256：

```text
59647098a860c93659d255b798ec372f06224f95b23811bbec01ac860951c6fe
```

Windows 可在 PowerShell 中运行 `Get-FileHash .\wosee_3.53.4_noads_signed.apk -Algorithm SHA256`。Release 同时提供 `SHA256SUMS.txt` 和 `release-manifest.json`。
