#!/usr/bin/env python3
"""Behaviour tests of step 2p (tools/smashrun_walker_cave.py; docs/smash-run-port.md "Step 2p") on a patched
executable, in unicorn (smashrun_step2h_test.py's machine; the game's own functions run natively where named):

  python3 tools/smashrun_step2p_test.py PATCHED.rpx [LOG.txt [ENEMY_SRC WIIU_TEMPLATE_BANK CONVERTED_ROOT]]

LOG.txt (optional): the user's step 2o log build log (upload 693c657a): the stomps' `hs` / `pd` lines re-read.
ENEMY_SRC / WIIU_TEMPLATE_BANK / CONVERTED_ROOT (optional): the 3DS enemy/ folder, the Wii U's
snd_se_enemy_Mczakoplasmawisp.nus3bank and the package root holding sound/se/ (tools/smashrun_sound.py convert).

- the stomp bounce (the Big Goomba's "no height"): every stompable kind's stomp (Goomba, Tiki Buzz, Big Goomba walking
  and angry, Paratroopa winged and walking) writes, with the StepJump request, the fighter's float 0x1000006 = the
  kind's multiplier, the step count int 0x10000006 = 0 and the tread target int 0x10000008 = 0x50000000; the kind's
  slot 20 runs once (our stomp only);
- that id resolves to no object in the game's own 0x02BF205C (category 5), so StepJump's func_1149 (`if (LinkModule(5,
  3, int 0x10000008)) ...; float 0x1000006 = float 0x1000009`) is skipped and float 0x1000006 keeps the multiplier:
  the game's StepJump speed 0x02E79938 then gives the Big Goomba's 0.9 x step_jump_speed_y; the step 2o path (a stale
  target answering 0) gives 0, the fall from rest the log shows;
- (with LOG.txt) the log's stomps: from Jump (0xB) the Big Goomba's first stomp left the fighter falling from rest
  (dy -0.11 then -0.22: speed 0) and its second rose only a frame later with the A -> C (10 -> 12) second tread; the
  Goomba's from 0xC rose at once, with a second tread 8 -> 8 in the next frame (the game's event 6);
- (with the banks) the 19 converted banks: the 3DS BINF (name, id) and PACK kept, the template's PROP / GRP / DTON /
  JUNK, every tone the 3DS's with the Wii U entry flags 0x1800, 7 output sends (3-6 at -90 dB) and the two zero words
  at the end; its data offset / size / volume / rate / channels / samples / loop the 3DS's; the Lethinium bank's tones
  laid out word for word as the Wii U's own Lethinium (Mczakoplasmawisp) tones, differing only in those values;
- slot 63 (the push area / jostle switch the game's change_state calls, 0x026A39E4): the Paratroopa's 3DS 0xB4EF8 (0
  in states 8, 16, 19, 20, 21) and the Spiny's 0xB4940 (0 in 10, 11, 12); the other kinds keep BehaviorImpl's 1.
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_enemy_cave as E  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402
import smashrun_walker_test as T  # noqa: E402
import smashrun_step2h_test as H  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_LR  # noqa: E402

check = T.check
M = H.M
OBJ, INPUT, POSTURE, EN, HEAP = T.OBJ, T.INPUT, T.POSTURE, T.EN, T.HEAP
FWM, FACC, FPOST, FSTAT = H.FWM, H.FACC, H.FPOST, H.FSTAT
FIND_OBJ = 0x02BF205C          # BattleObjectManager: id -> object by its category (id >> 28: 0-4), else 0
BI_SLOT63 = 0x026A4848         # BehaviorImpl's slot 63 (li r3, 1)
CHANGE_STATE_BASE_63 = 0x026A3B28   # change_state_interrupt_base's bl 0x026A39E4 (slot 63 -> the push area)


def log_stomps(path):
    """the step 2o log's stomps: (kind, the fighter's status, posture ys of the pd lines per frame after it, the
    kind's state changes in the next three frames)"""
    out = []
    lines = open(path, errors='replace').read().splitlines()
    f = lambda h: struct.unpack('>f', bytes.fromhex(h.zfill(8)))[0]  # noqa: E731
    for i, ln in enumerate(lines):
        m = re.search(r'S4N hs k=(\w+) s=\w+ fst=(\w+) fy=(\w+)', ln)
        if not m:
            continue
        k, fst, fy = int(m.group(1), 16), int(m.group(2), 16), f(m.group(3))
        ys, sts = [fy], []
        for ln2 in lines[i + 1:i + 200]:
            p = re.search(r'S4N pd .*fy=(\w+)', ln2)
            if p and f(p.group(1)) != ys[-1]:
                ys.append(f(p.group(1)))
            s = re.search(r'S4N st k=(\w+) v=\w+ s=(\w+) n=(\w+)', ln2)
            if s and int(s.group(1), 16) == k and len(ys) <= 4:
                sts.append((int(s.group(2), 16), int(s.group(3), 16)))
            if len(ys) > 6:
                break
        out.append((k, fst, ys, sts))
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    img = E.Image(sys.argv[1])
    A, _B, d = W.assemble(W.read_vt(img))
    D = d.addr
    T.VT_ADDR[0] = D['vt']
    fn = dict(A.labels)
    M.STUBS = {fn[k]: k for k in ('f_amode', 'f_aupd', 'f_anone')}
    byname = {w['name']: w for w in W.WALKERS}
    cfg = {w['name']: D['cfg_' + w['name']] for w in W.WALKERS}
    want = {}
    for a in (A.h, A.e, A.g):
        want.update({a.base + 4 * i: x for i, x in enumerate(a.words())})
    bad = [hex(a) for a, x in want.items() if img.u32(a) != x]
    check(not bad, 'regions E / G / H: the assembled code is in the executable %s' % bad[:4])

    def vslot(name, k):
        vt = img.u32(cfg[name] + W.CF['VT'])
        return img.u32(vt + 0xC + 8 * k)

    def top(name):
        tb = W.tread_box(byname[name])
        return tb[1] + tb[2]

    # ---------------------------------------------------------------- the stomp: our tread only, no link
    def stomp(name, state, var=0, status=0xB):
        w = byname[name]
        m = M(img)
        m.walker(cfg[name], state=state, kind=w['kind'], var=var)
        m.wf(POSTURE + 0x14, 0.0)
        m.call(fn['w_init'], {3: OBJ})
        bt = top(name) if name != 'tikibuzz' else 11.72 + 1.5
        m.fighter(y=bt + 10.0, status=status)
        got = []
        for fy in (5.0, -1.0):
            m.wf(FPOST + 0x14, bt + fy)
            m.w32(FSTAT + W.STATUS_KIND, status)
            m.calls = []
            m.call(fn['w_upd'], {3: OBJ, 4: INPUT})
            got.append(list(m.calls))
        return m, got
    mults = {'kuribo': 0.8, 'tikibuzz': 0.98, 'dekakuribo': 0.9, 'patapata': 1.0}
    for name, state, var in (('kuribo', 3, 0), ('tikibuzz', 3, 0), ('dekakuribo', 3, 0), ('dekakuribo', 5, 0),
                             ('patapata', 2, 0), ('patapata', 12, 2)):
        m, got = stomp(name, state, var)
        sets = [c for c in got[1] if c[0] in ('set_float', 'set_int')]
        treads = [c for c in got[1] if c[0] in ('chgi', 'chg')]
        mul = mults[name]
        check(sets == [('set_float', FWM, W.F_TREAD_MUL, mul), ('set_int', FWM, 0, W.I_STEP_COUNT),
                       ('set_int', FWM, W.BO_ID_INVALID, W.I_TREAD_TARGET)]
              and ('msc_status', FACC, (3, W.STEP_JUMP, 0)) in got[1] and len(treads) == 1
              and not [c for c in got[0] if c[0] in ('set_float', 'set_int', 'msc_status')],
              '%s (state %d, var %d), the fighter in Jump (0xB): one tread (%s), float 0x1000006 = %.2f, count 0, '
              'tread target 0x50000000, StepJump requested %s' % (name, state, var, treads, mul, sets))

    # the invalid id finds no object (the game's own resolver, natively): category 5 -> 0
    def find(oid):
        m = M(img)
        m.uc.reg_write(UC_PPC_REG_LR, T.DONE)
        m.run(FIND_OBJ, T.DONE, {3: 0, 4: oid})
        return m.uc.reg_read(T.R[3])
    check(find(W.BO_ID_INVALID) == 0 and find(0x6FFFFFFF) == 0,
          '0x02BF205C(0x50000000) = 0: no object of category 5, so LinkModule op 5 (vt+0x34(3, id)) links nothing and '
          'StepJump\'s func_1149 is skipped')

    # the game's StepJump speed (0x02E79938, natively, paired-single saves nopped) from float 0x1000006
    def speed(mult, count=0):
        m = M(img)
        lo_, hi_ = W.STEP_JUMP_SPEED, W.STEP_JUMP_SPEED + 0x340
        for a in range(lo_, hi_, 4):
            if img.u32(a) >> 26 == 4:
                m.uc.mem_write(a, struct.pack('>I', 0x60000000))
        m.fighter()
        m.params = {0x300015F: 2.4, 0x3000160: 1.5, 0x300000D: 0.0, 0x300000E: 0.0, 0x300000F: 1.0, 0x20000B5: 0.8}
        m.work[(FWM, W.F_TREAD_MUL)] = mult
        m.work[(FWM, W.I_STEP_COUNT)] = count
        m.wf(HEAP + 0x3F000, 0.0)
        m.wf(HEAP + 0x3F004, 0.0)
        m.uc.reg_write(UC_PPC_REG_LR, T.DONE)
        m.run(W.STEP_JUMP_SPEED, T.DONE, {3: HEAP + 0x3E000, 4: HEAP + 0x3F000, 5: FACC})
        return round(m.rf(HEAP + 0x3F004), 4)

    def func_1149(float6, target_answers):
        """common MSC func_1149 (Mario's MSC, StepJump's main): a linked target's event 6 answer (+0x20) replaces
        float 0x1000006; no link (our invalid id): float 0x1000006 as it is"""
        return float6 if target_answers is None else target_answers
    ours = speed(func_1149(0.9, None))
    stale = speed(func_1149(0.9, 0.0))
    check(ours == round(2.4 * 0.9, 4) and stale == 0.0,
          'Big Goomba: with the invalid target the StepJump speed is 0.9 x step_jump_speed_y (%s); the step 2o path '
          '(a linked object answering 0) gives %s: the fall from rest in the log' % (ours, stale))

    # ---------------------------------------------------------------- the log (optional)
    if len(sys.argv) > 2:
        st = log_stomps(sys.argv[2])
        dk = [s for s in st if s[0] == 0x23]
        kb = [s for s in st if s[0] == 0x01]

        def dys(ys):
            return [round(b - a, 2) for a, b in zip(ys, ys[1:])]
        ok = (len(dk) == 2 and dk[0][1] == 0xB and dys(dk[0][2])[1:3] == [-0.11, -0.22] and
              dk[1][1] == 0xB and dys(dk[1][2])[1] == -0.11 and dys(dk[1][2])[2] > 2.5 and (10, 12) in dk[1][3] and
              len(kb) == 1 and kb[0][1] == 0xC and dys(kb[0][2])[1] > 2.0 and (8, 8) in kb[0][3])
        check(ok, 'the step 2o log: Big Goomba stomp 1 from Jump: dy %s (speed 0, falling from rest); stomp 2: dy %s '
              '(a frame at 0, then up with the second tread %s); Goomba from 0xC: dy %s, second tread %s'
              % (dys(dk[0][2]) if dk else None, dys(dk[1][2]) if len(dk) > 1 else None,
                 dk[1][3] if len(dk) > 1 else None, dys(kb[0][2]) if kb else None, kb[0][3] if kb else None))

    # ---------------------------------------------------------------- the banks in the Wii U layout (optional)
    if len(sys.argv) > 5:
        import smashrun_sound as SS
        import minecraft_sound as ms
        src, tpl_path, root = sys.argv[3], sys.argv[4], sys.argv[5]
        tpl = dict(SS.sections_list(open(tpl_path, 'rb').read()))
        bad = []
        for _row, (k, bank, _labs) in sorted(SS.SND_ROWS.items()):
            d3 = open(os.path.join(src, k, 'snd_se_enemy_%s.nus3bank' % k), 'rb').read()
            name = SS.bank_names(os.path.join(src, k, 'snd_se_enemy_%s.nus3bank' % k))
            pth = os.path.join(root, 'sound', 'se', name[0] + '.nus3bank')
            if not os.path.exists(pth):
                bad.append((k, 'missing'))
                continue
            dw = open(pth, 'rb').read()
            s3, sw = dict(SS.sections_list(d3)), dict(SS.sections_list(dw))
            if SS.bank_names(pth) != name or sw[b'PACK'] != s3[b'PACK'] or sw[b'BINF'] != s3[b'BINF'] or \
                    any(sw[x] != tpl[x] for x in (b'PROP', b'GRP ', b'DTON', b'JUNK')):
                bad.append((k, 'sections'))
            for e3, ew in zip(SS.tone_entries(s3[b'TONE']), SS.tone_entries(sw[b'TONE'])):
                if len(e3) < 0x20:
                    if e3 != ew:
                        bad.append((k, 'empty tone'))
                    continue
                h3, n3, r3 = ms.parse_entry(e3)
                hw, nw, rw = ms.parse_entry(ew)
                w3 = struct.unpack('<%dI' % (len(r3) // 4), r3)
                ww = struct.unpack('<%dI' % (len(rw) // 4), rw)
                i = SS.send_list(list(w3))
                f3, fw = struct.unpack('<I', e3[8:12])[0], struct.unpack('<I', ew[8:12])[0]
                exp = list(w3[:i]) + [7] + list(w3[i + 1:i + 7]) + [3, SS.MINUS90, 4, SS.MINUS90, 5, SS.MINUS90,
                                                                      6, SS.MINUS90] + list(w3[i + 7:]) + [0, 0]
                if n3 != nw or fw != f3 | 0x1800 or w3[i] != 3 or list(ww) != exp or hw[:8] != h3[:8]:
                    bad.append((k, n3))
        check(not bad, 'banks: the 19 converted banks (3DS BINF / PACK, the template\'s PROP / GRP / DTON / JUNK, every '
              'tone in the Wii U layout with its 3DS values) %s' % bad[:6])
        b = dict(SS.sections_list(open(os.path.join(root, 'sound', 'se', 'snd_se_enemy_Plasmawisp.nus3bank'),
                                       'rb').read()))
        diffs = set()
        for x, y in zip(SS.tone_entries(b[b'TONE']), SS.tone_entries(tpl[b'TONE'])):
            hx, _nx, rx = ms.parse_entry(x)
            hy, _ny, ry = ms.parse_entry(y)
            wx = struct.unpack('<%dI' % (len(rx) // 4), rx)
            wy = struct.unpack('<%dI' % (len(ry) // 4), ry)
            if hx != hy or len(wx) != len(wy):
                diffs.add('layout')
            diffs |= {i for i, (p, q) in enumerate(zip(wx, wy)) if p != q}
        check(diffs <= {1, 2, 3, 12, 39, 41, 43, 44, 45},
              'banks: Lethinium\'s converted tones = the Wii U\'s own Lethinium tones word for word but the data offset '
              '/ size (1, 2), volume (3), priority (12), loop flag (39), rate (41), samples / loop points (43-45): %s'
              % sorted(diffs, key=str))

    # ---------------------------------------------------------------- slot 63 (the push area per state)
    def s63(name, state):
        m = M(img)
        m.walker(cfg[name], state=state, kind=byname[name]['kind'])
        m.uc.reg_write(UC_PPC_REG_LR, T.DONE)
        m.run(vslot(name, 63), T.DONE, {3: OBJ})
        return m.uc.reg_read(T.R[3])
    pt = {s: s63('patapata', s) for s in range(1, 24)}
    tg = {s: s63('togezo', s) for s in range(1, 14)}
    check(vslot('patapata', 63) == fn['pt_63'] and vslot('togezo', 63) == fn['tg_63'] and
          [s for s, v in pt.items() if v == 0] == [8, 16, 19, 20, 21] and all(v == 1 for s, v in pt.items()
                                                                            if s not in (8, 16, 19, 20, 21)) and
          [s for s, v in tg.items() if v == 0] == [10, 11, 12],
          'slot 63: Paratroopa 0 in 8 / 16 / 19 / 20 / 21 (0xB4EF8), Spiny 0 in 10 / 11 / 12 (0xB4940), else 1')
    others = [n for n in byname if n not in ('patapata', 'togezo') and byname[n].get('vtover')
              and vslot(n, 63) != BI_SLOT63]
    check(not others and img.u32(CHANGE_STATE_BASE_63) == 0x4BFFFEBD,
          'slot 63: every other kind keeps BehaviorImpl\'s 0x026A4848 (1) %s; change_state_interrupt_base calls the '
          'slot-63 switch (bl 0x026A39E4 at 0x026A3B28)' % others)

    T.overrun_check()
    print('%d failures' % len(T.FAILS))
    sys.exit(1 if T.FAILS else 0)


if __name__ == '__main__':
    main()
