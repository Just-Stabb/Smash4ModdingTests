#!/usr/bin/env python3
"""The Super God Fist's victim motion from Xenoverse 2's CMN.ean (the animations the skill's BAC plays on the victim),
as curves for the scripted hold / launch / slide (tools/supamario_godfist_build.py).

  python3 -I tools/supamario_godfist_xv2.py CMN.ean OUT.json      (reference/xv2/godfist_victim_cmn.json)

The BAC (030_GOD_CSA.bac, `tools/xv2bac.py`): the victim plays entry 2 = CMN.ean #179 GOK_SPA_CSG_D (59 frames:
held 0-40 at x0.8, launched at 40, BAC Movement -Z 0.3 a frame 40-58), then entry 3 = #96 CMN_DMG_SUBERI_AOMUKE
(78 frames: a tumbling slide along the ground, ending on its back). Per frame, from the pelvis (b_C_Pelvis, world):
  s     metres travelled away from the attacker (#179: -Z plus the BAC's 0.3 a frame from 40; #96: +Z, played with the
        victim turned away, as its travel continues)
  h     the pelvis' height (metres; ~1 standing)
  phi   the body's tilt toward the travel (degrees; its up axis turned about its side axis), unwrapped: 57 when
        launched (leaning back from the fist), ~993 at the end (2.6 turns, lying on its back)
Rows: ['179', frame, s, h, phi] for #179 0-58, then ['96', frame, ...] for #96 0-77 (s continuing from #179's end).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import xv2ean as X  # noqa: E402

HELD, LAUNCHED = 179, 96
LAUNCH_FRAME = 40
BAC_PUSH = 0.3            # entry 2's Movement: -Z 0.3 a frame, frames 40-58


def curves(ean):
    bi = {b.name: i for i, b in enumerate(ean.bones)}
    par = [b.parent for b in ean.bones]

    def pelvis(an, f):
        chain, i = [], bi['b_C_Pelvis']
        while i >= 0:
            chain.append(i)
            i = par[i]
        p, q = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)
        for j in reversed(chain):
            lp, lq, _s = ean.local(an, j, f)
            r = X.qrot(q, lp)
            p = (p[0] + r[0], p[1] + r[1], p[2] + r[2])
            q = X.qmul(q, lq)
        return p, X.qrot(q, (0.0, 1.0, 0.0))
    held, launched = ean.animations[HELD], ean.animations[LAUNCHED]
    raw = []
    z0 = pelvis(held, 0)[0][2]
    for f in range(held.frames):
        p, up = pelvis(held, f)
        s = -(p[2] - z0) + BAC_PUSH * max(0, f - LAUNCH_FRAME)
        raw.append(['179', f, s, p[1], math.degrees(math.atan2(-up[2], up[1]))])
    s_end = raw[-1][2]
    z96 = pelvis(launched, 0)[0][2]
    for f in range(launched.frames):
        p, up = pelvis(launched, f)
        raw.append(['96', f, s_end + p[2] - z96, p[1], math.degrees(math.atan2(up[2], up[1]))])
    prev, off = None, 0.0
    for r in raw:
        ph = r[4] + off
        if prev is not None:
            while ph - prev > 180:
                ph -= 360
                off -= 360
            while ph - prev < -180:
                ph += 360
                off += 360
        r[4] = ph
        prev = ph
    return [[a, b, round(s, 4), round(h, 4), round(ph, 2)] for a, b, s, h, ph in raw], held.name, launched.name


def main():
    a = sys.argv[1:]
    if len(a) != 2:
        sys.exit(__doc__)
    ean = X.Ean(open(a[0], 'rb').read())
    rows, n1, n2 = curves(ean)
    head = {'source': 'XV2 CMN.ean #%d %s, #%d %s (b_C_Pelvis); tools/supamario_godfist_xv2.py' % (
        HELD, n1, LAUNCHED, n2), 'launch_frame': LAUNCH_FRAME, 'bac_push': BAC_PUSH,
        'columns': ['anim', 'frame', 's', 'h', 'phi']}
    text = json.dumps(head)[:-1] + ', "rows": [\n' + ',\n'.join(json.dumps(r) for r in rows) + ']}\n'
    open(a[1], 'w').write(text)
    print('%s: %d rows; travel %.2f m, turn %.1f degrees after the launch' % (
        a[1], len(rows), rows[-1][2] - rows[LAUNCH_FRAME][2], rows[-1][4] - rows[LAUNCH_FRAME][4]))


if __name__ == '__main__':
    main()
