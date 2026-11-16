// The Hitbox Viewer's scripts (Sm4shCommand v1.7.2): every one of a move's four ACMD scripts runs, as in the game
// (HitboxRunner.Others): hitboxes / body states / effects from any of them, each script with its own frame cursor (FRAME /
// WAIT, loops, If / Else, CALL) on the motion's rate; and the v1.7.2 effect drawing fixes that need no window (an effect
// model's single-bound parts in their bone's space, a particle slot's UV animation).
// Build (next to the built SM4SHCommand.exe / SALT.dll): csc -out:VsTest.exe -r:SALT.dll -r:SM4SHCommand.exe
// -r:<mono 4.5>/mscorlib.dll -r:<mono 4.5>/System.dll -r:<mono 4.5>/System.Core.dll -r:<mono 4.5>/System.Drawing.dll
// -nostdlib viewer_scripts_test.cs. Run (the exe's type initialisers want a display: xvfb-run on Linux):
//   mono VsTest.exe Events.cfg [FIGHTER_DIR ...] [--common DIR]
// FIGHTER_DIR: a fighter folder (script/animcmd/body with game / effect / sound / expression.bin, e.g. the user's link,
// pacman, mariod): every script of it run the v1.7.1 way (game alone; effect / expression alone on the game's speeds) and
// the v1.7.2 way, compared; named cross-script moves checked (Pac-Man's hitboxes in its effect / expression scripts,
// Link's effect in a game script). --common DIR: the common bank's folder (EffCommonCrossBomb's fire column placed).
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;
using Sm4shCommand.Viewer;

class VsTest
{
    static int fails = 0, oks = 0;

    static void Check(string what, object got, object want)
    {
        bool ok = Equals(got, want);
        if (ok) oks++; else fails++;
        Console.WriteLine((ok ? "ok   " : "FAIL ") + what + (ok ? "" : ": got " + got + " (want " + want + ")"));
    }

    static void True(string what, bool ok, string detail = "")
    {
        if (ok) oks++; else fails++;
        Console.WriteLine((ok ? "ok   " : "FAIL ") + what + (ok || detail.Length == 0 ? "" : ": " + detail));
    }

    static IList<ICommand> Compile(string text)
    {
        var s = new ACMDScript(0x1234);
        s.Serialize(text);
        return s.Commands;
    }

    static string HB(int id, int bone = 0, float size = 3)
    {
        return "Hitbox(ID=" + id + ", Part=0, Bone=" + bone + ", Damage=5, Angle=361, KBG=100, FKB=0, BKB=30, Size=" + size +
               ", X=0, Y=5, Z=0, Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=0, SFXType=0, Ground/Air=3, Direct/Indirect=1, Type=0)";
    }

    static string FX(uint id)
    {
        return "Graphic_Effect2(Graphic=0x" + id.ToString("X") + ", Bone=0, X=0, Y=0, Z=0, XRot=0, YRot=0, ZRot=0, Size=1, RandomX=0, " +
               "RandomY=0, RandomZ=0, RandomXRot=0, RandomYRot=0, RandomZRot=0, Terminate=0)";
    }

    static HitboxRunner.ScriptSource Src(string kind, string text)
    {
        return new HitboxRunner.ScriptSource { Kind = kind, Commands = Compile(text), GetScript = c => null };
    }

    static string Frames(List<FrameState> fs, Func<FrameState, bool> on)
    {
        return string.Join(",", fs.Where(on).Select(f => f.GameFrame.ToString()).ToArray());
    }

