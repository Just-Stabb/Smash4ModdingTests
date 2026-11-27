# Smash Run trace (Azahar)

This records what Smash for 3DS really does in Smash Run while you play it in Azahar: every enemy's states and how
long each lasts, its speed, its hitboxes (damage, angle, knockback, size, bone, when they turn on / off), its effects
and sounds, its AI checks and the random rolls behind its choices, its params, plus the spawns, the doors, the
treasure chests and items, the stat boosts and the stage hazards. Each session gives one log file (`.jsonl`). Send
the logs back, and the Wii U port gets the 3DS's exact numbers.

It only reads the game. The one thing it writes is its breakpoints, and it removes every one of them when it stops
(Ctrl+C included). The emulator stays as it was.

What you need: Azahar, Smash for 3DS **with its latest update installed** (the update whose code the port was read
from), and Python 3 on your PC. Nothing else: no gdb, no extra Python packages.

## 1. Install Python (Windows)

1. Download Python 3 from <https://www.python.org/downloads/> (any 3.8 or newer).
2. Run the installer. **Tick "Add python.exe to PATH"** at the bottom of the first page, then "Install Now".
3. Check it: open a Command Prompt (Start, type `cmd`, Enter) and type `python --version`. It should print
   `Python 3.x.x`. If Windows opens the Microsoft Store instead, run the installer again with the PATH box ticked
   (or use `py` instead of `python` in the commands below).

## 2. Turn on Azahar's GDB stub

Azahar comes from Citra, and in Citra the setting was under **Emulation > Configure... > Debug**: a box called
**"Enable GDB Stub"** with a **port** next to it (24689 by default). Azahar's menus may be named a little
differently. Look in the configuration window for a **Debug** tab (sometimes under "Advanced") and a "GDB" box with a
port number.

- Tick it, keep the port at 24689 (or note the one you choose), press OK.
- Restart Azahar if it asks.
- Start Smash for 3DS. With the stub on, Azahar may wait for a debugger before the game runs. Azahar may freeze
  on a black screen until the tracer connects. That is normal: the tracer lets it run.
- Windows Firewall may ask about Azahar opening a port. "Private networks" is enough; the tracer connects from
  the same PC.

If you can't find a GDB option at all, your Azahar build doesn't have one: tell me which version you have.

## 3. Get the toolkit

Unzip `smashrun_trace_v1.zip` anywhere, e.g. `C:\smashrun_trace`. It contains `trace.py`, `analyse.py`,
`run_trace.bat`, this README and the `srtrace` folder (the hook list and the enemy maps: names and offsets only, no
game files).

## 4. Check the connection (do this first)

1. Start Azahar with the stub on, load Smash for 3DS and go to the main menu.
2. In a Command Prompt:

   ```
   cd C:\smashrun_trace
   python trace.py probe
   ```

   It connects, finds the game's code modules in RAM, prints them, says which enemy map matches, counts the hooks
   it could place, then lets the game run again and disconnects. It changes nothing. Any game version works for
   the probe.
   - **How long:** a few seconds normally (well under a minute). The game pauses while the probe reads and runs
     again at the end. The console shows each step with its packet count and time (`[probe] latency: 21 packets,
     0.4 s ...`). The first probe on a PC may have to search the RAM: it then prints `scan: ... % ... at most
     about N s left` lines. Let it finish (Ctrl+C still stops it cleanly and prints what it found so far).
   - **The second probe and every run after it are much faster:** what the probe found is kept in
     `smashrun_trace_cache.json` next to the logs (where the modules are, checked against their fingerprint each
     time). Delete that file if anything looks wrong. It is rebuilt.
   - `enemy_fs` only appears once you are **in Smash Run** (the mode loads it). Run the probe again from inside a
     Smash Run match: the line `map: update` (or `map: base`) must appear. `map: none` means your game version
     doesn't match the maps. Send me the probe's output.
   - If it says it cannot connect, check the port and that Azahar's stub is on (step 2).
3. Copy what the probe prints (from `==== probe summary` to `====`) and send it with your first logs. It contains
   the stub's speed (`stub latency: ... ms a packet halted, ... ms running`), the modules, the map and the cost of
   each step.
4. **Still slow, or the game stutters for more than a minute?** Press Ctrl+C, then run the probe again with a packet
   log and send me that file:

   ```
   python trace.py probe --rsp-log probe_log.txt
   ```

## 5. Record

Double-click `run_trace.bat`, or in a Command Prompt:

```
python trace.py run
```

It connects, waits for Smash Run, and logs until you press **Ctrl+C** in its window (then it removes its
breakpoints and lets the game run on). Each run writes `smashrun_trace_YYYYMMDD_HHMMSS.jsonl` in the folder.

The game runs slower while tracing, because every logged event stops the emulator for a moment. That is expected.
Slow motion doesn't change the frame counts: they come from the game's own frames.

