"""The clones' own sounds, announcer call and Kirby copy in the executable (the "extras" part of the tool's code space).

1. Sound bank aliases (a clone with its own sound banks). A fighter's sound (row << 16 | label) plays only from that
   fighter's own bank handles: the finder (0x02C71898) matches the row's bank id against each handle's BINF id or the
   handle's alias (+0x5C0 se, +0x5C4 voice, +0x5C8 the crowd's cheer, +0x580 the Final Smash's se_common), which the
   SoundModule set-up 0x02761C50 reads from fightermodelbanktable.mtb by the fighter's name (none for a new kind). The
   clone's banks have ids of their own (sound.py), so the base's ids that the game plays from code (the KO screams /
   damage voices of commonsoundtable.csb, MSC scripts, the voice sequences, the base's native code) would find no bank;
   with its base's ids as aliases they play from the clone's own banks. Hooks (each acts only when called from that
   one place, by its return address, and only for a clone's kind):
     SETUP 0x03127990 (`lwz r12, 0(r3)`), its call at 0x02761E44 (after the MTB lookups, before the handles):
           +0x5C0 / +0x5C4 / +0x5C8 = the base's se / vc / cheer bank ids;
     FS    0x03121FA8 (`lwz r3, 0(r3)`), its call at 0x02761598 (the Final Smash bank): +0x580 and r5 = se_common's.
2. The results screen's announcer call (narration.py): 0x02A65898(mode, kind, costume, flag) has no call past kind
   0x40. Its first four words become a far jump (out of a branch's reach from the code space); for a clone's kind the
   function runs with its base's kind and the result goes through the clone's map (base id -> the clone's own label).
3. Kirby (copy_grant 0x02EFCD8C refuses kinds >= 0x3A; the copy resources load per fighter in the match by kind and
   return for kinds >= 0x3A):
     GRANT 0x02EFCDA4 (`mr r28, r6`): a clone's kind is granted as its base's kind (the base's copy ability, every
           copy table and switch the base's);
     RES   0x030C46A8 (`mr r28, r4`, the per-resource helper, also keeps the real kind), 0x030C5254 (`mr r16, r4`, the
           loader), 0x030C5BD0 (`mr r23, r4`, the release): the clone's kind -> its base's;
     BODY  0x030C4710 (`lbz r10, 0(r7)`, the first use of the motion folder name; not the read 0x030C470C, which carries
           a relocation): fighter/kirby/motion/<clone>body for a clone with its own copy motions;
     HAT   0x030C4830 (`lwzx r7, r23, r21`): fighter/kirby/model/<clone>cap/cNN for a clone with its own hat;
     VOICE 0x030C0FF8 (`cmplwi r29, 0x39`, the Kirby-copy voice bank's bound): a clone's own
           snd_se_vc_Kirby_copy_<Cap> loads (Kirby's copy voices of that player come from it).
"""
from . import _paths  # noqa: F401
from ppcasm import Asm, ha  # noqa: E402

SETUP_HOOK, SETUP_RET = 0x03127990, 0x02761E48
FS_HOOK, FS_RET = 0x03121FA8, 0x0276159C
CALL = 0x02A65898
GRANT = 0x02EFCDA4
RES = ((0x030C46A8, 28, True), (0x030C5254, 16, False), (0x030C5BD0, 23, False))
BODY, HAT, VOICE = 0x030C4710, 0x030C4830, 0x030C0FF8
ORIGINALS = {SETUP_HOOK: 'lwz r12, 0(r3)', FS_HOOK: 'lwz r3, 0(r3)',
             CALL: 'mflr r0', CALL + 4: 'stwu r1, -0x10(r1)', CALL + 8: 'stw r31, 0xc(r1)', CALL + 12: 'mr r31, r3',
             GRANT: 'mr r28, r6', RES[0][0]: 'mr r28, r4', RES[1][0]: 'mr r16, r4', RES[2][0]: 'mr r23, r4',
             BODY: 'lbz r10, 0(r7)', HAT: 'lwzx r7, r23, r21', VOICE: 'cmplwi r29, 0x39'}
# the calls the hooks rely on (checked, never written)
CALLERS = {0x02761E44: SETUP_HOOK, 0x02761598: FS_HOOK}
SE_ALIAS, VC_ALIAS, CHEER_ALIAS, COMMON_ALIAS = 0x5C0, 0x5C4, 0x5C8, 0x580


