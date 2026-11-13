#!/usr/bin/env python3
"""New ACMD commands (native): prints rpx_patch.py arguments.

  python3 tools/rpx_patch.py IN.rpx OUT.rpx ... $(python3 tools/acmd_ext_cave.py)

How the game runs ACMD (docs/native-notes.md "ACMD commands: dispatch"): when a script is loaded,
0x02BEE1CC / 0x02BEE2F8 replace each command's CRC (the first word of each command) by its index,
from the binary search 0x02BEE154 over the sorted {crc, index} table 0x100FAAB8 (584 pairs), and
step to the next command with the size table 0x100FA198 (words, header included: CMD_SIZES). The
interpreter 0x02BEE63C then calls handler[index] (table 0x10350ED8, at 0x02BEE84C) as
handler(r3 module accessor, r4, r5 script state, r6 (+8: execute flag), r7 the parameters); a handler
moves the script on itself (state +4 += its size in bytes, when state +8 is -1) and returns 2.

New commands get indices NEW_BASE.. (584 + k):
- LOOKUP (0x02BEE1BC, the binary search's not-found `li r3, -1`): look the CRC up in our table.
- SIZE1 / SIZE2 (0x02BEE2C0 / 0x02BEE3C0, the two loaders' size reads): an index >= NEW_BASE reads
  our size table.
- FETCH (0x02BEE84C, the interpreter's handler read): an index >= NEW_BASE reads our handler table.

Commands (CRC = zlib.crc32 of the name as written, like the game's own):
- Extra_Special_Hitbox: Special_Hitbox's 41 parameters, then EXTRA (below).
- Extra_Extended_Special_Hitbox: Extended_Special_Hitbox's 43, then EXTRA.
  The handler calls the original handler (which makes the hitbox and steps over its own size), steps
  over the extra words too, and when the command runs (execute flag) records the extras for the
  hitbox's AttackModule slot ([accessor +0x50] +0x40 + ID * 0x84): an entry of the extras table
  (ENTRIES, round robin, reused for the same slot), with the slot's data +0x20..+0x2C (angle,
  KBG, FKB, BKB) and +0x3C (bone) as a check, and the entry's number tagged into the slot's data
  +0x66 (a halfword no hitbox builder writes: TAG | n). ext_find(data) gives the entry back at hit
  time only if the tag, the slot and the check words all still match (a later plain hitbox in that
  slot has different data / tag).
EXTRA = HitstunMul, HitstopMul, HitstopFrames, SelfHitstopMul, SelfHitstopFrames, DIMul: multipliers
<= 0 mean 1 (unchanged; a negative HitstunMul adds that many hitstun frames instead), frames 0 mean
"computed" (> 0 replaces the hitstop).
The hit-time hooks that use them are in this file too (HIT_* below), see docs/acmd-extra-commands.md.

The other commands (NEW_CMDS, ...) and the per-object variables / timers are described where they are defined;
New_Var (exe_v40: NV_* / nv_code) grows the text region (textregion: / grow: in the output) and redirects the
WorkModule vtables' int ops (their relocations moved with reloc:). Gravity_Set (exe_v42: GS_* / gs_code) sits after
New_Var's code in that region and hooks the fighters' gravity energy update and damage reaction decision. The hitbox
variables (exe_v43: HV_* / hv_code, in the free space after ACC_CACHE): the Extra hitbox commands' Damage / Angle /
KBG / FKB / BKB / Size take a variable (handler table -> hv_extra, which wraps h_extra), FOLLOW re-reads them every frame
(FRAME_HOOK -> hv_fhook before hk_frame, WM_RESET -> hv_wmreset before hk_wmreset), and user_entry's 0x3C0-0x3C8 (from
gs_var's gv_zero) are the stick angles / lengths and the rotation.
"""
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppcasm import Asm  # noqa: E402

CAVE = 0x04B90000
LIMIT = 0x04B9A000
TABLE = 0x04B92000               # extras entries (zero at load)
ENTRIES = 128
ENTRY = 0x30
TAG = 0xEC00
TAG_OFF = 0x66

LOOKUP = 0x02BEE1BC              # li r3, -1 (then blr)
SIZE1 = 0x02BEE2C0               # slwi r10, r3, 2 / stwx r3, r28, r5 / lwzx r0, r10, r4 -> 0x02BEE2CC
SIZE2 = 0x02BEE3C0               # slwi r11, r3, 2 / stwx r3, r28, r5 / lwzx r12, r11, r30 -> 0x02BEE3CC
FETCH = 0x02BEE84C               # slwi r6, r7, 2 / lwzx r0, r6, r29 -> 0x02BEE854 (r12 is live)
NEW_BASE = 584

# hit time (docs/acmd-extra-commands.md): the hit info's +0x44 is a copy of the hitbox data, so the
# tag is at hit info +0x44 +0x66; find_copy checks the tag and the check words (not the slot).
HIT_STUN = 0x02C25C88            # victim: stfs f28, 0x30(r30) (hitstun = knockback x 0.4 -> DamageModuleF(1));
                                 #   r27 victim accessor, r28 hit info; free r5 r8 r9 r10 r12 f9-f13
HIT_VSTOP = 0x02C25A78           # victim: cmpwi r19, 2, r20 = final hitstop frames; free r0 r3-r12 f0 f12 f13
HIT_AMUL = 0x02C2645C            # attacker: or. r27, r3, r3 (r3 = hitstop before the rate); r30 hit info
HIT_AFIX = 0x02C264C4            # attacker: lwz r27, 0x10(r1) (after the rate); r3 / ctr live
SLOT_SET = 0x02C0874C            # AttackModule vt +0x54 (set a hitbox, 0x02C086A8): after its 0x68-byte copy of
                                 #   the data into the slot (r26) and vt +0x5C, lwz r10, 0x14(r28): the tag halfword
                                 #   cleared there (a plain hitbox copied whatever its data buffer held; an Extra one
                                 #   is tagged after it). (0x02C08730, right after the copy, is strike_cave.py's.)
DI_STAT = 0x037EE180             # kirby_stat_cave.py's get_float path: bnelr after cmpwi r11, 3 (not a fighter stat)
DI_ID = 0x11A                    # fighter_param 0x0200011A: max DI angle (read by every fighter's MSC damage code)
DI_SLOTS = 16
HIT_ORIG = {HIT_STUN: 0xD39E0030, HIT_VSTOP: 0x2C130002, HIT_AMUL: 0x7C7B1B79, HIT_AFIX: 0x83610010,
            DI_STAT: 0x4C820020, SLOT_SET: 0x815C0014}

# per-object state (user variables, timers, tracking), keyed by the object's WorkModule
OBJS = 0x04B94000                # OBJ_N entries of OBJ_SIZE (zero at load)
OBJ_N = 48
OBJ_SIZE = 0x100                 # +0 WorkModule, +4 accessor (last seen), +8 tracking frames left (int, < 0 = until
                                 # stopped), +0xC speed, +0x10 cos(turn) (< -1.5: turn at once), +0x14 sin(turn),
                                 # +0x18 range squared (0 = any), +0x1C mode, +0x20 timers[16], +0x60 vars[32],
                                 # +0xE0 no-gravity tracking: the vertical speed last set, +0xE4 1 = +0xE0 is set,
                                 # +0xE8 / +0xF0 New_Var's masks (NV_DECL / NV_INT); its values: NV_POOL
ACC_CACHE = 0x04B97000           # 64 x {WorkModule, accessor}, filled by the per-frame hook for every object
THREADS = 0x04B98000             # THREAD_N slots of THREAD_SIZE: +0 accessor (0 = free), +4 script table (the
THREAD_N = 32                    # handler's r4), +8 ID, +0xC flags (0x80000000 = stop after this frame),
THREAD_SIZE = 0x48               # +0x10 the thread's own interpreter state (0x38 bytes)
STEP_HOOKS = [0x02E408B8, 0x02BAD64C, 0x03048064]   # object step entries (fighters, weapons, items?): every
                                 # unpaused frame, hitlag and KO included; stwu r1, -0x38(r1), r4 -> accessor
INTERP = 0x02BEE950              # (r3 script table, r4 accessor, r5 state, r6 exec, f1 frames, f2 target)
STATE_RESET = 0x02BEE9B8         # (r3 state): clear it, free a nested CALL state
THREAD_STOP_BIT = 0x80000000
GROW = 0x04B9A000
FRAME_HOOK = 0x02C5F430          # every object's motion step, right after its ACMD ran (not in hitlag): li r0, 1
WM_RESET = 0x02BF5864            # object set-up (every class, 0x02BF57B0): lwz r3, 0x28(r31) before WorkModule
                                 # vt +0x24 (reset): an object is set up / reused. r0 r10 ctr are free there
VAR_ENTRY = 0x04B79000           # position_vars_cave.py's var_entry (0x0F000xxx IDs): rlwinm r12, r4, 0, 22, 31
USER_BASE = 0x300                # IDs 0x0F000300+ come here (docs/acmd-extra-commands.md)
FIGHTERS = 0x1035184C            # [[FIGHTERS] + 0] = fighter table: +0 entries, +8 count
FIGHTER_ENTRY = 0x76B0           # entry: +0 object ID, +0xC accessor, byte +0x1E >= 4 = live
KINETIC_W = 0x030B29D8           # MSC module wrappers: wrapper(ctx (+4 = accessor), {words, count})
POSTURE_W = 0x030B2AB8
CONTROL_W = 0x030B2968           # ControlModule (vt +0x2F4): (0x2710 pressed / 0x2712 held, MSC button) -> r3
ATTACK_W = 0x030B50F0            # AttackModule (vt +0x334): (0x2724) clears "has hit" (+0xC8, what 0x2727 reads)
COMPARE = 0x02BEE010             # Float_Var_Compare's compare(r3 method, f1 value, f2 against) -> r3
DBG = 0x04B93900                 # debug counters (zero at load; docs/acmd-extra-commands.md "Debug counters")
INPUT_BASE = 0x0F000100          # position_vars_cave.py's input / state variables: + 0x20 * target + input
INPUT_RAW = 0x0F000260           # raw stick X: + 2 * target (+1 C-stick)
HIT_CLEAR_ALL = 0x02C0ECDC       # (AttackModule + 8): every group's hit records cleared (AttackModule vt +0x34's)
HIT_CLEAR_LIST = 0x02C10660      # (group, list, 0): that list's records of the group's current round (+0x16A) freed
KINETIC_FW = 0x030B2A10          # KineticModuleF (vt +0x11C, float result in f1): (0xB, energy) = its Y speed
OBJ_ORIG = {FRAME_HOOK: 0x38000001, WM_RESET: 0x807F0028, VAR_ENTRY: 0x548C05BE}
OBJ_ORIG.update({h: 0x9421FFC8 for h in STEP_HOOKS})

SPECIAL_HITBOX = 0x02BDBB20      # handler, size 42
EXT_SPECIAL_HITBOX = 0x02BDD46C  # handler, size 44
N_EXTRA = 6

# the extra parameters of the Extra hitbox commands: name, type (0 int, 1 float), description
EXTRA_PARAMS = [
    ('HitstunMul', 1, 'Multiplies the hitstun this hit gives the opponent (the game\'s own: knockback x 0.4). 0 = x1 (normal); a negative value adds that many frames instead (-2: 2 frames more, as Ultimate\'s set_add_reaction_frame).'),
    ('HitstopMul', 1, 'Multiplies the opponent\'s hitstop (hitlag) from this hit, on top of the Hitlag parameter. 0 or less = x1.'),
    ('HitstopFrames', 0, 'The opponent\'s hitstop in frames, replacing the computed one (HitstopMul is then ignored). 0 = computed.'),
    ('SelfHitstopMul', 1, 'Multiplies the attacker\'s own hitstop from this hit. 0 or less = x1.'),
    ('SelfHitstopFrames', 0, 'The attacker\'s own hitstop in frames, replacing the computed one. 0 = computed.'),
    ('DIMul', 1, 'Multiplies how far DI can turn this hit\'s launch angle (0.5 = half, 2 = double). 0 or less = x1; for no DI use a tiny value (0.001).'),
]
SM4SHCOMMAND_DESC = {
    'Extra_Special_Hitbox': 'Special_Hitbox with 6 more parameters at the end: hitstun multiplier, hitstop / self hitstop multiplier '
                            'and frames, DI multiplier. Damage, Angle, KBG, FKB, BKB and Size can be variables (exe_v43: '
                            'Angle=STICK_ANGLE, Damage=VAR_0, |FOLLOW, |WORLD, |NEG). New command: needs the patched cross_f.rpx '
                            '(docs/acmd-extra-commands.md).',
    'Extra_Extended_Special_Hitbox': 'Extended_Special_Hitbox (capsule: X2/Y2/Z2) with 6 more parameters at the end: hitstun multiplier, '
                                     'hitstop / self hitstop multiplier and frames, DI multiplier. Damage, Angle, KBG, FKB, BKB and '
                                     'Size can be variables (exe_v43: Angle=STICK_ANGLE, Damage=VAR_0, |FOLLOW, |WORLD, |NEG). New '
                                     'command: needs the patched cross_f.rpx (docs/acmd-extra-commands.md).',
}
SM4SHCOMMAND_DESC['Track_Target'] = (
    'Makes this object (a fighter, or a projectile in its own script) home in on the nearest other fighter for Frames frames: '
    'its direction turns toward the target by up to TurnRate degrees a frame, at Speed. Projectiles skip their owner; '
    'a reflected one goes back at its original owner instead (any distance). '
    'Read / stop it with variable 0x0F000331. New command: needs the patched cross_f.rpx (docs/acmd-extra-commands.md).')
SM4SHCOMMAND_DESC['Thread_Start'] = (
    'Thread_Start(ID, Flags){ ... }: the commands in the block run on their own, frame by frame, from the next frame on, '
    'while the script goes on past the block. The thread keeps running after the animation ends or changes and while the '
    'character is KO\'d, until the block ends, Thread_Stop(ID), or the object is set up again. FRAME inside counts from '
    'the thread\'s start. New command: needs the patched cross_f.rpx (docs/acmd-extra-commands.md).')
SM4SHCOMMAND_DESC['Thread_Stop'] = 'Stops this object\'s thread ID (-1 = all of them). New command: needs the patched cross_f.rpx.'
SM4SHCOMMAND_DESC['Input_Compare'] = (
    'Compares a fighter\'s input (a button held / pressed, a stick) with Value; True / Else after it run on the result, '
    'like Float_Var_Compare. New command: needs the patched cross_f.rpx (docs/acmd-extra-commands.md).')
SM4SHCOMMAND_DESC['Input_Get'] = (
    'Stores a fighter\'s input (1 / 0 for a button, -1 to 1 for a stick) in a float variable (e.g. VAR_0). New command: '
    'needs the patched cross_f.rpx (docs/acmd-extra-commands.md).')
SM4SHCOMMAND_DESC['Input_Set'] = (
    'Forces a fighter\'s input as if its controller did it: hold or tap a button, tilt a stick, or ignore its controller. '
    'Forced inputs last until changed and are cleared when it is KO\'d. New command: needs the patched cross_f.rpx '
    '(docs/acmd-extra-commands.md).')
SM4SHCOMMAND_DESC['Hit_Reset'] = (
    'Clears this object\'s "attack has hit" flag (variable SELF_HIT, 0x0F0000A0, reads 0 again until another hitbox '
    'connects), so a later hitbox of the move can be checked on its own. New command: needs the patched cross_f.rpx.')
SM4SHCOMMAND_DESC['Hit_Log_Clear'] = (
    'Forgets who this object\'s hitboxes of Part have hit (-1: every part), so they can hit the same fighter again, as a '
    'new attack would. Out-of-range parts do nothing (a weapon has fewer parts than a fighter: Zelda\'s Din\'s Fire and its '
    'copies 2, fighters 20). New command: needs the patched cross_f.rpx.')
HIT_LOG_CLEAR_PARAMS = [
    ('Part', 0, 'The hitboxes\' Part (their shared hit record), from 0; -1 = every part.'),
]
BASE_CRC = {'Extra_Special_Hitbox': 0x14FCC7E4, 'Extra_Extended_Special_Hitbox': 0x7075DC5A}

HANDLER = {'h_extra': 'hv_extra', 'h_extra_ext': 'hv_extra_ext'}   # cmd_handlers: the Extra hitbox commands go
                                 # through hv_extra (exe_v43: variables in their fields), which calls h_extra
COMMANDS = [                     # name, size (words, header included), handler label, base handler
    ('Extra_Special_Hitbox', 42 + N_EXTRA, 'h_extra', SPECIAL_HITBOX),
    ('Extra_Extended_Special_Hitbox', 44 + N_EXTRA, 'h_extra_ext', EXT_SPECIAL_HITBOX),
    ('Track_Target', 8, 'h_track', None),
    ('Thread_Start', 4, 'h_thread', None),
    ('Thread_Stop', 2, 'h_thread_stop', None),
    ('Input_Compare', 5, 'h_icmp', None),
    ('Input_Get', 4, 'h_iget', None),
    ('Input_Set', 4, 'h_iset', None),
    ('Hit_Reset', 1, 'h_hreset', None),
    ('Hit_Log_Clear', 2, 'h_hlclear', None),
]
THREAD_PARAMS = [
    ('Offset', 0, 'Words to the end of the block (Sm4shCommand works it out from the braces, like True).'),
    ('ID', 0, 'This thread\'s number (any). Starting it again restarts it; Thread_Stop(ID) stops it.'),
    ('Flags', 0, 'Bits: 1 = keep running during hitlag (normally the thread pauses with the object).'),
]
_TARGET = ('Whose inputs: 0 self, 1 the nearest opponent, 2 the last fighter hit, 3-10 player slots 1-8 '
           '(as the input variables, docs/position-variables.md).')
_INPUT = ('Which input: 0 attack, 1 special, 2 jump, 3 shield, 4 grab, 5 / 6 / 7 taunt up / side / down (held); '
          '8-15 the same buttons pressed this frame; 16 / 17 stick X (forward +) / Y, 18 / 19 C-stick X (forward +) / Y '
          '(-1 to 1); 20 a stick is forced; 21 inputs off; 22-31 the state quantities of the input variables '
          '(22 situation, 23 damage, ...); 32 / 33 stick / C-stick X on screen (right +).')
INPUT_CMP_PARAMS = [
    ('Target', 0, _TARGET),
    ('Input', 0, _INPUT),
    ('Method', 0, 'Comparison, as Float_Var_Compare: 0 ==, 1 !=, 2 <=, 3 >=, 4 <, 5 > (input Method Value).'),
    ('Value', 1, 'What the input is compared with (buttons: 1 = held / pressed, 0 = not).'),
]
INPUT_GET_PARAMS = [
    ('Target', 0, _TARGET),
    ('Input', 0, _INPUT),
    ('Variable', 3, 'Float variable that gets the value (this object\'s own, e.g. VAR_0 0x0F000300; any float variable).'),
]
INPUT_SET_PARAMS = [
    ('Target', 0, _TARGET),
    ('Input', 0, _INPUT),
    ('Value', 1, 'Buttons (0-15): 1 hold it until 0 is set, 2 press it for one frame, 0 stop forcing it. Sticks (16-19, '
                 '32 / 33): force the stick to this value until Input 20 is set (any value). 21: 1 ignore its own '
                 'controller, 0 back on. 22-31: as the input variables.'),
]
THREAD_STOP_PARAMS = [
    ('ID', 0, 'The thread to stop (Thread_Start\'s ID); -1 = every thread of this object.'),
]
TRACK_PARAMS = [
    ('Frames', 0, 'Frames to track for (counted while the object moves: not in hitlag). -1 = until a Track_Target with 0 frames (or the object is reset).'),
    ('Speed', 1, 'Travel speed while tracking. 0 = keep the current speed (and turn it).'),
    ('TurnRate', 1, 'Most the direction can turn per frame, in degrees. 0 (or 180+) = point straight at the target every frame.'),
    ('Range', 1, 'Only targets within this distance (X/Y). 0 = any distance.'),
    ('Mode', 0, 'Bits: 1 = horizontal only (ignore height), 2 = turn to face the target (fighters), 4 = no gravity while tracking (fighters; it comes back when tracking ends).'),
    ('TargetOwner', 0, '1 = a projectile may also target the fighter who fired it (normally skipped). Fighters: no effect.'),
    ('TargetTeammates', 0, '1 = may target teammates. Normally a fighter this object can\'t hit because of teams (its hurt team = this object\'s attack team: a teammate with team attack off) is skipped.'),
]


# --- new commands (part 2 of the cave: CODE2) -------------------------------------------------------------------
CODE2 = 0x04B98900               # free: after THREADS (0x04B98000 + 32 x 0x48 = 0x04B98900), up to GROW
POSTURE_FW = 0x030B2AF0          # PostureModuleF: 0 facing, 1-3 position x / y / z, 4-6 rotation x / y / z (degrees)
MOTION_W = 0x030B2A48            # MotionModule: 1 play (kind, frame, rate), 4 rate, 7 current kind, 0x2713 frame
MOTION_FW = 0x030B2A80           # MotionModuleF: 1 frame, 9 rate
WORK_W = 0x030B2B28              # WorkModule: (6, id) an int
LAST_ATTACKER = 0x10000065       # a fighter's int: the player slot (fighter table entry, from 0) that hit it last
ACC_VAR = 0x0F0002BC             # position_vars_cave.py: + target (0-10) = that target's module accessor's bits

# Leave_Ground_Cancel (docs/acmd-extra-commands.md, docs/native-notes.md "Leave_Ground_Cancel"). A grounded move
# goes to Fall when it leaves the ground because its own MSC loop asks for it: the per-frame MSC main reads the
# situation (global18 = StatusModule(1): base handler 0x0200D6D8 op 1, StatusModule +0x84; 2 = air) and the status
# loop does `if (global18 == 2) { func_16(0xE, 0); return; }` (Fall request: StatusModule(3, 0xE, 0), op 3 at
# 0x0200D8FC stores it at StatusModule +0x54; the change itself is 0x02E88B28, StatusModule vt +0x16C).
LGC = 0x04B93A00                 # LGC_N entries of 0x10 (zero at load, free after DBG): +0 the fighter's StatusModule
LGC_N = 16                       # (0 = free), +4 state bits (1 off, 2 in the air through it, 4 still stops at edges),
                                 # +8 its kinetic type when it went into the air, +0xC its module accessor (the
                                 # command's: StatusModule +4 is NOT the accessor, it's an embedded list whose first
                                 # word is 8, base ctor 0x0200D588; exe_v39's hooks read it there, so their pointer
                                 # check always failed and the Fall went through: fixed in exe_v41); then the
                                 # round-robin word
LGC_CODE = 0x04B93B10            # its code (after the table and its round-robin word), up to OBJS (zero at load)
LGC_SIT = 0x0200D868             # op 1 (situation read), r31 = StatusModule: lwz r10, 0(r31)
LGC_REQ = 0x0200D91C             # op 3 (status request), r31 = StatusModule, r29 = words (+4 kind): lwz r11, 0(r31)
LGC_CHG = 0x02E88B40             # status change (0x02E88B28, r30 = StatusModule, r28 new kind): stw r28, 0x4C(r30)
LGC_ORIG = {LGC_SIT: 0x815F0000, LGC_REQ: 0x817F0000, LGC_CHG: 0x939E004C}
LGC_TRAMP = {LGC_SIT: 0x037EE598, LGC_REQ: 0x037EE59C}   # the first two are out of the cave's branch range: `b`
                                 # trampolines at the end of copy_custom_cave.py's Havok-cave space (its
                                 # SPAWN_LIMIT lowered to 0x037EE598; zero in exe_v38); the cave jumps back by ctr
FIGHTER_STATUS_VT = 0x1012D42C   # fighters' StatusModule vtable (vt +0x144 = their MSC handler 0x02E882AC)
CANCEL_W = 0x030B2F58            # CancelModule (accessor +0x94, vt +0x4C): (0x2713) the cancel window is open
GROUND_W = 0x030B2C78            # GroundModule (accessor +0x2C, vt +0x4BC): (0x2710, kind) its ground correction
FALL_KIND = 0xE                  # Fall

