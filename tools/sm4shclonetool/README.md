# Sm4shCloneTool

Clone Super Smash Bros. for Wii U fighters and stages into **new slots**, the way BrawlEx's Clone Engine does for
Brawl: pick a base, give the clone a name, choose its portraits and options, see where it lands on the character /
stage select, and build a package to install. A fighter clone is a real new fighter kind (0x41, 0x42, ...) with its
own character id, folder, parameters, names and portraits; a stage clone is a new stage kind with its own stage-select
slot, folder, icons and names. Nothing of the game is replaced.

![Fighters tab](screenshots/gui_fighters_vanilla_ui.png)

(Screenshots from a test setup whose UI folder has only a few portraits: the others are drawn as name tiles. With
your full UI every tile is its portrait. More in `screenshots/`: the stage tab, the character / stage select previews.)

## What you need

- **Windows with Python 3.9 or later** (python.org; tick "Add python.exe to PATH"). Tkinter comes with it.
  Linux / macOS work too (`python3 gui.py`; Tkinter from your package manager).
- Your game's **data folder** as you have it installed: `param/`, `ui/`, `fighter/`, `stage/`, `sound/` (dumped from
  the game, or your mod's `content/patch/data` merged over a dump). Vanilla or modded, both work. At least
  `param/ui/ui_character_db.bin` (fighters) or `param/ui/ui_stage_db.bin` (stages), `ui/message/melee.msbt` and the base's
  folder.
- Your **cross_f.rpx** (`code/cross_f.rpx`): the game's latest update (v288) unmodified, or one this tool patched
  before. New fighter / stage kinds need the patched executable; without one the tool only makes the data files.
- Optional: a **custom UI folder** (your own portraits, your own character-select layout `lumen/chara/chara.lm`).

## Install

1. Unzip `Sm4shCloneTool_v1_2.zip` anywhere.
2. Double-click **setup.bat** once (installs numpy and Pillow with pip).
3. Double-click **run.bat** (the window) or use **run_cli.bat** (the command line).

## The window

**Folders** (remembered between runs, in `%USERPROFILE%\.sm4shclonetool.json`):

| field | what |
|---|---|
| Game data folder | your data folder (see above) |
| Custom UI folder | optional: the `ui` folder your game shows, if it is not `data/ui` (a UI mod) |
| Current cross_f.rpx | the executable to patch; the label on the right says what it is (vanilla / patched by Sm4shCloneTool, with its clones / not vanilla) |
| Output / project folder | where the package and `sm4shclonetool_project.json` go; use the same folder for every clone of one project |
| Patch anyway | for an executable that is not vanilla because another mod uses the code space after the game's: the clone code then goes after that mod's code (see "The executable") |

Press **Load / refresh** after changing a folder.

### Fighters tab

Click a **base fighter** in the roster (icons from your UI's `chr_10`, else `chr_00` / `stock_90` / `chr_13`; a `*`
marks your clones, which can be bases too). Then fill in:

| field | what | rules |
|---|---|---|
| Internal name | the folder and file name: `fighter/<name>/`, `fighter_param_vl_<name>.bin`, `<name>.mscsb` | lowercase letters / digits, 2-16, not taken |
| Cap name | the capitalised file name (`snd_se_<Cap>.nus3bank`, `Fin<Cap>` effects) | a capital, then letters / digits |
| UI name | portraits (`chr_00_<UiName>_01.nut`) and text labels (`MmelCharaN_01_<UiName>`) | a capital, then letters / digits, no spaces, not taken |
| Title | the name the game shows (the character select, results); capitals version made for you | any text |
| Subtitle | the character select's second line (`MmelCharaA`); empty = the base's | any text |
| Series icon id | the series emblem (the base's by default) | number |
| Costumes | how many costumes the character select offers (the base's by default) | 1-16 |
| Fighter kind / Character id | filled in: the next free kind (from 0x41) and id (from 59) | they must be consecutive; the tool checks every database, name table and label |
| CSS: place after | the character the clone comes after on the character select (name or id) | see "Character select placement" |
| CSS: or first sort key | the sort key itself, instead of "after" | 1-126 |

**Options**

- **Custom moves**: the clone owns its base's custom moves (the save data's owned-move bits are per character; the
  patch maps the clone's id to its base's), and gets the Customize menu's names / icons (`ui/message/menu.msbt`,
  `spi_10_<UiName>_*`) when your files have them.
