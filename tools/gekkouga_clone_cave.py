#!/usr/bin/env python3
"""Greninja's clones (fighters/gekkouga/README.md "Clones v1" / "Clones v2"): the native part. Prints rpx_patch.py
arguments (v2: exe_v46z_gk2; v1's exe_v46z_gk1 was this without the v2 parts).

  python3 tools/rpx_patch.py exe_v46z_ui10.rpx exe_v46z_gk2.rpx $(python3 tools/gekkouga_clone_cave.py --rpx exe_v46z_ui10.rpx)
  python3 tools/gekkouga_clone_cave.py --rpx exe_v46z_ui10_diag.rpx --diag # + the TEST ONLY OSReport lines (exe_v46z_gk2_diag)
  python3 tools/gekkouga_clone_cave.py --rpx exe_v46z_ui10.rpx --info      # where everything went

Greninja (fighter kind 0x30) runs his own native code; for him ONLY this adds (every other fighter, Kirby's Greninja copy
included, runs the game's words as before: the hooks sit in Greninja's own specializer, vtable 0x101347B4):

1. THE CLONE ARTICLE: a brand-new weapon kind CLONE_KIND (0x1A1, the first free one after Byleth's 0x1A0) owned by
   "gekkouga", named / foldered "clone" (fighter/gekkouga/model|motion/clone/, script/animcmd/weapon/clone/,
   script/msc/clone/clone.mscsb). It is a copy of his Final Smash clone (bunshin, 0xFE: a Greninja model article with a
   MotionModule, no params) built the way tools/weapon_expand.py builds a brand-new article, written into the weapon
   cave's tables that exe_v46q+ already has (kind 0x1A1's entries were unused):
   - the 4 name tables (owner = Greninja's own "gekkouga" string, name / folder = "clone", root = bunshin's) and the 3
     static tables (bunshin's u32 / u8 / u16 flags 0x87D: 0x40 a model, 0x10 the model in the owner's colour: c00-c07);
   - its descriptor (a copy of bunshin's) whose motion info lists EVERY body motion of his (his fighter motion table's
     668 main-animation hashes, v2 with his flags, and v2 his motion parts / groups: words 2-5 of his own motion info,
     the hands' and parts' per-motion tables): the article plays motion kind K from motion/clone/main.pac (his body
     main.pac; v2 + his part pacs) and runs the script its motion.mtable names for K (his body mtable);
   - its own module row: bunshin's 28 constructors with the shuriken's KineticModule (slot 0), AttackModule (2) and
     slots 5, 8, 9, 11 (the attack's companions every attacking Greninja article has): his hitboxes, copied into the
     article's game scripts, hit as his;
   - its own singleton (bunshin's vtable copied, the hit-result method +0xAC replaced): its attack connecting / being
     shielded (result bits 0x17) never removes it (the default removes a weapon whose attack connects); v2: it also
     sets its owner's VAR_22 = 1.0 (the owner: the fighter table entry of the slot in the clone's VAR_0, which its MSC
     writes), his MSC's signal for his hitlag;
   - the base kind (bunshin: its 11 native methods), the descriptor case, the singleton case, the own row.
   Greninja's article list becomes his 6 articles + two CLONE_KIND entries (article 6 the left clone, 7 the right one,
   one instance each, no spawner callback as bunshin's), through a copy of his fighter descriptor (+8 the new list)
   that the fighter descriptor switch (tools/kind_expand.py's pointer table, entry 0x30) now returns.
2. THE CLONES' "HURTBOXES": his counter shape group (ShieldModule [acc + 0x72F4], kind 2, group 1, which his slot 0
   builds inline from his vl counter shape) is built with SHAPES instead: four capsules on joint 0 at the clone places
   (z = -2 GAP, -GAP, +GAP, +2 GAP along his facing, y 3-15, radius 5.5): the bl at G1_HOOK passes our desc. The guard
   bubble has 1 shape, so the module's 5-shape pool is exactly full. His MSC switches each one on while a clone stands
   there (ShieldModule(0, 2, shape, on, 1)); his down special is no longer a counter, so group 1 is never on otherwise.
3. SLOT 42 (the shield-hit event, entry 0x02EEFF18): a hit on group 1 while his clones are out (VAR_20 bit 4, his MSC
   writes it every frame) is recorded for his MSC: VAR_21 (0x0F000315) = HIT_BIAS + the hitting object's X - his X
   (through his WorkModule's set_float, the variables' hooks); his MSC turns the nearest clone into a Substitution log
   and clears VAR_21. His vanilla counter code (the rest of slot 42) is skipped for those hits, and runs as before for
   anything else.
4. SLOT 43 (the shield damage event that follows, entry 0x02EF0408): while VAR_21 holds a hit, 0 and the message's
   handled bit (no shield damage, no reaction: a clone, not his shield, took it); otherwise his vanilla code.
5. SLOT 13 (his per-frame code, entry 0x02EEE734), every frame: VAR_20 bit 1 (the ability: his name tag hidden)
   refreshes his player slot's hide counter (TAG_LIFE frames); VAR_20 bit 2 (the burnout) puts the Timer item's slow on
   him once when it starts (SlowModule [acc + 0xB8] vt +0x44: slot 3, rate 2 = half speed, SLOW_FRAMES), and clears it
   (vt +0x6C) when the bit goes off. His slot is his table entry's index (the slot's r4 is the fighter table's entry).
6. THE NAME TAG: the battle HUD's update (vtable 0x100B0718, 0x028E3FE4) places each player's cursor (the "P1" / "CPU"
   tag, ui/info/plycursor/, the per-player struct's +0x2BB0) from the player's screen position, then calls 0x03091E34;
   the bl at HUD_HOOK goes (through a trampoline at TRAMP: the HUD code is out of a branch's reach of the cave) to a stub
   that, while that player's hide counter runs, counts it down and puts the cursor far off screen (FAR, FAR) first.
   Player index = the HUD's loop index = the fighter table's slot (assumed: both are the entry order).

His MSC's side (fighters/gekkouga/README.md): VAR_20 = the flags (1 tag hidden, 2 burnout slow, 4 clones out), VAR_21 =
a clone hit (0 none), VAR_22 (v2) = a clone's hit landed (1: his hitlag). Space: CAVE-LIMIT (past Supamario's 0x04BE8000-0x04BEA000; `textregion:0x2BEC000
grow:0x04BEC000`), TRAMP (4 words of the zero run 0x037EE4DC-0x037EE550 inside copy_custom_cave.py's never-used spawn
reserve). Calls go through ctr (game functions only). Every hooked / written word is asserted against the base.
Test: tools/gekkouga_clone_cave_test.py (unicorn).
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kind_expand as K  # noqa: E402
import weapon_expand as W  # noqa: E402
import weapon_expand_append as WA  # noqa: E402
from ppcasm import Asm, ha  # noqa: E402

CAVE = 0x04BEA000
LIMIT = 0x04BEC000
TEXT_REGION = LIMIT - 0x02000000
TRAMP = 0x037EE540                # 4 words (zero in exe_v46z_ui10)

GK_KIND = 0x30                    # Greninja (fighter_param_attributes.csv CharID 48; the fighter tables' index)
CLONE_KIND = 0x1A1
CLONE_NAME = 'clone'
CLONE_BASE = 0xFE                 # bunshin (his Final Smash's clone)
MODULES_FROM = 0xF9               # shuriken
MODULE_SLOTS = (0, 2, 5, 8, 9, 11)
ART_L, ART_R = 6, 7               # the clones' article ids (his list: shuriken water tatami moon monsterball bunshin)
HIT_BITS = 0x17                   # attack-result bits that never remove a clone (0x13 hit, 0x4 shield)

# his specializer (vtable 0x101347B4: slot n's entry at +0xC + 8n)
GK_VT = 0x101347B4
SLOT13 = 0x02EEE734               # per-frame (Robin's per-frame code is his vtable's slot 13 too)
SLOT42 = 0x02EEFF18
SLOT43 = 0x02EF0408
G1_HOOK = 0x02EED92C              # his slot 0's `bl 0x02C6F5C0` (the group init: r7 the desc, r8 the group = 1)
G1_FN = 0x02C6F5C0
HUD_HOOK = 0x028E40B4             # the HUD update's `bl 0x03091E34` (r3 the cursor, r29 = 8 - player)
HUD_FN = 0x03091E34
DESC_TABLE = 0x04BAA208           # kind_expand.py's fighter descriptor cases (a pointer each)
GK_DESC = 0x10378FC8              # his fighter descriptor (0x38 bytes: +4 motion info, +8 article list)
GK_DESC_CASE = 0x02E4362C         # its case (bl getter; epilogue)
ORIGINAL = {SLOT13: 0x9421FF90, SLOT42: 0x9421FF38, SLOT43: 0x9421FF98, G1_HOOK: 0x4BD81C95,
            HUD_HOOK: 0x487ADD81, DESC_TABLE + 4 * GK_KIND: GK_DESC_CASE}

# game functions / data (none is an import)
HANDLE = 0x02BF2108               # (manager [0x102F6C30], &handle, object id, 0)
HANDLE_GONE = 0x02BEF50C          # (&handle) -> 0 while the object exists
HANDLE_POS = 0x02BEF640           # (&handle) -> its position (x at +0)
OBJ_MANAGER = 0x102F6C30
FIGHTERS = 0x1035184C             # [[FIGHTERS] + 0]: +0 the entries (0x76B0 each), +8 their count
ENTRY = 0x76B0
SLOTS = 8
OSREPORT_VENEER = 0x0288B4D4      # --diag only (diag_crumbs_cave.py's veneer)

# the fighter (the specializer's r4 is its table entry): +0x28 -> the module block, +0xC -> the module accessor
ACC = 0x28
WORK = 0x726C                     # module block -> WorkModule (vt +0x44 get_float, +0x4C set_float)
POSTURE = 0x72E4                  # module block -> PostureModule (+0x10 x)
BASE_ACC = 0xC                    # entry -> the module accessor ([+0xB8] SlowModule: vt +0x44 set slot, +0x6C clear)
SLOW_SLOT, SLOW_RATE, SLOW_FRAMES = 3, 2, 600

# the variables his MSC and this share (docs/acmd-extra-commands.md VAR_0-VAR_23: his private ones)
VAR_FLAGS = 0x0F000314            # VAR_20: 1 name tag hidden, 2 burnout slow, 4 clones out
VAR_HIT = 0x0F000315              # VAR_21: HIT_BIAS + (hitting object's X - his X); 0 = none
VAR_LAG = 0x0F000316             # VAR_22 (v2): 1 = a clone's hit landed (w_hit sets it; his MSC gives him the hitlag)
VAR_SLOT = 0x0F000300             # the clone's VAR_0 (v2): its owner's slot (1-8), its MSC writes it every frame
W_ACC = 0x28                      # weapon -> its module accessor (+0x20 StatusModule, +0x28 WorkModule)
W_WORK = 0x28
FLAG_TAG, FLAG_SLOW, FLAG_CLONES = 1, 2, 4
HIT_BIAS = 10000.0
TAG_LIFE = 4                      # HUD frames a refresh keeps the tag hidden
FAR = -100000.0                   # where a hidden cursor goes

# the clone shapes: joint 0, along his facing (z), capsules
GAP = 14.0                        # the clones' spacing (fighters/gekkouga/gekkouga.c gk_gap())
SHAPE_Z = (-2 * GAP, -GAP, GAP, 2 * GAP)
SHAPE_Y = (3.0, 15.0)
SHAPE_R = 5.5


def call(addr):
    return '''
        lis r12, 0x%X
        ori r12, r12, 0x%X
        mtctr r12
        bctrl''' % (addr >> 16, addr & 0xFFFF)


def tail(addr):
    return '''
        lis r12, 0x%X
        ori r12, r12, 0x%X
        mtctr r12
        bctr''' % (addr >> 16, addr & 0xFFFF)


def var_get(wm_reg, vid):
    return '''
        mr r3, %s
        lis r4, 0x%X
        ori r4, r4, 0x%X
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl''' % (wm_reg, vid >> 16, vid & 0xFFFF)


def var_set(wm_reg, vid):
    return '''
        mr r3, %s
        lis r4, 0x%X
        ori r4, r4, 0x%X
        lwz r12, 0(r3)
        lwz r12, 0x4C(r12)
        mtctr r12
        bctrl''' % (wm_reg, vid >> 16, vid & 0xFFFF)


def fmt_words(text):
    b = text.encode() + b'\0'
    b += b'\0' * (-len(b) % 4)
    return ''.join('\n        .word 0x%08X' % int.from_bytes(b[i:i + 4], 'big') for i in range(0, len(b), 4))


def osr():
    return '''
        lis r12, 0x%X
        ori r12, r12, 0x%X
        mtctr r12
        .word 0x4CC63182
        bctrl''' % (OSREPORT_VENEER >> 16, OSREPORT_VENEER & 0xFFFF)


class Out:
    """the words to write: {address: (word, note)}, each address once"""

    def __init__(self, img):
        self.img = img
        self.words = {}

    def put(self, addr, word, note, orig=None):
        assert addr not in self.words, 'written twice: 0x%08X (%s)' % (addr, note)
        if orig is not None:
            got = self.img.w(addr)
            assert got == orig, '0x%08X is 0x%08X, expected 0x%08X (%s)' % (addr, got, orig, note)
        self.words[addr] = (word & 0xFFFFFFFF, note)

    def blob(self, addr, data, note):
        assert len(data) % 4 == 0
        for i in range(0, len(data), 4):
            self.put(addr + i, int.from_bytes(data[i:i + 4], 'big'), note)


def tables(img):
    """the weapon cave's per-kind tables (exe_v46q+): their addresses"""
    W.parse_switch = WA.parse_patched_switch
    dsw = WA.parse_patched_switch(img, W.DESC_SWITCH)
    dpairs = WA.lis_addi_pairs(img, dsw['stub'], 32)
    ssw = WA.parse_patched_switch(img, W.SINGLETON_SWITCH)
    spairs = WA.lis_addi_pairs(img, ssw['stub'], 32)
    mr = K.branch_target(W.MODULE_ROW, img.w(W.MODULE_ROW))
    mpairs = WA.lis_addi_pairs(img, mr, 24)
    t = dict(dt=dpairs[1], st=spairs[1], bt=spairs[2], rt=mpairs[0])
    assert mpairs[1] == t['bt']
    for nm, addr in W.NAME_TABLES:
        t[nm] = WA.find_table(img, addr, 4, 0x1C0)
    for nm, addr, es, _inv in W.STATIC_TABLES:
        t[nm] = WA.find_table(img, addr, es, 0x1C0)
    return t


