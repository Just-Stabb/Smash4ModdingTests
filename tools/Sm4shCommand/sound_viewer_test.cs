// The Sound Effect Viewer (Sm4shCommand v1.7.32), headless (Mono): nus3bank / soundlabeltable reading and rebuilding,
// sound ids, the DSP-ADPCM decoder (its PCM written for sound_viewer_test.py to check against its own decoder and the
// user's mp3), previews / WAV, aliases, the editor tooltip, the inserted command lines (compile + round trip), part 2's
// label-table writer; with --gui (Xvfb) the form: lists, filter, alias edit, Add to Script, and a picture of it.
// Run through sound_viewer_test.py. Build (next to the built SM4SHCommand.exe / SALT.dll): csc -out:SvTest.exe
// -r:SALT.dll -r:SM4SHCommand.exe -r:<mono 4.5>/mscorlib.dll -r:<mono 4.5>/System.dll -r:<mono 4.5>/System.Core.dll
// -r:<mono 4.5>/System.Windows.Forms.dll -r:<mono 4.5>/System.Drawing.dll -nostdlib sound_viewer_test.cs
// Run: mono SvTest.exe Events.cfg FIGHTER_ROOT GAME_DATA PORT_ROOT OUT_DIR [--gui]
//   FIGHTER_ROOT  .../fighter/gekkouga (sound/: the user's snd_se_Gekkouga with the skeleton / ice tones, vanilla vc)
//                 with .../sound/config/soundlabeltable.bin above it (the package's)
//   GAME_DATA     a folder with sound/se/snd_se_joucyu.nus3bank and sound/config/soundlabeltable.bin (vanilla)
//   PORT_ROOT     .../fighter/master (a port's banks on their own ids 46192 ..., its table above it)
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Windows.Forms;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;
using Sm4shCommand.Sound;

class SvTest
{
    static int fails = 0, oks = 0;
    static readonly CultureInfo IC = CultureInfo.InvariantCulture;

    static void Check(string what, object got, object want)
    {
        bool ok = Equals(got, want);
        if (ok) oks++; else fails++;
        Console.WriteLine((ok ? "ok   " : "FAIL ") + what + (ok ? "" : string.Format(IC, ": got {0} (want {1})", got, want)));
    }

    static void True(string what, bool ok) { Check(what, ok, true); }

    static byte[] Bytes(ACMDScript s) { return s.Commands.Cast<ACMDCommand>().SelectMany(c => c.GetBytes(Endianness.Big)).ToArray(); }

    static void WritePcm(string outDir, string name, AudioClip a, List<string> manifest, string source)
    {
        var b = new byte[a.Pcm.Length * 2];
        Buffer.BlockCopy(a.Pcm, 0, b, 0, b.Length);
        File.WriteAllBytes(Path.Combine(outDir, name + ".s16"), b);
        manifest.Add(string.Join("\t", new[] { name, source, a.Channels.ToString(IC), a.SampleRate.ToString(IC), a.Samples.ToString(IC),
            a.Loops ? "1" : "0", a.LoopStart.ToString(IC), a.LoopEnd.ToString(IC) }));
    }

