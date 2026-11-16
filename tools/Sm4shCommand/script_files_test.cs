// Sm4shCommand v1.7.2: a motion's script added to (and removed from) one of its four ACMD files in fighter mode (Add
// Script File / Remove Script File: ScriptFileSet, on the main window's open files, then its save: Export of each file),
// saved, read back; a missing file made from nothing; the Hitbox Viewer's scripts finding the new one. The editors
// (FastColoredTextBox) don't load on Mono: the script text goes in as the editor's compile would put it.
// Build (next to the built SM4SHCommand.exe / SALT.dll): csc -out:SfTest.exe -r:SALT.dll -r:SM4SHCommand.exe
// -r:<mono 4.5>/mscorlib.dll -r:<mono 4.5>/System.dll -r:<mono 4.5>/System.Core.dll -r:<mono 4.5>/System.Windows.Forms.dll
// -r:<mono 4.5>/System.Drawing.dll -r:FastColoredTextBox.dll -nostdlib script_files_test.cs
// Run: mono SfTest.exe Events.cfg ANIMCMD_BODY_DIR WORK_DIR   (ANIMCMD_BODY_DIR: a fighter's
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

    /// <summary>The fighter folder as the main window opens it (OpenFighter: every .bin, path -> file).</summary>
    static SortedList<string, IScriptCollection> Open(string dir)
    {
        var files = new SortedList<string, IScriptCollection>();
        foreach (var p in Directory.EnumerateFiles(dir))
            if (p.EndsWith(".bin")) files.Add(p, Read(p));
        return files;
    }

    /// <summary>The main window's fighter-mode save: every file exported where it was opened from.</summary>
    static void Save(SortedList<string, IScriptCollection> files)
    {
        foreach (var pair in files) pair.Value.Export(pair.Key);
    }

    /// <summary>The script's text compiled into it, as the editor's TryApplyChanges does.</summary>
    static void Edit(ACMDFile f, uint crc, string text)
    {
        ((ACMDScript)f.Scripts[crc]).Serialize(text);
    }

    [STAThread]
    static int Main(string[] args)
    {
        var errors = new List<string>();
        ACMD_INFO.OverrideInfo(args[0], errors);
        string src = args[1], work = args[2];
        // 1. a script added to a file that has others: a motion with a game script and no effect script
        string d1 = Path.Combine(work, "add");
        CopyDir(src, d1);
        var game0 = Read(Path.Combine(src, "game.bin"));
        var fx0 = Read(Path.Combine(src, "effect.bin"));
        uint crc = game0.Scripts.Keys.First(k => !fx0.Scripts.ContainsKey(k) && ((ACMDScript)game0.Scripts[k]).Count > 1);
        Console.WriteLine("motion 0x" + crc.ToString("X8") + ": a game script, no effect script");
        var files = Open(d1);
        Check("before: no effect script", Sm4shCommand.ScriptFileSet.Has(files, d1, crc, "effect"), false);
        bool made;
        string path = Sm4shCommand.ScriptFileSet.Add(files, d1, crc, "effect", Sm4shCommand.ScriptFileSet.EndianOf(files, Endianness.Big), out made);
        Check("added to effect.bin (not a new file)", Path.GetFileName(path ?? "") + " " + made, "effect.bin False");
        Check("an empty script (Script_End)", ((ACMDScript)((ACMDFile)files[path]).Scripts[crc]).Count, 1);
        string text = "FRAME(Frames=3)\nGraphic_Effect2(Graphic=0x1000002, Bone=0, X=0, Y=5, Z=0, XRot=0, YRot=0, ZRot=0, Size=1, RandomX=0, " +
                      "RandomY=0, RandomZ=0, RandomXRot=0, RandomYRot=0, RandomZRot=0, Terminate=0)";
        Edit((ACMDFile)files[path], crc, text);
        // the Hitbox Viewer's scripts (the open files, before saving) give it, and it plays with the game script
        var vs = new ViewerScripts(d1, () => files);
        var got = vs.Get("effect", crc);
        Check("the Hitbox Viewer's effect script for the motion (unsaved)", got != null ? got.Count : -1, 3);
        var r = new HitboxRunner { GetScript = vs.Getter("game"), OneShotLife = id => 10 };
        r.Others = new List<HitboxRunner.ScriptSource> { new HitboxRunner.ScriptSource { Kind = "effect", Commands = got, GetScript = vs.Getter("effect") } };
        r.Run(vs.Get("game", crc), 10);
        Check("...played with the game script: its effect", string.Join(",", r.AllEffects.Select(e => "0x" + e.Id.ToString("X") + "@" + e.StartFrame + "/" + e.Script).ToArray()),
              "0x1000002@3/effect");
        Save(files);
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
        // reopened: the motion has its effect script; removed again: the file as it was
        files = Open(d1);
        Check("reopened: the effect script", Sm4shCommand.ScriptFileSet.Has(files, d1, crc, "effect"), true);
        Check("removed", Sm4shCommand.ScriptFileSet.Remove(files, d1, crc, "effect"), true);
        Check("removed twice: nothing to remove", Sm4shCommand.ScriptFileSet.Remove(files, d1, crc, "effect"), false);
        Save(files);
        var fx2 = Read(Path.Combine(d1, "effect.bin"));
        Check("effect.bin: the script gone", fx2.Scripts.ContainsKey(crc), false);
        Check("effect.bin byte-identical to the original again", File.ReadAllBytes(Path.Combine(d1, "effect.bin")).SequenceEqual(File.ReadAllBytes(Path.Combine(src, "effect.bin"))), true);

        // 2. a file made from nothing: sound.bin missing from the folder
        string d2 = Path.Combine(work, "new");
        CopyDir(src, d2);
        File.Delete(Path.Combine(d2, "sound.bin"));
        files = Open(d2);
        path = Sm4shCommand.ScriptFileSet.Add(files, d2, crc, "sound", Sm4shCommand.ScriptFileSet.EndianOf(files, Endianness.Big), out made);
        Check("added to a new sound.bin", Path.GetFileName(path ?? "") + " " + made, "sound.bin True");
        Edit((ACMDFile)files[path], crc, "FRAME(Frames=2)\nSound_Effect(SFX=0x51)");
        Save(files);
        Check("sound.bin written", File.Exists(Path.Combine(d2, "sound.bin")), true);
        var b = File.ReadAllBytes(Path.Combine(d2, "sound.bin"));
        var g = File.ReadAllBytes(Path.Combine(src, "game.bin"));
        Check("its header: ACMD, the other files' version / endianness word", b.Length > 16 && b[0] == 'A' && b[1] == 'C' && b[2] == 'M' && b[3] == 'D' &&
              b.Skip(4).Take(4).SequenceEqual(g.Skip(4).Take(4)), true);
        var s2 = Read(Path.Combine(d2, "sound.bin"));
        Check("read back: one script, the motion's, same endianness", s2.Scripts.Count + " " + s2.Scripts.ContainsKey(crc) + " " + (s2.Endian == game0.Endian), "1 True True");
        Check("its commands", string.Join(",", ((ACMDScript)s2.Scripts[crc]).Cast<ACMDCommand>().Select(c => c.Name).ToArray()), "FRAME,Sound_Effect,Script_End");
        // the vanilla sound.bin's layout: a lone script written as the game's files are (header, the hash / offset table, the commands)
        Check("size: 0x10 header + 8 a script + its words x 4", b.Length, 0x10 + 8 + 4 * (2 + 2 + 1));
        // 3. the whole folder new: a script file for an article with only a game.bin
        string d3 = Path.Combine(work, "article");
        if (Directory.Exists(d3)) Directory.Delete(d3, true);
        Directory.CreateDirectory(d3);
        File.Copy(Path.Combine(src, "game.bin"), Path.Combine(d3, "game.bin"));
        files = Open(d3);
        foreach (var k in new[] { "effect", "sound", "expression" })
            Sm4shCommand.ScriptFileSet.Add(files, d3, crc, k, Sm4shCommand.ScriptFileSet.EndianOf(files, Endianness.Big), out made);
        Save(files);
        files = Open(d3);
        Check("article folder: four files, the motion in each", files.Count + " " + Sm4shCommand.ScriptFileSet.Kinds.All(k => Sm4shCommand.ScriptFileSet.Has(files, d3, crc, k)), "4 True");
        // 4. a little-endian folder (3DS files): the new file made little-endian as the others
        string d4 = Path.Combine(work, "little");
        if (Directory.Exists(d4)) Directory.Delete(d4, true);
        Directory.CreateDirectory(d4);
        Read(Path.Combine(src, "game.bin")).Export(Path.Combine(d4, "game.bin"), Endianness.Little);
        files = Open(d4);
        Check("little-endian game.bin read as such", ((ACMDFile)files.Values[0]).Endian, Endianness.Little);
        Sm4shCommand.ScriptFileSet.Add(files, d4, crc, "effect", Sm4shCommand.ScriptFileSet.EndianOf(files, Endianness.Big), out made);
        Save(files);
        var le = File.ReadAllBytes(Path.Combine(d4, "effect.bin"));
        Check("its new effect.bin: little-endian header (version word 02 00 00 00, as game.bin's)", le.Skip(4).Take(4).SequenceEqual(File.ReadAllBytes(Path.Combine(d4, "game.bin")).Skip(4).Take(4)) && le[4] == 2, true);
        Check("read back: little-endian, the motion's script", Read(Path.Combine(d4, "effect.bin")).Endian + " " + Read(Path.Combine(d4, "effect.bin")).Scripts.ContainsKey(crc), "Little True");
        Console.WriteLine(oks + " ok, " + fails + " failed");
        return fails == 0 ? 0 : 1;
    }
}