def motion_hashes(img):
    """his fighter motion table's main-animation hashes (the descriptor's +4 motion info: {table, count})"""
    return [h for h, _f in motion_entries(img)]


def motion_entries(img):
    """his fighter motion table's entries {hash, flags} (v2: the clones keep his flags)"""
    mi = img.w(GK_DESC + 4)
    tbl, n = img.w(mi), img.w(mi + 4)
    return [(img.w(tbl + 8 * i), img.w(tbl + 8 * i + 4)) for i in range(n)]


def motion_parts(img):
    """his motion info's words 2-5: {parts list, count, groups list, count} (v2: the clones' hand / face parts)"""
    mi = img.w(GK_DESC + 4)
    return [img.w(mi + 4 * i) for i in range(2, 6)]


def layout(img):
    """what the cave writes, read from the base: the sizes / sources of the data blocks"""
    bdesc = W.descriptor_of(img, CLONE_BASE)
    descs = W.all_descriptors(img)
    nxt = [x for x in descs if x > bdesc]
    dsize = min(W.DESC_COPY_MAX, (nxt[0] - bdesc) if nxt else W.DESC_COPY_MAX)
    dsize -= dsize % 4
    _sat, svt, svt2 = W.singleton_of(img, CLONE_BASE)
    assert svt2 is None, 'bunshin has a vtable 2'
    alist = img.w(GK_DESC + 8)
    aents, acount = img.w(alist), img.w(alist + 4)
    assert acount == 6 and [img.w(aents + 16 * i) for i in range(acount)] == [0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE]
    rows = [[img.w(aents + 16 * i + 4 * j) for j in range(4)] for i in range(acount)]
    rows += [[CLONE_KIND, 1, 0, 0], [CLONE_KIND, 1, 0, 0]]
    mrow = [img.w(W.MODULE_TABLE + 0x70 * CLONE_BASE + 4 * j) for j in range(28)]
    for s in MODULE_SLOTS:
        mrow[s] = img.w(W.MODULE_TABLE + 0x70 * MODULES_FROM + 4 * s)
    return dict(bdesc=bdesc, bminfo=img.w(bdesc + 8), dsize=dsize, svt=svt, vsize=W.vtable_size(img, svt),
                old_hit=img.w(svt + W.HIT_METHOD), hashes=motion_hashes(img), ents=motion_entries(img),
                parts=motion_parts(img), rows=rows, mrow=mrow)


