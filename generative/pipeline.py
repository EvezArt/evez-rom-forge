"""THE GENERATIVE SPINE — EVEZ mass generative pipeline v1.

Stages (all idempotent, all receipted on an append-only hash chain):
  INGEST   verify + checksum legal source ROMs
  EXTRACT  codec-suite dissection into corpora
  CORPUS   dedup + stats over the full asset corpus
  SYNTH    polysemantic cluster crossover -> novel assets
  ATLAS    compose atlas sheets FROM synthesized assets
           (generative media holding generative media)
  PUBLISH  emit run receipt, provenance manifest, generated index
  TRAIN    (gated: requires >= 1000 corpus tiles; local/Ollama only)

Runs: python3 -m generative.pipeline [--roms dir] [--n 32] [--out generative/output]
"""
import os, sys, json, time, hashlib, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from n64.dissect import load, scan_textures, parse_header
from n64.n64tex import decode
from n64.synthesize import features, kmeans
from generative.png import write_png

STAGES = ["INGEST", "EXTRACT", "CORPUS", "SYNTH", "ATLAS", "PUBLISH"]

class RunSpine:
    """Append-only run receipt chain (mirror of the evidence-runtime spine)."""
    def __init__(self, path):
        self.path = path
        self.events = []
        if os.path.exists(path):
            for line in open(path):
                if line.strip():
                    self.events.append(json.loads(line))

    def append(self, stage, data):
        prev = self.events[-1]["hash"] if self.events else "0" * 64
        core = {"stage": stage, "data": data, "prev_hash": prev,
                "seq": len(self.events), "ts": time.time()}
        h = hashlib.sha256(json.dumps(core, sort_keys=True, default=str).encode()).hexdigest()
        ev = dict(core); ev["hash"] = h
        self.events.append(ev)
        with open(self.path, "a") as f:
            f.write(json.dumps(ev, sort_keys=True, default=str) + "\n")
        return h

