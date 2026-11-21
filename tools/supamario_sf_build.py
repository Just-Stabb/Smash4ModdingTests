#!/usr/bin/env python3
"""Supamario's Ultra Instinct v11: Soaring Fist (Dragon Ball Xenoverse 2's skill 1510_GKS_HKN) as his transformed
forward smash. Called by tools/supamario_ui_build.py (`--sf-skill DIR --sf-cmn-vfx DIR`): the values for supamario.c's
sf_* and weapons/soaringfist.c, his body scripts for the move's two motion slots, the projectile (article 0, the
fireball's slot: its MSC, scripts, motion table, a hidden model and a still motion), its effects (the skill's .eepk
effects 0 / 1 / 5 and BTL_CMN's ground hits) and sounds (the skill's SE cues 0 / 1).

What XV2's files say (tools/xv2bac.py; the BSA read in sf_bsa below; fighters/supamario/README.md "Ultra Instinct v11"):
- BCM: roots #3 / #4 / #1 / #2 play BAC 0 / 3 / 8 / 11 (the same move; 8 / 11 with a stronger early tracking), each
  with its charge entries +1 / +2: BAC 0 one punch (EAN #0, 101 frames), 1 two (EAN #1, 121), 2 three (EAN #2, 141).
  ChargeControl [0, 0, 30, 0] on 5-17 of the uncharged entry.
- Each punch (BAC Projectile items, BSA entries 0 | 1, 2 | 3, 4, 5) at 20 / 40 / 60, with the skill's effect 0 (Hkn_Fir
  on b_R_Hand) or 1 (Hkn_Fir on b_L_Hand) and skill SE cue 1 (Fire); cue 0 (Bishi) at frame 0. BcmCallback (the next
  move) from 65 / 85 / 105. BTL_CMN 120 (MHitSmk) at 1, 140 (GHitSmk) after each punch, 240 (GHit) and 220 (MHit).
- BSA (every entry alike but for its life and its BDM): speed 0 to frame 3 then 80 m/s (1.33 m a frame), a 1.2 m
  hitbox from frame 2 to its end, the skill's effect 5 (Hkn_Wav following the shot + the Hkn_Wind trace) at 1; life
  15 (entry 0), 25 (1, 2), 35 (3, 4, 5): BDM entry = BSA entry.
- BDM: entries 0 / 2 / 5 (the uncharged and the final punches) damage type 7 (a launch), victim hitstop 10, stun 110
  (the uncharged one) / 40; entries 1 / 3 / 4 (non-final) type 3 (a stagger), pushback 0.7 / 0.75, hitstop 7, stun 30.
  Damage 80 | 40 + 60 | 30 + 30 + 60 (XV2's scale).
"""
import os
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(HERE)
import acmd  # noqa: E402
import supamario_ui_anim as anim  # noqa: E402

