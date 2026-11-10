#!/usr/bin/env python3
"""Add the universal mechanics (docs/universal-mechanics.md) to a fighter's decompiled MSC:
reverse tilts, tilts / down smash / shield out of run (and out of the dash and the turns), and
roll-off (the MSC side; the rolls' ACMD speed is tools/rolloff_acmd.py).

  python3 tools/universal_mechanics.py IN.c OUT.c [--air-mult 1.0] [--name Fighter] [--ground-uncapped]
  python3 tools/universal_mechanics.py --upgrade IN.c OUT.c   (a fighter patched before Hero's roll-off)

Roll-off momentum is Hero's (fighters/brave/brave.c, his fixes 61-85; CLAUDE.md: Hero's roll-off is
the universal version): sliding off an edge (into Fall, or an attack buffered off the edge) takes the
air speed cap off (flag 0x20000044) and it stays off, through Fall and any air action after it, for as
long as the stick holds the way the fighter moves (raw stick X on screen x that way past 0.3; a frame
attack or special is pressed doesn't count as letting go); landing, a ledge or a hit puts it back
(rolloff_hold_update, every frame from the fighter's per-frame hook, global14's function). Fall's
end doesn't put it back. The speed is set once (the ACMD, at the roll's speed frame) and scaled
once by rolloff_air_speed_mult(); after that it changes the way the game changes it.

--upgrade: a fighter's MSC (decompiled or source) patched by an earlier version of this tool (the
cap back at Fall's end): its roll ends, Fall's end and per-frame hook get Hero's momentum, and
rolloff_hold_x / rolloff_hold_update are added at the end (its speeds and multiplier unchanged).

--ground-uncapped (fighters the user picks): the roll's speed isn't held to the ground speed limit.
Every roll frame, KineticModule(0x15, 3, -1, -1): no speed limit on energy 3 (the stick-driven
energy kinetic type 0x6 sets up, which the roll's ACMD speed goes into), the game's own pattern
after an energy reset (KineticModule(0xe, 3, ...) then (0x15, 3, -1, -1)). Without it a roll speed
above the limit is cut down to it (user: Pikachu's 80 rolled like 8).

Works on any fighter's common status scripts: the functions are found through the status table
(sv_set_mem(0x1, kind, status, func_N): kind 0 pre, 1 main, 2 end) and the loops through the
mains' func_78(loop). A part a fighter already has (its own reverse tilts, an earlier patch) is
left alone. Prints what it changed; exits 1 if an anchor isn't found (nothing is written then).

The code is the same as Hero's (and Captain Falcon's / Kirby's / Luigi's / Sonic's, done by hand).
"""
import argparse
import re
import sys

STATUS = {'fall': 0xE, 'dash': 0x3, 'run': 0x4, 'runbrake': 0x5, 'turn': 0x6, 'turndash': 0x7,
          'turnrun': 0x8, 'turnrunbrake': 0x9, 'escapef': 0x20, 'escapeb': 0x21, 'attackhi3': 0x29,
          'attacklw3': 0x2A}
TAG = '(universal mechanics)'


class Fail(Exception):
    pass


