#!/usr/bin/env python3
"""Checks smash_button_cave.py in a patched RPX, in unicorn.

  python3 tools/smash_button_test.py PATCHED.rpx ORIGINAL.rpx

- the original words are the expected ones, the patched the cave's;
- smash button: before each A+B flag getter, a smash bit (0x20) in the action bits gets attack (0x1);
- stick smash off: on an attack press without the smash bit, the frame's stick is limited to
  XRATIO / YRATIO of the game's stick scale D (fixed XMAX / YMAX without one), only for the pad
  types with their record bit set, only on the press;
- the `stick_smash` property (get / set per object), its load from and save to the record's bit,
  and the bind stub (the class's own bind, then the two new members);
- the Tap Jump getters (bit 0) and load_* clearing the Tap Jump byte's other bits.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import smash_button_cave as C  # noqa: E402
from ppcasm import Asm  # noqa: E402
from stage_slot_test import machine, RET  # noqa: E402
from unicorn.ppc_const import (UC_PPC_REG_1, UC_PPC_REG_3, UC_PPC_REG_4, UC_PPC_REG_5, UC_PPC_REG_6,  # noqa: E402
                               UC_PPC_REG_27, UC_PPC_REG_29, UC_PPC_REG_31, UC_PPC_REG_LR, UC_PPC_REG_MSR)

fails = 0
MEM = 0x7F000000                # test memory (0x10000)


def check(what, got, want):
    global fails
    ok = got == want
    fails += not ok
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', what, '' if ok else ': %r (want %r)' % (got, want)))


def r32(mu, a):
    return struct.unpack('>I', mu.mem_read(a, 4))[0]


def code(base, text):
    a = Asm(base)
    a.asm(text)
    return b''.join(struct.pack('>I', w) for w in a.words())


def main():
    patched, original = sys.argv[1:3]
    a, patches = C.build()
    om, mu = machine(original), machine(patched)
    mu.reg_write(UC_PPC_REG_MSR, mu.reg_read(UC_PPC_REG_MSR) | 0x2000)     # FP on (the stick scale)
    check('original words', {k: r32(om, k) for k in C.ORIGINAL}, C.ORIGINAL)
    check('patched words', all(r32(mu, k) == v for k, v in patches.items()), True)

    def run(fn, regs):
        for r, v in regs.items():
            mu.reg_write(r, v)
        mu.reg_write(UC_PPC_REG_1, MEM + 0xF000)
        mu.reg_write(UC_PPC_REG_LR, RET)
        mu.emu_start(fn, RET, count=5000)

    # smash button: the getters return 7 (stubs)
    for _site, getter, _r in C.AB_CALLS:
        mu.mem_write(getter, code(getter, 'li r3, 7\nblr'))
    for i, (_site, _g, acc) in enumerate(C.AB_CALLS):
        reg = UC_PPC_REG_27 if acc == 'r27' else UC_PPC_REG_29
        run(a.addr('ab%d' % i), {reg: 0x20, UC_PPC_REG_3: 0})
        check('ab%d: smash bit + attack, getter result kept' % i, (mu.reg_read(reg), mu.reg_read(UC_PPC_REG_3)), (0x21, 7))
        run(a.addr('ab%d' % i), {reg: 0x0A, UC_PPC_REG_3: 0})
        check('ab%d: no smash bit: unchanged' % i, mu.reg_read(reg), 0x0A)

    # stick smash off: dispatcher stub (does nothing), a pad whose state has type at +0x7C
    mu.mem_write(C.DISPATCH, code(C.DISPATCH, 'blr'))
    pad, vt, state, cfg, frame = MEM + 0x100, MEM + 0x200, MEM + 0x300, MEM + 0x1000, MEM + 0x3000
    mu.mem_write(MEM + 0x400, code(MEM + 0x400, 'lis r3, %d\nori r3, r3, %d\nblr' % (state >> 16, state & 0xFFFF)))
    mu.mem_write(pad + 4, struct.pack('>I', vt))
    mu.mem_write(vt + 0x1C, struct.pack('>I', MEM + 0x400))
    port = 2
    rec_flags = cfg + port * 0x3C + 0x3B
    prev = cfg + 0x1E0 + port * 9 + 2

    def frame_run(typ, flags, bits, x, y, prev_attack):
        mu.mem_write(state + 0x7C, struct.pack('>I', typ))
        mu.mem_write(rec_flags, bytes([flags]))
        mu.mem_write(prev, bytes([prev_attack]))
        mu.mem_write(frame, struct.pack('>Hbb', bits, x, y))
        run(a.addr('wrap'), {UC_PPC_REG_3: cfg, UC_PPC_REG_4: port, UC_PPC_REG_5: frame, UC_PPC_REG_6: pad,
                             UC_PPC_REG_31: 0x31313131})
        b, fx, fy = struct.unpack('>Hbb', mu.mem_read(frame, 4))
        return b, fx, fy, mu.mem_read(prev, 1)[0], mu.reg_read(UC_PPC_REG_31)
    X, Y = C.XMAX, C.YMAX
    check('GC, off, attack press, stick up-right', frame_run(7, 0x04, 0x1, 127, 127, 0), (0x1, X, Y, 1, 0x31313131))
    check('GC, off, attack press, stick down-left', frame_run(7, 0x04, 0x1, -127, -127, 0), (0x1, -X, -Y, 1, 0x31313131))
    check('GC, off, attack press, tilt range kept', frame_run(7, 0x04, 0x1, 60, -40, 0), (0x1, 60, -40, 1, 0x31313131))
    check('GC, off, attack held (no press): stick kept', frame_run(7, 0x04, 0x1, 127, 0, 1), (0x1, 127, 0, 1, 0x31313131))
    check('GC, off, smash bit: stick kept', frame_run(7, 0x04, 0x21, 127, 0, 0), (0x21, 127, 0, 1, 0x31313131))
    check('GC, off, no attack: prev cleared', frame_run(7, 0x04, 0x2, 127, 0, 1), (0x2, 127, 0, 0, 0x31313131))
    check('GC, on: stick kept', frame_run(7, 0x00, 0x1, 127, 127, 0), (0x1, 127, 127, 1, 0x31313131))
    check('GC, another type\'s bit: stick kept', frame_run(7, 0x0B, 0x1, 127, 127, 0), (0x1, 127, 127, 1, 0x31313131))
    check('STANDARD (type 5), off', frame_run(5, 0x01, 0x1, 127, -127, 0), (0x1, X, -Y, 1, 0x31313131))
    check('CTR (type 9), off', frame_run(9, 0x08, 0x1, -127, 127, 0), (0x1, -X, Y, 1, 0x31313131))
    check('FREE_STYLE (type 4), off', frame_run(4, 0x02, 0x1, 127, 127, 0), (0x1, X, Y, 1, 0x31313131))
    check('REMOTE (type 3): nothing, state kept', frame_run(3, 0x0F, 0x1, 127, 127, 0), (0x1, 127, 127, 0, 0x31313131))

    # the limits from the stick scale D ([STICK_SCALE] -> float): stick = byte / D in the game
    SC = MEM + 0x7800
    for d in (127.0, 105.0, 100.0, 80.0, 64.0):
        mu.mem_write(C.STICK_SCALE, struct.pack('>I', SC))
        mu.mem_write(SC, struct.pack('>f', d))
        b, fx, fy, _p, _k = frame_run(5, 0x01, 0x1, 127, -127, 0)
        check('D %.0f: limits (%d, %d) = %.3f / %.3f of full: under the smash thresholds 0.83 / 0.66, '
              'over the tilt one 0.25' % (d, fx, -fy, fx / d, -fy / d),
              (0.25 < fx / d < 0.83, 0.25 < -fy / d < 0.66, fx == int(d * C.XRATIO), -fy == int(d * C.YRATIO)),
              (True, True, True, True))
        check('D %.0f: a stick under the limits kept' % d, frame_run(5, 0x01, 0x1, 20, 15, 0)[1:3], (20, 15))
    for d in (30.0, 250.0):
        mu.mem_write(SC, struct.pack('>f', d))
        check('D %.0f (out of range): the fixed limits' % d, frame_run(5, 0x01, 0x1, 127, 127, 0)[1:3], (X, Y))
    mu.mem_write(C.STICK_SCALE, struct.pack('>I', 0))
    check('no stick scale: the fixed limits', frame_run(5, 0x01, 0x1, -127, 127, 0)[1:3], (-X, Y))

    # Tap Jump getters: accessor word 0 -> the record
    ACC0, TREC = MEM + 0x7400, MEM + 0x7500
    mu.mem_write(ACC0, struct.pack('>I', TREC))
    for name, (off, getter) in C.TAP.items():
        got = []
        for v in range(4):
            mu.mem_write(TREC + off, bytes([v]))
            run(getter, {UC_PPC_REG_3: ACC0})
            got.append(mu.reg_read(UC_PPC_REG_3))
        check('%s Tap Jump getter: bit 0' % name, got, [0, 1, 0, 1])

    # stick_smash property: call frame r3: +0x10 type tag, +0x14 value, +0x18 the argument
    fr = MEM + 0x5000

    def prop(fn, key, arg=None, tag=7):
        mu.mem_write(fr, struct.pack('>IIIII', 0, 0, 0, 0, tag))
        mu.mem_write(fr + 0x14, struct.pack('>I', key))
        if arg is not None:
            mu.mem_write(fr + 0x18, struct.pack('>I', arg))
        run(a.addr(fn), {UC_PPC_REG_3: fr})
        return struct.unpack('>II', mu.mem_read(fr, 8))
    P = MEM + 0x6000
    check('get, unknown object: true (on)', prop('get', P + 0x0E), (3, 0))
    check('set false', prop('set', P + 0x0E, 2), (2, 0))
    check('get after set false', prop('get', P + 0x0E), (2, 0))
    check('another object still on', prop('get', P + 0x1C), (3, 0))
    check('set true', prop('set', P + 0x0E, 3), (3, 0))
    check('get after set true', prop('get', P + 0x0E), (3, 0))
    mu.mem_write(P + 0x100 + 0x18, struct.pack('>I', P + 0x1C))     # a userdata object (tag 0x10) -> its data
    check('set via a userdata this', prop('set', P + 0x100, 2, tag=0x10), (2, 0))
    check('get the same data directly', prop('get', P + 0x1C), (2, 0))
    for k in range(20):                                             # fill the table (round robin)
        prop('set', MEM + 0x8000 + 4 * k, 2)
    check('20 objects later, the latest kept', prop('get', MEM + 0x8000 + 4 * 19), (2, 0))

    # load / save: accessor at ACC (+0 / +4 the flags record), getter / setter stubs
    ACC, REC = MEM + 0x7000, MEM + 0x7100
    for name, off, word, bit, _lc, getter, _sc, setter, _bc in C.MENU:
        # the getters are the A+B getters stubbed above (li r3, 7; unicorn keeps translated code)
        mu.mem_write(setter, code(setter, 'mr r5, r4\nblr'))
        mu.mem_write(ACC, struct.pack('>II', REC if word == 0 else TREC, 0))
        mu.mem_write(ACC + word, struct.pack('>I', REC))
        tap = (REC if word == 0 else TREC) + C.TAP[name][0]
        for flags in (bit | 0x40, 0xF0 & ~bit):
            mu.mem_write(REC + 0xD, bytes([flags]))
            tj = 3 if flags & bit else 2
            mu.mem_write(tap, bytes([tj]))
            run(a.addr('load_' + name), {UC_PPC_REG_3: ACC, UC_PPC_REG_31: P})
            check('load_%s: Tap Jump byte %d -> bit 0' % (name, tj), mu.mem_read(tap, 1)[0], tj & 1)
            check('load_%s flags 0x%02X: getter result' % (name, flags), mu.reg_read(UC_PPC_REG_3), 7)
            check('load_%s flags 0x%02X: property' % (name, flags), prop('get', P + off), (2 if flags & bit else 3, 0))
        for on, base in ((False, 0x40), (True, 0x4F)):
            prop('set', P + off, 3 if on else 2)
            mu.mem_write(REC + 0xD, bytes([base]))
            run(a.addr('save_' + name), {UC_PPC_REG_3: ACC, UC_PPC_REG_4: 0x55, UC_PPC_REG_31: P})
            want = (base & ~bit) | (0 if on else bit)
            check('save_%s %s: flags byte' % (name, 'on' if on else 'off'), mu.mem_read(REC + 0xD, 1)[0], want)
            check('save_%s: setter gets r4' % name, mu.reg_read(UC_PPC_REG_5), 0x55)

    # bind stubs: BIND logs (r3, r4, r5) at LOG
    LOG = MEM + 0x9000
    mu.mem_write(C.BIND, code(C.BIND, '''
        lis r12, %d
        ori r12, r12, %d
        lwz r11, 0(r12)
        add r11, r11, r12
        stw r3, 4(r11)
        stw r4, 8(r11)
        stw r5, 12(r11)
        lwz r11, 0(r12)
        addi r11, r11, 12
        stw r11, 0(r12)
        blr''' % (LOG >> 16, LOG & 0xFFFF)))
    for name in ('ctr', 'gc', 'standard'):
        mu.mem_write(LOG, b'\0' * 0x40)
        run(a.addr('bind_' + name), {UC_PPC_REG_3: 0x1111, UC_PPC_REG_4: 0x2222, UC_PPC_REG_5: 0x3333,
                                     UC_PPC_REG_31: 0xC1A55})
        calls = [struct.unpack('>III', mu.mem_read(LOG + 4 + 12 * i, 12)) for i in range(3)]

        def s(p):
            return bytes(mu.mem_read(p, 32)).split(b'\0')[0].decode()
        check('bind_%s: own bind first' % name, calls[0], (0x1111, 0x2222, 0x3333))
        check('bind_%s: getter' % name, (calls[1][0], s(calls[1][1]), r32(mu, calls[1][2]), r32(mu, calls[1][2] + 4)),
              (0xC1A55, 'stick_smash', a.addr('get'), C.DESC_TYPES[name][0]))
        check('bind_%s: setter' % name, (calls[2][0], s(calls[2][1]), r32(mu, calls[2][2]), r32(mu, calls[2][2] + 4)),
              (0xC1A55, 'set_stick_smash', a.addr('set'), C.DESC_TYPES[name][1]))
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
