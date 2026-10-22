# Smash 4 effect banks: the .efc, effect ids, effect models

A fighter's effect bank is `fighter/<name>/effect/<name>/<name>.010d0000.efc` + `.ptcl` + `model/`
(the Final Smash bank the same under `effect/Fin<Name>/`). `efc.py` reads / writes the .efc (all
118 vanilla files round-trip byte for byte) and adds entries.

## Runtime (cross_f.rpx)

- **Bank load** = registration: `0x0334CB20` -> `0x032F1388(mgr [0x10353CA4], bank id, path, ...)`.
  It takes a slot (`0x032EFEA0(mgr, bank)`: banks are grouped by category `bank >> 8` (1 common,
  3 fighters, 4 Final Smashes): count `[0x101906D4 + 4 * cat]`, first slot `[0x10423B2C + 4 * cat]`;
  41 slots of 0x80 bytes at mgr `+0xB8`, `+0` = the bank id), loads `"%s.%08x.efc"`
  (`0x10190720`, with `0x010D0000`), checks 'EFC', keeps: `+8` the file, `+0xC` the entries,
  `+0x1C` the mesh-switch records, `+0x6C` the names; loads `"%s.%08x.ptcl"` (`0x10190738`) into the
  eft system (`+4` its resource id); then for each model name `model/<name>/` (`0x10190718`, a
  model resource, type 9) and its `model.omo` (`0x1019072C`) into arrays at `+0x28` (16 bytes a
  model) / `+0x2C` (8 bytes); `+0x24` the model count; `trail` (`0x10190710`) for sword trails.
