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

## Data files for a new kind

`tools/add_fighter.py` writes them from an "extra kinds" record (`tools/extra_kinds.json`, the
record of kind-expansion-code.md 3.3) and a base fighter, into a folder laid out like `data/` (only
the changed or new files). Each new row is a copy of the base's. Every edited param file is re-read
with `s4param.py` and checked: without the added rows it rebuilds byte-identical to the input.
Kinds must be consecutive from `0x41` and character ids from 59, because some files are positional.
Run every record in one call on the vanilla files.

```
python3 tools/add_fighter.py --param VANILLA/param --ui VANILLA/ui --out OUT --kinds tools/extra_kinds.json
python3 tools/add_fighter.py --kinds tools/extra_kinds.json --only supamario \
        --folder VANILLA/fighter/mario OUT [--model DIR_WITH_MODEL]
```

| file | keyed by | what is added |
|---|---|---|
| `param/fighter/fighter_param.bin` | word 0 = kind (searched; the kind-map loop is patched to cover new kinds) | the base's entry with word 0 = kind, appended |
| `param/fighter/fighter_param_vl_<name>.bin` | file name (vl name table) | the base's file, byte for byte |
| `param/ai/fighter_ai_fighter_param.bin` | value 0 = kind | the base's entry, appended |
| `param/ai/fighter_ai_nfp_learning_param.bin` | **position** (entry k = kind k) | the base's entry at position kind, value 0 = kind |
| `param/simple/simple_character_db_cafe.bin` | value 0 = kind (not in kind order) | the base's row, appended (Classic; its two id-like values 2 / 3 are the base's) |
| `param/sound/audience_ouen_param.bin` | (kind, variant) | the base's rows, appended (cheer timing) |
| `param/ui/ui_character_db.bin` | **position** = character id (ids `<= 0xC7`) | the base's entry at position id (before the 200+ specials, which are searched for): id, kind (`+0x10`), shown (`+0x05`) = 1, fighter (`+0x0C`) = 1, Mii = 0, DLC = 0, sort keys = after every fighter (or the record's `ui.sort`), series / costumes from the record or the base |
| `param/ui/ui_layout_db.bin` | (id, variant), searched | the base's rows with the new id, after the last fighter row |
| `param/ui/ui_skill_db.bin` | position = id (0-58) | the base's row (custom moves) |
| `param/ui/ui_sound_call_voice_db.bin` | position = id - 1 (1-58) | the base's row: the announcer calls the base's name until a new narration id exists |
| `ui/message/melee.msbt` | label | `MmelCharaN/C/A/R_NN_<UiName>` for each label the base has (`ui.title`; C / R in capitals; A = the base's title) |
| `ui/replace[/append]/chr/<set>/<set>_<UiName>_NN.nut` | file name | the base's portraits (`chr_00/10/11/13/40/90`, `chrn_11/12/40/41`, `stock_90`, `chr_70` when present), each texture with a new GIDX id from `0x28010000 + 0x100 * (id - 59)` (the stage icons showed blank with duplicated ids) |

Left as they are, with the reason:
- `unlock/unlock_condition_of_fighters.bin`: a non-DLC id that isn't listed is unlocked (`0x030A0A3C`).
- `ui_character_mask.bin` / `show_character_mask.bin`: they list ids 0-51 only. The DLC ids 52-58 are
  missing and still show, so a missing id doesn't hide a fighter.
- `ui_sound_voice_chara_db.bin` (the Vault voice list), `ui_sound_voice_db_cafe.bin`, `ui_nfp_db.bin`
  (amiibo): optional.
- `fighter_param_etc / power_up / equipment_ability / common`: they have no per-kind rows.
- `record_vs_param(_cafe).bin` and the save data: not traced (open item below).
- `sound/config/*`: the copied banks keep the base's BINF ids, so they reuse the base's
  `soundlabeltable` rows.

**The fighter folder** (`--folder BASE_DIR OUT_DIR` → `OUT_DIR/fighter/<name>/`). Paths the executable
builds with the names get the new name (`%L` = lowercase, `%C` = Capitalised):
- `script/msc/%L.mscsb`
- `effect/%L/%L.010d0000.efc` / `.ptcl`
- `effect/Fin%C/Fin%C.010d0000.*`
- `sound/snd_se_%C`, `snd_vc_%C`, `snd_vc_%C_ouen`, `soundseq_%C.sqb`, `voiceanim_%C.vat`
- `snd_se_vc_Kirby_copy_%C`

Names that are found by listing, by hash or from inside another file are kept: `motion/*/<base>pt1.pac`
(no `pt1` string in the executable), the `.omo` names inside the packs (the descriptor copy keeps the
base's animation hashes), and the effect model folders `Eff<Base>*` (named in the `.efc`).

ACMD effect IDs carry the kind (`0x3KK....` own effects, `0x4KK....` Final Smash). Vanilla clones use
their own kind: Dr. Mario `0x324`, Lucina `0x325`, Dark Pit `0x326`. So `body/effect.bin` gets
`0x3BB` / `0x4BB` → `0x3KK` / `0x4KK`, in effect commands only (`--keep-effect-ids` turns this off).
Mario's MSC has no such constants.

Article folders are not copied (`--articles` copies them): weapons load
`fighter/<owner>/model|motion/<article>/`, `script/animcmd/weapon/<article>/` and
`script/msc/<article>/` by the owner name in the weapon table (`0x10418FF0`, `mario`). So the clone's
Fireball, F.L.U.D.D. and cape use Mario's files from `fighter/mario/`.

The Kirby-copy bank is renamed but not loaded: the loader takes it only for kinds up to `0x39`, and
`copy_grant` refuses kinds `>= 0x3A`.

**Sound caveat:** a renamed bank keeps the base's BINF id, so the clone's sounds are the base's
`soundlabeltable` rows and its ACMD sound IDs stay valid. For Mario these are se 2004, vc 6001,
ouen 6086 and Kirby-copy 2077. Two banks with the same id loaded in one match (Mario and Supamario
together) are **untested**. Separate sounds need new ids, new `soundlabeltable` rows and ACMD that
uses the new ids.

First kind: **`supamario` / `Supamario`, kind `0x41`, character id 59, base Mario** (built from the
vanilla dump; `fighter/supamario/` is 213 files, and 212 of them are byte-identical to Mario's;
`effect.bin` differs in 66 effect-ID words).

## Open items

- Save data keyed by character id (records, Classic clears): not traced. `record_vs_param.bin` (79
  rows) and `record_vs_param_cafe.bin` (75 rows) got no row.
- Effect IDs `0x341....` for the new kind: the copy's `effect.bin` uses them (as vanilla clones use
  their own kind), but the decoder wasn't found. If the effects are missing in game, rebuild with
  `--keep-effect-ids`.
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
