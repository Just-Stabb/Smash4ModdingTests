# Wii models and animations (MDL0 / CHR0) to Smash 4

Two converters for BRRES-era Wii files (the formats BrawlBox / BrawlLib read), first used for Greninja's Parabeetle
(fighters/gekkouga/README.md "Parabeetle v1"). Both only parse their input (bounds checked); nothing in it runs.

## `tools/mdl0_to_nud.py`: MDL0 v8 - v11 -> a model folder

```sh
python3 tools/mdl0_to_nud.py MODEL.mdl0 --info                      # bones, arrays, objects, materials and their TEV
python3 tools/mdl0_to_nud.py MODEL.mdl0 TEX_DIR OUT_DIR --scale 1.25 --face +z --tex-id 0x4030A000 \
        --env-bake MATERIAL                                          # -> model.nud / .nut / .vbn / .jtb / .sb / .nhb / .xmb / .flp
python3 tools/mdl0_to_nud.py verify OUT_DIR                          # read the written files back
```

- `TEX_DIR`: the model's textures as PNG, named as its texture references.
- `--face`: the MDL0 axis the model's head points along; a TransN root is added that turns it to +Z (Smash 4 articles
  face +Z and are turned by their facing). Wii models usually face +Z already.
- `--scale`: positions and bone translations (give `chr0_to_omo.py` the same).
- `--tex-id`: the first texture id (keep it in the owner's range, e.g. 0x4030xxxx for Greninja's articles).
- Every vertex is rigged to the node GX draws it with (single-bound objects to their node, weighted ones through their
  position matrix index); one bone a vertex (MDL0 envelopes, blended weights, aren't handled: an error names them).
- Triangles are turned to counter-clockwise: GX's front faces are clockwise, the NUDs' counter-clockwise.
- Materials become Smash 4's lit fighter body shader (0x9A011063: colour, a flat normal map, the shared ramp) with the
  source's wrap and culling. Wii models of this era light themselves with sphere maps on the camera-space normal
  ("lm_01e" / "lm_02e"); the game's lighting takes their place. `--env-bake MATERIAL`: a material that adds an
  EnvCamera reflection to a flat colour (its TEV: `CPREV + TEXC x Ax`) gets one texture, colour + k x the reflection,
  addressed by each vertex's sphere-map coordinates seen from the side facing right (what GX's texgen computes per
  vertex). `--info` prints each material's TEV stages to check what a material does first.
- model.sb / .nhb / .xmb are reference/enemy_model_defaults' (tools/s3ds_enemy.py); model.flp an empty mirror table.

## `tools/chr0_to_omo.py`: CHR0 v4 / v5 -> OMOs in a main.pac

```sh
python3 tools/chr0_to_omo.py MODEL.mdl0 OUT/main.pac NAME=wait.chr0 NAME2=rise.chr0 --scale 1.25 [--hold BONE:1] [--info]
```

- `NAME`: the OMO's name without `.omo`; an article's motion info keys it by `tools/mtable.py anim_hash(NAME)`.
- Every frame is sampled (Hermite keys with their tangents, the linear formats as they are), each bone's local
  translation x scale, rotation (XYZ Euler degrees, R = Rz Ry Rx, as the MDL0) and scale; bones without a track keep
  the bind pose; TransN (the added root) constant.
- `--hold BONE:AXIS`: that bone's translation on that axis held at 0; the values taken out are returned
  (`convert(...)['held']`), for an object that moves itself by them (the Parabeetle bobs its whole article so its
  collision line follows its shell).

## Checking the result

`python3 tools/nud_preview.py MODEL_DIR OUT.png|gif [--pac main.pac --anim NAME[:FRAME]] [--yaw 90]` renders the written
files (textured, culled, lit). `tools/gekkouga_clones_test.py` (`parabeetle_data_tests`) compares the Parabeetle's
written files with its source: bind pose, vertices, UVs, the baked shell, and every OMO frame against its CHR0.
