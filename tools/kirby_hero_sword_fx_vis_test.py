#!/usr/bin/env python3
"""Kirby's Hero copy fix v8: why the sword spells' blade effects never showed, and the fix, run with the executable's
own code (unicorn).

  python3 tools/kirby_hero_sword_fx_vis_test.py EXE.rpx            (exe_v46i)

The chain (read in the executable; fighters/kirby/specials.md "Hero copy fix v8", docs/native-notes.md):
- Every frame an object's VisibilityModule update (0x02C76F70, from the object updates, e.g. 0x02B94164) asks its
  is_visible (vt +0xA4: the fighter's 0x02C77004, its own flag +8) and hands it to the EffectModule's vt +0x34C
  (0x02C317A4): when the EffectModule's byte +0x9B is set ("the effects follow the model's visibility", set to 1 by
  the module's reset at 0x02C28528), that calls its set_visible vt +0x17C (0x02C2C178): byte +0x9A = the value and, on a
  change, every effect of the module shown / hidden through the effect manager (0x0334CA64).
- A following effect (EFFECT_FOLLOW / External_Graphic / MSC EffectModule 0x2712: vt +0x64, 0x02C2AF98) made while
  +0x9A is 0 is hidden at once (0x02C2B4A8: 0x0334CA4C(handle, 0)); a one-shot effect (Graphic_Effect / 0x2710: vt
  +0x4C / +0x54) isn't checked there. Kirby is hidden for the whole stone (his MSC's VisibilityModule(0x2710, 0)), so
  his blade effects (fire / ice / dark blade, following his LHaveN) were made hidden, while the one-shot speed lines
  and bursts showed (the user's fix v6 clip) and the trail (not a module effect) too.
- The MSC's EffectModule handler (0x02C2CEC8) has both switches: op 0x26 (value) sets +0x9B (vt +0x21C), op 0x1C
  (value) is set_visible (vt +0x17C). Fix v8's khm_sword: EffectModule(0x26, 0) and EffectModule(0x1C, 1) every frame
  of a sword spell, EffectModule(0x26, 1) at its end (khm_sw_stop): the game's own sync hides them again.

Run here (natively; stubbed: the effect manager's all-effects switch 0x0334CA64 and per-effect one 0x0334CA4C, the
ModelModule's draw switch, the LinkModule's parent query): Kirby hidden, the module as reset -> his effects hidden
by the update; the MSC ops 0x26 0 / 0x1C 1 -> shown, and the update leaves them shown; a following effect's creation
check (0x02C2B4A8-0x02C2B4C4, run) hides it with +0x9A 0 and not with 1; op 0x26 1 -> the next update hides them
again. Statically: the one-shot request path (0x02C2A040, 400 instructions) never reads +0x9A.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kind_expand_test import Emu, REGS, STACK  # noqa: E402
from unicorn.ppc_const import UC_PPC_REG_MSR, UC_PPC_REG_1  # noqa: E402

VIS_UPDATE = 0x02C76F70
EFF_MSC = 0x02C2CEC8
VT_EFFECT, VT_FIGHTER_VIS = 0x10105FE8, 0x1010C724
ALL_SWITCH, ONE_SWITCH = 0x0334CA64, 0x0334CA4C
CREATE_CHECK, CREATE_CHECK_END = 0x02C2B4A8, 0x02C2B4C8
ONE_SHOT = 0x02C2A040
PS_RANGES = ((0x02C27000, 0x02C33000), (0x02C76000, 0x02C78000))
FAIL = []


def check(what, got, want):
    ok = got == want
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': got %r, want %r' % (got, want)))
    if not ok:
        FAIL.append(what)


class Kirby:
    def __init__(self, path):
        e = self.e = Emu(path)
        e.mu.reg_write(UC_PPC_REG_MSR, e.mu.reg_read(UC_PPC_REG_MSR) | 0x2000)
        for lo, hi in PS_RANGES:
            for a in range(lo, hi, 4):
                if e.w(a) >> 26 == 4:
                    e.setw(a, 0x60000000)
        self.code = e.alloc(0x200, b'\0')
        self.ncode = 0
        self.switches, self.one = [], []
        e.stub(ALL_SWITCH, lambda e_: self.switches.append(e_.r(5)))       # (group, mask, value, 0)
        e.stub(ONE_SWITCH, lambda e_: self.one.append((e_.r(3), e_.r(4))))
        self.acc = e.alloc(0x200, b'\0')
        self.eff = e.alloc(0x100, b'\0')                # the EffectModule: its fields the switches touch
        e.setw(self.eff, VT_EFFECT)
        e.setw(self.eff + 4, self.acc)
        e.setw(self.eff + 0x10, 0x00010000)            # its effect group
        self.vis = e.alloc(0x20, b'\0')
        e.setw(self.vis, VT_FIGHTER_VIS)
        e.setw(self.vis + 4, self.acc)
        model = e.alloc(0x20, b'\0')
        e.setw(model, self.vtable({0x164: lambda e_: None}))
        link = e.alloc(0x20, b'\0')
        e.setw(link, self.vtable({0xDC: lambda e_: 1}))
        for off, m in ((0xA0, self.eff), (0xA8, self.vis), (0x3C, model), (0x68, link)):
            e.setw(self.acc + off, m)
        self.args = e.alloc(0x40, b'\0')
        self.words = e.alloc(0x40, b'\0')

    def vtable(self, entries):
        e = self.e
        vt = e.alloc(0x400, b'\0')
        for off, f in entries.items():
            a = self.code + 4 * self.ncode
            self.ncode += 1
            e.stub(a, f)
            e.setw(vt + off, a)
        return vt

    def byte(self, a):
        return bytes(self.e.mu.mem_read(a, 1))[0]

    def setbyte(self, a, v):
        self.e.mu.mem_write(a, bytes([v]))

    def reset(self, kirby_visible):
        self.setbyte(self.eff + 0x9A, 1)                # 0x02C2826C / 0x02C28528: visible, follows the model
        self.setbyte(self.eff + 0x9B, 1)
        self.setbyte(self.vis + 8, kirby_visible)
        self.setbyte(self.vis + 9, 1)
        self.switches.clear()
        self.one.clear()

    def update(self):
        self.e.call(VIS_UPDATE, self.vis)

    def msc(self, *words):
        e = self.e
        for i, w in enumerate(words):
            e.setw(self.words + 4 * i, w)
        e.setw(self.args, self.words)
        e.setw(self.args + 4, len(words))
        return e.call(EFF_MSC, self.eff, self.args)

    def create_check(self, handle=0x4321, flags=0x0001C000):
        """the following request's tail after the effect is made (r27 the module, its +0x14 the new handle, r30
        the request's flags: 0x8000 | 0x4000 Terminate | 0x10000)"""
        e = self.e
        e.setw(self.eff + 0x14, handle)
        e.mu.reg_write(UC_PPC_REG_1, STACK + 0xF0000)
        e.mu.reg_write(REGS[27], self.eff)
        e.mu.reg_write(REGS[30], flags)
        e.mu.emu_start(CREATE_CHECK, CREATE_CHECK_END, count=1000)


