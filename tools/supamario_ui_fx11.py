#!/usr/bin/env python3
"""Supamario's Ultra Instinct v11: fixes to the converted XV2 effects in his bank (called by supamario_ui_build.effects,
after every set is in; fighters/supamario/README.md "Ultra Instinct v11").

1. streak_basis: the streaks' place (the user: "the Secret Sensation aura appears far below Supamario, similarly to Time
   Skip / Jump Spike's aura"). xv2_to_ptcl clones a vanilla type-3 (directional) template whose rotBasis (0x4C4, CB2
   vec4 36 .xy: every vertex program draws its quad at S x (corner + rotBasis)) is (0, -1.34): the quad lies 0.84 to
   1.84 of its length BEHIND its particle (a spark whose head leads). Run on the game's own programs (latte_exec): KTN's
   wind_1 (length 10.6) drew 10.7-21.4 under its particle, Time Skip's stripe 5.2-11.9. XV2 draws an
   AutoOriented_VisibleOnSpeed sprite centred on its particle (rotBasis 0) and a ConeExtrude ribbon behind its head
   (the path it took: rotBasis -0.5, the quad from the particle back by its length).
2. aura_flipbook: the aura's flicker (the user: "the aura seems stiff and doesn't animate"). XV2's aura sprites are
   SpriteSheet textures played in order (Aura_LoopFOK's 8 x 2 cells every 3 / 4 frames, its edge sprites 4 x 4 every
   6): xv2_to_ptcl keeps the first cell only, so every sprite showed one still flame. In v9 the GPU sprites stayed where
   they were born (the trail the user saw) and their spread over his moves hid it; v10's following variants hold them on
   him, still. Now each GPU aura sprite on a sprite sheet gets the whole sheet as its texture and plays it (mode 2, loop:
   XV2's Sequential; its frames a cell), on its program's flipbook variant (the same key with byte 10 | 0x08 and the same
   pixel program: vanilla Donkey Kong's 39 for the follow variant of 39, Ganondorf's 36 for 62's; `--flip-ptcl`). Its
   UV animation block neutral (scale 1): the flipbook programs draw slot 0's scroll / scale / turn too.
3. aura_spread: XV2's VerticalDistribution emitters scatter each sprite by their Position_Variance (Aura_LoopFOK 0.3 m):
   lost in the conversion (every sprite on its bone's point). A circle volume of that radius (8.5 units a metre, the
   sprites' own scale).
4. piace: the sparkles (the user: "too small and positioned at Supamario's feet rather than covering his body and
   moving up"). XV2's Aura_FOKpiace emits from a 0.3 m circle 0.5 m under the pelvis with a Position_Variance of 1 m
   (up and down: the whole body) rising 0.3 m/s; the conversion kept the -0.5 m (x the call's 1.75: 7 units under his
   hip, at his feet) and lost the variance. Now: on joint 0 (TransN: his up is the world's, the MSC's request at his
   hip's height), an upright disc (the emitter turned X -90: a circle fill in his XY plane, PIACE_R) round his middle,
   rising along his up (PIACE_RISE a frame), PIACE_SIZE times bigger.
"""
import math
import os
import struct
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)

ROT_BASIS = 0x4C4
BASIS_CENTRED, BASIS_CONE = 0.0, -0.5
TS_DIM = 0.85
STREAK_PREFIXES = ('PtcSupamarioTs', 'PtcSupamarioUi', 'PtcSupamarioSf')
# the sets fixed: the auras the user reported (Time Skip's CrgAura / CrgAuraH, Secret Sensation's KTN_GKS_Loop / its
# BoostGKS_End) and Ultra Instinct's / Soaring Fist's own; the earlier moves' hit sparks (Btl_HitL's lines, Frt_Hit's
# waves: the same template offset) are left as the user approved them
STREAK_SETS = ('PtcSupamarioTsFrt_CrgAura', 'PtcSupamarioTsFrt_CrgAuraH', 'PtcSupamarioUi', 'PtcSupamarioSf')
GPU_FLAG = 0x00800000
UNIT = 8.5
PIACE_R = 2.9                         # the disc's radius (x the call's 1.75: 5 units: his body round his middle)
PIACE_RISE = 0.12                     # units a frame up (x 1.75: ~6 units over the sparkles' 30 frames)
PIACE_SIZE = 3.5                      # x the converted size (0.098: 0.17 units at the call's 1.75)
PIACE_Y = 5.0                         # the MSC's request: TransN, this high (his hip's height in Wait)


def pkg_dir(src, keep_eepk=None):
    """a temporary package folder: src's files (only keep_eepk's .eepk when given)"""
    d = tempfile.mkdtemp()
    for fn in os.listdir(src):
        if fn.lower().endswith('.eepk') and keep_eepk and fn != keep_eepk:
            continue
        os.symlink(os.path.abspath(os.path.join(src, fn)), os.path.join(d, fn))
    return d


