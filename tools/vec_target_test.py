#!/usr/bin/env python3
"""Tests for Ultimate's set_vec_target_pos in the port tools (tools/vec_target.py, tools/ultimate_acmd.py).

  python3 tools/vec_target_test.py [DUMP_DIR]

1. the converter records set_vec_target_pos (frame, ID, bone, point, frames, the hitbox) and leaves nothing out of
   the script for it (nothing in Smash 4's hitbox takes it: the MSC pull does);
2. the generator gives Sephiroth's up tilt the numbers of his hand-made pull (edge.c edge_hi3_pull, test 151, which
   the user confirmed in game): feet target (2, 37), until frame 22, marked on frames 17 - 18, box 7 +- 15, -10 to 20;
3. the generated per-frame step (the MSC's arithmetic, run here in Python) carries a fighter hit at its feet 7 in front
   to (2, 37) from him by frame 21, and leaves it alone outside the box / out of hitstun;
4. the generated MSC compiles (msclang) and passes msc_stack_check;
5. with DUMP_DIR (a smashline fighter folder): every script with set_vec_target_pos scans and generates.
The up tilt's game script is quoted below (its 368 part, from the smashline dump of Ultimate's edge).
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ultimate_acmd as UA  # noqa: E402
import vec_target as VT  # noqa: E402

EDGE_HI3 = '''unsafe extern "C" fn game_attackhi3(agent: &mut L2CAgentBase) {
    frame(agent.lua_state_agent, 1.0);
    macros::FT_MOTION_RATE(agent, 0.3);
    frame(agent.lua_state_agent, 11.0);
    macros::FT_MOTION_RATE(agent, 1);
    frame(agent.lua_state_agent, 17.0);
    if macros::is_excute(agent) {
        AttackModule::disable_tip(agent.module_accessor);
        macros::ATTACK(agent, 0, 0, Hash40::new("top"), 1.0, 368, 100, 0, 0, 4.5, 0.0, 8.5, 5.0, Some(0.0), Some(8.5), Some(5.0), 0.4, 1.0, *ATTACK_SETOFF_KIND_OFF, *ATTACK_LR_CHECK_POS, false, 0, 0.0, 0, false, false, false, false, true, *COLLISION_SITUATION_MASK_G, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_normal"), *ATTACK_SOUND_LEVEL_S, *COLLISION_SOUND_ATTR_CUTUP, *ATTACK_REGION_NONE);
        macros::ATTACK(agent, 1, 0, Hash40::new("top"), 1.0, 368, 100, 0, 0, 4.5, 0.0, 8.5, 9.5, Some(0.0), Some(8.5), Some(10.0), 0.4, 1.0, *ATTACK_SETOFF_KIND_OFF, *ATTACK_LR_CHECK_POS, false, 0, 0.0, 0, false, false, false, false, true, *COLLISION_SITUATION_MASK_G, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_normal"), *ATTACK_SOUND_LEVEL_S, *COLLISION_SOUND_ATTR_CUTUP, *ATTACK_REGION_NONE);
        AttackModule::set_vec_target_pos(agent.module_accessor, 0, Hash40::new("top"), &Vector2f{x: 2.0, y: 45.0}, 5, false);
        AttackModule::set_vec_target_pos(agent.module_accessor, 1, Hash40::new("top"), &Vector2f{x: 0.0, y: 46.0}, 6, false);
    }
    frame(agent.lua_state_agent, 18.0);
    if macros::is_excute(agent) {
        AttackModule::clear_all(agent.module_accessor);
    }
}
'''

fails = 0


def check(what, ok, detail=''):
    global fails
    print('%s  %s%s' % ('ok  ' if ok else 'FAIL', what, (': ' + str(detail)) if detail and not ok else ''))
    if not ok:
        fails += 1


class _NoBones(UA.Translator):
    def bone(self, name):
        return 0


def step(seg, f, me, lr, victims, mask, self_stop=False):
    """the generated function's arithmetic for one frame: victims [[x, y, hitstun, hitstop]]; returns the mask"""
    if f < seg['frame']:
        return 0
    if f >= seg['end']:
        return mask
    tx, ty = me[0] + seg['x'] * lr, me[1] + seg['y']
    k = 1.0 / (seg['end'] - f)
    bx, bw, blo, bhi = seg['box']
    for s, v in enumerate(victims):
        bit = 1 << s
        if f < seg['frame'] + 2 and not mask & bit and (v[3] > 0 or v[2] > 0) and abs(v[0] - me[0] - bx * lr) < bw \
                and blo < v[1] - me[1] < bhi:
            mask |= bit
        if mask & bit and not self_stop:
            v[0] += (tx - v[0]) * k
            v[1] += (ty - v[1]) * k
    return mask


