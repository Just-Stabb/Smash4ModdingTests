#!/usr/bin/env python3
"""Behaviour tests of step 2m (tools/smashrun_walker_cave.py; docs/smash-run-port.md "Step 2m") on a patched
executable, in unicorn (smashrun_step2k_test.py's machine), every expected value from the 3DS code / files:

  python3 tools/smashrun_step2m_test.py PATCHED.rpx S3DS_STB WIIU_STB ENEMY_SRC WIIU_SE_DIR [OTHER_STB ...]

  S3DS_STB / WIIU_STB: the 3DS's / the Wii U's sound/config/soundlabeltable.bin; ENEMY_SRC: the 3DS enemy/ folder (the
  kinds' snd_se_enemy_<kind>.nus3bank, shipped unchanged, and their animcmd/); WIIU_SE_DIR: the Wii U sound/se (the
  twins' snd_se_enemy_Mczako*.nus3bank); OTHER_STB: more Wii U tables to check the rows are free in (e.g. the user's
  latest package's).

- the map (tools/smashrun_sound.py): each ported kind's bank = its 3DS row (bank id, label list), the row empty in
  every Wii U table given; every 3DS play_se id (smashrun_sound.SITES) and every converted ACMD Sound_Effect id of the
  ported kinds resolves after snd_rows to the same tone name as on the 3DS, a tone of that kind's bank; the twins'
  ids (0xBE2 / 0xBE3 / 0xBE4) to the Smash Run kind's tone of the same name;
- snd_rows run in unicorn on the real Wii U table, then the game's own lookups (0x0311EDBC id -> bank id,
  0x0311EF88 id -> tone) on it: every id above gives its kind's BINF id and the tone named as on the 3DS; a row
  already used by another bank is left alone; on another battle (r3 0) the twins' rows get their own banks back;
- every hooked state / slot calls play_se / stop_se with the 3DS's id at the 3DS's point (play_se stubbed): the
  state enters (SE_EN, the handle where the 3DS keeps it), Shy Guy's second hop, Churine's powder, the Waddle Doo's
  beam end / exit, Ghos's loop (start, damage with the kinetic flag 2, remove) and its immune hit (15), Furiijio's
  beam exits and bound sound (slots 57 / 69), the Propeller Heiho's loop counted per kind (start, death, gone) and
  its swap, the Pooka's damage at the threshold;
- Stalfos (kind 0x30): states 7 / 8 update (sf7_up / sf8_up) make the same calls as the game's 0x026D3EB4 /
  0x026D41E8 in every branch, plus the 3DS's L5F470 drop (set_attach_ground(0), set_passable_check(1),
  set_correct(0), +0x1D4 = 8, -> 1) only when the ground is passable, the target more than P+0xC8 x 10 below and a
  floor under; the Fortress twin (0x59) runs the game's update.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acmd  # noqa: E402
import s3ds_enemy as SE  # noqa: E402
import smashrun_enemy_cave as E  # noqa: E402
import smashrun_flier_test as FT  # noqa: E402
import smashrun_sound as SND  # noqa: E402
import smashrun_step2k_test as K2  # noqa: E402
import smashrun_walker_cave as W  # noqa: E402
import smashrun_walker_test as T  # noqa: E402

check = T.check
OBJ, ACC, HEAP, R = T.OBJ, T.ACC, T.HEAP, T.R
TBL = 0x38000000                    # the fake sound manager / table (mapped by the test)
VTB_CHG = HEAP + 0x3B000            # the twin object's [+0xE0] (change_state vt+0x24C / +0x254)
STUB_CHG, STUB_CHGI = 0x02000100, 0x02000104
PRM, PMGRX = HEAP + 0x3B400, HEAP + 0x3BC00   # [[0x102F6C00] + 0x1C4] (the twin's slot) for the Stalfos runs
ST_STUBS = {W.IS_PASSABLE_GROUND: 'passable', W.RAY_CHECK: 'ray', 0x026A70FC: 'search', 0x026A706C: 'interval',
            0x026A66DC: 'move', W.CHECK_WALL: 'wall', W.CHECK_CLIFF: 'cliff', W.CHECK_TURN: 'turn',
            W.NEAREST: 'nearest', W.GET_TARGET_POS: 'target_pos', W.IS_TOUCH: 'touch', W.SET_ATTACH_GROUND: 'GND',
            W.SET_PASSABLE: 'PASS', W.SET_CORRECT: 'set_correct', STUB_CHG: 'ST', STUB_CHGI: 'STI'}
ST_STUBS.update({v: k for k, v in W.ST_HELP.items()})


class M(K2.K):
    """K2.K with the Stalfos update's calls stubbed by name (self.res: name -> result)"""
    stalfos = False

    def hook(self, u, addr, size, x):
        if self.stalfos and struct.unpack('>I', u.mem_read(addr, 4))[0] >> 26 == 4:
            u.reg_write(T.UC_PPC_REG_PC, addr + 4)   # the game's psq_st / psq_l f31 (paired singles: not in unicorn)
            return
        if self.stalfos and addr in ST_STUBS:
            r = lambda n: u.reg_read(R[n])  # noqa: E731
            n = ST_STUBS[addr]
            res = self.res.get(n, 0)
            if n == 'target_pos':
                self.wf(r(3), 0.0)
                self.wf(r(3) + 4, self.res.get('ty', 0.0))
                self.wf(r(3) + 8, 0.0)
                self.st_calls.append((n, r(5)))
                return self.ret()
            if n == 'ray':
                self.st_calls.append((n, tuple(round(self.rf(r(a) + o), 3) for a in (4, 5) for o in (0, 4)), r(7)))
                return self.ret(res)
            if n in ('l5f7f8',):
                self.w32(r(5), self.res.get('out', -1) & 0xFFFFFFFF)
            arg = {'touch': 4, 'GND': 4, 'PASS': 4, 'set_correct': 4, 'ST': 4, 'STI': 4, 'search': 4,
                   'interval': 4, 'l5f7f8': 4, 'l5f110': 4, 'l5f754': 4, 'turn': 4}.get(n)
            self.st_calls.append((n, r(arg)) if arg else (n,))
            return self.ret(res if n not in ('ST', 'STI') else None)
        return K2.K.hook(self, u, addr, size, x)


