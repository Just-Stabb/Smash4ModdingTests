#!/usr/bin/env python3
"""Fighter motion lists: script/animcmd/body/motion.mtable and the RPX's per-fighter motion tables
(docs/params/fighter_files.md "Motions").

  python3 tools/mtable.py MTABLE [--motions DIR] [--rpx RPX --kind K]   list the motion kinds
  python3 tools/mtable.py MTABLE --text OUT.txt                          the same as an editable list
  python3 tools/mtable.py --build IN.txt OUT.mtable                      write a motion.mtable
  python3 tools/mtable.py --selftest MTABLE...                           byte-exact round trip

motion.mtable: big-endian u32 per motion kind (no header): the CRC32 (zlib.crc32 of the
lower-case name) of the motion's ACMD script name in game.bin / effect.bin / sound.bin /
expression.bin; 0 = no scripts. Its length is the fighter's motion count, which must equal
the RPX table's count and fighter_param_vl group 0's entry count. Kinds 0x000-0x210 are common
to every fighter (same hashes); 0x211 on are the fighter's own (specials, final, ...).

Names: the common list below (named by hash: 294 of the 494 used common kinds), Sm4shCommand's
AnimNames.txt when found, and names taken from the fighter's animation files (--motions DIR =
the fighter's motion/body folder, or any folder of .pac files).

--rpx RPX --kind K: the executable's static motion table for fighter kind K (one per kind in
.data, found by its descriptor {kind, motion table}): per motion, the main animation's file-name
hash (zlib.crc32(name without .omo, 0xFFFFFFFF), the pack loader's key) and a flags word, and
one hash per extra part (lhand, rhand, <name>sw1, ...). Animations are found by these hashes,
not by the mtable names: a new animation must be named so it hashes to the slot's value (or
the table patched, see tools/kirby_marth_sword.py).
"""
import os
import re
import struct
import sys
import zlib

