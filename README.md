# EVEZ ROM-FORGE

**Generative video game asset engine for all platforms.** ROMs become training data; AI play becomes behavioral telemetry; the output is a generative model that produces textures, sprites, meshes, music, and level layouts in platform-native formats.

*by Steven Crawford-Maggard (EVEZ) - EVEZ-OS ecosystem*

## The Pipeline

```
ROMs (.z64/.iso/...) --> rom-dissect --> asset-forge (datasets) --> gen-models --> package-export
                        ^                                  |
AI emulator play -----> emu-harvest (play telemetry) -------+
```

### 1. `rom-dissect` - reverse engineering engine
- **N64**: .z64/.n64/.v64 parsing, file-table extraction, TMEM texture decoding (RGBA5551, CI4/CI8, IA4/IA8/IA16), display-list mesh capture
- **GameCube**: .iso/.gcm FST filesystem extraction, DOL/REL parsing, CMPR/RGB5A3/I4/I8 texture decode, DSP-ADPCM audio
- Extensible format registry: SNES, GBA, Genesis to follow
- Every extracted asset hashed and logged to the provenance ledger

### 2. `emu-harvest` - AI play as telemetry
- AI agents play games in-emulator (extends moltbot-live + game-agent-infra)
- Captures: input traces, RAM state deltas, frame streams, event boundaries
- Play traces are structured behavioral data: how a level flows, when audio triggers, how cameras move

### 3. `asset-forge` - dataset construction
- Normalized asset classes: texture, sprite, tileset, mesh, SFX, music, level-layout
- Every asset carries provenance: source ROM hash, offset, format, extraction method
- Datasets hash-chained via evez-event-spine (immutable, verifiable)

### 4. `gen-models` - the generative stack
- Texture/sprite diffusion model (first target)
- Mesh generation (VAE/GAN over extracted display lists)
- Music + SFX generation (links to evez-daw lineage)
- Level-layout grammar (transformer over tile graphs)

### 5. `package-export` - all platforms out
- Platform-native packagers: .mrom (metarom), GLTF, sprite sheets, homebrew formats (GBA/N64/GCN), engine bundles

## Corpus Strategy

| Corpus | Source | Use |
|--------|--------|-----|
| Research | ROM-derived extractions | Local analysis, format RE, architecture study |
| Production | Synthetic + licensed + homebrew datasets | Model weights that ship |

ROM contents are copyrighted. Research corpus stays local and private; published models train on the production corpus. Homebrew and original pipelines feed both.

## Phases

- **Phase 1**: N64 + GCN dissectors, provenance ledger online
- **Phase 2**: emu-harvest harness (agent-in-emulator play telemetry)
- **Phase 3**: first generative model - texture/sprite diffusion
- **Phase 4**: mesh + audio generation, level grammar, full platform packager
