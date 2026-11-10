# SPDX-License-Identifier: MIT
"""In-place DEX method patching with unchanged IDs, code sizes and offsets."""
import hashlib
import struct
import zlib


class DexFile:
    def __init__(self, data):
        self.data = data
        assert data[:4] == b"dex\n" and len(data) == self.u32(32)
        assert data[12:32] == hashlib.sha1(data[32:]).digest(), "Bad DEX SHA-1"
        assert self.u32(8) == zlib.adler32(data[12:]) & 0xFFFFFFFF, "Bad DEX checksum"
        string_count, string_start = struct.unpack_from("<II", data, 56)
        self.strings = []
        for i in range(string_count):
            off = self.u32(string_start + 4 * i)
            _, off = self.uleb(off)
            end = data.index(b"\0", off)
            # Modified UTF-8 differs for NUL/supplementary characters. Method
            # identifiers targeted here contain only ordinary BMP characters.
            self.strings.append(data[off:end].replace(b"\xc0\x80", b"\0").decode("utf-8", "surrogatepass"))
        type_count, type_start = struct.unpack_from("<II", data, 64)
        self.types = [self.strings[self.u32(type_start + 4 * i)] for i in range(type_count)]
        proto_count, proto_start = struct.unpack_from("<II", data, 72)
        self.protos = []
        for i in range(proto_count):
            _, return_type, params_off = struct.unpack_from("<III", data, proto_start + 12 * i)
            params = [] if not params_off else [
                self.types[struct.unpack_from("<H", data, params_off + 4 + 2 * n)[0]]
                for n in range(self.u32(params_off))
            ]
            self.protos.append("(" + "".join(params) + ")" + self.types[return_type])
        method_count, method_start = struct.unpack_from("<II", data, 88)
        self.methods = []
        for i in range(method_count):
            cls, proto, name = struct.unpack_from("<HHI", data, method_start + i * 8)
            self.methods.append((self.types[cls], self.strings[name], self.protos[proto]))
        self.code = {}
        class_count, class_start = struct.unpack_from("<II", data, 96)
        for i in range(class_count):
            class_data = self.u32(class_start + 32 * i + 24)
            if not class_data:
                continue
            off, sizes = class_data, []
            for _ in range(4):
                val, off = self.uleb(off)
                sizes.append(val)
            for _ in range(sizes[0] + sizes[1]):
                _, off = self.uleb(off)
                _, off = self.uleb(off)
            for n_methods in sizes[2:]:
                method_index = 0
                for _ in range(n_methods):
                    delta, off = self.uleb(off)
                    method_index += delta
                    flags, off = self.uleb(off)
                    code_off, off = self.uleb(off)
                    if code_off:
                        self.code[self.methods[method_index]] = (code_off, flags)

    def u32(self, off):
        return struct.unpack_from("<I", self.data, off)[0]

    def uleb(self, off):
        value = shift = 0
        while True:
            b = self.data[off]
            off += 1
            value |= (b & 127) << shift
            if b < 128:
                return value, off
            shift += 7
            assert shift < 35

    def return_zero(self, targets):
        result = bytearray(self.data)
        changes = []
        for key in targets:
            code_off, flags = self.code[key]
            registers, ins, outs, tries, debug, size = struct.unpack_from("<HHHHII", self.data, code_off)
            assert tries == 0 and registers >= 1 and size >= 2, f"Unsafe code item: {key}"
            return_type = key[2].split(")", 1)[1]
            assert return_type in {"Z", "I", "Ljava/util/List;"}
            opcode = 0x11 if return_type == "Ljava/util/List;" else 0x0F
            replacement = bytes((0x12, 0, opcode, 0))
            start, end = code_off + 16, code_off + 16 + size * 2
            old = self.data[start:end]
            # const/4 v0, #0; return[-object] v0; remaining units are NOPs.
            result[start:end] = replacement + b"\0" * (size * 2 - 4)
            changes.append({"class": key[0], "method": key[1], "descriptor": key[2],
                            "code_offset": code_off, "code_units": size,
                            "original_instructions_sha256": hashlib.sha256(old).hexdigest(),
                            "replacement": "const/4 v0, 0; " + ("return-object" if opcode == 0x11 else "return") + " v0; nop padding"})
        result[12:32] = hashlib.sha1(result[32:]).digest()
        struct.pack_into("<I", result, 8, zlib.adler32(result[12:]) & 0xFFFFFFFF)
        verified = DexFile(bytes(result))
        assert len(result) == len(self.data) and verified.methods == self.methods
        for key in targets:
            off, _ = verified.code[key]
            opcode = 0x11 if key[2].endswith(")Ljava/util/List;") else 0x0F
            assert result[off + 16:off + 20] == bytes((0x12, 0, opcode, 0))
        return bytes(result), changes
