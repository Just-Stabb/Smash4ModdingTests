#!/usr/bin/env python3
"""Controls menu: "Smash Attack" for every button, and the "Stick Smash" / "Stick F-Smash" ON / OFF
rows.

  python3 tools/option_button_ui.py UI_DIR MENU_MSBT OUT_DIR

UI_DIR: the game's ui folder (script/app/option/option_view_button.xtal, lumen/option_button/
option_button.lm); MENU_MSBT: the menu.msbt to add the rows' text to. Writes OUT_DIR/ui/... (the
three files). Needs the RPX side (tools/smash_button_cave.py: the `stick_smash` / `side_smash`
properties and what the settings do in a match).

The Controls screen is ui/script/app/option/option_view_button.xtal (compiled Xtal, tools/xtal.py)
on the Lumen layout option_button.lm:
- Smash Attack for buttons: the button popups list the actions of `equip_table` (pad -> key ->
  [window, actions]); every key without Smash gets it (attack, special, jump, shield, grab, smash),
  in the next bigger window (typ_5N -> typ_6N, typ_6N -> typ_7N: same place, one more row).
- Stick Smash row (sub_11), for 3DS / GameCube / Pro, GamePad and Classic (not the Wii Remote ones):
  the key name STICK after SMASH in BTN_NAME_TABLE (null in BTN_ID_TABLE, its own cursor entry:
  SMASH -> STICK -> the key below), the row movie clip `sub_11` in the clip table, the value
  `stick_smash` in refresh_key_assign (an ON / OFF row as RUMBLE / FLICK / SMASH / SHAKE),
  toggling it with A (as FLICK: set_stick_smash(!stick_smash)), the save prompt's is_diff, and
  shown in state_set unless the pad is REMOTE / FREE_STYLE (whose SHAKE row is in its place).
- Stick F-Smash row (sub_12): the same, as SIDE after STICK, with the property `side_smash`.
- Layout: the rows are other instances of the toggle row sprite (186) in btn_group (420): sub_11
  at the SHAKE row's place (hidden for the pads that get the new rows), above it in depth (8),
  sub_12 one row lower (depth 9; the sprite header's depth count, word 6 >> 16, goes from 8 to 10:
  a placement past it overruns the player's display list). Five rows don't fit above the TRY button at the game's size
  (104 high, 116 apart), so every toggle row is drawn at ROW_SCALE, ROW_YS apart (the top row's top
  edge where it was). Their label sprites (166 / 171, a frame per row name) get a frame per new
  row: a copy of the Tap Jump text object (its own character: the game binds a text object to the
  msbt label of its instance name, so one shared by two names flickers between them), named
  LABEL$0, MmenOption_button_85 = "Stick\\nSmash" / _86 = "Stick\\nF-Smash" in menu.msbt.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import xtal  # noqa: E402
import chara_layout as LM  # noqa: E402
from msbt import Msbt  # noqa: E402

XTAL = 'script/app/option/option_view_button.xtal'
LMB = 'lumen/option_button/option_button.lm'
ROW_PADS = ('CTR', 'GC', 'DRC', 'URCC', 'CLASSIC')
# the new rows: (key name, clip sub_N, property, setter, msbt label, text)
ROWS = (('STICK', 11, 'stick_smash', 'set_stick_smash', 'MmenOption_button_85', 'Stick\nSmash'),
        ('SIDE', 12, 'side_smash', 'set_side_smash', 'MmenOption_button_86', 'Stick\nF-Smash'))
# btn_group depth -> the row's y: RUMBLE / FLICK / SMASH / SHAKE + STICK / SIDE (game: -429, -313,
# -197, -81, 116 apart; the TRY button's top edge is at 52)
ROW_SCALE = 0.9
ROW_YS = {6: -434.0, 5: -326.5, 4: -219.0, 3: -111.5, 8: -111.5, 9: -4.0}
OP_SMASH = ('L', 51)            # the PAD_BUTTON_OPE_SMASH local of the top level
WINDOWS = {5: 6, 6: 7}          # popup window sizes that have a bigger one

# original pcs (option_view_button.xtal as shipped); each is checked below
NAMES_AT, IDS_AT, CURSOR_AT, EQUIP_AT, CLIPS_AT = 490, 1118, 1615, 3837, 7142
ROWS_MAP_AT = 11363             # refresh_key_assign: {'RUMBLE': 1, 'FLICK': 2, 'SMASH': 10, 'SHAKE': 3}
VALUE_LISTS = (11730, 11808, 11891)  # SetLocalVariable of the CTR / GC / DRC-URCC-CLASSIC value lists
ROW_CHAIN = 12128               # refresh: `If` after the RUMBLE / FLICK / SMASH / SHAKE compares
VISIBLE_AT = 16073              # state_set: after the pad's frame (local -16 = pad name)
TOGGLE_AT, TOGGLE_END = 17291, 17911   # state_set: after the SHAKE toggle; the cases' common end
SHAKE_SCOPE = 89
IS_DIFF_ENDS = (13485, 13769, 14073)   # is_diff: the CTR / GC / DRC.. compare chains' ends


def table_end(c, start):
    """end of the straight-line literal table code from start"""
    ok = {'Line', 'LoadConstant', 'LoadInt1Byte', 'LoadValue', 'MakeArray', 'MakeMap', 'ArrayAppend',
          'MapInsert', 'Copy', 'Call'}
    dest = None
    for pc, op, f, _ in c.instructions():
        if pc < start:
            continue
        n = xtal.INSTS[op][0]
        if dest is None:
            dest = f['result']
        elif n not in ok or f.get('result', 0) < 0 and f['result'] != dest:
            return pc
    raise ValueError(start)


def ins_at(c, pc):
    for p, op, f, _ in c.instructions():
        if p == pc:
            return xtal.INSTS[op][0], f
    raise ValueError(pc)


def expect(c, pc, name, **fields):
    n, f = ins_at(c, pc)
    assert n == name and all(f[k] == v for k, v in fields.items()), (pc, n, f, name, fields)


def patch_xtal(data):
    c = xtal.Code(data)
    edits = []

    def table(start, change):
        end = table_end(c, start)
        dest, value = xtal.read_table(c, start, end)
        change(value)
        edits.append((start, end, xtal.gen_table(c, dest, value)))
        return value

    # names, ids, cursor: STICK after SMASH, SIDE after STICK
    order = [('SMASH', 'STICK'), ('STICK', 'SIDE')]

    def names_(t):
        for p in ROW_PADS:
            for prev, new in order:
                t[p].insert(t[p].index(prev) + 1, new)
    names = table(NAMES_AT, names_)
    table(IDS_AT, lambda t: [t[p].insert(names[p].index(r[0]), None) for p in ROW_PADS for r in ROWS])

    def cursor(t):
        for p in ROW_PADS:
            rows = t[p]
            cur = [x for x in names[p] if x not in [r[0] for r in ROWS]]
            for prev, new in order:
                s = cur.index(prev)
                above = rows[s]
                below = above[1]
                rows.insert(s + 1, [prev, below, above[2], above[3]])
                cur.insert(s + 1, new)
                above[1] = new
                if below is not None:
                    rows[cur.index(below)][0] = new
            assert len(rows) == len(names[p]) and cur == names[p]
    table(CURSOR_AT, cursor)

    def equip(t):
        for keys in t.values():
            for key, (window, ops) in keys.items():
                if OP_SMASH not in ops and window // 10 in WINDOWS:
                    keys[key] = [WINDOWS[window // 10] * 10 + window % 10, ops + [OP_SMASH]]
    table(EQUIP_AT, equip)

    def clips(t):
        for p in ROW_PADS:
            for k, r in enumerate(ROWS):
                i = t[p].index(('call', 4, 10))
                t[p].insert(i + 1 + k, ('call', 4, r[1]))
    table(CLIPS_AT, clips)

    def rows(t):
        assert t == {'RUMBLE': 1, 'FLICK': 2, 'SMASH': 10, 'SHAKE': 3}, t
        t.update((r[0], r[1]) for r in ROWS)
    table(ROWS_MAP_AT, rows)

    props = [(c.ident_index(r[2]), c.ident_index(r[3])) for r in ROWS]
    get_path, visible, play_se = c.ident_index('get_path_mc'), c.ident_index('set_visible'), c.ident_index('play_se')
    menu = c.ident_index('menu')
    for pc in VALUE_LISTS:                      # the rows' values, in the names' order
        expect(c, pc, 'SetLocalVariable', target=0, number=37)
        b = xtal.Block()
        for prop, _set in props:
            b.ins('Property', result=1, primary=prop, target=-7, stack_base=2)
            b.ins('ArrayAppend', target=0, value=1)
        edits.append((pc, pc, b))

    expect(c, ROW_CHAIN, 'If', target=0)        # an ON / OFF row
    b = xtal.Block()
    b.ins('If', target=0, address_true=('I', ROW_CHAIN), address_false='cmp0')
    for k, r in enumerate(ROWS):
        b.label('cmp%d' % k).ins('LoadConstant', result=2, value_number=c.const(r[0]))
        b.ins('IfEq', lhs=-1, rhs=2, stack_base=3)
        b.ins('If', target=1, address_true='t', address_false='cmp%d' % (k + 1) if k + 1 < len(ROWS) else 'f')
    b.label('t').ins('LoadValue', result=0, value=3).ins('Goto', address=('I', ROW_CHAIN))
    b.label('f').ins('LoadValue', result=0, value=2)
    edits.append((ROW_CHAIN, ROW_CHAIN, b))

    for end in IS_DIFF_ENDS:
        expect(c, end, 'ScopeEnd')
        b = xtal.Block()
        b.ins('If', target=0, address_true=('I', end), address_false='cmp0')
        for k, (prop, _set) in enumerate(props):
            b.label('cmp%d' % k).ins('Property', result=2, primary=prop, target=-2, stack_base=3)
            b.ins('Property', result=3, primary=prop, target=-1, stack_base=4)
            b.ins('IfEq', lhs=2, rhs=3, stack_base=4)
            b.ins('If', target=1, address_true='cmp%d' % (k + 1) if k + 1 < len(props) else 'same', address_false='diff')
        b.label('diff').ins('LoadValue', result=0, value=3).ins('Goto', address=('I', end))
        b.label('same').ins('LoadValue', result=0, value=2)
        edits.append((end, end, b))

    expect(c, VISIBLE_AT, 'LocalVariable', result=0, number=33)
    b = xtal.Block()
    for k, r in enumerate(ROWS):
        b.ins('LocalVariable', result=0, number=7, depth=2)
        b.ins('LoadConstant', result=1, value_number=c.const('sub_%d' % r[1]))
        b.ins('Send', result=0, need_result=1, target=0, primary=get_path, secondary=0, stack_base=1, ordered=1)
        b.ins('LoadConstant', result=2, value_number=c.const('REMOTE'))
        b.ins('IfEq', lhs=-16, rhs=2, stack_base=3)
        b.ins('If', target=1, address_true='hide%d' % k, address_false='fs%d' % k)
        b.label('fs%d' % k).ins('LoadConstant', result=2, value_number=c.const('FREE_STYLE'))
        b.ins('IfEq', lhs=-16, rhs=2, stack_base=3)
        b.ins('If', target=1, address_true='hide%d' % k, address_false='show%d' % k)
        b.label('show%d' % k).ins('LoadValue', result=1, value=3).ins('Goto', address='set%d' % k)
        b.label('hide%d' % k).ins('LoadValue', result=1, value=2)
        b.label('set%d' % k).ins('SetProperty', primary=visible, target=0, stack_base=1)
    edits.append((VISIBLE_AT, VISIBLE_AT, b))

    expect(c, TOGGLE_END, 'FilelocalVariableByName', result=0)
    b = xtal.Block()
    for k, (r, (prop, setp)) in enumerate(zip(ROWS, props)):
        if k:
            b.label('row%d' % k)
        b.ins('LoadConstant', result=2, value_number=c.const(r[0]))
        b.ins('At', result=1, target=-15, index=2, stack_base=3)
        b.ins('IfEq', lhs=-12, rhs=1, stack_base=2)
        b.ins('If', target=0, address_true='go%d' % k,
              address_false='row%d' % (k + 1) if k + 1 < len(ROWS) else ('I', TOGGLE_AT))
        b.label('go%d' % k).ins('ScopeBegin', info_number=SHAKE_SCOPE)
        b.ins('FilelocalVariableByName', result=0, identifier_number=menu)
        b.ins('LoadConstant', result=1, value_number=c.const('se_sys_switch'))
        b.ins('SetProperty', primary=play_se, target=0, stack_base=1)
        b.ins('LocalVariable', result=0, number=51, depth=3)
        b.ins('Copy', result=1, target=-16)
        b.ins('Call', result=-1, need_result=1, target=0, stack_base=1, ordered=1)
        b.ins('Property', result=0, primary=prop, target=-1, stack_base=1)
        b.ins('Not', result=0, target=0)
        b.ins('SetProperty', primary=setp, target=-1, stack_base=0)
        b.ins('LocalVariable', result=0, number=58, depth=3)
        b.ins('Copy', result=1, target=-16)
        b.ins('Call', result=0, need_result=0, target=0, stack_base=1, ordered=1)
        b.ins('ScopeEnd')
        b.ins('Goto', address=('T', TOGGLE_END))
    edits.append((TOGGLE_AT, TOGGLE_AT, b))
    # the SHAKE case's ScopeBegin / the toggle code it copies
    expect(c, 17251, 'ScopeBegin', info_number=SHAKE_SCOPE)

    c.relocate = c.edit(edits)
    c.edits = [(s, e, b.size) for s, e, b in edits]
    return c


# ---- layout ------------------------------------------------------------------------------------

def add_symbol(lm, s):
    tag = lm.tags[0]
    assert tag[0] == LM.T_SYMBOLS
    n = struct.unpack('>I', tag[1][:4])[0]
    b = s.encode('cp932')
    tag[1] += struct.pack('>I', len(b)) + b + b'\0' * (((len(b) + 4) & ~3) - len(b))
    struct.pack_into('>I', tag[1], 0, n + 1)
    lm.sy.append(s)
    return n


def sprite_range(lm, cid):
    T = lm.tags
    i = next(k for k, (t, b) in enumerate(T) if t == 0x27 and LM.words(b)[0] == cid)
    j = i + 1
    while T[j][0] not in (0x27, 0x25, LM.T_END) and T[j][0] != 0xF022:
        j += 1
    return i, j


def max_place_id(lm):
    return max(LM.words(b)[1] for t, b in lm.tags if t == LM.T_PLACE and LM.words(b)[1] != LM.NONE)


def patch_lm(data):
    lm = LM.Lm(data)
    T = lm.tags
    syms = [(add_symbol(lm, 'sub_%d' % r[1]), add_symbol(lm, r[4] + '$0')) for r in ROWS]
    pid = max_place_id(lm)
    # new characters: a text object per new label (the game binds a text object's string by its
    # instance name: no layout places one text under two names). Ids from the root sprite's up, the
    # root renumbered after them (in every layout the root is the last, highest id: F00C words 3
    # (max id) and 5 (root); F00D word 4: the text count)
    props, counts = T[lm.ti[0xF00C]], T[lm.ti[0xF00D]]
    root = LM.words(props[1])[5]
    next_id = [root]

    def new_text(src):
        k = next(n for n, (t, b) in enumerate(T) if t == 0x25 and LM.words(b)[0] == src)
        w = LM.words(T[k][1])
        w[0] = next_id[0]
        next_id[0] += 1
        T.insert(k + 1, [0x25, LM.pack(w)])
        return w[0]

    # label sprites (a frame per row name): a new frame per row `sub_N`, the Tap Jump frame's (sub_2)
    # text object named LABEL$0
    for cid in (166, 171):
        for sym_row, sym_text in syms:
            i, j = sprite_range(lm, cid)
            hdr = LM.words(T[i][1])
            nlabels, nframes, nkeys = hdr[3], hdr[4], hdr[5]
            labels = [k for k in range(i + 1, j) if T[k][0] == LM.T_LABEL]
            frames = [k for k in range(i + 1, j) if T[k][0] == LM.T_FRAME]
            keys = [k for k in range(i + 1, j) if T[k][0] == LM.T_KEYFRAME]
            assert [LM.words(T[k][1])[0] for k in frames] == list(range(nframes)) and len(keys) == nkeys
            tap_frame = next(LM.words(T[k][1])[1] for k in labels if lm.sy[LM.words(T[k][1])[0]] == 'sub_2')
            tap = frames[tap_frame]
            rem, place = T[tap + 1], T[tap + 2]
            assert LM.words(T[tap][1])[1] == 2 and rem[0] == LM.T_REMOVE and place[0] == LM.T_PLACE
            pw = LM.words(place[1])
            pid += 1
            pw[0], pw[1], pw[3] = new_text(pw[0]), pid, sym_text
            if pw[6]:
                pw[6] = nframes << 16
            new_frame = [[LM.T_FRAME, LM.pack([nframes, 2])], [rem[0], bytearray(rem[1])], [LM.T_PLACE, LM.pack(pw)]]
            new_key = [[LM.T_KEYFRAME, LM.pack([nframes, 1])], [LM.T_PLACE, LM.pack(pw)]]
            last_key_end = keys[-1] + 1 + LM.words(T[keys[-1]][1])[1]
            T[last_key_end:last_key_end] = new_key
            last_frame_end = frames[-1] + 1 + LM.words(T[frames[-1]][1])[1]
            T[last_frame_end:last_frame_end] = new_frame
            T[labels[-1] + 1:labels[-1] + 1] = [[LM.T_LABEL, LM.pack([sym_row, nframes])]]
            hdr[3], hdr[4], hdr[5] = nlabels + 1, nframes + 1, nkeys + 1
            T[i][1] = LM.pack(hdr)

    new_root = next_id[0]
    k = next(n for n, (t, b) in enumerate(T) if t == LM.T_SPRITE and LM.words(b)[0] == root)
    w = LM.words(T[k][1])
    w[0] = new_root
    T[k][1] = LM.pack(w)
    w = LM.words(props[1])
    assert w[3] == w[5] == root, w
    w[3] = w[5] = new_root
    props[1] = LM.pack(w)
    w = LM.words(counts[1])
    w[4] += new_root - root
    counts[1] = LM.pack(w)

    # btn_group: the rows sub_11 / sub_12 at depth 8 / 9 wherever the SHAKE row (sub_3, depth 3) is;
    # every toggle row's matrix: ROW_SCALE at its ROW_YS
    pos = LM.table(T[lm.ti[LM.T_POSITIONS]][1], 2)
    xf_tag = T[lm.ti[LM.T_TRANSFORMS]]
    xf = LM.table(xf_tag[1], 6)
    made = {}

    def row_matrix(m, depth):
        if m == LM.NONE:
            return m
        x = pos[m & 0xFFFF][0] if m & LM.POS_FLAG else xf[m][4]
        assert m & LM.POS_FLAG or xf[m][:4] == (1.0, 0.0, 0.0, 1.0), xf[m]
        key = (x, ROW_YS[depth])
        if key not in made:
            made[key] = LM.append_rows(xf_tag, [(ROW_SCALE, 0.0, 0.0, ROW_SCALE) + key], 6)[0]
        return made[key]
    i, j = sprite_range(lm, 420)
    k = i + 1
    row_pids = []
    for _r in ROWS:
        pid += 1
        row_pids.append(pid)
    out = T[:i + 1]
    while k < j:
        t, b = T[k]
        if t in (LM.T_FRAME, LM.T_KEYFRAME):
            w = LM.words(b)
            kids = T[k + 1:k + 1 + w[1]]
            extra = []
            moved = []
            for kt, kb in kids:
                if kt != LM.T_PLACE:
                    moved.append([kt, bytearray(kb)])
                    continue
                kw = LM.words(kb)
                d = kw[5] >> 16
                if d in ROW_YS:
                    kw[7] = row_matrix(kw[7], d)
                if d == 3:
                    for n, (sym_row, _t) in enumerate(syms):
                        nw = list(kw)
                        nw[5] = ((8 + n) << 16) | (kw[5] & 0xFFFF)
                        nw[7] = row_matrix(LM.words(kb)[7], 8 + n)
                        if kw[0] == 186:                # a full placement: the row, named sub_N
                            assert lm.sy[kw[3]] == 'sub_3'
                            nw[1], nw[3] = row_pids[n], sym_row
                        extra.append([LM.T_PLACE, LM.pack(nw)])
                moved.append([kt, LM.pack(kw)])
            out.append([t, LM.pack([w[0], w[1] + len(extra)])])
            out += moved + extra
            k += 1 + w[1]
        else:
            out.append([t, bytearray(b)])
            k += 1
    # the sprite header's word 6: its depth count << 16 (the player's display list size)
    hdr = LM.words(out[i][1])
    hdr[6] = max(hdr[6] >> 16, 8 + len(ROWS)) << 16
    out[i][1] = LM.pack(hdr)
    lm.tags = out + T[j:]
    return lm.data()


def patch_msbt(data):
    m = Msbt(data)
    for r in ROWS:
        m.set(r[4], r[5])
    return m.build()


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    ui, menu, out = sys.argv[1:]
    files = {
        os.path.join('ui', XTAL): patch_xtal(open(os.path.join(ui, XTAL), 'rb').read()).data(),
        os.path.join('ui', LMB): patch_lm(open(os.path.join(ui, LMB), 'rb').read()),
        os.path.join('ui', 'message', 'menu.msbt'): patch_msbt(open(menu, 'rb').read()),
    }
    for path, data in files.items():
        p = os.path.join(out, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(data)
        print('wrote', p, len(data))


if __name__ == '__main__':
    main()
