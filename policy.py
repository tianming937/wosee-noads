"""Patch policy for ONE known Wosee 3.53.4 APK, not a generic APK modifier."""
PACKAGE = "com.tange365.wosee"
VERSION = "3.53.4"
VERSION_CODE = 271
SOURCE_SHA256 = "e3af142bce99fc71b8e64e2568333f689aeca9e10f16c562a6cd5b5731dc0d7f"
APK_FILENAME = "wosee_3.53.4_noads_signed.apk"
RELEASE_SHA256 = "59647098a860c93659d255b798ec372f06224f95b23811bbec01ac860951c6fe"
RELEASE_BYTES = 113104788
RELEASE_CERT_SHA256 = "0a93f47be534be7e5fdca3a43a76767dce5b810641756d5eea41f90823bec193"
ENTRY_COUNT = 7611
COMPONENTS = {"activity", "activity-alias", "provider", "service", "receiver"}
PREFIXES = (
    "com.bytedance.", "com.byted.live.", "com.ss.android.downloadlib.",
    "com.ss.android.socialbase.", "com.baidu.mobads.", "com.qq.e.",
    "com.kwad.", "com.jd.ad.", "com.anythink.", "com.beizi.ad.",
    "com.octopus.ad.", "com.alimm.tanx.", "com.wangmai.appsdkdex.",
    "com.insightvision.openadsdk.", "com.ptg.", "com.qumeng.advlib.",
    "com.leyou.fusionsdk.", "com.ubix.", "com.ubixnow.", "cn.haorui.sdk.",
    "cn.vlion.ad.", "com.mcto.sspsdk.", "com.qy.sdk.", "com.tramini.",
)
AD_PERMISSIONS = {
    "com.google.android.gms.permission.AD_ID",
    "com.tange365.wosee.openadsdk.permission.TT_PANGOLIN",
}
AD_METADATA = "com.huawei.hms.client.service.name:ads-identifier"
BASE = "Lcom/tg/icam/core/feat/advert/"
TARGETS = (
    (BASE + "AdvertManager;", "getAdvertEnable", "()Z"),
    (BASE + "AdvertManager;", "getLocalEnable", "()Z"),
    (BASE + "AdvertManager;", "getServerEnable", "()Z"),
    (BASE + "AdvertManager;", "getPlatforms", "()Ljava/util/List;"),
    (BASE + "AdGlobalConfig;", "getAdSwitch", "()I"),
    (BASE + "AdGlobalConfig;", "isAdSwitch", "(Ljava/lang/String;)Z"),
    (BASE + "AdGlobalConfig;", "isBackupAdSwitch", "()Z"),
    (BASE + "AdGlobalConfig;", "isServerEnable", "()Z"),
)
EXPECTED_REMOVALS = {
    "activity": 179, "provider": 31, "service": 21, "receiver": 3,
    "uses-permission": 2, "permission": 1, "meta-data": 1,
}
