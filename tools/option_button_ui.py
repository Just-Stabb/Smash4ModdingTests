#!/usr/bin/env python3
"""Controls menu: "Smash Attack" for every button, the "Stick Smash" ON / OFF row and the stick clicks' keys.

  python3 tools/option_button_ui.py UI_DIR MENU_MSBT OUT_DIR

UI_DIR: the game's ui folder (script/app/option/option_view_button.xtal, lumen/option_button/
option_button.lm); MENU_MSBT: the menu.msbt to add the rows' text to. Writes OUT_DIR/ui/... (the
three files). Needs the RPX side (tools/smash_button_cave.py: the `stick_smash` property and what
the setting does in a match).

The Controls screen is ui/script/app/option/option_view_button.xtal (compiled Xtal, tools/xtal.py)
on the Lumen layout option_button.lm:
- Smash Attack for buttons: the button popups list the actions of `equip_table` (pad -> key ->
  [window, actions]); every key without Smash gets it (attack, special, jump, shield, grab, smash),
  in the next bigger window (typ_5N -> typ_6N, typ_6N -> typ_7N: same place, one more row).
- Stick Smash row (sub_11), for 3DS / GameCube / Pro, GamePad and Classic (not the Wii Remote ones):
  the key name STICK after SMASH in BTN_NAME_TABLE (null in BTN_ID_TABLE, its own cursor entry:
  SMASH -> STICK -> the key below), the row movie clip `sub_11` in the clip table, the value
  `stick_smash` in refresh_key_assign (an ON / OFF row as RUMBLE / FLICK / SMASH / SHAKE),
  toggling it with A (as FLICK: set_stick_smash(!stick_smash)), the save prompt's is_diff, shown
  in state_set unless the pad is REMOTE / FREE_STYLE (whose SHAKE row is in its place), and one of
  is_sub's items (the right-hand column: without it the hovered row was taken for a key button,
  whose depth handling crashed the game).
- Layout: the row is another instance of the toggle row sprite (186) in btn_group (420), named
  sub_11, at the SHAKE row's place (hidden for the pads that get the new row), above it in depth
  (8; the sprite header's depth count, word 6 >> 16, goes from 8 to 9: a placement past it overruns
  the player's display list). Its label sprites (166 / 171, a frame per row name) get a frame
  `sub_11`: a copy of the Tap Jump text object (its own character: the game binds a text object to
  the msbt label of its instance name, so one shared by two names flickers between them), named
  MmenOption_button_85$0, MmenOption_button_85 = "Stick\\nSmash" in menu.msbt. The row's icon
  sprite (182, also a frame per row name: each of these sprites' first frame runs
  gotoAndStop(_parent._name), and without the label it played through every icon and crashed the
  menu when the row was selected) gets a frame `sub_11` with the Tap Jump row's stick icon (ICON_FROM).
- Stick clicks (CLICKS, smash_button_cave.py 5.): key buttons L_PUSH / R_PUSH on the GamePad and Pro Controller
  pictures. Script: the key names after R_STICK (ids 14 / 15: clips key_group.key_14 / key_15, the pictures'
  highlight frames key_14 / key_15), their cursor links (L <-> L_PUSH <-> UP down the left side, R_STICK <->
  R_PUSH <-> X on the right, L_PUSH <-> R_STICK across), popups of 7 (Not Set, attack, special, jump, shield,
  grab, smash: typ_73), icons btn_42 / btn_43, their values (`stick_l_push` / `stick_r_push`) in the STANDARD
  value list, setter cases 12 / 13 before the STANDARD switch's lookup, the save prompt's is_diff; op 14 (not
  set) -> text frame txt_14. The three STANDARD pads share these lists, so CLASSIC has the keys too: hidden
  (its picture frame gives them colour 120, as its unused keys) and out of its cursor links. Layout: key_14 /
  key_15 at depths 14 / 15 of key_group (top_mc 14 -> 16: the selected box is swapped to top_mc's depth, so
  it stays above every box and its popup with it), at (-470, 50) (across from R_STICK's box) and (470, 150)
  (under it) on typ_1 / typ_2; txt_14 = "Not Set" (MmenOption_button_31, the box's own off text); btn_42 /
  btn_43 = new icon labels MmenIcon_linecover_55 / 56 (U+E381 / U+E382: the font's sticks; R_STICK's own
  icon is U+E382); the pictures' key_14 = the R stick's highlight (key_9) mirrored, key_15 = it with the line
  from the lower box.
(More rows: add them to ROWS, each after the one before; a fifth toggle row doesn't fit above the
TRY button at the game's size: ROW_LAYOUT then draws the rows smaller.)
"""
import math
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
ROWS = (('STICK', 11, 'stick_smash', 'set_stick_smash', 'MmenOption_button_85', 'Stick\nSmash'),)
# None: the rows where the game has them (RUMBLE / FLICK / SMASH / SHAKE -429, -313, -197, -81, 104
# high, 116 apart; the TRY button's top edge is at 52), the new row at SHAKE's. For five rows:
# (0.9, {6: -434.0, 5: -326.5, 4: -219.0, 3: -111.5, 8: -111.5, 9: -4.0}): scale, btn_group depth -> y
ROW_LAYOUT = None
ICON_SPRITE, ICON_FROM = 182, 'sub_2'   # the new rows' icon: the Tap Jump row's (the control stick)
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
IS_SUB_END = 16380              # is_sub(index): the Return after its RUMBLE .. BACK compares

