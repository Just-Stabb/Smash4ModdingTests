#!/usr/bin/env python3
"""Ultimate fighter effects (ef_<name>.eff, VFXB: tools/vfxb.py) -> Smash 4 emitter sets added to a
fighter's ptcl (one set per Ultimate emitter set), its .efc entries, and an ids file for
tools/ultimate_acmd.py --effects.

  python3 tools/vfxb_to_ptcl.py EFF BASE_DIR OUT_DIR KIND IDS.json [EFFECT ...] [--prefix PtcEdge]
                                [--templates VANILLA.ptcl ...]

BASE_DIR: the base fighter's effect folder (<base>.010d0000.ptcl / .efc, e.g. Zelda's: the new
fighter's bank is a copy of it, the base's specials still use its sets). OUT_DIR gets
<name>.010d0000.ptcl / .efc (named after BASE_DIR's files: rename for the fighter); KIND: the
fighter kind (ids 0x3KKnnnn). EFFECT: Ultimate effect names (default: all).

Mapping (eft2 v22 -> eft 0x42), per emitter, from a template emitter, as tools/xv2_to_ptcl.py:
- template: Templates (the base's own or one imported from --templates files) of the eft particle
  type (eft2's numbers: 0 billboard, 1 / 2 plate XY / XZ, 3 directional, 4 directional polygon, 8 Y
  billboard; 7 primitive as a billboard mesh; a type-3 mesh at rest as type 4; 5 / 6 as type 3,
  as type 4 on a mesh) and mesh-ness (the blend too unless its pixel program is ours: the blend
  is the emitter's), plain shaders first, never one reading the screen, ranked by what its vertex
  program draws (tools/eft_vertex.py: UV animation, flipbook, follow types, rotation), one that
  turns its particles (v_inRot) when they turn (a fixed turn no template draws is baked: a mesh's
  into its vertices, a quad's quarter turns into its texture); Ultimate's follow type, flipbook
  mode and blend written over the template's;
- meshes (a primitive id): the VFXB's model (G3PR BFRES, tools/bfres_switch.py; first shape)
  written to the primitive table (Ptcl.add_primitive, once per id);
- texture: the first sampler that isn't an indirect / grade / noise / mask helper, its BNTX channel
  selection applied (tools/vfxb.py images), the flipbook cell its pattern table shows first
  (uv_div; shown_cell), its repeat (0x508), UV set (uv_channel); the sampler's wrap
  per axis; its UV shift / scale / rotation (initial, random, a frame) into slot 0's UV block
  (set_uv_anim; baked into a mesh's UVs when the template can't animate them);
- colour / alpha: eft2's combiner (colour modes 0-3: colour 0, x texture, + colour 1 x (1 -
  texture), + colour 1; alpha modes 0-4) folded into a BC4 shape and one particle colour (combine):
  each pixel's brightness kept, the hue averaged; the 3-key colour and alpha fits; colour scale;
  with own pixel programs (EXACT, tools/eft_pixel.py) the combiner itself: the other samplers
  combined into texture 0 (exact_texture), or one moving apart from it drawn live as texture 1 of a
  two-texture template (live_sampler: its own UV animation in slot 1's block, set_slot1); Ultimate's
  dissolve (custom shader 8, dissolve_of: the threshold in a colour track, the mask in texture 0);
- meshes: the particle's 3D scale baked into the mesh, the emitter's scale 1 (x the animation);
- scale: the particle scale x the scale keys (3-key fit), random % -> fraction;
- life (+ random % -> frames; infinite -> 0x7FFFFFFF, emitted once), emission (start, duration when one-time, else
  forever, interval, rate), velocity (all-direction -> figure velocity, designated direction x
  scale -> emitter velocity / direction, diffusion angle, random %), gravity (scale x direction),
  air resistance, volume (same 0-14 shape list; radius x form scale), rotation (init / random /
  add, radians), the emitter transform (translate / rotate / scale); the fade when turned off
  (0x82C: 1 / alpha fade time; infinite life fades too);
- not converted: pattern (flipbook) animation where no template plays its mode, a third sampler
  moving on its own, alpha / scale fades at the end, emitter animations (EAA0 / EAA1 ...), child
  emitters.
"""
import argparse
import hashlib
import json
import math
import os
import re
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import eft_pixel  # noqa: E402
import eft_vertex  # noqa: E402
import efc  # noqa: E402
import ptcl  # noqa: E402
import vfxb  # noqa: E402
from xv2_to_ptcl import (BLEND, FOREVER, MAX_EMITTERS, MAX_LIVE, buffer_count, color_fit,  # noqa: E402
                         pow2, resize, sanitize, three_key)

NONE64 = 2 ** 64 - 1
SHAPE_SEL = 0x00000000          # a BC4 shape's channel selectors: R R R R
RGBA_SEL = 0x00010203           # R G B A
GREY_ALPHA_SEL = 0x00000001     # a BC5's R R R G: a grey colour input in R, the alpha in G
# eft's colour combiner (shader-keyed; read off the vanilla pixel shaders): 0 colour 0 (alpha from
# the texture's red), 1 colour 0 x texture (alpha from its alpha), 2 colour 1 + (colour 0 - colour 1)
# x texture (alpha from red)
COLOR_MODE = 0x314
# Ultimate custom shader (index, flag bit) whose colour goes out x its alpha shape x 2 (vfxb shader
# custom_shader_index / custom_shader_flag; Sephiroth's ef_edge.eff)
PREMULT_SHADER = (4, 64)
# Ultimate's emitter animations (VFXB sub-sections, little endian: u8 on, u8 loop, u16, u32 key count,
# u32, then keys of x, y, z, frame; from the emitter's start) -> eft's key-animation targets
# (ptcl.KEYA_TARGETS), read off their values: EAER turns tornadoes (degrees), EAET slides Hero's sword
# light 11.8 along the blade, EAES / EASS grow emitters / their shapes, EATR / EAPL ramp the rate / life
EMITTER_ANIMS = {
    'EATR': (0,), 'EAPL': (1,), 'EAES': (2, 3, 4), 'EAER': (5, 6, 7), 'EAET': (8, 9, 10), 'EAC0': (11, 12, 13),
    'EAA0': (14,), 'EAOV': (15,), 'EASL': (17, 18), 'EAC1': (19, 20, 21), 'EASS': (22, 23, 24)}
# Ultimate's particle fields (VFXB sub-sections, little endian; main's section table 0x8CB00, its CPU
# fields 0x955F0) -> eft's complex-emitter field blocks (ptcl.FIELD_BLOCKS: the same fields, eft2 having
# kept eft's units) and per-particle key animations (ptcl.INT_TARGETS / KEYA_TARGETS 0x1C - 0x25). eft
# runs them on the CPU's particles only (no vanilla GPU program reads them but spin / magnet), so an
# emitter with any wants a template whose particles the CPU moves (no v_inVec). Each section ends in
# 8-key animations of 37 words: on, loop, random, key count, period (100), 8 keys of x, y, z, time 0 - 1
# of the life (main 0x93C80; eft's keys 0 - 100 the same). FRND (eft2's sine-noise random) and FCOL have
# no eft equivalent worked out yet
FIELD_SECTIONS = ('FSPN', 'FCLN', 'FCOV', 'FMAG', 'FRN1')
SPIN_UNITS = 2 ** 32 / 360.0        # eft's spin rate: 2^32 a full turn a frame (cross_f 0x04A6EC2C)
# shape scale, colour 0, colour 1, alpha (0x378 - 0x3A4): what the animations replace, 1 when none (a
# template's own otherwise: Kaboom's flareBase had a shape scale of 10)
EMITTER_DEFAULTS = 0x378
# Ultimate's custom shader 8, a dissolve (Woosh's whirlwinds, the spell flashes' ring2; read from
# their Maxwell code with the WindowSmash translator): pixels whose sampler 1 alpha is under colour 1's
# alpha are dropped, alpha x (mask - threshold) / width over the edge (width: the emitter's CSDP's
# first float, 0.05 / 0.12)
DISSOLVE_SHADER = 8
# (Ultimate set, emitter) drawn with two colours, not one: lerp(colour 1, colour 0, texture rgb) x
# texture alpha where the rgb is a thin core inside a wide alpha glow (ef_cmn_line06: a white core,
# a blue glow); one colour drew the glow as bright as the core, dash attack's thick white band
# (tests 51-54). Listed one by one: the sword flares fit the same way would change too
TWO_COLOUR = {('P_EdgeAttackDash2', 'FlashLine1')}
# a pixel program of our own (tools/eft_pixel.py) for each emitter whose template layout allows it:
# eft2's combiner exactly (colour from the texture's rgb, alpha from its alpha, both colours, alpha
# past 1); off (--no-exact), the one-shape fold of combine()
EXACT = True
TWO_TEXTURES = True     # two-texture templates (a second sampler drawn live: live_sampler)
DISSOLVE = True         # Ultimate's dissolve (dissolve_of)
WRITE_FOLLOW = True     # Ultimate's follow type over the template's
GRAFT = True            # vertex programs given slot 1's UV animation (tools/eft_vertex.py graft_uv1)
# a shader key's texture bytes (copied to the shader object at +0x47C, cross_f 0x04A5779C): 0x29 the
# textures past the first (eft looks up textureSampler1 / 2 only for them: 5397 vanilla keys, all
# matching their pixel samplers), 0x3B / 0x3C slot 0 / 1 a texture array
KEY_TEXTURES, KEY_ARRAY1 = 0x29, 0x3C
# eft2 vertex transform -> eft particle type (the same numbers: 0 billboard, 1 / 2 plate XY / XZ,
# 3 directional, 4 directional polygon, 8 Y billboard); 7 (primitive) as a billboard mesh. eft2's
# 5 / 6 "stripe" types carry no stripe settings (eft2's history ribbons are emitter plugins,
# EP01-EP04, on other types; 1825 + 289 type-5 / 6 emitters in 31 fighters' files have none), all
# move, and are scaled long (his speed lines 2.5 x 36): quads stretched along their motion, as
# eft's directional type 3. (eft's own stripes are complex emitters with a 0x34-byte history block.)
TYPES = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 3, 6: 3, 7: 0, 8: 8}
TEX_MAX = 128           # vanilla effect textures are mostly 64-128 (the bank's size: Bayonetta's is 4.6 MB)
BASE_FIRST = 2          # a template of the base's own beats an imported one this much
# follow type (eft2's numbers: 0 follow the emitter, 1 not, 2 its position only): at emission
# (cross_f.rpx 0x04A5C89C, from the emitter's +0x12C = this) 0 points the particle at the emitter's
# live matrices, else copies them. No vanilla shader group mixes values, but one vertex program
# serves all three (tools/eft_vertex.py): the converter writes Ultimate's
FOLLOW = 0x310
KEY_HOOKS = (0x32C, 0x330, 0x334, 0x338, 0x33C)
# slot 0's flipbook (cross_f.rpx 0x04A5A858 / 0x04A5A6AC, the emitter's uniforms; 0x04A54A88 the
# random start cell): 0x4D5 table used, 0x4D7 / 0x4D8 cells across / down, 0x4D9 random start cells,
# 0x4E0 32-byte table, 0x500 mode, 0x504 s16 frames a cell, 0x506 s16 cells (or table entries),
# 0x508 / 0x50C UV scale (1 / cells). The mode sets a uboFlag bit every flipbook program tests: 1 -> 0x4,
# 4 -> 0x8, 2 -> 0x10, 3 -> 0x20, 5 -> 0x10000000; in that bit order eft2's life-fit / clamp / loop /
# random, as vanilla's numbers agree (1 / 3 / 5 have no frame rate, 2 / 4 do: 4 plays once over the
# life, 2 loops: Bayonetta's bats)
PTN_MODE = 0x500
PTN_FROM_EFT2 = {1: 1, 2: 4, 3: 2, 4: 3}
SLOT1 = 0x7C            # slot 1's UV block: slot 0's + this (0x550; 0x04A5A6AC reads each slot's so)
# the alpha an emitter loses a frame while its set fades (Terminate_Graphic_Effect), the emitter and
# its particles ending at 0; it climbs back to 1 otherwise (cross_f.rpx 0x04A64F00 / 0x04A661D8:
# emitter instance +0x58 -= / += this x the frame step)
FADE_ALPHA = 0x82C
# while its set fades, an emitter stops emitting only when this byte is set (0x04A65034: eft2's
# is_fade_emit); with it 0 and FADE_ALPHA 0 it emits on for good (test 37's speed lines)
FADE_EMIT = 0x2F9
# an effect light (it shines on fighters): eft's user callback (0x34) 1 with its user data, the flags
# in 0x0C's top half, colour (0x14-0x1C: 0 the particle's) and radius x the particle's scale (0x20);
# eft2's custom action 1, CADP: u32 flags, 3 x colour, radius, a strength (folded into the colour). The
# common effects both games share match so (FliesUp: 0x1B, 0.5 / 0x1B, 0.5; SpecialSpeedUp's radius
# 15 x 1.3 / 0.5 x 30), Smash 4 without the flag bits from 0x20 up. Templates' own lights are cleared
USER_DATA, USER_FLOATS, USER_CALLBACK = 0x0C, 0x14, 0x34
LIGHT_CALLBACK, LIGHT_FLAGS = 1, 0x1F
# flag 0x10: the radius a multiple of the particle's scale (vanilla's: x scale at most 108, median 20, of
# 330 non-Final lights; without it the radius stands alone, 100s - 2100). Ultimate's go further
# (Kaboom's 60 x 4.3 = 260 lit the whole stage for 55 frames, far too bright). Smash 4's designers drew
# the same lights in both games' effects (60 pairs: the colour the same, Ultimate's factor aside) at the
# same reach up to about 30, and pulled the bigger ones in (Ultimate 40 -> 30, 50 -> 29, 75 -> 50; none
# past 50): light_reach does so (fix 50: Kacrackle Slash's 70 washed Hero out)
LIGHT_SCALED, LIGHT_KNEE, LIGHT_SLOPE, LIGHT_RADIUS_MAX = 0x10, 30.0, 0.4, 50.0


def light_reach(reach):
    """an Ultimate light's reach (radius, x the particle's scale with LIGHT_SCALED) as Smash 4's"""
    return reach if reach <= LIGHT_KNEE else min(LIGHT_RADIUS_MAX, LIGHT_KNEE + LIGHT_SLOPE * (reach - LIGHT_KNEE))
# the eft sampler word: U wrap in bits 24-27, V in 28-31, the same codes as eft2's (0 mirror,
# 1 repeat, 2 clamp: vanilla's 2 x 2 repeats, quarter textures mirrored into a star, are all 0x0;
# the axes from the 374 vanilla emitters repeated along U only: bits 24-27 always mirror, 28-31
# any, the other way round for V. Tests 31-55 had them swapped: dash attack's line, a half profile
# mirrored across U, drew clamped, a solid band)
# eft2 texture repeat (tex_anim repeat) -> UV repeat; eft's 0x508 / 0x50C hold repeat / cells
REPEAT = {0: (1, 1), 1: (2, 1), 2: (1, 2), 3: (2, 2)}
# brightness over HDR_START kept at HDR_KNEE of itself (hdr_scale): 4.4 -> 1.16, 2 -> 1.05, 1.3 ->
# 1.02. Vanilla's fire keeps its colour keys at 1.0 - 1.05 (its colour is in its textures: Mario's
# fireball, Charizard's flamethrower, Robin's Arcfire); fix 21's 1.2 / 0.25 (peaks up to 2) still
# glowed purple in Smash 4's bloom (the whirlwind test: pale blue meshes at 1.3 too)
HDR_START, HDR_KNEE = 1.0, 0.05


# shaders that read the screen behind them (refraction: Zelda's Nayru's Love crystal, test 35's type-4
# templates, drew his sword glows and neutral air as see-through distortion; 56 of 1797 vanilla
# shaders) or texture arrays: never templates
SCREEN_SAMPLERS = (b'frameBufferTexture_CROSS', b'depthBufferTexture_CROSS', b'textureArraySampler')
# shader modes (the shader key's first word, low byte; the emitter's 0x831 the same) drawn in another
# pass: 5 and 6 write a screen offset (x 1/960, 1/540) for the distortion pass, not a colour
# (Bayonetta's ciecle1_rif, Shulk's rifraction2, Ryu's rifraction1), 7 Fox / Falco's Illusion.
# Never templates: an own pixel program's colour there bends the picture behind instead (fix 33's
# Frizz / Zap charge flare1, a see-through lens at the hand; fix 32's sword light and explosions)
PASS_MODES = (5, 6, 7)
# vertex programs lighting their particles (smoke's: colour x max(normal . light, 0) x the light's
# colour + ambient, from the game's userUniformBlockParam, CB4; 245 vanilla emitters, all shader mode
# 4): never templates. Ultimate's parts aren't lit so: Frizz's / Kafrizz's flames on smoke templates
# (Mario's fireball smoke) burned dark red to black away from the light (fixes 33 - 37: 71 - 102 parts)
LIT_BLOCK = 'userUniformBlockParam'
# a particle's rotation is shader-keyed: the vertex program turns it from this attribute, and a
# shader without it draws every particle unturned (vanilla: all 3165 emitters with a rotation have
# it; down air's flares, turned -90 degrees in Ultimate, lay across the plunge as crosses)
ROTATION_ATTR = b'v_inRot'
# what an emitter's rotation needs of a template: none; a fixed one the converter can bake (a mesh's
# into its vertices, a quad's quarter turns about Z into its texture); one only a turning shader draws
ROT_NONE, ROT_FIXED, ROT_ANIMATED = 0, 1, 2
# eft's directional type (3) comes in two shader kinds: one aligns the particle with its own velocity
# (this attribute; 535 of 1732 vanilla type-3 emitters), the other with its change in world
# position (v_inWldPosDf), which on a following emitter includes the bone's motion. Ultimate aligns
# with the velocity: down smash's speed lines, slow (0.1) on the swinging sword, stood across the
# blade as a 23 x 180 bar (test 46); in Ultimate they lie along it. No emitter byte selects it alone
VELOCITY_ATTR = b'v_inVec'