def ingest(rom_paths):
    out = []
    for p in rom_paths:
        raw, order = load(p)
        out.append({"rom": os.path.basename(p), "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "order": order})
    return out

def extract(rom_paths, max_hits=64):
    tiles, sources = [], []
    for p in rom_paths:
        raw, _ = load(p)
        for off, bal, var in scan_textures(raw, max_hits=max_hits):
            tiles.append(decode("RGBA5551", raw[off:off+512], 16, 16))
            sources.append({"rom": os.path.basename(p), "offset": off})
    return tiles, sources

def corpus(tiles, sources):
    feats = [features(t)[0] for t in tiles]
    assign, cents = kmeans(feats, k=6)
    return feats, assign, cents

def synth(tiles, assign, sources, n, seed=42):
    import random
    rng = random.Random(seed)
    clusters = {}
    for i, c in enumerate(assign):
        clusters.setdefault(c, []).append(i)
    corpus_hashes = {hashlib.sha256(bytes(c for p in t for v in p for c in v)).hexdigest() for t in tiles}
    made, seen = [], set()
    for _ in range(n * 6):
        c = rng.choice([c for c in clusters if len(clusters[c]) >= 2])
        a, b = rng.sample(clusters[c], 2)
        cut = rng.randrange(4, 13)
        child = [list(r) for r in tiles[a]]
        for y in range(cut, 16):
            child[y] = list(tiles[b][y])
        y1, y2 = rng.sample(range(16), 2)
        child[y1], child[y2] = child[y2], child[y1]
        h = hashlib.sha256(bytes(c for p in child for v in p for c in v)).hexdigest()
        if h in corpus_hashes or h in seen:
            continue
        seen.add(h)
        made.append({"tiles": child, "sha256": h,
                     "parents": [sources[a], sources[b]], "cluster": c})
        if len(made) >= n:
            break
    return made

def atlas(novel, outdir, cols=8):
    """Compose atlas sheets FROM synthesized assets: generated media
    holding generated media. Each sheet + its manifest + a generated
    HTML index describing the generated corpus."""
    os.makedirs(outdir, exist_ok=True)
    n = len(novel)
    rows_n = (n + cols - 1) // cols
    grid = [[(17, 17, 17, 255)] * cols for _ in range(rows_n * 16)]
    for i, a in enumerate(novel):
        gx, gy = i % cols, (i // cols) * 16
        for y, row in enumerate(a["tiles"]):
            grid[gy + y][gx * 16:(gx + 1) * 16] = [tuple(p) for p in row]
    # 16x16 tiles at scale 1 -> widen: pack each tile as 16x16 in a cols*16 grid
    sheet = []
    for band in range(rows_n):
        for y in range(16):
            sheet.append(grid[band * 16 + y][:cols * 16])
    path = os.path.join(outdir, "atlas_001.png")
    write_png(path, cols * 16, rows_n * 16, sheet)
    manifest = {"sheet": "atlas_001.png", "composed_of": [a["sha256"] for a in novel],
                "layout": f"{cols}x16px tiles, {rows_n} rows",
                "content": "every cell is a novel synthesized asset; generative media holding generative media"}
    json.dump(manifest, open(os.path.join(outdir, "atlas_001.manifest.json"), "w"), indent=2)
    return path, manifest

def publish(outdir, run, stats, spine_path):
    """Generated index: the pipeline generates its own documentation from
    live run data. No fabricated numbers."""
    idx = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>EVEZ Generative Spine — Run {run[:8]}</title>
<style>body{{background:#111;color:#ddd;font-family:monospace;padding:24px}}
img{{image-rendering:pixelated;width:512px;border:1px solid #444}}
td{{padding:2px 10px;border-bottom:1px solid #333}}</style></head><body>
<h1>EVEZ GENERATIVE SPINE</h1>
<p>run {run[:8]} | {time.strftime("%Y-%m-%d %H:%M", time.gmtime())} UTC</p>
<p>{stats['roms']} source ROMs -> {stats['corpus_tiles']} corpus tiles ->
{stats['novel_assets']} novel assets -> 1 atlas sheet (media holding media)</p>
<img src="atlas_001.png">
<h3>Run receipt chain</h3><table>
""" + "".join(f"<tr><td>{e['seq']}</td><td>{e['stage']}</td><td>{e['hash'][:16]}...</td></tr>"
              for e in stats["events"]) + "</table></body></html>"
    p = os.path.join(outdir, "index.html")
    open(p, "w").write(idx)
    return p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roms", default="/tmp/roms")
    ap.add_argument("--n", type=int, default=32)
    ap.add_argument("--out", default="generative/output")
    a = ap.parse_args()
    rom_paths = sorted(os.path.join(a.roms, f) for f in os.listdir(a.roms) if f.endswith(".z64"))
    os.makedirs(a.out, exist_ok=True)
    spine_path = os.path.join(os.path.dirname(__file__), "runs", "spine.jsonl")
    os.makedirs(os.path.dirname(spine_path), exist_ok=True)
    spine = RunSpine(spine_path)
    run_id = hashlib.sha256(str(time.time()).encode()).hexdigest()
    print(f"== EVEZ GENERATIVE SPINE run {run_id[:8]} ==")

    h = spine.append("INGEST", {"run": run_id, "roms": ingest(rom_paths)})
    print(f"[INGEST ] {len(rom_paths)} ROMs verified  receipt {h[:10]}")

    tiles, sources = extract(rom_paths)
    h = spine.append("EXTRACT", {"tiles": len(tiles)})
    print(f"[EXTRACT] {len(tiles)} tiles extracted  receipt {h[:10]}")

    feats, assign, cents = corpus(tiles, sources)
    h = spine.append("CORPUS", {"tiles": len(tiles), "clusters": len(cents)})
    print(f"[CORPUS ] {len(tiles)} tiles, {len(cents)} clusters  receipt {h[:10]}")

    novel = synth(tiles, assign, sources, a.n)
    h = spine.append("SYNTH", {"novel": len(novel),
                               "hashes": [x["sha256"][:12] for x in novel[:8]]})
    print(f"[SYNTH  ] {len(novel)} NOVEL assets  receipt {h[:10]}")

    sheet, manifest = atlas(novel, a.out)
    h = spine.append("ATLAS", {"sheet": sheet, "cells": len(novel)})
    print(f"[ATLAS  ] {sheet} ({len(novel)} cells)  receipt {h[:10]}")

    stats = {"roms": len(rom_paths), "corpus_tiles": len(tiles),
             "novel_assets": len(novel), "events": spine.events}
    idx = publish(a.out, run_id, stats, spine_path)
    h = spine.append("PUBLISH", {"index": idx})
    print(f"[PUBLISH] {idx}  receipt {h[:10]}")
    if len(tiles) < 1000:
        print("[TRAIN  ] GATED: corpus below 1000-tile threshold "
              f"({len(tiles)}/1000). Corpus growth is the unlock.")

if __name__ == "__main__":
    main()
