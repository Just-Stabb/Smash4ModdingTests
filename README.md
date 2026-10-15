# Smash4ModdingTests

Moveset code experiments for Super Smash Bros. for Wii U, written in MSC-C.

- [`docs/MSC-C_Guide.md`](docs/MSC-C_Guide.md): how to write MSC-C, with the MSC Note Sheet's assembly translated into C
- [`reference/msc-note-sheet/`](reference/msc-note-sheet/): CSV snapshot of every tab of the MSC Note Sheet
- `tools/setup_toolchain.sh`: fetches Jam1Garner's [mscdec](https://github.com/jam1garner/mscdec) and [msclang](https://github.com/jam1garner/msclang)
- `tools/mscinfo.xml`: syscall names (`WorkModule`, `StatusModule`, ...). Pass `-x tools/mscinfo.xml` to both tools
- `tools/action_table.py`: lists which function handles each action/key in a decompiled fighter
- [`fighters/gekkouga/`](fighters/gekkouga/): Greninja's decompiled MSC, with a map of its action scripts
- [`fighters/gekkouga/specials.md`](fighters/gekkouga/specials.md): how Greninja's special moves work, script by script
- [`fighters/kirby/specials.md`](fighters/kirby/specials.md): Kirby's specials and copy abilities (all Kirby scripts labelled in `kirby.c`)
- `tools/vbn_bones.py`: lists the bones in a `model.vbn` (index = the bone number `ModelModule` takes)
- [`fighters/ryu/README.md`](fighters/ryu/README.md): Ryu Focus Attack shield-dash cancel
- `tools/rpx_patch.py`: patches 32-bit values in the game executable (`cross_f.rpx`), e.g. article max counts from `reference/FighterArticles.xml`. Writes a new file; patched executables go in `build/` (git-ignored)
- `tools/starcopy_cave.py`: builds the native code patch for "Kirby gets a copy ability after 12 star missile hits" (prints words for `rpx_patch.py`)
- `tools/acmd.py`: reads/edits ACMD files (`animcmd/body/game.bin` etc., the format FITX uses). `dump game.bin specialairs` prints a script by animation name, `find game.bin Search_Collision` lists scripts using a command. Command table in `tools/acmd_info.json`, generated from Sammi Husky's [SALT](https://github.com/Sammi-Husky/SALT) (MIT)
- [`fighters/metaknight/README.md`](fighters/metaknight/README.md): Meta Knight ledge grab during Mach Tornado
- [`docs/native-notes.md`](docs/native-notes.md): notes from reading the game executable (Kirby BattleObject commands, homing investigation)