class Templates:
    """template emitters by (eft particle type, blend 0 / 1 / 2, mesh): simple emitters with one BC4
    texture (slot 0; slot 2 unused, slot 1 only on a two-texture template whose pixel program is
    ours). Among them, in this order: a plain shader (no shader parameters: Ike's FS cloud shader,
    FinIkeCloud FNSmoke with 32 bytes of them, tinted Sephiroth's meshes orange; or, its pixel
    program ours, a vertex program parameter-free emitters run too), a flipbook program only for a
    flipbook, the follow type, the UV animation the emitter needs, then animated colour tracks. What a
    template draws is read from its vertex program (tools/eft_vertex.py features), not its mode
    words: the UV animation (none or all of it, by slot), whether it plays a flipbook (then any
    mode: the converter writes the wanted one), the follow types it draws right (all but for programs
    reading the live emitter matrix; the converter writes the wanted one, 0x310 being the CPU's).
    Then animated colour tracks
    (2 / 2, then 2 / x) and the base's own (no import); others are imported from the corpus
    (Ptcl.import_emitter: their shader, shader parameters and textures copied). Shaders reading the
    screen or texture arrays (SCREEN_SAMPLERS), drawn in another pass (PASS_MODES) or lighting their
    particles (LIT_BLOCK) are left out."""

    def __init__(self, base, corpus):
        self.base, self.files, self.found = base, {}, {}
        self.no_graft = False       # (--no-graft-for: no grafted templates for the emitter at hand)
        self.test_white1 = self.test_mean_colour = False    # (--test-white1-for, --test-mean-colour-for)
        self.test_no_light = False                          # (--test-no-light-for)
        for path in corpus:
            self.files[path] = ptcl.Ptcl(open(path, 'rb').read())
        # vanilla child blocks by (blend, particle type): what child_block starts from (none with a
        # shader parameter range of their own)
        self.children = {}
        for path in [None] + list(corpus):
            p = base if path is None else self.files[path]
            for s in p.sets:
                for x in s['emitters']:
                    em = x['data']
                    if em is not None and ptcl.Ptcl.has_child(em):
                        c = bytes(em[ptcl.CHILD:ptcl.CHILD + ptcl.CHILD_SIZE])
                        if not any(struct.unpack_from('>4I', c, 0x2DC)):
                            self.children.setdefault((struct.unpack_from('>I', c, 0x3C)[0],
                                                      struct.unpack_from('>I', c, 0x44)[0]), c)
        for path in [None] + list(corpus):
            p = base if path is None else self.files[path]
            screen = {}
            for si, s in enumerate(p.sets):
                for k, x in enumerate(s['emitters']):
                    em = x['data']
                    if em is None or len(em) != ptcl.SIMPLE_SIZE:
                        continue
                    t = [p.texres(em, j) for j in range(3)]
                    # slot 2 never; slot 1 only as a two-texture own pixel program's (below)
                    if t[2]['native_size']:
                        continue
                    two = bool(t[1]['native_size'])
                    key = (p.field(em, 'particle_type'), p.field(em, 'blend_type'), p.field(em, 'primitive_index') >= 0)
                    c = (p.field(em, 'color0_type'), p.field(em, 'color1_type'))
                    score = (2 if c == (2, 2) else 1 if c[0] == 2 else 0) + (BASE_FIRST if path is None else 0)
                    si_ = struct.unpack_from('>I', em, 0x844)[0]
                    if si_ not in screen:
                        b = p.shader_binary(si_)
                        hdr = eft_vertex.vertex_header(bytes(b))
                        screen[si_] = (any(t in b for t in SCREEN_SAMPLERS)
                                       or struct.unpack_from('>I', p.shader_entry(si_), 0)[0] & 0xFF in PASS_MODES
                                       or hdr is not None and any(n == LIT_BLOCK for n, _cb, _s in hdr['blocks']),
                                       ROTATION_ATTR in b, VELOCITY_ATTR in b, eft_vertex.features(bytes(b)))
                    if screen[si_][0]:
                        continue
                    # 0 no own program, 1 one without colour 1, 2 with it
                    lay = eft_pixel.layout(bytes(p.shader_binary(si_))) if EXACT else None
                    own = 0 if lay is None else 2 if lay['c1'] is not None else 1
                    if t[0]['native_format'] != 9 and not own:
                        continue
                    # a two-texture template: its pixel program ours (texture 1 sampled from the
                    # coordinates its vertex program works out with slot 1's UV animation), no
                    # flipbook on slot 1
                    feat = screen[si_][3]
                    if two != (lay is not None and 'uv1' in lay) or (two and (feat['flipbook'][1] or not TWO_TEXTURES)):
                        continue
                    # parameters a vertex program doesn't read do nothing once the pixel program is
                    # ours (853 of 1055 vanilla emitters with them; half the two-texture templates)
                    plain = not p.field(em, 'shader_param_size') or bool(own) and not feat['shader_param']
                    # what its vertex program draws (not the mode words: tools/eft_vertex.py)
                    traits = (plain, feat['uv'][0], feat['follow'], feat['flipbook'][0],
                              screen[si_][1], screen[si_][2], own, c[0] == 2, c[1] == 2,
                              two, feat['uv'][1] if two else 0, not screen[si_][2] or feat['fluc'])
                    self.found.setdefault(key, {})
                    variants = [(traits, False)]
                    if GRAFT and TWO_TEXTURES and not two and graftable(bytes(p.shader_binary(si_)), lay):
                        # also a two-texture template once grafted (two_texture_shader): slot 1's UV
                        # animation all there (eft's own code, or the program's); 2: a three-texture
                        # one too (three_texture_shader)
                        variants.append((traits[:9] + (True, 7) + traits[11:],
                                         2 if three_graftable(bytes(p.shader_binary(si_)), lay) else 1))
                    for tr, grafted in variants:
                        # (a vanilla two-texture program over a grafted one drawing as much)
                        old = self.found[key].get(tr)
                        if old is None or (not grafted, score) > (not old[4], old[0]):
                            self.found[key][tr] = (score, path, si, k, grafted)

    def get(self, typ, blend, mesh, uv_mode, follow, ptn, rot, notes, anim=(False, False), need_c1=False,
            want2=False, uv_mode1=0, swap_ok=False, need_thr=0, want3=False, fields=False, fluc=False):
        """the best template for this particle type / blend / mesh-ness, follow type, flipbook mode
        (eft's, 0 none), rotation (ROT_*) and UV mode bits; another blend (add), then type 0, when
        there's none. A flipbook template is never taken for no flipbook when another is there. A rotation the converter can bake (ROT_FIXED) ranks after the UV mode,
        which it can't (only freeze); one it can't, before. With own pixel programs (EXACT) a template
        they can stand in for comes first, then animated colour tracks where anim (colour 0 / 1 change
        over the particle's life: a constant track is their mean, Frizzle's white flash at birth went).
        want2: a second texture drawn live (uv_mode1 its UV mode bits); swap_ok: the two may trade
        slots (texture 0 x / + texture 1 either way round) when the template animates them better so.
        need_thr: a dissolve's threshold over life wants an animated colour track, 1: colour 1's, 2:
        either (colour 0's rgb constant). fields: particle fields (FIELD_SECTIONS), which want the CPU's
        particles (no v_inVec), ranked after the main texture's UV animation; fluc: fluctuation, which
        wants the CPU's particles or a GPU program reading flucX / flucY, after the colour tracks.
        Returns (emitter bytes, turns, swapped)"""
        def assign(t):
            """(main's UV mode met, the second's met, swapped): the better way round"""
            mode, two, mode1 = t[1], t[9], t[10]
            ways = [(mode & uv_mode == uv_mode, not two or mode1 & uv_mode1 == uv_mode1, False)]
            # only when both fit so (half a fit bakes slot 0's UVs into a mesh, and texture 1 then
            # can't be drawn live: Hero's ring2 / wind1 lost both)
            if swap_ok and two and mode1 & uv_mode == uv_mode and mode & uv_mode1 == uv_mode1:
                ways.append((True, True, True))
            return max(ways, key=lambda w: (w[0], w[1], not w[2]))

        def rank(item):
            (plain, mode, fol, pm, turns, by_vel, own, an0, an1, two, mode1, fluc_ok), (score, grafted) = \
                item[0][1:], item[1][::4]
            same_blend = item[0][0] == blend
            fit0, fit1, swapped = assign(item[0][1:])
            # a mesh's UV animation first: freezing it bakes the mesh again (his slash arcs'
            # glows: four 240 KB copies), and its starting rotation bakes into the one copy
            # the UV animation before the colour tracks: frozen, a scrolling texture is a still picture
            # (test 30: Woosh's whirlwinds, whose rising streaks are the whole look, stood still and
            # thin for a template with animated colour); a colour track's mean loses less
            # (two textures where a second one is wanted, its UV animation in slot 1 too)
            # (a dissolve's threshold rides in a colour track: an animated one after the UV animation,
            # need_thr: Woosh's whirlwinds kept their rising streaks over the dissolve)
            # (a flipbook played before the UV animation: frozen on one cell, fire and smoke sheets
            # were a still picture faded by their cells' ink)
            # (the main texture's UV animation before a second texture: missing on a mesh, it bakes
            # slot 0's UVs, and texture 1 then can't be drawn live either: Hero's ring2 / wind1)
            # (a spin before the colour tracks: a mesh's can't be baked, only its starting rotation,
            # and stood still Woosh's rings / wind lost their whole motion for colour 1's mean)
            # (a third texture (want3) wants a template whose slot 1 can be grafted: slot 2 is made from it)
            # (fields before the second texture: Woosh's tornado particles are their spin)
            return (plain, not pm or bool(ptn), own if need_c1 else min(own, 1), follow in fol, pm == bool(ptn),
                    fit0, not fields or not by_vel, two == want2, fit1, not want3 or grafted == 2,
                    not need_thr or an1 or (need_thr == 2 and an0),
                    turns or rot != ROT_ANIMATED, an0 or not anim[0], an1 or not anim[1], fluc_ok or not fluc,
                    by_vel or typ != 3, (mode1 if swapped else mode) == uv_mode,
                    turns or rot == ROT_NONE, turns == (rot != ROT_NONE), not grafted, same_blend, score)
        # the blend is the emitter's (0x324: not the program's, 352 vanilla file / shader pairs use
        # more than one): any blend's template whose pixel program is ours (it draws rgb and alpha
        # for whichever), the same blend's otherwise; then another blend's (add), then type 0
        for t, b in ((typ, blend), (typ, 1), (0, blend), (0, 1)):
            cands = {(b_,) + traits: v for b_ in (0, 1, 2) for traits, v in self.found.get((t, b_, mesh), {}).items()
                     if (b_ == b or (EXACT and traits[6])) and not (self.no_graft and v[4])}
            if not cands:
                continue
            key = (t, b, mesh)
            traits, (_score, path, si, k, _grafted) = max(cands.items(), key=rank)
            traits = traits[1:]
            (plain, mode, fol, pm, turns, by_vel, own, an0, an1, two, mode1, fluc_ok) = traits
            swapped = assign(traits)[2]
            if swapped:
                mode, mode1 = mode1, mode
                notes.append('texture slots swapped (the template animates them so)')
            if key != (typ, blend, mesh):
                notes.append('no template (type %d blend %d%s): type %d blend %d' % (
                    typ, blend, ' mesh' if mesh else '', key[0], key[1]))
            if follow not in fol:
                notes.append('follow %d: template draws only %s' % (follow, '/'.join(map(str, sorted(fol)))))
            if mode & uv_mode != uv_mode:
                notes.append('UV animation %d: template has %d' % (uv_mode, mode))
            if ptn and not pm:
                notes.append('flipbook mode %d: template plays none (one cell shown)' % ptn)
            if fields and by_vel:
                notes.append('fields lost: the template moves its particles on the GPU')
            if fluc and not fluc_ok:
                notes.append('fluctuation lost: the template\'s GPU program draws none')
            if key[0] == 3 and not by_vel and follow != 1:
                # (unfollowing particles' world motion is their velocity; every vanilla v_inVec
                # program moves its particles on the GPU)
                notes.append('directional by world motion: template has no v_inVec')
            if rot == ROT_ANIMATED and not turns:
                notes.append('rotation: template has none' + (' (the spin lost)' if mesh else ''))
            if path is None:
                em = self.base.emitter_bytes(si, k)
                struct.pack_into('>II', em, 0x2CC, 0, 0)
            else:
                em = self.base.import_emitter(self.files[path], si, k, skip_slots=(0, 1))
            if follow in fol and WRITE_FOLLOW:
                # the CPU's (0x04A5C89C): Ultimate's
                struct.pack_into('>I', em, FOLLOW, follow)
            # a key-animated template's key animation isn't imported (Ptcl.import_emitter), but its
            # per-particle hooks (0x32C - 0x33C, cross_f 0x04A627A0: function tables, 2 = by key
            # animation, only ever on key-animated emitters) would read it: fix 25's F-smash ground
            # flare crashed on the null table (0x04A5E154). 1, the hook every other emitter has
            for o in KEY_HOOKS:
                if struct.unpack_from('>I', em, o)[0] == 2:
                    struct.pack_into('>I', em, o, 1)
            return em, turns, swapped
        raise KeyError((typ, blend, mesh))


def face_normals(pos, idx):
    """unit vertex normals of a triangle list: the area-weighted sum of the faces' at each vertex"""
    tri = np.asarray(idx, np.int64).reshape(-1, 3)
    p0, p1, p2 = (pos[tri[:, k]].astype(np.float64) for k in range(3))
    fn = np.cross(p1 - p0, p2 - p0)
    out = np.zeros((len(pos), 3))
    for k in range(3):
        np.add.at(out, tri[:, k], fn)
    return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-9)


def fresnel_bake(e, notes):
    """(near, far) of a camera-facing mesh's view-angle alpha (eft2's fresnel alpha), to bake into its
    vertex alpha, else None. Ultimate's vertex program (Kafrizz's sphere1, read with the WindowSmash
    shader translator) gives the pixel alpha x smoothstep(near, far, |N . V|): opaque where the mesh
    faces the camera, gone at its outline (or the other way round, near > far). On a billboard mesh
    (eft2 types 0 / 7) V is the mesh's Z whatever the camera does, so it bakes exactly while the mesh
    turns only about Z; drawn without it Kafrizz's ball was a hard solid disc. Other types need a
    shader that has the view vector"""
    pt, st = e['particle'], e['static']
    if not e['color']['fresnel_alpha'] or pt['billboard_type'] not in (0, 7):
        return None
    if any(abs(st[k][a]) > 1e-6 for k in ('rotate_init', 'rotate_init_rand', 'rotate_add') for a in (0, 1)):
        notes.append('fresnel alpha: turns off Z, not baked')
        return None
    near, far = (float(v) for v in st['fresnel_alpha'][:2])
    if abs(far - near) < 1e-6:
        return None
    notes.append('fresnel alpha %.2f - %.2f baked into the vertex alpha' % (near, far))
    return near, far


def mesh(model, uv_channel=0):
    """(pos, nrm, col, uv, idx) of a BFRES model's first shape. Every vanilla primitive has normals
    (825 of them; 106 have no colour): missing ones are +Z; an all-white colour is left out. The UV
    set the texture reads (eft2's uv_channel) comes first"""
    shp = model['shapes'][0]
    a = model['vertex_buffers'][shp['vertex_buffer']]['attrs']
    n = len(a['_p0'])
    uv0 = a.get('_u0', np.zeros((n, 2), np.float32))[:, :2]
    uv1 = a.get('_u1', uv0)[:, :2]
    if uv_channel == 1:
        uv0, uv1 = uv1, uv0
    nrm = a['_n0'][:, :3] if '_n0' in a else np.tile(np.array([0, 0, 1], np.float32), (n, 1))
    col = a['_c0'][:, :4] if '_c0' in a else None
    if col is not None and col.min() >= 0.99:
        col = None
    return (a['_p0'][:, :3], nrm, col, np.concatenate([uv0, uv1], 1), shp['meshes'][0]['indices'])


HELPER_TEXTURES = ('indirect', 'grade', 'noise', 'mask')



LATTE_DIS = os.path.join(HERE, 'latte_dis', 'latte-dis')
_alpha_mask = {}


def alpha_mask_shader(p, si):
    """True when shader si's pixel program samples only the texture's alpha (SAMPLE Rn.___w): a mask
    over a mesh its own view-angle falloff shapes (123: the sword flares, down throw's ring1). Such a
    shader wants vanilla's alpha 1 (R R R 1); every other one gets the shape in every channel. None
    when tools/latte_dis/latte-dis is missing (then R R R R)."""
    import hashlib
    import subprocess
    import tempfile
    from trail_shader import gsh_blocks
    b = bytes(p.shader_binary(si))
    key = hashlib.md5(b).hexdigest()
    if key not in _alpha_mask:
        if not os.path.exists(LATTE_DIS):
            return None
        blk = [x for x in gsh_blocks(b, 0) if x[0] == 7][0]
        with tempfile.NamedTemporaryFile(suffix='.gsh', delete=False) as t:
            t.write(b)
        out = subprocess.run([LATTE_DIS, t.name, str(blk[2]), str(blk[3])], capture_output=True, text=True).stdout
        os.unlink(t.name)
        masks = [ln.split()[2].split('.')[1].rstrip(',') for ln in out.splitlines() if 'SAMPLE' in ln]
        _alpha_mask[key] = bool(masks) and all(m == '___w' for m in masks)
    return _alpha_mask[key]

def hdr_scale(p, em, scale, notes):
    """the colour scale with the particle's brightest channel (its colour keys x scale) compressed
    above HDR_START: HDR_START + (peak - HDR_START) x HDR_KNEE, the hue kept. Ultimate's colours are
    for its own bloom and tone mapping (Frizz's sparks peak at 4.4, 86 of Hero's 840 emitters over
    2.5); vanilla Smash 4's stay low (99% of its 8115 emitters at 2.0 or less), and its bloom /
    glare turns anything far over 1 into a wide pink-white haze with blue-purple fringes (the Frizz
    test: each part of the fireball alone, every bright one purple at its core)"""
    peak = scale * max(max(c[:3]) for track in (0, 1) for c in p.color_keys(em, track))
    if peak <= HDR_START:
        return scale
    out = scale * (HDR_START + (peak - HDR_START) * HDR_KNEE) / peak
    notes.append('brightness %.2f -> %.2f' % (peak, peak * out / scale))
    return out


def keys(table, n, comps=3):
    """an eft2 key table (8 x (x, y, z, time 0-1)) -> [101, comps] samples over the particle's life"""
    k = np.array(table['keys'], float).reshape(8, 4)[:max(1, n)]
    t = np.linspace(0, 1, 101)
    return np.stack([np.interp(t, k[:, 3], k[:, c]) for c in range(comps)], 1)


def is_indirect(e, j, names):
    """sampler j only moves the picture (a distortion map): named so ('indirect'), or sampler 0 of a
    combiner shader_type 2 (Ultimate's programs read it for the UV offset alone, whatever it holds:
    Kamera's sphere1 ef_brave_mask02, the spell rings' ef_cmn_cloud00; distortion())"""
    return 'indirect' in names.get(e['sampler'][j]['texture_id'], '') or (
        j == 0 and e['combiner']['shader_type'] == 2)