def sounds(m):
    return [s for s in m.sounds]


def main():
    if len(sys.argv) < 6:
        sys.exit(__doc__)
    img = E.Image(sys.argv[1])
    t3, tw, src, sedir = SND.stb(sys.argv[2]), SND.stb(sys.argv[3]), sys.argv[4], sys.argv[5]
    others = [SND.stb(p) for p in sys.argv[6:]]
    A, _B, d = W.assemble(W.read_vt(img))
    D = d.addr
    T.VT_ADDR[0] = D['vt']
    fn = dict(A.labels)
    want = {A.h.base + 4 * i: x for i, x in enumerate(A.h.words())}
    bad = [hex(a) for a, x in want.items() if img.u32(a) != x]
    check(not bad, 'region H: the step 2m code to 0x%08X is in the executable %s' % (A.h.pc, bad[:4]))
    byname = {w['name']: w for w in W.WALKERS}
    cfgs = {w['name']: D['cfg_' + w['name']] for w in W.WALKERS}
    vslot = lambda n, k: img.u32(img.u32(cfgs[n] + W.CF['VT']) + 0xC + 8 * k)  # noqa: E731

    # ==== 1. the map, from the files
    banks, names = {}, {}
    bad = []
    for row, (k, bank, labs) in sorted(SND.SND_ROWS.items()):
        bname, bid, tones = SND.bank_names(os.path.join(src, k, 'snd_se_enemy_%s.nus3bank' % k))
        banks[bid], names[k] = tones, bname
        b3, l3 = SND.labels(t3, row)
        if not (bid == bank == b3 and tuple(l3) == labs and tw[0][row][0] == 0xFFFFFFFF and
                all(o[0][row][0] == 0xFFFFFFFF for o in others)):
            bad.append(hex(row))
    check(not bad and len(SND.SND_ROWS) == 19,
          'the 19 ported kinds\' banks: BINF id = their 3DS row\'s bank, the 3DS label lists, the rows (0x28D, 0x69B, '
          '...) empty in the Wii U table%s %s' % (' and %d more' % len(others) if others else '', bad))
    rows3 = {r: SND.labels(t3, r) for r in SND.SND_ROWS}
    rowsw = SND.wiiu_rows(tw)
    ids = {}                          # id -> where
    for k, fa, role, at, sid, _f in SND.SITES:
        if isinstance(sid, int) and sid >> 16:
            ids[sid] = '%s 0x%X' % (k, at)
    acmd_ids = []
    for k in sorted({w['name'] for w in W.WALKERS}):
        dd = os.path.join(src, k, 'animcmd')
        if not os.path.isdir(dd):
            continue
        for f in sorted(os.listdir(dd)):
            p = '/dev/shm/smashrun_step2m_acmd.bin'
            open(p, 'wb').write(SE.acmd_be(open(os.path.join(dd, f), 'rb').read()))
            for h, cmds in acmd.ACMDFile.load(p).scripts.items():
                for c in cmds:
                    if c.name == 'Sound_Effect':
                        acmd_ids.append((k, f, h, c.params[0]))
                        ids[c.params[0]] = '%s %s 0x%08X' % (k, f, h)
            os.remove(p)
    res = {sid: (SND.tone_of(sid, rows3, banks), SND.tone_of(sid, rowsw, banks)) for sid in ids}
    bad = {hex(s): v for s, v in res.items() if v[0] is None or v[0] != v[1] or
           v[1] not in banks[SND.SND_ROWS[s >> 16][1]]}
    check(not bad and len(acmd_ids) == 18,
          'every 3DS play_se id (%d) and converted ACMD Sound_Effect id (%d: heiho, whitebear, dekakuribo, patapata) '
          'names the same tone on the Wii U (its 3DS row registered: the id unchanged) as on the 3DS, a tone of its '
          'kind\'s bank %s' % (len([s for s in SND.SITES if isinstance(s[4], int) and s[4] >> 16]), len(acmd_ids), bad))
    tw_bad = []
    for trow, (krow, tname, tbank) in sorted(SND.TWIN_SND.items()):
        _n, bid, ttones = SND.bank_names(os.path.join(sedir, 'snd_se_enemy_%s.nus3bank' % tname))
        wb, wl = SND.labels(tw, trow)
        for lab, ti in enumerate(wl):
            ours = SND.tone_of((trow << 16) | lab, rowsw, banks)
            if bid != tbank or wb != tbank or ours is None or \
                    ours.lower().replace('snd_se_enemy_', '') != ttones[ti].lower().replace('snd_se_enemy_mczako', ''):
                tw_bad.append(hex((trow << 16) | lab))
    check(not tw_bad, 'the twins\' ids 0xBE2xxxx / 0xBE3xxxx / 0xBE4xxxx (Mczakoplasmawisp / darios / stalfos, banks '
          '5095-5097) name, on a Smash Run stage, the kind\'s tone of the same name (Mczakostarfos_Attack -> '
          'Starfos_Attack, ...) %s' % tw_bad)
    _r, jl = SND.labels(t3, 0)
    _r, wl0 = SND.labels(tw, 0)
    j3 = SND.bank_names(os.path.join(os.path.dirname(sys.argv[2]), '..', 'se', 'snd_se_joucyu.nus3bank'))[2] \
        if os.path.exists(os.path.join(os.path.dirname(sys.argv[2]), '..', 'se', 'snd_se_joucyu.nus3bank')) else None
    jw = SND.bank_names(os.path.join(sedir, 'snd_se_joucyu.nus3bank'))[2] \
        if os.path.exists(os.path.join(sedir, 'snd_se_joucyu.nus3bank')) else None
    if j3 and jw:
        check(j3[jl[15]] == jw[wl0[15]] == SND.COMMON[15],
              'the common id 15 (Ghos\'s immune hit) is %s in both games (row 0, snd_se_joucyu)' % jw[wl0[15]])

    # ==== 2. snd_rows on the real Wii U table, then the game's own lookups
    raw = open(sys.argv[3], 'rb').read()

    def table_machine():
        m = M(img)
        m.uc.mem_map(TBL, 0x40000)
        m.uc.mem_write(TBL + 0x100, raw)
        m.w32(W.SND_MGR, TBL)                    # [SND_MGR] -> mgr; [mgr] -> obj; [obj + 0x29C] -> holder
        m.w32(TBL, TBL + 0x20)
        m.w32(TBL + 0x20 + 0x29C, TBL + 0x60)
        m.w32(TBL + 0x60 + 4, TBL + 0x100)
        m.uc.mem_write(TBL + 0x60 + 8, b'\x01')
        return m

    def lookup(m, sid):
        holderp = TBL + 0x20 + 0x29C
        m.call(0x0311EDBC, {3: holderp, 4: sid})
        bank = m.uc.reg_read(R[3])
        m.call(0x0311EF88, {3: holderp, 4: sid})
        return bank, m.uc.reg_read(R[3])

    m = table_machine()
    before = {sid: lookup(m, sid) for sid in sorted(ids)}
    m.call(fn['snd_rows'], {3: 1})
    after = {sid: lookup(m, sid) for sid in sorted(ids)}
    bad = []
    for sid in sorted(ids):
        k, bank, _l = SND.SND_ROWS[sid >> 16]
        b, t = after[sid]
        if b != bank or t >= 0x80000000 or banks[bank][t] != res[sid][0] or before[sid][0] != 0xFFFFFFFF:
            bad.append((hex(sid), b, t))
    check(not bad, 'snd_rows (a Smash Run stage) on the Wii U table, then the game\'s 0x0311EDBC / 0x0311EF88: every '
          'id above gives its kind\'s bank id and the tone named as on the 3DS (none resolved before) %s' % bad[:4])
    tw_ids = [(trow << 16) | lab for trow in SND.TWIN_SND for lab in range(len(SND.labels(tw, trow)[1]))]
    got = {hex(s): lookup(m, s) for s in tw_ids}
    exp = {hex(s): (SND.SND_ROWS[SND.TWIN_SND[s >> 16][0]][1], SND.labels(tw, s >> 16)[1][s & 0xFFFF]) for s in tw_ids}
    m.call(fn['snd_rows'], {3: 0})
    back = {hex(s): lookup(m, s)[0] for s in tw_ids}
    check(got == exp and back == {hex(s): SND.TWIN_SND[s >> 16][2] for s in tw_ids} and
          lookup(m, 0x69B0002)[0] == 5012,
          'the twins\' rows on a Smash Run stage: bank 5019 / 5037 / 5052 (the kinds\'), the twins\' label lists; on '
          'any other enemy battle (r3 0) their own 5095-5097 back; the kinds\' rows stay %s' % (got == exp))
    m = table_machine()
    ro = TBL + 0x100 + 0x10 + 16 * 0x69B
    m.uc.mem_write(ro, struct.pack('<4I', 7777, 1, 0, 0))
    m.call(fn['snd_rows'], {3: 1})
    check(lookup(m, 0x69B0000)[0] == 7777 and lookup(m, 0x28D0002)[0] == 5002,
          'snd_rows leaves a row another bank already uses (the user\'s own table) alone, writes the others')
    m = table_machine()
    m.uc.mem_write(TBL + 0x60 + 8, b'\x00')
    m.call(fn['snd_rows'], {3: 1})
    check(lookup(m, 0x28D0002)[0] == 0xFFFFFFFF, 'snd_rows does nothing while the table is not loaded (+8 = 0)')

    # ==== 3. the hooked states / slots call play_se / stop_se as the 3DS
    def km(n, state=1, kind=None, walker=False):
        if byname[n].get('flier') and not walker:              # the fliers' machine (smashrun_flier_test.py: modules, items)
            m = FT.Machine(img)
            m.flier(cfgs[n], kind=byname[n]['kind'] if kind is None else kind, state=state, lr=-1.0)
            return m
        m = M(img)
        m.walker(cfgs[n], state=state, kind=byname[n]['kind'] if kind is None else kind)
        m.uc.mem_write(OBJ + W.FL_SIZE, bytes(0x40))
        return m

    bad = []
    for (n, sid), (snd, field) in sorted(W.SE_EN.items()):
        m = km(n, sid)
        st = byname[n]['states'][sid]
        m.call(fn[st[0]], {3: OBJ, 4: HEAP + 0x100})
        ok = sounds(m) == [('play', OBJ, snd, 0)] and st[0] == 'se_%s_%d' % (n, sid)
        if field:
            ok &= m.r32(OBJ + field) == 0x5E01
        if not ok:
            bad.append((n, sid, sounds(m)))
    check(not bad, 'the %d state enters with a 3DS play_se (Goomba 4 / 8, Shy Guy 6 / 7, Waddle Doo 11, Tiki Buzz 4 / '
          '5 / 10 / 11, Furiijio 2 / 4 / 5 / 7, Big Goomba 2 / 8 / 10 / 11, Spiny 5, Pooka 5 / 6 / 11): the enter, then '
          'play_se(id, false) once; the Doo\'s / Furiijio\'s beam handle kept (DO_SE / FU_SE) %s'
          % (len(W.SE_EN), bad))
    # Shy Guy 7 update: the second hop sounds, the landing after it (-> 8) does not
    out = []
    for v4 in (1, 2):
        m = km('heiho', 7)
        m.w32(OBJ + W.V(4), v4)
        m.ground, m.vy = True, 0.0
        m.call(fn['se_heiho_7u'], {3: OBJ, 4: HEAP + 0x100})
        out.append((sounds(m), m.r32(OBJ + W.V(4))))
    check(out == [([('play', OBJ, 0x69B0002, 0)], 2), ([], 2)],
          'Shy Guy 7 update (0x1BD54): landing with one hop done: the second hop and play_se(0x69B0002) (0x1BDD0); '
          'after two: -> 8, no sound %s' % out)
    # Churine 9: the powder effect's request plays 0x6B00001 (0x3DB28), the effect's wait does not
    m = km('churine', 9)
    m.ground = True
    m.w32(OBJ + W.V(5), 0)
    m.w32(OBJ + W.V(6), 100)
    m.call(fn['ch_pw_up'], {3: OBJ, 4: HEAP + 0x100})
    s1 = sounds(m)
    m.sounds = []
    m.exist = 1
    m.call(fn['ch_pw_up'], {3: OBJ, 4: HEAP + 0x100})
    check(s1 == [('play', OBJ, 0x6B00001, 0)] and sounds(m) == [] and
          [c for c in m.calls if c[0] == 'rate_last'],
          'Churine 9 (3DS 7 update): play_se(0x6B00001) with the powder effect (after set_rate_last, 0x3DB28), once %s'
          % s1)
    # Waddle Doo 11: the motion's end stops the beam (0x7DC18), the exit stops it if still playing (0x7DD18)
    m = km('waddledoo', 11)
    m.w32(OBJ + W.DO_SE, 0x5E07)
    m.w32(OBJ + W.DO_IX, 99)
    m.motion_end = True
    m.call(fn['do_bm_up'], {3: OBJ, 4: HEAP + 0x100})
    a1 = (sounds(m), m.r32(OBJ + W.DO_SE))
    m.sounds = []
    m.call(fn['se_doo_11x'], {3: OBJ})
    a2 = sounds(m)
    m.w32(OBJ + W.DO_SE, 0x5E08)
    m.call(fn['se_doo_11x'], {3: OBJ})
    check(a1 == ([('stop', OBJ, 0x5E07, 0)], 0xFFFFFFFF) and a2 == [] and sounds(m) == [('stop', OBJ, 0x5E08, 0)] and
          byname['waddledoo']['states'][11][2] == 'se_doo_11x',
          'Waddle Doo 11 (3DS 8): all shot and the motion\'s end: stop_se(+0x1A4), -1 (0x7DC18); its exit (0x7DD18) '
          'stops a handle still playing, not a stopped one %s %s' % (a1, a2))
    # Ghos
    m = km('ghos', 1)
    m.call(vslot('ghos', 41), {3: OBJ})
    g1 = (sounds(m), m.r32(OBJ + W.GH_SE))
    out = []
    for flag in (2, 0):
        m = km('ghos', 1)
        m.w32(OBJ + W.GH_SE, 0x5E33)
        m.w32(T.FLAGS, flag)
        m.call(vslot('ghos', 10), {3: OBJ})
        out.append((sounds(m), m.r32(OBJ + W.GH_SE)))
    m = km('ghos', 1)
    m.w32(OBJ + W.GH_SE, 0x5E34)
    m.call(vslot('ghos', 27), {3: OBJ})
    g3 = (sounds(m), m.r32(OBJ + W.GH_SE))
    check(g1 == ([('play', OBJ, 0x8A60000, 0)], 0x5E01) and
          out == [([('stop', OBJ, 0x5E33, 0)], 0xFFFFFFFF), ([], 0x5E33)] and
          g3 == ([('stop', OBJ, 0x5E34, 0)], 0xFFFFFFFF),
          'Ghos: start (0x10AA4) play_se(0x8A60000) -> GH_SE (3DS +0x200); slot 10 (3DS 11) stops it with the kinetic '
          'flag 2 only (0x110F4); slot 27 (3DS 28) stops it (0x11180) %s %s %s' % (g1, out, g3))
    imm = []
    for byte in (1, 0):
        m = km('ghos', 1)
        AD, HR = HEAP + 0x3B800, HEAP + 0x3B900
        m.uc.mem_write(AD, bytes(0x60))
        m.uc.mem_write(AD + 0x4C, bytes([byte]))
        m.uc.mem_write(HR, bytes(0x40))
        m.w32(HR + 0x14, AD)
        m.w32(HR + 0x20, HR + 0x40)             # the attacker record: category (+0x1C) 0, a fighter's own hit
        m.uc.mem_write(HR + 0x40, bytes(0x40))
        m.call(vslot('ghos', 31), {3: OBJ, 4: HR})
        imm.append(sounds(m))
    check(imm == [[('play', OBJ, 15, 0)], []],
          'Ghos slot 31 (0x113F0): an immune hit plays the common id 15 (snd_se_common_Hit_Muteki, 0x11454), a normal '
          'hit nothing %s' % imm)
    # Furiijio: the beam exits, slot 57 / 69
    m = km('furiijio', 4)
    m.w32(OBJ + W.FU_SE, 0x5E44)
    m.call(fn['se_fu_bexit'], {3: OBJ})
    f1 = (sounds(m), m.r32(OBJ + W.FU_SE))
    out = []
    for mk, ground, done in ((4, True, 0), (6, True, 0), (5, True, 0), (4, False, 0), (4, True, 1)):
        m = km('furiijio', 1)
        m.w32(T.MOTION + W.MOT_KIND, mk)
        m.ground = ground
        m.uc.mem_write(OBJ + W.FU_BND, bytes([done]))
        m.call(vslot('furiijio', 57), {3: OBJ})
        out.append((len(sounds(m)) and sounds(m)[0][2], m.uc.mem_read(OBJ + W.FU_BND, 1)[0]))
    m = km('furiijio', 1)
    m.uc.mem_write(OBJ + W.FU_BND, b'\x01')
    m.call(vslot('furiijio', 69), {3: OBJ})
    check(f1 == ([('stop', OBJ, 0x5E44, 0)], 0xFFFFFFFF) and byname['furiijio']['states'][7][2] == 'se_fu_bexit' and
          out == [(0x6A90003, 1), (0x6A90003, 1), (0, 0), (0, 0), (0, 1)] and
          m.uc.mem_read(OBJ + W.FU_BND, 1)[0] == 0 and m.uc.reg_read(R[3]) == 0,
          'Furiijio: 4 / 7 exits stop the beam\'s sound (0x6D0E0 / 0x6D4E0); slot 57 (0x6DBDC) plays 0x6A90003 once on '
          'the ground in DownBoundEnd (4) / DownWait (6); slot 69 clears the flag, returns 0 %s %s' % (f1, out))
    # Propeller Heiho: the loop, one per kind
    m = km('propellerheiho', 4)
    ph = D['ph_snd']
    m.w32(ph, 0xFFFFFFFF)
    m.w32(ph + 4, 0)
    m.call(vslot('propellerheiho', 41), {3: OBJ})
    first = (sounds(m), m.r32(ph), m.r32(ph + 4))
    m = km('propellerheiho', 4)                  # a second one (its own machine; the count is the kind's)
    m.w32(ph, first[1])
    m.w32(ph + 4, first[2])
    m.call(vslot('propellerheiho', 41), {3: OBJ})
    p1 = (first[0] + sounds(m), m.r32(ph), m.r32(ph + 4))
    m.sounds = []
    m.call(vslot('propellerheiho', 71), {3: OBJ})
    p2 = (sounds(m), m.r32(ph + 4))
    m.w32(OBJ + W.PH_F, 1)                       # state 2: the timer's last frame -> gone
    m.call(fn['se_ph2_up'], {3: OBJ, 4: HEAP + 0x100})
    p3 = (sounds(m), m.r32(ph), m.r32(ph + 4))
    check(p1 == ([('play', OBJ, 0x6D20000, 0)], 0x5E01, 2) and p2 == ([], 1) and
          p3 == ([('stop', OBJ, 0x5E01, 0)], 0xFFFFFFFF, 0) and
          [c[2] for c in m.calls if c[0] == 'chg'][-1:] == [8],
          'Propeller Heiho: start (0x990C8) plays the propeller loop only for the first of its kind (count 2 after two '
          'starts); death (slot 71) counts down; the last one gone (state 2, 0x99D0C) stops it %s %s %s' % (p1, p2, p3))
    m = km('propellerheiho', 4)
    m.w32(OBJ + 4, 4)
    m.w32(OBJ + W.PH_X, 0)
    m.w32(OBJ + W.PH_S, 1)
    m.call(vslot('propellerheiho', 55), {3: OBJ})
    s1 = sounds(m)
    m = km('propellerheiho', 4)
    m.w32(OBJ + 4, 4)
    m.w32(OBJ + W.PH_X, 0)
    m.w32(OBJ + W.PH_S, 5)
    m.call(vslot('propellerheiho', 55), {3: OBJ})
    check(s1 == [('play', OBJ, 0x6D20001, 0)] and sounds(m) == [],
          'Propeller Heiho slot 55 (0x99E24): the item swap plays 0x6D20001 (0x9A070), the countdown does not %s' % s1)
    # Pooka slot 10 (3DS 11)
    out = []
    for hp in (5.0, 90.0):
        m = km('pooka', 3, walker=True)
        m.wf(T.EN + 0, hp)                       # W+0 HP, +4 max HP (pk_thr)
        m.wf(T.EN + 4, 100.0)
        m.call(vslot('pooka', 10), {3: OBJ})
        out.append((sounds(m), [c[0] for c in m.calls if c[0] == 'notify_damage']))
    check(out[0] == ([('play', OBJ, 0x6B10004, 0)], ['notify_damage']) and out[1] == ([], ['notify_damage']),
          'Pooka slot 10 (3DS 11, 0x22900): HP at the threshold or below plays 0x6B10004 (0x22A44), then '
          'BehaviorImpl::notify_on_damage; above it only the latter %s' % out)

    # ==== 4. Stalfos 7 / 8 update: the game's calls, plus the 3DS's drop
    def srun(fnaddr, kind, res):
        m = M(img)
        m.stalfos = True
        m.res = dict(res)
        m.st_calls = []
        m.uc.mem_write(OBJ, bytes(0x240))
        m.w32(OBJ, ACC)
        m.w32(OBJ + 8, kind)
        m.w32(OBJ + 0xE0, VTB_CHG)
        m.w32(VTB_CHG + 0x24C, STUB_CHG)
        m.w32(VTB_CHG + 0x254, STUB_CHGI)
        m.uc.mem_write(STUB_CHG, b'\x4E\x80\x00\x20' * 2)
        m.uc.mem_write(PRM, bytes(0x200))
        m.w32(W.PARAM_MGR, PMGRX)
        m.w32(PMGRX + 0x1C4, PRM)
        m.wf(PRM + 0xC8, 2.0)
        m.w32(PRM + 0xE8, 0x41200000)
        m.wf(T.POSTURE + 0x10, 7.0)
        m.wf(T.POSTURE + 0x14, 50.0)
        for k, v in res.get('obj', {}).items():
            m.w32(OBJ + k, v)
        m.call(fnaddr, {3: OBJ, 4: HEAP + 0x100})
        return m.st_calls, m.r32(OBJ + 0x1D4)

    base = {'touch': 1}
    scen = [dict(base, touch=0), dict(base, obj={0x1C2: 0x01000000}, search=3),
            dict(base, obj={0x1C2: 0x01000000}, search=-1), dict(base, l5f7f8=1, out=-1), dict(base, l5f3a4=1),
            dict(base, l5f110=1), dict(base, l5f754=1), dict(base, wall=1, turn=1), dict(base, cliff=1, turn=0),
            dict(base, obj={0x188: 5, 0x180: 5}), dict(base), dict(base, passable=1, ty=0.0, ray=0),
            dict(base, passable=1, ty=45.0, ray=1)]
    drop = dict(base, passable=1, ty=0.0, ray=1)
    bad = []
    for sid in (7, 8):
        word, orig = W.ST_ROW_UP[sid]
        mine = img.u32(word)
        for sc in scen:
            a, _ = srun(mine, 0x30, sc)
            b, _ = srun(orig, 0x30, sc)
            strip = list(a)                       # the drop's own calls (sf_drop: passable, then nearest /
            if ('passable',) in strip:            # target_pos / ray while it holds) taken out
                i = strip.index(('passable',))
                j = i + 1
                while j < len(strip) and strip[j][0] in ('nearest', 'target_pos', 'ray') and j - i <= 3:
                    j += 1
                del strip[i:j]
            if strip != b:
                bad.append((sid, sc, a, b))
        a, d1d4 = srun(mine, 0x30, drop)
        tail = [c for c in a if c[0] in ('GND', 'PASS', 'set_correct', 'ST')]
        if tail != [('GND', 0), ('PASS', 1), ('set_correct', 0), ('ST', 1)] or d1d4 != 8 or \
                ('ray', (7.0, 40.0, 0.0, -100.0), 1) not in a:
            bad.append((sid, 'drop', a, d1d4))
        a, _ = srun(mine, 0x59, drop)
        b, _ = srun(orig, 0x59, drop)
        if a != b or img.u32(word) == orig:
            bad.append((sid, 'twin', a, b))
    check(not bad, 'Stalfos 7 / 8 update (mczakostalfos 0x102FE944 / 0x102FE95C -> sf7_up / sf8_up): for kind 0x30 '
          'the game\'s 0x026D3EB4 / 0x026D41E8 calls in every branch (%d cases), plus the 3DS\'s L5F470 drop (passable '
          'ground, the target below by more than P+0xC8 x 10, a floor under: ray from (x, y - 10) along (0, -100)): '
          'set_attach_ground(0), set_passable_check(1), set_correct(0), +0x1D4 = 8, -> 1; kind 0x59 the game\'s %s'
          % (len(scen), bad[:2]))
    print('%d failures' % len(T.FAILS))
    sys.exit(1 if T.FAILS else 0)


if __name__ == '__main__':
    main()
