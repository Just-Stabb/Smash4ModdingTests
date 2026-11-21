#!/usr/bin/env python3
"""Supamario's Ultra Instinct v12: effect changes in his bank (called by supamario_ui_build.effects after every earlier
set and v11's fixes; fighters/supamario/README.md "Ultra Instinct v12"), and the attack arcs' colour while transformed
(supamario_ui_build.scripts).

1. sf_3d: Soaring Fist's shot (the user: "Soaring Fist appears flat instead of like a 3-dimensional shockwave"). XV2's
   Hkn_Wav (1510_GKS_HKN.eepk effect 5, PositionUpdate + RotateUpdate) is ShapeDraw rings: the wind crescents spawn
   turned at random about all three axes (wind_1 / wind_1_1 / wind: RotationVariance 360, 360, 360) round the shot, and
   10 of its 16 emissions are screen refraction (materials Ref / Ref_Custom: ScreenRefractAdjust): the shockwave in
   the user's XV2 clips is the background bent by rings round the shot, seen from behind. v11 drew every ring with one
   orientation (the converter keeps the node's Rotation, not its variance: rings round the travel axis, edge-on from
   Smash 4's side camera: lines) and the refraction rings as flat additive colour, on plain GPU programs (their particles
   left where they were born). Now: the wind crescents get XV2's random turn on all three axes (eft's rotation random,
   ptcl 0x804, drawn by their program 29, which reads v_inRot); the refraction emissions are the fireball's refraction
   program (v9's aura_refraction way: its bytes, XV2's emission fields) at XV2's sizes: a distortion bubble round the
   shot; every GPU emitter on its program's follow variant, follow 0 (on the shot every frame, XV2's PositionUpdate).
2. ss_charge: Secret Sensation's ki charge (the user: "the aura is weak and too small"; XV2's charge clip: a white-violet
   flame column from his feet to about twice his height): KTN_GKS_Loop's alpha x SS_CHARGE_GAIN (the effect script
   calls it bigger and higher: supamario_ui_build FX 'ss_charge').
3. ts_aura: Time Skip / Jump Spike's aura (the user: "too small, weak, doesn't follow Supamario when charging and placed
   too low"; the screenshot: the purple streaks left behind and below him as he drifts): XV2's effect 0 world parts
   (Frt_CrgAura on the pelvis and the right foot, CrgAuraB on the pelvis) as one set his MSC now requests FOLLOWING on
   TransN (v4-v11: world-placed at his ground point, turned to his facing, none following): the set's emitters moved
   from its world space (+X his forward) to TransN's (+Z forward: turned -90 about Y), TS_AURA_UP higher; CPU streaks
   follow 2, GPU ones their follow variant (v10's aura_follow way); their alpha x TS_AURA_GAIN; the call's size
   TS_AURA_SIZE (v11 1.75).
4. smash_hed_blue: the up / down smash's arc (his own PtcMarioSmashHed, 0x0341000B: orange colour keys) copied blue
   (red and blue swapped, lifted ARC_LIFT toward white: a light-blue edge round its white core), played instead while
   transformed (blue_arcs).
5. blue_arcs (effect scripts): the common attack arcs (0x0100008D / 8E / 90 / 92: greyscale emitters coloured by the
   fighter's table, Mario's (2, 0.8, 0.35) / (3, 0.7, 0.2) / (3, 0.7, 0.25): orange-brown, docs/native-notes.md
   "Fighter colours for the common attack effects") get LAST_EFFECT_SET_COLOR (ARC_RGB, light blue: the core still
   saturates white) right after the request while transformed (Float_Var_Compare(TIMER_0 > 1500) True { ... }); the
   smash's own arc swapped for its blue copy the same way.
"""
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)

