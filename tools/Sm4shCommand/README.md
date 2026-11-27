# Sm4shCommand (updated)

Sm4shCommand and the SALT library it builds on, copied from Sammi Husky's repositories and fixed here:

- `SM4SHCommand/` from https://github.com/Sammi-Husky/Sm4sh-Tools (commit `0173bd3`)
- `SALT/` from https://github.com/Sammi-Husky/SALT (commit `9ffff37`; Sm4sh-Tools pins an older
  submodule commit, `4753c93`)

Both are by Sammi Husky; see `SM4SHCommand/LICENSE.txt`, `SM4SHCommand/COPYING.txt` and
`SALT/LICENSE`. Sm4shCommand uses FastColoredTextBox (LGPLv3), included as `FastColoredTextBox.dll`.

**Version:** v1.7.33 (title bar and Help > About). v1.7.33: **Sound Adder** (the Sound Effect Viewer's Add sounds..): audio files (WAV natively; MP3 / OGG / FLAC ... through Windows Media Foundation or ffmpeg on PATH) added to one of the fighter's banks as new tones, resampled to 48 kHz, mono / stereo kept, encoded to DSP-ADPCM IDSP as the vanilla tones are (`tools/dspadpcm` ported to C#: byte for byte dspenc's frames), each with its tone name (the bank's prefix filled in), alias, volume (dB, slider / box), silence trimming, normalising and looping, previewed as the game will play it; listed as new / unsaved rows (preview, alias, filter, Add to Script); ids = the next labels of the bank's row (row << 16 | label), checked against every id in the label table (ports' alias rows included; 65536 labels a row at most: the id's low 16 bits), the costume banks on the row given the same tones at the same indexes; the Volume column edits existing tones' level (only that float changes); Save writes the banks and soundlabeltable.bin in place (timestamped backups first) or Save to.. under a folder ready to install (fighter/NAME/sound, sound/config), everything checked against the vanilla layout and the originals before writing. No command changed. See "Sound Adder (v1.7.33)" below. Test: `sound_viewer_test.cs` / `.py` (`--adder`). v1.7.32: **Sound Effect Viewer** (Tools > Sound Effect Viewer.., Ctrl+Shift+E): the open fighter's sounds (se, costume, vc, cheer, Kirby-copy banks) and the common ones (sound/se/snd_se_joucyu, row 0) listed with the sound id ACMD plays them by, tone, bank, length, loop, volume and your alias (Aliases/sounds/), played (DSP-ADPCM decoded, at the bank's volume), filtered by name / alias / id, and added to the open script as a sound command; hovering a sound id in a script shows its tone and alias; Sound_Effect / Transient_Sound_Effect / Stop_Sound_Effect gain help on sound ids and an example each (no command changed). See "Sound Effect Viewer (v1.7.32)" below. Test: `sound_viewer_test.cs` / `.py`. v1.7.31: Corrin's cyan sword trail: trail texture ids 272 `TexKamuiSwordTraceCyan` / 273 `TexKamuiSwordTraceCyanAdd` (`tools/kamui_trail_cave.py`, after `trail_table_cave.py`'s 260 - 271) named in the Hitbox Viewer's table (`TrailNames.cs`, which also gains Byleth's 270 / 271) and in the new `Tooltips/trails.txt` (`make_tooltips.py`: every trail texture id by name in the trail commands' texture parameters, a fighter's own ones first when it is open, 272 / 273 with the executable they need: exe_v46z_gkb21 or later); `Sword_Glow` / `Sword_Glow2` keep their group and gain help on their texture ids ("changed in v1.7.31") and an example with the new pair on Corrin's sword (`acmd_ext_help.py` VANILLA_HELP / VANILLA_EXAMPLES, which `make_events_cfg.py` writes after the game's own example); "New Commands"' group text lists them. Test: `trail_textures_test.cs` (`tools/kamui_trail_cave_test.py --sm4shcommand`). v1.7.30: `ModAnimNames.txt` names Greninja's Parabeetle v1 article's scripts (weapon kind 0x1A4, folder `parabeetle`: `ParabeetleWait`, `ParabeetleRise`, `ParabeetleRidden`, its motion kinds 0 / 1 / 2, empty scripts) with a `->` line each to its own animation in `motion/parabeetle/main.pac` (the user's Wii CHR0s converted by `tools/chr0_to_omo.py`), so the Hitbox Viewer plays them; no command changed. v1.7.29: `ModAnimNames.txt` names Greninja's Ice detonation v1 script `FireTrailIceBoom` (the fire trail article's motion kind 3, the ice blast; its game script is empty, the hitbox being its MSC's) with a `->` line to its carrier's animation (Pac-Man's hydrant's, `motion/firetrail/main.pac`), so the Hitbox Viewer plays it; no command changed. v1.7.28: `ModAnimNames.txt` names Greninja's Burn v2 fire trail article's scripts (weapon kind 0x1A3, folder `firetrail`: `FireTrailS4`, `FireTrailHi4`, `FireTrailLw4`, the forward / up / down smash's trail hitboxes, its motion kinds 0 / 1 / 2) with a `->` line each to its carrier's animation in its own `motion/firetrail/main.pac` (Pac-Man's hydrant's), so the Hitbox Viewer plays them; no command changed. v1.7.27: `ModAnimNames.txt` names Greninja's Skeleton v1 Running Skeleton article's scripts (weapon kind 0x1A2, folder `skeleton`: `SkeletonRun`, `SkeletonExplode` (its explosion's hitbox), `SkeletonSmoke`, its motion kinds 0 / 1 / 2) with a `->` line each to its carrier's animation in its own `motion/skeleton/main.pac` (Pac-Man's hydrant's), so the Hitbox Viewer plays them; no command changed. v1.7.26: `ModAnimNames.txt` names Greninja's Clones v1 clone article's scripts (weapon kind 0x1A1, folder `clone`: copies of his body's 37 hitbox scripts, Attack11 ... his specials, under his own motion names) with a `->` line each to his body animation in the article's own `motion/clone/main.pac`, so the Hitbox Viewer plays them; no command changed. v1.7.25: `ModAnimNames.txt` names Supamario's Ultra Instinct v12 projectile script `soaringfist1` (article 0's slot 3: the uncharged Soaring Fist punch, its own fixed knockback) with a `->` line to the fireball's animation; no command changed. v1.7.24: `ModAnimNames.txt` names Supamario's Ultra Instinct v11 scripts: Soaring Fist (his transformed forward smash) in SpecialAirLwHeavy's custom-move slots `SpecialAirLwHeavy_c2` (0x246, the wind-up and the charge) and `SpecialAirLwHeavy_c3` (0x247, the one / two / three-punch releases), each with a `->` line to SpecialAirLwHeavy's animation, and its projectile's scripts (article 0, the fireball's slot) `soaringfist` / `soaringfist2` / `soaringfist3` with `->` lines to the fireball's animation; no command changed. v1.7.23: `ModAnimNames.txt` names Supamario's Ultra Instinct v10 scripts: the alternating sways in SpecialAirLwLight's custom-move slots `SpecialAirLwLight_c2` (0x242) and `SpecialAirLwLight_c4` (0x244), and the dodge's short rush `SpecialLwHeavy_c2` (0x236, after the long rush in SpecialLwHeavy's animation); each with a `->` line to the animation the game plays for it (Hitbox Viewer); no command changed. v1.7.22: `ModAnimNames.txt` drops `SpecialAirLwLight_c2` (Supamario's Ultra Instinct v8: the sway's counter is the transformation's rush, SpecialLwHeavy, so v7's strike script in that slot is gone); no command changed. v1.7.21: `ModAnimNames.txt` names Supamario's Ultra Instinct v7 scripts, the custom-move slots of SpecialAirLwLight his sway uses (`SpecialAirLwLight_c2` the sway's counter, `SpecialAirLwLight_c3` the forward sway; the game plays SpecialAirLwLight's animation for both, so each has a `->` line to it for the Hitbox Viewer); no command changed. v1.7.20: **Outline_Shell's colour shows as given** (exe_v46z_outline5): Smash 4 stores its picture with every colour multiplied by the frame's hdrRange (the lit fighter programs, trails and effects all do it) and divides the finished frame by it again; up to exe_v46z_outline4 the shell wrote its colour unscaled, so it came out 1 / hdrRange times too bright and light colours clipped to white (Time Skip's light blue band: "the outline is white"). exe_v46z_outline5's programs read hdrRange (FB3) like the game's and scale the colour by it; its help says what changed and example 9 shows Time Skip's light blue and a blue-violet glow. Parameters unchanged. v1.7.19: **Mesh_Visibility by name finds every mesh** (exe_v46z_ui4): the game's model loader packs a model's mesh names back to back, most at addresses that aren't a multiple of 4, and the name search up to exe_v46z_ui3 took such a name for "no name": the mesh was never found and was taken for an extra part of the mesh found before it (Supamario's Ultra Instinct v4: Mario_Nohat's command changed Mario_Eye and the half-blinks, Mario_Hair and the silver copies were never reached); its help says what changed and example 9 shows the same look by mesh index (which never searched names) and Mario_Hair by name. Parameters unchanged. v1.7.18: **Mesh_Visibility Persist 2** (exe_v46z_ui2 and later): the mesh's own set state (0 hidden, 1 shown, 2 follow the animation), no entry in the 32-entry override table, kept until written again (a look that lasts a whole stock); its help says what changed and example 8 shows it (a transformation taking the cap off with Persist 2, Entry giving the look back); Outline_Set's help names exe_v46z_outline4. v1.7.15-v1.7.17: Outline_Shell's colour / fixes (exe_v46z_outline3 / outline4). v1.7.14: **Outline_Shell** (exe_v46z_outline2: `tools/outline_shell_cave.py`): `Outline_Shell(Target, Red, Green, Blue, Alpha, Width, Frames, FadeIn, FadeOut, Flash, Blend)` draws a band of colour round an object's silhouette, outside it (a real outline: an inverted hull, the meshes drawn again pushed out along their normals with their front faces culled, in a flat colour behind the body); Width above 0 in pixels of the 1280 x 720 picture, below 0 in game units; grows in / shrinks (FadeIn / FadeOut, Frames), pulses (Flash), solid (Blend 0) or added (Blend 1); Alpha 0 ends it. In New Commands / Effects with its full help and six examples (XV2's white outline, a red pulsing power-up outline, ending it, a black ink line, a mark on the fighter hit, the outline over Screen_Invert's negative). Outline_Set's help says it is unchanged but a rim (inside the silhouette) and gains example 6 (both together). **Mesh_Visibility** (mesh visibility v2, same exe): a mesh with several parts (Polygon_0, Polygon_1 ...: HammerM2_O_OBJ) changes whole; its help says what changed and gains example 7 (a two-part mesh). The Hitbox Viewer draws the shell's band round the model's silhouette (Viewport.DrawShell) and lists the command. `new_var_test.cs` 285 / 1 (on Dr. Mario's files: the effect.bin else-if count expects Kirby's 5), `hitbox_var_test.cs` 243 / 0. v1.7.13: **Outline_Set** and **Mesh_Visibility** (exe_v46z_outline: `tools/outline_cave.py`, `tools/mesh_vis_cave.py`). `Outline_Set(Target, Red, Green, Blue, Alpha, Tint, Frames, FadeIn, FadeOut, Flash)` puts a coloured glow on an object's silhouette edges: the fighter shaders' own rim (fresnel) light, coloured per object through the model's FB1 uniform block (g_fresnelOffset), with an optional body tint (the overlay), fades, Frames and a pulse (Flash: one cycle every Flash frames); Alpha 0 ends it; a KO, the match end or a training reset clear it. `Mesh_Visibility(Target, Mesh, Visible, Persist)` hides / shows a mesh by name (**Mesh="name" in quotes compiles to the name's CRC32**: any int parameter takes a quoted name that way; shown as the hex number afterwards, which compiles the same) or index, over the motion's visibility animation and the visibility groups, until the motion changes (Persist 0) or until changed (Persist 1); Visible 2 ends one override, Mesh -1 every one. Outline_Set in New Commands / Effects, Mesh_Visibility in New Commands / Animation, each with its full help and examples (a white edge glow for a time stop, a red pulsing power-up outline, ending it, XV2's flashing outline, a mark on the fighter hit; a weapon hidden for one animation, hidden until shown again, given back, a hidden prop shown, by index and ending every override). The Hitbox Viewer follows both: Mesh_Visibility in the Model parts tab ("hidden / shown by Mesh_Visibility (script)"), the outline drawn on the model (a rim on the edges seen edge-on, its tint over the overlay) and listed with the screen events. `new_var_test.cs` 272 / 1 (the known effect.bin else-if count; every example compiles and round-trips), `hitbox_var_test.cs` 231 / 0 (the viewer's outline fades / pulse and mesh overrides). v1.7.12: **Screen_Invert** (exe_v46z_inv: `tools/screen_invert_cave.py`): `Screen_Invert(Mode, Strength, Frames, FadeIn, FadeOut, Saturation, Brightness, Red, Green, Blue)` turns the 3D picture (not the HUD) into a photo-negative at any strength, then greys it (Saturation), darkens / brightens it (Brightness) and lifts it toward a colour (Red / Green / Blue, 0-255, added), faded in and out; Mode 0 ends it; Frames holds it; the match end / a training reset clear it. It is the game's own colour-correction pass (the 3D copy's colour matrix that Screen_Tint drives), so nothing new is drawn. In New Commands / Effects with its full help (the maths, timing, the gotchas: the fighters are inverted too, Strength 0.5 is grey) and five examples (Xenoverse 2's dark blue-grey time stop, the white negative after the punch, a negative flash on a strong hit, a half-strength fade, a greyscale look). `new_var_test.cs` counts updated. v1.7.11: Effect_Camera's help says LAST_EFFECT_SET_COLOR takes 0-255 (divided by 255, multiplying the effect's own colours; 0-1 values are black) and LAST_EFFECT_SET_ALPHA percent; example 7's blue is (0, 90, 255) (v1.7.10's (0, 0.35, 1) drew black, as camera_effects v5's test did). v1.7.10: Effect_Camera's help says what camera_effects v5 changed (exe_v46z_camfx5: the game's 2.5D mode, which the world request switches on, squashed every CPU particle's depth x 0.07 toward the stage: v4's dizzy stars were drawn small near the screen's centre; v5 turns that mode off for camera effects, so every emitter type works, CPU or GPU particles), the billboard gotcha (billboards now face the camera exactly), example 4 at Size 0.05 (the stars' real size, no longer squashed) and a new example 7 (corner squares with the dizzy stars on them). The command's parameters are unchanged. v1.7.9: Effect_Camera's help says what camera_effects v4 changed (exe_v46z_camfx4: the effect's particle emitter sets now get the camera matrix every frame; v1-v3's particles stayed where they started) and has a **Shape** note (a round flash texture draws a disc: a darkening overlay wants a square, solid texture); Stage_Freeze's help records v3's in-game result (On 1 no flash, On 2 / 3 flash). Examples unchanged but example 6's comment. v1.7.8: **Stage_Freeze's On** (camera_effects v3, exe_v46z_camfx3): On 1 now freezes the stage with no white screen (only the stage manager's update flag; v1.7.7's On 1 was the game's full stop, which whited the screen out for the whole freeze in game: the user's Dr. Mario test, Supamario's Time Skip); On 2 is that full stop (the flash kept for whoever wants it), On 3 the Final Smash stop (the full stop and the effects the Final Smashes hide and pause); the help has a "What changed" section and example 5. **Effect_Camera**'s help says what v3 changed (the camera matrix given to eft after the game's own update of the effect, its position / scale fields kept with it, the camera manager's camera as a fallback; the battle camera's fitted near clip) and has example 6 (a time stop's darkening staying on the screen while the camera pans); parameters unchanged. `new_var_test.cs` 243 / 1 (the known effect.bin else-if count; every example compiles and round-trips, Stage_Freeze's 5 and Effect_Camera's 6 included), `hitbox_var_test.cs` 208 / 0. v1.7.7: Effect_Camera's help gains **Sizing** (a bank particle's scale is its quad's full width; Mode 1 shows it W x Size / 2 screen heights wide, Mode 0 / 2 W x Size units at Z, the screen ~0.75 x Z tall; bank effects are 10-40 units, so Mode 1 sizes of 0.02-0.2; check an ID's emitters first: 0x1000042, labelled "Multiple white stars flashing", is PtcCommonThunder, additive flashes up to 40 units, which camera_effects v1's test used and which blew the screen out to white); the Size text now says one effect unit = Size half screen heights (a quad 2 units across at Size 1 covers the height: v1.7.6 said 1 unit, wrongly); example 4 uses the common dizzy stars 0x100002C at Size 0.08. The command and the executable are unchanged (exe_v46z_camfx). v1.7.6: **Effect_Camera** (exe_v46z_camfx: `tools/camera_effect_cave.py`): `Effect_Camera(Graphic, X, Y, Z, XRot, YRot, ZRot, Size, Mode, Frames, Flags)` starts an effect (the fighter's bank or the common one) attached to the camera the game draws with, set every frame: offsets in camera space (X right, Y up, Z forward from the eye), facing it, following its moves and zooms; Mode 0 follow, 1 fixed to the screen (X / Y / Size in half screen heights, scaled with the FOV: full-screen overlays), 2 position only; Frames ends it (a fade), Flags 1 unslowed (Time_Scale's slow-motion). In a new subgroup, New Commands / **Effects** (its group help, the command's full help and five examples: a time-stop darkening, a glass-shatter burst, a charge vignette, a common effect pinned to a corner, Mode 2 falling particles); the command list now orders Time & stage and Effects before Variables. The Hitbox Viewer draws it in front of its own view (X / Y from the view's centre, Mode 1 in half the view's height) and ends it with its Frames. `new_var_test.cs`: 241 checks (631 commands, 47 with help, 11 group blocks; Effect_Camera's words, round trip, group; every example compiles and round-trips; the one failure is the effect.bin else-if count, as in v1.7.5's run on the same body); `hitbox_var_test.cs` 206 / 0; `viewer_scripts_test.cs` 39 / 0 (6 new: Effect_Camera's spawns, Frames, the view placement). v1.7.5: **Hitbox_Hold** (exe_v46y_hold: `tools/hitbox_hold_cave.py`): `Hitbox_Hold(ID, Mode)` after a hitbox command makes that hitbox's hits keep the victim in place (no knockback travel; damage, hitstun, hitlag, SDI and the reaction stay): Mode 1 a victim on the ground the hit doesn't lift (the rapid-jab setting the port pipeline now gives Ultimate's setoff-off rapid-jab hits, with Ultimate's own angle 361), Mode 2 every victim (drills), 0 off; ID -1 every hitbox of the object; it goes with the hitbox (a new hitbox in that ID drops it), plain and Extra hitboxes alike. In New Commands / Hitboxes & hits with its help and four examples (a rapid-jab loop hit, a holding drill, the same hit without it for comparison, every hitbox at once). `new_var_test.cs`: 232 checks (630 commands, Hitbox_Hold's words, its group, every example compiles and round-trips; the one failure is the effect.bin else-if count, which is Kirby's 5 and 0 on the ZSS body used here, as in v1.7.4's run); `hitbox_var_test.cs` 201 / 0. v1.7.4: **variable resets** (exe_v46w: `tools/var_reset_cave.py`): `New_Var` takes an optional **`Reset`** (1 KO, 2 landing, 4 ledge grab, 8 hit, or the names joined by `|`: `Reset=landing|ledge`), the events that put the variable back to its Initial; kept in bits 8-11 of the Scope word, shown only when not 0, so every old script compiles and shows as before; **`Var_Reset_Set(Variable, Reset, Value, Owner)`** gives any variable (`VAR_n`, `TIMER_n`, a New_Var name, the input / state variables) a reset on its owner (this object or a target); the variables `VAR_RESET_ID` / `VAR_RESET_VALUE` / `VAR_RESET_OWNER` / `VAR_RESET` (`0x0F0003CA`-`3CD`, MSC's way) have names. New_Var's help says what changed and has four new examples (a combo counter reset on landing, a once-per-airtime flag reset on landing / ledge, a buff cleared on KO, a charge cleared when hit); Var_Reset_Set has its help and five examples (in New Commands / Variables). `new_var_test.cs`: 226 checks, 0 failures (629 commands, every example compiles and round-trips, Line_Test's too; Reset's words, names, errors; Var_Reset_Set's words); `hitbox_var_test.cs` 197 / 0. v1.7.3: **Line_Test** (exe_v46v_line, `tools/line_test_cave.py`): `Line_Test(Space, X0, Y0, X1, Y1, Floors, Distance, HitX, HitY, Kind)` follows a segment against the stage (the game's own GroundModule ray check) and stores how far the first floor / wall / ceiling is, the point and its kind; Space 0 relative to the object along its facing, 1 world; Floors 1 leaves the passable platforms out; the same from the variables `LINE_X0` ... `LINE_NY` (`0x0F0003D0`-`3DA`, named) for MSC. In New Commands / Position & rotation with help and four examples (a beam cut at a wall, a floor check ahead, the variables, a world line); `new_var_test.cs`: 205 checks, every example compiles and round-trips. v1.7.2: **every script of a move runs in the Hitbox Viewer** (game, effect, sound and expression, together and each on its own frame cursor, as the game runs them: hitboxes, body states and effects from any of them), **effect models' parts placed in their bone's space** (a flame pillar drawn under the stage now stands on the fighter), **particles' UV animation** (the common flash's ring, Link's air up special: a ring, not four arcs), and **Add Script File / Remove Script File** (give a motion a script in one more of its four files, the file made if missing); see "Every script, effect models, UV animation, script files (v1.7.2)" below. v1.7.1: the Hitbox Viewer's **common effects checked against the game's own common bank** (vanilla, sent by the user): Dr. Mario's forward-air arc in front of him and orange-yellow (each fighter's colour for the common attack arcs / streaks, fighter_param 0x13C-0x147), Pac-Man's jab streak ahead of his fist and his neutral-air puffs without blocks, Link's air-grab beam (the Genesis beam) without its edge lines and with its head meshes the right way round; see "Common effects against the game's bank (v1.7.1)" below. v1.7.0: **Time_Scale / Target_Time_Scale / Stage_Freeze** (exe_v46n): the whole match slower (the game's own slow-motion, 1/2 ... 1/20) or faster (2-4 game steps a frame), one fighter slower (the Timer item's slow), the stage frozen (the stage manager's own stop), each for some frames or until ended, all ended with the match. In New Commands / Time & stage, with help (what each affects, how they stack with training's speed / the Timer / Final Smashes, offline only) and examples (a hit opponent at half speed for 60 frames, the stage frozen during a hold, a 2x speed-up for 120 frames); new_var_test.cs: 198 checks, every example compiles and round-trips. v1.6.4: **Thread_Start's help** says what exe_v46m changed (threads run in game: before it no thread of any object ever ran) and has an example of a fighter's thread (docs/acmd-extra-commands.md "Thread_Start"); nothing else changed. v1.6.3: the Hitbox Viewer's **Model parts** right-click menu (defaults saved per fighter in VisUser.txt), Pac-Man's visibility groups, part animations (hands, props), billboard sprites, stripes drawn as ribbons, emitter blocks fixed; see "Model parts menu, part animations, stripes, blocks (v1.6.3)" below. v1.6.2: the Hitbox Viewer gets a **Model parts** tab (every mesh, shown / hidden and why, your own choice per mesh), shows the fighter's meshes as the game's **visibility animations** say (faces, eyes, ... per motion), follows the scripts' **visibility commands** (Model_Changer & co., the expression script too), draws **effect colours / alphas as the game scales them** and the **body overlays / flashes**, has a **Hitboxes** toggle, and draws **swoosh / streak effects the right way round** (following particles follow their emitter's live turn; camera billboards were mirrored); see "Model parts, visibility, colours, arcs (v1.6.2)" below. v1.6.1: the Hitbox Viewer's **effects follow the same scripts as its hitboxes** (one rule for both: the selected tab's game and effect scripts, edits followed as you type, an effect.bin opened alone works), **common effects are drawn** (the game's data/effect/common, found above the fighter's folder or picked once with **Common effects..**), and **effect rates** (`LAST_EFFECT_SET_RATE`, a spawn's own Rate) speed up / slow down particles, models and lifetimes; see "Effects: scripts, common bank, rates (v1.6.1)" below. v1.6.0: **the Hitbox Viewer draws the effects** (Level 2: the .ptcl particles simulated, the effect models animated, the sword trails textured; approximate, see "Effects drawn" below; Level 1's markers are their own toggle). v1.5.0: **the Hitbox Viewer shows the effect script's effects** (Level 1: where each effect plays; see "Effects in the Hitbox Viewer" below). v1.4.13: **Buffer_Clear / Buffer_Set** (exe_v46l): `Buffer_Clear(Target, Inputs, Frames)` empties a fighter's input buffer (Inputs bits: 1 attacks, 2 specials, 4 jump, 8 shield / dodges, 16 grab, 32 taunts, 64 stick commands; 0 everything), now or for some frames; `Buffer_Set(Target, Input, Direction, Frames)` puts a press in it as if pressed (a stick direction, + 8 flicked), for the game's window or Frames. In New Commands / Inputs, with help (how the game's buffer works, the difference from Input_Set) and examples (Super God Fist's release, a buffered jump at the end of a move, ...); the variable `BUFFER_CLEAR` (`0x0F0003C9`, MSC's way) has a name. Tested by `new_var_test.cs` and `hitbox_var_test.cs`, 0 failures. v1.4.12: **Position_Place / Position_Offset_Get and Target 12** (exe_v46k): `Position_Place(Target, Relative, Fwd, Up, Depth, Axes, Frames, Collision)` puts a fighter (or this object) at a stage point, in front of / above this object, moved from where it is, or this object next to the target, some axes only, once or held every frame (Collision 1: through the stage while held); `Position_Offset_Get(Target, Axis, RelativeTo, Variable)` reads its stage position / facing, how far in front / above, behind its back, or the distance: the position variables' uses as commands (the variables keep working). Every command that takes a Target (the input commands too) takes **Target 12**, the fighter this attack hit (its newest hit only; nobody once the attack is over, unlike Target 2), and `Last_Hit_Get` Which 2; its variables are named `ATKHIT_...` (`0x0F0002C8`-`0x0F0002FF`). Help, examples (a Target 12 one for every changed command), tooltips. Tested by `new_var_test.cs` (176 checks: every example compiles and round-trips) and `hitbox_var_test.cs` (159 checks), 0 failures. v1.4.11: **variables in Extra hitboxes** (exe_v43): `Extra_Special_Hitbox` / `Extra_Extended_Special_Hitbox`'s Damage, Angle, KBG, FKB, BKB and Size take a variable (`Angle=STICK_ANGLE`, `Damage=VAR_0`, `Size=charge`, an ID such as `0x0F000300`) with flags after it: `|FOLLOW` (read again every frame while the hitbox is out), `|WORLD` (Angle: a screen angle, mirrored when facing left), `|NEG` (minus it); they compile to the ID in the parameter word (flags in bits 20-23) and show by name. New variable names `STICK_ANGLE` / `STICK_ANGLE_RAW` / `STICK_LEN`, the C-stick's, `ROT_X` / `ROT_Y` / `ROT_Z` (`0x0F0003C0`-`3C8`). Help and four new examples (a stick-aimed hit, one that follows the stick, the fighter's rotation as the angle, a hitbox growing with a charge; an Extended capsule aimed with the C-stick). The Hitbox Viewer draws a variable with the script's last `SET_FLOAT` of it (else a stand-in) and lists it in the Extras column. Tested by `hitbox_var_test.cs` (build it next to the built exe: `csc -out:HvTest.exe -r:SALT.dll -r:SM4SHCommand.exe` + mono's mscorlib / System / System.Core, `-nostdlib`; `mono HvTest.exe Events.cfg Aliases`: 122 checks, 0 failures). v1.4.10: **Gravity_Set** (exe_v42): `Gravity_Set(Accel=0.02, MaxFall=0.6, Mode=0)` sets a fighter's gravity and max fall speed for the rest of the move (Mode bits: 1 multipliers of its own, 2 cut a faster fall at once, 4 no fast fall; -1 keeps its own); it ends by itself at the next status, a hit that takes effect, a ledge grab or a KO. In New Commands / Fighter state with its help and examples; the variables `GRAVITY` / `MAX_FALL` (`0x0F000337` / `338`, read only) have names. v1.4.9: **New_Var** (exe_v40): `New_Var(Name=charge, Type=int, Initial=0, Scope=move)` declares a variable with your own name (int or float, a starting value, kept per object or reset per move; slots `0x0F000380`–`0x0F0003BF`, 64 per object). The name compiles in every variable parameter of every open script (and in int parameters that take a variable ID, such as `SUB_FLOAT_2`'s) and is shown wherever the variable is used; the command stores the name, so opening the file again brings the names back. `Slot` is optional (the name's slot, else the lowest free one) and shown when the script is shown again. View > Commands has it under New Commands / Variables with its help, examples and the names declared in the open scripts; hovering a name shows its slot, type and scope. Int parameters that hold a variable ID (named `...Var...`: `SUB_FLOAT_2`, `Float_Var_Compare_Var`, ...) now show the variable's name (`VAR_0`, a New_Var name) like variable parameters do. v1.4.8: `Leave_Ground_Cancel(Enabled)` (exe_v39: a grounded move goes on in the air instead of ending in Fall) in New Commands / Fighter state, with its help and examples. v1.4.7: View > Commands puts every command this mod adds (33 then) under one group, **New Commands** (first in the list), in subgroups (Hitboxes & hits, Fighter state, Inputs, Position & rotation, Animation, Targets & tracking, Threads); vanilla commands stay where they were. Each new command has in-depth help (how it works, each parameter's values, gotchas) and several complete examples, and clicking a group shows its overview (targets, compare methods, variables, what the commands need). Variable names (`VAR_0`, `SELF_HIT`, ...) compile in int parameters too (the new commands' `Variable` parameters and `SUB_FLOAT_2`'s were refused: "must be a whole number"), and the new commands' `Variable` parameters are variables, shown by name. v1.4.6: threads fixed (a script with a `Thread_Start` block was cut at the block when its file was opened again: everything after it was lost), and the Hitbox Viewer runs thread blocks on their own; new commands Hit_Check / Hit_Get (what an attack connected with: hurtbox, shield, ...), Rotation_Get / _Set, Position_Get / _Set, Motion_Get / _Set, Last_Hit_Get, Target_Slot_Get and the fighter-state commands (Status_, Hitstun_, Hitstop_Set, Damage_, Body_State_Set, Armor_Set, Item_State_Set, Stage_Collision_Set, Joint_Position_Get, Animation_Rate_Set) (`ACMD-new-commands.md`; they need the matching cross_f.rpx). v1.4.5: `ModAnimNames.txt` names Supamario's Kamehameha projectile scripts (fly1-3, finish1-3). v1.4.4: the Hitbox Viewer plays a mod's scripts with their own animations from other motion folders and draws the held model they show (Kirby's Marth-copy sword aerials: `marthbody` animations, `marthsword` on `LHaveN`), from `->` lines in `ModAnimNames.txt`. v1.4.3: `ModAnimNames.txt` names the scripts the mods add (Kirby's Marth-copy sword scripts); loaded with `AnimNames.txt`, which keeps your own labels. v1.4.2: kinetic types listed in Set_Kinetic_Handler's description; Track_Target Mode bit 4 (no gravity). v1.4.1: Hitbox Viewer fixes (Extra hitbox commands, fractional FRAME / WAIT timers, the selected tab's script) and a DI multiplier. v1.4.0: usage examples in View > Commands.

**Run:** needs .NET Framework 4 (built into Windows 10/11). Windows may warn that the exe is from an
unknown publisher ("More info" > "Run anyway"); if the zip was downloaded, right-click it > Properties >
Unblock before extracting. A file or fighter folder can be dragged onto the exe (or given on the command
line) to open it. If anything goes wrong, the error and its details are written to
`Sm4shCommand_errors.log` next to the exe.

**Build:** open `Sm4shCommand.sln` in Visual Studio (Windows, .NET Framework 4.0 or later) and build. On Linux
(v1.4.7's exe): mono's `xbuild` with Microsoft's C# compiler (Roslyn, from the .NET SDK, as for Sm4shExplorer:
`tools/sm4shexplorer/README.md`), on a copy of this folder with two case links the project files expect
(`ln -s Params SALT/SALT/PARAMS`, `ln -s Gui SM4SHCommand/GUI`):
`xbuild SM4SHCommand/SM4SHCommand.csproj /p:Configuration=Release /p:CscToolPath=$PWD/roslyn /p:CscToolExe=csc`.
`Events.cfg`, `AnimNames.txt` and the `Tooltips` and `Aliases` folders are copied next to the exe (regenerate the tooltips with `python3 make_tooltips.py`). (The FastColoredTextBox reference used to
point at the original author's desktop; it now uses the bundled DLL.)

## What changed

| Problem | Fix |
|---|---|
| Variables showed as `LA-Int[1]` | Shown as their raw value, `0x2100000D` (like FITX and the game's code). Both forms, and FITX's `var 0x...`, compile. View > "Show variables as LA-Int[1] style" brings the old form back. |
| Hidden scripts weren't listed | In fighter (folder) and project mode, scripts that aren't in `motion.mtable` (subroutines reached through JUMP/CALL, unused scripts) are listed after the motion table entries as `[unlisted] name`, in grey. |
| Save did nothing while scripts were open | Open tabs are compiled before saving (they used to be compiled only when their tab closed). The toolbar Save/Open buttons had no click handlers. In fighter mode, files were written to the working directory instead of where they were opened from. |
| Hitbox fields were missing / wrong | The bundled `Events.cfg`, loaded on top of SALT's definitions at startup, was older than SALT and replaced its hitbox definitions (Special_Hitbox's fields as `Unknown`, X/Z swapped, Rebound/SFXLevel missing). It's now generated from SALT's table (`make_events_cfg.py`). |
| Scripts named by hash | `AnimNames.txt` (next to the exe) lists standard animation names (about half of a fighter's `game.bin` scripts on Kirby, Captain Falcon and Bowser). Tools > Parse Animations now saves the names it finds there, and right-click > **Set Name** names a script (or labels a hash whose real name isn't known), so names only need finding once. Names show in file, fighter and project mode. |
| Parsing animations by hand every time | Tools > **Auto-Parse Animations on Open** (on by default, remembered in `Sm4shCommand.ini` next to the exe): opening a file, fighter folder or project parses that fighter's `motion` folder automatically, found next to the opened folder or one of its parents (`fighter/NAME/motion` for `fighter/NAME/script/animcmd/body`). Each folder is parsed once per session; turning the setting on re-parses the current one. The names are saved to `AnimNames.txt` as with Parse Animations. The "LA-Int[1] style" view option is remembered too. |
| JUMP/CALL targets couldn't be opened | The hash in `JUMP(Hash=0x...)` / `CALL(Hash=0x...)` is underlined; **Ctrl+click** it to open that script. Hovering it shows the script's name. |
| Couldn't add scripts | Right-click > **Add Script..**: an animation name or `0xHASH`. In a fighter folder it's added to game/effect/sound/expression, and you choose whether it also goes into `motion.mtable` (a new motion) or stays unlisted (a JUMP/CALL target). |
| No animation IDs | View > **Show Animation IDs** (on by default, remembered in `Sm4shCommand.ini`) lists each script with its animation (motion) ID: its index in `motion.mtable`, the number the game's code uses for the motion (`MotionModule` / `func_22(0x5f, ...)` in MSC), e.g. `0x5F - AttackS4`. The script's tooltip and its tab show it too, and the filter box matches it (`0x5F`). Fighter and project mode, and single-file mode when `motion.mtable` is next to the opened .bin (scripts are then listed in ID order, then the unlisted ones). Tools > **Go to Animation ID..** (Ctrl+Shift+G; Ctrl+G is the editor's Go to line) opens a script by its ID (hex, `0x383` or `383`). |
| Undo emptied the script | Opening a script put its text in the undo history, so pressing Ctrl+Z past your own edits removed the whole script. Loading isn't an undo step any more. |
| EFFECT_FOLLOW_COLOR unlabeled, in hex floats | Its parameters are named and typed: `Graphic, Bone` (int), `X, Y, Z, XRot, YRot, ZRot, Size` (float), `Terminate` (int), `R, G, B` (float, 0-255), e.g. `EFFECT_FOLLOW_COLOR(Graphic=0x1000012, Bone=0x0, X=10.0, Y=0.0, Z=-50.0, XRot=0.0, YRot=90.0, ZRot=0.0, Size=5.5, Terminate=0x1, R=250.0, G=0.0, B=250.0)`. Float parameters also accept the hex float bits int parameters show (`0x437A0000` = 250.0; up to `0xFFFF` a hex value is that number), so older text still compiles (same bytes). |
| Colors | The name of a command with R, G, B parameters (`EFFECT_FOLLOW_COLOR`, `Color_Overlay`, ...: any command whose definition names three parameters R/G/B or Red/Green/Blue) is drawn in the color they make. Right-click the line > **Pick Color for ...** opens a color picker set to the current color and writes the chosen R, G, B (one undo step; 0-1 values stay 0-1). |
| Numbers only in hex | View > **Show Numbers as Decimal** (remembered in `Sm4shCommand.ini`): int parameters show as decimal (`Angle=361`, `KBG=100`). Int parameters that hold float bits show as floats (`unknown=0.6f`; View > **Show Float Values in Int Parameters as Floats**). Hashes, effect / sound IDs and bit fields stay hex: values above 0xFFFF, and parameters listed in View > **Parameters Always in Hex..** (default: Hash, Graphic, GFXLeft, GFXRight, SFX, HitBits, Flag, Variable1–3). Every form compiles in any int parameter (`0x169`, `361`, `1.5f`), with or without the setting. Checked on 3,443 scripts (Kirby's game/effect/sound/expression and weapons, Captain Falcon): the same bytes back as with hex. |
| Comments were lost on save | `// ...` (on its own line or after a command) and `/* ... */` comments are kept. The game's .bin has no room for them, so saving writes each commented script's text to `FILE.comments` next to the file (e.g. `game.bin.comments`; deleted again when no script has comments); the game never reads it. Opening a script shows that text again. If the .bin was changed by another tool since, the comments go back onto the lines that still match (compared by what they compile to, so `0x169` and `361` match). File and fighter mode (not project mode). A comment after a command used to be a compile error; comments inside `if` blocks are fine too. |
| Editing a parameter meant clicking or arrowing to it | View > **Jump Between Parameters** (off by default, remembered in `Sm4shCommand.ini`): **Tab** selects the next parameter's value on the line, so typing replaces it (in a `Hitbox`: ID, Part, Bone, then Damage, ...); **Shift+Tab** goes back; after the line's last parameter it goes on to the next line that has some (in `if(Bit_Variable_Test(...))` the inner call's values). View > **Parameter Jump Key..** picks another key. Off, Tab works as before. |
| Value tooltips | Hovering a number in a parameter explains it, from the text files in the `Tooltips` folder next to the exe. They're generated from the MSC Note Sheet, the fighter_param sheets and the article list, with `make_tooltips.py`. They cover variables (work variables, fighter_param stats, STrans / STransGroup IDs, the position variables `0x0F0000xx`), common effect IDs in `Graphic=`, the 361 angle, and each fighter's article IDs and special-move params (`0x05`–`0x09xxxxxx`, with default values). Per-fighter entries are used when the open path is `.../fighter/NAME/...`. **Right-click a number > Edit Tooltip..** adds or changes one in `Tooltips/custom.txt`. Tools > **Reload Tooltips** / **Open Tooltips Folder**. The file format (filters by fighter, command, parameter name, type or position) is described at the top of `SM4SHCommand/Classes/Tooltips.cs`. |
| Variable aliases | Names for variables, e.g. `SET_FLOAT(Value=1.5, Variable=LASTHIT_HITSTUN_MUL)` instead of `0x0F000052`. Loaded from the text files in the `Aliases` folder next to the exe (`NAME = 0x0F000052`, any variable form works; `custom.txt` for your own, it wins). `Aliases/variables.txt` (from `make_tooltips.py`) names the common variables of `tools/position_vars_cave.py`: `POS_SELF_X` … `POS_OPP_OFFSET_X` … `POS_SLOT1_X` …, the combat ones as `TARGET_QUANTITY` (`SELF`, `OPP`, `LASTHIT`, `SLOT1`–`SLOT8` × `HITSTUN`, `HITSTUN_DEALT`, `HITSTUN_MUL`, `HITSTOP_SHAKE`, `HITSTOP`, `OFFSET_X/Y/Z`) and `SELF_ANIM_RATE`. The input / state variables (`0x0F000100`–`0x0F00025F`) are `TARGET_QUANTITY` too: `SELF_ATTACK`, `OPP_JUMP_PRESSED`, `LASTHIT_INPUT_OFF`, `SELF_STICK_X`, `SLOT2_DAMAGE`, `SELF_INTANGIBLE`, ... (docs/position-variables.md "Inputs and state"). View > **Show Variable Aliases** (on by default) shows them by name; names always compile, case doesn't matter, and tooltips work on them. Tools > **Reload Variable Aliases** / **Open Aliases Folder**. |
| Tooltips stayed on screen | The editor's tooltip only went away on a mouse move over the editor, so after switching programs, moving the window or changing tabs it stayed over other tabs, sometimes for good. It's now hidden as soon as the pointer isn't over a visible editor in the active window (and a tooltip still waiting for its delay isn't shown then). |
| No list of what commands exist | View > **Commands..** (**F1**): every ACMD command in groups by what it does (Script flow, Variables, Hitboxes, Grabs & throws, Effects, Sound, Camera, Movement, Items, ...), with its description, each parameter's type and meaning, and a template line. Search filters by name, identifier, description or parameter ("knockback", "B738EABD"). **Insert into Script** (or double-click / Enter) adds the command below the caret in the open script with its first value selected; **Copy** copies it. The group is each command's `Category:` line in `Events.cfg`. **Examples:** 332 commands show a usage example under the template: a real use from the game's scripts (`// fighter, script (file)` and the line, with its block for True / False / Else / Set_Loop; `make_examples.py` picks them from the vanilla fighter folder into `vanilla_examples.json`), and, for the new commands, hand-written ones (`EXAMPLES` in `tools/acmd_ext_help.py`). **Insert Example** adds it below the caret (comments included, indented like the caret's line); **Copy Example** copies it. They're the `Example:` lines in `Events.cfg`. **New Commands** (v1.4.7): every command this mod adds is in this one group, at the top, in subgroups (`Category: New Commands / Inputs`: a group `A / B` is shown as B inside A); each has a **help** section after its parameters (`Help:` lines: how it works, the parameters' values, gotchas) and several examples, and picking a group shows its own help (`Group:` blocks: for New Commands, the targets, compare methods, variables and what the commands need). The help, groups and examples are written in `tools/acmd_ext_help.py` (`acmd_ext_cave.py --labels` puts them in `param_labels.json`, `make_events_cfg.py` in `Events.cfg`); search finds words in the help too. |
| Unknown parameters, wrong types | Every `unknown` parameter is labelled from the game's command handlers (`docs/acmd-params.md`; data in `param_labels.json`, applied by `apply_param_labels.py`). 85 commands' int/float types are fixed, 62 `unk_` commands are named (old `unk_XXXXXXXX` names still compile), and misnamed commands give their real name in the description. |
| Command definitions / descriptions | Tools > **Command Definitions..** edits names, parameter names and types, and descriptions, and adds new commands; Save writes `Events.cfg`. Hovering a command in the editor shows its description and parameters; hovering a parameter shows its name, type and description. A description can run over several lines (each further line in `Events.cfg` is a line break; Save keeps them), e.g. Set_Kinetic_Handler's kinetic types, one per line in groups (in the air, jumps, on the ground, moved by the animation, ledge, hit, ...). A long one is cut to its first 24 lines in the editor's tooltip (the command list shows it all), and hovering a parameter's value shows the description's line for that value (`Set_Kinetic_Handler(ID=0xA)`: "0x0A  AIR_STOP - in the air with no drift control"). |
| No way to see hitboxes | Tools > **Hitbox Viewer..** (Ctrl+Shift+H) on an open ACMD script shows its game script's hitboxes on the fighter's own model, posed by its animation, frame by frame: Play, `<` `>` and the slider step game frames (`Set_Frame_Duration` / `Frame_Speed_Multiplier` slow the animation as in game). Timers can be fractional: `FRAME(Frames=8.2)` comes out on the first game frame at or past 8.2 (frame 9 at normal speed), and `WAIT(Frames=0.2)` takes one frame (it isn't rounded down to none). The fighter folder must be laid out as in the game: `NAME\model\body\c00` (model.nud, model.vbn, model.jtb), `NAME\motion\body\main.pac` and `NAME\script\animcmd\body`; the animation is found from the script's name. There is one viewer: it shows the script of the tab selected in the main window and switches when you pick another script tab (Ctrl+Shift+H again brings it to the front). Picking another animation in the list shows that animation's game script (the saved one in game.bin; edits are followed for the open script), or no hitboxes when it has none. The models are textured (model.nut; **Textures** turns it off). Hitboxes are colored by ID, extended ones drawn as capsules (all the hitbox commands, including `Extra_Special_Hitbox` / `Extra_Extended_Special_Hitbox`, whose six extras are in the list's **Extras** column), with their launch angle (`S` for 361); intangible / invincible / super armor are shown. `True` / `Else` blocks: **If conditions true** picks the branch. Drag to rotate, right-drag to pan, wheel to zoom, double-click for the side view; **Bones** shows the skeleton, **Meshes..** the hidden expression meshes. The viewer follows the editor as you type (a script that doesn't compile shows the saved one, with the error). **Enemy**: Mario (the `mario` folder next to the fighter's, e.g. `fighter\mario`; **Enemy model..** picks another fighter folder, remembered) stands where the picked hitbox hits, takes the hit (hitlag), then flies along the calculated trajectory with his damage animation. The corner of the view says what state he's in (hitlag, hitstun and frames left, which cancels he could use, out of hitstun). **Play until the enemy can act** (remembered) makes the timeline run past the end of the animation (the attacker holds its last pose) to the frame he's out of hitstun. **Show hitlag freeze** (remembered) puts the frames both fighters stand still in hitlag (and any `SELF_HITSTOP` / enemy hitstop from the script) on the slider, so playback is in real game frames; the label shows the script frame and "(hitlag freeze)". **Floor** (on by default) keeps the enemy on the ground line; off, he follows the trajectory through it. Pick a hitbox in the list for the **knockback / hitstun calculator** (Sm4sh-Calculator's formulas): target fighter (all 58, from `Viewer\Fighters.txt`), target and attacker (rage) %, smash charge, staleness, crouch cancel, aerial target, launch rate, DI (**DI at** a stick angle; **DI x** multiplies how far DI turns the launch: 0.5 half, 2 double, 0 none). An Extra hitbox's own extras count too: HitstunMul, HitstopMul / HitstopFrames (enemy hitlag), SelfHitstopMul / SelfHitstopFrames (attacker hitlag) and DIMul (multiplied with **DI x**). **Hitstun x**, **Attacker hitstop x** and **Enemy hitstop x** multiply the hitstun and the two hitlags (before the script's own modifiers). It gives damage, knockback, launch angle and speed, hitstun and the first actionable frame, hitstun cancel frames (worked out again for the final hitstun, and later by any hitstop frozen during it), hitlag, shield stun and the distance travelled, and draws the trajectory (no stage) in the view. The script's own modifiers count: `SET_FLOAT` to the hitstun / hitstop variables (`LASTHIT_HITSTUN_MUL`, `OPP_HITSTUN_MUL`, `LASTHIT_HITSTUN`, `LASTHIT_HITSTOP` / `_HITSTOP_SHAKE`, `SELF_HITSTOP`, ... `0x0F000040`–`0x0F000057`) change the hitstun, hitlag and when the enemy flies, at the frame they run relative to the hit, and are listed under the results; the animation rate variable (`0x0F000098`) speeds up the timeline, and the hitbox's own Hitlag multiplier and electric effect are used. Any fighter whose folder has model, motion and script. |

Also:

- **Compile errors instead of crashes or silent damage.** A line that doesn't compile (unknown
  command, wrong number of parameters, a value that isn't a number, an unclosed `{`) stops the save,
  shows the tab and selects the line with the reason. Before, a missing parameter was silently left
  out or the app threw. Closing a tab with an error asks before discarding the changes.
- **Script_End** is added back if it's deleted (the game reads past the end of a script without it).
- **Numbers** are written in a culture-independent, exact form (floats round-trip bit for bit; a
  Windows decimal-comma locale no longer breaks parameter lists).
- **Name lookup:** `Else` and `ELSE` are different commands; exact-case names win.
- **Intensity_Special_Hitbox** listed 46 parameters for a 48-word command, so saving zeroed its last
  word; it now has 47.
- The tree filter box no longer throws when narrowing the list.
- Empty motion.mtable slots show as `(empty)` (with their animation ID).
- The toolbar/window images are embedded as plain PNG/ICO files (`SM4SHCommand/Resources/`) and loaded
  by `Images.cs`, instead of being serialized into the forms' .resx; a startup failure is logged and shown
  instead of the program silently not opening.
- The folder picker falls back to the standard folder dialog if the Vista-style one can't be created.

## Effects in the Hitbox Viewer (v1.5.0, Level 1)

The viewer runs the effect script of the same name (effect.bin next to game.bin, or the open tab's effect editor,
followed as you type) on the game script's timeline: each game frame moves it by the same animation frames
(`Set_Frame_Duration` / `Frame_Speed_Multiplier` / the animation rate in the game script slow it as in game; the
effect script's own are ignored, the motion's rate is one), with the same `FRAME` / `WAIT` timers, loops,
`True` / `Else` (**If conditions true**) and threads.

- **What it reads.** Every effect command, by its name and its parameters' names (Events.cfg / the ACMD events
  sheet): `Graphic_Effect*`, `External_Graphic*`, the `EFFECT_*` family (`_FOLLOW*`, `_FLW*`, `_FLIP*` with their
  GFXRight / GFXLeft, `_COLOR`, `_ALPHA`, `_GLOBAL`, `EM_EFFECT_*` ...): the effect ID, bone, offset, rotation, size,
  its colour / alpha; `LAST_EFFECT_SET_COLOR` / `_ALPHA` / `_RATE` / `_SCALE` (and `LAST_PARTICLE_SET_COLOR`) on the
  last effect; `Terminate_Graphic_Effect` (by ID), `EFFECT_OFF` / `EFFECT_REMOVE_ATTR` (all), `EFFECT_OFF_HANDLE`
  (the last), `EFFECT_DETACH_KIND` (a following effect stays where it is); sword trails (`Sword_Glow`, `Sword_Glow2`,
  `Sword_Trace`, `AFTER_IMAGE*`: every command with Bone1 / Bone2) and `Terminate_Sword_Glow` (+ its FadeTime); screen
  and light effects (tints, flashes, lights, wind, `EFFECT_PAUSE` / `_RESUME`, the `_WORK` calls whose ID is in a
  variable) are listed, not drawn.
- **Following or one-shot.** The developers' `EFFECT_FOLLOW*` / `_FLW*` (`External_Graphic` = EFFECT_FOLLOW,
  `Graphic_Effect4` / `5` / `6` = `EFFECT_FOLLOW_NO_STOP` / `_RND` / `_ALPHA`) move with their bone until terminated
  or the script's end; the others are placed on their spawn frame and stay there, shown for their emitter set's
  lifetime (the .ptcl's one-time emitters: start + emission + particle life), a set that never stops by itself until
  terminated, an effect whose files aren't there (common effects) 20 frames.
- **Names.** An ID `0xBBBBnnnn` is entry nnnn of bank 0xBBBB (docs/efc-format.md): the fighter's
  `effect/NAME/NAME.010d0000.efc` names the `.ptcl`'s emitter set (and an effect model), shown as the effect's name
  (`PtcSupamarioGfCsg_Crg`, `model EffSupamarioGfCsgBas`); bank `0x300 + kind` is looked up by the fighter kind's
  folder (this fighter's, else the sibling `fighter/<kind>`: Kirby's copies use Hero's 0x345), a port's base fighter's
  number in its own folder (Hero's 0x32C, Robin's); common effects (`0x01000000 +`) from the tooltips (gfx.txt).
- **In the view.** Each effect is a sphere (radius 2 x Size) at its bone + offset, with its axes (X red, Y green,
  its forward Z blue) turned by its rotation (degrees, X then Y then Z), coloured by its set colour, dashed when
  one-shot, labelled with its ID and name (**Labels**); sword trails are the blade's line with a fading band over its
  last frames (**Trails**). **Markers** (v1.5.0's **Effects**) turns them off. The **Effects** tab next to the hitboxes lists the frame's
  effects (or **every effect of the script**): ID, name, bone, offset, rotation, size, colour / alpha / rate / scale,
  follow or one-shot, its frames (and why it ended), the facing check; trails and screen events below them.
- **Flip facing** turns the scene round as the game turns a fighter facing left (and shows a `_FLIP` call's
  GFXLeft). Effects turn with it rigidly here; in game an effect isn't simply turned: what the God Fist / Core Breaker
  ports learned (tools/xv2_smash_fx.py `facing_check`: on bone 0 only a height / forward offset and a Y turn of 0 or
  180, on any other bone no offset and no turn) is checked, and an effect that breaks it is marked `!` in the view and
  in the list, with why.
- **Approximate / not done (Level 1).** (v1.6.0 draws particles, models and trails: below.) The effect's own
  rotation order and the game's left-facing transform of effects aren't decoded (see Flip facing); `Random*` offsets
  are left out; an effect whose ID comes from a variable (`_WORK`) shows "(from variable ...)"; `EFFECT_FOLLOW_STR`'s
  bone (a name hash) isn't resolved; `Terminate` flags (end with the status) aren't modelled (the script's end is);
  one-shot lifetimes ignore a set's looping emitters' own life and `LAST_EFFECT_SET_RATE`. Tested headless by
  `effect_viewer_test.py` / `effect_viewer_test.cs` (Super God Fist, Mario's up smash / back throw, Hero, Kirby's
  BraveSword17, timeline cases: 32 checks).

## Effects drawn in the Hitbox Viewer (v1.6.0, Level 2)

On top of Level 1 (which effect plays where and when, above), the viewer draws what each effect is, from the
fighter's effect bank: the `.ptcl` emitter set's particles, the `.efc` entry's effect model and the sword trails'
textures, blended over the fighter and depth-tested against it. Toolbar: **Effects** (draw them), **HQ** (quality),
**Dark bg** (a dark background, on by default: additive effects show as on a stage), **Markers** (Level 1's spheres /
axes; **Labels** their names), **Trails**.

- **Particles** (`Classes/Viewer/Particles.cs`; a port of `tools/fx_render.py`'s Smash 4 simulation, the rules in
  docs/ptcl-format.md). Each emitter of the set is stepped one game frame at a time from the effect's start to the shown
  frame: emission (start frame + emit start, end frame for one-time emitters, interval + its random, the rate carried
  between frames, key-animated), the volume (point, circle random / even with its sweep, filled circle, sphere, filled
  sphere x the shape scale), velocity (all-direction + directional along the emit direction, spread, its random part),
  then each frame the move by the velocity it had, air resistance and gravity (world or the emitter's); life (+ its
  random), the scale / alpha / colour curves over the particle's life (eft's 3-key ramps, colour keys x colour scale x
  the emitter's colour / alpha multipliers 0x378-0x3A7), rotation (init + random, its speed), the emitter's key
  animations (rate, life, emitter scale / rotation / translation, colours, alpha, speeds, particle scale, shape scale)
  and its follow type (0: the particles move with the effect; 1: left where they were born; 2: by its position).
  Particle types: camera billboards (0, 7), Y billboards (8), XY / XZ plates in the emitter's frame (1, 2),
  directional along the velocity (3, 4); an emitter's primitive mesh is drawn instead of the quad. Texture slot 0 is
  decoded through the model textures' GX2 decoder (BC1-5, RGBA8; its channel selector), its first flipbook cell (UV
  scale); blend alpha / add / subtract (0x324); the colour combiner (0x314: colour, colour x texture, colour 1 to
  colour 0 by the texture). Distortion passes aren't drawn. The random numbers are a fixed-seed generator per effect
  and emitter: the same picture every time, scrubbing back gives the same particles.
- **Effect models** (an `.efc` entry's `model/<name>/`): model.nud / .nut / .vbn, posed by model.omo from the
  effect's spawn (looped while it follows, held on its last frame for a one-shot), its materials' `NU_effColorGain`
  (colour and alpha) and `NU_effTransUV` / `NU_effScaleUV` from model.mta (else the material's own), the vertex
  colours, blended by the material (dst 2 add, 3 subtract, else alpha), placed by the call's bone / offset / rotation
  x Size. A one-shot model-only entry lives as long as its animation.
- **Sword trails** (`Sword_Glow` / `AFTER_IMAGE*`): the blade's two points on this frame and the BlurLength frames
  before (4 steps between each two), as a ribbon with its two textures: the texture ids through the game's trail-name
  table (`TrailNames.cs`: ids 1-259 the game's, 260 - 271 `tools/trail_table_cave.py`'s, 272 on `tools/kamui_trail_cave.py`'s), `<name>.nut` (NTP3 or NTWU)
  from this fighter's or the other fighters' `effect/*/trail` folders, shaded as the trail shaders 1 / 2 / 3
  (docs/native-notes.md "The trail shaders"; 3 = Hero's retracting trail), faded over Terminate_Sword_Glow's frames.
  A trail whose texture isn't found keeps Level 1's band.
- **Responsiveness.** Particles a set's emitter keeps: 150 (HQ 600), quads drawn a frame: 2,500 (HQ 8,000); the
  status line says when a cap was hit. Without HQ the effects are drawn at half resolution and added back smoothed
  (an explosion's screen-filling glows: about 0.2 s a frame at worst, 60 ms typical, against 0.5 s), textures
  nearest-sampled unless blown up past twice their size; HQ draws at full resolution with bilinear textures. A
  simulation is kept per effect and stepped on as the frame moves on (a frame back starts it again).
- **Approximate (no game shaders, no bloom).** The emitters' own pixel / vertex programs aren't run: the combiner
  word decides the colour, and the alpha comes from the texture's own alpha channel when it has one, from its red
  when its alpha is constant (BC4's R R R 1; the converted effects' programs read it so); no HDR / glare / bloom,
  no refraction (distortion passes and trail shaders 1001 / 1002 left out, the latter drawn as 1); premultiplied
  (ONE / INV_SRC_ALPHA) trail blending assumed; no lighting on effect models (`NU_angleFadeParams`, `NU_effRotUV`,
  the efc's mesh-switch records not read); complex emitters' fields (random / magnet / spin / collision /
  convergence / curl noise), fluctuation and child emitters, stripes (types 5 / 6 drawn as quads in the emitter's
  frame), velocity stretch and texture slot 2 aren't simulated (slot 1 is a mask since v1.6.1); eft's random generator isn't reproduced (the
  sets' shapes and timings are, the exact scatter isn't); a
  following effect's particles vanish when it's terminated (the game lets live ones finish). (v1.6.1: rates and
  common effects are drawn: below.) The view's camera is orthographic: a
  flat ring on the ground (Fake Death's) is edge-on from the side; drag to look from above.
- **Tested** headless by `effect_viewer_test.py` / `.cs` (58 checks): the live particles on frames 0-29 of the God
  Fist's Csg_Crg and Csg_Circle, Core Breaker's Cor_Fire, Fake Death's ring and Mario's up special sets equal
  `tools/fx_render.py`'s simulation of them (every emitter with no random life / gap), a particle's path (velocity,
  air, gravity) equals it to 0.002, the fixed seeds (stepping on and back), the textures equal `tools/ptcl.py`'s
  decode, the God Fist aura and Core Breaker orb models' frames and colour gain equal `tools/mta.py`'s and they pose,
  the trail ids / names / Hero's textures, the blending; plus Level 1's 32. Screenshots (God Fist, Core Breaker,
  Fake Death, Kirby's BraveSword17, Mario's forward smash) under Xvfb.

## Effects: scripts, common bank, rates (v1.6.1)

- **Where the scripts come from: one rule for hitboxes and effects** (`HitboxViewer.PickCommands`,
  `Classes/Viewer/ViewerScripts.cs`). The viewer shows the selected tab's animation. While it is shown, each script
  (game for the hitboxes, effect for the effects) is that tab's editor text, compiled as you type; a compile error
  shows the saved script and says why. Another animation picked in the viewer's list shows that animation's saved game
  and effect scripts. The saved files are the ones open in the main window, else the game.bin / effect.bin next to
  them on disk (read again when they change on disk; read from a copy, so the main window can always save over them).
  - Fixed: picking another tab in the main window kept the first tab's effect editor (its edits drove the effects of
    every script shown after it); the effect.bin next to game.bin was read once when the viewer opened (later saves
    weren't seen); in single-file mode an effect.bin opened alone was refused ("No game.bin is open") or its script
    taken for the game script. Now an effect.bin (or sound / expression.bin) opened alone shows its effects with the
    game script's hitboxes from the game.bin next to it, and a game.bin opened alone finds its effect.bin.
- **Common effects** (ids `0x01000000 +`, bank 0x100: dust and landing clouds, hit sparks, fire puffs, ...). The game
  keeps them in `data/effect/common/common.010d0000.efc` / `.ptcl` (+ `model/`, `trail/`), next to `data/fighter`. The
  viewer looks for that folder above the fighter's folder (`fighter/NAME/../../effect/common`, any folder further
  up too: a dump's content/patch/data, a mod's data folder). If it isn't there, **Common effects..** (next to Enemy
  model..) picks it once: the folder itself, `data/effect` or `data` (remembered in Sm4shCommand.ini,
  `ViewerCommonEffects`). Common effects are then drawn as the fighter's (particles, models, one-shot life from their
  set) and named by their tooltip name with the set after it; without the folder they stay markers, and the status
  line says how to pick it. The common trail textures (`TexCommonHammerTrace`, ...) come from its `trail` folder.
- **Effect rates.** `LAST_EFFECT_SET_RATE(Rate)` sets the last effect's playback speed: the game multiplies the
  effect's emitter-set step by it (eft's frame step x the rate; docs/ultimate-fighter-port.md: Ultimate's command of
  the same name writes the set's rate, "as Smash 4's command of the same name"), so the viewer steps the effect's own
  time by the rate each game frame: rate 2 runs two of its frames a game frame (emission, motion, life), 0.5 one every
  other game frame, the particles drawn between their steps by the fraction; its model's animation (omo / mta) plays
  at the rate; a one-shot's life becomes life / rate game frames. `EFFECT_FLW_POS_STRENGTH`'s own `Rate` does the
  same. `LAST_EFFECT_SET_RATE_WORK` (the rate in a work variable) is listed, not applied (the value isn't known
  here). The game script's `Set_Frame_Duration` / `Frame_Speed_Multiplier` / the animation rate slow the effect
  script's timers (FRAME / WAIT, as in v1.5.0) but not the particles: an effect plays on game frames at its own rate
  (the system's step), as the trails do (docs/native-notes.md "Sword trails": the tick's step x the trail's rate);
  `LAST_EFFECT_SET_DISABLE_SYSTEM_SLOW` exists for the global slow-down, which the viewer has none of.
- **Texture slot 1** (new, approximate): an emitter's second texture (vanilla fire, e.g. Mario's: a shape flipbook
  over a noise texture) is drawn as a mask on the first (its first cell, its own UV scale): the fire puffs no longer
  show as squares.
- **Tested** (`effect_viewer_test.py` / `.cs`, 80 checks, 0 failures): rated lives (2, 0.5, 1.5, 1); three
  `LAST_EFFECT_SET_RATE`s in a script; `EFFECT_FLW_POS_STRENGTH`'s Rate; every particle of the God Fist's Csg_Circle at
  rate 2 on game frame 1 + t = at rate 1 on 1 + 2t, at 0.5 on 1 + 2t = at 1 on 1 + t, half a step drawn between; the
  aura model's frame at 0.5 / 2; the common bank found as the game lays it out and picked from data / data/effect /
  the folder (the game's own common files aren't in this repository: the test puts a stand-in there, Supamario's bank
  under the common name), its sets, model, names, life and particles; without it markers and tooltip names; the
  script rule (single-file effect.bin and game.bin, fighter mode's sub-tabs, the editor text compiled, an edit, a
  compile error falling back with the error, another animation's saved script, game.bin read from disk next to an
  effect.bin, a file changed on disk read again). The editors themselves (FastColoredTextBox) don't load on Mono:
  the rule picking a tab's editor is what's tested headless.

## Model parts, visibility, colours, arcs (v1.6.2)

- **Model parts tab** (next to Hitboxes / Effects; the toolbar's **Model parts..** opens it, replacing the v1.4 mesh
  dialog): every mesh of the fighter's model (and of the held model) with a **Show** box, what the frame shows without
  your choice (**Now**) and **Why** (your choice, a visibility group, the visibility animation, the default). Ticking a
  box overrides it; **Reset to script / default** drops your choices, **Show all** / **Hide all**. Choices are kept per
  fighter while Sm4shCommand runs. Below the list: the script's visibility commands so far and the groups' states.
- **Which meshes show by default (the Pac-Man ball bug).** Smash 4 decides it per motion from the model folder's own
  visibility animations: `material_anime_face.pac`, `_eye.pac`, `_eyelid.pac` (packs of MTA4 files named after each
  motion, `FitMarioBodyMainF00DamageHi1.mta`, whose visibility tracks switch the `_VIS_O_OBJ` meshes key by key: Mario's
  FaceN / Ouch / Blink / Nohat, Kirby's eyes and big body ...). The viewer now reads them (`Classes/Viewer/MeshVisibility.cs`
  MaterialVis): on each frame the motion's own tracks, and for a motion without a file the neutral state (Wait1's frame
  0). Meshes no track names keep the name rule (expression variants hidden). Not found in any data file: the model's
  `model.moi` lists the `_VIS_` objects (name, bone, index) but no default state; `model.xmb` / `model.nud` / the
  fighter's vl params have none either.
- **The scripts' visibility commands on the timeline.** `Model_Changer(ChangerID, ChangerState)`,
  `VIS_SET_DEFAULT(Group, State)`, `VIS_BACK_DEFAULT(Group)`, `VIS_RESET_DEFAULT(Group)` and `Visibility(State)` (the
  whole model) are run from the game, effect **and expression** scripts (the expression script now follows the same
  rule as the others: the tab's expression editor, else expression.bin), each group's state per frame, the scripts
  merged (the later change wins). `Visibility(State=0)` hides the model. A group's meshes are in the game's code (the
  VisibilityModule, accessor +0xA8: `Model_Changer`'s handler `0x02BD70E8` calls its vt +0xCC op 0x2711 -> vt +0x4C,
  which looks the group up in a per-fighter table of per-state part records at module +0xC and switches them through
  the ModelModule's vt +0x17C), not in the fighter's files, so they come from **`VisGroups.txt`** next to the exe
  (`fighter group state: mesh, ...` and `fighter group default: state`; shipped empty, documented in the file): a
  group listed there shows its current state's meshes and hides its others; without it, the group's changes are
  listed in the tab, not applied.
- **Effect colours and alphas as the game applies them.** The colour commands' values are 0-255 and divided by 255
  (`EFFECT_*_COLOR`, `LAST_EFFECT_SET_COLOR`: 510 = 2.0), the alphas percents divided by 100 (`LAST_EFFECT_SET_ALPHA`,
  `EFFECT_*_ALPHA`, `Graphic_Effect6` / `7`); `LAST_PARTICLE_SET_COLOR`'s multipliers (0-1.5) go on top; the light
  commands' colour (`EFFECT_LIGHT` / `_FOLLOW_LIGHT`) is the light's, not the effect's. The result multiplies every
  emitter's colour (x its own emitter colour 0x384 / alpha 0x3A4 x the particle's curves) and the effect model's colour
  gain. v1.6.0 / 1.6.1 took a colour over 5 as 0-255 and used the alpha as it was (50 meant 50 x).
  `EFFECT_COLOR_WORK` (from variables) stays as listed.
- **Body overlays / flashes** (`Color_Overlay`, `Change_Overlay` over its Transition frames, `Terminate_Overlays`,
  `FLASH_NO_STOP` / `FLASH_OFF`, `Flash_Light_Effect` / `Change_Flash_Light_Color` added as a light) tint the fighter
  (and its held model) on their frames (**Overlays**); approximate: the colour mixed in by its alpha, no shader.
- **Hitboxes** checkbox: hides the hitbox spheres / capsules and their angle arrows (the list, the calculator and the
  trajectory keep working); remembered in Sm4shCommand.ini.
- **Swooshes / streaks the right way round.** Two fixes:
  - Particles of a following emitter (0x310 = 0, "the particle points at the emitter's live matrices") are kept in the
    emitter's own space and placed by the call x the emitter matrix **of the frame shown**, its key-animated turn
    included. v1.6.0 froze the emitter's matrix at each particle's birth, so a swoosh whose emitter swings with the
    move (Mario's up smash `PtcMarioSmashHed`: its emitters turn about Y from -180 to -100 degrees over frames 2-10;
    the common forward-air arc is made the same way) stayed where the swing started.
  - Camera billboards (types 0, 7, 8) were mirrored: their X pointed to the screen's left (tools/fx_render.py's CPU
    basis), so the quad was seen from behind and every asymmetric sprite (a streak, an arc) pointed backwards. eft's
    own programs build them from the view block's billboard matrix, X along the screen's right (fx_render's
    `s4_view_block`), as the viewer now does.
  Facing left (Flip facing) the scene turns round, so effects attached to the fighter come out mirrored on screen
  while billboards still face the camera unmirrored.
- **Tested** (`effect_viewer_test.py` / `.cs`, 91 checks, 0 failures): Mario's DamageHi1 face meshes on frames 0 / 3 /
  11 against `tools/mta.py`'s reading of the three packs; the parts priority (your choice > a group > the visibility
  animation > the default) and a group switching with `Model_Changer`; the visibility commands on the timeline and
  two scripts merged; the colour / alpha scaling (`EFFECT_FOLLOW_FLIP_COLOR` 100 / 180 / 510, `LAST_EFFECT_SET_ALPHA` 50,
  `LAST_PARTICLE_SET_COLOR`, `Graphic_Effect6`'s Alpha, `EFFECT_LIGHT`); an overlay set, changed over 4 frames and
  ended; a following particle placed by the live emitter matrix (Mario's up smash swoosh), the swoosh in front of him
  facing right and mirrored facing left, billboards not mirrored in either facing. Not available here: Pac-Man's and
  Dr. Mario's files and the game's common effect bank (the forward-air arc and the attack streak are common effects),
  so the two reported cases weren't drawn; Mario's own swoosh (the same make) was.

## Model parts menu, part animations, stripes, blocks (v1.6.3)

Tested with the user's own Pac-Man, Dr. Mario and Link folders (game files: not in this repository).

- **Model parts right-click menu** (the selected rows, or the one clicked): **Show now** / **Hide now** (this session,
  as the Show box), **Hidden by default for this fighter** / **Visible by default** (saved in **`VisUser.txt`** next
  to the exe as `fighter hide: mesh` / `fighter show: mesh`, read on every start), **Follow the script / default**
  (takes your choice and your saved default away), **Isolate** (only these meshes now), **Show all**. A default is the
  fighter's neutral state: a script's visibility group still shows / hides the mesh on its frames. The order a mesh is
  decided in: your choice now; a group whose state doesn't list it (hidden); the motion's visibility animation; a group
  whose state lists it (shown); the fighter's defaults (yours over `VisGroups.txt`'s); the name rule. (v1.6.2 let a
  group's current state show a mesh over the visibility animation; now the animation decides those, so a group can
  list a body together with its face meshes.)
- **`VisGroups.txt` entries for Pac-Man**, read from his expression scripts (`Model_Changer` calls) and model:
  group 0, the 3D body / the 2D Pac-Man `PizaM` (state 1: neutral air, dash attack and others through subroutine
  `0x669E43CF`); group 1, the ghosts (forward smash 1: Blinky `Aaka`; up smash 2; down smash 3; down taunt 4; win 2: 5);
  group 2, the Final Smash power pellets `FinalpoweresaA` / `B` (the "ball", state 1 in `finalstart` only); group 3,
  the up taunt's 18 signs (`boardA`-`R`, one a state). Every group defaults to 0: in Wait only the body shows. Which
  ghost sprite the up / down smash and down taunt raise on bone `GhostA1N` (`Aaka`, `Aosuke`, `Guzuta`, `Ijike` and
  the signs all sit on it; `Pinkey` alone on `GhostB1N`) is inferred: correct the lines if the game shows another.
  The file also takes `fighter hide:` / `fighter show:` defaults now.
- **Part animations.** A fighter's `motion/body` holds more than `main.pac`: `lhand.pac` / `rhand.pac` (the hands'
  poses: fists, open hands), `NAMEpt1.pac`, `NAMEsw1.pac` ... (props, swords, Pac-Man's ghosts, signs and pellets),
  each with the same motions (`FitPacmanBodyPacmanpt1C03AttackS4S.omo` beside `FitPacmanBodyMainC03AttackS4S.omo`) on
  bones `main.pac` doesn't animate. The viewer played only `main.pac` (open hands everywhere, Pac-Man's ghosts never
  moved); it now layers the parts on the main motion.
- **Billboard bones.** A bone named `..._BILLBOARD_...` turns its meshes to the camera (`BILLBOARDY`: about the
  vertical only): Pac-Man's ghosts and signs are flat sprites on such bones, drawn edge-on (invisible) before.
- **The expression script ran late.** `SetExpression` (the main window passes the expression scripts after making the
  viewer) didn't run the scripts again, so their visibility commands waited for the first edit. It does now.
- **Emitter blocks (the translucent squares, Pac-Man's neutral air).** Two causes, both fixed:
  - A combiner that takes the alpha from the texture (0x314 = 1, or a selector naming its own alpha) on a texture that
    has none (every texel opaque: a one-channel BC4 whose selector names a missing alpha channel) covered its whole
    quad. Such a texture's shape is in its red channel: the viewer now reads the alpha from red there. Reproduced with
    Dr. Mario's real Cyclone (`PtcMariodCyclone` ring1 / impact2, `PtcMariodSmashAura`), squares before, ring after.
  - A texture with no native surface (TexRes native size 0) wasn't decoded, and its quad was drawn untextured, a
    solid block. Its original image (+0x20 format 2, RGBA8, row by row) is decoded now, with its component selector
    (Pac-Man's Final Smash eyes and scores: B G R A); an emitter whose texture still can't be read isn't drawn (the
    status line counts them). Pac-Man's neutral-air blocks come from common effects (0x1000072 / 0x1000052 /
    0x1000023): the same rules apply to them once the common bank is set.
- **Stripes** (particle types 5 / 6: eft's ribbons, the sword trails `kiseki*` and streak / beam emitters) are drawn as
  ribbons: type 5 through each particle's history of places (as many as the stripe block's history length, the
  divisions between each two smoothed), type 6 through the emitter's particles; width the particle's scale, across
  facing the camera (stripe type 0) or along the emitter's Y (1 / 2); alpha from the block's start to end alpha;
  texture U across, V along. v1.6.2 drew one quad per particle in the emitter's frame, a block or bar pointing
  wherever the emitter did. Link's up special (`PtcLinkKaitengiriSword` kiseki1) now trails the blade, both facings.
- **Effect models' UVs and colours** as the effect shader (`texas_cross.nsh` MC_EFFECT, docs/smash-run-port.md "UV
  transforms") works them out: turned by `NU_effRotUV`, `U = (u + t.x) s.x`, `V = 1 - s.y (1 - (v + t.y))` (v1.6.2:
  `u s + t`, another part of a scaled / scrolled texture); `NU_effCombinerColor0 / 1` (colour 1 + (colour 0 - colour 1)
  x the texture, by analogy with eft's interpolating combiner: the effect pixel program isn't read yet). The body
  shaders' `NU_colorSamplerUV` likewise as `s (uv + t)`.
- **Defaults**: Markers off, Labels off, HQ on. An `Sm4shCommand.ini` from an older version is reset to these three
  **once** (the `ViewerDefaults163` entry records it); what you choose after that is kept.
- **Arc / streak / beam colours and sides (open; found and fixed in v1.7.1, see "Common effects against the game's bank").** Dr. Mario's forward air plays one effect, the common arc
  `0x1000090` (`EFFECT_FOLLOW_FLIP` on bone 0, (-3, 5.5, 1), turned (-24, -11, -60), size 0.95), with no colour command
  and no trail command (`Sword_Glow` has no colour fields: a trail's colour is its two textures and shader), so its
  light yellow is the common bank's own (the arc's emitter colour keys / combiner, or its effect model's vertex
  colours, colour gain and combiner colours). Pac-Man's jab streak (`0x100008D`), Link's air grab beam (`0x10000A5`, at
  rate 4) are common effects too. The game's common bank (`data/effect/common`) wasn't among the files sent, so these
  three weren't drawn here; the viewer's billboards, polygons and directional particles were checked against Smash 4's
  own vertex programs run on real emitters (tools/latte_exec.py: the same corners, U toward the screen's right, V
  down / back along the velocity), and stripes, untextured blocks and missing-alpha blocks (the likely causes of the
  bars and blocks) are fixed above.
- **Tested** (`effect_viewer_test.py --pacman DIR --mariod DIR --link DIR`, the folders read where they are; 113
  checks, 0 failures; without the folders the 22 real-file checks are skipped): Pac-Man in Wait (body only), finalstart
  (pellets), forward smash frames 20 / 40 (Blinky on, then off), neutral air (the 2D Pac-Man through the CALLed
  subroutine, on the slowed timeline), the up taunt (one sign); the menu's defaults written to and read back from a
  VisUser.txt, a mesh hidden by default still shown by its group, and taken out again; forward smash's ghost bones
  animated by `pacmanpt1.pac` only; the ghost sprite facing the camera both facings; FinPacman's original-format
  textures (16 x 16, pupils blue); all 184 emitters of the three fighters' banks textured and none reading alpha from
  a texture without it; Dr. Mario's Cyclone ring and forward-air script; the effect UV formula; Link's up special
  stripes as ribbons both facings, mirrored. `new_var_test` 186 / 0 and `hitbox_var_test` 169 / 0 unchanged.

## Common effects against the game's bank (v1.7.1)

Checked with the game's own **vanilla** common bank (`data/effect/common`: `common.010d0000.efc` / `.ptcl`, `model/`,
`trail/`, sent by the user; game files, not in this repository) and the user's Pac-Man, Dr. Mario and Link folders.
**The viewer draws whatever common bank is in your game folder** (found above the fighter's folder, or the one picked
with **Common effects..**): if you have modded your common effects, the viewer shows yours, not the vanilla ones these
notes describe. Each fix below was read off Smash 4's own vertex programs (`tools/fx_render.py` `draw_s4`, the game's
`cross_f.rpx` shaders run on the real emitters) or its code:

- **Fighter colours for the common attack effects.** The common arcs and streaks are white in the bank; the game
  colours them per fighter. Every fighter's EffectModule holds a table (fighter_param_etc g14: common 0x8D, 0x92, 0x8E,
  0x90) with the fighter's own r, g, b for each (fighter_param words 0x13C-0x147, labelled "motion_blend" before), and a
  request for one of those ids gets it as the effect's colour (the call `LAST_EFFECT_SET_COLOR` makes; a colour command
  after it replaces it). Dr. Mario / Mario / Luigi / Sonic: 0x90 (3, 0.7, 0.25), Dr. Mario's forward-air arc's
  orange-yellow (white where it's brightest); Pac-Man 0x8D (2, 0.65, 0.55); Fox / Lucario blue, Samus / Ness green;
  Link, Marth and others white (docs/native-notes.md "Fighter colours for the common attack effects"). The viewer
  reads the game folder's `data/param/fighter/fighter_param.bin` when it finds one above the fighter's folder (your
  edited colours), else the vanilla values. A colour call's colour now multiplies colour 1 too (eft's own rule: the
  arcs' edges kept their colour 1 before).
- **Dr. Mario's forward-air arc in front of him** (both facings). The arc's sheets are directional polygons (particle
  type 4) given a tiny motion on purpose (1e-6 along the emitter's Y, 1e-8 along -Z); the game's program aims them by
  it however small, which turns them 180 degrees about Y. The viewer took them as at rest (under 1e-4) and drew the arc
  mirrored behind him.
- **rotBasis** (the emitter's 0x4C4): the game draws a particle's quad off its centre by this fraction of its size.
  Pac-Man's streak lines (`PtcCommonAttackLine`, 0x100008D) lie ahead of his fist, not centred on it.
- **Texture wraps** (each texture's sampler: mirror, repeat or clamp per axis). A 2 x 2 repeat in eft mirrors a
  quarter texture into a whole one; the viewer repeated it, so the streak's head glow (and others) came out as four
  bright corners, a square. Mirrored and clamped edges no longer blend with the texture's far edge (the Genesis beam's
  long quads drew a thin line along each edge).
- **Colour 1 with a texture's own alpha**: an emitter whose texture has its own alpha (combiner 2 with an RGBA texture)
  lost its colour 1 (black): the soccer-ball puffs (0x1000072) in Pac-Man's neutral air were sooty black, tan in the game.
- **XZ plates** (particle type 2): laid with their Y along the emitter's -Z, not +Z (the game's programs on the bomb
  rings and the Genesis beam's head meshes: they trail their particle along the beam).
- **Box volumes** (type 10): particles on the box's faces (`0x04A503C4`), not a sphere (Pac-Man's streak lines).
- Checked and left: hit sparks 0x1000001 / 0x1000002, landing smoke 0x1000006 / 0x1000007, dash smoke 0x1000009 and the
  fire puff 0x1000011 sit, move and grow as the game's programs draw them. The game lights its smoke (a stage light
  colour the programs read and the viewer doesn't have): the viewer's dust is the emitters' own cream / white.
  Stripes (types 5 / 6: the Genesis beam's lightning) aren't run through the game's programs here: unverified.
- **Tested** (`effect_viewer_test.py ... --common DIR`: the bank linked where the game keeps it, read in place; 131
  checks, 0 failures; without it, the stand-in bank as before, 113): the bank's entries (13 ids, against tools/efc.py +
  ptcl.py), the colour table (Dr. Mario, Pac-Man, Link; a fighter_param.bin in a game folder read instead), Dr. Mario's
  arc and Pac-Man's streak on the fighter's front in both facings, the wraps, rotBasis, the box volume, the beam's
  plates, and every emitter of the common bank textured with no blocks.

## Every script, effect models, UV animation, script files (v1.7.2)

- **Every script of the move runs.** The game runs all four ACMD scripts of a motion every frame (game, effect, sound,
  expression, in that order) and any command works in any of them; the viewer now does the same
  (`HitboxRunner.Others`): one timeline, each script with **its own frame cursor** (FRAME / WAIT timers, Set_Loop,
  True / Else blocks, CALL / JUMP into its own file, Thread_Start), all on the motion's rate (Set_Frame_Duration /
  Frame_Speed_Multiplier / the rate variable from whichever script sets it, from its next frame). Hitboxes, body states
  (intangible / invincible / armour), effects, trails, overlays and visibility commands from any script are the move's;
  the lists say which script a hitbox / effect came from when it isn't the usual one (`Hitbox (expression script)`).
  Up to v1.7.1 hitboxes came from the game script only and effects from the effect script only (a game script's effects
  were dropped when the move had an effect script; the sound script never ran). Vanilla cases: Pac-Man's 0xE8410CDF
  (FitPacmanBodyMainD03SpecialLwFailure) has its two hitboxes only in its expression script and 0x2BB1E8A1 its
  Special_Hitbox and its Set_Frame_Duration(7) in its effect script; Link's 0x1DDF4AA6 (EscapeAir) an effect in its game
  script. Sound commands (Sound_Effect, Stop_Sound_Effect, ...) aren't listed as effects. The sound script is followed as
  you type, like the other three (its tab's editor).
- **Effect models' single-bound parts in their bone's space.** An effect model's mesh bound to one bone (no weights)
  has its vertices in that bone's own space, placed by the bone's world matrix alone: EffCommonCrossBomb's fire meshes
  on a bone 250 units up have their vertices from -253 to -44 (the column from the ground to its flares' top at 206),
  Link's boomerang tornado's wind rings on bones 3-9 up sit at 0-12 in theirs. v1.7.1 skinned them as a fighter's
  (world x inverse bind: right for a fighter's face meshes, which are in model space), which takes the bone's bind
  transform off again: every such part was drawn that far off, a flame pillar under the stage (the user's Link up
  special) while its particles and hitboxes were in place. Rigged parts are skinned as before.
- **Particles' UV animation** (each texture slot's scroll / scale / turn, per frame, initial and random: the emitter's
  0x514-0x54C for slot 0, 0x590-0x5C8 for slot 1, the inverse-random flips 0x4DA / 0x4DB), worked out as the game's
  vertex programs do (`tools/eft_vertex.py` `uv1_lines`, fitted against them within 2e-5): a quad's corner turned about
  the texture's centre, scaled, minus the shift. The common flash (0x100001C, PtcCommonFlash; Link's air up special's
  start, many others) has a ring of a quarter texture mirrored 2 x 2 and shifted by one along V: v1.7.1 ignored the
  shift and drew four arcs bowing in round the star; it's a ring now, as the game's programs draw it (gold ring, white
  to blue star). The particles' randoms come from a generator of their own: their paths are unchanged. Approximated: the
  vertex programs aren't read, so a slot's animation is drawn whenever its values aren't the still ones; which random
  flips a particle's U / V (inverse random) is a guess.
- **Add Script File / Remove Script File** (fighter mode: a fighter's or an article's animcmd folder opened with File >
  Open > Fighter..). Right-click a motion in the tree, or the script tabs of its open tab: **Add Script File** lists the
  files that have no script for it (game, effect, sound, expression; "new KIND.bin" when the folder has no such file)
  and gives it an empty one (Script_End) under the motion's hash (the CRC32 of its lower-case name, as every script is
  keyed), opened in its own tab to edit at once; **Remove Script File** takes one out (asked first). Save writes it: an
  existing file keeps its other scripts byte for byte; a missing file is made, an ACMD file in the endianness of the
  folder's other files (big for Wii U, little for 3DS), that the game and Sm4shCommand read. The Hitbox Viewer plays the
  new script with the others (from the open files, before saving too). (Add Script.. still adds a new motion to all
  four files at once.) Saving works under Mono too now (SALT wrote through kernel32 and mapped a temp file past its end).
- **Tested** (Mono; build next to the exe, see each file's head):
  - `viewer_scripts_test.cs` (`xvfb-run mono VsTest.exe Events.cfg link pacman mariod --common DIR`): 45 checks, 0
    failures. Synthetic four-script moves (a hitbox and a body state in the effect / sound scripts, a Set_Loop in the
    sound script on its own WAIT cursor, an If / Else in the expression script both ways, a Set_Frame_Duration in the
    effect script slowing every script, no game script); every script of Link (380), Pac-Man (366) and Dr. Mario (325)
    run the v1.7.1 way and the v1.7.2 way: the game script's hitboxes / body states and the effect script's effects the
    same (no effect twice), apart from the 5 Pac-Man motions whose rate another script sets (their timeline is now the
    game's); Pac-Man's and Link's cross-script moves above; the UV formula; EffCommonCrossBomb's parts above ground.
  - `script_files_test.cs` (`mono SfTest.exe Events.cfg BODY_DIR WORK`, on Link's and Pac-Man's folders): 25 checks, 0
    failures. An effect script added to a motion with only a game script, edited, played by the viewer's scripts,
    saved: one more script, the others byte-identical, the other files untouched; reopened, removed, saved: effect.bin
    byte-identical to the original; sound.bin made from nothing (header, one script, size); an article folder with only
    a game.bin given the three others; a little-endian folder's new file little-endian.
  - Rendered (the user's Link, the vanilla common bank): Link's air up special frames 4-8 (the flash a ring), the
    CrossBomb fire column on his up special (v1.7.1 under the stage, v1.7.2 above it), Pac-Man's SpecialLwFailure
    (hitboxes from its expression script). `hitbox_var_test.cs` 184 / 0; `new_var_test.cs` 200 / 1, the one failure
    the same as v1.7.1's (its effect.bin else-if count is Kirby's).

## Sound Effect Viewer (v1.7.32)

**Open it:** Tools > **Sound Effect Viewer..** (Ctrl+Shift+E) with a fighter's script open (or after opening a fighter
folder); with nothing open it asks for a fighter folder. **Fighter..** opens another one. One viewer; it follows the
fighter when opened again with another fighter's script.

**What it loads** (`Classes/Sound/`):

- the fighter's banks, every `fighter/NAME/sound/*.nus3bank`: `snd_se_<Name>` (se), its costume banks `_cNN`
  (se c01 ...), `_common` (se_common: Robin / Incineroar), `snd_vc_<Name>` (vc) and its `_cNN`, `_ouen` (cheer),
  `snd_se_vc_Kirby_copy_<Name>` (Kirby copy);
- `sound/config/soundlabeltable.bin`, found as the game lays it out (data/sound next to data/fighter) in a folder above
  the fighter's: a dump's `content/patch/data`, a mod's `INSTALL_TO_data` (whose own table, with its added rows / labels,
  is used);
- the common bank `sound/se/snd_se_joucyu.nus3bank` (BINF 2000, row 0), the same way;
- what isn't above the fighter's folder (a mod folder with only `fighter/NAME`) comes from the game data folder picked
  with **Game data..** (remembered as `SoundDataFolder` in `Sm4shCommand.ini`; the folder, its `data`, or its `sound`
  folder). The mod's own label table wins over the picked one.

**Sound ids:** a sound id is `row << 16 | label`. The label table gives each bank (by the BINF id inside it) a row; each
label of the row names a tone of the bank (-1 none). Greninja's snd_se_Gekkouga (BINF 2058) is row 0x768: his IceBoom,
label 97 -> tone 110, is `0x07680061`. Costume banks share the main bank's ids. A port's banks on their own ids
(46000+, `tools/sound_bank_ids.py`) have no row of their own: the game plays them through their alias (the old id's
row, `tools/sound_alias_cave.py`); the viewer reads the aliases from `Viewer/SoundBanks.txt` (written by
`make_tooltips.py` from `reference/port_sound_ids.json`); a costume bank with no row uses its main bank's.
Common sounds are row 0, `0x00000000` - `0x0000019E`, played by every fighter with the same commands
(`Sound_Effect(SFX=0x46)`, futtobi_l, the strong-launch sound; vanilla Dr. Mario's and Kirby's sound scripts play row-0 ids 222 times): no other command form.
Ids from `0x80000000` are voice sequences (`soundseq_<Name>.sqb`, Low_Voice_Clip / PLAY_FLY_VOICE), not tones.

**The lists** (tabs **Fighter sounds** and **Common sounds**; **Banks** lists the files, BINF names / ids and how
each found its row): one row per label that reaches a tone, then the tones no label reaches (id `-`: no id plays
them). Columns: **Sound ID** (hex, as a sound command takes it), **Tone (label)** (the tone's name in the bank),
**Alias (yours)** (editable), **Bank** (se, se c01, vc, cheer, common ...), **Length (s)**, **Loop** (the tone has loop
points: the game holds it until stopped), **Ch**, **Rate**, **Volume (dB)** (the TONE entry's, what the game plays
it at), **Tone #** (its index in TONE), **Note** (a label pointing past the bank's tones, an empty / container slot).
Column headers sort. The **Bank:** list on top narrows the fighter tab to one bank; the common tab's own **Bank:**
list shows another `sound/se` bank (items, menus ...) for reference: only `snd_se_joucyu` is the fighters' common bank,
other banks play only when the match has them loaded (not checked).

**Filter (name, alias, ID):** above both lists, as you type, case doesn't matter: a sound stays when its tone name,
alias or bank has the text, or its id does: hex with or without `0x`, any part (`0768`, `5B`, `0x7680061`,
`0x0768005B`), or the id in decimal (`124256353`). The tabs say how many are shown (`6 of 136`). Clearing it shows
everything. The picked sound stays picked while it is in the list; an alias edited while filtering keeps its row
until the filter changes.

**Aliases:** type in the Alias column; saved at once to `Aliases/sounds/<fighter>.txt` next to the exe (the fighter's
folder name, e.g. `gekkouga.txt`), the common tab's to `Aliases/sounds/common.txt`, one `0x07680061 = Creeper boom`
per line (editable by hand; `#` comments). Labels only: scripts keep the number. Tools > Open Aliases Folder shows
them; the variable aliases (`Aliases/*.txt`) don't read this folder.

**Tooltips:** hovering a sound id in a script (Sound_Effect's `SFX`, PLAY_SE_REMAIN's `Se`, PLAY_STEP_FLIPPABLE's
`SoundID` ...) shows `Sound 0x07680061: snd_se_Gekkouga_IceBoom`, its bank, row, label, tone, length, channels, rate,
volume, and your alias (looked for in the open fighter's file, then common.txt, then any fighter's: Kirby's copies
play other fighters' rows); an id of a bank the fighter doesn't have shows its row / bank id; a voice sequence says so.
The fighter's banks are read (headers only) the first time a sound id is hovered.

**Preview:** **Play** (or double-click a row, or Enter) decodes the tone and plays it; **Stop**. Every Smash 4 Wii U
tone seen is Namco IDSP: DSP-ADPCM (the GameCube / Wii codec: 8-byte frames of a predictor / scale byte and 14 4-bit
samples, 8 coefficient pairs per channel) with a big-endian header; mono or stereo (channels interleaved every 0x10
bytes), 47-48 kHz. The decoder (`Classes/Sound/Idsp.cs`) is the DSP's formula (vgmstream's); it plays the PCM as an
in-memory WAV through `System.Media.SoundPlayer` (.NET Framework, Windows). **Bank volume** (on) plays it at the
tone's volume (dB); **Gain** adds preview gain; **Loop** plays a looping tone's loop (its loop start - end) after its
intro for about 8 s, as the game holds it. A tone in another codec (none seen) is listed with its codec and isn't
played. The info line under the list gives the codec, channels, rate, samples, loop points, volume and its place in
PACK.

**Add to Script:** **Command** picks the sound command (Sound_Effect = PLAY_SE, Transient_Sound_Effect = PLAY_STATUS
for looping sounds, Stop_Sound_Effect, PLAY_SE_REMAIN, PLAY_SE_NO_3D, Sound_Effect3 = PLAY_LANDING_SE,
Sound_Effect4 = PLAY_DOWN_SE, Sound_Effect2 = PLAY_STEP; their Events.cfg names); **Add to Script** puts e.g.
`Sound_Effect(SFX=0x7680061)` on a new line below the caret of the script tab selected in the main window (any of its
four scripts; the sound script is where the game's own sounds are), with its value selected, one undo step, as View >
Commands' Insert. A common sound is the same command with its row-0 id. **Copy ID** / **Copy Line** copy `0x07680061`
/ the line. Help: Sound_Effect, Transient_Sound_Effect and Stop_Sound_Effect's View > Commands pages have a "Sound
ids" section and an example (`tools/acmd_ext_help.py` VANILLA_HELP / VANILLA_EXAMPLES).

**Limits:** the preview plays one sound at a time, without the game's 3D placement, pitch or the sound priority /
volume tables (`soundvolumetable.svt`, `soundprioritytable_fighter.spt`); container tones (snd_se_joucyu's
`futtobi_meteor_`, which the game fills from other tones) and empty slots aren't played; a bank's id with no row and
no known alias has no ids. The viewer alone writes nothing to the banks or the label table: v1.7.33's Sound Adder (below) does.

**For part 2 (adding tones; done in v1.7.33, "Sound Adder" below):** `Sound.Nus3Bank` keeps every section and TONE entry as read and `Build()` writes the bank
back (byte-identical when unchanged: the user's snd_se_Gekkouga, vanilla vc and snd_se_joucyu); `Tone.VolumeDb` is
settable (only its float changes); `Build(pack)` takes a PACK with new audio appended. `Sound.SoundLabelTable.Build()`
is byte-identical too; `SetLabels(row, tones)` grows a row (its old labels and ids stay), `UseRow` gives an empty row a
bank, `UsedIds()` lists every id in use (a new tone gets the row's next label, so it can't clash).

**Tested** (Mono; `sound_viewer_test.py` builds `sound_viewer_test.cs` next to the built exe and runs it: `python3 -I
tools/Sm4shCommand/sound_viewer_test.py RUN_DIR FIGHTER_ROOT GAME_DATA PORT_ROOT OUT [--mp3 MP3] [--gui]`, the GUI part
under xvfb-run): 196 C# checks and 23 Python checks, 0 failures. The user's snd_se_Gekkouga (111 tones, the skeleton
and IceBoom ones; 14 empty stubs), vanilla snd_vc_Gekkouga and snd_se_joucyu (404 tones, 9 stereo, a container)
parsed and rebuilt byte for byte; a volume change touches only its float; the package's label table (row 0x768: 98
labels, label 97 -> tone 110) rebuilt byte for byte, part 2's row growth / empty row read back; the fighter's list
(0x07680061 IceBoom, 0x0768005B SkSpawn1 ...), the common one (0x46 futtobi_l, 0x61 furafura looping, 0x0F
Hit_Muteki); Master's banks on their own ids (46192, 46201) through SoundBanks.txt's 2028 row; seven tones (mono,
stereo, looping, a voice, the 47962 Hz zoom) decoded sample for sample the same as the test's own Python decoder; the
IceBoom decode against the user's creeper_explosion.mp3 it was made from: correlation 0.9974 at 0.149 s (the padding
`tools/gekkouga_sound.py` put in front); previews (a loop's repeats, gain), the WAV header; the aliases' files, reading
back, finding another fighter's, clearing; the variable aliases skipping `Aliases/sounds`; the tooltips (own id,
common id, a sequence, not on other parameters); the filter (name, alias, hex with / without 0x, partial, decimal,
empty); every command line Add to Script gives (8 commands x own / common id) compiles, decompiles to the same text and
recompiles to the same bytes, and the three commands' examples; the form under Xvfb: both lists filled, the IceBoom
row's columns, the filter, an alias typed in the list (kept while filtered), Add to Script (the line it hands over: the
script editor, FastColoredTextBox, can't be created under Mono), a common looping sound as Transient_Sound_Effect, the
looped preview WAV. `new_var_test.cs` 290 / 1 (the known effect.bin else-if count on Dr. Mario's body, as v1.7.31's),
`hitbox_var_test.cs` 248 / 0. **Not run on Windows:** the sound itself (SoundPlayer playing the WAV; Mono has no audio
device here), the real Add to Script into the editor (the same `InsertCommandLine` View > Commands uses), and the
tooltip in the live editor.

## Sound Adder (v1.7.33)

New sounds for a fighter's bank, with sound ids no other sound has, and the volume ("sound level") of the tones it
already has; inside the Sound Effect Viewer (Tools > Sound Effect Viewer.., Ctrl+Shift+E). Code: `Classes/Sound/`
`SoundAdder.cs` (the plan, the build, the checks, the save), `AudioImport.cs` (reading, resampling, trimming),
`DspAdpcm.cs` (the encoder and the IDSP writer); `Gui/SoundAdderDialog.cs`, `Gui/SoundViewer.cs`.

**Adding:** **Add sounds..** (the viewer's top bar) opens the adder on the fighter shown:

- **Bank:** the fighter's bank the sounds go into (se by default; any of its banks with a row: vc, cheer, se_common,
  the Kirby-copy bank, a costume bank alone). **Also the costume banks on this row** (on): see "Costume banks" below.
- **Add files..** picks one or more files. **WAV is read natively** (PCM 8 / 16 / 24 / 32-bit, float 32 / 64-bit,
  WAVE_FORMAT_EXTENSIBLE, any rate; more than 2 channels are mixed to stereo). **Other formats** (MP3, OGG, FLAC, M4A,
  WMA, Opus, AIFF): on Windows through **Media Foundation** (the system's own decoders: MP3 / AAC / WMA on Windows 7+,
  FLAC on Windows 10+, OGG only with Microsoft's Web Media Extensions); if that fails, or off Windows, through
  **ffmpeg** when it is on PATH (or `ffmpeg.exe` next to Sm4shCommand.exe), which decodes to a temporary 16-bit WAV.
  With neither, the file is refused with "Convert it to a WAV first (Audacity: File > Export > WAV, 16-bit PCM), or put
  ffmpeg on PATH". The dialog's grey line says what this machine can read.
- Each sound is then **resampled to 48000 Hz** (the rate of the game's own tones; a Kaiser-windowed sinc, 32 zero
  crossings a side: against ffmpeg's resampler r = 1.00000), **mono or stereo as the file is**, and **encoded to
  DSP-ADPCM in a Namco IDSP file exactly as the vanilla tones are**: the 0x40 header, a 0x60 DSP header per channel
  (samples, nibbles = nibble(n - 1) + 1, the loop flag, start / end nibbles, the 8 coefficient pairs, the first frame's
  ps; for a looping sound the loop frame's ps and history), each channel's frames padded to an even count and
  interleaved every 0x10 bytes for stereo (read from vanilla snd_se_Gekkouga, snd_se_joucyu's stereo tones and
  snd_vc_Gekkouga_ouen). The encoder is `tools/dspadpcm/grok.c` ported to C# (`DspAdpcm.cs`): its coefficients and
  frames are byte for byte those of `tools/dspadpcm` (dspenc), the encoder the tones in the game today were made with.
- Per sound (the list; the row picked also has the controls under it):
  - **Tone name**: the bank's naming pattern filled in (its BINF name + `_` + the file's name: `snd_se_Gekkouga_IceCrack`);
    letters, digits and `_`, up to 254 characters, not a name the bank already has;
  - **Alias**: written to `Aliases/sounds/<fighter>.txt` when saved;
  - **Volume (dB)**: the TONE entry's volume float, what the game plays it at (vanilla tones -20 .. +6), from the slider or
    the number box (-40 .. +20, 0.1 dB steps);
  - **Trim** (on): leading / trailing silence cut, below **Silence below (dBFS)** (-45 by default, the peak in any
    channel: `tools/gekkouga_sound.py`'s rule);
  - **Normalize** (on): the clip's peak at -0.5 dBFS before the volume, as `tools/fighter_own_bank.py` does (off: as
    the file is);
  - **Loop** (off): the whole clip loops in game (loop 0 .. n - 1 in the IDSP and the TONE tail); play it with
    Transient_Sound_Effect, stop it with Stop_Sound_Effect.
- **Preview** (or double-click) plays the sound **as the game will have it**: the IDSP decoded back to PCM, at the
  chosen volume (a looping one for ~8 s), through the viewer's playback.
- The plan line under the list gives the row, the labels, the ids and the tone indexes the sounds will get, and any
  problem. **Close** keeps them: they are listed in the Fighter sounds tab **as new / unsaved rows** (bold, blue, after
  their bank's last id), which play, take an alias, filter (name, alias, id) and go into a script with Add to Script
  / Copy ID / Copy Line like any other (`Sound_Effect(SFX=0x7680062)`).

**The ids can't clash:** a new tone gets the **next label of the row its bank plays from**: the row of the bank's BINF
id (snd_se_Gekkouga, 2058: row 0x768); a port's bank on its own id (46000+) through its alias' row
(`Viewer/SoundBanks.txt`, as the game's alias cave does); a costume bank with no row through its main bank's. Label =
the row's label count + k, **sound id = row << 16 | label** (Greninja: 98 labels, so 0x07680062, 0x07680063 ...), each
checked against **every id in use in the whole soundlabeltable.bin** (`UsedIds()`: every fighter's rows, the common
row 0, the ports' alias rows): a label past a row's count is in use nowhere, and no other row's id has that row number.
The old labels and ids stay where they are (the row's list is written again at the end of the label pool with the new
labels after the old ones, as `tools/fighter_own_bank.py`'s `set_row`). When the row is shared (a port's alias row is
also its base fighter's; two ports on one alias), the dialog names the other banks: the new labels are new ids for them
too, which nothing plays.

**Caps:** a sound id's label is its low 16 bits: the game splits the id with `clrlwi r5, r4, 16` / `srwi r4, r4, 16`
(cross_f.rpx `0x0311EEC4`) and `0x0311EDC4` checks only label < the row's label count (no other limit; the label pool
is addressed by the row's 32-bit offset), so **a row holds at most 65536 labels** (ids `0xRRRR0000`-`0xRRRRFFFF`). A
plan past that is refused ("Row 0x768 is full: 65534 labels, room for 2 more ..."). Rows of 0x8000 and above would read
as voice sequences (0x8000xxxx): every row in use is below 3252. No tone-count limit was found in the bank loader (the
largest vanilla bank read, snd_se_joucyu, has 404 tones); not tried past a few hundred.

**Tones:** each new tone gets a new TONE entry, a copy of a one-shot of the same bank (its `_Special_L01` when it has
one, as `tools/fighter_own_bank.py`; else its first mono one-shot whose TONE tail is the standard one; a stereo sound
copies a stereo one-shot when the bank has one) with its name, PACK offset / size, volume and the tail's rate /
channels / samples / loop start / loop end / loop flag; its tone index is past every tone of the banks it goes into.
The audio is appended to PACK at a multiple of 0x10 (vanilla banks pack tones back to back at 0x10 boundaries) and
JUNK is sized (zeros) so PACK's body starts at a multiple of 0x10, as in every vanilla bank read (snd_se_Gekkouga,
snd_vc_Gekkouga, _ouen, snd_se_joucyu, snd_se_item, snd_se_Kirby, snd_se_SZerosuit); a bank with MARK after TONE
(vanilla snd_se_SZerosuit, Master's port) keeps it unchanged (it doesn't hold a tone count; TONE's count is the only
one in a bank: PROP, BINF, GRP and DTON are the same in every bank read).

**Costume banks:** a player in costume NN loads `snd_se_NAME_cNN` **instead of** the main bank (docs/native-notes.md
"Fighter sound banks") and plays the same ids from it (its own id aliased to the main's, or the main's id): the game
finds the row from the id, the label's tone index from the row, and takes that index **in the bank that player
loaded**. So a new label's tone index has to be the new sound in every bank on the row: **with "Also the costume banks
on this row" (on by default) the new tones go into the main bank and, at the same tone indexes, into each costume bank
of the same kind on the same row** (a bank with fewer tones is padded with vanilla's empty 12-byte slots first, so the
index is new in all of them). Off: the main bank only (the new ids are then silent in those costumes, or play whatever
tone a costume bank has at that index).

**Volume of existing tones:** the **Volume (dB)** column of the Fighter sounds tab is editable (yellow): type a value
(-40 .. +20) and the tone plays at it in the preview; the row is marked "volume +4.0 -> +1.5 dB (unsaved)". Saving
changes **only that 4-byte float** of the tone's TONE entry (checked byte for byte); a bank with only volume changes
keeps its layout as it was and the label table isn't written.

**Saving:** **Save** writes into the fighter's folder: the changed banks in `fighter/NAME/sound/`, and
`soundlabeltable.bin` where it was found when it is the mod's own (above the fighter's folder), else (it came from the
picked game data folder) as the mod's own, `DATA/sound/config/soundlabeltable.bin` next to `DATA/fighter` (the picked
one is never written). **Save to..** writes under a folder of your choice laid out as the game's data, ready to install:
`<folder>/fighter/NAME/sound/snd_se_NAME.nus3bank` (and the costume banks changed) and
`<folder>/sound/config/soundlabeltable.bin`; the viewer then shows that folder. **Every file replaced is backed up first
as `FILE.yyyyMMdd-HHmmss.bak`** next to it (the viewer doesn't list them: they don't end in .nus3bank). **Discard**
drops the unsaved changes; closing the viewer, Reload, Fighter.. or opening another fighter asks first.
Before writing, everything is built in memory and checked, and nothing is written if a check fails:
- the layout rules (`BankCheck.Validate`): `NUS3` + the size of the rest; `BANKTOC `, its size, the section count, each
  section's (name, size) as in its header; the sections back to back to the end, each at a multiple of 4, in vanilla's
  order (PROP BINF GRP DTON TONE [MARK] JUNK PACK); BINF; TONE's count, its (offset, size) table with the entries back
  to back, each a multiple of 4 bytes; every new tone's audio inside PACK at a multiple of 0x10, an IDSP whose size is
  its header's (0x40 + 0x60 x channels + channels x the data size, an even frame count), its TONE tail = its IDSP's
  rate / channels / samples / loop; JUNK zeros; PACK's body and size at multiples of 0x10;
- against the bank on disk (`BankCheck.CompareWithOriginal`): every section but TONE / JUNK / PACK byte for byte, the old
  TONE entries byte for byte (but the volume floats changed, and only those 4 bytes), the old PACK byte for byte at
  PACK's start, the tone count = the old one + the new;
- the table (`BankCheck.CompareTables`): the header and every other row byte for byte, the old label words in place,
  the row = its old labels + the new tones, no new id in use;
- the new tones read back from the bytes: name, channels, samples, loop, volume, and their audio = the encoded IDSP.
The written files are then read back (the bank's id, the table) and compared with what was built.

**Install:** copy what Save to.. wrote over the game's data (or your mod's `INSTALL_TO_data`): `fighter/NAME/sound/`
and `sound/config/soundlabeltable.bin`. The label table is one file for the whole game: if a mod of yours already ships
one, add the sounds with that one (open the mod's folder: its own table is used), or the other mod's rows are lost.

**Limits:** voice banks: a vc bank's `voiceanim_<Name>.vat` (mouth animations per voice) isn't extended (its count
isn't the row's label count: snd_vc_Gekkouga 38 labels, the .vat 41; a new voice gets no mouth animation); sounds are
48000 Hz, mono or stereo (more channels mixed down); one loop, the whole clip; the TONE entry's other fields (its group,
priority, 3D settings) are the template's; the Kirby-copy bank and a port's banks are handled as any bank with a row (their own, or
their alias'). Nothing here changes scripts: put the new ids in with Add to Script.

**Tested** (Mono; `python3 -I tools/Sm4shCommand/sound_viewer_test.py RUN_DIR FIGHTER_ROOT GAME_DATA PORT_ROOT OUT --mp3
creeper_explosion.mp3 --adder --gui`): 352 C# checks and 87 Python checks, 0 failures (part 1's 196 + 23 among them).
ffmpeg makes the inputs from the user's creeper_explosion.mp3 (44.1 kHz WAVs mono / stereo / 24-bit / float, a 22.05
kHz one, one padded with 0.5 s / 0.3 s of silence, an mp3, a flac, an ogg). Encoding: 44.1 kHz mono and stereo WAVs ->
48 kHz (frames x 48000 / 44100) -> IDSP (header, DSP header, sizes) -> decoded back: r 0.9998 against the PCM encoded;
the C# resampling against ffmpeg's r 1.00000 (44.1 and 22.05 kHz); the coefficients, ps and every ADPCM frame byte for
byte dspenc's; a looping one's header and loop ps; 24-bit / float WAVs within 1 LSB of the 16-bit one; the trim (0.800
s cut); mp3 / flac / ogg through ffmpeg (the flac sample for sample the wav), the message without ffmpeg. Adding 3 tones
(mono, stereo, a looping mp3) to the user's snd_se_Gekkouga (111 tones) and soundlabeltable row 0x768 (98 labels): ids
0x07680062 - 64 (in use nowhere in the table, nor on any port's alias row), labels 98 - 100, tones 111 - 113; written to
a folder: PROP / BINF / GRP / DTON, the 111 old TONE entries and the old PACK byte for byte, PACK at a multiple of 0x10
(the user's bank had it at +0x1C), BankCheck clean; the bank reloads and the tones decode; the table's other 3251 rows
and old label words byte for byte, the row = its 98 labels + 111, 112, 113; the viewer lists 0x07680062 - 64 with their
names and aliases; read with the repo's tools (fighter_own_bank.py's Table / binf, minecraft_sound.py's TONE reader,
fighter_sound.py's tone count) and the test's own decoder: tails, volumes, offsets, and each new tone against its source
clip (trimmed and resampled by ffmpeg) r 0.998 - 0.9998 at lag 0. In place: backups that are the originals, the mod's
table where it was; a table from the picked game data written as the mod's own (the picked one untouched); a new id's
alias replacing a stale line. A volume change: only its float differs (1 - 4 bytes), the table not written, set back /
discarded; a volume change and a new tone together. A full row (65534 labels: 3 refused, Build / Save refuse and
write nothing, 2 fit as 0x0768FFFE / FFFF); names in use / bad names refused. Costume banks: Master's port (se 46192
and se c01 46201, both on 2028's row through SoundBanks.txt): the tone in both at the same index, the same audio, the id
reaching it in both, both banks' ids kept, BankCheck clean (MARK kept); costume banks off: the main bank only. The layout
rules hold for vanilla snd_se_joucyu, snd_vc_Gekkouga and _ouen. The new ids' Sound_Effect / Transient_Sound_Effect /
Stop_Sound_Effect lines compile and round-trip. The form under Xvfb: the dialog filled (3 files, names prefilled,
the planned ids, a name / alias typed, loop ticked, the volume from the box and the slider, the preview WAV, the plan
line), the 3 pending rows in the list (marked, after IceBoom, found by name and by id, an alias typed kept until saved,
a looped preview, Add to Script with a new id), IceBoom's volume typed (marked unsaved), Save to a folder (the viewer
then shows it: the new sounds with their volumes and aliases, IceBoom at +1.5 dB). Pictures: `adder_dialog.png`,
`adder_pending.png`, `adder_saved.png`. `new_var_test.cs` 290 / 1 (the known effect.bin else-if count),
`hitbox_var_test.cs` 248 / 0. **Not run on Windows:** the Media Foundation decoding (MP3 / M4A ... without ffmpeg), the
file and folder pickers, hearing the preview (Windows' SoundPlayer), the backups / writes on a Windows file system; **not
tried in game:** the added tones (built by the rules the game's own banks and the in-game skeleton / IceBoom tones
follow, `tools/gekkouga_sound.py`), a stereo or looping added tone, a costume bank given tones, a row past ~400 labels.

## Events.cfg format

One block per command, blocks separated by a blank line; lines starting with `//` are comments:

```
B738EABD                     identifier (hex CRC32 of the command)
Hitbox                       name
0,0,0,1,...                  parameter types: 0 int, 1 float, 2 decimal, 3 variable (or NONE)
ID,Part,Bone,Damage,...      parameter names (or NONE)
Defines a hitbox ...         description, shown in tooltips (optional; NONE = none)
Category: Hitboxes           optional, the command's group in View > Commands
Param: KBG = Knockback growth   optional, one per parameter, shown when hovering that parameter
Example: Hitbox(ID=0, ...)   optional, one per line of a usage example (View > Commands);
                             the indentation after "Example: " is kept, "//" lines are comments
Help: text                   optional, one per line of help shown in View > Commands after the
                             parameters (not in tooltips); "Help:" alone is an empty line,
                             "Help: ## text" a heading, "Help: - text" a list line
```

A group's own help (shown when the group is picked in View > Commands) is a block of its own:

```
Group: New Commands / Inputs
Help: A fighter's controller: ...
```

A block with a problem is skipped and reported in the log at startup.

## Checked

- Run under Wine (wine-mono): opens a fighter folder, names and unlisted scripts in the tree, filter,
  editor with tooltips, Ctrl+click on CALL, edit + Ctrl+S saving in place (only the edited script
  changes), the compile-error dialog, Command Definitions (edit + save), Add Script (all four files +
  motion.mtable). Not run on Windows itself.
- SALT: every script of Kirby's game/sound/expression.bin and Captain Falcon's game.bin
  (2,000+ scripts) prints to text and compiles back to identical bytes. In effect.bin, 470 of 475 do; the
  other 5 are else-if chains that SALT writes as nested Else blocks (same behaviour, different offsets;
  unchanged from upstream).
- Events.cfg written by Tools > Command Definitions reads back with no errors.
- v1.4.10 (Mono, the same `new_var_test.cs`, counts updated): Events.cfg loads with no errors (620 commands, 36 with help); Gravity_Set's 4 examples (its `GRAVITY` alias included) compile and round-trip; everything below still passes (134 checks, 0 failures).
- v1.4.9 (Mono, `new_var_test.cs`): Events.cfg loads with no errors (619 commands, 9 group help blocks, 35 commands with
  help); New_Var's bytes, text and round trip; defaults, positional and numeric forms, a name used above its
  declaration and in another script, explicit / auto slots, all 64 slots, the errors (unknown name, an alias's or a
  command's name, too long, bad type / slot); aliases off (hex, compiles back); a preview compile (the Hitbox Viewer following the editor) leaves no half-typed names behind; names coming back from a saved file
  in a new session; Kirby's game / sound / expression scripts (1,651) still decompile and compile to the same bytes
  (effect.bin: the same 5 else-if chains as before); every new command's examples compile and round-trip. Under
  Xvfb (`new_var_gui_test.cs`, also referencing SM4SHCommand.exe and System.Windows.Forms / System.Drawing; `xvfb-run
  mono GuiTest.exe Events.cfg`): View > Commands' New_Var page (5 parameters, the declared names, the template) and
  the hover on a name. 130 + 9 checks, 0 failures. Build and run: `dotnet .../csc.dll -out:NvTest.exe -r:SALT.dll -r:/usr/lib/mono/4.5/mscorlib.dll
  -r:/usr/lib/mono/4.5/System.dll -r:/usr/lib/mono/4.5/System.Core.dll -nostdlib new_var_test.cs`, then
  `mono NvTest.exe Events.cfg Aliases FIGHTER/script/animcmd/body TMP_DIR` next to the built SALT.dll.
- v1.4.8 (Mono): Events.cfg loads with no errors (618 commands, 8 group help blocks, 34 commands with help); every
  new command's examples compile (names such as `VAR_0` / `SELF_DAMAGE` included) and come back the same after
  decompiling and compiling again; `SaveInfo` (Tools > Command Definitions' Save) writes the help, groups and
  examples back unchanged; View > Commands (Xvfb) shows New Commands first with its subgroups, the group
  overview and each command's help and examples.
- View > Commands (Mono under Xvfb): all 584 commands load in 20 groups, search and the parameter view
  work; Insert (Wine) adds the line under the caret with its indent, selects the first value, one undo.
- Tooltips (Wine): the old build left a tooltip over the next tab and over another window; now it's
  hidden on both, and still shown on hover.
- Hitbox Viewer textures: Mario's and Kirby's model.nut (BC1, BC3, RGBA8, GX2 2D-tiled) decode to their
  textures; LASTHIT_HITSTUN_MUL 1.5 typed into Kirby's AttackS4 gives 40 frames of hitstun instead of 27.
- Hitbox Viewer (Wine): Kirby's AttackS4 on his model and animation, hitboxes on frames 13-15 on the
  leg, following edits as typed; the calculator's result for it (16%, 361, KBG 102, BKB 30 on Mario at
  0%: 70.46 knockback, 27 hitstun) matches Sm4sh-Calculator.

Hitbox Viewer credits (MIT): the script timing, bone IDs and hitbox placement follow Smash Forge's
`ACMDScript.cs` and the model / texture reading (NUD materials, NUT, the GX2 deswizzle from `GTX.cs`, itself
from AboodXD's GTX Extractor) follow Smash Forge (https://github.com/jam1garner/Smash-Forge); the knockback / hitstun formulas and the
fighters' attributes (`Viewer/Fighters.txt`) are from Sm4sh-Calculator by rubendal
(https://github.com/rubendal/Sm4sh-Calculator).

`make_events_cfg.py` regenerates `Events.cfg` from SALT's table; `make_anim_names.py` regenerates
`AnimNames.txt` (this drops names added by Parse Animations / Set Name).
