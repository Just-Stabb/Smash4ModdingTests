// The Hitbox Viewer's effects (v1.5.0, Level 1; v1.6.0, Level 2: particles, models, trail textures), headless (Mono): the effect script run on the game script's timeline
// (HitboxRunner with SpeedSchedule), the effects it starts / ends, their names and lifetimes from the fighter's .efc /
// .ptcl (EffectLibrary), their place (Viewport.EffectMatrix), sword trails, flip IDs, colours, rates, the facing rule.
// Run through effect_viewer_test.py, which builds the fighter folders and the expected names / lifetimes (tools/efc.py,
// tools/ptcl.py). Build (next to the built SM4SHCommand.exe / SALT.dll): csc -out:EvTest.exe -r:SALT.dll
// -r:SM4SHCommand.exe -r:<mono 4.5>/mscorlib.dll -r:<mono 4.5>/System.dll -r:<mono 4.5>/System.Core.dll
// -r:<mono 4.5>/System.Windows.Forms.dll -r:<mono 4.5>/System.Drawing.dll -nostdlib effect_viewer_test.cs.
// Run: mono EvTest.exe Events.cfg FIGHTERS_DIR EXPECT.txt [EXPECT_FX.txt]
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;
using Sm4shCommand.Viewer;

class EvTest
{
    static int fails = 0, oks = 0;
    static readonly CultureInfo IC = CultureInfo.InvariantCulture;

    static void Check(string what, object got, object want)
    {
        bool ok = Equals(got, want);
        if (ok) oks++; else fails++;
        Console.WriteLine((ok ? "ok   " : "FAIL ") + what + (ok ? "" : string.Format(IC, ": got {0} (want {1})", got, want)));
    }

    static bool Near(float[] a, float[] b, float tol = 1e-3f)
    {
        return a != null && b != null && a.Length == b.Length && a.Zip(b, (x, y) => Math.Abs(x - y) <= tol).All(x => x);
    }

    static string V(float[] v) { return v == null ? "null" : string.Join(", ", v.Select(x => x.ToString("0.###", IC)).ToArray()); }

    static Dictionary<uint, Tuple<string, int>> expect = new Dictionary<uint, Tuple<string, int>>();

    static IList<ICommand> Script(string path, uint crc)
    {
        if (!File.Exists(path)) return null;
        var f = new ACMDFile(path);
        IScript s;
        return f.Scripts.TryGetValue(crc, out s) ? ((ACMDScript)s).Commands : null;
    }

    static IList<ICommand> Compile(string text)
    {
        var s = new ACMDScript(0x1234);
        s.Serialize(text);
        return s.Commands;
    }

    class Run
    {
        public List<FrameState> Game, Fx;
        public HitboxRunner FxRunner;
        public EffectLibrary Lib;
    }

    /// <summary>As the viewer does it (HitboxViewer.Rerun / RunEffects): the game script, then the effect script on its
    /// speeds, one-shot lifetimes from the library.</summary>
    static Run RunPair(IList<ICommand> game, IList<ICommand> fx, EffectLibrary lib, int frames = 300, bool conditions = true)
    {
        var r = new Run { Lib = lib };
        r.Game = new HitboxRunner().Run(game ?? new List<ICommand>(), frames);
        r.FxRunner = new HitboxRunner
        {
            ConditionsTrue = conditions,
            SpeedSchedule = r.Game.Select(x => x.Speed).ToArray(),
            OneShotLife = id =>
            {
                if (id == 0 || lib == null) return 0;
                var l = lib.Lifetime(id);
                return l.HasValue ? Math.Max(1, l.Value) : (lib.GetBank((int)(id >> 16)) != null ? -1 : 0);
            },
        };
        r.Fx = r.FxRunner.Run(fx, frames);
        return r;
    }

    /// <summary>The game frame FRAME(n) runs on: the first whose animation frame (+1) reaches n.</summary>
    static int FrameOf(List<FrameState> game, float n)
    {
        for (int i = 0; i < game.Count; i++)
            if (game[i].AnimFrame + 1 >= n - 0.001f) return i + 1;
        return -1;
    }

    /// <summary>An effect id played at (0, 5, 2), size 1.5, from game frame 1 (effect_viewer_test.py's fx_render runs).</summary>
    static EffectSim SimOf(EffectLibrary lib, uint id, bool follow = true)
    {
        var a = lib.AssetsFor(id);
        if (a == null) return null;
        return new EffectSim(new EffectData { Index = 0, Id = id, StartFrame = 1, Size = 1.5f, Follow = follow }, a, 1000000);
    }

