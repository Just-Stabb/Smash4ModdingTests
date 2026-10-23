# Weapon (article) kind expansion: new projectiles for new fighters

Goal: a new fighter kind (first: Supamario, kind `0x41`, docs/kind-expansion.md) gets weapon kinds
of its own (`0x185` and up), so its projectiles load from its own folder
(`fighter/supamario/model|motion/<article>/`, `script/animcmd/weapon/<article>/`,
`script/msc/<article>/`) and can be changed without touching Mario's. First milestone: copies of
Mario's six weapon kinds (0 fireball, 1 mantle, 2 pump, 3 pumpwater, 4 hugeflame, 5 dokan) owned by
"supamario", their ACMD on Supamario's effect banks (`0x341` / `0x441`).

Scoping (static analysis of `cross_f.rpx`, nothing patched yet):
- [weapon-expansion-code.md](weapon-expansion-code.md): tables, switches, descriptors, the plan.
- [weapon-expansion-ram.md](weapon-expansion-ram.md): RAM structures (none to grow found), data files,
  id rewrites, `add_fighter.py` changes.

## How it fits together

- A fighter's descriptor `+8` -> `{entries, count}`: its **article list**, 16 bytes per article id
  (`{weapon kind (bit 31 special), max count, callback, extra}`; Mario's at `0x1013B1DC`: fireball 5,
  mantle 1, pump 1, hugeflame 1, dokan 1). Scripts and native code use the local article id, so
  Supamario's MSC / ACMD need no change if its own list keeps Mario's order. Pumpwater is the pump's
  sub-article (the pump's weapon descriptor `+0x14`). `kind_expand.py`'s copy of Mario's descriptor
  for kind `0x41` points at Mario's list today; pointing it at a new list is data only.
- A **weapon descriptor** per kind (switch `0x0320D934`): `+8` motion info, `+0x14` sub-articles,
  `+0x18` get_param (reads the owner's vl slot at a fixed offset: Mario's fireball `[mgr+0x1128]`),
  `+0x1C` the kind.
- **Files**: the path builders `0x030BC8E4` / `0x030BCB10` take the owner / name / folder from four
  389-pointer tables (root `0x104189DC`, owner `0x10418FF0`, name `0x10419604`, folder `0x10419C18`;
  contiguous, so they move to the cave). Resources are keyed `kind * 0x29 + n` in a refcounted map:
  no array to grow.
- **Static info**: u32 `0x1018A1D4`, u8 `0x1018A7E8`, u16 flags `0x1018A970` (12 unbounded accessors).
- **13 switches** on the kind (`cmplwi 0x184`): the descriptor getter, a per-kind singleton getter,
  and 11 weapon virtual methods (vtable `0x100F7A90`-`0x100F7B8C`) whose new-kind cases go to their
  base's.
- **Effects**: weapon ACMD effect ids name the owner fighter's bank (`0x3KK` / `0x4KK`), not the
  weapon kind: copies get `0x303` -> `0x341`, `0x403` -> `0x441` (fireball 8, pump 13, pumpwater 8,
  hugeflame 1 ids).
- **Params**: Supamario's vl file already has Mario's weapon blocks at the same offsets; copies of
  the get_param / accessors (`0x031B21CC`, `0x031B21FC`, `0x031B2A80`, `0x02B1A5C4`, `0x02B1A088`)
  pointed at kind `0x41`'s slot (manager `+0x26B4`) give the new weapons their own params.

## Plan (capacity e.g. 0x1C0)

1. Executable (`tools/weapon_expand.py`, driven by a `weapons` map in `tools/extra_kinds.json`):
   relocate the 4 name tables + 3 static tables to the cave (27 relocation pairs moved, the bound at
   `0x0320E5AC` raised); the descriptor / singleton getters extended past their `bgt`; the 11 method
   switches' bound-and-dispatch replaced by far jumps to a cave stub sending new kinds to their base's
   case; per new kind a writable descriptor copy (`+0x1C` = kind, own motion info, remapped
   sub-articles, optionally its own get_param); Supamario's article list set in kind_expand's
   descriptor copy. Estimated ~105 in-place words, ~200 cave words, ~11 KB data. Unicorn tests as
   for kind_expand.
2. Data (`add_fighter.py`): copy the article folders into `fighter/<new>/` (names unchanged), rewrite
   effect ids in `script/animcmd/weapon/*` too, log the weapon kinds.
3. Then `base_effects_cave.py` is no longer needed for a kind whose weapons are its own.

Open risks: native code testing specific weapon kinds inline (copies fail such checks: needs a
data-flow scan), the article callbacks reading the owner's specializer (fine while Supamario uses
Mario's), writable descriptors in the grown code space on a real console, two article sets (Mario +
Supamario) in one match sharing fixed load pools, CPU projectile handling by kind.

