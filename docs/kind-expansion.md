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

**Low models:** `model/body/l00`-`l07` (the base's low-poly models, `fighter/%s/model/body/l%02d/`,
loaded in most battle modes, `0x030BB540`) must come along with `c00`-`c07`. Supamario v5 had only
the `c` folders and showed nothing in the off-screen magnifying glass (most likely the low model
is what the magnifier draws; not confirmed in game yet).

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

Second kind: **`edge` / `Edge` (UI name `Sephiroth`, subtitle "One-Winged Angel"), kind `0x42`,
character id 60, base Zelda** (Sephiroth, a port from Ultimate; trait Technical). See
[Adding a fighter to a pack that already has one](#adding-a-fighter-to-a-pack-that-already-has-one).

## Implementation: the executable side

`tools/kind_expand.py` reads `tools/extra_kinds.json` (the records `add_fighter.py` also reads) and
prints one `rpx_patch.py` argument list for every new kind. **Unicorn-tested, not yet run in game.**

```
python3 tools/rpx_patch.py build/cross_f.rpx OUT.rpx $(python3 tools/biome_select_cave.py) \
    $(python3 tools/monster_roll_cave.py) $(python3 tools/trait_badge_cave.py) $(python3 tools/kind_expand.py)
python3 tools/kind_expand_test.py OUT.rpx build/cross_f.rpx \
    --others <(python3 tools/biome_select_cave.py) --others <(python3 tools/monster_roll_cave.py) \
    --others <(python3 tools/trait_badge_cave.py)
```

`--info` prints the cave layout; `--rescan-ram` refreshes `tools/kind_expand_ram.json` (below).

### The JSON

```json
{"capacity": "0x60",
 "kinds": [{"kind": "0x41", "name": "supamario", "cap": "Supamario", "base": "mario",
            "ai": "base", "ui": {"id": 59, "name": "Supamario"}}]}
```

| key | meaning |
|---|---|
| `capacity` | how many kinds the per-kind arrays, tables and switches hold (default `0x60`, at most `0x13F`). Adding a fighter below it changes no RAM layout |
| `kind` | consecutive from `0x41` |
| `name` / `cap` | lowercase (folder, files) and Capitalised (sound banks, effects) names |
| `base` | a game kind (name or number): its specializer, vl parser, size tables, sound class and AI |
| `ai` | `base` (the base's cases in both AI switches, default) or `generic` (the switches' default) |
| `ui.id` / `ui.name` | character id (59-199) and UI name (portraits, `MmelChara` labels); no `ui`: no character select entry |
| `vl` | vl file name (default `fighter_param_vl_<name>`) |
| `descriptor.from` | whose descriptor and motion table to copy (default the base) |
| `motions` | motion table entries changed from the base's: `{"0x51": {"anim": "FitZeldaBodyMainC00Attack12", "flags": "0x0"}}` (anim: the main.pac name it plays, hashed `zlib.crc32(name, 0xFFFFFFFF)`; flags: the entry's word, low byte 0x4 = the root moves the fighter, 0x1 = turn; byte +4 and bit 0x80 are set at run time from vl group 1). For a motion slot the base leaves empty (a 3-hit jab on a one-jab base) or a move flag that differs; other keys are comments |

`add_fighter.py`'s `n` key is ignored here; `ui.title`, `series`, `costumes`, `sort` are its own.

### What each part does

