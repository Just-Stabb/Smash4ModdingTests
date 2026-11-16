#!/usr/bin/env python3
"""How much of a move's converted effects would bloom (Sledgehammer v3, the user's "extremely bright" glow): fx_render's
Smash 4 side (the converted emitters through their own programs) on a black background, per frame: the brightest
channel drawn, the area (square units) drawn over 1.0 (Smash 4 blooms colours past 1: fighters/brave/README.md) and
over 0.5, and the energy (the summed colour, per square unit). Supamario's moves as their scripts call them: the
Sledgehammer's charge, uncharged and charged swing and hit (calls built from tools/supamario_sledgehammer_build.py),
the Super God Fist (attackdash) and Core Breaker's charge (specialhi before its frame 55) from effect.bin.

  python3 -I tools/supamario_fx_glow.py BUILD_OUT_DIR [MOVE ...] [--png DIR]

BUILD_OUT_DIR: tools/supamario_sledgehammer_build.py's OUT_DIR. MOVE: sh_charging, sh_uncharged, sh_charged, sh_hit,
attackdash, cb_charge (default all). --png DIR: each move's six brightest frames side by side. Bones other than top
are drawn at top (the fist's effects placed 8 up, 3 ahead); his body isn't drawn.
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
    c = [x for x in R.s4_calls(eb, 'attackdash') if (x[1] >> 16) == 0x341]
    out['attackdash'] = (c, list(range(min(x[0] for x in c), min(x[0] for x in c) + 90)))
    c = [x for x in R.s4_calls(eb, 'specialhi') if (x[1] >> 16) == 0x341 and x[0] < 55]
    out['cb_charge'] = (c, list(range(31, 58)))
    return out


def measure(out_dir, which=(), png=None):
    R.BG = np.array([0.0, 0.0, 0.0])
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
                sim = R.simulate(em, (fr0, cm, size, off), frames, seed=k + 1)
                for fr in frames:
                    if sim[fr]:
                        m = cm @ R.emitter_matrix(em, fr - fr0)
                        if em.s4 is not None and R.draw_s4(canv[fr], em, sim[fr], m, float(fr - fr0)):
                            continue
                        R.draw(canv[fr], em, sim[fr], cm)
        rows = []
        for fr in frames:
            mx = canv[fr].rgb.max(axis=2)
            rows.append((fr, round(float(mx.max()), 2), round(float((mx > 1.0).sum()) / 36.0, 1),
                         round(float((mx > 0.5).sum()) / 36.0, 1), round(float(canv[fr].rgb.sum()) / 36.0, 1)))
        res[mv] = {'brightest': max(rows, key=lambda r: r[4]), 'max_over_1': max(r[2] for r in rows), 'frames': rows}
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
    png = None
    if '--png' in a:
        i = a.index('--png')
        png = a[i + 1]
        del a[i:i + 2]
    if not a:
        sys.exit(__doc__)
    for mv, r in measure(a[0], a[1:], png).items():
        f = r['brightest']
        print('%-13s brightest frame %d: peak %.2f, over 1.0 %.1f, over 0.5 %.1f, energy %.1f; most over 1.0 in a frame '
              '%.1f' % (mv, f[0], f[1], f[2], f[3], f[4], r['max_over_1']))


if __name__ == '__main__':
    main()
