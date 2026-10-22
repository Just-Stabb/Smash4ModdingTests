# Weapon-kind (article) expansion: the executable side (scoping)

Goal: new weapon kinds `0x185`+ that are copies of a base fighter's weapons owned by a new fighter
(Supamario, fighter kind `0x41`: copies of Mario's fireball / mantle / pump / pumpwater / hugeflame /
dokan), so their files load from `fighter/supamario/` and their ACMD can use Supamario's effect bank.
Static analysis of `build/cross_f.rpx` (scratchpad `rpx/` dump). Scripts: `scan.py` (bounds / `li` of
`0x183`-`0x186`, jump tables after them), `switches.py` (the 13 switches, their cases), `ptrruns.py`
(pointer tables), `tables.py` (static tables ~389 entries), `desc.py` (weapon descriptors / singletons
per kind), `callers.py`.

Weapon kinds: `0x000`-`0x184` (389). Mario's (fighter kind 3): `0` fireball, `1` mantle, `2` pump,
`3` pumpwater, `4` hugeflame, `5` dokan. The weapon object (generic class, ctor `0x02B6246C`,
`0x1E20` bytes) has its kind at `+4`. Items are a separate id space (`0x138` items, table `0x104157A0`,
`getArticleById` `0x0305368C` in Manifold): not touched.

## 1. Tables and switches indexed by weapon kind

### 1.1 Static data (4 + 3 tables, no other found)

| table | entries | content | readers (all the code references) |
|---|---|---|---|
| `0x104189DC` | 389 x ptr | root (`"fighter"`) | path builder `0x030BCB10` (2 HA/LO pairs) |
| `0x10418FF0` | 389 x ptr | **owner fighter name** (`mario`, ...) | `0x030BCB10` (2 pairs) |
| `0x10419604` | 389 x ptr | weapon name (`fireball`) | `0x030BC8E4` (3 pairs, returns `&name[kind]` as a 1-entry list), `0x030BCB10` (1) |
| `0x10419C18` | 389 x ptr | weapon folder | `0x030BC8E4` (3), `0x030BCB10` (2) |
| `0x1018A1D4` | 389 x u32 | static info (0 / 1 / 2) | accessor `0x0320E5BC` (1 pair; 0 when invalid) |
| `0x1018A7E8` | 389 x u8 | static info (0 / 2) | accessor `0x0320E5FC` (1 pair; 6 when invalid) |
| `0x1018A970` | 389 x u16 | **flags**, bits 0-11 (bit 6: load its models, bits 7 / 8 / 0: the article-list filter, ...) | 12 one-line accessors `0x0320E634`, `648`, `65C`, `670`, `684`, `698`, `6AC`, `6C0`, `6D4`, `6E8`, `6FC`, `710` (`addis r12, kind*2, HA; lhz LO(r12)`: **no bound**) |

- `0x0320E5AC` = `kind < 0x185` (`addic r0, r4, -0x185`), used by the u32 / u8 accessors only.
- The four name tables are contiguous and followed by the Smash Run enemy name tables
  (`0x1041A22C`...): they can't grow in place. The three static tables end at `0x1018AC7A` (zeros after;
  not checked as free).