| part | sites | how |
|---|---|---|
| FighterParamManager | 2 sizes, 3 loop counts, 164 immediates, 2 hooks | strategy (d) of kind-expansion-ram.md: allocation `0x25B0` → `0x25B0 + capacity * 0x48` (`0x40B0`); the 9 per-kind arrays get a copy at `+0x25B0` (vl `0x25B0`, refcnt `0x2730`, x1324 `0x28B0`, x1428 `0x2A30`, x152C `0x2BB0`, fpidx `0x2D30`, vl50 `0x2EB0`, att `0x3030`, attp `0x3DB0` for `0x60`); every variable-kind access moves its immediate by its array's offset. The list comes from `kind_ram_scan.py plan_sites()`, cached with each site's original word in `tools/kind_expand_ram.json` (checked against the RPX at every run, so a changed base fails loudly). **Hook A** (vl load's common tail `0x02EA8D50`) copies old vl[k] → new vl[k] for k < 0x41; **hook B** (unload store `0x02EA6AF8`) clears both. The 928 kind-built-in reads of the old vl array keep working for vanilla kinds |
| equipment-ability object | 2 | `0x424` → `0x320 + 4 * capacity` (`0x02EA5964`, `0x02EA5978`) |
| AI amiibo learning | 15 words in place | the two increments (`0x02751B04` / `0x02751B28`) are rewritten in place with a `kind < 0x41` guard (the code is out of a branch's reach from the cave; the two blocks share one increment and the common continuation `0x02751B3C`) |
| 6 kind switches | 3-4 words each | the `b` jump table becomes a table of **addresses** in the cave (`add r0, rK, r0` → `lwzx r0, rK, r0`, table address and bound changed; AI `0x02E02458`: `addis` / `addi` → `addis` / `lwz`), so a case can be anywhere. Entries 0x00-0x40 are the game's targets; a new kind: specializer = the base's case, descriptor / vl load / vl unload = its own cases, AI = the base's or the default. Unused kinds up to the capacity → the default. The dispatch now leaves the target in r0 (r12) instead of the table entry: no case reads it before writing it (tested) |
| name tables, size tables, sound class | 18 reader words, 5 bounds | cave copies of `capacity` rows (new kind = the base's values; unused = `""` / 0), readers repointed |
| character id → UI name | 3 | `0x1033BE68` copied with `{ui id, ui name}` added, count `0x53` → `0x54`; the first row's name, filled at run time in the old table only, is `""` in the copy |
| immediates | 12 | random picks `0x021ED1A0` / `B0` / `E0`, `0x021E6E30`: the count (highest kind + 1); kind → character id `0x0309FE68`: capacity - 1; sound banks, AI motion count, AI files, resource holders: the capacity; random-select entries `0x02FFB644`: `0x51` + 1 a UI entry (≤ 96) |
| relocations | 32 moved | every patched in-place word that carried a relocation (switch dispatch, table readers) has it moved to the dead word `0x037EE73C`, else the loader would put the old addresses back |
| per new kind (cave) | | descriptor (`0x38` bytes: the base's, `+0` = kind, `+4` = its own motion info, `+0x1C` = 0) + motion info (`0x18`, its main table pointer) + main motion table (the base's `count * 8` bytes, written at run time by `0x02EA9008`); the descriptor case; the **vl load case** = the base's case copied (31 words; its `bl`s re-aimed), prefixed with `vl_load(mgr, base)` (the base's params, which the base's native code reads at fixed offsets), storing into the equipment object's `+0x320 + 4 * kind`, the new vl / vl50 arrays; the **vl unload case** = the base's (its kind's field), then `vl_unload(mgr, base)` |

Space: `0x04BA0000` up (after smash_button_cave's `0x04B9B000`); ~5.5 KB of tables shared by all
kinds, ~5 KB a kind (Mario base ~5 KB, Zelda ~5.3 KB: two kinds use `0x04BA0000-0x04BA3C00`). The
code space ends at `0x04BB8000`: about 17 kinds. It started at `0x04B85000` (one kind,
`0x04B85000-0x04B877C4`), but the second kind ran into base_effects_cave's `0x04B88000`; that space
is unused now (stale words, nothing points there). 247 words change in place; nothing overlaps the
other caves (checked by the test with `--others`).

**Bases to avoid for now:** kinds 5, 6, 8, 0x17, 0x18, 0x19, 0x1C, 0x20, 0x21, 0x23, 0x26, 0x35. The vl
tail stores an extra vector (x1324 / x152C) for those kinds only, keyed by the kind itself, so a new
kind on such a base gets 0 there (the generator warns). Mario has none.

### Adding the next fighter

1. Append a record to `tools/extra_kinds.json` (next kind, next ui id).
2. `add_fighter.py --kinds tools/extra_kinds.json ...` for the data files and the folder (all records
   in one call on the vanilla files).
3. Rebuild the RPX with the command above and run the test. No RAM change below the capacity.

### Adding a fighter to a pack that already has one

How Sephiroth v1 (`build/sephiroth_v1_test.zip`) was built on top of Supamario (v5 data, test 18
executable), without the vanilla-files-in-one-call rule (the positional files only need the new
row to be next, which it is when the earlier fighters' rows are already there):

1. Executable: the current pack's `cross_f.rpx` (the user's `controls_smash_button` build, which
   test 18 extends with weapon_expand) + `kind_expand.py` (all records: its in-place words are
   rewritten, its cave moves as a whole) + `base_effects_cave.py` + `base_customs_cave.py` +
   `weapon_expand.py`. Checked: against test 18's executable only the words of those three
   generators differ; `kind_expand_test.py` (with `--others` for every other cave),
   `weapon_expand_test.py`, `base_effects_test.py`, `base_customs_test.py`: 0 failed.
2. Data: `add_fighter.py --kinds tools/extra_kinds.json --only edge --param V5/param --param
   USER_PARAM --param VANILLA_PARAM --ui USER_UI --msbt V5/ui/message/melee.msbt` (the edited
   files come from the newest pack first, so Supamario's rows stay; each is re-read and checked);
   `add_fighter.py --only edge --folder ZELDA OUT` with Zelda's universal-mechanics `game.bin` /
   `zelda.mscsb` (`build/universal_mechanics_all.zip`) in place of the vanilla ones;
   `add_fighter_customs.py --only edge --menu V5/ui/message/menu.msbt ...`;
   `chara_layout.py USER_chara.lm OUT/ui/lumen/chara/chara.lm --last 59` (frames past `--last`
   are deltas on the rewritten ones: only their keyframes, which the game jumps to, are held
   unchanged).

### Test results (`kind_expand_test.py`, unicorn)

All 84 checks pass on base + biome + monster + trait + kind_expand (supamario), and 143 with a
3-kind file (Mario, Fox with generic AI, kind 0x40 with no UI entry: the fall-through last case):
- every generated word is in the RPX; the 247 in-place words decode (capstone) to the intended
  instruction or the moved immediate; their originals were checked when generating; the copied
  case words differ from the base's only in the planned fields; no relocation is left on a patched
  word; no overlap with the other three caves;
- the six switches: kinds 0x00-0x40 reach the same targets as unpatched; 0x41 reaches the planned
  case; unused kinds and past the capacity reach the default;
- specializer, descriptor (copy: `+0` 0x41, `+0x1C` 0, rest = Mario's; own main table = Mario's
  bytes), names, size getters, sound class, character id → name (59 → "Supamario"), kind →
  character id (fake database) for all game kinds = unpatched;
- param manager with stubbed allocator / file binders and fake vl structs: constructor sizes
  (`0x40B0`, equipment `0x4A0`); loader clears the new arrays for 0x00-0x5F and maps kinds to
  fighter_param entries as unpatched (0x41 too); vl load / load / unload / unload of **every game
  kind** gives the same calls, file names and per-kind values as unpatched, with the old vl array
  mirroring the new one; kind 0x41 loads Mario's params then `param/fighter/fighter_param_vl_supamario.bin`
  with Mario's parser, fills its own fields only (nothing written at the old `0x111C + 4 * 0x41`, which
  is the old refcnt[0]), refcounts, frees with Mario's functions, releases Mario (not freed while a
  Mario player holds it); unload-all reaches it;
- `0x02EA9064(mgr, 0x41)` builds the motion table into supamario's copy (Mario's untouched);
- AI guard: kinds 0x00-0x40 write exactly as unpatched, 0x41 / 0x5F write nothing (unpatched 0x41
  wrote into the next record).

### Not tested (in game only)

- Everything at run time: the character select entry, loading a match, Supamario next to Mario.
- The writable descriptor / motion table in the grown code space (fine on Cemu; maybe not on a console).
- The game's real parsers and file loading (stubbed in the test), the fighter set-up path
  (`0x02E11C60`, module set-up `0x02E3F32C`) with kind 0x41, and the 62 partial switches / predicates
  that send new kinds to their defaults.
- Resource-id collisions (`kind * 9 + n`, `kind * 0x11 + n`), the effect-id decoder, save data by id,
  two banks with the same BINF id, the unverified `0x02FCD770` / `0x02748648` compares.
- The 164 RAM immediates come from a static scan: a site it missed still works for vanilla kinds
  (mirror), but would read stale or wrong values for kind 0x41.

## A new fighter's own sound-effect bank (and new sounds)

`tools/fighter_own_bank.py FIGHTER_DIR SOUNDLABELTABLE OUT --name <Name> [--bank-id N] [--row N]
[--sound LABEL=FILE[@VOLUME_DB] ...]` gives a new fighter's renamed copy of its base's
`snd_se_<Name>.nus3bank` its own bank id and soundlabeltable row, appends sounds from audio files, and
moves the fighter's scripts' sound ids to the new row.

How the game binds sounds (cross_f.rpx):
- A fighter's banks are loaded by file name (`fighter/%s/sound/snd_se_%s.nus3bank`, builder
  `0x030BB464`); no table of bank ids by fighter kind. The bank id is BINF's.