GPU_FLAG = 0x00800000
# ---------------------------------------------------------------- 1. Soaring Fist
SF_SET = 'PtcSupamarioSfHkn_Wav'
SF_TUMBLE = ('wind_1', 'wind_1_1', 'wind')          # XV2 RotationVariance (360, 360, 360)
SF_WIND_GAIN = 2.0                                   # their alpha x this: the white crescents carry the shot's look
SF_REF_MATS = ('Ref', 'Ref_Custom')
SF_REF_STRENGTH = 2.0                                # the bend: XV2's transparency x 2 (v10's aura haze: x 2 to read in game)
SF_REF_KEEP = ('wave_ref_ring', 'wave_ref', 'ref_ring', 'core_1_1', 'core_3_1')   # the refraction parts kept as
# refraction: XV2's rings / the shot's lasting cores (the 5-frame cores and the small ring stay colour-less: removed,
# their alpha 0 (an emitter set keeps its layout))
# ---------------------------------------------------------------- 2. Secret Sensation
SS_SETS = ('PtcSupamarioUiKTN_GKS_Loop', 'PtcSupamarioUiKTN_GKS_Loop_2')
SS_CHARGE_GAIN = 1.8
# ---------------------------------------------------------------- 3. Time Skip
TS_SET = 'PtcSupamarioTsFrt_CrgAura'
TS_AURA_GAIN = 1.4
TS_AURA_SIZE = 2.6                    # the call's size (v4-v11: 1.75, XV2's x1.0)
TS_AURA_UP = 5.0                      # units (at the call's size) the set's parts are raised
# ---------------------------------------------------------------- 4 / 5. the arcs
ARC_IDS = {0x0100008D: (0.8, 1.5, 3.0), 0x01000092: (0.8, 1.5, 3.0),     # Mario's 2-red ones
           0x0100008E: (1.2, 2.25, 4.5), 0x01000090: (1.2, 2.25, 4.5)}    # his 3-red ones, as bright
HED_ID = 0x0341000B                   # PtcMarioSmashHed (his up / down smash arc)
HED_SET = 'PtcMarioSmashHed'
HED_BLUE = 'PtcSupamarioUiSmashHedBlue'
ARC_LIFT = 0.25
FX_IDS = {}


def _set(p, name):
    si = p.find_set(name)
    assert si is not None and si >= 0, name
    return si


def _emitters(p, si):
    return [e for e in p.sets[si]['emitters'] if e['data'] is not None]


def _twins():
    import ptcl
    import supamario_ui_build as B
    out = []
    for path in B.TWIN_PTCL + B.FLIP_PTCL:
        q = ptcl.Ptcl(open(path, 'rb').read())
        q.path = path
        out.append(q)
    return out


def _follow(p, em, twins):
    """the emitter's particles on it every frame: CPU follow 2, GPU follow 0 on its program's follow variant (v10)"""
    import supamario_ui_build as B
    if struct.unpack_from('>I', em, 4)[0] & GPU_FLAG:
        p.set_field(em, 'shader_index', B.follow_variant(p, p.field(em, 'shader_index'), twins))
        struct.pack_into('>I', em, 0x310, 0)
        return 'gpu'
    struct.pack_into('>I', em, 0x310, 2)
    return 'cpu'


def _gain(p, em, k):
    for fld in ('alpha_init', 'alpha_diff21', 'alpha_diff32'):
        p.set_field(em, fld, p.field(em, fld) * k)


def sf_materials(skill_dir):
    """{emission name: its material's name} of Hkn_Wav (XV2's EMM)"""
    import xv2vfx
    import supamario_ui_fx11 as FX11
    pkg = xv2vfx.load_package(FX11.pkg_dir(skill_dir), strict=False)
    try:
        emp = pkg['emp']['Hkn_Wav.emp']
        out = {}
        for _d, n in xv2vfx.emp_nodes(emp):
            if n['NodeType'] == 'Emission':
                m = xv2vfx.resolve_material(pkg, 'PBIND', n['EmissionNode']['Texture']['MaterialID'])
                out.setdefault(n['Name'], (m or {}).get('Name'))
        return out
    finally:
        import shutil
        shutil.rmtree(pkg['dir'], ignore_errors=True)


def sf_3d(p, skill_dir, rep):
    """1 (module doc)"""
    import supamario_ui_build as B
    mats = sf_materials(skill_dir)
    twins = _twins()
    si = _set(p, SF_SET)
    src = p.find_set(B.HAZE_SRC[0])
    base = [e['data'] for e in p.sets[src]['emitters'] if e['data'] is not None and
            p.emitter_name(e['data']) == B.HAZE_SRC[1]][0]
    done = {'tumble': [], 'refraction': [], 'quiet': [], 'follow': {}}
    for e in _emitters(p, si):
        em = e['data']
        name = p.emitter_name(em)
        if name in SF_TUMBLE:
            p.set_field(em, 'rotation_random', [math.pi, math.pi, math.pi])
            _gain(p, em, SF_WIND_GAIN)
            done['tumble'].append(name)
        elif mats.get(name) in SF_REF_MATS:
            if name in SF_REF_KEEP:
                new = bytearray(base)
                struct.pack_into('>I', new, 0x38, struct.unpack_from('>I', em, 0x38)[0])     # its own name
                for fld in B.REF_COPY:
                    p.set_field(new, fld, p.field(em, fld))
                _gain(p, new, SF_REF_STRENGTH)
                e['data'] = em = new
                p.dirty_layout = True
                done['refraction'].append(name)
            else:
                _gain(p, em, 0.0)
                done['quiet'].append(name)
        if name in done['refraction']:
            # v13 (the user: "the on-hit distortion swirls"; XV2's picture: blocky distortion where the shot passed):
            # the refraction rings left where they are made (the plain refraction program, follow 1: v12 had them
            # follow the shot, so nothing stayed behind)
            struct.pack_into('>I', e['data'], 0x310, 1)
            done['follow'][name] = 'left behind'
            continue
        done['follow'][name] = _follow(p, e['data'], twins)
    rep['v12_sf_3d'] = done
    return done


