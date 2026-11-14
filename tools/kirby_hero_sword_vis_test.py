#!/usr/bin/env python3
"""Kirby's Hero copy fix v5: the held sword on the stone, run end to end with the executable's own code (unicorn).

  python3 tools/kirby_hero_sword_vis_test.py NEW.rpx [OLD.rpx]        (exe_v46h; exe_v46g shows the failure)

What runs natively (every instruction from the executable; fighters/kirby/specials.md "Hero copy fix v5"):
- the held article's init 0x02B02078 (the joint and the link's constraint flags it picks by the copy kind) with the
  real LinkModule constraint setter (vt +0x314, 0x02C5B164); the link call 0x02B61FB8 itself is recorded (its joint);
- the held article's per-frame update 0x02B02534, frame after frame, through copy_held_cave.py's hook, the sword
  cave's stone check, its show / hide paths and the update's own motion checks, with the real VisibilityModule
  (weapon vtable 0x1010C55C: set 0x02C76EC0, is_visible 0x02C77004), the real LinkModule (vtable 0x10109900:
  set_attribute 0x02C5847C, is_attribute 0x02C5852C, the parent-visibility query 0x02C560C8 and their helpers
  0x02C55670 / 0x02C54FD0 / 0x0317C4B0 / 0x02C5B244) on a link 3 from the article to Kirby, and Kirby's own
  VisibilityModule (fighter vtable 0x1010C724) and LinkModule;
- whether the sword is drawn = the article VisibilityModule's is_visible (0x02C77004), as the game asks it.
Stubbed (Python, at addresses of their own): the battle-object lookup 0x02BF2108 (gives Kirby's handle), the
article's owner-id getter, Kirby's status / motion / work modules (status, motion kind, the sword int 0x1000008B, the
copy kind 0x100000A4), the article's work / motion modules, the link call 0x02B61FB8. Paired-single register saves
(opcode 4, `ps_merge` in the prologues / epilogues: unicorn has no Gekko / Espresso paired singles) are nops in the
emulated copy only.

Scenarios (each from a fresh article and link, attribute 7 off as made):
- the Hero copy (kind 0x2C): Kirby in the stone hold 0x175 (his VisibilityModule hidden, as his stone code sets it),
  no spell / a sword spell (int 0x1000008B = 1) for 40 frames / after it; the stone's end 0x176 (Kirby shown, int 0);
  a normal status. The sword must be drawn on every spell frame and on no other (exe_v46g: never);
- unchanged: the Marth copy's sword in its aerial motions 0x380 / 0x382 / 0x384 (Kirby visible) and in Shield Breaker
  0x1C1, hidden in a plain status; the Sonic copy's sphere (0x22) in the spin motions 0x318 / 0x319 / 0x31A with Kirby
  hidden, hidden in other motions with Kirby hidden;
- the init: kind 0x2C on joint 0x18 (LHaveN, where the sword model and the spells' hitboxes are) with flags 0x108
  (exe_v46g: joint 0x19 RHaveN, flags 8); Marth 0x12, Lucina 0x25, Ike 0x1D, Sonic 0x22, Shulk 0x2F as before.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kind_expand_test import Emu, REGS, STACK, RET  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_MSR, UC_PPC_REG_1, UC_PPC_REG_LR  # noqa: E402
import kirby_hero_sword_cave as C  # noqa: E402
from kirby_copy_new_test import Img  # noqa: E402

UPDATE, INIT = 0x02B02534, 0x02B02078
LINK_CALL = 0x02B61FB8
VIS_IS = 0x02C77004
VT_WEAPON_VIS, VT_FIGHTER_VIS, VT_LINK = 0x1010C55C, 0x1010C724, 0x10109900
LOOKUP = 0x02BF2108
SWORD_INT, COPY_KIND_INT, ART_KIND_INT = 0x1000008B, 0x100000A4, 0x10000007
PS_RANGES = ((0x02B01E00, 0x02B03100), (0x02C54000, 0x02C5C000), (0x02C76000, 0x02C78000), (0x0317C400, 0x0317C600),
             (0x02BEF000, 0x02BF0700))
fails = []


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        fails.append(what)
    return ok


class World:
    """an executable in unicorn with Kirby, his held article and the modules the update and the init touch"""

    def __init__(self, path):
        e = self.e = Emu(path)
        e.mu.reg_write(UC_PPC_REG_MSR, e.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
        for lo, hi in PS_RANGES:                    # paired-single saves -> nop (emulated copy only)
            for a in range(lo, hi, 4):
                if e.w(a) >> 26 == 4:
                    e.setw(a, 0x60000000)
        self.code = e.alloc(0x400, b'\0')           # stub functions
        self.ncode = 0
        self.state = dict(status=0x175, motion=0x2ED, sword=0, kind=0x2C, kirby_vis=0)
        self.links = []
        self.ints = {}
        st = self.state

        def fn(f):
            a = self.code + 4 * self.ncode
            self.ncode += 1
            e.stub(a, f)
            return a

        def vtable(entries):
            vt = e.alloc(0x400, b'\0')
            for off, f in entries.items():
                e.setw(vt + off, fn(f))
            return vt

        def module(vt, size=0x40):
            m = e.alloc(size, b'\0')
            e.setw(m, vt)
            return m

        # Kirby
        self.kacc = e.alloc(0x200, b'\0')
        kst = module(vtable({0x8C: lambda e_: st['status']}))
        kwk = module(vtable({0x84: lambda e_: {SWORD_INT: st['sword'], COPY_KIND_INT: st['kind']}.get(e_.r(4), 0)}))
        kmo = module(vtable({0x94: lambda e_: st['motion'], 0x2EC: lambda e_: None}))
        self.kvis = module(VT_FIGHTER_VIS, 0x20)
        e.setw(self.kvis + 4, self.kacc)
        self.plink = self.link_module(self.kacc)
        for off, m in ((0x20, kst), (0x28, kwk), (0x44, kmo), (0x68, self.plink), (0xA8, self.kvis)):
            e.setw(self.kacc + off, m)
        self.handle_rec = e.alloc(0x20, b'\0')
        e.setw(self.handle_rec + 0xC, self.kacc)
        # the article
        self.art = e.alloc(0x200, b'\0')
        awk = module(vtable({0x84: lambda e_: self.ints.get(e_.r(4), 0),
                             0x8C: lambda e_: self.ints.__setitem__(e_.r(5), e_.r(4))}))
        amo = module(vtable({0x2F4: lambda e_: None}))
        self.avis = module(VT_WEAPON_VIS, 0x20)
        e.setw(self.avis + 4, self.art)
        self.alink = self.link_module(self.art)
        for off, m in ((0x28, awk), (0x44, amo), (0x68, self.alink), (0xA8, self.avis)):
            e.setw(self.art + off, m)
        self.obj = e.alloc(0x40, b'\0')
        e.setw(self.obj + 0x24, vtable({0x254: lambda e_: 0x1234}))
        e.setw(self.obj + 0x28, self.art)
        self.setup = e.alloc(0x40, b'\0')           # the init's r5 (+0x20 read and passed on)
        e.stub(LOOKUP, lambda e_: e_.setw(e_.r(4), self.handle_rec))
        e.stub(LINK_CALL, lambda e_: self.links.append(e_.r(5)))
        self.reset()

    def link_module(self, acc):
        """a LinkModule as the game's (vtable, +4 its accessor, +0xC 4 links of 0x38, +0x10 / +0x1C lists of
        {first node, ., count}, +0x80 / +0x84 attribute masks, +0xAC constraint flags)"""
        e = self.e
        m = e.alloc(0xC0, b'\0')
        e.setw(m, VT_LINK)
        e.setw(m + 4, acc)
        e.setw(m + 0xC, e.alloc(4 * 0x38, b'\0'))
        return m

    def reset(self):
        """a fresh link 3 from the article to Kirby (its node at the link's +0x1C: node +0xC the link, +0x10 the
        parent's LinkModule), attribute 7 off, the article hidden, Kirby's LinkModule with no parent"""
        e = self.e
        for m in (self.alink, self.plink):
            for off in (0x10, 0x14, 0x18, 0x1C, 0x20, 0x24, 0x80, 0x84, 0xAC):
                e.setw(m + off, 0)
        link = e.w(self.alink + 0xC) + 3 * 0x38
        e.mu.mem_write(link, b'\0' * 0x38)
        e.setw(link + 0x1C, 0)                      # node: next
        e.setw(link + 0x28, link)                   # node +0xC: the link
        e.setw(link + 0x2C, self.plink)             # node +0x10: the parent's LinkModule
        e.setw(self.alink + 0x1C, link + 0x1C)      # the article's parent links: one
        e.setw(self.alink + 0x24, 1)
        e.setw(self.plink + 0x10, link + 0x1C)      # Kirby's child links: one
        e.setw(self.plink + 0x18, 1)
        e.mu.mem_write(self.avis + 8, b'\0\1')
        e.mu.mem_write(self.kvis + 8, b'\1\1')
        self.link = link

    def call(self, fn, *args):
        e = self.e
        for i, v in enumerate(args):
            e.mu.reg_write(REGS[3 + i], v & 0xFFFFFFFF)
        e.mu.reg_write(UC_PPC_REG_1, STACK + 0xF0000)
        e.mu.reg_write(UC_PPC_REG_LR, RET)
        e.mu.emu_start(fn, RET, count=20000)
        return e.r(3)

    def frame(self, **kw):
        """one frame: Kirby's state, the update; whether the game draws the sword (is_visible), the attribute"""
        self.state.update(kw)
        self.e.mu.mem_write(self.kvis + 8, bytes([1 if self.state['kirby_vis'] else 0]))
        self.ints[ART_KIND_INT] = self.state['kind']
        self.call(UPDATE, 0, self.obj)
        drawn = self.call(VIS_IS, self.avis) & 0xFF
        return drawn, (self.e.w(self.link + 0x30) >> 7) & 1, self.e.mu.mem_read(self.avis + 8, 1)[0]

    def init(self, kind):
        self.links = []
        self.state['kind'] = kind
        self.e.setw(self.alink + 0xAC, 0)
        self.call(INIT, 0, self.obj, self.setup)
        return (self.links[0] if self.links else None), self.e.w(self.alink + 0xAC) >> 16


def stone_spell(w):
    """the Hero copy's stone with a sword spell: [(label, drawn)] a frame"""
    w.reset()
    out = []
    for f in range(10):
        out.append(('stone, no spell', w.frame(status=0x175, motion=0x2ED, sword=0, kind=0x2C, kirby_vis=0)[0]))
    for f in range(40):
        out.append(('stone, sword spell', w.frame(status=0x175, motion=0x2ED, sword=1, kirby_vis=0)[0]))
    for f in range(10):
        out.append(('stone, after the spell', w.frame(status=0x175, motion=0x2ED, sword=0, kirby_vis=0)[0]))
    for f in range(5):
        out.append(('stone end 0x176', w.frame(status=0x176, motion=0x2E9, sword=0, kirby_vis=1)[0]))
    for f in range(5):
        out.append(('wait', w.frame(status=0, motion=0, sword=0, kirby_vis=1)[0]))
    return out


def run(path, expect_fixed):
    w = World(path)
    name = os.path.basename(path)
    seq = stone_spell(w)
    want = [1 if lab == 'stone, sword spell' else 0 for lab, _d in seq]
    got = [d for _lab, d in seq]
    if expect_fixed:
        check('%s: the stone sword spell end to end: the sword drawn on its 40 frames and on no other (no spell, after '
              'it, the stone\'s end, a normal status)' % name, got, want)
        check('%s: link 3\'s attribute 7 (the parent\'s visibility) back on after the spell' % name,
              (w.e.w(w.link + 0x30) >> 7) & 1, 1)
    else:
        check('%s: the failure reproduced: the sword never drawn in the stone, spell or not (Kirby hidden, attribute 7 '
              'set again by the update every frame)' % name, got, [0] * len(seq))
        w.reset()
        d, attr, own = w.frame(status=0x175, motion=0x2ED, sword=1, kind=0x2C, kirby_vis=0)
        check('%s: on a spell frame its own flag is set (v6\'s stone path ran) but attribute 7 is on and Kirby hidden'
              % name, (d, attr, own), (0, 1, 1))
    # unchanged paths
    bad = []
    for mot in (0x380, 0x382, 0x384):
        w.reset()
        d = w.frame(status=0x2B, motion=mot, sword=0, kind=0x12, kirby_vis=1)[0]
        if d != 1:
            bad.append(('marth aerial', hex(mot), d))
    w.reset()
    if w.frame(status=0x1C1, motion=0x37F, sword=0, kind=0x12, kirby_vis=1)[0] != 1:
        bad.append('marth shield breaker')
    if w.frame(status=0, motion=0, sword=0, kind=0x12, kirby_vis=1)[0] != 0:
        bad.append('marth wait shown')
    for mot in (0x318, 0x319, 0x31A):
        w.reset()
        d = w.frame(status=0x20B, motion=mot, sword=0, kind=0x22, kirby_vis=0)[0]
        if d != 1:
            bad.append(('sonic spin', hex(mot), d))
    w.reset()
    if w.frame(status=0x20B, motion=0x316, sword=0, kind=0x22, kirby_vis=0)[0] != 0:
        bad.append('sonic start shown with Kirby hidden')
    w.reset()
    if w.frame(status=0x175, motion=0x2ED, sword=1, kind=0x12, kirby_vis=0)[0] != 0:
        bad.append('another copy\'s held model shown on the stone')
    check('%s: unchanged: the Marth sword in its aerials / Shield Breaker and hidden in Wait; the Sonic sphere in the '
          'spin motions with Kirby hidden, hidden in its start; another copy\'s held model (Marth\'s) never shown on the '
          'stone, int 0x1000008B 1 or not' % name, bad, [])
    # the init's joint and link flags
    got = {hex(k): w.init(k) for k in (0x2C, 0x12, 0x25, 0x1D, 0x22, 0x2F)}
    want = {'0x2c': (0x18, 0x108) if expect_fixed else (0x19, 8), '0x12': (0x18, 0x108), '0x25': (0x18, 0x108),
            '0x1d': (0x19, 0x108), '0x22': (0x3E8, 0x108), '0x2f': (0x1A, 0x108)}
    check('%s: the held article\'s init: joint / link flags per copy kind (the Hero copy\'s 0x2C %s)'
          % (name, 'on LHaveN 0x18 as Marth\'s' if expect_fixed else 'on RHaveN 0x19, flags 8: the failure'), got, want)
    check('%s: the init stores the copy kind in the article\'s int 0x10000007' % name, w.ints.get(ART_KIND_INT), 0x2F)


def main():
    new = sys.argv[1]
    old = sys.argv[2] if len(sys.argv) > 2 else None
    _a, out = C.build()
    img = Img(new)
    check('%s: every word of kirby_hero_sword_cave.py (fix v5 included) in place' % os.path.basename(new),
          [hex(k) for k, v in sorted(out.items()) if img.w(k) != v], [])
    run(new, True)
    if old:
        run(old, False)
    print('%d failures' % len(fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
