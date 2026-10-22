# Weapon kind expansion: RAM and data (scoping)

Goal: Supamario (fighter kind 0x41) gets its own projectiles: new weapon kinds 0x185+ copied from
Mario's articles, owned by "supamario" (files from fighter/supamario/, effect bank 0x341).
Static analysis of cross_f.rpx only (scratchpad/rpx/text.bin), nothing patched or tested.
Scripts here: scan_imm.py, globals.py (ramrefs.pkl), callers.py, desc.py, acmd_ids.py, msc/*.c.

## How a fighter's weapons work (what the expansion hooks into)

- Fighter descriptor (switch 0x02E4313C, kinds 0x00-0x40; Supamario's is kind_expand's cave copy of
  Mario's) **+8 = the fighter's article list**: {u32 *entries, u32 count}, entries 0x10 bytes:
  [weapon kind | flags in bits 30-31, max count, callback, callback2]. Mario (kind 3, desc
  0x103A7BDC, list 0x1013D204 -> 0x1013D20C):
  | article id | weapon kind | name | max | callbacks |
  |---|---|---|---|---|
  | 0 | 0x00 | fireball | 5 | 0x02F1AC88 |
  | 1 | 0x01 | mantle | 1 | 0x02F1AE24 |
  | 2 | 0x02 | pump | 1 | 0x02F1AEE8 |
  | 3 | 0x04 | hugeflame | 1 | 0x02F1B01C, 0x02F1B0B8 |
  | 4 | 0x05 | dokan | 1 | - |
  pumpwater (0x03) is the pump's own sub-article (weapon descriptor +0x14 list, created by
  pump.mscsb `ArticleModule(0x2710, 0)`).
- **Article ids in scripts are local indices into that list** (FighterArticles.xml IDs; Mario's MSC
  calls ArticleModule(op, 0..4); higher ids in mario.mscsb are leftovers of shared code). So the
  fighter's MSC / ACMD need no change if Supamario's list keeps Mario's order.
- Weapon descriptors: switch 0x0320D934 (kinds 0-0x184, default 0x1018A19C), one static record a
  kind in .data 0x10341270-0x10422E68 (fireball 0x1041ED4C, mantle 0x1041EDB4, pump 0x1041EEAC,
  pumpwater 0x10344144, hugeflame 0x103440BC, dokan 0x1034408C; Dr. Mario's own drcapsule 0x10343F84:
  the precedent of a clone with its own weapon kinds). Stored per weapon object at +0x1BF4 (setup
  0x02B62EF4; +0x1BF0 = switch 0x03210C30's result). +0x18 get_param, +0x24 modifier list.
- Resource request: fighter set-up -> 0x030C0BB0 (fighter descriptor +8) -> 0x030C3E7C ->
  0x030C37AC (walks the list, recursing into each weapon descriptor's +0x14 list) -> 0x030C3B78 per
  weapon kind: model / motion / animcmd / msc paths from 0x030BCB10 (name 0x10419604, folder
  0x10419C18, owner 0x10418FF0, root 0x104189DC = "fighter"), registered in holder
  `[[0x102F9028]+0x30]` (holder 0xC) under **id = wkind * 0x29 + n** (n: models 0-7, motion +8..,
  +0x10, +0x18; variant << 28): a refcounted id -> file map (add 0x030BEEE0), no per-kind bound.
  Special cases in 0x030C3B78 / 0x030C3A40: 0x157 -> 0xCC alias; 0xC, 0x11, 0x13, 0x164-0x165;
  0x80, 0x81, 0x179-0x17E; and the per-kind u16 flag table 0x1018A970 (2 * kind, via 0x0320E634 /
  0x0320E698 / 0x0320E6AC / 0x0320E6C0 / 0x0320E6D4; their `this` 0x104D1633 is unused).

## 1. RAM: arrays indexed by weapon kind

**None found.** Evidence (medium confidence; no data-flow tracker for weapon kinds):
- no loop over all weapon kinds: the 6 `li 0x185`, 10 `li 0x184`, 4 `cmplwi 0x185` sites are other
  enums (sound / UI state machines); the 15 `cmplwi 0x184` are switches on a weapon kind (other scope);
- RAM blocks referenced from code (21710 addresses via lis+D-form) whose span is 389 x element:
  only the four static .data word tables above (0x104189DC, 0x10418FF0, 0x10419604, 0x10419C18);
  0x10315720 (389 x 0x1C) is unrelated;
- allocation sizes 389 x element + 0..0x200: none weapon-related (0x1EE4 = holder 0xC's object, fixed
  pools; 0x5518 etc. elsewhere);
- the weapon pipeline itself keeps state per object (weapon +0x1BF0 / +0x1BF4), per fighter
  ArticleModule (sized from the list's counts) and in id-keyed holders.
Resource ids for kinds 0x185-0x18A: 0x3E5D-0x3F2A (+n): fine as map keys; holder 0xC's fixed
pools (5 x 8 x 0xC0 at +0x2C) are load slots, not per kind (Mario + Supamario together load both
sets: check in game).
Static per-kind data that new kinds index past (other scope, listed for completeness): the four
word tables, the u16 flags 0x1018A970, the descriptor switch 0x0320D934, the 13 switches at
0x02B651AC-0x02B83D58 and 0x03210C30, the vl accessor switches.

## 2. Data files

| file (fighter/<owner>/...) | keyed by | for a Supamario-owned copy |
|---|---|---|
| `model/<article>/` (fireball, mantle, pump, pumpwater, hugeflame, dokan; from the model dump) | owner + folder name | copy under fighter/supamario/, names kept |
| `motion/<article>/` (fireball, mantle, pump, hugeflame, dokan) | owner + folder | copy |
| `script/animcmd/weapon/<article>/` game / effect / sound / expression .bin + motion.mtable | owner + folder | copy; **effect ids 0x303xxxxx -> 0x341xxxxx, 0x403 -> 0x441** (fireball effect.bin 8, pump 13, pumpwater 8, hugeflame 1): `move_effect_ids` as for the body; sound ids (0x20036 / 0x20037 ...) unchanged (the renamed banks keep Mario's BINF ids); motion.mtable unchanged (animation hashes) |
| `script/msc/<article>/<article>.mscsb` (fireball, pump, pumpwater, hugeflame) | owner + folder | copy unchanged: no effect ids, no fighter / weapon kind constants (decompiled: msc/*.c); one sound id `SoundModule(0x2710, 0x20037)` (bank id, kept); pump's `ArticleModule(0x2710, 0)` is local (its sub-list) |
| `param/fighter/fighter_param_vl_supamario.bin` | file per fighter | already Mario's copy, weapon blocks at the same offsets: fireball +0x164 (x 0x2C a custom slot), fireball modifiers +0x1B4, pump +0x184 (x 0x1C), pumpwater +0x198 (x 0x20), hugeflame +0x1AC (x 8); mantle / dokan none. Mario's accessors (0x031B21CC, 0x031B21FC, 0x031B2A80, 0x02B1A5C4, 0x02B1A088) read **Mario's slot** `[[0x102FF448]+0x1128]`; the new kinds' copies must read kind 0x41's relocated slot, **`+0x26B4`** (kind_expand's vl array at +0x25B0, capacity 0x60) |
| fighter MSC / ACMD (body) | - | no change (article ids local) |
| effect `.efc` / `.ptcl` | bank 0x300 + kind | Supamario's is already Mario's copy (holds the article effects); with the ids moved, base_effects_cave's Mario banks are no longer needed for these weapons |
| sound banks | BINF id | unchanged (Mario's ids) |
| `reference/FighterArticles.xml` | fighter name | add a supamario entry (docs only) |
No param file under param/ is keyed by weapon kind (no 389-entry group or record layout).

## 3. add_fighter.py

- `--own-articles` (or `--articles` when the record lists `weapons`): copy the article folders
  (`is_article`) under the new name (folders keep their article names), and run `move_effect_ids`
  on `script/animcmd/weapon/*/*.bin` too (today only `script/animcmd/body/`).
- extra_kinds.json record: the new weapon kinds (e.g. `"weapons": {"fireball": "0x185", "mantle":
  "0x186", "pump": "0x187", "pumpwater": "0x188", "hugeflame": "0x189", "dokan": "0x18A"}`), read
  by both add_fighter.py (logging, FighterArticles entry) and the executable generator (tables,
  descriptors, Supamario's article list and the pump's sub-list, get_param copies at +0x26B4).
- vl file: nothing (same layout).

## Open risks

- Native code comparing weapon kinds to constants (e.g. Mario's fighter code or other fighters'
  reflect / absorb / item code testing `kind == 0` fireball): new kinds take defaults (other scope).
- The article callbacks (0x02F1AC88 ...) read the spawning fighter's Mario specializer fields
  (+0x72E4 ...): fine for Supamario (Mario's specializer); no kind constants seen in their prologues.
- Holder 0xC's pools with Mario and Supamario both loaded (two article sets).
- Weapon descriptor words 0 / 1 (often 0xFFFFFFFF in .data) may be written at run time (as the
  fighter descriptors' +0 / motion table): a copy must be writable (cave, as kind_expand's).
- AI (CPU) projectile handling by weapon kind: not traced.