    [STAThread]
    static int Main(string[] args)
    {
        var errors = new List<string>();
        ACMD_INFO.OverrideInfo(args[0], errors);
        Check("Events.cfg loads with no errors", errors.Count, 0);
        string root = args[1], game = args[2], port = args[3], outDir = args[4];
        bool gui = args.Contains("--gui");
        Directory.CreateDirectory(outDir);
        var manifest = new List<string>();

        // ---- the bank: the user's snd_se_Gekkouga (skeleton v1.5's six tones + the ice detonation's IceBoom)
        string sePath = Path.Combine(Path.Combine(root, "sound"), "snd_se_Gekkouga.nus3bank");
        var se = Nus3Bank.Load(sePath);
        Check("se: BINF name", se.Name, "snd_se_Gekkouga");
        Check("se: BINF id", se.Id, 2058u);
        Check("se: tones", se.Tones.Count, 111);
        Check("se: empty stubs", se.Tones.Count(t => t.Kind == ToneKind.Empty), 14);
        Check("se: every sound IDSP", se.Tones.Where(t => t.HasAudio).All(t => t.Codec == "IDSP"), true);
        var ice = se.Tones[110];
        Check("tone 110 name", ice.Name, "snd_se_Gekkouga_IceBoom");
        Check("tone 110 volume (gekkouga_sound.py's +4 dB)", ice.VolumeDb, 4.0f);
        Check("tone 110 mono 48 kHz one-shot", string.Format(IC, "{0} {1} {2}", ice.Channels, ice.SampleRate, ice.Loops), "1 48000 False");
        Check("tone 104 name", se.Tones[104].Name, "snd_se_Gekkouga_SkSpawn1");
        Check("tone 0 volume (vanilla step: -6.5 dB)", se.Tones[0].VolumeDb, -6.5f);
        Check("se rebuilt byte for byte", se.Build().SequenceEqual(File.ReadAllBytes(sePath)), true);
        // a volume change touches only that float (part 2's level)
        var copy = Nus3Bank.Load(sePath);
        copy.Tones[110].VolumeDb = -3f;
        var changed = copy.Build();
        var orig = File.ReadAllBytes(sePath);
        int diff = 0;
        for (int i = 0; i < orig.Length; i++) if (orig[i] != changed[i]) diff++;
        Check("volume set: same size", changed.Length, orig.Length);
        True("volume set: only its float's bytes differ (" + diff + ")", diff >= 1 && diff <= 4);
        string tmpBank = Path.Combine(outDir, "volume_test.nus3bank");
        File.WriteAllBytes(tmpBank, changed);
        Check("volume set: read back", Nus3Bank.Load(tmpBank).Tones[110].VolumeDb, -3f);
        File.Delete(tmpBank);

        string vcPath = Path.Combine(Path.Combine(root, "sound"), "snd_vc_Gekkouga.nus3bank");
        var vc = Nus3Bank.Load(vcPath);
        Check("vc: BINF", vc.Name + " " + vc.Id, "snd_vc_Gekkouga 6071");
        Check("vc rebuilt byte for byte", vc.Build().SequenceEqual(File.ReadAllBytes(vcPath)), true);
        string commonPath = Path.Combine(Path.Combine(Path.Combine(game, "sound"), "se"), "snd_se_joucyu.nus3bank");
        var common = Nus3Bank.Load(commonPath);
        Check("common: BINF", common.Name + " " + common.Id, "snd_se_joucyu 2000");
        Check("common: tones (row 0 has 415 labels)", common.Tones.Count, 404);
        Check("common: the container (futtobi_meteor_)", common.Tones.Count(t => t.Kind == ToneKind.Container), 1);
        Check("common: stereo tones", common.Tones.Count(t => t.HasAudio && t.Channels == 2), 9);
        Check("common rebuilt byte for byte", common.Build().SequenceEqual(File.ReadAllBytes(commonPath)), true);

        // ---- the label table
        string stbPath = FighterSounds.FindData(root, Path.Combine(Path.Combine("sound", "config"), "soundlabeltable.bin"), null, out bool fromPicked);
        True("the package's soundlabeltable.bin found above the fighter: " + stbPath, stbPath != null && !fromPicked);
        var stb = SoundLabelTable.Load(stbPath);
        Check("table rows", stb.Rows.Count, 3252);
        Check("row of 2058", stb.RowOf(2058), 0x768);
        Check("row 0x768 labels (91 vanilla + 6 skeleton + IceBoom)", stb.Labels(0x768).Length, 98);
        Check("label 97 -> tone 110", stb.Labels(0x768)[97], 110);
        Check("row of 2000 (common)", stb.RowOf(2000), 0);
        Check("row of 6071 (his voices)", stb.RowOf(6071) >= 0, true);
        uint bank;
        Check("0x07680061 reaches tone 110", stb.ToneOf(0x07680061, out bank), 110);
        Check("... of bank 2058", bank, 2058u);
        Check("table rebuilt byte for byte", stb.Build().SequenceEqual(File.ReadAllBytes(stbPath)), true);
        // part 2: a row's labels grown (the old ids stay), an empty row used; written, read back
        var grow = SoundLabelTable.Parse(stb.Build());
        var labels = grow.Labels(0x768).ToList();
        labels.Add(110);
        grow.SetLabels(0x768, labels);
        int empty = grow.Rows.FindIndex(r => r.Empty);
        grow.UseRow(empty, 47000, new[] { 0, 1, 2 });
        var back = SoundLabelTable.Parse(grow.Build());
        Check("part 2: grown row keeps its ids", back.ToneOf(0x07680061, out bank), 110);
        Check("part 2: the new label 98", back.ToneOf(0x07680062, out bank), 110);
        Check("part 2: the used row's bank", back.RowOf(47000), empty);
        Check("part 2: the used row's labels", string.Join(",", back.Labels(empty)), "0,1,2");
        True("part 2: used ids hold 0x07680061, not 0x07680063", back.UsedIds().Contains(0x07680061) && !back.UsedIds().Contains(0x07680063));

        // ---- the fighter's sounds (as the viewer loads them), the common bank from the picked game data
        string ini = Path.Combine(Application.StartupPath, "Sm4shCommand.ini");
        var fs = FighterSounds.Load(root, game);
        Check("fighter name", fs.Name, "gekkouga");
        Check("banks", string.Join(",", fs.Fighter.Banks.Select(b => fs.Fighter.Kinds[b])), "se,vc,cheer");
        Check("the mod's table used", fs.TablePath, stbPath);
        Check("common bank from the picked game data", fs.CommonBankPath, commonPath);
        var byId = fs.Fighter.Entries.Where(e => e.Id.HasValue).ToDictionary(e => e.Id.Value, e => e);
        Check("0x07680061 -> IceBoom", byId[0x07680061].Name, "snd_se_Gekkouga_IceBoom");
        Check("0x0768005B -> SkSpawn1", byId[0x0768005B].Name, "snd_se_Gekkouga_SkSpawn1");
        Check("0x07680060 -> SkBoom", byId[0x07680060].Name, "snd_se_Gekkouga_SkBoom");
        int vcRow = stb.RowOf(6071);
        var vcEntry = fs.Fighter.Entries.First(e => e.Kind == "vc" && e.Id.HasValue && e.Playable);
        Check("a vc id is on his vc row", SoundLabelTable.RowOfId(vcEntry.Id.Value), vcRow);
        Check("ids: one per label that reaches a tone (se)", fs.Fighter.Entries.Count(e => e.Kind == "se" && e.Id.HasValue), stb.Labels(0x768).Count(x => x >= 0));
        var commonById = fs.Common.Entries.Where(e => e.Id.HasValue).ToDictionary(e => e.Id.Value, e => e);
        Check("common ids: row 0's labels", commonById.Count, stb.Labels(0).Count(x => x >= 0));
        Check("common 0x46 (blowaway_l: futtobi)", commonById[0x46].Name.Contains("futtobi"), true);
        Check("common 0x61 (dizzy: furafura)", commonById[0x61].Name, "snd_se_common_furafura");
        Check("common 0x0F (Hit_Muteki)", commonById[0x0F].Name, "snd_se_common_Hit_Muteki");
        Check("common 0x61 loops", commonById[0x61].Tone.Loops, true);

        // a port: own ids (46192 ...) played through their alias' row (Viewer/SoundBanks.txt), its costume bank too
        var aliases = FighterSounds.LoadBankAliases(Path.Combine(Path.Combine(Application.StartupPath, "Viewer"), "SoundBanks.txt"));
        Check("SoundBanks.txt: Master's se 46192 -> 2028", aliases.ContainsKey(46192) ? aliases[46192] : 0u, 2028u);
        var ms = FighterSounds.Load(port, null, aliases);
        var mse = ms.Fighter.Banks.First(b => ms.Fighter.Kinds[b] == "se");
        Check("port se: own id", mse.Id, 46192u);
        int mrow = ms.Table.RowOf(2028);
        Check("port se: its alias' row", ms.Fighter.RowOfBank[mse], mrow);
        var mc01 = ms.Fighter.Banks.First(b => ms.Fighter.Kinds[b] == "se c01");
        Check("port se c01 (own id 46201 -> 2028): the same row", ms.Fighter.RowOfBank[mc01], mrow);
        True("port: ids on row 0x1B", ms.Fighter.Entries.Any(e => e.Kind == "se" && e.Id.HasValue && SoundLabelTable.RowOfId(e.Id.Value) == mrow));
        // without the alias list: a costume bank falls back to the main bank's row, the main has none
        var ms2 = FighterSounds.Load(port, null, new Dictionary<uint, uint>());
        Check("no alias list: the port's se has no row", ms2.Fighter.RowOfBank[ms2.Fighter.Banks.First(b => ms2.Fighter.Kinds[b] == "se")], -1);

        // ---- decoding: the PCM for sound_viewer_test.py (its own decoder; the creeper mp3)
        WritePcm(outDir, "iceboom", Idsp.Decode(se.ReadAudio(ice)), manifest, sePath + "#110");
        WritePcm(outDir, "skboom", Idsp.Decode(se.ReadAudio(se.Tones[109])), manifest, sePath + "#109");
        WritePcm(outDir, "step", Idsp.Decode(se.ReadAudio(se.Tones[0])), manifest, sePath + "#0");
        WritePcm(outDir, "voice", Idsp.Decode(vc.ReadAudio(vcEntry.Tone)), manifest, vcPath + "#" + vcEntry.Tone.Index);
        var stereo = common.Tones.First(t => t.HasAudio && t.Channels == 2);
        WritePcm(outDir, "stereo", Idsp.Decode(common.ReadAudio(stereo)), manifest, commonPath + "#" + stereo.Index);
        var furafura = commonById[0x61].Tone;
        var ff = Idsp.Decode(common.ReadAudio(furafura));
        WritePcm(outDir, "furafura", ff, manifest, commonPath + "#" + furafura.Index);
        var zoom = common.Tones.First(t => t.Name == "snd_se_system_zoom_in");
        var zc = Idsp.Decode(common.ReadAudio(zoom));
        WritePcm(outDir, "zoom_in", zc, manifest, commonPath + "#" + zoom.Index);
        File.WriteAllLines(Path.Combine(outDir, "manifest.txt"), manifest.ToArray());
        Check("zoom_in loop points (IDSP header)", zc.LoopStart + "-" + zc.LoopEnd, "10472-36175");

        // ---- previews: a one-shot as it is, a loop repeated after its intro; the WAV
        var ic = Idsp.Decode(se.ReadAudio(ice));
        var p0 = Idsp.Preview(ic, 0, 8);
        Check("one-shot preview: its own length", p0.Length, ic.Samples);
        Check("one-shot preview at 0 dB: the samples", p0.SequenceEqual(ic.Pcm), true);
        var pz = Idsp.Preview(zc, 0, 8);
        long body = zc.LoopEnd - zc.LoopStart + 1;
        True("looped preview: intro + whole loops, about 8 s (" + pz.Length / (double)zc.SampleRate + " s)",
             (pz.Length - (zc.LoopEnd + 1)) % body == 0 && pz.Length >= 8 * zc.SampleRate && pz.Length < 8 * zc.SampleRate + body);
        Check("looped preview: after the loop end comes the loop start", pz[zc.LoopEnd + 1], zc.Pcm[zc.LoopStart]);
        Check("loop off: once", Idsp.Preview(zc, 0, 0).Length, zc.Samples);
        var pg = Idsp.Preview(ic, -6.0206, 0);
        int k = Array.FindIndex(ic.Pcm, s => Math.Abs((int)s) > 1000);
        Check("-6 dB halves", pg[k], (short)Math.Round(ic.Pcm[k] / 2.0));
        var wav = Idsp.Wav(p0, 1, 48000);
        Check("WAV: RIFF size", BitConverter.ToInt32(wav, 4), wav.Length - 8);
        Check("WAV: rate", BitConverter.ToInt32(wav, 24), 48000);
        Check("WAV: data size", BitConverter.ToInt32(wav, 40), p0.Length * 2);
        File.WriteAllBytes(Path.Combine(outDir, "iceboom_preview.wav"), wav);
        File.WriteAllBytes(Path.Combine(outDir, "stereo_preview.wav"), Idsp.Wav(Idsp.Preview(Idsp.Decode(common.ReadAudio(stereo)), 0, 0), 2, stereo.SampleRate));

        // ---- aliases: Aliases/sounds/FIGHTER.txt and common.txt
        string aliasDir = Path.Combine(outDir, "aliases");
        if (Directory.Exists(aliasDir)) Directory.Delete(aliasDir, true);
        SoundAliases.Folder = aliasDir;
        byId[0x07680061].Alias = "Creeper boom (ice detonation)";
        commonById[0x46].Alias = "Strong hit";
        Check("alias file", File.Exists(Path.Combine(aliasDir, "gekkouga.txt")), true);
        True("alias line", File.ReadAllLines(Path.Combine(aliasDir, "gekkouga.txt")).Contains("0x07680061 = Creeper boom (ice detonation)"));
        True("common alias line", File.ReadAllLines(Path.Combine(aliasDir, "common.txt")).Contains("0x00000046 = Strong hit"));
        SoundAliases.Reload();
        Check("alias read back", SoundAliases.Get("gekkouga", 0x07680061), "Creeper boom (ice detonation)");
        string set;
        Check("alias found from another fighter's scripts", SoundAliases.Find(0x07680061, "kirby", out set), "Creeper boom (ice detonation)");
        Check("... in gekkouga's file", set, "gekkouga");
        SoundAliases.Set("gekkouga", 0x0768005B, "Skeleton ding");
        SoundAliases.Set("gekkouga", 0x0768005B, "");
        Check("an alias cleared", SoundAliases.Get("gekkouga", 0x0768005B), "");
        Check("the others kept", SoundAliases.Get("gekkouga", 0x07680061), "Creeper boom (ice detonation)");
        // the variable aliases don't read Aliases/sounds
        string varSounds = Path.Combine(Path.Combine(Sm4shCommand.Classes.VariableAliases.Folder, "sounds"), "svtest.txt");
        Directory.CreateDirectory(Path.GetDirectoryName(varSounds));
        File.WriteAllText(varSounds, "0x07680061 = Creeper boom\n");
        var problems = Sm4shCommand.Classes.VariableAliases.Load();
        Check("variable aliases skip Aliases/sounds", problems.Count(p => p.Contains("svtest")), 0);
        File.Delete(varSounds);
        if (Directory.GetFileSystemEntries(Path.GetDirectoryName(varSounds)).Length == 0) Directory.Delete(Path.GetDirectoryName(varSounds));

        // ---- the editor's tooltip on a sound id
        SoundTips.OpenedPath = Path.Combine(Path.Combine(Path.Combine(Path.Combine(root, "script"), "animcmd"), "body"), "sound.bin");
        SoundTips.PickedData = game;
        SoundTips.Current = null;
        string tip = Sm4shCommand.Classes.Tooltips.Describe("0x7680061", "Sound_Effect", "SFX", "0", 1);
        Console.WriteLine("     tooltip: " + tip.Replace("\n", " / "));
        True("tooltip: the tone", tip.Contains("Sound 0x07680061: snd_se_Gekkouga_IceBoom"));
        True("tooltip: row / label / tone", tip.Contains("row 0x768, label 97, tone 110"));
        True("tooltip: volume", tip.Contains("volume +4.0 dB"));
        True("tooltip: the alias", tip.Contains("Alias: Creeper boom (ice detonation)"));
        string tipC = Sm4shCommand.Classes.Tooltips.Describe("0x46", "Sound_Effect", "SFX", "0", 1);
        True("tooltip: a common id (" + tipC.Replace("\n", " / ") + ")", tipC.Contains("futtobi") && tipC.Contains("Alias: Strong hit"));
        string tipS = Sm4shCommand.Classes.Tooltips.Describe("0x803A0000", "Low_Voice_Clip", "Sequence", "0", 1);
        True("tooltip: a voice sequence", tipS.Contains("Voice sequence: set 0x3A, sequence 0"));
        True("tooltip: not on other parameters", !Sm4shCommand.Classes.Tooltips.Describe("0x7680061", "Hitbox", "Damage", "0", 4).Contains("IceBoom"));

        // ---- the filter (SoundViewer.Matches): name, alias, hex ID with / without 0x, any part, decimal, empty
        Func<string, List<string>> filt = f => fs.Fighter.Entries.Where(e => Sm4shCommand.GUI.SoundViewer.Matches(e, f)).Select(e => e.IdText).ToList();
        var all = fs.Fighter.Entries.Count;
        Check("filter: empty = every sound", filt("").Count, all);
        Check("filter: blanks = every sound", filt("   ").Count, all);
        Check("filter: name, any case", string.Join(",", filt("iceboom")), "0x07680061");
        Check("filter: part of a name", filt("_Sk").Count, 6);
        Check("filter: alias", string.Join(",", filt("CREEPER")), "0x07680061");
        Check("filter: hex with 0x, padded", string.Join(",", filt("0x07680061")), "0x07680061");
        Check("filter: hex with 0x, unpadded (as scripts show it)", string.Join(",", filt("0x7680061")), "0x07680061");
        Check("filter: hex without 0x", string.Join(",", filt("7680061")), "0x07680061");
        True("filter: partial id 0768 = his whole se row", filt("0768").Count == fs.Fighter.Entries.Count(e => e.Id.HasValue && e.Id.Value >> 16 == 0x768));
        True("filter: partial id 5B finds 0x0768005B", filt("5B").Contains("0x0768005B"));
        True("filter: 0x5B finds 0x0768005B", filt("0x5b").Contains("0x0768005B"));
        Check("filter: decimal id (124256353)", filt("124256353").Contains("0x07680061"), true);
        Check("filter: nothing matches", filt("zzzz_no_such_sound").Count, 0);
        Check("filter: common, by id", string.Join(",", fs.Common.Entries.Where(e => Sm4shCommand.GUI.SoundViewer.Matches(e, "0x61")).Where(e => e.Id == 0x61).Select(e => e.Name)), "snd_se_common_furafura");
        Check("filter: common, by alias", string.Join(",", fs.Common.Entries.Where(e => Sm4shCommand.GUI.SoundViewer.Matches(e, "strong hit")).Select(e => e.IdText)), "0x00000046");

        // ---- the lines Add to Script gives: they compile and round-trip
        foreach (var c in Sm4shCommand.GUI.SoundViewer.Commands)
            foreach (uint id in new uint[] { 0x07680061, 0x46 })
            {
                string line = Sm4shCommand.GUI.SoundViewer.CommandLine(c[0], id);
                var s = new ACMDScript(0x1234);
                string err = null;
                try { s.Serialize(line); } catch (Exception e) { err = e.Message; }
                Check(line + " compiles", err, null);
                if (err != null) continue;
                uint crc;
                ACMD_INFO.TryGetIdent(c[0], out crc);
                var cmd = (ACMDCommand)s.Commands[0];
                Check(line + ": its command and id", cmd.Ident.ToString("X8") + " " + Convert.ToUInt32(cmd.Parameters[0]).ToString("X"), crc.ToString("X8") + " " + id.ToString("X"));
                string text = s.Deserialize().Replace("\r", "").Split('\n').First(x => x.Trim().Length > 0).Trim();
                Check(line + ": decompiled the same", text, line);
                var s2 = new ACMDScript(0x1234);
                s2.Serialize(s.Deserialize());
                Check(line + ": recompiled the same bytes", Bytes(s2).SequenceEqual(Bytes(s)), true);
            }

        // ---- the sound commands' help and examples (acmd_ext_help.py VANILLA_HELP / VANILLA_EXAMPLES, v1.7.32): every
        // example block compiles and round-trips
        foreach (var name in new[] { "Sound_Effect", "Transient_Sound_Effect", "Stop_Sound_Effect" })
        {
            uint crc;
            ACMD_INFO.TryGetIdent(name, out crc);
            True(name + ": help on sound ids (v1.7.32)", ACMD_INFO.GetHelp(crc).Any(l => l.Contains("Sound ids (new in v1.7.32")));
            Check(name + ": still in Sound", ACMD_INFO.GetCategory(crc), "Sound");
            var blocks = new List<List<string>> { new List<string>() };
            foreach (var l in ACMD_INFO.GetExample(crc)) { if (l.Length == 0) blocks.Add(new List<string>()); else blocks.Last().Add(l); }
            int i = 0;
            foreach (var blk in blocks.Where(x => x.Count > 0))
            {
                i++;
                try
                {
                    var c1 = new ACMDScript(1); c1.Serialize(string.Join("\n", blk));
                    var c2 = new ACMDScript(1); c2.Serialize(c1.Deserialize());
                    Check(name + " example " + i + ": compiles, round-trips", Bytes(c2).SequenceEqual(Bytes(c1)), true);
                }
                catch (Exception e) { Check(name + " example " + i + ": compiles", e.Message, ""); }
            }
            Check(name + ": the game's example and ours", i, 2);
        }
        True("New Commands' group text lists the sound ids", ACMD_INFO.GetGroupHelp("New Commands").Any(l => l.Contains("Sound ids (Sm4shCommand v1.7.32")));

        if (gui) Gui(root, game, outDir, ini);
        Console.WriteLine(string.Format(IC, "{0} checks, {1} failures", oks + fails, fails));
        return fails;
    }