def ss_charge(p, rep):
    """2 (module doc)"""
    n = 0
    for name in SS_SETS:
        for e in _emitters(p, _set(p, name)):
            _gain(p, e['data'], SS_CHARGE_GAIN)
            n += 1
    rep['v12_ss_charge'] = {'gain': SS_CHARGE_GAIN, 'emitters': n}
    return n


def ts_aura(p, rep):
    """3 (module doc)"""
    import xv2_to_ptcl as XP
    import numpy as np
    twins = _twins()
    si = _set(p, TS_SET)
    turn = XP.euler_matrix([0.0, -90.0, 0.0])
    done = []
    for e in _emitters(p, si):
        em = e['data']
        t = np.array(p.field(em, 'emitter_translation'), float)
        r = XP.euler_matrix(list(np.degrees(p.field(em, 'emitter_rotation'))))
        t2 = turn @ t
        t2[1] += TS_AURA_UP
        rot = XP.matrix_euler(turn @ r)
        p.set_emitter_srt(em, tuple(p.field(em, 'emitter_scale')), tuple(rot), [float(v) for v in t2])
        _gain(p, em, TS_AURA_GAIN)
        done.append((p.emitter_name(em), _follow(p, em, twins), [round(float(v), 3) for v in t2]))
    rep['v12_ts_aura'] = {'gain': TS_AURA_GAIN, 'up': TS_AURA_UP, 'emitters': done}
    return done


def f32(vals):
    """the values as the script file stores them (float32)"""
    return [struct.unpack('>f', struct.pack('>f', v))[0] for v in vals]


# v13 (the user, v12: "The hitbox trails are all black now"): LAST_EFFECT_SET_COLOR's handler (0x02BE44B0) DIVIDES its
# three floats by 255 (fdivs at 0x02BE4534-44 by the float at 0x100FC3E4, 255.0) before the set colour call (EffectModule vt
# +0x27C): v12 passed the set colour itself (0.8, 1.5, 3.0), i.e. 0.003-0.012: black. The command takes 0-255 (more to
# brighten); the fighter table's colours (the 2 / 0.8 / 0.35 kind) are the set colour already
COLOR_DIV = 255.0


def arc_cmd_rgb(rgb):
    """the command's Red / Green / Blue for a set colour (what the handler divides back)"""
    return f32([v * COLOR_DIV for v in rgb])


def set_colour_of_cmd(params):
    """the set colour the handler makes of the command's parameters (the game's: / 255)"""
    return [v / COLOR_DIV for v in params]


def _blue(rgb):
    r, g, b = rgb[:3]
    r, g, b = b, g, r
    return tuple(c + (1.0 - c) * ARC_LIFT if c < 1.0 else c for c in (r, g, b))


def smash_hed_blue(p, e, rep):
    """4 (module doc): the copy's efc id"""
    src = _set(p, HED_SET)
    si = p.clone_set(src, HED_BLUE)
    for x in _emitters(p, si):
        em = x['data']
        for track in (0, 1):
            keys = [tuple(k) for k in p.color_keys(em, track)]
            p.set_color_keys(em, track, [_blue(k[:3]) + tuple(k[3:]) for k in keys])
    idx = e.add(si + 1)
    FX_IDS['hed_blue'] = 0x03410000 | idx
    rep['v12_hed_blue'] = {'set': si, 'id': '0x%08X' % FX_IDS['hed_blue']}
    return FX_IDS['hed_blue']