METRE = 5.04                          # his units a metre (the earlier XV2 ports')
SS = anim.SS
# ---------------------------------------------------------------- the move's frames (XV2's, 60 fps)
MOT_START, MOT_REL = 0x246, 0x247     # specialairlwheavy_c2 / _c3: SpecialAirLwHeavy's animation, its custom-move slots
SCRIPT_START, SCRIPT_REL = 'specialairlwheavy_c2', 'specialairlwheavy_c3'
XV2_HOLD = 12                         # the charge's pose (XV2's ChargeControl 5-17); the release goes on from it
START_AT = anim.part_start('sf_start')                   # 45
HOLD_AT = anim.part_start('sf_hold')                     # 57
HOLD_N = anim.part_len('sf_hold')                        # 60: the most frames he charges (Smash 4's smash hold)
HOLD_DECIDE = XV2_HOLD                                   # status frame 12: held -> the charge, else the release
REL_AT = [anim.part_start('sf_rel%d' % k) for k in (1, 2, 3)]       # 117, 206, 315
REL_N = [anim.part_len('sf_rel%d' % k) for k in (1, 2, 3)]          # 89, 109, 129
PUNCH_XV2 = (20, 40, 60)              # the BAC's Projectile items
PUNCH = [f - XV2_HOLD for f in PUNCH_XV2]                           # 8, 28, 48 frames into the release
HAND = ('RHandN', 'LHandN', 'RHandN')  # XV2's effect 0 (b_R_Hand) / 1 (b_L_Hand) / 0
IASA = [f - XV2_HOLD for f in (65, 85, 105)]                        # XV2's BcmCallback: 53, 73, 93
HOLD_FLAG_AT = 6                      # the hold allowed from here (flag 0x2100001B, Mario's AttackS4S frame 6)
# ---------------------------------------------------------------- the charge (chosen: not in the user's spec)
LV2, LV3 = 20, 40                     # frames held for two / three punches (of Smash 4's 60)
# ---------------------------------------------------------------- the projectile (XV2's BSA)
SPEED = round(80.0 * METRE / 60.0, 3)  # 6.72 a frame
MOVE_FROM = 3
HIT_FROM = 2
SIZE = round(1.2 * METRE, 2)          # 6.05
LIFE = (15, 25, 35)                   # by level (BSA entries 0 | 1, 2 | 3, 4, 5)
X0, Y0 = 9.0, 6.5                     # where a punch starts: in front of him at his fist's height (chosen)
ARTICLE = 0                           # the fireball's slot (Mario's; Supamario never fires one: his neutral special
                                      # is the Kamehameha, article 5)
# ---------------------------------------------------------------- damage (chosen; README "Ultra Instinct v11")
FINAL = dict(Damage=14.0, Angle=50, KBG=96, FKB=0, BKB=30, HitstunMul=1.1, HitstopFrames=10, SDI=1.0, Hitlag=1.0,
             SFXLevel=2, SFXType=1)
NONFINAL_DMG = {2: 5.0, 3: 4.0}       # level 2's first punch, level 3's first two
NONFINAL = dict(Angle=0, KBG=100, FKB=10, BKB=0, HitstunMul=-20.0, HitstopFrames=7, SDI=0.5, Hitlag=0.7,
                SFXLevel=1, SFXType=1)
# ---------------------------------------------------------------- always connecting / shields (sf_hold)
REACH = SIZE + 3.0                    # a punch reaches a fighter this far short of its centre
BEHIND = 4.0
LANE_DOWN, LANE_UP = 14.0, 6.0        # a fighter's feet this far under / over his own: in the lane
GROUNDED = 0.5                        # its feet within this of his: on the ground (no pull)
MID = 5.0                             # a fighter's middle above its feet (the pull puts it on the punches' line)
PULL = 0.35                           # of the way to the lane a frame (the "windbox")
HOLD_PAD = 3.0                        # hitstun frames kept past the next punch's arrival
PUSH_NF, PUSH_F = 0.8, 2.0            # a shield's pushback speed (units a frame) as a punch reaches it
PUSH_W = 10.0                         # ... fading to 0 over this many frames
ST_GUARD_DAMAGE = 0x1E
# ---------------------------------------------------------------- effects / sounds
SKILL_EMPS = ('Hkn_Fir.emp', 'Hkn_Wav.emp')
CMN_EMPS = ('Btl_GHit.emp', 'Btl_GHitSmk.emp')
FX_SIZE = round(METRE / 8.5, 4)       # xv2_to_ptcl's 8.5 units a metre -> his 5.04 (the hitbox's size)
FIR_SIZE = FX_SIZE                    # EEPK scale 0.8-1.2: 1.0
WAV_SIZE = FX_SIZE
CMN_SIZE = FX_SIZE
SE = {'sf_bishi': ('CAR_S1510_HKN_Bishi', 0.0), 'sf_fire': ('CAR_S1510_HKN_Fire', 0.0)}
SND_CHARGE = 0x69                     # Smash 4's smash-charge sound (Mario's AttackS4Hold)
FX_IDS = {}
# BTL_CMN (EEPK type 1) per release: (XV2 frame, effect): the BAC's items
CMN_AT = {1: [(22, 'GHitSmk'), (27, 'GHit'), (31, 'GHit')],
          2: [(22, 'GHitSmk'), (23, 'GHit'), (28, 'GHit'), (41, 'GHitSmk'), (44, 'GHit'), (49, 'GHit'), (55, 'GHit')],
          3: [(22, 'MHit'), (22, 'GHitSmk'), (29, 'GHit'), (40, 'GHitSmk'), (46, 'GHit'), (50, 'GHit'), (62, 'GHitSmk'),
              (66, 'GHit'), (70, 'GHit'), (74, 'GHit')]}


