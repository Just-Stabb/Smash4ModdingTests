#!/usr/bin/env python3
"""Steve's moves (fighters/pickel/README.md): his Ultimate normals' hitboxes in Pit's scripts, and which
of his tools each move shows.

  python3 tools/pickel_build.py DUMP STEVE PICKEL_BODY VL MODEL OUT

DUMP: the smashline dump's lua2cpp_pickel; STEVE: Ultimate's fighter/pickel (motion/body/c00);
PICKEL_BODY: his folder's script/animcmd/body (add_fighter.py's copy of Pit's, universal-mechanics
game.bin); VL: his fighter_param_vl (Pit's); MODEL: his converted model/body/c00 (joint ids). Writes
OUT/script/animcmd/body/{game,effect,sound,expression}.bin + motion.mtable,
OUT/fighter_param_vl_pickel.bin and OUT/tool_vis.json (for ultimate_fighter.py motions --extra-vis).

- Material: Ultimate's moves branch on the tool's material (wood / stone / iron / gold / diamond: damage
  x1 / x1.1 / x1.2 / x1 (faster) / x1.35). There's no material system here yet: every move is iron
  (MATERIAL), as the tools drawn. Where the dump has no iron branch (side tilt, neutral air: the
  decompiler kept only some), the wood one x1.2 (the ratio of the moves that have both).
- Articles: down tilt's fire, down smash's lava (twice: in front, then behind) and down air's anvil
  are articles in Ultimate; their hitboxes go into his own scripts at where the article appears
  (ARTICLE_HITS: an estimate, the spawn points are in Ultimate's code).
- Tools: his game scripts ask for a tool (WorkModule set_int CRAFT_WEAPON_KIND_*, at a frame) and put
  it away (on_flag REQUEST_REMOVE_HAVE_CRAFT_WEAPON); tool_vis.json shows that tool's mesh (in Pit's
  bow / blade slots, ultimate_fighter.py PIT_TOOL_VIS) from that frame to the end of the animation.
- His jab is his side tilt in Ultimate (no game_attack11 in the dump): attack11 = attacks3, one jab and
  no rapid jab (JAB_PARAMS, set with tools/fighter_param.py). Walking during it and up tilt (Ultimate's
  arm / upper-body layers) isn't done: they play standing.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import acmd  # noqa: E402
import ultimate_acmd as U  # noqa: E402

MATERIAL = 'IRON'
WOOD_TO_IRON = 1.2
CONDS = ['MATERIAL_KIND_%s)' % MATERIAL, 'SITUATION_KIND_GROUND)']
TOOLS = {'SWORD': 'tool_sword', 'PICK': 'tool_pick', 'AXE': 'tool_axe', 'SHOVEL': 'tool_shovel'}
# Smash 4 script <- (article script file, its game function, the frame it appears, forward / up offset,
# mirrored: behind him)
ARTICLE_HITS = {
    'attacklw3': [('pickel_fire/AttackLw3', 'game_attacklw3', 5, 9.0, 0.0, False)],
    'attacklw4': [('pickel_melt/AttackLw4', 'game_attacklw4', 8, 0.0, 0.0, False),
                  ('pickel_melt/AttackLw4', 'game_attacklw4', 26, 0.0, 0.0, True)],
}
# down air's anvil: falls under him from frame 12 (param_forge: speed 1.5, +0.3 a frame up to 3)
ANVIL = ('pickel_forge/FallAttack', 'game_fallattack', 12, 20)
# fighter_param (reference/fighter_param_attributes.csv): 263 jab count, 264 has rapid jab
JAB_PARAMS = {263: 1, 264: 0}


def run(*argv):
    r = subprocess.run([sys.executable] + list(argv), capture_output=True, text=True)
    if r.returncode:
        sys.exit('%s failed:\n%s%s' % (os.path.basename(argv[0]), r.stdout, r.stderr))
    return r.stdout


def timeline(cmds):
    """[(frame, command)] of a script (FRAME / WAIT / END dropped)"""
    out, f = [], 0.0
    for c in cmds:
        if c.name == 'FRAME':
            f = max(f, float(c.params[0]))
        elif c.name == 'WAIT':
            f += float(c.params[0])
        elif c.ident != acmd.END:
            out.append((f, c))
    return out


def script_of(events):
    out, f = [], 0.0
    for fr, c in sorted(events, key=lambda e: e[0]):
        if fr > f:
            out.append(U.cmd('FRAME', int(round(fr))))
            f = fr
        out.append(c)
    return out + [acmd.Command(acmd.END)]


def hitboxes(cmds):
    return [c for c in cmds if c.name in ('Special_Hitbox', 'Extended_Special_Hitbox')]


def moved(c, z, y, mirror):
    """an article's hitbox on its top -> on his top, z / y further; mirrored (behind him)"""
    c = acmd.Command(c.ident, list(c.params))
    if c.name not in ('Special_Hitbox', 'Extended_Special_Hitbox'):
        return c
    sgn = -1.0 if mirror else 1.0
    c.params[11] = sgn * float(c.params[11]) + sgn * z
    c.params[10] = float(c.params[10]) + y
    if c.name == 'Extended_Special_Hitbox':
        c.params[-1] = sgn * float(c.params[-1]) + sgn * z
        c.params[-2] = float(c.params[-2]) + y
    if mirror:
        c.params[34] = U.FACING['ATTACK_LR_CHECK_POS']      # sends them away from him, behind him too
    return c