def node_types(pkg):
    """{(emp stem, node name): NodeSpecificType} of a loaded package's Emission nodes"""
    import xv2vfx
    out = {}
    for emp_name, emp in pkg['emp'].items():
        stem = emp_name[:-4]
        for _d, n in xv2vfx.emp_nodes(emp):
            if n['NodeType'] == 'Emission':
                out.setdefault((stem, n['Name']), n['NodeSpecificType'])
    return out


def _stem(set_name, prefix):
    s = set_name[len(prefix):]
    return s[:-2] if s.endswith('_2') else s


def streak_basis(p, pkgs, rep):
    """1: every type-3 emitter of the XV2 sets (STREAK_PREFIXES): rotBasis by its node (centred / a cone's head)"""
    types = {}
    for pk in pkgs:
        types.update(node_types(pk))
    done = []
    for si in range(len(p.sets)):
        name = p.set_name(si)
        prefix = next((x for x in STREAK_PREFIXES if name.startswith(x)), None)
        if prefix is None or not any(name == x or (x.endswith(('Ui', 'Sf')) and name.startswith(x))
                                     for x in STREAK_SETS):
            continue
        stem = _stem(name, prefix)
        for e in p.sets[si]['emitters']:
            em = e['data']
            if em is None or p.field(em, 'particle_type') != 3:
                continue
            en = p.emitter_name(em)
            t = types.get((stem, en))
            if t is None and prefix == 'PtcSupamarioTs':
                t = 'ConeExtrude'              # Time Skip's CrgAura copies (per bone, renamed): its ConeExtrude ribbons
            if t is None:
                continue
            b = BASIS_CONE if t == 'ConeExtrude' else BASIS_CENTRED
            old = struct.unpack_from('>2f', em, ROT_BASIS)
            struct.pack_into('>2f', em, ROT_BASIS, 0.0, b)
            if name.startswith('PtcSupamarioTsFrt_CrgAura'):
                # on him now, Time Skip's streaks overlap more: their colours x TS_DIM keep the user's white-area
                # rule (supamario_fx_glow ts_e0 on grass: at most 1.0 square unit; v10 0.7, undimmed v11 1.1)
                for track in (0, 1):
                    keys = p.color_keys(em, track)
                    p.set_color_keys(em, track, [tuple(c * TS_DIM for c in k[:3]) + tuple(k[3:]) for k in keys])
            done.append((name, en, t, round(old[1], 3), b))
    rep['v11_streak_basis'] = done
    return done


def is_gpu(em):
    return bool(struct.unpack_from('>I', em, 4)[0] & GPU_FLAG)


def flip_variant(p, sh, others):
    """the flipbook variant of shader sh (key byte 10 | 0x08, every other key byte and the pixel program the same), in p
    or imported from others: its index (None: none)"""
    import eft_pixel
    want = bytearray(p.shader_entry(sh))
    want[10] |= 0x08
    pix = eft_pixel.disassemble(p.shader_binary(sh))
    for q in [p] + list(others):
        for i in range(q.shader_count()):
            if bytes(q.shader_entry(i)[:0x68]) == bytes(want[:0x68]) and eft_pixel.disassemble(q.shader_binary(i)) == pix:
                return i if q is p else p.import_shader(q, i)
    return None


def sheet_of(sampler):
    """(cells across, down, [cell indices in play order], frames a cell) of an XV2 SpriteSheet sampler, or None"""
    ss = sampler.get('ScrollState') or {}
    ks = ss.get('Keyframes') or []
    if ss.get('ScrollType') != 'SpriteSheet' or len(ks) < 2:
        return None
    su, sv = abs(ks[0]['ScaleU']), abs(ks[0]['ScaleV'])
    if not su or not sv:
        return None
    nx, ny = int(round(1.0 / su)), int(round(1.0 / sv))
    cells = [int(round((k['ScrollV'] % 1.0) / sv)) * nx + int(round((k['ScrollU'] % 1.0) / su)) for k in ks]
    return nx, ny, cells, max(1, int(ks[0]['Time']))


