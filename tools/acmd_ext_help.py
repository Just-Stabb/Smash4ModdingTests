#!/usr/bin/env python3
"""Help for the new ACMD commands (tools/acmd_ext_cave.py) in Sm4shCommand's command list (View > Commands).

Data only: acmd_ext_cave.py --labels puts GROUP, HELP and EXAMPLES into tools/Sm4shCommand/param_labels.json
("_group", "_help", "_example"); make_events_cfg.py writes them to Events.cfg as the command's
"Category: New Commands / GROUP", its "Help:" lines and its "Example:" lines, and GROUP_HELP as "Group:" blocks
(the text shown when a group is picked in the list).

Help lines: "## text" is a heading, "" an empty line, anything else a paragraph / list line. Example lines are
script text that compiles in Sm4shCommand as written ("//" lines are comments, "" separates examples). Keep both
accurate to acmd_ext_cave.py and docs/acmd-extra-commands.md / docs/position-variables.md.
"""

NEW_GROUP = 'New Commands'

# subgroup of each new command (the command list shows them under "New Commands", in SUBGROUPS' order)
SUBGROUPS = ['Hitboxes & hits', 'Fighter state', 'Inputs', 'Position & rotation', 'Animation', 'Targets & tracking',
             'Threads', 'Variables']
GROUP = {}
for _g, _names in (
        ('Hitboxes & hits', ['Extra_Special_Hitbox', 'Extra_Extended_Special_Hitbox', 'Hit_Check', 'Hit_Get',
                             'Hit_Reset', 'Hit_Log_Clear']),
        ('Fighter state', ['Status_Get', 'Status_Set', 'Hitstun_Get', 'Hitstun_Set', 'Hitstop_Set', 'Damage_Get',
                           'Damage_Set', 'Body_State_Set', 'Armor_Set', 'Item_State_Set', 'Stage_Collision_Set',
                           'Leave_Ground_Cancel', 'Gravity_Set']),
        ('Inputs', ['Input_Compare', 'Input_Get', 'Input_Set']),
        ('Position & rotation', ['Position_Get', 'Position_Set', 'Rotation_Get', 'Rotation_Set', 'Joint_Position_Get']),
        ('Animation', ['Motion_Get', 'Motion_Set', 'Animation_Rate_Set']),
        ('Targets & tracking', ['Track_Target', 'Last_Hit_Get', 'Target_Slot_Get']),
        ('Threads', ['Thread_Start', 'Thread_Stop']),
        ('Variables', ['New_Var'])):
    for _n in _names:
        GROUP[_n] = _g

# --- shared text ---------------------------------------------------------------------------------------------------
NEEDS = ('Needs the patched cross_f.rpx (tools/acmd_ext_cave.py, part of the standard build). Without it a script '
         'that uses this command won\'t load properly: ship the executable with any script that uses it.')
TARGETS = [
    '## Target',
    '- 0: this object: the fighter, or the article (projectile) whose script it is.',
    '- 1: the nearest opponent (by X/Y distance; teams aren\'t considered).',
    '- 2: the last fighter this one hit (its current attack\'s newest hit; once the attack is over, a fighter whose '
    'last attacker is this one).',
    '- 3-10: player slots 1-8 (Target = 2 + slot: player 1 is 3, player 2 is 4, ...).',
    '- 11: the last fighter that hit this one (the game\'s own record, its projectiles included).',
    'Targets 1, 2 and 11 are worked out from a fighter\'s own script; from an article\'s script they find nobody. A '
    'target that isn\'t there (empty slot, nobody hit yet): the command does nothing and reads give 0.',
]
VARS = [
    '## Where the value goes',
    'Variable is any float variable. The usual choice is this object\'s own VAR_0-VAR_31 (0x0F000300-0x0F00031F): '
    'every object (fighter or article) has its own, they start at 0 and keep their value until the object is set up '
    'again (a fighter\'s KO, a projectile\'s next shot). Test them with Float_Var_Compare, set them with SET_FLOAT. '
    'Floats only: SET_INT and Int_Var_Compare don\'t work on them, and ADD_FLOAT does nothing in this game (to add, '
    'SUB_FLOAT_2 a variable holding the negative step).',
]
METHODS = ('Method is Float_Var_Compare\'s: 0 ==, 1 !=, 2 <=, 3 >=, 4 <, 5 > (read as "input Method Value").')
NOT_VIEWER = 'The Hitbox Viewer doesn\'t simulate this command (it only acts in game).'


def _hitbox(cmd='Hitbox', **kw):
    """a hitbox line with every parameter named (kw overrides the defaults; '/' names as Ground_Air)"""
    keys = ['ID', 'Part', 'Bone', 'Damage', 'Angle', 'KBG', 'FKB', 'BKB', 'Size', 'X', 'Y', 'Z', 'Effect', 'Trip',
            'Hitlag', 'SDI', 'Clang', 'Rebound', 'ShieldDamage', 'SFXLevel', 'SFXType', 'Ground/Air', 'Direct/Indirect',
            'Type']
    special = ['HitBits', 'Unk41', 'CollisionPart', 'NoScale', 'Shieldable', 'Reflectable', 'Absorbable', 'Rehit',
               'IgnoreInvuln', 'HitAllStates', 'FacingRestrict', 'NoGrabRelease', 'TeamDamage', 'DisableHitlag',
               'NoGFX', 'Flinchless']
    extras = ['HitstunMul', 'HitstopMul', 'HitstopFrames', 'SelfHitstopMul', 'SelfHitstopFrames', 'DIMul']
    if cmd == 'Hitbox':
        pass
    elif cmd in ('Special_Hitbox', 'Extra_Special_Hitbox'):
        keys += special + ['Shape']
    elif cmd in ('Extended_Special_Hitbox', 'Extra_Extended_Special_Hitbox'):
        keys += special + ['X2', 'Y2', 'Z2']
    if cmd.startswith('Extra_'):
        keys += extras
    d = dict(ID=0, Part=0, Bone=0, Damage=12, Angle=361, KBG=100, FKB=0, BKB=40, Size=5, X=0, Y=8, Z=6, Effect=0,
             Trip=0, Hitlag=1, SDI=1, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=2, SFXType=1, Ground_Air=3,
             Direct_Indirect=1, Type=1, HitBits='0x3F', Unk41=0, CollisionPart='0xF', NoScale=0, Shieldable=1,
             Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0, HitAllStates=0, FacingRestrict=3, NoGrabRelease=0,
             TeamDamage=0, DisableHitlag=0, NoGFX=0, Flinchless=0, Shape=0, X2=0, Y2=8, Z2=14, HitstunMul=0,
             HitstopMul=0, HitstopFrames=0, SelfHitstopMul=0, SelfHitstopFrames=0, DIMul=0)
    d.update(kw)
    return '%s(%s)' % (cmd, ', '.join('%s=%s' % (k, d[k.replace('/', '_')]) for k in keys))


# --- the groups' own help (shown when a group is picked) ----------------------------------------------------------
GROUP_HELP = {
    NEW_GROUP: [
        'Commands this mod adds to ACMD. They work in game, effect, sound and expression scripts, in fighters\' and '
        'articles\' (projectiles\') scripts alike, and Sm4shCommand, tools/acmd.py and the Hitbox Viewer know them. '
        'Vanilla commands stay in their usual groups; everything new is here.',
        '',
        '## Requirement',
        'They need the patched cross_f.rpx (tools/acmd_ext_cave.py, part of the standard build). Without it a script '
        'that uses any of them won\'t load properly: ship the executable with any script that uses them.',
        '',
        '## Groups',
        '- Hitboxes & hits: hitboxes with hitstun / hitstop / DI extras, checking what an attack connected with, '
        'clearing the "has hit" flag and the hit records.',
        '- Fighter state: read or change any fighter\'s status, hitstun, hitstop, damage, intangibility, armor, '
        'item states and stage collision; let a grounded move go on in the air (Leave_Ground_Cancel); change its '
        'gravity and fall speed for a move (Gravity_Set).',
        '- Inputs: read, test or force a fighter\'s buttons and sticks.',
        '- Position & rotation: read or move a fighter / article, rotate it, read a joint\'s position.',
        '- Animation: which animation plays, its frame and rate; play another one; the fighter\'s overall speed.',
        '- Targets & tracking: homing (Track_Target), who was hit last / hit this one last, player slots.',
        '- Threads: a block that keeps running on its own after the animation ends or changes.',
        '- Variables: New_Var declares your own named variables (int or float, a starting value), usable in every '
        'variable parameter.',
        '',
    ] + TARGETS + [
        '',
        '## Conditions',
        'Hit_Check and Input_Compare work like Float_Var_Compare: the True(...){ } block right after them runs when '
        'the test passes, an Else(...){ } after that block when it fails. Sm4shCommand works out the blocks\' Offset '
        'from the braces when the script compiles (write Offset=0).',
        METHODS,
        '',
    ] + VARS + [
        'Also per object: TIMER_0-TIMER_15 (0x0F000320-0x0F00032F: set frames, they count down by 1 every frame the '
        'object moves, not in hitlag, and stop at 0), KINETIC_TYPE (0x0F000330), TRACK_FRAMES (0x0F000331), SPEED_X / '
        'SPEED_Y (read only), GRAVITY / MAX_FALL (0x0F000337 / 338: a fighter\'s gravity and max fall speed in effect, '
        'Gravity_Set\'s included; read only), STICK_ANGLE / STICK_ANGLE_RAW / STICK_LEN and the C-stick\'s '
        '(0x0F0003C0-3C5: the stick\'s angle along the facing / on screen, in degrees, and how far it is pushed), '
        'ROT_X / ROT_Y / ROT_Z (0x0F0003C6-3C8: the rotation in degrees; read only; exe_v43). SLOT1_SHARED_0-SLOT8_SHARED_7 are VAR_24-VAR_31 of the fighter in that player slot, '
        'so another object can leave values there for it.',
        'More, with your own names: New_Var(Name=charge, Type=int, Initial=0) gives up to 64 more per object (Variables '
        'group), and those work with SET_INT / ADD_INT / INC_INT / Int_Var_Compare too.',
        '',
        '## More',
        'ACMD-new-commands.md next to Sm4shCommand.exe (the repository\'s docs/acmd-extra-commands.md) has the '
        'details; docs/position-variables.md the variables these commands are built on.',
    ],
    NEW_GROUP + ' / Hitboxes & hits': [
        'Extra_Special_Hitbox / Extra_Extended_Special_Hitbox make the vanilla Special hitboxes with six extras '
        '(hitstun / hitstop / DI); their Damage, Angle, KBG, FKB, BKB and Size can be variables (exe_v43: '
        'Angle=STICK_ANGLE, Damage=VAR_0, |FOLLOW to follow them every frame). Hit_Check / Hit_Get tell what an attack connected with (a hurtbox, a shield, ...). '
        'Hit_Reset clears the "has hit" flag (SELF_HIT); Hit_Log_Clear the record of who a hitbox Part has hit, so '
        'the same hitboxes can hit again.',
    ],
    NEW_GROUP + ' / Fighter state': [
        'Read or change a fighter\'s status, hitstun, hitstop, damage, intangibility / invincibility, armor, item '
        'states and stage collision, on any target (self, the nearest opponent, the last fighter hit, a player slot, '
        'the last attacker). Each is the matching position variable\'s own code (docs/position-variables.md) with '
        'parameters instead of a variable ID. They act on fighters: on an article (Target 0 in a projectile\'s '
        'script) they do nothing. Leave_Ground_Cancel decides whether this fighter\'s grounded move ends when it '
        'leaves the ground; Gravity_Set changes this fighter\'s gravity and max fall speed for the move.',
    ],
    NEW_GROUP + ' / Inputs': [
        'A fighter\'s controller: test an input (Input_Compare, then True / Else), copy it into a variable '
        '(Input_Get), or force it as if the controller did it (Input_Set). Targets 0-10 (not 11).',
    ],
    NEW_GROUP + ' / Position & rotation': [
        'Where a fighter or article is, which way it faces, its rotation, and a joint\'s place, read into variables '
        'or set. They run the same PostureModule ops MSC does, so articles work too.',
    ],
    NEW_GROUP + ' / Animation': [
        'Which animation (motion) a fighter or article plays, its frame and rate; play another one or jump within '
        'the current one; speed up / slow down everything a fighter does.',
    ],
    NEW_GROUP + ' / Targets & tracking': [
        'Track_Target makes a fighter or projectile home in on the nearest fighter. Last_Hit_Get and '
        'Target_Slot_Get give player slots (1-8) of the last fighter hit, the last attacker or any target.',
    ],
    NEW_GROUP + ' / Threads': [
        'Thread_Start(ID, Flags){ ... } runs its block on its own, frame by frame, while the script goes on; it '
        'keeps going after the animation ends or changes. Thread_Stop(ID) ends it.',
    ],
    NEW_GROUP + ' / Variables': [
        'New_Var(Name=..., Type=int / float, Initial=..., Scope=object / move) declares a variable with your own name. '
        'The name then works in every variable parameter of every open script: SET_FLOAT / SET_INT / ADD_INT / INC_INT, '
        'Float_Var_Compare / Int_Var_Compare, SUB_FLOAT_2, the new commands\' Variable=... (Hit_Get, Position_Get, '
        'Input_Get, ...). 64 per object (fighter or article), besides VAR_0-VAR_31 and TIMER_0-TIMER_15, which work '
        'as before.',
    ],
}