# ---------------------------------------------------------------- v13: Soaring Fist's trail and swirls
TRAIL_SET = 'PtcSupamarioSfTrail'
SWIRL_SET = 'PtcSupamarioSfSwirl'
TRAIL_SRC = ('PtcMarioFireball', 'PtcMarioFireballSmoke_Copy2')   # vanilla's own trail (the fireball's grey smoke: CPU,
# one a frame, left where it is made)
# XV2's Hkn_Wind.etr (1510_GKS_HKN.eepk effect 5's TBIND part: the shot's trace, Orientation None): three ribbons from
# the shot, at (0, +0.2, 0) / (0, -0.2, 0) / (0, 0, -0.5) m, held 13 / 15 / 17 frames, width 0.5 -> 0.1 m, colour 1
# white -> (0.4, 0.5, 0.5), transparency 0.4 -> 0.25 -> 0 (TranceNML: normal blend)
TRAIL_NODES = ((0.0, 0.2, 0.0, 13), (0.0, -0.2, 0.0, 15), (0.0, 0.0, -0.5, 17))
TRAIL_METRE = 5.04
TRAIL_WIDTH = 0.5 * 5.04 * 2.0         # the wisp's size (units): XV2's ribbon half-width 0.5 m, doubled (a billboard
                                       # puff spans the ribbon's width)
TRAIL_ALPHA = 0.4
TRAIL_RGB0, TRAIL_RGB1 = (1.0, 1.0, 1.0), (0.4, 0.5, 0.5)
SWIRL_FROM = ('PtcSupamarioSfHkn_Fir', ('wave_ref', 'wave_ring_ref'))   # XV2's punch burst's refraction rings
SWIRL_SIZE = 1.6


def _refraction_of(p, em, base):
    """the fireball's refraction program with this emitter's emission fields (v9's aura_refraction way)"""
    import supamario_ui_build as B
    new = bytearray(base)
    struct.pack_into('>I', new, 0x38, struct.unpack_from('>I', em, 0x38)[0])
    for fld in B.REF_COPY:
        p.set_field(new, fld, p.field(em, fld))
    _gain(p, new, SF_REF_STRENGTH)
    return new


def sf_trail(p, e, rep):
    """v13 (the user: "please add the trail to Soaring Fist"): XV2's Hkn_Wind trace as three wisps a frame (the
    fireball's own smoke trail emitter, recoloured / sized as the trace's three nodes), left where they are made as the
    shot flies on: a set the projectile's effect script plays with the wave (following its bone 0)"""
    src = _set(p, TRAIL_SRC[0])
    base = [x['data'] for x in p.sets[src]['emitters'] if x['data'] is not None and
            p.emitter_name(x['data']) == TRAIL_SRC[1]][0]
    import supamario_sf_build as SF
    size = SF.WAV_SIZE * SF.V13_WAV
    ems, names = [], []
    for k, (x, y, z, life) in enumerate(TRAIL_NODES):
        em = bytearray(base)
        p.set_field(em, 'ptcl_life', life)
        p.set_field(em, 'scale', [TRAIL_WIDTH / size] * 2)
        t = [x * TRAIL_METRE / size, y * TRAIL_METRE / size, z * TRAIL_METRE / size]
        p.set_emitter_srt(em, tuple(p.field(em, 'emitter_scale')), tuple(p.field(em, 'emitter_rotation')), t)
        for track, rgb in ((0, TRAIL_RGB0), (1, TRAIL_RGB1)):
            keys = [tuple(k_) for k_ in p.color_keys(em, track)]
            p.set_color_keys(em, track, [tuple(rgb) + tuple(k_[3:]) for k_ in keys])
        for fld in ('alpha_init', 'alpha_diff21', 'alpha_diff32'):
            p.set_field(em, fld, p.field(em, fld) * TRAIL_ALPHA)
        struct.pack_into('>I', em, 0x310, 1)                      # left behind: the trail
        ems.append(bytes(em))
        names.append('HknWind%d' % k)
    si = p.new_set(TRAIL_SET, ems, names)
    FX_IDS['trail'] = SF.FX_IDS['trail'] = 0x03410000 | e.add(si + 1)
    rep['v13_trail'] = {'set': si, 'id': '0x%08X' % FX_IDS['trail'], 'nodes': TRAIL_NODES}
    return FX_IDS['trail']