def build(rpx, diag=False):
    """(Out, info): every word, asserted against the base"""
    img = K.Image(rpx)
    out = Out(img)
    end = img.text_end()
    assert end <= CAVE, 'the cave space 0x%08X is in use (text ends 0x%08X)' % (CAVE, end)
    for x in range(TRAMP, TRAMP + 16, 4):
        assert img.w(x) == 0, 'trampoline word 0x%08X not free' % x
    assert img.w(GK_DESC) == GK_KIND, 'his descriptor'
    assert K.branch_target(GK_DESC_CASE, img.w(GK_DESC_CASE)) == 0x02EF1B78, 'his descriptor case'
    for s, fn in ((13, SLOT13), (42, SLOT42), (43, SLOT43)):
        assert img.w(GK_VT + 0xC + 8 * s) == fn, 'his vtable slot %d' % s
    T = tables(img)
    k = CLONE_KIND - W.OLD_N
    assert img.w(T['bt'] + 4 * k) == 0xFFFF and img.w(T['dt'] + 4 * k) == 0, 'kind 0x%X in use' % CLONE_KIND
    assert img.w(T['st'] + 4 * k) == 0 and img.w(T['rt'] + 4 * k) == 0, 'kind 0x%X in use' % CLONE_KIND
    for nm, addr in W.NAME_TABLES:
        assert img.w(T[nm] + 4 * CLONE_KIND) == img.w(addr), 'name table %s: kind 0x%X in use' % (nm, CLONE_KIND)
    L = layout(img)
    owner_str = img.w(T['owner'] + 4 * 0xF9)
    assert img.cstr(owner_str) == 'gekkouga'

    # ---- data blocks first (fixed places), the code after them
    pc = CAVE

    def alloc(n, align=8):
        nonlocal pc
        pc = (pc + align - 1) & ~(align - 1)
        at = pc
        pc += n
        return at
    A = {}
    A['w_ents'] = alloc(8 * len(L['hashes']))
    A['w_minfo'] = alloc(W.MINFO_SIZE)
    A['w_desc'] = alloc(L['dsize'])
    A['w_vt'] = alloc(L['vsize'])
    A['w_single'] = alloc(8)
    A['w_row'] = alloc(0x70)
    A['gk_list'] = alloc(8 + 16 * len(L['rows']))
    A['gk_desc'] = alloc(0x38)
    A['g1_desc'] = alloc(12)
    A['g1_shapes'] = alloc(0x20 * len(SHAPE_Z))
    A['gk_hide'] = alloc(4 * SLOTS)
    A['gk_slow'] = alloc(4 * SLOTS)
    assert A['gk_slow'] == A['gk_hide'] + 0x20
    A['consts'] = alloc(20)          # 0.0, 0.5, HIT_BIAS, FAR, 1.0
    A['gk_str'] = alloc(8)
    fmts = [('gk_ft', 'S4GT slot=%d hide=%d\n'), ('gk_fs', 'S4GS slot=%d slow=%d\n'),
            ('gk_f42', 'S4GH clone hit dx=%d\n'), ('gk_f43', 'S4GV shield damage vetoed\n'),
            ('gk_fl', 'S4GL clone hit landed: owner slot %d hitlag\n')]
    for nm, s in fmts:
        A[nm] = alloc((len(s) + 4) & ~3, 4) if diag else 0
    code_at = alloc(0, 4)

    # weapon motion entries / info / descriptor / vtable / singleton / row
    out.blob(A['w_ents'], b''.join(struct.pack('>II', h, f) for h, f in L['ents']), 'clone motions (his body + flags)')
    mi = bytearray(img.blob(L['bminfo'], W.MINFO_SIZE))
    struct.pack_into('>II', mi, 0, A['w_ents'], len(L['hashes']))
    struct.pack_into('>4I', mi, 8, *L['parts'])       # v2: his parts (hands, face) and groups
    out.blob(A['w_minfo'], bytes(mi), 'clone motion info')
    d = bytearray(img.blob(L['bdesc'], L['dsize']))
    struct.pack_into('>I', d, 8, A['w_minfo'])
    if struct.unpack_from('>I', d, 0x1C)[0] == CLONE_BASE:
        struct.pack_into('>I', d, 0x1C, CLONE_KIND)
    out.blob(A['w_desc'], bytes(d), 'clone descriptor (bunshin copy)')
    out.blob(A['w_single'], struct.pack('>II', A['w_vt'], 0), 'clone singleton')
    out.blob(A['w_row'], b''.join(struct.pack('>I', w) for w in L['mrow']), 'clone module row')
    out.blob(A['gk_list'], struct.pack('>II', A['gk_list'] + 8, len(L['rows'])) +
             b''.join(struct.pack('>4I', *e) for e in L['rows']), 'his article list (+ clones 6 / 7)')
    gd = bytearray(img.blob(GK_DESC, 0x38))
    struct.pack_into('>I', gd, 8, A['gk_list'])
    out.blob(A['gk_desc'], bytes(gd), 'his fighter descriptor copy')
    out.blob(A['g1_desc'], struct.pack('>III', A['g1_shapes'], len(SHAPE_Z), 1), 'clone shapes desc')
    out.blob(A['g1_shapes'], b''.join(struct.pack('>7fI', 0.0, SHAPE_Y[0], z, 0.0, SHAPE_Y[1], z, SHAPE_R, 0x200)
                                      for z in SHAPE_Z), 'clone shapes (joint 0, capsules)')
    out.blob(A['gk_hide'], bytes(8 * SLOTS), 'hide counters / slow states')
    out.blob(A['consts'], struct.pack('>5f', 0.0, 0.5, HIT_BIAS, FAR, 1.0), 'constants')
    out.blob(A['gk_str'], CLONE_NAME.encode().ljust(8, b'\0'), '"clone"')
    if diag:
        for nm, s in fmts:
            b = s.encode() + b'\0'
            out.blob(A[nm], b + b'\0' * (-len(b) % 4), nm)

    p = dict(acc=ACC, work=WORK, posture=POSTURE, bacc=BASE_ACC, entry=ENTRY, slots=SLOTS, tag=FLAG_TAG,
             slow=FLAG_SLOW, clones=FLAG_CLONES, life=TAG_LIFE, sslot=SLOW_SLOT, srate=SLOW_RATE, sframes=SLOW_FRAMES,
             hitbits=HIT_BITS, wacc=W_ACC, wwork=W_WORK, s13b=SLOT13 + 4, s42b=SLOT42 + 4, s43b=SLOT43 + 4)
    for nm in ('g1_desc', 'gk_hide', 'gk_desc', 'w_desc', 'gk_ft', 'gk_fs', 'gk_f42', 'gk_f43', 'gk_fl'):
        p[nm + '_hi'], p[nm + '_lo'] = ha(A[nm]), K.slo(A[nm])
    for i, nm in enumerate(('zero', 'half', 'bias', 'far', 'one')):
        p[nm + '_hi'], p[nm + '_lo'] = ha(A['consts'] + 4 * i), K.slo(A['consts'] + 4 * i)
    p['ftab_hi'], p['ftab_lo'] = ha(FIGHTERS), K.slo(FIGHTERS)
    p['mgr_hi'], p['mgr_lo'] = ha(OBJ_MANAGER), K.slo(OBJ_MANAGER)
    D = (lambda s: s) if diag else (lambda s: '')

    src = '''
# ---- his slot 0's group-1 init: our 4-shape desc (G1_HOOK's bl comes here; r8 = 1 the group, the rest the game's)
g1_stub:
        lis r7, %(g1_desc_hi)d
        addi r7, r7, %(g1_desc_lo)d''' + tail(G1_FN) + '''

# ---- the HUD's cursor update (HUD_HOOK -> TRAMP -> here; r3 the cursor, r29 = 8 - player, LR back into the HUD)
hud:    li r12, 8
        subf r12, r29, r12              # the player (r12 = 8 - r29)
        cmplwi r12, %(slots)d
        bge hud_go
        slwi r12, r12, 2
        lis r11, %(gk_hide_hi)d
        addi r11, r11, %(gk_hide_lo)d
        lwzx r10, r11, r12
        cmpwi r10, 0
        beq hud_go
        addi r10, r10, -1               # (r10: addi from r0 would read 0)
        stwx r10, r11, r12
        lis r11, %(far_hi)d
        lfs f0, %(far_lo)d(r11)
        stfs f0, 8(r3)
        stfs f0, 0xC(r3)
hud_go:''' + tail(HUD_FN) + '''

# ---- slot 13: his per-frame code (r3 specializer, r4 his table entry)
s13:    stwu r1, -0x50(r1)
        mflr r0
        stw r0, 0x54(r1)
        stmw r25, 0x34(r1)
        stw r3, 0x8(r1)
        stw r4, 0xC(r1)
        stw r5, 0x10(r1)
        mr r31, r4
        lis r12, %(ftab_hi)d
        lwz r12, %(ftab_lo)d(r12)
        cmpwi r12, 0
        beq s13_out
        lwz r12, 0(r12)
        cmpwi r12, 0
        beq s13_out
        lwz r12, 0(r12)                 # the entries
        subf r11, r12, r31              # r31 - r12
        li r10, %(entry)d
        divwu r27, r11, r10             # his slot
        cmplwi r27, %(slots)d
        bge s13_out
        mullw r10, r27, r10
        cmpw r10, r11
        bne s13_out
        lwz r29, %(acc)d(r31)
        lwz r28, %(work)d(r29)''' + var_get('r28', VAR_FLAGS) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r26, 0x1C(r1)               # the flags
        lis r25, %(gk_hide_hi)d
        addi r25, r25, %(gk_hide_lo)d
        slwi r12, r27, 2
        andi. r0, r26, %(tag)d
        beq s13_slow''' + D('''
        lwzx r0, r25, r12
        cmpwi r0, 0
        bne s13_tagon
        lis r3, %(gk_ft_hi)d
        addi r3, r3, %(gk_ft_lo)d
        mr r4, r27
        li r5, 1''' + osr() + '''
        slwi r12, r27, 2
