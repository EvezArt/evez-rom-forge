"""Training-data extractor: ROM -> texture dataset with provenance.
Usage: python3 -m n64.extract ROM.z64 --out dataset/    by EVEZ"""
import sys, os, hashlib, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from n64.dissect import load, parse_header, scan_textures
from n64.n64tex import decode, to_png

def extract(rom_path, outdir):
    raw, order = load(rom_path)
    h = parse_header(raw)
    os.makedirs(outdir, exist_ok=True)
    manifest = {
        "source": os.path.basename(rom_path),
        "rom_sha256": hashlib.sha256(raw).hexdigest(),
        "title": h["name"], "byte_order": order,
        "assets": [],
    }
    import sys as _s
    max_hits = int(dict(zip(_s.argv, _s.argv[1:])).get("--max", 48)) if "--max" in _s.argv else 48
    for off, bal, var in scan_textures(raw, max_hits=max_hits):
        block = raw[off:off+512]
        rows = decode("RGBA5551", block, 16, 16)
        fn = f"tex_{off:06X}_{manifest['rom_sha256'][:8]}.png"
        to_png(rows, os.path.join(outdir, fn))
        manifest["assets"].append({
            "file": fn, "rom_offset": f"0x{off:X}", "format": "RGBA5551",
            "w": 16, "h": 16, "sha256": hashlib.sha256(block).hexdigest(),
            "scan_alpha_balance": round(bal, 3), "scan_variance": var,
            "provenance": {"extractor": "n64.extract v1", "decoder": "n64tex (round-trip verified)"},
        })
    with open(os.path.join(outdir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest

if __name__ == "__main__":
    rom, out = sys.argv[1], (sys.argv + [None, "dataset"])[2] if "--out" not in sys.argv else sys.argv[sys.argv.index("--out")+1]
    m = extract(rom, out)
    print(f"extracted {len(m['assets'])} assets from {m['source']} (sha256 {m['rom_sha256'][:16]}...) -> {out}/")
    for a in m["assets"][:3]:
        print(f"  {a['file']} @ {a['rom_offset']}")