- **Victory fanfare and KO voices**: the clone's records in `sound/config/bgm_fighter.fbb` and
  `commonsoundtable.csb` (the base's). Without them the clone has no fanfare and no KO scream.
- **Own articles**: select the base's articles (its projectiles and items, e.g. Fox's `blaster`) the clone should own
  as new weapon kinds (0x185 on): their files then load from the clone's own folder (`fighter/<name>/model/<article>`,
  `script/animcmd/weapon/<article>`, ...) so you can change them without changing the base's. Articles not selected
  keep loading from the base's folder.
- **Fully independent clone (recommended, on by default)**: turns on the three below, so the clone shares no
  file, bank or article with its base:
  - **Own sound bank**: its copies of the base's sound banks (`snd_se_<Cap>`, `snd_vc_<Cap>` ...) get their own
    bank ids and their own soundlabeltable rows (`sound/config/soundlabeltable.bin`), and every sound id in its
    ACMD scripts (body and own articles) moves to its rows: editing its banks changes only the clone. The sounds
    are byte-for-byte copies (nothing re-encoded). Sound ids inside MSC scripts are not moved (the tool can't read
    MSC): a clone whose MSC plays sounds by id keeps the base's for those.
  - **Own effect bank**: the clone's effects (`effect/<name>/`, ids `0x3KK....`) are its own and the base's bank is
    no longer loaded with it. Its own articles' effects move to its bank too; an article it doesn't own keeps the
    base's effects, which then only show when the base is in the match.
  - **Own articles (all)**: every article of the base (its article list) becomes the clone's own weapon kind, with
    its files under the clone's folder. Without an own sound bank the articles keep the base's sounds.
- **In the random select**: whether the character select's random pick can choose the clone (on by default).
- Kirby: Kirby cannot copy a new fighter kind (the game refuses kinds past its own); swallowing the clone gives no
  ability. This is the game's behaviour, not changed by the tool.

**Portraits**: by default the clone gets every portrait the base has in your UI (`chr_00`, `chr_10`, `chr_11`,
`chr_12`, `chr_13`, `chr_40`, `chr_70`, `chr_90`, `chrn_11`, `chrn_12`, `chrn_40`, `chrn_41`, `stock_90`), renamed and
with **new texture ids** (the game shows a texture id once). To use your own art, pick the set and the costume number
and **Import PNG...**: the picture is resized to that set's size and encoded in its format (the base's file, or
another character's file of that set when the base has none). One-file sets (`chr_10`, `chrn_*`) use costume 01.

**Character select preview**: the select screen drawn from your files with every clone and the planned one
(highlighted): your portraits, and your UI's layout when it has `lumen/chara/chara.lm` (see "Custom UIs").
The line under it says the clone's slot ("slot 30 of 62") and any layout problem.

### Stages tab

Click a **base stage**, then:

| field | what |
|---|---|
| Folder name | `stage/melee/<Name>/`, `stage/end/<Name>/` (the Omega form), the icons `stage_10_<Name>.nut` ...; a capital, letters / digits / `_` |
| Title | `MmelStageN_<Name>` (the shown name) |
| Series line | `MmelStageG_<Name>` (empty: the base's) |
| Stage select page | 1, or 2 (the DLC page). Page 1 has 48 slots and 47 stages: room for one clone; more go on page 2 |
| Cosmetic id | filled in: the next free stage-select id (from 0x38) |

**Stage icons**: the base's (`stage_00`, `stage_10`, `stage_11`, `stage_12`, `stage_30` ..., page 2's
`append/stage/stage_13`) with new texture ids, or **Import PNG...** per set. The song list (My Music) is the base's.

