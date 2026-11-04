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

## Checking effects offline: tools/fx_render.py

`python3 tools/fx_render.py NAME MOVE [MOVE ...] --build DIR --out OUT [--frames 0-40] [--every 4]`
draws a move's effects as Ultimate's files describe them (its .eff, its effect script) beside the converted
ones (the package's .ptcl / .efc, the translated effect.bin), a row per frame (side view of "top": forward
right, 5-unit grid). Stage 1: the particles' motion, shape, type, mesh, scale / alpha / colour over life
and their textures (first flipbook cell, a plain colour x texture combine: the converted side's colours
are approximate, its textures being made for our own pixel programs). Stage 2 (default, `--stage 1` for the
old drawing): each converted part drawn by its own pixel program (tools/latte_pixel.py: the latte-dis
disassembly run over every pixel of a triangle with numpy; checked against eft_pixel_test's reference on
1440 cases, and runs all 1336 unique vanilla programs) on its inputs (colour 0 / 1 = keys x colour scale,
alpha; a mesh's vertex colours; UVs x the slot's repeat), blended as the game does (ONE / INV_SRC_ALPHA on a
premultiplied template, else the emitter's blend). Not yet: the vertex programs (UV scroll / flipbooks are
the first cell), u_nwHdrRange taken as (1, 0, 0, 0), no bloom, the distortion pass not drawn. Both sides
apply a mesh's vertex colours (Ultimate's smash flash disc fades to its edge so).