def distortion(e, ti, images, is_mesh):
    """(sx, sy): Ultimate's combiner shader_type 2, sampler ti's UVs moved by sampler 0 (a map):
    u + (2 r - 1) sx, v + (2 a - 1) sy, sx / sy the static coefficient x the param animation's x
    (per particle over its life in Ultimate: here its mean over the life weighted by alpha 0, while
    the part shows; Kaboom's smokeBase 0.05 -> 0.5 -> 0.1, his flames 1). Read off its fire / smoke pixel programs with the WindowSmash translator: sampler 1
    moved, a third sampler not (Frizz's grade05 at its own UVs). None when there's nothing to move
    or the map can't be drawn: a mesh's two-texture programs read one UV set"""
    s0 = e['sampler'][0]
    if e['combiner']['shader_type'] != 2 or ti in (None, 0) or s0['texture_id'] == NONE64 or s0['texture_id'] not in images:
        return None
    if is_mesh and e['tex_anim'][0]['uv_channel'] != e['tex_anim'][ti]['uv_channel']:
        return None
    st = e['static']
    w = track(st, e['color'], 0)[1] + 1e-3
    k = float((keys(st['param_anim'], int(st['num_param_keys']), 1)[:, 0] * w).sum() / w.sum())
    sx, sy = (float(c) * k for c in st['coefficient'])
    if max(abs(sx), abs(sy)) < 1e-3:
        return None
    return sx, sy


def main_texture(e, names):
    smp = [(i, s) for i, s in enumerate(e['sampler']) if s['texture_id'] != NONE64]
    for i, s in smp:
        if not any(h in names.get(s['texture_id'], '') for h in HELPER_TEXTURES) and not is_indirect(e, i, names):
            return i, s
    drawn = [(i, s) for i, s in smp if not is_indirect(e, i, names)]
    return (drawn or smp)[0] if smp else (None, None)


def sampler_channel(e, i, img):
    """the channel eft2 takes a sampler's alpha from (combiner tex_alpha_input: 1 red; Ultimate's
    flares are opaque, their round shape in red), 0-1"""
    f = img.astype(np.float32) / 255
    return f[..., 0] if e['combiner']['tex_alpha_input'][i] == 1 else f[..., 3]


def shape_sampler(e, ti, images, notes, names=None):
    """(sampler, alpha factor): the sampler that holds the piece's shape when the one main_texture
    picked is a tiling fill. eft2 multiplies its textures (combiner blends 0); his auras / fire /
    smoke (the throws, dash attack, Shadow Flare) put a tiling fire / noise (edges 0.13-0.45) first and
    the shape (edges 0) second or third: drawn from the first alone each was a tinted rectangle up
    to 16 units across (test 47: "lights most of the stage"). The fill is folded in as its mean"""
    cb = e['combiner']
    if any(cb[k] for k in ('tex1_color_blend', 'tex2_color_blend', 'tex1_alpha_blend', 'tex2_alpha_blend')):
        return ti, 1.0
    stats = {}
    for i, s in enumerate(e['sampler']):
        img = images.get(s['texture_id']) if s['texture_id'] != NONE64 else None
        if img is None or (names is not None and is_indirect(e, i, names)):
            continue
        c = sampler_channel(e, i, img)
        border = np.concatenate([c[0], c[-1], c[:, 0], c[:, -1]])
        stats[i] = (float(border.mean()), float(c.mean()))
    if ti not in stats or len(stats) < 2 or stats[ti][0] < 0.1:
        return ti, 1.0
    shaped = [i for i, (edge, mean) in stats.items() if edge < 0.05 and mean > 0.01]
    if not shaped:
        return ti, 1.0
    best = shaped[0]
    factor = float(np.prod([mean for i, (edge, mean) in stats.items() if edge >= 0.1]))
    notes.append('shape from sampler %d (sampler %d a fill: x %.2f)' % (best, ti, factor))
    return best, factor


def wrap_uv(t, mode):
    """eft2 / eft wrap codes: 0 mirror, 1 repeat, 2 clamp"""
    if mode == 2:
        return np.clip(t, 0, 1 - 1e-6)
    if mode == 0:
        t = np.mod(t, 2)
        return np.clip(np.where(t > 1, 2 - t, t), 0, 1 - 1e-6)
    return np.mod(t, 1)


def bake_samplers(e, ti, img, ptn, images, names, notes):
    """img (the main sampler's picture: one cell, or the whole sheet of a flipbook) with the
    emitter's other samplers multiplied into the channel its shape is read from, each sampled as
    Ultimate places it on the quad (its repeat, starting scale / shift / turn, wrap; a flipbook's
    first cell): eft2 multiplies its textures (combiner blends 0). Smash 4's templates draw one
    texture, so his fire / aura / smoke (a flipbook or a mask times a tiling noise times a square
    fade) drew as one flat shape; now the product, frozen at its start (the other samplers' scroll
    is lost). Distortion maps ('indirect': they move the picture) are left out. None when nothing
    is multiplied"""
    cb = e['combiner']
    if any(cb[k] for k in ('tex1_color_blend', 'tex2_color_blend', 'tex1_alpha_blend', 'tex2_alpha_blend')):
        return None
    others = [(j, s) for j, s in enumerate(e['sampler']) if j != ti and s['texture_id'] != NONE64
              and s['texture_id'] in images and not is_indirect(e, j, names)]
    if not others:
        return None
    out = img.astype(np.float32).copy()
    am = cb['alpha_process']
    ch = 0 if am in (2, 3) or cb['tex_alpha_input'][ti] == 1 else 3
    nx, ny = ((max(1, int(round(v))) for v in e['static']['tex_scroll'][ti]['uv_div']) if ptn else (1, 1))
    h, w = out.shape[0] // ny, out.shape[1] // nx
    yy, xx = np.mgrid[0:h, 0:w]
    quad = np.stack([(xx.ravel() + 0.5) / w, (yy.ravel() + 0.5) / h], 1).astype(np.float32)
    product = np.ones(h * w, np.float32)
    for j, s in others:
        ts = e['static']['tex_scroll'][j]
        src = first_cell(images[s['texture_id']], ts, shown_cell(e, j))
        c = sampler_channel(e, j, src)
        uv = uv_transform(quad * np.array(REPEAT.get(e['tex_anim'][j]['repeat'], (1, 1)), np.float32),
                          ts['scale'], ts['scroll'], ts['rotation'])
        sh, sw = c.shape
        product *= c[(wrap_uv(uv[:, 1], s['wrap_v']) * sh).astype(int), (wrap_uv(uv[:, 0], s['wrap_u']) * sw).astype(int)]
    product = product.reshape(h, w)
    for cy in range(ny):
        for cx in range(nx):
            out[cy * h:(cy + 1) * h, cx * w:(cx + 1) * w, ch] *= product
    notes.append('samplers %s multiplied in' % ','.join(str(j) for j, _s in others))
    return np.clip(out, 0, 255).astype(np.uint8)


def sampler_inputs(e, i, img):
    """sampler i's colour and alpha inputs to eft2's combiner (tex_color_input: 0 rgb, 1 its alpha
    in rgb; tex_alpha_input: 0 alpha, 1 red, 2 one: the sampler leaves the alpha alone (Woosh's
    tornado1_f2, read with the WindowSmash translator: alpha = texture 0's x colour 0's, texture 1's
    alpha never read; taken as its alpha, its mean 0.34 dimmed the whirlwind); alpha modes 2 / 3
    red), [h, w, 3] and [h, w], 0-1"""
    f = img.astype(np.float32) / 255
    cb = e['combiner']
    rgb = np.repeat(f[..., 3:4], 3, -1) if cb['tex_color_input'][i] == 1 else f[..., :3]
    if cb['tex_alpha_input'][i] == 2:
        return rgb, np.ones_like(f[..., 0])
    red = cb['tex_alpha_input'][i] == 1 or cb['alpha_process'] in (2, 3)
    return rgb, (f[..., 0] if red else f[..., 3])


def same_uv(e, i, j):
    """samplers i and j read the same UVs all life: the same UV set, repeat and UV animation"""
    ta, ts_ = e['tex_anim'], e['static']['tex_scroll']
    keys = ('scroll', 'scroll_add', 'scroll_random', 'scale', 'scale_add', 'scale_random', 'rotation',
            'rotation_add', 'rotation_random', 'uv_div')
    return (ta[i]['uv_channel'] == ta[j]['uv_channel'] and ta[i]['repeat'] == ta[j]['repeat']
            and all(np.allclose(ts_[i][k], ts_[j][k]) for k in keys))


def live_sampler(e, ti, images, names, is_mesh):
    """the sampler a two-texture own pixel program draws as texture 1, or None: one that moves apart
    from sampler ti (its own UV animation, repeat or UV set; same-UV ones combine exactly in
    exact_texture), as Ultimate draws it rather than frozen (bake_samplers) or as its mean (a mesh).
    A mesh's two-texture vertex programs read one UV set for both: the same set only. With three
    samplers the one baked into texture 0 must combine as the live one does (eft2's order 0, 1, 2
    otherwise matters)"""
    cb = e['combiner']
    others = [j for j, s in enumerate(e['sampler']) if j != ti and s['texture_id'] != NONE64
              and s['texture_id'] in images and not is_indirect(e, j, names)]
    moving = [j for j in others if not same_uv(e, ti, j)
              and (not is_mesh or e['tex_anim'][j]['uv_channel'] == e['tex_anim'][ti]['uv_channel'])]
    if not moving or len(others) > 1 and (cb['tex1_color_blend'], cb['tex1_alpha_blend']) != (
            cb['tex2_color_blend'], cb['tex2_alpha_blend']):
        return None
    return moving[-1]


def dissolve_of(e, ti, images, names, ptn):
    """(edge width, threshold over life [101], mask [h, w] 0-1) for Ultimate's dissolve
    (DISSOLVE_SHADER), else None. The mask is sampler 1's alpha as stored (whatever its alpha input
    to the combiner), so it must read sampler ti's UVs (it rides in texture 0's green); the colour
    input grey (texture 0 carries it in red and blue: eft_pixel's dissolve programs); no flipbook"""
    if not DISSOLVE or e['shader']['custom_shader_index'] != DISSOLVE_SHADER or 'CSDP' not in e['subsections']:
        return None
    s = e['sampler'][1]
    if s['texture_id'] == NONE64 or s['texture_id'] not in images or ptn or not (ti == 1 or same_uv(e, ti, 1)):
        return None
    for j, x in enumerate(e['sampler']):
        if x['texture_id'] != NONE64 and x['texture_id'] in images and not is_indirect(e, j, names):
            rgb, _a = sampler_inputs(e, j, images[x['texture_id']])
            if float(np.abs(rgb - rgb[..., :1]).max()) > 2.5 / 255:
                return None
    width = struct.unpack('<f', bytes.fromhex(e['subsections']['CSDP'][:8]))[0]
    thr = track(e['static'], e['color'], 1)[1] * e['info']['color1'][3]
    mask = first_cell(images[s['texture_id']], e['static']['tex_scroll'][1], shown_cell(e, 1))[..., 3] / 255.0
    return width, thr, mask.astype(np.float32)


def tex_blend(e, ti, j):
    """(colour, alpha) blend bringing sampler j in (0 multiply, 1 add): eft2's tex1 for sampler 1,
    tex2 for 2"""
    k = 2 if 2 in (ti, j) else 1
    cb = e['combiner']
    return cb['tex%d_color_blend' % k], cb['tex%d_alpha_blend' % k]