Useful options (add them after `run`):

| option | what it does |
|---|---|
| `--kinds kuribo,heiho` | only these enemies (their names are in the checklist below). Much faster: use it for the per-enemy checklists |
| `--mode full` | also logs every frame of every state and the AI's checks. Gives exact speeds and AI decisions, but runs very slowly. Use it with `--kinds` and one enemy at a time |
| `--cats spawn,leave,door,chest,item,stat` | only these kinds of events (categories: state, attack, effect, sound, rng, ai, spawn, leave, damage, item, chest, door, stat, hazard, stage, result, param, motion, kinetic, facing) |
| `--duration 600` | stop by itself after 600 seconds |
| `--max-mb 300` | stop when the log reaches 300 MB (default 500) |
| `--port 24690` | if you changed the stub's port |
| `--out goomba1.jsonl` | name the log yourself |

One-shot dumps (run them while in a Smash Run match, standing still):

```
python trace.py dump params      every enemy kind's params as the game holds them in RAM
python trace.py dump objects     the stage's objects (doors, chests, hazards ...) found in RAM
python trace.py dump all         both, plus the game's managers (spawner, items, Smash Run manager)
```

`run` also makes a stage dump by itself about 2 seconds after each Smash Run stage loads.

If the clock line in the console says `no frame clock hook`, or the frame numbers in the logs look wrong, run
`python trace.py calibrate-clock` for 20 seconds next to an enemy and send me what it prints.

## 6. What to do in game

Smash Run is 5 minutes, so plan one or two items of the list per run. Use `--kinds` for the enemy items: it keeps
the game fast. Between runs, close the tracer with Ctrl+C. One log per item is ideal; name them with `--out`.

### Enemies (one enemy at a time: `python trace.py run --kinds NAME --out NAME_1.jsonl`)

For each enemy you meet:
1. **Leave it alone** for 20-30 seconds: let it walk, turn at walls and ledges, idle, fly its path. Keep some
   distance at first, then come close so it notices you.
2. **Let it attack you** a few times: stand in front of it, let it charge / shoot / swoop. Shield some of them.
3. **Stomp it** (jump on it), if it can be stomped. Do it twice.
4. **Hit it** with a weak attack (jab) a few times without killing it: its flinch and recovery.
5. **Kill it** with a strong attack (a smash): its death flight.
6. For the most detailed record, do the same once with `--mode full` added (it is slow: one enemy, 1-2 minutes).