# New_Var (docs/acmd-extra-commands.md "New_Var"; first in exe_v40): named variables beyond VAR_n, IDs
# 0x0F000380 + slot (slot < NV_N), per object like VAR_n. user_entry sends 0x380-0x3BF to ue_nv (float reads / writes);
# the WorkModule int ops (vtable entries WM_INT_OPS of every class, WM_VTABLES) go to nvi_* for these IDs, so SET_INT,
# ADD_INT, INC_INT, Int_Var_Compare and MSC's WorkModule int ops work on them too. Storage: always the float value.
NV_BASE = USER_BASE + 0x80       # 0x380: slot k is ID 0x0F000380 + k (any top nibble: 0x1F000380 is the same, as
NV_N = 64                        # the WorkModule's own code ignores it)
NV_POOL = 0x04BD0000             # OBJ_N blocks of NV_N floats, OBJ_SIZE apart like OBJS: the block of the entry at
NV_OFF = NV_POOL - OBJS          # e is e + NV_OFF (zero at load; cleared with the entry when obj_find takes it)
NV_CODE = NV_POOL + OBJ_N * OBJ_SIZE     # 0x04BD3000: nv_code
NV_LIMIT = 0x04BD4000            # the text region grown to here (file info textRegionSize 0x2BD0000 -> 0x2BD4000)
NV_DECL = 0xE8                   # entry words (free before): +0xE8 / +0xEC slots declared (New_Var has initialised
NV_INT = 0xF0                    # them; bits 0-31 / 32-63), +0xF0 / +0xF4 slots of Type int (float writes truncated)
NV_SIZE = 11                     # New_Var's words: header, Name (the ID), Type, Initial, Scope, the name (6 words)
NV_NAME_WORDS = 6                # the name's ASCII, 4 characters a word, zero-padded (24 at most): Sm4shCommand's
WM_VTABLES = [0x10003224, 0x100F93CC, 0x1012132C, 0x1013A1C0, 0x1013AFFC, 0x10153184]   # WorkModule classes
# WorkModule int ops (vt offset, name, base class copy; every class's copy is the same code, so other IDs go on in the
# base's, as position_vars_cave.py's float hooks do): get(id), set(v, id), inc(id), dec(id), add / sub / mul / div(v,
# id), cdown(id, v) (> v: -1, returns new == v)
WM_INT_OPS = [(0x84, 'get', 0x0200F7F0), (0x8C, 'set', 0x0200F810), (0xA4, 'inc', 0x0200F8F8),
              (0xAC, 'dec', 0x0200F920), (0xB4, 'add', 0x0200F948), (0xBC, 'sub', 0x0200F970),
              (0xC4, 'mul', 0x0200F998), (0xCC, 'div', 0x0200F9C0), (0xD4, 'cdown', 0x0200F9F4)]
WM_INT_ORIG = {}                 # vtable word -> the class's own function there (exe_v39)
for _vt, _fns in zip(WM_VTABLES, [
        [0x0200F7F0, 0x0200F810, 0x0200F8F8, 0x0200F920, 0x0200F948, 0x0200F970, 0x0200F998, 0x0200F9C0, 0x0200F9F4],
        [0x02BCDA68, 0x02BCDA88, 0x02BCDB70, 0x02BCDB98, 0x02BCDBC0, 0x02BCDBE8, 0x02BCDC10, 0x02BCDC38, 0x02BCDC6C],
        [0x02DA61E8, 0x02DA6208, 0x02DA62F0, 0x02DA6318, 0x02DA6340, 0x02DA6368, 0x02DA6390, 0x02DA63B8, 0x02DA63EC],
        [0x02F1DDAC, 0x02F1DDCC, 0x02F1DEB4, 0x02F1DEDC, 0x02F1DF04, 0x02F1DF2C, 0x02F1DF54, 0x02F1DF7C, 0x02F1DFB0],
        [0x02F1DDAC, 0x02F1DDCC, 0x02F1DEB4, 0x02F1DEDC, 0x02F1DF04, 0x02F1DF2C, 0x02F1DF54, 0x02F1DF7C, 0x02F1DFB0],
        [0x03060A48, 0x03060A68, 0x03060B50, 0x03060B78, 0x03060BA0, 0x03060BC8, 0x03060BF0, 0x03060C18, 0x03060C4C]]):
    for (_off, _n, _b), _f in zip(WM_INT_OPS, _fns):
        WM_INT_ORIG[_vt + _off] = _f
RELOC_DUMMY = 0x037EE73C         # a dead word for the vtable words' relocations (as position_vars_cave.py)

# Gravity_Set (docs/acmd-extra-commands.md "Gravity_Set", docs/native-notes.md "Gravity_Set"; first in exe_v42). A
# fighter's gravity is its KineticModule's energy 1 (the fighters' KineticModule, vtable 0x1012C5C0, ctor 0x02E78B58:
# energy 1 at +0x334, class ctor 0x02E814B0, vtable 0x1012C8F8 at the energy's +0x1C): +4 vertical speed, +0x24 the
# acceleration (negative: -gravity), +0x28 the max fall speed, +0x2C the brake (V acceleration) back to it, +0x30 an
# absolute limit, +0x34 a multiplier (1), +0x38 the limit mode. Its reset (vt +0x1C, 0x02E818A8: every kinetic type
# change / KineticModule(0xE, 1, ...)) sets them again from the fighter's params (type 0: -0x03000018 gravity,
# 0x03000019 max fall, 0x0300001A, 0x03000023). Its update (vt +0x14, 0x02E8159C, from the KineticModule update
# 0x02C50058 every frame it's enabled: r3 energy, r4 the module accessor) reads +0x24 / +0x28 there. The command keeps
# its values in GS (per fighter); the update's entry swaps them into the energy and its exit puts the energy's own
# back, so the energy never holds them outside its update: nothing to restore, a reset in between is the game's.
GS_UPD = 0x02E8159C              # gravity energy update entry: stwu r1, -0x48(r1) (r3 energy, r4 accessor)
GS_UPD_END = 0x02E81860          # its single exit (every path): mr r3, r29 (r28 energy, r29 accessor), then
                                 # bl 0x0275FF54; r0 r11 r12 free
GS_HIT = 0x02E76BB4              # the fighters' damage reaction decision (owner vt +0x14C, from DamageModule vt +0x94
                                 # 0x02C22EF0 after its armor check, on every hit: r4 accessor, r5 the hit, r6 armor);
                                 # returns 0 = the hit takes effect (damage status), else no reaction: mflr r0
GS_ORIG = {GS_UPD: 0x9421FFB8, GS_UPD_END: 0x7FA3EB78, GS_HIT: 0x7C0802A6}
GRAV_VT = 0x1012C8F8             # the fighters' gravity energy class (its +0x1C)
FIGHTER_KINETIC_VT = 0x1012C5C0  # the fighters' KineticModule
GS_CODE = 0x04BD3600             # code (after New_Var's, in the grown text region), up to GS
GS = 0x04BD3E00                  # GS_N entries of 0x20 (zero at load), up to NV_LIMIT: +0 the accessor (0 = free),
GS_N = 16                        # +4 its StatusModule (the status change hook's key), +8 Accel, +0xC MaxFall (floats,
                                 # < 0 = the fighter's own), +0x10 Mode
GS_VARS = (0x337, 0x338)         # user_entry IDs 0x0F000337 GRAVITY / 0x0F000338 MAX_FALL (read only)
FAST_FALL_FLAG = 0x21000001      # the fighter's fast-fall flag (MSC WorkModule(0x2711, flag): off)

# Hitbox variables (docs/acmd-extra-commands.md "Variables in Extra hitboxes"; first in exe_v43). The Extra hitbox
# commands' Damage, Angle, KBG, FKB, BKB and Size (parameters 3-8, both commands) take a variable: a word in
# 0x01000000-0x1FFFFFFF (no hitbox has such a number: as an int it's 16 million or more, as a float 2.4e-38 to 1e-19)
# is the variable ID, bits 20-23 (0x00F00000, never part of a variable ID the game or the mod uses) its flags:
#   0x00100000 FOLLOW (re-read every frame while the hitbox is out), 0x00200000 WORLD (Angle: the value is a screen
#   angle, 0 = right: mirrored to 180 - a when the object faces left), 0x00400000 NEG (minus the value).
# The ID without the flags is read from the object's WorkModule (int IDs 0x1xxxxxxx as an int, the rest as a float)
# when the command runs, converted (Angle: rounded, 361-368 kept, else wrapped into 0-359; KBG / FKB / BKB rounded,
# >= 0; Damage / Size >= 0) and written into the command's own parameter word for the original handler (h_extra:
# the game's hitbox handler then builds the hitbox from it through AttackModule as from a number), then the word is
# put back. The command's handler table entry points at hv_extra / hv_extra_ext, which wrap h_extra / h_extra_ext
# unchanged (a command without variables: the same call, nothing else).
# FOLLOW: an entry of HV_TAB (16 x 0x48) keyed by the hitbox's slot: +0 accessor (0 = free), +4 AttackModule, +8 the
# slot, +0xC the slot's tag (TAG | the extras entry: a later hitbox in the slot changes it), +0x10 the fields that
# follow (bits 0-5), +0x14 + 4k field k's word, +0x2C + 4k its coefficient (Damage / Size: slot value / the value
# written, ints: slot value - the value written: whatever the game's own path did to them, as Strike's x1.15), +0x44
# the ID. Every frame the object moves (FRAME_HOOK, before acmd's hk_frame) the fields are read again: Damage / Size
# through AttackModule's own calls that Change_Hitbox_Damage / Change_Hitbox_Size make (AM_SET_DAMAGE / AM_SET_SIZE),
# Angle / KBG / FKB / BKB into the slot's +0x20 / 24 / 28 / 2C, with the extras entry's check words.
HV_CODE = 0x04B97200             # free (after ACC_CACHE, up to THREADS: zero in exe_v42)
HV_TAB = 0x04B97B00              # HV_N entries of HV_ENTRY (zero at load)
HV_N = 16
HV_ENTRY = 0x48
HV_LIMIT = THREADS
HV_FIELD0 = 3                    # parameter index of Damage (Angle, KBG, FKB, BKB, Size after it)
HV_FIELDS = ('Damage', 'Angle', 'KBG', 'FKB', 'BKB', 'Size')
HV_FLAGS = {'FOLLOW': 0x00100000, 'WORLD': 0x00200000, 'NEG': 0x00400000}
HV_FLAG_MASK = 0x00F00000
HV_VAR_LO, HV_VAR_HI = 0x01000000, 0x20000000
HV_VARS = 0x3C0                  # user_entry IDs 0x0F0003C0-0x0F0003C8 (read only), from gs_var's gv_zero:
HV_VAR_NAMES = ['STICK_ANGLE', 'STICK_ANGLE_RAW', 'STICK_LEN', 'CSTICK_ANGLE', 'CSTICK_ANGLE_RAW', 'CSTICK_LEN',
                'ROT_X', 'ROT_Y', 'ROT_Z']
AM_SET_DAMAGE = 0xB4             # AttackModuleImpl vt +0xB4 (0x02C090D0: id, f1 damage, r5 0): slot +0x18 (what the
                                 # Change_Hitbox_Damage handler 0x02BDAEE0 calls)
AM_SET_SIZE = 0xCC               # vt +0xCC (0x02C09128: id, f1 size): slot +0x1C (the Change_Hitbox_Size handler
                                 # 0x02BDAF64's call; the collision reads the slot's size every frame)
HV_PARAM_DESC = [' ' + d + ' Or a variable (exe_v43): its value when the command runs; |FOLLOW: every frame; |NEG: minus '
                 'it (Extra hitboxes help: "Variables in ...").' for d in (
                     'Damage=VAR_0, Damage=charge (a New_Var): below 0 is 0.',
                     'Angle=STICK_ANGLE (the stick, along the facing), Angle=VAR_1: rounded, wrapped into 0-359 (361-368 '
                     'kept); |WORLD: a screen angle (0 right), mirrored when facing left.',
                     'KBG=VAR_0: rounded, below 0 is 0.', 'FKB=VAR_0: rounded, below 0 is 0.',
                     'BKB=VAR_0: rounded, below 0 is 0.', 'Size=VAR_0: below 0 is 0.')]
HV_SPECIAL = (361, 368)          # angles kept as they are (361 Sakurai, 362-368 the game's other special angles)

_T = ('Whose: 0 this object (fighter or article), 1 the nearest opponent, 2 the last fighter this one hit, 3-10 '
      'player slots 1-8, 11 the last fighter that hit this one. 1, 2 and 11 are found from a fighter\'s own script.')
_V = 'Float variable that gets the value (e.g. VAR_0 0x0F000300; any float variable).'
# name, handler label, params (name, type 0 int / 1 float / 3 variable, description), description
NEW_CMDS = [
    ('Hit_Check', 'h_hcheck', [
        ('Target', 0, _T),
        ('When', 0, '0: since the move started (or the last Hit_Reset), 1: this frame only.'),
        ('Kinds', 0, 'What it connected with (bits, add them): 2 a hurtbox (a fighter / object was hit), 4 a shield, '
                     '6 either; 1 another attack (clank), 8 a reflector, 16 an absorber, 32 a search box, 64 other '
                     '(1, 8-64 as Ultimate\'s collision kinds: unconfirmed). 0 = anything (0x7F, MSC\'s default).')],
     'Checks whether this object\'s (or another\'s) attack connected, and with what (a hurtbox, a shield, ...); True / '
     'Else after it run on the result. MSC\'s AttackModule(0x2727 / 0x2726, kinds).'),
    ('Hit_Get', 'h_hget', [
        ('Target', 0, _T),
        ('When', 0, '0: since the move started (or the last Hit_Reset), 1: this frame only.'),
        ('Variable', 3, _V + ' Gets the kinds connected with, as bits: 2 hurtbox, 4 shield, 1 clank, ... (0 = none).')],
     'Stores what this object\'s (or another\'s) attack connected with (bits: 2 hurtbox, 4 shield, ...) in a variable.'),
    ('Rotation_Get', 'h_rget', [
        ('Target', 0, _T),
        ('Axis', 0, '0 X, 1 Y, 2 Z: the model\'s rotation in degrees (PostureModuleF(4 / 5 / 6)).'),
        ('Variable', 3, _V)],
     'Stores a fighter\'s or article\'s rotation about one axis (degrees) in a variable.'),
    ('Rotation_Set', 'h_rset', [
        ('Target', 0, _T),
        ('X', 1, 'Rotation about X, degrees (relative to its facing: + tilts it forward).'),
        ('Y', 1, 'Rotation about Y, degrees.'),
        ('Z', 1, 'Rotation about Z, degrees.')],
     'Sets a fighter\'s or article\'s rotation (degrees, as MSC PostureModule(4, x, y, z)). A fighter\'s status may set '
     'its own every frame; an article keeps it.'),
    ('Position_Get', 'h_pget', [
        ('Target', 0, _T),
        ('Axis', 0, '0 X, 1 Y, 2 Z (world position), 3 facing (1 right, -1 left).'),
        ('Variable', 3, _V)],
     'Stores a fighter\'s or article\'s world position (one axis) or facing in a variable.'),
    ('Position_Set', 'h_pset', [
        ('Target', 0, _T),
        ('X', 1, 'X (Mode 1: forward along its facing).'),
        ('Y', 1, 'Y.'),
        ('Z', 1, 'Z.'),
        ('Mode', 0, '0: put it at (X, Y, Z) (world); 1: move it by (X forward, Y, Z) from where it is.')],
     'Moves a fighter or article (MSC PostureModule(3, x, y, z)). A grounded fighter moved up may snap back or fall.'),
    ('Motion_Get', 'h_mget', [
        ('Target', 0, _T),
        ('What', 0, '0 the motion (animation) kind playing, 1 its frame, 2 its rate (speed).'),
        ('Variable', 3, _V)],
     'Stores which animation a fighter (or article) plays, its frame or its rate in a variable.'),
    ('Motion_Set', 'h_mset', [
        ('Target', 0, _T),
        ('Motion', 0, 'The motion (animation) kind to play (motion numbers are per fighter). -1: keep the current one '
                      'and only set its frame / rate.'),
        ('Frame', 1, 'The frame to start at (Motion -1: jump to it; a negative Frame leaves the frame as it is).'),
        ('Rate', 1, 'Playback rate (1 = normal). 0 or less: 1 for a new motion; Motion -1: the rate is left as it is.')],
     'Plays an animation on a fighter (or article) from a frame at a rate, or changes the current one\'s frame / rate '
     '(MSC MotionModule(1 / 0x2713 / 4)). The status keeps running: it may change the motion again.'),
    ('Last_Hit_Get', 'h_lastget', [
        ('Which', 0, '0: the last fighter this one hit (its current attack\'s newest hit; once the attack is over, a '
                     'fighter whose last attacker is this one); 1: the last fighter that hit this one (the game\'s own '
                     'record, its projectiles included).'),
        ('Variable', 3, _V + ' Gets its player slot, 1-8; 0 = none.')],
     'Stores the player slot (1-8) of the last fighter this one hit, or of the last fighter that hit it. The same '
     'fighters are Target 2 / 11 of the other commands.'),
    ('Target_Slot_Get', 'h_tslot', [
        ('Target', 0, _T),
        ('Variable', 3, _V + ' Gets the player slot, 1-8; 0 = none / not a fighter.')],
     'Stores which player slot (1-8) a target is: the nearest opponent, the last fighter hit, the last attacker, ...'),
    ('Status_Get', 'h_stget', [('Target', 0, _T), ('Variable', 3, _V)],
     'Stores a fighter\'s status (action) kind in a variable.'),
    ('Status_Set', 'h_stset', [('Target', 0, _T),
                               ('Status', 0, 'The status kind (reference/msc-note-sheet/Actions_Fighters.csv: 0x59 shield '
                                             'break, 0x5D dizzy, ...). It takes effect on its next frame.')],
     'Changes a fighter\'s status (StatusModule(3, status, 0)).'),
    ('Hitstun_Get', 'h_hsget', [('Target', 0, _T),
                                ('What', 0, '0 hitstun frames left, 1 the hitstun of the last hit it took.'),
                                ('Variable', 3, _V)],
     'Stores a fighter\'s hitstun frames left, or the last hit\'s hitstun, in a variable.'),
    ('Hitstun_Set', 'h_hsset', [('Target', 0, _T), ('Frames', 0, 'Hitstun frames left (only matters in a hit status).')],
     'Sets a fighter\'s hitstun frames left.'),
    ('Hitstop_Set', 'h_hpset', [('Target', 0, _T), ('Frames', 0, 'Frames of hitstop (hitlag).'),
                                ('Shake', 0, '1: it shakes as from a hit, 0: no shake.')],
     'Puts a fighter in hitstop (hitlag) for some frames.'),
    ('Damage_Get', 'h_dget', [('Target', 0, _T), ('Variable', 3, _V)], 'Stores a fighter\'s damage % in a variable.'),
    ('Damage_Set', 'h_dset', [('Target', 0, _T), ('Percent', 1, 'Damage %.')],
     'Sets a fighter\'s damage % (the counter follows).'),
    ('Body_State_Set', 'h_bset', [('Target', 0, _T),
                                  ('State', 0, '0 intangible (HitModule(2, frames)), 1 invincible (HitModule(1, frames)).'),
                                  ('Frames', 0, 'For how many frames.')],
     'Makes a fighter intangible or invincible for some frames.'),
    ('Armor_Set', 'h_aset', [('Target', 0, _T),
                             ('Type', 0, '0 none, 1 super armor, 2 knockback-based, 3 damage-based.'),
                             ('Threshold', 1, 'The knockback (2) or damage (3) it withstands.')],
     'Gives a fighter armor (DamageModule(0xB, type, threshold)).'),
    ('Item_State_Set', 'h_iset2', [('Target', 0, _T),
                                   ('Code', 0, '1 metal on, 2 metal off, 3 giant, 4 small, 5 Super Star, 6 flower, 7 the '
                                               'Timer\'s slow on everyone else, 8 camera close-up, 9 camera back to '
                                               'normal (docs/position-variables.md "Item states").')],
     'Puts one of the items\' states on a fighter (the item\'s own function and durations).'),
    ('Stage_Collision_Set', 'h_gset', [('Target', 0, _T),
                                       ('Mode', 0, '0 none (passes through the stage), 5 air, 1 / 2 ground (can / '
                                                   'can\'t slide off edges). Its status sets its own again when it '
                                                   'changes: set it every frame for as long as it should hold.')],
     'Sets how a fighter collides with the stage (GroundModule(0x2710, mode)).'),
    ('Joint_Position_Get', 'h_jget', [('Target', 0, _T),
                                      ('Joint', 0, 'A model.jtb table 0 joint ID (as ACMD\'s bones).'),
                                      ('VariableX', 3, 'Gets the joint\'s world X.'), ('VariableY', 3, 'World Y.'),
                                      ('VariableZ', 3, 'World Z.')],
     'Stores a joint\'s world position (its unanimated place on the target, ModelModuleF) in three variables.'),
    ('Animation_Rate_Set', 'h_arset', [('Rate', 1, 'Multiplier on every animation and the ACMD timed to it (1 = '
                                                   'normal) until set back to 1.')],
     'Speeds up / slows down everything this fighter does (MotionModule +0xF4, the Mii rate).'),
    ('Leave_Ground_Cancel', 'h_lgc', [('Enabled', 0, '1 on (normal: the move ends in Fall when it leaves the ground); '
                                                    '0 off: the move goes on in the air, and a move that stops at '
                                                    'edges (every dash attack) can slide off them; 2 off, but the '
                                                    'move still stops at edges (it leaves the ground only by moving '
                                                    'up).')],
     'Whether this grounded move is cut into Fall when the fighter leaves the ground (walks / slides off an edge, or '
     'moves up). Off: the move (animation, hitboxes, scripts) goes on in the air with air physics (gravity, air '
     'drift) until its interrupt frame or its end, then Fall; landing during it, it goes on grounded. Back on by '
     'itself at the next status (move). Fighters only.'),
    ('New_Var', 'h_newvar', [
        ('Name', 3, 'The new variable: its name (letters, digits, _; up to 24 characters). Sm4shCommand gives it a '
                    'free slot (ID 0x0F000380 + slot) and stores the name in the command.'),
        ('Type', 0, 'float (0, the default) or int (1): an int variable keeps whole numbers (a float written to it is '
                    'cut to one: 2.7 -> 2).'),
        ('Initial', 1, 'Its starting value (0 by default).'),
        ('Scope', 0, 'object (0, the default): set to Initial the first time New_Var runs for this object, then it '
                     'keeps its value (as VAR_n) until the object is set up again (a fighter\'s KO, a projectile\'s '
                     'next shot). move (1): set to Initial every time this New_Var runs (at the top of a move\'s '
                     'script: fresh for every use of the move).')]
     + [('Text%d' % (i + 1), 0, 'The name\'s characters %d-%d (ASCII; Sm4shCommand fills these from Name and doesn\'t '
                                'show them).' % (4 * i + 1, 4 * i + 4)) for i in range(NV_NAME_WORDS)],
     'Declares a named variable (Type int or float, a starting value) that every variable parameter takes by name: '
     'SET_FLOAT / SET_INT / ADD_INT / INC_INT, Float_Var_Compare / Int_Var_Compare, Hit_Get(Variable=...), ... 64 '
     'slots per object (fighter or article), beyond VAR_0-VAR_31.'),
    ('Gravity_Set', 'h_gs', [
        ('Accel', 1, 'Gravity: how much the vertical speed drops each frame (the fighter_param "Gravity", e.g. Diddy '
                     'Kong 0.105). 0: no gravity (the vertical speed stays as it is). Below 0 (-1): the fighter\'s own. '
                     'Mode 1: a multiplier of its own (0.5 = half).'),
        ('MaxFall', 1, 'Max fall speed (the fighter_param "Maximum Fall Speed", Diddy 1.75). Falling faster, the '
                       'fighter slows to it gradually as after a fast fall (Mode 2: at once). Below 0 (-1): the '
                       'fighter\'s own. Mode 1: a multiplier of its own.'),
        ('Mode', 0, 'Bits, add them: 1 Accel and MaxFall are multipliers of the fighter\'s own; 2 a fall faster than '
                    'MaxFall is cut to it at once; 4 no fast fall while it holds. 0: plain values. Accel and MaxFall '
                    'both below 0 with Mode 0 (or 1): turns Gravity_Set off.')],
     'Sets this fighter\'s gravity and max fall speed for the rest of the move (aerials, specials, a grounded move '
     'that went on in the air with Leave_Ground_Cancel, ...). Back to the fighter\'s own by itself at the next status '
     '(move), when a hit takes effect, on a ledge grab and on a KO. Fighters only.'),
]
SM4SHCOMMAND_DESC.update({n: d + ' New command: needs the patched cross_f.rpx (docs/acmd-extra-commands.md).'
                          for n, _l, _p, d in NEW_CMDS})