def fit_texture(pix, tmax=None):
    """pix at power-of-two sizes up to tmax (TEX_MAX), halved while that changes it by under 1%"""
    h, w = pix.shape[:2]
    tmax = tmax or TEX_MAX
    tw, th = pow2(w, hi=tmax), pow2(h, hi=tmax)
    if (tw, th) != (w, h):
        pix = resize(pix.astype(np.float32), tw, th)
    # smooth textures (glows, gradients) at half size while that changes them by under 1% (the
    # bank's size: test 37's 6.0 MB loaded)
    while min(tw, th) > 16:
        half = resize(pix.astype(np.float32), tw // 2, th // 2)
        back = resize(half, tw, th)
        if float(np.abs(back - pix).mean()) > 0.01 * max(float(pix.mean()), 0.05):
            break
        pix, tw, th = half, tw // 2, th // 2
    return pix


def set_exact_texture(p, em, slot, pix):
    """an own pixel program's texture (colour input in rgb, alpha input in a, 0-1) in a slot"""
    q8 = (np.clip(pix, 0, 1) * 255 + 0.5).astype(np.uint8)
    if int(np.abs(q8[..., :3].astype(int) - q8[..., :1]).max()) <= 2:
        # grey colour input: BC5, R the colour (every rgb channel), G the alpha
        p.set_texture(em, slot, np.stack([q8[..., 0], q8[..., 3], np.zeros_like(q8[..., 0]),
                                          np.full_like(q8[..., 0], 255)], 2), 0x35, comp_sel=GREY_ALPHA_SEL)
    else:
        p.set_texture(em, slot, q8, 0x33, comp_sel=RGBA_SEL)


def set_wrap(em, slot, wu, wv):
    struct.pack_into('>I', em, ptcl.TEXRES + ptcl.TEXRES_SIZE * slot + 0x0C, (wv & 0xF) << 28 | (wu & 0xF) << 24 | 0x100)


def graftable(b, lay):
    """a one-texture template whose program can draw a second texture once grafted (two_texture_shader):
    its pixel program ours, the texture coordinates in .xy, its vertex program taking the slot-1
    graft or already animating slot 1 (639 + 71 of 710 vanilla one-texture own templates)"""
    if lay is None or 'uv1' in lay or lay['uv'][1] != 'xy':
        return False
    if eft_vertex.uv_caps(b)[1]:
        return True
    return eft_vertex.uv1_graft_point(b, lay['sems'][lay['uv'][0]]) is not None


_two = {}


def two_texture_shader(p, si):
    """shader si (a graftable one-texture template) as a two-texture one, added once: slot 1's UV
    animation grafted into its vertex program (unless it has it), a 2D textureSampler1 in its pixel
    header, its key's texture count 1. None when the graft doesn't take"""
    key = (id(p), si)
    if key not in _two:
        b = bytes(p.shader_binary(si))
        lay = eft_pixel.layout(b)
        nb = b if eft_vertex.uv_caps(b)[1] else eft_vertex.graft_uv1(b, lay['sems'][lay['uv'][0]])
        if nb is None:
            _two[key] = None
        else:
            nb = eft_vertex.add_pixel_sampler(nb, 'textureSampler1', 1)
            eft_pixel.GRAFTED[hashlib.md5(nb).hexdigest()] = None
            entry = bytearray(p.shader_entry(si))
            entry[KEY_TEXTURES], entry[KEY_ARRAY1] = 1, 0
            _two[key] = p.add_shader(bytes(entry), nb)
    return _two[key]


def three_graftable(b, lay):
    """a one-texture template whose slot-1 UV can be grafted from the still one (graft_uv1, not one
    already animating slot 1): slot 2 is made from it too (three_texture_shader)"""
    return graftable(b, lay) and not eft_vertex.uv_caps(b)[1]


def three_texture_shader(p, si):
    """shader si (three_graftable) drawing three textures, added once: slots 1 and 2's UV animation
    grafted (slot 2 exported in a parameter of its own, a semantic the program doesn't use), a pixel
    input for it, 2D textureSampler1 / 2, its key's texture count 2. None when the graft doesn't take"""
    key = (id(p), si, 3)
    if key not in _two:
        b = bytes(p.shader_binary(si))
        lay = eft_pixel.layout(b)
        sem = lay['sems'][lay['uv'][0]]
        h = eft_vertex.vertex_header(b)
        params = 1 + ((h['regs'][2] >> 1) & 0x1F)
        used = {eft_vertex._param_semantic(h['regs'], q) for q in range(params)} | set(lay['sems'])
        sem2 = next(s for s in range(11, 64) if s not in used)
        nb = eft_vertex.graft_uv1(b, sem, sem2)
        if nb is None:
            _two[key] = None
        else:
            nb = eft_vertex.add_pixel_input(nb, sem, sem2)
            nb = eft_vertex.add_pixel_sampler(nb, 'textureSampler1', 1)
            nb = eft_vertex.add_pixel_sampler(nb, 'textureSampler2', 2)
            eft_pixel.GRAFTED[hashlib.md5(nb).hexdigest()] = sem2
            entry = bytearray(p.shader_entry(si))
            entry[KEY_TEXTURES], entry[KEY_ARRAY1], entry[KEY_ARRAY1 + 1] = 2, 0, 0
            _two[key] = p.add_shader(bytes(entry), nb)
    return _two[key]


def turning_shader(p, si):
    """shader si turning its particles, added once: v_inRot and the turn grafted into its vertex
    program (eft_vertex.graft_rot; its pixel program's layout kept: eft_pixel.GRAFTED). None when the
    graft doesn't take"""
    key = (id(p), si, 'rot')
    if key not in _two:
        b = bytes(p.shader_binary(si))
        nb = eft_vertex.graft_rot(b)
        if nb is None:
            _two[key] = None
        else:
            old = hashlib.md5(b).hexdigest()
            if old in eft_pixel.GRAFTED:
                eft_pixel.GRAFTED[hashlib.md5(nb).hexdigest()] = eft_pixel.GRAFTED[old]
            _two[key] = p.add_shader(bytes(p.shader_entry(si)), nb)
    return _two[key]


def set_slot1(p, em, e=None, ti=0, j=None, images=None, notes=None, slot=1, raw=False):
    """texture 1 (slot: 2) of a two- (three-) texture template: sampler j as Ultimate places it (its
    first cell, repeat, wrap, UV animation in the slot's block); white (x 1: nothing) without one.
    raw: a distortion map (distortion()): R R R A, the channels Ultimate's program reads for U and V"""
    if j is None:
        pix, ts, rep, wrap = np.ones((16, 16, 4), np.float32), None, (1, 1), (1, 1)
    else:
        s = e['sampler'][j]
        ts = e['static']['tex_scroll'][j]
        cell = first_cell(images[s['texture_id']], ts, shown_cell(e, j))
        if raw:
            # U from its red (its alpha with colour input 1), V from its alpha input (0 alpha, 1 red,
            # 2 one: Kaboom's smokeBase, its V moved by the coefficient alone)
            f = cell.astype(np.float32) / 255
            cb = e['combiner']
            u = f[..., 3] if cb['tex_color_input'][j] == 1 else f[..., 0]
            v = (np.ones_like(u), f[..., 0], f[..., 3])[{2: 0, 1: 1}.get(cb['tex_alpha_input'][j], 2)]
            pix = fit_texture(np.stack([u, u, u, v], -1))
            notes.append('sampler %d drawn live as texture %d (distortion map, UV mode %d)' % (j, slot, uv_mode(ts)))
        else:
            rgb, a = sampler_inputs(e, j, cell)
            pix = fit_texture(np.concatenate([rgb, a[..., None]], -1))
            cbl, abl = tex_blend(e, ti, j)
            notes.append('sampler %d drawn live as texture %d (colour %s, alpha %s, UV mode %d)' % (
                j, slot, 'x+-'[cbl % 3], 'x+-'[abl % 3], uv_mode(ts)))
        rep, wrap = REPEAT.get(e['tex_anim'][j]['repeat'], (1, 1)), (s['wrap_u'], s['wrap_v'])
    set_exact_texture(p, em, slot, pix)
    set_wrap(em, slot, *wrap)
    struct.pack_into('>2f', em, 0x508 + SLOT1 * slot, float(rep[0]), float(rep[1]))
    em[0x4D7 + SLOT1 * slot], em[0x4D8 + SLOT1 * slot] = 1, 1
    struct.pack_into('>I', em, PTN_MODE + SLOT1 * slot, 0)
    set_uv_anim(em, ts, slot=slot)


def _texblend(x, y, mode):
    """eft2's texture blend: 0 multiply, 1 add, 2 subtract (x - y: tools/eft_pixel.py _blend)"""
    return x + y if mode == 1 else x - y if mode == 2 else x * y


def exact_texture(e, ti, img, ptn, images, names, notes, is_mesh, live=None, live2=None):
    """the texture an own pixel program (tools/eft_pixel.py) reads, [h, w, 4] 0-1: Ultimate's colour
    input in rgb and its alpha input in a, sampler ti's (img: one cell or the flipbook sheet) with
    the emitter's other samplers combined in as eft2 does (tex1 / tex2 colour and alpha blends: 0
    multiply, 1 add), each sampled over sampler ti's quad as bake_samplers places it (frozen at its
    start). Distortion maps ('indirect') only move the picture: left out. A mesh's other samplers
    read their own UVs: they come in as their mean (Kafrizz's sphere1, a gradient x ef_brave_mask02:
    left out, the ball drew at the gradient's full alpha)"""
    rgb, a = sampler_inputs(e, ti, img)
    cb = e['combiner']
    others = [(j, s) for j, s in enumerate(e['sampler']) if j not in (ti, live, live2) and s['texture_id'] != NONE64
              and s['texture_id'] in images and not is_indirect(e, j, names)]
    if not others:
        return np.concatenate([rgb, a[..., None]], -1)
    if is_mesh:
        meaned, same = [], []
        for j, s in others:
            orgb, oa = sampler_inputs(e, j, first_cell(images[s['texture_id']], e['static']['tex_scroll'][j],
                                                      shown_cell(e, j)))
            k = 2 if j == 2 or (j == 0 and ti == 2) else 1
            if same_uv(e, ti, j) and not ptn:
                # the same UVs as sampler ti all life (Swoosh's whirlwind columns: ef_cmn_wind00 in
                # both, its red x its alpha): their product texel by texel is exact
                m_rgb, m_a = resize(orgb, rgb.shape[1], rgb.shape[0]), resize(oa[..., None], a.shape[1], a.shape[0])[..., 0]
                same.append(j)
            else:
                m_rgb, m_a = orgb.reshape(-1, 3).mean(0), float(oa.mean())
                meaned.append(j)
            rgb = _texblend(rgb, m_rgb, cb['tex%d_color_blend' % k])
            a = _texblend(a, m_a, cb['tex%d_alpha_blend' % k])
        if same:
            notes.append('samplers %s combined texel by texel (same UVs)' % ','.join(map(str, same)))
        if meaned:
            notes.append('samplers %s in as their mean (mesh)' % ','.join(map(str, meaned)))
        return np.clip(np.concatenate([rgb, a[..., None]], -1), 0, 1)
    nx, ny = ((max(1, int(round(v))) for v in e['static']['tex_scroll'][ti]['uv_div']) if ptn else (1, 1))
    h, w = rgb.shape[0] // ny, rgb.shape[1] // nx
    yy, xx = np.mgrid[0:h, 0:w]
    quad = np.stack([(xx.ravel() + 0.5) / w, (yy.ravel() + 0.5) / h], 1).astype(np.float32)
    for j, s in others:
        ts = e['static']['tex_scroll'][j]
        src = first_cell(images[s['texture_id']], ts, shown_cell(e, j))
        orgb, oa = sampler_inputs(e, j, src)
        uv = uv_transform(quad * np.array(REPEAT.get(e['tex_anim'][j]['repeat'], (1, 1)), np.float32),
                          ts['scale'], ts['scroll'], ts['rotation'])
        sh, sw = oa.shape
        iy = (wrap_uv(uv[:, 1], s['wrap_v']) * sh).astype(int)
        ix = (wrap_uv(uv[:, 0], s['wrap_u']) * sw).astype(int)
        orgb, oa = orgb[iy, ix].reshape(h, w, 3), oa[iy, ix].reshape(h, w)
        k = 2 if j == 2 or (j == 0 and ti == 2) else 1     # the blend that brings sampler 1 / 2 in
        bc, ba = cb['tex%d_color_blend' % k], cb['tex%d_alpha_blend' % k]
        for cy in range(ny):
            for cx in range(nx):
                ys, xs = slice(cy * h, (cy + 1) * h), slice(cx * w, (cx + 1) * w)
                rgb[ys, xs] = _texblend(rgb[ys, xs], orgb, bc)
                a[ys, xs] = _texblend(a[ys, xs], oa, ba)
    notes.append('samplers %s combined in' % ','.join(str(j) for j, _s in others))
    return np.clip(np.concatenate([rgb, a[..., None]], -1), 0, 1)


def exact_combiner(p, em, e, alpha, notes, blend1=(0, 0), dissolve=None, dissolve_c0=False, blend2=(0, 0),
                   distort=None):
    """(shader index, alpha keys, alpha gain) when the template's pixel program can be replaced by
    one of tools/eft_pixel.py's for this emitter's combiner (EXACT), else None. alpha: the alpha
    track [101] (alpha 0, x alpha 1 for alpha mode 4: folded into the keys). Ultimate's alphas past 1
    (its whirlwinds' 2 - 4) go into the program's gain, the keys / gain. blend1: how a two-texture
    template's texture 1 combines (tex_blend); dissolve: the dissolve's edge width (dissolve_of), its
    threshold in colour 0's track (dissolve_c0: colour 0 then constants) or colour 1's; distort:
    texture 1 a distortion map (distortion())"""
    if not EXACT:
        return None
    sh, cb = e['shader'], e['combiner']
    if (sh['custom_shader_index'], sh['custom_shader_flag'] & PREMULT_SHADER[1]) == PREMULT_SHADER:
        return None
    am = cb['alpha_process']
    erode = am in (1, 3)
    gain = 1.0 if erode else max(1.0, float(np.max(alpha)))
    # colour 1 at its life mean x the colour scale, for a template that doesn't pass colour 1
    c1 = track(e['static'], e['color'], 1)[0].mean(0) * np.array(e['info']['color1'][:3]) \
        * float(e['static']['color_scale'] or 1.0)
    c0 = track(e['static'], e['color'], 0)[0].mean(0) * np.array(e['info']['color0'][:3]) \
        * float(e['static']['color_scale'] or 1.0) if dissolve is not None and dissolve_c0 else None
    si = eft_pixel.own_shader(p, struct.unpack_from('>I', em, 0x844)[0], cb['color_process'],
                              1 if erode else 0, gain, c1, blend1, dissolve, c0, blend2, distort)
    if si is None:
        notes.append('own pixel program: template layout not supported')
        return None
    lay = eft_pixel.layout(bytes(p.shader_binary(si)))
    notes.append('own pixel program (colour %d, alpha %d%s%s%s%s)' % (
        cb['color_process'], am, ', x %.2f' % gain if gain != 1.0 else '',
        ', colour 1 constant' if (lay['c1'] is None or (dissolve is not None and not dissolve_c0))
        and cb['color_process'] in (2, 3) else '',
        ', dissolve (edge %.2f, threshold in colour %d)' % (dissolve, not dissolve_c0) if dissolve is not None else '',
        ', premultiplied' if eft_pixel.premultiplied(p, si) else '')
        + (', UVs distorted by texture 1 (%.3f, %.3f)' % tuple(distort) if distort is not None and 'uv1' in lay else ''))
    return si, np.clip(alpha / gain, 0, 1), gain


def flipbook_fade(e, ti, sheet, notes):
    """[101] the alpha over life of a flipbook shown as one cell (no template plays its mode): each
    cell's ink (mean alpha) as Ultimate plays them, against the shown cell's. F-smash's impact1 runs
    ef_cmn_impact00 from a thick burst to thin wisps once over its life; frozen on its first cell it
    stayed a solid band. Life-fit (1) spreads the table over the life, clamp / loop (2 / 3) step a cell
    each frequency frames (clamp holds the last); random (4): no fade"""
    if sheet is None:
        return np.ones(101)
    ts, tp, kind = e['static']['tex_scroll'][ti], e['static']['tex_pat'][ti], e['tex_anim'][ti]['pattern_type']
    nx, ny = (max(1, int(round(v or 1))) for v in ts['uv_div'])
    cells = nx * ny
    table = [int(v) % cells for v in tp['table'][:int(tp['num'])]] if tp['num'] else list(range(cells))
    if kind not in (1, 2, 3) or len(table) < 2:
        return np.ones(101)
    f = sheet.astype(np.float32) / 255
    a = f[..., 0] if e['combiner']['tex_alpha_input'][ti] == 1 or e['combiner']['alpha_process'] in (2, 3) else f[..., 3]
    h, w = a.shape[0] // ny, a.shape[1] // nx
    ink = np.array([float(a[(c // nx) * h:(c // nx + 1) * h, (c % nx) * w:(c % nx + 1) * w].mean()) for c in range(cells)])
    shown = ink[shown_cell(e, ti)]
    if shown <= 1e-6:
        return np.ones(101)
    t = np.linspace(0, 1, 101)
    if kind == 1:
        idx = np.minimum((t * len(table)).astype(int), len(table) - 1)
    else:
        life = max(1, int(e['particle'].get('life') or 1))
        step = (t * life / max(float(tp['frequency'] or 1), 1e-3)).astype(int)
        idx = np.minimum(step, len(table) - 1) if kind == 2 else step % len(table)
    fade = np.clip(ink[np.array(table)[idx]] / shown, 0, 1)
    notes.append('flipbook as one cell: alpha x the cells\' ink over life (%.2f at the end)' % fade[-1])
    return fade


def first_cell(img, scroll, cell=0):
    """a flipbook's cell (row-major, uv_div columns x rows)"""
    nx, ny = (int(round(v)) if v and v >= 1 else 1 for v in scroll['uv_div'])
    h, w = img.shape[:2]
    ch, cw = max(4, h // ny), max(4, w // nx)
    cy, cx = divmod(int(cell) % (nx * ny), nx)
    return img[cy * ch:(cy + 1) * ch, cx * cw:(cx + 1) * cw]


def shown_cell(e, ti):
    """the flipbook cell to show (eft's flipbooks aren't converted): the first one Ultimate's
    pattern animation plays (its table's first entry; e.g. neutral air's impact rings start at cell
    1, cell 0 being the full solid shape)"""
    if not e['tex_anim'][ti]['pattern_type']:
        return 0
    tp = e['static']['tex_pat'][ti]
    return tp['table'][0] if tp['num'] else 0


LUMA = np.array([0.299, 0.587, 0.114])


def track(st, col, n):
    """colour track n (0 / 1) over the particle's life [101, 3] and alpha track n [101]"""
    c = keys(st['color%d' % n], st['num_color%d_keys' % n]) if col['color%d_type' % n] == 2 else \
        np.tile(np.array(col['color%d' % n][:3], float), (101, 1))
    a = keys(st['alpha%d' % n], st['num_alpha%d_keys' % n], 1)[:, 0] if col['alpha%d_type' % n] == 2 else \
        np.full(101, float(col['color%d' % n][3]))
    return c, a


def combine(img, e, notes, ti=0, fill=1.0, two_colour=False):
    """eft2's combiner on the main texture, folded into what a one-colour eft template draws (a BC4
    shape x the particle colour): (shape [h, w] 0-1, colour [101, 3], alpha [101]).
    Colour modes (combiner color_process): 0 colour 0; 1 colour 0 x texture; 2 colour 0 x texture +
    colour 1 x (1 - texture); 3 colour 0 x texture + colour 1. Each pixel's colour at the tracks' life
    means, weighted by the texture's alpha: their mean is the particle colour, each pixel's
    brightness against it the shape (the hue across the texture is lost, its brightness kept); the
    colour over life is the same mix of the tracks at the texture's mean. Alpha modes (alpha_process):
    0 / 1 texture alpha x alpha 0 (1 erodes the texture by alpha 0: a fade by the ink left), 2 / 3 the
    same with the texture's red, 4 texture alpha x alpha 0 x alpha 1.
    Custom shader 4 with flag 64 (PREMULT_SHADER: his dark fire / aura, read off its Maxwell code in
    the file's BNSH, all 13 of them; flags 32 / 1, his smoke / planes, and the 125 shader_type 2
    emitters without a custom shader don't): the colour is the tracks' mix by the alpha shape, not
    the texture's colour (0: colour 0;
    2: colour 1 + (colour 0 - colour 1) x shape), and goes out x the shape x 2 before blending (which
    multiplies by it again): a mostly faint shape (ef_cmn_fire00) draws dark, his black flames. Then
    the shape is the alpha shape and the 4th value the shape's mean (the colour isn't x 2 yet: the
    template's colour mode decides how the x shape is drawn); else None.
    two_colour (colour mode 2; TWO_COLOUR): the shape is the alpha shape and the texture's rgb is
    fitted against it (r ~ k1 + (k0 - k1) x shape, weighted by the shape), so a lerp template draws
    colour 1 + (colour 0 - colour 1) x shape with colour 0 / 1 the tracks' mix at k0 / k1: the 5th
    value is that colour 1 [101, 3] (else None)."""
    st, col, cb, info = e['static'], e['color'], e['combiner'], e['info']
    c0, a0 = track(st, col, 0)
    c1, a1 = track(st, col, 1)
    c0 = c0 * np.array(info['color0'][:3])
    c1 = c1 * np.array(info['color1'][:3])
    f = img.astype(np.float32) / 255
    rgb = f[..., :3]
    am = cb['alpha_process']
    atex = f[..., 0] if am in (2, 3) or cb['tex_alpha_input'][ti] == 1 else f[..., 3]
    cm = cb['color_process']
    m0, m1 = c0.mean(0), c1.mean(0)
    premult, colour1 = None, None
    sh = e['shader']
    if (sh['custom_shader_index'], sh['custom_shader_flag'] & PREMULT_SHADER[1]) == PREMULT_SHADER:
        premult = float((atex * atex).sum() / max(float(atex.sum()), 1e-6))
        k = premult if cm in (2, 3) else 1.0
        colour = c0 * k + c1 * ((1 - k) if cm == 2 else 1.0 if cm == 3 else 0.0)
        shape = atex
        notes.append('custom shader: colour by the shape (%.2f), x the shape x 2' % premult)
    elif two_colour and cm == 2:
        r, u = rgb.mean(-1), atex
        sw, su, sr = float(u.sum()), float((u * u).sum()), float((u * r).sum())
        suu, sur = float((u ** 3).sum()), float((u * u * r).sum())
        b = (sw * sur - su * sr) / max(sw * suu - su * su, 1e-9)
        k1 = float(np.clip((sr - b * su) / max(sw, 1e-9), 0, 1))
        k0 = float(np.clip(k1 + b, 0, 1))
        colour, colour1 = c1 + (c0 - c1) * k0, c1 + (c0 - c1) * k1
        shape = atex
        notes.append('two colours: texture rgb ~ %.2f at the shape\'s peak, %.2f at its edge' % (k0, k1))
    else:
        if cm == 0:
            pix = np.broadcast_to(m0, rgb.shape)
        elif cm == 1:
            pix = rgb * m0
        elif cm == 2:
            pix = rgb * m0 + (1 - rgb) * m1
        else:
            pix = rgb * m0 + m1
        w = atex[..., None]
        wsum = max(float(w.sum()), 1e-6)
        tm = (rgb * w).reshape(-1, 3).sum(0) / wsum                     # the texture's mean (per channel)
        cmean = (pix * w).reshape(-1, 3).sum(0) / wsum
        lc = max(float(cmean @ LUMA), 1e-4)
        shape = atex * (pix @ LUMA) / lc
        peak = max(float(shape.max()), 1e-4)
        shape = shape / peak
        if cm == 0:
            colour = c0
        elif cm == 1:
            colour = c0 * tm
        elif cm == 2:
            colour = c0 * tm + c1 * (1 - tm)
        else:
            colour = c0 * tm + c1
        colour = colour * peak * float(cmean @ LUMA > 0)
    alpha = a0 * info['color0'][3] * (a1 * info['color1'][3] if am == 4 else 1.0) * fill
    if am in (1, 3):
        # erosion: each pixel is texture - (1 - alpha), so the faint parts go first and the bright
        # strokes last (the texture can't change over life here): the fade kept is the texture's
        # remaining ink against its full ink
        t = atex[::max(1, atex.shape[0] // 64), ::max(1, atex.shape[1] // 64)].ravel()
        ink = max(float(t.sum()), 1e-6)
        alpha = np.array([np.clip(t - (1 - a), 0, 1).sum() / ink for a in np.clip(alpha, 0, 1)])
        notes.append('alpha erosion: fade by the remaining ink')
    return (shape, np.clip(colour, 0, None), np.clip(alpha, 0, 1), premult,
            None if colour1 is None else np.clip(colour1, 0, None))


def eft_rotation(rot):
    """eft2's emitter rotation (radians, applied Z then Y then X: R = Rx Ry Rz) as eft's angles
    (applied X then Y then Z: R = Rz Ry Rx, Ptcl.set_emitter_srt). eft2's order, from 86 streak
    emitters (types 5 / 6 moving along a designated direction, rotated about 2+ axes) in 31
    fighters' VFXBs: their offset lies across their motion in 53 with Z first (13 with X first),
    along it in 10 (51): layered speed lines side by side, not one behind the other. Sephiroth's
    forward-air lines (90, 0, 90 degrees) ran along their own offset (test 43: "the wrong plane")"""
    a, b, c = (float(v) for v in rot[:3])
    if sum(abs(v) > 1e-6 for v in (a, b, c)) < 2:
        return a, b, c
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    r = (np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]]) @ np.array([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]])
         @ np.array([[cc, -sc, 0], [sc, cc, 0], [0, 0, 1]]))
    y = math.asin(max(-1.0, min(1.0, -r[2, 0])))
    if abs(r[2, 0]) < 1 - 1e-6:
        x, z = math.atan2(r[2, 1], r[2, 2]), math.atan2(r[1, 0], r[0, 0])
    else:                                                   # gimbal lock: all of it in x
        x, z = math.atan2(-r[1, 2], r[1, 1]), 0.0
    return x, y, z


def crossed_ribbon(pos, nrm, col, uv, idx, notes):
    """a flat ribbon along Y (his sword glows: 25.5 long, 2 wide, ~0 thick) with a copy turned 90
    degrees about Y. Ultimate's directional type keeps such a mesh facing the camera round its Y
    (the glow shows along the blade in every move); held in the sword's frame it went edge-on at
    some rolls (test 47: forward air without a glow). Crossed, one of the two always faces it"""
    span = pos.max(0) - pos.min(0)
    if span[1] <= 0 or min(span[0], span[2]) > 0.1 * span[1] or max(span[0], span[2]) > 0.3 * span[1]:
        return pos, nrm, col, uv, idx
    turn = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], np.float32)
    notes.append('ribbon crossed')
    idx = np.asarray(idx).reshape(-1)
    return (np.concatenate([pos, pos @ turn.T]), np.concatenate([nrm, nrm @ turn.T]),
            None if col is None else np.concatenate([col, col]), np.concatenate([uv, uv]),
            np.concatenate([idx, idx + len(pos)]))


def radial_gradient(shape, notes, n=64):
    """a one-way gradient (Ultimate's ef_cmn_grade00: bright at V 0, gone by V 0.4; the same in every
    column) read outward from the centre. The flare meshes read it so (their UVs polar: V the radius);
    on a quad it was a lit square (the pummel's / down throw's pointlight1: test 49's pink diamond)"""
    if shape.shape[0] < 4 or shape.shape[1] < 4:
        return shape
    for prof, flat in ((shape.mean(1), shape.std(1).max()), (shape.mean(0), shape.std(0).max())):
        if flat < 0.02 and prof.max() - prof.min() > 0.5:
            yy, xx = np.mgrid[0:n, 0:n] + 0.5
            r = np.clip(np.hypot(xx - n / 2, yy - n / 2) / (n / 2), 0, 1)
            if prof[0] < prof[-1]:
                prof = prof[::-1]
            # to 0 at the rim (grade00's dark end is ~0.1: a faint lit square on a bright piece)
            prof = np.clip((prof - prof[-1]) / max(float(prof[0] - prof[-1]), 1e-6), 0, 1) * prof[0]
            notes.append('gradient on a quad: read from the centre')
            return np.interp(r, np.linspace(0, 1, len(prof)), prof).astype(np.float32)
    return shape


def rotation_need(st, is_mesh):
    """ROT_NONE / ROT_FIXED / ROT_ANIMATED for an emitter's particle rotation"""
    init, rand, add = st['rotate_init'][:3], st['rotate_init_rand'][:3], st['rotate_add'][:3]
    if not any(abs(v) > 1e-6 for v in init + rand + add):
        return ROT_NONE
    if any(abs(v) > 1e-6 for v in rand + add):
        return ROT_ANIMATED
    return ROT_FIXED if is_mesh or fixed_quarter_turn(st) else ROT_ANIMATED


def rotation_matrix(rot):
    """eft's particle rotation (radians): Y, then Z, then X (R = Rx Rz Ry, column vectors; a turning
    mesh shader's vertex program builds it from v_inRot so, its x column scaling the position's x:
    the emitter's own order, X Y Z, differs)"""
    a, b, c = rot
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    return (np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]]) @ np.array([[cc, -sc, 0], [sc, cc, 0], [0, 0, 1]])
            @ np.array([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]]))