**Stage select preview**: pages 1 and 2 in stage-select order with the icons you have, the clone highlighted.

### Plan, Check, Build

- **Add to plan** queues the clone (several fighters and stages build together); what is in the form is included too.
- **Check** validates everything (names, ids, kinds, labels, the executable) and lists the files it will write and the
  executable patches. Nothing is written.
- **Build** writes the package (log below), then checks it: new texture ids unique against your UI, portraits
  decodable, the executable re-read.
- **Open output** opens the output folder.

## The package and how to install it

The output folder holds:

```
INSTALL_TO_data/     every file the project's clones add or change, laid out like data/
INSTALL_TO_code/     cross_f.rpx (when an executable was given)
README.txt           what is in it and how to install it
sm4shclonetool_project.json   the project (keep it to add more clones later)
```

1. Copy the contents of `INSTALL_TO_data/` over your data folder (or add them to your mod with Sm4shExplorer). In
   Sm4shExplorer, set every packaged folder that gets a new file (`ui/replace/chr/chr_*`, `ui/replace/stage/stage_*`)
   to **Pack this folder** before rebuilding the patch, or the game reads past the pack and crashes on the select
   screen.
2. Replace `code/cross_f.rpx` with `INSTALL_TO_code/cross_f.rpx`. Keep a copy of the old one.

The package is **cumulative**: each build of a project holds all of its clones and only files that differ from your
data folder, so it installs over your current install whether or not you installed an earlier one. To add another
clone later, use the same output folder and give the tool your **current** (patched) cross_f.rpx: it adds the new
clone to the ones already there.

## The executable

- **What is patched** (only what new slots need; nothing else of the game changes):
  - fighter kinds: the per-kind tables (names, sizes, sound classes), the six fighter-kind switches, the per-kind arrays
    of the parameter manager (moved to a larger copy), the kind-count bounds (random pick, sound banks, AI files,
    resource holders), the character-name table, the save's per-character records for the new ids, the victory
    fanfare / KO voice name tables; each clone gets its base's native code (specials, articles) and its own descriptor;
  - the base's effect banks load with the clone (its articles' effects use the base's ids);
  - own articles: new weapon kinds (tables, switches, descriptors, the clone's article list);
  - custom moves: the clone's id owns its base's moves;
  - stages: the stage-kind table (new kinds 0x80 + 2i / 0x81 + 2i), the stage-select names, the page-2 checks.
- All of it lives in the free code space after the game's code (`0x04B78000`-`0x04BB8000`, inside the game's own code
  region), plus the words it hooks in place.
- **How the tool knows your executable**: before patching it checks every word it will hook against the game's
  original (several hundred words: switch bounds, table readers, counts, call sites) and that the code space after
  the game's code is free. That is "vanilla" for the tool. Its SHA-1 is shown too (the research was done on
  `3b7e1b3f421f330e259a3200d391f47ee6b5931a`).
- **The marker**: a patched executable carries a block at `0x04B78000` starting `Sm4shCloneTool` with the list of
  clones and the original of every word the tool changed. Given that executable again, the tool puts the originals
  back in memory, adds the new clones to the list and patches from scratch: cloning again **adds** to the clones and
  never stacks patches; patching with the same clones twice gives the same file. Old clones keep their kinds and ids.
- **Another mod's executable**: if one of the words the tool hooks was changed by another mod, the tool refuses (the
  two patches would collide). If only the code space after the game's code is in use, **Patch anyway** puts the
  clone code after that mod's code (and grows the code region): use it only if you know that mod.

## What a clone owns, and what it shares

A fully independent clone owns: its fighter kind and character id; every database row (fighter / AI / amiibo /
Classic / crowd cheer params, character, layout, custom-move, announcer rows); its names; its portraits, stock icon
and name plates (new texture ids); its whole fighter folder (model, motions incl. its victory poses, ACMD, MSC,
AI scripts, sounds, effects, cameras) under its own name; its own sound banks and rows, effect bank and articles
(above); its victory fanfare and KO-voice records; its results-screen loser panel (`param/ui/result_param.bin`,
keyed by its name); its own random-select bit.

