#!/usr/bin/env python3
"""The Hitbox Viewer's effects (Sm4shCommand v1.5.0), headless: builds the fighter folders effect_viewer_test.cs reads
and the names / lifetimes it expects (independently, from tools/efc.py and tools/ptcl.py), compiles and runs it.

  python3 tools/Sm4shCommand/effect_viewer_test.py BUILT_DIR WORK_DIR --supamario-base DIR --supamario-build DIR
      --kirby DIR --kirby-pac MAIN.pac --kirby-acmd DIR --brave DIR

BUILT_DIR: the built Sm4shCommand (SM4SHCommand.exe, SALT.dll, Events.cfg, Tooltips). Supamario: the base folder (Mario's
model, Mario's scripts) and a build (tools/supamario_*_build.py: motion, scripts, effect); Kirby: a folder with model /
motion, the main.pac with the BraveSword animations and the folder with the Kirby sword build's effect.bin; Hero: the
brave folder (effect, script).

v1.6.0 (Level 2) adds the particles (counts on each frame, a particle's path; tools/fx_render.py's simulation as the
reference), the .ptcl textures (tools/ptcl.py), the effect models' frames / colour gain (tools/mta.py) and the trail
textures, written to expect_fx.txt.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import efc as EFC  # noqa: E402
import ptcl as PTCL  # noqa: E402

MONO = '/usr/lib/mono/4.5'
SUPERJUMP = 0x5     # Mario's PtcMarioSuperjumppunch entry: an emitter with a deterministic path (speed 4, gravity, air)
CSC = ['dotnet', '/usr/lib/dotnet/sdk/8.0.134/Roslyn/bincore/csc.dll']


def arg(a, name):
    return a[a.index(name) + 1]


def copy(src, dst):
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    elif os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)


def lifetime(p, si):
    """the set's play time as the viewer works it out: max over emitters of start + emit start + end + life + random
    life; None when one never stops"""
    best = 0
    ems = [e['data'] for e in p.sets[si]['emitters'] if e['data'] is not None]
    for d in ems:
        one = d[0x2FF] != 0
        start, est, end = (int.from_bytes(d[o:o + 4], 'big', signed=True) for o in (0x448, 0x44C, 0x450))
        life, rnd = (int.from_bytes(d[o:o + 4], 'big', signed=True) for o in (0x4B0, 0x4B4))
        if not one or end >= 0x7FFFFFF or life >= 0x7FFFFFF:
            return None
        best = max(best, max(0, start) + max(0, est) + max(0, end) + max(0, life) + max(0, rnd))
    return best if ems else None


def expect(bank_dir, name, ids):
    e = EFC.Efc(open(os.path.join(bank_dir, name + '.010d0000.efc'), 'rb').read())
    p = PTCL.Ptcl(open(os.path.join(bank_dir, name + '.010d0000.ptcl'), 'rb').read())
    out = []
    for i in ids:
        fl, st, md, _a, _b = e.entries[i & 0xFFFF]
        parts = []
        if st:
            parts.append(p.set_name(st - 1))
        if md:
            parts.append('model ' + e.models[md - 1])
        life = lifetime(p, st - 1) if st else None
        if md and (life is not None or not st):
            # (v1.6.0) a model's animation counts too: a model-only entry plays as long as it
            life = max(life or 0, model_frames(bank_dir, e.models[md - 1])) or None
        out.append('0x%X\t%s\t%d' % (i, ' + '.join(parts), max(1, life) if life is not None else -1))
    return out


def particles(bank_dir, name, ids, frames=30):
    """v1.6.0: what the viewer's particles must come out as, from tools/fx_render.py's own simulation (s4_emitters,
    simulate; its CPU particles, no shaders) of each id's set placed at (0, 5, 2), size 1.5: per emitter whose counts
    don't depend on the random generator (no life / interval random) its live particles on frames 0 .. frames - 1;
    for emitters whose first particle's path doesn't either (point volume, no spread, no random speed, no all-direction
    speed) that particle's place on some frames; texture slot 0 of the first emitter (ptcl.py decode_texture: size,
    mean red / alpha); an effect model's frame count and its first material's colour gain on frame 10 (tools/mta.py)."""
    import fx_render
    import mta as MTA
    import numpy as np
    fx_render.S4_SHADERS = False
    e = EFC.Efc(open(os.path.join(bank_dir, name + '.010d0000.efc'), 'rb').read())
    p = PTCL.Ptcl(open(os.path.join(bank_dir, name + '.010d0000.ptcl'), 'rb').read())
    out = []
    cm = fx_render.call_matrix((0, 5, 2), (0, 0, 0), 1.5)
    for i in ids:
        _fl, st, md, _a, _b = e.entries[i & 0xFFFF]
        if st:
            ems = fx_render.s4_emitters(p, st - 1)
            datas = [x['data'] for x in p.sets[st - 1]['emitters'] if x['data'] is not None]
            for k, (em, d) in enumerate(zip(ems, datas)):
                f = lambda n, d=d: p.field(d, n)    # noqa: E731
                sim = fx_render.simulate(em, (0, cm, 1.5, None), list(range(frames)), seed=k + 1)
                if f('ptcl_life_random') <= 0 and f('emit_interval_random') <= 1:     # (a gap random of 1 adds int(U x 1) = 0)
                    out.append('count\t0x%X\t%d\t%s' % (i, k, ' '.join(str(len(sim[t])) for t in range(frames))))
                if (f('volume_type') == 0 and f('dispersion_angle') == 0 and f('init_velocity_random') == 0
                        and f('figure_velocity') == 0 and not any(a['target'] in (0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 16)
                                                                 for a in p.key_anims(d))):
                    for t in range(frames):
                        if sim[t]:
                            pos = sim[t][0][0]
                            out.append('pos\t0x%X\t%d\t%d\t%.5f %.5f %.5f' % (i, k, t, pos[0], pos[1], pos[2]))
            d0 = datas[0]
            img = p.decode_texture(d0, 0)
            if img is not None:
                out.append('tex\t0x%X\t0\t%d %d %.3f %.3f' % (i, img.shape[1], img.shape[0], img[..., 0].mean(), img[..., 3].mean()))
        if md:
            mdir = os.path.join(bank_dir, 'model', e.models[md - 1])
            om = open(os.path.join(mdir, 'model.omo'), 'rb').read()
            omo_frames = int.from_bytes(om[0x10:0x12], 'big')
            m = MTA.read(open(os.path.join(mdir, 'model.mta'), 'rb').read())
            mat = m['mats'][0]
            gain = [pp for pp in mat['props'] if pp['name'] == 'NU_effColorGain'][0]['values']
            g10 = gain[min(10, len(gain) - 1)]
            out.append('model\t0x%X\t%d\t%d\t0x%08X\t%s' % (i, omo_frames, m['frames'], mat['hash'], ' '.join('%.4f' % x for x in g10)))
    return out


def model_frames(bank_dir, model):
    """an effect model's animation length: the longer of model.omo's frames and model.mta's (the viewer's
    EffectModel.Frames)"""
    mdir = os.path.join(bank_dir, 'model', model)
    n = 0
    if os.path.exists(os.path.join(mdir, 'model.omo')):
        n = int.from_bytes(open(os.path.join(mdir, 'model.omo'), 'rb').read()[0x10:0x12], 'big')
    if os.path.exists(os.path.join(mdir, 'model.mta')):
        n = max(n, int.from_bytes(open(os.path.join(mdir, 'model.mta'), 'rb').read()[8:12], 'big'))
    return n


def main():
    a = sys.argv[1:]
    built, work = a[0], a[1]
    fighters = os.path.join(work, 'fighter')
    shutil.rmtree(work, ignore_errors=True)
    sm = os.path.join(fighters, 'supamario')
    base, build = arg(a, '--supamario-base'), arg(a, '--supamario-build')
    for sub in ('model', 'motion', 'script', 'effect'):
        copy(os.path.join(base, sub), os.path.join(sm, sub))
    for sub in ('motion', 'script', 'effect'):
        copy(os.path.join(build, sub), os.path.join(sm, sub))
    kb = os.path.join(fighters, 'kirby')
    copy(os.path.join(arg(a, '--kirby'), 'model'), os.path.join(kb, 'model'))
    copy(arg(a, '--kirby-pac'), os.path.join(kb, 'motion', 'body', 'main.pac'))
    copy(os.path.join(arg(a, '--kirby-acmd'), 'effect.bin'), os.path.join(kb, 'script', 'animcmd', 'body', 'effect.bin'))
    copy(os.path.join(arg(a, '--kirby-acmd'), 'motion.mtable'), os.path.join(kb, 'motion', 'body', 'motion.mtable'))
    br = os.path.join(fighters, 'brave')
    copy(arg(a, '--brave'), br)
    lines = expect(os.path.join(sm, 'effect', 'supamario'), 'supamario',
                   [0x341002F, 0x3410034, 0x3410056, 0x3410031, 0x341002C, 0x341000B])
    lines += expect(os.path.join(br, 'effect', 'brave'), 'brave', [0x32C0025, 0x32C000F])
    lines += expect(os.path.join(br, 'effect', 'brave'), 'brave', [0x3450078 & 0xFFFF])
    lines[-1] = '0x3450078\t' + lines[-1].split('\t', 1)[1]
    exp = os.path.join(work, 'expect.txt')
    open(exp, 'w').write('\n'.join(lines) + '\n')
    fx = particles(os.path.join(sm, 'effect', 'supamario'), 'supamario',
                   [0x341002F, 0x3410031, 0x3410040, 0x3410057, 0x3410034, 0x3410049, 0x3410000 + SUPERJUMP])
    exp_fx = os.path.join(work, 'expect_fx.txt')
    open(exp_fx, 'w').write('\n'.join(fx) + '\n')
    print('expect_fx: %d lines (%d counts, %d positions)' % (len(fx), sum(x.startswith('count') for x in fx),
                                                            sum(x.startswith('pos') for x in fx)))
    for l in lines:
        print('expect', l)
    test = os.path.join(work, 'run')
    copy(built, test)
    src = os.path.join(HERE, 'effect_viewer_test.cs')
    refs = ['-r:SALT.dll', '-r:SM4SHCommand.exe'] + ['-r:%s/%s.dll' % (MONO, n) for n in (
        'mscorlib', 'System', 'System.Core', 'System.Windows.Forms', 'System.Drawing')]
    subprocess.check_call(CSC + ['-nologo', '-out:EvTest.exe', '-nostdlib'] + refs + [src], cwd=test)
    # (Runtime and the Viewport are WinForms: an X display, xvfb-run when there's none)
    cmd = ['mono', 'EvTest.exe', 'Events.cfg', fighters, exp, exp_fx]
    if not os.environ.get('DISPLAY') and shutil.which('xvfb-run'):
        cmd = ['xvfb-run', '-a'] + cmd
    r = subprocess.run(cmd, cwd=test)
    sys.exit(r.returncode)


if __name__ == '__main__':
    main()