def aura_flipbook(p, aura_pkg, set_names, others, rep, tex_max=256):
    """2: the GPU aura sprites on sprite sheets play them"""
    import vfxb_to_ptcl as VP
    import xv2_to_ptcl as XP
    import xv2vfx
    import eft_vertex
    images = XP.emb_images(aura_pkg)
    nodes = {}
    for emp_name, emp in aura_pkg['emp'].items():
        for _d, n in xv2vfx.emp_nodes(emp):
            if n['NodeType'] == 'Emission':
                nodes.setdefault((emp_name[:-4], n['Name']), (n, emp))
    done = []
    for name in set_names:
        si = p.find_set(name)
        stem = _stem(name, 'PtcSupamarioUi')
        for e in p.sets[si]['emitters']:
            em = e['data']
            if em is None or not is_gpu(em):
                continue
            en = p.emitter_name(em)
            ne = nodes.get((stem, en))
            if ne is None:
                continue
            node, emp = ne
            refs = [r for r in node['EmissionNode']['Texture']['TextureEntryRef'] if r is not None and r >= 0]
            if not refs:
                continue
            smp = emp['Textures'][refs[0]]
            sh = sheet_of(smp)
            img = images.get(smp.get('TextureRef'))
            if sh is None or img is None:
                continue
            prog = p.field(em, 'shader_index')
            if any(eft_vertex.features(p.shader_binary(prog))['flipbook']):
                continue
            fv = flip_variant(p, prog, others)
            if fv is None:
                done.append((name, en, 'no flipbook variant'))
                continue
            nx, ny, cells, per = sh
            shape, _tint = XP.shape_texture(img)
            h, w = shape.shape
            tw, th = XP.pow2(w, hi=tex_max), XP.pow2(h, hi=tex_max)
            if (tw, th) != (w, h):
                shape = XP.resize(shape[..., None].astype(np.float32), tw, th)[..., 0]
            r8 = (np.clip(shape, 0, 1) * 255 + 0.5).astype(np.uint8)
            p.set_texture(em, 0, np.stack([r8, r8, r8, np.full_like(r8, 255)], 2), 0x34)
            p.set_field(em, 'shader_index', fv)
            seq = cells == list(range(len(cells)))
            VP.set_flipbook(em, 2, {'uv_div': [nx, ny]},
                            {'num': 0 if seq else len(cells), 'num_random': 1, 'table': cells + [0] * (32 - len(cells)),
                             'frequency': per})
            if seq:
                struct.pack_into('>h', em, 0x506, len(cells))
            VP.set_uv_anim(em, None)
            VP.set_inv_rand(em, 0, (smp.get('SymmetryU') == 'Random', smp.get('SymmetryV') == 'Random'))
            done.append((name, en, (nx, ny, len(cells), per, prog, fv, tw, th)))
    rep['v11_flipbook'] = done
    return done


def aura_spread(p, aura_pkg, set_names, rep):
    """3: XV2's Position_Variance of a VerticalDistribution parent as a circle volume"""
    parent = {}
    for emp_name, emp in aura_pkg['emp'].items():
        def walk(ns, up):
            for n in ns:
                if n['NodeType'] == 'Emission' and up is not None:
                    parent.setdefault((emp_name[:-4], n['Name']), up)
                nxt = n if n['NodeType'] == 'Emitter' else up
                walk(n.get('ChildParticleNodes') or [], nxt)
        walk(emp['ParticleNodes'], None)
    done = []
    for name in set_names:
        si = p.find_set(name)
        stem = _stem(name, 'PtcSupamarioUi')
        for e in p.sets[si]['emitters']:
            em = e['data']
            if em is None:
                continue
            up = parent.get((stem, p.emitter_name(em)))
            if up is None or up['NodeSpecificType'] != 'VerticalDistribution':
                continue
            var = float(up['EmitterNode'].get('Position_Variance', 0.0))
            if var <= 0 or p.field(em, 'volume_type') != 0:
                continue
            r = round(var * UNIT, 3)
            p.set_field(em, 'volume_type', 3)
            p.set_field(em, 'volume_radius', [r, 0.0, r])
            done.append((name, p.emitter_name(em), r))
    rep['v11_spread'] = done
    return done


def piace(p, rep, name='PtcSupamarioUiAura_FOKpiace'):
    """4: the sparkles over his body, rising, bigger"""
    done = []
    for e in p.sets[p.find_set(name)]['emitters']:
        em = e['data']
        if em is None:
            continue
        p.set_emitter_srt(em, (1, 1, 1), (-math.pi / 2, 0.0, 0.0), (0.0, 0.0, 0.0))
        p.set_field(em, 'emit_direction', [0.0, 0.0, 1.0])
        p.set_field(em, 'volume_type', 3)
        p.set_field(em, 'volume_radius', [PIACE_R, 0.0, PIACE_R])
        p.set_field(em, 'emitter_velocity', PIACE_RISE)
        p.set_field(em, 'figure_velocity', 0.0)
        p.set_field(em, 'dispersion_angle', 10.0)
        p.set_field(em, 'scale', [float(v) * PIACE_SIZE for v in p.field(em, 'scale')])
        done.append((p.emitter_name(em), [round(v, 3) for v in p.field(em, 'scale')]))
    rep['v11_piace'] = done
    return done