def main():
    path = sys.argv[1]
    k = Kirby(path)
    # Kirby hidden (the stone), the module as the game resets it
    k.reset(kirby_visible=0)
    k.update()
    check('Kirby hidden, EffectModule +0x9B 1 (the reset\'s): the visibility update hides all his effects (+0x9A 0, '
          'the manager\'s switch with 0)', (k.byte(k.eff + 0x9A), list(k.switches)), (0, [0]))
    k.one.clear()
    k.create_check()
    check('a following effect made now (External_Graphic / EffectModule 0x2712) is hidden at once (0x0334CA4C(h, 0))',
          k.one, [(0x4321, 0)])
    k.update()
    check('the next updates switch nothing more (no change)', list(k.switches), [0])
    # fix v8: the MSC switches
    k.msc(0x26, 0)
    check('MSC EffectModule(0x26, 0): +0x9B 0 (vt +0x21C)', k.byte(k.eff + 0x9B), 0)
    k.msc(0x1C, 1)
    check('MSC EffectModule(0x1C, 1): set_visible: +0x9A 1, all his effects shown', (k.byte(k.eff + 0x9A),
                                                                                   list(k.switches)), (1, [0, 1]))
    for _ in range(3):
        k.update()
    check('with +0x9B 0 the updates (Kirby still hidden) leave them shown', (k.byte(k.eff + 0x9A),
                                                                             list(k.switches)), (1, [0, 1]))
    k.one.clear()
    k.create_check()
    check('a following effect made now is left shown', k.one, [])
    # the spell's end: khm_sw_stop
    k.msc(0x26, 1)
    k.update()
    check('MSC EffectModule(0x26, 1) at the spell\'s end: the next update hides them again (the game\'s own sync)',
          (k.byte(k.eff + 0x9B), k.byte(k.eff + 0x9A), list(k.switches)), (1, 0, [0, 1, 0]))
    # Kirby visible: nothing hidden (the ops change nothing for a shown Kirby)
    k.reset(kirby_visible=1)
    k.update()
    check('Kirby visible: his effects stay shown', (k.byte(k.eff + 0x9A), k.switches), (1, []))
    # statically: the one-shot request path doesn't read +0x9A
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
    code = bytes(k.e.mu.mem_read(ONE_SHOT, 400 * 4))
    reads = [hex(i.address) for i in md.disasm(code, ONE_SHOT) if i.mnemonic == 'lbz' and i.op_str.endswith('0x9a(r27)')
             or (i.mnemonic == 'lbz' and '0x9a(' in i.op_str)]
    check('the one-shot request (vt +0x54, 0x02C2A040) never reads +0x9A (why the speed lines / bursts showed)', reads, [])
    print('%d failures' % len(FAIL))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