s13_tagon:''') + '''
        li r0, %(life)d
        stwx r0, r25, r12
s13_slow:
        addi r25, r25, 0x20             # the slow states
        lwzx r10, r25, r12
        andi. r0, r26, %(slow)d
        beq s13_slowoff
        cmpwi r10, 0
        bne s13_out
        li r0, 1
        stwx r0, r25, r12
        lwz r12, %(bacc)d(r31)
        lwz r3, 0xB8(r12)               # his SlowModule: the Timer's slot, half speed
        cmpwi r3, 0
        beq s13_out
        li r4, %(sslot)d
        li r5, %(srate)d
        li r6, %(sframes)d
        li r7, 0
        lis r8, 0x5000
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl''' + D('''
        lis r3, %(gk_fs_hi)d
        addi r3, r3, %(gk_fs_lo)d
        mr r4, r27
        li r5, 1''' + osr()) + '''
        b s13_out
s13_slowoff:
        cmpwi r10, 0
        beq s13_out
        li r0, 0
        stwx r0, r25, r12
        lwz r12, %(bacc)d(r31)
        lwz r3, 0xB8(r12)
        cmpwi r3, 0
        beq s13_out
        li r4, %(sslot)d
        lwz r12, 0(r3)
        lwz r12, 0x6C(r12)
        mtctr r12
        bctrl''' + D('''
        lis r3, %(gk_fs_hi)d
        addi r3, r3, %(gk_fs_lo)d
        mr r4, r27
        li r5, 0''' + osr()) + '''