# stick clicks (smash_button_cave.py 5.: the STANDARD record's Tap Jump byte, the `stick_l_push` /
# `stick_r_push` properties): two key buttons on the GamePad and Pro Controller pictures. The three STANDARD
# pads share one key list (one value list, one setter switch), so CLASSIC gets the keys too, hidden (the
# Classic Controller has no stick clicks) and out of its cursor table.
# (key name, btn id: key_group.key_NN / the pictures' key_NN frame, key_mc icon frame btn_N, property,
#  setter, icon msbt label, icon text)
CLICKS = (('L_PUSH', 14, 42, 'stick_l_push', 'set_stick_l_push', 'MmenIcon_linecover_55', '\ue381'),
          ('R_PUSH', 15, 43, 'stick_r_push', 'set_stick_r_push', 'MmenIcon_linecover_56', '\ue382'))
CLICK_PADS = ('DRC', 'URCC', 'CLASSIC')
CLICK_SHOWN = {'DRC': 0, 'URCC': 1}            # their key_group frames (typ_1 / typ_2)
CLICK_POS = ((-470.0, 50.0), (470.0, 150.0))   # L: across from R_STICK's box; R: under it
OP_NONE = 14                    # "Not Set" (the key box's off text, MmenOption_button_31): op -> txt_14
CLICK_OPS = [OP_NONE, ('L', 56), ('L', 55), ('L', 54), ('L', 53), ('L', 52), OP_SMASH]   # attack .. smash
CLICK_WINDOW = 73               # 7 rows, R_STICK's / UP's variant
OPS_MAP_AT = 490                # after the op -> text frame map (-43)
ICON_ENDS = {'DRC': 10967, 'URCC': 11066, 'CLASSIC': 11165}   # the icon calls' Goto, per pad
STD_VALUES_AT = 11876           # the STANDARD value list: after stick_r
STD_SET_AT, SET_END = 12707, 13168   # the STANDARD setter switch's lookup; the switch's end
TXT_SPRITE, NOT_SET = 217, 'MmenOption_button_31'   # the action text sprite (txt_N frames)
KEY_MC, KEY_ICON_FROM = 267, 'btn_30'   # the box icon sprite; R_STICK's icon frame (a text object to copy)
PICTURES = {'DRC': 199, 'URCC': 334, 'CLASSIC': 360}   # the pads' img_mc (key_N highlight frames)
KEY_GROUP, TOP_DEPTH = 419, 14  # the boxes' sprite; top_mc's depth
R_STICK_Y = 50.0                # R_STICK's box y on typ_1 / typ_2


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

    # names, ids, cursor: the new rows after SMASH
    order = list(zip(['SMASH'] + [r[0] for r in ROWS], [r[0] for r in ROWS]))

    def names_(t):
        for p in CLICK_PADS:
            i = t[p].index('R_STICK')
            t[p][i + 1:i + 1] = [k[0] for k in CLICKS]
        for p in ROW_PADS:
            for prev, new in order:
                t[p].insert(t[p].index(prev) + 1, new)
    names = table(NAMES_AT, names_)

    def ids(t):
        for p in CLICK_PADS:
            i = t[p].index(9)               # R_STICK
            t[p][i + 1:i + 1] = [k[1] for k in CLICKS]
        for p in ROW_PADS:
            for r in ROWS:
                t[p].insert(names[p].index(r[0]), None)
    table(IDS_AT, ids)

    def cursor(t):
        for p in CLICK_PADS:                # [up, down, left, right], in the names' order
            rows = t[p]
            keys = [x for x in names[p] if x not in [r[0] for r in ROWS]]
            i = keys.index('R_STICK') + 1
            if p in CLICK_SHOWN:
                lrow, rrow = ['L', 'UP', None, 'R_STICK'], ['R_STICK', 'X', 'L_PUSH', 'TRY']
                cur = keys[:i] + keys[i + 2:]
                assert rows[cur.index('L')][1] == 'UP' and rows[cur.index('UP')][0] == 'L', rows
                assert rows[cur.index('R_STICK')][:3] == ['R', 'X', 'L'] and rows[cur.index('X')][0] == 'R_STICK', rows
                rows[cur.index('L')][1] = 'L_PUSH'
                rows[cur.index('UP')][0] = 'L_PUSH'
                rows[cur.index('R_STICK')][1:3] = ['R_PUSH', 'L_PUSH']
                rows[cur.index('X')][0] = 'R_PUSH'
            else:
                lrow, rrow = [None] * 4, [None] * 4
            rows[i:i] = [lrow, rrow]
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
        for p in CLICK_PADS:
            for k in CLICKS:
                t[p][k[0]] = [CLICK_WINDOW, list(CLICK_OPS)]
        for keys in t.values():
            for key, (window, ops) in keys.items():
                if OP_SMASH not in ops and window // 10 in WINDOWS:
                    keys[key] = [WINDOWS[window // 10] * 10 + window % 10, ops + [OP_SMASH]]
    table(EQUIP_AT, equip)

    def clips(t):
        for p in CLICK_PADS:
            i = t[p].index(('call', 5, 9))  # R_STICK's key_group.key_09
            t[p][i + 1:i + 1] = [('call', 5, k[1]) for k in CLICKS]
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

    click_props = [(c.ident_index(k[3]), c.ident_index(k[4])) for k in CLICKS]
    for n_end, end in enumerate(IS_DIFF_ENDS):
        expect(c, end, 'ScopeEnd')
        b = xtal.Block()
        b.ins('If', target=0, address_true=('I', end), address_false='cmp0')
        cmp_props = props + (click_props if n_end == 2 else [])     # 2: DRC / URCC / CLASSIC
        for k, (prop, _set) in enumerate(cmp_props):
            b.label('cmp%d' % k).ins('Property', result=2, primary=prop, target=-2, stack_base=3)
            b.ins('Property', result=3, primary=prop, target=-1, stack_base=4)
            b.ins('IfEq', lhs=2, rhs=3, stack_base=4)
            b.ins('If', target=1, address_true='cmp%d' % (k + 1) if k + 1 < len(cmp_props) else 'same',
                  address_false='diff')
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

    expect(c, IS_SUB_END, 'Return', base=0, result_count=1)
    b = xtal.Block()                            # is_sub: index == name_index[row] for the new rows too
    b.ins('If', target=0, address_true=('I', IS_SUB_END), address_false='cmp0')
    for k, r in enumerate(ROWS):
        b.label('cmp%d' % k).ins('LocalVariable', result=3, number=8, depth=1)
        b.ins('LoadConstant', result=4, value_number=c.const(r[0]))
        b.ins('At', result=2, target=3, index=4, stack_base=5)
        b.ins('IfEq', lhs=-1, rhs=2, stack_base=3)
        b.ins('If', target=1, address_true='t', address_false='cmp%d' % (k + 1) if k + 1 < len(ROWS) else 'f')
    b.label('t').ins('LoadValue', result=0, value=3).ins('Goto', address=('I', IS_SUB_END))
    b.label('f').ins('LoadValue', result=0, value=2)
    edits.append((IS_SUB_END, IS_SUB_END, b))
    expect(c, 16364, 'LoadConstant', result=4)     # is_sub's last compare ('BACK'), the pattern copied

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

    # stick clicks: op OP_NONE -> text frame txt_14 ("Not Set")
    expect(c, OPS_MAP_AT, 'MakeMap', result=-42)
    expect(c, OPS_MAP_AT - 3, 'MapInsert', target=-43)
    b = xtal.Block()
    b.ins('LoadInt1Byte', result=0, value=OP_NONE).ins('LoadInt1Byte', result=1, value=OP_NONE)
    b.ins('MapInsert', target=-43, key=0, value=1)
    n = next(k for k, e in enumerate(edits) if e[0] == OPS_MAP_AT)     # the names table starts there: prefix it
    s_, e_, tb = edits[n]
    b.labels.update({lab: v + len(b.items) for lab, v in tb.labels.items()})
    b.items += tb.items
    edits[n] = (s_, e_, b)
    # their key_mc icons
    for p, end in ICON_ENDS.items():
        expect(c, end, 'Goto')
        expect(c, end - 3, 'Call', target=-1, need_result=0)
        b = xtal.Block()
        for k in CLICKS:
            b.ins('LoadConstant', result=0, value_number=c.const(k[0]))
            b.ins('LoadInt1Byte', result=1, value=k[2])
            b.ins('Call', result=0, need_result=0, target=-1, stack_base=0, ordered=2)
        edits.append((end, end, b))
    # the STANDARD value list: their values after stick_r's
    expect(c, STD_VALUES_AT - 5, 'Property', primary=c.ident_index('stick_r'), target=-7)
    expect(c, STD_VALUES_AT, 'Property', primary=c.ident_index('is_rumble'), target=-7)
    b = xtal.Block()
    for prop, _set in click_props:
        b.ins('Property', result=1, primary=prop, target=-7, stack_base=2).ins('ArrayAppend', target=0, value=1)
    edits.append((STD_VALUES_AT, STD_VALUES_AT, b))
    # the STANDARD setter switch (index -3 into the key list, value -2, the pad object -1): indices 12, 13
    expect(c, STD_SET_AT, 'Copy', result=1, target=-3)
    expect(c, STD_SET_AT + 2, 'At', result=0, target=0, index=1)
    expect(c, 12612, 'Once', result=0)             # the switch's map (cached), then the lookup
    expect(c, 12805, 'SetProperty', primary=c.ident_index('set_stick_r'), target=-1)
    b = xtal.Block()
    for k, (_prop, setp) in enumerate(click_props):
        if k:
            b.label('c%d' % k)
        b.ins('LoadInt1Byte', result=2, value=12 + k)
        b.ins('IfEq', lhs=-3, rhs=2, stack_base=3)
        b.ins('If', target=1, address_true='s%d' % k,
              address_false='c%d' % (k + 1) if k + 1 < len(click_props) else ('I', STD_SET_AT))
    for k, (_prop, setp) in enumerate(click_props):
        b.label('s%d' % k).ins('Copy', result=0, target=-2)
        b.ins('SetProperty', primary=setp, target=-1, stack_base=0)
        b.ins('Goto', address=('T', SET_END))
    edits.append((STD_SET_AT, STD_SET_AT, b))

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

    # the icon sprite: a frame per new row, the ICON_FROM frame's keyframe again (every depth the
    # sprite uses removed first, so it reads the same played in order as gone to)
    for sym_row, _t in syms:
        i, j = sprite_range(lm, ICON_SPRITE)
        hdr = LM.words(T[i][1])
        nlabels, nframes, nkeys = hdr[3], hdr[4], hdr[5]
        labels = [k for k in range(i + 1, j) if T[k][0] == LM.T_LABEL]
        frames = [k for k in range(i + 1, j) if T[k][0] == LM.T_FRAME]
        keys = [k for k in range(i + 1, j) if T[k][0] == LM.T_KEYFRAME]
        src = next(LM.words(T[k][1])[1] for k in labels if lm.sy[LM.words(T[k][1])[0]] == ICON_FROM)
        key = next(k for k in keys if LM.words(T[k][1])[0] == src)
        places = [LM.words(b) for t, b in T[key + 1:key + 1 + LM.words(T[key][1])[1]] if t == LM.T_PLACE]
        depths = sorted({LM.words(b)[5] >> 16 for t, b in T[i:j] if t == LM.T_PLACE})
        for w in places:
            pid += 1
            w[1] = pid
        removes = [[LM.T_REMOVE, LM.pack([0, d << 16])] for d in depths]
        new_frame = [[LM.T_FRAME, LM.pack([nframes, len(removes) + len(places)])]] + removes + \
            [[LM.T_PLACE, LM.pack(w)] for w in places]
        new_key = [[LM.T_KEYFRAME, LM.pack([nframes, len(places)])]] + [[LM.T_PLACE, LM.pack(w)] for w in places]
        last_key_end = keys[-1] + 1 + LM.words(T[keys[-1]][1])[1]
        T[last_key_end:last_key_end] = new_key
        last_frame_end = frames[-1] + 1 + LM.words(T[frames[-1]][1])[1]
        T[last_frame_end:last_frame_end] = new_frame
        T[labels[-1] + 1:labels[-1] + 1] = [[LM.T_LABEL, LM.pack([sym_row, nframes])]]
        hdr[3], hdr[4], hdr[5] = nlabels + 1, nframes + 1, nkeys + 1
        T[i][1] = LM.pack(hdr)

    # ---- stick clicks: frames txt_14 / btn_42.. / key_14.., the boxes key_14 / key_15 (CLICKS)
    pos_tag, xf_tag = T[lm.ti[LM.T_POSITIONS]], T[lm.ti[LM.T_TRANSFORMS]]

    def new_pos(x, y):
        return LM.POS_FLAG | LM.append_rows(pos_tag, [(x, y)], 2)[0]

    def new_xf(m):
        return LM.append_rows(xf_tag, [tuple(m)], 6)[0]

    def matrix(m):
        """(a, b, c, d, tx, ty) of a placement's matrix word"""
        pos = LM.table(pos_tag[1], 2)
        if m == LM.NONE:
            return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        if m & LM.POS_FLAG:
            return (1.0, 0.0, 0.0, 1.0) + tuple(pos[m & 0xFFFF])
        return tuple(LM.table(xf_tag[1], 6)[m])

    def sprite_frames(cid):
        i, j = sprite_range(lm, cid)
        labels = {lm.sy[LM.words(T[k][1])[0]]: LM.words(T[k][1])[1] for k in range(i + 1, j) if T[k][0] == LM.T_LABEL}
        keys = {LM.words(T[k][1])[0]: k for k in range(i + 1, j) if T[k][0] == LM.T_KEYFRAME}
        return i, j, labels, keys

    def key_places(cid, label):
        i, j, labels, keys = sprite_frames(cid)
        k = keys[labels[label]]
        return [LM.words(b) for t, b in T[k + 1:k + 1 + LM.words(T[k][1])[1]] if t == LM.T_PLACE]

    def add_frame(cid, label, places):
        """a new last frame `label` of sprite cid: every depth the sprite uses removed, then places (its
        keyframe: places)"""
        nonlocal pid
        sym = add_symbol(lm, label) if label not in lm.sy else lm.sy.index(label)
        i, j, labels, keys = sprite_frames(cid)
        hdr = LM.words(T[i][1])
        nlabels, nframes, nkeys = hdr[3], hdr[4], hdr[5]
        frames = [k for k in range(i + 1, j) if T[k][0] == LM.T_FRAME]
        lab_tags = [k for k in range(i + 1, j) if T[k][0] == LM.T_LABEL]
        depths = sorted({LM.words(b)[5] >> 16 for t, b in T[i:j] if t == LM.T_PLACE})
        places = [list(w) for w in places]
        for w in places:
            pid += 1
            w[1] = pid
            if w[6]:
                w[6] = nframes << 16
        removes = [[LM.T_REMOVE, LM.pack([0, d << 16])] for d in depths]
        new_frame = [[LM.T_FRAME, LM.pack([nframes, len(removes) + len(places)])]] + removes + \
            [[LM.T_PLACE, LM.pack(w)] for w in places]
        new_key = [[LM.T_KEYFRAME, LM.pack([nframes, len(places)])]] + [[LM.T_PLACE, LM.pack(w)] for w in places]
        last_key = max(keys.values())
        last_key_end = last_key + 1 + LM.words(T[last_key][1])[1]
        T[last_key_end:last_key_end] = new_key
        last_frame_end = frames[-1] + 1 + LM.words(T[frames[-1]][1])[1]
        T[last_frame_end:last_frame_end] = new_frame
        T[lab_tags[-1] + 1:lab_tags[-1] + 1] = [[LM.T_LABEL, LM.pack([sym, nframes])]]
        hdr[3], hdr[4], hdr[5] = nlabels + 1, nframes + 1, nkeys + 1
        T[i][1] = LM.pack(hdr)

    # the action text sprite: txt_14 = "Not Set" (the key box's own off text, MmenOption_button_31), a new
    # text object (a label's instance name binds its string)
    w = key_places(TXT_SPRITE, 'txt_13')[0]
    w[0], w[3] = new_text(w[0]), add_symbol(lm, NOT_SET + '$3')
    add_frame(TXT_SPRITE, 'txt_%d' % OP_NONE, [w])
    # the icons: btn_42 / btn_43, each a new text object of a new icon label (msbt)
    for k in CLICKS:
        w = key_places(KEY_MC, KEY_ICON_FROM)[0]
        w[0], w[3] = new_text(w[0]), add_symbol(lm, k[5] + '$0')
        add_frame(KEY_MC, 'btn_%d' % k[2], [w])
    # the pictures' highlight frames key_14 / key_15: the R stick's (key_9) mirrored for L, its line from
    # the box under R_STICK's for R; the Classic picture (no stick clicks): its off frame
    for pad, cid in PICTURES.items():
        if pad not in CLICK_SHOWN:
            for k in CLICKS:
                add_frame(cid, 'key_%d' % k[1], key_places(cid, 'off'))
            continue
        base, line, mark = key_places(cid, 'key_9')
        a, b_, c_, d_, tx, ty = matrix(line[7])
        mx, my = matrix(mark[7])[4:]
        lw, lm_ = list(line), list(mark)
        lw[7] = new_xf((-a, b_, -c_, d_, -tx, ty))
        lm_[7] = new_xf((-1.0, 0.0, 0.0, 1.0, -mx, my))
        add_frame(cid, 'key_%d' % CLICKS[0][1], [list(base), lw, lm_])
        # the line: a unit shape scaled along (c, d) from (tx, ty) to the stick; R's starts the boxes' gap lower
        h = math.hypot(mx - tx, my - ty) / math.hypot(c_, d_)
        sx, sy = tx, ty + (CLICK_POS[1][1] - R_STICK_Y)
        vx, vy = (mx - sx) / h, (my - sy) / h
        ux, uy = vx / math.hypot(vx, vy), vy / math.hypot(vx, vy)
        th = math.hypot(a, b_)
        lw = list(line)
        lw[7] = new_xf((uy * th, -ux * th, vx, vy, sx, sy))
        add_frame(cid, 'key_%d' % CLICKS[1][1], [list(base), lw, list(mark)])
    # key_group: the boxes key_14 / key_15 at depths 14 / 15 (shown on typ_1 / typ_2, colour 120 = hidden
    # elsewhere, as the unused key_05), top_mc 14 -> 16 (the selected box is swapped to top_mc's depth: it
    # stays the highest)
    i, j = sprite_range(lm, KEY_GROUP)
    box_syms = [add_symbol(lm, 'key_%02d' % k[1]) for k in CLICKS]
    box_pids = []
    for _k in CLICKS:
        pid += 1
        box_pids.append(pid)
    vis = {n: [new_pos(*xy) for xy in CLICK_POS] for n in CLICK_SHOWN.values()}
    hid = new_pos(0.0, 0.0)
    out = T[:i + 1]
    k = i + 1
    frame_no = None
    box_char = None
    while k < j:
        t, b = T[k]
        if t in (LM.T_FRAME, LM.T_KEYFRAME):
            w = LM.words(b)
            frame_no = w[0]
            kids = []
            for kt, kb in T[k + 1:k + 1 + w[1]]:
                kw = LM.words(kb)
                if kt in (LM.T_PLACE, LM.T_REMOVE) and kw[5 if kt == LM.T_PLACE else 1] >> 16 == TOP_DEPTH:
                    n = 5 if kt == LM.T_PLACE else 1
                    kw[n] = (TOP_DEPTH + 2) << 16 | (kw[n] & 0xFFFF)
                if kt == LM.T_PLACE and kw[3] != LM.NONE and lm.sy[kw[3]] == 'key_09':
                    box_char = kw[0]
                kids.append([kt, LM.pack(kw)])
            extra = []
            full = t == LM.T_KEYFRAME or frame_no == 0
            for n, (sym, bp) in enumerate(zip(box_syms, box_pids)):
                shown = frame_no in vis
                mat = vis[frame_no][n] if shown else hid
                col = [55, 1] if shown else [120, 1]
                if full:
                    nw = [box_char, bp, 0, sym, 0x10000, (TOP_DEPTH + n) << 16, 0, mat] + col + [0, 0]
                else:                       # a move: the matrix and colour
                    nw = [0, LM.NONE, 0, 0, 0x20000, (TOP_DEPTH + n) << 16, 0, mat] + col + [0, 0]
                assert box_char is not None
                extra.append([LM.T_PLACE, LM.pack(nw)])
            out.append([t, LM.pack([w[0], w[1] + len(extra)])])
            out += kids + extra
            k += 1 + w[1]
        else:
            out.append([t, bytearray(b)])
            k += 1
    hdr = LM.words(out[i][1])
    assert hdr[6] >> 16 == TOP_DEPTH + 1, hdr
    hdr[6] = (TOP_DEPTH + 3) << 16
    out[i][1] = LM.pack(hdr)
    T[:] = out + T[j:]
    lm.tags = T

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

    # btn_group: the rows sub_11.. at depth 8.. wherever the SHAKE row (sub_3, depth 3) is; with a
    # ROW_LAYOUT, every toggle row's matrix: its scale at its y
    pos = LM.table(T[lm.ti[LM.T_POSITIONS]][1], 2)
    xf_tag = T[lm.ti[LM.T_TRANSFORMS]]
    xf = LM.table(xf_tag[1], 6)
    made = {}

    def row_matrix(m, depth):
        if m == LM.NONE or ROW_LAYOUT is None:
            return m
        ROW_SCALE, ROW_YS = ROW_LAYOUT
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
                if ROW_LAYOUT and d in ROW_LAYOUT[1]:
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
    for k in CLICKS:
        m.set(k[5], k[6])
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