Name plates (`chrn_11`, `chrn_12`, `chrn_40`, `chrn_41`: the name drawn as a picture) are redrawn with the clone's
title: white capitals with a dark edge on a clear background, in each plate's size and format. That is not the game's
plate lettering; import your own PNG per plate set for an exact look. The name text itself (`MmelChara*`) goes into
the one `melee.msbt` your data has (one language per install: run the tool on each region's file for others).

Shared with the base, because that is how a Smash 4 clone works:
- **the base's native code**: special moves, status logic, articles' behaviour, anything the game does for that
  kind in code. The clone's files decide what it looks and sounds like and its ACMD / MSC / params, but its moveset
  structure is the base's. The base's per-fighter state lives in each fighter, so a clone and its base in one match
  behave like two copies of the base (the game shares the kind's static specializer object between every fighter of
  a kind already); the clone has its own parameter slot (its vl file) and article kinds;
- the announcer call on the character select and the results (the clone's 16 call ids are the base's), the
  victory fanfare's and the results screen's music track (its own records point at the base's tracks);
- its Final Smash cutscene assets that the game finds by kind instead of by folder (its `camera/final/` and
  `effect/Fin<Cap>/` folders are copied and renamed, but whether the game loads them for a new kind was not traced),
  and a transformation (a clone of Bowser, Wario, Little Mac or Lucario transforms into the base's transformation);
- sound ids inside MSC scripts (only ACMD ids are moved to its own banks);
- the custom moves' unlock bits (the clone owns what its base owns: the save has no room for new characters);
- Kirby: Kirby can't copy a new kind (the game refuses kinds past its own); swallowing the clone gives no ability.

## Character select placement

The character select lists the characters by their **first sort key** (`ui_character_db.bin`), the DLC characters
after the others, and places them on the layout's faces in that order: the layout file `lumen/chara/chara.lm` has an
arrangement for each count (`num_058`, `num_059`, ...) and the game shows the one for your count. A clone added
"after Fox" gets Fox's key + 1 and every later character's key moves up by one (only that key: the other two sort
keys order other menus and put the clone last). Without "after", the clone goes after every other non-DLC character.

## Game modes

| mode | with clones |
|---|---|
| Smash, Special Smash, Training | selectable on the character select, random included |
| Classic | its row in `simple_character_db_cafe.bin`; its save records (per character, in memory only) |
| amiibo | its learning row (`fighter_ai_nfp_learning_param.bin`) |
| CPU AI | its AI params row and its own AI files |
| All-Star, Stadium, Smash Tour, Events, Trophy Rush, online, replays | **not checked**: these modes were not traced with new kinds. Test them in Cemu before relying on them; please report any crash with the mode and what you selected |

## Custom UIs

Point **Custom UI folder** at your UI (the folder with `message/`, `replace/`, `lumen/`). The tool then:

- copies the base's portraits **from your UI** (a vanilla portrait in a modded select looks out of place), and checks
  texture ids against all of your UI's textures;
- draws the preview with your portraits and, if you have one, your `lumen/chara/chara.lm`: for the new count it reads
  that arrangement's face places. If your layout has no arrangement for the new count, or two faces share a place
  (some custom layouts are only clean up to their own count), the preview and the log say so: add or fix that
  arrangement in your layout before installing (the tool does not rewrite your layout).
- A UI with different files can say so in `sm4shclonetool_ui.json` in the UI folder:

```json
{"css_layout": "lumen/chara/chara.lm", "grid_icon": ["chr_10", "chr_00"], "icon_size": [116, 116],
 "stage_icon": ["stage_10"]}
```

Without a `chara.lm` the preview approximates the grid (the game's own layout file isn't shipped with the tool).

## Command line

```
python cli.py info   --exe cross_f.rpx
python cli.py roster --data DATA [--exe EXE]
python cli.py check  --data DATA --out OUT --exe EXE --fighter fox:wolf:title=Wolf,after=Falco,weapons=blaster+illusion
python cli.py build  --data DATA --out OUT --exe EXE --fighter fox:wolf:title=Wolf --portrait wolf:chr_00:01=wolf1.png
python cli.py build  --data DATA --out OUT --exe EXE --stage BattleField_f:Skyworld:title=Skyworld,page=2
python cli.py css    --data DATA --out OUT [--ui UI] --fighter fox:wolf --png preview.png
```

`python cli.py --help` lists every key.

## Limits

The window shows the current counts and limits under the plan ("Fighter clones: 3 of 37 ...").

| limit | how many | why |
|---|---|---|
| fighter clones on the character select | **37** with the game's layout; more with a layout that has more places | the select shows arrangement `num_<count>` of `lumen/chara/chara.lm` and binds `face_001` ... in order; the game's file has arrangements up to `num_096` (96 entries: 59 are the game's). A UI whose `chara.lm` has more arrangements and faces raises it: the tool reads its highest `num_NNN` |
| fighter clones in all | **141** | character ids up to 199 are found by their place in the character database (59-199 are free); kinds 0x41-0xCD fit the kind tables (the tool sizes them to the clones) |
| clones the character select's random pick can choose | **every clone** (up to the 141) | the game's 96-bit pool is replaced by one of 224 bits in the tool's space (refill, count, remove and pick replaced); any clone can be left out with "In the random select" off |
| own articles (weapon kinds) | grows with them (0x185 on) | the weapon tables are sized to the articles |
| stage clones | **41**: 1 on page 1, 40 on page 2 | the stage select has 48 slots a page (`img_01`-`img_48`) and 2 pages; the game has 47 + 8 stages. More pages are not supported |
| stage clones in random stage select | **every stage clone** (the 41) | the random stage pools cover ids below 0x63, which every stage clone has (0x38-0x60); any can be left out with "In the random stage select" off |
| stage-select ids | 0x38-0xC7 | ids up to 0xC7 are found by position |
| code space | grows with the clones (about 6 KB a fighter, more with articles) | from `0x04B78000`; past `0x04BB8000` the executable's code region is enlarged (as other code mods do; tested on Cemu by such mods, not on a console) |
| effect banks in one match | 8 | the game's bank slot table; a clone whose base isn't in the match uses two. A per-match limit, not a clone count |

## What is not confirmed in game

- **Tested by emulating the patched code** (the game's own functions run on the patched executable), not yet in a
  game: please report what you see. The tool was built without an untouched v288 executable at hand: the patch was
  tested on a stand-in rebuilt from a modded one (every word the tool touches restored to the game's original), so
  the first run on a real vanilla executable is the first true one. If the tool says your vanilla executable is not
  vanilla, please report its SHA-1.
- Many clones: 40 fighter and 8 stage clones were built and emulated; the enlarged code region (to about 0x04BD1000,
  356 KB, for 40 fighters and 8 stages), high kinds' resource ids (`kind * 0x11 + n`, map keys) and a select screen with 99 entries were not
  seen in a game.
- A clone shares its base's **native code**: special moves, articles and anything the game does for that kind
  in code. What is in its files (model, motions, ACMD, MSC, params, effects, sounds) is its own to change.
- **Sounds**: the clone's sound banks are the base's files renamed; they keep the base's bank ids, so with the base
  and the clone in one match their banks may answer for each other (not tested). A bank of its own needs the
  soundlabeltable edited (not in this version).
- The announcer calls the clone with the base's call. Kirby can't copy clones.
- **Records / Classic mode**: the new characters' records live in memory only (the save file has no room for them).
- **Stages**: a clone is the base's folder renamed; the game builds it as a generic stage (its own models, collision
  and parameters). Stages whose behaviour is native code (moving platforms, hazards) may not move (not tested).
- Mii Fighters, transformations and Mii enemies are not offered as bases.
- The character-select preview approximates the game's layout when your UI folder has no `chara.lm`, and the
  stage-select grid; ties between equal sort keys are drawn in id order (the game's order for ties is not known).
