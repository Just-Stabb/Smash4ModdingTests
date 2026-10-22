#!/usr/bin/env python3
"""Fighter-kind expansion, code and tables: every switch, bound, loop and static table indexed or sized by
fighter kind (and by UI character id), and how a "grow to N kinds" patch must change each one
(docs/kind-expansion-code.md; RAM arrays inside objects: docs/kind-expansion-ram.md).

  python3 tools/kind_code_scan.py [RPX] [--n N] [--scan] [--params DIR] [--plan EXTRA.json] [--json OUT]

RPX defaults to build/cave_fix_s4/cross_f.rpx.

(no option)   the reviewed inventory: each site / table with its address, what it is, what a kind >= 0x41
              does there today and how to extend it (action), checked against the RPX (the instruction or
              table must still be what the inventory says); totals by category and by action.
--n N         the new kind count (default 0x60, i.e. kinds 0x41-0x5F): prints the new immediates.
--scan        the automatic scanners the inventory was built from, each hit marked "inv" (in the
              inventory), "no" (reviewed: not a fighter kind) or "?" (not reviewed):
                1. jump tables bounded by 0x30-0x40 (cmplwi + bgt + bctr + table of b);
                2. every cmpwi / cmplwi whose effective bound is 0x39-0x42, with its branch and the
                   data-flow class of the compared value (S = proven kind: parameter / return of a kind
                   function, w:<field> = loaded from a field, - = other), relational compares only;
                3. every `li rX, 0x41`;
                4. pointer tables of 56-66 entries (runs of ADDR32 relocations, nulls allowed);
                5. constant-base indexed tables whose size (gap to the next referenced address) is
                   56-70 entries.
              The data flow: a kind is a parameter of a known kind function (descriptor getter,
              name readers, predicates, ...), the return of a kind producer, or (weak) a field load
              that the same function passes to a kind function; propagated through mr / clrlwi /
              stack spills, and between functions (parameters / returns) to a fixpoint.
--params DIR  data files under DIR (a param/ folder) with one entry per kind or per UI id.
--plan FILE   a JSON "extra kinds" table (one record per new kind, see EXAMPLE_PLAN) -> the per-kind
              values every inventory item needs (base's switch cases, size-table values, names) and the
              global immediates. It prints the patch list; it doesn't write caves (untested design).
--json OUT    write the inventory (with the checks) as JSON.
"""
import array
import bisect
import json
import os
import struct
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rpx_patch  # noqa: E402

RPX = os.path.join(HERE, '..', 'build', 'cave_fix_s4', 'cross_f.rpx')
TEXT_BASE = 0x02000020
NKINDS = 0x41

