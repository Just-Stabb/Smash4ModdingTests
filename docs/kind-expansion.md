# Fighter kind expansion (a growing roster)

Goal: real fighter kinds beyond the game's 65 (`0x00`-`0x40`), each a first-class kind with its own
files, params, motion table and UI entry; no per-match or per-slot limit (the alternative of reusing
the Fighting Mii Team kinds, docs/new-fighter-slot.md, caps at three and breaks that mode).

Scoping pass (static analysis of cross_f.rpx; **nothing patched or tested in game yet**). Details:
- [kind-expansion-code.md](kind-expansion-code.md): switches, bounds, tables, UI ids, data files,
  encodings; the per-new-kind record. Tool: `tools/kind_code_scan.py` (`--scan`, `--params DIR`,
  `--plan FILE`, `--json`).
- [kind-expansion-ram.md](kind-expansion-ram.md): per-kind arrays in RAM. Tool:
  `tools/kind_ram_scan.py` (`--summary`, `--csv`, `--missed`, `--loops`, `--plan N`).

## Verdict

Feasible. Nothing found makes kinds above `0x40` impossible.

| Part | Job | Strategy | Confidence |
|---|---|---|---|
| FighterParamManager `[0x102FF448]` (0x25B0 bytes: 9 `[0x41]` arrays from `+0x111C`) | 1344 instructions in 853 functions address the arrays; 993 with the kind built into the offset | (d): grow the allocation, move the per-kind block to its end, keep the old vl array as a mirror for kinds 0x00-0x40: **165 immediates + 2 sizes + 3 loop counts + 2 small hooks**; the 928 constant-kind reads stay untouched, so a missed site still works for vanilla kinds. N ≤ 0x13F (`--plan N`: N = 0x60 → allocation 0x40B0) | inventory high, plan medium |
| Equipment-ability object `[0x10353FC0]` (0x424 bytes, `[0x41]` array at `+0x320`) | 402 accesses, all in the vl load / unload cases | grow in place: 2 size words (`0x02EA5964`, `0x02EA5978`) | high |
| AI object `[[0x102FAD78]+0x794]` (8 × 0x488 records ending in two `[0x41]` amiibo-learning arrays) | 54 instructions in 4 functions | cap: guard the two increments (`0x0274FE18`) with kind < 0x41 (2 small caves); amiibo don't learn against new kinds | high |
| 65-case kind switches | 6 | extend each in a cave (its `bgt` → a stub + one entry a kind) | high |
| Tables (names ×3, value tables ×6, character names) | 10 | cave copies with more entries, readers repointed (~20 relocations moved) | high |
| Immediates (bounds, size getters, UI counts) | 17 | one word each | high |
| Partial switches, predicates, range checks | 62 | none (new kinds take the defaults) | medium (range checks sampled) |
| Kirby copying new kinds | 11 (six 58-entry tables) | optional, later | high |

Per new kind (code and tables): **33 sites**, about 48 words in place, ~20 relocation moves,
~3 KB of cave; the grown code space has ~207 KB free above `0x04B84800`.

## Per new kind: minimum native support (a fighter driven by its own MSC)

- Specializer: a base fighter's singleton (`fighter+0x7538` is read unchecked). Smallest bases:
  purin (4 slots), donkey (5), samus / ganon (6), mario (8).
- Descriptor: its own copy of the base's (kind at `+0`, its own motion table at `+4`, `+0x1C` = 0,
  written at run time: the copy must be writable).
- vl params: copies of the base's load / unload cases storing into the new kind's fields (and loading
  the base's file too: the base's native code reads the base's slot at fixed offsets).
- Size tables, sound class: the base's values. AI: the two AI switches default to the generic AI.
- Data: fighter_param.bin entry (word 0 = kind), `fighter_ai_nfp_learning_param.bin` entry k = kind
  k, vl file, ui_character_db entry (ids 59-199 free; the random-select set caps the database at 96
  entries: 14 new characters before it must widen), ui_layout_db, audience_ouen_param, names
  (melee.msbt), portraits, the fighter folder.

## Open items

- Save data keyed by character id (records, Classic clears): not traced.
- Resource ids `kind*9+n` / `kind*0x11+n` for kinds ≥ 0x41: collisions not checked (they're map keys,
  not indices).
- The `0x3KK…` effect-id decoder wasn't found (the field is 8 bits: room to 0xFF).
- 4 code sites to verify (kind-expansion-code.md); an array only cleared by a memset and indexed
  without a bound would slip past the RAM searches.
- A writable descriptor on a real console (the grown code space is writable on Cemu).

## Next: first milestone

One new kind `0x41` = an exact copy of a base fighter under a new name (its own folder, params, UI
entry), selectable and playable next to the base in Cemu. Then swap in the new model, motions, ACMD,
MSC and params. Generator: an "extra kinds" JSON (kind-expansion-code.md) → the RAM plan
(`kind_ram_scan.py --plan N`) + the code / table plan (`kind_code_scan.py --plan`) + the caves, as
one `rpx_patch.py` argument list, with unicorn tests in the style of the other caves.