def fl(v):
    return '%sf' % repr(float(v))


def msc_values(snd_charge=SND_CHARGE):
    """the SF_* names in fighters/supamario/supamario.c"""
    v = {'SF_MOT_START': '0x%X' % MOT_START, 'SF_MOT_REL': '0x%X' % MOT_REL, 'SF_START_AT': fl(START_AT),
         'SF_HOLD_AT': fl(HOLD_AT), 'SF_HOLD_N': fl(HOLD_N), 'SF_HOLD_DECIDE': fl(HOLD_DECIDE), 'SF_LV2': fl(LV2),
         'SF_LV3': fl(LV3), 'SF_SPEED': fl(SPEED), 'SF_MOVE_FROM': fl(MOVE_FROM), 'SF_X0': fl(X0), 'SF_Y': fl(Y0),
         'SF_REACH': fl(REACH), 'SF_BEHIND': fl(BEHIND), 'SF_LANE_DOWN': fl(LANE_DOWN), 'SF_LANE_UP': fl(LANE_UP),
         'SF_GROUNDED': fl(GROUNDED), 'SF_MID': fl(MID), 'SF_PULL': fl(PULL), 'SF_HOLD_PAD': fl(HOLD_PAD),
         'SF_PUSH_NF': fl(PUSH_NF), 'SF_PUSH_F': fl(PUSH_F), 'SF_PUSH_W': fl(PUSH_W),
         'SF_ST_GUARD_DAMAGE': fl(ST_GUARD_DAMAGE), 'SF_ARTICLE': '0x%X' % ARTICLE, 'SF_SND_CHARGE': '0x%X' % snd_charge}
    for k in range(3):
        v['SF_PUNCH_%d' % (k + 1)] = fl(PUNCH[k])
        v['SF_LIFE_%d' % (k + 1)] = fl(LIFE[k])
        v['SF_IASA_%d' % (k + 1)] = fl(IASA[k])
        v['SF_REL%d_AT' % (k + 1)] = fl(REL_AT[k])
        v['SF_REL%d_N' % (k + 1)] = fl(REL_N[k])
    return v


def weapon_values():
    """the SF_* names in fighters/supamario/weapons/soaringfist.c"""
    return {'SF_SPEED': fl(SPEED), 'SF_MOVE_FROM': str(MOVE_FROM), 'SF_X0': fl(X0), 'SF_Y': fl(Y0),
            'SF_LIFE_1': str(LIFE[0]), 'SF_LIFE_2': str(LIFE[1]), 'SF_LIFE_3': str(LIFE[2]),
            'SF_MAX': str(max(LIFE) + 20), 'SF_KIND': '0x41'}


def level_of(held):
    return 1 if held < LV2 else 2 if held < LV3 else 3


def code_of(level, k):
    """the custom number the punch is generated with: (level - 1) x 2 + 0 the final / 1 a non-final punch"""
    return (level - 1) * 2 + (0 if k == level - 1 else 1)


# ---------------------------------------------------------------- the projectile's ACMD
# fireball's motion.mtable: 4 slots; 0 the final punch, 1 a level-2 non-final one, 2 a level-3 non-final one (3 left)
WEAPON_SCRIPTS = ('soaringfist', 'soaringfist2', 'soaringfist3')


def motion_of(code):
    level, nonfinal = code // 2 + 1, code % 2
    return 0 if not nonfinal else (1 if level == 2 else 2)