    static void Synthetic()
    {
        Console.WriteLine("== synthetic: four scripts, one timeline");
        // the game script doubles the motion's rate from frame 1: every script's FRAME timers count motion frames
        string game = "FRAME(Frames=1)\nSet_Frame_Duration(Speed=0.5)\nFRAME(Frames=9)\n" + HB(0) + "\nFRAME(Frames=13)\nRemove_All_Hitboxes()";
        string effect = "FRAME(Frames=5)\n" + HB(1) + "\n" + FX(0x1000002) + "\nWAIT(Frames=4)\nRemove_Hitbox(ID=1)";
        string sound = "Set_Loop(Iterations=3){\n    WAIT(Frames=2)\n    " + FX(0x1000003) + "\n    Goto(Offset=-19)\n}\nBody_Collision(State=2)";
        string expr = "IS_FLAG(Variable=0x2100000E)\nTrue(Offset=6){\n    " + FX(0x1000004) + "\n}\nElse(Offset=4){\n    " + FX(0x1000005) + "\n}";
        foreach (bool cond in new[] { true, false })
        {
            var r = new HitboxRunner { ConditionsTrue = cond, GetScript = c => null, OneShotLife = id => 3 };
            r.Others = new List<HitboxRunner.ScriptSource> { Src("effect", effect), Src("sound", sound), Src("expression", expr) };
            var fs = r.Run(Compile(game), 20);
            string tag = cond ? " (if true)" : " (if false)";
            // motion frames: game frame 1 -> 0 .. 1 (first frame), then +2 a frame: 3, 5, 7, 9, 11, 13 on frames 2-7
            Check("anim frames" + tag, string.Join(",", fs.Take(8).Select(f => f.AnimFrame.ToString("0.#")).ToArray()), "0,2,4,6,8,10,12,14");
            Check("game hitbox 0 on (motion 9-12)" + tag, Frames(fs, f => f.Hitboxes.Any(h => h.Id == 0)), "6,7");
            Check("effect-script hitbox 1 on (motion 5 + 4 = 9)" + tag, Frames(fs, f => f.Hitboxes.Any(h => h.Id == 1)), "4,5");
            Check("hitbox 1 says its script" + tag, fs[3].Hitboxes.First(h => h.Id == 1).Script, "effect");
            Check("hitbox 0 says its script" + tag, fs[5].Hitboxes.First(h => h.Id == 0).Script, "game");
            var all = r.AllEffects;
            Check("effect-script effect: one, on motion 5" + tag, string.Join(",", all.Where(e => e.Id == 0x1000002).Select(e => e.StartFrame + "/" + e.Script).ToArray()), "4/effect");
            // the sound script's loop: WAIT 2 three times, on its own cursor (2 motion frames a game frame from frame 2)
            Check("sound-script loop effects (its own WAIT cursor)" + tag,
                  string.Join(",", all.Where(e => e.Id == 0x1000003).Select(e => e.StartFrame + "/" + e.Script).ToArray()), "2/sound,3/sound,4/sound");
            Check("sound-script body state: intangible from its frame" + tag, Frames(fs.Take(8).ToList(), f => f.Intangible), "4,5,6,7");
            uint want = cond ? 0x1000004u : 0x1000005u, not = cond ? 0x1000005u : 0x1000004u;
            Check("expression If / Else: the branch taken" + tag,
                  all.Count(e => e.Id == want && e.Script == "expression") + " " + all.Count(e => e.Id == not), "1 0");
            Check("no effect twice" + tag, all.Count, 5);
        }
        // a frame-speed command in another script sets the motion's rate for every script (from the next frame)
        var r2 = new HitboxRunner { GetScript = c => null };
        r2.Others = new List<HitboxRunner.ScriptSource> { Src("effect", "FRAME(Frames=2)\nSet_Frame_Duration(Speed=2)\nFRAME(Frames=4)\n" + HB(2)) };
        var f2 = r2.Run(Compile("FRAME(Frames=3)\n" + HB(3)), 10);
        Check("effect script's Set_Frame_Duration slows the motion", string.Join(",", f2.Take(6).Select(f => f.AnimFrame.ToString("0.#")).ToArray()), "0,1,2,2.5,3,3.5");
        Check("game hitbox at motion 3 (slowed)", Frames(f2, f => f.Hitboxes.Any(h => h.Id == 3)).Split(',')[0], "5");
        Check("effect hitbox at motion 4 (slowed)", Frames(f2, f => f.Hitboxes.Any(h => h.Id == 2)).Split(',')[0], "7");
        // sound commands aren't effects or notes
        var r3 = new HitboxRunner { GetScript = c => null };
        r3.Others = new List<HitboxRunner.ScriptSource> { Src("sound", "FRAME(Frames=2)\nSound_Effect(SFX=0x51)\nStop_Sound_Effect(SFX=0x51)") };
        r3.Run(Compile("FRAME(Frames=1)"), 5);
        Check("sound commands: no effects / screen events", r3.AllEffects.Count + " " + r3.AllScreen.Count, "0 0");
        // a move with no game script: the other scripts still run
        var r4 = new HitboxRunner { GetScript = c => null };
        r4.Others = new List<HitboxRunner.ScriptSource> { Src("expression", "FRAME(Frames=3)\n" + HB(4)) };
        var f4 = r4.Run(new List<ICommand>(), 6);
        Check("no game script: expression hitbox", Frames(f4, f => f.Hitboxes.Any(h => h.Id == 4)), "4,5,6");
    }

