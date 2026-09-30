"""Minimal pure-python PNG writer for arbitrary-size RGBA sheets."""
import zlib, struct

def _chunk(tag, data):
    c = struct.pack(">I", len(data)) + tag + data
    return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

def write_png(path, width, height, rows):
    """rows: list of height lists, each width pixels of (r,g,b,a)."""
    raw = b""
    for row in rows:
        raw += b"\x00" + bytes(v for p in row for v in p)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
                + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b""))