s13_out:
        lwz r3, 0x8(r1)
        lwz r4, 0xC(r1)
        lwz r5, 0x10(r1)
        lmw r25, 0x34(r1)
        lwz r0, 0x54(r1)
        mtlr r0
        addi r1, r1, 0x50
        stwu r1, -0x70(r1)              # his slot 13's first word
        b %(s13b)d

# ---- slot 42: the shield-hit event (r4 his entry, r5 the message: +0x10 the record (+0x18 the object), +0x14 group)
s42:    stwu r1, -0x50(r1)
        mflr r0
        stw r0, 0x54(r1)
        stmw r27, 0x3C(r1)
        stw r3, 0x8(r1)
        stw r4, 0xC(r1)
        stw r5, 0x10(r1)
        mr r31, r4
        mr r30, r5
        lwz r12, 0x14(r30)
        cmpwi r12, 1
        bne s42_orig
        lwz r29, %(acc)d(r31)
        lwz r28, %(work)d(r29)''' + var_get('r28', VAR_FLAGS) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r0, 0x1C(r1)
        andi. r0, r0, %(clones)d
        beq s42_orig
        lis r12, %(zero_hi)d
        lfs f13, %(zero_lo)d(r12)
        stfs f13, 0x28(r1)              # dx (0 when the object is gone)
        lis r3, %(mgr_hi)d
        lwz r3, %(mgr_lo)d(r3)
        addi r4, r1, 0x20
        lwz r12, 0x10(r30)
        lwz r5, 0x18(r12)
        li r6, 0''' + call(HANDLE) + '''
        addi r3, r1, 0x20''' + call(HANDLE_GONE) + '''
        cmpwi r3, 0
        bne s42_set
        addi r3, r1, 0x20''' + call(HANDLE_POS) + '''
        lfs f0, 0(r3)
        lwz r12, %(posture)d(r29)
        lfs f13, 0x10(r12)
        fsubs f0, f0, f13
        stfs f0, 0x28(r1)
s42_set:
        lfs f1, 0x28(r1)
        lis r12, %(bias_hi)d
        lfs f0, %(bias_lo)d(r12)
        fadds f1, f1, f0''' + var_set('r28', VAR_HIT) + D('''
        lfs f1, 0x28(r1)
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lis r3, %(gk_f42_hi)d
        addi r3, r3, %(gk_f42_lo)d
        lwz r4, 0x1C(r1)''' + osr()) + '''
        lmw r27, 0x3C(r1)
        lwz r0, 0x54(r1)
        mtlr r0
        addi r1, r1, 0x50
        blr
s42_orig:
        lwz r3, 0x8(r1)
        lwz r4, 0xC(r1)
        lwz r5, 0x10(r1)
        lmw r27, 0x3C(r1)
        lwz r0, 0x54(r1)
        mtlr r0
        addi r1, r1, 0x50
        stwu r1, -0xC8(r1)              # his slot 42's first word
        b %(s42b)d

# ---- slot 43: the shield damage event (r5 the message: +8 the handled byte) -> 0 skips it
s43:    stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stw r3, 0x8(r1)
        stw r4, 0xC(r1)
        stw r5, 0x10(r1)
        stw r31, 0x2C(r1)
        lwz r12, %(acc)d(r4)
        lwz r31, %(work)d(r12)''' + var_get('r31', VAR_HIT) + '''
        lis r12, %(half_hi)d
        lfs f0, %(half_lo)d(r12)
        fcmpu cr0, f1, f0
        ble s43_orig
        lwz r5, 0x10(r1)
        lbz r0, 8(r5)
        ori r0, r0, 1
        stb r0, 8(r5)''' + D('''
        lis r3, %(gk_f43_hi)d
        addi r3, r3, %(gk_f43_lo)d''' + osr()) + '''
        lwz r31, 0x2C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        li r3, 0
        blr
s43_orig:
        lwz r3, 0x8(r1)
        lwz r4, 0xC(r1)
        lwz r5, 0x10(r1)
        lwz r31, 0x2C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        stwu r1, -0x68(r1)              # his slot 43's first word
        b %(s43b)d

# ---- the clone article's hit-result method (its singleton vtable +0xAC): (singleton, weapon, result bits)
w_hit:  andi. r0, r5, %(hitbits)d
        beq w_base
        stwu r1, -0x30(r1)              # its attack connected / was shielded: kept (not removed), and (v2) its owner's
        mflr r0                         # VAR_22 = 1 (his MSC gives him the hitlag); the owner's slot is the clone's VAR_0
        stw r0, 0x34(r1)
        stw r31, 0x2C(r1)
        lwz r12, %(wacc)d(r4)           # the clone's module accessor
        cmpwi r12, 0
        beq w_done
        lwz r31, %(wwork)d(r12)         # its WorkModule
        cmpwi r31, 0
        beq w_done''' + var_get('r31', VAR_SLOT) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r11, 0x1C(r1)
        addi r11, r11, -1               # the owner's table index (slot 1-8)
        cmplwi r11, %(slots)d
        bge w_done
        lis r12, %(ftab_hi)d
        lwz r12, %(ftab_lo)d(r12)
        cmpwi r12, 0
        beq w_done
        lwz r12, 0(r12)
        cmpwi r12, 0
        beq w_done
        lwz r10, 8(r12)                 # the entries' count
        cmplw r11, r10
        bge w_done
        lwz r12, 0(r12)
        mulli r11, r11, %(entry)d
        add r12, r12, r11
        lbz r0, 0x1E(r12)               # live (>= 4)
        cmplwi r0, 4
        blt w_done
        lwz r12, %(acc)d(r12)
        cmpwi r12, 0
        beq w_done
        lwz r31, %(work)d(r12)          # his WorkModule
        cmpwi r31, 0
        beq w_done
        lis r12, %(one_hi)d
        lfs f1, %(one_lo)d(r12)''' + var_set('r31', VAR_LAG) + D('''
        lis r3, %(gk_fl_hi)d
        addi r3, r3, %(gk_fl_lo)d
        lwz r4, 0x1C(r1)''' + osr()) + '''
