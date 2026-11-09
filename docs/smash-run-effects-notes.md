# Smash Run effects notes: Furiijio's mist, colour modes, billboard effect models (effects v3)

These notes are meant to be merged into `docs/smash-run-port.md`, under "Enemy particle effects" / "Enemy effect
models", plus a step entry.

Package: `smashrun_effects_v3.zip` in the session scratchpad. It is data only, merged on top of step 2h, and replaces:
- 43 `.ptcl` files;
- 69 `model.vbn` files;
- optionally `data_wiiu_overlap/`: 5 `.ptcl` and 6 `.vbn` files.

No `.efc`, `.nud`, `.nut`, `.omo` or `.mta` changes. The HEAD converter's output matched every shipped file
(`smashrun_effects_v2`, step 2b / 2c / 2h), so each replaced file differs only by the fixes below.

## Furiijio's mist: what the logs show

The uploads dc67f861 (1260 `cl` lines, 12 beam snapshots) and e48d89f5 (2742 lines, 26 snapshots) were decoded
against the eft code in cross_f.rpx. The eft EmitterInstance fields were read from:
- the emitter calc, 0x04A64CE8;
- the CPU particle pass, 0x04A65480;
- the GPU-ring pass, 0x04A667A0 ff.;
- particle creation, 0x04A5C628 / 0x04A5D7C0 ff.

**EmitterInstance fields** (the first 0x100 bytes):

| Offset | Meaning |
|---|---|
| +0x10 | live particles (0 = skip the draw pass) |
| +0x1C | the next emission gap (0x454 + random 0x458) |
| +0x20 | state bits (0x4 = stop emitting) |
| +0x24 | the emitter's 0x308 flags |
| +0x30 | frame |
| +0x38 | previous frame |
| +0x3C / +0x40 / +0x44 | emission timer / last emission frame / fraction |
| +0x58 | fade alpha |
| +0x5C | frame step |
| +0x64 | particles written to this frame's draw buffer |
| +0x68 / +0x6C | GPU emitters: the ring buffer's write index / capacity |
| +0x7C | the set |
| +0x80 | the controller |
| +0x84 / +0xB4 | the emitter's RT / SRT world matrices: set +0x218 / +0x1E8 x the instance's local +0x2A8 / +0x2D8 |

Emission is at 0x04A6507C ff.:
- the gap is +0x1C x the controller's +4;
- the start / end tests use 0x44C / 0x450 against the set's +0x2AC.

**Every snapshot (38 beams)** shows the cloud working:

| Emitter | Particles alive (beam frame 2 -> 20) | Written to the draw buffer | Notes |
|---|---|---|---|
| BG | 1 -> 3 | the same | gap 8 |
| snow | 1-2 -> 2-4 | the same | gap 0-6 |
| cool_air | ring 4 / 8, then 8 / 8 | the same | gap 6; a GPU emitter (particles written once into the ring, 0x04A6680C; the shader animates them) |

- **Alpha:** +0x58 = 1.0 every time (no fade).
- **Matrices:** at Furiijio's body centre:
  - the set's SRT is 1.5 x identity;
  - snow and cool_air carry their 3DS emitter turn Rx(90 deg);
  - the set's particle scale (+0x264 / +0x268) is 1.5;
  - its colour / alpha (+0x278..+0x284) is 1.

