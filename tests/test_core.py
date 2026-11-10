"""Small synthetic fixtures; no third-party APK, credentials or phone required."""
from pathlib import Path
import hashlib
import struct
import tempfile
import unittest
import zlib
from axml import ANDROID, BinaryXML
from build import selected_nodes, supported_input
from dexpatch import DexFile


def uleb(value):
    out = bytearray()
    while True:
        b, value = value & 127, value >> 7
        out.append(b | (128 if value else 0))
        if not value:
            return bytes(out)


def fix_dex(data):
    data = bytearray(data)
    data[12:32] = hashlib.sha1(data[32:]).digest()
    struct.pack_into("<I", data, 8, zlib.adler32(data[12:]) & 0xFFFFFFFF)
    return bytes(data)


def sample_dex():
    strings = ["LExample;", "Ljava/lang/Object;", "I", "value"]
    data = bytearray(192)
    offsets = []
    for s in strings:
        offsets.append(len(data))
        data.extend(uleb(len(s)) + s.encode("utf-8") + b"\0")
    data.extend(bytes((-len(data)) % 4))
    code = len(data)
    data.extend(struct.pack("<HHHHII", 1, 0, 0, 0, 0, 3))
    data.extend(b"\x12\x10\x0f\x00\x00\x00")  # const/4 v0, 1; return v0; nop
    class_data = len(data)
    data.extend(bytes((0, 0, 1, 0, 0, 9)) + uleb(code))
    data[:8] = b"dex\n035\0"
    struct.pack_into("<III", data, 32, len(data), 112, 0x12345678)
    struct.pack_into("<II", data, 56, 4, 112)
    struct.pack_into("<II", data, 64, 3, 128)
    struct.pack_into("<II", data, 72, 1, 140)
    struct.pack_into("<II", data, 88, 1, 152)
    struct.pack_into("<II", data, 96, 1, 160)
    struct.pack_into("<II", data, 104, len(data) - 192, 192)
    for i, off in enumerate(offsets):
        struct.pack_into("<I", data, 112 + i * 4, off)
    struct.pack_into("<III", data, 128, 0, 1, 2)
    struct.pack_into("<III", data, 140, 2, 2, 0)
    struct.pack_into("<HHI", data, 152, 0, 0, 3)
    struct.pack_into("<8I", data, 160, 0, 1, 1, 0, 0xFFFFFFFF, 0, class_data, 0)
    return fix_dex(data)


def sample_manifest():
    strings = [ANDROID, "manifest", "package", "com.tange365.wosee", "application",
               "activity", "name", "com.qq.e.ads.ADActivity", "example.MainActivity", "meta-data", "inside"]
    offsets, content = [], bytearray()
    for s in strings:
        encoded = s.encode("utf-8")
        offsets.append(len(content))
        content.extend(uleb(len(s)) + uleb(len(encoded)) + encoded + b"\0")
    content.extend(bytes((-len(content)) % 4))
    start = 28 + 4 * len(strings)
    pool = struct.pack("<HHI5I", 1, 28, start + len(content), len(strings), 0, 0x100, start, 0)
    pool += struct.pack("<" + "I" * len(offsets), *offsets) + content
    def begin(tag, attrs=()):
        body = struct.pack("<IIHHHHHH", 0xFFFFFFFF, tag, 20, 20, len(attrs), 0, 0, 0)
        for ns, name, value in attrs:
            body += struct.pack("<IIIHBBI", ns, name, value, 8, 0, 3, value)
        return struct.pack("<HHIII", 0x102, 16, 16 + len(body), 1, 0xFFFFFFFF) + body
    def end(tag):
        return struct.pack("<HHIIIII", 0x103, 16, 24, 1, 0xFFFFFFFF, 0xFFFFFFFF, tag)
    nodes = begin(1, [(0xFFFFFFFF, 2, 3)]) + begin(4)
    nodes += begin(5, [(0, 6, 7)]) + begin(9, [(0, 6, 10)]) + end(9) + end(5)
    nodes += begin(5, [(0, 6, 8)]) + end(5) + end(4) + end(1)
    return struct.pack("<HHI", 3, 8, 8 + len(pool) + len(nodes)) + pool + nodes


class ManifestTests(unittest.TestCase):
    def test_remove_full_subtree_and_preserve_pool_and_main_activity(self):
        original = sample_manifest()
        xml = BinaryXML(original)
        nodes = selected_nodes(xml)
        self.assertEqual([(n.tag, n.name) for n in nodes], [("activity", "com.qq.e.ads.ADActivity")])
        patched = xml.remove(nodes)
        result = BinaryXML(patched)
        self.assertEqual([(n.tag, n.name) for n in result.nodes],
                         [("manifest", ""), ("application", ""), ("activity", "example.MainActivity")])
        self.assertEqual(result.root.attrs, xml.root.attrs)
        self.assertEqual(result.strings, xml.strings)
        self.assertEqual(patched[8:nodes[0].start], original[8:nodes[0].start])
        self.assertEqual(xml.data, original)

    def test_reject_invalid_header_and_overlapping_removals(self):
        data = bytearray(sample_manifest())
        data[4] ^= 1
        with self.assertRaises(AssertionError):
            BinaryXML(bytes(data))
        xml = BinaryXML(sample_manifest())
        with self.assertRaises(AssertionError):
            xml.remove([xml.root, xml.root.children[0]])


class DexTests(unittest.TestCase):
    key = ("LExample;", "value", "()I")

    def test_patch_preserves_ids_offsets_length_and_unrelated_bytes(self):
        original = sample_dex()
        dex = DexFile(original)
        off, _ = dex.code[self.key]
        patched, changes = dex.return_zero([self.key])
        after = DexFile(patched)
        self.assertEqual(len(patched), len(original))
        self.assertEqual(after.methods, dex.methods)
        self.assertEqual(after.code, dex.code)
        self.assertEqual(patched[off + 16:off + 22], b"\x12\x00\x0f\x00\x00\x00")
        allowed = set(range(8, 32)) | set(range(off + 16, off + 22))
        self.assertTrue(all(i in allowed for i, (a, b) in enumerate(zip(original, patched)) if a != b))
        self.assertEqual(len(changes), 1)

    def test_reject_checksum_corruption(self):
        original = bytearray(sample_dex())
        original[-1] ^= 1
        with self.assertRaises(AssertionError):
            DexFile(bytes(original))

    def test_reject_methods_with_exception_handlers(self):
        data = bytearray(sample_dex())
        off, _ = DexFile(bytes(data)).code[self.key]
        struct.pack_into("<H", data, off + 6, 1)
        with self.assertRaisesRegex(AssertionError, "Unsafe code item"):
            DexFile(fix_dex(data)).return_zero([self.key])

    def test_reject_missing_target(self):
        with self.assertRaises(KeyError):
            DexFile(sample_dex()).return_zero([("LExample;", "missing", "()I")])


class InputTests(unittest.TestCase):
    def test_unknown_apk_rejected_without_patching(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wrong.apk"
            path.write_bytes(b"not the supported APK")
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "Unsupported original APK"):
                supported_input(path)
            self.assertEqual(path.read_bytes(), before)

    def test_missing_input_has_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Original APK not found"):
            supported_input(Path("__missing_original_apk__.apk"))


if __name__ == "__main__":
    unittest.main()