def fixed_quarter_turn(st):
    """a particle turned a fixed whole number of quarter turns about Z (no other axis, no random or
    spin): that number, 1-3 (counter-clockwise), else None"""
    x, y, z = (float(v) for v in st['rotate_init'][:3])
    if abs(x) > 1e-3 or abs(y) > 1e-3 or any(abs(v) > 1e-6 for v in st['rotate_init_rand'][:3] + st['rotate_add'][:3]):
        return None
    q = z / (math.pi / 2)
    if abs(q - round(q)) > 1e-3:
        return None
    return int(round(q)) % 4 or None


def uv_mode(ts):
    """the UV animation bits (1 scroll, 2 scale, 4 rotate) a sampler's eft2 UV parameters need"""
    if ts is None:
        return 0
    nz = lambda v: any(abs(x) > 1e-6 for x in (v if isinstance(v, list) else [v]))  # noqa: E731
    return (1 if nz(ts['scroll']) or nz(ts['scroll_add']) or nz(ts['scroll_random']) else 0) \
        | (2 if nz([x - 1 for x in ts['scale']]) or nz(ts['scale_add']) or nz(ts['scale_random']) else 0) \
        | (4 if nz(ts['rotation']) or nz(ts['rotation_add']) or nz(ts['rotation_random']) else 0)


# How both games move a texture (slot 0): about its centre, scale (rotation (uv x repeat - 0.5)) -
# shift + 0.5 (Smash 4: every vanilla vertex program that scrolls, shader 142's groups 37-47, the
# uniforms copied unchanged at 0x04A5A6AC, docs/ptcl-format.md; Ultimate: its vertex programs
# subtract 0.5 before the scale and add it back after). An earlier reading from where clamped,
# shifted meshes land on their texture had Smash 4 adding the shift and both scaling about the
# corner (uv x scale - shift); test 30 showed the scrolls that came of it running backwards.
def uv_transform(uv, scale, scroll, rotation):
    """the UV transform at a time (repeat already applied): turned and scaled about the texture's
    centre, then shifted, as both games' vertex programs draw it"""
    c, s = math.cos(rotation), math.sin(rotation)
    q = uv - 0.5
    r = np.stack([q[:, 0] * c - q[:, 1] * s, q[:, 0] * s + q[:, 1] * c], 1)
    return (r * np.array(scale, np.float32) - np.array(scroll, np.float32) + 0.5).astype(np.float32)


def set_flipbook(em, ptn, ts, tp, rep=(1, 1)):
    """slot 0's flipbook from eft2's pattern animation (PTN_MODE); ptn 0: none (one cell shown,
    first_cell). Cells across / down from eft2's uv_div, the UV scale repeat / cells, its table (eft2's
    num entries of it), frames a cell (frequency) and random start cells (num_random)"""
    struct.pack_into('>I', em, PTN_MODE, ptn)
    if not ptn:
        return
    nx, ny = (max(1, int(round(v))) for v in ts['uv_div'])
    num = int(tp['num']) if tp['num'] else nx * ny
    em[0x4D5] = 1 if tp['num'] else 0
    em[0x4D7], em[0x4D8] = nx, ny
    em[0x4D9] = max(1, int(tp['num_random']))
    em[0x4E0:0x500] = bytes(min(255, max(0, int(v))) for v in tp['table'][:32])
    struct.pack_into('>hh', em, 0x504, max(1, int(round(tp['frequency']))) if ptn in (2, 4) else 0, num)
    struct.pack_into('>2f', em, 0x508, rep[0] / nx, rep[1] / ny)


def set_uv_anim(em, ts, slot=0):
    """eft2's UV parameters (shift / scale / rotation: initial, random, per frame) -> slot 0's eft
    block: 0x514 scroll a frame, 0x51C scroll init, 0x524 scroll random, 0x52C scale a frame, 0x534 scale init, 0x53C
    scale random, 0x544 rotation a frame, 0x548 rotation init, 0x54C rotation random; the template's
    vertex program draws all of them or none (eft_vertex.uv_caps; the mode word 0x510 is read by
    nothing). Unused ones are left neutral. The
    shifts keep their sign: eft subtracts them as eft2 does (cross_f.rpx 0x04A5A6AC copies 0x514-0x54C
    into the static uniforms' shtAnim0 unchanged; the vertex programs draw s (uv x repeat - 0.5) -
    (t x a frame + initial +- random) + 0.5 on both axes). Fix 29 and before negated them: every
    scroll ran backwards (F-smash's crown2_back: its band climbed the cone instead of sinking)."""
    if ts is None:
        ts = {'scroll': [0, 0], 'scroll_add': [0, 0], 'scroll_random': [0, 0], 'scale': [1, 1],
              'scale_add': [0, 0], 'scale_random': [0, 0], 'rotation': 0, 'rotation_add': 0, 'rotation_random': 0}
    o = SLOT1 * slot
    struct.pack_into('>2f', em, o + 0x514, *ts['scroll_add'])
    struct.pack_into('>2f', em, o + 0x51C, *ts['scroll'])
    struct.pack_into('>2f', em, o + 0x524, *ts['scroll_random'])
    struct.pack_into('>2f', em, o + 0x52C, *ts['scale_add'])
    struct.pack_into('>2f', em, o + 0x534, *ts['scale'])
    struct.pack_into('>2f', em, o + 0x53C, *ts['scale_random'])
    struct.pack_into('>3f', em, o + 0x544, ts['rotation_add'], ts['rotation'], ts['rotation_random'])


