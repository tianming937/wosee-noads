"""Verify released/local APKs. SDK checks are optional only with --no-sdk."""
from pathlib import Path
import argparse
import json
import re
import struct
import sys
import zipfile
from axml import ANDROID, BinaryXML
from common import (Toolchain, add_tool_args, require, require_normal_python,
                    run, sha256_bytes, sha256_file)
from dexpatch import DexFile
import policy


def verify_contents(path, original=None):
    """Check ZIP, manifest, code stubs, alignment; optionally compare original entries."""
    require_normal_python()
    path = Path(path)
    with zipfile.ZipFile(path) as apk, path.open("rb") as raw:
        names = apk.namelist()
        require(len(names) == len(set(names)) == policy.ENTRY_COUNT, "Unexpected/duplicate ZIP entries.")
        require(apk.testzip() is None, "ZIP CRC verification failed.")
        require(len([n for n in names if re.fullmatch(r"classes\d*\.dex", n)]) == 10, "Expected 10 dex files.")
        require(apk.getinfo("resources.arsc").compress_type == zipfile.ZIP_STORED, "resources.arsc must be uncompressed.")
        for info in apk.infolist():
            if info.compress_type != zipfile.ZIP_STORED or info.is_dir():
                continue
            raw.seek(info.header_offset + 26)
            name_size, extra_size = struct.unpack("<HH", raw.read(4))
            offset = info.header_offset + 30 + name_size + extra_size
            alignment = 16384 if info.filename.startswith("lib/") and info.filename.endswith(".so") else 4
            require(offset % alignment == 0, "Misaligned entry: " + info.filename)
        xml = BinaryXML(apk.read("AndroidManifest.xml"))
        require(xml.root.attrs.get("package") == policy.PACKAGE, "Unexpected package name.")
        require(xml.root.attrs.get(f"{{{ANDROID}}}versionName") == policy.VERSION, "Unexpected version name.")
        require(xml.root.attrs.get(f"{{{ANDROID}}}versionCode") == str(policy.VERSION_CODE), "Unexpected version code.")
        require(not any(n.tag in policy.COMPONENTS and n.name.startswith(policy.PREFIXES) for n in xml.nodes),
                "A targeted advertising component is still registered.")
        require(not any(n.tag in {"permission", "uses-permission"} and n.name in policy.AD_PERMISSIONS for n in xml.nodes),
                "A targeted advertising permission remains.")
        require(not any(n.tag == "meta-data" and n.name == policy.AD_METADATA for n in xml.nodes), "Advertising metadata remains.")
        activities = {n.name for n in xml.nodes if n.tag == "activity"}
        require({"com.ihomeiot.icam.feat.launch.LaunchActivity", "com.tg.login.activity.LoginActivity"} <= activities,
                "Launch or login activity is missing.")
        dex = DexFile(apk.read("classes8.dex"))
        for key in policy.TARGETS:
            require(key in dex.code, "Missing target method: " + key[1])
            off, _ = dex.code[key]
            size = dex.u32(off + 12)
            opcode = 0x11 if key[2].endswith(")Ljava/util/List;") else 0x0F
            expected = bytes((0x12, 0, opcode, 0)) + bytes(size * 2 - 4)
            require(dex.data[off + 16:off + 16 + size * 2] == expected, "Unexpected patched code: " + key[1])
        changed = None
        if original:
            require(sha256_file(original) == policy.SOURCE_SHA256, "Original APK SHA-256 does not match supported input.")
            with zipfile.ZipFile(original) as source:
                require(set(source.namelist()) == set(names), "ZIP entry set differs from original.")
                changed = sorted(n for n in names if sha256_bytes(source.read(n)) != sha256_bytes(apk.read(n)))
                require(changed == ["AndroidManifest.xml", "classes8.dex"], "Unexpected file changes: " + repr(changed))
    return {"file": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size,
            "package": policy.PACKAGE, "version_name": policy.VERSION, "version_code": policy.VERSION_CODE,
            "zip_crc": True, "alignment": True, "targeted_components_absent": True,
            "patched_methods_verified": len(policy.TARGETS), "original_compared": bool(original),
            "changed_entries": changed}


def verify_sdk(path, tools):
    output = run(tools.signer + ["verify", "--verbose", "--print-certs", path])
    require("Verified using v2 scheme (APK Signature Scheme v2): true" in output, "v2 signature check failed.")
    require("Verified using v3 scheme (APK Signature Scheme v3): true" in output, "v3 signature check failed.")
    match = re.search(r"Signer #1 certificate SHA-256 digest: ([0-9a-f]{64})", output)
    require(match, "Missing signer certificate digest.")
    run([tools.zipalign, "-c", "-P", "16", "4", path])
    badging = run([tools.aapt2, "dump", "badging", path])
    require(f"name='{policy.PACKAGE}'" in badging and "minSdkVersion:'24'" in badging, "aapt2 package check failed.")
    run([tools.aapt2, "dump", "xmltree", path, "--file", "AndroidManifest.xml"])
    return {"v2_signature": True, "v3_signature": True, "aapt2_parse": True, "certificate_sha256": match.group(1)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--original", type=Path, help="Optional exact original APK for full content comparison.")
    parser.add_argument("--published-release", action="store_true", help="Also require the published APK hash and signing certificate.")
    parser.add_argument("--no-sdk", action="store_true", help="ZIP/code/hash checks only; does NOT verify Android signatures.")
    parser.add_argument("--report", type=Path)
    add_tool_args(parser)
    args = parser.parse_args()
    try:
        if args.published_release:
            # Authenticate the expected artifact BEFORE decompressing/parsing it.
            require(args.apk.is_file() and args.apk.stat().st_size == policy.RELEASE_BYTES,
                    "Not the published release APK (size mismatch).")
            require(sha256_file(args.apk) == policy.RELEASE_SHA256,
                    "Not the published release APK (SHA-256 mismatch).")
        report = verify_contents(args.apk, args.original)
        if args.published_release:
            require(report["sha256"] == policy.RELEASE_SHA256 and report["bytes"] == policy.RELEASE_BYTES,
                    "Not the published release APK (hash/size mismatch).")
        if not args.no_sdk:
            tools = Toolchain.discover(args.android_sdk, args.build_tools, args.java_home)
            report.update(verify_sdk(args.apk, tools))
            if args.published_release:
                require(report["certificate_sha256"] == policy.RELEASE_CERT_SHA256, "Release signing certificate mismatch.")
        else:
            report["signature_verification"] = "not performed (--no-sdk)"
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, AssertionError, OSError, RuntimeError, KeyError, zipfile.BadZipFile) as exc:
        print("Verification failed: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
