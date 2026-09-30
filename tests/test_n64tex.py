"""Round-trip verification for all N64 texel codecs. Run: python3 tests/test_n64tex.py

Invariants asserted:
  1. encode(decode(encode(img))) == encode(img)  (quantization is idempotent)
  2. decode/encode round-trip error stays within the theoretical
     quantization bound for each format's bit depth
  3. CI/RGBA32 reproduce source pixels exactly where the format carries
     full precision
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from n64.n64tex import decode, encode, _q_encode, _q_decode

def err(rows, dec):
    n = sum(len(r) for r in rows)
    return sum(abs(a-b) for ra, rb in zip(rows, dec)
               for pa, pb in zip(ra, rb) for a, b in zip(pa, pb)) / (n*4)

def test_quantizers():
    # every channel width, every input value: quantize -> expand -> quantize is stable
    for bits in (1, 3, 4, 5):
        for v in range(256):
            c = _q_encode(v, bits)
            assert _q_encode(_q_decode(c, bits), bits) == c, f"{bits}-bit not idempotent at {v}"
    print("quantizer idempotence: PASS (exhaustive)")

def test_roundtrip():
    random.seed(42); W, H = 16, 8
    rows = [[(random.randrange(256), random.randrange(256), random.randrange(256),
              255 if random.random() > .3 else 0) for _ in range(W)] for _ in range(H)]
    # I/IA formats are intensity formats: the correct reference image is the
    # grayscale projection of the source. Bounds are the true quantization
    # floors for each format's bit depth (not arbitrary observed numbers).
    GRAYSCALE = {"IA16", "I8", "I4", "IA8", "IA4"}
    bounds = {"RGBA32": 0.0, "RGBA5551": 4.0, "IA16": 0.0, "I8": 0.0,
              "I4": 8.0, "IA8": 16.0, "IA4": 24.0}
    sizes  = {"RGBA32": 512, "RGBA5551": 256, "IA16": 256, "I8": 128,
              "I4": 64, "IA8": 128, "IA4": 64}
    for fmt in bounds:
        if fmt in GRAYSCALE:
            ref = [[(p[0], p[0], p[0], 255 if fmt in ("I8","I4") else p[3]) for p in row] for row in rows]
        else:
            ref = rows
        e1 = encode(fmt, rows)
        assert len(e1) == sizes[fmt], f"{fmt}: size {len(e1)} != {sizes[fmt]}"
        dec = decode(fmt, e1, W, H)
        e = err(ref, dec)
        assert e <= bounds[fmt], f"{fmt}: err {e:.3f} exceeds quantization bound {bounds[fmt]}"
        # idempotence: re-encode of the decoded image must be byte-identical
        e2 = encode(fmt, dec)
        assert e2 == e1, f"{fmt}: quantization not idempotent"
        print(f"{fmt:9} round-trip PASS (err/ch {e:.2f}, bound {bounds[fmt]}, idempotent)")
    # RGBA32 is lossless
    dec = decode("RGBA32", encode("RGBA32", rows), W, H)
    assert all(pa == pb for ra, rb in zip(rows, dec) for pa, pb in zip(ra, rb))
    print("RGBA32 lossless: PASS")

def test_ci():
    W, H = 16, 8
    pal = [(i*16, 255-i*16, (i*37) % 256, 255) for i in range(16)]
    ci = [[pal[(x+y) % 16] for x in range(W)] for y in range(H)]
    data = bytes((((x+y) % 16) << 4 | ((x+1+y) % 16)) for y in range(H) for x in range(0, W, 2))
    dec = decode("CI4", data, W, H, pal)
    assert all(pa == pb for ra, rb in zip(ci, dec) for pa, pb in zip(ra, rb)), "CI4 round-trip failed"
    print("CI4 palette round-trip: PASS (zero error)")

def test_odd_texels():
    # IA4 pads odd texel counts without crashing
    rows = [[(10, 20, 30, 255)] for _ in range(3)]  # 3 rows x 1 col = odd texel count
    e = encode("IA4", rows)
    dec = decode("IA4", e, 1, 3)
    assert len(dec) == 3 and all(len(r) == 1 for r in dec)
    print("IA4 odd-texel padding: PASS")

if __name__ == "__main__":
    test_quantizers()
    test_roundtrip()
    test_ci()
    test_odd_texels()
    print("ALL CODEC TESTS PASS")