# ----------------------------------------------------------------------------------------------
# The reviewed inventory.
# (category, address, check, action, description)
#   check: ('cmp', imm)  cmpwi / cmplwi with that immediate      ('li', imm)  li with that immediate
#          ('jt', N)     cmplwi N + jump table                    ('tbl', n, stride)  table of n entries
#          ('ptr', n)    table of n pointers (relocated)          ('fn',)  function / site, not checked
#   action: switch   extend the jump table in a cave (bgt -> cave: cmplwi N-1, cave table, bctr)
#           table    copy the table into a cave with N entries, repoint its readers (lis/addi pairs:
#                    move their ADDR16_HA/LO relocations with reloc:, as stage_slot_cave.py does)
#           imm      raise the immediate (count -> N, last kind -> N-1)
#           ram      RAM array sized by kind: docs/kind-expansion-ram.md (immediate listed here)
#           ok       a kind >= 0x41 takes the default / "not special" path: nothing to change
#           opt      only for an optional feature (Kirby copy, name-matched sound rows)
#           verify   probably a kind bound: confirm before patching
#           data     data file / encoding note
# imm items: 'count' (immediate = number of kinds, 0x41 -> N) or 'last' (immediate = last kind, 0x40 -> N-1)
# ----------------------------------------------------------------------------------------------
INV = [
    # --- names (one pointer a kind) ---
    ('names', 0x102FF484, ('ptr', 65), 'table', 'lowercase names (folder / file names); reader 0x0275DB24'),
    ('names', 0x102FF588, ('ptr', 65), 'table', 'Capitalised names (sound / resource names); reader 0x0275DB38'),
    ('names', 0x10353DB4, ('ptr', 65), 'table', 'fighter_param_vl_<name> file names; reader in vl load 0x02EA6BC4'),
    ('names', 0x10340BBC, ('ptr', 58), 'opt', 'Cap names of kinds 0-0x39, matched by name by a sound-side parser '
     '(0x02A63954, bound cmplwi r25,0x3A at 0x02A63AFC); rows for new kinds only if that file needs them'),
    ('names', 0x10340F8C, ('ptr', 62), 'opt', '62 Cap names in another order (Mario first, transformations and '
     'Miis at 0x30-0x36): a sound-side parser 0x02ABA37C matches records by name (cmplwi r28,0x3E at 0x02ABA4C8)'),
    # --- the six 65-case kind switches ---
    ('switch65', 0x02E669F0, ('jt', 0x40), 'switch', 'specializer getter (r4): case -> b getter -> static singleton; '
     'default 0x02E66C18 returns 0 (fighter+0x7538 null: 3 unchecked reads crash)'),
    ('switch65', 0x02E43148, ('jt', 0x40), 'switch', 'kind descriptor getter 0x02E4313C (r4); default 0x02E43780 '
     'ABORTS (0x04ADC364)'),
    ('switch65', 0x02EA6C94, ('jt', 0x40), 'switch', 'vl param load 0x02EA6BC4 (r4): per-kind parser into '
     '[mgr+0x2574]+0x320+4k, stores mgr+0x111C+4k (fixed offsets); default reads the slot without loading'),
    ('switch65', 0x02EA5DA0, ('jt', 0x40), 'switch', 'vl param unload 0x02EA5D64: per-kind free functions'),
    ('switch65', 0x02E02458, ('jt', 0x40), 'switch', 'AI on [ai+0x18] (0x02E02440): per-kind routine; default '
     '0x02E034A0 = generic AI (a new kind works without a case)'),
    ('switch65', 0x0275B44C, ('jt', 0x40), 'switch', 'AI 0x0275B440 (r5): per-kind routine; default returns 0 '
     '(works without a case)'),
    # --- switches over the playable / part of the kinds: kinds >= 0x41 go to the default ---
    ('switchpart', 0x026F4C24, ('jt', 0x35), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x026F4F10, ('jt', 0x39), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x026F5114, ('jt', 0x39), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x026F5240, ('jt', 0x39), 'ok', 'AI (+0x134 of the same record)'),
    ('switchpart', 0x027011B4, ('jt', 0x3D), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x02701B9C, ('jt', 0x3C), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x02701F7C, ('jt', 0x37), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x027030FC, ('jt', 0x3D), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x027047CC, ('jt', 0x38), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x02704930, ('jt', 0x39), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x02704C94, ('jt', 0x39), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x02705054, ('jt', 0x36), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x027051BC, ('jt', 0x3B), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x02707EF8, ('jt', 0x38), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x0270810C, ('jt', 0x3C), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x02709740, ('jt', 0x39), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x02717488, ('jt', 0x3A), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x0271CF30, ('jt', 0x39), 'ok', 'AI (byte kind)'),
    ('switchpart', 0x02DF0054, ('jt', 0x35), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x02E0CEC4, ('jt', 0x3D), 'ok', 'AI [+0x18]'),
    ('switchpart', 0x02010BFC, ('jt', 0x39), 'ok', 'per-kind handler on the BattleObject kind (0x02BEF604); '
     '5 callers 0x020110F0-0x02011324'),
    ('switchpart', 0x02EFC944, ('jt', 0x33), 'ok', 'Kirby copy set-up 0x02EFC940 (r5): no set-up past 0x33'),
    ('switchpart', 0x0274EB90, ('jt', 0x3C), 'verify', 'AI map 0x0274EB90 (r3 <= 0x3C, one caller in '
     '0x0274FE18); result compared with 0x37 / 0x3E: probably kind -> group'),
    # --- per-kind value tables and their getters ---
    ('tables', 0x1012F638, ('tbl', 65, 2), 'table', 'u16 a kind (special-block size); getter 0x02EA90E0 '
     '(cmplwi r4,0x40 -> 0)'),
    ('tables', 0x1012F6BC, ('tbl', 65, 1), 'table', 'u8 special N block size; getter 0x02EA9104 (bound 0x40)'),
    ('tables', 0x1012F700, ('tbl', 65, 1), 'table', 'u8 special S block size; getter 0x02EA9120 (bound 0x40)'),
    ('tables', 0x1012F744, ('tbl', 65, 1), 'table', 'u8 special Hi block size; getter 0x02EA913C (bound 0x40)'),
    ('tables', 0x1012F788, ('tbl', 65, 1), 'table', 'u8 special Lw block size; getter 0x02EA9158 (bound 0x40)'),
    ('tables', 0x100D21D8, ('tbl', 65, 4), 'table', 'u32 sound class (0-3); getter 0x02AB8CB0 has NO bound: a kind '
     '>= 0x41 reads the next data'),
    ('getters', 0x02EA90E0, ('cmp', 0x40), 'imm:last', 'bound of the u16 getter (with the table move)'),
    ('getters', 0x02EA9104, ('cmp', 0x40), 'imm:last', 'bound of the spN getter'),
    ('getters', 0x02EA9120, ('cmp', 0x40), 'imm:last', 'bound of the spS getter'),
    ('getters', 0x02EA913C, ('cmp', 0x40), 'imm:last', 'bound of the spHi getter'),
    ('getters', 0x02EA9158, ('cmp', 0x40), 'imm:last', 'bound of the spLw getter'),
    # --- kind-count bounds in code ---
    ('bounds', 0x021ED1A0, ('li', 0x41), 'imm:count', 'random fighter pick: rand(0x41)'),
    ('bounds', 0x021ED1B0, ('cmp', 0x41), 'imm:count', 'random pick: wrap'),
    ('bounds', 0x021ED1E0, ('cmp', 0x41), 'imm:count', 'random pick: retry loop bound'),
    ('bounds', 0x021E6E30, ('li', 0x41), 'imm:count', 'second random fighter pick (0x021E4DD0): rand(0x41) -> '
     'chr id 0x0309FE50 -> availability 0x0301BA44'),
    ('bounds', 0x0309FE68, ('cmp', 0x41), 'imm:last', 'kind -> character id 0x0309FE50 (`<= 0x41`, already one too many)'),
    ('bounds', 0x02A79158, ('cmp', 0x41), 'imm:count', 'sound bank loader 0x02A7912C (chr id -> kind, kind < 0x41)'),
    ('bounds', 0x0275BAC0, ('cmp', 0x41), 'imm:count', 'kind -> motion count 0x0275BAB0 (AI attack_data check)'),
    ('bounds', 0x02DE1DDC, ('cmp', 0x41), 'imm:count', 'AI file loader 0x02DE1DBC ([+0x1BB0] >= 0x41: no AI files)'),
    ('bounds', 0x02AC3F7C, ('cmp', 0x41), 'imm:count', 'fighter resource holder [[0x102F9028]+0x34] (+0x20 kind): '
     'loaded by Cap name only for kind < 0x41'),
    ('bounds', 0x02761528, ('cmp', 0x41), 'imm:count', 'twin of 0x02AC3F7C'),
    ('bounds', 0x02FCD770, ('cmp', 0x41), 'verify', '0x02FCD740: picks count [+0x10] or [+0xC] by r4 < 0x41 '
     '(r4 probably a kind)'),
    ('bounds', 0x02748648, ('cmp', 0x41), 'verify', 'AI [+0xA4] >= 0x41 (the same field is range-tested '
     '0x33-0x35 at 0x0270BE10: probably a kind)'),
    ('bounds', 0x0274868C, ('cmp', 0x41), 'verify', 'twin of 0x02748648'),
    # --- loops over kinds / per-kind arrays in RAM (immediates; the arrays: kind-expansion-ram.md) ---
    ('loops', 0x02EA5C9C, ('li', 0x41), 'ram', 'param manager: zero refcounts mgr+0x1220'),
    ('loops', 0x02EA5CBC, ('li', 0x41), 'ram', 'param manager: map fighter_param.bin entries by word 0 '
     '(entries with kind > 0x40 are never looked up)'),
    ('loops', 0x02EA6B8C, ('li', 0x41), 'ram', 'param manager: unload all'),
    ('loops', 0x0274EAA8, ('li', 0x41), 'ram', 'AI record [+0x280] init'),
    ('loops', 0x0274EAC8, ('li', 0x41), 'ram', 'AI record [+0x384] init'),
    ('loops', 0x027588BC, ('li', 0x41), 'ram', 'AI record [+0x280] init (second copy)'),
    ('loops', 0x027588DC, ('li', 0x41), 'ram', 'AI record [+0x384] init (second copy)'),
] + [('loops', a, ('li', 0x41), 'ram', 'AI 0x0275233C: loop over the [0x41] AI arrays')
     for a in (0x0275318C, 0x02753210, 0x027539F4, 0x027540A8, 0x027542D0, 0x027544F8, 0x02754720, 0x02754980,
               0x02754B94, 0x02755068, 0x02755290, 0x027554B8, 0x027556E0, 0x0275593C)] + [
    ('loops', 0x03B2EED4, ('cmp', 0x41), 'ram', 'float [0x41] arrays (r3+0x38B4+0x20FA8...) init, function 0x03B2EDA8'),
    ('loops', 0x03B2EEF4, ('cmp', 0x41), 'ram', 'second array, same function'),
    ('loops', 0x03B36454, ('cmp', 0x41), 'ram', 'double [0x41] arrays copy, function 0x03B35F1C'),
    ('loops', 0x03B36B5C, ('cmp', 0x41), 'ram', 'same function'),
    # --- kind predicates and range checks: kinds >= 0x41 already get the right answer ---
    ('predicates', 0x02E694AC, ('fn',), 'ok', 'isMii(kind, enemies): 0-2 / 0x3E-0x40 -> false for new kinds'),
    ('predicates', 0x02E694E8, ('fn',), 'ok', 'isMiiEnemy: == 0x3E / 0x3F / 0x40'),
    ('predicates', 0x028E25C0, ('cmp', 2), 'ok', 'kind <= 2'),
    ('predicates', 0x02E69510, ('fn',), 'ok', 'has-transformation (equality list)'),
    ('predicates', 0x02E69560, ('cmp', 0x33), 'ok', '0x33 <= kind <= 0x3C (closed range)'),
    ('predicates', 0x03058B6C, ('cmp', 0x3A), 'ok', 'kind == 0x3A / 0x3C'),
    ('predicates', 0x03058B8C, ('cmp', 0x3A), 'ok', '0x3A-0x3D (closed)'),
    ('predicates', 0x030BF9C0, ('cmp', 0x3B), 'ok', 'transform -> base (others returned unchanged)'),
    ('predicates', 0x030C1FDC, ('cmp', 0x3B), 'ok', 'transform -> base, second copy'),
    ('predicates', 0x02704F44, ('fn',), 'ok', 'AI armor check (== 0x3A / 0x3C / 0x3D)'),
] + [('predicates', a, ('fn',), 'ok', 'inline Mii-enemy range test (0x3E-0x40, closed)')
     for a in (0x02542FD4, 0x0265FC74, 0x026F4ACC, 0x026F4B50, 0x0270EDCC, 0x027294C8, 0x02A65928, 0x02DE6A98,
               0x02DEA014, 0x02FE3FC4)] + [
    # --- Kirby's copy ability (native) ---
    ('kirby', 0x02EFCDC8, ('cmp', 0x3A), 'opt', 'copy_grant: kinds >= 0x3A are never copied (raise to let Kirby '
     'copy new kinds; then every table below needs their rows)'),
    ('kirby', 0x1038281C, ('ptr', 58), 'opt', 'per-kind copy record {ptr to 16-byte entries, count} (null for Kirby); '
     'indexed by fighter+0xB9CC in 0x02EFD828 and 5 more readers, no bound of their own'),
    ('kirby', 0x1041A6D0, ('ptr', 58), 'opt', 'copy resources: owner folder name a kind (reader 0x030C46E4..)'),
    ('kirby', 0x1041A7B8, ('ptr', 58), 'opt', 'copy hat model (mariocap, ...)'),
    ('kirby', 0x1041A8A0, ('ptr', 58), 'opt', 'copy item model (marthsword, ...)'),
    ('kirby', 0x1041A988, ('ptr', 58), 'opt', 'copy extra model R (bayonettagunr)'),
    ('kirby', 0x1041AA70, ('ptr', 58), 'opt', 'copy extra model L (bayonettagunl)'),
    ('kirby', 0x030C46C8, ('cmp', 0x3A), 'opt', 'copy resource loader 0x030C4698: kind >= 0x3A -> nothing'),
    ('kirby', 0x030C526C, ('cmp', 0x3A), 'opt', 'copy resource function 0x030C5244: same bound'),
    ('kirby', 0x030C5BDC, ('cmp', 0x3A), 'opt', 'copy resource function 0x030C5BC0: same bound'),
    ('kirby', 0x030C0FF8, ('cmp', 0x39), 'opt', 'fighter sound loader 0x030C0C34: snd_se_vc_Kirby_copy_<Name> '
     '(type 14) only for kinds <= 0x39'),
    # --- UI character ids ---
    ('ui', 0x1033BE68, ('pair', 83), 'table', '{u32 id, char *name} a character id ({-1, ""} first, then 82: 0-0x3A, 0xC8-0xE3); '
     'reader 0x0293DCCC: lis/addi + `li r4, 0x53`'),
    ('ui', 0x0293DCD4, ('li', 0x53), 'imm:ui', 'count of that table (+ new ids)'),
    ('ui', 0x02FFB644, ('li', 0x51), 'imm:ui', 'random-select bitset: first 0x51 database entries -> +new entries; '
     'the set is 12 bytes (96 entries max, copied to +0x98)'),
    ('ui', 0x030A04C0, ('cmp', 0xC7), 'ok', 'ui_character_db accessors (19 at 0x0309FB94-0x030A0C58): ids <= 0xC7 '
     'by position; ids are bytes (0xFF = none): room for ids 59-199'),
    ('ui', 0x030A0A3C, ('fn',), 'ok', 'unlock index: DLC id -> id - 0x34 + 8; non-DLC ids not in '
     'unlock_condition_of_fighters.bin are unlocked'),
] + [('ui', a, ('jt', 0x3A), 'ok', 'HUD (Palutena\'s Guidance / Smash taunts): switch on character id - 1 '
      '(<= 0x3A); new ids -> default') for a in (
          0x0267E228, 0x0267E618, 0x0267F0D4, 0x0267F4C4, 0x0267FE98, 0x026826BC, 0x02682AB0, 0x02682DF4,
          0x026830E4, 0x02683414, 0x02683B14, 0x02684774, 0x02684A68, 0x02684DA0, 0x026854A8, 0x02686F80,
          0x02687514)] + [
    # --- IDs that encode the kind ---
    ('encodings', 0x030C010C, ('fn',), 'data', 'fighter resource IDs kind*0x11 + 6..0xF (map keyed by id, no '
     'array): kind 0x5F -> 0x655-0x65E; no table to grow'),
    ('encodings', 0x030C1BBC, ('fn',), 'data', 'result-screen / common SE resource IDs kind*9 + 1..8 (same map)'),
    ('encodings', 0x030C1B34, ('fn',), 'ok', 'costume -> voice variant: unlisted kinds use variant 0'),
    ('encodings', 0x0, ('fn',), 'data', 'ACMD effect IDs 0x3KKnnnn / 0x4KKnnnn: 8-bit kind field (room to 0xFF); '
     'the decoder was not located: test'),
]

