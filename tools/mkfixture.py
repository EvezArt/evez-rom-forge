"""Generate a synthetic legal .z64 fixture with embedded known textures."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from n64.n64tex import encode

OUT = sys.argv[1] if len(sys.argv) > 1 else "tests/fixture.z64"
W = H = 16
# gradient + checker textures
grad = [[(x*16, y*16, (x+y)*8, 255) for x in range(W)] for y in range(H)]
check = [[(255,255,255,255) if (x+y)%2 else (40,40,40,255) for x in range(W)] for y in range(H)]

rom = bytearray(b"\x00" * 0x10000)
hdr = struct.pack(">I I Q I I I 2s 20s H s s I",
    0x80371240, 0x000F, 0x80000400, 0x00000000, 0x0, 0x0, b"\x00"*2,
    b"ROMFORGE FIXTURE \x00\x00\x00\x00\x00", 0x4E, b"\x45", b"\x41", 0x00)
rom[0:0x40] = hdr
tex1 = encode("RGBA5551", grad)
tex2 = encode("RGBA5551", check)
rom[0x4000:0x4000+len(tex1)] = tex1
rom[0x8000:0x8000+len(tex2)] = tex2
rom[0xF000:0xF010] = b"STRING-TABLE: fixture by rom-forge"
open(OUT, "wb").write(bytes(rom))
print(f"fixture written: {OUT} ({len(rom)} bytes), textures at 0x4000/0x8000")
