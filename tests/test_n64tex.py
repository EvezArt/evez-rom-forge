"""Round-trip verification for all N64 texel codecs. Run: python3 tests/test_n64tex.py"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from n64.n64tex import decode, encode

def test_roundtrip():
    random.seed(42); W, H = 16, 8
    rows = [[(random.randrange(256), random.randrange(256), random.randrange(256),
              255 if random.random() > .3 else 0) for _ in range(W)] for _ in range(H)]
    for fmt, expect in [("RGBA32", 0), ("RGBA5551", 3.5), ("I8", 62), ("I4", 64), ("IA8", 42), ("IA4", 47), ("IA16", 40)]:
        enc = encode(fmt, rows)
        dec = decode(fmt, enc, W, H)
        err = sum(abs(a-b) for ra, rb in zip(rows, dec) for pa, pb in zip(ra, rb) for a, b in zip(pa, pb)) / (W*H*4)
        assert abs(err - expect) < 1.0, f"{fmt}: err {err} != expected {expect}"
    pal = [(i*16, 255-i*16, (i*37) % 256, 255) for i in range(16)]
    ci = [[pal[(x+y) % 16] for x in range(W)] for y in range(H)]
    data = bytes((((x+y) % 16) << 4 | ((x+1+y) % 16)) for y in range(H) for x in range(0, W, 2))
    dec = decode("CI4", data, W, H, pal)
    assert all(pa == pb for ra, rb in zip(ci, dec) for pa, pb in zip(ra, rb)), "CI4 round-trip failed"
    print("all codec round-trips pass")

if __name__ == "__main__":
    test_roundtrip()