w_done: lwz r31, 0x2C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        li r3, 0
        blr
w_base:''' + tail(L['old_hit']) + '''

# ---- the fighter descriptor switch's case for him: his descriptor copy (+8 the new article list)
gk_dcase:
        lis r3, %(gk_desc_hi)d
        addi r3, r3, %(gk_desc_lo)d
        lwz r0, 0xC(r1)                 # the getter's epilogue (as the game's cases)
        mtlr r0
        addi r1, r1, 8
        blr
# ---- the weapon descriptor switch's case for the clone
w_dcase:
        lis r3, %(w_desc_hi)d
        addi r3, r3, %(w_desc_lo)d
        blr
'''
    a = Asm(code_at)
    a.asm(src % p)
    words = a.words()
    for i, w in enumerate(words):
        out.put(code_at + 4 * i, w, 'code %s' % a.items[i] if hasattr(a, 'items') else 'code')
    end = code_at + 4 * len(words)
    assert end <= LIMIT, 'cave full: 0x%08X' % end
    lab = a.labels
    # the singleton's vtable copy with our hit method
    vb = bytearray(img.blob(L['svt'], L['vsize']))
    struct.pack_into('>I', vb, W.HIT_METHOD, lab['w_hit'])
    out.blob(A['w_vt'], bytes(vb), 'clone vtable (bunshin copy, +0xAC ours)')

    # ---- hooks in place (each asserted)
    def asm1(at, text):
        return K.one(at, text)
    out.put(G1_HOOK, asm1(G1_HOOK, 'bl 0x%X' % lab['g1_stub']), 'his group-1 init: our desc', ORIGINAL[G1_HOOK])
    out.put(SLOT13, asm1(SLOT13, 'b 0x%X' % lab['s13']), 'his slot 13', ORIGINAL[SLOT13])
    out.put(SLOT42, asm1(SLOT42, 'b 0x%X' % lab['s42']), 'his slot 42', ORIGINAL[SLOT42])
    out.put(SLOT43, asm1(SLOT43, 'b 0x%X' % lab['s43']), 'his slot 43', ORIGINAL[SLOT43])
    out.put(HUD_HOOK, asm1(HUD_HOOK, 'bl 0x%X' % TRAMP), 'the HUD cursor update', ORIGINAL[HUD_HOOK])
    t = Asm(TRAMP)
    t.asm(tail(lab['hud']))
    for i, w in enumerate(t.words()):
        out.put(TRAMP + 4 * i, w, 'HUD trampoline', 0)
    out.put(DESC_TABLE + 4 * GK_KIND, lab['gk_dcase'], 'his fighter descriptor case', GK_DESC_CASE)
    # ---- the weapon cave's tables, kind 0x1A1
    for nm, addr in W.NAME_TABLES:
        v = {'owner': owner_str, 'name': A['gk_str'], 'folder': A['gk_str']}.get(nm, img.w(addr + 4 * CLONE_BASE))
        out.put(T[nm] + 4 * CLONE_KIND, v, 'table %s 0x%X' % (nm, CLONE_KIND), img.w(addr))
    for nm, addr, es, invalid in W.STATIC_TABLES:
        rd = {1: img.b, 2: img.h, 4: img.w}[es]
        v = rd(addr + es * CLONE_BASE)
        at = T[nm] + es * CLONE_KIND
        assert rd(at) == invalid, 'table %s: kind 0x%X in use' % (nm, CLONE_KIND)
        wa = at & ~3
        word = out.words[wa][0] if wa in out.words else img.w(wa)
        sh = 8 * (4 - es - (at - wa))
        mask = ((1 << (8 * es)) - 1) << sh
        word = (word & ~mask) | (v << sh)
        out.words.pop(wa, None)
        out.put(wa, word, 'table %s 0x%X' % (nm, CLONE_KIND))
    out.put(T['dt'] + 4 * k, lab['w_dcase'], 'descriptor case 0x%X' % CLONE_KIND, 0)
    out.put(T['bt'] + 4 * k, CLONE_BASE, 'base kind 0x%X' % CLONE_KIND, 0xFFFF)
    out.put(T['st'] + 4 * k, A['w_single'], 'singleton case 0x%X' % CLONE_KIND, 0)
    out.put(T['rt'] + 4 * k, (A['w_row'] - W.MODULE_TABLE) & 0xFFFFFFFF, 'own module row 0x%X' % CLONE_KIND, 0)
    info = dict(A=A, labels=lab, T=T, layout=L, end=end, owner_str=owner_str)
    return out, info


def args(rpx, diag=False):
    out, _info = build(rpx, diag)
    return ['textregion:0x%X' % TEXT_REGION, 'grow:0x%08X' % LIMIT] + \
        ['0x%08X=0x%08X' % (a, w) for a, (w, _n) in sorted(out.words.items())]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rpx', required=True)
    ap.add_argument('--diag', action='store_true')
    ap.add_argument('--info', action='store_true')
    o = ap.parse_args()
    if o.info:
        out, info = build(o.rpx, o.diag)
        for nm, at in sorted(info['A'].items(), key=lambda kv: kv[1]):
            print('%-10s 0x%08X' % (nm, at))
        for nm in ('g1_stub', 'hud', 's13', 's42', 's43', 'w_hit', 'gk_dcase', 'w_dcase'):
            print('%-10s 0x%08X' % (nm, info['labels'][nm]))
        print('end        0x%08X (limit 0x%08X), %d words' % (info['end'], LIMIT, len(out.words)))
        return
    print(' '.join(args(o.rpx, o.diag)))


if __name__ == '__main__':
    main()
