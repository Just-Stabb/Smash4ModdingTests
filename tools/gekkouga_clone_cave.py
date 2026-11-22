#!/usr/bin/env python3
"""Greninja's clones (fighters/gekkouga/README.md "Clones v1" - "Clones v3"): the native part. Prints rpx_patch.py
arguments (v3: exe_v46z_gk3; v1 / v2's exe_v46z_gk1 / gk2 were this without the later parts).

v3: the clone's u16 flags without the Final-Smash-only resource category (its files load with him); its base kind for
the weapon switches and its module row are lizardonm's (an attacking, hittable article's per-frame template); its
specializer +0x1C gives it his hurtboxes, +0x64 / +0x84 / +0x8C / +0x94 poll its damage (a hit -> his VAR_21 = 20000 +
its id), +0xAC sets his hitstop at its hit. Diag: S4GF / S4GI / S4GC / S4GU along the spawn chain.

  python3 tools/rpx_patch.py exe_v46z_ui10.rpx exe_v46z_gk3.rpx $(python3 tools/gekkouga_clone_cave.py --rpx exe_v46z_ui10.rpx)
  python3 tools/gekkouga_clone_cave.py --rpx exe_v46z_ui10_diag.rpx --diag # + the TEST ONLY OSReport lines (exe_v46z_gk3_diag)
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
import outline_cave as OL  # noqa: E402
import weapon_expand as W  # noqa: E402
import weapon_expand_append as WA  # noqa: E402
from ppcasm import Asm, ha  # noqa: E402

CAVE = 0x04BEA000
LIMIT = 0x04BF4000                # v3: 8 KB more (zero in exe_v46z_ui10: past its text); v13: 24 KB (the hit check's
                                  # projectiles / items and the swing bind filled v12's)
TEXT_REGION = LIMIT - 0x02000000
TRAMP = 0x037EE540                # 4 words (zero in exe_v46z_ui10)

GK_KIND = 0x30                    # Greninja (fighter_param_attributes.csv CharID 48; the fighter tables' index)
CLONE_KIND = 0x1A1
CLONE_NAME = 'clone'
CLONE_BASE = 0xFE                 # bunshin (his Final Smash's clone)
MODULES_FROM = 0xF9               # shuriken (v1 / v2's module row: bunshin's + these slots; v3: TEMPLATE's row)
MODULE_SLOTS = (0, 2, 5, 8, 9, 11)
TEMPLATE = 0x15C                  # v3: lizardonm (Charizard's Final Smash form): the clone's base kind for the weapon
                                  # switches (their per-kind module update templates) and its whole module row: bunshin's
                                  # modules + Kinetic, Attack, Hit, Damage, whose updates bunshin's template never runs
TEMPLATE_NAME = ('lizardon', 'lizardonm')
CATEGORY_BITS = 0x181             # u16 flags 0x80 / 0x1 / 0x100: the resource request's categories 1 / 4 / 8 (0x030C37AC);
                                  # none: 2, loaded with the fighter. Bunshin's 0x87D has 0x1 (4: the Final Smash load,
                                  # as his tatami / moon): v1 / v2's clone files were never loaded (the user's "clones
                                  # don't appear"). v3: 0x87C
FEATURES = frozenset(('attack', 'hurt', 'parts', 'bstart', 'sway', 'hitcheck', 'burn', 'skeleton'))   # v5: each risky part, built in or not (the v3 / v4 in-game crashes
# at a clone's spawn: v4's B with lizardonm's routine / row crashed inside the generate). VARIANTS: the shipped builds.
#   (none)  the safe set: base kind moon (SAFE_BASE: bunshin's per-frame template + the MSC agent's update), bunshin's
#           row + the MSC agent (slot 8): the clone's MSC runs; no attack, no hurtbox
#   attack  base kind Mario's pump (ATTACK_BASE: bunshin's template + the MSC agent + the AttackModule's update; its row
#           is bunshin's + Attack / +0x2C / the MSC agent, u16 flags 0x87C like the clone's): the clones' hitboxes work
#   hurt    base kind mewtwom (HURT_BASE: + Kinetic / Hit / Ground updates) and its row + lizardonm's DamageModule (slot
#           20); the hurtboxes (+0x1C) and the damage pollers (+0x64 ... +0x94)
#   parts   his motion parts and flags on the clone (v2's hands / face)
#   burn    burn v1: his water moves burn whoever they hit (burn_scan / burn_add / burn_tick, BURN_MOVES)
#   skeleton skeleton v1: the Running Skeleton article (needs burn): its kind, claim, collision, HP hit check, burn
#   hitcheck v12: the clone hit from his side (w_hitchk: other fighters' attack boxes against the clone's box)
#   sway    v11: the clone's swing step every frame (w_sway: his MotionModule's swing update, as his frame calls it)
#   bstart  v8: the clone's start (specializer +0x34) runs bunshin's own (0x02AF6738: black overlay, LinkModule link 3
#           attributes 0 / 0xD, EffectModule +0xB4 / +0xA4), then clears the black (ColorBlendModule vt +0x44(0), as
#           Terminate_Overlays' handler 0x02BE37B8 does); without it the start does nothing (v7)
SAFE_BASE = 0xFC                  # v5: moon (his Final Smash's moon). v4's safe build (bunshin's row and template) never
                                  # ran the clone's MSC (the user's v4 A log: no S4GC): bunshin has no MSC agent (row slot
                                  # 8, accessor +0x1C: shuriken / water / moon have it, bunshin / tatami / monsterball
                                  # don't), and its template no +0x1C update
ATTACK_BASE = 0x2                 # Mario's pump
HURT_BASE = 0x168                 # mewtwom (Mewtwo's Final Smash form)
MSC_SLOT = 8
BUNSHIN_START = 0x02AF6738        # v8 (bstart): bunshin's specializer +0x34 (singleton, weapon, init)
COLOUR_CLEAR = 0x44               # ColorBlendModule (accessor +0x38, vtable 0x10104618) vt +0x44(slot): slot off
W_COLOUR = 0x38                   # weapon accessor -> ColorBlendModule (+0x50 + 0x4C n: slot n on, +0xD9 enabled)
W_MODEL = 0x3C                    # -> ModelModule (+4 the handle: +8 a mode, +0xC the instance: +0x7DB drawn)
W_LINK = 0x68                     # -> LinkModule (+0x84 the mask: bit 7 a link with attribute 7 (parent's visibility))
W_VIS = 0xA8                      # -> VisibilityModule (+8 its own flag (MSC VisibilityModule(0x2710, v)), vt +0xA4
                                  # is_visible 0x02C77004: +8 and, through the LinkModule, the parent's)
HM_CLEAR = 0x3C                   # v9: HitModule (vtable 0x10107774) vt +0x3C: every hurtbox off (0x02C42CE4: each group,
                                  # +0x4C = 0, the collision container cleared); its lifecycle reset vt +0x34 calls it
HM_GROUPS = 0x3C                  # +0x3C its hurt groups (setup vt +0x14 0x02C42570: params +0x18; weapons 1: the generic
HM_GROUP = 0x40                   # params 0x032107B4), +0x40 the groups (0x38 each: +4 / +6 its records' start / count)
HM_COUNT = 0x4C                   # +0x4C the hurtboxes added (vt +0x4C adds)
HM_RECS = 0x48                    # +0x44 {capacity (params +0xAC: 0x14), +0x48 the records (0x40 each)}: v9 read
                                  # [+0x44] as a pointer (0x14) and C_hurt's S4GO crashed (the user's v9.1 log)
HM_OBJARR = 0x14                  # v11: +8 +0xC the container's objects (0x174 each)
HM_OBJS = 0x18                    # +8 the collision container (+0xC its objects (0x174 each), +0x10 their count)
# burn v1: the moves that burn (his motion.mtable indices: attackairn 104, attackairf 105, attacks4 95, attackhi4 99,
# attacklw4 101), each hit one instance: (motion kind, damage a tick, interval (frames), duration (frames)). A shielded
# hit: half the frames, BURN_SHIELD_DAMAGE x the damage. Totals: damage x (duration // interval) ticks. The user's
# rule: no instance, shielded or not, does less than BURN_MIN_TOTAL (3 %) over time: a shielded one whose 50 % / 20 %
# total would fall under it gets its damage a tick raised so its total is exactly 3 % (its halved duration kept);
# above the floor the 50 % / 20 % rule is exact (burn_shield_damage: the table's fifth word, used as it is)
BURN_MOVES = (
    (95, 0.4, 6, 240),            # forward smash: 0.4 % every 6 frames for 4 s = 16 %
    (99, 0.4, 6, 240),            # up smash: 16 %
    (101, 0.4, 6, 240),           # down smash: 16 % (each side that hits)
    (105, 0.3, 10, 180),          # forward air: 0.3 % every 10 frames for 3 s = 5.4 %
    (104, 0.25, 15, 180),         # neutral air (multi-hit: one each hit): 0.25 % every 15 frames for 3 s = 3 %
    (0x101A2, 0.6, 6, 360),       # skeleton v1: the Running Skeleton's explosion (key: no motion kind, its scan passes the
                                  # row): 0.6 % every 6 frames for 6 s = 36 %, the strongest (shielded 0.21 % x 30 = 6.3 %)
)
SK_BURN_KEY = 0x101A2
BURN_MIN_TOTAL = 3.0              # the user's floor for one instance, shielded or not
BURN_SHIELD_DAMAGE = 0.35         # a shielded hit: 35 % of the damage a tick (burn v1.1; v1 20 %), half the duration


def burn_shield_frames(row):
    return max(1, row[3] // 2)


def burn_shield_damage(row):
    """a shielded instance's damage a tick: 35 % (v1.1), raised so its total is at least BURN_MIN_TOTAL (the clamp)"""
    _k, dmg, interval, _frames = row
    ticks = max(1, burn_shield_frames(row) // interval)
    return max(dmg * BURN_SHIELD_DAMAGE, BURN_MIN_TOTAL / ticks)


def burn_total(row, shielded=False):
    """one instance's total percent: (damage a tick) x (ticks)"""
    _k, dmg, interval, frames = row
    if shielded:
        dmg, frames = burn_shield_damage(row), burn_shield_frames(row)
    return dmg * (frames // interval)


assert all(burn_total(m, sh) >= BURN_MIN_TOTAL - 1e-4 for m in BURN_MOVES for sh in (False, True)), \
    'a burn under %s %%' % BURN_MIN_TOTAL
BURN_CAP = 32                     # instances a victim holds at most (more are dropped)
BURN_ENTS = 16                    # attack entries scanned (hitbox ids 0-15)
BURN_CONTEXTS = 8 * 4             # his slot x 4 + 0 him / 1 / 2 a clone / 3 his skeleton (skeleton v1; burn v1: x 3)
DM_ADD = 0x74                     # DamageModule vt +0x74(0, f1): add percent (MSC DamageModule(9, %)'s op)
F_STATUS, ST_KIND = 0x20, 0x48     # burn v1.1: a fighter's accessor -> StatusModule (vtable 0x1012D42C), +0x48 its status kind
ST_DEAD, ST_DEAD_N = 0xB1, 2      # Dead 0xB1 (every KO), Rebirth 0xB2 (the respawn platform): a victim in them loses
                                  # every burn on it (the user's burn v1 test: burns ticked on after a KO)
ENT_LOG, NODE_OBJ, NODE_TYPE, MM_KIND = 0x130, 0x18, 0x23, 0x38
VAR_LATCH = 0x0F000304            # v12: the clone's VAR_4: its hit reported (w_hitchk; w_start clears it)
AM_ENTS, AM_COUNT, AM_MAX = 0x14, 0x18, 32         # AttackModule +8 container: +0xC entries, +0x10 count (cap)
ENT_SIZE, ENT_NODES, NODE_MAX = 0x174, 0x18, 64    # an entry: +0 first node, +4 count, +0x18 node pointers (cap)
NODE_ON, NODE_MIN_X, NODE_MIN_Y, NODE_MAX_X, NODE_MAX_Y = 0x3C, 0x18, 0x1C, 0x20, 0x24   # a node: on, its x / y box
TEAM_MOD = 0x6C                   # the accessor's TeamModule (+8 the team id)
HC_OBJ_SIZES = (0x76B0, 0x1E20, 0, 0, 0x3B88)   # v13: the object tables' entry sizes (categories 0 fighters, 1 weapons,
                                  # 4 items: 0x02BF4A88 / 0x02BF4B24 / 0x02BF4CF8)
HC_OBJ_MAX = 128                  # objects a category tested at most
AM_DATA, SLOT_SIZE, SLOT_DMG = 0x40, 0x84, 0x18   # AttackModule +0x40 its hitboxes' data (0x84 each, +0x18 damage)
HC_BOX = (6.0, 0.0, 18.0)         # the clone's box: x +- 6, y + 0 to y + 18 (his body: his shield-route capsules y 3 -
                                  # 15, radius 5.5)
SWING_RATE = 0x03318A10           # v12: (motion object, f1 rate): its swing's +0x90
SWING_STEP = 0x03314FB8           # (motion object): the swing set-up (first) / step
MO_SWING = 0x20                   # the motion object's swing system
VAR_BIND = 0x0F000306             # v13: the clone's VAR_6: its swing bind tried this life
SWING_NEW = 0x03327448            # v13: () -> a swing system (0xC0 from the animation heap, 0x036B53B4)
SWING_SKEL = 0x036C60E0           # (motion +0x1C, motion +0x18, swing, 9, 9, [[[motion +0x18]] +8]): the evaluator
SWING_SB = 0x036B8040             # (swing, model.sb data): the swing parser
SWING_NHB = 0x036B736C            # (swing, model.nhb data)
MI_SB, MI_NHB = 0x6FC, 0x700      # the model instance's model.sb / model.nhb data (0x034205FC copies them in)
VAR_SWAYLOG = 0x0F000305          # the clone's VAR_5 (diag): its first swing step logged
SWING_UPDATE = 0x02C67064        # v11: MotionModule's swing update (mm): a fighter's frame calls it (0x02E3543C)
W_MOTION = 0x44                   # the accessor's MotionModule (+0x14 its motion object (+0x20 the swing system, +0xF1
MM_MOTION = 0x14                  # set up), +0x38 what the swing update needs)
MM_SWING = 0x38
SWAY_MODULES = (0x18, 0x3C, 0x44, 0x48, 0x60, 0xB8)   # the accessor's modules the swing update reads (posture, model,
                                  # motion, stop, +0x60 (0x02C66254), slow): all must be there
W_POSTURE = 0x18                  # -> PostureModule (+0x10 / +0x14 / +0x18 x y z, +0x5C the scale)
FLX_INTERN = 0x032CB1B8           # v7: (atom pool [0x102FCAA4] + 0x24, char *, length) -> atom (docs: "Damage panel")
FLX_ATOM_POOL = 0x102FCAA4
FLX_FIND = 0x032CCAA0             # (clip, &atom) -> the child clip
FLX_ROTATE = 0x032CDEDC           # (clip, f1 degrees)
FLX_GOTO = 0x032CCC44             # (clip, frame 1-based): goto and play (then +0x9C = 1: stopped)
GAUGE_NAMES = ('gkgauge_mc', 'gk_ticks_mc', 'gk_dots_mc', 'gk_arcs_mc', 'gk_heavy_mc', 'gk_fill_mc')
GAUGE_SPEEDS = (0.35, -0.8, 1.5, -2.4)   # degrees a frame (tools/gekkouga_gauge_art.py LAYERS), + clockwise
MSG_HANDLE = 0x02BF2108           # v7: the SET_CURSOR handler's message route (0x02BE7C80): (manager, &handle, id, 1)
MSG_SEND = 0x02BF019C             # (&handle, &message)
MSG_KIND = 0x100FCC00             # the message's first word (its vtable: +0x14 0x02BE9724 -> +4, the type 6), as the
                                  # handler's (lis 0x1010 / addi -0x3400); v7 / v8's 0x1010CC00 was string data: no hide
TAG_RESEND = 30                   # frames between the hide messages while the tag is hidden
PANEL_VT = 0x100871D8 + 0x3C      # v6: the damage panel's update (InfoGadgetDmg vtable +0x3C: docs/native-notes.md "Damage
                                  # panel"; its relocation moved to a dead word by trait_badge_cave.py)
PANEL_PREV = 0x04B84000           # what it points at in exe_v46z_ui10: the trait badge cave (it calls the game's 0x02661808)
PANEL_KO_SET = 0x02663C54         # (panel, slot, 0-100): Little Mac's KO meter value (labels num_0 - num_10, ko)
PANEL_VISIBLE = 0x032CDFFC        # (clip, visible)
PANEL_COLOUR = 0x032CDF80         # (clip, &{u8 mul A R G B, s16 add A R G B})
FIGHTER_MANAGER = 0x102F7024
PANEL_SLOT = 0x30C0
VAR_GAUGE = 0x0F000313            # his VAR_19 (v6): mode x 1000 + 0-100 (1 charge, 2 the ability left, 3 the burnout left)
GAUGE_COLOURS = ((100, 100, 100, 100, 0, 0, 0, 0), (100, 100, 100, 100, 0, 0, 0, 0),
                 (100, 35, 70, 100, 0, 0, 0, 0), (100, 45, 45, 45, 0, 0, 0, 0))
# v7: the panel's colour multipliers are 0-100 (docs/native-notes.md "Panel alpha": 255 hid Hero's menu): v6's 0xFF
# alpha hid the meter (the user's "no bar shows")
VT_BASE = 0xFC                    # v6: the clone's specializer (its singleton's vtable) is a copy of the moon's, not
                                  # bunshin's: bunshin's +0x34 (0x02AF6738, at its start) paints the model black (its
                                  # [acc+0x38] vt +0x4C colour (0, 0, 0, 255): the Final Smash's shadow clones) and links
                                  # it to its owner; the moon's +0x34 only sets the model scale (the user's v5 "completely
                                  # black" clone)
DAMAGE_SLOT = 20
# ---- skeleton v1 (feature skeleton): Greninja's side special leaves a Running Skeleton (fighters/gekkouga/README.md
# "Skeleton v1"): a new weapon kind SK_KIND (article SK_ARTICLE), its MSC fighters/gekkouga/weapons/skeleton.c
SK_KIND = 0x1A2
SK_NAME = 'skeleton'
SK_ARTICLE = 8                    # his list: 6 articles, the clones 6 / 7, the skeleton 8
SK_MOTION = 0xB16D0064            # the hydrant's motion (its motion info's hash; motion/skeleton/main.pac is its own)
SK_LVD = 'skeleton.lvd'           # its collision: model/skeleton/c00/skeleton.lvd (tools/gekkouga_build.py skeleton_lvd)
HYDRANT = 0x12D                   # Pac-Man's fire hydrant: a weapon fighters stand on and are blocked by. Its module row
                                  # slot 5 (accessor +0x2C, the GroundModule) is its own class (ctor 0x02B387FC, vtable
                                  # SK_GM_VT): a GroundModule that makes stage grounds from an .lvd in the article's files
                                  # (0x02AC2B84) and moves their vertices (0x02AC30C0 / 0x02AC312C, commit 0x02AC3204); the
                                  # hydrant's specializer +0x3C (0x02B34508) loads "firehydrant.lvd" and makes them; Fox /
                                  # Falco's Landmaster use the same class (landmaster.lvd)
SK_GM_CTOR = 0x02BCC7FC           # its row slot 5 constructor (the hydrant's)
SK_GM_VT = 0x100ED868             # the hydrant GroundModule's vtable (the ctor's last store)
RES_MGR = 0x102F9028              # [RES_MGR] + 0x30: the resource manager (the hydrant's 0x02B3459C)
RES_GET = 0x030C40A8              # (manager, &bundle, weapon kind, 0, 0): the kind's file bundle
RES_FIND = 0x032D7140             # (&bundle, &file, name, 1): a file of it by name
RES_ASSIGN = 0x032D69B8           # (&handle, &file): GroundModule +0xEC = the .lvd
RES_FREE = 0x032D4200             # (&handle, 2): a stack handle's release
GC_MAKE = 0x02AC2B84              # (gm, 1, 0, 0): the grounds from the .lvd (+0xF0 / +0xF4, at most 2 collisions)
GC_ON = 0x02AC2EF0                # (gm, 0): on (the hydrant's call after making them)
GC_SETV = 0x02AC30C0              # (gm, vertex, &(x, y)): a vertex placed (its last position too: no carry)
GC_MOVEV = 0x02AC312C             # (gm, vertex, &(x, y)): a vertex moved (last = where it was: riders carried)
GC_COMMIT = 0x02AC3204            # (gm): the grounds' lines recomputed after the vertex moves
GC_FREE = 0x02AC29D8              # (gm): the grounds removed (the GroundModule's own end, vt +0x2C / +0x4C, does this)
SK_W, SK_B, SK_H = 6.0, 2.0, 28.0   # its collision: x +- 6, a wall each side from y + 2 up to the top, a floor on top
                                  # at y + 28 (about 1.75 x a fighter's height: Greninja's ~16)
SK_VERTS = ((-SK_W, SK_B), (-SK_W, SK_H), (SK_W, SK_H), (SK_W, SK_B))   # the .lvd's vertices (left wall, top, right wall)
SK_HP = 25.0
SK_SCALE = 2.0                    # the carrier model's scale while it runs (its stand-in body: the hydrant's top at 14.09
                                  # x 2 = the collision's top); 1.0 from its explosion / smoke on (its hitbox unscaled)
PM_SCALE = 0xE4                   # PostureModule (accessor +0x18) vt +0xE4(f1): the object's scale (the moon's start)
SK_LATCH = 16                     # attackers remembered per skeleton (one per owner slot): {accessor, entries latched}
# its VARs (its MSC reads / writes them; the executable fills 0-4, 6-9)
SK_VAR_SLOT, SK_VAR_X, SK_VAR_Y, SK_VAR_DIR = 0x0F000300, 0x0F000301, 0x0F000302, 0x0F000303
SK_VAR_DMG, SK_VAR_PHASE, SK_VAR_COL = 0x0F000304, 0x0F000305, 0x0F000306
SK_VAR_HX, SK_VAR_HY, SK_VAR_HITS, SK_VAR_LOGP = 0x0F000307, 0x0F000308, 0x0F000309, 0x0F00030A
# his VARs (his MSC writes them at the release): 15 a skeleton asked for (1), 16 / 17 the shadow's X / Y, 18 its way
GK_VAR_SKREQ, GK_VAR_SKX, GK_VAR_SKY, GK_VAR_SKDIR = 0x0F00030F, 0x0F000310, 0x0F000311, 0x0F000312
RELEASE = frozenset(('attack', 'hitcheck', 'burn', 'skeleton'))   # v13: the user's v12 F_hitcheck (clones hit, in game) + v8's B_attack;
# skeleton v1: + the Running Skeleton
VARIANTS = (('A_release', RELEASE), ('D_parts', RELEASE | {'parts'}),
            ('E_sway', RELEASE | {'sway'}))   # v13: each on the release's set (v3 - v12's hurtbox route, C_hurt, dropped:
                                  # it never met an attack)


def base_of(feats):
    return HURT_BASE if 'hurt' in feats else ATTACK_BASE if 'attack' in feats else SAFE_BASE


def row_of(img, feats):
    """the clone's module row for a feature set"""
    rw = lambda k: [img.w(W.MODULE_TABLE + 0x70 * k + 4 * j) for j in range(28)]
    dummy = lambda f: img.w(f) == 0x38600000 and img.w(f + 4) == 0x4E800020
    if 'hurt' in feats:
        r = rw(HURT_BASE)
        r[DAMAGE_SLOT] = rw(TEMPLATE)[DAMAGE_SLOT]
        return r
    r = rw(CLONE_BASE)
    donor = rw(ATTACK_BASE if 'attack' in feats else SAFE_BASE)
    for j in range(28):
        if dummy(r[j]) and not dummy(donor[j]):
            r[j] = donor[j]
    return r


VAR_GEN = 0x0F000317              # his VAR_23 (v3 diag): the last generate's result (ArticleModule 0x2710)
VAR_LOGGED = 0x0F000302           # the clone's VAR_2 (v3 diag): its first frame logged
HITSTOP_FN = 0x02C2678C           # (accessor, hitbox data, f1 damage, f2 multiplier, r5 side, r6 use its multiplier) -> frames
HITSTOP_MUL = 0x10105DCC          # the attacker handler's f1 for it (0x02C2643C: lfs f1, 0x5DCC(0x1010))
W_HIT_MOD = 0x58                  # weapon accessor -> HitModule (vt +0x4C: hurtboxes from {data, count}, 0)
W_DAMAGE = 0x54                   # -> DamageModule (vt +0x7C(0): the damage taken this frame, f1)
W_ATTACK = 0x50                   # -> AttackModule (+0x14 record arrays (0x174 each, +0x18 count), +0x40 slots 0x84)
W_STOP = 0x48                     # (a fighter's accessor too) -> StopModule (vt +0x8C(frames, 1): hitstop)
POLL_SLOTS = (0x64, 0x84, 0x8C, 0x94)   # specializer methods every frame phase calls (spec, weapon): the damage poll
VAR_ID = 0x0F000301               # the clone's VAR_1 (v3): which clone it is (1 / 2), its MSC writes it
HIT_BIAS2 = 20000.0               # v3: his VAR_21 = HIT_BIAS2 + the clone's id when a clone's hurtbox is hit
# v3: the clone's hurtboxes: his own (fighter_param_vl_gekkouga group 5, vanilla), bones as the article's joints
# (0x7D0 + his model.jtb table-0 entry); {x1 y1 z1 x2 y2 z2 radius, bone, part, height, 0, pool 2}
HURTBOXES = (
    (0.3, 0, 0, 2.2, 0, 0, 3.2, 12, 0, 1),
    (0.7, 1.4, 0, 1.5, -1.9, 0, 2.5, 19, 0, 2),
    (-0.3, 0, 0, 3.3, 0, 0, 1.2, 22, 1, 1),
    (-0.3, 0, 0, 3.3, 0, 0, 1.2, 16, 1, 1),
    (1.7, 0, 0, 3.3, 0, 0, 2.0, 8, 3, 0),
    (1.7, 0, 0, 3.3, 0, 0, 2.0, 4, 3, 0),
    (0, 0, 0, 4.0, 0, 0, 1.5, 9, 3, 0),
    (0, 0, 0, 4.0, 0, 0, 1.5, 5, 3, 0))
WEAPON_JOINT = 0x7D0


def pos_diag():
    """diag: a clone's place every 60 frames (240 poll calls: 4 phases) for its whole life (v13; v12: 30 frames, 8 logs)
    (S4GX); v8: also on its
    first frame (the 4th poll), each with its draw state (S4GM / S4GN, w_ddiag)"""
    return '''
        lwz r30, %(wwork)d(r31)
        cmpwi r30, 0
        beq wp_nopos''' + var_get('r30', 0x0F000303) + '''
        lis r12, %(one_hi)d
        lfs f0, %(one_lo)d(r12)
        fadds f1, f1, f0
        stfs f1, 0x20(r1)''' + var_set('r30', 0x0F000303) + '''
        lfs f1, 0x20(r1)
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r0, 0x1C(r1)
        cmpwi r0, 4
        beq wp_dopos
        li r12, 240                     # v13: every 60 frames, its whole life (v12: 30, its first 8)
        divwu r11, r0, r12
        mullw r11, r11, r12
        cmpw r11, r0
        bne wp_nopos
wp_dopos:
        lwz r12, 0x18(r31)              # its PostureModule: +0x10 x, +0x14 y
        cmpwi r12, 0
        beq wp_nopos
        lfs f1, 0x10(r12)
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r0, 0x1C(r1)
        stw r0, 0x10(r1)
        lfs f1, 0x14(r12)
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r0, 0x1C(r1)
        stw r0, 0x14(r1)''' + var_get('r30', VAR_ID) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lis r3, %(gk_fx_hi)d
        addi r3, r3, %(gk_fx_lo)d
        lwz r4, 0x1C(r1)
        lwz r5, 0x10(r1)
        lwz r6, 0x14(r1)''' + osr() + '''
        mr r3, r31
        lwz r4, 0x1C(r1)
        bl w_ddiag
wp_nopos:'''
HURT_CALL = '''
        cmpwi r3, 0
        beq wi_out
        lis r11, %(hurt_hi)d
        addi r11, r11, %(hurt_lo)d
        stw r11, 8(r1)
        li r0, %(nhurt)d
        stw r0, 0xC(r1)
        addi r4, r1, 8
        li r5, 0
        lwz r12, 0(r3)
        lwz r12, 0x4C(r12)
        mtctr r12
        bctrl'''


def hurt_blob():
    return b''.join(struct.pack('>7f5I', *h[:7], WEAPON_JOINT + h[7], h[8], h[9], 0, 2) for h in HURTBOXES)
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
PLYC_HOOK = 0x028E4020            # v10: the player-cursor HUD update's per-player call (bl PLYC_FN, r3 the HUD, r4 player)
PLYC_TRAMP = 0x037EE570           # 4 words (zero in exe_v46z_ui10, after ts_scene_sites_cave.py's 0x037EE550-0x037EE570):
                                  # the cave is out of a bl's reach from PLYC_HOOK
PLYC_FN = 0x028E3E18              # its per-player fade: shown only while the block's +0x2B75 byte is set
PLYC_BLK = 0x2B00                 # a player's block (the HUD + player x 0x2B00; its +0xC0 part: +0 the player id)
PLYC_SHOW = 0x2B75                # the show byte (0: the cursor fades out)
PLYC_ALPHA = 0xC0 + 0x2AB8        # its alpha now (float)
PLYC_ID = 0xC0                    # its player id (lha; -1 none)
DESC_TABLE = 0x04BAA208           # kind_expand.py's fighter descriptor cases (a pointer each)
GK_DESC = 0x10378FC8              # his fighter descriptor (0x38 bytes: +4 motion info, +8 article list)
GK_DESC_CASE = 0x02E4362C         # its case (bl getter; epilogue)
ORIGINAL = {SLOT13: 0x9421FF90, SLOT42: 0x9421FF38, SLOT43: 0x9421FF98, G1_HOOK: 0x4BD81C95,
            HUD_HOOK: 0x487ADD81, DESC_TABLE + 4 * GK_KIND: GK_DESC_CASE, 0x028E4020: 0x4BFFFDF9}

# burn v1.2: the game's clear-all chain (the slow manager's "clear every request" 0x02FB3498, which the battle set-up
# and the battle sequences' start / restart / end run: match start, match end or quit, rematch, training reset); each
# cave's clear ends with a `b` to the next, the last to CLEAR_BACK (r3 / r10 / LR kept). gk_clear joins at its end
# (OL.clear_tail) and empties the per-match state: every burn, the processed counts, the name tag hide counters, the
# slow states, the tag message countdowns (the user's burn v1.1 test: burns went on into the next match)
CLEAR_BACK = OL.CLEAR_BACK

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
VAR_GEN_CLR = 0x0F00030E          # skeleton v1: his VAR_14 = the clear-all chain's count & 7 (his MSC resets on a change)
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


def vint(wm, vid, reg):
    """an int from a variable: var_get then fctiwz into reg"""
    return var_get(wm, vid) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz %s, 0x1C(r1)''' % reg


def vnum(wm, vid, reg):
    """a variable = the int in reg (0-9: sk_nums)"""
    return '''
        lis r12, %%(sk_nums_hi)d
        addi r12, r12, %%(sk_nums_lo)d
        slwi r0, %s, 2
        lfsx f1, r12, r0''' % reg + var_set(wm, vid)


def sk_source(D, old_hit, orig94):
    """skeleton v1: the Running Skeleton's native part (fighters/gekkouga/README.md "Skeleton v1")"""
    zero = '''
        lis r12, %(zero_hi)d
        lfs f1, %(zero_lo)d(r12)'''
    return r'''
# ==== skeleton v1: the Running Skeleton (weapon kind SK_KIND, his article 8; its MSC fighters/gekkouga/weapons/
# skeleton.c). Its specializer is a copy of the moon's with +0x34 sk_start, +0x94 sk_94, +0xAC sk_hit. Its VARs: 0 its
# owner's slot (1-8, the claim), 1 / 2 / 3 where it starts and its way (copied from his VAR_16-18), 4 the damage taken,
# 5 its phase (its MSC: 1 running, 2 exploded, 3 smoked), 6 its collision (0 none, 1 made, 2 removed, 3 failed), 7 / 8
# the last hit's place, 9 the hits counted, 10 (diag) the phase logged
sk_hit: andi. r0, r5, %(hitbits)d       # its explosion connecting / shielded: not removed (its MSC removes it)
        beq skh_base
        li r3, 0
        blr
skh_base:''' + tail(old_hit) + '''

# its start (+0x34, (singleton, weapon, init)): a grounds of a last life removed, its VARs 0
sk_start:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stw r31, 0x2C(r1)
        stw r30, 0x28(r1)
        lwz r31, %(wacc)d(r4)
        cmpwi r31, 0
        beq sks_out
        mr r3, r31
        bl sk_col_free
        lwz r30, %(wwork)d(r31)
        cmpwi r30, 0
        beq sks_out''' + ''.join(zero + var_set('r30', 0x0F000300 + v) for v in range(11)) + '''
sks_out:
        lwz r30, 0x28(r1)
        lwz r31, 0x2C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# +0x94 (spec, weapon, ...): sk_frame, then the moon's method with the same arguments
sk_94:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r3, 0x08(r1)
        stw r4, 0x0C(r1)
        stw r5, 0x10(r1)
        stw r6, 0x14(r1)
        stw r7, 0x18(r1)
        stw r8, 0x1C(r1)
        stw r9, 0x20(r1)
        stw r10, 0x24(r1)
        mr r3, r4
        bl sk_frame
        lwz r3, 0x08(r1)
        lwz r4, 0x0C(r1)
        lwz r5, 0x10(r1)
        lwz r6, 0x14(r1)
        lwz r7, 0x18(r1)
        lwz r8, 0x1C(r1)
        lwz r9, 0x20(r1)
        lwz r10, 0x24(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40''' + tail(orig94) + '''

# (r3 the weapon): its frame
sk_frame:
        stwu r1, -0x90(r1)
        mflr r0
        stw r0, 0x94(r1)
        stmw r20, 0x40(r1)
        lwz r31, %(wacc)d(r3)
        cmpwi r31, 0
        beq skf_out
        lwz r30, %(wwork)d(r31)
        cmpwi r30, 0
        beq skf_out''' + vint('r30', 0x0F000300, 'r29') + '''
        cmpwi r29, 0
        bne skf_owned
        bl sk_claim                     # whose it is (his VAR_15 asked for it): its VAR_0 - 3 filled
        mr. r29, r3
        beq skf_out
skf_owned:
        addi r12, r29, -1
        cmplwi r12, %(slots)d
        bge skf_out''' + vint('r30', 0x0F000305, 'r28') + vint('r30', 0x0F000306, 'r27') + D('''
        bl sk_logphase''') + '''
        lwz r3, %(wpost)d(r31)          # its scale: SK_SCALE running (the stand-in body), 1.0 else
        cmpwi r3, 0
        beq skf_noscale
        lis r12, %(one_hi)d
        lfs f1, %(one_lo)d(r12)
        cmpwi r28, 1
        bne skf_scale
        lis r12, %(sk_k16_hi)d
        lfs f1, %(sk_k16_lo)d(r12)
skf_scale:
        lwz r12, 0(r3)
        lwz r12, %(pm_scale)d(r12)
        mtctr r12
        bctrl
skf_noscale:
        cmpwi r28, 1
        bne skf_notrun
        cmpwi r27, 0
        bne skf_have
        bl sk_col_make                  # its first running frame: the grounds made and placed
        mr r27, r3
        b skf_hits
skf_have:
        cmpwi r27, 1
        bne skf_hits
        mr r3, r31
        li r4, 0
        bl sk_col_place                 # moved with it (riders carried)
skf_hits:
        bl sk_hits
        b skf_burn
skf_notrun:
        cmpwi r28, 2
        blt skf_burn
        cmpwi r27, 1
        bne skf_burn
        mr r3, r31                      # exploded / smoked: the grounds removed (anyone on it falls)
        bl sk_col_free
        li r27, 2''' + vnum('r30', 0x0F000306, 'r27') + D('''
        lis r3, %(gk_fsf_hi)d
        addi r3, r3, %(gk_fsf_lo)d
        mr r4, r29''' + osr()) + '''
skf_burn:
        mr r3, r31                      # its explosion's hits: the skeleton row's burn on each (burn_scan)
        addi r4, r29, -1
        slwi r5, r4, 2
        addi r5, r5, 3
        lis r6, %(sk_row_hi)d
        addi r6, r6, %(sk_row_lo)d
        bl burn_scan
skf_out:
        lmw r20, 0x40(r1)
        lwz r0, 0x94(r1)
        mtlr r0
        addi r1, r1, 0x90
        blr
''' + D('''
# diag: its phase when it changes (VAR_10): S4SX owner, phase, damage x10, place
sk_logphase:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)''' + vint('r30', 0x0F00030A, 'r12') + '''
        cmpw r12, r28
        beq skl_out''' + vnum('r30', 0x0F00030A, 'r28') + var_get('r30', 0x0F000304) + '''
        lis r12, %(sk_k4_hi)d
        lfs f0, %(sk_k4_lo)d(r12)
        fmuls f1, f1, f0
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r6, 0x1C(r1)
        li r7, 0
        li r8, 0
        lwz r12, %(wpost)d(r31)
        cmpwi r12, 0
        beq skl_log
        lfs f1, 0x10(r12)
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r7, 0x1C(r1)
        lfs f1, 0x14(r12)
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r8, 0x1C(r1)
skl_log:
        mr r4, r29
        mr r5, r28
        lis r3, %(gk_fsx_hi)d
        addi r3, r3, %(gk_fsx_lo)d''' + osr() + '''
skl_out:
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
''') + '''
# (r30 its WorkModule) -> r3 its owner's slot (1-8) or 0: the first live Greninja whose VAR_15 (a skeleton asked for)
# is on: it is cleared, his VAR_16 / 17 / 18 copied to its VAR_1 / 2 / 3, its VAR_0 = his slot
sk_claim:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r26, 0x20(r1)
        li r29, 1
skc_slot:
        cmpwi r29, %(slots)d
        bgt skc_none
        mr r3, r29
        bl gk_entry
        mr. r28, r3
        beq skc_next
        lwz r0, 4(r28)
        cmpwi r0, %(gkind)d
        bne skc_next
        lwz r12, %(acc)d(r28)
        cmpwi r12, 0
        beq skc_next
        lwz r27, %(work)d(r12)
        cmpwi r27, 0
        beq skc_next''' + var_get('r27', GK_VAR_SKREQ) + '''
        lis r12, %(half_hi)d
        lfs f0, %(half_lo)d(r12)
        fcmpu cr0, f1, f0
        ble skc_next''' + zero + var_set('r27', GK_VAR_SKREQ) + var_get('r27', GK_VAR_SKX) + var_set('r30', SK_VAR_X) + \
        var_get('r27', GK_VAR_SKY) + var_set('r30', SK_VAR_Y) + var_get('r27', GK_VAR_SKDIR) + var_set('r30', SK_VAR_DIR) + \
        vnum('r30', SK_VAR_SLOT, 'r29') + D(vint('r30', SK_VAR_X, 'r5') + '''
        stw r5, 0x10(r1)''' + vint('r30', SK_VAR_Y, 'r6') + '''
        stw r6, 0x14(r1)''' + vint('r30', SK_VAR_DIR, 'r7') + '''
        lwz r5, 0x10(r1)
        lwz r6, 0x14(r1)
        mr r4, r29
        lis r3, %(gk_fss_hi)d
        addi r3, r3, %(gk_fss_lo)d''' + osr()) + '''
        mr r3, r29
        b skc_out
skc_next:
        addi r29, r29, 1
        b skc_slot
skc_none:
        li r3, 0
skc_out:
        lmw r26, 0x20(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

# (r3 an accessor) -> r3 its GroundModule when it is the hydrant's class, else 0 (a leaf)
sk_gm:  lwz r3, %(wground)d(r3)
        lis r0, 0x1000
        cmplw r3, r0
        blt skg_no
        lis r0, 0x8000
        cmplw r3, r0
        bge skg_no
        lwz r0, 0(r3)
        lis r12, %(gm_vt_hi)d
        ori r12, r12, %(gm_vt_lo)d
        cmplw r0, r12
        beqlr
skg_no: li r3, 0
        blr

# (r3 an accessor): its grounds removed (the GroundModule's own removal; nothing made: nothing)
sk_col_free:
        mflr r0
        stw r0, 4(r1)
        stwu r1, -0x10(r1)
        bl sk_gm
        cmpwi r3, 0
        beq skcf_out''' + call(GC_FREE) + '''
skcf_out:
        addi r1, r1, 0x10
        lwz r0, 4(r1)
        mtlr r0
        blr

# (r31 its accessor, r30 its WorkModule) -> r3 its collision state (1 made, 3 failed), its VAR_6: as the hydrant's
# specializer +0x3C (0x02B345A0): its kind's file bundle, SK_LVD in it, the GroundModule's +0xEC, its grounds made, placed
# at it, on; the two stack handles released
sk_col_make:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r28, 0x30(r1)
        li r28, 3
        mr r3, r31
        bl sk_gm
        mr. r29, r3
        beq skm_done
        lis r12, %(resmgr_hi)d
        lwz r12, %(resmgr_lo)d(r12)
        cmpwi r12, 0
        beq skm_done
        li r0, 0
        stw r0, 0x10(r1)
        stw r0, 0x14(r1)
        lwz r3, 0x30(r12)
        addi r4, r1, 0x10
        li r5, %(sk_kind)d
        li r6, 0
        li r7, 0''' + call(RES_GET) + '''
        addi r3, r1, 0x10
        addi r4, r1, 0x14
        lis r5, %(sk_lvd_hi)d
        addi r5, r5, %(sk_lvd_lo)d
        li r6, 1''' + call(RES_FIND) + '''
        lwz r0, 0x14(r1)
        cmpwi r0, 0
        beq skm_free
        addi r3, r29, 0xEC
        addi r4, r1, 0x14''' + call(RES_ASSIGN) + '''
        mr r3, r29
        li r4, 1
        li r5, 0
        li r6, 0''' + call(GC_MAKE) + '''
        lwz r0, 0xF0(r29)
        cmpwi r0, 0
        beq skm_free
        mr r3, r31
        li r4, 1
        bl sk_col_place
        mr r3, r29
        li r4, 0''' + call(GC_ON) + '''
        li r28, 1
skm_free:
        addi r3, r1, 0x14
        li r4, 2''' + call(RES_FREE) + '''
        addi r3, r1, 0x10
        li r4, 2''' + call(RES_FREE) + '''
skm_done:''' + vnum('r30', SK_VAR_COL, 'r28') + D('''
        li r5, 0
        cmpwi r29, 0
        beq skm_log
        lwz r5, 0xF0(r29)
skm_log:
        mr r4, r28
        lis r3, %(gk_fsc_hi)d
        addi r3, r3, %(gk_fsc_lo)d''' + osr()) + '''
        mr r3, r28
        lmw r28, 0x30(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

# (r3 its accessor, r4 1 placed / 0 moved): its collision's vertices at its place + SK_VERTS, the lines recomputed
sk_col_place:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r27, 0x2C(r1)
        mr r31, r3
        mr r30, r4
        bl sk_gm
        mr. r29, r3
        beq skp_out
        lwz r12, 0xF0(r29)              # its first ground still there (+0x160 its id, -1 none)
        cmpwi r12, 0
        beq skp_out
        lhz r0, 0x160(r12)
        cmplwi r0, 0xFFFF
        beq skp_out
        lwz r12, %(wpost)d(r31)
        cmpwi r12, 0
        beq skp_out
        lfs f0, 0x10(r12)
        stfs f0, 0x20(r1)
        lfs f0, 0x14(r12)
        stfs f0, 0x24(r1)
        li r28, 0
        lis r27, %(sk_verts_hi)d
        addi r27, r27, %(sk_verts_lo)d
skp_v:  lfs f0, 0(r27)
        lfs f1, 0x20(r1)
        fadds f0, f0, f1
        stfs f0, 0x10(r1)
        lfs f0, 4(r27)
        lfs f1, 0x24(r1)
        fadds f0, f0, f1
        stfs f0, 0x14(r1)
        mr r3, r29
        mr r4, r28
        addi r5, r1, 0x10
        cmpwi r30, 0
        beq skp_mv''' + call(GC_SETV) + '''
        b skp_n
skp_mv:''' + call(GC_MOVEV) + '''
skp_n:  addi r27, r27, 8
        addi r28, r28, 1
        cmpwi r28, %(sk_nv)d
        blt skp_v
        mr r3, r29''' + call(GC_COMMIT) + '''
skp_out:
        lmw r27, 0x2C(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

# (r31 its accessor, r30 its WorkModule, r29 its owner's slot): the opponents' attacks on it (the clone hit check's
# objects: fighters, weapons, items; his team skipped). Per attacker: its entries with an on node (sk_box: r4) and those
# over its box (r3); a hit when one over it isn't latched: the lowest such entry's damage (AttackModule +0x40 + id x
# 0x84, +0x18) added to its VAR_4 (HP = SK_HP - it), VAR_9 + 1, VAR_7 / 8 the place (the attacker's X / Y + 8 kept in
# its box), the attacker's hitlag (as the clones'), then every entry on now latched: an attack hits it once, until that
# entry goes off (a new attack). SK_LATCH attackers per skeleton (its owner's slot)
sk_hits:
        stwu r1, -0xA0(r1)
        mflr r0
        stw r0, 0xA4(r1)
        stmw r14, 0x58(r1)
        mr r19, r29
        mr r18, r30
        mr r17, r31
        lwz r12, %(wpost)d(r17)
        cmpwi r12, 0
        beq skh_out
        lis r8, %(sk_box_hi)d
        addi r8, r8, %(sk_box_lo)d
        lfs f2, 0x10(r12)
        lfs f3, 0(r8)
        fsubs f4, f2, f3
        stfs f4, 0xC(r8)                # left
        fadds f4, f2, f3
        stfs f4, 0x10(r8)               # right
        lfs f2, 0x14(r12)
        lfs f3, 4(r8)
        fadds f4, f2, f3
        stfs f4, 0x14(r8)               # bottom
        lfs f3, 8(r8)
        fadds f4, f2, f3
        stfs f4, 0x18(r8)               # top
        addi r12, r19, -1
        mulli r12, r12, %(sk_lat8)d
        lis r16, %(sk_latch_hi)d
        addi r16, r16, %(sk_latch_lo)d
        add r16, r16, r12               # its latches
        li r15, 0
skh_ref:                                # every latched attacker: entries no longer on let go
        slwi r12, r15, 3
        add r14, r16, r12
        lwz r3, 0(r14)
        cmpwi r3, 0
        beq skh_rn
        bl sk_box
        lwz r0, 4(r14)
        and r0, r0, r4
        stw r0, 4(r14)
        cmpwi r0, 0
        bne skh_rn
        stw r0, 0(r14)
skh_rn: addi r15, r15, 1
        cmpwi r15, %(sk_lat)d
        blt skh_ref
        mr r3, r19
        bl gk_entry
        mr. r27, r3                     # his entry
        beq skh_out
        li r26, -2
        lwz r12, %(bacc)d(r27)
        cmpwi r12, 0
        beq skh_cats
        lwz r12, %(team)d(r12)
        cmpwi r12, 0
        beq skh_cats
        lwz r26, 8(r12)
skh_cats:
        li r25, 0
skh_cat:
        lis r12, %(ftab_hi)d
        lwz r12, %(ftab_lo)d(r12)
        cmpwi r12, 0
        beq skh_out
        slwi r0, r25, 2
        lwzx r12, r12, r0
        lis r0, 0x1000
        cmplw r12, r0
        blt skh_ncat
        lis r0, 0x8000
        cmplw r12, r0
        bge skh_ncat
        lwz r23, 0(r12)
        lwz r22, 8(r12)
        cmplwi r22, %(obj_max)d
        ble skh_cnt
        li r22, %(obj_max)d
skh_cnt:
        li r21, 0
        lis r12, %(hcsize_hi)d
        addi r12, r12, %(hcsize_lo)d
        slwi r0, r25, 2
        lwzx r20, r12, r0
skh_obj:
        cmpw r21, r22
        bge skh_ncat
        mullw r12, r21, r20
        add r24, r23, r12
        addi r21, r21, 1
        cmpwi r25, 0
        bne skh_notme
        cmpw r24, r27
        beq skh_obj                     # him
skh_notme:
        lbz r0, 0x1E(r24)
        cmplwi r0, 4
        blt skh_obj
        lwz r24, %(bacc)d(r24)
        lis r0, 0x1000
        cmplw r24, r0
        blt skh_obj
        lis r0, 0x8000
        cmplw r24, r0
        bge skh_obj
        cmpw r24, r17
        beq skh_obj                     # itself
        lwz r12, %(team)d(r24)
        cmpwi r12, 0
        beq skh_test
        lwz r12, 8(r12)
        cmpw r12, r26
        bne skh_test
        cmpwi r25, 0
        bne skh_obj                     # a weapon / item of his team (his own, his clones', the explosion)
        cmpwi r12, -1
        bne skh_obj                     # a fighter of his team
skh_test:
        mr r3, r24
        bl sk_box
        mr. r15, r3                     # entries over it
        beq skh_obj
        mr r14, r4                      # entries on
        li r3, 0                        # its latch (r3) and the entries latched (r4)
        li r4, 0
        li r5, %(sk_lat)d
        mr r6, r16
skh_lf: lwz r0, 0(r6)
        cmpw r0, r24
        bne skh_lfn
        mr r3, r6
        lwz r4, 4(r6)
        b skh_lfd
skh_lfn:
        addi r6, r6, 8
        addi r5, r5, -1
        cmpwi r5, 0
        bne skh_lf
skh_lfd:
        andc r0, r15, r4
        cmpwi r0, 0
        beq skh_obj                     # this attack hit it already
        li r12, 0                       # the hitbox: the lowest new entry
skh_lo: srw r11, r0, r12
        andi. r11, r11, 1
        bne skh_lod
        addi r12, r12, 1
        cmpwi r12, 31
        blt skh_lo
skh_lod:
        stw r12, 0x20(r1)
        cmpwi r3, 0
        bne skh_put
        li r5, %(sk_lat)d               # a free latch (none: the first one's)
        mr r6, r16
        mr r3, r16
skh_ff: lwz r0, 0(r6)
        cmpwi r0, 0
        bne skh_ffn
        mr r3, r6
        b skh_put
skh_ffn:
        addi r6, r6, 8
        addi r5, r5, -1
        cmpwi r5, 0
        bne skh_ff
        li r4, 0
skh_put:
        or r4, r4, r14
        stw r24, 0(r3)
        stw r4, 4(r3)
        lwz r12, %(watk)d(r24)          # the damage
        lwz r12, %(am_data)d(r12)
        lis r0, 0x1000
        cmplw r12, r0
        blt skh_obj
        lwz r0, 0x20(r1)
        mulli r0, r0, %(slot_size)d
        add r4, r12, r0
        stw r4, 0x24(r1)                # its data
        lfs f1, %(slot_dmg)d(r4)
        stfs f1, 0x28(r1)''' + var_get('r18', SK_VAR_DMG) + '''
        lfs f0, 0x28(r1)
        fadds f1, f1, f0''' + var_set('r18', SK_VAR_DMG) + var_get('r18', SK_VAR_HITS) + '''
        lis r12, %(one_hi)d
        lfs f0, %(one_lo)d(r12)
        fadds f1, f1, f0''' + var_set('r18', SK_VAR_HITS) + '''
        lis r8, %(sk_box_hi)d
        addi r8, r8, %(sk_box_lo)d
        lwz r12, %(wpost)d(r24)         # the place: the attacker's, in its box
        lfs f1, 0xC(r8)
        lfs f2, 0x14(r8)
        cmpwi r12, 0
        beq skh_pl
        lfs f1, 0x10(r12)
        lfs f2, 0x14(r12)
        lis r11, %(sk_k8_hi)d
        lfs f0, %(sk_k8_lo)d(r11)
        fadds f2, f2, f0
skh_pl: lfs f0, 0xC(r8)
        fcmpu cr0, f1, f0
        bge skh_p1
        fmr f1, f0
skh_p1: lfs f0, 0x10(r8)
        fcmpu cr0, f1, f0
        ble skh_p2
        fmr f1, f0
skh_p2: lfs f0, 0x14(r8)
        fcmpu cr0, f2, f0
        bge skh_p3
        fmr f2, f0
skh_p3: lfs f0, 0x18(r8)
        fcmpu cr0, f2, f0
        ble skh_p4
        fmr f2, f0
skh_p4: stfs f2, 0x2C(r1)
        stfs f1, 0x30(r1)''' + var_set('r18', SK_VAR_HX) + '''
        lfs f1, 0x2C(r1)''' + var_set('r18', SK_VAR_HY) + '''
        lwz r4, 0x24(r1)                # the attacker's hitlag (as a clone hit)
        lfs f1, %(slot_dmg)d(r4)
        lis r12, %(hmul_hi)d
        lfs f2, %(hmul_lo)d(r12)
        mr r3, r24
        li r5, 1
        li r6, 1''' + call(HITSTOP_FN) + '''
        mr. r4, r3
        ble skh_log
        lwz r3, %(wstop)d(r24)
        cmpwi r3, 0
        beq skh_log
        li r5, 1
        lwz r12, 0(r3)
        lwz r12, 0x8C(r12)
        mtctr r12
        bctrl
skh_log:''' + D('''
        lis r12, %(sk_k4_hi)d
        lfs f0, %(sk_k4_lo)d(r12)
        lfs f1, 0x28(r1)
        fmuls f1, f1, f0
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r0, 0x1C(r1)
        stw r0, 0x34(r1)''' + var_get('r18', SK_VAR_DMG) + '''
        lis r12, %(sk_k_hi)d
        lfs f0, %(sk_k_lo)d(r12)
        fsubs f1, f0, f1
        lis r12, %(sk_k4_hi)d
        lfs f0, %(sk_k4_lo)d(r12)
        fmuls f1, f1, f0
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r0, 0x1C(r1)
        stw r0, 0x38(r1)
        lfs f1, 0x30(r1)
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r9, 0x1C(r1)
        lfs f1, 0x2C(r1)
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r10, 0x1C(r1)
        mr r4, r19
        slwi r5, r25, 4
        add r5, r5, r21
        lwz r6, 0x20(r1)
        lwz r7, 0x34(r1)
        lwz r8, 0x38(r1)
        lis r3, %(gk_fsh_hi)d
        addi r3, r3, %(gk_fsh_lo)d''' + osr()) + '''
        b skh_obj
skh_ncat:
        addi r25, r25, 1
        cmpwi r25, 2
        blt skh_cat
        bne skh_out
        li r25, 4
        b skh_cat
skh_out:
        lmw r14, 0x58(r1)
        lwz r0, 0xA4(r1)
        mtlr r0
        addi r1, r1, 0xA0
        blr

# (r3 an attacker's accessor) -> r3 its entries (hitbox ids, bits) with an on node over the skeleton's box (sk_box +0xC
# left, +0x10 right, +0x14 bottom, +0x18 top), r4 its entries with an on node (a leaf)
sk_box: mr r11, r3
        li r3, 0
        li r4, 0
        lwz r12, %(watk)d(r11)
        lis r0, 0x1000
        cmplw r12, r0
        bltlr
        lis r0, 0x8000
        cmplw r12, r0
        bgelr
        lwz r7, %(am_ents)d(r12)
        lwz r6, %(am_count)d(r12)
        lis r0, 0x1000
        cmplw r7, r0
        bltlr
        lis r0, 0x8000
        cmplw r7, r0
        bgelr
        cmplwi r6, %(am_max)d
        bgtlr
        lis r8, %(sk_box_hi)d
        addi r8, r8, %(sk_box_lo)d
        li r5, 0
sb_ent: cmpw r5, r6
        bgelr
        mulli r12, r5, %(ent_size)d
        add r12, r12, r7
        lwz r11, 0(r12)
        lwz r10, 4(r12)
        cmplwi r11, %(node_max)d
        bgt sb_next
        cmplwi r10, %(node_max)d
        bgt sb_next
        slwi r11, r11, 2
        add r11, r11, r12
        addi r11, r11, %(ent_nodes)d
        li r12, 1
        slw r12, r12, r5                # this entry's bit
sb_node:
        cmpwi r10, 0
        ble sb_next
        lwz r9, 0(r11)
        addi r11, r11, 4
        addi r10, r10, -1
        lis r0, 0x1000
        cmplw r9, r0
        blt sb_node
        lis r0, 0x8000
        cmplw r9, r0
        bge sb_node
        lbz r0, %(node_on)d(r9)
        cmpwi r0, 0
        beq sb_node
        or r4, r4, r12
        lfs f0, %(node_max_x)d(r9)
        lfs f1, 0xC(r8)
        fcmpu cr0, f0, f1
        blt sb_node
        lfs f0, %(node_min_x)d(r9)
        lfs f1, 0x10(r8)
        fcmpu cr0, f0, f1
        bgt sb_node
        lfs f0, %(node_max_y)d(r9)
        lfs f1, 0x14(r8)
        fcmpu cr0, f0, f1
        blt sb_node
        lfs f0, %(node_min_y)d(r9)
        lfs f1, 0x18(r8)
        fcmpu cr0, f0, f1
        bgt sb_node
        or r3, r3, r12
        b sb_node
sb_next:
        addi r5, r5, 1
        b sb_ent

'''


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


def layout(img, feats=None):
    """what the cave writes, read from the base: the sizes / sources of the data blocks"""
    bdesc = W.descriptor_of(img, CLONE_BASE)
    descs = W.all_descriptors(img)
    nxt = [x for x in descs if x > bdesc]
    dsize = min(W.DESC_COPY_MAX, (nxt[0] - bdesc) if nxt else W.DESC_COPY_MAX)
    dsize -= dsize % 4
    _sat, svt, svt2 = W.singleton_of(img, VT_BASE)
    assert svt2 is None, 'moon has a vtable 2'
    alist = img.w(GK_DESC + 8)
    aents, acount = img.w(alist), img.w(alist + 4)
    assert acount == 6 and [img.w(aents + 16 * i) for i in range(acount)] == [0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE]
    rows = [[img.w(aents + 16 * i + 4 * j) for j in range(4)] for i in range(acount)]
    rows += [[CLONE_KIND, 1, 0, 0], [CLONE_KIND, 1, 0, 0]]
    feats = FEATURES if feats is None else feats
    if 'skeleton' in feats:
        rows += [[SK_KIND, 1, 0, 0]]                    # skeleton v1: article 8, one at a time
    mrow = row_of(img, feats)
    assert img.w(img.w(svt + 0x1C)) == 0x4E800020, "the specializer's +0x1C: a blr"
    for j in (2, 6, 7, 20, 26):
        f = img.w(W.MODULE_TABLE + 0x70 * TEMPLATE + 4 * j)
        assert not (img.w(f) == 0x38600000 and img.w(f + 4) == 0x4E800020), 'template row slot %d empty' % j
    skrow = None
    if 'skeleton' in feats:
        assert 'burn' in feats and 'attack' in feats, 'skeleton needs burn and attack'
        skrow = list(row_of(img, feats))
        assert img.w(W.MODULE_TABLE + 0x70 * HYDRANT + 4 * 5) == SK_GM_CTOR, "the hydrant's GroundModule constructor"
        skrow[5] = SK_GM_CTOR                           # its GroundModule: the hydrant's (grounds from an .lvd)
        assert img.w(SK_GM_CTOR + 8) >> 26 == 18 and K.branch_target(SK_GM_CTOR + 8, img.w(SK_GM_CTOR + 8)) == 0x02B387FC
        for f, want in ((GC_MAKE, 0x9421F640), (GC_ON, 0x9421FFE0), (GC_SETV, 0x7C6C1B78), (GC_MOVEV, 0x7C6C1B78),
                        (GC_COMMIT, 0x7C0802A6), (GC_FREE, 0x9421FFD0)):
            assert img.w(f) == want, 'collision function 0x%08X: 0x%08X' % (f, img.w(f))
    return dict(skrow=skrow, bdesc=bdesc, bminfo=img.w(bdesc + 8), dsize=dsize, svt=svt, vsize=W.vtable_size(img, svt),
                vt_orig={o: img.w(svt + o) for o in POLL_SLOTS + (0x1C,)},
                old_hit=img.w(svt + W.HIT_METHOD), hashes=motion_hashes(img), ents=motion_entries(img),
                parts=motion_parts(img), rows=rows, mrow=mrow)


def build(rpx, diag=False, feats=None):
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
    feats = FEATURES if feats is None else frozenset(feats)
    assert feats <= FEATURES, feats
    L = layout(img, feats)
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
    skel = 'skeleton' in feats
    A['sk_ents'] = alloc(8 * 3) if skel else 0             # skeleton v1: its motion entries (3 kinds, the hydrant's motion)
    A['sk_minfo'] = alloc(W.MINFO_SIZE) if skel else 0
    A['sk_desc'] = alloc(L['dsize']) if skel else 0
    A['sk_vt'] = alloc(L['vsize']) if skel else 0
    A['sk_single'] = alloc(8) if skel else 0
    A['sk_row'] = alloc(0x70) if skel else 0
    A['sk_str'] = alloc(12) if skel else 0                 # "skeleton"
    A['sk_lvd'] = alloc(16, 4) if skel else 0              # "skeleton.lvd"
    A['sk_verts'] = alloc(8 * len(SK_VERTS), 4) if skel else 0
    A['sk_box'] = alloc(0x1C, 4) if skel else 0             # (W, 0, H) + this frame's left / right / bottom / top
    A['sk_nums'] = alloc(4 * 10, 4) if skel else 0           # 0.0 - 9.0 (ints as floats)
    A['sk_k'] = alloc(20, 4) if skel else 0                  # SK_HP, 10.0, 8.0 (the hit point's height), 0.5, SK_SCALE
    A['sk_latch'] = alloc(SLOTS * SK_LATCH * 8, 4) if skel else 0
    A['gk_desc'] = alloc(0x38)
    A['g1_desc'] = alloc(12)
    A['g1_shapes'] = alloc(0x20 * len(SHAPE_Z))
    A['gk_hide'] = alloc(4 * SLOTS)
    A['gk_slow'] = alloc(4 * SLOTS)
    A['gk_lastf'] = alloc(8 * SLOTS) if diag else 0   # diag: the flags last logged / the tag-hide logged, per slot
    A['gk_seen'] = alloc(4 * 16) if diag else 0       # diag: the HUD calls seen, by r29
    assert A['gk_slow'] == A['gk_hide'] + 0x20
    assert not diag or A['gk_lastf'] == A['gk_slow'] + 0x20
    A['ctf'] = alloc(12 * 4, 4)         # v6: the gauge's colour per mode
    A['hcbox'] = alloc(0x1C) if 'hitcheck' in feats else 0   # v12: the hit check's box (+0xC: this frame's edges)
    A['hcsize'] = alloc(4 * len(HC_OBJ_SIZES)) if 'hitcheck' in feats else 0
    burn = 'burn' in feats
    A['btab'] = alloc(SLOTS * BURN_CAP * 16) if burn else 0      # burn v1: the victims' instances
    A['bproc'] = alloc(BURN_CONTEXTS * BURN_ENTS) if burn else 0  # the hit logs' processed counts
    A['bmoves'] = alloc(20 * len(BURN_MOVES)) if burn else 0
    A['bconst'] = alloc(8) if burn else 0                        # 0.2 (shield), 1000.0
    A['bsum'] = alloc(SLOTS * SLOTS * 4) if burn and diag else 0  # diag: damage per owner x victim this second
    A['bclock'] = alloc(4 * SLOTS) if burn and diag else 0
    A['gk_clr'] = alloc(4 + 4 * SLOTS)  # burn v1.2: the clears seen (+0), per slot the count its diag last logged
    A['gk_plyr'] = alloc(4 * SLOTS)     # v10: per player, the cursor show byte we cleared + 1 (0: none)
    A['gk_tags'] = alloc(4 * SLOTS)     # v7: the tag messages' countdown per slot (0: shown)
    A['gk_names'] = alloc(8 * len(GAUGE_NAMES), 4)    # v7: the round gauge's clip names {char *, length}
    A['gk_namestr'] = alloc(sum(len(n) + 1 for n in GAUGE_NAMES) + 4, 4)
    A['gk_atoms'] = alloc(4 * len(GAUGE_NAMES), 4)
    A['gk_angles'] = alloc(16 * SLOTS, 4)             # 4 ring angles per panel slot
    A['gk_speeds'] = alloc(16, 4)
    A['gk_gaugelog'] = alloc(4 * SLOTS) if diag else 0
    A['consts'] = alloc(36)          # 0.0, 0.5, HIT_BIAS, FAR, 1.0, HIT_BIAS2, the hitstop multiplier, 100.0, 360.0
    A['hurt'] = alloc(0x30 * len(HURTBOXES))
    A['gk_str'] = alloc(8)
    fmts = [('gk_ft', 'S4GT slot=%d hide=%d\n'), ('gk_fs', 'S4GS slot=%d slow=%d\n'),
            ('gk_f42', 'S4GH clone hit dx=%d\n'), ('gk_f43', 'S4GV shield damage vetoed\n'),
            ('gk_fl', 'S4GL clone hit landed: owner slot %d hitlag %d\n'),
            ('gk_fd', 'S4GD clone %d hurt\n'),
            ('gk_ff', 'S4GF slot=%d flags=%d gen=%d\n'),
            ('gk_fi', 'S4GI clone set-up: hitmodule=%08X\n'),
            ('gk_fc', 'S4GC clone first frame: id=%d owner slot=%d\n'),
            ('gk_fu', 'S4GU tag hook: hud=%08X player=%d id=%d show byte %d -> 0, alpha %08X\n'),
            ('gk_fj', 'S4GJ clone set-up done\n'),
            ('gk_fp', 'S4GP clone first update (its script not run yet): weapon accessor=%08X\n'),
            ('gk_fv', 'S4GV HUD cursor update: r29=%d cursor=%08X\n'),
            ('gk_fx', 'S4GX clone id=%d at x=%d y=%d\n'),
            ('gk_fb', 'S4GB panel slot=%d gauge mode=%d value=%d\n'),
            ('gk_fz', 'S4GZ clone start: init=%08X scale x100=%d\n'),
            ('gk_fw', 'S4GW tag message: visible=%d object id=%d gone=%d handle=%08X\n'),
            ('gk_fm', 'S4GM clone id=%d draw: visflag=%d visible=%d model mode=%d drawn=%d overlay=%d/%d\n'),
            ('gk_fn', 'S4GN clone id=%d z=%d scale x100=%d link mask=%08X model=%08X\n'),
            ('gk_fba', 'S4BA burn added: victim slot=%d move=%d shielded=%d damage x1000=%d interval=%d frames=%d\n'),
            ('gk_fss', 'S4SS skeleton spawned: owner slot=%d at x=%d y=%d way=%d\n'),
            ('gk_fsc', 'S4SC skeleton collision: state=%d (1 made, 3 failed) grounds=%08X\n'),
            ('gk_fsf', 'S4SF skeleton collision removed: owner slot=%d\n'),
            ('gk_fsh', 'S4SH skeleton hit: owner slot=%d attacker=%X hitbox=%d damage x10=%d HP left x10=%d at x=%d y=%d\n'),
            ('gk_fsx', 'S4SX skeleton owner slot=%d phase=%d (1 running, 2 exploded, 3 smoked at 0 HP) damage taken x10=%d at x=%d y=%d\n'),
            ('gk_fbr', 'S4BR match state cleared (match start / end, training reset, restart): clear #%d, seen by slot=%d\n'),
            ('gk_fbt', 'S4BT burn ticks: owner slot=%d victim slot=%d stacks=%d damage x1000 this second=%d\n'),
            ('gk_fbk', 'S4BK burns cleared: victim slot=%d status=%X (KO: Dead / Rebirth; -1 gone) seen by owner slot=%d\n'),
            ('gk_fh', 'S4GH hit check: attacker=%X (category x 16 + index) hitbox=%d clone id=%d hitlag=%d at x=%d y=%d\n'),
            ('gk_fr', 'S4GR clone swing stage %d: %08X %08X %X %08X (0 / 1 before / after its first step: motion, swing, set up, flags; 2 bind sources: sb, nhb, own; 3 bound: motion, swing)\n'),
            ('gk_fq', 'S4GQ clone id=%d swing: motionmodule=%08X need=%08X motion=%08X swing=%08X flags=%08X set up=%d\n'),
            ('gk_fy', 'S4GY clone hurt object 0: %08X %08X %08X %08X %08X %08X\n'),
            ('gk_fk', 'S4GK clone hurtboxes set: hitmodule=%08X groups=%d boxes %d -> %d group0=%d+%d objects=%d\n'),
            ('gk_fo', 'S4GO clone id=%d hurt: boxes=%d objects=%d first record %08X %08X %08X %08X\n')]
    for nm, s in fmts:
        A[nm] = alloc((len(s) + 4) & ~3, 4) if diag else 0
    code_at = alloc(0, 4)

    # weapon motion entries / info / descriptor / vtable / singleton / row
    out.blob(A['w_ents'], b''.join(struct.pack('>II', h, f if 'parts' in feats else 0) for h, f in L['ents']),
             'clone motions (his body (+ flags))')
    mi = bytearray(img.blob(L['bminfo'], W.MINFO_SIZE))
    struct.pack_into('>II', mi, 0, A['w_ents'], len(L['hashes']))
    if 'parts' in feats:
        struct.pack_into('>4I', mi, 8, *L['parts'])   # v2: his parts (hands, face) and groups
    out.blob(A['w_minfo'], bytes(mi), 'clone motion info')
    d = bytearray(img.blob(L['bdesc'], L['dsize']))
    struct.pack_into('>I', d, 8, A['w_minfo'])
    if struct.unpack_from('>I', d, 0x1C)[0] == CLONE_BASE:
        struct.pack_into('>I', d, 0x1C, CLONE_KIND)
    out.blob(A['w_desc'], bytes(d), 'clone descriptor (bunshin copy)')
    out.blob(A['w_single'], struct.pack('>II', A['w_vt'], 0), 'clone singleton')
    out.blob(A['w_row'], b''.join(struct.pack('>I', w) for w in L['mrow']), 'clone module row')
    if skel:
        out.blob(A['sk_ents'], struct.pack('>6I', SK_MOTION, 0, SK_MOTION, 0, SK_MOTION, 0),
                 'skeleton motions (run / explode / smoke: the hydrant\'s animation)')
        mi2 = bytearray(img.blob(L['bminfo'], W.MINFO_SIZE))
        struct.pack_into('>II', mi2, 0, A['sk_ents'], 3)
        out.blob(A['sk_minfo'], bytes(mi2), 'skeleton motion info')
        d2 = bytearray(img.blob(L['bdesc'], L['dsize']))
        struct.pack_into('>I', d2, 8, A['sk_minfo'])
        if struct.unpack_from('>I', d2, 0x1C)[0] == CLONE_BASE:
            struct.pack_into('>I', d2, 0x1C, SK_KIND)
        out.blob(A['sk_desc'], bytes(d2), 'skeleton descriptor (bunshin copy)')
        out.blob(A['sk_single'], struct.pack('>II', A['sk_vt'], 0), 'skeleton singleton')
        out.blob(A['sk_row'], b''.join(struct.pack('>I', w) for w in L['skrow']), 'skeleton module row')
        out.blob(A['sk_str'], SK_NAME.encode().ljust(12, b'\0'), '"skeleton"')
        out.blob(A['sk_lvd'], SK_LVD.encode().ljust(16, b'\0'), '"skeleton.lvd"')
        out.blob(A['sk_verts'], b''.join(struct.pack('>2f', *v) for v in SK_VERTS), 'skeleton collision vertices')
        out.blob(A['sk_box'], struct.pack('>7f', SK_W, 0.0, SK_H, 0, 0, 0, 0), 'skeleton hit box')
        out.blob(A['sk_nums'], struct.pack('>10f', *range(10)), 'skeleton 0-9')
        out.blob(A['sk_k'], struct.pack('>5f', SK_HP, 10.0, 8.0, 0.5, SK_SCALE), 'skeleton constants')
        out.blob(A['sk_latch'], bytes(SLOTS * SK_LATCH * 8), 'skeleton attackers latched')
    out.blob(A['gk_list'], struct.pack('>II', A['gk_list'] + 8, len(L['rows'])) +
             b''.join(struct.pack('>4I', *e) for e in L['rows']), 'his article list (+ clones 6 / 7, skeleton 8)')
    gd = bytearray(img.blob(GK_DESC, 0x38))
    struct.pack_into('>I', gd, 8, A['gk_list'])
    out.blob(A['gk_desc'], bytes(gd), 'his fighter descriptor copy')
    out.blob(A['g1_desc'], struct.pack('>III', A['g1_shapes'], len(SHAPE_Z), 1), 'clone shapes desc')
    out.blob(A['g1_shapes'], b''.join(struct.pack('>7fI', 0.0, SHAPE_Y[0], z, 0.0, SHAPE_Y[1], z, SHAPE_R, 0x200)
                                      for z in SHAPE_Z), 'clone shapes (joint 0, capsules)')
    out.blob(A['gk_hide'], bytes(8 * SLOTS), 'hide counters / slow states')
    if diag:
        out.blob(A['gk_lastf'], bytes(8 * SLOTS), 'diag: flags logged / tag hide logged')
        out.blob(A['gk_seen'], bytes(4 * 16), 'diag: HUD calls seen')
    out.blob(A['consts'], struct.pack('>6fI2f', 0.0, 0.5, HIT_BIAS, FAR, 1.0, HIT_BIAS2, img.w(HITSTOP_MUL), 100.0, 360.0), 'constants')
    out.blob(A['hurt'], hurt_blob(), 'clone hurtboxes (his vl group 5, article joints)')
    out.blob(A['ctf'], b''.join(struct.pack('>4B4h', *c) for c in GAUGE_COLOURS), 'gauge colours')
    out.blob(A['gk_tags'], bytes(4 * SLOTS), 'tag message countdowns')
    out.blob(A['gk_plyr'], bytes(4 * SLOTS), 'cursor show bytes saved')
    out.blob(A['gk_clr'], bytes(4 + 4 * SLOTS), 'clears seen (burn v1.2)')
    if 'burn' in feats:
        out.blob(A['btab'], bytes(SLOTS * BURN_CAP * 16), 'burn instances')
        out.blob(A['bproc'], bytes(BURN_CONTEXTS * BURN_ENTS + (-BURN_CONTEXTS * BURN_ENTS) % 4), 'burn processed counts')
        out.blob(A['bmoves'], b''.join(struct.pack('>IfIIf', *(m + (burn_shield_damage(m),))) for m in BURN_MOVES),
                 'burn moves (kind, damage, interval, frames, shielded damage)')
        out.blob(A['bconst'], struct.pack('>2f', BURN_SHIELD_DAMAGE, 1000.0), 'burn constants')
        if diag:
            out.blob(A['bsum'], bytes(SLOTS * SLOTS * 4), 'burn sums')
            out.blob(A['bclock'], bytes(4 * SLOTS), 'burn clocks')
    if 'hitcheck' in feats:
        out.blob(A['hcbox'], struct.pack('>7f', *(HC_BOX + (0.0,) * 4)), 'hit check box')
        out.blob(A['hcsize'], struct.pack('>%dI' % len(HC_OBJ_SIZES), *HC_OBJ_SIZES), 'hit check object sizes')
    strs, ptrs, at = b'', [], A['gk_namestr']
    for n in GAUGE_NAMES:
        ptrs.append((at + len(strs), len(n)))
        strs += n.encode() + b'\0'
    out.blob(A['gk_names'], b''.join(struct.pack('>II', a_, l_) for a_, l_ in ptrs), 'gauge names')
    out.blob(A['gk_namestr'], strs + b'\0' * (-len(strs) % 4), 'gauge name strings')
    out.blob(A['gk_atoms'], bytes(4 * len(GAUGE_NAMES)), 'gauge atoms')
    out.blob(A['gk_angles'], bytes(16 * SLOTS), 'gauge ring angles')
    out.blob(A['gk_speeds'], struct.pack('>4f', *GAUGE_SPEEDS), 'gauge ring speeds')
    if diag:
        out.blob(A['gk_gaugelog'], struct.pack('>8i', *([-1] * SLOTS)), 'diag: gauge logged')
    out.blob(A['gk_str'], CLONE_NAME.encode().ljust(8, b'\0'), '"clone"')
    if diag:
        for nm, s in fmts:
            b = s.encode() + b'\0'
            out.blob(A[nm], b + b'\0' * (-len(b) % 4), nm)

    p = dict(acc=ACC, work=WORK, posture=POSTURE, bacc=BASE_ACC, entry=ENTRY, slots=SLOTS, tag=FLAG_TAG,
             slow=FLAG_SLOW, clones=FLAG_CLONES, life=TAG_LIFE, sslot=SLOW_SLOT, srate=SLOW_RATE, sframes=SLOW_FRAMES,
             hitbits=HIT_BITS, wacc=W_ACC, wwork=W_WORK, whit=W_HIT_MOD, wdmg=W_DAMAGE, watk=W_ATTACK,
             wstop=W_STOP, wcol=W_COLOUR, wmodel=W_MODEL, wlink=W_LINK, wvis=W_VIS, wpost=W_POSTURE,
             cclear=COLOUR_CLEAR, nmoves=len(BURN_MOVES), bcap=BURN_CAP, bcap16=BURN_CAP * 16, bents=BURN_ENTS,
             dm_add=DM_ADD, fstatus=F_STATUS, st_kind=ST_KIND, st_dead=ST_DEAD, st_dead_n=ST_DEAD_N, ent_log=ENT_LOG, node_obj=NODE_OBJ, node_type=NODE_TYPE, mm_kind=MM_KIND, am_ents=AM_ENTS, am_count=AM_COUNT, am_max=AM_MAX, ent_size=ENT_SIZE,
             ent_nodes=ENT_NODES, node_max=NODE_MAX, node_on=NODE_ON, node_min_x=NODE_MIN_X, node_min_y=NODE_MIN_Y,
             node_max_x=NODE_MAX_X, node_max_y=NODE_MAX_Y, team=TEAM_MOD,
             obj_max=HC_OBJ_MAX, am_data=AM_DATA, slot_size=SLOT_SIZE, slot_dmg=SLOT_DMG, wmotion=W_MOTION, mo_swing=MO_SWING, mi_sb=MI_SB, mi_nhb=MI_NHB, mm_swing=MM_SWING, mm_motion=MM_MOTION, plyc_blk=PLYC_BLK, plyc_show=PLYC_SHOW, plyc_id=PLYC_ID, plyc_alpha=PLYC_ALPHA, pm_scale=PM_SCALE, nlatch=SLOTS * SK_LATCH * 2, sk_kind=SK_KIND, sk_lat=SK_LATCH, sk_lat8=SK_LATCH * 8, sk_nv=len(SK_VERTS), gm_vt_hi=SK_GM_VT >> 16, gm_vt_lo=SK_GM_VT & 0xFFFF, wground=0x2C, nbtab=SLOTS * BURN_CAP * 4, nbproc=(BURN_CONTEXTS * BURN_ENTS + 3) // 4, clear_back=CLEAR_BACK, hm_count=HM_COUNT, hm_clear=HM_CLEAR, hm_groups=HM_GROUPS, hm_group=HM_GROUP,
             hm_objs=HM_OBJS, hm_objarr=HM_OBJARR, hm_recs=HM_RECS, nhurt=len(HURTBOXES), gkind=GK_KIND, pslot=PANEL_SLOT, tagresend=TAG_RESEND, s13b=SLOT13 + 4, s42b=SLOT42 + 4, s43b=SLOT43 + 4)
    for nm in ('g1_desc', 'gk_hide', 'gk_desc', 'w_desc', 'gk_ft', 'gk_fs', 'gk_f42', 'gk_f43', 'gk_fl', 'gk_fd', 'hurt',
               'gk_ff', 'gk_fi', 'gk_fc', 'gk_fu', 'gk_lastf', 'gk_fj', 'gk_fp', 'gk_fv', 'gk_seen', 'gk_fx', 'gk_fb', 'ctf',
               'gk_gaugelog', 'gk_fz', 'gk_fw', 'gk_fm', 'gk_fn', 'gk_fh', 'hcbox', 'hcsize', 'btab', 'bproc', 'bmoves', 'bsum', 'bclock', 'gk_fba', 'gk_fbt', 'gk_fbr', 'gk_clr', 'sk_desc', 'gk_fss', 'gk_fsc', 'gk_fsf', 'gk_fsh', 'gk_fsx', 'sk_lvd', 'sk_verts', 'sk_box', 'sk_nums', 'sk_k', 'sk_latch', 'gk_fbk', 'gk_fr', 'gk_fq', 'gk_fy', 'gk_fk', 'gk_fo', 'gk_tags', 'gk_plyr', 'gk_names', 'gk_atoms', 'gk_angles', 'gk_speeds'):
        p[nm + '_hi'], p[nm + '_lo'] = ha(A[nm]), K.slo(A[nm])
    for i, nm in enumerate(('zero', 'half', 'bias', 'far', 'one', 'bias2', 'hmul', 'hundred', 'deg360')):
        p[nm + '_hi'], p[nm + '_lo'] = ha(A['consts'] + 4 * i), K.slo(A['consts'] + 4 * i)
    p['ftab_hi'], p['ftab_lo'] = ha(FIGHTERS), K.slo(FIGHTERS)
    if skel:
        p['sk_k4_hi'], p['sk_k4_lo'] = ha(A['sk_k'] + 4), K.slo(A['sk_k'] + 4)
        p['sk_k8_hi'], p['sk_k8_lo'] = ha(A['sk_k'] + 8), K.slo(A['sk_k'] + 8)
        p['sk_k16_hi'], p['sk_k16_lo'] = ha(A['sk_k'] + 16), K.slo(A['sk_k'] + 16)
        p['resmgr_hi'], p['resmgr_lo'] = ha(RES_MGR), K.slo(RES_MGR)
        ski = [m[0] for m in BURN_MOVES].index(SK_BURN_KEY)
        p['sk_row_hi'], p['sk_row_lo'] = ha(A['bmoves'] + 20 * ski), K.slo(A['bmoves'] + 20 * ski)
    p['bshield_hi'], p['bshield_lo'] = ha(A['bconst']), K.slo(A['bconst'])
    p['thousand_hi'], p['thousand_lo'] = ha(A['bconst'] + 4), K.slo(A['bconst'] + 4)
    p['fm_hi'], p['fm_lo'] = ha(FIGHTER_MANAGER), K.slo(FIGHTER_MANAGER)
    p['msgk_hi'], p['msgk_lo'] = ha(MSG_KIND), K.slo(MSG_KIND)
    p['apool_hi'], p['apool_lo'] = ha(FLX_ATOM_POOL), K.slo(FLX_ATOM_POOL)
    p['mgr_hi'], p['mgr_lo'] = ha(OBJ_MANAGER), K.slo(OBJ_MANAGER)
    D = (lambda s: s) if diag else (lambda s: '')

    src = '''
# ---- his slot 0's group-1 init: our 4-shape desc (G1_HOOK's bl comes here; r8 = 1 the group, the rest the game's)
g1_stub:
        lis r7, %(g1_desc_hi)d
        addi r7, r7, %(g1_desc_lo)d''' + tail(G1_FN) + '''

# ---- the HUD's cursor update (HUD_HOOK -> TRAMP -> here; r3 the cursor, r29 = 8 - player, LR back into the HUD)
hud:''' + D('''
        lis r11, %(gk_seen_hi)d
        addi r11, r11, %(gk_seen_lo)d
        andi. r10, r29, 15
        slwi r10, r10, 2
        lwzx r0, r11, r10
        cmpwi r0, 0
        bne hud_s
        li r0, 1
        stwx r0, r11, r10
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r3, 0x8(r1)
        stw r4, 0xC(r1)
        stw r5, 0x10(r1)
        stw r6, 0x14(r1)
        stw r7, 0x18(r1)
        stw r8, 0x1C(r1)
        stw r9, 0x20(r1)
        mr r5, r3
        mr r4, r29
        lis r3, %(gk_fv_hi)d
        addi r3, r3, %(gk_fv_lo)d''' + osr() + '''
        lwz r3, 0x8(r1)
        lwz r4, 0xC(r1)
        lwz r5, 0x10(r1)
        lwz r6, 0x14(r1)
        lwz r7, 0x18(r1)
        lwz r8, 0x1C(r1)
        lwz r9, 0x20(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
hud_s:''') + '''
        li r12, 8
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
        stfs f0, 0xC(r3)''' + D('''
        lis r11, %(gk_lastf_hi)d
        addi r11, r11, %(gk_lastf_lo)d
        addi r11, r11, 0x20
        lwzx r10, r11, r12
        cmpwi r10, 0
        bne hud_go
        li r10, 1
        stwx r10, r11, r12
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r3, 0x8(r1)
        stw r4, 0xC(r1)
        stw r5, 0x10(r1)
        stw r6, 0x14(r1)
        stw r7, 0x18(r1)
        stw r8, 0x1C(r1)
        stw r9, 0x20(r1)
        mr r5, r3
        srwi r4, r12, 2
        lis r3, %(gk_fu_hi)d
        addi r3, r3, %(gk_fu_lo)d''' + osr() + '''
        lwz r3, 0x8(r1)
        lwz r4, 0xC(r1)
        lwz r5, 0x10(r1)
        lwz r6, 0x14(r1)
        lwz r7, 0x18(r1)
        lwz r8, 0x1C(r1)
        lwz r9, 0x20(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40''') + '''
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
        bne s13_out''' + D('''
        lis r25, %(gk_clr_hi)d
        addi r25, r25, %(gk_clr_lo)d
        lwz r4, 0(r25)                  # burn v1.2 diag: a clear since this slot last logged one
        slwi r12, r27, 2
        addi r12, r12, 4
        lwzx r0, r25, r12
        cmpw r0, r4
        beq s13_noclr
        stwx r4, r25, r12
        mr r5, r27
        lis r3, %(gk_fbr_hi)d
        addi r3, r3, %(gk_fbr_lo)d''' + osr() + '''
s13_noclr:''') + (('''
        mr r3, r31                      # burn v1: his hits and his burns' ticks
        mr r4, r27
        bl burn_him''') if 'burn' in feats else '') + '''
        lwz r29, %(acc)d(r31)
        lwz r28, %(work)d(r29)''' + (('''
        lis r12, %(gk_clr_hi)d
        lwz r12, %(gk_clr_lo)d(r12)
        andi. r11, r12, 7''' + vnum('r28', VAR_GEN_CLR, 'r11')) if skel else '') + var_get('r28', VAR_FLAGS) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r26, 0x1C(r1)               # the flags''' + D('''
        lis r25, %(gk_lastf_hi)d
        addi r25, r25, %(gk_lastf_lo)d
        slwi r12, r27, 2
        lwzx r0, r25, r12
        cmpw r0, r26
        beq s13_nof
        stwx r26, r25, r12
        andi. r0, r26, %(tag)d
        bne s13_keep
        addi r11, r25, 0x20             # the tag gone: its hide may be logged again
        li r0, 0
        stwx r0, r11, r12
s13_keep:''' + var_get('r28', VAR_GEN) + '''
        fctiwz f1, f1
        stfd f1, 0x20(r1)
        lis r3, %(gk_ff_hi)d
        addi r3, r3, %(gk_ff_lo)d
        mr r4, r27
        mr r5, r26
        lwz r6, 0x24(r1)''' + osr() + '''
s13_nof:''') + '''
        lis r25, %(gk_tags_hi)d
        addi r25, r25, %(gk_tags_lo)d
        slwi r12, r27, 2
        lwzx r10, r25, r12
        andi. r0, r26, %(tag)d
        beq s13_tagoff
        addi r10, r10, -1
        cmpwi r10, 0
        bgt s13_tagkeep
        li r10, %(tagresend)d
        stwx r10, r25, r12
        mr r3, r31
        li r4, 0
        bl gk_tag
        b s13_tagdone
s13_tagkeep:
        stwx r10, r25, r12
        b s13_tagdone
s13_tagoff:
        cmpwi r10, 0
        beq s13_tagdone
        li r0, 0
        stwx r0, r25, r12
        mr r3, r31
        li r4, 1
        bl gk_tag
s13_tagdone:
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

# ---- an owner's fighter table entry from his slot (r3, 1-8) -> r3 (0: none / not live); leaf
gk_entry:
        addi r11, r3, -1
        cmplwi r11, %(slots)d
        bge ge_none
        lis r12, %(ftab_hi)d
        lwz r12, %(ftab_lo)d(r12)
        cmpwi r12, 0
        beq ge_none
        lwz r12, 0(r12)
        cmpwi r12, 0
        beq ge_none
        lwz r10, 8(r12)                 # the entries' count
        cmplw r11, r10
        bge ge_none
        lwz r12, 0(r12)
        mulli r11, r11, %(entry)d
        add r3, r12, r11
        lbz r0, 0x1E(r3)                # live (>= 4)
        cmplwi r0, 4
        blt ge_none
        blr
ge_none:
        li r3, 0
        blr

# ---- the clone article's hit-result method (its singleton vtable +0xAC): (singleton, weapon, result bits)
# bits 0x17 (a hit / a shield): kept (0, not removed), and (v3) its owner gets the hitlag at once: the game's hitstop
# (HITSTOP_FN, the attacker side, with the hitbox's own multiplier) for the clone's hitbox with the biggest damage
# among those with hit records, on his StopModule (vt +0x8C(frames, 1): the longer of it and what he has); his
# VAR_22 = 1.0 (his MSC: a fallback if he still isn't in hitlag)
w_hit:  andi. r0, r5, %(hitbits)d
        beq w_base
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r27, 0x2C(r1)
        lwz r31, %(wacc)d(r4)           # the clone's module accessor
        cmpwi r31, 0
        beq w_done
        lwz r30, %(wwork)d(r31)         # its WorkModule
        cmpwi r30, 0
        beq w_done''' + var_get('r30', VAR_SLOT) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r3, 0x1C(r1)                # its owner's slot (its VAR_0)
        bl gk_entry
        cmpwi r3, 0
        beq w_done
        mr r29, r3                      # his table entry
        li r27, 0                       # the hitbox data
        lis r12, %(zero_hi)d
        lfs f0, %(zero_lo)d(r12)
        stfs f0, 0x20(r1)               # its damage
        lwz r28, %(watk)d(r31)          # the clone's AttackModule
        cmpwi r28, 0
        beq w_lag
        lwz r9, 0x18(r28)               # record arrays (one a hitbox), at most 8
        cmplwi r9, 8
        ble w_cnt
        li r9, 8
w_cnt:  lwz r10, 0x14(r28)
        cmpwi r10, 0
        beq w_lag
w_h:    cmpwi r9, 0
        beq w_lag
        addi r11, r10, 0x124            # the list's sentinel
        lwz r12, 0x128(r10)             # its first node
        li r8, 32
w_n:    cmpw r12, r11
        beq w_next
        cmpwi r12, 0
        beq w_next
        lbz r7, 0x27(r12)               # the node's hitbox id
        mulli r7, r7, 0x84
        lwz r6, 0x40(r28)
        add r6, r6, r7                  # its attack data (+0x18 damage)
        lfs f0, 0x18(r6)
        lfs f13, 0x20(r1)
        fcmpu cr0, f0, f13
        ble w_skip
        stfs f0, 0x20(r1)
        mr r27, r6
w_skip: lwz r12, 4(r12)
        addi r8, r8, -1
        cmpwi r8, 0
        bne w_n
w_next: addi r10, r10, 0x174
        addi r9, r9, -1
        b w_h
w_lag:  cmpwi r27, 0
        beq w_mark
        lwz r28, %(bacc)d(r29)          # his module accessor
        cmpwi r28, 0
        beq w_mark
        mr r3, r28
        mr r4, r27
        lfs f1, 0x20(r1)
        lis r12, %(hmul_hi)d
        lfs f2, %(hmul_lo)d(r12)
        li r5, 1                        # the attacker's side
        li r6, 1''' + call(HITSTOP_FN) + '''
        mr r27, r3
        cmpwi r27, 0
        ble w_mark
        lwz r3, %(wstop)d(r28)          # his StopModule
        cmpwi r3, 0
        beq w_mark
        mr r4, r27
        li r5, 1
        lwz r12, 0(r3)
        lwz r12, 0x8C(r12)
        mtctr r12
        bctrl''' + D(''' 
        lis r3, %(gk_fl_hi)d
        addi r3, r3, %(gk_fl_lo)d
        lwz r4, 0x1C(r1)
        mr r5, r27''' + osr()) + '''
w_mark: lwz r12, %(acc)d(r29)
        cmpwi r12, 0
        beq w_done
        lwz r30, %(work)d(r12)          # his WorkModule
        cmpwi r30, 0
        beq w_done
        lis r12, %(one_hi)d
        lfs f1, %(one_lo)d(r12)''' + var_set('r30', VAR_LAG) + '''
w_done: lmw r27, 0x2C(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        li r3, 0
        blr
w_base:''' + tail(L['old_hit']) + '''

# ---- v3: the clone's set-up (its singleton vtable +0x1C, (singleton, weapon); bunshin's is a blr): his hurtboxes on
# its HitModule (vt +0x4C(&{data, count}, 0), the can's call)
w_init: stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        lwz r12, %(wacc)d(r4)
        cmpwi r12, 0
        beq wi_out
        lwz r3, %(whit)d(r12)           # its HitModule''' + D('''
        stw r3, 0x10(r1)
        mr r4, r3
        lis r3, %(gk_fi_hi)d
        addi r3, r3, %(gk_fi_lo)d''' + osr() + '''
        lwz r3, 0x10(r1)''') + (HURT_CALL if 'hurt' in feats else '') + D('''
        lis r3, %(gk_fj_hi)d
        addi r3, r3, %(gk_fj_lo)d''' + osr()) + '''
wi_out: lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
# ---- v3: the clone hurt? (r3 the weapon): damage taken this frame (DamageModule vt +0x7C(0) > 0) -> its owner's
# VAR_21 = HIT_BIAS2 + its id (its VAR_1): his MSC turns that clone into the log (which clone: exact)
w_poll: stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stw r31, 0x2C(r1)
        stw r30, 0x28(r1)
        lwz r31, %(wacc)d(r3)
        cmpwi r31, 0
        beq wp_out''' + D('''
        lwz r30, %(wwork)d(r31)
        cmpwi r30, 0
        beq wp_nolog''' + var_get('r30', VAR_LOGGED) + '''
        lis r12, %(half_hi)d
        lfs f0, %(half_lo)d(r12)
        fcmpu cr0, f1, f0
        bgt wp_nolog
        lis r12, %(zero_hi)d
        lfs f0, %(zero_lo)d(r12)
        fcmpu cr0, f1, f0
        bgt wp_named                    # its first update already logged
        lis r12, %(half_hi)d
        lfs f1, %(half_lo)d(r12)''' + var_set('r30', VAR_LOGGED) + '''
        lis r3, %(gk_fp_hi)d
        addi r3, r3, %(gk_fp_lo)d
        mr r4, r31''' + osr() + '''
wp_named:''' + var_get('r30', VAR_ID) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r0, 0x1C(r1)
        stw r0, 0x10(r1)''' + var_get('r30', VAR_SLOT) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lis r12, %(half_hi)d
        lfs f0, %(half_lo)d(r12)
        lwz r0, 0x10(r1)
        cmpwi r0, 0
        beq wp_nolog                    # its MSC hasn't named it yet: logged on a later frame
        lis r12, %(one_hi)d
        lfs f1, %(one_lo)d(r12)''' + var_set('r30', VAR_LOGGED) + '''
        lis r3, %(gk_fc_hi)d
        addi r3, r3, %(gk_fc_lo)d
        lwz r4, 0x10(r1)
        lwz r5, 0x1C(r1)''' + osr() + '''
wp_nolog:''' + pos_diag()) + (('''
        lwz r3, %(wdmg)d(r31)           # its DamageModule
        cmpwi r3, 0
        beq wp_out
        li r4, 0
        lwz r12, 0(r3)
        lwz r12, 0x7C(r12)
        mtctr r12
        bctrl
        lis r12, %(zero_hi)d
        lfs f0, %(zero_lo)d(r12)
        fcmpu cr0, f1, f0
        ble wp_out
        lwz r30, %(wwork)d(r31)
        cmpwi r30, 0
        beq wp_out''' + var_get('r30', VAR_ID) + '''
        stfs f1, 0x20(r1)               # its id''' + var_get('r30', VAR_SLOT) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r3, 0x1C(r1)
        bl gk_entry
        cmpwi r3, 0
        beq wp_out
        lwz r12, %(acc)d(r3)
        cmpwi r12, 0
        beq wp_out
        lwz r30, %(work)d(r12)          # his WorkModule
        cmpwi r30, 0
        beq wp_out
        lfs f1, 0x20(r1)
        lis r12, %(bias2_hi)d
        lfs f0, %(bias2_lo)d(r12)
        fadds f1, f1, f0''' + var_set('r30', VAR_HIT) + D('''
        lfs f1, 0x20(r1)
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lis r3, %(gk_fd_hi)d
        addi r3, r3, %(gk_fd_lo)d
        lwz r4, 0x1C(r1)''' + osr()) + '''
''') if 'hurt' in feats else '') + '''
wp_out: lwz r30, 0x28(r1)
        lwz r31, 0x2C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# the specializer's +0x64 (spec, weapon, ...): the damage poll, then bunshin's method with the same arguments
wp_64:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r3, 0x08(r1)
        stw r4, 0x0C(r1)
        stw r5, 0x10(r1)
        stw r6, 0x14(r1)
        stw r7, 0x18(r1)
        stw r8, 0x1C(r1)
        stw r9, 0x20(r1)
        stw r10, 0x24(r1)
        mr r3, r4
        bl w_poll
        lwz r3, 0x08(r1)
        lwz r4, 0x0C(r1)
        lwz r5, 0x10(r1)
        lwz r6, 0x14(r1)
        lwz r7, 0x18(r1)
        lwz r8, 0x1C(r1)
        lwz r9, 0x20(r1)
        lwz r10, 0x24(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40''' + tail(L['vt_orig'][0x64]) + '''

# the specializer's +0x84 (spec, weapon, ...): the damage poll, then bunshin's method with the same arguments
wp_84:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r3, 0x08(r1)
        stw r4, 0x0C(r1)
        stw r5, 0x10(r1)
        stw r6, 0x14(r1)
        stw r7, 0x18(r1)
        stw r8, 0x1C(r1)
        stw r9, 0x20(r1)
        stw r10, 0x24(r1)
        mr r3, r4
        bl w_poll
        lwz r3, 0x08(r1)
        lwz r4, 0x0C(r1)
        lwz r5, 0x10(r1)
        lwz r6, 0x14(r1)
        lwz r7, 0x18(r1)
        lwz r8, 0x1C(r1)
        lwz r9, 0x20(r1)
        lwz r10, 0x24(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40''' + tail(L['vt_orig'][0x84]) + '''

# the specializer's +0x8C (spec, weapon, ...): the damage poll, then bunshin's method with the same arguments
wp_8C:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r3, 0x08(r1)
        stw r4, 0x0C(r1)
        stw r5, 0x10(r1)
        stw r6, 0x14(r1)
        stw r7, 0x18(r1)
        stw r8, 0x1C(r1)
        stw r9, 0x20(r1)
        stw r10, 0x24(r1)
        mr r3, r4
        bl w_poll
        lwz r3, 0x08(r1)
        lwz r4, 0x0C(r1)
        lwz r5, 0x10(r1)
        lwz r6, 0x14(r1)
        lwz r7, 0x18(r1)
        lwz r8, 0x1C(r1)
        lwz r9, 0x20(r1)
        lwz r10, 0x24(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40''' + tail(L['vt_orig'][0x8C]) + '''

# the specializer's +0x94 (spec, weapon, ...): the damage poll, then bunshin's method with the same arguments
wp_94:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r3, 0x08(r1)
        stw r4, 0x0C(r1)
        stw r5, 0x10(r1)
        stw r6, 0x14(r1)
        stw r7, 0x18(r1)
        stw r8, 0x1C(r1)
        stw r9, 0x20(r1)
        stw r10, 0x24(r1)
        mr r3, r4
        bl w_poll''' + (('''
        lwz r3, 0x0C(r1)
        bl w_sway''') if 'sway' in feats else '') + (('''
        lwz r3, 0x0C(r1)
        bl w_burn''') if 'burn' in feats else '') + (('''
        lwz r3, 0x0C(r1)
        bl w_hitchk''') if 'hitcheck' in feats else '') + '''
        lwz r3, 0x08(r1)
        lwz r4, 0x0C(r1)
        lwz r5, 0x10(r1)
        lwz r6, 0x14(r1)
        lwz r7, 0x18(r1)
        lwz r8, 0x1C(r1)
        lwz r9, 0x20(r1)
        lwz r10, 0x24(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40''' + tail(L['vt_orig'][0x94]) + '''

''' + ((r'''# ---- v11 - v13 sway: the clone's swing step. A fighter's frame calls its MotionModule's swing update 0x02C67064
# (0x02E3543C); v11 called that for the clone (crashed: fighter-side modules), v12 its last two steps on the motion
# object: the rate 0x03318A10(motion, 1.0) and 0x03314FB8(motion) (set up 0x036B715C (+0xF1), then step 0x036B726C).
# The user's v12 log: the clone's motion object has no swing system (+0x20 0) at all, so nothing ran. v13 binds one
# the way the motion bind does (0x0330DFE8 - 0x0330E03C, when the model instance has a model.sb (+0x6FC) / model.nhb
# (+0x700)): a swing system 0x03327448(), stored at motion +0x20, the skeleton evaluator told 0x036C60E0([motion +0x1C],
# [motion +0x18], swing, 9, 9, [[[motion +0x18]] +8]), the sb / nhb parsed 0x036B8040 / 0x036B736C. Its own model
# instance's sb / nhb, or his (the same skeleton) when it has none. Once per clone life (VAR_6). Diag S4GR stages:
# 0 / 1 before / after its first step (motion, swing, set up, flags), 2 the bind's sources (sb, nhb, own 1 / his 0),
# 3 bound (swing)
w_sway: stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r26, 0x28(r1)
        lwz r29, %(wacc)d(r3)
        cmpwi r29, 0
        beq wsw_out
        lwz r30, %(wwork)d(r29)
        cmpwi r30, 0
        beq wsw_out
        lwz r11, %(wmotion)d(r29)       # its MotionModule
        cmpwi r11, 0
        beq wsw_out
        lwz r31, %(mm_motion)d(r11)     # its motion object
        lis r0, 0x1000
        cmplw r31, r0
        blt wsw_out
        lis r0, 0x8000
        cmplw r31, r0
        bge wsw_out
        lwz r11, %(mo_swing)d(r31)      # its swing system
        cmpwi r11, 0
        bne wsw_have
        bl wsw_bind
        lwz r11, %(mo_swing)d(r31)
        cmpwi r11, 0
        beq wsw_out
wsw_have:''' + D('''
        li r0, 0
        stw r0, 0x10(r1)''' + var_get('r30', VAR_SWAYLOG) + '''
        lis r12, %(half_hi)d
        lfs f0, %(half_lo)d(r12)
        fcmpu cr0, f1, f0
        bgt wsw_nolog0
        li r0, 1
        stw r0, 0x10(r1)
        li r4, 0
        bl wsw_log
wsw_nolog0:''') + '''
        mr r3, r31
        lis r12, %(one_hi)d
        lfs f1, %(one_lo)d(r12)''' + call(SWING_RATE) + '''
        mr r3, r31''' + call(SWING_STEP) + D('''
        lwz r0, 0x10(r1)
        cmpwi r0, 0
        beq wsw_out
        li r4, 1
        bl wsw_log
        lis r12, %(one_hi)d
        lfs f1, %(one_lo)d(r12)''' + var_set('r30', VAR_SWAYLOG)) + '''
wsw_out:
        lmw r26, 0x28(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr
wsw_bind:                               # (r29 its accessor, r30 its WorkModule, r31 its motion object)
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)''' + var_get('r30', VAR_BIND) + '''
        lis r12, %(half_hi)d
        lfs f0, %(half_lo)d(r12)
        fcmpu cr0, f1, f0
        bgt wb_out                      # tried this life already
        lis r12, %(one_hi)d
        lfs f1, %(one_lo)d(r12)''' + var_set('r30', VAR_BIND) + '''
        lwz r12, 4(r31)                 # its model link: mode 8 = none
        cmpwi r12, 0
        beq wb_out
        lwz r0, 4(r12)
        cmpwi r0, 8
        beq wb_out
        li r27, 0                       # sb
        li r28, 0                       # nhb
        li r0, 1
        stw r0, 0x18(r1)                # own 1 / his 0
        mr r3, r29
        bl wb_mi
        cmpwi r3, 0
        beq wb_his
        lwz r27, %(mi_sb)d(r3)
        lwz r28, %(mi_nhb)d(r3)
        or. r0, r27, r28
        bne wb_have
wb_his: li r0, 0
        stw r0, 0x18(r1)''' + var_get('r30', VAR_SLOT) + '''
        fctiwz f1, f1
        stfd f1, 0x20(r1)
        lwz r3, 0x24(r1)
        bl gk_entry
        cmpwi r3, 0
        beq wb_out
        lwz r3, %(bacc)d(r3)
        bl wb_mi
        cmpwi r3, 0
        beq wb_out
        lwz r27, %(mi_sb)d(r3)
        lwz r28, %(mi_nhb)d(r3)
wb_have:''' + D('''
        li r4, 2
        mr r5, r27
        mr r6, r28
        lwz r7, 0x18(r1)
        li r8, 0
        bl wsw_logn''') + '''
        or. r0, r27, r28
        beq wb_out''' + call(SWING_NEW) + '''
        mr. r26, r3
        beq wb_out
        stw r26, %(mo_swing)d(r31)
        lwz r4, 0x18(r31)
        lwz r10, 0(r4)
        lwz r8, 8(r10)
        lwz r3, 0x1C(r31)
        mr r5, r26
        li r6, 9
        li r7, 9''' + call(SWING_SKEL) + '''
        cmpwi r27, 0
        beq wb_nosb
        mr r3, r26
        mr r4, r27''' + call(SWING_SB) + '''
wb_nosb:
        cmpwi r28, 0
        beq wb_nonhb
        mr r3, r26
        mr r4, r28''' + call(SWING_NHB) + '''
wb_nonhb:''' + D('''
        li r4, 3
        mr r5, r31
        mr r6, r26
        li r7, 0
        li r8, 0
        bl wsw_logn''') + '''
wb_out: lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
wb_mi:  cmpwi r3, 0                     # (r3 an accessor) -> its model instance ([[+0x3C] +4 handle] +8), or 0
        beqlr
        lwz r3, %(wmodel)d(r3)
        cmpwi r3, 0
        beqlr
        lwz r3, 0xC(r3)
        lis r0, 0x1000
        cmplw r3, r0
        blt wb_mi0
        lis r0, 0x8000
        cmplw r3, r0
        bltlr
wb_mi0: li r3, 0
        blr''' + D('''
wsw_log:                                # (r4 0 before / 1 after, r31 the motion object)
        mr r5, r31
        lwz r6, %(mo_swing)d(r31)
        lbz r7, 0xF1(r31)
        li r8, -1
        cmpwi r6, 0
        beq wsw_logn
        lwz r8, 0xB4(r6)
wsw_logn:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        lis r3, %(gk_fr_hi)d
        addi r3, r3, %(gk_fr_lo)d''' + osr() + '''
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr''') + '''

''') if 'sway' in feats else '') + '''
''' + ((r'''# ---- v12 / v13 hitcheck: the clone hit from Greninja's side (the native hurtboxes never met an attack; v12's
# F_hitcheck worked in the user's game). Once a frame (the +0x94 phase) every live battle object's active attack nodes
# against the clone's box at its place: the fighters (holder [0x1035184C] +0, 0x76B0 each), v13 the weapons (+4,
# 0x1E20) and the items (+0x10, 0x3B88); an object: +0x1E live (>= 4, as 0x02BF2108), +0xC its module accessor.
# AttackModule (accessor +0x50) +8 its collision container: +0xC the entries (0x174, one per hitbox id), +0x10 their
# count; an entry's nodes: +0 first index, +4 count, +0x18 the node pointers; a node: +0x3C on, its x / y box +0x18 /
# +0x1C (min) +0x20 / +0x24 (max) (the boxes the game's pair pass 0x02C0F6F0 tests first). His team (TeamModule +0x6C,
# team id +8) skipped (a fighter's team -1 never matches; a weapon's / item's equal to his always skipped: his own
# shuriken). A hit: his VAR_21 = HIT_BIAS2 + its id (his MSC: smoke and the log), the clone's VAR_4 latched (w_start
# clears it), v13 the attacker's hitlag (HITSTOP_FN on that hitbox's data and damage, its StopModule vt +0x8C(frames,
# 1), as the clone's own hit method gives him). Diag S4GH (attacker: category x 16 + index, hitbox, clone id, place)
w_hitchk:
        stwu r1, -0x70(r1)
        mflr r0
        stw r0, 0x74(r1)
        stmw r20, 0x40(r1)
        lwz r31, %(wacc)d(r3)
        cmpwi r31, 0
        beq hc_out
        lwz r30, %(wwork)d(r31)
        cmpwi r30, 0
        beq hc_out''' + var_get('r30', VAR_LATCH) + '''
        lis r12, %(half_hi)d
        lfs f0, %(half_lo)d(r12)
        fcmpu cr0, f1, f0
        bgt hc_out''' + var_get('r30', VAR_ID) + '''
        stfs f1, 0x28(r1)
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r29, 0x1C(r1)               # its id (1 / 2)
        addi r0, r29, -1
        cmplwi r0, 1
        bgt hc_out''' + var_get('r30', VAR_SLOT) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r28, 0x1C(r1)               # its owner's slot (1 - 8)
        lwz r12, %(wpost)d(r31)         # its place: the box
        cmpwi r12, 0
        beq hc_out
        lis r8, %(hcbox_hi)d
        addi r8, r8, %(hcbox_lo)d
        lfs f2, 0x10(r12)
        lfs f3, 0(r8)
        fsubs f4, f2, f3
        stfs f4, 0xC(r8)                # left
        fadds f4, f2, f3
        stfs f4, 0x10(r8)               # right
        lfs f2, 0x14(r12)
        lfs f3, 4(r8)
        fadds f4, f2, f3
        stfs f4, 0x14(r8)               # bottom
        lfs f3, 8(r8)
        fadds f4, f2, f3
        stfs f4, 0x18(r8)               # top
        lfs f2, 0x10(r12)
        stfs f2, 0x20(r1)
        lfs f2, 0x14(r12)
        stfs f2, 0x24(r1)
        mr r3, r28
        bl gk_entry
        mr. r27, r3                     # his entry
        beq hc_out
        li r26, -2                      # his team (-2: none read)
        lwz r12, %(bacc)d(r27)
        cmpwi r12, 0
        beq hc_cats
        lwz r12, %(team)d(r12)
        cmpwi r12, 0
        beq hc_cats
        lwz r26, 8(r12)
hc_cats:
        li r25, 0                       # the category (0 fighters, 1 weapons, 4 items)
hc_cat: lis r12, %(ftab_hi)d
        lwz r12, %(ftab_lo)d(r12)
        cmpwi r12, 0
        beq hc_out
        slwi r0, r25, 2
        lwzx r12, r12, r0               # the category's table
        lis r0, 0x1000
        cmplw r12, r0
        blt hc_ncat
        lis r0, 0x8000
        cmplw r12, r0
        bge hc_ncat
        lwz r23, 0(r12)                 # its objects
        lwz r22, 8(r12)                 # their count
        cmplwi r22, %(obj_max)d
        ble hc_cnt
        li r22, %(obj_max)d
hc_cnt: li r21, 0
        lis r12, %(hcsize_hi)d
        addi r12, r12, %(hcsize_lo)d
        slwi r0, r25, 2
        lwzx r20, r12, r0               # its object size
hc_obj: cmpw r21, r22
        bge hc_ncat
        mullw r12, r21, r20
        add r24, r23, r12               # the object
        addi r21, r21, 1
        cmpwi r25, 0
        bne hc_notme
        cmpw r24, r27
        beq hc_obj                      # him
hc_notme:
        lbz r0, 0x1E(r24)
        cmplwi r0, 4
        blt hc_obj
        lwz r24, %(bacc)d(r24)          # its accessor
        lis r0, 0x1000
        cmplw r24, r0
        blt hc_obj
        lis r0, 0x8000
        cmplw r24, r0
        bge hc_obj
        lwz r12, %(team)d(r24)
        cmpwi r12, 0
        beq hc_test
        lwz r12, 8(r12)
        cmpw r12, r26
        bne hc_test
        cmpwi r25, 0
        bne hc_obj                      # a weapon / item of his team: skipped
        cmpwi r12, -1
        bne hc_obj                      # a fighter of his team
hc_test:
        mr r3, r24
        bl hc_box
        cmpwi r3, 0
        blt hc_obj
        b hc_hit
hc_ncat:
        addi r25, r25, 1
        cmpwi r25, 2
        blt hc_cat
        bne hc_last
        li r25, 4                       # (categories 2 / 3: not attack objects)
        b hc_cat
hc_last:
        b hc_out
hc_hit: mr r23, r3                      # the hitbox (entry index)
        lis r12, %(one_hi)d
        lfs f1, %(one_lo)d(r12)''' + var_set('r30', VAR_LATCH) + '''
        lwz r12, %(acc)d(r27)           # his WorkModule: VAR_21 = HIT_BIAS2 + the id
        cmpwi r12, 0
        beq hc_lag
        lwz r20, %(work)d(r12)
        cmpwi r20, 0
        beq hc_lag
        lfs f1, 0x28(r1)
        lis r12, %(bias2_hi)d
        lfs f0, %(bias2_lo)d(r12)
        fadds f1, f1, f0''' + var_set('r20', VAR_HIT) + '''
hc_lag: li r22, 0                       # the attacker's hitlag: HITSTOP_FN(accessor, its data, damage, mul, 1, 1)
        lwz r12, %(watk)d(r24)
        lwz r12, %(am_data)d(r12)
        lis r0, 0x1000
        cmplw r12, r0
        blt hc_log
        mulli r0, r23, %(slot_size)d
        add r4, r12, r0
        lfs f1, %(slot_dmg)d(r4)
        lis r12, %(hmul_hi)d
        lfs f2, %(hmul_lo)d(r12)
        mr r3, r24
        li r5, 1
        li r6, 1''' + call(HITSTOP_FN) + '''
        mr. r22, r3
        ble hc_log
        lwz r3, %(wstop)d(r24)          # its StopModule
        cmpwi r3, 0
        beq hc_log
        mr r4, r22
        li r5, 1
        lwz r12, 0(r3)
        lwz r12, 0x8C(r12)
        mtctr r12
        bctrl
hc_log:''' + D('''
        lfs f1, 0x20(r1)
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r8, 0x1C(r1)
        lfs f1, 0x24(r1)
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r9, 0x1C(r1)
        slwi r4, r25, 4
        add r4, r4, r21                 # category x 16 + its index (+1)
        mr r5, r23
        mr r6, r29
        mr r7, r22
        lis r3, %(gk_fh_hi)d
        addi r3, r3, %(gk_fh_lo)d''' + osr()) + '''
hc_out: lmw r20, 0x40(r1)
        lwz r0, 0x74(r1)
        mtlr r0
        addi r1, r1, 0x70
        blr

# (r3 an attacker's accessor) -> r3 the first entry (hitbox) with an on node over the clone's box (hcbox +0xC left,
# +0x10 right, +0x14 bottom, +0x18 top), or -1
hc_box: lwz r12, %(watk)d(r3)           # its AttackModule
        li r3, -1
        lis r0, 0x1000
        cmplw r12, r0
        bltlr
        lis r0, 0x8000
        cmplw r12, r0
        bgelr
        lwz r7, %(am_ents)d(r12)        # the entries
        lwz r6, %(am_count)d(r12)
        lis r0, 0x1000
        cmplw r7, r0
        bltlr
        lis r0, 0x8000
        cmplw r7, r0
        bgelr
        cmplwi r6, %(am_max)d
        bgtlr
        lis r8, %(hcbox_hi)d
        addi r8, r8, %(hcbox_lo)d
        li r5, 0                        # the entry
hb_ent: cmpw r5, r6
        bgelr
        mulli r12, r5, %(ent_size)d
        add r12, r12, r7
        lwz r11, 0(r12)                 # its first node index
        lwz r10, 4(r12)                 # its node count
        cmplwi r11, %(node_max)d
        bgt hb_next
        cmplwi r10, %(node_max)d
        bgt hb_next
        slwi r11, r11, 2
        add r11, r11, r12
        addi r11, r11, %(ent_nodes)d    # its first node pointer
hb_node:
        cmpwi r10, 0
        ble hb_next
        lwz r9, 0(r11)
        addi r11, r11, 4
        addi r10, r10, -1
        lis r0, 0x1000
        cmplw r9, r0
        blt hb_node
        lis r0, 0x8000
        cmplw r9, r0
        bge hb_node
        lbz r0, %(node_on)d(r9)
        cmpwi r0, 0
        beq hb_node
        lfs f0, %(node_max_x)d(r9)
        lfs f1, 0xC(r8)
        fcmpu cr0, f0, f1
        blt hb_node
        lfs f0, %(node_min_x)d(r9)
        lfs f1, 0x10(r8)
        fcmpu cr0, f0, f1
        bgt hb_node
        lfs f0, %(node_max_y)d(r9)
        lfs f1, 0x14(r8)
        fcmpu cr0, f0, f1
        blt hb_node
        lfs f0, %(node_min_y)d(r9)
        lfs f1, 0x18(r8)
        fcmpu cr0, f0, f1
        bgt hb_node
        mr r3, r5
        blr
hb_next:
        addi r5, r5, 1
        b hb_ent

''') if 'hitcheck' in feats else '') + '''
''' + ((r'''# ---- burn v1 (feature burn): his water moves (BURN_MOVES: forward / neutral air, the three smashes) burn whoever
# they hit. Each new hit-log node of his AttackModule (and his clones') while he (it) plays one of those motions (his
# MotionModule accessor +0x44, +0x38 the motion kind = the motion.mtable index) adds one instance to the victim's
# list: the hit log of an attack entry (0x174 each, AttackModule +0x14 / +0x18) is the list at [entry +0x130] (+4 the
# first node, +8 the count; a node +4 next, +0x18 the hit object's id, +0x23 the hit container's type: 1 a hurtbox,
# 2 a shield (half the frames, 35 %% of the damage); 0x02C10F40 appends, 0x02C1118C reads); processed counts per
# attacker context (his slot x 3 + 0 him / 1 / 2 a clone) and entry; outside the moves the counts follow the logs.
# The lists: BURN_VICTIMS x BURN_CAP instances of 16 bytes {frames left, tick left << 16 | interval, owner slot,
# damage}; each Greninja ticks only his own (their timing their own: his slot 13 once a frame), raw percent through
# the victim's DamageModule vt +0x74(0, f1) (MSC DamageModule(9, %%)'s op: no hit, no knockback, no hitstun: invincible
# or intangible doesn't matter). Diag S4BA (an instance added), S4BT (each victim's ticks from him, every 60 frames)
burn_him:                               # (r3 his entry, r4 his slot 0-7): his hits, then his burns' ticks
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        mr r31, r4
        lwz r3, %(bacc)d(r3)
        slwi r5, r4, 2                  # his context: slot x 4 (skeleton v1: x 4, 3 the skeleton's)
        li r6, 0
        bl burn_scan
        mr r3, r31
        bl burn_tick
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
w_burn:                                 # (r3 the clone weapon): its hits, for its owner
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stw r31, 0x2C(r1)
        stw r30, 0x28(r1)
        lwz r31, %(wacc)d(r3)
        cmpwi r31, 0
        beq wbn_out
        lwz r30, %(wwork)d(r31)
        cmpwi r30, 0
        beq wbn_out''' + var_get('r30', VAR_SLOT) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r0, 0x1C(r1)
        stw r0, 0x10(r1)''' + var_get('r30', VAR_ID) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r5, 0x1C(r1)                # its id 1 / 2
        lwz r4, 0x10(r1)
        addi r4, r4, -1                 # its owner's slot 0-7
        cmplwi r4, %(slots)d
        bge wbn_out
        addi r0, r5, -1
        cmplwi r0, 1
        bgt wbn_out
        slwi r6, r4, 2
        add r5, r5, r6                  # its context
        li r6, 0
        mr r3, r31
        bl burn_scan
wbn_out:
        lwz r30, 0x28(r1)
        lwz r31, 0x2C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

burn_scan:                              # (r3 an attacker's accessor, r4 the owner's slot, r5 its context, r6 a row or 0:
                                        # the attacker's motion kind's; skeleton v1: its explosion row for every hit)
        stwu r1, -0x50(r1)
        mflr r0
        stw r0, 0x54(r1)
        stmw r22, 0x28(r1)
        mr r31, r4
        mr r30, r5
        cmpwi r3, 0
        beq bs_out
        lwz r12, %(wmotion)d(r3)
        lwz r29, %(watk)d(r3)           # its AttackModule
        cmpwi r29, 0
        beq bs_out
        mr. r28, r6                     # the move row (0: none / by the motion kind)
        bne bs_rows
        cmpwi r12, 0
        beq bs_rows
        lwz r0, %(mm_kind)d(r12)        # its motion kind
        lis r11, %(bmoves_hi)d
        addi r11, r11, %(bmoves_lo)d
        li r10, %(nmoves)d
bs_find:
        lwz r9, 0(r11)
        cmpw r9, r0
        beq bs_found
        addi r11, r11, 20
        addi r10, r10, -1
        cmpwi r10, 0
        bne bs_find
        b bs_rows
bs_found:
        mr r28, r11
bs_rows:
        lwz r27, %(am_ents)d(r29)
        lwz r26, %(am_count)d(r29)
        lis r0, 0x1000
        cmplw r27, r0
        blt bs_out
        lis r0, 0x8000
        cmplw r27, r0
        bge bs_out
        cmplwi r26, %(bents)d
        ble bs_cnt
        li r26, %(bents)d
bs_cnt: lis r25, %(bproc_hi)d
        addi r25, r25, %(bproc_lo)d
        mulli r0, r30, %(bents)d
        add r25, r25, r0                # its processed counts
        li r24, 0                       # the entry
bs_ent: cmpw r24, r26
        bge bs_out
        mulli r12, r24, %(ent_size)d
        add r12, r12, r27
        lwz r23, %(ent_log)d(r12)       # its hit log
        lis r0, 0x1000
        cmplw r23, r0
        blt bs_next
        lis r0, 0x8000
        cmplw r23, r0
        bge bs_next
        lwz r22, 8(r23)                 # its count
        lbzx r0, r25, r24               # processed
        cmpwi r28, 0
        beq bs_sync
        cmplw r22, r0
        bge bs_more
        li r0, 0                        # (a new attack: the log restarted)
bs_more:
        cmplw r22, r0
        ble bs_sync
        mr r10, r0                      # the first new one
        lwz r9, 4(r23)                  # the first node
        li r8, 0
bs_node:
        cmplw r9, r23
        beq bs_sync
        cmplwi r8, 64
        bge bs_sync
        cmplw r8, r10
        blt bs_skip
        stw r8, 0x10(r1)
        stw r9, 0x14(r1)
        stw r10, 0x18(r1)
        mr r3, r9
        mr r4, r28
        mr r5, r31
        bl burn_add
        lwz r8, 0x10(r1)
        lwz r9, 0x14(r1)
        lwz r10, 0x18(r1)
bs_skip:
        addi r8, r8, 1
        lwz r9, 4(r9)
        lis r0, 0x1000
        cmplw r9, r0
        blt bs_sync
        b bs_node
bs_sync:
        cmplwi r22, 255
        ble bs_st
        li r22, 255
bs_st:  stbx r22, r25, r24
bs_next:
        addi r24, r24, 1
        b bs_ent
bs_out: lmw r22, 0x28(r1)
        lwz r0, 0x54(r1)
        mtlr r0
        addi r1, r1, 0x50
        blr

burn_add:                               # (r3 a hit-log node, r4 the move's row, r5 the owner's slot)
        lbz r0, %(node_type)d(r3)
        li r11, 0                       # 0 full, 1 shield
        cmpwi r0, 1
        beq ba_kind
        cmpwi r0, 2
        bnelr
        li r11, 1
ba_kind:
        lwz r12, %(node_obj)d(r3)       # the hit object's id
        srwi r0, r12, 28
        cmpwi r0, 0
        bnelr                           # not a fighter
        rlwinm r12, r12, 16, 20, 31     # its index
        cmplwi r12, %(slots)d
        bgelr
        lis r10, %(btab_hi)d
        addi r10, r10, %(btab_lo)d
        mulli r0, r12, %(bcap16)d
        add r10, r10, r0                # its list
        li r9, %(bcap)d
ba_free:
        lwz r0, 0(r10)
        cmpwi r0, 0
        beq ba_put
        addi r10, r10, 16
        addi r9, r9, -1
        cmpwi r9, 0
        bne ba_free
        blr                             # full (BURN_CAP)
ba_put: lwz r8, 12(r4)                  # the duration
        lfs f1, 4(r4)                   # the damage a tick
        cmpwi r11, 0
        beq ba_full
        srwi r8, r8, 1                  # shielded: half the frames
        lfs f1, 16(r4)                  # its damage: 35 %%, raised to the 3 %% total floor (burn_shield_damage)
        cmpwi r8, 0
        bne ba_full
        li r8, 1
ba_full:
        lwz r9, 8(r4)                   # the interval
        stw r8, 0(r10)
        slwi r0, r9, 16
        or r0, r0, r9
        stw r0, 4(r10)
        stw r5, 8(r10)
        stfs f1, 12(r10)''' + D('''
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        lwz r5, 0(r4)                   # the move (its motion kind)
        mr r4, r12                      # the victim's slot
        mr r6, r11
        fmr f2, f1
        lis r7, %(thousand_hi)d
        lfs f0, %(thousand_lo)d(r7)
        fmuls f2, f2, f0
        fctiwz f2, f2
        stfd f2, 0x10(r1)
        lwz r7, 0x14(r1)
        lwz r8, 4(r10)
        clrlwi r8, r8, 16
        lwz r9, 0(r10)
        lis r3, %(gk_fba_hi)d
        addi r3, r3, %(gk_fba_lo)d''' + osr() + '''
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20''') + '''
        blr

burn_tick:                              # (r3 his slot 0-7): his burns tick, on every victim
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r24, 0x20(r1)
        mr r31, r3
        li r30, 0                       # the victim
bt_vic: cmpwi r30, %(slots)d
        bge bt_done
        lis r29, %(btab_hi)d
        addi r29, r29, %(btab_lo)d
        mulli r0, r30, %(bcap16)d
        add r29, r29, r0
        li r28, %(bcap)d
        li r27, 0                       # its DamageModule (0: none)
        mr r26, r29                     # burn v1.1: any instance on it (anyone's)?
        li r25, %(bcap)d
bt_any: lwz r0, 0(r26)
        cmpwi r0, 0
        bne bt_chk
        addi r26, r26, 16
        addi r25, r25, -1
        cmpwi r25, 0
        bne bt_any
        b bt_next                       # none: nothing to tick or clear
bt_chk: li r24, -1                      # its status kind (-1: not read)
        addi r3, r30, 1
        bl gk_entry
        cmpwi r3, 0
        beq bt_ko                       # no such fighter now (not live)
        lwz r12, %(bacc)d(r3)
        cmpwi r12, 0
        beq bt_ko
        lwz r27, %(wdmg)d(r12)          # its DamageModule
        lwz r11, %(fstatus)d(r12)       # its StatusModule (accessor +0x20)
        lis r0, 0x1000
        cmplw r11, r0
        blt bt_ins
        lis r0, 0x8000
        cmplw r11, r0
        bge bt_ins
        lwz r24, %(st_kind)d(r11)       # its status kind (+0x48)
        addi r10, r24, -%(st_dead)d     # (not r0: addi from r0 reads 0)
        cmplwi r10, %(st_dead_n)d
        bge bt_ins                      # not Dead (0xB1) / Rebirth (0xB2)
bt_ko:  li r0, 0                        # KO'd (or gone): every burn on it ends, anyone's
        li r25, %(bcap)d
        mr r26, r29
bt_clr: stw r0, 0(r26)
        addi r26, r26, 16
        addi r25, r25, -1
        cmpwi r25, 0
        bne bt_clr''' + D('''
        lis r3, %(gk_fbk_hi)d
        addi r3, r3, %(gk_fbk_lo)d
        mr r4, r30
        mr r5, r24
        mr r6, r31''' + osr()) + '''
        b bt_next
bt_ins: lwz r9, 0(r29)
        cmpwi r9, 0
        beq bt_nins
        lwz r12, 8(r29)
        cmpw r12, r31
        bne bt_nins                     # another Greninja's: his own timing
        addi r9, r9, -1                 # (not r0: addi from r0 reads 0)
        stw r9, 0(r29)
        lhz r11, 4(r29)
        addi r11, r11, -1
        sth r11, 4(r29)
        cmpwi r11, 0
        bne bt_nins
        lhz r11, 6(r29)
        sth r11, 4(r29)                 # the next tick
        cmpwi r27, 0
        beq bt_nins                     # (no DamageModule: no damage)
        mr r3, r27
        li r4, 0
        lfs f1, 12(r29)
        lwz r12, 0(r3)
        lwz r12, %(dm_add)d(r12)
        mtctr r12
        bctrl''' + D('''
        lis r12, %(bsum_hi)d
        addi r12, r12, %(bsum_lo)d
        slwi r0, r31, 5
        add r12, r12, r0
        slwi r0, r30, 2
        add r12, r12, r0
        lfs f0, 0(r12)
        lfs f1, 12(r29)
        fadds f0, f0, f1
        stfs f0, 0(r12)''') + '''
        b bt_nins
bt_nins:
        addi r29, r29, 16
        addi r28, r28, -1
        cmpwi r28, 0
        bne bt_ins
bt_next:
        addi r30, r30, 1
        b bt_vic
bt_done:''' + D('''
        lis r29, %(bsum_hi)d
        addi r29, r29, %(bsum_lo)d
        slwi r0, r31, 5
        add r29, r29, r0                # his sums
        lis r12, %(bclock_hi)d
        addi r12, r12, %(bclock_lo)d
        slwi r0, r31, 2
        lwzx r11, r12, r0
        addi r11, r11, 1
        stwx r11, r12, r0
        cmpwi r11, 60
        blt bt_out
        li r11, 0
        stwx r11, r12, r0
        li r30, 0
bt_log: cmpwi r30, %(slots)d
        bge bt_out
        slwi r0, r30, 2
        lfsx f1, r29, r0
        lis r12, %(zero_hi)d
        lfs f0, %(zero_lo)d(r12)
        fcmpu cr0, f1, f0
        beq bt_lnext
        stfsx f0, r29, r0
        lis r12, %(thousand_hi)d
        lfs f0, %(thousand_lo)d(r12)
        fmuls f1, f1, f0
        fctiwz f1, f1
        stfd f1, 0x10(r1)
        lis r12, %(btab_hi)d
        addi r12, r12, %(btab_lo)d
        mulli r0, r30, %(bcap16)d
        add r12, r12, r0
        li r10, %(bcap)d
        li r6, 0                        # his stacks on it
bt_cnt: lwz r0, 0(r12)
        cmpwi r0, 0
        beq bt_cn
        lwz r0, 8(r12)
        cmpw r0, r31
        bne bt_cn
        addi r6, r6, 1
bt_cn:  addi r12, r12, 16
        addi r10, r10, -1
        cmpwi r10, 0
        bne bt_cnt
        lis r3, %(gk_fbt_hi)d
        addi r3, r3, %(gk_fbt_lo)d
        mr r4, r31
        mr r5, r30
        lwz r7, 0x14(r1)''' + osr() + '''
bt_lnext:
        addi r30, r30, 1
        b bt_log
bt_out:''') + '''
        lmw r24, 0x20(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

''') if 'burn' in feats else '') + '''
# ---- the clone's start (its specializer +0x34, (singleton, weapon, init)). v7: nothing (the moon's sets the model
# scale from the init's +0x68; bunshin's paints it black). v8 bstart: bunshin's own, then its black overlay cleared
# (ColorBlendModule slot 0 off). Diag: the init's scale (S4GZ)
w_start:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stw r31, 0x2C(r1)
        mr r31, r4
        stw r5, 0x10(r1)''' + (('''
        lwz r12, %(wacc)d(r31)          # v12 hitcheck: a new clone life: its hit latch off
        cmpwi r12, 0
        beq ws_latched
        lwz r12, %(wwork)d(r12)
        cmpwi r12, 0
        beq ws_latched
        lis r11, %(zero_hi)d
        lfs f1, %(zero_lo)d(r11)''' + var_set('r12', VAR_LATCH) + '''
ws_latched:''') if 'hitcheck' in feats else '') + (('''
        lwz r12, %(wacc)d(r31)          # v13 sway: a new clone life: its swing bind / log latches off
        cmpwi r12, 0
        beq ws_swayed
        lwz r12, %(wwork)d(r12)
        cmpwi r12, 0
        beq ws_swayed
        stw r12, 0x14(r1)
        lis r11, %(zero_hi)d
        lfs f1, %(zero_lo)d(r11)''' + var_set('r12', VAR_BIND) + '''
        lwz r12, 0x14(r1)
        lis r11, %(zero_hi)d
        lfs f1, %(zero_lo)d(r11)''' + var_set('r12', VAR_SWAYLOG) + '''
ws_swayed:''') if 'sway' in feats else '') + (('''
        bl ws_bunshin
        lwz r12, %(wacc)d(r31)
        cmpwi r12, 0
        beq ws_diag
        lwz r3, %(wcol)d(r12)           # its ColorBlendModule: slot 0 (bunshin's black) off
        cmpwi r3, 0
        beq ws_diag
        li r4, 0
        lwz r12, 0(r3)
        lwz r12, %(cclear)d(r12)
        mtctr r12
        bctrl''') if 'bstart' in feats else '') + '''
ws_diag:''' + (('''
        lwz r12, %(wacc)d(r31)          # v9 hurt: its hurtboxes (re)made at each start: cleared, then his 8 added
        cmpwi r12, 0
        beq ws_hurtdone
        lwz r3, %(whit)d(r12)           # its HitModule
        cmpwi r3, 0
        beq ws_hurtdone
        stw r3, 0x14(r1)
        lwz r0, %(hm_count)d(r3)
        stw r0, 0x28(r1)
        lwz r12, 0(r3)
        lwz r12, %(hm_clear)d(r12)
        mtctr r12
        bctrl
        lwz r3, 0x14(r1)
        lis r11, %(hurt_hi)d
        addi r11, r11, %(hurt_lo)d
        stw r11, 0x20(r1)
        li r0, %(nhurt)d
        stw r0, 0x24(r1)
        addi r4, r1, 0x20
        li r5, 0
        lwz r12, 0(r3)
        lwz r12, 0x4C(r12)
        mtctr r12
        bctrl''' + D('''
        lwz r11, 0x14(r1)
        lis r3, %(gk_fk_hi)d
        addi r3, r3, %(gk_fk_lo)d
        mr r4, r11
        lwz r5, %(hm_groups)d(r11)
        lwz r6, 0x28(r1)
        lwz r7, %(hm_count)d(r11)
        li r8, -1
        li r9, -1
        lwz r12, %(hm_group)d(r11)
        cmpwi r12, 0
        beq wsk_g
        lha r8, 4(r12)
        lha r9, 6(r12)
wsk_g:  lwz r10, %(hm_objs)d(r11)''' + osr() + '''
        lwz r11, 0x14(r1)               # v11: S4GY its collision object 0's first words (the container +0xC)
        lwz r11, %(hm_objarr)d(r11)
        li r4, 0
        li r5, 0
        li r6, 0
        li r7, 0
        li r8, 0
        li r9, 0
        lis r0, 0x1000
        cmplw r11, r0
        blt wsy_log
        lis r0, 0x8000
        cmplw r11, r0
        bge wsy_log
        lwz r4, 0(r11)
        lwz r5, 4(r11)
        lwz r6, 8(r11)
        lwz r7, 0xC(r11)
        lwz r8, 0x10(r11)
        lwz r9, 0x14(r11)
wsy_log:
        lis r3, %(gk_fy_hi)d
        addi r3, r3, %(gk_fy_lo)d''' + osr()) + '''
ws_hurtdone:''') if 'hurt' in feats else '') + D('''

        lwz r5, 0x10(r1)
        li r6, -1
        cmpwi r5, 0
        beq ws_log
        lfs f1, 0x68(r5)
        lis r12, %(hundred_hi)d
        lfs f0, %(hundred_lo)d(r12)
        fmuls f1, f1, f0
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r6, 0x1C(r1)
ws_log: mr r4, r5
        mr r5, r6
        lis r3, %(gk_fz_hi)d
        addi r3, r3, %(gk_fz_lo)d''' + osr()) + '''
        lwz r31, 0x2C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr''' + (('''
ws_bunshin:''' + tail(BUNSHIN_START)) if 'bstart' in feats else '') + '''

# ---- v8 diag: a clone's draw state (r3 its accessor, r4 its id): S4GM VisibilityModule +8 / is_visible, the
# ModelModule's mode / its instance's drawn byte, ColorBlendModule slot 0 / enabled; S4GN z, scale, LinkModule mask
''' + D('''w_ddiag:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r31, 0x3C(r1)
        stw r30, 0x38(r1)
        mr r31, r3
        stw r4, 0x10(r1)
        li r0, -1
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        stw r0, 0x1C(r1)
        stw r0, 0x20(r1)
        stw r0, 0x24(r1)
        stw r0, 0x28(r1)
        lwz r30, %(wvis)d(r31)
        cmpwi r30, 0
        beq wd_model
        lbz r0, 8(r30)
        stw r0, 0x14(r1)
        mr r3, r30
        lwz r12, 0(r3)
        lwz r12, 0xA4(r12)
        mtctr r12
        bctrl
        clrlwi r3, r3, 24
        stw r3, 0x18(r1)
wd_model:
        lwz r12, %(wmodel)d(r31)
        cmpwi r12, 0
        beq wd_colour
        lwz r0, 8(r12)
        stw r0, 0x1C(r1)
        lwz r11, 0xC(r12)
        cmpwi r11, 0
        beq wd_colour
        lbz r0, 0x7DB(r11)
        stw r0, 0x20(r1)
wd_colour:
        lwz r12, %(wcol)d(r31)
        cmpwi r12, 0
        beq wd_log
        lbz r0, 0x50(r12)
        stw r0, 0x24(r1)
        lbz r0, 0xD9(r12)
        stw r0, 0x28(r1)
wd_log: lis r3, %(gk_fm_hi)d
        addi r3, r3, %(gk_fm_lo)d
        lwz r4, 0x10(r1)
        lwz r5, 0x14(r1)
        lwz r6, 0x18(r1)
        lwz r7, 0x1C(r1)
        lwz r8, 0x20(r1)
        lwz r9, 0x24(r1)
        lwz r10, 0x28(r1)''' + osr() + '''
        li r0, -1
        stw r0, 0x14(r1)
        stw r0, 0x18(r1)
        stw r0, 0x1C(r1)
        lwz r12, %(wpost)d(r31)
        cmpwi r12, 0
        beq wd_link
        lfs f1, 0x18(r12)
        fctiwz f1, f1
        stfd f1, 0x30(r1)
        lwz r0, 0x34(r1)
        stw r0, 0x14(r1)
        lfs f1, 0x5C(r12)
        lis r11, %(hundred_hi)d
        lfs f0, %(hundred_lo)d(r11)
        fmuls f1, f1, f0
        fctiwz f1, f1
        stfd f1, 0x30(r1)
        lwz r0, 0x34(r1)
        stw r0, 0x18(r1)
wd_link:
        lwz r12, %(wlink)d(r31)
        cmpwi r12, 0
        beq wd_log2
        lwz r0, 0x84(r12)
        stw r0, 0x1C(r1)
wd_log2:
        lis r3, %(gk_fn_hi)d
        addi r3, r3, %(gk_fn_lo)d
        lwz r4, 0x10(r1)
        lwz r5, 0x14(r1)
        lwz r6, 0x18(r1)
        lwz r7, 0x1C(r1)
        lwz r8, %(wmodel)d(r31)''' + osr() + '''
        li r5, 0                        # v11: S4GQ its swing: MotionModule, +0x38, the motion object, its swing system,
        li r6, 0                        # the system's flags (+0xB4), set up (motion +0xF1)
        li r7, 0
        li r8, 0
        li r9, -1
        li r10, -1
        lwz r5, %(wmotion)d(r31)
        cmpwi r5, 0
        beq wd_qlog
        lwz r6, %(mm_swing)d(r5)
        lwz r7, %(mm_motion)d(r5)
        lis r0, 0x1000
        cmplw r7, r0
        blt wd_qlog
        lis r0, 0x8000
        cmplw r7, r0
        bge wd_qlog
        lbz r10, 0xF1(r7)
        lwz r8, 0x20(r7)
        lis r0, 0x1000
        cmplw r8, r0
        blt wd_qlog
        lis r0, 0x8000
        cmplw r8, r0
        bge wd_qlog
        lwz r9, 0xB4(r8)
wd_qlog:
        lis r3, %(gk_fq_hi)d
        addi r3, r3, %(gk_fq_lo)d
        lwz r4, 0x10(r1)''' + osr() + ('''
        lwz r12, %(whit)d(r31)          # v9: its HitModule: hurtboxes, collision objects, the first hurtbox's record
        cmpwi r12, 0
        beq wd_end
        lwz r5, %(hm_count)d(r12)
        lwz r6, %(hm_objs)d(r12)
        li r7, 0
        li r8, 0
        li r9, 0
        li r10, 0
        lwz r11, %(hm_group)d(r12)
        cmpwi r11, 0
        beq wd_hlog
        lha r0, 4(r11)
        lwz r11, %(hm_recs)d(r12)       # the records (checked to be in the data range: a diag never faults)
        lis r3, 0x1000
        cmplw r11, r3
        blt wd_hlog
        lis r3, 0x8000                  # (MEM2, with the Extended Memory pack up to 0x80000000)
        cmplw r11, r3
        bge wd_hlog
        slwi r0, r0, 6
        add r11, r11, r0
        lwz r7, 0(r11)
        lwz r8, 4(r11)
        lwz r9, 8(r11)
        lwz r10, 0xC(r11)
wd_hlog:
        lis r3, %(gk_fo_hi)d
        addi r3, r3, %(gk_fo_lo)d
        lwz r4, 0x10(r1)''' + osr() if 'hurt' in feats else '') + '''
wd_end:
        lwz r30, 0x38(r1)
        lwz r31, 0x3C(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr
''') + '''
# ---- v7: the name tag: the SET_CURSOR message (as the ACMD command's handler 0x02BE7C80: {0xA, visible} to the
# fighter's object id ([accessor + 0]) through the object messages 0x02BF2108 / 0x02BF019C); (r3 his entry, r4 visible)
gk_tag: stwu r1, -0x50(r1)
        mflr r0
        stw r0, 0x54(r1)
        stw r31, 0x4C(r1)
        mr r31, r4
        lwz r12, %(bacc)d(r3)
        cmpwi r12, 0
        beq gt_out
        lwz r5, 0(r12)                  # his object id
        li r11, 0xA
        stw r11, 8(r1)
        stw r31, 0xC(r1)
        addi r0, r1, 8
        stw r0, 0x10(r1)
        li r11, 2
        stw r11, 0x14(r1)
        lis r11, %(msgk_hi)d
        addi r11, r11, %(msgk_lo)d
        stw r11, 0x18(r1)
        li r0, 6
        stw r0, 0x1C(r1)
        addi r0, r1, 0x10
        stw r0, 0x20(r1)
        li r0, 0
        stw r0, 0x24(r1)
        stw r5, 0x48(r1)
        lis r3, %(mgr_hi)d
        lwz r3, %(mgr_lo)d(r3)
        addi r4, r1, 0x28
        li r6, 1''' + call(MSG_HANDLE) + D('''
        addi r3, r1, 0x28''' + call(HANDLE_GONE) + '''
        mr r6, r3                       # v9 diag: 0 = his object found (the message reaches it)
        lis r3, %(gk_fw_hi)d
        addi r3, r3, %(gk_fw_lo)d
        mr r4, r31
        lwz r5, 0x48(r1)
        lwz r7, 0x28(r1)''' + osr()) + '''
        addi r3, r1, 0x28
        addi r4, r1, 0x18''' + call(MSG_SEND) + '''
gt_out: lwz r31, 0x4C(r1)
        lwz r0, 0x54(r1)
        mtlr r0
        addi r1, r1, 0x50
        blr

# ---- v7: a child of a panel clip by name: (r3 parent, r4 name index into gk_names) -> r3 (0: none). The names are
# interned every call (the trait badge's lesson: the flx runtime's name table can be rebuilt)
gk_find:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        stw r30, 0x18(r1)
        mr r31, r3
        mr r30, r4
        lis r3, %(apool_hi)d
        lwz r3, %(apool_lo)d(r3)
        cmpwi r3, 0
        beq gf_none
        addi r3, r3, 0x24
        lis r12, %(gk_names_hi)d
        addi r12, r12, %(gk_names_lo)d
        slwi r11, r30, 3
        add r12, r12, r11
        lwz r4, 0(r12)
        lwz r5, 4(r12)''' + call(FLX_INTERN) + '''
        cmpwi r3, 0
        beq gf_none
        lis r12, %(gk_atoms_hi)d
        addi r12, r12, %(gk_atoms_lo)d
        slwi r11, r30, 2
        stwx r3, r12, r11
        add r4, r12, r11
        mr r3, r31''' + call(FLX_FIND) + '''
        b gf_out
gf_none:
        li r3, 0
gf_out: lwz r30, 0x18(r1)
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# ---- v7: the round gauge's moving parts: (r3 gkgauge_mc, r4 panel slot, r5 value 0-100): each ring (gk_names 1-4)
# turned by its own speed (gk_speeds, degrees a frame) from its angle kept per slot (gk_angles), the fill (5) on the
# value's frame (1 + value / 10, rounded) and stopped
gk_rings:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r26, 0x28(r1)
        mr r31, r3
        mr r30, r5
        slwi r29, r4, 4                 # this slot's 4 angles
        lis r12, %(gk_angles_hi)d
        addi r12, r12, %(gk_angles_lo)d
        add r29, r29, r12
        li r28, 1
gr_ring:
        cmpwi r28, 5
        bge gr_fill
        mr r3, r31
        mr r4, r28
        bl gk_find
        mr. r27, r3
        beq gr_next
        slwi r26, r28, 2
        addi r26, r26, -4
        add r26, r26, r29               # its angle
        lis r12, %(gk_speeds_hi)d
        addi r12, r12, %(gk_speeds_lo)d
        add r12, r12, r26
        subf r12, r29, r12              # (speeds + 4 x (ring - 1))
        lfs f0, 0(r12)
        lfs f1, 0(r26)
        fadds f1, f1, f0
        lis r12, %(deg360_hi)d
        lfs f13, %(deg360_lo)d(r12)
        fcmpu cr0, f1, f13
        blt gr_lo
        fsubs f1, f1, f13
gr_lo:  lis r12, %(zero_hi)d
        lfs f0, %(zero_lo)d(r12)
        fcmpu cr0, f1, f0
        bge gr_set
        fadds f1, f1, f13
gr_set: stfs f1, 0(r26)
        mr r3, r27''' + call(FLX_ROTATE) + '''
gr_next:
        addi r28, r28, 1
        b gr_ring
gr_fill:
        mr r3, r31
        li r4, 5
        bl gk_find
        mr. r27, r3
        beq gr_out
        mulli r4, r30, 10
        addi r4, r4, 50
        li r0, 100
        divwu r4, r4, r0
        addi r4, r4, 1                  # frame 1 - 11
        mr r3, r27''' + call(FLX_GOTO) + '''
        li r0, 1
        sth r0, 0x9C(r27)               # stopped
gr_out: lmw r26, 0x28(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

# ---- v6: the charge / ability / burnout gauge on his damage panel: the panel's update (its vtable +0x3C, the trait
# badge cave's hook before us) then, for each panel slot of a Greninja, his VAR_19 (mode x 1000 + 0-100) on Little
# Mac's KO meter (ko_mc, the slot's +0x18C): shown and set (0x02663C54: 0 empty, 1-99 ten steps, 100 "KO" blinking:
# ready) with a colour per mode (1 charge: as is, 2 the ability draining: blue, 3 the burnout draining: grey); mode 0:
# hidden
gk_panel:
        stwu r1, -0x50(r1)
        mflr r0
        stw r0, 0x54(r1)
        stmw r24, 0x2C(r1)
        mr r31, r3''' + call(PANEL_PREV) + '''
        stw r3, 0x10(r1)
        li r26, 0
gp_slot:
        cmpwi r26, %(slots)d
        bge gp_done
        mulli r30, r26, %(pslot)d
        add r30, r30, r31
        addi r30, r30, 0xC0             # the panel slot
        lha r0, 8(r30)
        cmpwi r0, 2
        beq gp_next                     # empty
        lbz r0, 0xA(r30)
        extsb r0, r0
        cmpwi r0, %(gkind)d
        bne gp_next
        lwz r29, 0x18C(r30)             # ko_mc
        cmpwi r29, 0
        beq gp_next
        lha r5, 0(r30)                  # its fighter: the manager's entry, the current object (the trait badge's way)
        cmpwi r5, 0
        blt gp_next
        lis r12, %(fm_hi)d
        lwz r12, %(fm_lo)d(r12)
        cmpwi r12, 0
        beq gp_next
        lwz r0, 0x18(r12)
        cmplw r5, r0
        bge gp_next
        slwi r5, r5, 2
        add r12, r12, r5
        lwz r12, 0x24(r12)
        cmpwi r12, 0
        beq gp_next
        lbz r5, 0x14E9(r12)
        lwz r0, 0xDB4(r12)
        cmplw r5, r0
        bge gp_next
        slwi r5, r5, 2
        add r12, r12, r5
        lwz r12, 0xDC0(r12)
        cmpwi r12, 0
        beq gp_next
        lwz r0, 4(r12)
        cmpwi r0, %(gkind)d
        bne gp_next
        lwz r12, 0xC(r12)
        cmpwi r12, 0
        beq gp_next
        lwz r28, 0x28(r12)              # his WorkModule
        cmpwi r28, 0
        beq gp_next''' + var_get('r28', VAR_GAUGE) + '''
        fctiwz f1, f1
        stfd f1, 0x18(r1)
        lwz r27, 0x1C(r1)               # mode x 1000 + value
        li r0, 1000
        divwu r25, r27, r0              # the mode
        mullw r10, r25, r0
        subf r28, r10, r27              # the value
        cmplwi r25, 3
        ble gp_ok
        li r25, 0
gp_ok:  lwz r3, 0x5C(r30)               # v7: the round gauge (gkgauge_mc in his panel, tools/gekkouga_gauge_flx.py)?
        cmpwi r3, 0
        beq gp_ko
        li r4, 0
        bl gk_find
        mr. r24, r3
        beq gp_ko
        mr r3, r29
        li r4, 0''' + call(PANEL_VISIBLE) + '''
        cmpwi r25, 0
        bne gp_cshow
        mr r3, r24
        li r4, 0''' + call(PANEL_VISIBLE) + '''
        b gp_log
gp_cshow:
        mr r3, r24
        li r4, 1''' + call(PANEL_VISIBLE) + '''
        mr r3, r24
        lis r4, %(ctf_hi)d
        addi r4, r4, %(ctf_lo)d
        mulli r0, r25, 12
        add r4, r4, r0''' + call(PANEL_COLOUR) + '''
        mr r3, r24
        mr r4, r26
        mr r5, r28
        bl gk_rings
        b gp_log
gp_ko:  cmpwi r25, 0
        bne gp_show
        mr r3, r29
        li r4, 0''' + call(PANEL_VISIBLE) + '''
        b gp_log
gp_show:
        mr r3, r29
        li r4, 1''' + call(PANEL_VISIBLE) + '''
        mr r3, r31
        mr r4, r26
        mr r5, r28''' + call(PANEL_KO_SET) + '''
        mr r3, r29
        lis r4, %(ctf_hi)d
        addi r4, r4, %(ctf_lo)d
        mulli r0, r25, 12
        add r4, r4, r0''' + call(PANEL_COLOUR) + '''
gp_log:''' + D('''
        lis r11, %(gk_gaugelog_hi)d
        addi r11, r11, %(gk_gaugelog_lo)d
        slwi r12, r26, 2
        li r0, 10
        divwu r10, r27, r0
        lwzx r0, r11, r12
        cmpw r0, r10
        beq gp_next
        stwx r10, r11, r12
        lis r3, %(gk_fb_hi)d
        addi r3, r3, %(gk_fb_lo)d
        mr r4, r26
        mr r5, r25
        mr r6, r28''' + osr()) + '''
gp_next:
        addi r26, r26, 1
        b gp_slot
gp_done:
        lwz r3, 0x10(r1)
        lmw r24, 0x2C(r1)
        lwz r0, 0x54(r1)
        mtlr r0
        addi r1, r1, 0x50
        blr

# ---- v10: the name tag, at the player-cursor HUD's per-player update (PLYC_HOOK: its `bl 0x028E3E18(hud, player)`,
# the 8-player loop of the HUD update 0x028E3FDC's caller): that function shows the cursor only when the player block's
# byte +0x2B75 (PLYC_SHOW, hud + player x 0x2B00) is set (else it fades it out: +0x2AB8 alpha). While s13 keeps the
# player's hide counter up (his tag bit), the byte is 0 before every call; when it runs out, its saved value goes back
plyc:   cmplwi r4, %(slots)d
        bge plyc_go
        slwi r12, r4, 2
        lis r11, %(gk_hide_hi)d
        addi r11, r11, %(gk_hide_lo)d
        lwzx r10, r11, r12
        mulli r9, r4, %(plyc_blk)d
        add r9, r9, r3                  # r9 = the player's block
        lis r8, %(gk_plyr_hi)d
        addi r8, r8, %(gk_plyr_lo)d
        lwzx r7, r8, r12                # its saved flag + 1 (0: not hidden by us)
        cmpwi r10, 0
        beq plyc_back
        addi r10, r10, -1
        stwx r10, r11, r12
        cmpwi r7, 0
        bne plyc_hide
        lbz r7, %(plyc_show)d(r9)
        addi r7, r7, 1
        stwx r7, r8, r12''' + D('''
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stw r3, 0x8(r1)
        stw r4, 0xC(r1)
        stw r9, 0x10(r1)
        mr r5, r4
        lha r6, %(plyc_id)d(r9)
        addi r7, r7, -1
        lwz r8, %(plyc_alpha)d(r9)
        mr r4, r3
        lis r3, %(gk_fu_hi)d
        addi r3, r3, %(gk_fu_lo)d''' + osr() + '''
        lwz r3, 0x8(r1)
        lwz r4, 0xC(r1)
        lwz r9, 0x10(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40''') + '''
plyc_hide:
        li r0, 0
        stb r0, %(plyc_show)d(r9)
        b plyc_go
plyc_back:
        cmpwi r7, 0
        beq plyc_go
        addi r7, r7, -1                 # the saved flag back, once
        stb r7, %(plyc_show)d(r9)
        li r0, 0
        stwx r0, r8, r12
plyc_go:''' + tail(PLYC_FN) + '''

''' + (sk_source(D, L['old_hit'], L['vt_orig'][0x94]) if skel else '') + '''
# ---- burn v1.2: the clear-all chain (a leaf: r3 / r10 / LR kept, r0 r4-r9 r11 r12 free): the per-match state
gk_clear:
        li r0, 0''' + (('''
        lis r12, %(sk_latch_hi)d
        addi r12, r12, %(sk_latch_lo)d
        li r11, %(nlatch)d
gc_lat: stw r0, 0(r12)                  # skeleton v1: its attackers latched
        addi r12, r12, 4
        addi r11, r11, -1
        cmpwi r11, 0
        bne gc_lat''') if skel else '') + (('''
        lis r12, %(btab_hi)d
        addi r12, r12, %(btab_lo)d
        li r11, %(nbtab)d
gc_btab:
        stw r0, 0(r12)                  # every burn
        addi r12, r12, 4
        addi r11, r11, -1
        cmpwi r11, 0
        bne gc_btab
        lis r12, %(bproc_hi)d
        addi r12, r12, %(bproc_lo)d
        li r11, %(nbproc)d
gc_bproc:
        stw r0, 0(r12)                  # the hit logs' processed counts
        addi r12, r12, 4
        addi r11, r11, -1
        cmpwi r11, 0
        bne gc_bproc''') if 'burn' in feats else '') + '''
        lis r12, %(gk_hide_hi)d
        addi r12, r12, %(gk_hide_lo)d
        li r11, 16
gc_hide:
        stw r0, 0(r12)                  # the tag hide counters, the slow states (the cursor's saved byte is kept: its
        addi r12, r12, 4                # restore runs once the counter is 0)
        addi r11, r11, -1
        cmpwi r11, 0
        bne gc_hide
        lis r12, %(gk_tags_hi)d
        addi r12, r12, %(gk_tags_lo)d
        li r11, %(slots)d
gc_tags:
        stw r0, 0(r12)
        addi r12, r12, 4
        addi r11, r11, -1
        cmpwi r11, 0
        bne gc_tags
        lis r12, %(gk_clr_hi)d
        lwz r11, %(gk_clr_lo)d(r12)
        addi r11, r11, 1
        stw r11, %(gk_clr_lo)d(r12)
        b 0x%(clear_back)08X

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
''' + ('''sk_dcase:
        lis r3, %(sk_desc_hi)d
        addi r3, r3, %(sk_desc_lo)d
        blr
''' if skel else '')
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
    if 'hurt' in feats or diag:
        struct.pack_into('>I', vb, 0x1C, lab['w_init'])
    struct.pack_into('>I', vb, 0x34, lab['w_start'])  # v7: not the moon's start (it sets the model scale from the init's
                                                      # +0x68: the generate's, 0 for ours: the user's v6 invisible clones)
    for o in (POLL_SLOTS if 'hurt' in feats or diag else (0x94,) if feats & {'sway', 'hitcheck', 'burn'} else ()):
        struct.pack_into('>I', vb, o, lab['wp_%X' % o])
    out.blob(A['w_vt'], bytes(vb), 'clone vtable (bunshin copy, +0x1C / +0x64 / +0x84 / +0x8C / +0x94 / +0xAC ours)')
    if skel:
        vs = bytearray(img.blob(L['svt'], L['vsize']))
        struct.pack_into('>I', vs, W.HIT_METHOD, lab['sk_hit'])
        struct.pack_into('>I', vs, 0x34, lab['sk_start'])
        struct.pack_into('>I', vs, 0x94, lab['sk_94'])
        out.blob(A['sk_vt'], bytes(vs), 'skeleton vtable (the moon\'s, +0x34 / +0x94 / +0xAC ours)')

    # ---- hooks in place (each asserted)
    def asm1(at, text):
        return K.one(at, text)
    out.put(G1_HOOK, asm1(G1_HOOK, 'bl 0x%X' % lab['g1_stub']), 'his group-1 init: our desc', ORIGINAL[G1_HOOK])
    out.put(SLOT13, asm1(SLOT13, 'b 0x%X' % lab['s13']), 'his slot 13', ORIGINAL[SLOT13])
    out.put(SLOT42, asm1(SLOT42, 'b 0x%X' % lab['s42']), 'his slot 42', ORIGINAL[SLOT42])
    out.put(SLOT43, asm1(SLOT43, 'b 0x%X' % lab['s43']), 'his slot 43', ORIGINAL[SLOT43])
    out.put(HUD_HOOK, asm1(HUD_HOOK, 'bl 0x%X' % TRAMP), 'the HUD cursor update', ORIGINAL[HUD_HOOK])
    out.put(PLYC_HOOK, asm1(PLYC_HOOK, 'bl 0x%X' % PLYC_TRAMP), 'the player cursor update (v10)', ORIGINAL[PLYC_HOOK])
    t = Asm(PLYC_TRAMP)
    t.asm(tail(lab['plyc']))
    for i, w in enumerate(t.words()):
        out.put(PLYC_TRAMP + 4 * i, w, 'player cursor trampoline', 0)
    t = Asm(TRAMP)
    t.asm(tail(lab['hud']))
    for i, w in enumerate(t.words()):
        out.put(TRAMP + 4 * i, w, 'HUD trampoline', 0)
    out.put(DESC_TABLE + 4 * GK_KIND, lab['gk_dcase'], 'his fighter descriptor case', GK_DESC_CASE)
    ct = OL.clear_tail(img.w)                         # burn v1.2: the clear-all chain's last `b CLEAR_BACK` -> gk_clear
    assert not CAVE <= ct < LIMIT, 'clear chain already through this cave'
    out.put(ct, asm1(ct, 'b 0x%X' % lab['gk_clear']), 'the clear-all chain -> gk_clear (burn v1.2)', img.w(ct))
    assert PANEL_VT not in img.relocs(), 'the panel update word has a relocation'
    out.put(PANEL_VT, lab['gk_panel'], 'the damage panel update: the gauge (then the trait badge / the game)', PANEL_PREV)
    # ---- the weapon cave's tables, kind 0x1A1 (and skeleton v1's 0x1A2)
    def register(kind, nstr, u16_clear, dcase, base, single, row):
        kk = kind - W.OLD_N
        for nm, addr in W.NAME_TABLES:
            v = {'owner': owner_str, 'name': nstr, 'folder': nstr}.get(nm, img.w(addr + 4 * CLONE_BASE))
            out.put(T[nm] + 4 * kind, v, 'table %s 0x%X' % (nm, kind), img.w(addr))
        for nm, addr, es, invalid in W.STATIC_TABLES:
            rd = {1: img.b, 2: img.h, 4: img.w}[es]
            v = rd(addr + es * CLONE_BASE)
            if es == 2:
                v &= ~u16_clear
            at = T[nm] + es * kind
            assert rd(at) == invalid, 'table %s: kind 0x%X in use' % (nm, kind)
            wa = at & ~3
            word = out.words[wa][0] if wa in out.words else img.w(wa)
            sh = 8 * (4 - es - (at - wa))
            mask = ((1 << (8 * es)) - 1) << sh
            word = (word & ~mask) | (v << sh)
            out.words.pop(wa, None)
            out.put(wa, word, 'table %s 0x%X' % (nm, kind))
        out.put(T['dt'] + 4 * kk, dcase, 'descriptor case 0x%X' % kind, 0)
        out.put(T['bt'] + 4 * kk, base, 'base kind 0x%X' % kind, 0xFFFF)
        out.put(T['st'] + 4 * kk, single, 'singleton case 0x%X' % kind, 0)
        out.put(T['rt'] + 4 * kk, (row - W.MODULE_TABLE) & 0xFFFFFFFF, 'own module row 0x%X' % kind, 0)
    # v3: loaded with him (bunshin's 0x1: only with his Final Smash)
    register(CLONE_KIND, A['gk_str'], CATEGORY_BITS, lab['w_dcase'], base_of(feats), A['w_single'], A['w_row'])
    if skel:
        # skeleton v1: loaded with him, its model c00 only (no 0x10: the owner's colour); pump's template (attack)
        register(SK_KIND, A['sk_str'], CATEGORY_BITS | 0x10, lab['sk_dcase'], ATTACK_BASE, A['sk_single'], A['sk_row'])
    info = dict(A=A, labels=lab, T=T, layout=L, end=end, owner_str=owner_str, feats=feats, diag=diag, clear_at=ct)
    return out, info


def args(rpx, diag=False, feats=None):
    out, _info = build(rpx, diag, feats)
    return ['textregion:0x%X' % TEXT_REGION, 'grow:0x%08X' % LIMIT] + \
        ['0x%08X=0x%08X' % (a, w) for a, (w, _n) in sorted(out.words.items())]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rpx', required=True)
    ap.add_argument('--diag', action='store_true')
    ap.add_argument('--info', action='store_true')
    ap.add_argument('--features', default=None, help='comma list of %s (default: %s); "" = the safe set' %
                    (','.join(sorted(FEATURES)), ','.join(sorted(RELEASE))))
    o = ap.parse_args()
    feats = RELEASE if o.features is None else frozenset(f for f in o.features.split(',') if f)
    if o.info:
        out, info = build(o.rpx, o.diag, feats)
        for nm, at in sorted(info['A'].items(), key=lambda kv: kv[1]):
            print('%-10s 0x%08X' % (nm, at))
        for nm in ('g1_stub', 'hud', 's13', 's42', 's43', 'gk_entry', 'w_hit', 'w_init', 'w_poll', 'gk_panel', 'gk_dcase',
                   'w_dcase'):
            print('%-10s 0x%08X' % (nm, info['labels'][nm]))
        print('end        0x%08X (limit 0x%08X), %d words' % (info['end'], LIMIT, len(out.words)))
        return
    print(' '.join(args(o.rpx, o.diag, feats)))


if __name__ == '__main__':
    main()
