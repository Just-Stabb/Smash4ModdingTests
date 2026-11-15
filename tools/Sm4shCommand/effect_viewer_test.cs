// The Hitbox Viewer's effects (v1.5.0, Level 1), headless (Mono): the effect script run on the game script's timeline
// (HitboxRunner with SpeedSchedule), the effects it starts / ends, their names and lifetimes from the fighter's .efc /
// .ptcl (EffectLibrary), their place (Viewport.EffectMatrix), sword trails, flip IDs, colours, rates, the facing rule.
// Run through effect_viewer_test.py, which builds the fighter folders and the expected names / lifetimes (tools/efc.py,
// tools/ptcl.py). Build (next to the built SM4SHCommand.exe / SALT.dll): csc -out:EvTest.exe -r:SALT.dll
// -r:SM4SHCommand.exe -r:<mono 4.5>/mscorlib.dll -r:<mono 4.5>/System.dll -r:<mono 4.5>/System.Core.dll
// -r:<mono 4.5>/System.Windows.Forms.dll -r:<mono 4.5>/System.Drawing.dll -nostdlib effect_viewer_test.cs.
// Run: mono EvTest.exe Events.cfg FIGHTERS_DIR EXPECT.txt
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
