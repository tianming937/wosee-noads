"""Build the version-locked Wosee patch using your own original APK and signing key."""
from collections import Counter
from pathlib import Path
import argparse
import copy
import getpass
import json
import os
import re
import secrets
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from axml import ANDROID, BinaryXML
from common import (Toolchain, add_tool_args, require, require_normal_python,
                    run, sha256_file)
from dexpatch import DexFile
from verify import verify_contents, verify_sdk
import policy

ROOT = Path(__file__).resolve().parent


def supported_input(path):
    require(Path(path).is_file(), "Original APK not found. Supply your own Wosee 3.53.4 APK with --input.")
    require(sha256_file(path) == policy.SOURCE_SHA256,
            "Unsupported original APK. Only SHA-256 " + policy.SOURCE_SHA256 + " is supported; no files were patched.")


def selected_nodes(xml):
    candidates = [n for n in xml.nodes if
                  (n.tag in policy.COMPONENTS and n.name.startswith(policy.PREFIXES)) or
                  (n.tag in {"permission", "uses-permission"} and n.name in policy.AD_PERMISSIONS) or
                  (n.tag == "meta-data" and n.name == policy.AD_METADATA)]
    ids = {id(n) for n in candidates}
    def selected_ancestor(node):
        node = node.parent
        while node is not None:
            if id(node) in ids:
                return True
            node = node.parent
        return False
    return [n for n in candidates if not selected_ancestor(n)]


def prune(element, selected):
    for child in list(element):
        if (child.tag, child.get(f"{{{ANDROID}}}name", "")) in selected:
            element.remove(child)
        else:
            prune(child, selected)


def patch_payloads(original):
    xml = BinaryXML(original.read("AndroidManifest.xml"))
    remove = selected_nodes(xml)
    require(dict(Counter(n.tag for n in remove)) == policy.EXPECTED_REMOVALS, "Unexpected component removal counts.")
    manifest = xml.remove(remove)
    expected = xml.root.element()
    prune(expected, {(n.tag, n.name) for n in remove})
    require(ET.tostring(expected) == ET.tostring(BinaryXML(manifest).root.element()), "Retained manifest content changed.")
    dex, changes = DexFile(original.read("classes8.dex")).return_zero(policy.TARGETS)
    return {"AndroidManifest.xml": manifest, "classes8.dex": dex}, remove, changes


def prepare_key(args, tools):
    """Keep generated keys/passwords locally; never print password values."""
    local = ROOT / ".local" / "keys"
    custom_key = args.keystore is not None
    keystore = args.keystore.expanduser().resolve() if custom_key else local / "wosee-noads.p12"
    password = os.environ.get(args.password_env)
    if not password and custom_key:
        require(keystore.is_file(), "Custom keystore does not exist.")
        require(sys.stdin.isatty(), "Set the named password environment variable for a custom keystore.")
        password = getpass.getpass("Keystore password: ")
    elif not password:
        local.mkdir(parents=True, exist_ok=True)
        password_file = local / "keystore.password"
        require(not keystore.exists() or password_file.exists(), "Keystore exists but its password file is missing.")
        if password_file.exists():
            password = password_file.read_text(encoding="utf-8").strip()
        else:
            password = secrets.token_urlsafe(32)
            password_file.write_text(password + "\n", encoding="utf-8")
            if os.name != "nt":
                password_file.chmod(0o600)
    require(password, "Empty keystore passwords are not supported.")
    env = os.environ.copy()
    env["WOSEE_INTERNAL_KEY_PASSWORD"] = password
    if not keystore.exists():
        require(tools.keytool.is_file(), "JDK keytool is missing; use a full JDK or supply --keystore.")
        keystore.parent.mkdir(parents=True, exist_ok=True)
        run([tools.keytool, "-genkeypair", "-keystore", keystore, "-storetype", "PKCS12",
             "-alias", args.key_alias, "-keyalg", "RSA", "-keysize", "3072", "-validity", "10000",
             "-dname", "CN=Wosee Local Modification,O=Local,C=CN",
             "-storepass:env", "WOSEE_INTERNAL_KEY_PASSWORD", "-keypass:env", "WOSEE_INTERNAL_KEY_PASSWORD"], env=env)
    return keystore, env


def build(args):
    require_normal_python()
    source = args.input.expanduser().resolve()
    supported_input(source)  # fail closed BEFORE creating a key or output
    output = args.output.expanduser().resolve()
    require(output != source, "Output must not overwrite the original APK.")
    require(args.overwrite or not output.exists(), "Output exists; choose another path or pass --overwrite.")
    tools = Toolchain.discover(args.android_sdk, args.build_tools, args.java_home)
    keystore, env = prepare_key(args, tools)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wosee-build-", dir=output.parent) as folder:
        work = Path(folder).resolve()
        require(work.parent == output.parent, "Temporary build directory escaped output directory.")
        unsigned, aligned, signed = (work / n for n in ("unsigned.apk", "aligned.apk", "signed.apk"))
        with zipfile.ZipFile(source) as original:
            replacements, removed, changes = patch_payloads(original)
            with zipfile.ZipFile(unsigned, "w", allowZip64=True) as target:
                target.comment = original.comment
                for entry in original.infolist():
                    if re.match(r"META-INF/(?:[^/]+\.(?:SF|RSA|DSA|EC)|MANIFEST\.MF)$", entry.filename, re.I):
                        continue
                    data = replacements[entry.filename] if entry.filename in replacements else original.read(entry)
                    target.writestr(copy.copy(entry), data)
        run([tools.zipalign, "-P", "16", "-f", "4", unsigned, aligned])
        run(tools.signer + ["sign", "--ks", keystore, "--ks-key-alias", args.key_alias,
                           "--ks-pass", "env:WOSEE_INTERNAL_KEY_PASSWORD", "--key-pass", "env:WOSEE_INTERNAL_KEY_PASSWORD",
                           "--min-sdk-version", "24", "--v1-signing-enabled", "false", "--v2-signing-enabled", "true",
                           "--v3-signing-enabled", "true", "--v4-signing-enabled", "false", "--out", signed, aligned], env=env)
        report = verify_contents(signed, source)
        report.update(verify_sdk(signed, tools))
        report.update({"file": output.name, "source_sha256": policy.SOURCE_SHA256,
                       "removed_declarations": len(removed), "removed_by_tag": dict(Counter(n.tag for n in removed)),
                       "dex_changes": changes, "runtime_test": "not performed by build script"})
        require(sha256_file(source) == policy.SOURCE_SHA256, "Original APK changed during build.")
        os.replace(signed, output)  # only publish a completely verified output
    output.with_suffix(".verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".sha256").write_text(report["sha256"] + "  " + output.name + "\n", encoding="ascii")
    print("Build and verification passed: " + str(output))
    print("SHA-256: " + report["sha256"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / policy.APK_FILENAME)
    parser.add_argument("--keystore", type=Path, help="Existing private keystore. Omit to generate a local key.")
    parser.add_argument("--key-alias", default="wosee-noads")
    parser.add_argument("--password-env", default="WOSEE_KEYSTORE_PASSWORD", help="Name of an environment variable; never a password value.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output only after all checks pass.")
    add_tool_args(parser)
    args = parser.parse_args()
    try:
        build(args)
        return 0
    except (ValueError, AssertionError, OSError, RuntimeError, KeyError, zipfile.BadZipFile) as exc:
        print("Build failed: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