## Built (unicorn-tested, not yet run in game)

`tools/weapon_expand.py` (records' `weapons` maps in `tools/extra_kinds.json`, `weapon_capacity`
0x1C0): Supamario's weapons `0x185`-`0x18A` = Mario's fireball, mantle, pump, pumpwater, hugeflame,
dokan, owner "supamario". Cave `0x04B8C000`-`0x04B8F804`: Supamario's article list first (Mario's
order; `kind_expand.py` sets its descriptor copy's `+8` to it via `weapon_expand.article_lists()`),
the 4 name tables and 3 static tables with 0x1C0 entries (27 HA/LO pairs repointed, the `0x0320E5AC`
bound raised), the 13 switches' bounds raised in place (and `0x02B83B84` / `0x02B83C74`) with a far
jump after each `bgt` (its temp register one the original writes there) to a stub that dispatches old
kinds as before and a new kind as its base (the descriptor getter returns the new kind's own
descriptor), per new kind a descriptor copy (`+0x1C` = kind, own motion info, the pump's sub-article
remapped to `0x188`) and param getter copies reading Supamario's vl slot (`+0x26B4`: fireball x2, pump,
pumpwater, hugeflame). 122 words in place, 80 relocations moved. `weapon_expand_test.py`: 78 checks
(every switch for every kind 0-0x1C0+, descriptors, sub-articles, param getters, the 14 table
accessors, the path builders building `fighter/supamario/...`, the article list, no overlap).
Inline weapon-kind checks: none found (12 candidates in weapon / Mario code, all count / null tests or
a param-type switch; a heuristic scan).

`add_fighter.py`: a record with `weapons` copies those articles' folders (names unchanged) and moves
their weapon ACMD effect ids to the new kind's banks (fireball 8, pump 13, pumpwater 8, hugeflame 1).

Kept: `base_effects_cave.py` (Mario's native code may still call effects by Mario's bank; set
`"effects_base": false` once a game test shows nothing missing). Native per-kind code still reads
Mario's vl slot at fixed offsets; the copies' bound params are Supamario's.

Build: the eight scripts' outputs to `rpx_patch.py` (biome_select, monster_roll, trait_badge,
kind_expand, base_effects, base_customs, series, weapon_expand).

## First game test (user's Cemu log): the module rows

Supamario crashed in a match: Cemu stopped in the recompiler running `0x02BE5E4C` (an ACMD command
handler), called from `0x02BCB5D4`, with r8 = `0xAA30` = `0x185 * 0x70`. `0x02BCB42C(object, kind)`
(from `0x02BCB964`, an article's set-up, kind = descriptor `+0x4C`) builds the article's modules
from its kind's row of 28 constructors, table `0x103464A8` (0x70 a row, 389 rows), with no bound. Row
`0x185` is past the table, in the next one (whose rows also look like constructor rows: a scan for
389-row tables misses it), so the fireball's set-up called a wrong function. The table's only
reference is that `mulli r8, r30, 0x70` / `addis r30, r8, 0x1034` / `lwzu r10, 0x64A8(r30)`;
`weapon_expand.py` now replaces the `mulli` (`MODULE_ROW`) with a call to a stub that swaps a new kind
for its base (the base-kind table) first. `weapon_expand_test.py`: every kind 0-0x1C0 gets the row
unpatched code gives it (a new kind its base's); kind 0x185 = row 0 (`0x103464A8`). The check fails
on the previous build (rows past the table) and passes on this one.

User afterwards: that crashing build was also missing Supamario's parameters and other files, which
they had forgotten to add (adding them fixed their crash). The out-of-table read above is real for
kind 0x185 on any build without this fix (the unpatched code indexes the table with the kind
unconditionally), so the fix stays; whether the fireball runs on an older RPX with the files in
place would tell whether something else gates that path.

**In game (user, Minecraft World v18i's RPX with the fix and Supamario's files): every special works**
(fireball, cape, F.L.U.D.D. and up special).

Still possible: other per-kind data indexed without a bound, met further into a match. A crash log
with a different address would show the next one.
