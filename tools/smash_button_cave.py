#!/usr/bin/env python3
"""Smash attack button and the "Stick Smash" / "Stick F-Smash" controls settings. Prints
rpx_patch.py arguments.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/smash_button_cave.py)

(The Controls menu side is tools/option_button_ui.py: the xtal script, layout and text.)

Controls (docs/native-notes.md "Controls settings"): a name's controls are a 0x3C-byte save record
per pad type (CTR 3DS / GC / STANDARD Pro, GamePad, Classic / FREE_STYLE Wii Remote + Nunchuk /
REMOTE); each button holds an action (PAD_BUTTON_OPE_*: 0 attack, 1 special, 2 jump, 3 shield,
4 grab, 5 smash, ...). Byte 0x3B holds the A+B smash ("Smash Attack") flags, one bit per pad type
(0x80 CTR, 0x40 GC, 0x20 FREE_STYLE, 0x10 STANDARD); its low four bits were unused. Each pad type's
Tap Jump is a bool byte (GC record byte 0x0B, STANDARD 0x2D, CTR 0x3A), read and written only
through its accessor (getter: != 0, setter: the byte).

Every frame the input manager (0x030B9A38 / 0x030BA218, 8 ports) turns each player's pad into a
4-byte input frame (u16 action bits, s8 stick X / Y, the stick x 127) with the mapping function of
the pad type (dispatcher 0x030B8F08(config base, port, frame, pad, ..): the config base holds the
players' records, port * 0x3C, and 9 bytes of mapping state per port at +0x1E0). A button's action
op becomes bit 1 << op (grab 0x18), so a button set to Smash already gives the smash bit 0x20; the
C-stick's smash gives 0x21 (smash + attack) and the C-stick direction as the stick. The fighter
(0x02E71464 / 0x02E71774) takes the smash bit with a neutral or sideways stick as a side smash,
up / down as up / down smash; without the smash bit, attack + a stick flicked past the smash
thresholds (fsmash 0.83 / usmash 0.66 / dsmash -0.66, fighter_param_common words 7 / 0x3A / 0x3C,
within 2 / 4 / 4 frames) is a smash attack.

1. Smash attack button: in each mapping function, just before the A+B smash check (its call to
   the pad type's A+B flag getter), a smash bit from a button gets the attack bit too (0x21, as the
   C-stick's smash): F-smash with no direction on the ground, the direction's smash attack; in the
   air the aerial for the stick (neutral air with no direction). Holding the button charges.
2. Stick Smash off (bit STICK_BIT[type] of the record's byte 0x3B set): the dispatcher calls are
   wrapped; on the frame attack is pressed (the attack bit was clear the frame before, kept in the
   port's mapping state byte 2) without the smash bit, the frame's stick is limited to |x| <= XMAX,
   |y| <= YMAX (0.79 / 0.63: under the smash thresholds, over the tilt ones, 0.25), so that press
   is a tilt / aerial and never a smash attack. The stick is only limited that frame, and it stays
   over 0.25 (the flick counters, which restart when the stick crosses 0.25, are unaffected). The
   setting is part of the input frame, so replays and online inputs stay as played.
   Stick F-Smash off (SIDE_BIT of the type's Tap Jump byte set, stick smash on): the same, x only
   (|x| <= XMAX), so a sideways flick + attack is a forward tilt and up / down smash attacks stay.
   The Tap Jump getters return bit 0 only (clrlwi in place of the != 0) and the setters keep the
   other bits (a stub: rlwimi of bit 0).
3. Controls menu: OptionPadAssignCtr / Gc / Standard get bool properties `stick_smash` and
   `side_smash` (true = on), bound with their other members (0x033C4FB8 after the last member);
   their values per object are kept in a small table keyed by the object's data (the
   OptionPadAssign sub-struct), bit 0 stick smash off, bit 1 side smash off. load_parameter_ctr /
   gc / standard (0x021B49DC / 0x021B4B64 / 0x021B4CF4) read them from the record's bits,
   save_parameter_* (0x021B53DC / 0x021B5568 / 0x021B56F4) write them, at their calls to the A+B
   flag getter / setter (r31 = the OptionPadAssign data there).

Code in the grown .text at CAVE; the menu hooks (0x021Bxxxx, out of reach of it) go through `b`
trampolines at TRAMPOLINES (Havok cave).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ppcasm import Asm  # noqa: E402

CAVE = 0x04B9A000               # grown .text after acmd_ext_cave.py (GROW 0x04B9A000)
LIMIT = 0x04B9B000
GROW = 0x04B9B000
TRAMPOLINES = 0x037EE3D0        # 9 words; position_vars_cave.py's CAVE2 ends at 0x037EE3D0
TRAMP_LIMIT = 0x037EE3F4        # stage_omega_cave.py's trampolines

BIND = 0x033C4FB8               # bind(class, name, descriptor)
# a member's argument types (the class's own type first: a descriptor of another class's member
# fails the call for this one): [this] for a getter, [this, bool] for a setter, as the class's own
# bool member (smash_attack)'s
DESC_TYPES = {'ctr': (0x100283FC, 0x10028534), 'gc': (0x10028560, 0x10028680),
              'standard': (0x100286C4, 0x100287FC)}
DISPATCH = 0x030B8F08
DISPATCH_CALLS = (0x030B9AB0, 0x030B9B00, 0x030BA2B0, 0x030BA300)
XMAX, YMAX = 100, 80            # stick bytes (x 1/127) on an attack press with stick smash off
SIDE_ENTRIES = 16
SIDE_BIT = 0x02                 # in the Tap Jump byte: stick F-smash off

# pad type (pad state +0x7C, the dispatcher's jump table) -> stick smash bit in record byte 0x3B
TYPE_BITS = {1: 0x08, 9: 0x08,                  # CTR       (A+B bit 0x80)
             2: 0x01, 5: 0x01, 6: 0x01, 8: 0x01,  # STANDARD  (0x10)
             4: 0x02,                           # FREE_STYLE (0x20)
             7: 0x04}                           # GC        (0x40); 3 REMOTE: none
# pad type -> its Tap Jump byte in the record (FREE_STYLE: no Stick F-Smash setting)
TYPE_TAP = {1: 0x3A, 9: 0x3A, 2: 0x2D, 5: 0x2D, 6: 0x2D, 8: 0x2D, 7: 0x0B}

# smash attack button: (call site, A+B flag getter, the mapping's action-bit register)
AB_CALLS = (
    (0x030B71F0, 0x030C8A00, 'r27'),     # CTR        0x030B6F7C
    (0x030B75A4, 0x030C8858, 'r27'),     # STANDARD   0x030B7330
    (0x030B792C, 0x030C83D8, 'r27'),     # GC         0x030B76E8
    (0x030B8DD4, 0x030C86A0, 'r29'),     # FREE_STYLE 0x030B8620 (two calls)
    (0x030B8E0C, 0x030C86A0, 'r29'),
)

# Controls menu: per class (name, sub-struct offset in OptionPadAssign, flags record word in the
# accessor (0 / 4), stick smash bit, A+B getter call / getter in load_parameter_*, setter call /
# setter in save_parameter_*, the bind function's last bind call)
MENU = (
    ('ctr', 0x00, 0, 0x08, 0x021B4B3C, 0x030C8A00, 0x021B5540, 0x030C8A10, 0x021B6E88),
    ('gc', 0x0E, 4, 0x04, 0x021B4CBC, 0x030C83D8, 0x021B56C0, 0x030C83E8, 0x021B718C),
    ('standard', 0x1C, 4, 0x01, 0x021B4E54, 0x030C8858, 0x021B5858, 0x030C8868, 0x021B7480),
)
# per class: Tap Jump byte in the accessor's word 0 record, its getter, setter
TAP = {'ctr': (0x0C, 0x030C89E0, 0x030C89F4), 'gc': (0x0B, 0x030C83B8, 0x030C83CC),
       'standard': (0x0C, 0x030C8838, 0x030C884C)}
# the members: (getter label, setter label, name, side table bit)
PROPS = (('get', 'set', 'stick_smash', 0), ('gets', 'sets', 'side_smash', 1))

ORIGINAL = {
    0x030B71F0: 0x48011811, 0x030B75A4: 0x480112B5, 0x030B792C: 0x48010AAD,
    0x030B8DD4: 0x4800F8CD, 0x030B8E0C: 0x4800F895,
    0x030B9AB0: 0x4BFFF459, 0x030B9B00: 0x4BFFF409, 0x030BA2B0: 0x4BFFEC59, 0x030BA300: 0x4BFFEC09,
    0x021B4B3C: 0x48F13EC5, 0x021B4CBC: 0x48F1371D, 0x021B4E54: 0x48F13A05,
    0x021B5540: 0x48F134D1, 0x021B56C0: 0x48F12D29, 0x021B5858: 0x48F13011,
    0x021B6E88: 0x4920E131, 0x021B718C: 0x4920DE2D, 0x021B7480: 0x4920DB39,
    0x030C89E8: 0x300CFFFF, 0x030C89EC: 0x7C606110, 0x030C89F8: 0x988C000C,     # Tap Jump CTR
    0x030C83C0: 0x300CFFFF, 0x030C83C4: 0x7C606110, 0x030C83D0: 0x988C000B,     # GC
    0x030C8840: 0x300CFFFF, 0x030C8844: 0x7C606110, 0x030C8850: 0x988C000C,     # STANDARD
}


def far(target, link=False):
    """branch to an absolute address through ctr (r12)"""
    return '''
            lis r12, %d
            ori r12, r12, %d
            mtctr r12
            %s''' % (target >> 16, target & 0xFFFF, 'bctrl' if link else 'bctr')


def find(value_reg):
    """r10 = the side-table entry of key (r12), or 0; uses r0, r9, r10, ctr"""
    n = find.n = getattr(find, 'n', 0) + 1
    return '''
            lis r10, side@ha
            addi r10, r10, side@l
            li r9, %(cnt)d
            mtctr r9
    f%(n)d_l:  lwz r9, 0(r10)
            cmplw r9, r12
            beq f%(n)d_e
            addi r10, r10, 8
            bdnz f%(n)d_l
            li r10, 0
    f%(n)d_e:  li %(v)s, 0
            cmpwi r10, 0
            beq f%(n)d_x
            lwz %(v)s, 4(r10)
    f%(n)d_x:''' % dict(n=n, cnt=SIDE_ENTRIES, v=value_reg)


def store(value_reg):
    """side[key r12] = value: the key's entry, else the next one (round robin); uses r0, r9-r11"""
    n = store.n = getattr(store, 'n', 0) + 1
    return find('r11') + '''
            cmpwi r10, 0
            bne s%(n)d_w
            lis r9, side_next@ha
            lwz r10, side_next@l(r9)
            addi r0, r10, 1
            clrlwi r0, r0, %(mask)d
            stw r0, side_next@l(r9)
            slwi r10, r10, 3
            lis r9, side@ha
            addi r9, r9, side@l
            add r10, r10, r9
            stw r12, 0(r10)
    s%(n)d_w:  stw %(v)s, 4(r10)''' % dict(n=n, v=value_reg, mask=32 - (SIDE_ENTRIES.bit_length() - 1))


