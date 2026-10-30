# Porting an Ultimate fighter: the framework

Every port so far found its bugs one test at a time: Hero took 75 fixes, Squirtle shipped five versions
with many of the same bugs again. This framework turns each of those bugs into either a default the
pipeline can't skip or a check the finished package must pass. The converters themselves are described
in docs/ultimate-fighter-port.md; this page is the procedure.

| tool | what |
|---|---|
| `tools/port_sources.py` | where Ultimate's files and the vanilla game are (`port_sources.json`, not committed) |
| `tools/ultimate_port.py` | the pipeline: `init`, `status`, `effects`, `stats`, `plan`, `run`, `check` |
| `fighters/NAME/port.json` | one fighter's settings (`init` fills it from Ultimate's files) |
| `reference/port_bases.json` | what each base fighter's own code does to a port built on it |
| `tools/ultimate_stats.py` | fighter_param stats from Ultimate's `fighter_param.prc`, by name |
| `tools/port_check.py` | the finished package against every bug class so far |

## What the user provides

Once (the shared files; every later port reuses them):
- Ultimate's `fighter/common/param` (fighter_param.prc, effect.prc), `effect/system/common/ef_common.eff`,
  the UI (`ui/replace/chara`), the sound folder;
- ParamLabels.csv (github.com/ultimate-research/param-labels);
- the smashline ACMD dumps (WuBoytH/SSBU-Dumped-Scripts, `lua2cpp_<name>`).

Per fighter: Ultimate's `fighter/<name>/` folder (model, motion, param/vl.prc), its
`effect/fighter/<name>/ef_<name>.eff`, and the trait (CLAUDE.md). Optional, for the specials: the
fighter's decompiled status code (OpenSmash-Ultimate's ssbu-recomp fighter tooling, run on the
user's own dump: Ultimate's speeds and logic for specials, which aren't in the ACMD or the params).

## The procedure

```
python3 tools/port_sources.py NAME                    # every input found?
python3 tools/ultimate_port.py init NAME --base BASE --kind 0x47 --ui-name "Name" --trait TRAIT
python3 tools/ultimate_port.py status NAME            # sources + the base's known traps
python3 tools/ultimate_port.py effects NAME           # his effects; Ultimate's common ones -> ef_common sets
python3 tools/ultimate_port.py plan NAME --out DIR    # every command, in order; '?' = an input missing
python3 tools/ultimate_port.py run NAME body model-c00 ... motions effects sound scripts specials variants shapes stats portraits --out DIR
   (specials: the fighter's MSC / articles: fighters/NAME/NAME.c, weapons/, specials_acmd.json, its build script
    with port.json specials.build_args)
python3 tools/ultimate_port.py check NAME PKG [later packages ...]
```