COMMANDS += [(n, 1 + len(p), l, None) for n, l, p, _d in NEW_CMDS]
NEW_PARAMS = {n: p for n, _l, p, _d in NEW_CMDS}
# variable-backed commands: (base, stride per target, quantity) of position_vars_cave.py's IDs
VB = {'status': (0xA0, 8, 2), 'hitstun': (0x40, 8, 0), 'dealt': (0x40, 8, 1), 'stop_shake': (0x40, 8, 3),
      'stop': (0x40, 8, 4), 'damage': (0x100, 0x20, 0x17), 'intan': (0x100, 0x20, 0x1B), 'invin': (0x100, 0x20, 0x1C),
      'armor': (0x100, 0x20, 0x1D), 'armor_t': (0x100, 0x20, 0x1E), 'item': (0x276, 1, 0), 'ground': (0xA0, 8, 6),
      'joint': (0x290, 4, 0)}


def newcmd_code(b):
    """the new commands' handlers and their helpers, in their own Asm (b, at CODE2)"""
    pro = lambda lab, n, skip=True: """
%(lab)s:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r26, 0x28(r1)
        mr r31, r5                      # script state
        mr r30, r7                      # parameters
        mr r29, r3                      # this object's accessor
        li r28, %(bytes)d""" % dict(lab=lab, bytes=4 * n) + (("""
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq nc_out""") if skip else "") + chk_t('r29', 'r0', 'nc_out')     # noqa: E731
    size = {n: 1 + len(p) for n, _l, p, _d in NEW_CMDS}
    S = lambda name: size[name]          # noqa: E731

    def vid(key, treg='r4'):
        """r4 = position_vars ID of key for target in treg (0 -> nc_out on a bad target)"""
        base, stride, q = VB[key]
        return """
        mr r3, r29
        mr r4, %(t)s
        bl nc_tid
        cmpwi r3, 0
        blt nc_out
        mulli r4, r3, %(stride)d
        addis r4, r4, 0x0F00
        addi r4, r4, %(bq)d""" % dict(t=treg, stride=stride, bq=base + q)

    def msc_args(*words):
        """nc_args = words: ints, ('p', k) parameter k, ('r', reg)"""
        out = ["        lis r12, nc_args@ha", "        addi r12, r12, nc_args@l"]
        for i, w in enumerate(words):
            if isinstance(w, tuple) and w[0] == 'p':
                out.append("        lwz r0, %d(r30)" % (4 * w[1]))
            elif isinstance(w, tuple) and w[0] == 'r':
                out.append("        mr r0, %s" % w[1])
            else:
                out += ["        lis r0, 0x%X" % ((w >> 16) & 0xFFFF), "        ori r0, r0, 0x%X" % (w & 0xFFFF)]
            out.append("        stw r0, %d(r12)" % (4 * i))
        return "\n" + "\n".join(out)

    def call(wrapper, n, acc='r27'):
        return """
        mr r3, %s
        lis r4, 0x%X
        ori r4, r4, 0x%X
        li r5, %d
        bl nc_msc""" % (acc, wrapper >> 16, wrapper & 0xFFFF, n)

    tgt = """
        mr r3, r29
        lwz r4, 0(r30)
        bl nc_target
        mr. r27, r3
        beq nc_out"""
    store = lambda k: """
        mr r3, r29
        lwz r4, %d(r30)
        bl nc_set""" % (4 * k)       # noqa: E731
    fbits = """
        stw r3, 0x8(r1)
        lfs f1, 0x8(r1)"""
    seti = lambda key, k, treg='r26': ("""
        lwz r26, 0(r30)""" if treg == 'r26' else "") + vid(key, treg) + """
        mr r26, r4
        lwz r3, %d(r30)
        bl i2f
        mr r3, r29
        mr r4, r26
        bl nc_set""" % (4 * k)        # noqa: E731
    b.asm("""
# --- shared epilogue: step over the command (r28 bytes) when running; the handlers' frame (0x40, r26-r31)
nc_out:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne nc_ret
        lwz r11, 4(r31)
        add r11, r11, r28
        stw r11, 4(r31)
        li r3, 2
nc_ret:
        lmw r26, 0x28(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

# --- nc_msc(r3 accessor, r4 MSC module wrapper, r5 word count; words in nc_args) -> r3 (float bits for F) ----
nc_msc:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        mtctr r4
        li r0, 0
        stw r0, 0x10(r1)                # fake MSC context: +4 = the module accessor
        stw r3, 0x14(r1)
        lis r12, nc_args@ha
        addi r12, r12, nc_args@l
        stw r12, 0x18(r1)
        stw r5, 0x1C(r1)
        addi r3, r1, 0x10
        addi r4, r1, 0x18
        bctrl
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- nc_tid(r3 accessor, r4 target) -> r3 target 0-10 of position_vars' IDs (11, the last attacker: its slot's
#     3 + slot), or -1 -------------------------------------------------------------------------------------------
nc_tid:
        cmplwi r4, 10
        bgt nt_last
        mr r3, r4
        blr
nt_last:
        cmpwi r4, 11
        bne nt_bad
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)""" + msc_args(6, LAST_ATTACKER) + """
        lis r4, 0x%(wh)X
        ori r4, r4, 0x%(wl)X
        li r5, 2
        bl nc_msc
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        cmplwi r3, 7
        bgt nt_bad
        addi r3, r3, 3
        blr
nt_bad:
        li r3, -1
        blr

# --- nc_target(r3 accessor, r4 target) -> r3 that target's module accessor, or 0 ------------------------------
nc_target:
        cmpwi r4, 0
        bne ntg_go
        blr
ntg_go:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        mr r31, r3
        bl nc_tid
        cmpwi r3, 0
        blt ntg_none
        beq ntg_self
        lis r4, 0x%(acch)X
        ori r4, r4, 0x%(accl)X
        add r4, r4, r3
        lwz r3, 0x28(r31)               # this object's WorkModule: position_vars_cave.py's ACC""" % dict(
        wh=WORK_W >> 16, wl=WORK_W & 0xFFFF, acch=ACC_VAR >> 16, accl=ACC_VAR & 0xFFFF) + chk_t('r3', 'r0', 'ntg_none') + \
        vcall(0x44) + """
        stfs f1, 0x8(r1)
        lwz r3, 0x8(r1)""" + chk_t('r3', 'r0', 'ntg_none') + """
        b ntg_out
ntg_self:
        mr r3, r31
        b ntg_out
ntg_none:
        li r3, 0
ntg_out:
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# --- nc_get(r3 accessor, r4 ID) -> f1 / nc_set(r3 accessor, r4 ID, f1): its WorkModule's float -------------------
nc_get:
        lwz r3, 0x28(r3)""" + chk_t('r3', 'r0', 'ng_zero') + """
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctr
ng_zero:
        lis r12, zero@ha
        lfs f1, zero@l(r12)
        blr
nc_set:
        lwz r3, 0x28(r3)""" + chk_t('r3', 'r0', 'ns_out') + """
        lwz r12, 0(r3)
        lwz r12, 0x4C(r12)
        mtctr r12
        bctr
ns_out:
        blr

# --- nc_slot(r3 accessor) -> r3 its player slot 1-8 (fighter table entry + 1), 0 = none ---------------------------
nc_slot:
        mr r11, r3
        lis r12, 0x%(fh)X
        lwz r12, %(fl)d(r12)""" % dict(fh=ha(FIGHTERS), fl=lo(FIGHTERS)) + chk_t('r12', 'r0', 'nsl_none') + """
        lwz r12, 0(r12)""" + chk_t('r12', 'r0', 'nsl_none') + """
        lwz r10, 8(r12)                 # count
        lwz r12, 0(r12)                 # entries""" + chk_t('r12', 'r0', 'nsl_none') + """
        li r3, 0
nsl_loop:
        cmplw r3, r10
        bge nsl_none
        cmplwi r3, 8
        bge nsl_none
        lbz r0, 0x1E(r12)               # live
        cmplwi r0, 4
        blt nsl_next
        lwz r0, 0xC(r12)
        cmplw r0, r11
        bne nsl_next
        addi r3, r3, 1
        blr
nsl_next:
        addi r3, r3, 1
        addi r12, r12, %(fe)d
        b nsl_loop
nsl_none:
        li r3, 0
        blr
""" % dict(fe=FIGHTER_ENTRY))

    # ---- hits
    hit_mask = tgt + """
        lwz r3, 0x50(r27)               # AttackModule""" + chk_t('r3', 'r0', 'nc_out') + """
        lwz r12, 0(r3)
        lwz r0, 4(r30)                  # When: 0 since the move started (0x2727's vt +0x2C4), 1 this frame (0x2726's +0x2BC)
        li r11, 0x2C4
        cmpwi r0, 0
        beq hm_vt_%(n)s
        li r11, 0x2BC
hm_vt_%(n)s:
        lwzx r12, r12, r11
        mtctr r12
        bctrl                           # -> r3 the kinds connected with (bits)"""
    b.asm("""
h_hcheck:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r26, 0x28(r1)
        mr r31, r5
        mr r30, r7
        mr r29, r3
        li r28, %d
        li r26, 0
        stw r26, 0xC(r31)               # no target / no attack module: False""" % (4 * S('Hit_Check')) +
          chk_t('r29', 'r0', 'nc_out') + hit_mask % dict(n='c') + """
        lwz r0, 8(r30)
        cmpwi r0, 0
        bne hc_and
        li r0, 0x7F
hc_and:
        and. r0, r3, r0
        beq hc_set
        li r26, 1
hc_set:
        stw r26, 0xC(r31)               # the compare result True / Else read
        b nc_out
""")
    b.asm(pro('h_hget', S('Hit_Get')) + hit_mask % dict(n='g') + """
        bl i2f""" + store(2) + """
        b nc_out
""")
    # ---- posture
    b.asm(pro('h_rget', S('Rotation_Get')) + tgt + """
        lwz r26, 4(r30)
        cmplwi r26, 2
        bgt nc_out
        addi r26, r26, 4""" + msc_args(('r', 'r26')) + call(POSTURE_FW, 1) + fbits + store(2) + """
        b nc_out
""")
    b.asm(pro('h_rset', S('Rotation_Set')) + tgt + msc_args(4, ('p', 1), ('p', 2), ('p', 3)) + call(POSTURE_W, 4) + """
        b nc_out
""")
    b.asm(pro('h_pget', S('Position_Get')) + tgt + """
        lwz r26, 4(r30)
        cmplwi r26, 3
        bgt nc_out
        addi r26, r26, 1
        cmpwi r26, 4
        bne pg_go
        li r26, 0                       # 3: facing""" + """
pg_go:""" + msc_args(('r', 'r26')) + call(POSTURE_FW, 1) + fbits + store(2) + """
        b nc_out
""")
    b.asm(pro('h_pset', S('Position_Set')) + tgt + """
        lwz r0, 16(r30)
        cmpwi r0, 1
        beq ps_rel
        lwz r0, 4(r30)
        stw r0, 0x10(r1)
        lwz r0, 8(r30)
        stw r0, 0x14(r1)
        lwz r0, 12(r30)
        stw r0, 0x18(r1)
        b ps_go
ps_rel:""" + msc_args(0) + call(POSTURE_FW, 1) + """
        stw r3, 0x1C(r1)                # facing""" + msc_args(1) + call(POSTURE_FW, 1) + fbits + """
        lfs f2, 0x1C(r1)
        lfs f3, 4(r30)
        fmadds f1, f2, f3, f1           # x + X x facing
        stfs f1, 0x10(r1)""" + msc_args(2) + call(POSTURE_FW, 1) + fbits + """
        lfs f2, 8(r30)
        fadds f1, f1, f2
        stfs f1, 0x14(r1)""" + msc_args(3) + call(POSTURE_FW, 1) + fbits + """
        lfs f2, 12(r30)
        fadds f1, f1, f2
        stfs f1, 0x18(r1)
ps_go:
        lwz r6, 0x10(r1)
        lwz r7, 0x14(r1)
        lwz r8, 0x18(r1)""" + msc_args(3, ('r', 'r6'), ('r', 'r7'), ('r', 'r8')) + call(POSTURE_W, 4) + """
        b nc_out
""")
    # ---- motion
    b.asm(pro('h_mget', S('Motion_Get')) + tgt + """
        lwz r26, 4(r30)
        cmpwi r26, 0
        bne mg_f""" + msc_args(7) + call(MOTION_W, 1) + """
        bl i2f
        b mg_st
mg_f:
        cmplwi r26, 2
        bgt nc_out
        li r0, 1
        cmpwi r26, 1
        beq mg_ff
        li r0, 9
mg_ff:
        mr r26, r0""" + msc_args(('r', 'r26')) + call(MOTION_FW, 1) + fbits + """
mg_st:""" + store(2) + """
        b nc_out
""")
    b.asm(pro('h_mset', S('Motion_Set')) + tgt + """
        lis r12, zero@ha
        lfs f0, zero@l(r12)
        lwz r0, 4(r30)
        cmpwi r0, 0
        blt ms_keep
        lfs f1, 8(r30)                  # frame (< 0: 0)
        stfs f1, 0x10(r1)
        fcmpu cr0, f1, f0
        bge ms_fr
        stfs f0, 0x10(r1)
ms_fr:
        lfs f1, 12(r30)                 # rate (<= 0: 1)
        stfs f1, 0x14(r1)
        fcmpu cr0, f1, f0
        bgt ms_rt
        lis r12, one@ha
        lfs f1, one@l(r12)
        stfs f1, 0x14(r1)
ms_rt:
        lwz r6, 0x10(r1)
        lwz r7, 0x14(r1)""" + msc_args(1, ('p', 1), ('r', 'r6'), ('r', 'r7')) + call(MOTION_W, 4) + """
        b nc_out
ms_keep:
        lfs f1, 8(r30)
        fcmpu cr0, f1, f0
        blt ms_k_rate""" + msc_args(0x2713, ('p', 2)) + call(MOTION_W, 2) + """
ms_k_rate:
        lis r12, zero@ha
        lfs f0, zero@l(r12)
        lfs f1, 12(r30)
        fcmpu cr0, f1, f0
        ble nc_out""" + msc_args(4, ('p', 3)) + call(MOTION_W, 2) + """
        b nc_out
""")
    # ---- who
    b.asm(pro('h_lastget', S('Last_Hit_Get')) + """
        li r4, 2
        lwz r0, 0(r30)
        cmpwi r0, 0
        beq lg_go
        li r4, 11
lg_go:
        mr r3, r29
        bl nc_target
        cmpwi r3, 0
        beq lg_zero
        bl nc_slot
        b lg_st
lg_zero:
        li r3, 0
lg_st:
        bl i2f""" + store(1) + """
        b nc_out
""")
    b.asm(pro('h_tslot', S('Target_Slot_Get')) + """
        mr r3, r29
        lwz r4, 0(r30)
        bl nc_target
        cmpwi r3, 0
        beq ts2_zero
        bl nc_slot
        b ts2_st
ts2_zero:
        li r3, 0
ts2_st:
        bl i2f""" + store(1) + """
        b nc_out
""")
    # ---- variable-backed
    getv = lambda key, k: """
        lwz r26, 0(r30)""" + vid(key, 'r26') + """
        mr r3, r29
        bl nc_get""" + store(k)      # noqa: E731
    b.asm(pro('h_stget', S('Status_Get')) + getv('status', 1) + "\n        b nc_out\n")
    b.asm(pro('h_stset', S('Status_Set')) + seti('status', 1) + "\n        b nc_out\n")
    b.asm(pro('h_hsget', S('Hitstun_Get')) + """
        lwz r0, 4(r30)
        cmpwi r0, 0
        bne hsg_dealt""" + getv('hitstun', 2) + """
        b nc_out
hsg_dealt:""" + getv('dealt', 2) + "\n        b nc_out\n")
    b.asm(pro('h_hsset', S('Hitstun_Set')) + seti('hitstun', 1) + "\n        b nc_out\n")
    b.asm(pro('h_hpset', S('Hitstop_Set')) + """
        lwz r0, 8(r30)
        cmpwi r0, 0
        beq hp_noshake""" + seti('stop_shake', 1) + """
        b nc_out
hp_noshake:""" + seti('stop', 1) + "\n        b nc_out\n")
    b.asm(pro('h_dget', S('Damage_Get')) + getv('damage', 1) + "\n        b nc_out\n")
    b.asm(pro('h_dset', S('Damage_Set')) + """
        lwz r26, 0(r30)""" + vid('damage', 'r26') + """
        lfs f1, 4(r30)
        mr r3, r29
        bl nc_set
        b nc_out
""")
    b.asm(pro('h_bset', S('Body_State_Set')) + """
        lwz r0, 4(r30)
        cmpwi r0, 0
        bne bs_inv""" + seti('intan', 2) + """
        b nc_out
bs_inv:
        cmpwi r0, 1
        bne nc_out""" + seti('invin', 2) + "\n        b nc_out\n")
    b.asm(pro('h_aset', S('Armor_Set')) + """
        lwz r26, 0(r30)""" + vid('armor_t', 'r26') + """
        lfs f1, 8(r30)                  # the threshold first (the type's write reads it)
        mr r3, r29
        bl nc_set""" + seti('armor', 1) + "\n        b nc_out\n")
    b.asm(pro('h_iset2', S('Item_State_Set')) + seti('item', 1) + "\n        b nc_out\n")
    b.asm(pro('h_gset', S('Stage_Collision_Set')) + seti('ground', 1) + "\n        b nc_out\n")
    b.asm(pro('h_jget', S('Joint_Position_Get')) + """
        lwz r26, 0(r30)""" + vid('joint', 'r26') + """
        mr r26, r4                      # n 0: the joint the reads use; 1-3 its world x / y / z
        lwz r3, 4(r30)
        bl i2f
        mr r3, r29
        mr r4, r26
        bl nc_set""" + ''.join("""
        mr r3, r29
        addi r4, r26, %d
        bl nc_get""" % (i + 1) + store(2 + i) for i in range(3)) + "\n        b nc_out\n")
    b.asm(pro('h_arset', S('Animation_Rate_Set')) + """
        lfs f1, 0(r30)
        mr r3, r29
        lis r4, 0x0F00
        ori r4, r4, 0x98
        bl nc_set
        b nc_out
""")
    b.asm("""
nc_args:
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
        .word 0
""")


def lgc_code(b):
    """Leave_Ground_Cancel: the command, its table and the three StatusModule hooks (in CODE2, after the new
    commands; nc_msc / nc_args / nc_out are theirs)"""
    def msc2(wrapper, w0, src):
        """nc_msc(r29, wrapper, 2) with nc_args = {w0, src} (src: a register)"""
        return """
        lis r12, nc_args@ha
        addi r12, r12, nc_args@l
        li r0, 0x%X
        stw r0, 0(r12)
        stw %s, 4(r12)
        mr r3, r29
        lis r4, 0x%X
        ori r4, r4, 0x%X
        li r5, 2
        bl nc_msc""" % (w0, src, wrapper >> 16, wrapper & 0xFFFF)

    def msc1(wrapper, w0):
        return """
        lis r12, nc_args@ha
        li r0, 0x%X
        stw r0, nc_args@l(r12)
        mr r3, r29
        lis r4, 0x%X
        ori r4, r4, 0x%X
        li r5, 1
        bl nc_msc""" % (w0, wrapper >> 16, wrapper & 0xFFFF)
    b.asm("""
# --- Leave_Ground_Cancel(Enabled): 1 on, 0 off (edges don't stop the move), 2 off (edges still stop it) ---------
h_lgc:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r26, 0x28(r1)
        mr r31, r5
        mr r29, r3
        li r28, 8
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq nc_out
        lwz r26, 0(r7)                  # Enabled""" + chk_t('r29', 'r0', 'nc_out') + """
        lwz r27, 0x20(r29)              # StatusModule""" + chk_t('r27', 'r0', 'nc_out') + """
        lwz r0, 0(r27)
        lis r12, 0x%(vth)X
        ori r12, r12, 0x%(vtl)X
        cmplw r0, r12
        bne nc_out                      # fighters only
        mr r3, r27
        xori r4, r26, 1                 # an entry is made unless Enabled is 1
        bl lgc_find
        mr. r30, r3
        beq nc_out
        lwz r0, 4(r30)
        rlwinm r0, r0, 0, 30, 30        # keep "in the air through it"
        cmpwi r26, 1
        beq lgc_lg_st
        ori r0, r0, 1
        cmpwi r26, 2
        bne lgc_lg_st
        ori r0, r0, 4
lgc_lg_st:
        stw r0, 4(r30)
        stw r29, 0xC(r30)               # the accessor, for the hooks
        andi. r12, r0, 2                # in the air: the landing sets the ground correction
        bne nc_out
        lwz r12, 0x84(r27)
        cmpwi r12, 0
        bne nc_out
        mr r4, r0
        mr r3, r27
        bl lgc_gc
        cmpwi r4, 0                     # the status's own isn't an edge-stopping one: leave it
        beq nc_out
        mr r26, r3""" % dict(vth=FIGHTER_STATUS_VT >> 16, vtl=FIGHTER_STATUS_VT & 0xFFFF) + msc2(GROUND_W, 0x2710, 'r26') + """
        b nc_out

# --- lgc_gc(r3 StatusModule, r4 state) -> r3 the ground correction the move gets: its status's own (+0x78), or 1
#     (slides off edges) for an edge-stopping one (2 / 3) while off with edges not kept; r4 = 1 if its own stops at
#     edges. Leaf: r0 r3 r4 ---------------------------------------------------------------------------------------
lgc_gc:
        andi. r0, r4, 5
        lwz r3, 0x78(r3)
        addi r4, r3, -2
        cmplwi r4, 1
        li r4, 0
        bgtlr
        li r4, 1
        cmpwi r0, 1
        bnelr
        li r3, 1
        blr

# --- lgc_find(r3 StatusModule, r4 make) -> r3 its entry or 0 (make: a free one, else the next in turn); leaf: r0 r3
#     r10 r11 r12 -----------------------------------------------------------------------------------------------
lgc_find:
        lis r12, lgc_tab@ha
        addi r12, r12, lgc_tab@l
        li r11, %(n)d
        li r10, 0
lgc_lf_loop:
        lwz r0, 0(r12)
        cmplw r0, r3
        beq lgc_lf_hit
        cmpwi r0, 0
        bne lgc_lf_next
        cmpwi r10, 0
        bne lgc_lf_next
        mr r10, r12
lgc_lf_next:
        addi r12, r12, 0x10
        addi r11, r11, -1
        cmpwi r11, 0
        bne lgc_lf_loop
        cmpwi r4, 0
        beq lgc_lf_none
        cmpwi r10, 0
        bne lgc_lf_take
        lis r11, lgc_tab@ha
        addi r11, r11, lgc_tab@l
        lwz r12, %(rr)d(r11)            # all taken: the next in turn
        addi r0, r12, 0x10
        andi. r0, r0, %(mask)d
        stw r0, %(rr)d(r11)
        add r10, r11, r12
lgc_lf_take:
        stw r3, 0(r10)
        li r0, 0
        stw r0, 4(r10)
        stw r0, 8(r10)
        mr r12, r10
lgc_lf_hit:
        mr r3, r12
        blr
lgc_lf_none:
        li r3, 0
        blr

# --- hook: the MSC situation read (StatusModule(1), every frame from the fighter's MSC main, before its status
#     loop). Off and in the air (a grounded move: its correction 1-3): air kinetics (KineticModule(0, 0)) and air
#     ground correction (GroundModule(0x2710, 5)), as the game's own air switch does (func_102 in every fighter's
#     MSC), the kinetic type kept; back on the ground through it: that kinetic type and the move's correction. ----
hk_lgc_sit:
        mr r3, r31
        bl lgc_sit
        lwz r10, 0(r31)
        lis r12, 0x%(sit_bh)X
        ori r12, r12, 0x%(sit_bl)X
        mtctr r12
        bctr
lgc_sit:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stmw r29, 0x14(r1)
        mr r31, r3
        li r4, 0
        bl lgc_find
        mr. r30, r3
        beq lgc_ls_ret
        lwz r29, 0xC(r30)               # accessor (the command's)""" % dict(n=LGC_N, rr=LGC_N * 0x10, mask=LGC_N * 0x10 - 1,
                                                          sit_bh=(LGC_SIT + 4) >> 16, sit_bl=(LGC_SIT + 4) & 0xFFFF) + chk_t('r29', 'r0', 'lgc_ls_ret') + """
        lwz r0, 4(r30)
        lwz r12, 0x84(r31)              # situation
        andi. r11, r0, 3
        cmpwi r11, 1                    # off, still on the ground
        bne lgc_ls_land
        cmpwi r12, 2
        bne lgc_ls_ret
        lwz r11, 0x78(r31)
        addi r11, r11, -1
        cmplwi r11, 2
        bgt lgc_ls_ret                      # not a grounded move
        ori r0, r0, 2
        stw r0, 4(r30)
        lwz r11, 0x34(r29)              # KineticModule: its type (+0x11C) back on landing
        lwz r11, 0x11C(r11)
        stw r11, 8(r30)
        li r4, 0
        li r5, 5
        b lgc_ls_set
lgc_ls_land:
        andi. r11, r0, 2
        beq lgc_ls_ret
        cmpwi r12, 0
        bne lgc_ls_ret
        rlwinm r0, r0, 0, 31, 29        # landed: "in the air" off
        stw r0, 4(r30)
        mr r4, r0
        mr r3, r31
        bl lgc_gc
        mr r5, r3
        lwz r4, 8(r30)
lgc_ls_set:
        stw r5, 8(r1)""" + msc2(KINETIC_W, 0, 'r4') + """
        lwz r30, 8(r1)""" + msc2(GROUND_W, 0x2710, 'r30') + """
lgc_ls_ret:
        lmw r29, 0x14(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# --- hook: a status request (StatusModule(3, kind, ...)). Fall asked for while off and in the air through it is
#     dropped (the move goes on) until the move's cancel window opens (CancelModule(0x2713)) or its motion ends
#     (MotionModule(0x2712)): then the Fall goes through, as the status's own loop asks for it. -----------------
hk_lgc_req:
        mr r3, r31
        mr r4, r29
        bl lgc_req
        cmpwi r3, 0
        bne lgc_lq_drop
        lwz r11, 0(r31)
        lis r12, 0x%(req_bh)X
        ori r12, r12, 0x%(req_bl)X
        mtctr r12
        bctr
lgc_lq_drop:
        stw r30, 0x10(r1)               # (the request's result word, as the original path)
        lis r12, 0x%(skip_h)X
        ori r12, r12, 0x%(skip_l)X
        mtctr r12
        bctr
lgc_req:
        lwz r0, 4(r4)
        cmpwi r0, %(fall)d
        bne lgc_lq_no
        lwz r0, 0x84(r3)
        cmpwi r0, 2
        bne lgc_lq_no
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stmw r29, 0x14(r1)
        mr r31, r3
        li r4, 0
        bl lgc_find
        cmpwi r3, 0
        beq lgc_lq_0
        lwz r0, 4(r3)
        andi. r0, r0, 3
        cmpwi r0, 3
        bne lgc_lq_0
        lwz r29, 0xC(r3)                # accessor (the command's)""" % dict(req_bh=(LGC_REQ + 4) >> 16, req_bl=(LGC_REQ + 4) & 0xFFFF, skip_h=0x0200D948 >> 16,
                             skip_l=0x0200D948 & 0xFFFF, fall=FALL_KIND) + chk_t(
        'r29', 'r0', 'lgc_lq_0') + msc1(MOTION_W, 0x2712) + """
        cmpwi r3, 0
        bne lgc_lq_0
        lwz r0, 0x94(r29)
        cmpwi r0, 0
        beq lgc_lq_1""" + msc1(CANCEL_W, 0x2713) + """
        cmpwi r3, 0
        bne lgc_lq_0
lgc_lq_1:
        li r3, 1
        b lgc_lq_ret
lgc_lq_0:
        li r3, 0
lgc_lq_ret:
        lmw r29, 0x14(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
lgc_lq_no:
        li r3, 0
        blr

# --- hook: every status change (0x02E88B28): the fighter's entry goes (the next move starts on) --------------
hk_lgc_chg:
        stw r28, 0x4C(r30)
        mr r3, r30
        li r4, 0
        bl lgc_find
        cmpwi r3, 0
        beq lgc_lc_back
        li r0, 0
        stw r0, 0(r3)
        stw r0, 4(r3)
lgc_lc_back:
        b gs_chg                        # Gravity_Set's entry too (exe_v42; it goes on to 0x02E88B44)
""")