class Fighter:
    def __init__(self, text):
        self.nl = '\r\n' if '\r\n' in text else '\n'
        self.lines = text.replace('\r\n', '\n').split('\n')
        self.log = []

    # --- structure
    def func_span(self, name):
        """(header line index, closing brace index) of a function"""
        pat = re.compile(r'^(void|int|float) %s\(' % re.escape(name))
        for i, l in enumerate(self.lines):
            if pat.match(l):
                if self.lines[i + 1] != '{':
                    raise Fail('%s: no body' % name)
                for j in range(i + 2, len(self.lines)):
                    if self.lines[j] == '}':
                        return i, j
        raise Fail('%s not found' % name)

    def body(self, name):
        i, j = self.func_span(name)
        return self.lines[i + 2:j]

    def table(self, kind, status, common=False):
        """the status's script of a kind: the fighter's own (the last entry), or common=True: the common
        one (the first entry, the common scripts' table, which the fighter's often calls)"""
        pat = re.compile(r'^\s*sv_set_mem\(0x1, %s, %s, (func_\d+)\);' % (hex(kind) if kind else '0', hex(status)))
        found = [m.group(1) for m in map(pat.match, self.lines) if m]
        if not found:
            raise Fail('no status table entry kind %d status %s' % (kind, hex(status)))
        return found[0] if common else found[-1]

    def holder(self, name, regex, depth=2):
        """the function with a line matching regex: name itself, or a function it calls (a fighter's
        own status script that hands over to the common one: Palutena's EscapeF pre calls func_362,
        Mega Man's down tilt pre returns func_248(), Yoshi's roll main sets its loop in a helper)"""
        if self.has(name, regex):
            return name
        if depth:
            for l in self.body(name):
                for callee in re.findall(r'\b(func_\d+)\(|callFunc\d?\((func_\d+)\)', l):
                    callee = callee[0] or callee[1]
                    if callee != name and callee != 'func_78':
                        try:
                            got = self.holder(callee, regex, depth - 1)
                        except Fail:
                            continue
                        if got:
                            return got
        return None

    def loop(self, status):
        main = self.table(1, status)
        fn = self.holder(main, r'func_78\(func_\d+\)')
        if not fn:
            raise Fail('%s (main of %s) sets no loop' % (main, hex(status)))
        calls = [re.search(r'func_78\((func_\d+)\)', l) for l in self.body(fn)]
        return [m.group(1) for m in calls if m][-1]

    def returns_value(self, name):
        return any(re.search(r'\breturn 0x1;', l) for l in self.body(name))

    def block_end(self, start):
        """index of the line closing the block whose statement starts at start (an if with braces)"""
        if self.lines[start + 1].strip() != '{':
            raise Fail('no block at line %d' % start)
        ind = len(self.lines[start + 1]) - len(self.lines[start + 1].lstrip())
        for k in range(start + 2, len(self.lines)):
            l = self.lines[k]
            if l.strip() == '}' and len(l) - len(l.lstrip()) == ind:
                return k
        raise Fail('unclosed block at line %d' % start)

    def find_in(self, name, regex, first=True):
        i, j = self.func_span(name)
        hits = [k for k in range(i + 2, j) if re.search(regex, self.lines[k])]
        if not hits:
            raise Fail('%s: no line matching %s' % (name, regex))
        return hits[0] if first else hits[-1]

    def insert(self, at, new, indent='    '):
        self.lines[at:at] = [indent + l if l else l for l in new]

    def has(self, name, regex):
        return any(re.search(regex, l) for l in self.body(name))

    def globals_next(self):
        nums = [int(m.group(1)) for m in (re.match(r'^(?:int|float) global(\d+);', l) for l in self.lines) if m]
        if not nums:
            raise Fail('no globals')
        return max(nums) + 1, max(i for i, l in enumerate(self.lines) if re.match(r'^(?:int|float) global\d+;', l))

    def text(self):
        return self.nl.join(self.lines)