def convert_emitter(p, e, names, images, notes, templates, prims, prim_index, as_child=False):
    """one Ultimate emitter as an eft emitter (bytes; None when skipped). as_child: a child emitter's,
    for child_block to take its drawing from: one texture, the CPU's particles, nothing complex"""
    pt = e['particle']
    if not e['info']['is_particle_draw']:
        # Ultimate doesn't draw it (eft2's is_particle_draw; none of Hero's 5 has child emitters):
        # F-smash's impact2_frontL, a solid yellow zigzag over the ground spikes in fix 27
        notes.append('not drawn in Ultimate (is_particle_draw 0): skipped')
        return None
    if e['combiner']['shader_type'] == 1:
        # a refraction piece (it bends the picture behind it: back throw's indirect1, the entry's
        # rifrection1): no template reads the screen (SCREEN_SAMPLERS), and drawn plain its
        # normal-map texture is a tinted blob
        notes.append('refraction: skipped')
        return None
    typ = TYPES.get(pt['billboard_type'])
    if typ is None:
        notes.append('billboard type %d: skipped' % pt['billboard_type'])
        return None
    is_mesh = pt['primitive_id'] != NONE64
    if is_mesh and as_child:
        notes.append('child mesh: skipped (eft\'s children are quads)')
        return None
    if is_mesh and pt['primitive_id'] not in prims:
        notes.append('primitive %d not in the file: skipped' % pt['primitive_id'])
        return None
    vel = e['velocity']
    rest_dir = False
    if is_mesh and typ == 3 and abs(vel['all_direction']) + abs(vel['designated_dir_scale']) < 1e-3:
        # a directional mesh at rest (his sword glows, slash arcs) lies in the emitter's frame in
        # Ultimate; eft's directional type 3 turns it by its (zero) velocity (test 32: the up-air arc
        # lay flat), type 4 keeps the emitter's frame at rest (Zelda's Nayru's Love crystals)
        typ = 4
        rest_dir = True
        notes.append('directional mesh at rest: type 4')
    elif is_mesh and typ == 3 and abs(vel['all_direction']) < 1e-3 and abs(abs(vel['designated_dir'][1]) - 1) < 1e-3 \
            and not any(abs(v) > 1e-3 for v in [vel['diffusion_dir_angle'], vel['xz_diffusion'], vel['diffusion'][0],
                                                vel['diffusion'][2]]):
        # a directional mesh moving straight along the emitter's Y (Woosh's whirlwinds, rising) stands
        # along it in Ultimate, which is the emitter's frame; eft's type 3 turned it end-on to the camera
        # (the whirlwind test: a flat red ring at his feet). Type 4 keeps the emitter's frame. A spread
        # along Y alone keeps it on Y (Swoosh / Kaswoosh's big funnels, diffusion 0 0.1 0, following the
        # moving projectile: as type 3 eft aimed them along its travel, a flat blue disc, fix 51)
        typ = 4
        notes.append('directional mesh moving along Y: type 4')
    elif is_mesh and pt['billboard_type'] in (5, 6):
        # a "stripe" mesh (no ribbon data: its shape is the mesh) keeps the emitter's frame: neutral
        # air's rainbow1, a flat 69-unit disc laid level (emitter X 90) and sent off in a random
        # direction, faced its motion as type 3 (test 43-44's purple disc; Ultimate shows none)
        typ = 4
        notes.append('stripe mesh: type 4')
    blend = {0: 'normal', 1: 'add', 2: 'sub'}.get(e['render']['blend_type'], 'add')
    ti, smp = main_texture(e, names)
    fill = 1.0
    if smp:
        ti, fill = shape_sampler(e, ti, images, notes, names)
        smp = e['sampler'][ti]
    ts = e['static']['tex_scroll'][ti] if smp else None
    uv_quarter = 0
    if ts is not None and pt['primitive_id'] == NONE64 and uv_mode(ts) == 4 and not ts['rotation_add'] \
            and not ts['rotation_random']:
        # a quad's texture turned a fixed number of quarter turns (and nothing else): turned in the
        # image, so no template needs UV rotation (down smash's speed lines, Octaslash's lines)
        q = ts['rotation'] / (math.pi / 2)
        if abs(q - round(q)) < 1e-3:
            uv_quarter = int(round(q)) % 4
            ts = dict(ts, rotation=0.0)
    ptn_want = PTN_FROM_EFT2.get(e['tex_anim'][ti]['pattern_type'], 0) if smp else 0
    if ptn_want and all(int(round(v or 1)) <= 1 for v in e['static']['tex_scroll'][ti]['uv_div']):
        # a one-cell sheet plays nothing; as a flipbook its UV scale (1 / cells) would replace the
        # repeat (forward air's X, a quarter texture repeated 2 x 2 mirrored, drew one quarter from
        # test 39 on: a ">" at the blade tip)
        ptn_want = 0
    tp = e['static']['tex_pat'][ti] if smp else None
    st = e['static']
    if is_mesh and pt['billboard_type'] == 3 and not all(pt['is_rotate']):
        # a directional mesh turns only about the axes its is_rotate enables: Woosh's whirlwinds
        # (is_rotate 0 1 0, rotate_init X 180: turned so, the mesh hung upside down under the stage,
        # nothing of it showed) spin about Y and stand upright in Ultimate. Observed on them, not
        # derived, so kept to directional meshes: billboards keep their rotation whatever is_rotate
        # says (96 Z-turning ones have it all 0), and the chant's crossed rings (type 4, X 45 with X
        # disabled) look right turned
        st = dict(st, **{k: [0.0 if a < 3 and not pt['is_rotate'][a] else v for a, v in enumerate(st[k])]
                         for k in ('rotate_init', 'rotate_init_rand', 'rotate_add', 'rotate_add_rand')})
        if any(abs(a - b) > 1e-6 for a, b in zip(st['rotate_init'], e['static']['rotate_init'])):
            notes.append('rotation about disabled axes dropped (is_rotate %s)' % ''.join(map(str, pt['is_rotate'])))
    # a directional mesh at rest keeps no particle rotation: his slash arcs (all turned Z 180,
    # their glows Y -20 too, spinning) looked right unturned (test 36: back / up air "nearly
    # right") and wrong turned (tests 44 / 45: the arc a whole disc, behind him too). Ultimate's
    # directional basis at rest evidently undoes it (his sword glows, unturned, extend along +Y,
    # so it isn't a plain flip of every such mesh); not derived, only observed
    rot = ROT_NONE if rest_dir else rotation_need(st, is_mesh)
    anim = tuple(e['color']['color%d_type' % n] == 2 and float(np.ptp(track(e['static'], e['color'], n)[0], 0).max()) > 0.05
                 for n in (0, 1))
    # a second sampler moving apart from the main one: drawn live by a two-texture template
    dis = dissolve_of(e, ti, images, names, ptn_want) if EXACT and smp and not as_child else None
    # a dissolve's threshold rides in colour 1's track, or colour 0's when its rgb is constant
    c0_flat = float(np.ptp(track(e['static'], e['color'], 0)[0], 0).max()) <= 0.01
    dis_moving = dis is not None and float(np.ptp(dis[1])) > 0.01
    live = live_sampler(e, ti, images, names, is_mesh) if EXACT and TWO_TEXTURES and smp and not uv_quarter and \
        dis is None and not as_child else None
    # Ultimate's distortion (shader_type 2): its map, sampler 0, drawn live as texture 1 moving texture
    # 0's UVs (Bang / Kaboom's smoke, his fire spells' flames waver); a third sampler as texture 2
    warp = distortion(e, ti, images, is_mesh) if EXACT and TWO_TEXTURES and smp and not uv_quarter and \
        dis is None and not as_child else None
    if warp is not None:
        live = 0
    # samplers 1 and 2 both drawn live by a three-texture graft (three_texture_shader), in eft2's order
    # (t0 . t1) . t2: sampler 0 the main one, the other two its UV set's on a mesh
    live3 = None
    if warp is not None and GRAFT and not templates.no_graft and ti == 1:
        s2 = e['sampler'][2]
        if s2['texture_id'] != NONE64 and s2['texture_id'] in images and not e['tex_anim'][2]['pattern_type'] \
                and not same_uv(e, ti, 2) \
                and (not is_mesh or e['tex_anim'][2]['uv_channel'] == e['tex_anim'][ti]['uv_channel']):
            live3 = (0, 2)
    elif EXACT and TWO_TEXTURES and GRAFT and not templates.no_graft and smp and not uv_quarter and dis is None \
            and ti == 0 and not as_child:
        usable = [j for j in (1, 2) if e['sampler'][j]['texture_id'] != NONE64 and e['sampler'][j]['texture_id'] in images
                  and not is_indirect(e, j, names)
                  and not e['tex_anim'][j]['pattern_type']
                  and (not is_mesh or e['tex_anim'][j]['uv_channel'] == e['tex_anim'][0]['uv_channel'])]
        if usable == [1, 2] and not (live is not None and same_uv(e, 0, 3 - live)):
            live3 = (1, 2)
    # the two may trade slots: no flipbook either side (slot 1 has none), nothing else combined in
    swap_ok = live is not None and warp is None and not ptn_want and not e['tex_anim'][live]['pattern_type'] and not [
        j for j, s in enumerate(e['sampler']) if j not in (ti, live) and s['texture_id'] != NONE64
        and s['texture_id'] in images and not is_indirect(e, j, names)]
    if live3:
        live, swap_ok = live3[0], False
    fblocks, fanims, fdone = particle_fields(e) if not as_child else ({}, [], set())
    fluct = fluctuation(e) if not as_child else None
    child, child_e = None, (e['children'] or [None])[0] if not as_child else None
    em, turns, swapped = templates.get(typ, BLEND[blend], is_mesh, uv_mode(ts), e['info']['follow_type'], ptn_want, rot,
                                       notes, anim, e['combiner']['color_process'] in (2, 3) or dis is not None,
                                       live is not None,
                                       uv_mode(e['static']['tex_scroll'][live]) if live is not None else 0, swap_ok,
                                       (2 if c0_flat else 1) if dis_moving else 0, live3 is not None,
                                       bool(fblocks) or as_child or child_e is not None, fluct is not None)
    if swapped:
        ti, live = live, ti
        smp, ts, tp = e['sampler'][ti], e['static']['tex_scroll'][ti], e['static']['tex_pat'][ti]
    lay_t = eft_pixel.layout(bytes(p.shader_binary(struct.unpack_from('>I', em, 0x844)[0]))) if EXACT else None
    live2 = None
    if live3 and lay_t is not None and 'uv1' not in lay_t and \
            three_graftable(bytes(p.shader_binary(struct.unpack_from('>I', em, 0x844)[0])), lay_t):
        si3 = three_texture_shader(p, struct.unpack_from('>I', em, 0x844)[0])
        if si3 is not None:
            struct.pack_into('>I', em, 0x844, si3)
            lay_t = eft_pixel.layout(bytes(p.shader_binary(si3)))
            live2 = 2
            notes.append('vertex program grafted: slot 1 and 2 UV animation')
    if live3 and live2 is None:
        # no three-texture template: as before (one live sampler, if the blends allow; the map)
        live = 0 if warp is not None else live_sampler(e, ti, images, names, is_mesh)
    if live is not None and GRAFT and not templates.no_graft and lay_t is not None and 'uv1' not in lay_t and \
            graftable(bytes(p.shader_binary(struct.unpack_from('>I', em, 0x844)[0])), lay_t):
        # a one-texture template taken for two (Templates): its vertex program grafted
        si2 = two_texture_shader(p, struct.unpack_from('>I', em, 0x844)[0])
        if si2 is not None:
            struct.pack_into('>I', em, 0x844, si2)
            lay_t = eft_pixel.layout(bytes(p.shader_binary(si2)))
            notes.append('vertex program grafted: slot 1 UV animation')
    if is_mesh and rot == ROT_ANIMATED and not turns and GRAFT and not templates.no_graft:
        # a mesh's spin (or random starting turn) its template can't draw: its vertex program
        # grafted to turn the mesh (Zap's impact2 stripes, each turned at random about Z in
        # Ultimate, all lay one way on Pikachu's template)
        si_r = turning_shader(p, struct.unpack_from('>I', em, 0x844)[0])
        if si_r is not None:
            struct.pack_into('>I', em, 0x844, si_r)
            turns = True
            notes[:] = [n for n in notes if not n.startswith('rotation: template has none')]
            notes.append('vertex program grafted: rotation')
    two_tpl = lay_t is not None and 'uv1' in lay_t
    dis_in = None       # the colour track carrying the dissolve's threshold
    if dis is not None and lay_t is not None and not two_tpl:
        if lay_t['c1'] is not None and (p.field(em, 'color1_type') == 2 or not dis_moving):
            dis_in = 1
        elif c0_flat and (p.field(em, 'color0_type') == 2 or not dis_moving) and (
                lay_t['c1'] is not None or e['combiner']['color_process'] not in (2, 3)):
            dis_in = 0
    if dis is not None and dis_in is None:
        notes.append('dissolve not drawn (template: %s)' % (
            'not ours' if lay_t is None else 'two textures' if two_tpl else 'no animated colour track for it'))
        dis = None
    # a rotation no template draws: baked (a quad's fixed quarter turns; a mesh's starting rotation)
    baked_rot = rot != ROT_NONE and not turns and (is_mesh or rot == ROT_FIXED)
    quarter = fixed_quarter_turn(st) if baked_rot and not is_mesh else None
    mesh_rot = tuple(float(v) for v in st['rotate_init'][:3]) if baked_rot and is_mesh else None
    if mesh_rot and not any(abs(v) > 1e-6 for v in mesh_rot):
        mesh_rot = None
    # a flipbook program plays any mode (the CPU sets its flags from the mode word: tools/eft_vertex.py)
    flip = eft_vertex.features(bytes(p.shader_binary(struct.unpack_from('>I', em, 0x844)[0])))['flipbook'][0]
    ptn = ptn_want if ptn_want and flip else 0
    repeat = REPEAT.get(e['tex_anim'][ti]['repeat'], (1, 1)) if smp else (1, 1)
    bake = None
    if is_mesh:
        # eft's particle scale has two axes (vanilla 3D meshes, e.g. Zelda's smash arc, are built at
        # size with scale 1): an uneven 3D scale goes into the mesh (one primitive per mesh and
        # scale) and the emitter scales by 1 (x its scale animation); an even one stays the
        # particle's (the mesh shared)
        s3 = tuple(round(float(v), 4) for v in e['scale']['scale'])
        is_mesh = 'even' if max(s3) - min(s3) < 1e-3 else True
        if is_mesh == 'even':
            s3 = (1.0, 1.0, 1.0)
        # a template without all the UV animation needed: what it can't animate goes into the mesh's
        # UVs at its starting value (its change over life is lost), what it can keeps running (test
        # 30: Woosh's whirlwinds, wanting scroll and scale from a scroll-only template, stood still
        # with all of it baked)
        need = uv_mode(ts)
        bake = None
        have = eft_vertex.uv_caps(bytes(p.shader_binary(struct.unpack_from('>I', em, 0x844)[0])))[0]
        if have & need != need:
            keep = have & need
            bake = (repeat, tuple(ts['scale']) if not keep & 2 else (1.0, 1.0),
                    tuple(ts['scroll']) if not keep & 1 else (0.0, 0.0), ts['rotation'] if not keep & 4 else 0.0)
            repeat = (1, 1)
            if keep:
                ts = dict(ts)
                if not keep & 1:
                    ts.update(scroll=[0, 0], scroll_add=[0, 0], scroll_random=[0, 0])
                if not keep & 2:
                    ts.update(scale=[1, 1], scale_add=[0, 0], scale_random=[0, 0])
                if not keep & 4:
                    ts.update(rotation=0, rotation_add=0, rotation_random=0)
                notes.append('UV %s baked into the mesh at the start, %s kept' % (
                    '/'.join(n for b, n in ((1, 'scroll'), (2, 'scale'), (4, 'rotation')) if need & b and not keep & b),
                    '/'.join(n for b, n in ((1, 'scroll'), (2, 'scale'), (4, 'rotation')) if keep & b)))
            else:
                notes.append('UV transform baked into the mesh')
        channel = e['tex_anim'][ti]['uv_channel'] if smp else 0
        fres = fresnel_bake(e, notes)
        key = (pt['primitive_id'], s3, bake, channel, mesh_rot, rest_dir, fres)
        if key not in prim_index:
            pos, nrm, col_, uv, idx = mesh(prims[pt['primitive_id']], channel)
            if rest_dir:
                pos, nrm, col_, uv, idx = crossed_ribbon(pos, nrm, col_, uv, idx, notes)
            if bake:
                uv = np.concatenate([uv_transform(uv[:, :2] * np.array(bake[0], np.float32), *bake[1:]),
                                     uv[:, 2:]], 1)
            pos = pos * np.array(s3, np.float32)
            if mesh_rot:
                # as a turning template would (rotation_matrix), the particle's scale first
                r = rotation_matrix(mesh_rot).astype(np.float32)
                pos, nrm = pos @ r.T, nrm @ r.T
                notes.append('rotation baked into the mesh')
            if fres:
                # the scaled mesh's normals from its triangles (Kafrizz's sphere1 has none: the +Z
                # default baked nothing), facing the camera along Z
                nz = np.abs(face_normals(pos, idx)[:, 2])
                t = np.clip((nz - fres[0]) / (fres[1] - fres[0]), 0, 1)
                col_ = np.ones((len(pos), 4), np.float32) if col_ is None else np.array(col_, np.float32)
                col_[:, 3] *= t * t * (3 - 2 * t)
            # every attribute present: a template's vertex program may read normals / vertex colour
            # (an absent one is an empty buffer: Cemu's "GX2RSetAttributeBuffer(): Offset exceeds
            # buffer size", fix 25's F-smash rocks)
            if nrm is None:
                nrm = face_normals(pos, idx).astype(np.float32)
            if col_ is None:
                col_ = np.ones((len(pos), 4), np.float32)
            prim_index[key] = p.add_primitive(pos, nrm, col_, uv, idx)
        struct.pack_into('>i', em, 0x2DC, prim_index[key])
        if bake and not have & need:
            ts = None
    # the blend: Ultimate's on a template whose pixel program is ours (any blend's: Templates.get),
    # else the template's
    if lay_t is None:
        blend = {0: 'normal', 1: 'add', 2: 'sub'}[p.field(em, 'blend_type')]

    # ---- texture
    img = images.get(smp['texture_id']) if smp else None
    if img is None:
        img = np.full((16, 16, 4), 255, np.uint8)
        notes.append('no texture: white')
    elif not ptn:
        img = first_cell(img, e['static']['tex_scroll'][ti], shown_cell(e, ti))
    # the alpha track (x alpha 1 in alpha mode 4), for an own pixel program
    st_, col_ = e['static'], e['color']
    a_track = track(st_, col_, 0)[1] * e['info']['color0'][3]
    if e['combiner']['alpha_process'] == 4:
        a_track = a_track * track(st_, col_, 1)[1] * e['info']['color1'][3]
    if smp and ptn_want and not ptn:
        a_track = a_track * flipbook_fade(e, ti, images.get(smp['texture_id']), notes)
    if live is not None and not (two_tpl and bake is None and not quarter):
        # texture 1 reads slot 0's UVs before its transform: not once they're baked into the mesh;
        # nor a texture 0 turned in the image
        notes.append('sampler %d not drawn live (%s)' % (live, 'no two-texture template' if not two_tpl else
                                                          'UVs baked' if bake is not None else 'turn baked'))
        live = None
    if live2 is not None and live is None:
        live2 = None
    if live != 0:
        warp = None
    exact = exact_combiner(p, em, e, a_track, notes, tex_blend(e, ti, live) if live is not None else (0, 0),
                           dis[0] if dis is not None else None, dis_in == 0,
                           tex_blend(e, ti, live2) if live2 is not None else (0, 0), warp)
    if not exact:
        live = live2 = dis = warp = None
    if exact:
        pix = exact_texture(e, ti, img, ptn, images, names, notes, is_mesh, live, live2)
        rgb = track(st_, col_, 0)[0] * np.array(e['info']['color0'][:3])
        rgb1 = track(st_, col_, 1)[0] * np.array(e['info']['color1'][:3])
        alpha, premult = exact[1], None
        if dis is not None:
            # texture 0: grey colour in red and blue, the mask in green, alpha; colour 1's track the
            # threshold (Smash 4 scales colour 1 by the colour scale too, cross_f 0x04A588CC)
            m = resize(dis[2][..., None], pix.shape[1], pix.shape[0])
            pix = np.concatenate([pix[..., :1], m, pix[..., :1], pix[..., 3:]], -1)
            thr = np.repeat(dis[1][:, None] / float(e['static']['color_scale'] or 1.0), 3, 1)
            if dis_in == 0:
                rgb = thr
            else:
                rgb1 = thr
    else:
        if not is_mesh:
            baked = bake_samplers(e, ti, img, ptn, images, names, notes)
            if baked is not None:
                img, fill = baked, 1.0
        shape, rgb, alpha, premult, rgb1 = combine(img, e, notes, ti, fill,
                                                   (e.get('_set'), e['name']) in TWO_COLOUR)
        pix = shape[..., None].astype(np.float32)
    if not is_mesh:
        pix = np.stack([radial_gradient(pix[..., c], notes if c == pix.shape[-1] - 1 else [])
                        for c in range(pix.shape[-1])], -1)
    if uv_quarter:
        # eft2 samples at R(rotation) (uv - 0.5) + 0.5: the picture turns counter-clockwise as shown
        pix = np.ascontiguousarray(np.rot90(pix, uv_quarter))
        notes.append('UV rotation: %d quarter turn(s) baked into the texture' % uv_quarter)
    if quarter:
        # no template turns this quad: a fixed quarter turn goes into the texture (and the scale)
        pix = np.ascontiguousarray(np.rot90(pix, quarter))
        notes.append('rotation: %d quarter turn(s) baked into the texture' % quarter)
    # an odd number of baked quarter turns swaps the texture's U and V: their repeat and wraps too
    swap_uv = ((uv_quarter or 0) + (quarter or 0)) % 2 == 1
    if swap_uv:
        repeat = (repeat[1], repeat[0])
    # a whole flipbook sheet of 4+ cells a side gets twice the size, cells keeping 64 px
    grid = max(int(round(v)) for v in e['static']['tex_scroll'][ti]['uv_div']) if ptn else 1
    pix = fit_texture(pix, TEX_MAX * 2 if grid >= 4 else TEX_MAX)
    q8 = (np.clip(pix, 0, 1) * 255 + 0.5).astype(np.uint8)
    if two_tpl:
        # texture 1: the live sampler, else white (x 1)
        set_slot1(p, em, e, ti, None if templates.test_white1 else live, images, notes, raw=warp is not None)
        if lay_t is not None and 'uv2' in lay_t:
            set_slot1(p, em, e, ti, live2, images, notes, slot=2)
    if exact:
        struct.pack_into('>I', em, 0x844, exact[0])
        if dis is not None:
            # uncompressed: BC3's colour endpoints would tie the mask to the colour
            p.set_texture(em, 0, q8, 0x1A, comp_sel=RGBA_SEL)
        else:
            set_exact_texture(p, em, 0, pix)
    else:
        r8 = q8[..., 0]
        # the shape in every channel (selectors R R R R): most templates' pixel shaders take alpha
        # from red, some from alpha (Koopa's pointlight1 / Pikachu's spark1, picked for the hand /
        # throw auras and back throw's aura2), which with vanilla's R R R 1 drew the whole quad
        # (test 52's colour check: back throw's yellow square, the grab's purple one)
        # (not for a template that reads only the texture's alpha as a mask, alpha_mask_shader: with
        # the shape there forward smash's sword flare drew a dark band along the blade, test 53)
        mask_only = alpha_mask_shader(p, struct.unpack_from('>I', em, 0x844)[0])
        p.set_texture(em, 0, np.stack([r8, r8, r8, np.full_like(r8, 255)], 2), 0x34,
                      comp_sel=None if mask_only else SHAPE_SEL)
        if mask_only:
            notes.append('template reads the texture alpha as a mask: its channel selectors kept')
    if smp:
        set_wrap(em, 0, *((smp['wrap_v'], smp['wrap_u']) if swap_uv else (smp['wrap_u'], smp['wrap_v'])))
    p.set_field(em, 'tex0_uv_scale', [float(v) for v in repeat])
    set_uv_anim(em, ts)
    if ptn or not flip:
        set_flipbook(em, ptn, e['static']['tex_scroll'][ti] if smp else None, tp, repeat)
    else:
        # a flipbook program for no flipbook: one cell, played as any mode
        set_flipbook(em, 1, {'uv_div': [1, 1]}, {'num': 1, 'num_random': 1, 'table': [0] * 32, 'frequency': 1}, repeat)
        notes.append('flipbook template: one cell')

    # ---- blend, colour, alpha
    col = e['color']     # (st: the static block, its rotation masked above)
    p.set_field(em, 'blend_type', BLEND[blend])
    # pulled toward the camera (or pushed back) by eft2's offset, as eft's 0x4D0 does (the same units:
    # Bounce's barrier 10, drawn over Hero; the glow discs -2)
    p.set_field(em, 'camera_offset', float(e['static']['offset']))
    black1 = False
    if premult is not None:
        # the custom shader's colour x shape x 2: the shape is in every channel (SHAPE_SEL), so a
        # template whose colour mode (COLOR_MODE) takes the texture draws the x shape per pixel
        # (1: colour 0 x texture; 2: colour 1 + (colour 0 - colour 1) x texture, colour 1 black);
        # one that doesn't (0: colour 0) gets the shape's mean
        mode = struct.unpack_from('>I', em, COLOR_MODE)[0]
        rgb = rgb * 2 * (premult if mode == 0 else 1.0)
        black1 = mode == 2
        notes.append('template colour mode %d' % mode)
    if rgb1 is not None and not exact and struct.unpack_from('>I', em, COLOR_MODE)[0] != 2:
        rgb, rgb1 = (rgb + rgb1) / 2, None          # no lerp template: their mean
        notes.append('two colours: template not a lerp, their mean')
    if templates.test_mean_colour:
        p.set_field(em, 'color0_type', 0)
        p.set_field(em, 'color1_type', 0)
    fits = [(threshold_fit if dis is not None and dis_in == 0 else color_fit)(rgb),
            (threshold_fit if dis is not None and dis_in == 1 else color_fit)(rgb if rgb1 is None else rgb1)]
    for tr in (0, 1):
        cks, track_rgb = fits[tr][0], (rgb if rgb1 is None or tr == 0 else rgb1)
        if black1 and tr == 1:
            p.set_color_keys(em, tr, [(0.0, 0.0, 0.0, 1.0)] * (len(cks) if p.field(em, 'color1_type') == 2 else 1))
        elif p.field(em, 'color%d_type' % tr) == 2:
            p.set_color_keys(em, tr, [(*map(float, c), 1.0) for c in cks])
        else:
            p.set_color_keys(em, tr, [(*map(float, track_rgb.mean(0)), 1.0)])
    p.set_field(em, 'color_section1', [fits[0][1][0], fits[1][1][0]])
    p.set_field(em, 'color_section2', [fits[0][1][1], fits[1][1][1]])
    p.set_field(em, 'color_section3', [fits[0][1][2], fits[1][1][2]])
    p.set_field(em, 'color_repeat', [1, 1])
    # an own pixel program clamps the colour it draws to 1 (tools/eft_pixel.py): Ultimate's brightness
    # kept, what goes past 1 saturating as in Ultimate (F-smash's yellow spikes over grey bands, fix 25:
    # dull grey; Frizz's flames red); a template's own program gets it compressed (hdr_scale)
    p.set_field(em, 'color_scale', float(st['color_scale'] or 1.0) if exact else
                hdr_scale(p, em, float(st['color_scale'] or 1.0), notes))
    a0, a1, a2, s1, s2 = (float(np.squeeze(v)) for v in three_key(alpha))
    p.set_field(em, 'alpha_init', a0)
    p.set_field(em, 'alpha_diff21', a1 - a0)
    p.set_field(em, 'alpha_diff32', a2 - a1)
    p.set_field(em, 'alpha_section1', s1 / 100)
    p.set_field(em, 'alpha_section2', s2 / 100)

    # ---- scale
    sc = e['scale']
    curve = keys(st['scale_anim'], st['num_scale_keys'], 2)
    base = np.ones(2) if is_mesh is True else np.array([max(sc['scale'][0], 1e-4), max(sc['scale'][1], 1e-4)])
    peak = np.maximum(curve.max(0), 1e-4)
    v0, v1, v2, s1, s2 = three_key(curve / peak)
    xy = (lambda v: [v[1], v[0]]) if quarter in (1, 3) else (lambda v: list(v))
    p.set_field(em, 'scale', xy([float(b * m) for b, m in zip(base, peak)]))
    p.set_field(em, 'scale_init_ratio', xy([float(v) for v in v0]))
    p.set_field(em, 'scale_diff21', xy([float(v) for v in v1 - v0]))
    p.set_field(em, 'scale_diff32', xy([float(v) for v in v2 - v1]))
    p.set_field(em, 'scale_sections', [int(s1), int(s2)])
    p.set_field(em, 'scale_random', xy([min(1.0, sc['scale_random'][0] / 100), min(1.0, sc['scale_random'][1] / 100)]))

    # ---- rotation
    # (a template that doesn't turn: none, as vanilla's; what could be baked was)
    unturned = rest_dir or (rot != ROT_NONE and not turns)
    p.set_field(em, 'rotation_init', [0.0] * 3 if unturned else [float(v) for v in st['rotate_init'][:3]])
    p.set_field(em, 'rotation_random', [0.0] * 3 if unturned else [float(v) for v in st['rotate_init_rand'][:3]])
    p.set_field(em, 'rotation_velocity', [0.0] * 3 if unturned else [float(v) for v in st['rotate_add']])
    p.set_field(em, 'rotation_velocity_random', [0.0] * 3 if unturned else [float(v) for v in st['rotate_add_rand'][:3]])

    # ---- shape and motion
    sh, vel, ems = e['shape'], e['velocity'], e['emission']
    vt = sh['volume_type'] if sh['volume_type'] <= 14 else 0
    p.set_field(em, 'volume_type', vt)
    p.set_field(em, 'volume_radius', [float(r * f) for r, f in zip(sh['volume_radius'], sh['volume_form_scale'])])
    p.set_field(em, 'figure_velocity', float(vel['all_direction']))
    d = np.array(vel['designated_dir'], float)
    n = np.linalg.norm(d)
    p.set_field(em, 'emit_direction', [float(v) for v in (d / n if n else np.array([0.0, 1.0, 0.0]))])
    p.set_field(em, 'emitter_velocity', float(vel['designated_dir_scale']))
    p.set_field(em, 'dispersion_angle', float(vel['diffusion_dir_angle']))
    p.set_field(em, 'init_velocity_random', min(1.0, vel['vel_random'] / 100))
    p.set_field(em, 'gravity', [float(ems['gravity_scale'] * g) for g in ems['gravity_dir']])
    p.set_field(em, 'air_resistance', float(st['air_res']))
    info = e['info']
    p.set_emitter_srt(em, tuple(info['scale']), eft_rotation(info['rotate']), tuple(info['trans']))

    # ---- timing
    one = bool(ems['one_time'])
    if pt['infinite_life'] and not one:
        # a particle that lives until the effect ends (a held glow): emitted once (eft sizes the
        # buffer from life x rate / interval, unbounded for an endless emitter)
        one, ems = True, dict(ems, duration=1)
        notes.append('infinite life: emitted once')
    p.set_field(em, 'start_frame', int(ems['start']))
    p.set_field(em, 'end_frame', max(1, int(ems['duration'])) if one else FOREVER)
    p.set_field(em, 'one_time', 1 if one else 0)
    p.set_field(em, 'emit_start', 0)
    p.set_field(em, 'emit_interval', int(ems['interval']))
    p.set_field(em, 'emit_rate', float(max(ems['rate'], 0.01)))
    life = FOREVER if pt['infinite_life'] else max(1, int(pt['life']))
    p.set_field(em, 'ptcl_life', life)
    # turned off (Terminate_Graphic_Effect): eft2 fades the alpha over alpha_fade_time frames when
    # asked (and drops infinite-life particles); eft's FADE_ALPHA is that rate (1 / frames:
    # vanilla's infinite-life glows all have it), 0 lets the particles live out their life (test
    # 33's glow outlived the move; templates carrying 1 cut neutral air's burst at once); emission
    # stops as eft2's is_fade_emit says (always when nothing would end the emitter)
    info = e['info']
    fade = 1.0 / max(1, info['alpha_fade_time']) if info['is_fade_alpha_fade'] or life == FOREVER else 0.0
    if not one and not fade:
        # an endless emitter with no fade never ends once turned off (its instance stays, not
        # emitting); the rate ends it, its particles gone by then (forward air's speed lines)
        fade = 1.0 / max(1, info['alpha_fade_time'] or min(life, 10))
    struct.pack_into('>f', em, FADE_ALPHA, fade)
    em[FADE_EMIT] = 1 if info['is_fade_emit'] or not fade else 0
    p.set_field(em, 'ptcl_life_random', 0 if life == FOREVER else int(pt['life'] * pt['life_random'] / 100))
    if p.field(em, 'keyanim_size'):
        p.set_field(em, 'keyanim_size', 0)
    if child_e is not None:
        child = child_block(p, e, child_e, names, images, notes, templates, prims, prim_index)
        if len(e['children']) > 1:
            notes.append('%d more child emitters not converted (eft has one)' % (len(e['children']) - 1))
    anims, done = emitter_anims(p, em, e, notes) if not as_child else ([], set())
    left = set(e['subsections']) - done - fdone - ({'CSDP'} if dis is not None else set())   # (a dissolve's edge)
    if as_child:
        p.set_key_anims(em, [])
        return em
    if struct.unpack_from('>I', em, USER_CALLBACK)[0] == LIGHT_CALLBACK:
        em[USER_DATA:USER_CALLBACK + 4] = bytes(USER_CALLBACK + 4 - USER_DATA)
    if e['action_index'] == 1 and len(bytes.fromhex(e['subsections'].get('CADP', ''))) >= 20 and \
            not templates.test_no_light:
        cadp = bytes.fromhex(e['subsections']['CADP'])
        flags, r, g, b, radius = struct.unpack_from('<I4f', cadp)
        radius *= max(e['scale']['scale'][0], 1e-4) / base[0]
        # the colour given, not left to the particle's (0: x its colour scale, Ultimate's 2 on most
        # flares; vanilla lights stay within 1, 99% of 599: Kaboom's stacked lights were blinding),
        # x CADP's factor (the light's strength)
        if not (r or g or b):
            r, g, b = np.clip(track(e['static'], e['color'], 0)[0].mean(0) * np.array(e['info']['color0'][:3]), 0, 1)
        k = struct.unpack_from('<f', cadp, 20)[0] if len(cadp) >= 24 else 1.0
        r, g, b = (float(min(1.0, v) * max(0.0, min(1.0, k))) for v in (r, g, b))
        reach = radius * max(p.field(em, 'scale')[0], 1e-4)       # (the scale at its peak)
        if flags & LIGHT_SCALED:
            radius *= light_reach(reach) / reach
        struct.pack_into('>2I', em, USER_DATA, (flags & LIGHT_FLAGS) << 16, 0)
        struct.pack_into('>8f', em, USER_FLOATS, r, g, b, radius, 0, 0, 0, 0)
        struct.pack_into('>I', em, USER_CALLBACK, LIGHT_CALLBACK)
        left.discard('CADP')
        notes.append('light (flags 0x%X, radius %.3g, colour %.2f %.2f %.2f)' % (flags & LIGHT_FLAGS, radius, r, g, b))
    if left:
        notes.append('not converted: ' + ', '.join(sorted(left)))
    n = buffer_count(p, em)
    before = p.field(em, 'emit_rate')
    if n > 4 * MAX_LIVE:
        # fewer particles a burst (eft sizes the emitter's buffer from it; vanilla stays far below)
        p.set_field(em, 'emit_rate', max(1.0, before * 4 * MAX_LIVE / n))
        notes.append('buffer %d: rate lowered' % n)
    notes += sanitize(p, em)
    for a in anims:         # an animated rate lowered with the emitter's (its peak)
        if a['target'] == 0:
            a['keys'] = [(t, v * p.field(em, 'emit_rate') / before) for t, v in a['keys']]
    if fblocks or fluct or child:
        em = ptcl.Ptcl.with_fields(em, fblocks, fluct, *(child or (None, 0)))
    if fblocks:
        notes.append('fields: %s%s' % (', '.join(sorted(fblocks)), ' (animated %s)' % ', '.join(
            '0x%X' % a['target'] for a in fanims) if fanims else ''))
    if fluct:
        notes.append('fluctuation 0x%X' % fluct[0])
    p.set_key_anims(em, anims + fanims)
    return em