The order matters: the models before the motions (the model step writes the base's material pacs: Hero
fix 74); the effects before the scripts (the scripts take the bank's ids); `variants` after the scripts and
specials (it scans the translated effect.bin, rebuilds the bank with the turned copies at the end, so no
other id moves, `--variants-last`, points the scripts at them and installs the bank); `shapes` after
anything that rewrites the vl file (the scripts / specials steps start from the base's).

Sources (`port_sources.json`): `kind_folders.NAME` (add_fighter.py's folder: the base's sound banks under
his name), `soundlabeltable` (the user's current one), `s4_chr` (the user's ui/replace/chr) and
`templates.NAME` (add_fighter.py's portraits, a folder or ZIP:PREFIX), besides the Ultimate ones.

**The status code** (ssbu-recomp on the user's dump: `lua2cpp_<name>/c_*.c`, the NRO translated
instruction by instruction, no names, no data): `tools/recomp_hashes.py DUMP VL_PRC LABELS` lists which
function builds which hash40 (vl.prc labels, status / motion names). Most specials' numbers are in vl.prc
under ParamLabels' names (Squirtle's Withdraw: `param_special_s`); the NRO tells which status reads them.
Params it never builds (Withdraw's speed_x) are read in the executable's native code.

The slot itself (kind record in `tools/extra_kinds.json`, `add_fighter.py`, the executable caves) is
docs/kind-expansion.md; run every cave test with `--others` (Hero v4b).

**Delivering:** `port_check.py` over the install as the user will have it: the full package plus every
fix package after it, in order. No ERROR goes out. A fix package that ships a file ships its partners
(`model.nud` with `model.nut`; a `game.bin` built on the current one, not vanilla's).

## port.json

| field | |
|---|---|
| `ult`, `kind`, `base`, `ui_name`, `trait` | identity; trait: CLAUDE.md |
| `rolloff` | speed / air multiplier (defaults 2.2 / 1.0) |
| `costumes` | the Ultimate costumes converted |
| `model.max_bones` / `joints` / `have` | bone budget; bones his hitboxes use beyond the 26 (`init` finds them: table 1); `have` for a weapon / shield that rides LHaveN / RHaveN (Hero's `Shield,Sword1`, Sephiroth's swords) |
| `motions.add` | Ultimate motions the base has no slot for (jab 2 / 3, special phases) |
| `effects.own` / `common` | from `init` (the scripts' effects); `tint_for`, `hdr_white_for`, `bone_path` as vfxb_to_ptcl.py |
| `stats.jump_scale` | full / short hop factors (below) |
| `portraits.cross` / `stock_icon` | ultimate_portraits.py |
| `specials.msc` / `acmd` / `build` | the fighter's own specials code and build script |

## Stats

`tools/ultimate_stats.py` reads Ultimate's entry by name (ParamLabels.csv). Comparing the two games' tables
over the 51 fighters both have:
- the same in both games (so Ultimate's is the port's): jump x speeds, air-jump x speed (16, which the
  hand-made lists had at 1), double-jump height, air accel / speed / brakes (air brake y, 26, was left as
  the base's), gravity, fall / fast fall, weight, jump count, jab count;
- Ultimate's by design: walk / run (Ultimate is 1.05x / 1.1x on every fighter), dash, landing lag
  (~0.6x), jump squat 3;
- ground friction: Ultimate's x0.45, as every port (Smash 4's are 0.45-0.57 of Ultimate's);
- 264 rapid jab, 268 jump type (fly = Pit's multi-jump) from Ultimate's; 265 (side tilt count) never:
  the common combo repeats the first hit (Hero fix 16), the port writes its own loop.
- **Jump heights:** Smash 4's full / short hops equal Ultimate's for 48 / 47 of 51 fighters, so the data
  says x1: the default (user's call). Hero / Steve / Squirtle / Sephiroth were made at x0.82 / x0.9 and keep it
  in their port.json (`stats.jump_scale`).

## Bug catalogue

Each row: the bug, where it happened, and what now stops it. `port_check` codes in brackets.

| bug | ports | guard |
|---|---|---|
| joints past 26 in table 0: hitboxes over the whole stage, a stretched tail | Sephiroth t20, Squirtle v2-4 | `--joints` writes table 1 [M1] |
| base table-1 joints as stand-ins: the head came off | Hero / Steve fix 9 | own bones (`add_joint_bones`) [M2] |
| NUD bone range 0-N, rigged polygons unflagged: a pillar, invisible, a crash | Incineroar, Sephiroth t19 | `nud.write` [M3, M4] |
| `model.nud` shipped without `model.nut`: wrong textures | Hero fix 17 | plan ships both [M5] |
| the model step's material pacs shipped: shields gone | Hero fix 74 | plan ships the motions step's [M7] |
| the base's face keys hide meshes that are the port's face: black / missing face | Squirtle | drive the slots from Ultimate's visibility [F1] |
| body scripts from vanilla: no roll-off, the user's edits lost | Hero fix 57, Bowser jabs v3 | `unpack-body` (universal mechanics) [S1] |
| a hitbox on a joint the table hasn't | | [S2] |
| effects from another bank | | [S3] |
| Ultimate's angles 367 / 368: multi-hits let go | Squirtle's Waterfall, Hero's Swoosh | translator -> 366 [S4] |
| throw hitboxes free the held fighter | Squirtle's throws | translator: catch-only -> NoGrabRelease [S5] |
| the base's moves left in (its landing hit, its specials) | Squirtle, Hero | [S7] |
| motions that loop in Ultimate playing once | Hero fix 63 | translator [V1] |
| stats left as the base's / regressed by an older param file | Hero (fighters_latest has Robin's) | `ultimate_stats.py` [P1, P2] |
| msclang nested calls: the stack off by one | Hero fix 11 | patched compiler [C1] |
| `PostureModuleF(0x7)` (scale) taken as the facing | Hero fix 68 | [C2] |
| a speed set in world X without the facing: right-side bias | Squirtle's Withdraw | [C4] |
| no universal mechanics in the MSC | | [C3] |
| trait / README missing | | [K1, K2] |
| turned effects on bones flip for one facing | Sephiroth t49, Squirtle's dash attack | `--variants` in the plan [E1] |
| Smash 4 common effects standing in for Ultimate's | Squirtle (all), Hero's up air (fix 63-70) | plan converts `sys_*` from ef_common.eff [E3] |
| washed out / dark / purple effects | Hero fixes 21-52 | converter (own pixel programs, linear -> display, no HDR purple) |
| base native code playing its effects on copied articles | Hero (Robin's Thunder orb) | `reference/port_bases.json` traps; per base cave (thunder_orb_cave.py) |
| the base's landing hit left on a move Ultimate has no script for | Squirtle's down air | translator `EMPTY_IF_ABSENT` [S7] |
| the base's scripts the port keeps (ledge quick options, sleep) with Smash 4's common effects | Squirtle | translator `common_to_own` [E3] |
| variants inserted before the common effects: their ids moved under the translated scripts | Squirtle v6 build | `--variants-last` |
| an emitter with a fractional rate emitted once: a particle buffer of 0 | Ultimate's sys_piyo | converter: one particle |
| hurtboxes on the port's own joints (table 1) | Squirtle's tail | ultimate_vl_shapes.py: 1000 + k |
| a copied article keeps its base's native per-frame code: Squirtle's water bounced like Mario's fireball and died at close range | Squirtle v2-v5, Supamario's Kamehameha | `"nop2"` in the record (port_bases.json `weapon_nop2`) [W1] |
| base counters / native per-frame code acting on the port | Hero fixes 19, 62 | `reference/port_bases.json` traps |
| articles after the base's special entry never spawned | Hero fix 15 | weapon_expand.py |
| caves overlapping | Hero v4b | cave tests with `--others` |
| stock icon = the select render shrunk | Squirtle | `--stock-icon` (Ultimate's chara_2; its icons have no eyes: user) |
| portraits darker than Smash 4's | Hero fix 75 | ultimate_portraits.py tone curve |
| mirrored UVs black (sampler wrap) | Hero fix 70 | converter (Ultimate's wrap) |

## Open

- Statuses written by hand still need the status code for accuracy (Withdraw's speeds): ssbu-recomp.
