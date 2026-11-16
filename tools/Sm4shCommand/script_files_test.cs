// Sm4shCommand v1.7.2 under Mono + Xvfb: a motion's script added to (and removed from) one of its four ACMD files in
// fighter mode (Add Script File / Remove Script File), saved, read back; a missing file made from nothing; the Hitbox
// Viewer's scripts finding the new one.
// Build (next to the built SM4SHCommand.exe / SALT.dll): csc -out:SfTest.exe -r:SALT.dll -r:SM4SHCommand.exe
// -r:<mono 4.5>/mscorlib.dll -r:<mono 4.5>/System.dll -r:<mono 4.5>/System.Core.dll -r:<mono 4.5>/System.Windows.Forms.dll
// -r:<mono 4.5>/System.Drawing.dll -r:FastColoredTextBox.dll -nostdlib script_files_test.cs
// Run: xvfb-run -a mono SfTest.exe Events.cfg ANIMCMD_BODY_DIR WORK_DIR   (ANIMCMD_BODY_DIR: a fighter's
// script/animcmd/body with game / effect / sound / expression.bin; copied into WORK_DIR, never changed)
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Windows.Forms;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;
using Sm4shCommand.Viewer;

class SfTest
{
    static int fails = 0, oks = 0;

    static void Check(string what, object got, object want)
    {
        bool ok = Equals(got, want);
        if (ok) oks++; else fails++;
        Console.WriteLine((ok ? "ok   " : "FAIL ") + what + (ok ? "" : ": got " + got + " (want " + want + ")"));
    }

    /// <summary>An ACMD file read from a copy (SALT maps the file it reads).</summary>
    static ACMDFile Read(string path)
    {
        string copy = Path.GetTempFileName();
        File.Copy(path, copy, true);
        return new ACMDFile(copy);
    }

    static string Bytes(IScript s, Endianness e)
    {
        return BitConverter.ToString(((ACMDScript)s).Cast<ACMDCommand>().SelectMany(c => c.GetBytes(e)).ToArray());
    }

    static void CopyDir(string from, string to)
    {
        if (Directory.Exists(to)) Directory.Delete(to, true);
        Directory.CreateDirectory(to);
        foreach (var f in Directory.GetFiles(from)) File.Copy(f, Path.Combine(to, Path.GetFileName(f)));
    }

    static void Save(Form main)
    {
        main.GetType().GetMethod("saveToolStripMenuItem_Click", BindingFlags.NonPublic | BindingFlags.Instance).Invoke(main, new object[] { null, EventArgs.Empty });
    }

    static Sm4shCommand.GUI.CodeEditor Tab(Form main, uint crc)
    {
        var vp = (TabControl)main.GetType().GetField("Viewport", BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Public).GetValue(main);
        return vp.TabPages["script_" + crc.ToString("X8")] as Sm4shCommand.GUI.CodeEditor;
    }