def emitter_anims(p, em, e, notes):
    """the emitter's animations (EMITTER_ANIMS) as eft key animations (Ptcl.set_key_anims' form) and the
    sections taken; the rate's and life's peaks become the emitter's own (eft sizes the particle buffer
    from them). Rotation in radians, eft's order; colour 0 / 1 and alpha over Ultimate's emitter colours
    (folded into the colour / alpha keys already); the rate x what conversion did to it"""
    struct.pack_into('>12f', em, EMITTER_DEFAULTS, *([1.0] * 12))
    out, done, info = [], set(), e['info']
    for sec, targets in EMITTER_ANIMS.items():
        raw = bytes.fromhex(e['subsections'].get(sec, ''))
        if len(raw) < 12:
            continue
        on, loop, _pad, nk, _z = struct.unpack_from('<BBHII', raw, 0)
        keys = [struct.unpack_from('<4f', raw, 12 + 16 * k) for k in range(nk)]
        if not on or not keys:
            continue
        vals = [list(k[:3]) for k in keys]
        if sec == 'EAER':
            vals = [list(eft_rotation([math.radians(v) for v in x])) for x in vals]
        elif sec in ('EAC0', 'EAC1'):
            c = info['color0' if sec == 'EAC0' else 'color1']
            vals = [[v / c[i] if c[i] else v for i, v in enumerate(x)] for x in vals]
        elif sec == 'EAA0':
            vals = [[x[0] / info['color0'][3] if info['color0'][3] else x[0]] for x in vals]
        elif sec == 'EATR':
            k = p.field(em, 'emit_rate') / max(e['emission']['rate'], 0.01)
            vals = [[x[0] * k] for x in vals]
            p.set_field(em, 'emit_rate', max(p.field(em, 'emit_rate'), max(x[0] for x in vals)))
        elif sec == 'EAPL':
            if p.field(em, 'ptcl_life') == FOREVER:
                continue
            p.set_field(em, 'ptcl_life', max(p.field(em, 'ptcl_life'), int(math.ceil(max(x[0] for x in vals)))))
        for i, t in enumerate(targets):
            out.append({'target': t, 'loop': loop, 'keys': [(float(k[3]), float(x[i])) for k, x in zip(keys, vals)]})
        done.add(sec)
    if done:
        notes.append('emitter animations: ' + ', '.join(sorted(done)))
    return out, done


def field_anim(raw, word, targets, scale=1.0, to_int=False):
    """an Ultimate field's 8-key animation (FIELD_SECTIONS' note) at this word as eft per-particle key
    animations of these targets (its x / y / z), x scale; [] when off"""
    on, loop, rnd, nk, period = struct.unpack_from('<5I', raw, 4 * word)
    if not on or not nk:
        return []
    keys = [struct.unpack_from('<4f', raw, 4 * (word + 5) + 16 * k) for k in range(min(nk, 8))]
    out = []
    for i, t in enumerate(targets):
        vals = [k[i] * scale for k in keys]
        if to_int:
            vals = [(int(round(v)) + 2 ** 31) % 2 ** 32 - 2 ** 31 for v in vals]
        out.append({'target': t, 'loop': loop, 'w4': period, 'w5': rnd,
                    'keys': [(k[3] * 100.0, v) for k, v in zip(keys, vals)]})
    return out


def particle_fields(e):
    """the emitter's Ultimate fields (FIELD_SECTIONS) as eft field blocks ({name: bytes}), their
    per-particle key animations and the sections taken"""
    subs = e['subsections']
    blocks, anims, done = {}, [], set()

    def raw(k, n):
        r = bytes.fromhex(subs.get(k, ''))
        if len(r) < n:
            return None
        done.add(k)
        return r
    r = raw('FSPN', 308)
    if r:
        # rate (radians a frame; its animation, when on, degrees a frame and in its place: main
        # 0x944B0), axis (0 - 2 both), outward speed (its animation x pi / 180, as Ultimate's code does)
        rate, axis, outward = struct.unpack_from('<fIf', r, 0)
        blocks['spin'] = struct.pack('>IIf', int(round(math.degrees(rate) * SPIN_UNITS)) % 2 ** 32, axis, outward)
        anims += field_anim(r, 3, (0x20,), SPIN_UNITS, True) + field_anim(r, 40, (0x21,), math.pi / 180)
    r = raw('FCLN', 36)
    if r:
        # the same numbers in another order (Bayonetta's butterflies and bats, in both games)
        v = struct.unpack_from('<8f', r, 4)
        blocks['curl_noise'] = struct.pack('>BB2x8f', r[0], r[1], v[6], *(v[3:6] + v[0:3] + v[7:8]))
    r = raw('FCOV', 168)
    if r:
        # type 1 converges on the emitter (eft: any non-zero word; vanilla 0x01000000), 0 on the position
        typ, x, y, z, ratio = struct.unpack_from('<I4f', r, 0)
        blocks['convergence'] = struct.pack('>I4f', 0x01000000 if typ else 0, x, y, z, ratio)
        anims += field_anim(r, 5, (0x22,))
    r = raw('FMAG', 168)
    if r:
        # bytes: follows the emitter, then x / y / z on (Mii Gunner's absorber, Mega Man's KO lines)
        power, x, y, z = struct.unpack_from('<4f', r, 4)
        blocks['magnet'] = struct.pack('>4fIB3x', power, x, y, z, (r[1] & 1) | (r[2] & 1) << 1 | (r[3] & 1) << 2, r[0])
        anims += field_anim(r, 5, (0x1F,))
    r = raw('FRN1', 164)
    if r:
        # eft's own random (eft2's "random fe1"): velocity += rand x it every interval frames
        vx, vy, vz, interval = struct.unpack_from('<3fI', r, 0)
        blocks['random'] = struct.pack('>i3f', interval, vx, vy, vz)
        anims += field_anim(r, 4, (0x1C, 0x1D, 0x1E))
    return blocks, anims, done


# a child emitter's block (ptcl.CHILD; docs/ptcl-format.md) from Ultimate's child: its drawing taken from the
# child converted as an emitter of its own (convert_emitter as_child: shader, texture, colours, alpha,
# scale, rotation, UV block; the child's fields where they mirror the emitter's, cross_f 0x04A5B308 /
# 0x04A5AA00 filling the same uniforms from them), its emission from Ultimate's child: count = rate, step =
# interval, start % of the parent's life (0x04A5EC6C), as Duck Hunt's final smash has them in both games
CHILD_FROM_EMITTER = [      # (child offset, emitter offset, size)
    (0x3C, 0x324, 4), (0x40, 0x4B8, 4), (0x44, 0x4BC, 4), (0x48, 0x328, 4), (0x4C, 0x40, 0x38), (0x124, 0x320, 4),
    (0x140, 0x778, 4),
    (0x154, 0x784, 0x14), (0x190, 0x7F8, 0xC), (0x19C, 0x804, 0xC), (0x1A8, 0x810, 0xC), (0x1B4, 0x81C, 0xC),
    (0x1C8, 0x4C4, 8), (0x1D0, 0x4A4, 0xC), (0x1E8, 0x4D4, 0x7C), (0x26C, 0x484, 4), (0x270, 0x830, 0x38),
    (0x2A8, 0x86C, 0x10), (0x2B8, 0x868, 4), (0x2F4, 0x8A8, 0x14)]
# Ultimate's inherit flags (by index) -> ptcl.INHERIT (Duck Hunt's final-smash children agree bit for bit)
CHILD_INHERIT = ['velocity', 'scale', 'rotation', None, 'color0', 'color1', 'alpha0', 'alpha1', 'draw_path', 'pre_draw']


def child_block(p, parent, c, names, images, notes, templates, prims, prim_index):
    """Ultimate child emitter c of parent as (eft child block, inherit bits), or None"""
    cnotes = []
    em = convert_emitter(p, c, names, images, cnotes, templates, prims, prim_index, as_child=True)
    if em is None:
        notes.append('child %s: %s' % (c['name'], '; '.join(cnotes)))
        return None
    key = struct.unpack_from('>II', em, 0x324)[0], p.field(em, 'particle_type')
    tpl = templates.children.get(key) or next(iter(templates.children.values()))
    b = bytearray(tpl)
    for co, eo, n in CHILD_FROM_EMITTER:
        b[co:co + n] = em[eo:eo + n]
    struct.pack_into('>i', b, 0x34, -1)
    for k, base in ((0, 0x650), (1, 0x6D0)):      # colours: the tracks' mean (a child's is constant)
        keys = np.array(struct.unpack_from('>32f', em, base)).reshape(8, 4)[:, :3]
        struct.pack_into('>3f', b, 0x128 + 0xC * k, *map(float, keys.mean(0)))
    struct.pack_into('>2I', b, 0x14C, 1, 0)         # alpha 0 as the emitter's sections, alpha 1 constant 1
    struct.pack_into('>2f', b, 0x168, 1.0, 0.0)
    sc, v0 = np.array(p.field(em, 'scale')), np.maximum(np.array(p.field(em, 'scale_init_ratio')), 0.01)
    end = v0 + np.array(p.field(em, 'scale_diff21')) + np.array(p.field(em, 'scale_diff32'))
    struct.pack_into('>3f', b, 0x180, *(sc * v0), float(p.field(em, 'scale_random')[0]))
    struct.pack_into('>i2f', b, 0x1DC, 0, *map(float, end / v0))       # from birth to its end scale
    rr = c['particle']['rot_rev_rand']
    b[0x1C4:0x1C7] = bytes(int(bool(v)) for v in rr)
    rot = any(p.field(em, 'rotation_velocity')) or any(p.field(em, 'rotation_velocity_random'))
    flags = struct.unpack_from('>I', b, 0x10)[0] & ~7
    flags |= (1 if abs(p.field(em, 'air_resistance') - 1) > 1e-6 else 0) | (2 if any(p.field(em, 'gravity')) else 0) \
        | (4 if rot else 0)
    struct.pack_into('>I', b, 0x10, flags)
    ems, vel, pt, inh = c['emission'], c['velocity'], c['particle'], c['inherit']
    rate, interval = float(ems['rate']), max(0, int(ems['interval']))
    if rate >= 1:
        count, step = int(round(rate)), interval
    else:
        # fewer than one a spawn: one every so many frames (eft: count is whole)
        count, step = 1, max(0, int(round((interval + 1) / max(rate, 0.01))) - 1)
    sh = c['shape']
    pos_rand = float(max(sh['volume_radius']) * max(sh['volume_form_scale'])) if sh['volume_type'] else 0.0
    struct.pack_into('>4i', b, 0, count, min(100, max(0, int(ems['start']))), int(pt['life']), step)
    struct.pack_into('>5f', b, 0x14, float(inh['velocity_rate']), float(vel['all_direction']), 0.0, 0.0, 0.0)
    struct.pack_into('>f', b, 0x28, pos_rand)
    struct.pack_into('>f', b, 0x38, float(pt['momentum_random']) / 100)
    struct.pack_into('>f', b, 0x17C, float(inh['scale_rate']))
    inherit = 0x40
    for i, name in enumerate(CHILD_INHERIT):
        if name and inh['flags'][i]:
            inherit |= ptcl.INHERIT[name]
    if abs(vel['designated_dir_scale']) > 1e-3:
        cnotes.append('directional velocity dropped')
    notes.append('child %s: %d every %d frames from %d%%, life %d; %s' % (
        c['name'], count, step + 1, ems['start'], pt['life'], '; '.join(cnotes)))
    return bytes(b), inherit