def nv_code(b):
    """New_Var: the command, its slots' float path (ue_nv, from user_entry), the entry clear (nv_take, from obj_find)
    and the WorkModule int ops (nvi_*, from the vtables), in NV_CODE"""
    D = dict(base=NV_BASE, n=NV_N, offha=ha(NV_OFF), offlo=lo(NV_OFF), decl=NV_DECL, int=NV_INT, last=OBJ_SIZE - 4,
             step=4 * NV_SIZE)

    def ours(rid, other):
        """branch to other unless rid is a New_Var ID (category F, index 0x380 + k, k < 64; any top nibble); r11 r12"""
        return """
        rlwinm r12, %(r)s, 0, 4, 21
        lis r11, 0x0F00
        cmplw r12, r11
        bne %(o)s
        rlwinm r12, %(r)s, 0, 22, 31
        addi r12, r12, -%(base)d
        cmplwi r12, %(n)d
        bge %(o)s""" % dict(D, r=rid, o=other)
    b.asm("""
# --- user_entry's IDs 0x380-0x3BF (r31 WorkModule, r30 index, r29 write, 0x18(r1) value; r27 r28 free) ---------
ue_nv:
        addi r28, r30, -%(base)d
        cmplwi r28, %(n)d
        bge.far gs_var                  # 0x337-0x33F, 0x3C0-0x3FF (gs_var: GRAVITY / MAX_FALL, else 0; exe_v42)
        mr r3, r31
        mr r4, r29                      # writing creates the object's entry
        bl obj_find
        cmpwi r3, 0
        beq.far ue_zero
        slwi r12, r28, 2
        add r12, r12, r3
        addis r12, r12, %(offha)d
        addi r27, r12, %(offlo)d        # the slot (the entry's block + 4k)
        cmpwi r29, 0
        bne ue_nv_w
        lfs f1, 0(r27)
        b ue_out
ue_nv_w:
        lfs f1, 0x18(r1)
        srwi r11, r28, 5
        slwi r11, r11, 2
        add r11, r11, r3
        lwz r11, %(int)d(r11)           # int-typed?
        rlwinm r0, r28, 0, 27, 31
        srw r11, r11, r0
        andi. r11, r11, 1
        beq ue_nv_st
        bl f2i                          # a whole number (toward 0)
        bl i2f
ue_nv_st:
        stfs f1, 0(r27)
        b ue_out

# --- obj_find taking an entry (r12): clear its New_Var block too; leaf, r0 = 0 after (the replaced li r0, 0) -------
nv_take:
        addis r10, r12, %(offha)d
        addi r10, r10, %(offlo)d
        li r0, 0
        li r11, %(last)d
nv_tk_loop:
        stwx r0, r10, r11
        addi r11, r11, -4
        cmpwi r11, 0
        bge nv_tk_loop
        b of_take2

# --- New_Var(Name (the ID), Type, Initial, Scope, name x6) -------------------------------------------------------
# Type 1: int (float writes truncated; any other: float). Scope 1: set Initial every run; any other: only while the
# slot isn't declared for this object yet (the first run after the object's set-up).
h_newvar:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r27, 0x1C(r1)
        mr r31, r5                      # script state
        mr r30, r7                      # parameters
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq nv_step""" % D + chk_t('r3', 'r0', 'nv_step') + """
        lwz r29, 0x28(r3)               # WorkModule""" + chk_t('r29', 'r0', 'nv_step') + """
        lwz r28, 0(r30)""" + ours('r28', 'nv_step') + """
        mr r28, r12                     # slot
        mr r3, r29
        li r4, 1
        bl obj_find
        mr. r27, r3
        beq nv_step
        srwi r10, r28, 5
        slwi r10, r10, 2
        add r10, r10, r27               # the entry + the slot's mask word
        rlwinm r0, r28, 0, 27, 31
        li r9, 1
        slw r9, r9, r0                  # the slot's bit
        lwz r11, %(int)d(r10)
        andc r11, r11, r9
        lwz r0, 4(r30)                  # Type
        cmpwi r0, 1
        bne nv_type
        or r11, r11, r9
nv_type:
        stw r11, %(int)d(r10)
        lwz r11, %(decl)d(r10)
        lwz r0, 0xC(r30)                # Scope 1 (move): every time
        cmpwi r0, 1
        beq nv_init
        and. r0, r11, r9
        bne nv_step                     # object: declared already
nv_init:
        or r11, r11, r9
        stw r11, %(decl)d(r10)
        lfs f1, 8(r30)                  # Initial
        lwz r0, 4(r30)
        cmpwi r0, 1
        bne nv_store
        bl f2i
        bl i2f
nv_store:
        slwi r12, r28, 2
        add r12, r12, r27
        addis r12, r12, %(offha)d
        stfs f1, %(offlo)d(r12)
nv_step:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne nv_ret
        lwz r11, 4(r31)
        addi r11, r11, %(step)d
        stw r11, 4(r31)
        li r3, 2
nv_ret:
        lmw r27, 0x1C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- nvi_op(r3 WorkModule, r4 ID, r5 operand, r6 op) -> r3: a WorkModule int op on a New_Var slot, through the
#     float path (user_entry): the value read, changed and written back as a float -------------------------------
nvi_op:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r27, 0x1C(r1)
        mr r31, r3
        mr r30, r4
        mr r29, r5
        mr r28, r6
        li r27, 0                       # the result (get: the value; cdown: reached)
        mr r3, r29
        cmpwi r28, 1                    # set: no read
        beq nvi_write
        mr r3, r31
        mr r4, r30
        li r5, 0
        bl user_entry
        bl f2i
        cmpwi r28, 0                    # get
        bne nvi_1
        mr r27, r3
        b nvi_out
nvi_1:
        cmpwi r28, 2                    # inc
        bne nvi_2
        addi r3, r3, 1
        b nvi_write
nvi_2:
        cmpwi r28, 3                    # dec
        bne nvi_3
        addi r3, r3, -1
        b nvi_write
nvi_3:
        cmpwi r28, 4                    # add
        bne nvi_4
        add r3, r3, r29
        b nvi_write
nvi_4:
        cmpwi r28, 5                    # sub
        bne nvi_5
        subf r3, r29, r3
        b nvi_write
nvi_5:
        cmpwi r28, 6                    # mul
        bne nvi_6
        mullw r3, r3, r29
        b nvi_write
nvi_6:
        cmpwi r28, 7                    # div (by 0: nothing)
        bne nvi_7
        cmpwi r29, 0
        beq nvi_out
        divw r3, r3, r29
        b nvi_write
nvi_7:
        cmpw r3, r29                    # cdown: above the operand: -1, and the result is whether it got there
        ble nvi_out
        addi r3, r3, -1
        cmpw r3, r29
        bne nvi_write
        li r27, 1
nvi_write:
        bl i2f
        mr r3, r31
        mr r4, r30
        li r5, 1
        bl user_entry
nvi_out:
        mr r3, r27
        lmw r27, 0x1C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
""" % D)
    for k, (_off, name, base) in enumerate(WM_INT_OPS):
        id_in_r5 = name in ('set', 'add', 'sub', 'mul', 'div')
        b.asm("""
nvi_%(name)s:""" % dict(name=name) + ours('r5' if id_in_r5 else 'r4', 'nvi_%s_o' % name) + ("""
        mr r0, r4
        mr r4, r5
        mr r5, r0""" if id_in_r5 else "") + """
        li r6, %(k)d
        b nvi_op
nvi_%(name)s_o:                         # not ours: the class's own code (the base copy: the same)
        lis r12, 0x%(hi)X
        ori r12, r12, 0x%(lo)X
        mtctr r12
        bctr
""" % dict(name=name, k=k, hi=base >> 16, lo=base & 0xFFFF))


CLIFF_KINDS = [(0x72, 0x7A), (0xF3, 0xF4)]   # CliffCatchMove - CliffJumpQuick2, AirCatchHit / AirCatchHang (a tether)


def gs_code(b):
    """Gravity_Set: the command, its table lookups, the gravity energy update's entry / exit hooks, the damage reaction
    hook, the status change clear (from hk_lgc_chg) and the GRAVITY / MAX_FALL variables (from ue_nv), in GS_CODE"""
    D = dict(n=GS_N, mask=GS_N * 0x20 - 1, upd_back=GS_UPD + 4, end_back=GS_UPD_END + 4, hit_back=GS_HIT + 4,
             chg_back=LGC_CHG + 4, svh=FIGHTER_STATUS_VT >> 16, svl=FIGHTER_STATUS_VT & 0xFFFF,
             kvh=FIGHTER_KINETIC_VT >> 16, kvl=FIGHTER_KINETIC_VT & 0xFFFF, gvh=GRAV_VT >> 16, gvl=GRAV_VT & 0xFFFF,
             wh=WORK_W >> 16, wl=WORK_W & 0xFFFF, ffh=FAST_FALL_FLAG >> 16, ffl=FAST_FALL_FLAG & 0xFFFF,
             g0=GS_VARS[0], g1=GS_VARS[1])
    cliff = ''.join("""
        addi r12, r10, -0x%X
        cmplwi r12, %d
        ble gg_clear""" % (lo_k, hi_k - lo_k) for lo_k, hi_k in CLIFF_KINDS)     # (not r0: addi rD, r0, n is li)
    b.asm("""
# --- Gravity_Set(Accel, MaxFall, Mode): Accel / MaxFall < 0 keep the fighter's own; Mode 1 multipliers of its own,
#     2 a fall faster than MaxFall is cut to it at once, 4 no fast fall. Accel and MaxFall < 0 with Mode 0 / 1: off
h_gs:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r27, 0x1C(r1)
        mr r31, r5                      # script state
        mr r30, r7                      # parameters
        mr r29, r3                      # accessor
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq gs_step""" % D + chk_t('r29', 'r0', 'gs_step') + """
        lwz r28, 0x20(r29)              # StatusModule""" + chk_t('r28', 'r0', 'gs_step') + """
        lwz r0, 0(r28)
        lis r12, 0x%(svh)X
        ori r12, r12, 0x%(svl)X
        cmplw r0, r12
        bne gs_step                     # fighters only
        lis r12, gs_zero@ha
        lfs f0, gs_zero@l(r12)
        lfs f1, 0(r30)                  # Accel
        lfs f2, 4(r30)                  # MaxFall
        li r4, 1
        fcmpu cr0, f1, f0
        bge gs_on
        fcmpu cr0, f2, f0
        bge gs_on
        lwz r0, 8(r30)
        andi. r0, r0, 6
        bne gs_on
        li r4, 0                        # off: only an existing entry, cleared
gs_on:
        mr r3, r29
        li r5, 0
        bl gs_find
        cmpwi r3, 0
        beq gs_step
        li r0, 0
        cmpwi r4, 0
        bne gs_set
        stw r0, 0(r3)
        stw r0, 4(r3)
        b gs_step
gs_set:
        stw r29, 0(r3)
        stw r28, 4(r3)
        stfs f1, 8(r3)
        stfs f2, 0xC(r3)
        lwz r0, 8(r30)                  # Mode
        stw r0, 0x10(r3)
gs_step:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne gs_hret
        lwz r11, 4(r31)
        addi r11, r11, 16
        stw r11, 4(r31)
        li r3, 2
gs_hret:
        lmw r27, 0x1C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- gs_find(r3 key, r4 make, r5 the key's offset: 0 accessor, 4 StatusModule) -> r3 its entry or 0 (make: a free
#     one, else the next in turn; the caller fills it). Leaf: r0 r3 r10 r11 r12 ----------------------------------
gs_find:
        lis r12, gs_tab@ha
        addi r12, r12, gs_tab@l
        li r11, %(n)d
        li r10, 0
gf_loop:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq gf_free
        lwzx r0, r12, r5
        cmplw r0, r3
        beq gf_hit
        b gf_next
gf_free:
        cmpwi r10, 0
        bne gf_next
        mr r10, r12
gf_next:
        addi r12, r12, 0x20
        addi r11, r11, -1
        cmpwi r11, 0
        bne gf_loop
        cmpwi r4, 0
        beq gf_none
        cmpwi r10, 0
        bne gf_take
        lis r11, gs_rr@ha
        lwz r10, gs_rr@l(r11)           # all taken: the next in turn
        addi r0, r10, 0x20
        andi. r0, r0, %(mask)d
        stw r0, gs_rr@l(r11)
        lis r12, gs_tab@ha
        addi r12, r12, gs_tab@l
        add r10, r12, r10
gf_take:
        mr r3, r10
        blr
gf_hit:
        mr r3, r12
        blr
gf_none:
        li r3, 0
        blr

# --- gs_get(r3 accessor) -> r3 its live entry or 0. On a ledge (situation 1, or a cliff status / tether hang as the
#     current or the pending status) the entry is cleared first: a ledge grab ends it whatever path it took. r0 r3-r5
#     r10-r12 ---------------------------------------------------------------------------------------------------
gs_get:
        stwu r1, -0x10(r1)
        mflr r0
        stw r0, 0x14(r1)
        li r4, 0
        li r5, 0
        bl gs_find
        cmpwi r3, 0
        beq gg_ret
        lwz r11, 4(r3)""" % D + chk_t('r11', 'r0', 'gg_ret') + """
        lwz r0, 0x84(r11)               # situation: 1 ledge
        cmpwi r0, 1
        beq gg_clear
        lwz r10, 0x48(r11)              # the status""" + cliff + """
        lwz r10, 0x4C(r11)              # the status being changed to""" + cliff + """
        b gg_ret
gg_clear:
        li r0, 0
        stw r0, 0(r3)
        stw r0, 4(r3)
        li r3, 0
gg_ret:
        lwz r0, 0x14(r1)
        mtlr r0
        addi r1, r1, 0x10
        blr

# --- gs_eff(r3 entry, f1 the energy's acceleration, f2 its max fall) -> f1, f2 the ones to use. Leaf: r0 r12 f0 f3
gs_eff:
        lis r12, gs_zero@ha
        lfs f0, gs_zero@l(r12)
        lwz r0, 0x10(r3)
        andi. r0, r0, 1                 # cr0: multipliers
        lfs f3, 8(r3)                   # Accel
        fcmpu cr1, f3, f0
        blt cr1, ge_max
        bne ge_amul
        fneg f1, f3                     # the energy's is negative (downward)
        b ge_max
ge_amul:
        fmuls f1, f1, f3
ge_max:
        lfs f3, 0xC(r3)                 # MaxFall
        fcmpu cr1, f3, f0
        blt cr1, ge_ret
        bne ge_mmul
        fmr f2, f3
        blr
ge_mmul:
        fmuls f2, f2, f3
ge_ret:
        blr

# --- hook: the gravity energy update's entry (r3 energy, r4 accessor). With a live entry: the energy's own
#     acceleration / max fall kept (gs_cur), the Gravity_Set ones put in for this update; Mode 2 cuts the fall
#     speed, Mode 4 turns the fast-fall flag off. ------------------------------------------------------------------
gs_upd:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stw r3, 0x10(r1)
        stw r4, 0x14(r1)
        stw r31, 0x18(r1)
        mr r31, r3
        mr r3, r4
        bl gs_get
        cmpwi r3, 0
        beq gu_go
        lfs f1, 0x24(r31)
        lfs f2, 0x28(r31)
        lis r12, gs_cur@ha
        addi r12, r12, gs_cur@l
        stw r31, 0(r12)
        stfs f1, 4(r12)
        stfs f2, 8(r12)
        bl gs_eff
        stfs f1, 0x24(r31)
        stfs f2, 0x28(r31)
        lwz r0, 0x10(r3)
        andi. r0, r0, 2
        beq gu_ff
        fneg f3, f2
        lfs f0, 4(r31)                  # vertical speed
        fcmpu cr0, f0, f3
        bge gu_ff
        stfs f3, 4(r31)
gu_ff:
        lwz r0, 0x10(r3)
        andi. r0, r0, 4
        beq gu_go
        lis r12, nc_args@ha
        addi r12, r12, nc_args@l
        li r0, 0x2711                   # WorkModule(0x2711, fast-fall flag): off
        stw r0, 0(r12)
        lis r0, 0x%(ffh)X
        ori r0, r0, 0x%(ffl)X
        stw r0, 4(r12)
        lwz r3, 0x14(r1)
        lis r4, 0x%(wh)X
        ori r4, r4, 0x%(wl)X
        li r5, 2
        bl nc_msc
gu_go:
        lwz r3, 0x10(r1)
        lwz r4, 0x14(r1)
        lwz r31, 0x18(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        stwu r1, -0x48(r1)              # the replaced instruction
        b 0x%(upd_back)08X

# --- hook: the update's exit (r28 energy): the energy's own acceleration / max fall back -------------------------
gs_end:
        lis r12, gs_cur@ha
        addi r12, r12, gs_cur@l
        lwz r11, 0(r12)
        cmplw r11, r28
        bne gs_end_b
        li r0, 0
        stw r0, 0(r12)
        lwz r0, 4(r12)
        stw r0, 0x24(r28)
        lwz r0, 8(r12)
        stw r0, 0x28(r28)
gs_end_b:
        mr r3, r29
        b 0x%(end_back)08X

# --- hook: the damage reaction decision (r4 accessor): run it; a hit that takes effect (0) ends the fighter's
#     Gravity_Set at once (a hit with no reaction, armor or too weak, leaves it) -------------------------------------
gs_hit:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r4, 0x10(r1)
        bl gs_hit_orig
        stw r3, 0x14(r1)
        cmpwi r3, 0
        bne gh_ret
        lwz r3, 0x10(r1)
        li r4, 0
        li r5, 0
        bl gs_find
        cmpwi r3, 0
        beq gh_ret
        li r0, 0
        stw r0, 0(r3)
        stw r0, 4(r3)
gh_ret:
        lwz r3, 0x14(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
gs_hit_orig:
        mflr r0                         # the replaced instruction (LR: back into gs_hit)
        b 0x%(hit_back)08X

# --- from hk_lgc_chg (every status change, r30 StatusModule; LR free): the fighter's entry goes -------------------
gs_chg:
        mr r3, r30
        li r4, 0
        li r5, 4
        bl gs_find
        cmpwi r3, 0
        beq gs_chg_b
        li r0, 0
        stw r0, 0(r3)
        stw r0, 4(r3)
gs_chg_b:
        b 0x%(chg_back)08X

# --- from ue_nv (user_entry: r31 WorkModule, r30 index, r29 write; r27 r28 free): 0x337 GRAVITY / 0x338 MAX_FALL,
#     the gravity in effect (what the next update uses, Gravity_Set's included); read only; other objects read 0 --
gs_var:
        cmplwi r30, 0x%(g0)X
        blt gv_zero
        cmplwi r30, 0x%(g1)X
        bgt gv_zero
        cmpwi r29, 0
        bne gv_out
        mr r3, r31
        bl acc_of""" % D + chk_t('r3', 'r0', 'gv_zero') + """
        mr r28, r3
        lwz r27, 0x34(r3)               # KineticModule""" + chk_t('r27', 'r0', 'gv_zero') + """
        lwz r0, 0(r27)
        lis r12, 0x%(kvh)X
        ori r12, r12, 0x%(kvl)X
        cmplw r0, r12
        bne gv_zero                     # fighters only
        addi r27, r27, 0x334            # energy 1
        lwz r0, 0x1C(r27)
        lis r12, 0x%(gvh)X
        ori r12, r12, 0x%(gvl)X
        cmplw r0, r12
        bne gv_zero
        mr r3, r28
        bl gs_get
        lfs f1, 0x24(r27)
        lfs f2, 0x28(r27)
        cmpwi r3, 0
        beq gv_pick
        bl gs_eff
gv_pick:
        cmplwi r30, 0x%(g0)X
        bne gv_max
        fneg f1, f1
        b ue_out
gv_max:
        fmr f1, f2
gv_out:
        b ue_out
gv_zero:
        b hv_var                        # (exe_v43: the hitbox variables 0x3C0-0x3C8; any other ID still reads 0)
gs_cur:                                 # the energy being updated with Gravity_Set's values, then its own two
        .word 0
        .word 0
        .word 0
gs_rr:
        .word 0
gs_zero:
        .float 0.0
""" % D)


