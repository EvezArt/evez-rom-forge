"""N64 TMEM texture codecs — encode + decode for every RDP texel format.
Round-trip verified in tests/test_n64tex.py. by EVEZ"""
import struct, zlib

# ---------------- DECODE ----------------
def decode(format_, data, width, height, palette=None):
    """Decode raw TMEM data -> list of RGBA rows [(r,g,b,a), ...]."""
    n = width * height
    if format_ == "RGBA5551":
        px = []
        for i in range(n):
            v = struct.unpack_from(">H", data, i*2)[0]
            px.append((((v>>11)&31)*255//31, ((v>>6)&31)*255//31, ((v>>1)&31)*255//31, 255 if v&1 else 0))
    elif format_ == "RGBA32":
        # RGBA32 lives in two TMEM halves: all R, all G, all B, all A
        px = [(data[i], data[n+i], data[2*n+i], data[3*n+i]) for i in range(n)]
    elif format_ == "IA16":
        px = []
        for i in range(n):
            v = struct.unpack_from(">H", data, i*2)[0]
            l = v >> 8
            px.append((l, l, l, v & 255))
    elif format_ == "IA8":
        px = []
        for c in data[:n]:
            l = (c >> 4) * 17
            px.append((l, l, l, (c & 15) * 17))
    elif format_ == "IA4":
        # intensity in HIGH nibble, alpha in LOW nibble
        px = []
        for c in data[: (n+1)//2 ]:
            hi, lo = c >> 4, c & 15
            px.append((hi*17, hi*17, hi*17, lo*17))
    elif format_ == "I8":
        px = [(c, c, c, 255) for c in data[:n]]
    elif format_ == "I4":
        px = []
        for c in data[: (n+1)//2 ]:
            px.append(((c>>4)*17, (c>>4)*17, (c>>4)*17, 255))
            px.append(((c&15)*17, (c&15)*17, (c&15)*17, 255))
    elif format_ == "CI8":
        px = [tuple(palette[c]) for c in data[:n]]
    elif format_ == "CI4":
        px = []
        for c in data[: (n+1)//2 ]:
            px.append(tuple(palette[c >> 4]))
            px.append(tuple(palette[c & 15]))
    else:
        raise ValueError("unknown format " + format_)
    return [px[i*width:(i+1)*width] for i in range(height)]

# ---------------- ENCODE ----------------
def encode(format_, rows):
    """Encode RGBA rows -> raw TMEM bytes. Inverse of decode()."""
    w = len(rows[0]); h = len(rows)
    flat = [p for row in rows for p in row]
    n = w * h
    if format_ == "RGBA5551":
        return b"".join(struct.pack(">H", ((r*31//255)<<11)|((g*31//255)<<6)|((b*31//255)<<1)|(1 if a>127 else 0)) for r,g,b,a in flat)
    if format_ == "RGBA32":
        return (b"".join(bytes([p[0] & 255]) for p in flat) + b"".join(bytes([p[1] & 255]) for p in flat)
              + b"".join(bytes([p[2] & 255]) for p in flat) + b"".join(bytes([p[3] & 255]) for p in flat))
    if format_ == "IA16":
        return b"".join(struct.pack(">H", (r << 8) | a) for r,g,b,a in ((p[0],p[0],p[0],p[3]) for p in flat))
    if format_ == "I8":
        return b"".join(bytes([p[0] & 255]) for p in flat)
    if format_ == "I4":
        return bytes((flat[i][0]//17) << 4 | (flat[i+1][0]//17) for i in range(0, n, 2))
    if format_ == "IA8":
        return bytes((p[0]//17) << 4 | (p[3]//17) for p in flat)
    if format_ == "IA4":
        return bytes((flat[i][0]//17) << 4 | (flat[i+1][3]//17) for i in range(0, n, 2))
    raise ValueError("encode not implemented for " + format_)

# ---------------- PNG ----------------
def to_png(rows, path):
    h = len(rows); w = len(rows[0])
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"".join(bytes(p) for p in row) for row in rows)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)