SKIP = {    # reviewed scanner hits that are not fighter kinds (address: why)
    0x0226EAB4: 'u16 copy loop (0x41 chars)', 0x0230C0B8: 'threshold ladder 0x23/0x2D/0x37/0x41',
    0x0247E020: 'char range', 0x02542FE4: 'equality on a non-kind enum (0x3E/0x40/0x41)',
    0x02794800: 'id 0x41 passed on', 0x0288F308: 'ASCII', 0x029B7F14: 'range 0x41-0x49',
    0x02AF8E90: 'stage kind ([[0x102F7020]])', 0x02AF8F2C: 'stage kind', 0x02AF9614: 'stage kinds 0x41/0x50/0x58',
    0x02DA2DF4: 'ASCII', 0x02DFB4E4: "'A' of the ATKD magic", 0x02DFC878: "'A' of the ATKD magic",
    0x02E07614: 'article (weapon) kind: bound 0x49', 0x02E56BE8: 'status 0x3F/0x40/0x41', 0x03A6DF20: "hex digit 'A'-'F'",
    0x03B0761C: 'opcode switch', 0x027137F0: 'equality on an object kind (not a bound)',
    0x0273EC44: 'equality on an object kind (not a bound)', 0x04ADB1A0: 'equality', 0x02FC743C: 'equality',
    0x02FC7464: 'equality', 0x0234E0A8: 'not a kind (0x36 cases)', 0x02E2BAA4: 'r6 - 0x4F (status)',
    0x03C07DB8: 'byte < 0x60 (not a kind)', 0x02C61700: 'value < 0x2710 (not a kind)',
    0x026F72CC: 'virtual call result', 0x0463C2B4: 'lookup byte', 0x04A96114: 'not a kind',
    0x02FA64DC: 'rule id 0x41 (0x41, 0x42, ... cleared from the player slot)',
    0x02FE2D9C: 'rule id 0x41', 0x028BC434: 'copy of 0x41 words (Manifold bound, not a kind)',
    0x02A61FCC: 'copy of 0x41 words (BGM request)', 0x02A620B4: 'copy of 0x41 words (BGM request)',
    0x033F7A94: 'zero 0x41 words (library)', 0x023C2F70: 'not a kind', 0x02C0AE80: 'id - 0x2710',
    0x02C2F8F4: 'id - 0x2710', 0x02E0A74C: 'article kinds 0xE2-0x113 (object kind)', 0x02E0DD3C: 'status',
    0x02E2B9B4: 'status', 0x03AE106C: 'cave function result', 0x03AE12B4: 'cave function result',
    0x03AE1598: 'cave function result', 0x03AE1F4C: 'not a kind', 0x03BD8FB8: 'value < 0x64',
    0x03BDAC68: 'value < 0x64', 0x03BDC714: 'value < 0x64', 0x03F974A8: 'byte code', 0x03F976D8: 'byte code',
    0x03F9CF9C: 'byte code', 0x03F9D268: 'byte code', 0x04A2EF58: 'id - 0x2100', 0x04A97620: 'code - 0x80',
    0x02DE2E48: 'AI +0x1BE0 flags 0x10 / 0x20 / 0x40', 0x02DE2E60: 'AI +0x1BE0 flags',
    0x10048EC7: 'byte table, index not a kind', 0x102FBB24: 'index <= 0x45 (another enum)',
    0x102FC484: 'loop over 0x45 records', 0x1024E2EC: 'float table (amiibo), loop index',
    0x104556D4: 'index = byte +0x302 (61 entries, not a kind)', 0x1009174C: 'index r4 (0x15B-range ids)',
    0x100600E0: '12-byte records, index from [r4]',
}

