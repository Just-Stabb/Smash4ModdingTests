## RAM structures

Status: **static analysis of `cross_f.rpx` only, nothing patched or tested in game.** Scope: every
per-fighter-kind array in RAM, every instruction that addresses one, and what a "grow to N kinds"
patch has to change there. Kind switches, `.rodata` / `.data` per-kind tables and kind bounds are in
"Code and tables".

Tool: `tools/kind_ram_scan.py` (about 10 s). It follows the object pointers through a data-flow pass
over `.text` and prints every access with the array, the kind and a class (method in its docstring):

| option | prints |
|---|---|
| (none) / `-S MGR\|EQ\|AI` | every per-kind access: address, function, instruction, array, class, kind or stride; `*imm` = the instruction's own 16-bit immediate holds the array offset (the word to patch when the array moves) |
| `--summary`, `--csv FILE`, `--all` | counts; CSV; also the fields that are not per kind |
| `--missed` | completeness check (below) |
| `--loops` | every loop in `.text` that runs 0x41 / 0x42 times and what it walks |
| `--plan N` | the word patches of the recommended plan for N kinds, as `rpx_patch.py` arguments (**untested**) |

Classes: **const** = the kind is built into the displacement (`lwz r12, 0x113C(r12)` = Kirby's vl
params); **indexed** = `slwi rX, kind, 2` / `mulli` added at run time; **walk** = a loop stepping
through the array; **addr** = `addi rX, mgr, 0x111C` (the uses follow); **arg** / **escape** = a
pointer into the array passed to a call / stored to memory.

### Summary

| structure | per-kind data | accesses | recommended | patches | confidence |
|---|---|---|---|---|---|
| FighterParamManager `[0x102FF448]` | 9 arrays of `[0x41]`, `+0x111C`-`+0x2364` | 1344 instructions in 853 functions (1226 carry the offset in their immediate) | relocate the block to the end of a bigger allocation; keep the old `vl` array as a mirror for kinds `0x00`-`0x40` | 165 immediates + 2 sizes + 3 loop counts + 2 small hooks | high (inventory), medium (plan untested) |
| equipment-ability object `[0x10353FC0]` | `[0x41]` at its end (`+0x320`) | 402, all in the vl param load / unload cases | grow in place | 2 immediates | high |
| AI object `[[0x102FAD78]+0x794]` | 8 records x 2 `[0x41]` at their ends | 54 instructions in 4 functions + 2 stack buffers | cap: ignore kinds `>= 0x41` | 2 small caves | high |
| anything else | none found | - | - | - | medium (heuristic search) |

**Nothing here makes more kinds infeasible.** The FighterParamManager is the only big job, and the
inventory makes it mechanical: all its words come out of `--plan`. The hard limits are soft:
- the relocated manager block must end below `+0x8000` (16-bit displacements), so N <= `0x13F`;
- the AI "shadow" variant (below) would allow N <= `0x91`.

### FighterParamManager `[0x102FF448]`