def main():
    # 1. the converter
    tr = _NoBones({})
    cmds = tr.script(UA.functions(EDGE_HI3)['game_attackhi3'])
    vt = tr.vec_targets
    check('converter: two targets recorded', len(vt) == 2, vt)
    check('converter: ID 0 (2, 45) over 5 at frame 17 on top', vt and (vt[0]['frame'], vt[0]['id'], vt[0]['bone'],
          vt[0]['x'], vt[0]['y'], vt[0]['frames']) == (17.0, 0, 'top', 2.0, 45.0, 5), vt[:1])
    check('converter: the hitbox kept with it (size 4.5, forward 5, G only)', vt and vt[0]['hitbox'] and
          (vt[0]['hitbox']['size'], vt[0]['hitbox']['z'], vt[0]['hitbox']['situation']) == (4.5, 5.0, 1), vt[:1])
    check('converter: set_vec_target_pos not counted as left out', not any('vec_target' in k for k in tr.skipped), tr.skipped)
    hbs = [c for c in cmds if c.name.endswith('Hitbox')]
    check('converter: the hitboxes as before (two, angle 366)', len(hbs) == 2 and all(c.params[4] == 366 for c in hbs),
          [c.params[4] for c in hbs])

    # 2. the generator against the hand-made up tilt (edge.c edge_hi3_pull)
    segs = VT.segments(vt)
    s = segs[0] if segs else {}
    check('generator: one segment', len(segs) == 1, segs)
    check('generator: feet target (2, 37) as edge_hi3_pull', (s.get('x'), s.get('y')) == (2.0, 37.0), s)
    check('generator: until frame 22 as edge_hi3_pull', s.get('end') == 22.0, s)
    check('generator: box 7 +- 15, -10 to 20 as edge_hi3_pull', s.get('box') == (7, 15, -10, 20), s.get('box'))
    fn, code = VT.msc('edge', 'AttackHi3', 0x29, segs, 0x0F00030E)
    check('generator: marked on frames 17 - 18 (mark = 19.0f)', 'mark = 19.0f;' in code)
    check('generator: status 0x29, mask VAR_14 as edge_hi3_pull',
          'global4 != 0x29' in code and '0x0f00030e' in code and 'vec_target: AttackHi3 ' in code)

    # 3. the arithmetic
    me, lr = (100.0, 0.0), -1.0
    v = [[93.0, 0.0, 20.0, 0.0], [100.0, 40.0, 20.0, 0.0], [60.0, 0.0, 20.0, 0.0], [95.0, 0.0, 0.0, 0.0]]
    mask = 0
    path = []
    for f in range(15, 26):
        mask = step(s, float(f), me, lr, v, mask)
        path.append((f, round(v[0][0], 2), round(v[0][1], 2)))
    check('step: the one hit 7 in front (facing left) ends at (2, 37) from him by frame 21',
          abs(v[0][0] - 98.0) < 1e-4 and abs(v[0][1] - 37.0) < 1e-4, path)
    check('step: it rises every frame 17 - 21', all(path[i + 1][2] > path[i][2] for i in range(2, 6)), path)
    check('step: outside the box (40 up, 40 behind) or out of hitstun: left alone',
          v[1][:2] == [100.0, 40.0] and v[2][:2] == [60.0, 0.0] and v[3][:2] == [95.0, 0.0], v)
    w = [[93.0, 0.0, 20.0, 0.0]]
    m = step(s, 17.0, me, lr, w, 0, self_stop=True)
    check('step: marked but not moved while he is in hitlag', m == 1 and w[0][:2] == [93.0, 0.0], w)

    # 4. compiles
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, 't.c')
        open(src, 'w').write('int global0;\nint global1;\nint global2;\nint global3;\nint global4;\n\nfloat func_13(float arg0)\n{\n    if (arg0 < 0.0f)\n    {\n        return -arg0;\n    }\n'
                             '    return arg0;\n}\n\nvoid main()\n{\n    %s();\n}\n\n%s\n' % (fn, code))
        out = os.path.join(d, 't.mscsb')
        r = subprocess.run([sys.executable, os.path.join(HERE, 'msclang/msclang.py'), '-x', os.path.join(HERE, 'mscinfo.xml'),
                            src, '-o', out], capture_output=True, text=True)
        check('msclang compiles the generated function', r.returncode == 0 and os.path.getsize(out) > 0, r.stderr[-400:])
        if r.returncode == 0:
            r = subprocess.run([sys.executable, os.path.join(HERE, 'msc_stack_check.py'), out], capture_output=True, text=True)
            check('msc_stack_check: no stack problems', r.returncode == 0 and r.stdout.lstrip().startswith('0 of '), r.stdout[-300:])

    # 5. a dump
    if len(sys.argv) > 1:
        res = VT.scan(sys.argv[1])
        errs = {k: v['error'] for k, v in res.items() if v.get('error')}
        check('scan: every script parses', not errs, errs)
        moves = [k for k, v in res.items() if v['targets']]
        try:
            _code, fns, _s = VT.build('t', sys.argv[1], {m: 0x200 for m in moves})
            check('generator: every set_vec_target_pos move (%s)' % ', '.join(moves), len(fns) == len(moves))
        except SystemExit as e:
            check('generator: every set_vec_target_pos move', False, e)
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