def patch(src, air_mult=1.0, name='the fighter', ground_uncapped=False):
    f = Fighter(src)
    if any('rolloff_update()' in l for l in f.lines) or any('run_attack_update()' in l for l in f.lines):
        raise Fail('already has roll-off / run attacks (hand-patched fighter)')
    for g, t in (('global48', 'float'), ('global32', 'float'), ('global38', 'int'), ('global24', 'int'),
                 ('global47', 'int'), ('global18', 'int'), ('global5', 'int'), ('global6', 'int'),
                 ('global4', 'int')):
        if not any(l == '%s %s;' % (t, g) for l in f.lines):
            raise Fail('common global %s is not a %s here' % (g, t))
    change = None                                  # the "change status" helper: func_16 in the fighters seen so far
    for l in f.body(f.loop(STATUS['dash'])):
        m = re.search(r'(func_\d+)\(0xe, 0\);', l)
        if m:
            change = m.group(1)
            break
    if not change:
        raise Fail('no status change helper in the dash loop')

    n, last = f.globals_next()
    g_hold, g_slid, g_cap = 'global%d' % n, 'global%d' % (n + 1), 'global%d' % (n + 2)
    g_dir, g_last = 'global%d' % (n + 3), 'global%d' % (n + 4)
    f.lines[last + 1:last + 1] = ['int %s;' % g for g in (g_hold, g_slid, g_cap)] + \
        ['float %s;' % g for g in (g_dir, g_last)]

    # --- reverse tilts: the up / down tilt pre scripts, after their StatusModule calls
    for st in ('attackhi3', 'attacklw3'):
        pre = f.table(0, STATUS[st])
        if f.holder(pre, r'PostureModule\(0x2710\)'):
            f.log.append('reverse tilts: %s (%s) already turns around' % (pre, st))
            continue
        pre = f.holder(pre, r'^\s*StatusModule\(0x2713,') or pre
        at = f.find_in(pre, r'^\s*StatusModule\(0x2713,')
        f.insert(at + 1, [
            'if (global48 < -0.12f && PostureModuleF(0) == 1.0f || global48 > 0.12f && PostureModuleF(0) == -1.0f)',
            '{',
            '    PostureModule(0x2710); // reverse facing direction (universal: reverse tilts) %s' % TAG,
            '}'])
        f.log.append('reverse tilts: %s (%s)' % (pre, st))

    # --- tilts / down smash out of run: Run main turns the commands on
    run_main = f.table(1, STATUS['run'])
    at = f.find_in(run_main, r'WorkModule\(0x16, 0x1e000054\);')
    f.insert(at + 1, ['WorkModule(0x16, 0x1e000056); // up tilt out of run %s' % TAG,
                      'WorkModule(0x16, 0x1e000057); // down tilt out of run %s' % TAG,
                      'WorkModule(0x16, 0x1e00005f); // down smash out of run %s' % TAG], indent='    ')
    f.log.append('run commands: %s' % run_main)

    def check(fn, regex, after_block, call, why):
        """insert 'if (call) return' before the line matching regex, or after its block"""
        at = f.find_in(fn, regex)
        if after_block:
            at = f.block_end(at) + 1
        ret = 'return 0x1;' if f.returns_value(fn) else 'return;'
        f.insert(at, ['if (%s) // %s %s' % (call, why, TAG), '{', '    %s' % ret, '}'])
        f.log.append('%s: %s' % (why, fn))

    done = set()
    for st, regex, after, call, why in (
            ('dash', r'^    if \(global18 == 0x2\)$', True, 'run_attack_update()', 'tilts / down smash out of the dash'),
            ('run', r'^    if \(func_43\(\)\)$', False, 'run_attack_update()', 'tilts / down smash out of run'),
            ('runbrake', r'^    if \(func_43\(\)\)$', False, 'run_attack_update()', 'tilts / down smash out of run (RunBrake)'),
            ('turn', r'^    if \(func_71\(', True, 'dash_turn_attack_update()', 'tilts / down smash turning out of a dash'),
            ('turndash', r'^    if \(func_71\(', True, 'dash_turn_attack_update()', 'tilts / down smash turning out of a dash'),
            ('turnrun', r'^    if \(func_60\(\)\)$', True, 'global18 == 0 && run_attack_update()', 'tilts / down smash turning from a run'),
            ('turnrunbrake', r'^    if \(CancelModule\(0x2713\) == 0x1 && func_39\(\) != 0\)$', True,
             'global18 == 0 && run_attack_update()', 'tilts / down smash turning from a run (TurnRunBrake)')):
        fn = f.loop(STATUS[st])
        if fn in done:
            continue
        done.add(fn)
        check(fn, regex, after, call, why)

    # --- roll-off (EscapeF and EscapeB can share their scripts: each is patched once)
    done = set()

    def top(fn):
        i, _ = f.func_span(fn)
        k = i + 2
        while re.match(r'^    (int|float) var\d+;$', f.lines[k]):
            k += 1
        return k

    for st in ('escapef', 'escapeb'):
        pre = f.table(0, STATUS[st])
        pre = f.holder(pre, r'^\s*StatusModule\(0x5, 0, 0xf, 0x2,') or pre
        if pre not in done:
            done.add(pre)
            at = f.find_in(pre, r'^\s*StatusModule\(0x5, 0, 0xf, 0x2,')
            f.lines[at] = f.lines[at].replace('StatusModule(0x5, 0, 0xf,', 'StatusModule(0x5, 0, 0x6,', 1) + \
                ' // roll-off: kinetic 0x6 (ACMD sets the speed) %s' % TAG
            ind = f.lines[at][:len(f.lines[at]) - len(f.lines[at].lstrip())]
            f.lines.insert(at + 1, '%s%s = 0; // roll-off: new roll, shield-hold count starts over' % (ind, g_hold))
            f.log.append('roll-off: roll pre %s (%s)' % (pre, st))
        lp = f.loop(STATUS[st])
        if lp not in done:
            done.add(lp)
            f.insert(top(lp), ['rolloff_update(); // roll-off: edge sliding from the speed frame, not while shield is held %s' % TAG])
            f.log.append('roll-off: roll loop %s (%s)' % (lp, st))
        end = f.table(2, STATUS[st])
        common = f.table(2, STATUS[st], common=True)
        if end != common and f.has(end, r'\b%s\(' % common):
            end = common                          # the fighter's own end calls the common one last (Palutena)
        if end not in done:
            done.add(end)
            f.insert(top(end), [l % dict(slid=g_slid, cap=g_cap, dir=g_dir, tag=TAG) for l in ROLL_END])
            f.log.append('roll-off: roll end %s (%s)' % (end, st))
    fall_main = f.table(1, STATUS['fall'])
    fall_main = f.holder(fall_main, r'func_78\(') or fall_main
    at = f.find_in(fall_main, r'func_78\(', first=False)
    f.insert(at, ['rolloff_fall_speed(); // roll-off: speed carried off the ledge x rolloff_air_speed_mult() %s' % TAG])
    f.log.append('roll-off: Fall main %s (Fall\'s end left alone: Hero\'s)' % fall_main)
    add_hold_call(f)

    # --- the added functions (at the end, so the original functions keep their numbers)
    uncap = ''
    if ground_uncapped:
        uncap = ('''    KineticModule(0x15, 0x3, -1.0f, -1.0f); // no ground speed limit on the roll's speed (user: %s)
''' % name)
    helpers = HELPERS % dict(name=name, hold=g_hold, slid=g_slid, cap=g_cap, mult='%rf' % float(air_mult),
                             change=change, uncap=uncap)
    hold = HOLD_HELPERS % dict(slid=g_slid, cap=g_cap, dir=g_dir, last=g_last, fall_speed='rolloff_fall_speed')
    while f.lines and f.lines[-1] == '':
        f.lines.pop()
    f.lines += [''] + helpers.split('\n') + [''] + hold.split('\n')
    return f