COMMON = """
Wait1 Wait2 Wait3 - - WaitItem - - - - WalkSlow WalkMiddle WalkFast walkbrake WalkBrakeR
WalkBrakeL Turn Dash Run runbrake RunBrakeR RunBrakeL TurnRun TurnRunBrake JumpSquat JumpFront
JumpFrontMini JumpBack JumpBackMini JumpAerialFront JumpAerialBack jumpaerialf1 jumpaerialf2
jumpaerialf3 jumpaerialf4 jumpaerialf5 Fall - - FallAerial - - FallSpecial - - LandingFallSpecial
DamageFall WalkFallR WalkFallL RunFallR RunFallL Squat squatwait1 squatwait2 SquatWaitItem squatf
squatb SquatRv LandingLight LandingHeavy StepJump StepPose StepPoseAir StepFall StepPoseBack - - -
- - - GuardOn Guard GuardOff GuardDamage EscapeN EscapeF EscapeB EscapeAir Rebound Attack11
Attack12 attack13 attack100start attack100 attack100end AttackDash attacks3hi attacks3 - -
attacks3lw AttackHi3 AttackLw3 attacks4hi attacks4 - attacks4lw ?AttackS4Charge AttackHi4
?AttackHi4Charge AttackLw4 - ?AttackLw4Charge AttackAirN AttackAirF AttackAirB AttackAirHi
AttackAirLw LandingAirN LandingAirF LandingAirB LandingAirHi LandingAirLw Catch CatchDash
CatchTurn CatchWait CatchAttack CatchCut ThrowF ThrowB ThrowHi ThrowLw ThrownF ThrownB ThrownHi
ThrownLw ThrownF ThrownB ThrownHi ThrownLw ThrownF ThrownB ThrownHi ThrownLw CapturePulledHi
CaptureWaitHi CaptureDamageHi CapturePulledLw CaptureWaitLw CaptureDamageLw CaptureCut CaptureJump
- - - - - - ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ?
? ? DamageHi1 DamageHi2 DamageHi3 DamageN1 DamageN2 DamageN3 DamageLw1 DamageLw2 DamageLw3
DamageAir1 DamageAir2 DamageAir3 DamageFlyHi DamageFlyN DamageFlyLw DamageFlyTop DamageFlyRoll
DamageElec DownBoundU DownWaitU DownDamageU DownDamageU3 DownEatU DownStandU DownAttackU
DownForwardU DownBackU DownSpot DownBoundD DownWaitD DownDamageD DownDamageD3 DownEatD DownStandD
DownAttackD DownForwardD DownBackD DownSpot Passive PassiveStandF PassiveStandB PassiveWall
PassiveWallJump PassiveCeil - ShieldBreakFly FuraFura ?FuraFura FuraFuraStartU FuraFuraStartD
FuraFuraEnd FuraSleepStart FuraSleepLoop FuraSleepEnd Swallowed CameraHit Pass Ottotto OttottoWait
WallDamage StopWall CeilDamage StopCeil MissFoot CliffCatch CliffWait CliffClimbQuick
CliffAttackQuick CliffEscapeQuick CliffJumpQuick1 CliffJumpQuick2 SlipDown Slip SlipWait SlipStand
SlipAttack SlipEscapeF SlipEscapeB ItemLightGet ?LightWalkGet ItemLightEat ?LightWalkEat
?LightThrowF ?LightThrowB ?LightThrowHi ?LightThrowLw ?LightThrowF ?LightThrowB ?LightThrowHi
?LightThrowLw ?LightThrowDash ?LightThrowDrop ?LightThrowAirF ?LightThrowAirB ?LightThrowAirHi
?LightThrowAirLw ?LightThrowAirF ?LightThrowAirB ?LightThrowAirHi ?LightThrowAirLw ItemHeavyGet
ItemHeavyWalk ? ? itemheavythrowf itemheavythrowb itemheavythrowhi itemheavythrowlw
itemheavythrowf4 itemheavythrowb4 itemheavythrowhi4 itemheavythrowlw4 SwordSwing1 SwordSwing3
SwordSwing4 - ?Swing4Charge SwordSwingDash BatSwing1 BatSwing3 BatSwing4 BatSwingDash
StarRodSwing1 StarRodSwing3 StarRodSwing4 - ?Swing4Charge StarRodSwingDash LipStickSwing1
LipStickSwing3 LipStickSwing4 - ?Swing4Charge LipStickSwingDash ?Swing1 ?Swing3 ?Swing4 -
?Swing4Charge ?SwingDash ClubSwing1 ClubSwing3 ClubSwing4 - ?Swing4Charge ClubSwingDash HammerWait
HammerMove HammerJump GoldenHammerWait GoldenHammerMove GoldenHammerJump Screw ScrewAir ScrewFall
DragoonGet DragoonRide ?ItemDragoonRide Big Small ShootLegsWait ?ItemLegsSlowF ?ItemLegsMiddleF
?ItemLegsFastF ?ItemLegsBrakeF ?ItemLegsDashF ?ItemLegsSlowB ?ItemLegsMiddleB ?ItemLegsFastB
?ItemLegsBrakeB ?ItemLegsDashB ?ItemLegsJumpSquat ShootLegsLanding ?ItemShoot ?ItemShootAir
?ItemShoot ?ItemShootAir ?ItemShoot ?ItemShootAir ?ItemScopeStart ?ItemScopeRapid ?ItemScopeFire
?ItemScopeEnd ScopeAirStart ScopeAirRapid ScopeAirFire ScopeAirEnd ?ItemScopeStart ?ItemScopeRapid
?ItemScopeFire ?ItemScopeEnd ?ItemScopeAirStart ?ItemScopeAirRapid ?ItemScopeAirFire
?ItemScopeAirEnd ?ItemScopeStart ?ItemScopeEnd ?ItemScopeAirStart ?ItemScopeAirEnd ?ItemShoot
DrillShootAir ?ItemShoot ?ItemShootAir GenesisGet ?ItemGenesisStart GenesisFallLegs GenesisFire
GenesisLoop GenesisEnd GenesisAirFire GenesisAirLoop GenesisAirEnd AssistItem ?ItemAssist
ItemGrassPull GekikaraWait ItemRocketBelt SwimRise SwimUp SwimUpDamage Swim SwimF SwimEnd SwimTurn
SwimDrown SwimDrownOut EntryR EntryL appealhir appealhil appealsr appealsl appeallwr appeallwl
Win1 Win1Wait Win2 Win2Wait Win3 Win3Wait Lose LadderWait LadderUp LadderDown LadderCatchR
LadderCatchL LadderCatchAirR LadderCatchAirL LadderCatchEndR LadderCatchEndL BarrelScrew ? ? ? ? ?
? ? ? ? ? ? ? ? ? ? YoshiEgg ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ?
? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? ? -
""".split()