def main():
    dump, steve, body, vl, model, out = sys.argv[1:7]
    sdir = os.path.join(out, 'script/animcmd/body')
    os.makedirs(sdir, exist_ok=True)
    mlist = os.path.join(steve, 'motion/body/c00/motion_list.bin')
    with tempfile.TemporaryDirectory() as tmp:
        print(run(os.path.join(HERE, 'ultimate_acmd.py'), os.path.join(dump, 'pickel'), os.path.join(body, 'game.bin'),
                  os.path.join(sdir, 'game.bin'), model, '--others', body, tmp, '--motion-list', mlist,
                  '--mtable', os.path.join(body, 'motion.mtable'), os.path.join(sdir, 'motion.mtable'),
                  '--vl', vl, os.path.join(out, 'fighter_param_vl_pickel.bin'), '--vl-kind', 'pit',
                  '--effects', os.path.join(ROOT, 'reference/ultimate_sys_effects.json'),
                  os.path.join(steve, 'model/body/c00/model.nusktb'), *sum((['--cond', c] for c in CONDS), [])
                  ).strip().split('\n')[0])
        for fn in ('effect.bin', 'sound.bin', 'expression.bin'):
            os.replace(os.path.join(tmp, fn), os.path.join(sdir, fn))
    game = acmd.ACMDFile.load(os.path.join(sdir, 'game.bin'))
    tr = U.Translator(U.joint_ids(model))
    by_game = {}                # game script -> the motion_list entries playing it (body, arm / upper layers)
    for e in U.read_motion_list(mlist):
        by_game.setdefault(e['game'], []).append(e)
    anims = {}
    for f in os.listdir(os.path.join(steve, 'motion/body/c00')):
        if f.endswith('.nuanmb'):
            anims[U.hash40(f)] = anims[U.hash40(f[:-7])] = f[:-7]
    vis, log = {}, []
    for src, name in U.TRANSLATE.items():
        path = os.path.join(dump, 'pickel', src + '.txt')
        if not os.path.exists(path):
            continue
        body_fn = U.functions(open(path).read()).get('game_' + src.lower())
        if body_fn is None:
            continue
        U.TRUE_CONDS[:] = CONDS
        cmds = tr.script(body_fn)
        events = list(tr.events)
        U.TRUE_CONDS[:] = CONDS[1:]
        bare = tr.script(body_fn)
        if hitboxes(cmds) and [c.params for c in hitboxes(cmds)] == [c.params for c in hitboxes(bare)] and \
                'MATERIAL_KIND' in body_fn:
            # no iron branch in the dump: its fallback ran; the wood branch x1.2 if there is one
            U.TRUE_CONDS[:] = ['MATERIAL_KIND_WOOD)'] + CONDS[1:]
            wood = tr.script(body_fn)
            if [c.params for c in hitboxes(wood)] != [c.params for c in hitboxes(bare)]:
                for c in hitboxes(wood):
                    c.params[3] = round(float(c.params[3]) * WOOD_TO_IRON, 3)
                game.scripts[acmd.crc(name)] = wood
                log.append('%s: wood x%g' % (name, WOOD_TO_IRON))
        # the tool: shown from its request to the end, hidden from a removal request
        keys = {}
        for fr, call, a in events:
            if call == 'WorkModule::set_int' and 'CRAFT_WEAPON_KIND_' in str(a[1]):
                kind = str(a[1]).rsplit('_', 1)[-1]
                if kind in TOOLS:
                    for t in TOOLS.values():
                        keys.setdefault(t, [[0, 0]])
                        keys[t].append([fr, 1 if t == TOOLS[kind] else 0])
            elif call == 'WorkModule::on_flag' and 'REQUEST_REMOVE_HAVE_CRAFT_WEAPON' in str(a[1]) and keys:
                for t in keys:
                    keys[t].append([fr, 0])
        for e in (by_game.get(U.hash40('game_' + src.lower()), []) if keys else ()):
            for a in e['anims']:
                if a in anims:
                    vis[anims[a]] = keys
    U.TRUE_CONDS[:] = []
    # his jab is his side tilt (Ultimate: the jab button slashes as forward tilt does; its game_attack11
    # isn't in the dump, its motion_list frames are the side tilt's): attacks3's scripts and tool
    for fn in ('game', 'effect', 'sound', 'expression'):
        f = game if fn == 'game' else acmd.ACMDFile.load(os.path.join(sdir, fn + '.bin'))
        if acmd.crc('attacks3') in f.scripts:
            f.scripts[acmd.crc('attack11')] = list(f.scripts[acmd.crc('attacks3')])
        if fn != 'game':
            f.save(os.path.join(sdir, fn + '.bin'))
    if 'c01attacks3s' in vis:
        vis['c00attack11'] = vis['c01attacks3s']
    log.append('attack11: side tilt\'s scripts (one jab, no rapid jab: fighter_param %s)' % JAB_PARAMS)
    # article hitboxes
    tr.skipped = {}
    for name, parts in ARTICLE_HITS.items():
        ev = timeline(game.scripts[acmd.crc(name)])
        for path, fn, start, z, y, mirror in parts:
            cmds = tr.script(U.functions(open(os.path.join(dump, path + '.txt')).read())[fn])
            ev += [(start + f, moved(c, z, y, mirror)) for f, c in timeline(cmds)
                   if c.name not in ('Set_Frame_Duration',)]
        game.scripts[acmd.crc(name)] = script_of(ev)
        log.append('%s: %s' % (name, ', '.join('%s at %d' % (p[0].split('/')[0], p[2]) for p in parts)))
    path, fn, start, frames = ANVIL
    anvil = [c for c in hitboxes(tr.script(U.functions(open(os.path.join(dump, path + '.txt')).read())[fn]))]
    ev, depth, v = timeline(game.scripts[acmd.crc('attackairlw')]), 0.0, 1.5
    for k in range(frames):
        ev += [(start + k, moved(c, 0.0, -depth - 4.0, False)) for c in anvil]
        depth, v = depth + v, min(3.0, v + 0.3)
    ev.append((start + frames, U.cmd('Remove_All_Hitboxes')))
    game.scripts[acmd.crc('attackairlw')] = script_of(ev)
    log.append('attackairlw: the anvil falling under him, frames %d-%d' % (start, start + frames))
    game.save(os.path.join(sdir, 'game.bin'))
    json.dump(vis, open(os.path.join(out, 'tool_vis.json'), 'w'), indent=1, sort_keys=True)
    for line in log:
        print(line)
    print('tools in %d animations: %s' % (len(vis), ', '.join('%s %s' % (a, '/'.join(
        t[5:] for t, k in v.items() if any(s for _f, s in k))) for a, v in sorted(vis.items()))))


if __name__ == '__main__':
    main()