# --- each command's help (after its description and parameters in View > Commands) ---------------------------------
_EXTRA_RULES = [
    '## The six extras',
    '- HitstunMul (float): multiplies the hitstun this hit gives (the game\'s knockback x 0.4). A negative value adds '
    'that many frames instead: -2 = 2 frames more (Ultimate\'s set_add_reaction_frame).',
    '- HitstopMul (float): multiplies the opponent\'s hitstop (hitlag), on top of the hitbox\'s own Hitlag parameter.',
    '- HitstopFrames (int): the opponent\'s hitstop in frames, replacing the computed one (HitstopMul is then '
    'ignored).',
    '- SelfHitstopMul (float): multiplies the attacker\'s own hitstop from this hit.',
    '- SelfHitstopFrames (int): the attacker\'s own hitstop in frames, replacing the computed one.',
    '- DIMul (float): multiplies how far DI can turn this hit\'s launch angle (0.5 half, 2 double).',
    '',
    '## Rules',
    '- A multiplier of 0 or less means x1 (unchanged), so all six at 0 make exactly the plain command\'s hitbox.',
    '- Frames 0 means "computed"; above 0 replaces it. Frame values aren\'t capped at 30 like the computed hitstop.',
    '- No DI at all: DIMul=0.001 (a tiny value; 0 would mean x1). No hitstop at all: the hitbox\'s DisableHitlag=1 '
    '(HitstopFrames=0 means computed, not none).',
    '- The extras stack with everything else: LASTHIT_HITSTUN_MUL (0x0F000052), Set_Frame_Duration slowdowns, '
    'Strike Kirby\'s hitstop, ... Hitstop frame values are applied after the game\'s slowdown rate, so they are exact.',
    '',
    '## Gotchas',
    '- Each Extra command takes its own extras record, so re-issuing the same ID every frame (a multi-hit, a moving '
    'hitbox) keeps each hit\'s own extras.',
    '- A later plain hitbox command with the same ID replaces the hitbox and drops the extras. Change_Hitbox_Damage / '
    'Change_Hitbox_Size keep them.',
    '- DIMul scales the max DI angle (fighter_param 0x0200011A) the fighter that was hit reads, until its next hit. '
    'It doesn\'t touch LSI or SDI (SDI is the hitbox\'s own SDI parameter). Not yet checked in game for every '
    'fighter\'s damage code.',
    '- IDs: fighters have hitbox IDs 0-9 and Parts 0-19; Din\'s Fire and the articles copied from it only IDs 0-6 '
    'and Parts 0-1. The game doesn\'t check: a hitbox past them crashes the game when it connects.',
    '- ShieldDamage is read unsigned: never negative (a negative value breaks a shield in one hit).',
    '- Works in articles\' (projectiles\') scripts too.',
    '- Hitbox Viewer: drawn like the plain command, with the six extras in the list\'s Extras column; the '
    'knockback / hitstun calculator uses them.',
    '',
    '## Variables in Damage, Angle, KBG, FKB, BKB and Size (exe_v43 and later)',
    'Any of these six can be a variable instead of a number: Damage=VAR_0, Angle=STICK_ANGLE, Size=charge (a New_Var), '
    'or an ID (0x0F000300). The variable is read when the command runs, and the hitbox is made from its value exactly '
    'as from a number (the game\'s own hitbox code). Fields left as numbers work as before, and a command with no '
    'variable is the same as in older executables.',
    '- Which variables: VAR_0-VAR_31, New_Var names (int or float), the mod\'s other variables (STICK_ANGLE, ROT_X, '
    'POS_..., SELF_DAMAGE, ...), and the game\'s own floats / ints (0x1000xxxx ints are read as ints). Not flags '
    '(0x2xxxxxxx).',
    '- How the value is used: Damage and Size as they are (below 0: 0). KBG, FKB and BKB rounded to a whole number '
    '(halves away from 0; below 0: 0). Angle rounded, then any value works: -30 is 330, 725 is 5, 360 is 0; 361-368 '
    'stay as they are (361 = the Sakurai angle).',
    '- The angle is along the facing, as every hitbox angle is (0 forward, 90 up, 180 backward, 270 down): the game '
    'mirrors it for a fighter facing left. STICK_ANGLE / CSTICK_ANGLE are measured that way, so Angle=STICK_ANGLE '
    'launches the way the stick points whichever way the fighter faces.',
    '- Flags after the variable, with |: |FOLLOW: the field is read again every frame while the hitbox is out (a '
    'stick-aimed hitbox that follows the stick, damage that grows with a charge); |WORLD (Angle): the value is an '
    'angle on screen (0 right, 90 up, 180 left), turned into the hitbox\'s angle for the facing (facing left: '
    '180 - value), e.g. Angle=STICK_ANGLE_RAW|WORLD; |NEG: minus the value (Angle=ROT_X|NEG). Several: '
    'Angle=STICK_ANGLE|FOLLOW.',
    '- Variables for it: STICK_ANGLE (0x0F0003C0: the control stick\'s angle along the facing, 0-360; 0 in '
    'neutral), STICK_ANGLE_RAW (0x0F0003C1, on screen: 0 right), STICK_LEN (0x0F0003C2: how far it is pushed, 0-1), '
    'the same for the C-stick (CSTICK_ANGLE, CSTICK_ANGLE_RAW, CSTICK_LEN: 0x0F0003C3-3C5), ROT_X / ROT_Y / ROT_Z '
    '(0x0F0003C6-3C8: this object\'s rotation in degrees, what Rotation_Get stores). All read only, this object\'s '
    'own.',
    '- FOLLOW lasts until another hitbox is made with the same ID (Extra or plain), the object is reset (KO / a '
    'projectile\'s next use), or 16 FOLLOW hitboxes later (the oldest goes). It doesn\'t update during hitlag (the '
    'object is frozen). Damage keeps whatever the game did to the first value (Strike Kirby\'s x1.15, ...).',
    '- The Hitbox Viewer draws a variable with the script\'s last SET_FLOAT of it, else a stand-in (Damage 10, '
    'Angle 0, KBG 100, FKB 0, BKB 40, Size 4), and lists it in the Extras column.',
    '- Needs exe_v43 or later: an older executable reads the variable\'s ID as a number (a hitbox of size 0 and '
    'an angle in the millions).',
]
HELP = {
    'Extra_Special_Hitbox': [
        '## How it works',
        'Special_Hitbox\'s 41 parameters (the same, in the same order, ending with Shape), then six extras. The '
        'hitbox itself is made exactly as Special_Hitbox makes it; the extras are remembered for that hitbox and '
        'applied when it connects (the victim\'s hitstun and hitstop, the attacker\'s hitstop, the victim\'s DI). To '
        'turn an existing Special_Hitbox into one, rename it and add the six values at the end.',
        '',
    ] + _EXTRA_RULES + ['', NEEDS],
    'Extra_Extended_Special_Hitbox': [
        '## How it works',
        'Extended_Special_Hitbox\'s 43 parameters (a capsule from X/Y/Z to X2/Y2/Z2, the same order), then the same '
        'six extras as Extra_Special_Hitbox. The hitbox is made exactly as Extended_Special_Hitbox makes it; the '
        'extras apply when it connects. Use it for long hitboxes (a sword, a beam) that need the extras.',
        '',
    ] + _EXTRA_RULES + ['', NEEDS],
    'Hit_Check': [
        '## How it works',
        'A condition, like Float_Var_Compare: the True(...){ } block after it runs when the target\'s attack has '
        'connected with any of the Kinds, an Else(...){ } after that when it hasn\'t. It reads the game\'s own '
        'record, what MSC\'s AttackModule(0x2727 / 0x2726, kinds) reads (Ryu\'s specials cancel on 6, "hit or '
        'shield"; Kirby\'s star missile checks 2, "hit").',
        '',
        '## Kinds (bits: add them)',
        '- 2: a hurtbox (it hit a fighter or object).',
        '- 4: a shield.',
        '- 6: either (2 + 4).',
        '- 0: anything (0x7F, MSC\'s default).',
        '- Not confirmed (they follow Ultimate\'s collision kinds): 1 another attack (clank), 8 a reflector, 16 an '
        'absorber, 32 a search box, 64 other.',
        '',
        '## When',
        '- 0: since the move started (or since the last Hit_Reset).',
        '- 1: this frame only (the frame the hit lands: put the check on that frame, or every frame in a loop).',
        '',
    ] + TARGETS + [
        '',
        '## Gotchas',
        '- The check runs where it is in the script: FRAME(Frames=20) then Hit_Check tests once, on frame 20. To react '
        'on whichever frame the hit lands, check When=1 every frame (a Set_Loop of WAIT(Frames=1)), or When=0 after the '
        'hitbox is gone.',
        '- "Since the move started" stays set until the move ends: use Hit_Reset between hitboxes to check a later '
        'one on its own.',
        '- In the Hitbox Viewer the True / Else branch follows its "If conditions true" setting.',
        '',
        NEEDS,
    ],
    'Hit_Get': [
        '## How it works',
        'Stores what the target\'s attack connected with in a float variable, as the same bits Hit_Check tests: 2 a '
        'hurtbox, 4 a shield (6 both), 1 / 8 / 16 / 32 / 64 the unconfirmed kinds (clank, reflector, absorber, search '
        'box, other); 0 = nothing. Use it when one check isn\'t enough: store once, then compare the variable several '
        'times (hit only, shield only, both).',
        '',
        '## When',
        '- 0: since the move started (or the last Hit_Reset). 1: this frame only.',
        '',
    ] + TARGETS + [''] + VARS + [
        '',
        '## Gotchas',
        '- The value is a bit mask stored as a float (the kinds added up): == 2 only a hurtbox, == 4 only a shield, '
        '== 6 both, == 0 nothing. A test like ">= 2" also counts the unconfirmed kinds (8 and up) if they ever show up.',
        '- In a block that isn\'t run (a False / Else branch not taken), it does nothing.',
        '',
        NEEDS,
    ],
    'Hit_Reset': [
        '## How it works',
        'Sets this object\'s "attack has hit" flag back to 0: the SELF_HIT variable (0x0F0000A0), and what Hit_Check / '
        'Hit_Get read with When=0. The flag otherwise stays 1 from the first connecting hitbox until the move ends, so '
        'without a reset a check after a second hitbox would also be true when only the first one hit. It is the '
        'game\'s own AttackModule(0x2724). Writing any value to SELF_HIT does the same.',
        '',
        '## Gotchas',
        '- Only the flag is cleared. The game\'s "already hit this fighter" record (which stops one hitbox Part '
        'hitting the same fighter twice) isn\'t: use Hit_Log_Clear for that.',
        '- Acts on this object only (no Target).',
        '',
        NEEDS,
    ],
    'Hit_Log_Clear': [
        '## How it works',
        'Makes this object forget which fighters its hitboxes of Part have hit, so the same hitboxes can hit them '
        'again, as a new attack would. Each Part has one record, shared by the hitboxes with that Part number; it '
        'stays through Remove_All_Hitboxes and new hitbox commands until the move (status) ends, which is why a '
        'second wave of the same Part normally can\'t hit the same fighter. Part=-1 clears every part. Unlike '
        'Hit_Reset, this is the record itself (the game\'s own clear, as when an object is set up).',
        '',
        '## Gotchas',
        '- A Part the object doesn\'t have does nothing: fighters have Parts 0-19; Din\'s Fire and the articles copied '
        'from it only 0-1.',
        '- Clear it between waves, not while the hitbox is still out: a hitbox that is still overlapping the fighter '
        'can hit again on the next frame.',
        '- Hitboxes with Rehit (a rehit rate) already hit again on their own; this is for hitboxes without it.',
        '- Sephiroth\'s Shadow Flare orbs use it to give each orb strike a new record.',
        '',
        NEEDS,
    ],
    'Status_Get': [
        '## How it works',
        'Stores the target\'s status (action) kind, the number its MSC runs (reference/msc-note-sheet/'
        'Actions_Fighters.csv), in a float variable: 0x0 Wait, 0xE Fall, 0x1C Guard (shielding), 0x1E GuardDamage '
        '(shield stun), 0x46 Damage (hitstun), 0x47 DamageFly (tumble), 0x59 shield break, 0x5D dizzy, ... '
        'Special moves\' statuses are the fighter\'s own numbers.',
        '',
    ] + TARGETS + [''] + VARS + ['', NOT_VIEWER, NEEDS],
    'Status_Set': [
        '## How it works',
        'Changes the target\'s status (StatusModule(3, status, 0), as MSC\'s change_status), e.g. 0x59 shield break, '
        '0x5D dizzy, 0xE fall. The change takes effect on the target\'s next frame.',
        '',
    ] + TARGETS + [
        '',
        '## Gotchas',
        '- A status runs its own code: it may need things the move didn\'t set up (a dizzy without a shield break '
        'before it, a status of another fighter\'s number). Stick to common statuses, or test in game.',
        '- Setting it on the frame of a hit: the hit\'s own damage status may come after it. Set it a frame later, or '
        'after the hitlag, if the hit status wins.',
        '- Shield break chain: 0x59 launch, 0x5A tumble, 0x5B landing, 0x5C-0x5E dizzy.',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Hitstun_Get': [
        '## How it works',
        'What 0: the target\'s hitstun frames left (0 when it isn\'t in hitstun). What 1: the hitstun of the last hit '
        'it took (frames, the game\'s DamageModuleF(1)).',
        '',
    ] + TARGETS + [''] + VARS + ['', NOT_VIEWER, NEEDS],
    'Hitstun_Set': [
        '## How it works',
        'Sets the target\'s hitstun frames left (WorkModule int 0x1000003E). 0 ends its hitstun now: it can act on its '
        'next frame (airdodge, attack, ...); a larger value extends it.',
        '',
    ] + TARGETS + [
        '',
        '## Gotchas',
        '- It only matters while the target is in a hit status (Damage, DamageFly, ...).',
        '- To change the hitstun a move gives instead (before or after the hit), use LASTHIT_HITSTUN_MUL '
        '(SET_FLOAT to 0x0F000052) or an Extra hitbox\'s HitstunMul.',
        '- The hit sets the target\'s hitstun itself, so set it after the hit has landed: a WAIT past the hitlag, or a '
        'thread.',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Hitstop_Set': [
        '## How it works',
        'Freezes the target in hitstop (hitlag) for Frames frames (StopModule(2, frames)). Shake 1 also shakes it as '
        'a hit does (ShakeModule), Shake 0 freezes it still.',
        '',
    ] + TARGETS + [
        '',
        '## Gotchas',
        '- Hitstop stops the target\'s animation, script timers and movement; its threads pause too (unless started '
        'with Flags 1).',
        '- To change the hitstop of a hit itself, use an Extra hitbox (HitstopFrames / SelfHitstopFrames) or the '
        'hitbox\'s Hitlag parameter: they are applied by the hit.',
        '- Target 0 freezes this fighter itself (its own script stops counting during the freeze).',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Damage_Get': [
        '## How it works',
        'Stores the target\'s damage % in a float variable. Compare it to make a move behave differently at high '
        'percent (a stronger finisher, a guaranteed follow-up below some %).',
        '',
    ] + TARGETS + [''] + VARS + ['', NOT_VIEWER, NEEDS],
    'Damage_Set': [
        '## How it works',
        'Sets the target\'s damage % (the HUD counter follows). 0 heals it completely.',
        '',
    ] + TARGETS + [
        '',
        '## Gotchas',
        '- It sets the %, it doesn\'t deal a hit: no knockback, no hitstun, no hitlag.',
        '- Percent is a fixed number. To add or take away an amount, use the damage variable with SUB_FLOAT_2 '
        '(a read, the change, a write): SELF_DAMAGE (0x0F000117), OPP_DAMAGE, LASTHIT_DAMAGE, SLOTn_DAMAGE. '
        'SUB_FLOAT_2 subtracts, so put a negative step in the source variable to add damage.',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Body_State_Set': [
        '## How it works',
        'State 0: the target is intangible for Frames frames (HitModule(2, frames): hitboxes pass through it). State '
        '1: invincible for Frames frames (HitModule(1, frames): hitboxes connect but do nothing). Other States do '
        'nothing.',
        '',
    ] + TARGETS + [
        '',
        '## Gotchas',
        '- It is a timed state on top of the status\'s own: the stronger of the two counts. For hurtbox states for the '
        'move itself, Body_Collision / Bone_Collision are still the usual way; this one is for timed states (and other '
        'fighters).',
        '- Read it with the input variables: SELF_INTANGIBLE / SELF_INVINCIBLE (or Input_Get Input 27 / 28).',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Armor_Set': [
        '## How it works',
        'Gives the target armor (DamageModule(0xB, type, threshold)), set before Type is applied so the type reads '
        'it. It holds until set again: Armor_Set(Type=0) ends it.',
        '- Type 0: none.',
        '- Type 1: super armor (no flinching from any hit).',
        '- Type 2: knockback-based: hits whose knockback is below Threshold don\'t make it flinch.',
        '- Type 3: damage-based: hits dealing less than Threshold % don\'t make it flinch.',
        '',
    ] + TARGETS + [
        '',
        '## Gotchas',
        '- End it yourself (Type 0) where the move\'s armor should end, rather than relying on the move ending.',
        '- The fighter still takes the damage %, only the flinch is skipped.',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Item_State_Set': [
        '## How it works',
        'Puts one of the items\' own states on the target, through the game\'s function for it (the one the item\'s '
        'pickup calls), with the item\'s own durations:',
        '- Code 1: metal on (the Metal Box: look, physics, knockback resistance). Code 2: metal off.',
        '- Code 3: giant (Super Mushroom). Code 4: small (Poison Mushroom).',
        '- Code 5: Super Star (invincible, flashing).',
        '- Code 6: the Lip\'s Stick flower on its head.',
        '- Code 7: the Timer\'s slow on every other fighter (half speed, 450 frames).',
        '- Code 8: the camera closes in on the target. Code 9: the camera back to normal.',
        '',
    ] + TARGETS + [
        '',
        '## Gotchas',
        '- The mushrooms refuse while the fighter can\'t grow / shrink (its flags 0x20000025, 0x20000037, 0x2000001B).',
        '- Code 2 ends metal; the other states last the item\'s own duration.',
        '- Used by Hero\'s Kaclang (metal), Metal Slash (metal on the last fighter hit), Hocus Pocus and critical hits '
        '(8 / 9).',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Stage_Collision_Set': [
        '## How it works',
        'Sets how the target collides with the stage (GroundModule(0x2710, mode), as Smash 4\'s own grab statuses do):',
        '- Mode 0: none: it passes through the stage and floors (as a grabbed fighter does).',
        '- Mode 5: air.',
        '- Mode 1 / 2: ground (1 can slide off edges, 2 can\'t).',
        '',
    ] + TARGETS + [
        '',
        '## Gotchas',
        '- The target\'s status sets its own collision again when it changes: set it every frame for as long as it '
        'should hold (a Set_Loop of WAIT(Frames=1), or a thread), and 5 (or the status\'s own) to end it.',
        '- A fighter left inside the stage with mode 0 falls through it; put it back in the air (5) somewhere open.',
        '- Sephiroth\'s held forward air drags fighters back through the stage with it.',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Leave_Ground_Cancel': [
        '## How it works',
        'Decides whether this grounded move is cut short when the fighter leaves the ground (walks or slides off an '
        'edge, or is moved up off it). Normally (on) the move ends there and the fighter goes to Fall. Off, the move '
        'goes on in the air: its animation, hitboxes, effects and the rest of its scripts, with air physics.',
        '- Enabled 1: on, the normal game (the move ends in Fall when the fighter leaves the ground).',
        '- Enabled 0: off: the move goes on in the air, and a move that stops at edges can slide off them.',
        '- Enabled 2: off, but the move still stops at edges: it leaves the ground only by moving up.',
        '',
        '## Edges',
        'Most Smash 4 ground moves stop at edges (ground correction 2, "cliff stop": every dash attack), so they never '
        'leave the ground sideways. With Enabled=0 such a move slides off edges (as a walk does) while it\'s on the '
        'ground, so a dash attack runs off the stage; Enabled=2 keeps the stop. A move that already slides off is left '
        'as it is.',
        '',
        '## In the air, and after',
        '- The frame it is in the air, the fighter gets the air kinetics and stage collision the game\'s own ground / '
        'air moves switch to (kinetic 0 FALL: gravity, air drift and air friction, with the speed it carried). The '
        'animation keeps playing (the status doesn\'t change).',
        '- The move ends in Fall at its interrupt frame (its cancel window opening: the vl file\'s cancel frame or '
        'ENABLE_CANCEL) or at the end of its animation, whichever comes first; in Fall it can act again.',
        '- Landing during it: the move goes on, grounded (no landing, no landing lag), until it ends as it normally '
        'would (with Enabled=0 still sliding off the next edge).',
        '',
        '## Gotchas',
        '- It resets to on by itself at every status change (the next move, Fall, a hit, ...), so it never carries into '
        'another move; it stays through a motion change inside one status (a smash attack\'s charge and swing).',
        '- Turning it back on in the air (Enabled=1) ends the move in Fall on the next frame.',
        '- Fighters only (Kirby\'s copies too); in an article\'s script it does nothing.',
        '- No ledge grab during the move (the move isn\'t Fall).',
        '- Only the leave-ground Fall is held back: a move that ends through its own MSC (a smash charge\'s hold, a '
        'rapid jab\'s loop, a motion change from MSC) won\'t end in the air until its interrupt frame, its '
        'animation\'s end, or the ground. Use it on moves that end by their animation (dash attacks, tilts, jabs, '
        'smash swings), or turn it back on at a frame in the script.',
        '- Not tested in game yet (emulator only, tools/leave_ground_test.py): the momentum carried into the air.',
        '',
        NOT_VIEWER,
        'Needs exe_v41 or later (the patched cross_f.rpx, tools/acmd_ext_cave.py; in exe_v39 / v40 the move still '
        'ended in Fall once it had slid off the edge). Without it a script that uses this command won\'t load '
        'properly: ship the executable with any script that uses it.',
    ],
    'Gravity_Set': [
        '## How it works',
        'Sets this fighter\'s gravity (how much its vertical speed drops each frame) and max fall speed for the rest '
        'of the move. It works in any move where the fighter falls with gravity: aerials, specials, a grounded move '
        'that went on in the air with Leave_Ground_Cancel(Enabled=0), ... The game\'s own gravity code does the rest '
        '(the same curve, with these two numbers).',
        '- Accel: the gravity, on the scale of the fighter_param "Gravity" (Diddy Kong 0.105, Jigglypuff 0.053). 0: '
        'no gravity: the vertical speed stays as it is (a rise keeps rising: use a small Accel with MaxFall 0 to '
        'hover). Below 0 (write -1): the fighter\'s own.',
        '- MaxFall: the max fall speed, on the scale of "Maximum Fall Speed" (Diddy 1.75). Falling faster than it '
        '(a fall already going when the command runs), the fighter slows to it gradually, by its "V acceleration" '
        '(Diddy 0.016) a frame, as the game does after a fast fall; Mode 2 cuts it at once. 0: it stops falling. '
        'Below 0 (-1): the fighter\'s own.',
        '- Mode (bits, add them): 1 Accel and MaxFall are multipliers of the fighter\'s own (0.5 = half; -1 still '
        'means its own); 2 a fall faster than MaxFall is cut to it at once (every frame it holds); 4 no fast fall '
        'while it holds (the fast-fall flag is turned off every frame, so pressing down does nothing).',
        '- Off: Accel and MaxFall both -1 with Mode 0 (or 1) turns it off at that frame.',
        '',
        '## When it ends',
        'Back to the fighter\'s own values by itself, so it never carries over:',
        '- at the next status change (the next move, Fall, landing, a jump, a grab or throw, a KO, ...);',
        '- the moment a hit takes effect (the fighter will flinch or fly), before its damage status even starts; a hit '
        'with no reaction (armor, or too weak to make it flinch) leaves it, since the move goes on;',
        '- on a ledge grab, whichever way it happens (the ledge situation, a cliff status, a tether hang), even if the '
        'status change hasn\'t happened yet.',
        'It stays through a motion change inside one status (an aerial\'s landing motion is a new status, so it ends '
        'there).',
        '',
        '## Gotchas',
        '- Only while the fighter falls with gravity. A move whose own kinetics turn gravity off (a special that '
        'moves by its animation, a hover the move itself does) isn\'t changed: there is no gravity to set.',
        '- It wins over the move\'s own gravity changes from MSC (KineticModule 0xF / 0x14 / 0x15 on energy 1) and '
        'over the kinetic type changing mid-move: every frame the fighter\'s gravity is computed with these values.',
        '- Without Mode 4 a fast fall (down during an aerial) still falls at the fighter\'s own fast-fall speed.',
        '- GRAVITY (0x0F000337) and MAX_FALL (0x0F000338) read the values in effect (Gravity_Set\'s, or the '
        'fighter\'s own), e.g. to test them with Float_Var_Compare. Read only.',
        '- Fighters only (Kirby\'s copies too); in an article\'s script it does nothing.',
        '- Not tested in game yet (emulator only, tools/gravity_set_test.py, with the game\'s own gravity code).',
        '',
        NOT_VIEWER,
        'Needs exe_v42 or later (the patched cross_f.rpx, tools/acmd_ext_cave.py). Without it a script that uses this '
        'command won\'t load properly: ship the executable with any script that uses it.',
    ],
    'New_Var': [
        '## How it works',
        'Declares a variable with your own name. Sm4shCommand gives the name a slot (0-63, the variable ID '
        '0x0F000380 + slot) and keeps the name in the command itself, so the script shows the name again when it is '
        'opened later. From then on the name works wherever a variable goes, in every script of the open fighter '
        '(game, effect, sound, expression): SET_FLOAT(Value=0, Variable=charge), INC_INT(Variable=charge), '
        'Int_Var_Compare(Variable=charge, Method=3, Value=30), Hit_Get(Target=0, When=0, Variable=charge), ...',
        'When it runs in game, it sets the variable to Initial (see Scope) and gives it its Type.',
        '',
        '## Parameters',
        '- Name: letters, digits and _, not starting with a digit, up to 24 characters; case doesn\'t matter (charge '
        '= Charge). Not a name the Aliases folder already has (VAR_0, SELF_HIT, ...) or a command\'s.',
        '- Type: float (the default) or int (also 0 / 1). Both are numbers the int and the float commands take: '
        'SET_INT, ADD_INT, INC_INT, Int_Var_Compare, INT_VAR_COMPARE_VAR read and write an int variable as a whole '
        'number; SET_FLOAT, SUB_FLOAT_2, Float_Var_Compare and the new commands\' Variable=... as a float. An int '
        'variable keeps whole numbers: a float written to it is cut toward 0 (2.7 -> 2, -2.7 -> -2). A float one '
        'read by an int command is cut the same way (the variable keeps its fraction).',
        '- Initial: the starting value (0 if left out).',
        '- Scope: object (the default, also 0): Initial is set the first time a New_Var for it runs for this object; '
        'after that New_Var leaves it alone, and the value stays (between moves, like VAR_n) until the object is set up '
        'again: a fighter\'s KO, a projectile\'s next shot. move (also 1): Initial is set every time this New_Var runs: '
        'at the top of a move\'s script it starts fresh at every use of the move.',
        '- Slot: optional, 0-63. Left out (or auto), the name keeps the slot it already has in the open scripts, else '
        'gets the lowest free one. Sm4shCommand shows it when the script is shown again (Slot=0, ...). Give it to '
        'fix the ID, e.g. for MSC.',
        '',
        '## Where they live',
        '- Each object has its own 64: a fighter\'s scripts and its articles\' (projectiles\') scripts each see their '
        'own, as with VAR_n. The same name in a fighter and in its projectile is two variables.',
        '- Before any New_Var or write, a variable reads 0. Writing it (SET_FLOAT, ...) before New_Var ran works: the '
        'first New_Var (Scope object) then still sets Initial.',
        '- They are apart from VAR_0-VAR_31 / TIMER_0-TIMER_15 (which work as before) and from every other object\'s.',
        '- MSC: WorkModuleF(0, 0x0F000380 + slot) reads one (WorkModule(6, ...) as an int), WorkModule(0, value, ID) / '
        'WorkModule(7, value, ID) write it.',
        '',
        '## Names in Sm4shCommand',
        '- A name is known once a script declaring it compiles, or a file with its New_Var is opened. Declare it in '
        'the script that sets it first; other scripts may use the name without declaring it again (or declare it too: '
        'with Scope object, a second New_Var doesn\'t reset it).',
        '- Names are per opened fighter / file / project: opening another forgets the old ones.',
        '- A name used nowhere in a New_Var gives "unknown variable" when compiling. Without its name a variable shows '
        'as 0x0F000380 + slot, which compiles too.',
        '- View > Commands lists the names known (pick New_Var), and hovering a name in a script shows its slot.',
        '',
        '## Gotchas',
        '- Up to 48 objects at once have variables (as VAR_n): past that the oldest one\'s are reset.',
        '- Floats hold whole numbers exactly up to 16,777,216.',
        '- Not for parameters that take a number, not a variable (FRAME(Frames=charge) doesn\'t work).',
        '',
        NOT_VIEWER,
        'Needs exe_v40 or later (the patched cross_f.rpx, tools/acmd_ext_cave.py). Without it a script that uses this '
        'command won\'t load properly, and SET_INT / INC_INT on 0x0F000380+ write out of bounds: ship the executable '
        'with any script that uses it.',
    ],
    'Input_Compare': [
        '## How it works',
        'A condition, like Float_Var_Compare: tests "input Method Value" and the True(...){ } block after it runs when '
        'it holds, an Else(...){ } after that when it doesn\'t.',
        METHODS,
        '',
        '## Inputs',
        '- 0-7: attack, special, jump, shield, grab, taunt up, taunt side, taunt down, held (1 / 0).',
        '- 8-15: the same buttons pressed this frame (1 only on the frame of the press).',
        '- 16 / 17: stick X (along the fighter\'s facing: + = forward) / Y, -1 to 1.',
        '- 18 / 19: C-stick X (forward +) / Y.',
        '- 20: a stick is forced (1 / 0). 21: its own controller is ignored (1 / 0).',
        '- 22-31: state: 22 situation (0 ground, 1 ledge, 2 air), 23 damage %, 24 / 25 jumps used / max, 26 shield '
        'HP, 27 intangible, 28 invincible, 29 armor type, 30 armor threshold, 31 KO (reads 0).',
        '- 32 / 33: stick / C-stick X on screen (+ = right, whatever the facing).',
        '',
        '## Target',
        '0 self, 1 the nearest opponent, 2 the last fighter hit, 3-10 player slots 1-8. (11 isn\'t supported by the '
        'input commands.)',
        '',
        '## Gotchas',
        '- The test runs where it is in the script: FRAME(Frames=12) then Input_Compare tests on frame 12 only. To '
        'catch a press any time in a window, test each frame (a Set_Loop of WAIT(Frames=1)) or use a held input.',
        '- Stick values are the game\'s own, after its dead zone (-1 to 1).',
        '- An unknown Target or Input compares 0; an unknown Method is false.',
        '- The fighter\'s own buttons (Target 0, inputs 0-15) are read with the game\'s ControlModule, as fighter MSC '
        'reads them; the rest through the input variables (docs/position-variables.md, "Inputs and state").',
        '- In the Hitbox Viewer the True / Else branch follows its "If conditions true" setting.',
        '',
        NEEDS,
    ],
    'Input_Get': [
        '## How it works',
        'Stores the input in a float variable: buttons 1 / 0, sticks -1 to 1, the state inputs their value. Same '
        'Target and Input numbers as Input_Compare:',
        '- 0-7 held / 8-15 pressed: attack, special, jump, shield, grab, taunt up / side / down.',
        '- 16 / 17 stick X (forward +) / Y, 18 / 19 C-stick, 20 a stick is forced, 21 controller ignored.',
        '- 22 situation, 23 damage, 24 / 25 jumps used / max, 26 shield HP, 27 intangible, 28 invincible, 29 / 30 '
        'armor type / threshold, 31 KO (0).',
        '- 32 / 33 stick / C-stick X on screen (+ = right).',
        '',
        '## Target',
        '0 self, 1 the nearest opponent, 2 the last fighter hit, 3-10 player slots 1-8 (no 11).',
        '',
    ] + VARS + [
        '',
        '## Gotchas',
        '- The value is read once, where the command is: read it again later for a newer value.',
        '- Use it to keep a value for later (the stick direction at the start of a move) or to compare inputs with '
        'each other (Float_Var_Compare_Var).',
        '- In a block that isn\'t run, it does nothing.',
        '',
        NEEDS,
    ],
    'Input_Set': [
        '## How it works',
        'Forces the target\'s input as if its controller did it. Forced inputs go in where the game reads the '
        'controller, so they act exactly like the real thing (a forced press is "pressed" on its first frame, a stick '
        'forced from neutral to 1 is a smash input) and work on CPUs too.',
        '',
        '## Value per Input',
        '- Buttons 0-15 (held or pressed numbers alike): 1 hold it until 0 is set, 2 press it for one frame, 0 stop '
        'forcing it.',
        '- Sticks 16-19 and 32 / 33: force the stick to the value (-1 to 1) until Input 20 is set.',
        '- 20: any value: stop forcing both sticks.',
        '- 21: 1 ignore its own controller (forced inputs still work), 0 back on.',
        '- 22-30: set that state (22 situation, 23 damage %, 24 / 25 jumps used / max (0 used gives every jump back), 26 '
        'shield HP, 27 intangible for N frames, 28 invincible for N frames, 29 armor type, 30 armor threshold, set '
        'before 29).',
        '- 31: any value but 0 KOs the target at once (it explodes as if KO\'d).',
        '',
        '## Target',
        '0 self, 1 the nearest opponent, 2 the last fighter hit, 3-10 player slots 1-8 (no 11).',
        '',
        '## Gotchas',
        '- The inputs of this frame were read before the script ran: a forced press counts from the next frame.',
        '- Forced inputs last until changed: always undo a hold (Value 0), a forced stick (Input 20) and Input 21. '
        'They are all cleared when the fighter is KO\'d, respawns, or in the match\'s entrance and results.',
        '- In a block that isn\'t run, it does nothing.',
        '',
        NEEDS,
    ],
    'Position_Get': [
        '## How it works',
        'Stores one coordinate of the target\'s world position, or its facing, in a float variable '
        '(PostureModuleF):',
        '- Axis 0: X. Axis 1: Y. Axis 2: Z (world units; Y up).',
        '- Axis 3: facing: 1 right, -1 left.',
        'Articles work too (Target 0 in a projectile\'s script is the projectile).',
        '',
    ] + TARGETS + [''] + VARS + [
        '',
        '## Gotchas',
        '- Positions are world coordinates, not relative to this fighter. For "how far in front of me" use the '
        'position variables (POS_OPP_OFFSET_X, 0x0F00000C, is the opponent\'s X minus self\'s along self\'s facing) '
        'or subtract two Position_Gets and multiply by the facing.',
        '- The position is the object\'s base (feet for fighters), not its centre: use Joint_Position_Get for a body part.',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Position_Set': [
        '## How it works',
        'Moves the target (MSC PostureModule(3, x, y, z)):',
        '- Mode 0: puts it at (X, Y, Z), world coordinates.',
        '- Mode 1: moves it by X forward (along its own facing), Y up, Z from where it is.',
        'Fighters and articles alike.',
        '',
    ] + TARGETS + [
        '',
        '## Gotchas',
        '- It is a teleport: no collision on the way. A fighter can end up inside a wall or off stage.',
        '- A grounded fighter moved up is still in a grounded status: the game\'s ground checks may snap it back or '
        'switch it to a fall on the next frame (the same as MSC). Put it in the air first, or move it along the '
        'ground.',
        '- Mode 1\'s "forward" is the target\'s facing, not this fighter\'s.',
        '- For "put the opponent N in front of me", the position variable POS_OPP_OFFSET_X (0x0F00000C) does it in one '
        'SET_FLOAT.',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Rotation_Get': [
        '## How it works',
        'Stores the target\'s model rotation about one axis, in degrees (PostureModuleF(4 / 5 / 6)):',
        '- Axis 0: about X. Axis 1: about Y. Axis 2: about Z.',
        'The rotation that Rotation_Set sets (and MSC\'s PostureModule(4, ...)); not the facing (Position_Get Axis 3).',
        'For a hitbox angle: store it, then give the variable as an Extra hitbox\'s Angle (Angle=VAR_1; exe_v43). '
        'ROT_X / ROT_Y / ROT_Z (0x0F0003C6-3C8) read the same rotation directly, as a live variable '
        '(Angle=ROT_X|FOLLOW follows it every frame).',
        '',
    ] + TARGETS + [''] + VARS + ['', NOT_VIEWER, NEEDS],
    'Rotation_Set': [
        '## How it works',
        'Sets the target\'s model rotation in degrees (MSC PostureModule(4, x, y, z)), relative to its facing: +X tilts '
        'it forward. Fighters and articles: a projectile rotated keeps the rotation until it\'s changed.',
        '',
    ] + TARGETS + [
        '',
        '## Gotchas',
        '- A fighter\'s status may set its own rotation every frame (rolls, damage flips): set it every frame (a loop '
        'or a thread) to keep it, and back to 0 when done.',
        '- It turns the model, not the movement direction: Track_Target or the projectile\'s MSC steers.',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Joint_Position_Get': [
        '## How it works',
        'Stores the world X / Y / Z of one of the target\'s joints in three variables (ModelModuleF(0 / 1 / 2, joint), '
        'the op Zelda\'s MSC places world effects with). Joint is a model.jtb table 0 ID, the numbers ACMD uses for '
        'bones (Bone=), not a model.vbn bone index (they often agree for the first bones: WaistN is 11 for most '
        'fighters).',
        '',
    ] + TARGETS + [
        '',
        '## Gotchas',
        '- It gives the joint\'s unanimated place on the target (its rest pose, moved with the fighter), not the '
        'current pose: fine for the waist or the hip, wrong for a hand or a foot in the middle of an attack.',
        '- A joint ID of 0x200 or more, or a target that isn\'t there, reads 0.',
        '- Sephiroth\'s Shadow Flare centres its orb ring on the target\'s waist with it.',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Motion_Get': [
        '## How it works',
        'Stores what the target\'s animation is doing in a float variable:',
        '- What 0: the motion (animation) kind playing (MotionModule(7)): the animation ID, its index in the '
        'fighter\'s motion.mtable (View > Show Animation IDs: 0x5F AttackS4, ...). Numbers are per fighter.',
        '- What 1: its current frame.',
        '- What 2: its rate (speed; 1 = normal).',
        '',
    ] + TARGETS + [''] + VARS + ['', NOT_VIEWER, NEEDS],
    'Motion_Set': [
        '## How it works',
        '- Motion 0 or more: plays that motion (animation) from Frame at Rate (MSC MotionModule(1, ...)). A negative '
        'Frame starts at 0; Rate 0 or less plays at 1.',
        '- Motion -1: keeps the current animation; jumps to Frame (MotionModule(0x2713), if Frame isn\'t negative) '
        'and sets Rate (MotionModule(4), if Rate is above 0). Frame -1 with a rate changes only the speed.',
        '',
    ] + TARGETS + [
        '',
        '## Gotchas',
        '- Only the animation changes: the status keeps running, with its own code, and may play its own motion '
        'again. The scripts follow the motion (as when MSC changes it), so playing another motion on this fighter '
        'normally hands over to that motion\'s scripts.',
        '- Motion numbers are per fighter: what is 0x5F for one fighter is another animation for the next.',
        '- Rate here is the motion\'s own (like Set_Frame_Speed); Animation_Rate_Set multiplies on top.',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Animation_Rate_Set': [
        '## How it works',
        'Sets this fighter\'s animation rate multiplier (SELF_ANIM_RATE, 0x0F000098: MotionModule\'s second rate, the '
        'one Mii Fighters\' MII_ENABLE_RATE sets). Every animation, and the ACMD timed to it, runs that many times '
        'faster until it\'s set back to 1. It multiplies each move\'s own rate (Set_Frame_Speed / Set_Frame_Duration / '
        'MotionModule(4)), so moves keep their own speed changes on top.',
        '',
        '## Gotchas',
        '- It stays after the move ends: always set it back (Rate=1), e.g. in a thread, or at the end of the effect.',
        '- This fighter only (no Target).',
        '- The Hitbox Viewer follows the variable form (SET_FLOAT to 0x0F000098), not this command.',
        '- Kirby\'s Overdrive uses the same value.',
        '',
        NEEDS,
    ],
    'Track_Target': [
        '## How it works',
        'Makes the object running the script (a fighter, or a projectile in its own script) home in on the nearest '
        'other fighter for Frames frames: every frame its direction turns toward the target by up to TurnRate '
        'degrees and it moves at Speed. It runs right after the object\'s script each frame it moves (not in hitlag).',
        '',
        '## Parameters in practice',
        '- Frames: how long. -1 = until stopped (Track_Target with Frames=0, or SET_FLOAT 0 to TRACK_FRAMES, '
        '0x0F000331, or the object being set up again). 0 stops it now.',
        '- Speed: travel speed. 0 keeps the current speed and only turns it.',
        '- TurnRate: degrees per frame. 0 (or 180 and up) points straight at the target every frame (a hard homing).',
        '- Range: only targets within this X/Y distance; 0 = any. With nobody in range it keeps going as it was.',
        '- Mode (bits, add them): 1 horizontal only (ignore height), 2 fighters turn to face the target, 4 no gravity '
        'while tracking (fighters). E.g. 6 = face it and fly level.',
        '- TargetOwner 1: a projectile may also go for the fighter who fired it (normally skipped).',
        '- TargetTeammates 1: teammates count too (normally a fighter this object couldn\'t hit because of teams is '
        'skipped).',
        '',
        '## Projectiles',
        '- Steers the projectile\'s own movement (its first kinetic energy, the one its MSC sets when fired); gravity '
        'stays as it was, so give a falling projectile enough Speed.',
        '- A reflected projectile goes back at the fighter who fired it, at any distance (Range doesn\'t apply); if '
        'that fighter is gone, at the nearest other fighter than the reflector.',
        '- Untested in game: projectiles whose movement isn\'t their first energy won\'t turn.',
        '',
        '## Fighters',
        '- Sets their X and Y speed every frame (X as Add / Set_Momentum does, no braking; Y through gravity\'s '
        'energy). Gravity keeps acting (a slow track sags) unless Mode has 4; nothing is left over when it ends.',
        '- Works in the air; on the ground the fighter\'s status may move it its own way.',
        '',
        '## Gotchas',
        '- Read the frames left with TRACK_FRAMES (0x0F000331); compare it to react when tracking ends.',
        '- The target is picked again every frame: with several fighters it switches to whoever is nearest.',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Last_Hit_Get': [
        '## How it works',
        'Stores a player slot (1-8; 0 = none) in a float variable:',
        '- Which 0: the last fighter this one hit (its current attack\'s newest hit; once the attack is over, a '
        'fighter whose last attacker is this one). The same fighter is Target 2 of the other commands.',
        '- Which 1: the last fighter that hit this one (the game\'s own record, the player number it keeps for the hit '
        'effects\' colour, so its projectiles count). Target 11 of the other commands.',
        '',
    ] + VARS + [
        '',
        '## Gotchas',
        '- You rarely need the slot itself: Target 2 / 11 act on these fighters directly. The slot is for keeping '
        'who it was (the next hit may be on someone else), for the SLOTn_ position / shared variables, or for '
        'comparing with Target_Slot_Get.',
        '- From an article\'s script it finds nobody (0).',
        '- Unconfirmed: what "hit last" holds before the fighter\'s first hit (slot 1 or none).',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Target_Slot_Get': [
        '## How it works',
        'Stores which player slot (1-8) a target is in a float variable; 0 = none, or not a fighter. Target 0 gives '
        'this fighter\'s own slot.',
        '',
    ] + TARGETS + [''] + VARS + [
        '',
        '## Gotchas',
        '- A player slot number n is Target 2 + n of the other commands and the SLOTn_ variables (POS_SLOTn_X, '
        'SLOTn_SHARED_k, ...).',
        '',
        NOT_VIEWER,
        NEEDS,
    ],
    'Thread_Start': [
        '## How it works',
        'Thread_Start(ID, Flags){ ... }: the commands in the block run on their own, frame by frame, while the script '
        'goes on past the block (the script itself jumps over it). Any command works inside: FRAME, WAIT, True / '
        'Else, loops, hitboxes, effects, sounds, CALL.',
        '- The thread\'s first frame is the frame after Thread_Start; FRAME inside counts from the thread\'s start.',
        '- It runs 1 frame per game frame, whatever the animation\'s speed.',
        '- It keeps running after the animation ends or changes, and while the character is KO\'d.',
        '- It ends at the end of its block, at Thread_Stop(ID), or when the object is set up again (a projectile\'s '
        'next use).',
        '',
        '## Parameters in practice',
        '- Offset: words to the end of the block; Sm4shCommand works it out from the braces (write 0).',
        '- ID: any number of yours. Thread_Start with an ID that is already running restarts that thread.',
        '- Flags: bit 1 = keep running during hitlag (normally the thread pauses while the object is in hitlag).',
        '',
        '## Gotchas',
        '- Up to 32 threads at once, across all objects.',
        '- Hitboxes made by a thread while the fighter is in a KO status may be ignored by the game.',
        '- Kirby: don\'t leave a thread running in a copy ability\'s script when Kirby can lose the copy: the script '
        'may be unloaded with it and the game would crash.',
        '- Sm4shCommand ends the block with a Script_End when it compiles (and hides it when it decompiles); older '
        'versions (before v1.4.6) cut the script at that Script_End when the file was opened again.',
        '- Hitbox Viewer: the block runs on its own from the frame after Thread_Start, alongside the script.',
        '- Untested in game: whether a respawn counts as "set up again" and ends the threads.',
        '',
        NEEDS,
    ],
    'Thread_Stop': [
        '## How it works',
        'Stops this object\'s thread with that ID (the ID given to Thread_Start); -1 stops every thread of this '
        'object. Stopping a thread that isn\'t running does nothing.',
        '',
        '## Gotchas',
        '- Called from inside the thread it stops, the thread finishes the current frame first (the rest of that '
        'frame\'s commands still run).',
        '- Only this object\'s threads: a projectile\'s threads are the projectile\'s.',
        '- Threads also end on their own at the end of their block: Thread_Stop is for ending one early (the move was '
        'cancelled, the fighter was hit, ...).',
        '',
        NEEDS,
    ],
}

