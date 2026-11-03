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
- the Tap Jump getters (bit 0) and load_* clearing the Tap Jump byte's other bits (STANDARD: bits 1-6 kept,
  the stick clicks' codes);
- stick clicks (STANDARD): a click's action bits into the frame, an attack / special press zeroing the frame's
  stick (not while held, not for other actions, not for other pad types); the `stick_l_push` / `stick_r_push`
  properties (ops, 14 = not set), loaded from / saved to the Tap Jump byte's bits 1-3 / 4-6.
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
                               UC_PPC_REG_26, UC_PPC_REG_27, UC_PPC_REG_29, UC_PPC_REG_31, UC_PPC_REG_LR, UC_PPC_REG_MSR)

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

    tapb = cfg + port * 0x3C + C.STD_TAP
    held = a.addr('click_held') + port

    def frame_run(typ, flags, bits, x, y, prev_attack, buttons=0, tap=0, was=0, full=False):
        mu.mem_write(state, struct.pack('>I', buttons))
        mu.mem_write(tapb, bytes([tap]))
        mu.mem_write(held, bytes([was]))
        mu.mem_write(state + 0x7C, struct.pack('>I', typ))
        mu.mem_write(rec_flags, bytes([flags]))
        mu.mem_write(prev, bytes([prev_attack]))
        mu.mem_write(frame, struct.pack('>Hbb', bits, x, y))
        run(a.addr('wrap'), {UC_PPC_REG_3: cfg, UC_PPC_REG_4: port, UC_PPC_REG_5: frame, UC_PPC_REG_6: pad,
                             UC_PPC_REG_31: 0x31313131, UC_PPC_REG_26: 0x26262626, UC_PPC_REG_27: 0x27272727})
        b, fx, fy = struct.unpack('>Hbb', mu.mem_read(frame, 4))
        if full:
            return b, fx, fy, mu.mem_read(held, 1)[0], mu.reg_read(UC_PPC_REG_26), mu.reg_read(UC_PPC_REG_27)
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

    # stick clicks (STANDARD types 2 / 5 / 6 / 8): L 0x00800000, R 0x10000000; codes in the Tap Jump byte
    L, R = C.CLICK_BITS
    K = (0x26262626, 0x27272727)

    def tapv(lc=0, rc=0, tj=1):
        return tj | lc << 1 | rc << 4
    check('L attack press: attack + 0x200, stick neutral', frame_run(5, 0, 0, 100, 50, 0, L, tapv(1), 0, True),
          (0x0201, 0, 0, 1) + K)
    check('L attack held: the bits, stick kept', frame_run(5, 0, 0, 100, 50, 1, L, tapv(1), 1, True), (0x0201, 100, 50, 1) + K)
    check('R special press: special + 0x800, stick neutral', frame_run(2, 0, 0, -127, 127, 0, R, tapv(0, 2), 0, True),
          (0x0802, 0, 0, 2) + K)
    check('R jump: jump bit, stick kept', frame_run(6, 0, 0, 90, 90, 0, R, tapv(0, 3), 0, True), (0x0004, 90, 90, 2) + K)
    check('L shield', frame_run(8, 0, 0, 10, 0, 0, L, tapv(4), 0, True)[:3], (0x0008, 10, 0))
    check('L grab', frame_run(5, 0, 0, 10, 0, 0, L, tapv(5), 0, True)[:3], (0x0018, 10, 0))
    check('R smash: smash + attack, stick kept (its direction)', frame_run(5, 0, 0, 0, -127, 0, R, tapv(0, 6), 0, True)[:3],
          (0x0021, 0, -127))
    check('not set (code 0): nothing', frame_run(5, 0, 0x4, 50, 50, 0, L | R, tapv(0, 0), 0, True), (0x4, 50, 50, 3) + K)
    check('code 7 (unused): nothing', frame_run(5, 0, 0, 50, 50, 0, L, tapv(7), 0, True)[:3], (0, 50, 50))
    check('both: L attack held, R special pressed', frame_run(5, 0, 0x8000, 50, 50, 0, L | R, tapv(1, 2), 1, True),
          (0x8A03, 0, 0, 3) + K)
    check('clicks released: held cleared', frame_run(5, 0, 0x1, 50, 50, 0, 0, tapv(1, 2), 3, True), (0x1, 50, 50, 0) + K)
    check('a click with no code: no press recorded for later', frame_run(5, 0, 0, 50, 50, 0, L, tapv(0, 1), 0, True)[3], 1)
    check('GC (type 7) with the L bit: nothing', frame_run(7, 0, 0x2, 50, 50, 0, L, tapv(1), 0, True), (0x2, 50, 50, 0) + K)
    check('Stick Smash off + L attack press: neutral', frame_run(5, 0x01, 0, 127, 0, 0, L, tapv(1), 0, True)[:3], (0x0201, 0, 0))
    check('Stick Smash off + L attack: the attack press recorded', frame_run(5, 0x01, 0, 127, 0, 0, L, tapv(1), 0)[3], 1)

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
            check('load_%s: Tap Jump byte %d -> %s' % (name, tj, 'bits 0-6' if name == 'standard' else 'bit 0'),
                  mu.mem_read(tap, 1)[0], tj & (0x7F if name == 'standard' else 1))
            check('load_%s flags 0x%02X: getter result' % (name, flags), mu.reg_read(UC_PPC_REG_3), 7)
            check('load_%s flags 0x%02X: property' % (name, flags), prop('get', P + off), (2 if flags & bit else 3, 0))
        for on, base in ((False, 0x40), (True, 0x4F)):
            prop('set', P + off, 3 if on else 2)
            mu.mem_write(REC + 0xD, bytes([base]))
            run(a.addr('save_' + name), {UC_PPC_REG_3: ACC, UC_PPC_REG_4: 0x55, UC_PPC_REG_31: P})
            want = (base & ~bit) | (0 if on else bit)
            check('save_%s %s: flags byte' % (name, 'on' if on else 'off'), mu.mem_read(REC + 0xD, 1)[0], want)
            check('save_%s: setter gets r4' % name, mu.reg_read(UC_PPC_REG_5), 0x55)

    # the click properties: int frames (type 4 at +0, the value at +4; the argument at +0x18 / +0x1C)
    def cprop(fn, key, arg=None):
        mu.mem_write(fr, struct.pack('>IIIIIII', 0, 0, 0, 0, 7, key, 4) + struct.pack('>I', arg or 0))
        run(a.addr(fn), {UC_PPC_REG_3: fr})
        return struct.unpack('>II', mu.mem_read(fr, 8))
    Q = MEM + 0x6800
    check('getl / getr, unknown object: 14 (not set)', (cprop('getl', Q), cprop('getr', Q)), ((4, 14), (4, 14)))
    check('setl 0 (attack)', cprop('setl', Q, 0), (4, 0))
    check('setr 5 (smash)', cprop('setr', Q, 5), (4, 5))
    check('getl / getr', (cprop('getl', Q), cprop('getr', Q)), ((4, 0), (4, 5)))
    check('stick_smash of the same object still on', prop('get', Q), (3, 0))
    check('stick_smash set off', prop('set', Q, 2), (2, 0))
    check('the clicks kept', (cprop('getl', Q), cprop('getr', Q)), ((4, 0), (4, 5)))
    check('setl 14 (not set)', cprop('setl', Q, 14), (4, 14))
    check('setl 9 (taunt: not offered) -> not set', (cprop('setl', Q, 9), cprop('getl', Q)), ((4, 9), (4, 14)))
    check('stick_smash still off, R kept', (prop('get', Q), cprop('getr', Q)), ((2, 0), (4, 5)))

    name, off, word, bit = C.MENU[2][:4]
    assert name == 'standard'
    mu.mem_write(ACC, struct.pack('>II', TREC, REC))
    tap = TREC + C.TAP[name][0]
    mu.mem_write(REC + 0xD, bytes([0x40]))
    mu.mem_write(tap, bytes([1 | 1 << 1 | 6 << 4 | 0x80]))
    run(a.addr('load_standard'), {UC_PPC_REG_3: ACC, UC_PPC_REG_31: P})
    check('load_standard: L attack, R smash, Tap Jump on (bit 7 cleared)',
          (cprop('getl', P + off), cprop('getr', P + off), prop('get', P + off), mu.mem_read(tap, 1)[0]),
          ((4, 0), (4, 5), (3, 0), 0x63))
    cprop('setl', P + off, 2)
    cprop('setr', P + off, 14)
    for tj in (0, 1):
        mu.mem_write(tap, bytes([tj]))                      # as the Tap Jump setter left it
        run(a.addr('save_standard'), {UC_PPC_REG_3: ACC, UC_PPC_REG_4: 0x55, UC_PPC_REG_31: P})
        check('save_standard Tap Jump %d: L jump (code 3), R not set' % tj, mu.mem_read(tap, 1)[0], tj | 3 << 1)
    prop('set', P + off, 2)
    mu.mem_write(REC + 0xD, bytes([0x40]))
    run(a.addr('save_standard'), {UC_PPC_REG_3: ACC, UC_PPC_REG_4: 0x55, UC_PPC_REG_31: P})
    check('save_standard: stick smash off with clicks set: flags byte', mu.mem_read(REC + 0xD, 1)[0], 0x40 | bit)

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
        calls = [struct.unpack('>III', mu.mem_read(LOG + 4 + 12 * i, 12)) for i in range(7)]

        def s(p):
            return bytes(mu.mem_read(p, 32)).split(b'\0')[0].decode()
        check('bind_%s: own bind first' % name, calls[0], (0x1111, 0x2222, 0x3333))
        check('bind_%s: getter' % name, (calls[1][0], s(calls[1][1]), r32(mu, calls[1][2]), r32(mu, calls[1][2] + 4)),
              (0xC1A55, 'stick_smash', a.addr('get'), C.DESC_TYPES[name][0]))
        check('bind_%s: setter' % name, (calls[2][0], s(calls[2][1]), r32(mu, calls[2][2]), r32(mu, calls[2][2] + 4)),
              (0xC1A55, 'set_stick_smash', a.addr('set'), C.DESC_TYPES[name][1]))
        want = [(0xC1A55, n, a.addr(f), t) for (g, st_, _sh), (gf, sf) in zip(C.CLICK_PROPS, (('getl', 'setl'), ('getr', 'setr')))
                for n, f, t in ((g, gf, C.CLICK_DESC[0]), (st_, sf, C.CLICK_DESC[1]))] if name == 'standard' else [(0, '', 0, 0)] * 4
        check('bind_%s: the stick clicks\' members' % name,
              [(c[0], s(c[1]) if c[1] else '', r32(mu, c[2]) if c[2] else 0, r32(mu, c[2] + 4) if c[2] else 0) for c in calls[3:]],
              want)
    print('%d failed' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