def hv_code(b):
    """Hitbox variables (HV_* above): the Extra hitbox commands' wrappers, the conversion, the FOLLOW table (record,
    per-frame update, object reset) and the variables 0x0F0003C0-3C8 (stick angles / lengths, rotation), in HV_CODE"""
    D = dict(n=HV_N, es=HV_ENTRY, tag=TAG, tag_off=TAG_OFF, entries=ENTRIES, entry=ENTRY, f0=4 * HV_FIELD0,
             pfh=POSTURE_FW >> 16, pfl=POSTURE_FW & 0xFFFF, v0=HV_VARS, v8=HV_VARS + len(HV_VAR_NAMES) - 1,
             vr=HV_VARS + 6, sp0=HV_SPECIAL[0], spn=HV_SPECIAL[1] - HV_SPECIAL[0],
             frame_back=FRAME_HOOK + 4, vdmg=AM_SET_DAMAGE, vsize=AM_SET_SIZE)
    fl = lambda reg, fail: chk_t(reg, 'r0', fail)     # noqa: E731
    posture = """
        lis r12, nc_args@ha
        addi r12, r12, nc_args@l
        stw %s, 0(r12)
        lis r4, 0x%%(pfh)X
        ori r4, r4, 0x%%(pfl)X
        li r5, 1
        bl nc_msc                       # PostureModuleF(op): r3 the float's bits"""
    b.asm(("""
# --- the Extra hitbox commands' handlers (cmd_handlers): h_extra / h_extra_ext with variables in their fields ------
# frame 0xA0: 0x10 + 4k the field words as written, 0x28 + 4k the values put in their place, r22-r31 at 0x78
hv_extra:
        lis r12, h_extra@ha
        addi r12, r12, h_extra@l
        b hv_go
hv_extra_ext:
        lis r12, h_extra_ext@ha
        addi r12, r12, h_extra_ext@l
hv_go:
        stwu r1, -0xA0(r1)
        mflr r0
        stw r0, 0xA4(r1)
        stmw r22, 0x78(r1)
        mr r31, r3                      # accessor
        mr r30, r4
        mr r29, r5                      # script state
        mr r28, r6
        mr r27, r7                      # parameters
        mr r26, r12                     # the handler (h_extra / h_extra_ext)
        li r25, 0                       # fields replaced (bit k: field k)
        lbz r0, 8(r28)                  # skipped (not executed): as before
        cmpwi r0, 0
        beq hv_call
        li r24, 0
hv_scan:
        slwi r23, r24, 2
        addi r22, r23, %(f0)d            # the field's parameter (Damage = parameter 3)
        lwzx r4, r27, r22
        addi r11, r1, 0x10
        stwx r4, r11, r23
        rlwinm r0, r4, 8, 24, 31        # a variable: 0x01000000 <= word < 0x20000000
        cmplwi r0, 1
        blt hv_snext
        cmplwi r0, 0x20
        bge hv_snext
        mr r3, r31
        mr r5, r24
        bl hv_value
        stwx r3, r27, r22               # the value, in the command's own word for the game's handler
        addi r11, r1, 0x28
        stwx r3, r11, r23
        li r0, 1
        slw r0, r0, r24
        or r25, r25, r0
hv_snext:
        addi r24, r24, 1
        cmpwi r24, 6
        blt hv_scan
hv_call:
        mtctr r26
        mr r3, r31
        mr r4, r30
        mr r5, r29
        mr r6, r28
        mr r7, r27
        bctrl                           # h_extra: the game's hitbox handler, the extras, the step
        mr r24, r3
        cmpwi r25, 0
        beq hv_ret
        li r23, 0                       # the words put back
        li r30, 0                       # the fields that FOLLOW
hv_back:
        srw r0, r25, r23
        andi. r0, r0, 1
        beq hv_bnext
        slwi r22, r23, 2
        addi r11, r1, 0x10
        lwzx r0, r11, r22
        addi r11, r27, %(f0)d
        stwx r0, r11, r22
        rlwinm. r0, r0, 0, 11, 11       # 0x00100000 FOLLOW
        beq hv_bnext
        li r0, 1
        slw r0, r0, r23
        or r30, r30, r0
hv_bnext:
        addi r23, r23, 1
        cmpwi r23, 6
        blt hv_back
        lwz r29, 0x50(r31)              # AttackModule""" + fl('r29', 'hv_ret') + """
        lwz r4, 0(r27)                  # ID
        lwz r0, 0x3C(r29)
        cmplw r4, r0
        bge hv_ret
        lwz r28, 0x40(r29)""" + fl('r28', 'hv_ret') + """
        mulli r4, r4, 0x84
        add r28, r28, r4                # the slot
        lis r12, hv_tab@ha              # a FOLLOW of this slot's earlier hitbox ends
        addi r12, r12, hv_tab@l
        li r11, %(n)d
hv_drop:
        lwz r0, 8(r12)
        cmplw r0, r28
        bne hv_dnext
        li r0, 0
        stw r0, 0(r12)
hv_dnext:
        addi r12, r12, %(es)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne hv_drop
        cmpwi r30, 0
        beq hv_ret
        lhz r23, %(tag_off)d(r28)       # tagged by ext_record (h_extra) just now
        rlwinm r0, r23, 0, 16, 23
        cmplwi r0, %(tag)d
        bne hv_ret
        rlwinm r0, r23, 0, 24, 31
        cmplwi r0, %(entries)d
        bge hv_ret
        mulli r0, r0, %(entry)d
        lis r12, table@ha
        addi r12, r12, table@l
        lwzx r0, r12, r0
        cmplw r0, r28
        bne hv_ret
        lis r12, hv_tab@ha              # a free entry, else the next in turn
        addi r12, r12, hv_tab@l
        li r11, %(n)d
hv_free:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq hv_take
        addi r12, r12, %(es)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne hv_free
        lis r11, hv_rr@ha
        lwz r10, hv_rr@l(r11)
        addi r0, r10, 1
        cmplwi r0, %(n)d
        blt hv_wrap
        li r0, 0
hv_wrap:
        stw r0, hv_rr@l(r11)
        mulli r10, r10, %(es)d
        lis r12, hv_tab@ha
        addi r12, r12, hv_tab@l
        add r12, r12, r10
hv_take:
        stw r31, 0(r12)
        stw r29, 4(r12)
        stw r28, 8(r12)
        stw r23, 0xC(r12)
        stw r30, 0x10(r12)
        lwz r0, 0(r27)
        stw r0, 0x44(r12)               # the ID (for the AttackModule calls)
        li r23, 0
hv_coef:
        srw r0, r30, r23
        andi. r0, r0, 1
        beq hv_cnext
        slwi r22, r23, 2
        addi r11, r1, 0x10
        lwzx r0, r11, r22
        addi r11, r12, 0x14
        stwx r0, r11, r22               # the field's word (variable and flags)
        addi r11, r1, 0x28
        lwzx r3, r11, r22               # the value written
        cmpwi r23, 0
        beq hv_cdmg
        cmpwi r23, 5
        beq hv_csize
        addi r11, r28, 0x1C             # ints: the slot's word (+0x20 + 4 (k - 1)) - the value
        lwzx r0, r11, r22
        subf r0, r3, r0
        b hv_cset
hv_cdmg:
        lfs f1, 0x18(r28)
        b hv_cdiv
hv_csize:
        lfs f1, 0x1C(r28)
hv_cdiv:
        stw r3, 8(r1)
        lfs f2, 8(r1)
        lis r11, hv_k@ha
        lfs f0, hv_k@l(r11)             # 0.0
        fcmpu cr0, f2, f0
        bne hv_cratio
        lfs f1, hv_one@l(r11)           # (0 written: x1)
        b hv_cst
hv_cratio:
        fdivs f1, f1, f2
hv_cst:
        stfs f1, 8(r1)
        lwz r0, 8(r1)
hv_cset:
        addi r11, r12, 0x2C
        stwx r0, r11, r22
hv_cnext:
        addi r23, r23, 1
        cmpwi r23, 6
        blt hv_coef
hv_ret:
        mr r3, r24
        lmw r22, 0x78(r1)
        lwz r0, 0xA4(r1)
        mtlr r0
        addi r1, r1, 0xA0
        blr

# --- hv_value(r3 accessor, r4 the field's word, r5 field 0-5) -> r3 the word for the field (float bits / int) ------
hv_value:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r29, 0x24(r1)
        mr r31, r3
        mr r30, r4
        mr r29, r5
        rlwinm r4, r30, 0, 12, 7        # the ID: the flags (bits 20-23) off
        lwz r3, 0x28(r31)               # WorkModule""" + fl('r3', 'hvl_zero') + """
        lwz r12, 0(r3)
        rlwinm r0, r4, 4, 28, 31
        cmpwi r0, 1
        beq hvl_int
        lwz r12, 0x44(r12)              # get_float (the mod's 0x0F000xxx through position_vars' hooks)
        mtctr r12
        bctrl
        b hvl_have
hvl_int:
        lwz r12, 0x84(r12)              # get_int (New_Var's int IDs 0x1F00038x included)
        mtctr r12
        bctrl
        bl i2f
hvl_have:
        rlwinm. r0, r30, 0, 9, 9        # 0x00400000 NEG
        beq hvl_pos
        fneg f1, f1
hvl_pos:
        cmpwi r29, 1
        beq hvl_angle
        cmpwi r29, 0
        beq hvl_float
        cmpwi r29, 5
        beq hvl_float
        bl hv_round                     # KBG / FKB / BKB: rounded, >= 0
        cmpwi r3, 0
        bge hvl_ret
        li r3, 0
        b hvl_ret
hvl_float:                              # Damage / Size: >= 0 (NaN: 0)
        lis r12, hv_k@ha
        lfs f0, hv_k@l(r12)
        fcmpu cr0, f1, f0
        bge hvl_fok
        fmr f1, f0
hvl_fok:
        stfs f1, 8(r1)
        lwz r3, 8(r1)
        b hvl_ret
hvl_angle:
        rlwinm. r0, r30, 0, 10, 10      # 0x00200000 WORLD: facing left -> 180 - a
        beq hvl_round
        stfs f1, 0x18(r1)
        mr r3, r31
        li r0, 0                        # PostureModuleF(0): the facing""" + posture % 'r0' + """
        stw r3, 8(r1)
        lfs f2, 8(r1)
        lfs f1, 0x18(r1)
        lis r12, hv_k@ha
        lfs f0, hv_k@l(r12)
        fcmpu cr0, f2, f0
        bge hvl_round
        lfs f0, hv_180@l(r12)
        fsubs f1, f0, f1
hvl_round:
        bl hv_round
        addi r0, r3, -%(sp0)d            # 361-368: the special angles, as they are
        cmplwi r0, %(spn)d
        ble hvl_ret
        li r0, 360
        divw r12, r3, r0
        mullw r12, r12, r0
        subf r3, r12, r3
        cmpwi r3, 0
        bge hvl_ret
        addi r3, r3, 360
        b hvl_ret
hvl_zero:
        li r3, 0
hvl_ret:
        lmw r29, 0x24(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- hv_round(f1) -> r3: to the nearest whole number (halves away from 0); f0 f1 f2 r12 ---------------------------
hv_round:
        lis r12, hv_k@ha
        lfs f0, hv_k@l(r12)
        lfs f2, hv_half@l(r12)
        fcmpu cr0, f1, f0
        bge hr_pos
        fneg f2, f2
hr_pos:
        fadds f1, f1, f2
        b f2i

# --- FRAME_HOOK (every object, every frame it moves, after its ACMD; r31 MotionModule): the FOLLOW fields, then
#     the timers / tracking (hk_frame, which runs the replaced li r0, 1). Volatile registers are free there. -------
hv_fhook:
        lwz r3, 4(r31)                  # accessor
        bl hv_frame
        b hk_frame

# --- hv_frame(r3 accessor): its FOLLOW entries: still its hitbox? then the fields again -----------------------------
hv_frame:""" + fl('r3', 'hf_none') + """
        stwu r1, -0x50(r1)
        mflr r0
        stw r0, 0x54(r1)
        stmw r24, 0x30(r1)
        mr r31, r3
        lis r30, hv_tab@ha
        addi r30, r30, hv_tab@l
        li r29, %(n)d
hvf_loop:
        lwz r0, 0(r30)
        cmplw r0, r31
        bne hvf_next
        lwz r3, 0x50(r31)
        lwz r0, 4(r30)
        cmplw r3, r0
        bne hvf_drop
        lwz r28, 8(r30)                 # the slot: the same hitbox (tag) and extras entry?
        lhz r3, %(tag_off)d(r28)
        lwz r0, 0xC(r30)
        cmplw r3, r0
        bne hvf_drop
        rlwinm r3, r3, 0, 24, 31
        mulli r3, r3, %(entry)d
        lis r27, table@ha
        addi r27, r27, table@l
        add r27, r27, r3
        lwz r0, 0(r27)
        cmplw r0, r28
        bne hvf_drop
        li r26, 0
hvf_field:
        lwz r25, 0x10(r30)
        srw r0, r25, r26
        andi. r0, r0, 1
        beq hvf_fnext
        slwi r24, r26, 2
        mr r3, r31
        addi r4, r30, 0x14
        lwzx r4, r4, r24
        mr r5, r26
        bl hv_value
        addi r12, r30, 0x2C             # its coefficient
        cmpwi r26, 0
        beq hvf_dmg
        cmpwi r26, 5
        beq hvf_size
        lwzx r0, r12, r24
        add r3, r3, r0
        addi r11, r28, 0x1C
        stwx r3, r11, r24               # slot +0x20 / 24 / 28 / 2C
        stwx r3, r27, r24               # the extras entry's check word (+4 / 8 / C / 10)
        b hvf_fnext
hvf_dmg:
        li r10, %(vdmg)d                 # AttackModule vt +0xB4 (id, damage, 0): Change_Hitbox_Damage's call
        b hvf_mul
hvf_size:
        li r10, %(vsize)d                 # vt +0xCC (id, size): Change_Hitbox_Size's call
hvf_mul:
        stw r3, 8(r1)
        lfs f1, 8(r1)
        lfsx f2, r12, r24
        fmuls f1, f1, f2
        lwz r3, 0x50(r31)
        lwz r12, 0(r3)
        lwzx r12, r12, r10
        mtctr r12
        lwz r4, 0x44(r30)               # the hitbox ID
        li r5, 0
        bctrl
hvf_fnext:
        addi r26, r26, 1
        cmpwi r26, 6
        blt hvf_field
        b hvf_next
hvf_drop:
        li r0, 0
        stw r0, 0(r30)
hvf_next:
        addi r30, r30, %(es)d
        addi r29, r29, -1
        cmpwi r29, 0
        bne hvf_loop
        lmw r24, 0x30(r1)
        lwz r0, 0x54(r1)
        mtlr r0
        addi r1, r1, 0x50
hf_none:
        blr

# --- WM_RESET (object set up / reused; r31 accessor; r0 r10 ctr free): its FOLLOW entries go; then hk_wmreset -------
hv_wmreset:
        lis r10, hv_tab@ha
        addi r10, r10, hv_tab@l
        li r0, %(n)d
        mtctr r0
hvw_loop:
        lwz r0, 0(r10)
        cmplw r0, r31
        bne hvw_next
        li r0, 0
        stw r0, 0(r10)
hvw_next:
        addi r10, r10, %(es)d
        bdnz hvw_loop
        b hk_wmreset

# --- user_entry's 0x3C0-0x3C8 (from gs_var's gv_zero; r31 WorkModule, r30 index, r29 write; r27 r28 free), read only:
#     0x3C0 + 3c + q: c 0 stick / 1 C-stick; q 0 angle along the facing (0 forward, 90 up: a hitbox angle), 1 angle
#     on screen (0 right), 2 length. 0x3C6-0x3C8: the rotation X / Y / Z (PostureModuleF(4-6), degrees). Others: 0
hv_var:
        cmplwi r30, %(v0)d
        blt hvv_zero
        cmplwi r30, %(v8)d
        bgt hvv_zero
        cmpwi r29, 0
        bne hvv_out
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        cmplwi r30, %(vr)d
        blt hvv_stick
        mr r3, r31
        bl acc_of""" + fl('r3', 'hvv_pzero') + """
        addi r28, r30, -%(vr)d
        addi r28, r28, 4""" + posture % 'r28' + """
        stw r3, 8(r1)
        lfs f1, 8(r1)
        b hvv_done
hvv_stick:
        addi r28, r30, -%(v0)d
        li r27, 0                       # c
        cmplwi r28, 3
        blt hvv_c
        li r27, 1
        addi r28, r28, -3               # q
hvv_c:
        slwi r0, r27, 1
        lis r4, 0x0F00
        ori r4, r4, 0x110               # STICK_X (along the facing) / CSTICK_X
        add r4, r4, r0
        cmplwi r28, 1
        bne hvv_x
        lis r4, 0x0F00
        ori r4, r4, 0x260               # STICK_X_RAW / CSTICK_X_RAW (on screen)
        add r4, r4, r27
hvv_x:
        mr r3, r31
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl
        stfs f1, 0x10(r1)               # x
        slwi r0, r27, 1
        lis r4, 0x0F00
        ori r4, r4, 0x111               # STICK_Y / CSTICK_Y
        add r4, r4, r0
        mr r3, r31
        lwz r12, 0(r3)
        lwz r12, 0x44(r12)
        mtctr r12
        bctrl                           # f1 = y
        lfs f2, 0x10(r1)
        cmplwi r28, 2
        beq hvv_len
        bl hv_atan2
        b hvv_done
hvv_len:
        fmuls f1, f1, f1
        fmadds f1, f2, f2, f1
        bl fsqrt
hvv_done:
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
hvv_out:
        b ue_out
hvv_pzero:
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
hvv_zero:
        b ue_zero

# --- hv_atan2(f1 y, f2 x) -> f1 degrees, 0 to 360 (0: +x, 90: +y; 0 for (0, 0)); f0 f3-f8, cr0 cr1, r12 ---------
hv_atan2:
        lis r12, hv_k@ha
        addi r12, r12, hv_k@l
        lfs f0, 0(r12)
        fabs f3, f2
        fabs f4, f1
        fcmpu cr0, f3, f0
        bne hat_go
        fcmpu cr0, f4, f0
        bne hat_go
        fmr f1, f0
        blr
hat_go:
        fcmpu cr1, f4, f3
        ble cr1, hat_low
        fdivs f5, f3, f4                # |y| > |x|: z = |x| / |y|, angle 90 - atan z
        b hat_poly
hat_low:
        fdivs f5, f4, f3                # z = |y| / |x|, angle atan z
hat_poly:
        fmuls f6, f5, f5
        lfs f7, 4(r12)
        lfs f8, 8(r12)
        fmadds f7, f7, f6, f8
        lfs f8, 12(r12)
        fmadds f7, f7, f6, f8
        lfs f8, 16(r12)
        fmadds f7, f7, f6, f8
        lfs f8, 20(r12)
        fmadds f7, f7, f6, f8
        fmuls f7, f7, f5                # atan z (radians, z in 0-1: within 1e-5)
        lfs f8, 24(r12)
        fmuls f7, f7, f8                # degrees
        ble cr1, hat_q
        lfs f8, 28(r12)
        fsubs f7, f8, f7
hat_q:
        fcmpu cr0, f2, f0
        bge hat_y
        lfs f8, 32(r12)
        fsubs f7, f8, f7                # x < 0: 180 - a
hat_y:
        fcmpu cr0, f1, f0
        bge hat_out
        lfs f8, 36(r12)
        fsubs f7, f8, f7                # y < 0: 360 - a
        fcmpu cr0, f7, f8
        blt hat_out
        fsubs f7, f7, f8
hat_out:
        fmr f1, f7
        blr
hv_k:
        .float 0.0
        .float 0.0208351                # atan z = z (a1 + a3 z^2 + ... + a9 z^8) (Abramowitz & Stegun 4.4.49)
        .float -0.0851330
        .float 0.1801410
        .float -0.3302995
        .float 0.9998660
        .float 57.29577951
hv_90:
        .float 90.0
hv_180:
        .float 180.0
        .float 360.0
hv_half:
        .float 0.5
hv_one:
        .float 1.0
hv_rr:
        .word 0
""") % D)
    assert b.labels['hv_90'] - b.labels['hv_k'] == 28 and b.labels['hv_180'] - b.labels['hv_k'] == 32



def ha(v):
    return ((v + 0x8000) >> 16) & 0xFFFF


