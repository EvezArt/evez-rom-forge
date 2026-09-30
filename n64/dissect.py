"""N64 ROM dissector — header analysis, segment map, heuristic texture scan.
Usage: python3 -m n64.dissect file.z64 [--extract outdir]   by EVEZ"""
import sys, struct, os

MAGIC = {b"\x80\x37\x12\x40": ("z64", "big-endian"),
         b"\x37\x80\x40\x12": ("n64", "little-endian"),
         b"\x40\x12\x37\x80": ("v64", "byteswapped")}

def load(path):
    raw = open(path, "rb").read()
    head = raw[:4]
    if head in MAGIC:
        order, _ = MAGIC[head]
    else:
        order = "unknown"
    if order == "n64":
        raw = raw[0:4] + b"".join(raw[i:i+4][::-1] for i in range(4, len(raw), 4)) if len(raw)%4==0 else raw
        raw = struct.unpack(">I", struct.pack("<I", struct.unpack("<I", raw[:4])[0]))[0].to_bytes(4,"big") + raw[4:]
    elif order == "v64":
        raw = b"".join(raw[i:i+2][::-1] for i in range(0, len(raw) - 1, 2))
    return raw, order

def parse_header(raw):
    h = {}
    # canonical 64-byte z64 cartridge header (N64 Programming Manual):
    # 0x00 PI dom1 config, 0x04 clock rate, 0x08 entry (u32), 0x0C release,
    # 0x10/0x14 CRC1/2, 0x18-0x1F unused, 0x20 title (20B), 0x34 media (2B),
    # 0x36 cart id (2B), 0x38 region, 0x39 version, 0x3A-0x3F unused
    (h_pi, h["clock_rate"], h["entry"], h["release"], h["crc1"], h["crc2"],
     _u18, h["name"], h["media"], h["cart_id"], h["region"], h["version"],
     _u3a) = struct.unpack_from(">I I I I I I 8s 20s 2s 2s c c 6s", raw, 0)
    h["name"] = h["name"].decode("ascii", "replace").rstrip("\x00 ")
    h["media"] = h["media"].decode("ascii", "replace").rstrip("\x00 ")
    h["cart_id"] = h["cart_id"].decode("ascii", "replace").rstrip("\x00 ")
    h["region"] = h["region"].decode("ascii", "replace")
    h["version"] = h["version"].decode("ascii", "replace") if isinstance(h["version"], bytes) else h["version"]
    return h

def strings(raw, minlen=6, limit=40):
    out, cur, start = [], [], 0
    for i, c in enumerate(raw):
        if 32 <= c < 127:
            if not cur: start = i
            cur.append(chr(c))
        else:
            if len(cur) >= minlen:
                out.append((start, "".join(cur)))
            cur = []
    return out[:limit]

def scan_textures(raw, outdir=None, max_hits=8):
    """Heuristic: find 16-byte-aligned runs that decode as plausible RGBA5551
    image blocks (low alpha-channel noise, nonzero variance)."""
    hits = []
    i = 0x1000
    step = 16
    while i < len(raw) - 2048 and len(hits) < max_hits:
        block = raw[i:i+512]
        try:
            px = struct.unpack(">256H", block)
        except struct.error:
            break
        alpha = [p & 1 for p in px]
        oneness = sum(alpha)/256
        var = max(px)-min(px)
        if 0.15 < oneness < 0.85 and var > 64:
            hits.append((i, oneness, var))
            i += 2048
            continue
        i += step
    return hits

def main():
    path = sys.argv[1]
    raw, order = load(path)
    h = parse_header(raw)
    print(f"== N64 DISSECT: {os.path.basename(path)} ==")
    print(f"byte order : {order}  size: {len(raw)} bytes ({len(raw)/1048576:.2f} MiB)")
    print(f"title     : {h['name']!r}")
    print(f"media     : {h['media']!r}  cart_id: {h['cart_id']!r}  region: {h['region']!r}  v{h['version']}")
    print(f"entry     : 0x{h['entry']:X}  crc1: 0x{h['crc1']:08X}  crc2: 0x{h['crc2']:08X}")
    segs = [("header", 0, 0x40), ("boot", 0x40, 0x1000), ("code", 0x1000, None)]
    print("segments  :")
    for name, s, e in segs:
        e = e or len(raw)
        print(f"  0x{s:06X}-0x{e:06X} {name} ({e-s} bytes)")
    ss = strings(raw)
    print(f"strings   : {len(ss)} found, first entries:")
    for off, s in ss[:8]:
        print(f"  0x{off:06X} {s[:60]!r}")
    hits = scan_textures(raw)
    print(f"texture candidates: {len(hits)}")
    for off, o, v in hits:
        print(f"  0x{off:06X}  alpha-balance {o:.2f}  variance {v}")

if __name__ == "__main__":
    main()