    static Func<uint, IList<ICommand>> Get(string path)
    {
        var f = File.Exists(path) ? new ACMDFile(path) : null;
        return id => { IScript s; return f != null && f.Scripts.TryGetValue(id, out s) && s is ACMDScript ? ((ACMDScript)s).Commands : null; };
    }

    static IEnumerable<uint> Crcs(string path)
    {
        if (!File.Exists(path)) return new uint[0];
        return new ACMDFile(path).Scripts.Keys;
    }

    static string Key(EffectData e) { return e.Id.ToString("X") + "@" + e.StartFrame + "-" + e.EndFrame + "/" + e.SpawnAnimFrame.ToString("0.##") + "/" + e.Bone; }

    /// <summary>Every script of a fighter, the v1.7.1 way and the v1.7.2 way: the game script's hitboxes and body states
    /// the same unless another script has some, the effect script's effects the same (no duplicates), plus the other
    /// scripts' own.</summary>
    static void Fighter(string dir)
    {
        string body = Path.Combine(dir, "script", "animcmd", "body");
        string name = Path.GetFileName(dir.TrimEnd('/', '\\'));
        Console.WriteLine("== " + name + ": every script, v1.7.1 vs v1.7.2");
        var g = Get(Path.Combine(body, "game.bin")); var e = Get(Path.Combine(body, "effect.bin"));
        var s = Get(Path.Combine(body, "sound.bin")); var x = Get(Path.Combine(body, "expression.bin"));
        var all = new HashSet<uint>();
        foreach (var k in new[] { "game", "effect", "sound", "expression" }) foreach (var c in Crcs(Path.Combine(body, k + ".bin"))) all.Add(c);
        int same = 0, moreHb = 0, moreFx = 0, total = 0;
        var bad = new List<string>();
        foreach (var crc in all.OrderBy(c => c))
        {
            total++;
            const int N = 150;
            // v1.7.1: the game script alone, the effect script on its speeds
            var old = new HitboxRunner { GetScript = g }.Run(g(crc) ?? new List<ICommand>(), N);
            var oldFx = new HitboxRunner { GetScript = e, SpeedSchedule = old.Select(f => f.Speed).ToArray(), OneShotLife = id => 20 };
            if (e(crc) != null) oldFx.Run(e(crc), N);
            // v1.7.2
            var nr = new HitboxRunner { GetScript = g, OneShotLife = id => 20 };
            nr.Others = new List<HitboxRunner.ScriptSource>();
            if (e(crc) != null) nr.Others.Add(new HitboxRunner.ScriptSource { Kind = "effect", Commands = e(crc), GetScript = e });
            if (s(crc) != null) nr.Others.Add(new HitboxRunner.ScriptSource { Kind = "sound", Commands = s(crc), GetScript = s });
            if (x(crc) != null) nr.Others.Add(new HitboxRunner.ScriptSource { Kind = "expression", Commands = x(crc), GetScript = x });
            var nw = nr.Run(g(crc) ?? new List<ICommand>(), N);
            bool otherHb = nw.Any(f => f.Hitboxes.Any(h => h.Script != "game"));
            bool hbSame = true;
            for (int i = 0; i < N; i++)
            {
                string a = string.Join(";", old[i].Hitboxes.Select(h => h.Id + ":" + h.Bone + ":" + h.Damage).ToArray()) + old[i].Intangible + old[i].Invincible;
                string b = string.Join(";", nw[i].Hitboxes.Where(h => h.Script == "game").Select(h => h.Id + ":" + h.Bone + ":" + h.Damage).ToArray()) + nw[i].Intangible + nw[i].Invincible;
                if (old[i].AnimFrame != nw[i].AnimFrame) { hbSame = false; bad.Add(string.Format("0x{0:X8} frame {1}: anim {2} vs {3}", crc, i + 1, old[i].AnimFrame, nw[i].AnimFrame)); break; }
                if (a != b && !otherHb) { hbSame = false; bad.Add(string.Format("0x{0:X8} frame {1}: {2} vs {3}", crc, i + 1, a, b)); break; }
            }
            var oldKeys = oldFx.AllEffects.Select(Key).ToList();
            var newKeys = nw.Count > 0 ? nr.AllEffects.Where(q => q.Script == "effect").Select(Key).ToList() : new List<string>();
            bool fxSame = oldKeys.SequenceEqual(newKeys);
            if (!fxSame) bad.Add(string.Format("0x{0:X8} effects: [{1}] vs [{2}]", crc, string.Join(" ", oldKeys.ToArray()), string.Join(" ", newKeys.ToArray())));
            if (hbSame && fxSame) same++;
            if (otherHb) moreHb++;
            if (nr.AllEffects.Any(q => q.Script != "effect")) moreFx++;
        }
        True(name + ": " + same + " of " + total + " scripts keep the game script's hitboxes / body states and the effect script's effects " +
             "exactly (" + moreHb + " with hitboxes from another script, " + moreFx + " with effects from another script)", bad.Count == 0,
             string.Join("\n      ", bad.Take(8).ToArray()));
        if (name.StartsWith("pacman"))
        {
            // Pac-Man's hitboxes in other scripts: 0xE8410CDF's two in its expression script (frames 18-20), 0x2BB1E8A1's
            // Special_Hitbox in its effect script (frame 1, to 1.4 under its own Set_Frame_Duration(7))
            var r = new HitboxRunner { GetScript = g };
            r.Others = new List<HitboxRunner.ScriptSource> { new HitboxRunner.ScriptSource { Kind = "effect", Commands = e(0xE8410CDF), GetScript = e },
                                                             new HitboxRunner.ScriptSource { Kind = "expression", Commands = x(0xE8410CDF), GetScript = x } };
            var fs = r.Run(g(0xE8410CDF) ?? new List<ICommand>(), 40);
            Check("pacman 0xE8410CDF: expression-script hitboxes 0 / 1 on frames", Frames(fs, f => f.Hitboxes.Count == 2 && f.Hitboxes.All(h => h.Script == "expression")), "18,19,20");
            r = new HitboxRunner { GetScript = g };
            r.Others = new List<HitboxRunner.ScriptSource> { new HitboxRunner.ScriptSource { Kind = "effect", Commands = e(0x2BB1E8A1), GetScript = e },
                                                             new HitboxRunner.ScriptSource { Kind = "expression", Commands = x(0x2BB1E8A1), GetScript = x } };
            fs = r.Run(g(0x2BB1E8A1) ?? new List<ICommand>(), 60);
            Check("pacman 0x2BB1E8A1: effect-script Special_Hitbox on frames (motion 1 to 1.4 at 1/7)", Frames(fs, f => f.Hitboxes.Any(h => h.Script == "effect" && h.Special)), "1,2,3");
            Check("pacman 0x2BB1E8A1: its effects (one each)", string.Join(",", r.AllEffects.Select(q => "0x" + q.Id.ToString("X")).ToArray()),
                  "0x1000002,0x1000002,0x1000017,0x3310002");
        }
        if (name.StartsWith("link"))
        {
            // Link's 0x1DDF4AA6: an External_Graphic in his game script (no effect script): drawn now
            var r = new HitboxRunner { GetScript = g };
            r.Others = new List<HitboxRunner.ScriptSource>();
            var fs = r.Run(g(0x1DDF4AA6), 30);
            Check("link 0x1DDF4AA6: the game script's effect", string.Join(",", r.AllEffects.Select(q => "0x" + q.Id.ToString("X") + "@" + q.StartFrame + "/" + q.Script).ToArray()), "0x1000094@2/game");
        }
    }