- `0x030BC8E4(?, kind, variant, &names, &folders, &count)`: kinds `0x3C`, `0x68`, `0x69`, `0x6A`, `0xE5`,
  `0xEB` have multi-model lists (none of Mario's).
- Scans for other tables of ~389 entries (pointer runs; constant-base tables by size: 389 x 1/2/4/...,
  incl. 389 bytes padded to `0x188`) found only vtables and 97-entry tables besides these.

### 1.2 Switches (`cmplwi kind, 0x184` + jump table of `b`): 13

| switch | function | table | cases | what |
|---|---|---|---|---|
| `0x0320D934` | leaf, r4 = kind | `0x0320D954` (-> `b` -> case) | 389 distinct | **weapon descriptor getter** (case: `lis/addi r3, desc; blr`); default `0x0320E57C` -> `0x1018A19C` |
| `0x03210C30` | leaf, r4 = kind | `0x03210C4C` | 389 distinct | per-kind static singleton in `.bss` (fireball `0x1056AA00`: `{0x10179298, 0x101791BC}`, set by a static initializer; no kind field seen); default `0x03211874` -> `0x10497ACC` |
| `0x02B651AC`, `0x02B6B7A8`, `0x02B73AA4`, `0x02B75A88`, `0x02B77FAC`, `0x02B7A4DC` | weapon virtual methods (vtable `{0, fn}` pairs `0x100F7A90`-`0x100F7B8C`) | in place after the `bctr` | 196 distinct | per-kind native handlers (status / update families; kinds share cases) |
| `0x02B6894C`, `0x02B6FD44`, `0x02B7D378`, `0x02B80CF4`, `0x02B83D58` | same vtable | in place | ~317 distinct | per-kind calls (`bl kind_fn(weapon+0xD0, ...)`) |

`0x02B83B3C` (the last) also has `cmplwi r5, 0x184` at `0x02B83B84` (`ble 0x02B83D60`) and `0x02B83C74`
(`bgt default; b 0x02B83D60`) that jump **past** the switch's own bound into its table.
Other `0x183`-`0x186` immediates are not weapon kinds: `li r3, 0x184` before `0x03374578` = `new(0x184)`
(8 sites); `0x0349C514` / `0x034A2D54` / `0x034FF530` / `0x034B2E94` / `0x0354D7D8` / `0x0362A874` /
`0x0361E4CC` = compiler resume states (`0x16D`, `0x177`, `0x185`, `0x18C`...); `0x027DC30C` = an assert
line; `0x02185388`, `0x02E3BC5C` = other ids. Inline compares on specific kinds:
`0x030C3B94` (`0x157` uses `0xCC`'s models), `0x030C3BA8`-`BD0` / `0x030C3F68`-`F80` (`0xC`, `0x11`, `0x13`,
`0x164`, `0x165`: no model / motion), `0x02B633FC`-`0x02B63414` (`0x164`, `0x165`, `0x17C`, `0x183`).

### 1.3 Weapon descriptor (from `0x0320D934`, in `.data`, 48-136 bytes, writable)

`+0` / `+4` (e.g. `0x7D0`, count / -1), `+8` **motion info** `{entries (8 bytes: CRC32 hash, n), count, 0,
0, 0, 0, -90.0f, 90.0f}` (fireball: 4 at `0x1041ED2C`), `+0x10` a function (some), `+0x14` **sub-article
table** `{entries, count}` (pump -> `{pumpwater 3, 12, cb 0x031B262C, 0}`), `+0x18` **get_param**
`(out, custom slot)`, `+0x1C` **the weapon kind itself**, `+0x24` modifier list getter (some).
Fireball's get_param `0x031B21CC`: `[[0x102FF448] + 0x1128]` (= param manager `+0x111C + 4 * 3`, Mario's
vl slot) `+0x164 + slot * 0x2C`; pump's `0x031B2A80`: `+0x184 + slot * 0x1C`.

## 2. Article id -> weapon kind

Fighter descriptor (`0x02E4313C(kind)`) `+8` = the fighter's **article table** `{entries, count}`; an
entry is 16 bytes `{word0: bit 31 a special entry, bits 0-29 the weapon kind; max count (instances);
callback; extra}`. Mario (`0x1013B1DC` -> `0x1013B1E4`, 5): id 0 fireball (5, `0x02F1AC88`), 1 mantle (1,
`0x02F1AE24`), 2 pump (1, `0x02F1AEE8`), 3 hugeflame (1, `0x02F1B01C`, `0x02F1B0B8`), 4 dokan (1).
Pumpwater isn't listed: it's pump's sub-article (descriptor `+0x14`).
- At run time the ArticleModule (ctor `0x02C01254`, `0x148` bytes) holds the table at `+0x130` and reads
  `entries[id * 16]` (`0x02C01B38`, `0x02C01C7C`, `0x02C01854`); `generate_article(id)` from MSC / ACMD /
  native code is fighter-relative.