def threshold_fit(rgb):
    """color_fit's 3-key track (k0 until s1, -> k1 at s2, -> k2 at s3), least-squares on a 2% grid: for a
    dissolve's threshold, whose edge (0.05 wide) moves with it (color_fit's keys sampled on a 10% grid
    missed Swoosh's whirlwinds' by up to 0.08)"""
    f = np.asarray(rgb, float)
    t = np.arange(101.0)
    best = None
    grid = range(0, 101, 2)
    for s1 in grid:
        for s2 in range(s1, 101, 2):
            for s3 in range(s2, 101, 2):
                b1 = np.clip((t - s1) / (s2 - s1), 0, 1) if s2 > s1 else (t >= s1).astype(float)
                b2 = np.clip((t - s2) / (s3 - s2), 0, 1) if s3 > s2 else (t >= s2).astype(float)
                basis = np.stack([1 - b1, b1 - b2, b2], 1)
                k, res, _r, _s = np.linalg.lstsq(basis, f, rcond=None)
                err = float(((basis @ k - f) ** 2).sum())
                if best is None or err < best[0] - 1e-12:
                    best = (err, [k[0], k[1], k[2]], [s1, s2, s3])
    return best[1], best[2]


def fluctuation(e):
    """Ultimate's fluctuation (eft2's: emitter fluc flags, static amplitude / cycle / phase_rnd / phase_init,
    x then y) as eft's (ptcl.FLUCT_FMT: the same wave types (8 / 16 / 32) and 1 - wave x amplitude; Bayonetta's
    flares and bats agree in both games): (flags, block), or None when it changes nothing"""
    fl, st = e['fluc'], e['static']
    if not (fl['apply_alpha'] or fl['apply_scale']):
        return None
    flags = 1 | (2 if fl['apply_alpha'] else 0) | (4 if fl['apply_scale'] else 0) | (fl['wave_type'] & 0x38 or 8) \
        | (0x40 if fl['apply_scale'] and fl['apply_scale_y'] else 0)
    ch = []
    for a in range(2):
        cycle = max(st['cycle'][a], 1.0)
        # (the phase: degrees of the cycle, read off its values (360 on 12, the rest small); unverified)
        ch += [st['amplitude'][a], 128.0 / cycle, 1 if st['phase_rnd'][a] else 0, st['phase_init'][a] / 360.0 * cycle]
    return flags, struct.pack(ptcl.FLUCT_FMT, *ch)


def turn_set(p, si, rot_deg):
    """every emitter of set si turned by an effect's angles (degrees, R = Rz Ry Rx: Smash 4's effect
    turn, cross_f.rpx 0x03373478) on top of its own transform: the effect then needs no angles
    (tools/effect_variants.py)"""
    r = rotation_xyz([math.radians(v) for v in rot_deg])
    for e in p.sets[si]['emitters']:
        em = e['data']
        if em is None:
            continue
        own = rotation_xyz(p.field(em, 'emitter_rotation'))
        m = r @ own
        y = math.asin(max(-1.0, min(1.0, -m[2, 0])))
        if abs(m[2, 0]) < 1 - 1e-6:
            x, z = math.atan2(m[2, 1], m[2, 2]), math.atan2(m[1, 0], m[0, 0])
        else:
            x, z = math.atan2(-m[1, 2], m[1, 1]), 0.0
        t = r @ np.array(p.field(em, 'emitter_translation'), float)
        p.set_emitter_srt(em, tuple(p.field(em, 'emitter_scale')), (x, y, z), tuple(float(v) for v in t))
        anims = p.key_anims(em)
        if any(5 <= a['target'] <= 10 for a in anims):
            p.set_key_anims(em, turn_anims(anims, r, p.field(em, 'emitter_rotation'),
                                           p.field(em, 'emitter_translation'), r.T))


def key_value(keys, t):
    """a key animation's value at frame t (linear, held past either end)"""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0) if t1 > t0 else v1
    return keys[-1][1]


def euler_xyz(m):
    """rotation_xyz's angles of m"""
    y = math.asin(max(-1.0, min(1.0, -m[2, 0])))
    if abs(m[2, 0]) < 1 - 1e-6:
        return math.atan2(m[2, 1], m[2, 2]), y, math.atan2(m[1, 0], m[0, 0])
    return math.atan2(-m[1, 2], m[1, 1]), y, 0.0


def turn_anims(anims, r, rot, trans, r_inv):
    """an emitter's key animations with its translation (targets 8 - 10) and rotation (5 - 7) turned by r
    as turn_set turns its own: a translation key's vector by r, a rotation's angles composed with r
    (sampled at most 0.2 radians apart and unwrapped, so a looped 360 degree spin keeps its turns). rot /
    trans: the turned emitter's own (r_inv brings them back), for an axis without keys"""
    own_rot = euler_xyz(r_inv @ rotation_xyz(rot))
    own_trans = r_inv @ np.array(trans, float)
    out = [a for a in anims if not 5 <= a['target'] <= 10]
    for base, own in ((8, own_trans), (5, own_rot)):
        group = {a['target'] - base: a for a in anims if base <= a['target'] < base + 3}
        if not group:
            continue
        times = sorted({t for a in group.values() for t, _v in a['keys']})
        vec = [lambda t, i=i: key_value(group[i]['keys'], t) if i in group else own[i] for i in range(3)]
        if base == 5:
            dense = [times[0]]
            for t0, t1 in zip(times, times[1:]):
                step = max(abs(vec[i](t1) - vec[i](t0)) for i in range(3))
                n = max(1, int(math.ceil(step / 0.2)))
                dense += [t0 + (t1 - t0) * (k + 1) / n for k in range(n)]
            times = dense
        vals = []
        for t in times:
            v = np.array([vec[i](t) for i in range(3)], float)
            if base == 8:
                vals.append(r @ v)
                continue
            e = np.array(euler_xyz(r @ rotation_xyz(v)))
            if vals:                                   # unwrapped against the previous sample
                e += 2 * math.pi * np.round((vals[-1] - e) / (2 * math.pi))
            vals.append(e)
        loop = any(a['loop'] for a in group.values())
        out += [{'target': base + i, 'loop': loop, 'keys': [(t, float(v[i])) for t, v in zip(times, vals)]}
                for i in range(3)]
    return out


def rotation_xyz(rot):
    """R = Rz Ry Rx (radians): eft's emitter turn, X first"""
    a, b, c = (float(v) for v in rot)
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    return (np.array([[cc, -sc, 0], [sc, cc, 0], [0, 0, 1]]) @ np.array([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]])
            @ np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]]))


def set_name(prefix, ult):
    return prefix + ult[len('P_Edge'):] if ult.startswith('P_Edge') else prefix + ult.replace('P_', '')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('eff')
    ap.add_argument('base_dir')
    ap.add_argument('out_dir')
    ap.add_argument('kind', type=lambda v: int(v, 0))
    ap.add_argument('ids')
    ap.add_argument('effects', nargs='*')
    ap.add_argument('--prefix', default='PtcEdge')
    ap.add_argument('--templates', nargs='*', default=[],
                    help='vanilla .ptcl files to take template emitters from (the base\'s own first)')
    ap.add_argument('--variants', help='JSON [{"effect", "rot"}] (tools/effect_variants.py scan): a copy of '
                    'each effect\'s set turned by rot (degrees, R = Rz Ry Rx), id "effect@rx,ry,rz"')
    ap.add_argument('--empty', default='', help="comma-separated base bank entries (hex) to empty: effects "
                    "the base fighter's game code plays on its own that the new one hasn't (Robin's Thunder "
                    "orbs on Hero's Thunder-based articles)")
    ap.add_argument('--no-two', action='store_true', help='no two-texture templates: every emitter draws one texture')
    ap.add_argument('--no-dissolve', action='store_true', help="no dissolve (Ultimate's custom shader 8)")
    ap.add_argument('--keep-follow', action='store_true', help="keep each template's follow type (not Ultimate's)")
    ap.add_argument('--no-graft', action='store_true', help='no vertex program grafts (one-texture templates stay so)')
    ap.add_argument('--no-graft-for', default='', help='comma-separated EFFECT or EFFECT/EMITTER (Ultimate names): no '
                    'grafted templates for them (A / B tests)')
    ap.add_argument('--test-white1-for', default='', help='as --no-graft-for: texture 1 white (tests)')
    ap.add_argument('--test-mean-colour-for', default='', help='as --no-graft-for: colour tracks as their means (tests)')
    ap.add_argument('--test-skip-for', default='', help='as --no-graft-for: the emitters left out (tests)')
    ap.add_argument('--test-no-light-for', default='', help='as --no-graft-for: no effect light (tests)')
    ap.add_argument('--test-tint', default='', help='comma-separated EFFECT/EMITTER=RRGGBB: those emitters drawn in '
                    'that flat colour (tests: which part is which on screen)')
    ap.add_argument('--test-checker-for', default='', help='as --no-graft-for: texture 0 an 8 x 8 checkerboard '
                    '(tests: does the texture map in game)')
    ap.add_argument('--test-tint-texture', default='', help='comma-separated TEXTURE=RRGGBB: every mesh emitter '
                    'whose main texture that is, drawn in that flat colour (tests)')
    ap.add_argument('--test-alpha-for', default='', help='comma-separated EFFECT/EMITTER=FACTOR: those emitters\' '
                    'alpha x FACTOR (tests)')
    ap.add_argument('--test-texture-for', default='', help='comma-separated EFFECT/EMITTER=core|solid: texture 0 '
                    'white, its alpha 1 where V < 0.3 (core) or everywhere (solid); or its own texture as a '
                    'private copy (private) or as RGBA8 (rgba) (tests)')
    ap.add_argument('--test-glow-alpha', type=float, default=1.0, help="Ultimate's glow parts (draw path 21, a "
                    "grade / flare texture) at this x their alpha (tests)")
    ap.add_argument('--extra-eff', nargs='+', action='append', default=[], metavar=('EFF', 'NAME=SET'),
                    help="effects from another Ultimate file, named as the game plays them: e.g. ef_common.eff "
                         "sys_special_attack_up=p_cmnspecialattackup (Hero's Oomph glow, played by his game code)")
    ap.add_argument('--no-exact', action='store_true', help='no pixel programs of our own (tools/eft_pixel.py): '
                    'each emitter folded into one shape on its template\'s program, as before')
    a = ap.parse_args()
    global EXACT, TWO_TEXTURES, DISSOLVE, WRITE_FOLLOW, GRAFT
    EXACT = not a.no_exact
    TWO_TEXTURES = not a.no_two
    DISSOLVE = not a.no_dissolve
    WRITE_FOLLOW = not a.keep_follow
    GRAFT = not a.no_graft
    eff = vfxb.Eff(a.eff)
    names, _ = eff.textures()
    images = eff.images()
    base = [f for f in os.listdir(a.base_dir) if f.endswith('.010d0000.ptcl')][0][:-len('.ptcl')]
    p = ptcl.Ptcl(open(os.path.join(a.base_dir, base + '.ptcl'), 'rb').read())
    base_shaders = p.shader_count()
    ef = efc.Efc(open(os.path.join(a.base_dir, base + '.efc'), 'rb').read())
    for i in (int(v, 16) for v in a.empty.split(',') if v):
        ef.entries[i][1:] = [0, 0, 0, 0]    # no emitter set, model or meshes (403 vanilla entries)
    templates = Templates(p, a.templates)
    no_graft = set(v for v in a.no_graft_for.split(',') if v)
    white1 = set(v for v in a.test_white1_for.split(',') if v)
    mean_colour = set(v for v in a.test_mean_colour_for.split(',') if v)
    skip = set(v for v in a.test_skip_for.split(',') if v)
    no_light = set(v for v in a.test_no_light_for.split(',') if v)
    checker = set(v for v in a.test_checker_for.split(',') if v)
    tex_for = dict(x.split('=') for x in a.test_texture_for.split(',') if x)
    alpha_for = {k: float(v) for k, v in (x.split('=') for x in a.test_alpha_for.split(',') if x)}
    tint_tex = {k: tuple(int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))
                for k, v in (x.split('=') for x in a.test_tint_texture.split(',') if x)}
    tint = {k: tuple(int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))
            for k, v in (x.split('=') for x in a.test_tint.split(',') if x)}
    sources = [(eff, names, images, [(n, eff.effects[n]) for n in (a.effects or sorted(eff.effects))])]
    for path, *wanted in a.extra_eff:
        x = vfxb.Eff(path)
        sources.append((x, x.textures()[0], x.images(),
                        [(n, x.effects[sname.lower()]) for n, sname in (w.split('=') for w in wanted)]))
    ids, done, dropped = {}, {}, []

    def convert_source(src, eff, names, images, wanted):
        prims, prim_index = eff.primitives(), {}
        for name, si_ult in wanted:
            if (src, si_ult) in done:
                ids[name] = done[src, si_ult]
                continue
            made, log = [], []
            for e in eff.emitters(si_ult):
                notes = []
                e['_set'] = eff.sets[si_ult]
                templates.no_graft = name in no_graft or '%s/%s' % (name, e['name']) in no_graft
                templates.test_white1 = name in white1 or '%s/%s' % (name, e['name']) in white1
                templates.test_mean_colour = name in mean_colour or '%s/%s' % (name, e['name']) in mean_colour
                templates.test_no_light = name in no_light or '%s/%s' % (name, e['name']) in no_light
                if name in skip or '%s/%s' % (name, e['name']) in skip:
                    log.append('    %-24s left out (--test-skip-for)' % e['name'])
                    continue
                if '%s/%s' % (name, e['name']) in alpha_for:
                    f = alpha_for['%s/%s' % (name, e['name'])]
                    e['info'] = dict(e['info'], color0=list(e['info']['color0'][:3]) + [e['info']['color0'][3] * f])
                    notes.append('alpha x %g (--test-alpha-for)' % f)
                tex0 = names.get(e['sampler'][0]['texture_id'], '')
                if a.test_glow_alpha != 1.0 and e['info']['draw_path'] == 21 and \
                        re.match(r'ef_cmn_(grade|flare)', tex0):
                    e['info'] = dict(e['info'], color0=list(e['info']['color0'][:3]) +
                                     [e['info']['color0'][3] * a.test_glow_alpha])
                    notes.append('glow (draw path 21): alpha x %g (--test-glow-alpha)' % a.test_glow_alpha)
                em = convert_emitter(p, e, names, images, notes, templates, prims, prim_index)
                key = '%s/%s' % (name, e['name'])
                if e['particle']['primitive_id'] != NONE64 and names.get(e['sampler'][0]['texture_id']) in tint_tex:
                    tint[key] = tint_tex[names.get(e['sampler'][0]['texture_id'])]
                if em is not None and tex_for.get(key) in ('private', 'rgba'):
                    cur = np.asarray(p.decode_texture(em, 0)).astype(np.uint8).copy()
                    if tex_for[key] == 'private':
                        cur[-1, -1, 3] ^= 1                 # the same image, its own copy
                        q = cur.astype(np.float32) / 255
                        set_exact_texture(p, em, 0, q)
                    else:
                        p.set_texture(em, 0, cur, 0x1A, comp_sel=0x00010203)
                    notes.append('texture 0 %s (--test-texture-for)' % tex_for[key])
                elif em is not None and key in tex_for:
                    al = np.ones((64, 64), np.float32)
                    if tex_for[key] == 'core':
                        al[int(64 * 0.3):] = 0
                    set_exact_texture(p, em, 0, np.stack([np.ones_like(al)] * 3 + [al], -1))
                    notes.append('texture 0 %s (--test-texture-for)' % tex_for[key])
                if em is not None and key in checker:
                    c = ((np.indices((64, 64)) // 8).sum(0) % 2).astype(np.float32)
                    set_exact_texture(p, em, 0, np.stack([c, c, c, c], -1))
                    notes.append('texture 0 a checkerboard (--test-checker-for)')
                if em is not None and key in tint:
                    for tr in (0, 1):
                        p.set_field(em, 'color%d_type' % tr, 0)
                        p.set_color_keys(em, tr, [tint[key] + (1.0,)])
                    notes.append('tinted %02X%02X%02X (--test-tint)' % tuple(int(v * 255) for v in tint[key]))
                if em is not None:
                    made.append((em, e['name']))
                log.append('    %-24s %s' % (e['name'], '; '.join(dict.fromkeys(notes))))
            if not made:
                print('%-30s %s: nothing convertible' % (name, eff.sets[si_ult]))
                print('\n'.join(log))
                dropped.append(name)
                continue
            if len(made) > MAX_EMITTERS:
                log.append('    %d emitters: the first %d kept' % (len(made), MAX_EMITTERS))
                made = made[:MAX_EMITTERS]
            sname = set_name(a.prefix, eff.sets[si_ult])
            si = p.new_set(sname, [m[0] for m in made], [m[1] for m in made])
            ids[name] = done[src, si_ult] = (0x300 + a.kind) << 16 | ef.add(si + 1)
            print('%-30s %-28s -> %-28s 0x%07X  %d emitters' % (name, eff.sets[si_ult], sname, ids[name], len(made)))
            print('\n'.join(log))
    convert_source(0, *sources[0])
    if a.variants:
        import effect_variants
        for v in json.load(open(a.variants)):
            if v['effect'] not in ids:
                continue
            entry = ef.entries[ids[v['effect']] & 0xFFFF]          # [flags, set (1-based), ...]
            sname = p.name_at(p.sets[entry[1] - 1]['name_pos']) + 'R%d' % len(ids)
            si = p.clone_set(entry[1] - 1, sname)
            turn_set(p, si, v['rot'])
            key = effect_variants.variant_key(v['effect'], v['rot'])
            ids[key] = (0x300 + a.kind) << 16 | ef.add(si + 1, flags=entry[0])
            print('%-44s -> %-28s 0x%07X' % (key, sname, ids[key]))
    # the other files' effects after the variants: every id the base file's effects had stays
    for src, source in enumerate(sources[1:], 1):
        convert_source(src, *source)
    # the imported templates whose pixel program was replaced leave their shader unused
    unused = p.drop_unused_shaders(base_shaders)
    out = p.build()
    q = ptcl.Ptcl(out)
    assert q.validate() == [], q.validate()
    print('%d unused shaders dropped; bank %.2f MB' % (unused, len(out) / 1e6))
    os.makedirs(a.out_dir, exist_ok=True)
    open(os.path.join(a.out_dir, base + '.ptcl'), 'wb').write(out)
    open(os.path.join(a.out_dir, base + '.efc'), 'wb').write(ef.build())
    old = json.load(open(a.ids)) if os.path.exists(a.ids) else {}
    old.update({k: '0x%07X' % v for k, v in ids.items()})
    for k in dropped:       # an id from an earlier run would now name another effect's set
        old.pop(k, None)
    json.dump(old, open(a.ids, 'w'), indent=1)
    print('%d effects -> %d sets; %s' % (len(ids), len(set(done.values())), a.ids))


if __name__ == '__main__':
    main()