def add_hold_call(f):
    """rolloff_hold_update() at the end of the per-frame hook (global14's function: func_82 in every fighter
    seen; Hero's brave_frame calls func_82 then it)"""
    hooks = sorted({m.group(1) for m in (re.match(r'^\s*global14 = (func_\d+);', l) for l in f.lines) if m})
    if len(hooks) != 1:
        raise Fail('per-frame hook (global14 = func_N): %s' % (hooks or 'none'))
    hook = hooks[0]
    if f.has(hook, r'\breturn\b'):
        raise Fail('%s (the per-frame hook) returns early' % hook)
    _, j = f.func_span(hook)
    f.insert(j, ['rolloff_hold_update(); // roll-off: the air speed cap off while the stick holds the way he moves %s' % TAG])
    f.log.append('roll-off: per-frame hook %s (rolloff_hold_update)' % hook)


def upgrade(src):
    """Hero's roll-off momentum for a fighter patched by the earlier version (decompiled or source): the roll
    ends also take a slide into an air action, Fall's end no longer puts the cap back, the per-frame hook runs
    rolloff_hold_update"""
    f = Fighter(src)
    text = '\n'.join(f.lines)
    if 'rolloff_hold_update' in text:
        raise Fail('already has Hero\'s roll-off momentum')
    for g, t in (('global4', 'int'), ('global6', 'int')):
        if not any(l == '%s %s;' % (t, g) for l in f.lines):
            raise Fail('common global %s is not a %s here' % (g, t))
    # the roll ends: if (global6 == 0xe) { flag on; slid = 1; cap = 1; }
    ends = []
    for k in range(len(f.lines) - 5):
        if re.match(r'^    if \(global6 == 0xe\)( //.*)?$', f.lines[k]) and f.lines[k + 1] == '    {' and \
                re.match(r'^        WorkModule\(0x13, 0x1, 0x20000044\);', f.lines[k + 2]):
            m1 = re.match(r'^        (global\d+) = (?:0x)?1(?:\.0f)?;', f.lines[k + 3])
            m2 = re.match(r'^        (global\d+) = (?:0x)?1(?:\.0f)?;', f.lines[k + 4])
            if m1 and m2 and f.lines[k + 5] == '    }':
                ends.append((k, m1.group(1), m2.group(1)))
    if not ends or len({(s, c) for _, s, c in ends}) != 1:
        raise Fail('roll ends (if (global6 == 0xe) {flag; slid = 1; cap = 1;}): %d found' % len(ends))
    slid, cap = ends[0][1], ends[0][2]
    # Fall's end: if (cap) { cap = 0; flag off; }
    falls = [k for k in range(len(f.lines) - 4)
             if re.match(r'^    if \(%s\)( //.*)?$' % cap, f.lines[k]) and f.lines[k + 1] == '    {' and
             re.match(r'^        %s = 0;' % cap, f.lines[k + 2]) and
             re.match(r'^        WorkModule\(0x14, 0x20000044\);', f.lines[k + 3]) and f.lines[k + 4] == '    }']
    if len(falls) != 1:
        raise Fail('Fall\'s end (if (%s) {%s = 0; flag off;}): %d found' % (cap, cap, len(falls)))
    # rolloff_fall_speed: by name, or the function that reads slid back (if (slid != 0) { slid = 0; ...})
    names = [m.group(1) for m in (re.match(r'^void (\w+)\(\)$', l) for l in f.lines) if m]
    if 'rolloff_fall_speed' in names:
        fall_speed = 'rolloff_fall_speed'
    else:
        cands = [n for n in names if f.has(n, r'^\s*%s = 0;' % slid) and f.has(n, r'KineticModule\(0x11, 0x3,')]
        if len(cands) != 1:
            raise Fail('rolloff_fall_speed (reads %s back): %s' % (slid, cands))
        fall_speed = cands[0]
    n, last = f.globals_next()
    g_dir, g_last = 'global%d' % n, 'global%d' % (n + 1)
    # edits, last line first so the indices hold
    edits = [(k, 'end') for k, _, _ in ends] + [(falls[0], 'fall')]
    for k, what in sorted(edits, reverse=True):
        if what == 'fall':
            del f.lines[k:k + 5]
            f.lines.insert(k, '    // roll-off (Hero\'s): Fall\'s end no longer puts the air speed cap back (rolloff_hold_update) %s' % TAG)
        else:
            f.lines[k + 5:k + 6] = ['        %s = 0; // roll-off: the way he moves, once he\'s off (rolloff_hold_update)' % g_dir, '    }']
            f.lines[k] = '    if (global6 == 0xe || StatusModule(0x1) == 0x2) // roll-off (Hero\'s): slid off an edge, into Fall ' \
                         'or an attack buffered off the edge -> no air speed cap %s' % TAG
    f.log.append('roll-off: roll ends at lines %s, Fall\'s end at line %d (slid %s, cap %s, fall speed %s)' % (
        ', '.join(str(k + 1) for k, _, _ in ends), falls[0] + 1, slid, cap, fall_speed))
    f.lines[last + 1:last + 1] = ['float %s;' % g for g in (g_dir, g_last)]
    add_hold_call(f)
    while f.lines and f.lines[-1] == '':
        f.lines.pop()
    f.lines += [''] + (HOLD_HELPERS % dict(slid=slid, cap=cap, dir=g_dir, last=g_last, fall_speed=fall_speed)).split('\n')
    return f