    static Mat4 At052(int g) { return Mat4.TRS(new[] { 0f, 5f, 2f }, Mat4.EulerToQuat(0, 0, 0), new[] { 1f, 1f, 1f }); }

    static float[] WorldPos(EffectSim s, Particle q) { return q.Local ? s.Call.Transform(q.P[0], q.P[1], q.P[2]) : q.P; }

    static void Level2(string path, EffectLibrary lib, EffectLibrary kbLib, Run kirbyRun)
    {
        var lines = File.ReadAllLines(path).Select(l => l.Split('\t')).Where(p => p.Length >= 3).ToList();
        int frames = 30;
        // per id: each emitter's live count and first particle on frames 0 .. 29 (game frames 1 .. 30)
        var counts = new Dictionary<uint, List<int[]>>();
        var firsts = new Dictionary<uint, List<float[][]>>();
        foreach (uint id in lines.Where(p => p[0] == "count" || p[0] == "pos").Select(p => Convert.ToUInt32(p[1], 16)).Distinct())
        {
            var sim = SimOf(lib, id);
            if (sim == null) { Check("v1.6.0: 0x" + id.ToString("X") + "'s emitters found", false, true); continue; }
            var c = sim.Emitters.Select(x => new int[frames]).ToList();
            var f0 = sim.Emitters.Select(x => new float[frames][]).ToList();
            for (int t = 0; t < frames; t++)
            {
                sim.StepTo(1 + t, At052);
                for (int k = 0; k < sim.Emitters.Count; k++)
                {
                    c[k][t] = sim.Emitters[k].Live.Count;
                    f0[k][t] = sim.Emitters[k].Live.Count > 0 ? WorldPos(sim, sim.Emitters[k].Live[0]) : null;
                }
            }
            counts[id] = c;
            firsts[id] = f0;
        }
        foreach (var g in lines.Where(p => p[0] == "count").GroupBy(p => p[1]))
        {
            uint id = Convert.ToUInt32(g.Key, 16);
            if (!counts.ContainsKey(id)) continue;
            var bad = new List<string>();
            foreach (var p in g)
            {
                int k = int.Parse(p[2]);
                string got = k < counts[id].Count ? string.Join(" ", counts[id][k].Select(x => x.ToString()).ToArray()) : "none";
                if (got != p[3]) bad.Add("emitter " + k + ": " + got + " (fx_render " + p[3] + ")");
            }
            Check(string.Format("v1.6.0: 0x{0} ({1}): live particles on frames 0-{2} of its {3} emitters with no random life / gap (> 1) "
                                + "= tools/fx_render.py's simulate", g.Key.Substring(2), lib.Name(id), frames - 1, g.Count()),
                  string.Join("; ", bad.ToArray()), "");
        }
        foreach (var g in lines.Where(p => p[0] == "pos").GroupBy(p => p[1] + " " + p[2]))
        {
            var first = g.First();
            uint id = Convert.ToUInt32(first[1], 16);
            int k = int.Parse(first[2]);
            if (!firsts.ContainsKey(id)) continue;
            var bad = new List<string>();
            foreach (var p in g)
            {
                int t = int.Parse(p[3]);
                var want = p[4].Split(' ').Select(x => float.Parse(x, IC)).ToArray();
                var got = k < firsts[id].Count ? firsts[id][k][t] : null;
                if (!Near(got, want, 2e-3f)) bad.Add("frame " + t + ": " + V(got) + " (fx_render " + V(want) + ")");
            }
            Check(string.Format("v1.6.0: 0x{0} emitter {1}: its first particle's place on {2} frames (velocity, air, gravity; at "
                                + "(0, 5, 2), size 1.5) = fx_render's", first[1].Substring(2), k, g.Count()), string.Join("; ", bad.Take(3).ToArray()), "");
        }
        // the same frames again after stepping further: the fixed seeds give the same particles (scrubbing back)
        {
            uint id = 0x3410031;
            var s1 = SimOf(lib, id);
            var s2 = SimOf(lib, id);
            if (s1 != null)
            {
                s1.StepTo(12, At052);
                s2.StepTo(25, At052);
                s2.StepTo(12, At052);
                Func<EffectSim, string> dump = s => string.Join(";", s.Emitters.SelectMany(e => e.Live.Select(q => V(WorldPos(s, q)))).ToArray());
                Check("v1.6.0: fixed seeds: 0x3410031 stepped to 25 then back to 12 = stepped to 12 (every particle's place)", dump(s2) == dump(s1) && dump(s1).Length > 0, true);
            }
        }
        // textures: slot 0 through the model textures' decoder and comp_sel, as ptcl.py decode_texture
        foreach (var p in lines.Where(x => x[0] == "tex"))
        {
            uint id = Convert.ToUInt32(p[1], 16);
            var a = lib.AssetsFor(id);
            var t = a != null && a.Emitters.Count > 0 ? a.Emitters[0].Tex : null;
            var want = p[3].Split(' ');
            string got = t == null ? "none" : string.Format(IC, "{0} {1} {2:0.000} {3:0.000}", t.Width, t.Height,
                t.Argb.Average(c => (double)(c >> 16 & 255)), t.Argb.Average(c => (double)((uint)c >> 24)));
            bool ok = t != null && t.Width == int.Parse(want[0]) && t.Height == int.Parse(want[1]) &&
                      Math.Abs(t.Argb.Average(c => (double)(c >> 16 & 255)) - double.Parse(want[2], IC)) < 0.6 &&
                      Math.Abs(t.Argb.Average(c => (double)((uint)c >> 24)) - double.Parse(want[3], IC)) < 0.6;
            Check(string.Format("v1.6.0: 0x{0}'s first emitter's texture (size, mean red, mean alpha) = tools/ptcl.py decode_texture's", p[1].Substring(2)),
                  ok ? "ok" : got, ok ? "ok" : string.Join(" ", want));
        }
        // effect models: their frames, the MTA's colour gain, the model frame over time
        foreach (var p in lines.Where(x => x[0] == "model"))
        {
            uint id = Convert.ToUInt32(p[1], 16);
            var a = lib.AssetsFor(id);
            var m = a != null ? a.Model : null;
            Check(string.Format("v1.6.0: 0x{0}'s model: model.omo / model.mta frames", p[1].Substring(2)),
                  m != null ? (m.Anim != null ? m.Anim.Frames : -1) + " " + (m.Mta != null ? m.Mta.Frames : -1) : "none", p[2] + " " + p[3]);
            if (m == null || m.Mta == null) continue;
            var gain = m.Mta.Value(Convert.ToUInt32(p[4], 16), "NU_effColorGain", 10);
            Check(string.Format("v1.6.0: 0x{0}'s first material's NU_effColorGain on frame 10 = tools/mta.py's", p[1].Substring(2)),
                  V(gain), V(p[5].Split(' ').Select(x => float.Parse(x, IC)).ToArray()));
            var follow = SimOf(lib, id, true);
            var once = SimOf(lib, id, false);
            int n = m.Frames;
            Check(string.Format("v1.6.0: 0x{0}'s model frame {1} frames after its start: looped while it follows, held on its last "
                                + "for a one-shot", p[1].Substring(2), n + 3),
                  follow.ModelFrame(1 + n + 3) + " " + once.ModelFrame(1 + n + 3), 3 + " " + (n - 1));
            var p0 = m.Pose(0);
            var p5 = m.Pose(Math.Min(5, n - 1));
            bool moved = p0.Zip(p5, (x, y) => x.Zip(y, (u, v) => Math.Abs(u - v)).Max()).Max() > 1e-3;
            Check(string.Format("v1.6.0: 0x{0}'s model is posed by its model.omo (vertices move between frames 0 and 5)", p[1].Substring(2)),
                  moved || m.Anim == null, true);
        }
        foreach (uint id in new uint[] { 0x3410034 })
        {
            var l = lib.Lifetime(id);
            Check("v1.6.0: a model-only entry's one-shot life = its model's animation length (0x3410034)",
                  l.HasValue ? l.Value : -1, expect.ContainsKey(id) ? expect[id].Item2 : -2);
        }
        // trails: the texture ids and shader, the names table, the textures found next door
        var trail = kirbyRun.FxRunner.AllTrails.FirstOrDefault();
        Check("v1.6.0: BraveSword17's Sword_Glow textures 0x10A / 0x109, shader 3",
              trail != null ? string.Format("0x{0:X} 0x{1:X} {2}", trail.Texture1, trail.Texture2, trail.Shader) : "none", "0x10A 0x109 3");
        Check("v1.6.0: trail names: id 4 TexIkeSwordTrace (the game's table), 266 / 265 Hero's (trail_table_cave.py)",
              TrailNames.Name(4) + " " + TrailNames.Name(266) + " " + TrailNames.Name(265), "TexIkeSwordTrace TexBraveFireSwordTrace TexBraveSwordTraceAdd");
        var tt = kbLib.TrailTexture(0x10A);
        Check("v1.6.0: Kirby's trail texture 266 found in brave's effect/brave/trail (NTP3, DXT5)",
              tt != null ? tt.Width + "x" + tt.Height + " " + (tt.Argb.Any(c => (uint)c >> 24 < 10) && tt.Argb.Any(c => (uint)c >> 24 > 200)) : "none", "128x128 True");
        // the blending: add / alpha / subtract, the depth test
        {
            var pix = Enumerable.Repeat(unchecked((int)0xFF404040), 16).ToArray();
            var zb = Enumerable.Repeat(float.MaxValue, 16).ToArray();
            zb[15] = -1;     // in front: kept
            FxRaster.Tri(pix, zb, 4, 4, 0, 0, 0, 8, 0, 0, 0, 8, 0, null, null, false, 1, 0.5f, 0, 0.5f, null, null, FxRaster.Add);
            int add = pix[5];
            FxRaster.Tri(pix, zb, 4, 4, 0, 0, 0, 8, 0, 0, 0, 8, 0, null, null, false, 0, 0, 1, 0.5f, null, null, FxRaster.Alpha);
            Check("v1.6.0: blending: add 0x40 + (255, 128, 0) x 0.5, then alpha (0, 0, 255) at 0.5; the depth test keeps a nearer pixel",
                  string.Format("{0:X6} {1:X6} {2:X6}", add & 0xFFFFFF, pix[5] & 0xFFFFFF, pix[15] & 0xFFFFFF), "C08040 6040A0 404040");
        }
    }