    static object Field(object o, string name)
    {
        return o.GetType().GetField(name, BindingFlags.NonPublic | BindingFlags.Instance).GetValue(o);
    }

    static void Gui(string root, string game, string outDir, string ini)
    {
        File.WriteAllText(ini, "SoundDataFolder = " + game + "\n");
        try
        {
            // (the script editor, FastColoredTextBox, can't be made under Mono: Add to Script's line is caught here)
            var inserted = new List<string>();
            var form = new Sm4shCommand.GUI.SoundViewer(root, () => null) { InsertLine = l => { inserted.Add(l); return true; } };
            form.StartPosition = FormStartPosition.Manual;
            form.Location = new Point(0, 0);
            form.CreateControl();
            form.Show();
            Application.DoEvents();
            Check("form: fighter rows = entries", form.FighterGrid.Rows.Count, form.Sounds.Fighter.Entries.Count);
            Check("form: common rows = entries", form.CommonGrid.Rows.Count, form.Sounds.Common.Entries.Count);
            True("form: tab titles count the rows", form.Tabs.TabPages[0].Text == "Fighter sounds (" + form.FighterGrid.Rows.Count + ")");
            var row = form.FighterGrid.Rows.Cast<DataGridViewRow>().First(r => (string)r.Cells["Id"].Value == "0x07680061");
            Check("form: the IceBoom row's columns", string.Join("|", Enumerable.Range(0, 10).Select(i => Convert.ToString(row.Cells[i].Value, IC))),
                  "0x07680061|snd_se_Gekkouga_IceBoom|Creeper boom (ice detonation)|se|" + (form.Sounds.Fighter.Entries.First(e => e.Id == 0x07680061).Tone.Seconds).ToString("0.000", IC) + "||1|48000|+4.0|110");
            form.Filter.Text = "IceBoom";
            Application.DoEvents();
            Check("form: filter", form.FighterGrid.Rows.Count, 1);
            form.Filter.Text = "creeper";
            Application.DoEvents();
            Check("form: filter finds aliases", form.FighterGrid.Rows.Count, 1);
            form.FighterGrid.CurrentCell = form.FighterGrid.Rows[0].Cells["Name"];
            Application.DoEvents();
            True("form: info line", ((Label)Field(form, "info")).Text.Contains("tone 110 of snd_se_Gekkouga.nus3bank"));
            // alias typed in the list
            form.FighterGrid.Rows[0].Cells["Alias"].Value = "Ice boom";
            typeof(Sm4shCommand.GUI.SoundViewer).GetMethod("AliasEdited", BindingFlags.NonPublic | BindingFlags.Instance)
                .Invoke(form, new object[] { form.FighterGrid, 0, form.FighterGrid.Columns["Alias"].Index });
            Check("form: alias edit saved", SoundAliases.Get("gekkouga", 0x07680061), "Ice boom");
            Check("form: the edited row stays while filtered (its alias no longer has 'creeper')", form.FighterGrid.Rows.Count, 1);
            Check("form: still picked", form.Selected != null ? form.Selected.IdText : null, "0x07680061");
            form.Filter.Text = "";
            Application.DoEvents();
            Check("form: filter cleared: every row", form.FighterGrid.Rows.Count, form.Sounds.Fighter.Entries.Count);
            Check("form: the pick kept through the filter", form.Selected != null ? form.Selected.IdText : null, "0x07680061");
            form.Filter.Text = "0x768006";
            Application.DoEvents();
            Check("form: filter by hex id (0x768006: 0x0768006x)", form.FighterGrid.Rows.Count, 2);
            Check("form: the pick kept (it matches)", form.Selected != null ? form.Selected.IdText : null, "0x07680061");
            // Add to Script: the line below the caret
            typeof(Sm4shCommand.GUI.SoundViewer).GetMethod("AddToScript", BindingFlags.NonPublic | BindingFlags.Instance).Invoke(form, null);
            Check("form: Add to Script", string.Join("|", inserted), "Sound_Effect(SFX=0x7680061)");
            form.CommandBox.SelectedIndex = 1;
            form.Filter.Text = "";
            Application.DoEvents();
            form.Tabs.SelectedIndex = 1;
            Application.DoEvents();
            var crow = form.CommonGrid.Rows.Cast<DataGridViewRow>().First(r => (string)r.Cells["Id"].Value == "0x00000061");
            form.CommonGrid.CurrentCell = crow.Cells["Name"];
            Application.DoEvents();
            typeof(Sm4shCommand.GUI.SoundViewer).GetMethod("AddToScript", BindingFlags.NonPublic | BindingFlags.Instance).Invoke(form, null);
            Check("form: Add to Script, a common looping sound as Transient_Sound_Effect", inserted.Last(), "Transient_Sound_Effect(SFX=0x61)");
            var wav = form.PreviewWav(form.Selected);
            True("form: the preview WAV (looped furafura, ~8 s)", BitConverter.ToInt32(wav, 40) / 2 >= 8 * 47996);
            // pictures (offscreen)
            form.Tabs.SelectedIndex = 0;
            form.Filter.Text = "Sk";
            Application.DoEvents();
            form.FighterGrid.CurrentCell = form.FighterGrid.Rows[0].Cells["Name"];
            Application.DoEvents();
            foreach (var shot in new[] { "viewer_fighter", "viewer_common" })
            {
                if (shot == "viewer_common") { form.Filter.Text = "common_"; form.Tabs.SelectedIndex = 1; Application.DoEvents(); }
                for (int i = 0; i < 20; i++) { Application.DoEvents(); System.Threading.Thread.Sleep(25); }
                using (var bmp = new Bitmap(form.Width, form.Height))
                {
                    // (Mono's DrawToBitmap draws only the background: the form as the X server shows it)
                    using (var gr = Graphics.FromImage(bmp))
                        gr.CopyFromScreen(form.Location, Point.Empty, form.Size);
                    bmp.Save(Path.Combine(outDir, shot + ".png"), System.Drawing.Imaging.ImageFormat.Png);
                }
            }
            True("form: pictures written", File.Exists(Path.Combine(outDir, "viewer_fighter.png")));
            form.Close();
        }
        finally { File.Delete(ini); }
    }
}