def slo(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def one(addr, text):
    a = Asm(addr)
    a.asm(text)
    return a.words()[0]


def size_for(n):
    return (0x800 + 0x1C0 * n + 0xFFF) & ~0xFFF


def _cstr(s):
    b = s.encode() + b'\0'
    b += b'\0' * (-len(b) % 4)
    return ['.word 0x%08X' % int.from_bytes(b[i:i + 4], 'big') for i in range(0, len(b), 4)]


def check(read):
    bad = ['0x%08X is 0x%08X, expected 0x%08X (%s)' % (a, read(a), one(a, t), t)
           for a, t in ORIGINALS.items() if read(a) != one(a, t)]
    for at, target in CALLERS.items():
        w = read(at)
        off = w & 0x3FFFFFC
        if off & 0x2000000:
            off -= 0x4000000
        if not (w >> 26 == 18 and w & 1 and at + off == target):
            bad.append('0x%08X is not a call of 0x%08X' % (at, target))
    if bad:
        raise AssertionError('clone extras: ' + '; '.join(bad))


def build(read, fighters, kinds_of, cave, limit):
    """{address: word} for the fighters' registry records; kinds_of(base name) -> its vanilla kind.
    read(addr) -> the vanilla view's word."""
    check(read)
    alias = [f for f in fighters if any(f.get('sound_alias') or [])]
    calls = [f for f in fighters if f.get('call', 'own') != 'none']
    kirby = [f for f in fighters if f.get('kirby', True)]
    names = [f for f in kirby if f.get('kirby_body') or f.get('kirby_hat')]
    voice = [f for f in kirby if f.get('kirby_voice')]
    src = ['res_kind:', '.word 0xFFFFFFFF', 'alias:']
    for f in alias:
        se, vc, ch, cm = (list(f['sound_alias']) + [0, 0, 0, 0])[:4]
        src += ['.word 0x%X' % f['kind'], '.word %d' % se, '.word %d' % vc, '.word %d' % ch, '.word %d' % cm]
    src += ['.word 0xFFFFFFFF', 'calls:']
    for f in calls:
        pairs = f.get('call_map') or []
        src += ['.word 0x%X' % f['kind'], '.word 0x%X' % kinds_of(f['base']), '.word %d' % len(pairs)]
        for a, b in pairs:
            src += ['.word 0x%08X' % a, '.word 0x%08X' % b]
    src += ['.word 0xFFFFFFFF']
    for f in names:
        if f.get('kirby_body'):
            src += ['s_body_%x:' % f['kind']] + _cstr(f['kirby_body'])
        if f.get('kirby_hat'):
            src += ['s_hat_%x:' % f['kind']] + _cstr(f['kirby_hat'])
    # 1. aliases
    src += ['''
setup:  mflr r12
        lis r11, 0x%(sh)X
        ori r11, r11, 0x%(sl)X
        cmplw r12, r11
        bne s_out
        lwz r11, 8(r30)
        lis r12, alias@ha
        addi r12, r12, alias@l
s_lp:   lwz r0, 0(r12)
        cmpwi r0, -1
        beq s_out
        cmplw r0, r11
        beq s_hit
        addi r12, r12, 20
        b s_lp
s_hit:  lwz r0, 4(r12)
        cmpwi r0, 0
        beq s_vc
        stw r0, %(se)d(r30)
s_vc:   lwz r0, 8(r12)
        cmpwi r0, 0
        beq s_ch
        stw r0, %(vc)d(r30)
s_ch:   lwz r0, 12(r12)
        cmpwi r0, 0
        beq s_out
        stw r0, %(ch)d(r30)
s_out:  lwz r12, 0(r3)
        b 0x%(sback)X
fs:     mflr r12
        lis r11, 0x%(fh)X
        ori r11, r11, 0x%(fl)X
        cmplw r12, r11
        bne f_out
        lwz r11, 8(r30)
        lis r12, alias@ha
        addi r12, r12, alias@l
f_lp:   lwz r0, 0(r12)
        cmpwi r0, -1
        beq f_out
        cmplw r0, r11
        beq f_hit
        addi r12, r12, 20
        b f_lp
f_hit:  lwz r0, 16(r12)
        cmpwi r0, 0
        beq f_out
        stw r0, %(cm)d(r30)
        mr r5, r0
f_out:  lwz r3, 0(r3)
        b 0x%(fback)X
''' % dict(sh=SETUP_RET >> 16, sl=SETUP_RET & 0xFFFF, fh=FS_RET >> 16, fl=FS_RET & 0xFFFF, se=SE_ALIAS,
           vc=VC_ALIAS, ch=CHEER_ALIAS, cm=COMMON_ALIAS, sback=SETUP_HOOK + 4, fback=FS_HOOK + 4)]
    # 2. the results call
    back = CALL + 16
    src += ['''
call:   lis r12, calls@ha
        addi r12, r12, calls@l
c_lp:   lwz r11, 0(r12)
        cmpwi r11, -1
        beq c_orig
        cmplw r11, r4
        beq c_hit
        lwz r11, 8(r12)
        slwi r11, r11, 3
        add r12, r12, r11
        addi r12, r12, 12
        b c_lp
c_orig: mflr r0
        stwu r1, -0x10(r1)
        stw r31, 0xc(r1)
        mr r31, r3
        lis r12, 0x%(bh)X
        addi r12, r12, %(bl)d
        mtctr r12
        bctr
c_hit:  mflr r0
        stwu r1, -0x20(r1)
        stw r0, 0x24(r1)
        stw r30, 0x18(r1)
        mr r30, r12
        lwz r4, 4(r12)
        bl c_orig
        lwz r11, 8(r30)
        addi r12, r30, 12
m_lp:   cmpwi r11, 0
        beq m_done
        lwz r0, 0(r12)
        cmplw r0, r3
        bne m_nx
        lwz r3, 4(r12)
        b m_done
m_nx:   addi r12, r12, 8
        addi r11, r11, -1
        b m_lp
m_done: lwz r30, 0x18(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
''' % dict(bh=ha(back), bl=slo(back))]

    # 3. Kirby: kind maps without scratch registers (unrolled), names by the kept kind
    def kmap(reg, tag):
        out = []
        for i, f in enumerate(kirby):
            out += ['cmplwi r%d, 0x%X' % (reg, f['kind']), 'bne %s%d' % (tag, i),
                    'li r%d, 0x%X' % (reg, kinds_of(f['base'])), '%s%d:' % (tag, i)]
        return out
    src += ['grant:', 'mr r28, r6'] + kmap(28, 'g') + ['blr']
    for hook, reg, keep in RES:
        src += ['res_%X:' % hook]
        if keep:
            src += ['lis r12, res_kind@ha', 'stw r4, res_kind@l(r12)']
        src += ['mr r%d, r4' % reg] + kmap(reg, 'r%X_' % hook) + ['blr']
    src += ['body:', 'lis r12, res_kind@ha', 'lwz r12, res_kind@l(r12)']
    for f in names:
        if f.get('kirby_body'):
            src += ['cmplwi r12, 0x%X' % f['kind'], 'bne nb_%x' % f['kind'], 'lis r7, s_body_%x@ha' % f['kind'],
                    'addi r7, r7, s_body_%x@l' % f['kind'], 'nb_%x:' % f['kind']]
    src += ['lbz r10, 0(r7)', 'blr', 'hat:', 'lis r12, res_kind@ha', 'lwz r12, res_kind@l(r12)']
    for f in names:
        if f.get('kirby_hat'):
            src += ['cmplwi r12, 0x%X' % f['kind'], 'bne nh_%x' % f['kind'], 'lis r7, s_hat_%x@ha' % f['kind'],
                    'addi r7, r7, s_hat_%x@l' % f['kind'], 'blr', 'nh_%x:' % f['kind']]
    src += ['lwzx r7, r23, r21', 'blr', 'voice:']
    for f in voice:
        src += ['cmplwi r29, 0x%X' % f['kind'], 'beq v_hit']
    src += ['cmplwi r29, 0x39', 'blr', 'v_hit:', 'cmplw r29, r29', 'blr']
    a = Asm(cave)
    a.asm('\n'.join(src))
    cw = a.words()
    assert cave + 4 * len(cw) <= limit, 'clone extras: %d bytes, the part has %d' % (4 * len(cw), limit - cave)
    words = {cave + 4 * i: w for i, w in enumerate(cw)}
    L = a.labels
    words[SETUP_HOOK] = one(SETUP_HOOK, 'b 0x%X' % L['setup'])
    words[FS_HOOK] = one(FS_HOOK, 'b 0x%X' % L['fs'])
    for i, line in enumerate(['lis r12, 0x%X' % ha(L['call']), 'addi r12, r12, %d' % slo(L['call']), 'mtctr r12',
                              'bctr']):
        words[CALL + 4 * i] = one(CALL + 4 * i, line)
    if kirby:
        words[GRANT] = one(GRANT, 'bl 0x%X' % L['grant'])
        for hook, _reg, _k in RES:
            words[hook] = one(hook, 'bl 0x%X' % L['res_%X' % hook])
    if names:
        words[BODY] = one(BODY, 'bl 0x%X' % L['body'])
        words[HAT] = one(HAT, 'bl 0x%X' % L['hat'])
    if voice:
        words[VOICE] = one(VOICE, 'bl 0x%X' % L['voice'])
    return words, {'labels': dict(L), 'alias': len(alias), 'calls': len(calls), 'kirby': len(kirby)}
