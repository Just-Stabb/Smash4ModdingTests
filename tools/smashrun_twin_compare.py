#!/usr/bin/env python3
"""The Smash Run twins' Wii U AI against their kinds' 3DS states, state by state (docs/smash-run-port.md "Step 2l").

Smash Run's Zima / Lethinium (plasmawisp) / Darios / Stalfos run their Master Fortress twins' Wii U AI
(mczakozima / mczakoplasmawisp / mczakodarios / mczakostalfos, step 2a). This lines up each twin's state table (Wii U
.data, rows {0xFFFF, enter, 0xFFFF, update, 0xFFFF | 0, exit}) with the kind's 3DS state table (enemy_fs.cro, from
reference/smashrun_enemy_specs/<kind>.json) and reduces every enter / update / exit to the same tokens:

  ST(n) / STI(n)   change_state / change_state_interrupt (Wii U: Behavior vt +0x24C / +0x254; 3DS slots 72 / 73)
  KIN(n) GND(b) PASS(b) MOT(name)   change_kinetic, set_attach_ground, set_passable_check, the motion by name
  P+0xNN           a word of the kind's param object read at that offset (3DS PSxx.fN -> xx + 4 N)
  calls            Behavior helpers both sides name (search, random, play_se, effects, articles, ...)

and prints, per state part, the tokens only one side has (ST / STI / KIN / GND / PASS / MOT / P / calls). The Wii U side
is read straight from the PPC (a linear scan of the function: no branch structure), the 3DS side from the spec's
summaries (every path), so a difference is a lead to read, not a verdict: docs/smash-run-port.md "Step 2l" has the
reading of each.

  python3 tools/smashrun_twin_compare.py CROSS_F.RPX [KIND ...] [--all] [--expand]
      --all: every state part's tokens, not only the parts that differ; --expand: the twin's calls to its own helpers
      expanded in place (two levels; the 3DS inlines some of what the Wii U calls, e.g. Stalfos 3's move timer in
      0x026D2E9C, but the spec's 3DS summaries list their own helpers unexpanded, so this adds as much as it explains)
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smashrun_enemy_cave as E  # noqa: E402

SPECS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reference', 'smashrun_enemy_specs')
TWINS = {'zima': (0x5A, 0x102FEB04, (0x026D6680, 0x026D7CA0)),
         'plasmawisp': (0x57, 0x102FE754, (0x026CF4DC, 0x026D1E00)),
         'darios': (0x58, 0x102FE678, (0x026CBA64, 0x026CF4DC)),
         'stalfos': (0x59, 0x102FE8A8, (0x026D1E00, 0x026D6680))}
WIIU = {0x02DB420C: 'MOT', 0x02DBE00C: 'KIN', 0x02C37C6C: 'GND', 0x02C367C4: 'PASS', 0x02C38A24: 'is_touch',
        0x02C5F114: 'is_end', 0x026A706C: 'search_interval', 0x026A70FC: 'search_target', 0x026A70A4: 'search_target',
        0x026A7008: 'nearest', 0x026A6984: 'check_turn', 0x026A68E4: 'check_wall', 0x026A7410: 'random_range',
        0x026A8618: 'success_pct', 0x026A96EC: 'play_se', 0x02DB5158: 'bullet', 0x026A9584: 'req_effect',
        0x026A951C: 'req_effect', 0x026A94CC: 'req_effect', 0x026A95F8: 'req_follow', 0x026A95E4: 'remove_effect',
        0x026A7DD8: 'gen_art_angle', 0x026A7D40: 'gen_art', 0x026A6CF4: 'cliff_dist_lr', 0x026A6D88: 'cliff_lr',
        0x026A6E24: 'check_cliff', 0x026A8D50: 'set_mesh_vis', 0x026A66D0: 'move', 0x026A66DC: 'move',
        0x026A690C: 'target_pos', 0x026A678C: 'get_speed', 0x02C36458: 'set_correct', 0x02C64188: 'set_node_rot',
        0x02C642C8: 'set_node_trans', 0x02DB28C8: 'aer_update', 0x02DB2524: 'aer_update', 0x026A7104: 'center_pos'}
S3DS = {'EnemyKineticModuleImpl::change_kinetic': 'KIN', 'GroundModuleImpl::set_attach_ground': 'GND',
        'GroundModuleImpl::set_passable_check': 'PASS', 'GroundModuleImpl::is_touch': 'is_touch',
        'MotionModuleImpl::is_end': 'is_end', 'Behavior::search_interval': 'search_interval',
        'Behavior::search_target': 'search_target', 'Behavior::get_nearest_target': 'nearest',
        'Behavior::check_turn_to_target': 'check_turn', 'Behavior::check_wall': 'check_wall',
        'Behavior::random_range': 'random_range', 'Behavior::success_by_percent': 'success_pct',
        'Behavior::play_se': 'play_se', 'Behavior::bullet': 'bullet', 'Behavior::request_effect': 'req_effect',
        'Behavior::request_follow_effect': 'req_follow', 'Behavior::remove_effect': 'remove_effect',
        'Behavior::generate_article_angle': 'gen_art_angle', 'Behavior::generate_article': 'gen_art',
        'Behavior::check_cliff_distance_lr': 'cliff_dist_lr', 'Behavior::check_cliff_lr': 'cliff_lr',
        'Behavior::check_cliff': 'check_cliff', 'Behavior::set_mesh_visibility': 'set_mesh_vis',
        'Behavior::move': 'move', 'Behavior::get_target_pos': 'target_pos', 'Behavior::get_current_speed': 'get_speed',
        'GroundModuleImpl::set_correct': 'set_correct', 'MotionModuleImpl::set_node_rotate': 'set_node_rot',
        'MotionModuleImpl::set_node_translate': 'set_node_trans', 'EnemyAerialModuleImpl::update': 'aer_update',
        'Behavior::center_pos': 'center_pos'}
KEYS = ('ST', 'STI', 'KIN', 'GND', 'PASS', 'MOT', 'P')


def sx(v):
    return v - 0x10000 if v & 0x8000 else v


class Wiiu:
    def __init__(self, img):
        self.img = img

    def u32(self, a):
        try:
            return self.img.u32(a)
        except KeyError:
            return None

    def rows(self, base):
        out, a = [], base
        while self.u32(a) == 0xFFFF:
            out.append((self.u32(a + 4), self.u32(a + 12), self.u32(a + 20) if self.u32(a + 16) == 0xFFFF else None))
            a += 24
        return out

    def summarize(self, start, end, motions, local=None, depth=0):
        """tokens of one function (start .. end, a linear scan); a call to a helper of the twin's own code (local:
        {start: end}) is expanded in place (two levels), as the 3DS often inlines what the Wii U calls"""
        u = self.u32
        toks, li, lis, mgr, prm = [], {}, {}, set(), set()
        vtab, vbase, vslot, ctr = set(), {}, {}, None
        a = start
        while a < end:
            w = u(a)
            op, rd, ra, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
            if op == 14:                                    # addi / li
                v = lis.get(ra)
                for t in (li, lis, vbase):
                    t.pop(rd, None)
                if ra == 0:
                    li[rd] = sx(imm)
                elif v is not None:
                    lis[rd] = (v + sx(imm)) & 0xFFFFFFFF
                elif ra in vtab:
                    vbase[rd] = imm
                mgr.discard(rd)
                prm.discard(rd)
            elif op == 15:                                  # lis
                lis[rd] = (imm << 16) & 0xFFFFFFFF
                li.pop(rd, None)
            elif op in (32, 48):                            # lwz / lfs
                kind = None
                if ra in prm:
                    toks.append('P+0x%X' % imm)
                elif ra in lis and ((lis[ra] + sx(imm)) & 0xFFFFFFFF) == 0x102F6C00:
                    kind = 'mgr'
                elif ra in mgr and 0x60 <= imm < 0x60 + 4 * 0x61:
                    kind = 'prm'
                elif op == 32 and imm == 0xE0:
                    kind = 'vt'
                elif op == 32 and ra in vtab:
                    vslot[rd] = imm
                elif op == 32 and ra in vbase:
                    vslot[rd] = vbase[ra] + imm
                if op == 32:
                    keep = ra in vtab or ra in vbase
                    for t in (li, lis, vbase):
                        t.pop(rd, None)
                    for t in (mgr, prm, vtab):
                        t.discard(rd)
                    if not keep:
                        vslot.pop(rd, None)
                    if kind:
                        {'mgr': mgr, 'prm': prm, 'vt': vtab}[kind].add(rd)
            elif op == 31 and (w & 0x7FE) == 0x3A6 and ((w >> 11) & 0x3FF) == 0x120:     # mtctr rS
                ctr = vslot.get(rd)
            elif op == 18 and w & 1:
                off = w & 0x3FFFFFC
                if off & 0x2000000:
                    off -= 0x4000000
                n = WIIU.get(a + off)
                if local and a + off in local and depth < 2:
                    toks += self.summarize(a + off, local[a + off], motions, local, depth + 1)
                if n == 'MOT':
                    i = li.get(4)
                    toks.append('MOT(%s)' % (motions[i] if i is not None and 0 <= i < len(motions) else i))
                elif n in ('KIN', 'GND', 'PASS'):
                    toks.append('%s(%s)' % (n, li.get(4)))
                elif n:
                    toks.append(n)
                li = {}
            elif w in (0x4E800421, 0x4E800420):        # bctrl / bctr: a vtable call
                if ctr in (0x24C, 0x254):
                    toks.append('%s(%s)' % ('ST' if ctr == 0x24C else 'STI', li.get(4)))
                ctr = None
                li = {}
            a += 4
        return toks


def motions_wiiu(img, name, twin):
    entries = E.read_set(img, twin)[0]
    return [s.split('BodyMain', 1)[1] for s in E.map_set(name, entries)]


def tokens_3ds(evs, motions):
    out = []
    for e in evs or []:
        c, cat = e.get('call'), e['cat']
        if cat == 'state' and c in ('change_state', 'change_state_interrupt'):
            out.append('%s(%s)' % ('ST' if c == 'change_state' else 'STI', e.get('state', (e.get('args') or ['?'])[0])))
        elif cat == 'param' and str(e.get('ref', '')).startswith('PS'):
            ref = e['ref']
            base, f = ref[2:].split('.f')
            out.append('P+0x%X' % (int(base, 16) + 4 * int(f)))
        elif c in S3DS:
            n = S3DS[c]
            if n in ('KIN', 'GND', 'PASS'):
                out.append('%s(%s)' % (n, (e.get('args') or ['?'])[0]))
            else:
                out.append(n)
        elif c == 'Behavior::change_motion_state':
            out.append('MOT(%s)' % e.get('motion', (e.get('args') or ['?'])[0]))
    return out


def compare(img, name, show_all=False, expand=False):
    twin, table, (lo, hi) = TWINS[name]
    W = Wiiu(img)
    rows = W.rows(table)
    spec = json.load(open(os.path.join(SPECS, name + '.json')))
    st3 = [s for s in spec['states'] if s['enter']]
    mw = motions_wiiu(img, name, twin)
    notes = []
    redirected = {}
    for r in rows:                  # a row word the walker cave redirected (step 2l pw2_up): its tail jump's target
        for f in r:
            if f and not lo <= f < hi:
                for a in range(f, f + 0x80, 4):
                    w0, w1 = img.u32(a), img.u32(a + 4)
                    if w0 >> 26 == 15 and w1 >> 26 == 24:
                        t = ((w0 & 0xFFFF) << 16) | (w1 & 0xFFFF)
                        if lo <= t < hi:
                            redirected[f] = t
                            break
    rows = [tuple(redirected.get(f, f) for f in r) for r in rows]
    for f, t in redirected.items():
        notes.append('  (row word 0x%08X: the cave\'s wrapper, then the game\'s 0x%08X: compared)' % (f, t))
    starts = {x for r in rows for x in r if x}
    for a in range(lo, hi, 4):                      # the twin's own helpers (bl targets in its code)
        w = img.u32(a)
        if w >> 26 == 18 and w & 1:
            off = w & 0x3FFFFFC
            t = a + (off - 0x4000000 if off & 0x2000000 else off)
            if lo <= t < hi:
                starts.add(t)
    starts = sorted(starts)
    local = {x: min([y for y in starts if y > x] + [hi]) for x in starts}
    report = []
    report.append('%s: Wii U %d states (table 0x%08X), 3DS %d states (table 0x%s)' % (
        name, len(rows), table, len(st3), spec['state_table']))
    report += notes
    for i, r in enumerate(rows, 1):
        s = next((x for x in st3 if x['id'] == i), None)
        for part, f, key in (('enter', r[0], 'enter'), ('update', r[1], 'update'), ('exit', r[2], 'exit')):
            if not f and not (s and s[key]):
                continue
            wt = W.summarize(f, min(local[f], f + 0x1000), mw, local if expand else None) if f else []
            tt = tokens_3ds((s or {}).get('summary', {}).get(key), mw) if s else []
            cw, c3 = collections.Counter(wt), collections.Counter(tt)
            only_w, only_3 = sorted((cw - c3).elements()), sorted((c3 - cw).elements())
            # a token present on both sides a different number of times is a path difference of the linear scan,
            # not of the code: report presence only
            only_w = sorted(set(only_w) - set(tt))
            only_3 = sorted(set(only_3) - set(wt))
            if only_w or only_3 or show_all:
                report.append('  %2d %-6s Wii U 0x%s / 3DS 0x%s: Wii U only %s; 3DS only %s' % (
                    i, part, '%08X' % f if f else '-', (s or {}).get(key) or '-', only_w, only_3))
                if show_all:
                    report.append('       Wii U %s' % ' '.join(wt))
                    report.append('       3DS   %s' % ' '.join(tt))
    return report


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    img = E.Image(args[0])
    for name in args[1:] or list(TWINS):
        print('\n'.join(compare(img, name, '--all' in sys.argv, '--expand' in sys.argv)))


if __name__ == '__main__':
    main()