So the mist is not culled, stopped or faded, and its particles go to the GPU every frame. These were checked and
are not the cause:
- **Alpha track.** CPU (0x04A5C50C set-up, 0x04A641C4 hook, called from the calc at 0x04A62744) and GPU (the vertex
  program's alphaAnim0 / 1 keys, CB2 vec4 41 / 42) both run the 3-key track correctly from an alpha of 0. Ghos's gas
  (also endless, camera offset -10) draws.
- **Camera offset.** The vertex programs write clip.z - offset x (1 - ndc.z) (CB2 vec4 36.z), which is negligible at
  -2.
- **No soft-particle / depth read.** The furiijio templates' pixel program is
  `rgb = c1 + (c0 - c1) x t.rgb, a = c0.a x t.r` (plus `u_nwHdrRange`).
- **Texture format / tiling.** BC4, tile 4, the same as the visible banks.
- **Follow / emitter flags.** The cloud BG and the charge BG differ only in the 3DS fields (word-diffed).

## The cause and the fixes (tools/s3ds_effects.py)

What was wrong was what the converter told each particle to draw. Against the Smash Run sky it came out as a faint
deep-blue haze behind the body. Only a few snowflake specks showed, which matches 213.png / 214.png.

1. **The 3DS colour combiner (0x194) was ignored.** It uses the Wii U's colour-mode numbers (0x314). Over the
   fighter emitters both games ship:
   - 551 of 581 with 2 have 2;
   - 47 of 58 with 1 have 1;
   - 7 of 14 with 3 have 3.

   Every emitter drew its template's mode, mostly 2 (`c1 + (c0 - c1) x t`). The mist's cool_air is mode 3
   (`c0 x t + c1`: white-cyan) and drew deep blue.

   Fix: when the template's mode differs, the emitter gets `eft_pixel.own_shader(p, si, mode, 0, c1_const)`, the
   Ultimate ports' own-program path. Changes over the banks:

   | Change | Emitters |
   |---|---|
   | template 2 -> 1 | 34 |
   | 2 -> 3 | 22 |
   | 1 -> 3 | 1 |
   | 2 -> 0 | 1 |
   | 1 -> 2 | 11 (the old "colour 1 lost" notes) |

   0x314 is written to match.
2. **Colour 1 was multiplied by the texture tint too.** Now `tinted_keys`:
   - mode 1 / 3: colour 0 x tint;
   - mode 2: colour 0' = c1 + (c0 - c1) x tint, exact;
   - colour 1 is never tinted;
   - mode 0: no tint.
3. **Textures with no alpha channel (ETC1, L8, RGB565...) were stored as level squared.** The code set alpha = max(rgb),
   and `shape_texture` then multiplied the projection by it. `texture_shape` now stores the level once. Evidence: of 134
   fighter texture pairs that match (3DS ETC1 vs the vanilla Wii U copy), 104 hold the level, not its square. 148
   emitters are affected.
4. **A 3DS scale / alpha first section of -127 ("none") is written as 0.** The paired Wii U emitters have 0 there:
   86 + 37 + 20 + ... pairs. A negative value made 0x04A5D964 start the key at init - diff21 / section. 149 emitters
   are affected.

Tests (`tools/s3ds_effects_test.py`), new checks:
- the colour mode is the 3DS combiner;
- the emitter's pixel program, run on the CPU (`latte_exec.PixelProgram`, `program_mode`), draws that mode;
- colour 0 / 1 keys follow `tinted_keys`;
- the no-alpha shape is the level (mean error < 0.03) and nearer the level than its square;
- no negative section.

Result: **52 files, 238 emitters, 0 failures**, with the 117 vanilla files as the corpus. The HEAD converter fails 15
of these checks on Furiijio alone.

Banks changed: every kind but killer, killercannon, magnumkiller and shotzo (48 of 52).

## Billboard effect models (tools/s3ds_effect_models.py)

**The Wii U supports billboard bones in effect models, by bone NAME.**
- cross_f 0x03327FEC scans a model's VBN bone names (0x4C records, name at +0x1C) for:

  | Name tag | Type |
  |---|---|
  | `_BILLBOARDYAXISV_` | 4 |
  | `_BILLBOARDV_` | 3 |
  | `_BILLBOARDYAXIS_` | 2 |
  | `_BILLBOARD_` | 1 |
  | `_BILLBOARDWORLD_` | 5 |

  The strings are at 0x10193504 / 18 / 28 / 0x101934F8 / 0x1019353C.
- It is called from the model's skeleton set-up 0x0341F440 (list at +0x7D0, count +0x7D4) and applied each update by
  0x034235CC (-> 0x033168E0 or 0x033095B4 by +0x740).
- Vanilla effect models use these tags. Examples: Falco's reflector, Pit's Guardian Orbitars, Shulk's Monado swords
  (`bgplane_BILLBOARDYAXIS__O_OBJ_O_HIR`). Over the local vanilla VBNs: YAXIS 130, plain 77, V 30, YAXISV 5.
- NUD mesh flags carry none (step 2g v5's survey). The tag is in the name.

**H3D billboard modes** (bone flags bits 16-19, SPICA's H3DBillboardMode).

Correction to step 2g v5: World is 2, so 6 is YAxial, not YAxialViewpoint. The values found in the enemies' bones are
2, 4, 5, 6 and 7.

| H3D mode | Wii U tag |
|---|---|
| 2 World / 3 WorldViewpoint | `_BILLBOARDWORLD_` |
| 4 Screen | `_BILLBOARD_` |
| 5 ScreenViewpoint | `_BILLBOARDV_` |
| 6 YAxial | `_BILLBOARDYAXIS_` |
| 7 YAxialViewpoint | `_BILLBOARDYAXISV_` |

- The bone keeps its 3DS name's hash (the OMO's key). Only the VBN name changes, kept within 63 characters.
- "V" is read as viewpoint from the names' pairing. The per-type maths in 0x033168E0 / 0x033095B4 was not read.
- Furiijio's beam folders (`BILLBOARD_IN_CODE`) are left untagged, because `smashrun_walker_cave` already turns that
  node (step 2g v5). The engine agent could drop that turn and remove the two folders from `BILLBOARD_IN_CODE`; the
  bones are mode 6, `_BILLBOARDYAXIS_`.

Tests (`tools/s3ds_effect_models_test.py`), new checks:
- every H3D billboard bone carries its mode's tag and only that tag;
- no other bone carries a tag;
- hashes stay the 3DS names';
- names are <= 63 characters;
- the OMO world matrices are checked by the VBN names.

Result: **62 kinds, 99 models, 230 textures, 0 failures**.

**Per model** (W world, S screen, SV screen viewpoint, Y Y-axial, YV Y-axial viewpoint; counts of bones). The two
ported enemies listed first:
- Tiki Buzz Crump: 8 W.
- Waddle Doo Beam: beam1, glow1, both W.

subetenoyaminoou and yellowdevil are not in the fs kind list, so `all` does not build them.

- **bokkuncannon**: BokkuncannonBeamD (1 W 4 Y)
- **bubble**: BubbleFire_blue (1 S); BubbleFire_red (1 S)
- **churine**: ChurineSleepPowder (2 Y)
- **dafune**: DafuneMine (1 W); DafuneMineFlash (3 W)
- **darios**: DariosLaser (3 Y); DariosLaserOut (3 Y)
- **deathpod**: DeathpodBullet (1 S 2 Y); DeathpodBulletHit (3 S 1 Y); DeathpodFlash (3 S); DeathpodMuzzleFlash (3 S)
- **deathskull**: DeathskullBreak (2 W)
- **devilcar**: DevilcarPassing (2 S)
- **dosudosu**: DosudosuLeafscatter (4 S)
- **eggrobo**: EggroboBullet (2 W 3 Y); EggroboJetBlaster (2 W 2 Y); EggroboJet_L (4 Y); EggroboJet_M (2 W 2 Y); EggroboJet_S (2 W 2 Y); EggroboLaser (4 Y); EggroboLaserEnd (1 Y); EggroboLaserStart (1 Y)
- **galfire**: GalFirebreath01 (1 S 1 W)
- **galice**: GalIcebreath01 (1 S 1 W)
- **galthunder**: GalThunderbreath01 (1 S 1 W)
- **ghos**: GhosGas2 (2 W)
- **kamek**: KamekBullet (2 S); KamekBullet_out (1 S); KamekTeleport_end (1 S 1 Y); KamekTeleport_start (1 S 1 Y)
- **keronpa**: KeronpaFire (2 W); KeronpaFire2 (3 W)
- **kihunter**: Kihunter_dashattack (3 YV); KihunterHit_bill (2 W)
- **killer**: KillerVernier (1 W)
- **korokorobomb**: KorokorobombBikkuri (1 S); KorokorobombSpark (1 W)
- **magnumkiller**: MagnumKillerVernier (1 W)
- **meganta**: MegantaBullet (3 W)
- **metroid**: MetroidAbsorb (3 S)
- **mettaur**: MettaurBullet (2 S)
- **monoeye**: MonoeyeBullet (1 W); MonoeyeSign (3 W)
- **peahat**: PeahatDischarge (1 S 2 Y)
- **plasmawisp**: PWCharge (1 W); PWHadouDestroy (2 W); PWHadouNotice (2 S); PWLaserNotice (2 S); PWNeedle (1 Y); PWNeedleNotice (2 S)
- **pokkuri**: PokkuriBullet (3 S)
- **pooka**: PookaBlowout (3 S); PookaGogle (1 W)
- **popperam**: PopperamBikkuri (1 S)
- **shandera**: ShanderaCatchFireLv2 (1 S); ShanderaFireDrain (2 S); ShanderaFireStorm (1 W); ShanderaWisp (2 S)
- **shinigami**: ShinigamiBikkuri (1 S)
- **starman**: StarmanBeam (2 W 2 Y); StarmanPKFireCharge (4 W); StarmanPKFireFlash2 (2 W 2 Y)
- **tikibuzz**: TikibuzzCrump (8 W)
- **totsukotsu**: TotsukotsuBreak (7 S); TotsukotsuBullet (3 S); TotsukotsuBulletDelete (1 S); TotsukotsuDamage (1 S); TotsukotsuMuzzleFlash (2 S); TotsukotsuSign (2 W); TotsukotsuSink (3 S); TotsukotsuSinkB (3 S); TotsukotsuSinkC (3 S)
- **waddledoo**: WaddledooBeam (2 W)
- **zully**: ZullyAura (2 S)

No code-side turning is needed for these: the game turns the tagged bones itself. What remains is to check in game
that each turns as the 3DS does.

## Open

- **In-game check of the mist.** These are offline checks only: the logs prove the emitters run, and the converter
  fixes make the colours and levels the 3DS's. If the mist is still faint, the next suspects are:
  - the 3DS mesh particles: the mist's snow (primitive 0) and cool_air (primitive 1) are 3DS meshes, drawn as
    billboards here. The primitive table at 3DS header +0x40 / +0x44 (0x6C50, 0x948 bytes for furiijio) holds PICA
    command lists and is not parsed yet;
  - one shape for the colour and the alpha of RGBA textures (cool_air).
- **Billboard semantics.** Read 0x033168E0 / 0x033095B4 for the exact maths of each type, and the viewpoint ("V")
  reading.
- **Brightness of the other enemies.** Their effects get brighter / whiter where the 3DS mode is 1 / 3 or the
  texture has no alpha. This is intended (the 3DS's), but check in game.
- **Delivery name.** The package is `smashrun_effects_v3.zip`: `smashrun_effects_v1.zip` and `_v2.zip` are older
  user-facing packages (Nov 6) and were left untouched.
