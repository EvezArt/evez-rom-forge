# libdragon DFS (Dragon File System) — on-disk format
Source of truth: DragonMinded/libdragon trunk, include/dfsinternal.h + src/dragonfs.c (fetched 2026-09-30).

- Sector size: 256 bytes; payload 252 bytes (first 4 bytes of each sector chain to the next)
- Directory entry (256 bytes, packed): next_entry u32 | flags u32 | path[244] | file_pointer u32
- Root entry: path = "DragonFS 2.0", flags = 0xFFFFFFFF, next_entry = 0xDEADBEEF
- flags: FILETYPE = (flags >> 28) & 0xF (FILE=0, DIR=1, EOF=2); size = flags & 0x0FFFFFFF
- Lookup hash prime: 31
- Neither gamejam2024.z64 nor junkrunner v2.1 contains a DFS root; their assets are embedded raw. Parser implemented when a DFS-bearing ROM enters the corpus.