def sf_swirl(p, e, rep):
    """v13 (the user: "the on-hit distortion swirls"): XV2's punch burst's refraction rings (Hkn_Fir wave_ref /
    wave_ring_ref: one-time bursts, v11-v12 drawn as flat colour) as the fireball's refraction program, x SWIRL_SIZE,
    in a set of their own the MSC plays where a punch reaches a fighter; Hkn_Fir's own rings refract too"""
    import supamario_ui_build as B
    src = p.find_set(B.HAZE_SRC[0])
    base = [x['data'] for x in p.sets[src]['emitters'] if x['data'] is not None and
            p.emitter_name(x['data']) == B.HAZE_SRC[1]][0]
    fir = _set(p, SWIRL_FROM[0])
    ems, names = [], []
    for x in p.sets[fir]['emitters']:
        em = x['data']
        if em is None or p.emitter_name(em) not in SWIRL_FROM[1]:
            continue
        new = _refraction_of(p, em, base)
        struct.pack_into('>I', new, 0x310, 1)
        x['data'] = bytearray(new)
        p.dirty_layout = True
        sw = bytearray(new)
        p.set_field(sw, 'scale', [v * SWIRL_SIZE for v in p.field(sw, 'scale')])
        ems.append(bytes(sw))
        names.append(p.emitter_name(em) + 'Swirl')
    si = p.new_set(SWIRL_SET, ems, names)
    import supamario_sf_build as SF
    FX_IDS['swirl'] = SF.FX_IDS['swirl'] = 0x03410000 | e.add(si + 1)
    rep['v13_swirl'] = {'set': si, 'id': '0x%08X' % FX_IDS['swirl'], 'emitters': names}
    return FX_IDS['swirl']


def effects(p, e, sf_skill, rep):
    """every v12 change to the bank (supamario_ui_build.effects, after v11's); v13's trail and swirls after them"""
    sf_3d(p, sf_skill, rep)
    ss_charge(p, rep)
    ts_aura(p, rep)
    smash_hed_blue(p, e, rep)
    sf_trail(p, e, rep)
    sf_swirl(p, e, rep)


# ---------------------------------------------------------------- 5. the scripts
def _transformed(body):
    import supamario_ui_build as B
    import supamario_ui_cave as cave
    return B.if_var(cave.V_FORM, 5, B.UI_TRANSFORMED_OVER, body)


def arc_blocks():
    """[the blocks blue_arcs adds] (supamario_ui_build.strip_glow_restore takes them out for the earlier suites)"""
    import supamario_ui_build as B
    out = [_transformed([B.cmd('last_effect_set_color', *arc_cmd_rgb(rgb))]) for rgb in sorted(set(ARC_IDS.values()))]
    return out


def _hed_swap(c):
    """the smash arc's request again on its blue copy (the same parameters), the orange one ended at once"""
    import acmd
    import supamario_ui_build as B
    blue = acmd.Command(c.ident, [FX_IDS.get('hed_blue', 0) if (isinstance(v, int) and v == HED_ID) else v
                                  for v in c.params])
    return _transformed([B.cmd('terminate_graphic_effect', HED_ID, 1, 1), blue])


def _hed_end(c):
    import supamario_ui_build as B
    return _transformed([B.cmd('terminate_graphic_effect', FX_IDS.get('hed_blue', 0), *c.params[1:])])


def blue_arcs(f, own):
    """5 (module doc): every effect script not in `own`; [(script hash, what)]"""
    import acmd
    term = acmd.BY_NAME['terminate_graphic_effect']
    done = []
    for h in sorted(f.scripts):
        if h in own:
            continue
        body, out, hit = f.scripts[h], [], []
        for c in body:
            out.append(c)
            p0 = c.params[0] if c.params and isinstance(c.params[0], int) else None
            if c.ident == term:
                if p0 == HED_ID:
                    out += _hed_end(c)
                    hit.append('hed_end')
                continue
            if p0 in ARC_IDS and 'EFFECT' in c.name.upper():
                out += _transformed([acmd.Command(acmd.BY_NAME['last_effect_set_color'], arc_cmd_rgb(ARC_IDS[p0]))])
                hit.append('0x%08X' % p0)
            elif p0 == HED_ID and 'EFFECT' in c.name.upper():
                out += _hed_swap(c)
                hit.append('hed')
        if hit:
            f.scripts[h] = out
            done.append((h, hit))
    return done


def strip_blocks(cmds):
    """the commands without blue_arcs' blocks"""
    out, i = [], 0
    fvc = None
    import acmd
    import supamario_ui_cave as cave
    fvc = acmd.BY_NAME['float_var_compare']
    true = acmd.BY_NAME['true']
    colour = acmd.BY_NAME['last_effect_set_color']
    term = acmd.BY_NAME['terminate_graphic_effect']
    while i < len(cmds):
        c = cmds[i]
        if (c.ident == fvc and c.params[0] == cave.V_FORM and i + 1 < len(cmds) and cmds[i + 1].ident == true):
            n = (cmds[i + 1].params[0] - 2)
            j, size = i + 2, 0
            inner = []
            while j < len(cmds) and size < n:
                inner.append(cmds[j])
                size += acmd.INFO[cmds[j].ident]['size']
                j += 1
            if inner and (all(x.ident == colour for x in inner) or
                          (inner[0].ident == term and all('EFFECT' in x.name.upper() for x in inner))):
                i = j
                continue
        out.append(c)
        i += 1
    return out