Allocated with a fixed size, `li r3, 0x25B0`, at `0x02E4E684` (singleton set-up `0x02E4E654`) and
`0x02EA5860` (the constructor's own allocate-if-null). Constructor `0x02EA5848`, loader `0x02EA5BC0`,
destructor `0x02EA5AC8`.

| offset | size | what | per kind |
|---|---|---|---|
| `+0x0000` | `0x38` | `fighter_param.bin` vector (count `+8`, data `+0xC`, entries `0x588`) | no: sized by the file |
| `+0x0038` | `0xD68` | `fighter_param_common` | no |
| `+0x0DA0` | `0x2B8` | `fighter_param_etc` | no |
| `+0x1058` | `0xC4` | `fighter_param_power_up` | no |
| `+0x111C` | `[0x41] x 4` | **vl**: the kind's parsed `fighter_param_vl` struct (vl load `0x02EA6BC4`) | yes |
| `+0x1220` | `[0x41] x 4` | **refcnt**: vl load reference count | yes |
| `+0x1324` | `[0x41] x 4` | **x1324**: data of a kind-specific vl vector; set by the vl load tail `0x02EA8D50` for kinds 8, `0x17`, `0x18`, `0x1C`, `0x21`, `0x23`, `0x26` | yes |
| `+0x1428` | `[0x41] x 4` | **x1428**: only ever cleared (read by `0x02F1C31C`) | yes |
| `+0x152C` | `[0x41] x 4` | **x152C**: as x1324, for kinds 5, 6, `0x19`, `0x20`, `0x35` | yes |
| `+0x1630` | `[0x41] x 4` | **fpidx**: index of the kind's `fighter_param.bin` entry (loader loop `0x02EA5CBC`) | yes |
| `+0x1734` | `[0x41] x 4` | **vl50**: `vl + 0x50` (hurtbox vector) | yes |
| `+0x1838` | `[0x41] x 0x24` | **att**: 3 x {data, count, id 10000 / 11000 / 12000} from vl groups 9 / 10 | yes |
| `+0x215C` | `[0x41] x 8` | **attp**: {`&att[k]`, 3} | yes |
| `+0x2364` | `0x42 x 8` | common effect table (`effect_Xlu` ... `effect_ColorNormal`, names `0x10353EB8`; init `0x02EA5B7C`; `&table` is stored at fighter `+0x1C4`) | **no** |
| `+0x2574` | 4 | equipment-ability object pointer | no |
| `+0x2578`, `+0x2594` | `0x1C` each | containers for WorkModule categories 2 / 9 | no |

The per-kind block is contiguous, so a 66th kind writes into the next array: `vl[0x41]` is
`refcnt[0]`.

**Accesses** (instructions; `--summary`):

| array | const | indexed | walk | addr | arg / escape | carry the offset (`*imm`) |
|---|---|---|---|---|---|---|
| vl | 993 | 99 | - | 67 | - | 1093 |
| refcnt | - | 20 | 1 | 2 | - | 2 |
| x1324 / x1428 / x152C | 12 | 6 | 6 | 3 | 1 | 21 |
| fpidx | 5 | 19 | 1 | - | - | 25 |
| vl50 | - | 76 | - | 3 | - | 78 |
| att / attp | - | 13 | 18 | 9 | 4 | 7 |

- 993 vl reads and writes have the kind built in. 928 of them are reads outside the manager, in 799
  functions (fighter specializers, weapons, AI, sound): each reads its own kind's vl params, e.g.
  Kirby's `[mgr+0x113C]`. 65 are the vl load's own per-case stores.
- Variable-kind code is inlined, not funnelled through accessors. Besides the manager's own
  functions (`0x02EA5848`-`0x02EA9198`) and the generic word-fill helper `0x04AE0B14`, 45
  functions compute `mgr + 0x111C + 4*kind`-style addresses (63 instructions), e.g.:
  - the fighter set-up `0x02E13048` / `0x02E53E98`;
  - the WorkModule special loader `0x02F1BF88`;
  - the camera `0x02E4F7E8`;
  - the AI `0x02DFD060`.

  The accessor functions `0x02F1C2E4` / `0x02F1C300` / `0x02F1C31C` / `0x02F1C338` are 4 of them.
- Loops over 0x41: `0x02EA5C9C` (clear refcnt), `0x02EA5CBC` (kind -> `fighter_param` entry map),
  `0x02EA6B8C` (unload all).
- Pointers leave the block only internally (`&att[k]` into attp at `0x02EA8DB0`). The manager
  pointer itself is stored only into its global. No pointer into the block is passed to an indirect
  call.

**Completeness:**
- All 989 references to `0x102FF448` resolve to a pointer load the scan follows.
- The scan finds every site of an older, independent linear pass (the one behind
  `docs/params/fighter_param.md`, 937 sites).
- `--missed` lists every D-form access with a displacement in `0x111C`-`0x25B0` whose base the scan
  did not resolve, in the 904 functions that touch the manager. 28 are left, and all were checked to
  be other objects: the player-slot singleton, AI fighter objects, kinds stored at `+0x146C` of
  another object, constants.
- What it can't see: a manager pointer reaching code through memory or an indirect call. None was
  found.

**Strategies** (counts from the scan; "immediate" = rewrite the 16-bit field of one instruction):

| | what moves | patches | verdict |
|---|---|---|---|
| (a) grow in place | every array after vl, and the effect table and three fields after them | 545 immediates (133 per-kind, and 406 reads of `mgr+0x2574`, most of them in the vl load / unload cases) + sizes + loops | no: the arrays aren't the end of the object |
| (b) relocate the whole block to a new region `+0x25B0`..., patch every access | all per-kind arrays | 1226 immediates (993 of them kind-built-in vl) + sizes + loops | works, but every missed site breaks a vanilla fighter |
| (c) split: kinds `0x00`-`0x40` stay, an extension block for `>= 0x41` behind accessor hooks | nothing for old kinds | about 165 hooks (one `kind < 0x41 ?` cave per variable-kind site) | no: there are no few accessors to hook |
| **(d) relocate + mirror** | the block moves to the end of a bigger allocation; the old vl array stays as a mirror for kinds `0x00`-`0x40` | **165 immediates** (97 in the manager's functions; 68 in 50 others: the 63 above and the 5 kind-built-in fpidx reads) + 2 sizes + 3 loop counts + 2 hooks | **recommended** |

How (d) works:
- **Every variable-kind access gets the new array's offset.** These are the indexed, walk and addr
  sites, the unload store and the default case `0x02EA6DB8`.
- **The kind-built-in vl reads (928) are left alone.** They only exist for vanilla kinds, and the old
  vl array still holds their values.
- **The vanilla vl-load cases keep writing the old array** (65 stores, 65 read-backs). One hook at
  the common tail `0x02EA8D50` copies `old vl[k]` to `new vl[k]` for `k < 0x41`. One hook at the
  unload store `0x02EA6AF8` clears both.
- **The other old arrays become dead.** Their 5 kind-built-in fpidx reads and 12 x1324 / x152C tail
  stores are patched to the new arrays.
- **Safe when the scan misses a site.** A missed variable-kind access still reads correct values for
  vanilla kinds; only a new kind would be wrong there.

New layout from `--plan 0x60`:

| | |
|---|---|
| vl | `0x25B0` |
| refcnt | `0x2730` |
| x1324 | `0x28B0` |
| x1428 | `0x2A30` |
| x152C | `0x2BB0` |
| fpidx | `0x2D30` |
| vl50 | `0x2EB0` |
| att | `0x3030` |
| attp | `0x3DB0` |
| allocation | `0x40B0` (`0x25B0 + N*0x48`) |

**Still needed for a new kind, outside this section:** its vl load / unload cases (they write
`new vl[k]` and `[mgr+0x2574]+0x320+4k`), the `0x40` switch bounds, and a `fighter_param.bin`
entry (the vector is sized by the file; fpidx maps kind -> entry).

**Risks:**
- the word list is generated, so a wrong classification is a wrong word. Two cases needed care and
  are handled:
  - a loop base `addi rX, mgr, start - 4`, which looks like the previous array's last element
    (`0x02EA5CA0` is refcnt's loop base; `0x02EA5B88` is the effect table's and is not patched);
  - the vl-load cases.
- the hooks are not written.
- untested in game.

### Equipment-ability object `[0x10353FC0]` (= `[mgr+0x2574]`)

- `0x424` bytes. Allocated at `0x02EA5964` and cleared at `0x02EA5978`, both with `0x424`.
- `+0x0`-`+0x320`: `fighter_param_equipment_ability` (binder `0x02E901E4`).
- `+0x320`: `[0x41]` owning pointers to each kind's parsed vl struct.
- Its 402 accesses are all kind-built-in, in the vl load / unload cases (`0x02EA6BC4` / `0x02EA5D64`).
- **The array ends the object, so grow in place:** set both `0x424` to `0x320 + 4N` (`--plan`
  prints the two words). The vanilla cases are untouched; new kinds' cases use `+0x320+4k`.

### AI object `[[0x102FAD78]+0x794]`

- `0x26D0` bytes. Allocated at `0x02758574` (constructor `0x0275855C`, from the AI manager set-up
  `0x02DF7F6C`):
  - `+0x10`: 8 x `0x50`;
  - `+0x290`: 8 per-player records of `0x488`, built by the array constructor `0x02003E30` with the
    element constructor `0x027586EC`.
- **Each record ends with two `[0x41]` word arrays**, `+0x280` and `+0x384`. They hold amiibo (nfp)
  learning counts per fighter kind:
  - incremented in `0x0274FE18` (`0x02751B04`-`0x02751B38`, index `[event+0x134]`);
  - read by `0x0275233C`, which loops j = 0..0x40 and calls `0x02DFD4E8(j)` = entry j of
    `fighter_ai_nfp_learning_param.bin` (AI manager `+0x1D4`, `0xA4`-byte entries whose word 0 is j).
- The scan finds 54 instructions in 4 functions (20 carry the offset in their immediate):
  - init `0x0274E8D0`;
  - record constructor `0x027586EC` (reached only through a function pointer: seeded explicitly);
  - the increments;
  - `0x0275233C`, with 14 `li 0x41` loops.
- **`0x0275233C` also keeps two per-kind stack buffers**: `r1+0x2FC` (`0x41` words) and `r1+0x400`
  (`0x41 x 0x10`). The register save area follows at `r1+0x810` (frame `0x978`), so more kinds means
  re-laying out that frame: about 90 `r1` offsets.
- The AI manager's own arrays (`+0x748`, `+0x768`) are per player (8), not per kind.

Strategies:
- **(a) grow the records.** The stride `0x488` is in about 60 `mulli` / `addi` in
  `0x0274F4BC`-`0x02758700`, plus the record allocation `0x02758700`, the array constructor's
  argument `0x027585AC`, 18 loop counts and the stack frame. No.
- **(b) shadow.** Allocate `0x26D0 + 0x2440`, keep the stride, and move both arrays of record i to
  `rec + 0x2440` (the same place in a second 8 x `0x488` block). That is 20 immediates, 18 loop
  counts, the size, and the `0x0275233C` frame. N <= `0x91`.
- **(c) cap: recommended.** Guard the two increments (before `0x02751B04` and `0x02751B28`) with
  `kind < 0x41`. That is 2 small caves. Amiibo just don't learn from fights against the new kinds.
  Without the guard, kind `0x41` increments the other array's slot 0, and kinds above it run into
  the next player's record.

### Other per-kind RAM: none found

What was searched:
- **every loop in `.text` that runs 0x41 / 0x42 times** (30, `--loops`). The ones not covered
  above aren't kinds:
  - `0x0226EA08`: 0x41 UTF-16 characters;
  - `0x028BC3FC`: animation names;
  - `0x02A61F40`, `0x0311704C`: BGM request blocks;
  - `0x033F79EC`: a `0x101`-byte buffer;
  - `0x0343008C`, `0x03B35F84`: library code.
- **`k <= 0x40` loops**: only in library code.
- **a `cmplwi rK, 0x40 / 0x41` followed by `slwi` / `mulli` of rK**: kind switches, static tables,
  and per-slot arrays of other sizes.
- **the kind getters' results used as indices**: only resource ids `kind*9 + 4..6` (`0x030C2048`,
  `0x030C2260`, `0x030C2278`), kept in a map.
- **the fighter resource holder `[0x102F9028]`**: its arrays are per player (8). The Mii-enemy
  holders are fixed fields.
- **loops over character-id counts (0x37-0x3C)**: struct copies only.

Not RAM arrays, but needed per kind:
- the static specializers and descriptors (descriptor `+0x1C` is filled at run time and must start
  at 0);
- the ACMD manager's 16 slots, which are keyed by kind, not indexed;
- file-sized vectors that need an entry per kind: `fighter_param.bin`,
  `fighter_ai_fighter_param.bin`, and `fighter_ai_nfp_learning_param.bin`. That last one is
  indexed by kind: entry k must be kind k.

Open:
- save data keyed by character id (records, Classic clears). No per-character array was found with
  these methods, but it wasn't traced from the save code.
- whether resource ids `kind*9 + n` collide with other ids for kinds `>= 0x41`.
- arrays that are only zero-initialised by a `memset` and indexed inline without a bound check or a
  0x41 loop would escape these heuristics.
