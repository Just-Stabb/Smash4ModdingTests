# Games & More menu (ui/lumen/other, MenuViewOtherScene)

Found for the Smash Run button (user: put it in the empty space on the right). Not yet in game.

## Layout (vanilla other.lm, 1920x1080)
Root places bg_base_mc_anim, btn_01..btn_07 (character 108) and hit_01..hit_07 (character 111, a 32x32 shape: a
button's touch / cursor rect = hit_NN's centre +- 16 * its scale). Vanilla has the seven buttons across the whole
screen (btn_01 Vault, 03 Solo, 04 Group top; 07 amiibo, 05 Custom, 02 Stage Builder, 06 Options bottom): the
user's menu (Vault / Solo / Group / Stage Builder in a left column, three small buttons under them) is a modded
other.lm, so the new button has to be laid out on the user's file.
- Script (tools/lm_actions.py): animation helpers; `_global.SelectItemNum = 8` and action 9 loops
  `btn_0<i+1>.gotoAndPlay("in_<i+1>")` up to it: btn_08 would get in_8 (character 108 has in_1..7 / out_1..7).
- Art per button: nested sprites go to the frame named after their ancestor button (GotoFrame2 "btn_0N"):
  characters 19 (highlight), 32 (frame), 58 (picture), 72 (selected picture), 92 (text) need a btn_08 frame with
  content; 93, 95, 97, 99, 101, 104 (selected-text clips) only the label. Texts btn_01-05 are baked images
  (img-00003.nut); btn_06's is a text field `MmenOther_6$3$1` (character 89): `LABEL$a$b` binds a text field to
  an msbt label, so btn_08 can use a copy named `MmenOther_8$3$1`.
- Keyframes: new placements go in the root's frame 0 and every F105 keyframe (frames 0, 1, 12, 13, 24).

## Native
- `MenuViewOtherScene` (scene table 0x100CBE98; ctor 0x02C8C16C, vtable 0x1010ECF8, movie "other"), embedded in
  `MenuButtonSequenceScene` (ctor 0x02189BA0) at +0x23A0 as page 16 (0x02C8C350).
- Buttons: 0x02C8C280 calls `0x029ABC98(this, id, result, 0)` seven times (ids 0x3B Vault -> result 8, 0x37 Solo 3,
  0x38 Group 4, 0x39 Custom 5, 0x3A Stage Builder 6, 0x3C Options 9, 0x3D amiibo 10). Through 0x029ABC68 it fills
  per-button arrays (up to 16, count +0x144): +0x188 button number (param/ui/ui_button_sequence.bin group 1, the
  entry's field 6: btn_%02d / hit_%02d), +0x1C8 enabled (0x02946220), +0x148 result, +0x1D8 shown, +0x1E8 id.
  Group-1 entry: u32 id, u8 msbt number (MmenOther_N), u32, u8, u32, u8, u8 button number, u32, 6 s8 filters;
  page 16 lists ids 59, 55, 56, 57, 58, 60, 61 (room for 11). Ids 0-114 exist.
- Cursor: no table found: navigation is computed from the hit rects (0x0299DFB8, 0x0299E0A4, 0x0299E254), so a
  hit_08 on the right should be reachable (d-pad path not traced end to end).
- A (0x029ABDF0): result = +0x148[index] -> 0x029AD320 -> MenuButtonSequenceScene vtable +0xCC 0x0218AAA0(this,
  16, result) -> page 16's switch 0x0218B970 (jump table 0x0218B98C): 1 back, 3 Solo 0x0218C644, 4 Group 0x0218BF98,
  5 page 20 (Custom), 6 0x029ACFC0(this, 0x5A, 0) Stage Builder, **7 0x0218BA0C: 0x029ACFC0(this, 0x5B, 0): no
  vanilla button gives result 7**, 8 Vault 0x0218CA68, 9 page 31 (Options), 10 0x029ACFC0(this, 0x75, 0) amiibo.
- Leaving the menu: 0x029ACFC0 posts a key to the root controller (0x030CB3B8: root+0xA0); at the menu's end
  0x02C876E4 maps it through the root's +0xB4 map (built in 0x02C841E4) to a state at +0x8C (missing key: 2).
  0x5A -> 0x75, **0x5B -> 0x76** (0x02C871A8), 0x75 -> 0x77, 0x31 -> 0x5F (Training). Launcher 0x02C881D4:
  0x75 mode 0x2E StageMakeSequenceScene; **0x76 (0x02C893E8) mode 0x2F "StageMakeViewEditInfoScene"**; 0x77 mode
  0x30 NfpSequenceScene. Result 7 -> key 0x5B -> state 0x76 is a spare chain only reachable from that case: the
  hook for Smash Run (change the key at 0x0218BA10, or what state 0x76's case starts).
- An 8th button: a group-1 entry (e.g. id 115: [115, 8, 3, 1, 0, 0, 8, -1, 0 x 6]) and id 115 in page 16's list;
  a cave at the end of 0x02C8C280 (0x02C8C324) adding `0x029ABC98(this, 115, 7, 0)`; MmenOther_8 / MmenOther_8h
  (help: "%s%dh" at 0x0293AF58). Risk: the enabled flag (0x02946220 reads a table at 0x1034069C + 8: 0 for ids
  past its count once loaded): else fill the arrays with 0x029ABC68 directly.