ROLL_END = ['if (global6 == 0xe || StatusModule(0x1) == 0x2) // roll-off: slid off an edge (into Fall, or an attack '
            'buffered off the edge) -> no air speed cap %(tag)s',
            '{',
            '    WorkModule(0x13, 0x1, 0x20000044);',
            '    %(slid)s = 1; // roll-off: the speed carried off x rolloff_air_speed_mult(), once (rolloff_fall_speed)',
            '    %(cap)s = 1; // roll-off: the cap stays off while the stick holds the way he moves (rolloff_hold_update)',
            '    %(dir)s = 0; // roll-off: that way, from his movement once he\'s off (rolloff_hold_update)',
            '}']


HELPERS = '''// ===================================================================
// Universal mechanics (docs/universal-mechanics.md), added by tools/universal_mechanics.py; the same
// code as Hero's (fighters/brave/brave.c, the universal roll-off) and Captain Falcon's / Kirby's /
// Luigi's / Sonic's.
// Roll-off: the rolls' ACMD gives them their speed (EscapeF +S / EscapeB -S added at frame
// rolloff_start_frame(), 0 at frame 27); kinetic 0x6 so the animation doesn't move %(name)s.
// Every roll frame: before the speed frame, or while shield is held (ControlModule(0x2712, 3)),
// ground correction 0x2 (stops at edges); from the speed frame on, 0x1 (can slide off). Sliding off
// (into Fall, or an attack buffered off the edge) keeps the roll's speed: the roll end sets flag
// 0x20000044 (no max air speed), and it stays off until the stick stops holding the way he moves,
// he lands / grabs a ledge or he's hit (rolloff_hold_update, every frame). rolloff_fall_speed()
// scales the carried speed once. Lock: %(hold)s counts the frames in a row shield has been held this
// roll; at rolloff_lock_frames() (10) the roll can't slide off for the rest of it. %(slid)s: slid off.
// %(cap)s: the roll-off took the air speed cap off (rolloff_hold_update puts it back).
// ===================================================================
float rolloff_start_frame() { return 5.0f; } // = the ACMD's speed frame
float rolloff_clear_frames() { return 3.0f; } // the carried speed is cleared on the roll's frames before this
int   rolloff_lock_frames()  { return 10; }   // shield held this many frames in a row: no roll-off for the rest of the roll
float rolloff_air_speed_mult() { return %(mult)s; } // speed carried off a ledge x this (1.0 = unchanged)

void rolloff_fall_speed()
{
    float x;
    float y;
    if (%(slid)s != 0)
    {
        %(slid)s = 0;
        if (rolloff_air_speed_mult() != 1.0f)
        {
            x = KineticModuleF(0xa, 0x3);
            y = KineticModuleF(0xb, 0x3);
            KineticModule(0x11, 0x3, x * rolloff_air_speed_mult(), y);
        }
    }
}

void rolloff_update()
{
    if (MotionModuleF(0x1) < 1.0f)
    {
        %(hold)s = 0; // new roll
    }
    if (MotionModuleF(0x1) < rolloff_clear_frames()) // no speed carried into the roll (it comes in when the roll
    {                                                // starts; the ACMD's clear didn't reach it), well before the
        KineticModule(0x11, 0x3, 0, 0);              // ACMD adds the roll's speed (user)
        KineticModule(0x11, 0x2, 0, KineticModuleF(0xb, 0x2)); // and a dash's slide, energy 2 (user: a back roll
    }                                                          // out of a dash went almost nowhere)
%(uncap)s    if (%(hold)s < rolloff_lock_frames())
    {
        if (ControlModule(0x2712, 0x3))
        {
            %(hold)s++;
        }
        else
        {
            %(hold)s = 0;
        }
    }
    if (MotionModuleF(0x1) >= rolloff_start_frame() && !ControlModule(0x2712, 0x3) && %(hold)s < rolloff_lock_frames())
    {
        GroundModule(0x2710, 0x1);
    }
    else
    {
        GroundModule(0x2710, 0x2);
    }
}

// ===================================================================
// Tilts / down smash out of run, the dash and the turns (universal mechanic): when attack is
// pressed, stick Y <= -run_tilt_y() (0.5): down smash if flicked down in the last run_smash_flick()
// (4) frames or the down smash command is set, else down tilt; stick Y >= run_tilt_y(): up tilt.
// Shield out of run is the game's own (Run main turns the Shield group on).
// ===================================================================
float run_tilt_y()      { return 0.5f; }
int   run_smash_flick() { return 4; }

int run_attack_update()
{
    if (!(global38 & 0x1)) // attack pressed this frame
    {
        return 0;
    }
    if (global24 & 0x20) // up smash: the loops' own check
    {
        return 0;
    }
    if (global24 & 0x40 || global32 <= -run_tilt_y() && global47 < run_smash_flick())
    {
        %(change)s(0x2e, 0x1); // AttackLw4Start
        return 0x1;
    }
    if (global32 <= -run_tilt_y())
    {
        %(change)s(0x2a, 0x1); // AttackLw3
        return 0x1;
    }
    if (global32 >= run_tilt_y())
    {
        %(change)s(0x29, 0x1); // AttackHi3
        return 0x1;
    }
    return 0;
}

// Turn (0x6) / TurnDash (0x7) loops: tilts / down smash when the turn came out of a Dash (0x3).
int dash_turn_attack_update()
{
    if (global5 != 0x3 || global18 != 0)
    {
        return 0;
    }
    return run_attack_update();
}
'''

