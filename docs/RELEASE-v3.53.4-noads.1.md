# Wosee 3.53.4 去广告实验版

## 直接下载安装

[点击下载 APK（约 108MB）](https://github.com/tianming937/wosee-noads/releases/download/v3.53.4-noads.1/wosee_3.53.4_noads_signed.apk)

普通用户选择 Assets 中的 **wosee_3.53.4_noads_signed.apk**，不是 Source code.zip。下载到安卓手机后点开 APK，按系统提示确认安装。

如果已经安装官方版，签名不同无法覆盖；请先备份需要的本地数据并自行卸载旧版。卸载会清除应用本地数据。

## 这次提供什么

- 已签名的 Wosee 3.53.4（271）修改 APK，包名 com.tange365.wosee。
- 关闭广告管理开关和广告平台创建入口；移除 234 个广告组件声明，共 238 项声明。
- MIT 授权的补丁/校验工具源码，以及安装指南和校验记录。第三方 APK 内容不受该 MIT 许可证覆盖。
- SHA256SUMS.txt 与公开的 release-manifest.json，方便核对下载文件。

APK 的 SHA-256：

```text
59647098a860c93659d255b798ec372f06224f95b23811bbec01ac860951c6fe
```

## 验证范围

2026-10-24 已在 MuMu（Android API 32）及三星 SM-S9180（Android API 36）安装并启动到登录界面；模拟器两次冷启动通过。2026-11-10 重新通过发布文件哈希、ZIP、对齐、Manifest、8 个修改方法和 v2/v3 签名检查。

原始 APK 当前缺失，本次未重新构建，发布的是与历史测试哈希相同的成品。账号登录后的监控、推送、第三方登录和各广告位尚未完整实测，这是实验版。没有承诺所有广告完全消失或所有设备可用。

没有附带私钥、密码、手机日志或原厂 SDK 工具。自行构建需要自己的匹配原包、Python、JDK 和 Android SDK。