def lo(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def crc(name):
    return zlib.crc32(name.encode()) & 0xFFFFFFFF


def build():
    a = Asm(CAVE)
    n = len(COMMANDS)
    # --- dispatch -----------------------------------------------------------------------------
    a.asm("""
lookup:                                 # r3 = CRC not in the game's table
        lis r12, cmd_crcs@ha
        addi r12, r12, cmd_crcs@l
        li r11, 0
lk_loop:
        cmpwi r11, %(n)d
        bge lk_none
        slwi r0, r11, 2
        lwzx r0, r12, r0
        cmplw r0, r3
        beq lk_found
        addi r11, r11, 1
        b lk_loop
lk_found:
        addi r3, r11, %(base)d
        blr
lk_none:
        li r3, -1
        blr

size1:
        slwi r10, r3, 2
        stwx r3, r28, r5
        addi r0, r3, -%(base)d
        cmplwi r0, %(n)d
        bge s1_orig
        slwi r10, r0, 2
        addis r10, r10, cmd_sizes@ha     # (addis rD, r0, ... would read r0 as 0)
        lwz r0, cmd_sizes@l(r10)
        slwi r10, r3, 2
        b 0x%(s1back)08X
s1_orig:
        lwzx r0, r10, r4
        b 0x%(s1back)08X

size2:
        slwi r11, r3, 2
        stwx r3, r28, r5
        addi r12, r3, -%(base)d
        cmplwi r12, %(n)d
        bge s2_orig
        slwi r12, r12, 2
        addis r12, r12, cmd_sizes@ha
        lwz r12, cmd_sizes@l(r12)
        b 0x%(s2back)08X
s2_orig:
        lwzx r12, r11, r30
        b 0x%(s2back)08X

fetch:
        addi r6, r7, -%(base)d
        cmplwi r6, %(n)d
        bge f_orig
        slwi r6, r6, 2
        addis r6, r6, cmd_handlers@ha
        lwz r0, cmd_handlers@l(r6)
        b 0x%(fback)08X
f_orig:
        slwi r6, r7, 2
        lwzx r0, r6, r29
        b 0x%(fback)08X
""" % dict(n=n, base=NEW_BASE, s1back=SIZE1 + 12, s2back=SIZE2 + 12, fback=FETCH + 8))

    # --- Extra hitbox handlers ----------------------------------------------------------------
    for _name, size, label, base in COMMANDS[:2]:
        a.asm("""
%(label)s:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r27, 0x1C(r1)
        mr r31, r3                      # accessor
        mr r30, r5                      # script state
        mr r29, r6
        mr r28, r7                      # parameters
        bl 0x%(base)08X                 # the hitbox itself; steps over its own words
        mr r27, r3
        lbz r0, 8(r29)                  # executed (not skipped)?
        cmpwi r0, 0
        beq %(label)s_step
        lis r12, dbg@ha
        addi r12, r12, dbg@l
        lwz r11, 60(r12)
        addi r11, r11, 1
        stw r11, 60(r12)
        lwz r11, 0(r28)
        stw r11, 0x40(r12)
        mr r3, r31
        mr r4, r28
        addi r5, r28, %(extra)d         # the extra parameters
        bl ext_record
%(label)s_step:
        lwz r0, 8(r30)
        cmpwi r0, -1
        bne %(label)s_out
        lwz r11, 4(r30)
        addi r11, r11, %(extra_bytes)d
        stw r11, 4(r30)
%(label)s_out:
        mr r3, r27
        lmw r27, 0x1C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
""" % dict(label=label, base=base, extra=4 * (size - N_EXTRA - 1), extra_bytes=4 * N_EXTRA))

    # ext_record(r3 accessor, r4 params (ID first), r5 extras): find the slot, take an entry, copy.
    a.asm(("""
ext_record:
""" + chk('r3', 'er_out') + """
        lwz r6, 0x50(r3)                # AttackModule
""" + chk('r6', 'er_out') + """
        lwz r7, 0(r4)                   # ID, below the module's own slot count (fighters 10, dein copies 7)
        lwz r0, 0x3C(r6)
        cmplw r7, r0
        bge er_out
        lwz r8, 0x40(r6)                # slots
""" + chk('r8', 'er_out') + """
        mulli r7, r7, 0x84
        add r8, r8, r7                  # slot (its data)
        lis r9, table@ha
        addi r9, r9, table@l
                                        # always a new entry (round robin): a hit of this slot's previous
                                        # hitbox still being handled keeps its own extras (the slot's entry
                                        # used to be reused: such a hit read the new hitbox's extras)
        lis r12, next_entry@ha
        lwz r10, next_entry@l(r12)
        addi r0, r10, 1
        cmplwi r0, %(entries)d
        blt er_wrap
        li r0, 0
er_wrap:
        stw r0, next_entry@l(r12)
        mulli r11, r10, %(entry)d
        add r11, r9, r11
                                        # r10 = entry number, r11 = entry, r8 = slot
        stw r8, 0(r11)
        lwz r0, 0x20(r8)
        stw r0, 4(r11)
        lwz r0, 0x24(r8)
        stw r0, 8(r11)
        lwz r0, 0x28(r8)
        stw r0, 0xC(r11)
        lwz r0, 0x2C(r8)
        stw r0, 0x10(r11)
        lwz r0, 0x3C(r8)
        stw r0, 0x2C(r11)
        lis r12, one@ha
        lfs f0, one@l(r12)              # 1.0
        lfs f2, zero@l(r12)             # 0.0 (next to it)
""" + mul('0', '0x14', 'hs', signed=True) + mul('4', '0x18', 'hp') + """
        lwz r0, 8(r5)                   # hitstop frames
        stw r0, 0x1C(r11)
""" + mul('0xC', '0x20', 'sp') + """
        lwz r0, 0x10(r5)                # self hitstop frames
        stw r0, 0x24(r11)
""" + mul('0x14', '0x28', 'di') + """
        ori r0, r10, %(TAG)d
        sth r0, %(tag)d(r8)
        lis r12, dbg@ha
        addi r12, r12, dbg@l
        lwz r9, 0(r12)
        addi r9, r9, 1
        stw r9, 0(r12)
er_out:
        blr
""") % dict(tag=TAG_OFF, TAG=TAG, entries=ENTRIES, entry=ENTRY))
    a.asm('''
slot_set:                               # every hitbox set: the slot's tag cleared (ext_record tags an Extra one after)
        li r0, 0
        sth r0, %d(r26)
        lwz r10, 0x14(r28)
        b 0x%08X
''' % (TAG_OFF, SLOT_SET + 4))
    # ext_find(r3 data) -> r3 entry or 0. Leaf: r0, r11, r12.
    a.asm("""
ext_find:
        andi. r0, r3, 3
        bne ef_none
        addis r0, r3, -0x1000
        rlwinm. r0, r0, 0, 0, 0
        bne ef_none
        lhz r11, %(tag)d(r3)
        rlwinm r0, r11, 0, 16, 23
        cmplwi r0, %(TAG)d
        bne ef_none
        rlwinm r11, r11, 0, 24, 31
        cmplwi r11, %(entries)d
        bge ef_none
        mulli r11, r11, %(entry)d
        lis r12, table@ha
        addi r12, r12, table@l
        add r11, r12, r11
        lwz r0, 0(r11)
        cmplw r0, r3
        bne ef_none
        lwz r0, 0x20(r3)
        lwz r12, 4(r11)
        cmplw r0, r12
        bne ef_none
        lwz r0, 0x24(r3)
        lwz r12, 8(r11)
        cmplw r0, r12
        bne ef_none
        lwz r0, 0x28(r3)
        lwz r12, 0xC(r11)
        cmplw r0, r12
        bne ef_none
        lwz r0, 0x2C(r3)
        lwz r12, 0x10(r11)
        cmplw r0, r12
        bne ef_none
        lwz r0, 0x3C(r3)
        lwz r12, 0x2C(r11)
        cmplw r0, r12
        bne ef_none
        mr r3, r11
        blr
ef_none:
        li r3, 0
        blr
one:
        .float 1.0
zero:
        .float 0.0
next_entry:
        .word 0
""" % dict(tag=TAG_OFF, TAG=TAG, entries=ENTRIES, entry=ENTRY))

    hit_code(a)
    obj_code(a)
    thread_code(a)
    input_code(a)
    b2 = Asm(CODE2)                     # the new commands (their labels resolve with the main part's, below)
    newcmd_code(b2)
    b3 = Asm(LGC_CODE)                  # Leave_Ground_Cancel (its own space: CODE2 is full)
    lgc_code(b3)
    assert not set(b3.labels) & (set(a.labels) | set(b2.labels)), set(b3.labels) & (set(a.labels) | set(b2.labels))
    a.labels.update(b3.labels)
    b4 = Asm(NV_CODE)                   # New_Var (the grown text region, after its slots' pool)
    nv_code(b4)
    assert not set(b4.labels) & (set(a.labels) | set(b2.labels)), set(b4.labels) & (set(a.labels) | set(b2.labels))
    a.labels.update(b4.labels)
    b5 = Asm(GS_CODE)                   # Gravity_Set (exe_v42: the grown text region, after New_Var's code)
    gs_code(b5)
    assert not set(b5.labels) & (set(a.labels) | set(b2.labels)), set(b5.labels) & (set(a.labels) | set(b2.labels))
    a.labels.update(b5.labels)
    b6 = Asm(HV_CODE)                   # hitbox variables (exe_v43: free space after ACC_CACHE)
    hv_code(b6)
    assert not set(b6.labels) & (set(a.labels) | set(b2.labels)), set(b6.labels) & (set(a.labels) | set(b2.labels))
    a.labels.update(b6.labels)
    b2.asm('cmd_crcs:\n' + ''.join('        .word 0x%08X\n' % crc(c[0]) for c in COMMANDS))
    b2.asm('cmd_sizes:\n' + ''.join('        .word %d\n' % c[1] for c in COMMANDS))
    a.labels.update(b2.labels)
    if a.pc % 8:
        a.asm('.word 0')
    a.asm("""
scratch:                                # scale_int: a double, then 2^52 + 2^31
        .word 0
        .word 0
        .word 0x43300000
        .word 0x80000000
ue_nv_far:                              # user_entry's New_Var IDs (exe_v40): ue_nv is out of bge's reach
        b ue_nv
""")
    b2.asm('cmd_handlers:\n' + ''.join('        .word 0x%08X\n' % a.addr(HANDLER.get(c[2], c[2])) for c in COMMANDS))
    a.labels.update(b2.labels)
    a.labels['table'] = TABLE
    a.labels['di_tab'] = TABLE + ENTRIES * ENTRY
    a.labels['objs'] = OBJS
    a.labels['acc_cache'] = ACC_CACHE
    a.labels['threads'] = THREADS
    a.labels['dbg'] = DBG
    a.labels['lgc_tab'] = LGC
    assert DBG + 0x100 <= LGC and LGC + LGC_N * 0x10 + 4 <= OBJS
    assert TABLE + ENTRIES * ENTRY + 8 * DI_SLOTS <= DBG and DBG + 0x100 <= OBJS
    assert a.addr('scratch') % 8 == 0, hex(a.addr('scratch'))
    b2.labels.update(a.labels)
    b3.labels.update(a.labels)
    b4.labels.update(a.labels)
    b5.labels.update(a.labels)
    b6.labels.update(a.labels)
    b6.labels['hv_tab'] = HV_TAB
    a.labels['hv_tab'] = HV_TAB
    a.labels['gs_tab'] = GS
    b5.labels['gs_tab'] = GS
    words = a.words()
    assert CAVE + 4 * len(words) <= TABLE, hex(CAVE + 4 * len(words))
    words2 = b2.words()
    assert THREADS + THREAD_N * THREAD_SIZE <= CODE2 and CODE2 + 4 * len(words2) <= GROW, hex(CODE2 + 4 * len(words2))
    a.part2 = (CODE2, words2)
    words3 = b3.words()
    assert LGC + LGC_N * 0x10 + 4 <= LGC_CODE and LGC_CODE + 4 * len(words3) <= OBJS, hex(LGC_CODE + 4 * len(words3))
    a.part3 = (LGC_CODE, words3)
    words4 = b4.words()
    assert OBJS + OBJ_N * OBJ_SIZE + NV_OFF <= NV_CODE and NV_CODE + 4 * len(words4) <= NV_LIMIT, hex(NV_CODE + 4 * len(words4))
    assert NV_INT + 8 <= OBJ_SIZE and NV_DECL + 8 <= NV_INT and OBJ_SIZE == 4 * NV_N
    a.part4 = (NV_CODE, words4)
    words5 = b5.words()
    assert NV_CODE + 4 * len(words4) <= GS_CODE and GS_CODE + 4 * len(words5) <= GS, hex(GS_CODE + 4 * len(words5))
    assert GS + GS_N * 0x20 <= NV_LIMIT
    a.part5 = (GS_CODE, words5)
    words6 = b6.words()
    assert ACC_CACHE + 64 * 8 <= HV_CODE and HV_CODE + 4 * len(words6) <= HV_TAB, hex(HV_CODE + 4 * len(words6))
    assert HV_TAB + HV_N * HV_ENTRY <= HV_LIMIT
    a.part6 = (HV_CODE, words6)
    assert ACC_CACHE + 64 * 8 <= THREADS and THREADS + THREAD_N * THREAD_SIZE <= GROW <= LIMIT
    hooks = {LOOKUP: b(LOOKUP, a.addr('lookup')), SIZE1: b(SIZE1, a.addr('size1')),
             SIZE2: b(SIZE2, a.addr('size2')), FETCH: b(FETCH, a.addr('fetch')),
             HIT_STUN: b(HIT_STUN, a.addr('hk_stun')), HIT_VSTOP: b(HIT_VSTOP, a.addr('hk_vstop')),
             HIT_AMUL: b(HIT_AMUL, a.addr('hk_amul')), HIT_AFIX: b(HIT_AFIX, a.addr('hk_afix')),
             DI_STAT: b(DI_STAT, a.addr('di_check')),   # was bnelr: di_check tests cr0
             SLOT_SET: b(SLOT_SET, a.addr('slot_set')),
             LGC_SIT: b(LGC_SIT, LGC_TRAMP[LGC_SIT]), LGC_REQ: b(LGC_REQ, LGC_TRAMP[LGC_REQ]),
             LGC_TRAMP[LGC_SIT]: b(LGC_TRAMP[LGC_SIT], a.addr('hk_lgc_sit')),
             LGC_TRAMP[LGC_REQ]: b(LGC_TRAMP[LGC_REQ], a.addr('hk_lgc_req')),
             LGC_CHG: b(LGC_CHG, a.addr('hk_lgc_chg')),
             FRAME_HOOK: b(FRAME_HOOK, a.addr('hv_fhook')), WM_RESET: b(WM_RESET, a.addr('hv_wmreset')),
             VAR_ENTRY: b(VAR_ENTRY, a.addr('user_gate')),
             GS_UPD: b(GS_UPD, a.addr('gs_upd')), GS_UPD_END: b(GS_UPD_END, a.addr('gs_end')),
             GS_HIT: b(GS_HIT, a.addr('gs_hit'))}
    for k, h in enumerate(STEP_HOOKS):
        hooks[h] = b(h, a.addr('hk_step%d' % k))
    for vt in WM_VTABLES:               # New_Var: the WorkModule int ops (absolute addresses: no branch range)
        for off, name, _base in WM_INT_OPS:
            hooks[vt + off] = a.addr('nvi_' + name)
    return a, words, hooks


def vcall(off):
    """call vt +off of the object in r3 (r12 / ctr clobbered)"""
    return """
        lwz r12, 0(r3)
        lwz r12, %d(r12)
        mtctr r12
        bctrl""" % off


def kcall(wrapper, words):
    """MSC module op through its wrapper: ctx at 0x40(r1) (+4 = accessor in r30), args {0x30(r1), n} at
    0x28(r1); words: ints, or ('f', stack offset) for a float kept at that offset of the frame"""
    out = ["        stw r30, 0x44(r1)"]
    for i, w in enumerate(words):
        if isinstance(w, tuple):
            out.append("        lwz r0, %d(r1)" % w[1])
        else:
            out.append("        li r0, %d" % w)
        out.append("        stw r0, %d(r1)" % (0x30 + 4 * i))
    out += ["        addi r0, r1, 0x30", "        stw r0, 0x28(r1)", "        li r0, %d" % len(words),
            "        stw r0, 0x2C(r1)", "        addi r3, r1, 0x40", "        addi r4, r1, 0x28",
            "        bl 0x%08X" % wrapper]
    return "\n" + "\n".join(out)


def obj_code(a):
    """per-object state: user variables / timers / kinetic type / tracking"""
    U = dict(ubase=USER_BASE, u20=USER_BASE + 0x20, u30=USER_BASE + 0x30, u31=USER_BASE + 0x31,
             u32=USER_BASE + 0x32, u33=USER_BASE + 0x33, u34=USER_BASE + 0x34, u36=USER_BASE + 0x36,
             u40=USER_BASE + 0x40, fha=ha(FIGHTERS), flo=lo(FIGHTERS), fsize=FIGHTER_ENTRY)
    fl = lambda reg, fail: chk_t(reg, 'r0', fail)     # noqa: E731
    a.asm("""
# --- obj_find(r3 WorkModule, r4 create) -> r3 entry or 0; leaf: r0 r10 r11 r12 -----------------
obj_find:
        lis r12, objs@ha
        addi r12, r12, objs@l
        li r11, %(n)d
of_loop:
        lwz r0, 0(r12)
        cmplw r0, r3
        beq of_hit
        addi r12, r12, %(size)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne of_loop
        cmpwi r4, 0
        beq of_none
        lis r12, objs@ha
        addi r12, r12, objs@l
        li r11, %(n)d
of_free:
        lwz r0, 0(r12)
        cmpwi r0, 0
        beq of_take
        addi r12, r12, %(size)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne of_free
        lis r10, obj_next@ha            # all taken: the oldest one goes
        lwz r11, obj_next@l(r10)
        addi r0, r11, 1
        cmplwi r0, %(n)d
        blt of_wrap
        li r0, 0
of_wrap:
        stw r0, obj_next@l(r10)
        mulli r11, r11, %(size)d
        lis r12, objs@ha
        addi r12, r12, objs@l
        add r12, r12, r11
of_take:
        b nv_take                       # (was li r0, 0: nv_take clears the entry's New_Var block, then r0 = 0)
of_take2:
        li r11, %(last)d
of_zero:
        stwx r0, r12, r11
        addi r11, r11, -4
        cmpwi r11, 0
        bge of_zero
        stw r3, 0(r12)
of_hit:
        mr r3, r12
        blr
of_none:
        li r3, 0
        blr

# --- acc_of(r3 WorkModule) -> r3 accessor or 0 (the per-frame cache); leaf: r0 r11 r12 -----------
acc_of:                                 # (searched: a direct-mapped cache let two objects evict each other)
        lis r11, acc_cache@ha
        addi r11, r11, acc_cache@l
        li r12, 64
ao_loop:
        lwz r0, 0(r11)
        cmplw r0, r3
        beq ao_hit
        addi r11, r11, 8
        addi r12, r12, -1
        cmpwi r12, 0
        bne ao_loop
        li r3, 0
        blr
ao_hit:
        lwz r3, 4(r11)
        blr

# --- acc_put(r3 WorkModule, r4 accessor): remember it (the same entry, else the next in turn); r0 r11 r12
acc_put:
        lis r11, acc_cache@ha
        addi r11, r11, acc_cache@l
        li r12, 64
ap_loop:
        lwz r0, 0(r11)
        cmplw r0, r3
        beq ap_set
        addi r11, r11, 8
        addi r12, r12, -1
        cmpwi r12, 0
        bne ap_loop
        lis r11, acc_next@ha
        lwz r12, acc_next@l(r11)
        addi r0, r12, 1
        cmplwi r0, 64
        blt ap_wrap
        li r0, 0
ap_wrap:
        stw r0, acc_next@l(r11)
        slwi r12, r12, 3
        lis r11, acc_cache@ha
        addi r11, r11, acc_cache@l
        add r11, r11, r12
ap_set:
        stw r3, 0(r11)
        stw r4, 4(r11)
        blr
acc_next:
        .word 0

# --- i2f(r3) -> f1 (float); f2i(f1) -> r3 (truncated). r0 r12 f0 f12 ------------------------------
i2f:
        lis r12, scratch@ha
        addi r12, r12, scratch@l
        xoris r0, r3, 0x8000
        stw r0, 4(r12)
        lis r0, 0x4330
        stw r0, 0(r12)
        lfd f0, 0(r12)
        lfd f12, 8(r12)
        fsub f1, f0, f12
        frsp f1, f1
        blr
f2i:
        lis r12, scratch@ha
        addi r12, r12, scratch@l
        fctiwz f0, f1
        stfd f0, 0(r12)
        lwz r3, 4(r12)
        blr

# --- fsqrt(f1) -> f1; f0 f12 f13 (0 for <= 0) -----------------------------------------------------
fsqrt:
        lis r12, zero@ha
        lfs f0, zero@l(r12)
        fcmpu cr0, f1, f0
        bgt fs_go
        fmr f1, f0
        blr
fs_go:
        frsqrte f12, f1
        lfs f13, half@l(r12)
        lfs f0, onehalf@l(r12)
        fmul f13, f1, f13               # x / 2
        fmul f2, f12, f12
        fmul f2, f2, f13
        fsub f2, f0, f2
        fmul f12, f12, f2               # y (1.5 - x/2 y^2), twice
        fmul f2, f12, f12
        fmul f2, f2, f13
        fsub f2, f0, f2
        fmul f12, f12, f2
        fmul f1, f1, f12
        frsp f1, f1
        blr

# --- var_entry gate: IDs 0x0F000300+ -> user_entry ---------------------------------------------------
user_gate:
        rlwinm r12, r4, 0, 22, 31
        cmplwi r12, %(ubase)d
        blt ug_back
        b user_entry
ug_back:
        b 0x%(var_back)08X

# --- user_entry(r3 WorkModule, r4 ID, r5 write, f1 value) -> f1 ----------------------------------------
# 0x300+i (i < 32) user variable i; 0x320+i (i < 16) timer i (counts down to 0 each frame);
# 0x330 kinetic type (write: change it); 0x331 tracking frames left (write: set, 0 stops);
# 0x332 / 0x333 speed X / Y (read only, all energies); 0x334-0x336 team ids (read only);
# 0x340 + 8*s + k (s, k < 8): variable 24 + k of fighter table entry s (player slot s + 1), the same
# storage as that fighter's own 0x318 + k; any object may use them; an empty / not live entry reads 0
# and a write there does nothing. 0x380 + k (k < 64): New_Var slot k (ue_nv, nv_code). Any other: reads 0.
user_entry:
        stwu r1, -0x40(r1)
        mflr r0
        stw r0, 0x44(r1)
        stmw r27, 0x1C(r1)
        stfs f1, 0x18(r1)
        mr r31, r3
        rlwinm r30, r4, 0, 22, 31
        mr r29, r5""" % dict(n=OBJ_N, size=OBJ_SIZE, last=OBJ_SIZE - 4, ubase=USER_BASE, var_back=VAR_ENTRY + 4)
        + fl('r31', 'ue_zero') + """
        cmplwi r30, %(u20)d
        blt ue_var
        cmplwi r30, %(u30)d
        blt ue_timer
        beq ue_kin
        cmplwi r30, %(u31)d
        beq ue_track
        cmplwi r30, %(u33)d
        ble ue_speed
        cmplwi r30, %(u36)d
        bgt ue_shared
        cmpwi r29, 0                    # team ids: read only
        bne ue_out
        mr r3, r31
        bl acc_of""" % U + fl('r3', 'ue_zero') + """
        lwz r3, 0x6C(r3)                # team module""" + fl('r3', 'ue_zero') + """
        addi r12, r30, -%(u34)d          # (index - 0x334) * 0x10 + 8: main / hurt / attack team id
        slwi r12, r12, 4
        addi r12, r12, 8
        lwzx r3, r3, r12
        bl i2f
        b ue_out
ue_var:
        addi r28, r30, -%(ubase)d
        slwi r28, r28, 2
        addi r28, r28, 0x60
        b ue_slot
ue_timer:
        addi r28, r30, -%(u20)d
        slwi r28, r28, 2
        addi r28, r28, 0x20
ue_slot:
        mr r3, r31
        mr r4, r29                      # writing creates the object's entry
        bl obj_find
        cmpwi r3, 0
        beq ue_zero
        cmpwi r29, 0
        bne ue_slot_w
        lfsx f1, r3, r28
        b ue_out
ue_slot_w:
        lfs f1, 0x18(r1)
        stfsx f1, r3, r28
        b ue_out
ue_track:
        mr r3, r31
        mr r4, r29
        bl obj_find
        mr. r28, r3
        beq ue_zero
        cmpwi r29, 0
        bne ue_track_w
        lwz r3, 8(r28)
        bl i2f
        b ue_out
ue_track_w:
        lfs f1, 0x18(r1)
        bl f2i
        stw r3, 8(r28)
        b ue_out
ue_kin:
        mr r3, r31
        bl acc_of""" % U + fl('r3', 'ue_zero') + """
        lwz r3, 0x34(r3)                # KineticModule""" + fl('r3', 'ue_zero') + """
        mr r28, r3
        cmpwi r29, 0
        bne ue_kin_w
        lwz r3, 0x11C(r28)              # current kinetic type
        bl i2f
        b ue_out
ue_kin_w:
        lfs f1, 0x18(r1)
        bl f2i
        mr r4, r3
        mr r3, r28""" + vcall(0xEC) + """   # set the kinetic type (as Set_Kinetic_Handler: op 0)
        b ue_out
ue_speed:
        cmpwi r29, 0
        bne ue_out
        mr r3, r31
        bl acc_of""" + fl('r3', 'ue_zero') + """
        lwz r3, 0x34(r3)""" + fl('r3', 'ue_zero') + """
        li r4, -1""" + vcall(0xA4) + """   # sum of the enabled energies' speed: r3 x, r4 y (float bits)
        stw r3, 0x10(r1)
        stw r4, 0x14(r1)
        cmplwi r30, 0x332
        bne ue_sp_y
        lfs f1, 0x10(r1)
        b ue_out
ue_sp_y:
        lfs f1, 0x14(r1)
        b ue_out
ue_shared:                              # 0x340 + 8*s + k: fighter table entry s's variable 24 + k
        addi r28, r30, -%(u40)d
        cmplwi r28, 0x40                # (0x337-0x33F: negative, so unsigned huge)
        bge ue_nv_far                   # 0x380-0x3BF: New_Var's (nv_code); the rest reads 0 there
        srwi r27, r28, 3                # s
        rlwinm r28, r28, 2, 27, 29      # 4 * k
        addi r28, r28, 0xC0             # vars[24 + k] in the entry (+0x60 + 4 * (24 + k), as ue_var)
        lis r12, %(fha)d
        lwz r12, %(flo)d(r12)""" % U + fl('r12', 'ue_zero') + """
        lwz r12, 0(r12)                 # fighter table: +0 entries, +8 count""" + fl('r12', 'ue_zero') + """
        lwz r11, 8(r12)
        cmplw r27, r11
        bge ue_zero
        lwz r12, 0(r12)""" + fl('r12', 'ue_zero') + """
        mulli r11, r27, %(fsize)d
        add r12, r12, r11
        lbz r11, 0x1E(r12)              # live when >= 4
        cmplwi r11, 4
        blt ue_zero
        lwz r12, 0xC(r12)               # its accessor""" % U + fl('r12', 'ue_zero') + """
        lwz r31, 0x28(r12)              # its WorkModule: ue_slot finds / creates that fighter's entry""" + fl('r31', 'ue_zero') + """
        b ue_slot
ue_zero:
        lis r12, zero@ha
        lfs f1, zero@l(r12)
ue_out:
        cmpwi r29, 0
        beq ue_ret
        lfs f1, 0x18(r1)
ue_ret:
        lmw r27, 0x1C(r1)
        lwz r0, 0x44(r1)
        mtlr r0
        addi r1, r1, 0x40
        blr

# --- WorkModule set up / reused: forget its entry --------------------------------------------------
hk_wmreset:
        lwz r3, 0x28(r31)               # the WorkModule about to be reset
        lis r10, objs@ha
        addi r10, r10, objs@l
        li r0, %(n)d
        mtctr r0
wr_loop:
        lwz r0, 0(r10)
        cmplw r0, r3
        bne wr_next
        li r0, 0
        stw r0, 0(r10)
        stw r0, 8(r10)                  # no tracking
wr_next:
        addi r10, r10, %(size)d
        bdnz wr_loop
        stwu r1, -0x90(r1)              # and its threads (STATE_RESET frees a CALL state: save all)
        mflr r0
        stw r0, 0x94(r1)
        stmw r3, 0x10(r1)
        mfcr r0
        stw r0, 0x88(r1)
        mr r3, r31
        li r4, -1
        li r5, 0
        bl thread_drop
        lwz r0, 0x88(r1)
        mtcrf 0xFF, r0
        lmw r3, 0x10(r1)
        lwz r0, 0x94(r1)
        mtlr r0
        addi r1, r1, 0x90
        b 0x%(wm_back)08X

# --- every object, every frame it moves (after its ACMD): timers, tracking --------------------------
hk_frame:
        stwu r1, -0x60(r1)
        stmw r26, 0x28(r1)
        lwz r29, 4(r31)                 # accessor (r31 = MotionModule)""" % dict(U, n=OBJ_N, size=OBJ_SIZE, wm_back=WM_RESET + 4)
        + fl('r29', 'hf_out') + """
        lwz r28, 0x28(r29)              # WorkModule""" + fl('r28', 'hf_out') + """
        mr r3, r28
        mr r4, r29
        bl acc_put
        mr r3, r28
        li r4, 0
        bl obj_find
        mr. r30, r3
        beq hf_out
        stw r29, 4(r30)
        lis r12, one@ha
        lfs f2, one@l(r12)
        lfs f3, zero@l(r12)
        li r11, 0x20
hf_timer:
        lfsx f1, r30, r11
        fcmpu cr0, f1, f3
        ble hf_tnext
        fsubs f1, f1, f2
        fcmpu cr0, f1, f3
        bge hf_tset
        fmr f1, f3
hf_tset:
        stfsx f1, r30, r11
hf_tnext:
        addi r11, r11, 4
        cmpwi r11, 0x60
        blt hf_timer
        lwz r12, 8(r30)
        cmpwi r12, 0
        beq hf_out
        blt hf_go                       # < 0: until stopped
        addi r12, r12, -1               # (not r0: addi rD, r0, n is li)
        stw r12, 8(r30)
hf_go:
        mr r3, r30
        mr r4, r29
        bl track_step
hf_out:
        lmw r26, 0x28(r1)
        addi r1, r1, 0x60
        li r0, 1
        b 0x%(frame_back)08X
""" % dict(frame_back=FRAME_HOOK + 4))
    track_code(a)


def track_code(a):
    fl = lambda reg, fail: chk_t(reg, 'r0', fail)     # noqa: E731
    # frame: 0x10/0x14 current v, 0x18/0x1C target delta, 0x20/0x24 new v, 0x28 args, 0x30 words,
    # 0x40 ctx (+4 accessor), 0x48 best d2; r31 entry, r30 accessor, r29 KineticModule, r28 posture,
    # r27 owner ID, r26 self is a fighter, r25 count, r24 entries, r23 energy 0 (weapons), r22 found
    a.asm("""
# --- Track_Target command: (Frames, Speed, TurnRate, Range, Mode) ------------------------------------
h_track:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r28, 0x1C(r1)
        mr r31, r5
        mr r30, r7
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq ht_step""" + fl('r3', 'ht_step') + """
        lwz r3, 0x28(r3)""" + fl('r3', 'ht_step') + """
        li r4, 1
        bl obj_find
        mr. r29, r3
        beq ht_step
        lwz r0, 0(r30)
        stw r0, 8(r29)                  # frames
        lfs f1, 4(r30)
        stfs f1, 0xC(r29)               # speed
        lfs f1, 0xC(r30)                # range -> squared
        fmuls f1, f1, f1
        stfs f1, 0x18(r29)
        lwz r0, 0x10(r30)
        lwz r11, 0x14(r30)              # TargetOwner -> mode bit 0x100
        cmpwi r11, 0
        beq ht_noown
        ori r0, r0, 0x100
ht_noown:
        lwz r11, 0x18(r30)              # TargetTeammates -> mode bit 0x200
        cmpwi r11, 0
        beq ht_notm
        ori r0, r0, 0x200
ht_notm:
        stw r0, 0x1C(r29)               # mode
        li r0, 0
        stw r0, 0xE4(r29)               # no-gravity: nothing set yet
        lfs f1, 8(r30)                  # turn rate (degrees)
        lis r12, zero@ha
        lfs f0, zero@l(r12)
        lfs f2, snap@l(r12)
        stfs f2, 0x10(r29)              # cos < -1.5: turn at once
        fcmpu cr0, f1, f0
        ble ht_step
        lfs f3, deg180@l(r12)
        fcmpu cr0, f1, f3
        bge ht_step
        lfs f3, deg2rad@l(r12)
        fmuls f1, f1, f3                # x (radians)
        fmuls f2, f1, f1                # x^2
        lfs f4, one@l(r12)
""" + horner('f5', 'f2', [72, 42, 20, 6]) + """
        fmuls f5, f5, f1                # sin x = x (1 - x2/6 (1 - x2/20 (...)))
        stfs f5, 0x14(r29)
""" + horner('f5', 'f2', [56, 30, 12, 2]) + """
        stfs f5, 0x10(r29)              # cos x
ht_step:
        lwz r0, 8(r31)
        cmpwi r0, -1
        bne ht_out
        lwz r11, 4(r31)
        addi r11, r11, 32               # 8 words
        stw r11, 4(r31)
ht_out:
        li r3, 2
        lmw r28, 0x1C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- track_step(r3 entry, r4 accessor): steer toward the nearest other fighter ------------------------
track_step:
        stwu r1, -0x90(r1)
        mflr r0
        stw r0, 0x94(r1)
        stmw r19, 0x58(r1)
        mr r31, r3
        mr r30, r4
        li r21, -1                      # reflected: the original owner (the only target, if live)
        li r19, -1                      # this object's attack team (team module +0x28), -1 = none / ignore
        lwz r0, 0x1C(r31)
        andi. r0, r0, 0x200             # TargetTeammates: teammates are targets too
        bne ts_noteam
        lwz r3, 0x6C(r30)""" + fl('r3', 'ts_noteam') + """
        lwz r19, 0x28(r3)
ts_noteam:
        lwz r29, 0x34(r30)""" + fl('r29', 'ts_out') + """
        lwz r28, 0x18(r30)""" + fl('r28', 'ts_out') + """
        li r27, -1
        li r26, 0
        lis r12, %(fh)d
        lwz r12, %(fl)d(r12)""" % dict(fh=ha(FIGHTERS), fl=lo(FIGHTERS)) + fl('r12', 'ts_out') + """
        lwz r12, 0(r12)""" + fl('r12', 'ts_out') + """
        lwz r25, 8(r12)
        lwz r24, 0(r12)""" + fl('r24', 'ts_out') + """
        cmplwi r25, 16
        bgt ts_out
        li r11, 0
ts_self:
        cmpw r11, r25
        bge ts_self_done
        mulli r12, r11, %(fe)d
        add r12, r24, r12
        lwz r0, 0xC(r12)
        cmplw r0, r30
        bne ts_self_next
        li r26, 1
ts_self_next:
        addi r11, r11, 1
        b ts_self
ts_self_done:
        cmpwi r26, 0
        bne ts_vel
        lwz r3, 0x68(r30)               # a weapon: its owner (LinkModule link 0's object ID)""" % dict(fe=FIGHTER_ENTRY)
        + fl('r3', 'ts_vel') + """
        mr r22, r3
        li r4, 0""" + vcall(0x5C) + """
        cmpwi r3, 0
        beq ts_vel
        mr r3, r22
        li r4, 0
        li r5, 1""" + vcall(0x6C) + """
        mr r27, r3
        lwz r3, 0x6C(r30)               # reflected? the current owner (+0x34: the reflector, after a
                                        # reflect) differs from link 0's (the original owner)""" + fl('r3', 'ts_vel') + """
        lwz r3, 0x34(r3)
        cmpw r3, r27
        beq ts_ownbit
        lis r0, 0x5000                  # (no object)
        cmpw r3, r0
        beq ts_ownbit
        mr r21, r27                     # go for the original owner; skip the reflector
        mr r27, r3
        b ts_vel
ts_ownbit:
        lwz r0, 0x1C(r31)               # TargetOwner: the owner is a target like any other
        andi. r0, r0, 0x100
        beq ts_vel
        li r27, -1
ts_vel:
        cmpwi r26, 0
        beq ts_vel_w
        mr r3, r29
        li r4, -1""" + vcall(0xA4) + """   # fighter: speed of all energies
        stw r3, 0x10(r1)
        stw r4, 0x14(r1)
        b ts_find
ts_vel_w:
        mr r3, r29
        li r4, 0""" + vcall(0x54) + """   # weapon: energy 0 (its own movement)""" + fl('r3', 'ts_out') + """
        mr r23, r3
        lwz r0, 0(r23)
        stw r0, 0x10(r1)
        lwz r0, 4(r23)
        stw r0, 0x14(r1)
ts_find:
        li r22, 0
        li r11, 0
        li r20, 0                       # r20 = 1: first pass, the original owner only (any distance)
        cmpwi r21, -1
        beq ts_floop
        li r20, 1
ts_floop:
        cmpw r11, r25
        bge ts_fdone
        mulli r12, r11, %(fe)d
        add r12, r24, r12
        addi r11, r11, 1
        lbz r0, 0x1E(r12)
        cmplwi r0, 4
        blt ts_floop
        lwz r0, 0(r12)
        cmpwi r20, 0
        beq ts_any
        cmpw r0, r21
        bne ts_floop
        b ts_id_ok
ts_any:
        cmpw r0, r27
        beq ts_floop
ts_id_ok:
        lwz r10, 0xC(r12)
        cmplw r10, r30
        beq ts_floop""" % dict(fe=FIGHTER_ENTRY) + fl('r10', 'ts_floop') + """
        cmpwi r19, -1
        beq ts_team_ok
        lwz r9, 0x6C(r10)               # target's team module: its hurt team (+0x18) = our attack team ->
        cmpwi r9, 0                     # a teammate the game won't let us hit (team attack off): skip
        beq ts_team_ok
        lwz r9, 0x18(r9)
        cmpw r9, r19
        beq ts_floop
ts_team_ok:
        lwz r10, 0x18(r10)""" + fl('r10', 'ts_floop') + """
        lfs f1, 0x10(r10)
        lfs f2, 0x10(r28)
        fsubs f1, f1, f2                # dx
        lfs f2, 0x14(r10)
        lfs f3, 0x14(r28)
        fsubs f2, f2, f3                # dy
        lwz r0, 0x1C(r31)
        andi. r0, r0, 1
        beq ts_d2
        lis r12, zero@ha
        lfs f2, zero@l(r12)
ts_d2:
        fmuls f3, f1, f1
        fmadds f3, f2, f2, f3           # d2
        cmpwi r20, 0
        bne ts_take                     # the original owner: whatever the range
        lfs f4, 0x18(r31)               # range squared (0 = any)
        lis r12, zero@ha
        lfs f5, zero@l(r12)
        fcmpu cr0, f4, f5
        ble ts_inrange
        fcmpu cr0, f3, f4
        bgt ts_floop
ts_inrange:
        cmpwi r22, 0
        beq ts_take
        lfs f4, 0x48(r1)
        fcmpu cr0, f3, f4
        bge ts_floop
ts_take:
        li r22, 1
        stfs f3, 0x48(r1)
        stfs f1, 0x18(r1)
        stfs f2, 0x1C(r1)
        b ts_floop
ts_fdone:
        cmpwi r22, 0
        bne ts_found
        cmpwi r20, 0
        beq ts_out
        li r20, 0                       # the original owner isn't there: the nearest other than the reflector
        li r11, 0
        b ts_floop
ts_found:
        lfs f1, 0x48(r1)                # d^ = d / |d|
        bl fsqrt
        lis r12, tiny@ha
        lfs f0, tiny@l(r12)
        fcmpu cr0, f1, f0
        blt ts_out
        lfs f2, 0x18(r1)
        lfs f3, 0x1C(r1)
        fdivs f6, f2, f1                # f6, f7 = d^
        fdivs f7, f3, f1
        stfs f6, 0x20(r1)
        stfs f7, 0x24(r1)
        lfs f2, 0x10(r1)                # |v|
        lfs f3, 0x14(r1)
        fmuls f1, f2, f2
        fmadds f1, f3, f3, f1
        bl fsqrt
        stfs f1, 0x4C(r1)
        lfs f6, 0x20(r1)
        lfs f7, 0x24(r1)
        lfs f8, 0xC(r31)                # speed (0 = keep |v|)
        lis r12, zero@ha
        lfs f0, zero@l(r12)
        fcmpu cr0, f8, f0
        bgt ts_spd
        fmr f8, f1
ts_spd:
        lis r12, tiny@ha
        lfs f0, tiny@l(r12)
        fcmpu cr0, f1, f0
        blt ts_dir_d                    # not moving: straight at the target
        lfs f2, 0x10(r1)
        lfs f3, 0x14(r1)
        fdivs f2, f2, f1                # f2, f3 = v^
        fdivs f3, f3, f1
        lfs f4, 0x10(r31)               # cos(turn)
        lfs f5, snap@l(r12)
        fcmpu cr0, f4, f5
        blt ts_dir_d
        fmuls f9, f2, f6                # dot
        fmadds f9, f3, f7, f9
        fcmpu cr0, f9, f4
        bge ts_dir_d
        lfs f5, 0x14(r31)               # sin(turn), signed by cross
        fmuls f10, f2, f7               # cross = vx dy - vy dx
        fmuls f11, f3, f6
        fsubs f10, f10, f11
        lis r12, zero@ha
        lfs f0, zero@l(r12)
        fcmpu cr0, f10, f0
        bge ts_rot
        fneg f5, f5
ts_rot:
        fmuls f6, f2, f4                # (vx c - vy s, vx s + vy c)
        fmuls f11, f3, f5
        fsubs f6, f6, f11
        fmuls f7, f2, f5
        fmadds f7, f3, f4, f7
ts_dir_d:
        fmuls f6, f6, f8
        fmuls f7, f7, f8
        stfs f6, 0x20(r1)
        stfs f7, 0x24(r1)
        stfs f8, 0x4C(r1)
        cmpwi r26, 0
        bne ts_fighter
        stfs f6, 0(r23)                 # weapon: its own movement energy
        lwz r0, 0x1C(r31)
        andi. r0, r0, 1
        bne ts_out
        stfs f7, 4(r23)
        b ts_out
ts_fighter:""" + kcall(KINETIC_W, [0x11, 3, ('f', 0x20), 0]) + kcall(KINETIC_W, [0x10, 3, 0, 0])
        + kcall(KINETIC_W, [0xB, 3]) + """
        lwz r0, 0x1C(r31)
        andi. r0, r0, 1
        bne ts_face
        lwz r0, 0x1C(r31)
        andi. r0, r0, 4                 # no gravity: put back what gravity took since the last frame
        beq ts_vy                       # (the gravity energy's own acceleration and limit are left alone,
        lwz r0, 0xE4(r31)               # so nothing has to be restored when tracking ends)
        cmpwi r0, 0
        beq ts_vy""" + kcall(KINETIC_FW, [0xB, 1]) + """
        lfs f2, 0xE0(r31)               # set last frame - now = what gravity took
        fsubs f2, f2, f1
        lis r12, zero@ha
        lfs f0, zero@l(r12)
        fcmpu cr0, f2, f0
        bge ts_gpos
        fmr f2, f0
ts_gpos:
        lfs f0, gmax@l(r12)
        fcmpu cr0, f2, f0
        ble ts_gok
        fmr f2, f0
ts_gok:
        lfs f3, 0x24(r1)
        fadds f3, f3, f2
        stfs f3, 0x24(r1)
ts_vy:
        lwz r0, 0x24(r1)
        stw r0, 0xE0(r31)
        li r0, 1
        stw r0, 0xE4(r31)""" + kcall(KINETIC_W, [0x11, 1, ('f', 0x24)]) + kcall(KINETIC_W, [0xB, 1]) + """
ts_face:
        lwz r0, 0x1C(r31)
        andi. r0, r0, 2
        beq ts_out
        lfs f1, 0x18(r1)
        lfs f2, 0x60(r28)               # facing
        fmuls f1, f1, f2
        lis r12, zero@ha
        lfs f0, zero@l(r12)
        fcmpu cr0, f1, f0
        bge ts_out""" + kcall(POSTURE_W, [0x2710]) + kcall(POSTURE_W, [0x2]) + """
ts_out:
        lmw r19, 0x58(r1)
        lwz r0, 0x94(r1)
        mtlr r0
        addi r1, r1, 0x90
        blr
half:
        .float 0.5
onehalf:
        .float 1.5
tiny:
        .float 0.0001
snap:
        .float -2.0
deg180:
        .float 180.0
deg2rad:
        .float 0.017453292
gmax:                                   # no-gravity tracking: the most it puts back a frame (gravity: < 0.2;
        .float 1.0                      # more means landing or a status change reset the speed)
obj_next:
        .word 0
""" + ''.join("k_%d:\n        .float %r\n" % (d, 1.0 / d) for d in (72, 42, 20, 6, 56, 30, 12, 2)))


def horner(fd, fx2, ds):
    """fd = 1 - x2/d0 (1 - x2/d1 (... (1 - x2/dn))) for ds = [dn ... d0] (innermost first); f4 = 1.0;
    the constants 1/d are inline-loaded from k_<d> labels (made by consts_for)"""
    out = ["        fmr %s, f4" % fd]
    for d in ds:
        out += ["        lfs f6, k_%d@l(r12)" % d, "        fmuls f6, f6, %s" % fx2, "        fmuls f6, f6, %s" % fd,
                "        fsubs %s, f4, f6" % fd]
    return "\n".join(out)


def thread_code(a):
    """Thread_Start / Thread_Stop handlers, the per-object thread runner (step entries), thread_drop"""
    fl = lambda reg, fail: chk_t(reg, 'r0', fail)     # noqa: E731
    D = dict(n=THREAD_N, size=THREAD_SIZE, reset=STATE_RESET, interp=INTERP, stop=THREAD_STOP_BIT >> 16)
    a.asm("""
# --- thread_drop(r3 accessor, r4 ID (-1 = all), r5 running state or 0): stop matching threads;
#     the one whose state is r5 (it's running this command) is only marked to stop after this frame
thread_drop:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stmw r28, 0x10(r1)
        mr r31, r3
        mr r30, r4
        mr r29, r5
        lis r28, threads@ha
        addi r28, r28, threads@l
        li r0, %(n)d
        stw r0, 8(r1)
td_loop:
        lwz r0, 0(r28)
        cmplw r0, r31
        bne td_next
        cmpwi r30, -1
        beq td_hit
        lwz r0, 8(r28)
        cmpw r0, r30
        bne td_next
td_hit:
        addi r3, r28, 0x10
        cmplw r3, r29
        bne td_free
        lwz r0, 0xC(r28)
        oris r0, r0, %(stop)d
        stw r0, 0xC(r28)
        b td_next
td_free:
        bl 0x%(reset)08X
        li r0, 0
        stw r0, 0(r28)
td_next:
        addi r28, r28, %(size)d
        lwz r12, 8(r1)
        addi r12, r12, -1               # (not r0: addi rD, r0, n is li)
        stw r12, 8(r1)
        cmpwi r12, 0
        bne td_loop
        lmw r28, 0x10(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# --- Thread_Start(Offset, ID, Flags){ block ... Script_End }: r3 accessor, r4 table, r5 state, r6 ctx, r7 params
h_thread:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r26, 0x18(r1)
        mr r31, r3
        mr r30, r4
        mr r29, r5
        mr r28, r7
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq th_step""" % D + fl('r31', 'th_step') + """
        lwz r27, 4(r28)                 # ID
        lis r26, threads@ha
        addi r26, r26, threads@l
        li r11, %(n)d
th_find:                                # this object's thread with this ID: restart it
        lwz r0, 0(r26)
        cmplw r0, r31
        bne th_fnext
        lwz r0, 8(r26)
        cmpw r0, r27
        bne th_fnext
        addi r3, r26, 0x10
        cmplw r3, r29                   # (not from inside itself)
        beq th_step
        bl 0x%(reset)08X
        b th_take
th_fnext:
        addi r26, r26, %(size)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne th_find
        lis r26, threads@ha
        addi r26, r26, threads@l
        li r11, %(n)d
th_free:
        lwz r0, 0(r26)
        cmpwi r0, 0
        beq th_take
        addi r26, r26, %(size)d
        addi r11, r11, -1
        cmpwi r11, 0
        bne th_free
        b th_step                       # all taken: not started
th_take:
        stw r31, 0(r26)
        stw r30, 4(r26)
        stw r27, 8(r26)
        lwz r0, 8(r28)
        rlwinm r0, r0, 0, 1, 31
        stw r0, 0xC(r26)
        li r0, 0
        li r11, 0x34
th_zero:
        addi r12, r26, 0x10
        stwx r0, r12, r11
        addi r11, r11, -4
        cmpwi r11, 0
        bge th_zero
        li r0, -1
        stw r0, 0x18(r26)               # state +8: running
        lwz r3, 4(r29)
        addi r3, r3, 16                 # the block's first command (after Thread_Start's 4 words)
        stw r3, 0x10(r26)
        stw r3, 0x14(r26)
th_step:
        lwz r3, 8(r29)
        cmpwi r3, -1
        bne th_ret
        lwz r0, 0(r28)                  # jump over the block (as True)
        slwi r0, r0, 2
        lwz r11, 4(r29)
        add r11, r11, r0
        stw r11, 4(r29)
        li r3, 2
th_ret:
        lmw r26, 0x18(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- Thread_Stop(ID)
h_thread_stop:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stw r31, 0x1C(r1)
        mr r31, r5
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq ts2_step
        lwz r4, 0(r7)
        mr r5, r31
        bl thread_drop
ts2_step:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne ts2_ret
        lwz r11, 4(r31)
        addi r11, r11, 8
        stw r11, 4(r31)
        li r3, 2
ts2_ret:
        lwz r31, 0x1C(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr

# --- thread_run(r3 accessor): one frame of each of its threads ---------------------------------------
thread_run:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r27, 0x1C(r1)
        mr r31, r3
        li r30, 0                       # in hitlag?
        lwz r3, 0x48(r31)               # StopModule""" % D + fl('r3', 'tr_go') + """
        lbz r30, 0x10(r3)
tr_go:
        lis r29, threads@ha
        addi r29, r29, threads@l
        li r28, %(n)d
tr_loop:
        lwz r0, 0(r29)
        cmplw r0, r31
        bne tr_next
        lwz r0, 0xC(r29)
        andi. r0, r0, 1                 # Flags 1: also in hitlag
        bne tr_run
        cmpwi r30, 0
        bne tr_next
tr_run:
        lwz r3, 4(r29)
        mr r4, r31
        addi r5, r29, 0x10
        li r6, 1
        lis r12, one@ha
        lfs f1, one@l(r12)
        lfs f2, zero@l(r12)
        bl 0x%(interp)08X
        lwz r0, 0x14(r29)               # state +4 = 0: ended (Script_End)
        cmpwi r0, 0
        beq tr_end
        cmpwi r3, 0
        beq tr_end
        lwz r0, 0xC(r29)
        rlwinm. r0, r0, 0, 0, 0         # stop bit (Thread_Stop from inside itself)
        beq tr_next
tr_end:
        addi r3, r29, 0x10
        bl 0x%(reset)08X
        li r0, 0
        stw r0, 0(r29)
tr_next:
        addi r29, r29, %(size)d
        addi r28, r28, -1
        cmpwi r28, 0
        bne tr_loop
        lmw r27, 0x1C(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr
""" % D)
    for k, h in enumerate(STEP_HOOKS):
        a.asm("""
hk_step%(k)d:                            # object step entry: r4 -> accessor; save everything, run its threads
        stwu r1, -0xA0(r1)
        mflr r0
        stw r0, 0xA4(r1)
        stmw r3, 0x10(r1)
        mfcr r0
        stw r0, 0x88(r1)
        stfd f1, 0x90(r1)
        stfd f2, 0x98(r1)""" % dict(k=k) + fl('r4', 'hs%d_out' % k) + """
        lwz r3, 0(r4)""" + fl('r3', 'hs%d_out' % k) + """
        bl thread_run
hs%(k)d_out:
        lfd f1, 0x90(r1)
        lfd f2, 0x98(r1)
        lwz r0, 0x88(r1)
        mtcrf 0xFF, r0
        lmw r3, 0x10(r1)
        lwz r0, 0xA4(r1)
        mtlr r0
        addi r1, r1, 0xA0
        stwu r1, -0x38(r1)
        b 0x%(back)08X
""" % dict(k=k, back=h + 4))


def input_code(a):
    """Input_Compare / Input_Get / Input_Set / Hit_Reset (docs/acmd-extra-commands.md "Inputs"). A self button
    (inputs 0-15, target 0) is read with the game's own ControlModule(0x2712 held / 0x2710 pressed, MSC
    button), as fighter MSC does; anything else, and every write, goes through position_vars_cave.py's input
    variables (0x0F000100 + 0x20 * target + input; 32 / 33 the raw X ones, 0x0F000260 + 2 * target)."""
    a.asm("""
# --- in_id(r4 target, r5 input) -> r4 variable ID (0 = none); leaf: r0 -------------------------------------
in_id:
        cmplwi r4, 10
        bgt iid_none
        cmplwi r5, 0x20
        blt iid_q
        cmplwi r5, 0x22
        bge iid_none
        slwi r4, r4, 1
        add r4, r4, r5
        addis r4, r4, 0x%(hi)04X
        addi r4, r4, 0x%(raw)X
        blr
iid_q:
        slwi r4, r4, 5
        add r4, r4, r5
        addis r4, r4, 0x%(hi)04X
        addi r4, r4, 0x%(q)X
        blr
iid_none:
        li r4, 0
        blr

# --- in_read(r3 accessor, r4 target, r5 input) -> f1 ---------------------------------------------------
# frame: 0x28 args {words, count}, 0x30 words, 0x40 ctx (+4 accessor); r31 button, r30 accessor,
# r29 target, r28 input, r27 op
in_read:
        stwu r1, -0x60(r1)
        mflr r0
        stw r0, 0x64(r1)
        stmw r27, 0x4C(r1)
        mr r30, r3
        mr r29, r4
        mr r28, r5""" % dict(hi=0x0F00, raw=(INPUT_RAW & 0xFFFF) - 0x20, q=INPUT_BASE & 0xFFFF) + chk_t('r30', 'r0', 'ir_zero') + """
        cmpwi r29, 0
        bne ir_var
        cmplwi r28, 0x10
        bge ir_var
        li r27, 0x2712                  # 0-7 held, 8-15 pressed
        cmplwi r28, 8
        blt ir_held
        li r27, 0x2710
        addi r28, r28, -8
ir_held:
        lis r12, ir_btns@ha
        addi r12, r12, ir_btns@l
        lbzx r31, r12, r28
        bl ir_btn
        cmpwi r3, 0
        bne ir_one
        cmpwi r28, 6                    # taunt side: d-pad left or right
        bne ir_zero
        li r31, 8
        bl ir_btn
        cmpwi r3, 0
        beq ir_zero
ir_one:
        lis r12, one@ha
        lfs f1, one@l(r12)
        b ir_out
ir_var:
        mr r4, r29
        mr r5, r28
        bl in_id
        cmpwi r4, 0
        beq ir_zero
        lwz r3, 0x28(r30)""" + chk_t('r3', 'r0', 'ir_zero') + vcall(0x44) + """
        b ir_out
ir_zero:
        lis r12, zero@ha
        lfs f1, zero@l(r12)
ir_out:
        lmw r27, 0x4C(r1)
        lwz r0, 0x64(r1)
        mtlr r0
        addi r1, r1, 0x60
        blr
ir_btn:                                 # (in in_read's frame) r3 = ControlModule(r27, r31) of r30
        mflr r0
        stw r0, 0x48(r1)
        li r0, 0
        stw r0, 0x40(r1)
        stw r30, 0x44(r1)
        stw r27, 0x30(r1)
        stw r31, 0x34(r1)
        addi r0, r1, 0x30
        stw r0, 0x28(r1)
        li r0, 2
        stw r0, 0x2C(r1)
        addi r3, r1, 0x40
        addi r4, r1, 0x28
        bl 0x%(control)08X
        lwz r0, 0x48(r1)
        mtlr r0
        blr
ir_btns:                                # input -> MSC button: attack, special, jump, shield, grab (9), d-pad
        .word 0x00010203                # up (5), left (7; right 8 too), down (6)
        .word 0x09050706

# --- Input_Compare(Target, Input, Method, Value): state +0xC = input Method Value (as Float_Var_Compare) --
h_icmp:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r29, 0x24(r1)
        mr r31, r5
        mr r30, r7
        lwz r4, 0(r30)
        lwz r5, 4(r30)
        bl in_read
        lwz r3, 8(r30)
        cmplwi r3, 5
        li r3, 0
        bgt ic_set
        lwz r3, 8(r30)
        lfs f2, 0xC(r30)
        bl 0x%(compare)08X
ic_set:
        stw r3, 0xC(r31)
        li r29, 20                      # 5 words
        b in_step

# --- Input_Get(Target, Input, Variable): float variable Variable (of this object) = the input -----------
h_iget:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r29, 0x24(r1)
        mr r31, r5
        mr r30, r7
        li r29, 16
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq in_step""" % dict(control=CONTROL_W, compare=COMPARE) + chk_t('r3', 'r0', 'in_step') + """
        stw r3, 0x8(r1)
        lwz r4, 0(r30)
        lwz r5, 4(r30)
        bl in_read
        lwz r3, 0x8(r1)
        lwz r3, 0x28(r3)""" + chk_t('r3', 'r0', 'in_step') + """
        lwz r4, 8(r30)""" + vcall(0x4C) + """
        b in_step

# --- Input_Set(Target, Input, Value): the input variable = Value (forces it) --------------------------------
h_iset:
        stwu r1, -0x30(r1)
        mflr r0
        stw r0, 0x34(r1)
        stmw r29, 0x24(r1)
        mr r31, r5
        mr r30, r7
        li r29, 16
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq in_step""" + chk_t('r3', 'r0', 'in_step') + """
        lwz r3, 0x28(r3)""" + chk_t('r3', 'r0', 'in_step') + """
        lwz r4, 0(r30)
        lwz r5, 4(r30)
        bl in_id
        cmpwi r4, 0
        beq in_step
        lfs f1, 8(r30)""" + vcall(0x4C) + """
in_step:                                # r29 = the command's bytes, r31 = script state
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne in_ret
        lwz r11, 4(r31)
        add r11, r11, r29
        stw r11, 4(r31)
        li r3, 2
in_ret:
        lmw r29, 0x24(r1)
        lwz r0, 0x34(r1)
        mtlr r0
        addi r1, r1, 0x30
        blr

# --- Hit_Reset(): AttackModule(0x2724), "has hit" (+0xC8) back to 0 -------------------------------------
h_hreset:
        stwu r1, -0x60(r1)
        mflr r0
        stw r0, 0x64(r1)
        stmw r29, 0x54(r1)
        mr r31, r5
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq hr_step""" + chk_t('r3', 'r0', 'hr_step') + """
        li r0, 0
        stw r0, 0x40(r1)
        stw r3, 0x44(r1)
        li r0, 0x2724
        stw r0, 0x30(r1)
        addi r0, r1, 0x30
        stw r0, 0x28(r1)
        li r0, 1
        stw r0, 0x2C(r1)
        addi r3, r1, 0x40
        addi r4, r1, 0x28
        bl 0x""" + '%08X' % ATTACK_W + """
hr_step:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne hr_ret
        lwz r11, 4(r31)
        addi r11, r11, 4
        stw r11, 4(r31)
        li r3, 2
hr_ret:
        lmw r29, 0x54(r1)
        lwz r0, 0x64(r1)
        mtlr r0
        addi r1, r1, 0x60
        blr

# --- Hit_Log_Clear(Part): the hit records of the hitboxes of Part (-1: all) cleared ------------------------
# AttackModule (accessor +0x50) +8 is its hit-record set: +0x10 the parts (groups, dein 2 / fighters 20), +0x14
# the groups (0x174 each); a hitbox's part indexes them unchecked (0x02C08848). One group: 0x02C10660(group, its
# current list (+0x130), 0) and, if that isn't it, the list at +0x124, as the game's own clear 0x02C0ECDC does
# for every group (AttackModule vt +0x34's, run on object set-up).
h_hlclear:
        stwu r1, -0x20(r1)
        mflr r0
        stw r0, 0x24(r1)
        stmw r29, 0x14(r1)
        mr r31, r5
        lbz r0, 8(r6)
        cmpwi r0, 0
        beq hl_step""" + chk_t('r3', 'r0', 'hl_step') + """
        lwz r29, 0(r7)
        lwz r30, 0x50(r3)""" + chk_t('r30', 'r0', 'hl_step') + """
        cmpwi r29, 0
        bge hl_part
        addi r3, r30, 8
        bl 0x""" + '%08X' % HIT_CLEAR_ALL + """
        b hl_step
hl_part:
        lwz r0, 0x10(r30)
        cmplw r29, r0
        bge hl_step
        mulli r29, r29, 0x174
        lwz r0, 0x14(r30)
        add r30, r0, r29
        lwz r4, 0x130(r30)
        mr r3, r30
        li r5, 0
        bl 0x""" + '%08X' % HIT_CLEAR_LIST + """
        lwz r0, 0x130(r30)
        addi r4, r30, 0x124
        cmplw r0, r4
        beq hl_step
        mr r3, r30
        li r5, 0
        bl 0x""" + '%08X' % HIT_CLEAR_LIST + """
hl_step:
        lwz r3, 8(r31)
        cmpwi r3, -1
        bne hl_ret
        lwz r11, 4(r31)
        addi r11, r11, 8
        stw r11, 4(r31)
        li r3, 2
hl_ret:
        lmw r29, 0x14(r1)
        lwz r0, 0x24(r1)
        mtlr r0
        addi r1, r1, 0x20
        blr
""")


def hit_code(a):
    """find_copy, the four hit-time hooks, the DI table and the DI stat read"""
    sig = ''.join("""
        lwz r12, %d(r10)
        lwz r8, %d(r5)
        cmplw r8, r12
        bne fc_none""" % (e, d) for e, d in ((4, 0x20), (8, 0x24), (0xC, 0x28), (0x10, 0x2C), (0x2C, 0x3C)))
    a.asm("""
find_copy:                              # r5 = hitbox data (a copy) -> r5 = its extras or 0; uses r8 r10 r12 cr0
        andi. r10, r5, 3
        bne fc_none
        addis r10, r5, -0x1000
        rlwinm. r10, r10, 0, 0, 0
        bne fc_none
        lhz r10, %(tag)d(r5)
        rlwinm r12, r10, 0, 16, 23
        cmplwi r12, %(TAG)d
        bne fc_none
        rlwinm r10, r10, 0, 24, 31
        cmplwi r10, %(entries)d
        bge fc_none
        mulli r10, r10, %(entry)d
        lis r12, table@ha
        addi r12, r12, table@l
        add r10, r12, r10
        lwz r12, 0(r10)
        cmpwi r12, 0
        beq fc_none""" % dict(tag=TAG_OFF, TAG=TAG, entries=ENTRIES, entry=ENTRY) + sig + """
        mr r5, r10
        blr
fc_none:
        li r5, 0
        blr

scale_int:                              # r3 = floor(r3 x f13) (r3 >= 0); uses r0 r12 f0 f12
        lis r12, scratch@ha
        addi r12, r12, scratch@l
        xoris r0, r3, 0x8000
        stw r0, 4(r12)
        lis r0, 0x4330
        stw r0, 0(r12)
        lfd f0, 0(r12)
        lfd f12, 8(r12)                 # 2^52 + 2^31
        fsub f0, f0, f12
        fmul f0, f0, f13
        fctiwz f0, f0
        stfd f0, 0(r12)
        lwz r3, 4(r12)
        blr

hk_stun:                                # victim's hitstun (f28) x HitstunMul; this hit's DI x for the victim
        mfcr r9
        lis r12, dbg@ha
        addi r12, r12, dbg@l
        lwz r10, 52(r12)
        addi r10, r10, 1
        stw r10, 52(r12)
        addi r5, r28, 0x44
        bl find_copy
        lis r12, one@ha
        lfs f9, one@l(r12)              # DI x (1 for any other hit)
        cmpwi r5, 0
        beq st_di
        lis r12, dbg@ha
        addi r12, r12, dbg@l
        lwz r10, 56(r12)
        addi r10, r10, 1
        stw r10, 56(r12)
        lfs f10, 0x14(r5)               # HitstunMul: x it, or a negative one: that many frames more
        fsubs f9, f10, f10              # 0.0 (f9 / f10 are this hook's own: other float registers may be live)
        fcmpu cr1, f10, f9
        blt cr1, st_add
        fmuls f28, f28, f10
        b st_mul
st_add:
        fsubs f28, f28, f10
st_mul:
        lfs f9, 0x28(r5)
st_di:""" + chk_t('r27', 'r12', 'st_out') + """
        lwz r8, 0x28(r27)               # the victim's WorkModule""" + chk_t('r8', 'r12', 'st_out') + """
        bl di_store
st_out:
        mtcrf 0xFF, r9
        stfs f28, 0x30(r30)
        b 0x%(stun_back)08X

di_store:                               # r8 = WorkModule, f9 = DI x; uses r5 r10 r12 f10
        lis r10, di_tab@ha
        addi r10, r10, di_tab@l
        li r5, 0
ds_loop:
        lwz r12, 0(r10)
        cmplw r12, r8
        beq ds_set
        addi r10, r10, 8
        addi r5, r5, 1
        cmpwi r5, %(slots)d
        blt ds_loop
        lis r12, one@ha
        lfs f10, one@l(r12)
        fcmpu cr0, f9, f10
        beqlr                           # x1 and no entry: nothing to keep
        lis r12, di_next@ha
        lwz r5, di_next@l(r12)
        addi r10, r5, 1
        cmpwi r10, %(slots)d
        blt ds_wrap
        li r10, 0
ds_wrap:
        stw r10, di_next@l(r12)
        lis r10, di_tab@ha
        addi r10, r10, di_tab@l
        slwi r5, r5, 3
        add r10, r10, r5
        stw r8, 0(r10)
ds_set:
        stfs f9, 4(r10)
        blr

di_check:                               # from get_float after cmpwi r11, 3 (a b replaces its bnelr): r3 this, r4 id, f1
        bne dc_go
        b 0x%(stat_back)08X                # a fighter stat (category 3): on as before
dc_go:
        cmpwi r11, 2
        bnelr
        rlwinm r12, r4, 0, 8, 31
        cmplwi r12, %(di_id)d
        bnelr
        lis r10, di_tab@ha
        addi r10, r10, di_tab@l
        li r12, %(slots)d
dc_loop:
        lwz r0, 0(r10)
        cmplw r0, r3
        beq dc_found
        addi r10, r10, 8
        addi r12, r12, -1
        cmpwi r12, 0
        bne dc_loop
        blr
dc_found:
        lfs f0, 4(r10)
        fmuls f1, f1, f0
        blr

hk_vstop:                               # victim's hitstop (r20): HitstopFrames, else x HitstopMul
        lis r12, dbg@ha
        addi r12, r12, dbg@l
        lwz r11, 4(r12)
        addi r11, r11, 1
        stw r11, 4(r12)
        stw r20, 0xC(r12)
        addi r5, r28, 0x44
        bl find_copy
        cmpwi r5, 0
        beq vs_out
        lis r12, dbg@ha
        addi r12, r12, dbg@l
        lwz r11, 8(r12)
        addi r11, r11, 1
        stw r11, 8(r12)
        lwz r0, 0x1C(r5)
        cmpwi r0, 0
        ble vs_mul
        mr r20, r0
        b vs_out
vs_mul:
        lfs f13, 0x18(r5)
        mr r3, r20
        bl scale_int
        mr r20, r3
vs_out:
        lis r12, dbg@ha
        addi r12, r12, dbg@l
        stw r20, 16(r12)
        cmpwi r19, 2
        b 0x%(vstop_back)08X

hk_amul:                                # attacker's hitstop before the rate (r3): x SelfHitstopMul
        mfcr r9
        mr r27, r3
        lis r12, dbg@ha
        addi r12, r12, dbg@l
        lwz r11, 20(r12)
        addi r11, r11, 1
        stw r11, 20(r12)
        stw r27, 0x1C(r12)
        addi r5, r30, 0x44
        bl find_copy
        cmpwi r5, 0
        beq am_out
        lis r12, dbg@ha
        addi r12, r12, dbg@l
        lwz r11, 24(r12)
        addi r11, r11, 1
        stw r11, 24(r12)
        mr r8, r5
        lfs f13, 0x20(r8)
        mr r3, r27
        bl scale_int
        mr r27, r3
        lwz r0, 0x24(r8)                # fixed frames: make sure the hitstop path runs (set at HIT_AFIX)
        cmpwi r0, 0
        ble am_out
        cmpwi r27, 0
        bgt am_out
        li r27, 1
am_out:
        lis r12, dbg@ha
        addi r12, r12, dbg@l
        stw r27, 32(r12)
        mtcrf 0xFF, r9
        mr r3, r27
        or. r27, r27, r27
        b 0x%(amul_back)08X

hk_afix:                                # attacker's hitstop after the rate: SelfHitstopFrames
        lwz r27, 0x10(r1)
        mfcr r9
        lis r12, dbg@ha
        addi r12, r12, dbg@l
        lwz r11, 36(r12)
        addi r11, r11, 1
        stw r11, 36(r12)
        stw r27, 0x2C(r12)
        addi r5, r30, 0x44
        bl find_copy
        cmpwi r5, 0
        beq af_out
        lis r12, dbg@ha
        addi r12, r12, dbg@l
        lwz r11, 40(r12)
        addi r11, r11, 1
        stw r11, 40(r12)
        lwz r0, 0x24(r5)
        cmpwi r0, 0
        ble af_out
        mr r27, r0
af_out:
        lis r12, dbg@ha
        addi r12, r12, dbg@l
        stw r27, 48(r12)
        mtcrf 0xFF, r9
        b 0x%(afix_back)08X

di_next:
        .word 0
""" % dict(stun_back=HIT_STUN + 4, vstop_back=HIT_VSTOP + 4, amul_back=HIT_AMUL + 4, afix_back=HIT_AFIX + 4,
           slots=DI_SLOTS, di_id=DI_ID, stat_back=DI_STAT + 4))


def chk_t(reg, tmp, fail):
    """branch to fail unless reg is a word-aligned pointer in 0x10000000-0x8FFFFFFF (temp register tmp)"""
    return """
        addis %(t)s, %(r)s, -0x1000
        rlwinm. %(t)s, %(t)s, 0, 0, 0
        bne %(f)s
        andi. %(t)s, %(r)s, 3
        bne %(f)s""" % dict(t=tmp, r=reg, f=fail)


def mul(src, dst, k, signed=False):
    """copy the float multiplier at src(r5) to dst(r11); <= 0 or NaN -> 1.0 (f0 = 1.0, f2 = 0.0). signed:
    a negative one is kept (HitstunMul: that many frames added), only 0 / NaN -> 1.0"""
    return """
        lfs f1, %s(r5)
        fcmpu cr1, f1, f2
        bgt cr1, er_%s%s
        fmr f1, f0
er_%s:
        stfs f1, %s(r11)""" % (src, k, ("\n        blt cr1, er_%s" % k) if signed else "", k, dst)


def chk(reg, fail):
    """branch to fail unless reg is a word-aligned pointer in 0x10000000-0x8FFFFFFF"""
    return """
        addis r0, %s, -0x1000
        rlwinm. r0, r0, 0, 0, 0
        bne %s
        andi. r0, %s, 3
        bne %s""" % (reg, fail, reg, fail)


def b(at, to):
    off = to - at
    assert -0x2000000 <= off < 0x2000000, (hex(at), hex(to))
    return 0x48000000 | (off & 0x3FFFFFC)


# Sm4shCommand's help for these commands (View > Commands: group, help text and usage examples, each example
# compiling in Sm4shCommand as written) is in acmd_ext_help.py; labels() copies it into param_labels.json.
from acmd_ext_help import EXAMPLES, GROUP, HELP  # noqa: E402


def labels(path):
    """add / update the new commands in tools/Sm4shCommand/param_labels.json (apply_param_labels.py then
    puts them in Sm4shCommand's table, tools/acmd_info.json and Events.cfg; their group, help and examples come
    from acmd_ext_help.py)"""
    import json
    d = json.load(open(path))
    info = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'acmd_info.json')))['commands']
    for name, size, _label, _base in COMMANDS:
        own = {'Track_Target': TRACK_PARAMS, 'Thread_Start': THREAD_PARAMS, 'Thread_Stop': THREAD_STOP_PARAMS,
               'Input_Compare': INPUT_CMP_PARAMS, 'Input_Get': INPUT_GET_PARAMS, 'Input_Set': INPUT_SET_PARAMS,
               'Hit_Reset': [], 'Hit_Log_Clear': HIT_LOG_CLEAR_PARAMS}
        own.update(NEW_PARAMS)           # Variable parameters are type 3: Sm4shCommand shows them as VAR_0, ...
        if name in own:
            e = {'_command': name, '_new': True, '_name': name, '_size': size, '_desc': SM4SHCOMMAND_DESC[name],
                 '_format': [t for _n, t, _d in own[name]]}
            assert len(own[name]) == size - 1
            for k, (pname, _t, desc) in enumerate(own[name]):
                e[str(k)] = {'name': pname, 'desc': desc, 'confidence': 'high'}
            e['_example'] = EXAMPLES.get(name, [])
            e['_group'], e['_help'] = GROUP.get(name), HELP.get(name, [])     # (no entry yet: "New Commands" itself)
            d['%08X' % crc(name)] = e
            continue
        base = '%08X' % BASE_CRC[name]
        bi, bl = info[base], d.get(base, {})
        e = {'_command': name, '_new': True, '_name': name, '_size': size, '_desc': SM4SHCOMMAND_DESC[name],
             '_format': bi['format'] + [t for _n, t, _d in EXTRA_PARAMS]}
        for k, pname in enumerate(bi['syntax']):
            e[str(k)] = dict(bl.get(str(k), {}), name=pname)
            if HV_FIELD0 <= k < HV_FIELD0 + len(HV_FIELDS):     # exe_v43: a variable
                e[str(k)]['desc'] = e[str(k)].get('desc', '').rstrip() + HV_PARAM_DESC[k - HV_FIELD0]
        for k, (pname, _t, desc) in enumerate(EXTRA_PARAMS):
            e[str(len(bi['syntax']) + k)] = {'name': pname, 'desc': desc, 'confidence': 'high'}
        assert len(e['_format']) == size - 1
        e['_example'] = EXAMPLES.get(name, [])
        e['_group'], e['_help'] = GROUP.get(name), HELP.get(name, [])
        d['%08X' % crc(name)] = e
    json.dump(dict(sorted(d.items())), open(path, 'w'), indent=1)