def build():
    find.n = store.n = 0
    a = Asm(CAVE)
    src = []
    # 1. smash attack button
    for i, (_site, getter, acc) in enumerate(AB_CALLS):
        src.append('''
    ab%(i)d:    andi. r0, %(acc)s, 0x20      # a button's smash: + attack, as the C-stick's
            beq ab%(i)d_g
            ori %(acc)s, %(acc)s, 1
    ab%(i)d_g:%(go)s''' % dict(i=i, acc=acc, go=far(getter)))
    # 2. stick smash off: the dispatcher wrapper
    src.append('''
    wrap:   stwu r1, -0x20(r1)
            mflr r0
            stw r0, 0x24(r1)
            stmw r28, 0x10(r1)
            mr r31, r3                  # config base (records port * 0x3C, mapping state +0x1E0)
            mr r30, r4                  # port
            mr r29, r5                  # the input frame
            mr r28, r6                  # the pad
            bl %(dispatch)d
            lwz r12, 4(r28)             # pad type (as the dispatcher reads it)
            lwz r12, 0x1C(r12)
            mtctr r12
            mr r3, r28
            bctrl
            lwz r3, 0x7C(r3)
            cmplwi r3, 9
            bgt w_done
            lis r12, type_bits@ha
            addi r12, r12, type_bits@l
            lbzx r9, r12, r3
            cmpwi r9, 0
            beq w_done
            mulli r12, r30, 9           # the port's mapping state byte 2: attack held last frame
            add r12, r12, r31
            addi r12, r12, 0x1E2
            lhz r0, 0(r29)
            lbz r11, 0(r12)
            andi. r10, r0, 1
            stb r10, 0(r12)
            beq w_done                  # attack not held
            cmpwi r11, 0
            bne w_done                  # held before: not a press
            andi. r10, r0, 0x20
            bne w_done                  # smash bit (smash button, C-stick, A+B): a smash anyway
            mulli r8, r30, 0x3C
            add r8, r8, r31             # the record
            lbz r10, 0x3B(r8)
            and. r10, r10, r9
            bne w_xy                    # stick smash off: x and y
            lis r12, type_tap@ha
            addi r12, r12, type_tap@l
            lbzx r10, r12, r3
            cmpwi r10, 0
            beq w_done
            lbzx r10, r8, r10
            andi. r10, r10, %(side)d
            beq w_done                  # stick F-smash on
            b w_x
    w_xy:   lbz r10, 3(r29)
            extsb r10, r10
            cmpwi r10, %(ymax)d
            ble w_y1
            li r10, %(ymax)d
    w_y1:   cmpwi r10, -%(ymax)d
            bge w_y2
            li r10, -%(ymax)d
    w_y2:   stb r10, 3(r29)
    w_x:    lbz r10, 2(r29)
            extsb r10, r10
            cmpwi r10, %(xmax)d
            ble w_x1
            li r10, %(xmax)d
    w_x1:   cmpwi r10, -%(xmax)d
            bge w_x2
            li r10, -%(xmax)d
    w_x2:   stb r10, 2(r29)
    w_done: lmw r28, 0x10(r1)
            lwz r0, 0x24(r1)
            mtlr r0
            addi r1, r1, 0x20
            blr''' % dict(dispatch=DISPATCH, xmax=XMAX, ymax=YMAX, side=SIDE_BIT))
    # 3. the `stick_smash` / `side_smash` properties (a bit each in the side table), load / save
    for g, st, _name, sh in PROPS:
        src.append('''
    %(g)s:%(pad)s lwz r11, 0x10(r3)           # this: the pad type's OptionPadAssign sub-struct
            clrlwi r11, r11, 27
            cmpwi r11, 0x10
            lwz r12, 0x14(r3)
            bne %(g)s_k
            lwz r12, 0x18(r12)
    %(g)s_k:''' % dict(g=g, pad=' ' * (6 - len(g))) + find('r11') + '''
            rlwinm r11, r11, %(rot)d, 31, 31
            xori r11, r11, 1            # on = the bit clear
            addi r12, r11, 2            # false 2 / true 3
            stw r12, 0(r3)
            li r12, 0
            stw r12, 4(r3)
            blr
    %(s)s:%(pad)s lwz r11, 0x10(r3)
            clrlwi r11, r11, 27
            cmpwi r11, 0x10
            lwz r12, 0x14(r3)
            bne %(s)s_k
            lwz r12, 0x18(r12)
    %(s)s_k:  lwz r11, 0x18(r3)           # the argument: true (3) = on
            li r8, 1
            cmpwi r11, 2
            ble %(s)s_v
            li r8, 0
    %(s)s_v:''' % dict(s=st, pad=' ' * (6 - len(st)), rot=(32 - sh) % 32) + find('r11') + '''
            rlwimi r11, r8, %(sh)d, %(b)d, %(b)d
            mr r8, r11''' % dict(sh=sh, b=31 - sh) + store('r8') + '''
            rlwinm r8, r8, %(rot)d, 31, 31
            xori r8, r8, 1
            addi r12, r8, 2
            stw r12, 0(r3)
            li r12, 0
            stw r12, 4(r3)
            blr''' % dict(rot=(32 - sh) % 32))
    for name, off, word, bit, _lc, getter, _sc, setter, _bc in MENU:
        shift = bit.bit_length() - 1
        tap = TAP[name][0]
        src.append('''
    load_%(n)s:                             # r3 accessor, r31 OptionPadAssign data
            lwz r12, %(w)d(r3)
            lbz r8, 0xD(r12)
            rlwinm r8, r8, %(rot)d, 31, 31
            lwz r12, 0(r3)              # + the Tap Jump byte's side bit
            lbz r0, %(tap)d(r12)
            rlwinm r0, r0, 0, 30, 30
            or r8, r8, r0
            addi r12, r31, %(off)d''' % dict(n=name, w=word, rot=(32 - shift) % 32, off=off, tap=tap) + store('r8') + far(getter) + '''
    save_%(n)s:                             # r3 accessor, r4 the A+B value, r31 data
            addi r12, r31, %(off)d''' % dict(n=name, off=off) + find('r8') + '''
            lwz r12, %(w)d(r3)
            lbz r0, 0xD(r12)
            rlwinm r0, r0, 0, %(mb)d, %(me)d
            rlwinm r11, r8, %(sh)d, %(b)d, %(b)d
            or r0, r0, r11
            stb r0, 0xD(r12)
            lwz r12, 0(r3)
            lbz r0, %(tap)d(r12)
            rlwimi r0, r8, 0, 30, 30
            stb r0, %(tap)d(r12)''' % dict(w=word, sh=shift, b=31 - shift, mb=(32 - shift) % 32, me=(30 - shift) % 32,
                                         tap=tap) + far(setter) + '''
    tap_set_%(n)s:                          # the Tap Jump setter: bit 0 only
            lbz r0, %(tap)d(r12)
            rlwimi r0, r4, 0, 31, 31
            stb r0, %(tap)d(r12)
            blr
    bind_%(n)s:                             # the class's last member bind, then ours (r31 = class)
            mflr r0
            stwu r1, -0x10(r1)
            stw r0, 0x14(r1)
            bl %(bind)d''' % dict(n=name, bind=BIND, tap=tap) + ''.join('''
            mr r3, r31
            lis r4, name_%(g)s@ha
            addi r4, r4, name_%(g)s@l
            lis r5, desc_%(g)s_%(n)s@ha
            addi r5, r5, desc_%(g)s_%(n)s@l
            bl %(bind)d''' % dict(n=name, g=g, bind=BIND) for p in PROPS for g in p[:2]) + '''
            lwz r0, 0x14(r1)
            mtlr r0
            addi r1, r1, 0x10
            blr''')
    bits = [TYPE_BITS.get(t, 0) for t in range(12)]
    taps = [TYPE_TAP.get(t, 0) for t in range(12)]

    def table(b):
        return ''.join('\n            .word 0x%08X' % int.from_bytes(bytes(b[i:i + 4]), 'big') for i in range(0, 12, 4))
    src.append(''.join('''
    desc_%(g)s_%(n)s: .word 0
            .word %(t)d
            .word 0x%(f)08X''' % dict(n=m[0], g=g, t=DESC_TYPES[m[0]][k], f=(0x01000000, 0x01010000)[k])
        for m in MENU for p in PROPS for k, g in enumerate(p[:2])) + '''
    type_bits:''' + table(bits) + '''
    type_tap:''' + table(taps) + '''
    side_next: .word 0
    side:''' + '\n            .word 0' * (2 * SIDE_ENTRIES) + ''.join('''
    name_%s:''' % g + cstr(nm) for p in PROPS for g, nm in ((p[0], p[2]), (p[1], 'set_' + p[2]))))
    # .word of a label: resolve after assembly
    a.asm('\n'.join(src))
    words = a.words()
    for m in MENU:
        for p in PROPS:
            for g in p[:2]:
                words[(a.addr('desc_%s_%s' % (g, m[0])) - CAVE) // 4] = a.addr(g)
    assert CAVE + 4 * len(words) <= LIMIT, 'smash button cave too big'
    patches = {CAVE + 4 * i: w for i, w in enumerate(words)}

    def branch(at, to, link):
        off = to - at
        assert -0x2000000 <= off < 0x2000000, (hex(at), hex(to))
        return 0x48000000 | (off & 0x3FFFFFC) | link
    for i, (site, _g, _r) in enumerate(AB_CALLS):
        patches[site] = branch(site, a.addr('ab%d' % i), 1)
    for site in DISPATCH_CALLS:
        patches[site] = branch(site, a.addr('wrap'), 1)
    clr = Asm(0)
    clr.asm('rlwinm r3, r12, 0, 31, 31\nnop')
    for name, (_tap, getter, setter) in TAP.items():
        patches[getter + 8], patches[getter + 12] = clr.words()
        patches[setter + 4] = branch(setter + 4, a.addr('tap_set_' + name), 0)
    t = TRAMPOLINES
    for name, _off, _w, _b, load_call, _g, save_call, _s, bind_call in MENU:
        for call, lab in ((load_call, 'load_'), (save_call, 'save_'), (bind_call, 'bind_')):
            patches[t] = branch(t, a.addr(lab + name), 0)
            patches[call] = branch(call, t, 1)
            t += 4
    assert t <= TRAMP_LIMIT
    return a, patches


def cstr(s):
    b = s.encode() + b'\0'
    b += b'\0' * (-len(b) % 4)
    return ''.join('\n            .word 0x%08X' % int.from_bytes(b[i:i + 4], 'big') for i in range(0, len(b), 4))


def args(patches):
    return ['grow:0x%08X' % GROW] + ['0x%08X=0x%08X' % kv for kv in sorted(patches.items())]


def main():
    _a, patches = build()
    print(' '.join(args(patches)))
    sys.stderr.write('smash button + stick smash setting: cave 0x%08X, %d patches\n' % (CAVE, len(patches)))


if __name__ == '__main__':
    main()