    static int Main(string[] args)
    {
        var errors = new List<string>();
        ACMD_INFO.OverrideInfo(args[0], errors);
        string root = args[1];
        foreach (var line in File.ReadAllLines(args[2]))
        {
            var p = line.Split('\t');
            if (p.Length < 3) continue;
            expect[Convert.ToUInt32(p[0], 16)] = Tuple.Create(p[1], int.Parse(p[2]));
        }
        Sm4shCommand.Classes.Tooltips.Load();
        Func<uint, string> common = id =>
        {
            var e = Sm4shCommand.Classes.Tooltips.Find(id, "Graphic_Effect", "Graphic", "int").FirstOrDefault();
            return e != null ? e.Name : null;
        };

        // ---- Supamario: Super God Fist (attackdash) -----------------------------------------------------------------
        string sm = Path.Combine(root, "supamario");
        var smAssets = FighterAssets.Load(sm);
        var smLib = new EffectLibrary(sm) { CommonName = common };
        string smBody = Path.Combine(sm, "script", "animcmd", "body");
        uint dash = 0xAF93746E;
        var gf = RunPair(Script(Path.Combine(smBody, "game.bin"), dash), Script(Path.Combine(smBody, "effect.bin"), dash), smLib);
        var all = gf.FxRunner.AllEffects;
        Func<uint, EffectData> first = id => all.FirstOrDefault(e => e.Id == id);
        var fist = first(0x341002F);
        Check("God Fist: External_Graphic 0x341002F (FRAME 2) starts on the game frame FRAME(2) runs, follows",
              fist != null ? fist.StartFrame + " " + fist.Follow + " " + fist.Command : "none", FrameOf(gf.Game, 2) + " True External_Graphic");
        foreach (uint id in new uint[] { 0x341002F, 0x3410034, 0x3410056, 0x3410031, 0x341002C })
            Check(string.Format("God Fist: 0x{0:X}'s name (efc entry -> ptcl set; tools/efc.py + ptcl.py)", id), smLib.Name(id),
                  expect.ContainsKey(id) ? expect[id].Item1 : "?");
        var aura = first(0x3410034);
        Check("God Fist: 0x3410034 (FRAME 10) ends at FRAME 29's Terminate_Graphic_Effect (If conditions true)",
              aura != null ? aura.StartFrame + "-" + aura.EndFrame + " " + aura.EndReason : "none",
              FrameOf(gf.Game, 10) + "-" + FrameOf(gf.Game, 29) + " terminated (Terminate_Graphic_Effect)");
        var oneShot = first(0x341002C);
        int life = expect.ContainsKey(0x341002C) ? expect[0x341002C].Item2 : -2;
        Check("God Fist: one-shot 0x341002C lives its set's lifetime (tools/ptcl.py's emitters)",
              oneShot != null ? (oneShot.EndFrame - oneShot.StartFrame) + " " + oneShot.Follow : "none", life + " False");
        Check("God Fist: common 0x100008C's name from the tooltips (gfx.txt)", smLib.Name(0x100008C), common(0x100008C) ?? "(no tooltip)");
        // where: on its start frame, bone 0 (TransN) + (0, 6.826, 0.471)
        var anim = smAssets.GetAnimation(smAssets.AnimationFor(dash));
        Check("God Fist: its animation found", anim != null, true);
        var vp = new Viewport { Assets = smAssets, Animation = anim };
        float af = gf.Game[fist.StartFrame - 1].AnimFrame;
        vp.AnimFrame = af;
        var m = vp.EffectMatrix(fist);
        var tw = smAssets.Skeleton.World(anim, Math.Min(af, anim.Frames - 1))[smAssets.Skeleton.ScriptBone(0)].ClearScale();
        Check("God Fist: 0x341002F at TransN + (0, 6.83, 0.47) in TransN's frame",
              V(m != null ? m.Transform(0, 0, 0) : null), V(tw.Transform(fist.X, fist.Y, fist.Z)));
        var fr = gf.Fx[fist.StartFrame - 1];
        Check("God Fist: the frame it starts lists it (and not before)",
              fr.Effects.Any(e => e.Index == fist.Index) + " " + (fist.StartFrame > 1 && gf.Fx[fist.StartFrame - 2].Effects.Any(e => e.Index == fist.Index)),
              "True False");
        var bad = all.Where(e => FacingRule.Check(e).Length > 0 && e.Command == "External_Graphic").Select(e => "0x" + e.Id.ToString("X")).ToList();
        Check("God Fist: every External_Graphic keeps the facing rule (as supamario_corebreaker_test.py checks)", string.Join(",", bad.ToArray()), "");
        Check("Facing rule: bone 0 with a Z turn breaks it, Y 180 doesn't, a body bone offset does",
              (FacingRule.Check(new EffectData { RZ = 30 }).Length > 0) + " " + (FacingRule.Check(new EffectData { RY = 180, Y = 5, Z = 3 }) == "") +
              " " + (FacingRule.Check(new EffectData { Bone = 0x13, Y = 1 }).Length > 0), "True True True");

        // ---- Mario's vanilla moves (Supamario's base: Mario's scripts) ---------------------------------------------
        uint hi4 = 0xBF7EF5B8, throwb = 0xC94CD9B7;
        var up = RunPair(Script(Path.Combine(smBody, "game.bin"), hi4), Script(Path.Combine(smBody, "effect.bin"), hi4), smLib);
        var flipFx = up.FxRunner.AllEffects.FirstOrDefault(e => e.Command == "EFFECT_FLIP");
        Check("Mario up smash: EFFECT_FLIP 0x341000B, left 0x341000B, LAST_EFFECT_SET_RATE 0.8 on it, rotation -10 / -100 / -60",
              flipFx != null ? string.Format(IC, "0x{0:X} {1} 0x{2:X} {3} {4} {5} {6}", flipFx.Id, flipFx.HasLeft, flipFx.IdLeft, flipFx.Rate, flipFx.RX, flipFx.RY, flipFx.RZ) : "none",
              "0x341000B True 0x341000B 0.8 -10 -100 -60");
        Check("Mario up smash: 0x341000B ends at FRAME 15's Terminate, 0x341000D (External_Graphic, FRAME 9) too",
              string.Join(" ", up.FxRunner.AllEffects.Where(e => e.Id == 0x341000B || e.Id == 0x341000D).Select(e => e.StartFrame + "-" + e.EndFrame).ToArray()),
              FrameOf(up.Game, 9) + "-" + FrameOf(up.Game, 15) + " " + FrameOf(up.Game, 10) + "-" + FrameOf(up.Game, 15));
        Check("Mario up smash: 0x341000B's name", smLib.Name(0x341000B), expect.ContainsKey(0x341000B) ? expect[0x341000B].Item1 : "?");
        var tb = RunPair(Script(Path.Combine(smBody, "game.bin"), throwb), Script(Path.Combine(smBody, "effect.bin"), throwb), smLib);
        var col = tb.FxRunner.AllEffects.FirstOrDefault(e => e.Command == "EFFECT_FOLLOW_FLIP_COLOR");
        Check("Mario back throw: EFFECT_FOLLOW_FLIP_COLOR's colour 100 / 180 / 255, follows, bone 2",
              col != null ? string.Format(IC, "{0} {1} {2} {3} {4} {5}", col.HasColor, col.R, col.G, col.B, col.Follow, col.Bone) : "none",
              "True 100 180 255 True 2");
        var land = tb.FxRunner.AllEffects.FirstOrDefault(e => e.Command == "LANDING_EFFECT_FLIP");
        Check("Mario back throw: LANDING_EFFECT_FLIP right 0x100000D / left 0x100000E (IdFor(left))",
              land != null ? string.Format("0x{0:X} 0x{1:X}", land.IdFor(false), land.IdFor(true)) : "none", "0x100000D 0x100000E");

        // ---- Hero (a port over Robin: bank 0x32C in its own folder) ------------------------------------------------
        string hero = Path.Combine(root, "brave");
        var heroLib = new EffectLibrary(hero) { CommonName = common };
        string hb = Path.Combine(hero, "script", "animcmd", "body");
        uint lw = 0x971B322A;
        // (its effects are in an IS_FLAG ... False block: "If conditions true" off runs it)
        var hr = RunPair(Script(Path.Combine(hb, "game.bin"), lw), Script(Path.Combine(hb, "effect.bin"), lw), heroLib, 300, false);
        var hc = hr.FxRunner.AllEffects.FirstOrDefault(e => e.Command == "EFFECT_FOLLOW_COLOR");
        Check("Hero speciallwstart_c3: EFFECT_FOLLOW_COLOR 0x32C0025 106 / 50 / 255, LAST_EFFECT_SET_RATE 1.3",
              hc != null ? string.Format(IC, "0x{0:X} {1} {2} {3} {4}", hc.Id, hc.R, hc.G, hc.B, hc.Rate) : "none", "0x32C0025 106 50 255 1.3");
        foreach (uint id in new uint[] { 0x32C0025, 0x32C000F })
            Check(string.Format("Hero: 0x{0:X}'s name from brave's own bank (bank 0x32C, Robin's number)", id), heroLib.Name(id),
                  expect.ContainsKey(id) ? expect[id].Item1 : "?");

        // ---- Kirby's BraveSword17 (Hero's sword trail on LHaveN) -----------------------------------------------------
        string kb = Path.Combine(root, "kirby");
        var kbLib = new EffectLibrary(kb) { CommonName = common };
        string kbody = Path.Combine(kb, "script", "animcmd", "body");
        uint bs17 = 0x1CA81A01;
        var ks = RunPair(Script(Path.Combine(kbody, "game.bin"), bs17), Script(Path.Combine(kbody, "effect.bin"), bs17), kbLib);
        var trail = ks.FxRunner.AllTrails.FirstOrDefault();
        Check("BraveSword17: Sword_Glow's trail: LHaveN 0x18, (1.5, -0.2023, 0) to (14.4, -0.2023, 0), blur 7, FRAME 3 to FRAME 8 + fade 4",
              trail != null ? string.Format(IC, "0x{0:X} {1} {2} {3} / 0x{4:X} {5} {6} {7} {8} {9}-{10} {11}", trail.Bone1, trail.X1, trail.Y1, trail.Z1,
                  trail.Bone2, trail.X2, trail.Y2, trail.Z2, trail.Blur, trail.StartFrame, trail.EndFrame, trail.Fade) : "none",
              string.Format("0x18 1.5 -0.2023 0 / 0x18 14.4 -0.2023 0 7 {0}-{1} 4", FrameOf(ks.Game, 3), FrameOf(ks.Game, 8)));
        Check("BraveSword17: the trail on the frames from its start to its end + fade, not after",
              string.Join(",", ks.Fx.Where(f => f.Trails.Count > 0).Select(f => f.GameFrame.ToString()).ToArray()),
              string.Join(",", Enumerable.Range(FrameOf(ks.Game, 3), FrameOf(ks.Game, 8) + 4 - FrameOf(ks.Game, 3)).Select(x => x.ToString()).ToArray()));
        Check("BraveSword17: 0x3450078 named from the sibling brave folder (Hero's bank 0x345)", kbLib.Name(0x3450078),
              expect.ContainsKey(0x3450078) ? expect[0x3450078].Item1 : "?");

        // ---- v1.6.0 (Level 2): particles, textures, effect models, trail textures ------------------------------------
        if (args.Length > 3) Level2(args[3], smLib, kbLib, ks);

        // ---- the timeline: the game script's speed, threads, effect commands -----------------------------------------
        var g2 = Compile("FRAME(Frames=5)\nSet_Frame_Duration(Speed=2)\n");
        var f2 = Compile("FRAME(Frames=10)\nGraphic_Effect2(Graphic=0x1000001, Bone=0, X=0, Y=1, Z=2, XRot=0, YRot=0, ZRot=0, Size=1, " +
                         "RandomX=0, RandomY=0, RandomZ=0, RandomXRot=0, RandomYRot=0, RandomZRot=0, Terminate=1)\nLAST_EFFECT_SET_COLOR(Red=1, Green=0.5, Blue=0)\n" +
                         "LAST_EFFECT_SET_ALPHA(Alpha=0.25)\nExternal_Graphic(Graphic=0x1000002, Bone=0, X=0, Y=0, Z=0, XRot=0, YRot=0, ZRot=0, Size=2, Terminate=1)\n" +
                         "Set_Frame_Duration(Speed=10)\nFRAME(Frames=12)\nEFFECT_DETACH_KIND(Graphic=0x1000002, EndFadeFrames=0)\nFRAME(Frames=40)\n" +
                         "EFFECT_OFF(AttrMask=0, KillParticles=1)\n");
        var t = RunPair(g2, f2, null);
        var e1 = t.FxRunner.AllEffects.FirstOrDefault(e => e.Id == 0x1000001);
        var e2 = t.FxRunner.AllEffects.FirstOrDefault(e => e.Id == 0x1000002);
        // game: frames 1-4 at speed 1 (FRAME 5 on game frame 5), then half speed: anim frame n (> 5) on 5 + 2 (n - 5)
        Check("timeline: the game script's Set_Frame_Duration(2) slows the effect script (FRAME 10 on game frame 15; its own "
              + "Set_Frame_Duration ignored)", e1 != null ? e1.StartFrame : -1, FrameOf(t.Game, 10));
        Check("timeline: FRAME(10) = game frame 15", FrameOf(t.Game, 10), 15);
        Check("LAST_EFFECT_SET_COLOR / _ALPHA on the last effect", e1 != null ? string.Format(IC, "{0} {1} {2} {3}", e1.R, e1.G, e1.B, e1.A) : "none", "1 0.5 0 0.25");
        Check("one-shot with no files: the default 20 frames", e1 != null ? e1.EndFrame - e1.StartFrame : -1, 20);
        Check("EFFECT_DETACH_KIND: the follow effect stays where it was from FRAME 12, and goes on its one-shot life",
              e2 != null ? e2.DetachFrame + " " + (e2.EndFrame - e2.DetachFrame) : "none", FrameOf(t.Game, 12) + " 20");
        var g3 = Compile("FRAME(Frames=1)\n");
        var f3 = Compile("Thread_Start(Offset=0, ID=1, Flags=0){\n    FRAME(Frames=3)\n    External_Graphic(Graphic=0x1000003, Bone=0, X=0, Y=0, Z=0, XRot=0, YRot=0, ZRot=0, Size=1, Terminate=1)\n}\n" +
                         "FRAME(Frames=8)\nEFFECT_OFF(AttrMask=0, KillParticles=1)\nColor_Overlay(Red=1, Green=1, Blue=1, Alpha=0.5)\n");
        var t3 = RunPair(g3, f3, null);
        var e3 = t3.FxRunner.AllEffects.FirstOrDefault(e => e.Id == 0x1000003);
        Check("a thread's effect (its FRAME counted from the thread's start), ended by the script's EFFECT_OFF",
              e3 != null ? e3.StartFrame + "-" + e3.EndFrame + " " + e3.EndReason : "none", "5-8 terminated (EFFECT_OFF)");
        Check("Color_Overlay listed as a screen event on its frame", string.Join(";", t3.Fx[7].Screen.Select(x => x.Text.Split('(')[0]).ToArray()), "Color_Overlay");

        Console.WriteLine("{0} ok, {1} failures", oks, fails);
        return fails > 0 ? 1 : 0;
    }
}
