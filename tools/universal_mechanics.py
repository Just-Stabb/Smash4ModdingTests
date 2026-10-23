#!/usr/bin/env python3
"""Add the universal mechanics (docs/universal-mechanics.md) to a fighter's decompiled MSC:
reverse tilts, tilts / down smash / shield out of run (and out of the dash and the turns), and
roll-off (the MSC side; the rolls' ACMD speed is tools/rolloff_acmd.py).

  python3 tools/universal_mechanics.py IN.c OUT.c [--air-mult 1.0] [--name Fighter] [--ground-uncapped]

--ground-uncapped (fighters the user picks): the roll's speed isn't held to the ground speed limit.
Every roll frame, KineticModule(0x15, 3, -1, -1): no speed limit on energy 3 (the stick-driven
energy kinetic type 0x6 sets up, which the roll's ACMD speed goes into), the game's own pattern
after an energy reset (KineticModule(0xe, 3, ...) then (0x15, 3, -1, -1)). Without it a roll speed
above the limit is cut down to it (user: Pikachu's 80 rolled like 8).

Works on any fighter's common status scripts: the functions are found through the status table
(sv_set_mem(0x1, kind, status, func_N): kind 0 pre, 1 main, 2 end) and the loops through the
mains' func_78(loop). A part a fighter already has (its own reverse tilts, an earlier patch) is
left alone. Prints what it changed; exits 1 if an anchor isn't found (nothing is written then).

The code is the same as Captain Falcon's / Kirby's / Luigi's / Sonic's (done by hand), with one
difference: Fall's end only puts the air speed cap back (flag 0x20000044) when a roll-off took it
off, so a fighter's own moves that use the flag aren't touched.
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
                 ('global47', 'int'), ('global18', 'int'), ('global5', 'int'), ('global6', 'int')):
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
    f.lines[last + 1:last + 1] = ['int %s;' % g for g in (g_hold, g_slid, g_cap)]

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
            f.insert(top(end), ['if (global6 == 0xe) // roll-off: slid off an edge -> Fall without the air speed cap %s' % TAG,
                                '{',
                                '    WorkModule(0x13, 0x1, 0x20000044);',
                                '    %s = 1; // roll-off: Fall\'s main scales the carried speed (rolloff_fall_speed)' % g_slid,
                                '    %s = 1; // roll-off: Fall\'s end puts the cap back' % g_cap,
                                '}'])
            f.log.append('roll-off: roll end %s (%s)' % (end, st))
    fall_main = f.table(1, STATUS['fall'])
    fall_main = f.holder(fall_main, r'func_78\(') or fall_main
    at = f.find_in(fall_main, r'func_78\(', first=False)
    f.insert(at, ['rolloff_fall_speed(); // roll-off: speed carried off the ledge x rolloff_air_speed_mult() %s' % TAG])
    fall_end = f.table(2, STATUS['fall'])
    i, _ = f.func_span(fall_end)
    k = i + 2
    while re.match(r'^    (int|float) var\d+;$', f.lines[k]):
        k += 1
    f.insert(k, ['if (%s) // roll-off: Fall over, the air speed cap is back %s' % (g_cap, TAG),
                 '{',
                 '    %s = 0;' % g_cap,
                 '    WorkModule(0x14, 0x20000044);',
                 '}'])
    f.log.append('roll-off: Fall main %s, end %s' % (fall_main, fall_end))

    # --- the added functions (at the end, so the original functions keep their numbers)
    uncap = ''
    if ground_uncapped:
        uncap = ('''    KineticModule(0x15, 0x3, -1.0f, -1.0f); // no ground speed limit on the roll's speed (user: %s)
''' % name)
    helpers = HELPERS % dict(name=name, hold=g_hold, slid=g_slid, cap=g_cap, mult='%rf' % float(air_mult),
                             change=change, uncap=uncap)
    while f.lines and f.lines[-1] == '':
        f.lines.pop()
    f.lines += [''] + helpers.split('\n')
    return f


HELPERS = '''// ===================================================================
// Universal mechanics (docs/universal-mechanics.md), added by tools/universal_mechanics.py; the same
// code as Captain Falcon's / Kirby's / Luigi's / Sonic's.
// Roll-off: the rolls' ACMD gives them their speed (EscapeF +S / EscapeB -S added at frame
// rolloff_start_frame(), 0 at frame 27); kinetic 0x6 so the animation doesn't move %(name)s.
// Every roll frame: before the speed frame, or while shield is held (ControlModule(0x2712, 3)),
// ground correction 0x2 (stops at edges); from the speed frame on, 0x1 (can slide off). Sliding off
// goes to Fall, which keeps the roll's speed: the roll end sets flag 0x20000044 (no max air speed)
// when the next status is Fall, and Fall's end clears it. rolloff_fall_speed() scales the carried
// speed once. Lock: %(hold)s counts the frames in a row shield has been held this roll; at
// rolloff_lock_frames() (10) the roll can't slide off for the rest of it. %(slid)s: slid off.
// %(cap)s: the roll-off took the air speed cap off (Fall's end puts it back).
// ===================================================================
float rolloff_start_frame() { return 5.0f; } // = the ACMD's speed frame
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
    if (MotionModuleF(0x1) < rolloff_start_frame()) // no speed carried into the roll: it starts from 0
    {                                               // at the speed frame (user; the ACMD's clear didn't reach it)
        KineticModule(0x11, 0x3, 0, 0);
    }
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

ADDED_FUNCS = 9          # rolloff_start_frame ... dash_turn_attack_update (msc_fingerprint.py --added)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--air-mult', type=float, default=1.0)
    ap.add_argument('--name', default='the fighter')
    ap.add_argument('--ground-uncapped', action='store_true')
    a = ap.parse_args()
    try:
        f = patch(open(a.src).read(), a.air_mult, a.name, a.ground_uncapped)
    except Fail as e:
        print('FAILED: %s' % e)
        sys.exit(1)
    open(a.dst, 'w', newline='').write(f.text())
    print('\n'.join(f.log))


if __name__ == '__main__':
    main()