- **Spawn** (the id decoder): the ACMD effect commands -> `0x032F0110`: `bank = id >> 16` ->
  `0x032EFEA0` -> slot; an instance from the pool at mgr `+0x1540` (0x1C0 each) ->
  `0x0334D8D8(inst, handle, slot, id, ...)`: `index = id & 0xFFFF`, must be `< [efc+8]` (the entry
  count), `entry = [slot+0xC] + index * 16`:
  - `+0` flags -> `inst+0x144`; `0x100` / `0x200` pick the effect-budget counter the effect counts
    against (`0x1043xxxx` counters; over the limit an effect without `0x80` is dropped), `0x80000`:
    the draw group = the call's parameter + 3; `0x2000` / `0x10` / `0x800` / `0x400` are set at run
    time (non-uniform scale, ...).
  - `+4` emitter set: if > 0, `0x04A55BF0(eft, &handle, ..., [slot+4], set - 1)` creates the .ptcl's
    emitter set `set - 1` (1-based; 0 = none).
  - `+8` model: if > 0, the model `[slot+0x28] + (model - 1) * 16` is instanced and its
    `model.omo` played (`[slot+0x2C] + (model - 1) * 8`; `0x0330A590` / `0x0330A5F8` set its frame).
  - `+0xC` / `+0xE` (u16 first, 1-based / count): mesh-switch records (u16, u16 + a mesh name):
    which meshes of the model show when (e.g. Bayonetta's skulls `skull1-3_O_OBJ_O_HIR`).
- So an ACMD id `0x0BBBnnnn`: bank `0xBBB` (0x100 common, `0x300 + kind` fighter, `0x400 + kind`
  Final Smash; Mario 0x303, Supamario 0x341), entry `nnnn` of that bank's .efc.

## File

Big endian. `+0` 'EFCF', `+4` u16 variant (0 in all vanilla files; 1 = a u16 per model after the
mesh records), `+6` u16 version 7, `+8` u16 entries, `+0xA` u16 model names, `+0xC` u16 mesh
records, `+0xE` 0; entries (16 bytes: u32 flags, u32 set (1-based), u32 model (1-based), u16 mesh
first (1-based), u16 mesh count); mesh records (u16, u16; 0x30 / 0x31 in the second); model names
(one per entry that has a model, in entry order, duplicates included; an entry's model number is the
first occurrence of its name); mesh names (one per mesh record). No padding in any vanilla file.

Flags seen (2,499 entries): 0 1129, 0x100 1024, 0x110 76, 0x10 71, 0x200 65, 0x120 65, 0x210 26,
0x20 25, 0x5 23, 0x105 11, 0x80100 6, 0x220 5, 0x1 / 0x103 / 0x80110 4, 0x3 2, 0x101 / 0x130 /
0x40 / 0x400005 1. For a new effect copy the flags of a vanilla one that behaves alike (Mario's
fireball / cape entries: 0x100).

Every entry's set is at most the .ptcl's emitter-set count; nine banks have sets no entry uses.

## Effect models

`model/<name>/`: an ordinary model folder (444 in the vanilla fighters): `model.nud`, `.nut`,
`.vbn`, `.omo` (bone animation, played from the spawn), `.mta` (material animation), `.xmb`. Their
materials use the effect shaders `0xB02xxxxx` (`0xB0201000`, `0xB0201100`, `0xB0221100`,
`0xB0241100`): additive blend (src 5 / dst 1) or src 5 / dst 2, z-write off, cull none, with
`NU_eff*` properties: `NU_effColorGain`, `NU_effTransUV` / `NU_effScaleUV` / `NU_effRotUV`
(`NU_effMaxUV`, `NU_effOffsetUV`), `NU_effCombinerColor0/1`, `NU_angleFadeParams`,
`NU_materialHash` (the MTA's link); textures `0x15xxxxxx`. Examples:
- Samus's Zero Laser (`FinSamus/model/EffFinSamusMain`, 161 frames): a sphere whose texture scrolls
  (`NU_effTransUV` animated by the MTA, `0xB0221100`) inside flare planes faded by
  `NU_effColorGain`.
- Mario's cape (`EffMarioSupermant1`, 27 frames): cylinders, `NU_effTransUV` + `NU_effColorGain`.
A beam is therefore a model we can author with `tools/nud.py` (write), `tools/mta.py` (write: the
TransUV scroll / ColorGain fade curves), `tools/omo.py` (bone scale for its length), `tools/nut.py`
(its texture). No model needs an emitter: an entry can be model-only (set 0; Mario's cape entries
0x14 / 0x15).

## ACMD (`tools/acmd.py`)

Effect commands take the id as their first parameter:
- `Graphic_Effect` / `Graphic_Effect2` / `Graphic_Effect3` (0xC84B610E / 0x46985674 / 0x104F0834):
  Graphic, Bone, X, Y, Z, XRot, YRot, ZRot, Size, RandomX..Z, RandomXRot..ZRot, Terminate: one-shot
  at a bone.
- `External_Graphic` (0xFC061097), `Graphic_Effect4` (0x0EDC8BFD), `External_Graphic_Effect2`
  (0x089EBF6C, Final Smash ids): Graphic, Bone, X..ZRot, Size, Terminate: following the bone.
- `EFFECT_FOLLOW_FLIP` (0x7EF50766): GFXRight, GFXLeft (facing variants, e.g. the cape's `_L`
  model), Bone, X..ZRot, Size, Terminate (floats as raw bits: acmd_info marks them ints);
  `EFFECT_FOLLOW_FLIP_ALPHA` / `_COLOR`, `EFFECT_FLIP`.
- `Terminate_Graphic_Effect` (0xE8F38CA3): Graphic, 0, 0: stops a looping one.
- `LAST_EFFECT_SET_COLOR` (r, g, b), `LAST_EFFECT_SET_ALPHA`, `LAST_EFFECT_SET_RATE` (speed),
  `LAST_EFFECT_SET_SCALE` on the last spawned.
Mario's own ids in his scripts: `0x0303000x` (External_Graphic 13 ids, Graphic_Effect2 3,
EFFECT_FOLLOW_FLIP 2, Graphic_Effect4 1, Terminate 3, FOLLOW_FLIP_ALPHA 0x14/0x15 (the cape
models), `0x0403000x` Final Smash.

## A brand-new effect id for Supamario

1. Author what it shows: emitter set(s) appended to `supamario.010d0000.ptcl` (the .ptcl tool,
   scratchpad/fx/ptcl) and / or a model folder `effect/supamario/model/<Name>/` (nud / nut / vbn /
   omo / mta / xmb; texture ids in a free `0x15xxxxxx` range).
2. `efc.py add IN OUT --set <1-based set index or 0> [--model <Name>] --flags 0x100`: prints the
   entry index `nnnn` (Supamario's copy of Mario's has 22: the first new one is 0x0016).
3. Call `0x0341nnnn` from Supamario's ACMD (`acmd.py`: `Graphic_Effect`, `External_Graphic`,
   `EFFECT_FOLLOW_FLIP`, ... `Terminate_Graphic_Effect` for a looping one).
No executable change: the bank is already loaded for kind 0x41 (kind_expand / base_effects), the
entry count is read from the file, models are loaded by name at bank load.
Not tested in game: a model-only entry with a new model folder (Mario's cape entries show the path
works), the budget flags for a large beam.
