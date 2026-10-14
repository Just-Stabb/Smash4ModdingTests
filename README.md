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