def crc(name):
    return zlib.crc32(name.lower().encode()) & 0xFFFFFFFF


def anim_hash(name):
    return zlib.crc32(name.encode(), 0xFFFFFFFF) & 0xFFFFFFFF


def vocabulary(motions_dir=None):
    voc = {}
    here = os.path.dirname(os.path.abspath(__file__))
    an = os.path.join(here, 'Sm4shCommand', 'SM4SHCommand', 'AnimNames.txt')
    if os.path.exists(an):
        for line in open(an, encoding='utf-8', errors='replace'):
            s = line.strip()
            if s and not s.startswith('//') and '=' not in s:
                voc[crc(s)] = s
    for s in COMMON:
        if s not in ('-',) and not s.startswith('?'):
            voc[crc(s)] = s
    anims = {}
    if motions_dir:
        for root, _d, files in os.walk(motions_dir):
            for fn in files:
                if fn.endswith('.pac'):
                    for n in pac_names(os.path.join(root, fn)):
                        base = n[:-4] if n.endswith('.omo') else n
                        anims[anim_hash(base)] = (os.path.relpath(os.path.join(root, fn), motions_dir), base)
                        m = re.match(r'Fit\w+?Body[A-Z][a-z0-9]*[A-Z]\d\d(.+)$', base)
                        if m:
                            voc[crc(m.group(1))] = m.group(1)
    for move in ('N', 'S', 'Hi', 'Lw', 'AirN', 'AirS', 'AirHi', 'AirLw', 'S1', 'S2', 'S3', 'S4',
                 'AirS1', 'AirS2', 'AirS3', 'AirS4'):
        for tail in ('', 'Start', 'Loop', 'End', 'EndMax', 'Max', 'Hold', 'Hit', 'Charge', 'Shoot',
                     'Attack', 'Fall', 'Landing', 'Turn', 'Dash', 'Jump', 'Catch', 'Throw', 'Cancel'):
            s = 'Special%s%s' % (move, tail)
            voc.setdefault(crc(s), s)
    for s in list(voc.values()):          # custom-move variants: Name_c2 / _c3 / _c4
        if not re.search(r'_c\d$', s):
            for k in (2, 3, 4):
                voc.setdefault(crc('%s_c%d' % (s, k)), '%s_c%d' % (s, k))
    return voc, anims


def pac_names(path):
    b = open(path, 'rb').read()
    if b[:4] != b'KCAP':
        return []
    n = struct.unpack('>I', b[8:12])[0]
    offs = struct.unpack('>%dI' % n, b[0x10:0x10 + 4 * n])
    return [b[o:b.index(b'\0', o)].decode('latin1') for o in offs]


