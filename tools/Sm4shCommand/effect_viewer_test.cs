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
using Sm4shCommand;

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

    static readonly Dictionary<string, ACMDFile> files = new Dictionary<string, ACMDFile>();
    static IList<ICommand> Script(string path, uint crc)
    {
        if (!File.Exists(path)) return null;
        ACMDFile f;
        if (!files.TryGetValue(path, out f)) files[path] = f = new ACMDFile(path);   // (SALT maps a file once)
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
                    f0[k][t] = sim.Emitters[k].Live.Count > 0 ? sim.Emitters[k].World(sim.Emitters[k].Live[0]) : null;
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
                Func<EffectSim, string> dump = s => string.Join(";", s.Emitters.SelectMany(e => e.Live.Select(q => V(e.World(q)))).ToArray());
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

    /// <summary>v1.6.1: LAST_EFFECT_SET_RATE (and a spawn's own Rate) speeds an effect's particles, model and life up.</summary>
    static void Rates(EffectLibrary lib, Func<uint, string> common)
    {
        Check("v1.6.1: a rated effect's life: 20 frames at rate 2 = 10, at 0.5 = 40, at 1.5 = 14 (ceil), at 1 = 20",
              HitboxRunner.RatedLife(20, 2) + " " + HitboxRunner.RatedLife(20, 0.5f) + " " + HitboxRunner.RatedLife(20, 1.5f) + " " + HitboxRunner.RatedLife(20, 1),
              "10 40 14 20");
        // the God Fist's one-shot hit (0x341002C, its set's life 19 from expect.txt) at rates 2 and 0.5
        var g = Compile("FRAME(Frames=1)\n");
        var f = Compile("FRAME(Frames=1)\nGraphic_Effect(Graphic=0x341002C, Bone=0, X=0, Y=5, Z=0, XRot=0, YRot=0, ZRot=0, Size=1, RandomX=0, " +
                        "RandomY=0, RandomZ=0, RandomXRot=0, RandomYRot=0, RandomZRot=0, Terminate=1)\nLAST_EFFECT_SET_RATE(Rate=2)\n" +
                        "Graphic_Effect(Graphic=0x341002C, Bone=0, X=0, Y=5, Z=0, XRot=0, YRot=0, ZRot=0, Size=1, RandomX=0, " +
                        "RandomY=0, RandomZ=0, RandomXRot=0, RandomYRot=0, RandomZRot=0, Terminate=1)\nLAST_EFFECT_SET_RATE(Rate=0.5)\n" +
                        "Graphic_Effect(Graphic=0x341002C, Bone=0, X=0, Y=5, Z=0, XRot=0, YRot=0, ZRot=0, Size=1, RandomX=0, " +
                        "RandomY=0, RandomZ=0, RandomXRot=0, RandomYRot=0, RandomZRot=0, Terminate=1)\n");
        var r = RunPair(g, f, lib, 120);
        int life = expect.ContainsKey(0x341002C) ? expect[0x341002C].Item2 : -2;
        Check("v1.6.1: LAST_EFFECT_SET_RATE 2 / 0.5 / none on three 0x341002C: they play life / 2, life x 2, life game frames (life " + life + ")",
              string.Join(" ", r.FxRunner.AllEffects.Select(e => (e.EndFrame - e.StartFrame) + "@" + e.Rate.ToString(IC)).ToArray()),
              string.Format(IC, "{1}@2 {2}@0.5 {0}@1", life, HitboxRunner.RatedLife(life, 2), HitboxRunner.RatedLife(life, 0.5f)));
        var f2 = Compile("FRAME(Frames=1)\nEFFECT_FLW_POS_STRENGTH(Effect=0x341002C, Bone=0, X=0, Y=0, Z=0, RotX=0, RotY=0, RotZ=0, Scale=1, " +
                         "Strength=1, Terminate=1, Rate=1.5)\n");
        var r2 = RunPair(g, f2, lib, 60);
        var e2 = r2.FxRunner.AllEffects.FirstOrDefault();
        Check("v1.6.1: EFFECT_FLW_POS_STRENGTH's own Rate is the effect's rate", e2 != null ? e2.Rate.ToString(IC) : "none", "1.5");
        // the particles: at rate 2, game frame 1 + t is the effect's frame 2t; at 0.5, 1 + 2t is its frame t
        Func<float, EffectSim> sim = rate =>
        {
            var a = lib.AssetsFor(0x3410031);
            return new EffectSim(new EffectData { Index = 0, Id = 0x3410031, StartFrame = 1, Size = 1.5f, Follow = true, Rate = rate }, a, 1000000);
        };
        Func<EffectSim, string> dump = s => string.Join(";", s.Emitters.Select(e => e.Live.Count + ":" +
            string.Join(",", e.Live.Select(q => V(e.World(q))).ToArray())).ToArray());
        var one = sim(1); var two = sim(2); var half = sim(0.5f);
        var bad = new List<string>();
        for (int t = 0; t <= 14; t++)
        {
            one.StepTo(1 + 2 * t, At052); two.StepTo(1 + t, At052);
            if (dump(one) != dump(two)) bad.Add("rate 2, frame " + t);
        }
        one = sim(1);
        for (int t = 0; t <= 14; t++)
        {
            one.StepTo(1 + t, At052); half.StepTo(1 + 2 * t, At052);
            if (dump(one) != dump(half)) bad.Add("rate 0.5, frame " + 2 * t);
        }
        half.StepTo(2 + 2 * 14, At052);
        Check("v1.6.1: 0x3410031 at rate 2 on game frame 1 + t = at rate 1 on 1 + 2t (every particle), at 0.5 on 1 + 2t = at 1 on 1 + t; "
              + "halfway between, drawn half a step on", string.Join(", ", bad.ToArray()) + " frac " + half.Frac.ToString(IC), " frac 0.5");
        var m = sim(0.5f);
        var model = lib.AssetsFor(0x3410034);
        var ms = new EffectSim(new EffectData { Index = 0, Id = 0x3410034, StartFrame = 1, Size = 1, Follow = true, Rate = 0.5f }, model, 1000);
        var ms2 = new EffectSim(new EffectData { Index = 0, Id = 0x3410034, StartFrame = 1, Size = 1, Follow = true, Rate = 2 }, model, 1000);
        int n = model != null && model.Model != null ? model.Model.Frames : 0;
        Check("v1.6.1: the aura model's frame at rate 0.5 / 2, 11 game frames on (looped at its " + n + " frames)",
              ms.ModelFrame(12).ToString(IC) + " " + ms2.ModelFrame(12).ToString(IC), "5.5 " + (22 % Math.Max(1, n)).ToString(IC));
    }

    /// <summary>v1.6.1: the common bank (0x0100nnnn) from the game's data/effect/common above the fighter's folder
    /// (effect_viewer_test.py puts a stand-in there: Supamario's bank under the common name).</summary>
    static void Common(string fighters, string sm, Func<uint, string> common, bool standIn = true)
    {
        string want = Path.Combine(Path.Combine(Path.GetDirectoryName(fighters), "effect"), "common");
        string found = EffectLibrary.FindCommonFolder(sm);
        Check("v1.6.1: the common bank found where the game keeps it: data/effect/common next to data/fighter", found, want);
        Check("v1.6.1: a picked folder may be data, data/effect or data/effect/common",
              EffectLibrary.CommonFolderIn(Path.GetDirectoryName(fighters)) + "|" + EffectLibrary.CommonFolderIn(Path.Combine(Path.GetDirectoryName(fighters), "effect")) +
              "|" + EffectLibrary.CommonFolderIn(want) + "|" + (EffectLibrary.CommonFolderIn(sm) ?? "null"), want + "|" + want + "|" + want + "|null");
        var lib = new EffectLibrary(sm) { CommonName = common, CommonFolder = found };
        var plain = new EffectLibrary(sm) { CommonName = common };
        Check("v1.6.1: without the bank, common effects stay markers (no assets) and their tooltip names",
              (plain.AssetsFor(0x1000031) == null) + " " + plain.Name(0x1000011), "True " + (common(0x1000011) ?? ""));
        // (v1.7.1: with the game's own bank given, its entries are checked by RealCommon; these need the stand-in's)
        if (!standIn) return;
        var a = lib.AssetsFor(0x1000031);
        var b = lib.AssetsFor(0x3410031);
        Check("v1.6.1: common 0x1000031's emitters / model from the common bank (the stand-in: Supamario's entry 0x31)",
              a != null ? a.SetName + " " + a.Emitters.Count : "none", b != null ? b.SetName + " " + b.Emitters.Count : "?");
        var am = lib.AssetsFor(0x1000034);
        Check("v1.6.1: common 0x1000034's effect model from the common bank's model folder", am != null && am.Model != null ? am.Model.Name : "none", "EffSupamarioGfCsgBas");
        string tip = common(0x1000031);
        Check("v1.6.1: a common effect's name: its tooltip name (the bank's set after it)", lib.Name(0x1000031),
              tip != null ? tip + " (PtcSupamarioGfCsg_Circle)" : "PtcSupamarioGfCsg_Circle");
        Check("v1.6.1: a common one-shot's life from its set (as the fighter's)", lib.Lifetime(0x1000031).ToString(), lib.Lifetime(0x3410031).ToString());
        var s1 = new EffectSim(new EffectData { Index = 0, Id = 0x1000031, StartFrame = 1, Size = 1.5f }, a, 100000);
        var s2 = new EffectSim(new EffectData { Index = 0, Id = 0x3410031, StartFrame = 1, Size = 1.5f }, b, 100000);
        s1.StepTo(12, At052); s2.StepTo(12, At052);
        Check("v1.6.1: the common effect's particles drawn as the fighter's (live on frame 12)", s1.ParticleCount + " " + (s1.ParticleCount > 0), s2.ParticleCount + " True");
    }

    /// <summary>v1.6.1: the game and effect scripts found and followed by one rule (ViewerScripts, HitboxViewer.ScriptCommands).</summary>
    static void Sources(FighterAssets assets, string body, uint crc)
    {
        string tmp = Path.Combine(Path.GetTempPath(), "evtest_src_" + System.Diagnostics.Process.GetCurrentProcess().Id);
        Directory.CreateDirectory(tmp);
        foreach (var k in new[] { "game", "effect" }) File.Copy(Path.Combine(body, k + ".bin"), Path.Combine(tmp, k + ".bin"), true);
        // only effect.bin open (single-file mode): the folder is its, the game script from game.bin there
        var fx = new ACMDFile(Path.Combine(tmp, "effect.bin"));
        var openList = new List<KeyValuePair<string, IScriptCollection>> { new KeyValuePair<string, IScriptCollection>(Path.Combine(tmp, "effect.bin"), fx) };
        string folder = ViewerScripts.FolderFor(openList);
        var src = new ViewerScripts(folder, () => openList);
        var gameDisk = src.File("game");
        Check("v1.6.1: effect.bin open alone: its folder; effect = the open file, game = game.bin next to it (read from disk)",
              (folder == tmp) + " " + ReferenceEquals(src.File("effect"), fx) + " " + (gameDisk != null && gameDisk.Scripts.ContainsKey(crc)), "True True True");
        File.SetLastWriteTimeUtc(Path.Combine(tmp, "game.bin"), DateTime.UtcNow.AddMinutes(1));
        var again = src.File("game");
        Check("v1.6.1: a file on disk is read again when it changes (saved from elsewhere)",
              again != null && !ReferenceEquals(again, gameDisk) && again.Scripts.ContainsKey(crc), true);
        // the tab's editors (FastColoredTextBox doesn't load on Mono: the rule picking the sub-tab is checked)
        Check("v1.6.1: single-file effect.bin: its one editor (\"Script\") is the effect editor, not the game script's",
              ViewerScripts.EditorTab(new[] { "Script" }, "effect", "effect") + " " + (ViewerScripts.EditorTab(new[] { "Script" }, "game", "effect") ?? "none"), "Script none");
        Check("v1.6.1: single-file game.bin: its one editor is the game editor; fighter mode: the game / effect sub-tabs",
              ViewerScripts.EditorTab(new[] { "Script" }, "game", "game") + " " + (ViewerScripts.EditorTab(new[] { "Script" }, "effect", "game") ?? "none") + " " +
              ViewerScripts.EditorTab(new[] { "game", "effect", "sound", "expression" }, "effect", null) + " " +
              ViewerScripts.EditorTab(new[] { "game", "effect", "sound", "expression" }, "game", null), "Script none effect game");
        // the one rule for both scripts (HitboxViewer.PickCommands): the tab's editor text while its animation is shown,
        // compiled; an error falls back to the saved one; another animation: its saved script
        var gameScript = (ACMDScript)gameDisk.Scripts[crc];
        var fxScript = (ACMDScript)fx.Scripts[crc];
        Func<uint, IList<ICommand>> savedFx = src.Getter("effect");
        var text = fxScript.Deserialize().Split('\n').ToList();
        string err;
        var got = Sm4shCommand.GUI.HitboxViewer.PickCommands(crc, crc, savedFx, () => text, out err);
        Check("v1.6.1: the tab's effect text, compiled (as the game script's)", (got != null && got.Count == fxScript.Commands.Count) + " " + (err == null), "True True");
        var edited = text.Concat(new[] { "FRAME(Frames=40)", "EFFECT_OFF(AttrMask=0, KillParticles=1)" }).ToList();
        got = Sm4shCommand.GUI.HitboxViewer.PickCommands(crc, crc, savedFx, () => edited, out err);
        Check("v1.6.1: an edit is run (2 more commands)", got != null ? got.Count : -1, fxScript.Commands.Count + 2);
        var broken = text.Concat(new[] { "NOT_A_COMMAND(" }).ToList();
        got = Sm4shCommand.GUI.HitboxViewer.PickCommands(crc, crc, savedFx, () => broken, out err);
        Check("v1.6.1: a script that doesn't compile: the saved one, and the error", (got != null && got.Count == fxScript.Commands.Count) + " " + (err != null), "True True");
        uint other = fx.Scripts.Keys.First(k => k != crc && ((ACMDScript)fx.Scripts[k]).Commands.Count > 0);
        got = Sm4shCommand.GUI.HitboxViewer.PickCommands(other, crc, savedFx, () => edited, out err);
        Check("v1.6.1: another animation picked in the viewer: its saved effect script (the tab's edits are the tab's only)",
              got != null && got.Count == ((ACMDScript)fx.Scripts[other]).Commands.Count, true);
        got = Sm4shCommand.GUI.HitboxViewer.PickCommands(crc, crc, src.Getter("game"), null, out err);
        Check("v1.6.1: no game editor (effect.bin open alone): the game script from game.bin next to it (its commands)",
              got != null ? got.Count : -1, gameScript.Commands.Count);
        try { Directory.Delete(tmp, true); } catch (Exception) { }
    }

    /// <summary>v1.6.2: the model's visibility animations (material_anime_*.pac) = tools/mta.py's reading; the parts'
    /// priority (your choice > a VisGroups group > the visibility animation > the name rule); the script's visibility
    /// commands on the timeline.</summary>
    static void Visibility(string path, FighterAssets a)
    {
        var lines = File.ReadAllLines(path).Select(l => l.Split('\t')).Where(p => p[0] == "vis").ToList();
        var bad = new List<string>();
        foreach (var p in lines)
        {
            var at = a.MaterialVis.At(p[1] + ".omo", int.Parse(p[2]));
            bool got;
            if (!at.TryGetValue(p[3], out got) || got != (p[4] == "1")) bad.Add(p[2] + " " + p[3]);
        }
        Check("v1.6.2: Mario's DamageHi1 face meshes on frames 0 / 3 / 11 (" + lines.Count + " tracks x frames) = tools/mta.py's reading of "
              + "material_anime_face / eye / eyelid.pac", string.Join(", ", bad.ToArray()), "");
        var groups = new VisGroups();
        groups.AddLine(a.Name + " 0 1: Mario_Hathead");
        groups.AddLine(a.Name + " 0 2: Mario_Nohat");
        groups.AddLine(a.Name + " 0 default: 1");
        var vis = new VisState();
        var user = new Dictionary<string, bool>();
        ModelParts.Apply(a, "FitMarioBodyMainF00DamageHi1.omo", 3, vis, groups, user);
        Func<string, string> st = n => { var m = a.Model.Meshes.First(x => x.Name.StartsWith(n)); return (m.Visible ? "on" : "off") + "/" + m.Why; };
        Check("v1.6.2: a visibility group's default (VisGroups) decides its meshes; the visibility animation the others (Ouch on frame 3)",
              st("Mario_Hathead") + " " + st("Mario_Nohat") + " " + st("Mario_Ouch_"), "on/group 0 default 1 off/group 0 default 1 on/visibility animation (material_anime)");
        vis.Groups[0] = 2;
        ModelParts.Apply(a, "FitMarioBodyMainF00DamageHi1.omo", 3, vis, groups, user);
        // (v1.6.3: a group's current state leaves its meshes to the motion's visibility animation where it has a track:
        // Pac-Man's group lists his face meshes with the body; Mario's DamageHi1 animates Mario_Nohat off)
        Check("v1.6.2: Model_Changer(0, 2) switches the group's meshes (v1.6.3: Mario_Nohat then as its visibility animation)",
              st("Mario_Hathead") + " " + st("Mario_Nohat"), "off/group 0 state 2 (script) off/visibility animation (material_anime)");
        user[a.Model.Meshes.First(x => x.Name.StartsWith("Mario_Nohat")).Name] = false;
        ModelParts.Apply(a, "FitMarioBodyMainF00DamageHi1.omo", 3, vis, groups, user);
        Check("v1.6.2: the parts tab's choice wins", st("Mario_Nohat"), "off/your choice (now)");
        ModelParts.Apply(a, "FitMarioBodyMainF00DamageHi1.omo", 3, new VisState(), null, null);
        // the script's visibility commands on the timeline (the game / expression scripts)
        var g = Compile("FRAME(Frames=1)\n");
        var x = Compile("FRAME(Frames=2)\nModel_Changer(ChangerID=0, ChangerState=2)\nFRAME(Frames=5)\nVIS_SET_DEFAULT(Group=1, State=3)\n" +
                        "FRAME(Frames=8)\nVIS_BACK_DEFAULT(Group=0)\nModel_Changer(ChangerID=1, ChangerState=0)\nFRAME(Frames=10)\nVIS_BACK_DEFAULT(Group=1)\n" +
                        "Visibility(State=0)\nFRAME(Frames=12)\nVIS_RESET_DEFAULT(Group=1)\nVisibility(State=1)\n");
        var r = RunPair(g, x, null, 20);
        Func<int, string> vs = fr => { var v = r.Fx[fr - 1].Vis; return string.Join(",", v.Groups.OrderBy(k => k.Key).Select(k => k.Key + "=" + k.Value).ToArray()) + (v.Whole == false ? " hidden" : ""); };
        Check("v1.6.2: Model_Changer / VIS_SET_DEFAULT / VIS_BACK_DEFAULT / Visibility / VIS_RESET_DEFAULT on frames 1, 2, 5, 8, 10, 12",
              vs(1) + "|" + vs(2) + "|" + vs(5) + "|" + vs(8) + "|" + vs(10) + "|" + vs(12), "|0=2|0=2,1=3|1=0|1=3 hidden|");
        var merged = VisState.Merge(r.Fx[7].Vis, new VisState { Groups = { { 1, 7 } }, Changed = { { 1, 9 } } });
        Check("v1.6.2: two scripts' visibility merged: per group the later change", merged.Groups[1], 7);
    }

    /// <summary>v1.6.2: effect colours and alphas as the game applies them; the body overlays.</summary>
    static void Colours()
    {
        var g = Compile("FRAME(Frames=1)\n");
        var f = Compile("FRAME(Frames=1)\nEFFECT_FOLLOW_FLIP_COLOR(GFXRight=0x1000001, GFXLeft=0x1000001, Bone=0, X=0, Y=0, Z=0, XRot=0, YRot=0, ZRot=0, " +
                        "Size=1, Terminate=1, FlipType=1, Red=100, Green=180, Blue=510)\nLAST_EFFECT_SET_ALPHA(Alpha=50)\nLAST_PARTICLE_SET_COLOR(R=0.5, G=1, B=1)\n" +
                        "Graphic_Effect6(Graphic=0x1000002, Bone=0, X=0, Y=0, Z=0, XRot=0, YRot=0, ZRot=0, Size=1, Terminate=1, Alpha=70)\n" +
                        "LAST_EFFECT_SET_COLOR(Red=255, Green=0, Blue=51)\n" +
                        "EFFECT_LIGHT(Graphic=0x1000003, Bone=0, X=0, Y=0, Z=0, XRot=0, YRot=0, ZRot=0, Size=1, RandomX=0, RandomY=0, RandomZ=0, RandomXRot=0, " +
                        "RandomYRot=0, RandomZRot=0, Terminate=1, Red=120, Green=80, Blue=180, LightIntensity=1, LightX=0, LightY=0, LightZ=0)\n" +
                        "FRAME(Frames=2)\nColor_Overlay(Red=255, Green=0, Blue=0, Alpha=128)\nFRAME(Frames=6)\nChange_Overlay(Transition=4, Red=0, Green=0, Blue=255, Alpha=255)\n" +
                        "FRAME(Frames=12)\nTerminate_Overlays()\n");
        var r = RunPair(g, f, null, 20);
        Func<EffectData, string> c = e => { float rr, gg, bb, aa; Viewport.CallColour(e, out rr, out gg, out bb, out aa); return string.Format(IC, "{0:0.###} {1:0.###} {2:0.###} {3:0.###}", rr, gg, bb, aa); };
        var all = r.FxRunner.AllEffects;
        Check("v1.6.2: colours / 255 (510 = 2), alpha percent / 100, LAST_PARTICLE_SET_COLOR multiplies; Graphic_Effect6's Alpha 70 %; "
              + "LAST_EFFECT_SET_COLOR / 255; EFFECT_LIGHT's colour is its light's (not the effect's)",
              string.Join(" | ", all.Select(c).ToArray()), "0.196 0.706 2 0.5 | 1 0 0.2 0.7 | 1 1 1 1");
        Func<int, string> ov = fr => { var o = r.Fx[fr - 1].Overlay; return o == null ? "none" : string.Format(IC, "{0:0.##} {1:0.##} {2:0.##} {3:0.##}", o[0], o[1], o[2], o[3]); };
        Check("v1.6.2: Color_Overlay at 2, Change_Overlay over 4 frames from 6 (halfway on 8), Terminate_Overlays at 12",
              ov(1) + " | " + ov(2) + " | " + ov(8) + " | " + ov(10) + " | " + ov(12), "none | 1 0 0 0.5 | 0.5 0 0.5 0.75 | 0 0 1 1 | none");
    }

    /// <summary>v1.6.2: the swoosh arcs (follow-0 emitters whose rotation is key-animated: Mario's up smash 0x341000B, the
    /// same make as the common forward-air arc) follow the emitter's live rotation, and come out mirrored for the other
    /// facing; billboards aren't mirrored.</summary>
    static void Arcs(FighterAssets a, EffectLibrary lib, string body)
    {
        uint hi4 = 0xBF7EF5B8;
        var up = RunPair(Script(Path.Combine(body, "game.bin"), hi4), Script(Path.Combine(body, "effect.bin"), hi4), lib);
        var arc = up.FxRunner.AllEffects.First(e => e.Id == 0x341000B);
        var anim = a.GetAnimation(a.AnimationFor(hi4));
        var vp = new Viewport { Assets = a, Animation = anim, Width = 800, Height = 600, History = up.Game, GetEffectAssets = lib.AssetsFor };
        Func<int, bool, List<Tuple<float[], float[]>>> quads = (gf, flip) =>
        {
            vp.Flip = flip;
            vp.ResetEffects();
            vp.AnimFrame = up.Game[gf - 1].AnimFrame;
            vp.Frame = up.Fx[gf - 1];
            var e = up.Fx[gf - 1].Effects.First(x => x.Index == arc.Index);
            return vp.EffectScreenQuads(e, gf);
        };
        int f2 = Math.Min(arc.StartFrame + 6, arc.EndFrame - 1);
        // the live emitter matrix: on f2 the swoosh's emitter (line1_b) has turned by its Y key; a particle born before
        // sits where the turned emitter puts it
        var sim = vp.SimFor(up.Fx[f2 - 1].Effects.First(x => x.Index == arc.Index), f2);
        var es = sim.Emitters[2];
        var want = sim.Call * es.D.Matrix(sim.NextK - 1);
        Check("v1.6.2: a following particle is placed by the call x the emitter's matrix of the frame shown (its key-animated Y turn)",
              es.Live.Count > 0 && Near(es.World(es.Live[0]), want.Transform(es.Live[0].P[0], es.Live[0].P[1], es.Live[0].P[2])) && es.Live[0].Local, true);
        Func<List<Tuple<float[], float[]>>, float> cxOf = l => l.Count == 0 ? float.NaN : l.Average(t => (t.Item1[0] + t.Item1[3] + t.Item1[6]) / 3);
        var origin = vp.ScreenOf(new[] { 0f, 0f, 0f });
        vp.Flip = true;
        var originL = vp.ScreenOf(new[] { 0f, 0f, 0f });
        float r1 = cxOf(quads(f2, false)) - origin[0], l1 = cxOf(quads(f2, true)) - originL[0];
        Check(string.Format(IC, "v1.6.2: Mario's up smash swoosh {0} frames in: facing right {1:0} px from him, facing left {2:0} (mirrored)", f2 - arc.StartFrame, r1, l1),
              !float.IsNaN(r1) && Math.Abs(r1 + l1) < 1.5f, true);
        // a camera billboard's texture runs left to right on screen (u 0 -> 1) in both facings (v1.6.0 had it mirrored)
        var bb = Compile("FRAME(Frames=1)\nGraphic_Effect(Graphic=0x341002C, Bone=0, X=0, Y=8, Z=0, XRot=0, YRot=0, ZRot=0, Size=1, RandomX=0, RandomY=0, " +
                         "RandomZ=0, RandomXRot=0, RandomYRot=0, RandomZRot=0, Terminate=1)\n");
        var rb = RunPair(Compile("FRAME(Frames=1)\n"), bb, lib, 30);
        var hit = rb.FxRunner.AllEffects.First();
        var vp2 = new Viewport { Assets = a, Animation = anim, Width = 800, Height = 600, History = rb.Game, GetEffectAssets = lib.AssetsFor };
        Func<bool, string> dir = flip =>
        {
            vp2.Flip = flip; vp2.ResetEffects(); vp2.Frame = rb.Fx[3]; vp2.AnimFrame = rb.Game[3].AnimFrame;
            var q = vp2.EffectScreenQuads(rb.Fx[3].Effects.First(), 4);
            int right = 0, total = 0;
            foreach (var t in q)
            {
                // corners 0 (u 0, v 0), 1 (u 1, v 0), 2 (u 1, v 1) run clockwise on screen (y down) unless the texture is
                // mirrored; the particle's own turn doesn't change that
                var S = t.Item1;
                float cross = (S[3] - S[0]) * (S[7] - S[1]) - (S[4] - S[1]) * (S[6] - S[0]);
                total++;
                if (cross > 0) right++;
            }
            return right + "/" + total;
        };
        string dr = dir(false), dl = dir(true);
        Check("v1.6.2: camera billboards (0x341002C's sprites): the texture isn't mirrored on screen (u 0 -> 1 then v 0 -> 1 clockwise), facing right and left",
              dr.Split('/')[1] != "0" && dr.Split('/')[0] == dr.Split('/')[1] && dl == dr, true);
    }

    // ---- v1.6.3: the user's real fighter folders (given on the command line, not in the repository) --------------------

    /// <summary>The game and expression scripts of a move on one timeline (as HitboxViewer.Rerun / RunExpression).</summary>
    static List<FrameState> Expression(string root, uint crc, int frames)
    {
        string body = Path.Combine(root, "script", "animcmd", "body");
        var game = new HitboxRunner().Run(Script(Path.Combine(body, "game.bin"), crc) ?? new List<ICommand>(), frames);
        var ex = Script(Path.Combine(body, "expression.bin"), crc);
        var r = new HitboxRunner { GetScript = id => Script(Path.Combine(body, "expression.bin"), id), SpeedSchedule = game.Select(x => x.Speed).ToArray() };
        return r.Run(ex ?? new List<ICommand>(), frames);
    }

    static void RealPacman(string pm, string visGroupsPath)
    {
        var a = FighterAssets.Load(pm);
        var groups = VisGroups.Load(visGroupsPath);
        Func<string, string> st = n => { var m = a.Model.Meshes.First(x => x.Name.StartsWith(n)); return n + (m.Visible ? " on" : " off"); };
        Func<uint, int, string, string> at = (crc, fr, meshes) =>
        {
            var fs = crc == 0 ? null : Expression(pm, crc, 300);
            var vis = fs != null ? fs[fr - 1].Vis : new VisState();
            string anim = crc == 0 ? "FitPacmanBodyMainA00Wait1.omo" : a.AnimationFor(crc);
            ModelParts.Apply(a, anim, fr, vis, groups, null);
            return string.Join(", ", meshes.Split(',').Select(st).ToArray());
        };
        const string all = "FinalpoweresaA,FinalpoweresaB,Aaka,Aosuke,Pinkey,PizaM,Pacman_VIS,boardA";
        Check("v1.6.3 Pac-Man (VisGroups.txt): Wait: the body only (power pellets, ghosts, 2D Pac-Man, signs hidden)", at(0, 1, all),
              "FinalpoweresaA off, FinalpoweresaB off, Aaka off, Aosuke off, Pinkey off, PizaM off, Pacman_VIS on, boardA off");
        Check("v1.6.3 Pac-Man: finalstart frame 30 (Model_Changer(2, 1)): the power pellets shown", at(0x017EB3D5, 30, all),
              "FinalpoweresaA on, FinalpoweresaB on, Aaka off, Aosuke off, Pinkey off, PizaM off, Pacman_VIS on, boardA off");
        Check("v1.6.3 Pac-Man: forward smash frame 20 (Model_Changer(1, 1) on frame 18): Blinky (Aaka)", at(0x1D1238F2, 20, all),
              "FinalpoweresaA off, FinalpoweresaB off, Aaka on, Aosuke off, Pinkey off, PizaM off, Pacman_VIS on, boardA off");
        Check("v1.6.3 Pac-Man: forward smash frame 40 (Model_Changer(1, 0) on frame 38): Blinky gone", at(0x1D1238F2, 40, "Aaka"), "Aaka off");
        Check("v1.6.3 Pac-Man: neutral air game frame 15 (CALL 0x669E43CF: Model_Changer(0, 1) at FRAME 3 = game frame 10, the motion slowed): the 2D Pac-Man, not the body", at(0x66264190, 15, "PizaM,Pacman_VIS,colorparts"),
              "PizaM on, Pacman_VIS off, colorparts off");
        Check("v1.6.3 Pac-Man: up taunt frame 60: one sign (group 3)", at(0x2C42123B, 60, "boardA,boardB,boardR").Split(',').Count(x => x.EndsWith(" on")), 1);
        // the user's defaults (VisUser.txt): hidden by default, the script's group still shows it on its frames
        string tmp = Path.Combine(Path.GetTempPath(), "evtest_visuser_" + Guid.NewGuid().ToString("N") + ".txt");
        try
        {
            var g2 = VisGroups.Load(visGroupsPath, tmp);
            bool saved = PartsMenu.Default(g2, new Dictionary<string, bool>(), "pacman", new[] { "Pacman_HanaMayu_VIS_O_OBJ", "Aaka_VIS_O_OBJ_NSC" }, false);
            var g3 = VisGroups.Load(visGroupsPath, tmp);
            string why;
            Check("v1.6.3 parts menu: \"Hidden by default for this fighter\" saved in VisUser.txt and read back",
                  saved + " " + g3.DefaultFor("pacman", "Pacman_HanaMayu_VIS_O_OBJ", out why) + " " + File.ReadAllLines(tmp).Last(), "True False pacman hide: Aaka_VIS_O_OBJ_NSC, Pacman_HanaMayu_VIS_O_OBJ");
            var fs = Expression(pm, 0x1D1238F2, 21);
            ModelParts.Apply(a, a.AnimationFor(0x1D1238F2), 20, fs[19].Vis, g3, null);
            Check("v1.6.3 parts menu: a mesh hidden by default still shows when the script's group switches it on (Blinky, forward smash)",
                  st("Aaka"), "Aaka on");
            PartsMenu.Default(g3, new Dictionary<string, bool>(), "pacman", new[] { "Aaka_VIS_O_OBJ_NSC" }, null);
            var g4 = VisGroups.Load(visGroupsPath, tmp);
            Check("v1.6.3 parts menu: \"Follow the script / default\" takes it out again", g4.DefaultFor("pacman", "Aaka_VIS_O_OBJ_NSC", out why).HasValue, false);
        }
        finally { try { File.Delete(tmp); } catch (Exception) { } }
        // part animations (pacmanpt1.pac) and billboard sprites
        string fsm = a.AnimationFor(0x1D1238F2);
        var anim = a.GetAnimation(fsm);
        var main = new Omo(a.Animations[fsm]);
        var ghosts = a.Skeleton.Bones.Where(b => b.Name.StartsWith("Ghost")).ToList();
        Check("v1.6.3: forward smash plays pacmanpt1.pac's part animation with main.pac's (the ghost bones: main.pac has none of them)",
              ghosts.Count(b => main.Has(b.Hash)) + " " + (anim != null && ghosts.Any(b => anim.Has(b.Hash))), "0 True");
        var vp = new Viewport { Assets = a, Animation = anim, AnimFrame = 20 };
        for (int flip = 0; flip < 2; flip++)
        {
            vp.Flip = flip == 1;
            var v = vp.MeshVertices("Aaka");
            float[] r, u, f;
            vp.CameraAxes(out r, out u, out f);
            // the sprite's plane: two edges' cross product along the view direction
            var e1 = new[] { v[3] - v[0], v[4] - v[1], v[5] - v[2] };
            int k = 2;
            while (k * 3 + 2 < v.Length && Math.Abs(Fx.Len(Fx.Cross(e1, new[] { v[k * 3] - v[0], v[k * 3 + 1] - v[1], v[k * 3 + 2] - v[2] }))) < 1e-4f) k++;
            var n = Fx.Norm(Fx.Cross(e1, new[] { v[k * 3] - v[0], v[k * 3 + 1] - v[1], v[k * 3 + 2] - v[2] }));
            float d = Math.Abs(n[0] * f[0] + n[1] * f[1] + n[2] * f[2]);
            Check("v1.6.3: Pac-Man's ghost sprite (a billboard bone) faces the camera, facing " + (flip == 1 ? "left" : "right"), d > 0.999f, true);
        }
        // the Final Smash bank's textures with only an original image (RGBA8): decoded, the component selector applied
        var fin = new PtclFile(File.ReadAllBytes(Path.Combine(pm, "effect", "FinPacman", "FinPacman.010d0000.ptcl")));
        var eye = fin.Sets.First(x => x.Name == "PtcFinPacmanEyeLeft").Emitters[0].Def.Tex;
        Check("v1.6.3: FinPacman's eyes (native size 0, original RGBA8) decode, 16 x 16", eye != null ? eye.Width + "x" + eye.Height : "null", "16x16");
        int blue = eye != null ? eye.Argb.Count(c => (c >> 24 & 255) > 128 && (c & 255) > 150 && (c >> 16 & 255) < 100) : 0;
        Check("v1.6.3: ...with their selector (B G R A): the pupils blue, as the arcade's", blue > 0, true);
    }

    static void RealBanks(IEnumerable<string> roots)
    {
        int n = 0, bad = 0, untex = 0;
        var names = new List<string>();
        foreach (var root in roots)
            foreach (var path in Directory.GetFiles(Path.Combine(root, "effect"), "*.ptcl", SearchOption.AllDirectories))
            {
                var p = new PtclFile(File.ReadAllBytes(path));
                foreach (var set in p.Sets)
                    foreach (var e in set.Emitters)
                    {
                        var d = e.Def;
                        n++;
                        if (d.Tex == null) { untex++; names.Add(set.Name + "/" + e.Name); continue; }
                        // a combiner that takes the alpha from the texture (1, 4, 5) on a texture without alpha: a block
                        if ((d.Combiner == 1 || d.Combiner == 4 || d.Combiner == 5) && PtclData.Opaque(d.Tex)) { bad++; names.Add(set.Name + "/" + e.Name); }
                    }
            }
        Check("v1.6.3: the real banks' " + n + " emitters: every texture decoded, none drawn as a block (alpha read from a texture "
              + "with none)", untex + " " + bad + (names.Count > 0 ? " " + string.Join(", ", names.Take(5).ToArray()) : ""), "0 0");
    }

    static void RealMariod(string md)
    {
        var p = new PtclFile(File.ReadAllBytes(Path.Combine(md, "effect", "mariod", "mariod.010d0000.ptcl")));
        var ring = p.Sets.First(x => x.Name == "PtcMariodCyclone").Emitters.First(x => x.Name == "ring1").Def;
        Check("v1.6.3: Dr. Mario's Cyclone ring1 (combiner 2, BC4 texture whose selector names a missing alpha: drew squares) "
              + "takes its shape from red", ring.Combiner + " " + ring.Note.Contains("alpha from red"), "2 True");
        // forward air: the arc is the common 0x1000090 with no colour command (its colour is the common bank's)
        var fair = Script(Path.Combine(md, "script", "animcmd", "body", "effect.bin"), 0x68FDC9A2);
        Check("v1.6.3: Dr. Mario's forward air effect script: one EFFECT_FOLLOW_FLIP 0x1000090, no colour command",
              string.Join(";", fair.Select(c => c.ToString()).Where(t => t.Contains("0x1000090") || t.Contains("COLOR") || t.Contains("Color")).Select(t => t.Split('(')[0]).ToArray()),
              "EFFECT_FOLLOW_FLIP");
        float U, V;
        EffectModel.EffectUV(0.25f, 0.25f, new[] { 0.5f, 0.5f }, new[] { 0.5f, 0.5f }, 0, out U, out V);
        Check("v1.6.3: effect models' UVs as the effect shader works them out (U = (u + t) s, V = 1 - s (1 - (v + t)))",
              U.ToString("0.###", IC) + " " + V.ToString("0.###", IC), "0.375 0.875");
    }

    static void RealLink(string lk)
    {
        var a = FighterAssets.Load(lk);
        var lib = new EffectLibrary(lk);
        string body = Path.Combine(lk, "script", "animcmd", "body");
        uint spin = 0x1BA6EBD5;
        var run = RunPair(Script(Path.Combine(body, "game.bin"), spin), Script(Path.Combine(body, "effect.bin"), spin), lib);
        var e = run.FxRunner.AllEffects.FirstOrDefault(x => x.Id == 0x3050006);
        Check("v1.6.3 Link: up special's sword effect 0x3050006 (its stripes kiseki1)", e != null, true);
        if (e == null) return;
        var anim = a.GetAnimation(a.AnimationFor(spin));
        var heads = new List<string>();
        for (int flip = 0; flip < 2; flip++)
        {
            var vp = new Viewport { Assets = a, Animation = anim, Width = 800, Height = 600, Flip = flip == 1 };
            vp.GetEffectAssets = lib.AssetsFor;
            vp.History = run.Fx;
            int g = e.StartFrame + 8;
            vp.Frame = run.Fx[g - 1];
            vp.AnimFrame = run.Fx[g - 1].AnimFrame;
            var quads = vp.EffectScreenQuads(e, g);
            var stripes = quads.Where(q => q.Item1.Length > 12).ToList();
            Check("v1.6.3 Link: kiseki1 (particle type 5) drawn as ribbons through its history, not quads, facing " + (flip == 1 ? "left" : "right"),
                  stripes.Count > 0 && stripes.All(q => q.Item1.Length >= 3 * 2 * 3), true);
            if (stripes.Count > 0)
            {
                var s0 = stripes[0].Item1;
                heads.Add(((s0[0] + s0[3]) / 2 - 400).ToString("0", IC));
            }
        }
        Check("v1.6.3 Link: the ribbons' heads mirror between the two facings (screen x about the centre)",
              heads.Count == 2 && Math.Abs(float.Parse(heads[0], IC) + float.Parse(heads[1], IC)) <= Math.Max(4, 0.1f * Math.Abs(float.Parse(heads[0], IC))), true);
    }

    // ---- v1.7.1: the game's own common bank (given on the command line: never copied into the repository) -------------

    /// <summary>The screen-space centre (x) of one emitter's quads of an effect on game frame g, less the model origin's,
    /// or NaN: what side of the fighter it is drawn on.</summary>
    static float EmitterX(Viewport vp, EffectData e, int g, Func<EmitterSim, bool> which)
    {
        var sim = vp.SimFor(e, g);
        if (sim == null) return float.NaN;
        var all = sim.Emitters.ToList();
        sim.Emitters.Clear();
        sim.Emitters.AddRange(all.Where(which));
        var q = vp.EffectScreenQuads(e, g);
        sim.Emitters.Clear();
        sim.Emitters.AddRange(all);
        var xs = q.SelectMany(t => Enumerable.Range(0, t.Item1.Length / 3).Select(i => t.Item1[i * 3])).ToList();
        return xs.Count == 0 ? float.NaN : xs.Average() - vp.ScreenOf(new[] { 0f, 0f, 0f })[0];
    }

    /// <summary>A fighter_param.bin of the generic param format with one entry: kind, then 353 floats (0x13C-0x147 given).</summary>
    static byte[] ParamFile(int kind, float[] colours)
    {
        var o = new List<byte> { 0xFF, 0xFF, 0, 0, 0, 0, 0, 0, 0x20, 0, 0, 0, 1 };
        Action<byte, byte[]> put = (t, v) => { o.Add(t); o.AddRange(v.Reverse()); };
        put(6, BitConverter.GetBytes(kind));
        for (int k = 1; k < 354; k++)
            put(7, BitConverter.GetBytes(k >= 0x13C && k < 0x148 ? colours[k - 0x13C] : 0.5f));
        return o.ToArray();
    }

    static string C(float[] c) { return c == null ? "null" : string.Join(" ", c.Select(x => x.ToString("0.###", IC)).ToArray()); }

    static void RealCommon(string commonDir, string work, string expPath, Func<uint, string> common, string md, string pm, string lk)
    {
        // the entries the test names, against tools/efc.py + ptcl.py (effect_viewer_test.py: expect_common.txt)
        var lib0 = new EffectLibrary(Path.Combine(Path.Combine(work, "fighter"), "supamario")) { CommonName = common, CommonFolder = commonDir };
        foreach (var line in File.ReadAllLines(expPath))
        {
            var p = line.Split('\t');
            if (p.Length < 3) continue;
            uint id = Convert.ToUInt32(p[0], 16);
            var a = lib0.AssetsFor(id);
            string got = a == null ? "none" : string.Join(" + ", new[] { a.SetName, a.Model != null ? "model " + a.Model.Name : null }.Where(x => !string.IsNullOrEmpty(x)).ToArray());
            var life = lib0.Lifetime(id);
            Check(string.Format("v1.7.1: the game's common bank: 0x{0:X} is {1} (tools/efc.py + ptcl.py), life {2}", id, p[1], p[2]),
                  got + " " + (life.HasValue ? Math.Max(1, life.Value) : -1), p[1] + " " + p[2]);
        }
        // the fighters' colours for the common attack effects (fighter_param 0x13C-0x147 by fighter_param_etc g14)
        if (md != null)
            Check("v1.7.1: Dr. Mario's colour for 0x1000090 (his forward-air arc, fighter_param 0x145-0x147: the game's orange-yellow; "
                  + "0x100008D 0x13C-0x13E; a fighter bank's id none)",
                  C(new EffectLibrary(md).FighterColour(0x1000090)) + " | " + C(new EffectLibrary(md).FighterColour(0x100008D)) + " | " +
                  C(new EffectLibrary(md).FighterColour(0x3240090)), "3 0.7 0.25 | 2 0.8 0.35 | null");
        if (pm != null)
            Check("v1.7.1: Pac-Man's colour for his streak 0x100008D", C(new EffectLibrary(pm).FighterColour(0x100008D)), "2 0.65 0.55");
        if (lk != null)
            Check("v1.7.1: Link's colours are white (no tint: null)", C(new EffectLibrary(lk).FighterColour(0x1000090)), "null");
        string tmp = Path.Combine(Path.GetTempPath(), "evtest_param_" + Guid.NewGuid().ToString("N"));
        try
        {
            string fd = Path.Combine(Path.Combine(Path.Combine(tmp, "data"), "fighter"), "mariod");
            string pd = Path.Combine(Path.Combine(Path.Combine(tmp, "data"), "param"), "fighter");
            Directory.CreateDirectory(fd);
            Directory.CreateDirectory(pd);
            File.WriteAllBytes(Path.Combine(pd, "fighter_param.bin"),
                               ParamFile(36, new[] { 1f, 2, 3, 4, 5, 6, 7, 8, 9, 0.1f, 0.2f, 0.3f }));
            var ml = new EffectLibrary(fd);
            Check("v1.7.1: a fighter_param.bin in the game folder (data/param/fighter above data/fighter/mariod) is read instead of "
                  + "the vanilla table: entry 36's words 0x145-0x147 for 0x1000090, 0x13F-0x141 for 0x1000092",
                  EffectLibrary.FindFighterParam(fd) != null ? C(ml.FighterColour(0x1000090)) + " | " + C(ml.FighterColour(0x1000092)) : "not found",
                  "0.1 0.2 0.3 | 4 5 6");
        }
        finally { try { Directory.Delete(tmp, true); } catch (Exception) { } }

        // the texture wraps (TexRes +0x0C): Pac-Man's streak head flare1 is a mirrored 2 x 2 repeat
        var lp = lib0.AssetsFor(0x100008D);
        if (lp != null)
        {
            var flare = lp.Emitters.First(x => x.Name == "flare1");
            var line = lp.Emitters.First(x => x.Name == "line_main1_add");
            Check("v1.7.1: wraps: 0x100008D flare1 mirrored on both axes (0x00); Wrap mirror 1.25 -> 0.75, -0.25 -> 0.25, repeat keeps 1.25, clamp 1.25 -> 1",
                  flare.Wrap0.ToString("X2") + " " + FxRaster.Wrap(1.25f, 0).ToString("0.###", IC) + " " + FxRaster.Wrap(-0.25f, 0).ToString("0.###", IC) + " " +
                  FxRaster.Wrap(1.25f, 1).ToString("0.###", IC) + " " + FxRaster.Wrap(1.25f, 2).ToString("0.###", IC), "00 0.75 0.25 1.25 1");
            Check("v1.7.1: rotBasis read (0x4C4): 0x100008D line_main1_add's quad off its particle by -0.15 of its length",
                  line.RotBasis[0].ToString("0.###", IC) + " " + line.RotBasis[1].ToString("0.###", IC), "0 -0.15");
            // the box volume (10): line2_add's particles on the faces of its 3 x 3 x 0.1 box
            var box = lp.Emitters.First(x => x.Name == "line2_add");
            var sb = new EffectSim(new EffectData { Index = 0, Id = 0x100008D, StartFrame = 1, Size = 1f }, lp, 100000);
            sb.StepTo(2, k => Mat4.TRS(new[] { 0f, 0f, 0f }, Mat4.EulerToQuat(0, 0, 0), new[] { 1f, 1f, 1f }));
            var es = sb.Emitters.First(x => x.D == box);
            var r = box.Radius;
            bool onFace = es.Live.Count > 0 && es.Live.All(q => Math.Abs(Math.Max(Math.Abs(q.P[0]) / r[0], Math.Max(Math.Abs(q.P[1]) / r[1], Math.Abs(q.P[2]) / r[2])) - 1) < 0.05f);
            Check("v1.7.1: volume 10 (a box, cross_f 0x04A503C4): 0x100008D line2_add's particles each on a face (one axis at its radius)",
                  box.VolumeType + " " + es.Live.Count + " " + onFace, "10 3 True");
        }

        // Dr. Mario's forward-air arc (0x1000090, type 4 polygons with a 1e-6 motion): in front of him, both facings
        if (md != null)
        {
            var a = FighterAssets.Load(md);
            var lib = new EffectLibrary(md) { CommonFolder = commonDir };
            string body = Path.Combine(md, "script", "animcmd", "body");
            uint fair = 0x68FDC9A2;
            var run = RunPair(Script(Path.Combine(body, "game.bin"), fair), Script(Path.Combine(body, "effect.bin"), fair), lib);
            var arc = run.FxRunner.AllEffects.FirstOrDefault(x => x.Id == 0x1000090);
            if (arc == null) { Check("v1.7.1: Dr. Mario's forward air starts 0x1000090", false, true); }
            else
            {
                var anim = a.GetAnimation(a.AnimationFor(fair));
                var side = new List<float>();
                foreach (bool flip in new[] { false, true })
                {
                    var vp = new Viewport { Assets = a, Animation = anim, Width = 800, Height = 600, Flip = flip, GetEffectAssets = lib.AssetsFor, History = run.Fx };
                    int g = arc.StartFrame + 2;
                    vp.Frame = run.Fx[g - 1];
                    vp.AnimFrame = run.Fx[g - 1].AnimFrame;
                    side.Add(EmitterX(vp, run.Fx[g - 1].Effects.First(x => x.Index == arc.Index), g, x => x.D.Name.StartsWith("line1")));
                }
                Check(string.Format(IC, "v1.7.1: Dr. Mario's forward-air arc drawn in front of him: {0:0} px facing right, {1:0} facing left (v1.7.0: behind)", side[0], side[1]),
                      side[0] > 10 && side[1] < -10 && Math.Abs(side[0] + side[1]) < 0.25f * Math.Abs(side[0]), true);
            }
        }
        // Pac-Man's jab streak (0x100008D): its quads off their particles by rotBasis, in front of him, both facings
        if (pm != null)
        {
            var a = FighterAssets.Load(pm);
            var lib = new EffectLibrary(pm) { CommonFolder = commonDir };
            string body = Path.Combine(pm, "script", "animcmd", "body");
            uint jab = 0xAF37E1FA;
            var run = RunPair(Script(Path.Combine(body, "game.bin"), jab), Script(Path.Combine(body, "effect.bin"), jab), lib);
            var st = run.FxRunner.AllEffects.FirstOrDefault(x => x.Id == 0x100008D);
            if (st != null)
            {
                var anim = a.GetAnimation(a.AnimationFor(jab));
                var side = new List<float>();
                foreach (bool flip in new[] { false, true })
                {
                    var vp = new Viewport { Assets = a, Animation = anim, Width = 800, Height = 600, Flip = flip, GetEffectAssets = lib.AssetsFor, History = run.Fx };
                    int g = st.StartFrame + 1;
                    vp.Frame = run.Fx[g - 1];
                    vp.AnimFrame = run.Fx[g - 1].AnimFrame;
                    side.Add(EmitterX(vp, run.Fx[g - 1].Effects.First(x => x.Index == st.Index), g, x => x.D.Name.StartsWith("line_main1")));
                }
                Check(string.Format(IC, "v1.7.1: Pac-Man's jab streak centred in front of him: {0:0} px facing right, {1:0} facing left", side[0], side[1]),
                      side[0] > 10 && side[1] < -10, true);
            }
        }
        // an XZ plate (type 2) laid with its Y onto the emitter's -Z: the Genesis beam's head meshes trail their particles
        if (lk != null)
        {
            var a = FighterAssets.Load(lk);
            var lib = new EffectLibrary(lk) { CommonFolder = commonDir };
            var e = new EffectData { Index = 0, Id = 0x10000A5, StartFrame = 1, X = 0, Y = 8, Z = 0, Size = 0.4f, Rate = 4, Follow = true, World = true };
            var vp = new Viewport { Assets = a, Width = 800, Height = 600, GetEffectAssets = lib.AssetsFor, Frame = new FrameState() };
            int g = 4;
            float mesh = EmitterX(vp, e, g, x => x.D.Name == "beam_shoot1_front");
            var es = vp.SimFor(e, g).Emitters.First(x => x.D.Name == "beam_shoot1_front");
            float at = es.Live.Count == 0 ? float.NaN : es.Live.Average(q => vp.ScreenOf(es.World(q))[0]) - vp.ScreenOf(new[] { 0f, 0f, 0f })[0];
            Check(string.Format(IC, "v1.7.1: 0x10000A5 beam_shoot1_front (type 2 meshes): drawn behind their particles along the beam ({0:0} px vs {1:0}; eft's programs)", mesh, at),
                  mesh < at, true);
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
        bool fxFile = args.Length > 3 && !args[3].Contains("=");
        if (fxFile) Level2(args[3], smLib, kbLib, ks);
        // ---- v1.6.1: effect rates, common effects, the scripts' sources -------------------------------------------------
        Rates(smLib, common);
        Common(root, sm, common, !args.Skip(3).Any(x => x.StartsWith("common=")));
        Sources(smAssets, smBody, dash);
        // ---- v1.6.2: colours, overlays, visibility, model parts, the arcs' direction --------------------------------
        if (fxFile) Visibility(args[3], smAssets);
        Colours();
        Arcs(smAssets, smLib, smBody);
        // ---- v1.6.3: the user's fighter folders, when given (pacman=DIR mariod=DIR link=DIR visgroups=FILE) --------
        Func<string, string> opt = k => args.Skip(3).Where(x => x.StartsWith(k + "=")).Select(x => x.Substring(k.Length + 1)).FirstOrDefault();
        string pmDir = opt("pacman"), mdDir = opt("mariod"), lkDir = opt("link");
        var reals = new[] { pmDir, mdDir, lkDir }.Where(x => x != null && Directory.Exists(x)).ToList();
        if (pmDir != null) RealPacman(pmDir, opt("visgroups") ?? "VisGroups.txt");
        if (mdDir != null) RealMariod(mdDir);
        if (lkDir != null) RealLink(lkDir);
        // v1.7.1: the game's common bank (common=DIR, linked at WORK/effect/common; expect_common.txt from tools/efc.py + ptcl.py)
        string cmDir = opt("common");
        if (cmDir != null) RealCommon(cmDir, Path.GetDirectoryName(root), opt("commonexp"), common, mdDir, pmDir, lkDir);
        if (cmDir != null) reals.Add(Path.GetDirectoryName(root));
        if (reals.Count > 0) RealBanks(reals);
        else Console.WriteLine("(v1.6.3's real-folder checks skipped: give pacman= / mariod= / link= folders)");

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
