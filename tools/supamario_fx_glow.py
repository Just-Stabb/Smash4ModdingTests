#!/usr/bin/env python3
"""How much of a move's converted effects would bloom (Sledgehammer v3, the user's "extremely bright" glow): fx_render's
Smash 4 side (the converted emitters through their own programs) on a black background, per frame: the brightest
channel drawn, the area (square units) drawn over 1.0 (Smash 4 blooms colours past 1: fighters/brave/README.md) and
over 0.5, and the energy (the summed colour, per square unit). Supamario's moves as their scripts call them: the
Sledgehammer's charge, uncharged and charged swing and hit (calls built from tools/supamario_sledgehammer_build.py),
the Super God Fist (attackdash) and Core Breaker's charge (specialhi before its frame 55) from effect.bin.

  python3 -I tools/supamario_fx_glow.py BUILD_OUT_DIR [MOVE ...] [--png DIR] [--bg R,G,B] [--only NAMES]

BUILD_OUT_DIR: tools/supamario_sledgehammer_build.py's OUT_DIR (ts_hit: tools/supamario_timeskip_build.py's). MOVE:
sh_charging, sh_uncharged, sh_charged, sh_hit, ts_hit (Time Skip's punch; ts_hit_v1 with v1's shared Btl_HitLOD),
ts_e11 / ts_e0 (Time Skip v4: XV2's skill effects 11, the punch, and 0, the start), ts_outline (v6: the outline's rings), attackdash, cb_charge (default all). --png DIR: each move's six brightest frames side by side. Bones other than top
are drawn at top (the fist's effects placed 8 up, 3 ahead); his body isn't drawn.
--bg (v4): the background colour (default black): the effects are added onto it as in game (a bright stage pushes an
additive effect past 1 sooner: the user's screenshot 26 on a grass stage); the areas then count only the pixels the
effects push past the level (the background alone is under it), and 'white' the pixels they turn white (every channel
0.9 or more). --only: comma-separated parts of emitter names (fx_render's --only).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import json  # noqa: E402
import numpy as np  # noqa: E402
import efc  # noqa: E402
import fx_render as R  # noqa: E402
import ptcl  # noqa: E402
import supamario_sledgehammer_build as B  # noqa: E402

HAND = (0.0, 8.0, 3.0)


def moves(out_dir):
    eb = os.path.join(out_dir, 'fighter/supamario/script/animcmd/body/effect.bin')
    fx, sc = B.FX_IDS, B.SH_FX_SCALE
    fy = json.load(open(os.path.join(out_dir, 'sledgehammer_fx.json')))['fire_y']
    out = {}
    for ch in (False, True):
        sw = B.START_LAST + (B.CHARGE_FRAMES if ch else 0)
        off = sw + (B.FX_AT['crg_off_ch'] if ch else B.FX_AT['crg_off'])
        c = [(B.FX_AT['crg_on'], fx['crg'], 0, HAND, (0, 0, 0), B.EEPK_SCALE['Hmr_Crg.emp'] * sc, off)]
        if ch:
            c += [(sw + B.FX_AT['fire'], fx['fire_l'], 0, (0.0, fy, 0.0), (0, 0, 0), B.EEPK_SCALE['Hmr_Fire_L.emp'] * sc,
                   None),
                  (sw + B.FX_AT['fire'], fx['crg02'], 0, HAND, (0, 0, 0), B.EEPK_SCALE['Hmr_Crg02.emp'] * sc, None)]
            out['sh_charging'] = (c, list(range(B.FX_AT['crg_on'], sw + 1)))
        else:
            c += [(sw + B.FX_AT['fire'], fx['fire'], 0, (0.0, fy, 0.0), (0, 0, 0), B.EEPK_SCALE['Hmr_Fire.emp'] * sc,
                   None)]
        out['sh_charged' if ch else 'sh_uncharged'] = (c, list(range(sw, sw + 24)))
    out['sh_hit'] = ([(0, fx['hitlod'], 0, (0.0, 5.0, 0.0), (0, 0, 0), B.EEPK_SCALE['Btl_HitLOD.emp'] * sc, None),
                      (0, fx['hits'], 0, (0.0, 5.0, 0.0), (0, 0, 0), B.EEPK_SCALE['Btl_HitS.emp'] * sc, None)],
                     list(range(0, 20)))
    import supamario_timeskip_build as TB     # Time Skip's punch: XV2's hit look (BTL_CMN effect 2) from the MSC
    # (v2: its own Btl_HitLOD copy, TB.FX_LOD_ID; ts_hit_v1: v1's call of Sledgehammer's set, for the comparison)
    ts = [(0, TB.FX_LOD_ID, 0, (0.0, 5.0, 0.0), (0, 0, 0), TB.EEPK_SCALE['Btl_HitLOD.emp'] * TB.FX_SCALE, None)]
    ts += [(0, TB.FX_IDS[k], 0, (0.0, 5.0, 0.0), (0, 0, 0), TB.EEPK_SCALE['Btl_HitL.emp'] * TB.FX_SCALE, None)
           for k in ('hitl', 'hitl_2')]
    out['ts_hit'] = (ts, list(range(0, 24)))
    out['ts_hit_v1'] = ([(0, TB.SH_FX['hitlod']) + ts[0][2:]] + ts[1:], list(range(0, 24)))
    # v4: Time Skip's XV2 skill effects (1350_HIK_FRT.eepk), as the MSC places them facing right (world-placed: the
    # world's X is fx_render's top-frame Z, the screen's horizontal: the call turned -90 about Y): effect 11 at his fist
    # at the punch (its four sets), effect 0's world parts at his ground point, its elbow part (followed: drawn at the
    # elbow's height at frame 0, about 6 up)
    e11 = [(0, i, 0, (0.0, TB.E11_AT[1], -TB.E11_AT[0]), (0, -90, 0), TB.E11_SIZE, None) for i in TB.FX_E11_IDS.values()]
    out['ts_e11'] = (e11, list(range(0, 140)))
    out['ts_e0'] = ([(0, TB.FX_AURA_ID, 0, (0.0, 0.0, 0.0), (0, -90, 0), TB.AURA_SIZE, None),
                     (0, TB.FX_E0H_ID, 0, (0.0, 6.0, 0.0), (0, 0, 0), TB.E0_FOLLOW[2] * TB.AURA_SIZE, None)],
                    list(range(0, 80)))
    # v6: the outline's rings on his bones at his T pose (c00's rest: (x, y)), whole (fx_render draws no body: the
    # worst case, his body hides their insides in game)
    tpose = {64: (0.0, 13.18), 22: (0.0, 10.24), 12: (0.0, 7.85), 11: (0.0, 6.57), 14: (1.88, 8.71), 18: (-1.88, 8.72),
             15: (3.63, 8.71), 19: (-3.63, 8.72), 16: (5.35, 8.71), 20: (-5.36, 8.72), 3: (1.23, 5.5), 7: (-1.23, 5.5),
             4: (1.25, 3.4), 8: (-1.25, 3.4), 5: (1.27, 1.56), 9: (-1.27, 1.56)}
    out['ts_outline'] = ([(0, TB.FX_OUTLINE_ID, 0, (0.0, tpose[b][1], -tpose[b][0]), (0, 0, 0), TB.outline_size(r), None)
                          for b, r in TB.OUTLINE_BONES], list(range(0, 6)))
    c = [x for x in R.s4_calls(eb, 'attackdash') if (x[1] >> 16) == 0x341]
    out['attackdash'] = (c, list(range(min(x[0] for x in c), min(x[0] for x in c) + 90)))
    c = [x for x in R.s4_calls(eb, 'specialhi') if (x[1] >> 16) == 0x341 and x[0] < 55]
    out['cb_charge'] = (c, list(range(31, 58)))
    return out


def measure(out_dir, which=(), png=None, bg=(0.0, 0.0, 0.0), only=''):
    R.BG = np.array(bg, float)
    R.ONLY = only
    # v4 (Time Skip v4's test): each call from fresh vertex programs: a cached latte_exec program kept state from the
    # previous call's emitters (the grey pass's ts_hit drew 3.6 after the grass pass's new sets, 9.6 alone)
    R._s4_programs.clear()
    R._s4_static.clear()
    edir = os.path.join(out_dir, 'fighter/supamario/effect/supamario')
    p = ptcl.Ptcl(open(os.path.join(edir, 'supamario.010d0000.ptcl'), 'rb').read())
    ef = efc.Efc(open(os.path.join(edir, 'supamario.010d0000.efc'), 'rb').read())
    programs, cache, res = {}, {}, {}

    def ems(gid):
        if gid not in cache:
            i = gid & 0xFFFF
            ok = (gid >> 16) == 0x341 and i < len(ef.entries) and ef.entries[i][1]
            cache[gid] = R.s4_emitters(p, ef.entries[i][1] - 1, programs) if ok else None
        return cache[gid]
    for mv, (calls, frames) in moves(out_dir).items():
        if which and mv not in which:
            continue
        frames = sorted(set(frames))
        canv = {fr: R.Canvas(-30, 30, -20, 40, 6.0) for fr in frames}
        for fr0, gid, _bone, xyz, rot, size, off in calls:
            e = ems(gid)
            if e is None:
                continue
            cm = R.call_matrix(xyz, rot, size)
            for k, em in enumerate(e):
                if only and not any(o in em.name for o in only.split(',')):
                    continue
                sim = R.simulate(em, (fr0, cm, size, off), frames, seed=k + 1)
                for fr in frames:
                    if sim[fr]:
                        m = cm @ R.emitter_matrix(em, fr - fr0)
                        if em.s4 is not None and R.draw_s4(canv[fr], em, sim[fr], m, float(fr - fr0)):
                            continue
                        R.draw(canv[fr], em, sim[fr], cm)
        rows = []
        base = R.Canvas(-30, 30, -20, 40, 6.0).rgb
        for fr in frames:
            rgb = canv[fr].rgb
            mx = rgb.max(axis=2)
            add = rgb - base
            white = (np.clip(rgb, 0, 1).min(axis=2) >= 0.9) & (np.clip(base, 0, 1).min(axis=2) < 0.9)
            rows.append((fr, round(float(mx.max()), 2), round(float((mx > 1.0).sum()) / 36.0, 1),
                         round(float((add.max(axis=2) > 0.5).sum()) / 36.0, 1), round(float(add.sum()) / 36.0, 1),
                         round(float(white.sum()) / 36.0, 1)))
        res[mv] = {'brightest': max(rows, key=lambda r: r[4]), 'max_over_1': max(r[2] for r in rows),
                   'max_white': max(r[5] for r in rows), 'frames': rows}
        if png:
            from PIL import Image
            top = sorted(sorted(rows, key=lambda r: -r[4])[:6])
            ims = [Image.fromarray(canv[r[0]].image()) for r in top]
            sheet = Image.new('RGB', (ims[0].size[0] * len(ims), ims[0].size[1]))
            for i, im in enumerate(ims):
                sheet.paste(im, (i * im.size[0], 0))
            os.makedirs(png, exist_ok=True)
            sheet.save(os.path.join(png, 'glow_%s.png' % mv))
    return res


def main():
    a = sys.argv[1:]
    opt = {}
    for k in ('--png', '--bg', '--only'):
        if k in a:
            i = a.index(k)
            opt[k] = a[i + 1]
            del a[i:i + 2]
    if not a:
        sys.exit(__doc__)
    bg = tuple(float(v) for v in opt.get('--bg', '0,0,0').split(','))
    for mv, r in measure(a[0], a[1:], opt.get('--png'), bg, opt.get('--only', '')).items():
        f = r['brightest']
        print('%-13s brightest frame %d: peak %.2f, over 1.0 %.1f, added over 0.5 %.1f, energy %.1f, white %.1f; most over '
              '1.0 in a frame %.1f, most white %.1f' % (mv, f[0], f[1], f[2], f[3], f[4], f[5], r['max_over_1'],
                                                        r['max_white']))


if __name__ == '__main__':
    main()