def cmd(name, *params):
    return acmd.Command(acmd.BY_NAME[name.lower()], list(params))


def punch_box(final, level=3):
    """the punch's hitbox: an indirect hit (a projectile), never reflected or absorbed (the reflector's and absorber's
    shapes meet only reflectable / absorbable attacks: docs/native-notes.md "The masks"), shieldable"""
    import supamario_sledgehammer_build as SB
    kw = dict(FINAL) if final else dict(NONFINAL, Damage=NONFINAL_DMG[level])
    return SB.hitbox(ID=0, Part=0, Bone=0, Size=SIZE, X=0.0, Y=0.0, Z=0.0, Clang=1, Rebound=1, ShieldDamage=0,
                     **{'Direct/Indirect': 0}, Type=4, Shieldable=1, Reflectable=0, Absorbable=0, FacingRestrict=1,
                     NoGFX=0, **kw)


def weapon_game():
    return {WEAPON_SCRIPTS[0]: [cmd('frame', float(HIT_FROM)), punch_box(True)],
            WEAPON_SCRIPTS[1]: [cmd('frame', float(HIT_FROM)), punch_box(False, 2)],
            WEAPON_SCRIPTS[2]: [cmd('frame', float(HIT_FROM)), punch_box(False, 3)]}


def weapon_effect():
    """the skill's effect 5 (Hkn_Wav, PositionUpdate + RotateUpdate: following the shot) at the BSA's frame 1"""
    body = [cmd('frame', 1.0), cmd('external_graphic', FX_IDS['wav'], 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, WAV_SIZE, 1)]
    return {n: list(body) for n in WEAPON_SCRIPTS}