- A sound id is `(row << 16) | label`. `soundlabeltable.bin` (`STB\0`, rows of
  `{bank id, labels, offset, 0}`, then the label lists: tone indices, -1 = none): `0x0311EC30(stb, row)`
  -> the row (bounded by the row count), `0x0311EC80` -> its bank id, `0x0311EDC4` / `0x0311EEC4` ->
  the label's tone index. The bank id is then matched against the banks the player has loaded by
  their BINF id (`0x033EC060` a bank handle's id; e.g. a stage's `0x03125C78` tries its own handles,
  then the global ones). No array is indexed by bank id or row.
- So a renamed copy keeping the base's BINF id plays from the base's row, and with the base in the same
  match two loaded banks share the id (which answers is unknown). With its own id and row it is
  independent.

Supamario: `snd_se_Supamario` BINF `snd_se_Supamario` id **2144** (the fighter se ids run 2000-2143),
soundlabeltable row **3249** (an empty row, bank id -1: the row count stays 3252) = Mario's row 2's 139
labels + 3:

| sound | tone | label | sound id | length | volume |
|---|---|---|---|---|---|
| kame_charge (the charge) | 86 | 139 | `0x0CB1008B` | 6.20 s | 0 dB |
| kame_fire (the beam firing) | 87 | 140 | `0x0CB1008C` | 5.70 s | +1 dB |
| kame_beamhead (the beam head) | 88 | 141 | `0x0CB1008D` | 3.23 s | -2 dB |