def main():
    if '--labels' in sys.argv:
        labels(sys.argv[sys.argv.index('--labels') + 1])
        return
    a, words, hooks = build()
    out = ['grow:0x%08X' % LIMIT, 'textregion:0x%X' % (NV_LIMIT - 0x02000000), 'grow:0x%08X' % NV_LIMIT]
    out += ['0x%08X=0x%08X' % (CAVE + 4 * i, w) for i, w in enumerate(words)]
    out += ['0x%08X=0x%08X' % (a.part2[0] + 4 * i, w) for i, w in enumerate(a.part2[1])]
    out += ['0x%08X=0x%08X' % (a.part3[0] + 4 * i, w) for i, w in enumerate(a.part3[1])]
    out += ['0x%08X=0x%08X' % (a.part4[0] + 4 * i, w) for i, w in enumerate(a.part4[1])]
    out += ['0x%08X=0x%08X' % (a.part5[0] + 4 * i, w) for i, w in enumerate(a.part5[1])]
    out += ['0x%08X=0x%08X' % (a.part6[0] + 4 * i, w) for i, w in enumerate(a.part6[1])]
    out += ['0x%08X=0x%08X' % kv for kv in sorted(hooks.items())]
    # the vtable words have ADDR32 relocations to the classes' own functions: moved to a dead word, or the loader
    # would write those back over ours
    out += ['reloc:0x%08X-0x%08X=0x%08X' % (w, w + 4, RELOC_DUMMY) for w in sorted(WM_INT_ORIG)]
    print(' '.join(out))
    sys.stderr.write('acmd ext: %d words, %s\n' % (len(words), ', '.join(
        '%s 0x%08X index %d' % (c[0], crc(c[0]), NEW_BASE + i) for i, c in enumerate(COMMANDS))))


if __name__ == '__main__':
    main()