def write_weapon(sup, base_sup, tmp):
    """the projectile's files in sup (fighter/supamario): article 0's (the fireball's) MSC, scripts, motion table,
    hidden model and a still motion (the fireball's animation spins its root about X: the hitbox and the wave with it)"""
    import nud
    import omo
    import supamario_kame_build as kb
    src = os.path.join(base_sup, 'model/fireball/c00')
    dst = os.path.join(sup, 'model/fireball/c00')
    os.makedirs(dst, exist_ok=True)
    for fn in os.listdir(src):
        shutil.copy(os.path.join(src, fn), os.path.join(dst, fn))
    open(os.path.join(dst, 'model.nud'), 'wb').write(nud.hidden(os.path.join(src, 'model.nud')))
    still = []
    for name, data in omo.pac_read(os.path.join(base_sup, 'motion/fireball/main.pac')):
        o = omo.Omo(data)
        for n in list(o.nodes):
            pos, rot, scl = o.sample(n[1], 0)
            omo.set_node(o, n[1], [pos] * o.frames, [rot] * o.frames, [scl] * o.frames)
        still.append((name, o.encode()))
    os.makedirs(os.path.join(sup, 'motion/fireball'), exist_ok=True)
    omo.pac_write(os.path.join(sup, 'motion/fireball/main.pac'), still)
    src_c = open(os.path.join(HERE, '..', 'fighters/supamario/weapons/soaringfist.c')).read()
    for k in sorted(weapon_values(), key=len, reverse=True):
        src_c = src_c.replace(k, weapon_values()[k])
    code = '\n'.join(line.split('//')[0] for line in src_c.split('\n'))
    assert 'SF_' not in code, [w for w in code.split() if 'SF_' in w][:5]
    kb.compile_msc(src_c, os.path.join(sup, 'script/msc/fireball/fireball.mscsb'), tmp)
    wdir = os.path.join(sup, 'script/animcmd/weapon/fireball')
    os.makedirs(wdir, exist_ok=True)
    bdir = os.path.join(base_sup, 'script/animcmd/weapon/fireball')
    mt = open(os.path.join(bdir, 'motion.mtable'), 'rb').read()
    hashes = list(struct.unpack('>%dI' % (len(mt) // 4), mt))
    for i, n in enumerate(WEAPON_SCRIPTS):
        hashes[i] = acmd.crc(n)
    open(os.path.join(wdir, 'motion.mtable'), 'wb').write(struct.pack('>%dI' % len(hashes), *hashes))
    parts = {'game': weapon_game(), 'effect': weapon_effect(), 'sound': {n: [] for n in WEAPON_SCRIPTS}}
    for part, bodies in parts.items():
        f = acmd.ACMDFile.load(os.path.join(bdir, part + '.bin'))
        f.scripts = {}
        for n, body in bodies.items():
            f.scripts[acmd.crc(n)] = body + [acmd.Command(acmd.END)]
        f.save(os.path.join(wdir, part + '.bin'))
    return hashes


# ---------------------------------------------------------------- his body scripts
def timeline(events):
    out, at = [], 0
    for f, cmds in sorted(events, key=lambda e: e[0]):
        if f > at:
            out.append(cmd('frame', float(f)))
            at = f
        out += cmds
    return out


BONE = {'TransN': 0, 'RHandN': 20, 'LHandN': 16, 'HipN': 2}


def gfx(fx, bone, x, y, z, size):
    return cmd('graphic_effect2', fx, BONE[bone], float(x), float(y), float(z), 0.0, 0.0, 0.0, float(size), 0.0, 0.0,
               0.0, 0.0, 0.0, 0.0, 1)


def body_scripts(se_id, cmn_fx):
    """{script: {part: body}} for the two slots; frames are the animation's (the MSC starts each motion at a segment)"""
    hold = []
    for k in range(0, HOLD_N, 10):
        hold += [(HOLD_AT + k, [cmd('graphic_effect', 0x1000019, 0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 10.0, 0.0, 4.0,
                                    0.0, 0.0, 0.0, 0)]),
                 (HOLD_AT + k + 5, [cmd('graphic_effect2', 0x1000010, 0x11, 2.0, 3.0, 0.0, 0.0, 0.0, 0.0, 1.0, 3.0,
                                        3.0, 3.0, 0.0, 0.0, 0.0, 1)])]
    start = {'game': timeline([(START_AT + HOLD_FLAG_AT, [cmd('on_flag', 0x2100001B)])]),
             'effect': timeline([(START_AT + 1, [gfx(cmn_fx['MHitSmk'], 'TransN', 0, 0, 0, CMN_SIZE)])] + hold),
             'sound': timeline([(START_AT, [cmd('sound_effect', se_id('sf_bishi'))])]),
             'expression': timeline([(HOLD_AT, [cmd('start_charge', -1.0, -1.0, -1.0, -1.0, 0.1, -1.0, -1),
                                                cmd('rumble_loop', 0x22, 0x39)])])}
    eff, snd, exp = [], [], []
    for lv in (1, 2, 3):
        at = REL_AT[lv - 1]
        for k in range(lv):
            f = at + PUNCH[k]
            eff.append((f, [gfx(FX_IDS['fir'], 'TransN', 0, Y0, X0 - 3.0, FIR_SIZE)]))
            snd.append((f, [cmd('sound_effect', se_id('sf_fire'))]))
            exp.append((f, [cmd('rumble', 0x12 if k == lv - 1 else 0x10, 0)]))
        for xf, name in CMN_AT[lv]:
            eff.append((at + xf - XV2_HOLD, [gfx(cmn_fx[name], 'TransN', 0, 0, 0, CMN_SIZE)]))
        snd.append((at, [cmd('stop_sound_effect', SND_CHARGE)]))
    rel = {'game': [], 'effect': timeline(eff), 'sound': timeline(snd), 'expression': timeline(exp)}
    return {SCRIPT_START: start, SCRIPT_REL: rel}


# ---------------------------------------------------------------- effects
def effects(p, e, skill_dir, cmn_dir, rep):
    """the skill's EMPs (effect 0 / 1: Hkn_Fir; 5: Hkn_Wav) and BTL_CMN's GHit / GHitSmk into his bank, after every
    earlier set; FX_IDS / the returned cmn ids"""
    import xv2_to_ptcl
    out = {}
    for src, emps, prefix in ((skill_dir, SKILL_EMPS, 'PtcSupamarioSf'), (cmn_dir, CMN_EMPS, 'PtcSupamarioSf')):
        with tempfile.TemporaryDirectory() as pkg:
            for fn in os.listdir(src):
                low = fn.lower()
                if src == cmn_dir and low.endswith('.eepk') and fn != 'BTL_CMN.eepk':
                    continue
                if low.endswith(('.ean', '.bac', '.bcm', '.bsa', '.bdm', '.acb', '.awb')):
                    continue
                os.symlink(os.path.abspath(os.path.join(src, fn)), os.path.join(pkg, fn))
            old_tex, old_cone = xv2_to_ptcl.TEX_MAX, xv2_to_ptcl.CONE_STREAKS
            xv2_to_ptcl.TEX_MAX = 64
            xv2_to_ptcl.CONE_STREAKS = True
            try:
                made, log = xv2_to_ptcl.convert_package(p, pkg, prefix, emps=list(emps), strict=False)
            finally:
                xv2_to_ptcl.TEX_MAX = old_tex
                xv2_to_ptcl.CONE_STREAKS = old_cone
        for si, name, chunk in made:
            idx = e.add(si + 1)
            out.setdefault(name[len(prefix):] + '.emp', 0x03410000 | idx)
            rep[name] = {'set': si, 'emitters': [en for _b, en, _n in chunk], 'notes': [n for _b, _e, n in chunk]}
    FX_IDS.update({'fir': out['Hkn_Fir.emp'], 'wav': out['Hkn_Wav.emp']})
    return {'GHit': out['Btl_GHit.emp'], 'GHitSmk': out['Btl_GHitSmk.emp']}


# ---------------------------------------------------------------- the BSA (read for the README / tests)
def sf_bsa(path):
    """the BSA's entries: [{'life', 'move': [(start, duration, speed)], 'hit': (start, duration, size, bdm ids),
    'effect': (start, eepk type, skill id, effect id)}] (layout read from the file: header +0x12 count, +0x14 the offset
    table; an entry +0x16 its life, +0x22 its type count, +0x24 the type list (16 bytes a type: u16 type, u16, u16,
    u16 count, u32 headers, u32 data, relative to the item); type 1 movement (0x30 bytes, +4 f32 speed in m/s), type 3
    the hitbox (0x40: +0x14 f32 size in m, +0x3A / +0x3C / +0x3E the BDM entries), type 6 the effect (u16 eepk type,
    skill id, effect id))"""
    b = open(path, 'rb').read()
    n = struct.unpack_from('<H', b, 0x12)[0]
    offs = struct.unpack_from('<%dI' % n, b, struct.unpack_from('<I', b, 0x14)[0])
    out = []
    for o in offs:
        ent = {'life': struct.unpack_from('<H', b, o + 0x16)[0]}
        nt = struct.unpack_from('<H', b, o + 0x22)[0]
        tl = o + struct.unpack_from('<I', b, o + 0x24)[0]
        for k in range(nt):
            it = tl + 16 * k
            ty, _u, _u2, cnt, ho, do = struct.unpack_from('<HHHHII', b, it)
            hdr = [struct.unpack_from('<HH', b, it + ho + 4 * j) for j in range(cnt)]
            if ty == 1:
                ent['move'] = [(h[0], h[1], round(struct.unpack_from('<f', b, it + do + 0x30 * j + 4)[0], 3))
                               for j, h in enumerate(hdr)]
            elif ty == 3:
                d = it + do
                ent['hit'] = (hdr[0][0], hdr[0][1], round(struct.unpack_from('<f', b, d + 0x14)[0], 3),
                              struct.unpack_from('<3H', b, d + 0x3A))
            elif ty == 6:
                ent['effect'] = (hdr[0][0],) + struct.unpack_from('<3H', b, it + do)
        out.append(ent)
    return out