Encoded as Mario's se one-shots: Namco IDSP (DSP-ADPCM, 48000 Hz mono; header loop points 0, DSP loop
flag 0; nibble count / loop end as the game's), each clip normalised to a -0.5 dBFS peak (Mario's
special tones peak at ~0 dBFS; their RMS + TONE volume is -12 to -16 dB; these come to -15 / -12 /
-10.6 dB), the TONE entry a copy of `snd_se_Mario_Special_L01`'s (its group / flags), data 0x20-aligned
at the end of PACK. PROP / GRP / DTON untouched (the stage bank's 100 added tones play with GRP as
it was).

Scripts moved from row 2 to row 3249 (same labels): `script/animcmd/body/sound.bin` 190 ids,
`weapon/fireball/sound.bin` 8, `weapon/pumpwater/sound.bin` 4 (every int param of sound.bin commands,
the unnamed ones included; other ACMD files hold none), and the fireball's MSC `sys_1E(0x2710,
0x20037)` (pushInt at 0xE50). MSC pushInts are moved only as a SoundModule call's sound id (after a
`0x27xx` selector, up to `sys 0x1E`): Supamario's main script's `sys_18(0x2713, ..., 0x20001, ...)`
attack flags look like row-2 ids and are left alone. Checks: the scripts' bytes differ only in those
id words (ACMD round trip byte-exact), every moved id maps to the same tone, Mario's row and every other
row unchanged, the new tones decode at 43-49 dB SNR against the clips.

Left on Mario's ids: the voice banks (`snd_vc_Supamario` 6001 row 94, `_ouen` 6086, the Kirby-copy bank
2077) and the soundseq file (voice rows only).

Native code playing Mario's se ids: an immediate scan (`lis rN, 2` + `addi`) finds one, the fireball's
native code at `0x031B1D40` (vtable `+0x54` play, `0x20037` = `snd_se_Mario_Special_N02`, the bounce /
landing). Supamario's fireball (weapon kind 0x185) runs that code, so without Mario in the match that
one sound finds no bank 2004 and is silent; ids built at run time from tables weren't searched. Fixes if
it matters: load the base's se bank for the clone too (as `base_effects_cave.py` does effect banks), or
a weapon_expand hook rewriting the id for the copied kind.

Only the game can confirm: the bank with id 2144 loading and playing (Supamario's moves' sounds), the
three new sounds from ACMD (`Sound_Effect` 0x0CB1008B...), the fireball bounce, Mario and Supamario
together (now separate banks).

## v1 in game (user) and v2

v1 (Supamario, a copy of Mario): on the character select, loads, plays, stable; effects shown. Then:
- **Mario-only effects missing** (Fireball, F.L.U.D.D. water): an ACMD effect id `0xTKKnnnn` is
  bank `0x300 + kind` (`0x400 +` the Final Smash's). The copy's body ACMD uses `0x341` (loaded), but
  the articles load from `fighter/mario/` by the owner name and their ACMD uses Mario's `0x303`
  (fireball, pump, pumpwater) / `0x403` (hugeflame), only loaded with a Mario in the match.
  `tools/base_effects_cave.py` (cave `0x04B88000`): 13 call sites (effect folder add / remove, bank
  register / release, the Final Smash folder and bank) re-aimed at wrappers that repeat the call
  for the kind's base (`"effects_base": false` in a record turns it off); refcounted like two
  players of one fighter. `base_effects_test.py` (50 checks, the game's own holder / slot code).
  Limit: the bank slot table has 8 slots; a clone without its base uses two.
- **Character select distorted**: it shows frame `num_<count>` of `ui/lumen/chara/chara.lm`
  (`0x028BEE20`) and binds `face_001...` in list order. The user's (4XM honeycomb) file is clean
  up to `num_057` only (their count); `tools/chara_layout.py` rewrites `num_058...num_096` in their
  style. The "big portrait": the grid icon is `chr_10` (`0x028BE920` -> `0x02917A84`, set 0xA); v1
  copied the unmodified (rectangular) art, so `add_fighter.py --ui` must be the UI the game shows
  (the user's); `chr_12` added to `PORTRAIT_SETS`.
- **Customs: no custom moves**: the owned-move save bits are keyed by character id, room for 51
  ids (`0x02A51368`: `0x02A4D40C(id) * 12 + slot * 3 + variant - 1`, -1 past `0x264`; the prize
  code's `0x02946468` the same). `tools/base_customs_cave.py` (cave `0x04B8A000`) rewrites both
  entries to map a new id to its base's (59 -> 4): Supamario owns what Mario owns.
  `tools/add_fighter_customs.py` adds the `MmenSpN__ / MmenSpI__<Name>_*` labels (menu.msbt) and
  `spi_10_<Name>_*` icons. The "amiibo" look and the test-play softlock weren't explained (no id
  or kind range checks found in the Customize set-up, `0x029BA004` / `0x029BA0C4` / `0x0301491C`).
- v1's melee.msbt was built on the unmodified text; v2 on the user's (with the stage names).

v2 in game (user): crashed on the character select. Found: `chara_layout.py` read the last frame's
children up to the sprite's end, so it also rewrote the sprite's keyframes (tag `0xF105`, after the
last frame: each frame's full state, what a goto shows; in the user's file every keyframe equals
its frame's simulated state). All 84 got `num_096`'s scaled placements, and the file grew 130 KB
(58-96 rewritten). v3: frames read by their tag counts, a rewritten frame's keyframe updated too
(checked: keyframes = frames, every other frame and keyframe unchanged), `--last 58` (+1.8 KB).
The customs cave's two functions were checked (callers keep nothing in the registers it uses).
Not confirmed as the crash: v3 ships a split test (no chara.lm / no chr_12 / an RPX without the
v2 code).

**The crash, found** (the user's Cemu log, resource file and `chr_10/packed`): `ResourceSystem:Reading`
died reading `data/ui/replace/chr/chr_10/packed` with a size of `0xFFE7B682`. The build's resource
table (`tools/rf_check.py`) had `chr_10_Supamario_01.nut` at offset 0 with flags `0xC05` (`0x400`: a
package of its own), a loose file inside the `chr_10` package, which the package file doesn't hold.
Sm4shExplorer gives a file the game doesn't have offset 0, and offset 0 on a file reads as "a package
of its own", so a new file in a packaged folder is built loose unless the folder is set to **Pack this
folder** (the user's other portrait folders were: their Supamario files are in their packages). Not
our files or code: Sm4shExplorer v5 (`tools/sm4shexplorer/`) puts such files in their package; with
an older one, set each packaged folder holding a new character's files to "Pack this folder".

Build (v2): `rpx_patch.py build/cross_f.rpx OUT.rpx` with `biome_select_cave`, `monster_roll_cave`,
`trait_badge_cave`, `kind_expand`, `base_effects_cave`, `base_customs_cave`; data
`add_fighter.py --param USER_PARAM --param VANILLA_PARAM --ui USER_UI --msbt USER_melee.msbt`, then
`add_fighter_customs.py --ui USER_UI --menu USER_menu.msbt --used-ui OUT/ui --used-ui USER_UI`,
then `chara_layout.py USER_chara.lm OUT/ui/lumen/chara/chara.lm`.

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

## Next

The first milestone (kind `0x41` = Supamario, a copy of Mario) is built on both sides: data
(`add_fighter.py`) and executable (`kind_expand.py`), unicorn-tested. Next: run it in Cemu (select
Supamario, a match against Mario, CPU Supamario), then swap in the new model, motions, ACMD, MSC and
params.
