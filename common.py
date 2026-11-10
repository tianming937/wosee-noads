"""Standard-library helpers; no machine-specific paths or bundled credentials."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
import re
import shutil
import subprocess
import sys


def require(condition, message):
    if not condition:
        raise ValueError(message)


def require_normal_python():
    require(not sys.flags.optimize, "Do not run with python -O: binary parser assertions are required.")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def run(args, *, env=None):
    result = subprocess.run([str(x) for x in args], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=180, env=env)
    output = result.stdout.decode("utf-8", "replace")
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} failed ({result.returncode}):\n{output}")
    return output


@dataclass
class Toolchain:
    java: Path
    keytool: Path
    tools: Path

    @property
    def signer(self):
        return [self.java, "-jar", self.tools / "lib" / "apksigner.jar"]

    @property
    def zipalign(self):
        return self.tools / ("zipalign.exe" if os.name == "nt" else "zipalign")

    @property
    def aapt2(self):
        return self.tools / ("aapt2.exe" if os.name == "nt" else "aapt2")

    @classmethod
    def discover(cls, android_sdk=None, build_tools=None, java_home=None):
        java_home = java_home or os.environ.get("JAVA_HOME")
        suffix = ".exe" if os.name == "nt" else ""
        java = Path(java_home) / "bin" / ("java" + suffix) if java_home else shutil.which("java")
        require(java and Path(java).is_file(), "Java not found. Set JAVA_HOME or --java-home (JDK 17+).")
        java = Path(java).resolve()
        keytool = java.with_name("keytool" + suffix)
        if not keytool.is_file():
            keytool = Path(shutil.which("keytool") or "__missing_keytool__")
        if build_tools:
            tools = Path(build_tools).expanduser().resolve()
        else:
            sdk = android_sdk or os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
            require(sdk, "Set ANDROID_SDK_ROOT or --android-sdk, or pass --build-tools.")
            folder = Path(sdk).expanduser() / "build-tools"
            versions = [p for p in folder.glob("*") if p.is_dir() and re.fullmatch(r"\d+\.\d+\.\d+", p.name)]
            require(versions, "No stable SDK Build Tools found. Install Build Tools 35.0.0 or newer.")
            tools = max(versions, key=lambda p: tuple(map(int, p.name.split(".")))).resolve()
        result = cls(java, keytool, tools)
        require((tools / "lib" / "apksigner.jar").is_file(), "Missing apksigner.jar in Build Tools.")
        require(result.zipalign.is_file() and result.aapt2.is_file(), "Missing zipalign or aapt2.")
        return result


def add_tool_args(parser):
    parser.add_argument("--android-sdk", type=Path, help="Android SDK root (or ANDROID_SDK_ROOT).")
    parser.add_argument("--build-tools", type=Path, help="Exact Build Tools directory, 35.0.0+.")
    parser.add_argument("--java-home", type=Path, help="JDK 17+ directory (or JAVA_HOME).")