The enemy names the tracer uses (the 3DS's internal names): kuribo (Goomba), dekakuribo (Big Goomba), patapata
(Koopa Paratroopa / Koopa Troopa), togezo (Spiny), heiho (Shy Guy), propellerheiho (Fly Guy), waddledee (Waddle Dee),
waddledoo (Waddle Doo), churine (Churine), zima (Zoomer), plasmawisp (Plasma Wisp), darios (Darios), stalfos
(Stalfos), whitebear (White Bear), gordo (Gordo), ghos (Ghos), tikibuzz (Tiki Buzz), furiijio (Furiijio), pooka
(Pooka); the other 3DS names are the files in `docs/smash-run-enemies/` of the repo (e.g. octorock, mettaur,
redead, killer). Not sure of a name? Leave out
`--kinds`: every enemy is traced, just slower.

### Spawns and leave timings (`--cats spawn,leave,state,stage --out spawns_1.jsonl`)

- **Walk through each area for 2-3 minutes without fighting.** Let enemies appear and go away on their own. Go
  far from some of them and come back.
- Once, stand still in one room for a full minute.
- Write down roughly which areas you went through (or take a short video): the log has the frames, your notes say
  where you were.

### Doors (`--cats door,stage,chest --out doors_1.jsonl`)

- **Visit every door you find**: walk past it, go through it, come back. Rooms with a challenge or a treasure room
  too. After the run, `python trace.py dump objects` in the next Smash Run match adds the door objects from RAM.

### Treasure chests and items (`--cats chest,item,rng,stat,effect,sound --out chests_1.jsonl`)

- **Open every chest you find**, and note the area (or say "first chest in the cave" etc.). Open them with
  different attacks if you can.
- **Defeat enemies and let their drops sit until they vanish** (don't pick them up): that times how long a drop
  stays. Then defeat a few more and pick up everything.
- Gold, power-ups and equipment / custom parts all count: pick them up normally.

### Stat boosts and power-ups (`--cats stat,item,effect,sound --out stats_1.jsonl`)

- **Collect boosts of each stat** (speed, jump, attack, special, arms, defense) and take a photo / screenshot of
  your totals screen at the end, so the numbers in the log can be matched with what the game shows.
- **Use each power-up you have once** (the powers you equip before the run: healing, bombs, etc.).
- If you can, play the final battle until the results screen: the results go in the log too.

### Stage hazards (`--cats hazard,effect,sound,stage --out hazards_1.jsonl`)

- **Stand near each hazard for a few full cycles** (spikes going in and out, flames, crushers, moving floors).
  Count roughly how many cycles you watched.
- **Get hit by it once**, and **try to break it** (attack it), if it looks breakable.

### Params

- Once per game session, inside a Smash Run match: `python trace.py dump all --out dump_1.jsonl`.

## 7. What to send back

- Every `.jsonl` log (zip them: they compress very well), with a line each saying what you did in it (the
  checklist item, the areas, anything odd).
- The `probe` output from inside Smash Run (step 4), once.
- `smashrun_trace_cache.json` (next to the logs; it remembers where the modules were).
- Any error the console printed (copy the window's text).
- Videos of the same runs help, if you record them anyway.

## Troubleshooting

- **"connection refused"**: the stub isn't on, or another program is connected to it (only one at a time), or
  the port differs (`--port`).
- **The game froze after `probe` / `dump` and stayed frozen (v1.0.0)**: Azahar pauses the game while the tracer is
  connected and only resumes it when told to continue; v1.0.0 disconnected without saying so. Fixed in v1.0.1 (every
  command now ends with a continue). If a game is stuck like that, run `python trace.py resume` instead of rebooting.
- **Azahar is frozen right after the tracer connects**: wait a few seconds; it reads what it needs with the game
  paused, then lets it run (v1.1.0: a few hundred packets at most; a kind's breakpoints only go in when one of
  that kind first spawns, so the start is quick; `--eager-kinds` puts them all in at once). If it stays frozen, press Ctrl+C in the tracer window (the game resumes), then try
  `--kinds kuribo` to trace less.
- **The probe works but the run never logs any `state` events while enemies are clearly moving**: Azahar's fast
  CPU mode may skip debugger breakpoints. In the same Debug settings, untick **"Enable CPU JIT"** (if there is
  such a box), restart the game and try again. It runs slower without it.
- **The tracer says "the stub has no Z0"**: your stub doesn't take breakpoint packets, so the tracer writes
  breakpoint instructions into the game's code and puts the original bytes back when it stops. Always stop it
  with Ctrl+C (not by closing the window) so it can restore them; if it was killed, restart the game.
- **Azahar was paused / you closed the game**: the tracer waits, and reconnects when the stub comes back. Smash Run's
  code module is found again when you start the next run.
- **The log stopped growing**: the size cap (`--max-mb`) was reached; start a new run.

## How it works (for the port)

- `srtrace/rsp.py`: the GDB Remote Serial Protocol over TCP (packets, acks, escapes, run-length encoding, `qSupported`,
  `g` / `p` / `m`, `Z0` / `z0` with a BKPT fallback, `c` / `s` / `vCont`, stop replies, interrupt, detach). Every
  breakpoint is stepped over on continue (removed, single step, put back).
- `srtrace/locate.py` + `srtrace/cro.py`: finds the CROs in RAM with few packets: the cache first (each module
  checked by the 0x80-byte hash block at its base), else every thread's PC / LR and a bulk read of its stack
  (qXfer:threads + Hg + g) for a pointer into a CRO's code, walked back with bulk reads to its "CRO0" header, then the
  RO service's next / previous chain; only then a bulk scan (one packet per 16 KB, the linear heaps first). The
  stub's latency halted / running is measured and the faster state used. It reads the run-time segment tables, and
  the export tables only when the loaded file isn't the one the catalogue / maps were built from (same hash block). The export tags give each
  name's file offset, which identifies the module version; `srtrace/maps/enemy_fs_<version>.json` is used only when
  every kind's `create` export sits at the map's offset.
- `srtrace/catalog.json`: the framework hooks by mangled name, resolved through the game's own static.crs (code.bin's
  symbol module), so the same list works on any version; `srtrace/abi.py` decodes their arguments from the
  signatures (ARM AAPCS with VFP floats).
- `srtrace/tracer.py`: the breakpoint loop, the per-instance snapshots, the dumps, the log.
- `analyse.py LOG.jsonl ... --out report.md`: per-kind state machines, frame counts, speeds, attacks, effects,
  sounds, AI, RNG, params; spawns, leaves, items, chests, stats, doors, hazards; the diff against
  `reference/smashrun_enemy_specs/` (`--apply-confirmations` writes `azahar_trace` into hand_read.json).
- `tests/`: the RSP client against a mock stub, the CRO mapping on the dump's real modules, the tracer against a fake
  Azahar (Unicorn running the dump's enemy_fs.cro behind a Citra-style stub), the analysis. `dev/build_data.py`
  regenerates the catalogue and maps from the dump. See docs/smash-run-port.md "Azahar trace toolkit".