# Hero's roll-off momentum (fighters/brave/brave.c rolloff_hold_update, his fixes 61, 62, 85), with the fighter's
# globals; and the air multiplier for a slide straight into an air action (no Fall to apply it)
HOLD_HELPERS = '''// ===================================================================
// Roll-off momentum (Hero's, the universal version: fighters/brave/brave.c, his fixes 61 / 62 / 85).
// The speed carried off a ledge isn't held to the air speed cap (flag 0x20000044 off) for as long as
// the stick holds the way he moves on screen (raw stick X, position variable 0x0F000260, times
// %(dir)s, past rolloff_hold_x()), whatever he does in the air (Fall, an aerial, a special, an air
// dodge, a jump); on a frame attack or special is pressed the stick doesn't count (a stick click's
// neutral move zeroes it for that frame). Landing or a ledge (situation not air) or a hit (Damage
// 0x45 - DamageFall 0x4C) puts the cap back too. %(dir)s: the way he moves (1 right, -1 left), from
// his X (position variable 0x0F000000) against the last frame's (%(last)s) once he's off (a roll can
// turn him round, so not his facing). %(cap)s: the cap is off from a roll-off. The speed itself is
// the ACMD's, set once, x rolloff_air_speed_mult() once (Fall's main, or here when he slid straight
// into an air action: %(slid)s still set outside Fall and the rolls), then air friction slows it.
// ===================================================================
float rolloff_hold_x() { return 0.3f; } // the stick past this, on screen, the way he moves keeps the cap off

void rolloff_hold_update()
{
    float x;
    x = WorkModuleF(0, 0x0f000000);
    if (%(cap)s)
    {
        if (%(dir)s == 0)
        {
            if (x > %(last)s + 0.01f)
            {
                %(dir)s = 1.0f;
            }
            else if (x < %(last)s - 0.01f)
            {
                %(dir)s = -1.0f;
            }
        }
        if (StatusModule(0x1) != 0x2 || global4 >= 0x45 && global4 <= 0x4c
            || %(dir)s != 0 && WorkModuleF(0, 0x0f000260) * %(dir)s < rolloff_hold_x()
               && ControlModule(0x2710, 0) == 0 && ControlModule(0x2710, 0x1) == 0)
        {
            %(cap)s = 0;
            %(dir)s = 0;
            WorkModule(0x14, 0x20000044);
        }
    }
    %(last)s = x;
    if (%(slid)s != 0 && global4 != 0xe && global4 != 0x20 && global4 != 0x21)
    {
        if (StatusModule(0x1) == 0x2)
        {
            %(fall_speed)s(); // slid straight into an air action: the multiplier now, once
        }
        else
        {
            %(slid)s = 0;
        }
    }
}
'''

ADDED_FUNCS = 12         # rolloff_start_frame ... dash_turn_attack_update, rolloff_hold_x, rolloff_hold_update
UPGRADE_ADDED_FUNCS = 2  # --upgrade: rolloff_hold_x, rolloff_hold_update (msc_fingerprint.py --added)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--upgrade', action='store_true', help='Hero\'s roll-off momentum for a fighter patched earlier')
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--air-mult', type=float, default=1.0)
    ap.add_argument('--name', default='the fighter')
    ap.add_argument('--ground-uncapped', action='store_true')
    a = ap.parse_args()
    try:
        if a.upgrade:
            f = upgrade(open(a.src).read())
        else:
            f = patch(open(a.src).read(), a.air_mult, a.name, a.ground_uncapped)
    except Fail as e:
        print('FAILED: %s' % e)
        sys.exit(1)
    open(a.dst, 'w', newline='').write(f.text())
    print('\n'.join(f.log))


if __name__ == '__main__':
    main()