    [STAThread]
    static int Main(string[] args)
    {
        var errors = new List<string>();
        ACMD_INFO.OverrideInfo(args[0], errors);
        string src = args[1], work = args[2];
        var rt = typeof(FighterAssets).Assembly.GetType("Sm4shCommand.Runtime");
        var main = (Form)rt.GetProperty("Instance").GetValue(null);
        main.Show();
        Application.DoEvents();
        var T = main.GetType();
        Func<uint, string, string> add = (c, k) => (string)T.GetMethod("AddKindScript").Invoke(main, new object[] { c, k });
        Func<uint, string, bool> remove = (c, k) => (bool)T.GetMethod("RemoveKindScript").Invoke(main, new object[] { c, k, false });

        // 1. a script added to a file that has others: a motion with a game script and no effect script
        string d1 = Path.Combine(work, "add");
        CopyDir(src, d1);
        var game0 = Read(Path.Combine(src, "game.bin"));
        var fx0 = Read(Path.Combine(src, "effect.bin"));
        uint crc = game0.Scripts.Keys.First(k => !fx0.Scripts.ContainsKey(k) && ((ACMDScript)game0.Scripts[k]).Count > 1);
        Console.WriteLine("motion 0x" + crc.ToString("X8") + ": a game script, no effect script");
        T.GetMethod("OpenFighter").Invoke(main, new object[] { d1 });
        Application.DoEvents();
        string path = add(crc, "effect");
        Check("added to effect.bin", Path.GetFileName(path ?? ""), "effect.bin");
        var page = Tab(main, crc);
        Check("the motion's tab has an effect sub-tab", page != null && page.EditorFor("effect") != null, true);
        Check("...and its game sub-tab still", page != null && page.EditorFor("game") != null, true);
        string text = "FRAME(Frames=3)\nGraphic_Effect2(Graphic=0x1000002, Bone=0, X=0, Y=5, Z=0, XRot=0, YRot=0, ZRot=0, Size=1, RandomX=0, " +
                      "RandomY=0, RandomZ=0, RandomXRot=0, RandomYRot=0, RandomZRot=0, Terminate=0)";
        page.EditorFor("effect").Text = text;
        Save(main);
        var fx1 = Read(Path.Combine(d1, "effect.bin"));
        Check("effect.bin: one more script", fx1.Scripts.Count, fx0.Scripts.Count + 1);
        Check("the new script is there", fx1.Scripts.ContainsKey(crc), true);
        var sc = fx1.Scripts.ContainsKey(crc) ? (ACMDScript)fx1.Scripts[crc] : null;
        Check("its commands (FRAME, the effect, Script_End)", sc != null ? string.Join(",", sc.Cast<ACMDCommand>().Select(c => c.Name).ToArray()) : "",
              "FRAME,Graphic_Effect2,Script_End");
        int same = fx0.Scripts.Keys.Count(k => fx1.Scripts.ContainsKey(k) && Bytes(fx0.Scripts[k], fx0.Endian) == Bytes(fx1.Scripts[k], fx1.Endian));
        Check("every other effect script byte-identical", same, fx0.Scripts.Count);
        Check("the other files byte-identical", File.ReadAllBytes(Path.Combine(d1, "game.bin")).SequenceEqual(File.ReadAllBytes(Path.Combine(src, "game.bin"))) &&
              File.ReadAllBytes(Path.Combine(d1, "sound.bin")).SequenceEqual(File.ReadAllBytes(Path.Combine(src, "sound.bin"))) &&
              File.ReadAllBytes(Path.Combine(d1, "expression.bin")).SequenceEqual(File.ReadAllBytes(Path.Combine(src, "expression.bin"))), true);
        // the viewer's scripts (the open files) give it, and it plays
        var files = (SortedList<string, IScriptCollection>)T.GetProperty("ScriptFiles").GetValue(main);
        var vs = new ViewerScripts(d1, () => files);
        var got = vs.Get("effect", crc);
        Check("the Hitbox Viewer's effect script for the motion", got != null ? got.Count : -1, 3);
        var r = new HitboxRunner { GetScript = vs.Getter("game"), OneShotLife = id => 10 };
        r.Others = new List<HitboxRunner.ScriptSource> { new HitboxRunner.ScriptSource { Kind = "effect", Commands = got, GetScript = vs.Getter("effect") } };
        r.Run(vs.Get("game", crc), 10);
        Check("...played with the game script: its effect", string.Join(",", r.AllEffects.Select(e => "0x" + e.Id.ToString("X") + "@" + e.StartFrame + "/" + e.Script).ToArray()),
              "0x1000002@3/effect");
        // reopened: the motion lists four scripts
        T.GetMethod("OpenFighter").Invoke(main, new object[] { d1 });
        T.GetMethod("OpenScriptByHash").Invoke(main, new object[] { crc });
        page = Tab(main, crc);
        Check("reopened: effect tab with the script", page != null && page.EditorFor("effect") != null && page.EditorFor("effect").Text.Contains("Graphic_Effect2"), true);
        // removed again: the file as it was
        Check("removed", remove(crc, "effect"), true);
        Save(main);
        var fx2 = Read(Path.Combine(d1, "effect.bin"));
        Check("effect.bin: the script gone", fx2.Scripts.ContainsKey(crc), false);
        Check("effect.bin byte-identical to the original again", File.ReadAllBytes(Path.Combine(d1, "effect.bin")).SequenceEqual(File.ReadAllBytes(Path.Combine(src, "effect.bin"))), true);

        // 2. a file made from nothing: sound.bin missing from the folder
        string d2 = Path.Combine(work, "new");
        CopyDir(src, d2);
        File.Delete(Path.Combine(d2, "sound.bin"));
        T.GetMethod("OpenFighter").Invoke(main, new object[] { d2 });
        Application.DoEvents();
        path = add(crc, "sound");
        Check("added to a new sound.bin", Path.GetFileName(path ?? ""), "sound.bin");
        Tab(main, crc).EditorFor("sound").Text = "FRAME(Frames=2)\nSound_Effect(SFX=0x51)";
        Save(main);
        Check("sound.bin written", File.Exists(Path.Combine(d2, "sound.bin")), true);
        var b = File.ReadAllBytes(Path.Combine(d2, "sound.bin"));
        var g = File.ReadAllBytes(Path.Combine(src, "game.bin"));
        Check("its header: ACMD, the other files' version / endianness word", b.Length > 16 && b[0] == 'A' && b[1] == 'C' && b[2] == 'M' && b[3] == 'D' &&
              b.Skip(4).Take(4).SequenceEqual(g.Skip(4).Take(4)), true);
        var s2 = Read(Path.Combine(d2, "sound.bin"));
        Check("read back: one script, the motion's", s2.Scripts.Count + " " + s2.Scripts.ContainsKey(crc), "1 True");
        Check("its commands", string.Join(",", ((ACMDScript)s2.Scripts[crc]).Cast<ACMDCommand>().Select(c => c.Name).ToArray()), "FRAME,Sound_Effect,Script_End");
        T.GetMethod("OpenFighter").Invoke(main, new object[] { d2 });
        T.GetMethod("OpenScriptByHash").Invoke(main, new object[] { crc });
        Check("reopened: the sound tab", Tab(main, crc) != null && Tab(main, crc).EditorFor("sound") != null, true);
        Console.WriteLine(oks + " ok, " + fails + " failed");
        return fails == 0 ? 0 : 1;
    }
}
