// (Sm4shCloneTool 2.0) A fighter the importer wrote, opened with Sm4shCommand's own loaders (Mono): its ACMD files and
// motion.mtable as fighter mode opens them (SALT's ACMDFile / MTable, the main window's OpenFighter reads every .bin of
// the folder and motion.mtable), the names file (Runtime's AnimNames reader, by reflection on the tool's file), the
// Hitbox Viewer's assets (FighterAssets: the motion pack's animations by script), its sound banks through the
// soundlabeltable (FighterSounds: the Sound Effect Viewer's list), the decoded new tones, the aliases file
// (SoundAliases.ReadFile) and the effect library (EffectLibrary.AssetsFor: the .efc / .ptcl the Hitbox Viewer reads).
// Run through import_test.py, which writes EXPECT. Build (next to a built SM4SHCommand.exe / SALT.dll): csc
// -out:ScTest.exe -r:SALT.dll -r:SM4SHCommand.exe -r:<mono 4.5>/{mscorlib,System,System.Core,System.Windows.Forms,
// System.Drawing}.dll -nostdlib sm4shcommand_test.cs
// Run: mono ScTest.exe Events.cfg EXPECT.txt
// EXPECT lines (tab-separated):
//   fighter ROOT GAME_DATA            the fighter folder (its script/animcmd/body, motion, sound, effect) and the game data
//   names FILE                        the tool's Sm4shCommand_names.txt
//   aliases FILE                      the tool's Aliases/sounds/<fighter>.txt
//   count N                           motion.mtable's entries
//   scripts FILE N                    the scripts of FILE.bin (game, effect, sound, expression)
//   motion INDEX NAME OMO COPYOF      an imported motion (COPYOF: the motion index its scripts copy, or -1: empty)
//   sound ID TONE SAMPLES CHANNELS    an imported sound
//   effect ID SETNAME EMITTERS        an imported effect
//   alias ID TEXT
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;
using Sm4shCommand;
using Sm4shCommand.Sound;
using Sm4shCommand.Viewer;

class ScTest
{
    static int fails = 0, oks = 0;
    static readonly CultureInfo IC = CultureInfo.InvariantCulture;

    static void Check(string what, object got, object want)
    {
        bool ok = Equals(got, want);
        if (ok) oks++; else fails++;
        Console.WriteLine((ok ? "ok   " : "FAIL ") + what + (ok ? "" : string.Format(IC, ": got {0} (want {1})", got, want)));
    }

    static byte[] Bytes(ACMDScript s) { return s.Commands.Cast<ACMDCommand>().SelectMany(c => c.GetBytes(Endianness.Big)).ToArray(); }

    static uint Crc(string s) { return System.Security.Cryptography.Crc32.Compute(s.ToLowerInvariant()); }