def read(path):
    d = open(path, 'rb').read()
    assert len(d) % 4 == 0, 'not a motion.mtable'
    return list(struct.unpack('>%dI' % (len(d) // 4), d))


def common_name(i):
    if i < len(COMMON) and COMMON[i] != '-':
        return COMMON[i] if not COMMON[i].startswith('?') else None
    return None


# ---------------------------------------------------------------- RPX motion tables

def rpx_data(rpx):
    """(base address, bytes) of the RPX's .data section"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import rpx_patch
    d, _o, _e, secs = rpx_patch.load(rpx)
    for s in secs:
        if s[1] == 1 and s[3] == 0x102F6C00:
            return s[3], bytes(rpx_patch.section_data(d, s))
    sys.exit('no .data section at 0x102F6C00')


def motion_table(rpx, kind):
    """{'desc': addr, 'count': n, 'main': [(hash, flags)], 'parts': {part id: [hash]}}"""
    base, data = rpx_data(rpx)
    n = len(data) // 4
    w = struct.unpack('>%dI' % n, data[:n * 4])
    isd = lambda a: base <= a < base + len(data)  # noqa: E731
    at = lambda a: w[(a - base) // 4]  # noqa: E731
    for i in range(n - 2):
        if w[i] == kind and isd(w[i + 1]):
            p = w[i + 1]
            tbl, cnt = at(p), at(p + 4)
            if isd(tbl) and 200 < cnt < 2000:
                main = [(at(tbl + 8 * k), at(tbl + 8 * k + 4)) for k in range(cnt)]
                parts = {}
                plist, pn = at(p + 8), at(p + 12)
                if isd(plist) and pn < 16:
                    for k in range(pn):
                        t, part = at(plist + 8 * k), at(plist + 8 * k + 4)
                        if t and isd(t):
                            parts[part] = [at(t + 4 * m) for m in range(cnt)]
                return {'desc': base + 4 * i, 'count': cnt, 'main': main, 'parts': parts}
    sys.exit('no motion table for kind %d' % kind)


# ---------------------------------------------------------------- text form

def to_text(table, voc):
    out = []
    for i, h in enumerate(table):
        name = voc.get(h) or ''
        out.append('0x%03X 0x%08X %s' % (i, h, name))
    return '\n'.join(out) + '\n'


def from_text(text):
    rows = {}
    for line in text.splitlines():
        p = line.split()
        if not p or p[0].startswith('#'):
            continue
        i = int(p[0], 0)
        if len(p) >= 2 and re.fullmatch(r'0x[0-9A-Fa-f]{1,8}|\d+', p[1]):
            h = int(p[1], 0)
            if len(p) >= 3 and h and crc(p[2]) != h:
                sys.exit('line %s: the name %s does not hash to 0x%08X' % (p[0], p[2], h))
        elif len(p) >= 2:
            h = crc(p[1])
        else:
            h = 0
        rows[i] = h
    n = max(rows) + 1 if rows else 0
    return [rows.get(i, 0) for i in range(n)]


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == '--build':
        t = from_text(open(a[1]).read())
        open(a[2], 'wb').write(struct.pack('>%dI' % len(t), *t))
        print('wrote %s (%d motions)' % (a[2], len(t)))
        return
    if a[0] == '--selftest':
        for p in a[1:]:
            t = read(p)
            voc, _ = vocabulary()
            assert from_text(to_text(t, voc)) == t
            assert struct.pack('>%dI' % len(t), *t) == open(p, 'rb').read()
        print('%d files round-trip' % len(a[1:]))
        return
    table = read(a[0])
    mdir = a[a.index('--motions') + 1] if '--motions' in a else None
    voc, anims = vocabulary(mdir)
    if '--text' in a:
        open(a[a.index('--text') + 1], 'w').write(to_text(table, voc))
        print('wrote', a[a.index('--text') + 1])
        return
    mt = None
    if '--rpx' in a:
        mt = motion_table(a[a.index('--rpx') + 1], int(a[a.index('--kind') + 1], 0))
        print('RPX motion table: descriptor 0x%08X, %d motions, parts %s'
              % (mt['desc'], mt['count'], sorted(mt['parts'])))
        if mt['count'] != len(table):
            print('!! motion.mtable has %d entries, the RPX table %d' % (len(table), mt['count']))
    named = 0
    for i, h in enumerate(table):
        name = voc.get(h)
        named += bool(name)
        hint = ''
        if not name and i < len(COMMON) and COMMON[i].startswith('?'):
            hint = '(anim %s)' % (COMMON[i][1:] or 'none: uses the grabber\'s')
        line = '0x%03X %08X %-28s %s' % (i, h, name or ('-' if not h else '?'), hint)
        if mt and i < mt['count']:
            ah, fl = mt['main'][i]
            an = anims.get(ah, (None, '%08X' % ah if ah else '-'))[1]
            extra = ' '.join('%d:%s' % (p, anims.get(v[i], (None, '%08X' % v[i] if v[i] else '-'))[1]
                                         .split('Body')[-1]) for p, v in sorted(mt['parts'].items()))
            line += '  anim %s flags 0x%X  %s' % (an, fl, extra)
        print(line.rstrip())
    print('%d motions, %d with scripts, %d named; common kinds end at 0x210' %
          (len(table), sum(1 for h in table if h), named))


if __name__ == '__main__':
    main()