    static void Models(string common)
    {
        Console.WriteLine("== effect models: single-bound parts in their bone's space");
        var m = EffectModel.Load(Path.Combine(common, "model", "EffCommonCrossBomb"));
        var pose = m.Pose(20);
        int k = 0;
        foreach (var mesh in m.Model.Meshes)
            foreach (var p in mesh.Polys)
            {
                var v = pose[k++];
                float lo = 1e9f, hi = -1e9f;
                for (int i = 1; i < v.Length; i += 3) { lo = Math.Min(lo, v[i]); hi = Math.Max(hi, v[i]); }
                // every part of the column from the ground (about -5) to its top (206 / 247): none under the stage
                True("EffCommonCrossBomb " + mesh.Name + " from " + lo.ToString("0.#") + " to " + hi.ToString("0.#"), lo > -10 && hi > 150);
            }
    }

    static void UvAnim()
    {
        Console.WriteLine("== a particle slot's UV animation (eft's formula)");
        var a = new EmitterDef.UvAnim();
        a.Scl[2] = a.Scl[3] = 1;
        float U, V;
        // still: the corner x repeat
        a.At(1, 1, 2, 2, false, 5, new[] { 0.3f, 0.6f, 0.9f }, out U, out V);
        Check("still quad corner (1, 1) x 2", U.ToString("0.###") + " " + V.ToString("0.###"), "2 2");
        a.At(0.25f, 0.75f, 1, 1, true, 5, null, out U, out V);
        Check("still mesh UV", U.ToString("0.###") + " " + V.ToString("0.###"), "0.25 0.75");
        // the common flash's ring (PtcCommonFlash FlashRing: repeat 2, initial scroll v 1): its centre on V 0, a mirror edge
        a.Scroll[3] = 1;
        a.At(0.5f, 0.5f, 2, 2, false, 0, null, out U, out V);
        Check("FlashRing: the quad's centre at (1, 0)", U.ToString("0.###") + " " + V.ToString("0.###"), "1 0");
        a.At(0, 0, 2, 2, false, 0, null, out U, out V);
        Check("FlashRing: corner (0, 0) at (0, -1)", U.ToString("0.###") + " " + V.ToString("0.###"), "0 -1");
        // scroll a frame, a quarter turn
        a = new EmitterDef.UvAnim(); a.Scl[2] = a.Scl[3] = 1; a.Scroll[0] = 0.1f;
        a.At(0, 0, 1, 1, false, 3, null, out U, out V);
        Check("scroll 0.1 a frame, age 3: U - 0.3", U.ToString("0.###") + " " + V.ToString("0.###"), "-0.3 0");
        a = new EmitterDef.UvAnim(); a.Scl[2] = a.Scl[3] = 1; a.Rot[1] = (float)(Math.PI / 2);
        a.At(1, 0.5f, 1, 1, false, 0, null, out U, out V);
        Check("turned a quarter: (1, 0.5) to (0.5, 0)", U.ToString("0.###") + " " + V.ToString("0.###"), "0.5 0");
    }

    static void Main(string[] args)
    {
        var errors = new List<string>();
        ACMD_INFO.OverrideInfo(args[0], errors);
        Synthetic();
        UvAnim();
        for (int i = 1; i < args.Length; i++)
        {
            if (args[i] == "--common") { Models(args[++i]); continue; }
            Fighter(args[i]);
        }
        Console.WriteLine(oks + " ok, " + fails + " failed");
        Environment.Exit(fails == 0 ? 0 : 1);
    }
}