    [STAThread]
    static int Main(string[] args)
    {
        var errors = new List<string>();
        ACMD_INFO.OverrideInfo(args[0], errors);
        Check("Events.cfg loads with no errors", errors.Count, 0);
        var lines = File.ReadAllLines(args[1]).Select(l => l.Split('\t')).Where(p => p.Length > 1).ToList();
        string root = null, game = null, names = null, aliasFile = null;
        int count = -1;
        foreach (var p in lines)
        {
            if (p[0] == "fighter") { root = p[1]; game = p[2]; }
            else if (p[0] == "names") names = p[1];
            else if (p[0] == "aliases") aliasFile = p[1];
            else if (p[0] == "count") count = int.Parse(p[1], IC);
        }
        string fname = Path.GetFileName(root);

        // ---- fighter mode: every .bin of script/animcmd/body and motion.mtable (MainForm.OpenFighter)
        string body = Path.Combine(Path.Combine(Path.Combine(root, "script"), "animcmd"), "body");
        var files = new Dictionary<string, ACMDFile>();
        if (!Directory.Exists(body)) count = -1;
        if (count >= 0)
        {
        foreach (var path in Directory.EnumerateFiles(body).Where(x => x.EndsWith(".bin")))
            files[Path.GetFileNameWithoutExtension(path)] = new ACMDFile(path);
        Check(fname + ": fighter mode opens the four ACMD files", string.Join(",", files.Keys.OrderBy(x => x)), "effect,expression,game,sound");
        var endian = files.Values.First().Endian;
        var mt0 = new MTable(Path.Combine(body, "motion.mtable"), endian);
        Check(fname + ": motion.mtable (SALT's MTable): " + count + " entries", mt0.Count, count);
        foreach (var f in files)
        {
            var want = lines.FirstOrDefault(x => x[0] == "scripts" && x[1] == f.Key);
            Check(fname + ": " + f.Key + ".bin: SALT reads its " + (want != null ? want[2] : "?") + " scripts",
                  f.Value.Scripts.Count.ToString(IC), want != null ? want[2] : "?");
        }
        }

        // ---- the names (Runtime's own reader of AnimNames.txt / ModAnimNames.txt, on the tool's names file)
        // (Runtime is internal: its reader, AnimNames and ViewerAnims through reflection)
        var rt = typeof(FighterAssets).Assembly.GetType("Sm4shCommand.Runtime");
        var load = rt.GetMethod("LoadAnimNameFile", BindingFlags.NonPublic | BindingFlags.Static);
        var animNames = (Dictionary<uint, string>)rt.GetField("AnimNames", BindingFlags.Public | BindingFlags.Static | BindingFlags.NonPublic).GetValue(null);
        var viewerAnims = (System.Collections.IDictionary)rt.GetField("ViewerAnims", BindingFlags.Public | BindingFlags.Static | BindingFlags.NonPublic).GetValue(null);
        animNames.Clear();
        viewerAnims.Clear();
        load.Invoke(null, new object[] { names });
        Func<uint, string> viewerLine = h =>
        {
            if (!viewerAnims.Contains(h)) return null;
            var va = viewerAnims[h];
            var t = va.GetType();
            return t.GetField("Folder").GetValue(va) + "/" + t.GetField("File").GetValue(va);
        };

        var assets = count >= 0 ? FighterAssets.Load(root) : null;
        MTable mt = count >= 0 ? new MTable(Path.Combine(body, "motion.mtable"), files.Values.First().Endian) : null;
        foreach (var p in lines.Where(x => x[0] == "motion"))
        {
            int index = int.Parse(p[1], IC), copyOf = int.Parse(p[4], IC);
            string name = p[2], omo = p[3];
            uint crc = Crc(name);
            Check(fname + ": motion 0x" + index.ToString("X", IC) + " " + name + ": motion.mtable[" + index + "] = its script's hash",
                  mt[index], crc);
            bool all = true, same = true;
            foreach (var f in files)
            {
                if (!f.Value.Scripts.ContainsKey(crc)) { all = false; continue; }
                var s = (ACMDScript)f.Value.Scripts[crc];
                if (copyOf >= 0)
                {
                    uint src = mt[copyOf];
                    if (f.Value.Scripts.ContainsKey(src)) same &= Bytes(s).SequenceEqual(Bytes((ACMDScript)f.Value.Scripts[src]));
                    else same &= s.Commands.Count <= 1;
                }
                else same &= s.Commands.Count <= 1;
            }
            Check(fname + ": " + name + ": a script in each of the four files" + (copyOf >= 0 ? " (motion 0x" + copyOf.ToString("X", IC) + "'s)" : " (empty)"),
                  all && same, true);
            Check(fname + ": " + name + ": Sm4shCommand labels it (its names file read by Runtime)",
                  animNames.ContainsKey(crc) ? animNames[crc] : null, name);
            Check(fname + ": " + name + ": the names file's viewer line (Name -> body/" + omo + ")", viewerLine(crc), "body/" + omo);
            Check(fname + ": " + name + ": the Hitbox Viewer plays " + omo + " for it (FighterAssets, the motion pack)",
                  assets.AnimationFor(crc), omo);
            Omo anim = null;
            try { anim = assets.GetAnimation(omo); } catch (Exception) { }
            Check(fname + ": " + name + ": its animation reads (the viewer's OMO reader)", anim != null && anim.Frames > 0, true);
        }

        // ---- sounds: the Sound Effect Viewer's list (FighterSounds through the soundlabeltable)
        if (lines.Any(x => x[0] == "sound"))
        {
            var fs = FighterSounds.Load(root, game);
            foreach (var p in lines.Where(x => x[0] == "sound"))
            {
                uint id = uint.Parse(p[1].Substring(2), NumberStyles.HexNumber, IC);
                var e = fs.Fighter.Entries.FirstOrDefault(x => x.Id.HasValue && x.Id.Value == id);
                Check(fname + ": sound 0x" + id.ToString("X8", IC) + " is " + p[2] + " in the Sound Effect Viewer's list",
                      e != null && e.Tone != null ? e.Tone.Name : null, p[2]);
                if (e == null || e.Tone == null) continue;
                AudioClip clip = null;
                try { clip = Idsp.Decode(e.Bank.ReadAudio(e.Tone)); } catch (Exception ex) { Console.WriteLine("     " + ex.Message); }
                Check(fname + ": sound 0x" + id.ToString("X8", IC) + ": its tone decodes (" + p[3] + " samples, " + p[4] + " channel(s))",
                      clip != null ? clip.Samples + " " + clip.Channels : null, p[3] + " " + p[4]);
                Check(fname + ": sound 0x" + id.ToString("X8", IC) + ": playable", e.Playable, true);
            }
            var used = fs.Fighter.Entries.Where(x => x.Id.HasValue).GroupBy(x => x.Id.Value).Where(g => g.Count() > 1).Count();
            Check(fname + ": every sound id in its list once", used, 0);
        }
        if (aliasFile != null)
        {
            var al = SoundAliases.ReadFile(aliasFile);
            foreach (var p in lines.Where(x => x[0] == "alias"))
            {
                uint id = uint.Parse(p[1].Substring(2), NumberStyles.HexNumber, IC);
                Check(fname + ": alias of 0x" + id.ToString("X8", IC) + " (SoundAliases.ReadFile)", al.ContainsKey(id) ? al[id] : null, p[2]);
            }
        }

        // ---- effects: the Hitbox Viewer's effect library
        var lib = new EffectLibrary(root);
        foreach (var p in lines.Where(x => x[0] == "effect"))
        {
            uint id = uint.Parse(p[1].Substring(2), NumberStyles.HexNumber, IC);
            EffectAssets a = null;
            try { a = lib.AssetsFor(id); } catch (Exception ex) { Console.WriteLine("     " + ex.Message); }
            Check(fname + ": effect 0x" + id.ToString("X8", IC) + ": the effect library finds " + p[2] + " with " + p[3] + " emitter(s)",
                  a != null ? a.SetName + " " + a.Emitters.Count : null, p[2] + " " + p[3]);
        }

        Console.WriteLine(string.Format(IC, "\n{0} ok, {1} failed", oks, fails));
        return fails == 0 ? 0 : 1;
    }
}