- Resources: the per-fighter request (`0x030C0BB0`, unload `0x030BFA90`, `0x030C184C`, `0x030C1A78`,
  `0x030C1E2C`) passes descriptor `+8` to `0x030C3E7C`, which flattens it (`0x030C37AC`, recursive through
  each weapon descriptor's `+0x14`, filtered by the flags table, up to `0x30` kinds) and loads each kind
  with `0x030C3B78`.
- **Kind `0x41` today:** `tools/kind_expand.py` copies Mario's descriptor whole, so `+8` = Mario's table:
  Supamario generates Mario's weapon kinds `0`-`5`, owner `mario` (files from `fighter/mario/`). Giving it
  its own weapons = pointing its descriptor copy's `+8` at a new table listing the new kinds (data only).

## 3. Creation, resources, params, effects

- Weapon files: `0x030C3B78(holder, kind, color)` builds paths with `0x030BCB10` (root / **owner** /
  folder / name by kind) and adds them to the weapon holder (`[[0x102F9028]+0x30]`) under ids
  **`kind * 0x29 + n`**: models `+0..7` (`| color << 28`), motions `+8+k` (`| variant << 28`), `+0x10`
  (type 2), `+0x18` (type 3, ACMD); refcounted id map (`0x030BEEE0` / `0x030BF00C`): new kinds get unique
  ids, no array to grow (`(C-1) * 0x29 + 0x28` stays far below `1 << 28`).
- Weapon object: generic class, virtual methods dispatching by kind (1.2); descriptor `+0x18` binds its
  WorkModule params at set-up (`0x02BCC3C0`: `0x0320D934(kind)+0x18`, custom slot).
- Params: the base's get_param reads the **base fighter's vl slot by fixed offset** (fireball:
  `mgr+0x1128`). A copy keeps working (kind_expand loads Mario's vl for Supamario) but uses Mario's
  values; its own = a cave get_param per copied weapon reading kind `0x41`'s slot in kind_expand's new
  vl array (same `+0x164 + slot * 0x2C`), set in the copy's descriptor `+0x18` (and `+0x24` for modifier
  lists). Native per-kind handlers (1.2 cases) that read the base's slot directly stay on Mario's.
- Effects: a weapon ACMD effect id names its bank (`0x3KK` / `0x4KK`, KK = **fighter** kind,
  `tools/base_effects_cave.py` research), not the weapon kind: copies with ids rewritten `0x303 -> 0x341`
  (`0x403 -> 0x441`, hugeflame) use Supamario's banks (already loaded); unrewritten they need Mario's
  (base_effects_cave does that today).

## 4. Plan: new weapon kinds (copies of a base kind, new owner)

Capacity `C` (e.g. `0x1C0`: 59 new kinds). A record per new kind: `{kind, base kind, owner}`; per new
fighter its article table (the base's entries with kinds remapped).

| item | change | in place | cave / data |
|---|---|---|---|
| name tables x4 | copy to the cave with `C` entries (new: root `fighter`, owner `supamario`, base's name / folder strings); move the 26 relocations (13 HA/LO pairs, all in `0x030BC8E4` / `0x030BCB10`) to dummies and write the new halves | 26 | `4 * C * 4` = 7 KB + strings |
| static info x3 | copy (`C` entries; new = base's values); move 14 pairs (u32 1, u8 1, u16 12); bound `0x0320E5AC` `-0x185` -> `-C` | 29 | `7 * C` = 3.1 KB |
| descriptor getter `0x0320D934` | `bgt` -> cave: `kind < C` -> table of new descriptors | 1 | ~8 words + `(C - 0x185)` words |
| singleton getter `0x03210C30` | `bgt` -> cave: re-dispatch with the base kind | 1 | ~10 words |
| 11 method switches | **out of branch range** (`0x02B65000`-`0x02B84000` is > 32 MB below the grown space): overwrite each `cmplwi / bgt / slwi / addis / addi / mtctr / bctr` (7 words) with a far jump `lis rX / addi rX / mtctr rX / bctr` (rX = the register the original `addis` wrote: free) to a cave stub: `kind <= 0x184` -> original table; `kind < C` with a base -> `table + base * 4`; else the original default | 44 | 11 x ~12 words + shared `base_of` (byte / halfword table) |
| `0x02B83B84`, `0x02B83C74` | bound `0x184` -> `C - 1`, branch to the far-jump stub at `0x02B83D58` instead of `0x02B83D60` | 4 | - |
| per new kind | descriptor copy (base's bytes, `+0x1C` = kind, `+8` -> its own motion info copy (hashes: the base's, same `.omo` names), `+0x14` -> remapped sub-article table, optionally `+0x18` / `+0x24` -> cave get_param on the new fighter's vl) | - | ~0.1-0.2 KB a kind (Mario's 6: ~1.2 KB) + 5-8 words a get_param |
| new fighter | its article table (base's entries, kinds remapped; counts / callbacks the base's) and kind_expand's descriptor copy `+8` -> it | - | 16 bytes an article |

Size: ~105 words in place, ~200 cave words, ~11 KB data at `C = 0x1C0` (fits the grown space; the
switch tables stay in place). Data side (other agent): renamed article folders under
`fighter/supamario/` (`model|motion/<name>/`, `script/animcmd/weapon/<name>/`, `script/msc/<name>/`),
effect ids rewritten in the copied weapon ACMD, the vl weapon blocks (if own params).

## 5. Risks / open

- **Inline checks of specific weapon kinds** in native code (Mario's FLUDD / cape code testing
  `[weapon+4] == 2/3`, reflect / absorb lists, AI threat logic): copies fail them. Not scanned (needs a
  data-flow pass over `[weapon+4]` compares); the analog of the fighter side's inline `kind == base`.
- **RAM arrays sized by weapon kind** (weapon manager pools, ACMD / MSC managers keyed by weapon kind,
  per-kind counters): the RAM agent's scope; any found need growing / mirroring like the param manager.
- Branch range: every switch in `0x02B6xxxx`-`0x02B8xxxx` needs the in-place far-jump stub (register
  per switch to confirm); `0x0320D934` / `0x03210C30` / `0x030BC8E4` are in range.
- Writable descriptors / motion info in the grown code space (as for fighter descriptors: fine on Cemu,
  a console unknown).
- Native case handlers for a copied kind read the base fighter's vl slot and may look up the base
  fighter's objects (e.g. Mario's own work variables): shared behaviour, not separate params.
- Article callbacks (`0x02F1AC88`...) are Mario-native: reused; whether they check the owner's fighter
  kind is unverified.
- The flags table's bit meanings (beyond "load models" / the list filter) and the u32 / u8 tables'
  meanings are unverified; copies take the base's values.