It shows where the converter changed something (a dropped rotation, a lost texture, a wrong type). Where
both columns agree but the game doesn't, our reading of an Ultimate field is wrong in both (Squirtle v6:
the dash's droplets rise ~14 units in both columns, low behind his feet in Ultimate's footage; the down
smash fans upward in both, flat along the ground in the footage): check the Ultimate column against
Ultimate footage (the user's recordings, its grid) before trusting it for a new kind of effect.
Calibration so far: over 485 effects both games share (same set / emitter names in 12 fighters' banks),
velocity, gravity, air resistance and life are the same numbers (median ratio 1.000): no unit change.
Emitter animations (EA**) and eft2's rotation order (Rx Ry Rz) and world gravity are modelled; with them
the down smash's columns parted and the converter's two bugs showed (catalogue). Still open: the dash's
droplets fly higher in both columns than in Ultimate's footage.

## Bug catalogue

Each row: the bug, where it happened, and what now stops it. `port_check` codes in brackets.

| bug | ports | guard |
|---|---|---|
| joints past 26 in table 0: hitboxes over the whole stage, a stretched tail | Sephiroth t20, Squirtle v2-4 | `--joints` writes table 1 [M1] |
| base table-1 joints as stand-ins: the head came off | Hero / Steve fix 9 | own bones (`add_joint_bones`) [M2] |
| NUD bone range 0-N, rigged polygons unflagged: a pillar, invisible, a crash | Incineroar, Sephiroth t19 | `nud.write` [M3, M4] |
| `model.nud` shipped without `model.nut`: wrong textures | Hero fix 17 | plan ships both [M5] |
| the model step's material pacs shipped: shields gone | Hero fix 74 | plan ships the motions step's [M7] |
| MSC globals past index 0x86: the fighter's MSC stopped (no actions, no respawn) | Hero fix 79 / 80 (Zoom 2 U) | reuse a global [C5, WARN: the limit is inferred, not found in the VM] |
| `main.pac` rebuilt from an older install's: a move T-posed (its animation missing) | Hero fix 79 (forward tilt 2) | every motion-table animation in the installed `main.pac` [M8]; build on the newest one |
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
| an additive part on a premultiplied template drawn as a covering blend (the rainbow over the smash flash) | Squirtle (sys_smash_flash) | eft_pixel: alpha out 0 for Ultimate's additive parts (ONE / INV_SRC_ALPHA then adds) |
| Ultimate's alpha_process 4 (erosion: sat((tex.a - alpha0) x 4) x alpha1) read as tex.a x a0 x a1: splashes solid and lingering | Squirtle (down smash, dash) | eft_pixel alpha mode 4; vfxb_to_ptcl sends alpha0 as the threshold, mean alpha1 as the gain |
| emitter angles re-expressed as Z first (eft2 turns X first, as eft: main.bin 0x88320 / 0x8D0A0): multi-axis and EAER-swept emitters on the wrong plane | Squirtle (down smash water standing up), Sephiroth since test 44 | `eft_rotation` keeps the angles |
| is_rotate honoured on directional meshes only: other particles kept spins Ultimate zeroes | Squirtle's up-smash columns (type 5 meshes) splayed into a V | every particle's disabled axes zeroed (main.bin 0x8B8A0) |
| eft2 particle type 4 (XZ polygon) mapped to eft's 4 (the emitter's frame): flat discs / rings stood upright | Squirtle's up-smash ripple glow, a blue haze | `TYPES[4] = 2` (eft's XZ plate) |
| effect scripts always took the facing-left branch of Ultimate's `if LR < 0` (its mirrored `_r` effects dropped): asymmetric effects wrong facing right | Squirtle's forward / down smash water curling up over him | `fix_lr_split` + `LR_FACING`: chosen in game (Float_Var_Compare facing < 0) |
| a mesh's other sampler on its own UVs brought in as its mean, even when it varies along one axis only (a gradient) that the main sampler neither moves nor scales | Water Gun's crowns: ef_cmn_grade00 (mean 0.21) as their alpha: the shot a fifth as opaque, a faint line | `one_axis`: such a sampler multiplied in row by row (exact) |
| dissolves (custom shader 8) dropped: a colour texture grey only within compression noise (5 - 10 / 255 apart once display-encoded) failed the 2.5 / 255 grey test; a mask on its own UVs (the colour scrolling over a still mask) had no program | Squirtle's smash waves, up-smash columns, Water Gun crowns: plain fades where Ultimate's water is eaten away | grey test at 12 / 255; eft_pixel `mask1`: the mask live as texture 1 (sampler 1's alpha, its own UV animation), texture 0 its colour |
| circle volumes (eft2 types 1 / 2) kept the template's sweep: eft2 centres the sweep on its start and divides an even circle by num_divide_circle, eft starts at it and divides by the emission's particles | Squirtle's forward / down smash splashes (one division: one point in Ultimate) spread round a 9 - 15 unit circle, the water in pieces (found with the vfx_trace births) | converter writes ptcl volume_sweep_start / param / random / surface (cross_f 0x04A4B818 / 0x04A4BF18, main 0x90C40 / 0x90E20) |
| eft2's distance emission (emit_dist_enabled: a particle a dist_unit of the emitter's own movement) emitted by time: about half the particles (splash1 a fifth) | Squirtle's forward / down smash water | converter: per-frame rate keys from the emitter's EAET path (`dist_emission`, main.bin 0x8D340); movement from the fighter / an article stays by time (noted) |
| an emitter turning while it emits, converted at its keys only: another path between them | Squirtle's down smash (the water stood up) | converter: every frame between keys (found with fx_render.py) |
| eft2 directional meshes sent along a fixed emitter axis drawn as eft type 3 (turned upright to face the camera) | Squirtle's down-smash / run waves (curtains, user's test 1 clip) | converter: type 4 (the emitter's frame), as Hero's whirlwinds |
| eft2's type 3 read as "directional": it is the XY polygon (its vertex program places a mesh by the emitter's matrix at birth and reads no velocity), and eft's type 4 is not the emitter's frame (its program aims the mesh's Y along the particle's world motion, X = normalize(emitter Y x motion)) | Squirtle's forward / down smash waves stood on end, each fanned by its own spread and gravity: separate curtains where Ultimate shows one low band (tests 11-13) | converter: eft2 type-3 meshes -> eft type 1 (v_inEmtMat x the turned, scaled vertex + v_inWldPos); fx_render draws eft type 4 by the decoded program |
| eft2 type-3 meshes at rest converted to eft type 4 ("keeps the emitter's frame at rest"): type 4 aims the mesh's Y along the particle's motion, so a still particle has no frame and every vertex lands on its position | Squirtle's down-smash dust crown (sys_whirlwind_l / r's impact meshes) drawn as nothing; his ripples, landing smoke, attack arcs too (54 emitters), found by running the bank's own vertex programs (tools/latte_exec.py) | converter: eft2 type-3 meshes, still or not, -> type 1; `port_check` E4 (still type-4 meshes: ERROR when never moving, WARN when only their bone moves them) |
| eft2 type-5 meshes converted to eft type 4 (flat ones in test 16, curved ones in 17: Waterfall's wave sheets went edge-on, streaks): its X is emitter Y x motion, zero, so every vertex of the mesh's width lands on one line (drawn as nothing). eft2's type 5 is a directional billboard (Y along the last movement, X = movement x the eye vector: its program run in mx_exec), which eft's type-3 mesh programs reproduce | Squirtle's up-smash water columns, the crown, the double-jump ring (test 15: up smash "less full") | converter: flat type-5 meshes -> type 3; port_check E5 upright-type4-mesh |
| eft2 type-3 quads drawn as eft's directional type 3: eft2's type 3 is the XY polygon for quads too (smoke1's program draws the same square whatever the motion) | the common attack / dash / run / turn / landing smokes' smoke1 / smoke2 (edge-on or nothing) | converter: type-3 quads -> eft type 1 (the particle centre kept as rotBasis) |
| the template's speed stretch (ptcl 0x7F4, CB2 gravityParam.w: Y + it x speed in the directional programs) left as the template had it | Squirtle's up-smash columns stood 40 high at once (13 in Ultimate) | converter writes eft2's add_vel_to_scale (under add_scale_y), else 0 |
| particle random rotation as eft2's: eft2 turns init + random x (U - 1/2) (its vertex programs), eft init + U x random (cross_f 0x04A5DAB4) | every randomly turned part turned too far one way (Waterfall's spikes behind Squirtle) | converter: eft init = init - random / 2 |
| eft's random spin reversal (0x2FC - 0x2FE) left as the template had it | parts flipping their spin at random, or not, unlike Ultimate | converter writes eft2's rot_rev_rand |
| a directional refraction piece (eft2 type 5) on the corpus's billboard distortion template: stood upright | Waterfall's 80-unit refraction band beside the column (the streaks) | converter skips refraction pieces of types 3 / 4 (the corpus has distortion templates of types 0 - 2) |
| two samplers with equal UV settings taken as one UV set though each draws its own random scroll (eft2: sampler 0 from the particle's random x, 1 from y; eft the same) | dissolve masks laid exactly over the colour texture: cut nothing at threshold 0 (Waterfall's spikes 1.3x as full) | converter: a random UV part means separate UVs (same_uv); the mask drawn live as texture 1 |
| a dissolve's mask sampler also combined into the colour / alpha | faint fill where the texture is empty | converter: exact_texture leaves the mask out |
| random life as eft2's percentage of the life: eft2 runs its curves on whole frames, floor(life x (1 - r U)) | parts eroding / fading slower than Ultimate's (Waterfall's spikes 6.5 frames to 5.45) | converter: eft life ceil(life) - 1, random frames for the same mean |
| eft2 type-6 meshes (directional: Y = motion, X = motion x Y, Z = X x motion) taken as eft type 4 as they stand: eft's type 4 frames them turned 180 degrees about the motion | up smash's base band hung under the floor; the dash / run-brake ripples sank under the stage and stuck there (test 18, in game) | converter: a type-6 mesh turned 180 degrees about its Y (x, z negated) |
| fx_render feeding an eft2 particle's scale Z from its X: eft2 gives each axis its own (the emitter's 3-axis scale copied at main.bin 0x87CF0, the particle's x (1 - random x U) at 0x90738; one U when the X and Y randoms are equal) | the renderer's Ultimate side drew up smash's base band 1.7x too low (scale 1 / 0.5 / 1.7), so a right-height conversion looked too tall | renderer fixed (sysScaleAttr xyz, EASL Z) |
| an eft2 mesh's scale curve Z (its vertex programs read the key's z) taken as X: eft's curve has X / Y and its programs scale Z by X | up smash's base band kept growing taller (Z 0.2 -> 0.96 -> 0.3 in Ultimate while X / Y grow 0.77 -> 1.3); putting Z's curve on X instead narrowed the band's pieces heading toward the camera | converter: Z(t) / X(t) grafted onto v_inPos.z (eft_vertex.graft_zcurve, t = age / mean life); a template that can't take it is noted |
| main_texture taking a dissolve's sampler 1 (its mask, white in colour) as the picture when sampler 0 is a distortion map: Ultimate's program (shader 32) draws colour 1 -> 0 by sampler 2 x 1 and its alpha from sampler 2 | sampler 2 averaged in: Waterfall's wave lines (waveline1_2) were soft white blobs, the "whiter, wispy" look (test 18, in game) | converter: such a dissolve takes sampler 2 as the picture, the mask live as texture 1; distortion() moves sampler 1 only |
| colour mode 2's texture (the mix weight of colour 0 / 1) prepared as a colour: UNORM display-encoded, sRGB as stored; Ultimate mixes by the linear value in linear light | every blue-to-white water part pulled towards white (Waterfall's wave lines 0.71 median to Ultimate's 0.64) | converter: mix_weight_curve, a per-emitter weight curve fitted to Ultimate's linear mix over the colour tracks (one grey curve: dissolves keep their grey check) |
| a dissolve's threshold put in colour 1's track though colour 1 animates and colour 0 is constant | colour 1 held at its life mean: young wave lines pale (Ultimate's colour 1 runs (0.00, 0.18, 0.28) -> (0.56, 0.72, 0.82)) | converter: the threshold takes colour 0's track when colour 0 is constant and colour 1 animates |
| a sampler's UV scroll / scale / turn values used though its tex_anim switch is off: Ultimate's vertex programs leave those UVs alone, start, change and random alike (water1 with all three off; a common ring with scale 0 and the switch off draws whole) | Waterfall's water1 sheets: their dissolve mask slid and stretched off the water and ate the sheets by mid-life (67% of Ultimate's cover) | converter: gate_uv_anim makes a switched-off component identity |
| eft2's random texture flips (tex_anim inv_rand) never written: eft's slot bytes 0x4DA / 0x4DB left 0 | no part flipped; eft flips every slot on one random where eft2 flips each sampler on its own (sampler 0 random x, 1 random z), so a mask flipped with its water never lay mirrored over it | converter: set_inv_rand; an axis both slots flip is left to slot 0, so the two lie mirrored apart on half the particles as in Ultimate |
| fit_texture halving a texture while the change over all channels together stays under 1% | a faint channel's detail lost: water1's dissolve mask (alpha mean 0.10 beside white rgb) went 256 x 128 -> 32 x 32, blurred | converter: each channel against its own level |
| an alpha section of 0 (the fade from the first frame) | alpha 0 on a particle's first frame on templates dividing by the section (water1 on the two-texture template) | converter: alpha sections at least 1% |
| a universal-shader emitter (Ultimate's own programs lowered: tools/ult_shader.py) keeping its GPU template's GPU-calc flags (emitter byte 5 bit 0x80, the key's byte 4 bit 0x02): eft moves nothing on the CPU and the records hold birth values, which the programs (written for CPU particles' current ones) draw as they stand | Squirtle's effects test 22, in game: 145 of 355 parts frozen, many at the stage's origin (up smash's ripple / waves / splashes, the dash and run-brake waves); fx_render missed it, taking GPU from the program's v_inVec | converter clears both flags (vfxb_to_ptcl.universal_shader: the CPU's streams follow the program's attributes, cross_f 0x04A57DA4); fx_render follows the flag; `port_check` E6 universal-gpu |
| a universal-shader emitter whose program reads the particle's last movement (Ultimate's sysLocalDiffAttr -> `v_inWldPosDf`) on a template that isn't directional: eft works that stream out only under the emitter's +0x308 bit 0x10 (vanilla: its types 3 / 4 only), else it holds whatever the particle slot's last occupant left | Squirtle's effects test 23, in game: thin white water streaks from Squirtle up to the top of the screen for a frame or so in several moves (the common attack / dash / run / turn smokes, up smash's splash1_2, Water Gun, Waterfall's end: 20 emitters); fx_render fed velocity and drew them right | converter sets bit 0x10 when the program reads the stream; fx_render warns; `port_check` E6 universal-diff |
| the fighter's effect tint (fighter_param.prc `common_effect_0`, put by Ultimate's engine on `sys_attack_line` / `_b` and `sys_attack_arc` / `_b` / `_c` / `_d`) never passed: port.json `tint_for` was left empty | Squirtle's effects test 24: his jabs, forward tilt and up air white where Ultimate's are green (0.32, 1.6, 0.4) | pipeline default (`tools/ultimate_tints.py` -> `--tint-for`, also into universal programs' colours, linear); CLAUDE.md: effect colours checked against Ultimate's |
| effect macros the script translator had no form for dropped without a word, and `*_FLIP` ones made the plain macro | Squirtle's test 24: no up-tilt speed line (`EFFECT_FOLLOW_FLIP_ALPHA`), no back / down / neutral air winds (`EFFECT_FOLLOW_RND`, `_FLIP_ALPHA`), forward tilt's arc wrong facing left, the speed line's script colour (`LAST_PARTICLE_SET_COLOR`) dropped | translator: Smash 4's command of the same name (crc32 = ACMD id), flips with their type; uniform script colours baked; `port_check` E7 effect-macros |
| a universal-shader emitter keeping eft's colour scale (+0x778) from the conversion: eft's emc multiplies it into the program's colours, which apply Ultimate's own scale already (c9 word 236) | Squirtle's tests 22-24: 224 parts brighter than Ultimate's (x 1.04 to 3); fx_render fed emc 1 | converter writes 1; fx_render feeds eft's emc; `port_check` E6 universal-colour-scale |
| an Ultimate looping rumble (`set_rumble(rbkind_loopattack, .., true)` then `rbkind_erase`) translated as a plain `Rumble` on a Smash 4 kind whose pattern never ends (param/pad_rumble/rumble_pattern_data*.bin: an 8000-times loop in kinds 2, 3, 8, 9, 26, 34-36; kind 6 runs 1000 frames). Smash 4 has no rumble stop | Squirtle's up smash rumbled on for seconds (user) | translator: those kinds always `Rumble_Loop` (tied to the status, as vanilla plays them 1328 times to 27), `ultimate_acmd.RUMBLE_ENDLESS`; `port_check` S8 rumble-endless |
| no low models (`model/body/l00`-`l07`): the off-screen magnifier and 8-player Smash draw them | Squirtle invisible in the magnifier (user) | pipeline step `low-models` (copies of cXX, after the motions step); `port_check` M6 low-models |
| a new kind's records in `bgm_fighter.fbb` / `commonsoundtable.csb` never found: the executable names those files' records itself, by index, from tables of the vanilla roster (58 / 62 names), and matches them by the fighter's name; and the csb had no record for the new kinds at all | Squirtle extras 2 (user): no KO screams, no crowd chant; the extended fanfare file changed nothing | kind_expand.py grows both name tables (`SOUND_NAME_TABLES`); `fighter_extras.py common` gives each new kind its base's csb record (fanfare: `fighter_extras.py fanfare`); `port_check` A2 sound-names, A3 common-voices, A4 fanfare |
| eft2's world gravity not set on eft's emitters: gravity turned with the emitter | Squirtle's down smash | converter writes ptcl `world_gravity` (0x2F8, cross_f 0x04A62620) |
| a copied article keeps its base's native per-frame code: Squirtle's water bounced like Mario's fireball and died at close range | Squirtle v2-v5, Supamario's Kamehameha | `"nop2"` in the record (port_bases.json `weapon_nop2`) [W1] |
| Ultimate's negative shield damage (magic: Hero's spells -1 to -13) written as is: Smash 4 reads the Hitbox command's ShieldDamage unsigned, so 0xFFFFFFFF is a huge one | Hero (user, after Supamario fix 90): every spell breaks shields | Woosh's set to 0 (`brave_build.py` `no_negative_shield`; the rest kept at the user's choice); `port_check` S9 shield-negative (WARN) |
| a charge's endless effects (`EFFECT_FOLLOW` in the hold motion) left on when the status's own MSC changes motion: Ultimate's release / cancel scripts never turn them off (its status code does), and a hand-written MSC that only swaps the motion keeps them | Sephiroth test 59 (user): "the refraction effect never goes away when released" (Flare) | the MSC turns the hold effects off on the change (`edge.c` `edge_n_charge_off`, plain and turned-variant ids); ids written in MSC checked against `NAME_effects.json`: `port_check` E8 msc-effect-id |
| an Ultimate vertex program with an output location past the shader runner's slots (`mx_exec` gave each vertex 8: locations 0 - 7) | Sephiroth test 61's bank build: `edge_octaslash_charge`'s wind1 (program 621) writes location 8; the probe wrote past the buffer and the converter died ("double free or corruption") | `mx_exec.NOUT` 16, and the C++ generator refuses any in / out location past its slots (an error, not corrupt memory) |
| a quad's texture channels read as a radial gradient one by one: a channel that looked like a one-way gradient came out 64 x 64, the others at their own size | Sephiroth test 62's bank build: `edge_senkou_hold_attack` (a colour channel qualified, the alpha didn't): the converter died stacking them | the alpha decides once (`radial_gradient_axis`), every channel read along that axis |
| a fighter's effect bank too big for the ONE 44 MiB effect heap every bank in a match shares (~17 KB a converted shader entry: each gets its own program copy, + 0xA00 an emitter) | Sephiroth tests 61 / 62 (Octaslash's / Scintilla's effects added, 680 / 714 shaders, ~13.5 / 14.2 MiB): crash at match load; the user's bisect found the bank (D1 / P1 / P2 / P3: not the file size or counts) | `tools/effect_heap_patch.py` (44 -> 60 MiB, from the resource heap) in the executable; `port_check` E9 effect-heap |
| a base motion slot that loops (motion table flag 0x2) given to a move that ends: its motion never ends, so a status waiting for the end (`MotionModule(0x2712)`) never leaves | Sephiroth test 62b (user): "down special loops infinitely and breaks his MSC" (Scintilla's slash on Zelda's SpecialLwLoop 0x249 / 0x24D) | a `"flags"` override in `tools/extra_kinds.json` "motions"; `port_check` M9 loop-slot |
| ACMD / MSC user variables (`VAR_`, `TIMER_`, `KINETIC_TYPE`, `SLOTn_SHARED_k`) reading 0: `position_vars_cave.py` applied after `acmd_ext_cave.py` restores the original word at the hook `0x04B79000` | standard `build/cross_f.rpx` since Hero fix 79 (found building Sephiroth's Shadow Flare, test 64) | `acmd_ext_cave.py` applied last (`edge_specials_build.py --rpx` does); `port_check` X1 cave-hook |
| a weapon MSC with statuses past its status count (`global7` in its setup, copied from a smaller weapon's): changes to them are refused | Sephiroth test 64 (user): "Side special doesn't create the orbs" (the shot never left its hit status) | `global7` = the statuses it registers; `port_check` W2 weapon-status-max |
| a brand-new article's multi-hit (rehit) ends at its first hit, its following effects with it: the base weapon's hit method removes it | Sephiroth test 64 (user): Scintilla "doesn't multihit", its effects "not full" | `"on_hit"` in the record (0: stay in status 0), shield bit 0x4 in `"on_hit_bits"`; `port_check` W3 weapon-rehit |
| the game crashes when a new article's hitbox connects (Cemu's log: only `GX2RSetAttributeBuffer` errors): its ID or Part is past its base weapon's AttackModule arrays (dein: IDs 0-6, Parts 0-1), which the game never checks, so the hit record is written over other memory | Sephiroth tests 68-69, bisect 70 (user): Shadow Flare "crashes when it hits an opponent"; only the orb hitboxes (Parts 2-4) off didn't | IDs / Parts within the base's (`docs/native-notes.md` "AttackModule sizes"); a hit record of its own per wave with ACMD `Hit_Log_Clear(Part)`; `port_check` W4 weapon-parts (`WEAPON_ATTACK_SLOTS`) |
| an Ultimate move's per-fighter values (Shadow Flare's `edge_flare_radius` / node / offsets) replaced by one value for everyone: the orbs' ring sat inside big fighters and its orbiting hitboxes kept hitting the target | Sephiroth test 70 (user clip): Donkey Kong "the same hitboxes that the orb use multihit many times over" while circling | the per-fighter table by the target's kind (`SLOTn_KIND`, `tools/edge_flare_targets.py`); `port_check` F1 flare-targets (a new fighter without a row) |
| an article's MSC timing its script by a frame counter that runs in hitlag: the script (which stops in hitlag) is behind it, so a multi-hit move's later parts come after the MSC removed it | Sephiroth test 66 (user): Scintilla's "finishing hit also doesn't land" (multi-hit hitlag; the removal at 17 counted frames) | count the MSC's frames only outside hitlag (`StopModule(0x1)`: `weapons/flash.c`) |
| Kirby's copy of a new kind granted as its base's: his copy hat and motions still load per fighter in the match by kind, and the loaders (`0x030C5240`, `0x030C4694`, release `0x030C5BBC`) skip kinds `>= 0x3A` | Supamario fix 91: Kirby T-posed in the copied move, no hat (no Mario in the match) | pipeline default: `weapon_expand.py` `kirby_copy` maps the kind in all three (`KIRBY_COPY_RES`), tested by `weapon_expand_test.py` |
| base counters / native per-frame code acting on the port | Hero fixes 19, 62 | `reference/port_bases.json` traps |
| articles after the base's special entry never spawned | Hero fix 15 | weapon_expand.py |
| caves overlapping | Hero v4b | cave tests with `--others` |
| stock icon = the select render shrunk | Squirtle | `--stock-icon` (Ultimate's chara_2; its icons have no eyes: user) |
| portraits darker than Smash 4's | Hero fix 75 | ultimate_portraits.py tone curve |
| mirrored UVs black (sampler wrap) | Hero fix 70 | converter (Ultimate's wrap) |

## Open

- Statuses written by hand still need the status code for accuracy (Withdraw's speeds): ssbu-recomp.