OKSITES = {  # reviewed compares on a kind that a kind >= 0x41 passes correctly (closed ranges, ladders)
    0x023EAD44: '0x3A-0x3D (closed)', 0x023EAD4C: '0x3A-0x3D (closed)', 0x024090EC: '{<=0x2F, 0x32, 0x37-0x39}',
    0x024FC7B8: '{0x2F, 0x32, 0x38-0x39}', 0x02541EA8: '{0x2F, 0x32, 0x38-0x39}', 0x02542F60: '0x3A-0x3D (closed)',
    0x027690AC: '{0x33-0x34, 0x36-0x39}', 0x02E694D0: 'isMii (closed)', 0x02E69568: '0x33-0x3C (closed)',
    0x02E6C4E8: '0x3A-0x3D (closed)', 0x03058B94: '0x3A-0x3D (closed)', 0x030C0D1C: 'costume voice ladder',
    0x030C1B80: 'costume voice ladder', 0x026F4AD4: 'Mii-enemy range (closed)', 0x026F4B58: 'Mii-enemy range',
    0x0270EDD0: 'Mii-enemy range', 0x027294D0: 'Mii-enemy range', 0x02DE6AA0: 'Mii-enemy range',
    0x02FE3FCC: 'Mii-enemy range', 0x02DE3544: '0x3A-0x3D (closed)', 0x02DE354C: '0x3A-0x3D (closed)',
    0x02715D04: '0x3A-0x3D (closed)', 0x02715D0C: '0x3A-0x3D (closed)', 0x02DF9514: '0x3A-0x3D (closed)',
    0x0273AC44: '0x0F-0x3D (closed)', 0x0273ACE4: '0x0F-0x3D (closed)', 0x02739B8C: 'switch ladder',
    0x02739B9C: 'switch ladder', 0x02739BA4: 'switch ladder', 0x0273B1DC: 'closed', 0x0273B1E4: 'closed',
    0x0273EF04: 'closed', 0x0273EF0C: 'closed', 0x02DC876C: '0x3B-0x3C (closed)', 0x02DC8774: '0x3B-0x3C',
    0x02DE551C: 'switch ladder', 0x02E38208: 'switch ladder', 0x02F4D3C0: 'switch ladder',
    0x02F4E2F8: '0x3A-0x3B (closed)', 0x02F4E300: '0x3A-0x3B', 0x02F4F9FC: '0x3A-0x3B', 0x02F4FA04: '0x3A-0x3B',
    0x0272DB80: 'float select ladder', 0x02799A38: '0x39-0x3C (closed)', 0x02799A40: '0x39-0x3C (closed)',
    0x02750B1C: 'switch ladder', 0x02750B28: 'closed',
}

EXAMPLE_PLAN = {
    "n": "0x60",
    "cave": "0x04B7F000",
    "kinds": [
        {"kind": "0x41", "name": "wolf", "cap": "Wolf", "base": "fox",
         "descriptor": {"from": "fox", "motion_hashes": None},
         "ui": {"id": 59, "name": "Wolf", "series": 2, "costumes": 8, "sort": [59, 59, 59]},
         "sound": {"bank_rows": "own"}, "kirby": {"copy": False}}
    ]
}


