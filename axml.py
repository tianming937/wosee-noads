# SPDX-License-Identifier: MIT
"""Read Android binary XML and remove complete element chunk ranges.

String pool, resource map, retained nodes and their references stay byte-for-byte
unchanged. No resources.arsc or dex compilation is involved.
"""
from dataclasses import dataclass, field
import struct
import xml.etree.ElementTree as ET

ANDROID = "http://schemas.android.com/apk/res/android"
ET.register_namespace("android", ANDROID)
NONE = 0xFFFFFFFF


@dataclass
class Node:
    tag: str
    attrs: dict
    start: int
    end: int = 0
    parent: object = None
    children: list = field(default_factory=list)

    @property
    def name(self):
        return self.attrs.get(f"{{{ANDROID}}}name", "")

    def element(self):
        node = ET.Element(self.tag, self.attrs)
        node.extend(child.element() for child in self.children)
        return node


class BinaryXML:
    def __init__(self, data):
        self.data = data
        self.strings = []
        self.nodes = []
        self.root = None
        self._parse()

    def string(self, idx):
        return "" if idx == NONE else self.strings[idx]

    def qualified(self, ns, name):
        return f"{{{self.string(ns)}}}{self.string(name)}" if ns != NONE else self.string(name)

    def _pool(self, pos):
        count, styles, flags, start, style_start = struct.unpack_from("<5I", self.data, pos + 8)
        header_size = struct.unpack_from("<H", self.data, pos + 2)[0]

        def length(at, utf8):
            if utf8:
                v = self.data[at]
                return (((v & 0x7F) << 8) | self.data[at + 1], at + 2) if v & 0x80 else (v, at + 1)
            v = struct.unpack_from("<H", self.data, at)[0]
            return (((v & 0x7FFF) << 16) | struct.unpack_from("<H", self.data, at + 2)[0], at + 4) if v & 0x8000 else (v, at + 2)

        for i in range(count):
            offset = struct.unpack_from("<I", self.data, pos + header_size + 4 * i)[0]
            at = pos + start + offset
            if flags & 0x100:
                _, at = length(at, True)
                n, at = length(at, True)
                self.strings.append(self.data[at:at + n].decode("utf-8"))
            else:
                n, at = length(at, False)
                self.strings.append(self.data[at:at + n * 2].decode("utf-16le"))

    def _parse(self):
        kind, header_size, size = struct.unpack_from("<HHI", self.data)
        assert kind == 3 and size == len(self.data), "Invalid XML header"
        pos, stack = header_size, []
        while pos < size:
            kind, hs, chunk_size = struct.unpack_from("<HHI", self.data, pos)
            assert hs >= 8 and chunk_size >= hs and pos + chunk_size <= size, "Invalid chunk bounds"
            if kind == 1:
                assert not self.strings, "Multiple string pools"
                self._pool(pos)
            elif kind == 0x102:
                ns, name, attr_start, attr_size, count = struct.unpack_from("<IIHHH", self.data, pos + hs)
                attrs = {}
                for i in range(count):
                    at = pos + hs + attr_start + i * attr_size
                    ans, aname, raw, vsize, zero, vtype, value = struct.unpack_from("<IIIHBBI", self.data, at)
                    assert vsize == 8 and zero == 0
                    if raw != NONE:
                        text = self.string(raw)
                    elif vtype == 3:
                        text = self.string(value)
                    elif vtype in (1, 2):
                        text = ("@" if vtype == 1 else "?") + f"0x{value:08x}"
                    elif vtype == 0x12:
                        text = "true" if value else "false"
                    elif vtype == 0x10:
                        text = str(value if value < 0x80000000 else value - 0x100000000)
                    else:
                        text = f"0x{value:08x}"
                    attrs[self.qualified(ans, aname)] = text
                node = Node(self.qualified(ns, name), attrs, pos, parent=stack[-1] if stack else None)
                self.nodes.append(node)
                if stack:
                    stack[-1].children.append(node)
                else:
                    assert self.root is None
                    self.root = node
                stack.append(node)
            elif kind == 0x103:
                ns, name = struct.unpack_from("<II", self.data, pos + hs)
                node = stack.pop()
                assert node.tag == self.qualified(ns, name), "Unbalanced element"
                node.end = pos + chunk_size
            elif kind not in (0x100, 0x101, 0x180):
                raise ValueError(f"Unsupported manifest XML chunk {kind:#x}")
            pos += chunk_size
        assert pos == size and not stack and self.root is not None

    def xml(self):
        root = self.root.element()
        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    def remove(self, nodes):
        ranges = sorted((n.start, n.end) for n in nodes)
        result, cursor = bytearray(self.data[:8]), 8
        for start, end in ranges:
            assert start >= cursor and end > start, "Overlapping removal ranges"
            result.extend(self.data[cursor:start])
            cursor = end
        result.extend(self.data[cursor:])
        struct.pack_into("<I", result, 4, len(result))
        return bytes(result)