# --- examples (Events.cfg "Example:" lines; Insert Example adds them all) -------------------------------------------
EXAMPLES = {
    'Extra_Special_Hitbox': [
        '// Example 1: a 12% hit: half the hitstun, the opponent frozen 20 frames, (almost) no DI',
        'FRAME(Frames=5)',
        _hitbox('Extra_Special_Hitbox', HitstunMul=0.5, HitstopFrames=20, DIMul=0.001),
        'WAIT(Frames=3)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 2: a multi-hit (IDs 0 and 1 every 4 frames) that holds the opponent: 2 frames more hitstun and',
        '// no DI on each hit, then a launcher with 1.3x hitstun and a heavy freeze on both fighters',
        'FRAME(Frames=4)',
        'Set_Loop(Iterations=4){',
        '    ' + _hitbox('Extra_Special_Hitbox', Damage=1.5, Angle=80, KBG=20, BKB=20, Size=4, Z=8, Hitlag=0.5,
                         SFXLevel=0, HitstunMul=-2, DIMul=0.001),
        '    ' + _hitbox('Extra_Special_Hitbox', ID=1, Damage=1.5, Angle=80, KBG=20, BKB=20, Size=6, Z=14,
                         Hitlag=0.5, SFXLevel=0, HitstunMul=-2, DIMul=0.001),
        '    WAIT(Frames=2)',
        '    Remove_All_Hitboxes()',
        '    Hit_Log_Clear(Part=0)',
        '    WAIT(Frames=2)',
        '    Goto(Offset=0)',
        '}',
        _hitbox('Extra_Special_Hitbox', Damage=6, Angle=45, KBG=130, BKB=50, Size=7, Z=10, SFXLevel=2,
                HitstunMul=1.3, HitstopMul=1.5, SelfHitstopMul=1.5),
        'WAIT(Frames=2)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 3: a stronger sweet spot only if special is still held on frame 10',
        'FRAME(Frames=10)',
        'Input_Compare(Target=0, Input=1, Method=0, Value=1)',
        'True(Offset=0){',
        '    ' + _hitbox('Extra_Special_Hitbox', Damage=18, KBG=95, BKB=60, Size=6, SFXLevel=2, HitstopFrames=16,
                         SelfHitstopFrames=12),
        '}',
        'Else(Offset=0){',
        '    ' + _hitbox('Special_Hitbox', Damage=11, Size=5),
        '}',
        'WAIT(Frames=3)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 4 (exe_v43): a hit launched the way the control stick points on frame 8. STICK_ANGLE is the',
        '// stick\'s angle along the fighter\'s facing (0 forward, 90 up, 180 back, 270 down), so it works facing',
        '// either way. (With the stick in neutral it reads 0: forward.)',
        'FRAME(Frames=8)',
        _hitbox('Extra_Special_Hitbox', Damage=10, Angle='STICK_ANGLE', KBG=80, BKB=50, Size=6, Z=8),
        'WAIT(Frames=4)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 5 (exe_v43): the same, but the angle follows the stick every frame while the hitbox is out',
        '// (|FOLLOW), and a neutral stick sends straight up instead (STICK_LEN: how far the stick is pushed)',
        'FRAME(Frames=8)',
        'Float_Var_Compare(Variable=STICK_LEN, Method=5, Value=0.3)',
        'True(Offset=0){',
        '    ' + _hitbox('Extra_Special_Hitbox', Damage=10, Angle='STICK_ANGLE|FOLLOW', KBG=80, BKB=50, Size=6, Z=8),
        '}',
        'Else(Offset=0){',
        '    ' + _hitbox('Extra_Special_Hitbox', Damage=10, Angle=90, KBG=80, BKB=50, Size=6, Z=8),
        '}',
        'WAIT(Frames=10)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 6 (exe_v43): launch along the fighter\'s current rotation. Rotation_Get stores it in VAR_1',
        '// (degrees; Axis 0 = about X: a fighter\'s forward tilt, as Rotation_Set\'s X), and the hitbox takes',
        '// VAR_1 as its angle. (Angle=ROT_X does the same without the variable; Angle=ROT_X|NEG takes minus it:',
        '// tilted 30 degrees forward, nose down, launches 30 degrees down, 330.)',
        'FRAME(Frames=6)',
        'Rotation_Get(Target=0, Axis=0, Variable=VAR_1)',
        _hitbox('Extra_Special_Hitbox', Damage=9, Angle='VAR_1', KBG=90, BKB=40, Size=5, Z=7),
        'WAIT(Frames=3)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 7 (exe_v43): a hitbox that grows while special is held: damage 4% to 14% and size 3 to 7 over',
        '// 20 frames (New_Vars charge / reach; SUB_FLOAT_2 of a negative step adds). |FOLLOW reads them again every',
        '// frame while the hitbox is out',
        'New_Var(Name=charge, Type=float, Initial=4, Scope=move)',
        'New_Var(Name=reach, Type=float, Initial=3, Scope=move)',
        'SET_FLOAT(Value=-0.5, Variable=VAR_2)',
        'SET_FLOAT(Value=-0.2, Variable=VAR_3)',
        'FRAME(Frames=5)',
        _hitbox('Extra_Special_Hitbox', Damage='charge|FOLLOW', Angle=45, KBG=90, BKB=50, Size='reach|FOLLOW', Z=8),
        'Set_Loop(Iterations=20){',
        '    Input_Compare(Target=0, Input=1, Method=0, Value=1)',
        '    True(Offset=0){',
        '        SUB_FLOAT_2(Variable=charge, SourceVariable=VAR_2)',
        '        SUB_FLOAT_2(Variable=reach, SourceVariable=VAR_3)',
        '    }',
        '    WAIT(Frames=1)',
        '    Goto(Offset=0)',
        '}',
        'Remove_All_Hitboxes()',
    ],
    'Extra_Extended_Special_Hitbox': [
        '// Example 1: a sword swing as a capsule from (0, 8, 6) to (0, 8, 14): half the hitstun, a 20-frame freeze',
        '// on the opponent, no DI',
        'FRAME(Frames=5)',
        _hitbox('Extra_Extended_Special_Hitbox', HitstunMul=0.5, HitstopFrames=20, DIMul=0.001),
        'WAIT(Frames=3)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 2: a long beam on the hand bone (Bone=0x1C here: use your fighter\'s) whose tip is a sweet',
        '// spot: double DI on the sour part, 1.5x hitstun and a longer freeze for the attacker on the tip',
        'FRAME(Frames=12)',
        _hitbox('Extra_Extended_Special_Hitbox', ID=0, Bone='0x1C', Damage=8, Angle=50, KBG=80, BKB=40, Size=3, X=0,
                Y=0, Z=0, X2=0, Y2=0, Z2=20, DIMul=2),
        _hitbox('Extra_Extended_Special_Hitbox', ID=1, Bone='0x1C', Damage=15, Angle=40, KBG=90, BKB=50, Size=4,
                X=0, Y=0, Z=20, X2=0, Y2=0, Z2=26, SFXLevel=2, HitstunMul=1.5,
                SelfHitstopFrames=14),
        'WAIT(Frames=4)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 3 (exe_v43): a long sweep that launches the way the C-stick points on screen, followed every',
        '// frame (CSTICK_ANGLE_RAW is 0 = right, 90 = up whichever way the fighter faces; |WORLD turns it into the',
        '// hitbox\'s angle for the facing: the same as CSTICK_ANGLE)',
        'FRAME(Frames=10)',
        _hitbox('Extra_Extended_Special_Hitbox', Damage=11, Angle='CSTICK_ANGLE_RAW|WORLD|FOLLOW', KBG=85, BKB=45,
                Size=4, Z=4, Z2=18),
        'WAIT(Frames=6)',
        'Remove_All_Hitboxes()',
    ],
    'Hit_Check': [
        '// Example 1: a jump cancel on hit or on shield (MSC\'s AttackModule(0x2727, 6)), from frame 20',
        'FRAME(Frames=20)',
        'Hit_Check(Target=0, When=0, Kinds=6)',
        'True(Offset=0){',
        '    Input_Set(Target=0, Input=2, Value=2)',
        '}',
        '',
        '// Example 2: a follow-up only when the first hit landed on a body, not a shield',
        'FRAME(Frames=6)',
        _hitbox('Hitbox', Damage=5, Angle=80, KBG=30, BKB=60, Size=5, Z=8),
        'WAIT(Frames=2)',
        'Remove_All_Hitboxes()',
        'Hit_Check(Target=0, When=0, Kinds=2)',
        'True(Offset=0){',
        '    FRAME(Frames=14)',
        '    ' + _hitbox('Hitbox', Damage=9, Angle=45, KBG=110, BKB=50, Size=7, Y=12, Z=10),
        '    WAIT(Frames=3)',
        '    Remove_All_Hitboxes()',
        '}',
        'Else(Offset=0){',
        '    // whiffed or shielded: a longer ending',
        '    Set_Frame_Duration(Speed=1.5)',
        '}',
        '',
        '// Example 3: react on the very frame the hitbox connects (test every frame while it\'s out)',
        'FRAME(Frames=8)',
        _hitbox('Hitbox', Damage=10, Size=6, Z=9),
        'Set_Loop(Iterations=4){',
        '    Hit_Check(Target=0, When=1, Kinds=2)',
        '    True(Offset=0){',
        '        Graphic_Effect(Graphic=0x1000017, Bone=0, X=0, Y=8, Z=9, XRot=0, YRot=0, ZRot=0, Size=0.6, RandomX=0, '
        'RandomY=0, RandomZ=0, RandomXRot=0, RandomYRot=0, RandomZRot=0, Terminate=0)',
        '    }',
        '    WAIT(Frames=1)',
        '    Goto(Offset=0)',
        '}',
        'Remove_All_Hitboxes()',
    ],
    'Hit_Get': [
        '// Example 1: different endings for hit, shield and whiff',
        'FRAME(Frames=18)',
        'Hit_Get(Target=0, When=0, Variable=VAR_0)',
        '// VAR_0: 2 hit a hurtbox, 4 hit a shield, 6 both, 0 nothing',
        'Float_Var_Compare(Variable=VAR_0, Method=0, Value=4)',
        'True(Offset=0){',
        '    // only a shield: a slower, punishable ending (each script frame lasts 1.4 game frames)',
        '    Set_Frame_Duration(Speed=1.4)',
        '}',
        'Float_Var_Compare(Variable=VAR_0, Method=0, Value=2)',
        'True(Offset=0){',
        '    // a clean hit: a faster ending',
        '    Set_Frame_Duration(Speed=0.8)',
        '}',
        '',
        '// Example 2: did the nearest opponent\'s attack hit anything since its move started?',
        'Hit_Get(Target=1, When=0, Variable=VAR_1)',
        'Float_Var_Compare(Variable=VAR_1, Method=3, Value=2)',
    ],
    'Hit_Reset': [
        '// Example: two hitboxes, and a bonus only if the SECOND one connects',
        'FRAME(Frames=5)',
        _hitbox('Hitbox', Damage=4, Angle=70, KBG=40, BKB=40, Size=5, Z=8),
        'WAIT(Frames=3)',
        'Remove_All_Hitboxes()',
        '// forget the first hit (SELF_HIT back to 0)',
        'Hit_Reset()',
        'FRAME(Frames=20)',
        _hitbox('Hitbox', Damage=9, Angle=45, KBG=100, BKB=40, Size=6, Y=10, Z=10),
        'WAIT(Frames=3)',
        'Remove_All_Hitboxes()',
        'Float_Var_Compare(Variable=SELF_HIT, Method=0, Value=1)',
        'True(Offset=0){',
        '    // the second hitbox connected: freeze the fighter it hit for 10 more frames',
        '    Hitstop_Set(Target=2, Frames=10, Shake=1)',
        '}',
        '// (Hit_Check(Target=0, When=0, Kinds=2) reads the same flag, with the kinds)',
    ],
    'Hit_Log_Clear': [
        '// Example 1: a second wave of the same hitboxes (Part 0) that can hit the fighters the first one hit',
        'FRAME(Frames=5)',
        _hitbox('Special_Hitbox', Damage=5, Angle=80, KBG=30, BKB=50, Size=8),
        'WAIT(Frames=2)',
        'Remove_All_Hitboxes()',
        'FRAME(Frames=20)',
        'Hit_Log_Clear(Part=0)',
        _hitbox('Special_Hitbox', Damage=7, Angle=45, KBG=100, BKB=50, Size=9),
        'WAIT(Frames=2)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 2: a lingering field that hits every 6 frames, every part cleared each time',
        'FRAME(Frames=10)',
        'Set_Loop(Iterations=5){',
        '    Hit_Log_Clear(Part=-1)',
        '    ' + _hitbox('Hitbox', Damage=2, Angle=90, KBG=10, BKB=30, Size=12, Y=6, Z=0, SFXLevel=0),
        '    WAIT(Frames=2)',
        '    Remove_All_Hitboxes()',
        '    WAIT(Frames=4)',
        '    Goto(Offset=0)',
        '}',
    ],
    'Status_Get': [
        '// Example 1: a command grab-style bonus if the nearest opponent is shielding (status 0x1C, Guard)',
        'FRAME(Frames=6)',
        'Status_Get(Target=1, Variable=VAR_0)',
        'Float_Var_Compare(Variable=VAR_0, Method=0, Value=0x1C)',
        'True(Offset=0){',
        '    Status_Set(Target=1, Status=0x59)',
        '}',
        '',
        '// Example 2: is the last fighter hit in tumble (0x47 DamageFly)?',
        'Status_Get(Target=2, Variable=VAR_1)',
        'Float_Var_Compare(Variable=VAR_1, Method=0, Value=0x47)',
    ],
    'Status_Set': [
        '// Example 1: a hit that shield-breaks the fighter it hit (0x59 = the shield break launch)',
        'FRAME(Frames=10)',
        _hitbox('Hitbox', Damage=8, Angle=361, KBG=100, BKB=40, Size=5, Z=8),
        'WAIT(Frames=2)',
        'Remove_All_Hitboxes()',
        'Hit_Check(Target=0, When=0, Kinds=2)',
        'True(Offset=0){',
        '    Status_Set(Target=2, Status=0x59)',
        '}',
        '',
        '// Example 2: end this move early in the air: fall (0xE) if this fighter is airborne (situation 2)',
        'FRAME(Frames=25)',
        'Input_Compare(Target=0, Input=22, Method=0, Value=2)',
        'True(Offset=0){',
        '    Status_Set(Target=0, Status=0xE)',
        '}',
    ],
    'Hitstun_Get': [
        '// Example: a follow-up only if the fighter just hit still has more than 15 hitstun frames left',
        'FRAME(Frames=24)',
        'Hitstun_Get(Target=2, What=0, Variable=VAR_0)',
        'Float_Var_Compare(Variable=VAR_0, Method=5, Value=15)',
        'True(Offset=0){',
        '    ' + _hitbox('Hitbox', Damage=6, Angle=80, KBG=60, BKB=60, Size=6, Y=12, Z=6),
        '    WAIT(Frames=2)',
        '    Remove_All_Hitboxes()',
        '}',
        '',
        '// the hitstun the last fighter hit was given by its last hit',
        'Hitstun_Get(Target=2, What=1, Variable=VAR_1)',
    ],
    'Hitstun_Set': [
        '// Example 1: a weak poke whose victim can act right after the hitlag',
        'FRAME(Frames=4)',
        _hitbox('Hitbox', Damage=3, Angle=361, KBG=20, BKB=20, Size=4, Z=7, SFXLevel=0),
        'WAIT(Frames=2)',
        'Remove_All_Hitboxes()',
        'Hit_Check(Target=0, When=0, Kinds=2)',
        'True(Offset=0){',
        '    // wait out the hitlag (about 6 frames for a 3% hit), then end the hitstun',
        '    WAIT(Frames=7)',
        '    Hitstun_Set(Target=2, Frames=0)',
        '}',
        '',
        '// Example 2: lock the fighter in player slot 2 in hitstun for 30 more frames',
        'Hitstun_Set(Target=4, Frames=30)',
    ],
    'Hitstop_Set': [
        '// Example 1: a dramatic freeze on the fighter just hit, 8 frames, shaking',
        'FRAME(Frames=12)',
        _hitbox('Hitbox', Damage=14, Angle=361, KBG=95, BKB=50, Size=6, Z=9),
        'WAIT(Frames=1)',
        'Hit_Check(Target=0, When=0, Kinds=2)',
        'True(Offset=0){',
        '    Hitstop_Set(Target=2, Frames=8, Shake=1)',
        '    // and freeze this fighter still for 4 frames',
        '    Hitstop_Set(Target=0, Frames=4, Shake=0)',
        '}',
        'WAIT(Frames=2)',
        'Remove_All_Hitboxes()',
    ],
    'Damage_Get': [
        '// Example: a finisher that only launches hard at 100% or more',
        'FRAME(Frames=14)',
        'Damage_Get(Target=1, Variable=VAR_0)',
        'Float_Var_Compare(Variable=VAR_0, Method=3, Value=100)',
        'True(Offset=0){',
        '    ' + _hitbox('Hitbox', Damage=16, Angle=40, KBG=110, BKB=60, Size=7, Z=10, SFXLevel=2),
        '}',
        'Else(Offset=0){',
        '    ' + _hitbox('Hitbox', Damage=10, Angle=70, KBG=70, BKB=50, Size=7, Z=10),
        '}',
        'WAIT(Frames=3)',
        'Remove_All_Hitboxes()',
    ],
    'Damage_Set': [
        '// Example 1: heal the last fighter that hit this one completely',
        'Damage_Set(Target=11, Percent=0)',
        '',
        '// Example 2: a fixed 50% on the fighter just hit, if the move connected',
        'Hit_Check(Target=0, When=0, Kinds=2)',
        'True(Offset=0){',
        '    Damage_Set(Target=2, Percent=50)',
        '}',
        '',
        '// Example 3: heal this fighter by 10% and add 5% to the nearest opponent (Damage_Set only takes a fixed',
        '// number: amounts go through the damage variables; SUB_FLOAT_2 subtracts the source variable)',
        'SET_FLOAT(Value=10, Variable=VAR_0)',
        'SUB_FLOAT_2(Variable=SELF_DAMAGE, SourceVariable=VAR_0)',
        'SET_FLOAT(Value=-5, Variable=VAR_1)',
        'SUB_FLOAT_2(Variable=OPP_DAMAGE, SourceVariable=VAR_1)',
    ],
    'Body_State_Set': [
        '// Example 1: intangible for the first 10 frames of the move',
        'FRAME(Frames=1)',
        'Body_State_Set(Target=0, State=0, Frames=10)',
        '',
        '// Example 2: invincible (hits connect but do nothing) for 20 frames from frame 5',
        'FRAME(Frames=5)',
        'Body_State_Set(Target=0, State=1, Frames=20)',
        '',
        '// Example 3: give the fighter just hit 30 frames of intangibility (a "mercy" window)',
        'Hit_Check(Target=0, When=0, Kinds=2)',
        'True(Offset=0){',
        '    Body_State_Set(Target=2, State=0, Frames=30)',
        '}',
    ],
    'Armor_Set': [
        '// Example 1: knockback armor (anything under 60 knockback) during the wind-up, then none',
        'FRAME(Frames=4)',
        'Armor_Set(Target=0, Type=2, Threshold=60)',
        'FRAME(Frames=14)',
        'Armor_Set(Target=0, Type=0, Threshold=0)',
        '',
        '// Example 2: super armor during the active frames only',
        'FRAME(Frames=15)',
        'Armor_Set(Target=0, Type=1, Threshold=0)',
        _hitbox('Hitbox', Damage=20, Angle=361, KBG=90, BKB=60, Size=8, Z=10),
        'WAIT(Frames=4)',
        'Remove_All_Hitboxes()',
        'Armor_Set(Target=0, Type=0, Threshold=0)',
        '',
        '// Example 3: shrug off hits under 8% for the rest of a charge',
        'Armor_Set(Target=0, Type=3, Threshold=8)',
    ],
    'Item_State_Set': [
        '// Example 1: the last fighter hit turns metal (the Metal Box\'s), as Hero\'s Metal Slash',
        'FRAME(Frames=9)',
        _hitbox('Hitbox', Damage=10, Size=6, Z=9),
        'WAIT(Frames=2)',
        'Remove_All_Hitboxes()',
        'Hit_Check(Target=0, When=0, Kinds=2)',
        'True(Offset=0){',
        '    Item_State_Set(Target=2, Code=1)',
        '}',
        '',
        '// Example 2: this fighter grows (Super Mushroom), and the camera closes in for a moment',
        'Item_State_Set(Target=0, Code=3)',
        'Item_State_Set(Target=0, Code=8)',
        'WAIT(Frames=40)',
        'Item_State_Set(Target=0, Code=9)',
    ],
    'Stage_Collision_Set': [
        '// Example: a held hit that drags the fighter it hit through the floor for 20 frames',
        '// (its status sets its own collision again, so set it every frame), then gives it back',
        'Set_Loop(Iterations=20){',
        '    Stage_Collision_Set(Target=2, Mode=0)',
        '    Position_Set(Target=2, X=0, Y=-1, Z=0, Mode=1)',
        '    WAIT(Frames=1)',
        '    Goto(Offset=0)',
        '}',
        'Stage_Collision_Set(Target=2, Mode=5)',
        '',
        '// the same as a thread, so it keeps going if this move ends first',
        'Thread_Start(Offset=0, ID=2, Flags=1){',
        '    Set_Loop(Iterations=20){',
        '        Stage_Collision_Set(Target=2, Mode=0)',
        '        WAIT(Frames=1)',
        '        Goto(Offset=0)',
        '    }',
        '    Stage_Collision_Set(Target=2, Mode=5)',
        '}',
    ],
    'Leave_Ground_Cancel': [
        '// Example 1: Diddy Kong\'s dash attack (AttackDash, game script) keeps cartwheeling off the stage',
        'Leave_Ground_Cancel(Enabled=0)',
        'FRAME(Frames=9)',
        'Hitbox(ID=1, Part=0, Bone=0, Damage=2, Angle=0x28, KBG=0x64, FKB=0x37, BKB=0, Size=3.5, X=0, Y=7, Z=8.5, '
        'Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=1, SFXType=1, '
        'Ground/Air=0x80000003, Direct/Indirect=1, Type=6)',
        'WAIT(Frames=1)',
        'Remove_All_Hitboxes()',
        'FRAME(Frames=18)',
        'Hitbox(ID=0, Part=0, Bone=0, Damage=2, Angle=0x16E, KBG=0x64, FKB=0x3E, BKB=0, Size=3.5, X=0, Y=7, Z=8.5, '
        'Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=1, SFXType=1, Ground/Air=3, '
        'Direct/Indirect=1, Type=6)',
        'WAIT(Frames=1)',
        'Remove_All_Hitboxes()',
        'FRAME(Frames=24)',
        'Hitbox(ID=0, Part=0, Bone=0, Damage=3, Angle=0x4E, KBG=0x5A, FKB=0, BKB=0x50, Size=4.5, X=0, Y=6, Z=8.5, '
        'Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=2, SFXType=1, Ground/Air=3, '
        'Direct/Indirect=1, Type=6)',
        'WAIT(Frames=1)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 2: goes on in the air only if lifted (it still stops at edges); normal again from frame 20',
        'Leave_Ground_Cancel(Enabled=2)',
        'FRAME(Frames=20)',
        'Leave_Ground_Cancel(Enabled=1)',
    ],
    'Gravity_Set': [
        '// Example 1: Diddy Kong\'s dash attack (AttackDash, game script) cartwheels off the stage and floats down',
        '// (gravity 0.02 instead of 0.105, falling at most 0.6 instead of 1.75)',
        'Leave_Ground_Cancel(Enabled=0)',
        'Gravity_Set(Accel=0.02, MaxFall=0.6, Mode=0)',
        'FRAME(Frames=9)',
        'Hitbox(ID=1, Part=0, Bone=0, Damage=2, Angle=0x28, KBG=0x64, FKB=0x37, BKB=0, Size=3.5, X=0, Y=7, Z=8.5, '
        'Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=1, SFXType=1, '
        'Ground/Air=0x80000003, Direct/Indirect=1, Type=6)',
        'WAIT(Frames=1)',
        'Remove_All_Hitboxes()',
        'FRAME(Frames=18)',
        'Hitbox(ID=0, Part=0, Bone=0, Damage=2, Angle=0x16E, KBG=0x64, FKB=0x3E, BKB=0, Size=3.5, X=0, Y=7, Z=8.5, '
        'Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=1, SFXType=1, Ground/Air=3, '
        'Direct/Indirect=1, Type=6)',
        'WAIT(Frames=1)',
        'Remove_All_Hitboxes()',
        'FRAME(Frames=24)',
        'Hitbox(ID=0, Part=0, Bone=0, Damage=3, Angle=0x4E, KBG=0x5A, FKB=0, BKB=0x50, Size=4.5, X=0, Y=6, Z=8.5, '
        'Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=0, Rebound=0, ShieldDamage=0, SFXLevel=2, SFXType=1, Ground/Air=3, '
        'Direct/Indirect=1, Type=6)',
        'WAIT(Frames=1)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 2: a floaty aerial: half the fighter\'s own gravity and max fall from frame 6, its own again at 30',
        'FRAME(Frames=6)',
        'Gravity_Set(Accel=0.5, MaxFall=0.5, Mode=1)',
        'FRAME(Frames=30)',
        'Gravity_Set(Accel=-1, MaxFall=-1, Mode=0)',
        '',
        '// Example 3: a hover special: a rise slows to a stop and the fall stops at once (no fast fall), then from',
        '// frame 40 a heavy drop (gravity 0.2, max fall 3)',
        'Gravity_Set(Accel=0.03, MaxFall=0, Mode=6)',
        'FRAME(Frames=40)',
        'Gravity_Set(Accel=0.2, MaxFall=3, Mode=0)',
        '',
        '// Example 4: only if the fighter isn\'t already floaty (its gravity in effect under 0.05: leave it)',
        'Float_Var_Compare(Variable=GRAVITY, Method=3, Value=0.05)',
        'True(Offset=0){',
        '    Gravity_Set(Accel=0.03, MaxFall=1, Mode=0)',
        '}',
    ],
    'New_Var': [
        '// Example 1: a charge counter (Scope=move: 0 at every use of the move). Counts the frames special is held',
        '// from frame 5 to 34, then a stronger hitbox if it was held for 20 of them',
        'New_Var(Name=charge, Type=int, Initial=0, Scope=move)',
        'FRAME(Frames=5)',
        'Set_Loop(Iterations=30){',
        '    Input_Compare(Target=0, Input=1, Method=0, Value=1)',
        '    True(Offset=0){',
        '        INC_INT(Variable=charge)',
        '    }',
        '    WAIT(Frames=1)',
        '    Goto(Offset=0)',
        '}',
        'Int_Var_Compare(Variable=charge, Method=3, Value=20)',
        'True(Offset=0){',
        '    ' + _hitbox('Hitbox', Damage=18, BKB=60, Size=7, Z=9),
        '}',
        'Else(Offset=0){',
        '    ' + _hitbox('Hitbox', Damage=10, Size=5, Z=8),
        '}',
        'WAIT(Frames=3)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 2: every third use of this move is stronger (Scope=object: the count is kept between uses,',
        '// until the fighter is KO\'d)',
        'New_Var(Name=uses, Type=int, Initial=0, Scope=object)',
        'INC_INT(Variable=uses)',
        'FRAME(Frames=10)',
        'Int_Var_Compare(Variable=uses, Method=3, Value=3)',
        'True(Offset=0){',
        '    ' + _hitbox('Hitbox', Damage=16, BKB=60, Size=6, Z=8),
        '    SET_INT(Value=0, Variable=uses)',
        '}',
        'Else(Offset=0){',
        '    ' + _hitbox('Hitbox', Damage=8, Size=5, Z=8),
        '}',
        'WAIT(Frames=3)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 3: float variables with the target commands: how far the move has risen since it started',
        'New_Var(Name=start_y, Initial=0, Scope=move)',
        'New_Var(Name=now_y, Initial=0, Scope=move)',
        'Position_Get(Target=0, Axis=1, Variable=start_y)',
        'FRAME(Frames=20)',
        'Position_Get(Target=0, Axis=1, Variable=now_y)',
        '// now_y - start_y (SUB_FLOAT_2: Variable -= SourceVariable)',
        'SUB_FLOAT_2(Variable=now_y, SourceVariable=start_y)',
        'Float_Var_Compare(Variable=now_y, Method=5, Value=15)',
        'True(Offset=0){',
        '    // risen more than 15 units: a meteor hitbox',
        '    ' + _hitbox('Hitbox', Damage=12, Angle=270, BKB=30, Size=6, Y=2, Z=4),
        '}',
        '',
        '// Example 4: a hit counter kept on the fighter for the stock (game script of any move that should count),',
        '// read in another script, e.g. the up special\'s, which declares it too (the same name: the same slot)',
        'New_Var(Name=hits_landed, Type=int, Initial=0)',
        'FRAME(Frames=12)',
        _hitbox('Hitbox', Damage=6, Size=5, Z=8),
        'WAIT(Frames=3)',
        'Remove_All_Hitboxes()',
        'Hit_Check(Target=0, When=0, Kinds=2)',
        'True(Offset=0){',
        '    INC_INT(Variable=hits_landed)',
        '}',
        '',
        '// Example 5: the same variable with a fixed slot (so MSC can use WorkModuleF(0, 0x0F000385)), as a float',
        'New_Var(Name=power, Type=float, Initial=1, Scope=object, Slot=5)',
        'SET_FLOAT(Value=1.5, Variable=power)',
    ],
    'Input_Compare': [
        '// Example 1: on frame 12, a stronger hitbox if special is still held',
        'FRAME(Frames=12)',
        'Input_Compare(Target=0, Input=1, Method=0, Value=1)',
        'True(Offset=0){',
        '    ' + _hitbox('Hitbox', Damage=14, BKB=50, Size=6, Z=8),
        '}',
        'Else(Offset=0){',
        '    ' + _hitbox('Hitbox', Damage=9, Size=5, Z=8),
        '}',
        'WAIT(Frames=3)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 2: a follow-up if attack is PRESSED (input 8) any time in frames 20-29',
        '// (VAR_0 keeps its value from the last time: clear it first)',
        'SET_FLOAT(Value=0, Variable=VAR_0)',
        'FRAME(Frames=20)',
        'Set_Loop(Iterations=10){',
        '    Input_Compare(Target=0, Input=8, Method=0, Value=1)',
        '    True(Offset=0){',
        '        SET_FLOAT(Value=1, Variable=VAR_0)',
        '    }',
        '    WAIT(Frames=1)',
        '    Goto(Offset=0)',
        '}',
        'Float_Var_Compare(Variable=VAR_0, Method=0, Value=1)',
        'True(Offset=0){',
        '    ' + _hitbox('Hitbox', Damage=7, Angle=80, KBG=70, BKB=50, Size=6, Y=12, Z=6),
        '    WAIT(Frames=2)',
        '    Remove_All_Hitboxes()',
        '}',
        '',
        '// Example 3: the stick held forward past halfway (Method 5: >), or down (stick Y < -0.5)',
        'Input_Compare(Target=0, Input=16, Method=5, Value=0.5)',
        'Input_Compare(Target=0, Input=17, Method=4, Value=-0.5)',
    ],
    'Input_Get': [
        '// Example 1: remember the stick\'s height at the start of the move, aim the hitbox with it later',
        'FRAME(Frames=1)',
        'Input_Get(Target=0, Input=17, Variable=VAR_0)',
        'FRAME(Frames=10)',
        'Float_Var_Compare(Variable=VAR_0, Method=5, Value=0.3)',
        'True(Offset=0){',
        '    // stick was up: an upward-angled hit',
        '    ' + _hitbox('Hitbox', Damage=9, Angle=70, Size=6, Y=14, Z=7),
        '}',
        'Else(Offset=0){',
        '    ' + _hitbox('Hitbox', Damage=9, Angle=40, Size=6, Y=8, Z=9),
        '}',
        'WAIT(Frames=3)',
        'Remove_All_Hitboxes()',
        '',
        '// Example 2: the nearest opponent\'s shield HP (input 26) and situation (22: 0 ground, 1 ledge, 2 air)',
        'Input_Get(Target=1, Input=26, Variable=VAR_1)',
        'Input_Get(Target=1, Input=22, Variable=VAR_2)',
    ],
    'Input_Set': [
        '// Example 1: the fighter just hit jumps (one press) and can\'t use its controller for 30 frames',
        'Hit_Check(Target=0, When=0, Kinds=2)',
        'True(Offset=0){',
        '    Input_Set(Target=2, Input=21, Value=1)',
        '    Input_Set(Target=2, Input=2, Value=2)',
        '}',
        'WAIT(Frames=30)',
        '// always give the controller back',
        'Input_Set(Target=2, Input=21, Value=0)',
        '',
        '// Example 2: hold this fighter\'s shield for 20 frames, then let go',
        'Input_Set(Target=0, Input=3, Value=1)',
        'WAIT(Frames=20)',
        'Input_Set(Target=0, Input=3, Value=0)',
        '',
        '// Example 3: push player 1\'s stick fully left on screen (input 32) for 15 frames, then release both sticks',
        'Input_Set(Target=3, Input=32, Value=-1)',
        'WAIT(Frames=15)',
        'Input_Set(Target=3, Input=20, Value=0)',
    ],
    'Position_Get': [
        '// Example 1: VAR_0 / VAR_1 = the nearest opponent\'s X / Y; a different move if it\'s above this fighter',
        'Position_Get(Target=1, Axis=0, Variable=VAR_0)',
        'Position_Get(Target=1, Axis=1, Variable=VAR_1)',
        'Position_Get(Target=0, Axis=1, Variable=VAR_2)',
        '// VAR_1 -= VAR_2: the height difference',
        'SUB_FLOAT_2(Variable=VAR_1, SourceVariable=VAR_2)',
        'Float_Var_Compare(Variable=VAR_1, Method=5, Value=20)',
        'True(Offset=0){',
        '    ' + _hitbox('Hitbox', Damage=8, Angle=90, Size=7, Y=18, Z=2),
        '    WAIT(Frames=3)',
        '    Remove_All_Hitboxes()',
        '}',
        '',
        '// Example 2: which way does the last fighter hit face? (1 right, -1 left)',
        'Position_Get(Target=2, Axis=3, Variable=VAR_3)',
    ],
    'Position_Set': [
        '// Example 1: a short blink: 10 forward and 5 up from where this fighter is',
        'FRAME(Frames=8)',
        'Position_Set(Target=0, X=10, Y=5, Z=0, Mode=1)',
        '',
        '// Example 2: pull the fighter just hit 2 units toward this one every frame for 10 frames',
        '// (Mode 1 moves along ITS facing: here it is assumed to face this fighter)',
        'Set_Loop(Iterations=10){',
        '    Position_Set(Target=2, X=2, Y=0, Z=0, Mode=1)',
        '    WAIT(Frames=1)',
        '    Goto(Offset=0)',
        '}',
        '',
        '// Example 3: put player 2 at the world point (0, 30, 0)',
        'Position_Set(Target=4, X=0, Y=30, Z=0, Mode=0)',
    ],
    'Rotation_Get': [
        '// Example: VAR_0 = this article\'s rotation about Z; level it out once it is tilted past 30 degrees',
        'Rotation_Get(Target=0, Axis=2, Variable=VAR_0)',
        'Float_Var_Compare(Variable=VAR_0, Method=5, Value=30)',
        'True(Offset=0){',
        '    Rotation_Set(Target=0, X=0, Y=0, Z=0)',
        '}',
    ],
    'Rotation_Set': [
        '// Example 1: in a projectile\'s script: tilt it 45 degrees about Z',
        'Rotation_Set(Target=0, X=0, Y=0, Z=45)',
        '',
        '// Example 2: make this projectile wobble (+15 / -15 degrees every 3 frames) for 36 frames, in a thread so',
        '// the script goes on (the angles are fixed numbers: Rotation_Set doesn\'t take variables)',
        'Thread_Start(Offset=0, ID=5, Flags=0){',
        '    Set_Loop(Iterations=6){',
        '        Rotation_Set(Target=0, X=0, Y=0, Z=15)',
        '        WAIT(Frames=3)',
        '        Rotation_Set(Target=0, X=0, Y=0, Z=-15)',
        '        WAIT(Frames=3)',
        '        Goto(Offset=0)',
        '    }',
        '    Rotation_Set(Target=0, X=0, Y=0, Z=0)',
        '}',
        '',
        '// Example 3: the last fighter hit back upright',
        'Rotation_Set(Target=2, X=0, Y=0, Z=0)',
    ],
    'Joint_Position_Get': [
        '// Example: VAR_0-2 = player 1\'s waist (joint 11, WaistN for most fighters); something if it\'s above Y 20',
        'Joint_Position_Get(Target=3, Joint=11, VariableX=VAR_0, VariableY=VAR_1, VariableZ=VAR_2)',
        'Float_Var_Compare(Variable=VAR_1, Method=5, Value=20)',
        'True(Offset=0){',
        '    Hitstop_Set(Target=3, Frames=6, Shake=1)',
        '}',
        '',
        '// the nearest opponent\'s waist, to place something there later',
        'Joint_Position_Get(Target=1, Joint=11, VariableX=VAR_3, VariableY=VAR_4, VariableZ=VAR_5)',
    ],
    'Motion_Get': [
        '// Example 1: VAR_0 = the animation frame the last fighter hit is on',
        'Motion_Get(Target=2, What=1, Variable=VAR_0)',
        '',
        '// Example 2: only if this fighter is still playing motion 0x5F (its animation ID: View > Show Animation IDs)',
        'Motion_Get(Target=0, What=0, Variable=VAR_1)',
        'Float_Var_Compare(Variable=VAR_1, Method=0, Value=0x5F)',
        'True(Offset=0){',
        '    // and it\'s past frame 30',
        '    Motion_Get(Target=0, What=1, Variable=VAR_2)',
        '    Float_Var_Compare(Variable=VAR_2, Method=5, Value=30)',
        '    True(Offset=0){',
        '        Set_Frame_Duration(Speed=0.5)',
        '    }',
        '}',
    ],
    'Motion_Set': [
        '// Example 1: play motion 0x5F from frame 10 at half speed',
        'Motion_Set(Target=0, Motion=0x5F, Frame=10, Rate=0.5)',
        '',
        '// Example 2: keep the current animation: skip to frame 20 (rate unchanged)',
        'Motion_Set(Target=0, Motion=-1, Frame=20, Rate=0)',
        '',
        '// Example 3: on hit, slow the fighter just hit\'s animation to a quarter for 30 frames (frame unchanged)',
        'Hit_Check(Target=0, When=0, Kinds=2)',
        'True(Offset=0){',
        '    Motion_Set(Target=2, Motion=-1, Frame=-1, Rate=0.25)',
        '    WAIT(Frames=30)',
        '    // back to normal speed (1)',
        '    Motion_Set(Target=2, Motion=-1, Frame=-1, Rate=1)',
        '}',
    ],
    'Animation_Rate_Set': [
        '// Example 1: everything 1.2x faster for 60 frames, then back',
        'Animation_Rate_Set(Rate=1.2)',
        'WAIT(Frames=60)',
        'Animation_Rate_Set(Rate=1)',
        '',
        '// Example 2: a buff that outlasts the move: a thread puts the rate back after 5 seconds',
        'Animation_Rate_Set(Rate=1.15)',
        'Thread_Start(Offset=0, ID=7, Flags=1){',
        '    FRAME(Frames=300)',
        '    Animation_Rate_Set(Rate=1)',
        '}',
    ],
    'Track_Target': [
        '// Example 1: in a projectile\'s script: home in on the nearest opponent for 60 frames at speed 1.8,',
        '// turning at most 4 degrees a frame, at any distance',
        'Track_Target(Frames=60, Speed=1.8, TurnRate=4, Range=0, Mode=0, TargetOwner=0, TargetTeammates=0)',
        '// stop tracking early (it keeps flying straight)',
        'FRAME(Frames=40)',
        'Track_Target(Frames=0, Speed=0, TurnRate=0, Range=0, Mode=0, TargetOwner=0, TargetTeammates=0)',
        '',
        '// Example 2: a fighter\'s homing dash: face the target, no gravity, only if someone is within 60 units,',
        '// until stopped, with a hitbox the whole way; stop when the hitbox connects',
        'FRAME(Frames=6)',
        'Track_Target(Frames=-1, Speed=2.5, TurnRate=6, Range=60, Mode=6, TargetOwner=0, TargetTeammates=0)',
        _hitbox('Hitbox', Damage=8, Angle=45, KBG=90, BKB=50, Size=6, Y=8, Z=4),
        'Set_Loop(Iterations=30){',
        '    Hit_Check(Target=0, When=1, Kinds=6)',
        '    True(Offset=0){',
        '        SET_FLOAT(Value=0, Variable=TRACK_FRAMES)',
        '    }',
        '    WAIT(Frames=1)',
        '    Goto(Offset=0)',
        '}',
        'Remove_All_Hitboxes()',
        'Track_Target(Frames=0, Speed=0, TurnRate=0, Range=0, Mode=0, TargetOwner=0, TargetTeammates=0)',
    ],
    'Last_Hit_Get': [
        '// Example 1: VAR_0 = the player slot (1-8) this fighter last hit; VAR_1 = the one that last hit it',
        'Last_Hit_Get(Which=0, Variable=VAR_0)',
        'Last_Hit_Get(Which=1, Variable=VAR_1)',
        '',
        '// Example 2: revenge: a stronger hit if the fighter we hit is the one who hit us last',
        'FRAME(Frames=10)',
        _hitbox('Hitbox', Damage=10, Size=6, Z=8),
        'WAIT(Frames=2)',
        'Remove_All_Hitboxes()',
        'Last_Hit_Get(Which=0, Variable=VAR_0)',
        'Last_Hit_Get(Which=1, Variable=VAR_1)',
        'Float_Var_Compare_Var(Variable1=VAR_0, Method=0, Variable2=VAR_1)',
        'True(Offset=0){',
        '    Hitstop_Set(Target=2, Frames=10, Shake=1)',
        '}',
    ],
    'Target_Slot_Get': [
        '// Example 1: VAR_0 = the nearest opponent\'s player slot (1-8); VAR_1 = this fighter\'s own',
        'Target_Slot_Get(Target=1, Variable=VAR_0)',
        'Target_Slot_Get(Target=0, Variable=VAR_1)',
        '',
        '// Example 2: armor only while the nearest opponent is the fighter who hit this one last',
        'Target_Slot_Get(Target=1, Variable=VAR_2)',
        'Last_Hit_Get(Which=1, Variable=VAR_3)',
        'Float_Var_Compare_Var(Variable1=VAR_2, Method=0, Variable2=VAR_3)',
        'True(Offset=0){',
        '    Armor_Set(Target=0, Type=2, Threshold=50)',
        '}',
        '',
        '// Example 3: only if the nearest opponent is player 1',
        'Target_Slot_Get(Target=1, Variable=VAR_4)',
        'Float_Var_Compare(Variable=VAR_4, Method=0, Value=1)',
    ],
    'Thread_Start': [
        '// Example 1: a lingering explosion 30 frames after the move starts, whatever the fighter is doing by then',
        '// (Offset is worked out from the braces when the script compiles)',
        'Thread_Start(Offset=0, ID=1, Flags=0){',
        '    FRAME(Frames=30)',
        '    Graphic_Effect(Graphic=0x1000017, Bone=0, X=0, Y=8, Z=0, XRot=0, YRot=0, ZRot=0, Size=1.5, RandomX=0, '
        'RandomY=0, RandomZ=0, RandomXRot=0, RandomYRot=0, RandomZRot=0, Terminate=0)',
        '    ' + _hitbox('Hitbox', ID=3, Damage=8, Angle=361, KBG=80, BKB=50, Size=9, Y=8, Z=0),
        '    WAIT(Frames=3)',
        '    Remove_Hitbox(ID=3)',
        '}',
        '',
        '// Example 2: a 2-second window (120 frames) where this fighter is intangible every other 10 frames,',
        '// running through hitlag too (Flags 1)',
        'Thread_Start(Offset=0, ID=2, Flags=1){',
        '    Set_Loop(Iterations=6){',
        '        Body_State_Set(Target=0, State=0, Frames=10)',
        '        WAIT(Frames=20)',
        '        Goto(Offset=0)',
        '    }',
        '}',
        '',
        '// Example 3: a delayed effect that depends on what happened: 40 frames later, if the move hit, heal 5%',
        '// (VAR_0 is set below by Hit_Get: 2 or more = it hit something)',
        'SET_FLOAT(Value=0, Variable=VAR_0)',
        'Thread_Start(Offset=0, ID=3, Flags=0){',
        '    FRAME(Frames=40)',
        '    Float_Var_Compare(Variable=VAR_0, Method=3, Value=2)',
        '    True(Offset=0){',
        '        SET_FLOAT(Value=5, Variable=VAR_1)',
        '        SUB_FLOAT_2(Variable=SELF_DAMAGE, SourceVariable=VAR_1)',
        '    }',
        '}',
        '// ... the move\'s hitbox, then remember whether it hit (the thread reads VAR_0 on its frame 40)',
        'FRAME(Frames=10)',
        _hitbox('Hitbox', Damage=9, Size=6, Z=8),
        'WAIT(Frames=3)',
        'Remove_All_Hitboxes()',
        'Hit_Get(Target=0, When=0, Variable=VAR_0)',
    ],
    'Thread_Stop': [
        '// Example 1: stop thread 1 (started by Thread_Start(ID=1)) if it\'s still running',
        'Thread_Stop(ID=1)',
        '',
        '// Example 2: stop every thread this object started',
        'Thread_Stop(ID=-1)',
        '',
        '// Example 3: a thread that ends itself early when the move connects',
        'Thread_Start(Offset=0, ID=4, Flags=0){',
        '    Set_Loop(Iterations=60){',
        '        Hit_Check(Target=0, When=1, Kinds=2)',
        '        True(Offset=0){',
        '            Thread_Stop(ID=4)',
        '        }',
        '        WAIT(Frames=1)',
        '        Goto(Offset=0)',
        '    }',
        '}',
    ],
}