# ----------------------------------------------------------------------------------------------
class Image:
    def __init__(self, path):
        d, _o, _e, secs = rpx_patch.load(path)
        self.secs = secs
        self.mem = []
        self.bss = None
        for s in secs:
            if s[1] == 1 and s[3] and s[5]:
                self.mem.append((s[3], bytes(rpx_patch.section_data(d, s))))
            if s[1] == 8 and s[3]:
                self.bss = (s[3], s[5])
        td = next(x for b, x in self.mem if b == TEXT_BASE)
        self.W = array.array('I', td[:len(td) // 4 * 4])
        if sys.byteorder == 'little':
            self.W.byteswap()
        self.text_end = TEXT_BASE + 4 * len(self.W)
        symtab = next(i for i, s in enumerate(secs) if s[1] == 2)
        sym = rpx_patch.section_data(d, secs[symtab])
        vals = [struct.unpack('>I', sym[o + 4:o + 8])[0] for o in range(0, len(sym), 16)]
        self.rel = []
        for s in secs:
            if s[1] != 4:
                continue
            rel = rpx_patch.section_data(d, s)
            for o in range(0, len(rel), 12):
                off, info, add = struct.unpack('>IIi', rel[o:o + 12])
                self.rel.append((off, info & 0xFF, (vals[info >> 8] + add) & 0xFFFFFFFF))
        self.refs = defaultdict(list)
        for off, t, v in self.rel:
            self.refs[v].append((off, t))
        self.labels = sorted(set(v for off, t, v in self.rel if v >= 0x10000000))

    def find(self, a):
        for base, data in self.mem:
            if base <= a < base + len(data):
                return base, data
        return None, None

    def u32(self, a):
        if TEXT_BASE <= a < self.text_end:
            return self.W[(a - TEXT_BASE) >> 2]
        base, data = self.find(a)
        if data is None or a + 4 > base + len(data):
            return None
        return struct.unpack('>I', data[a - base:a - base + 4])[0]

    def u16(self, a):
        base, data = self.find(a)
        return None if data is None else struct.unpack('>H', data[a - base:a - base + 2])[0]

    def u8(self, a):
        base, data = self.find(a)
        return None if data is None else data[a - base]

    def cstr(self, a, maxlen=80):
        base, data = self.find(a or 0)
        if data is None or base == TEXT_BASE:
            return None
        o = a - base
        e = data.find(b'\0', o, o + maxlen)
        if e <= o:
            return None
        s = data[o:e]
        return s.decode() if all(32 <= c < 127 for c in s) else None

    def gap(self, a):
        """bytes from a to the next address something refers to (a table's size, at most)"""
        i = bisect.bisect_right(self.labels, a)
        return self.labels[i] - a if i < len(self.labels) else None

    def section_of(self, a):
        if TEXT_BASE <= a < self.text_end:
            return 'text'
        for base, data in self.mem:
            if base <= a < base + len(data):
                return {0x10000000: 'rodata', 0x102F6C00: 'data'}.get(base, 'sec%08X' % base)
        if self.bss and self.bss[0] <= a < self.bss[0] + self.bss[1]:
            return 'bss'
        return '?'


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def btarget(w, a):
    off = w & 0x3FFFFFC
    if off & 0x2000000:
        off -= 0x4000000
    return (a + off) & 0xFFFFFFFF


def dis1(img, a):
    """a short disassembly of one instruction (the forms this tool needs)"""
    w = img.u32(a)
    if w is None:
        return '?'
    op = w >> 26
    rd, ra = (w >> 21) & 31, (w >> 16) & 31
    if op in (10, 11):
        return '%s r%d, 0x%X' % ('cmplwi' if op == 10 else 'cmpwi', ra, w & 0xFFFF if op == 10 else s16(w & 0xFFFF))
    if op == 14 and ra == 0:
        return 'li r%d, 0x%X' % (rd, s16(w & 0xFFFF))
    if op == 18:
        return ('bl' if w & 1 else 'b') + ' 0x%08X' % btarget(w, a)
    return '.word 0x%08X' % w


def jt_at(img, a, max_back=0):
    """(N, table, default, cases) for a `cmplwi rX, N` at a followed by a bctr and a table of b"""
    W = img.W
    i = (a - TEXT_BASE) >> 2
    w = W[i]
    if (w >> 26) != 10:
        return None
    nb = w & 0xFFFF
    crf = (w >> 23) & 7
    dflt = None
    for j in range(i + 1, i + 14):
        x = W[j]
        if (x >> 26) == 16 and dflt is None and ((x >> 16) & 31) >> 2 == crf:
            o = s16(x & 0xFFFC)
            dflt = TEXT_BASE + 4 * j + o
        if (x >> 26) == 19 and ((x >> 1) & 0x3FF) == 16 and ((x >> 21) & 31) == 12 and dflt is None:
            dflt = 'bgtlr'
        if x == 0x4E800420:
            tbl = TEXT_BASE + 4 * (j + 1)
            cases = []
            for k in range(nb + 1):
                y = W[j + 1 + k]
                if (y >> 26) != 18 or (y & 3):
                    return None
                cases.append(btarget(y, tbl + 4 * k))
            return nb, tbl, dflt, cases
    return None


def check(img, item):
    """'ok' / a mismatch text for one inventory item"""
    cat, a, chk, act, what = item
    kind = chk[0]
    if kind == 'fn' or not a:
        return 'ok'
    w = img.u32(a)
    if w is None:
        return 'no such address'
    if kind == 'cmp':
        if (w >> 26) in (10, 11) and (w & 0xFFFF) == (chk[1] & 0xFFFF):
            return 'ok'
        # a function address whose compare is the first instruction (getters)
        return 'expected cmp 0x%X, found %s' % (chk[1], dis1(img, a))
    if kind == 'li':
        if (w >> 26) == 14 and ((w >> 16) & 31) == 0 and (w & 0xFFFF) == chk[1]:
            return 'ok'
        return 'expected li 0x%X, found %s' % (chk[1], dis1(img, a))
    if kind == 'jt':
        j = jt_at(img, a)
        if j and j[0] == chk[1]:
            return 'ok'
        return 'expected jump table bound 0x%X, found %s' % (chk[1], dis1(img, a))
    if kind == 'ptr':
        n = chk[1]
        relocated = set(off for off, t, v in img.rel if t == 1 and a <= off < a + 4 * n)
        nonnull = sum(1 for k in range(n) if img.u32(a + 4 * k))
        if len(relocated) == nonnull:
            return 'ok'
        return '%d relocated words of %d non-null' % (len(relocated), nonnull)
    if kind == 'pair':     # {u32 id, char *name} records, the first {-1, ...} (what a miss returns)
        n = chk[1]
        ok = all(img.u32(a + 8 * k + 4) == 0 or any(t == 1 for off, t, v in img.rel if off == a + 8 * k + 4)
                 for k in range(0, n, 20))
        first, last = img.u32(a), img.u32(a + 8 * (n - 1))
        if ok and first == 0xFFFFFFFF and last != 0xFFFFFFFF and img.u32(a + 8 * n) == 0xFFFFFFFF:
            return 'ok'
        return 'entry 0 id 0x%X, entry %d id 0x%X' % (first or 0, n - 1, last or 0)
    if kind == 'tbl':
        g = img.gap(a)
        n, st = chk[1], chk[2]
        if g is not None and g >= n * st and g - n * st < 8:
            return 'ok'
        return 'gap to the next label 0x%X (expected %d x %d)' % (g or 0, n, st)
    return 'ok'


def table_readers(img, a):
    """code sites that build the table's address (lis/addi pairs: their ADDR16_HA / LO relocations)"""
    return sorted(set((off - 2) & ~3 for off, t in img.refs.get(a, ()) if t in (4, 5, 6) and
                      TEXT_BASE <= off < img.text_end))


def new_imm(act, n, n_ui_new):
    if act == 'imm:count':
        return n
    if act == 'imm:last':
        return n - 1
    if act == 'imm:ui':
        return None
    return None


def print_inventory(img, n, n_ui_new=1):
    print('Fighter-kind expansion: code and tables (RPX checked; new kind count N = 0x%X)' % n)
    by_cat = defaultdict(list)
    for it in INV:
        by_cat[it[0]].append(it)
    totals = defaultdict(int)
    acts = defaultdict(int)
    for cat in ('names', 'switch65', 'switchpart', 'tables', 'getters', 'bounds', 'loops', 'predicates',
                'kirby', 'ui', 'encodings'):
        items = by_cat.get(cat, [])
        print('\n== %s (%d)' % (cat, len(items)))
        for it in items:
            _, a, chk, act, what = it
            st = check(img, it)
            extra = ''
            if chk[0] == 'jt':
                j = jt_at(img, a)
                if j:
                    d = j[2] if isinstance(j[2], str) else ('0x%08X' % j[2] if j[2] else '-')
                    extra = ' [table 0x%08X, %d cases (%d distinct), default %s]' % (j[1], j[0] + 1, len(set(j[3])), d)
            elif chk[0] in ('ptr', 'tbl', 'pair'):
                rd = table_readers(img, a)
                extra = ' [%s, %d reloc refs, code sites %s]' % (img.section_of(a), len(img.refs.get(a, ())),
                                                                ' '.join('0x%08X' % x for x in rd[:6]))
            elif act.startswith('imm') and act != 'imm:ui':
                v = new_imm(act, n, n_ui_new)
                w = img.u32(a)
                extra = ' [%s -> 0x%X: word 0x%08X=0x%08X]' % (dis1(img, a), v, a, (w & 0xFFFF0000) | v)
            elif chk[0] in ('cmp', 'li'):
                extra = ' [%s]' % dis1(img, a)
            print('  0x%08X  %-9s %-3s %s%s' % (a, act, 'OK' if st == 'ok' else '!!', what, extra))
            if st != 'ok':
                print('              check: %s' % st)
            totals[cat] += 1
            acts[act.split(':')[0]] += 1
    print('\n== totals')
    print('  by category: ' + ', '.join('%s %d' % kv for kv in totals.items()))
    print('  by action:   ' + ', '.join('%s %d' % kv for kv in sorted(acts.items())))
    must = [it for it in INV if it[3] in ('switch', 'table') or it[3].startswith('imm')]
    print('  to change for a kind >= 0x41 (switch / table / imm): %d sites; RAM: %d; verify: %d; optional: %d' % (
        len(must), acts['ram'], acts['verify'], acts['opt']))


# ----------------------------------------------------------------------------------------------
# scanners
X_LOGICAL_RA = {28, 60, 444, 412, 316, 124, 284, 476, 24, 536, 792, 824, 26, 954, 922}
X_NOWRITE = {0, 32, 4, 151, 183, 215, 247, 407, 439, 662, 918, 150, 663, 695, 727, 759, 983, 467, 144, 146,
             86, 54, 278, 246, 1014, 982, 598, 854, 535, 599, 567, 631, 470, 310}
X_LOADS = {23: 4, 87: 1, 279: 2, 343: 2, 55: 4, 119: 1, 311: 2, 375: 2, 535: 4, 599: 8, 567: 4, 631: 8}
X_STORES = {151: 4, 215: 1, 407: 2, 183: 4, 247: 1, 439: 2, 663: 4, 727: 8}
D_LOADS = {32: 4, 33: 4, 34: 1, 35: 1, 40: 2, 41: 2, 42: 2, 43: 2, 48: 4, 49: 4, 50: 8, 51: 8}
D_STORES = {36: 4, 37: 4, 38: 1, 39: 1, 44: 2, 45: 2, 52: 4, 53: 4, 54: 8, 55: 8}
UPDATE_D = {33, 35, 41, 43, 49, 51, 37, 39, 45, 53, 55}
VOLATILE = (0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)

# known kind functions: {address: kind parameter registers}; producers return a kind in r3
KIND_PARAMS = {0x02E4313C: {4}, 0x0275DB24: {3}, 0x0275DB38: {3}, 0x02E669F0: {4}, 0x02E694AC: {3},
               0x02E694E8: {3}, 0x028E25C0: {3}, 0x02E69510: {3}, 0x02E69560: {3}, 0x03058B6C: {4},
               0x03058B8C: {4}, 0x030BF9C0: {3}, 0x030C1FDC: {3}, 0x0309FE50: {4}, 0x0275BAB0: {3},
               0x02EA9064: {4}, 0x030C1B34: {4}, 0x02EA6BC4: {4}, 0x02EA5D64: {4}, 0x02EA90E0: {4},
               0x02EA9104: {4}, 0x02EA9120: {4}, 0x02EA913C: {4}, 0x02EA9158: {4}, 0x02AB8CB0: {3},
               0x0275B440: {5}}
KIND_PRODUCERS = {0x0309FDC8, 0x030BF9C0, 0x030C1FDC, 0x02BEF604}     # 0x02BEF604: [[r3]+4] BattleObject kind
KIND_TABLES = {0x102FF484: 4, 0x102FF588: 4, 0x10353DB4: 4, 0x1012F638: 2, 0x1012F6BC: 1, 0x1012F700: 1,
               0x1012F744: 1, 0x1012F788: 1, 0x100D21D8: 4}


def writes(w):
    op = w >> 26
    rd, ra = (w >> 21) & 31, (w >> 16) & 31
    if op in (7, 8, 12, 13, 14, 15) or op in (32, 34, 40, 42):
        return (rd,)
    if op in (33, 35, 41, 43):
        return (rd, ra)
    if op in (37, 39, 45, 49, 51, 53, 55, 20, 21, 23, 24, 25, 26, 27, 28, 29):
        return (ra,)
    if op == 46:
        return tuple(range(rd, 32))
    if op == 31:
        xo = (w >> 1) & 0x3FF
        if xo in X_LOGICAL_RA:
            return (ra,)
        if xo in X_NOWRITE:
            return (ra,) if xo in (183, 247, 439, 567, 631) else ()
        return (rd,)
    if (op == 18 and w & 1) or (op == 19 and ((w >> 1) & 0x3FF) == 528 and w & 1):
        return VOLATILE
    return ()


def functions(img):
    W = img.W
    starts = set()
    calls = defaultdict(list)
    for i in range(len(W)):
        w = W[i]
        if (w >> 26) == 18 and (w & 3) == 1:
            t = btarget(w, TEXT_BASE + 4 * i)
            if TEXT_BASE <= t < img.text_end:
                starts.add(t)
                calls[t].append(TEXT_BASE + 4 * i)
    for off, typ, val in img.rel:
        if typ == 1 and TEXT_BASE <= val < img.text_end and not (TEXT_BASE <= off < img.text_end):
            starts.add(val)
    return sorted(starts), calls


def jump_tables(img):
    W = img.W
    out = []
    for i in range(len(W)):
        if W[i] != 0x4E800420:
            continue
        for j in range(i - 1, max(i - 14, 0), -1):
            w = W[j]
            if (w >> 26) == 10 and not (w >> 21) & 1:
                j2 = jt_at(img, TEXT_BASE + 4 * j)
                if j2:
                    out.append((TEXT_BASE + 4 * j, (w >> 16) & 31) + j2)
                break
    return out


class Taint:
    """linear intra-procedural taint of kind values + parameter / return inference to a fixpoint
    value: (stride, add, origin, strong) = kind*stride + add"""

    def __init__(self, img, starts, calls, jts):
        self.img, self.starts, self.calls = img, starts, calls
        self.params = defaultdict(set, {k: set(v) for k, v in KIND_PARAMS.items()})
        self.prods = set(KIND_PRODUCERS)
        self.kf = defaultdict(set)
        self.events = {}
        self.switch_cmps = {j[0] for j in jts if j[2] == 0x40}
        self.bound = set(range(0x30, 0x46))
        self.prod_votes = defaultdict(set)

    def run(self, f):
        img, W = self.img, self.img.W
        i = bisect.bisect_right(self.starts, f)
        end = min(self.starts[i] if i < len(self.starts) else img.text_end, f + 0x20000)
        T, E, C, ST = {}, {}, {}, {}
        for r in self.params.get(f, ()):
            T[r] = (1, 0, 'p%d' % r, True)
        kf = self.kf.get(f, ())
        ev = []
        params, prods, bound = self.params, self.prods, self.bound

        def kill(r):
            T.pop(r, None)
            E.pop(r, None)
            C.pop(r, None)
        for k in range((f - TEXT_BASE) >> 2, (end - TEXT_BASE) >> 2):
            w = W[k]
            a = TEXT_BASE + 4 * k
            op = w >> 26
            rd, ra = (w >> 21) & 31, (w >> 16) & 31
            if op in (12, 13, 14):
                imm = s16(w & 0xFFFF)
                if op == 14 and ra == 0:
                    kill(rd)
                    C[rd] = imm & 0xFFFFFFFF
                    continue
                t, e, c = T.get(ra), E.get(ra), C.get(ra)
                kill(rd)
                if t:
                    T[rd] = (t[0], t[1] + imm, t[2], t[3])
                elif e:
                    E[rd] = ((e[0] + imm) & 0xFFFFFFFF,) + e[1:]
                elif c is not None:
                    C[rd] = (c + imm) & 0xFFFFFFFF
            elif op == 15:
                imm = (w & 0xFFFF) << 16
                t = T.get(ra) if ra else None
                e = E.get(ra) if ra else None
                c = C.get(ra) if ra else 0
                kill(rd)
                if t:
                    E[rd] = ((imm + t[1]) & 0xFFFFFFFF, t[0], t[2], t[3])
                elif e:
                    E[rd] = ((e[0] + imm) & 0xFFFFFFFF,) + e[1:]
                elif c is not None:
                    C[rd] = (c + imm) & 0xFFFFFFFF
            elif op == 7:
                t = T.get(ra)
                kill(rd)
                if t:
                    imm = s16(w & 0xFFFF)
                    T[rd] = (t[0] * imm, t[1] * imm, t[2], t[3])
            elif op in (10, 11):
                t = T.get(ra)
                if t and t[0] == 1:
                    v = (w & 0xFFFF) if op == 10 else s16(w & 0xFFFF)
                    if t[3] or (v - t[1]) in bound or a in self.switch_cmps:
                        ev.append(('cmp', a, v, t[1], t[2], t[3]))
            elif op == 21:
                sh, mb, me = (w >> 11) & 31, (w >> 6) & 31, (w >> 1) & 31
                t = T.get(rd)
                kill(ra)
                if t:
                    if sh == 0 and me == 31:
                        T[ra] = t
                    elif sh and me == 31 - sh and mb == 0:
                        T[ra] = (t[0] << sh, t[1] << sh, t[2], t[3])
            elif op == 24:
                c, t = C.get(rd), T.get(rd)
                kill(ra)
                if c is not None:
                    C[ra] = c | (w & 0xFFFF)
                elif t and not (w & 0xFFFF):
                    T[ra] = t
            elif op == 31:
                xo = (w >> 1) & 0x3FF
                rb = (w >> 11) & 31
                if xo in (444, 954, 922):
                    if xo == 444 and rd != rb:
                        kill(ra)
                        continue
                    t, e, c = T.get(rd), E.get(rd), C.get(rd)
                    kill(ra)
                    if t:
                        T[ra] = t
                    if e and xo == 444:
                        E[ra] = e
                    if c is not None:
                        C[ra] = c
                    continue
                if xo in (266, 10):
                    ta, tb, ca, cb = T.get(ra), T.get(rb), C.get(ra), C.get(rb)
                    kill(rd)
                    tt, cc = (ta, cb) if ta else (tb, ca)
                    if tt and cc is not None:
                        E[rd] = ((cc + tt[1]) & 0xFFFFFFFF, tt[0], tt[2], tt[3])
                    elif ca is not None and cb is not None:
                        C[rd] = (ca + cb) & 0xFFFFFFFF
                    continue
                if xo in X_LOADS or xo in X_STORES:
                    ta, tb, ca, cb = T.get(ra), T.get(rb), C.get(ra), C.get(rb)
                    tt, cc = (ta, cb) if ta else (tb, ca)
                    if tt and cc is not None:
                        ev.append(('tbl', a, (cc + tt[1]) & 0xFFFFFFFF, tt[0], tt[2], tt[3]))
                    if xo in X_LOADS and xo not in (535, 599, 567, 631):
                        kill(rd)
                    continue
                for r in writes(w):
                    kill(r)
            elif op in D_LOADS:
                d = s16(w & 0xFFFF)
                e = E.get(ra)
                if e:
                    ev.append(('tbl', a, (e[0] + d) & 0xFFFFFFFF, e[1], e[2], e[3]))
                if op in (48, 49, 50, 51):
                    if op in UPDATE_D:
                        kill(ra)
                    continue
                kill(rd)
                if ra == 1 and op == 32 and d in ST:
                    T[rd] = ST[d]
                elif ra != 1 and op in (32, 34, 40, 42):
                    key = 'f%d:%X' % (D_LOADS[op], d & 0xFFFF)
                    T[rd] = (1, 0, key, key in kf)
                if op in UPDATE_D:
                    kill(ra)
            elif op in D_STORES:
                d = s16(w & 0xFFFF)
                if ra == 1:
                    if op == 36 and rd in T:
                        ST[d] = T[rd]
                    else:
                        ST.pop(d, None)
                if op in UPDATE_D:
                    kill(ra)
            elif op == 18:
                tgt = btarget(w, a)
                if (w & 1) or not (f <= tgt < end):
                    pk = params.get(tgt, ())
                    for r in range(3, 11):
                        t = T.get(r)
                        if t and (t[3] or r in pk):
                            ev.append(('arg', a, tgt, r, t[0], t[1], t[2], t[3]))
                    if w & 1:
                        for r in VOLATILE:
                            kill(r)
                        T[3] = (1, 0, 'r%08X' % tgt, tgt in prods)
            elif op == 19:
                xo = (w >> 1) & 0x3FF
                if xo == 16 and rd == 20 and 3 in T:
                    ev.append(('ret', a) + T[3])
                elif xo == 528 and w & 1:
                    for r in VOLATILE:
                        kill(r)
            else:
                for r in writes(w):
                    kill(r)
        return ev

    def evidence(self, e):
        if e[0] == 'arg':
            if e[4] == 1 and e[5] == 0 and e[3] in self.params.get(e[2], ()):
                return e[6]
        elif e[0] == 'cmp':
            if e[1] in self.switch_cmps and e[3] == 0:
                return e[4]
        elif e[0] == 'tbl':
            if KIND_TABLES.get(e[2]) == e[3]:
                return e[4]
        return None

    def solve(self, rounds=12):
        callers = defaultdict(set)
        for g, sites in self.calls.items():
            for s in sites:
                i = bisect.bisect_right(self.starts, s) - 1
                if i >= 0:
                    callers[g].add(self.starts[i])
        nsites = {g: len(v) for g, v in self.calls.items()}
        work = set(self.starts)
        for _ in range(rounds):
            for f in work:
                self.events[f] = self.run(f)
            new_p, new_k, new_r = defaultdict(set), defaultdict(set), set()
            argstat = defaultdict(lambda: defaultdict(int))
            for f, ev in self.events.items():
                for e in ev:
                    o = self.evidence(e)
                    if o:
                        if o[0] == 'p':
                            new_p[f].add(int(o[1:]))
                        elif o[0] == 'f':
                            new_k[f].add(o)
                        elif o[0] == 'r':
                            self.prod_votes[int(o[1:], 16)].add(e[1])
                    if e[0] == 'arg' and e[4] == 1 and e[5] == 0 and e[7]:
                        argstat[e[2]][e[3]] += 1
                    elif e[0] == 'ret' and e[2] == 0 and e[1] == 1 and e[4]:
                        new_r.add(f)
            for g, votes in self.prod_votes.items():
                if len(votes) >= 2 and len(votes) * 3 >= nsites.get(g, 1):
                    new_r.add(g)
            for g, regs in argstat.items():
                n = nsites.get(g, 1)
                for r, k in regs.items():
                    if (k >= 2 and k * 2 >= n) or (n == 1 and k == 1):
                        new_p[g].add(r)
            changed = set()
            for f, regs in new_p.items():
                if regs - self.params[f]:
                    self.params[f] |= regs
                    changed.add(f)
                    changed |= callers.get(f, set())
            for f, keys in new_k.items():
                if keys - self.kf[f]:
                    self.kf[f] |= keys
                    changed.add(f)
            for f in new_r - self.prods:
                self.prods.add(f)
                changed |= callers.get(f, set())
            if not changed:
                break
            work = changed & set(self.starts)


def branch_after(W, i, crf):
    for j in range(i + 1, min(i + 12, len(W))):
        w = W[j]
        op = w >> 26
        if op == 16 or (op == 19 and ((w >> 1) & 0x3FF) in (16, 528)):
            bo, bi = (w >> 21) & 31, (w >> 16) & 31
            if bi >> 2 != crf:
                continue
            if (bo & 0x14) == 0x14:
                return None
            name = ['lt', 'gt', 'eq', 'so'][bi & 3]
            if not bo & 8:
                name = {'lt': 'ge', 'gt': 'le', 'eq': 'ne', 'so': 'ns'}[name]
            return name
        if op in (10, 11) and ((w >> 23) & 7) == crf:
            return None
    return None


def mark(a, inv):
    return 'inv' if a in inv else 'ok' if a in OKSITES else ('no' if a in SKIP else '?')


def scan(img):
    W = img.W
    inv = set(it[1] for it in INV)
    print('scanning (functions, jump tables, data flow; ~30 s)...', file=sys.stderr)
    starts, calls = functions(img)
    jts = jump_tables(img)
    T = Taint(img, starts, calls, jts)
    T.solve()
    cmps = {}
    for f, ev in T.events.items():
        for e in ev:
            if e[0] == 'cmp':
                cmps[e[1]] = e
    print('\n== 1. jump tables bounded by 0x30-0x40 (%d jump tables in all)' % len(jts))
    for a, reg, nb, tbl, dflt, cases in jts:
        if 0x30 <= nb <= 0x40 or a in inv:
            e = cmps.get(a)
            cls = ('S' if e[5] else 'w:' + e[4]) if e else '-'
            print('  %-3s 0x%08X r%-2d cases %3d (%2d distinct) table 0x%08X  %s  %s' % (
                mark(a, inv), a, reg, nb + 1, len(set(cases)), tbl, cls, SKIP.get(a, '')))
    print('\n== 2. relational compares with an effective bound 0x39-0x42 (S = proven kind, w:<field> = loaded '
          'value, - = other); "-" rows outside the inventory are mostly sizes / chars')
    nshow = defaultdict(int)
    for i in range(len(W)):
        w = W[i]
        op = w >> 26
        if op not in (10, 11) or (w >> 21) & 1:
            continue
        a = TEXT_BASE + 4 * i
        imm = (w & 0xFFFF) if op == 10 else s16(w & 0xFFFF)
        e = cmps.get(a)
        add = e[3] if e else 0
        eff = imm - add
        if not 0x39 <= eff <= 0x42:
            continue
        cond = branch_after(W, i, (w >> 23) & 7)
        if cond not in ('lt', 'gt', 'le', 'ge'):
            continue
        cls = ('S:' + e[4] if e[5] else 'w:' + e[4]) if e else '-'
        m = mark(a, inv)
        nshow[(m, cls[0])] += 1
        if cls[0] != '-' or m != '?':
            print('  %-3s 0x%08X %-24s %-2s eff 0x%X  %s  %s' % (m, a, dis1(img, a), cond, eff, cls, SKIP.get(a, OKSITES.get(a, ''))))
    print('  counts (mark, class): ' + ', '.join('%s/%s %d' % (k[0], k[1], v) for k, v in sorted(nshow.items())))
    print('\n== 3. li rX, 0x41')
    for i in range(len(W)):
        w = W[i]
        if (w >> 26) == 14 and ((w >> 16) & 31) == 0 and (w & 0xFFFF) == 0x41:
            a = TEXT_BASE + 4 * i
            m = mark(a, inv)
            ctr = any(W[i + k] & 0xFC1FFFFF == 0x7C0903A6 for k in (1, 2, 3))
            print('  %-3s 0x%08X %s%s  %s' % (m, a, dis1(img, a), ' (ctr)' if ctr else '', SKIP.get(a, '')))
    print('\n== 4. pointer tables of 56-66 entries (relocation runs, nulls allowed)')
    A = set(off for off, t, v in img.rel if t == 1 and 0x10000000 <= off < 0xC0000000)
    labels = set(img.labels)
    for base, data in img.mem:
        if base < 0x10000000:
            continue
        n = len(data) // 4
        k = 0
        while k < n:
            if base + 4 * k not in A:
                k += 1
                continue
            j, holes = k, 0
            while j < n and ((base + 4 * j) in A or (img.u32(base + 4 * j) == 0 and holes < 3)):
                holes += (base + 4 * j) not in A
                j += 1
            while j > k and (base + 4 * (j - 1)) not in A:
                j -= 1
            s, e = base + 4 * k, base + 4 * j
            cuts = [s] + [x for x in range(s + 4, e, 4) if x in labels] + [e]
            for x, y in zip(cuts, cuts[1:]):
                m = (y - x) // 4
                if 56 <= m <= 66:
                    first = [img.cstr(img.u32(x + 4 * q)) or '0x%08X' % img.u32(x + 4 * q) for q in range(3)]
                    print('  %-3s 0x%08X %d entries  %s' % (mark(x, inv), x, m, ', '.join(first)))
            k = j
    print('\n== 5. constant-base indexed tables of 56-70 entries (gap to the next referenced address)')
    acc = defaultdict(list)
    for i in range(len(W)):
        w = W[i]
        op = w >> 26
        if op == 31 and ((w >> 1) & 0x3FF) in X_LOADS:
            ra, rb = (w >> 16) & 31, (w >> 11) & 31
            for cr, ir in ((ra, rb), (rb, ra)):
                c = const_before(W, i, cr)
                if c is not None and c >= 0x10000000:
                    acc[(c, stride_before(W, i, ir))].append(TEXT_BASE + 4 * i)
                    break
        elif op == 15 and ((w >> 16) & 31):
            rd = (w >> 21) & 31
            for j in range(i + 1, min(i + 4, len(W))):
                x = W[j]
                if (x >> 26) in D_LOADS and ((x >> 16) & 31) == rd:
                    c = (((w & 0xFFFF) << 16) + s16(x & 0xFFFF)) & 0xFFFFFFFF
                    if c >= 0x10000000:
                        acc[(c, stride_before(W, i, (w >> 16) & 31))].append(TEXT_BASE + 4 * i)
                    break
                if rd in writes(x):
                    break
    for (c, st), sites in sorted(acc.items()):
        g = img.gap(c)
        if st > 0 and g and 56 <= g / st <= 70:
            print('  %-3s 0x%08X stride %d, %.0f entries, %s, read at %s' % (
                mark(c, inv), c, st, g / st, img.section_of(c), ' '.join('0x%08X' % s for s in sites[:4])))


def const_before(W, i, r, back=10):
    j = i - 1
    while j >= i - back:
        w = W[j]
        if r in writes(w):
            op = w >> 26
            if op == 15 and ((w >> 16) & 31) == 0:
                return (w & 0xFFFF) << 16
            if op == 14 and ((w >> 16) & 31) == 0:
                return s16(w & 0xFFFF) & 0xFFFFFFFF
            if (op == 12 or op == 14) and ((w >> 21) & 31) == r:
                b = const_before(W, j, (w >> 16) & 31, back - (i - j))
                return None if b is None else (b + s16(w & 0xFFFF)) & 0xFFFFFFFF
            if op == 24:
                b = const_before(W, j, (w >> 21) & 31, back - (i - j))
                return None if b is None else b | (w & 0xFFFF)
            return None
        j -= 1
    return None


def stride_before(W, i, r, back=10):
    for j in range(i - 1, i - back, -1):
        w = W[j]
        if r in writes(w):
            op = w >> 26
            if op == 21:
                sh, mb, me = (w >> 11) & 31, (w >> 6) & 31, (w >> 1) & 31
                if sh and mb == 0 and me == 31 - sh:
                    return 1 << sh
            if op == 7:
                return s16(w & 0xFFFF)
            return 1
    return 1


# ----------------------------------------------------------------------------------------------
def data_files(root):
    import s4param
    print('\n== data files under %s with one entry per kind / per character id' % root)
    for dp, dn, fn in sorted(os.walk(root)):
        for f in sorted(fn):
            if 'fighter_param_vl_' in f:
                continue
            p = os.path.join(dp, f)
            try:
                items = s4param.parse(open(p, 'rb').read())
            except Exception:
                continue
            for gi, it in enumerate(x for x in items if isinstance(x, list)):
                ents = it[2]
                if not ents:
                    continue
                notes = []
                for c in range(min(len(ents[0]), 6)):
                    vals = [e[c][1] for e in ents if e[c][0] in (1, 2, 3, 4, 5, 6)]
                    if len(vals) != len(ents):
                        continue
                    ks = [v for v in vals if 0 <= v <= 0x40]
                    if len(set(ks)) >= 30 and len(ks) >= len(ents) * 0.8:
                        notes.append('value %d = kind? (%d distinct, max %d)' % (c, len(set(vals)), max(vals)))
                if notes:
                    print('  %-48s group %d: %d entries x %d values; %s' % (
                        os.path.relpath(p, root), gi, len(ents), len(ents[0]), '; '.join(notes)))


# ----------------------------------------------------------------------------------------------
def kind_by_name(img):
    names = {}
    for k in range(NKINDS):
        names[img.cstr(img.u32(0x102FF484 + 4 * k))] = k
    return names


def plan(img, path):
    spec = json.load(open(path)) if path != '-' else EXAMPLE_PLAN
    n = int(str(spec.get('n', '0x60')), 0)
    kinds = spec['kinds']
    names = kind_by_name(img)
    print('# extra kinds plan: N = 0x%X (kinds 0x41-0x%X), %d records' % (n, n - 1, len(kinds)))
    print('# global immediates')
    for cat, a, chk, act, what in INV:
        if act in ('imm:count', 'imm:last'):
            v = new_imm(act, n, 0)
            w = img.u32(a)
            print('0x%08X=0x%08X   # %s: %s' % (a, (w & 0xFFFF0000) | v, dis1(img, a), what.split(';')[0]))
    nui = sum(1 for k in kinds if k.get('ui'))
    print('0x%08X=0x%08X   # character name table count 0x53 + %d' % (0x0293DCD4, (img.u32(0x0293DCD4) & 0xFFFF0000) | (0x53 + nui), nui))
    print('0x%08X=0x%08X   # random-select entries 0x51 + %d (<= 96 database entries in all)' % (
        0x02FFB644, (img.u32(0x02FFB644) & 0xFFFF0000) | (0x51 + nui), nui))
    sw = [it for it in INV if it[3] == 'switch']
    for rec in kinds:
        k = int(str(rec['kind']), 0)
        base = rec['base']
        b = names[base] if not str(base)[0].isdigit() else int(str(base), 0)
        print('\n# kind 0x%02X %s / %s (native cases from 0x%02X %s)' % (k, rec['name'], rec['cap'], b, base))
        print('#  names: "%s", "%s", "fighter_param_vl_%s" -> cave name tables entry 0x%X' % (
            rec['name'], rec['cap'], rec['name'], k))
        how = {0x02E43148: 'own case returning the copied descriptor (b to the base case only if it shares '
                           'its motion table)',
               0x02EA6C94: 'cave copy of the base case with kind 0x%X\'s fields (RAM doc), loading the base too' % k,
               0x02EA5DA0: 'cave copy of the base case with kind 0x%X\'s fields (RAM doc)' % k}
        for _, a, chk, act, what in sw:
            j = jt_at(img, a)
            print('#  switch 0x%08X entry 0x%X: base case 0x%08X; %s  (%s)' % (
                a, k, j[3][b], how.get(a, 'b to it'), what.split(':')[0].split(';')[0]))
        for _, a, chk, act, what in INV:
            if act == 'table' and chk[0] == 'tbl' and chk[1] == 65:
                st = chk[2]
                v = {1: img.u8, 2: img.u16, 4: img.u32}[st](a + st * b)
                print('#  table 0x%08X[0x%X] = %d (%s\'s)' % (a, k, v, base))
        desc = rec.get('descriptor', {})
        print('#  descriptor: copy of %s\'s (writable memory, +0 = 0x%X, +0x1C = 0)%s' % (
            desc.get('from', base), k, '; own motion table from ' + desc['motion_hashes']
            if desc.get('motion_hashes') else '; base motion table'))
        print('#  vl load / unload: %s\'s parser / free functions storing into kind 0x%X\'s fields (RAM doc)' % (base, k))
        if rec.get('ui'):
            u = rec['ui']
            print('#  UI: ui_character_db entry at position %d (id %d, kind 0x%X), name table {%d, "%s"}' % (
                u['id'], u['id'], k, u['id'], u['name']))
        if rec.get('kirby', {}).get('copy'):
            print('#  Kirby: copy_grant bound, copy record / hat tables rows for 0x%X (optional)' % k)


def main():
    args = sys.argv[1:]
    path = RPX
    if args and not args[0].startswith('--'):
        path = args.pop(0)
    n = int(args[args.index('--n') + 1], 0) if '--n' in args else 0x60
    img = Image(path)
    if '--plan' in args:
        plan(img, args[args.index('--plan') + 1])
        return
    print_inventory(img, n)
    if '--json' in args:
        out = [{'category': c, 'address': '0x%08X' % a, 'check': list(ch), 'action': act, 'what': w,
                'status': check(img, (c, a, ch, act, w))} for c, a, ch, act, w in INV]
        json.dump(out, open(args[args.index('--json') + 1], 'w'), indent=1)
    if '--scan' in args:
        scan(img)
    if '--params' in args:
        data_files(args[args.index('--params') + 1])


if __name__ == '__main__':
    main()
