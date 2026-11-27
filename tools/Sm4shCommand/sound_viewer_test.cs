// The Sound Effect Viewer (Sm4shCommand v1.7.32), headless (Mono): nus3bank / soundlabeltable reading and rebuilding,
// sound ids, the DSP-ADPCM decoder (its PCM written for sound_viewer_test.py to check against its own decoder and the
// user's mp3), previews / WAV, aliases, the editor tooltip, the inserted command lines (compile + round trip), part 2's
// label-table writer; with --gui (Xvfb) the form: lists, filter, alias edit, Add to Script, and a picture of it.
// Run through sound_viewer_test.py. Build (next to the built SM4SHCommand.exe / SALT.dll): csc -out:SvTest.exe
// -r:SALT.dll -r:SM4SHCommand.exe -r:<mono 4.5>/mscorlib.dll -r:<mono 4.5>/System.dll -r:<mono 4.5>/System.Core.dll
// -r:<mono 4.5>/System.Windows.Forms.dll -r:<mono 4.5>/System.Drawing.dll -nostdlib sound_viewer_test.cs
// Run: mono SvTest.exe Events.cfg FIGHTER_ROOT GAME_DATA PORT_ROOT OUT_DIR [--gui] [--adder IN_DIR]
//   --adder IN_DIR  v1.7.33's Sound Adder (AdderTests, AdderGui): IN_DIR's audio files (sound_viewer_test.py makes them
//                   with ffmpeg: 44.1 kHz WAVs mono / stereo / 24-bit / float, a padded one, an mp3, a flac)
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

        int ai = Array.IndexOf(args, "--adder");
        string adderIn = ai >= 0 && ai + 1 < args.Length ? args[ai + 1] : null;
        if (adderIn != null) AdderTests(root, game, port, outDir, adderIn);
        if (gui) Gui(root, game, outDir, ini);
        if (gui && adderIn != null) AdderGui(root, game, outDir, adderIn, ini);
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

    // ======================================================================== v1.7.33: the Sound Adder

    static double Corr(short[] a, short[] b, int channels, int c)
    {
        int n = Math.Min(a.Length, b.Length) / channels;
        double sa = 0, sb = 0, saa = 0, sbb = 0, sab = 0;
        for (int i = 0; i < n; i++)
        {
            double x = a[i * channels + c], y = b[i * channels + c];
            sa += x; sb += y; saa += x * x; sbb += y * y; sab += x * y;
        }
        double cov = sab - sa * sb / n, va = saa - sa * sa / n, vb = sbb - sb * sb / n;
        return cov / Math.Sqrt(va * vb);
    }

    static void WriteS16(string path, short[] pcm)
    {
        var b = new byte[pcm.Length * 2];
        Buffer.BlockCopy(pcm, 0, b, 0, b.Length);
        File.WriteAllBytes(path, b);
    }

    static int BE(byte[] b, int at) { return b[at] << 24 | b[at + 1] << 16 | b[at + 2] << 8 | b[at + 3]; }

    // the sections of a bank: name -> (body offset, size), as the test reads them (not Nus3Bank's)
    static Dictionary<string, int[]> Secs(byte[] d)
    {
        var r = new Dictionary<string, int[]>();
        int n = BitConverter.ToInt32(d, 20), q = 24 + 8 * n;
        for (int i = 0; i < n; i++)
        {
            string nm = System.Text.Encoding.ASCII.GetString(d, 24 + 8 * i, 4);
            int sz = BitConverter.ToInt32(d, 28 + 8 * i);
            r[nm] = new[] { q + 8, sz };
            q += 8 + sz;
        }
        return r;
    }

    static bool Same(byte[] a, int ao, byte[] b, int bo, int n)
    {
        for (int i = 0; i < n; i++) if (a[ao + i] != b[bo + i]) return false;
        return true;
    }

    static void CopyTo(string src, string dst)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(dst));
        File.Copy(src, dst, true);
    }

    // a fighter folder copy: DIR/data/fighter/NAME/sound/<banks>, DIR/data/sound/config/soundlabeltable.bin (when table)
    static string Stage(string dir, string name, IEnumerable<string> banks, string table)
    {
        if (Directory.Exists(dir)) Directory.Delete(dir, true);
        string froot = Path.Combine(Path.Combine(Path.Combine(dir, "data"), "fighter"), name);
        foreach (var b in banks) CopyTo(b, Path.Combine(Path.Combine(froot, "sound"), Path.GetFileName(b)));
        if (table != null) CopyTo(table, Path.Combine(Path.Combine(Path.Combine(Path.Combine(dir, "data"), "sound"), "config"), "soundlabeltable.bin"));
        return froot;
    }

    static void AdderTests(string root, string game, string port, string outDir, string inDir)
    {
        Console.WriteLine("---- v1.7.33: the Sound Adder");
        AudioImport.UseMediaFoundation = false;         // (Windows only; not here)
        string ad = Path.Combine(outDir, "adder");
        if (Directory.Exists(ad)) Directory.Delete(ad, true);
        Directory.CreateDirectory(ad);
        var manifest = new List<string>();
        Func<string, string> input = f => Path.Combine(inDir, f);

        // ---- encoding: WAV (44.1 kHz) -> 48 kHz -> DSP-ADPCM IDSP -> decoded back
        foreach (var t in new[] { new object[] { "mono44.wav", 1 }, new object[] { "stereo44.wav", 2 } })
        {
            string f = (string)t[0];
            int ch = (int)t[1];
            var src = AudioImport.Read(input(f));
            True(f + ": read natively (" + src.How + ")", src.How.StartsWith("WAV (16-bit PCM, 44100 Hz)"));
            Check(f + ": channels", src.Channels, ch);
            var p = new PendingSound { Source = input(f), Trim = false, Normalize = false };
            var sw = System.Diagnostics.Stopwatch.StartNew();
            p.Prepare();
            Console.WriteLine(string.Format(IC, "     {0}: {1} frames at 44.1 kHz -> {2} at 48 kHz, encoded in {3} ms ({4})", f, src.Frames, p.Samples, sw.ElapsedMilliseconds, p.How));
            Check(f + ": 48 kHz frames = 44.1 kHz frames x 48000 / 44100", p.Samples, (int)Math.Round(src.Frames * 48000.0 / 44100));
            Check(f + ": channels kept", p.Channels, ch);
            var h = Idsp.Header(p.Idsp);
            Check(f + ": IDSP header", string.Format(IC, "{0} {1} {2} {3:X} {4:X} {5:X} {6:X} {7}", h.Channels, h.SampleRate, h.Samples, h.Interleave, h.HeaderSize, h.ChannelHeaderSize, h.DataOffset, h.Loops),
                  string.Format(IC, "{0} 48000 {1} 10 40 60 {2:X} False", ch, p.Samples, 0x40 + 0x60 * ch));
            int frames = (p.Samples + 13) / 14;
            Check(f + ": data size per channel (an even frame count, as vanilla)", h.DataSize, (frames + (frames & 1)) * 8);
            Check(f + ": file size", p.Idsp.Length, 0x40 + 0x60 * ch + ch * h.DataSize);
            Check(f + ": DSP header: nibbles, loop flag 0, start / end nibbles, current 2", string.Format(IC, "{0} {1} {2} {3} {4}", BE(p.Idsp, 0x44), BE(p.Idsp, 0x4C) >> 16, BE(p.Idsp, 0x50), BE(p.Idsp, 0x54), BE(p.Idsp, 0x58)),
                  string.Format(IC, "{0} 0 2 {1} 2", IdspWriter.Nibble(p.Samples - 1) + 1, IdspWriter.Nibble(p.Samples - 1)));
            var dec = Idsp.Decode(p.Idsp);
            Check(f + ": decodes to its length", dec.Samples, p.Samples);
            for (int c = 0; c < ch; c++)
            {
                double r = Corr(dec.Pcm, p.Pcm, ch, c);
                True(string.Format(IC, "{0}: channel {1}: decoded vs the 48 kHz PCM encoded, r {2:0.00000} > 0.99", f, c, r), r > 0.99);
            }
            string stem = Path.Combine(ad, Path.GetFileNameWithoutExtension(f));
            WriteS16(stem + ".pcm48.s16", p.Pcm);
            WriteS16(stem + ".dec.s16", dec.Pcm);
            File.WriteAllBytes(stem + ".idsp", p.Idsp);
            manifest.Add(string.Join("\t", new[] { "encode", f, ch.ToString(IC), stem }));
        }
        // a looping one: the DSP header's loop, the loop frame's ps, the whole clip looped
        {
            var p = new PendingSound { Source = input("mono44.wav"), Loop = true };
            p.Prepare();
            var h = Idsp.Header(p.Idsp);
            Check("loop: IDSP loop points 0 .. n - 1, loops", h.LoopStart + " " + h.LoopEnd + " " + h.Loops, "0 " + (p.Samples - 1) + " True");
            Check("loop: DSP header loop flag, start nibble 2, end nibble, loop ps = the first frame's", string.Format(IC, "{0} {1} {2} {3}", BE(p.Idsp, 0x4C) >> 16, BE(p.Idsp, 0x50), BE(p.Idsp, 0x54), (BE(p.Idsp, 0x84) >> 16) & 0xFF),
                  string.Format(IC, "1 2 {0} {1}", IdspWriter.Nibble(p.Samples - 1), p.Idsp[0xA0]));
            var clip = Idsp.Decode(p.Idsp);
            Check("loop: preview loops ~8 s", Idsp.Preview(clip, 0, 8).Length >= 8 * 48000, true);
            Check("loop: normalised peak (-0.5 dBFS = 30930)", p.Pcm.Max(x => Math.Abs((int)x)), (int)Math.Round(Math.Pow(10, -0.5 / 20) * 32767));
        }
        // other WAV forms: 24-bit, float, a 22.05 kHz one (upsampled x 2.18); the same sound as the 16-bit one
        {
            var a16 = AudioImport.Read(input("mono44.wav"));
            foreach (var f in new[] { "mono44_s24.wav", "mono44_f32.wav" })
            {
                var a = AudioImport.Read(input(f));
                double maxd = 0;
                for (int i = 0; i < a.Samples.Length; i++) maxd = Math.Max(maxd, Math.Abs(a.Samples[i] - a16.Samples[i]));
                True(f + ": read (" + a.How + "), the 16-bit file's samples within 1 LSB (" + (maxd * 32768).ToString("0.00", IC) + ")", a.Frames == a16.Frames && maxd * 32768 <= 1.01);
            }
            var lo = new PendingSound { Source = input("mono22.wav"), Trim = false, Normalize = false };
            lo.Prepare();
            Check("22.05 kHz -> 48 kHz frames", lo.Samples, (int)Math.Round(AudioImport.Read(input("mono22.wav")).Frames * 48000.0 / 22050));
            WriteS16(Path.Combine(ad, "mono22.pcm48.s16"), lo.Pcm);
            manifest.Add(string.Join("\t", new[] { "resample", "mono22.wav", "1", Path.Combine(ad, "mono22") }));
        }
        // trimming: 0.5 s of silence before, 0.3 s after (sound_viewer_test.py's padded.wav)
        {
            var raw = new PendingSound { Source = input("padded.wav"), Trim = false, Normalize = false };
            raw.Prepare();
            var cut = new PendingSound { Source = input("padded.wav"), Trim = true, Normalize = false };
            cut.Prepare();
            int removed = raw.Samples - cut.Samples;
            True(string.Format(IC, "trim: {0} frames (~0.8 s) of silence cut ({1:0.000} s)", removed, removed / 48000.0), Math.Abs(removed / 48000.0 - 0.8) < 0.02);
            True("trim: the first frame isn't silent", Math.Abs((int)cut.Pcm[0]) * 1.0 >= Math.Pow(10, -45 / 20.0) * 32767 * 0.5);
        }
        // other formats through ffmpeg (on PATH here): an mp3 and a flac
        foreach (var f in new[] { "ding.mp3", "mono44.flac", "stereo44.ogg" })
        {
            var a = AudioImport.Read(input(f));
            True(f + ": read through ffmpeg (" + a.How + ")", a.How.StartsWith("ffmpeg (") && a.Frames > 1000);
        }
        {
            var flac = AudioImport.Read(input("mono44.flac"));
            var wav = AudioImport.Read(input("mono44.wav"));
            True("flac: the wav's samples (lossless)", flac.Frames == wav.Frames && flac.Samples.SequenceEqual(wav.Samples));
        }
        // no decoder: a clear message (ffmpeg turned off)
        {
            AudioImport.FfmpegPath = Path.Combine(ad, "no_such_ffmpeg");
            string msg = "";
            try { AudioImport.Read(input("ding.mp3")); } catch (Exception e) { msg = e.Message; }
            True("no ffmpeg: an mp3 can't be read, the message says to convert it (" + msg + ")", msg.Contains("Convert it to a WAV first"));
            AudioImport.FfmpegPath = null;
        }

        // ---- adding 3 tones to the user's snd_se_Gekkouga (111 tones) and the label table (row 0x768, 98 labels)
        string sePath = Path.Combine(Path.Combine(root, "sound"), "snd_se_Gekkouga.nus3bank");
        string stbPath = FighterSounds.FindData(root, Path.Combine(Path.Combine("sound", "config"), "soundlabeltable.bin"), null, out bool fp);
        string froot = Stage(Path.Combine(ad, "a"), "gekkouga", new[] { sePath }, stbPath);
        var fs = FighterSounds.Load(froot, game);
        var adder = new SoundAdder(fs);
        Check("adder: target = the se bank", Path.GetFileName(adder.Target.Path), "snd_se_Gekkouga.nus3bank");
        Check("adder: its row", adder.Row, 0x768);
        Check("adder: the default tone name (the bank's prefix)", PendingSound.DefaultName(adder.Target, "C:\\sounds\\Ice Boom 2.wav"), "snd_se_Gekkouga_Ice_Boom_2");
        var tpl = SoundAdder.Template(adder.Target, 1);
        Check("adder: the TONE template (fighter_own_bank.py's)", tpl.Name, "snd_se_Gekkouga_Special_L01");
        adder.Pending.Add(new PendingSound { Source = input("mono44.wav"), ToneName = "snd_se_Gekkouga_AddMono", Alias = "Added mono", VolumeDb = -2f });
        adder.Pending.Add(new PendingSound { Source = input("stereo44.wav"), ToneName = "snd_se_Gekkouga_AddStereo", Alias = "Added stereo", VolumeDb = 1.5f });
        adder.Pending.Add(new PendingSound { Source = input("ding.mp3"), ToneName = "snd_se_Gekkouga_AddLoop", Alias = "Added loop", VolumeDb = -6f, Loop = true });
        adder.Plan();
        Check("plan: no problems (" + string.Join("; ", adder.PlanErrors) + ")", adder.PlanErrors.Count, 0);
        Check("plan: ids", string.Join(",", adder.Pending.Select(p => p.Id.ToString("X8"))), "07680062,07680063,07680064");
        Check("plan: labels", string.Join(",", adder.Pending.Select(p => p.Label)), "98,99,100");
        Check("plan: tone indexes", string.Join(",", adder.Pending.Select(p => p.ToneIndex)), "111,112,113");
        var usedBefore = fs.Table.UsedIds();
        True("plan: the new ids are in use nowhere in the table (" + usedBefore.Count + " ids in use, every row)", adder.Pending.All(p => !usedBefore.Contains(p.Id)));
        Check("plan: the new ids are distinct", adder.Pending.Select(p => p.Id).Distinct().Count(), 3);
        True("plan: none of the ids of any port's alias rows (SoundBanks.txt) either", adder.Pending.All(p => !FighterSounds.LoadBankAliases(Path.Combine(Path.Combine(Application.StartupPath, "Viewer"), "SoundBanks.txt"))
            .Values.Distinct().Select(a => fs.Table.RowOf(a)).Where(r => r >= 0).SelectMany(r => Enumerable.Range(0, fs.Table.Labels(r).Length).Select(l => SoundLabelTable.SoundId(r, l))).Contains(p.Id)));
        var pend = adder.PendingEntries();
        Check("plan: pending entries listed as new / unsaved", string.Join("|", pend.Select(e => e.IdText + " " + e.Name + " " + e.Note)),
              "0x07680062 snd_se_Gekkouga_AddMono new / unsaved|0x07680063 snd_se_Gekkouga_AddStereo new / unsaved|0x07680064 snd_se_Gekkouga_AddLoop new / unsaved");
        True("plan: pending entries playable (their audio in memory)", pend.All(e => e.Playable) && Idsp.Decode(e0(pend).Bank.ReadAudio(e0(pend).Tone)).Samples == adder.Pending[0].Samples);
        Check("plan: a pending alias isn't written before saving", SoundAliases.Get("gekkouga", 0x07680062), "");
        Check("plan: pending tone volume", pend[1].Tone.VolumeDb, 1.5f);
        Check("plan: the looping one loops, stereo one has 2 channels", pend[2].Tone.Loops + " " + pend[1].Tone.Channels, "True 2");
        // the lines Add to Script gives for a new tone compile and round-trip
        foreach (var line in new[] { Sm4shCommand.GUI.SoundViewer.CommandLine("Sound_Effect", adder.Pending[0].Id), Sm4shCommand.GUI.SoundViewer.CommandLine("Transient_Sound_Effect", adder.Pending[2].Id),
                                     Sm4shCommand.GUI.SoundViewer.CommandLine("Stop_Sound_Effect", adder.Pending[2].Id) })
        {
            var s1 = new ACMDScript(1);
            string err = null;
            try { s1.Serialize(line); } catch (Exception e) { err = e.Message; }
            Check("new tone's line " + line + " compiles", err, null);
            if (err != null) continue;
            var s2 = new ACMDScript(1);
            s2.Serialize(s1.Deserialize());
            Check("new tone's line " + line + ": decompiles the same", s1.Deserialize().Replace("\r", "").Split('\n').First(x => x.Trim().Length > 0).Trim(), line);
            Check("new tone's line " + line + ": recompiles the same bytes", Bytes(s2).SequenceEqual(Bytes(s1)), true);
        }

        var built = adder.Build();
        Check("build: no problems (" + string.Join("; ", built.Problems) + ")", built.Ok, true);
        foreach (var c in built.Checks) Console.WriteLine("     " + c);
        string outRoot = Path.Combine(ad, "out");
        var saved = adder.Save(outRoot);
        string newBank = Path.Combine(Path.Combine(Path.Combine(Path.Combine(outRoot, "fighter"), "gekkouga"), "sound"), "snd_se_Gekkouga.nus3bank");
        string newTable = Path.Combine(Path.Combine(Path.Combine(outRoot, "sound"), "config"), "soundlabeltable.bin");
        Check("save to folder: the files, laid out as the game's", string.Join("|", saved.Written.Select(w => w.Substring(outRoot.Length + 1).Replace('\\', '/'))),
              "fighter/gekkouga/sound/snd_se_Gekkouga.nus3bank|sound/config/soundlabeltable.bin");
        Check("save to folder: nothing to back up there", saved.Backups.Count, 0);
        Check("save: the pending cleared", adder.Pending.Count, 0);
        // the bytes, compared here (not with BankCheck's code)
        var od = File.ReadAllBytes(sePath);
        var nd = File.ReadAllBytes(newBank);
        var os = Secs(od);
        var ns = Secs(nd);
        Check("bank: the same sections, in vanilla's order", string.Join(",", ns.Keys), "PROP,BINF,GRP ,DTON,TONE,JUNK,PACK");
        foreach (var nm in new[] { "PROP", "BINF", "GRP ", "DTON" })
            True("bank: " + nm.Trim() + " byte for byte", os[nm][1] == ns[nm][1] && Same(od, os[nm][0], nd, ns[nm][0], os[nm][1]));
        Check("bank: NUS3 size", BitConverter.ToInt32(nd, 4), nd.Length - 8);
        Check("bank: TONE count 111 + 3", BitConverter.ToInt32(nd, ns["TONE"][0]), 114);
        int oldEntries = 0;
        for (int i = 0; i < 111; i++)
        {
            int oo = BitConverter.ToInt32(od, os["TONE"][0] + 4 + 8 * i), osz = BitConverter.ToInt32(od, os["TONE"][0] + 8 + 8 * i);
            int no = BitConverter.ToInt32(nd, ns["TONE"][0] + 4 + 8 * i), nsz = BitConverter.ToInt32(nd, ns["TONE"][0] + 8 + 8 * i);
            if (osz == nsz && Same(od, os["TONE"][0] + oo, nd, ns["TONE"][0] + no, osz)) oldEntries++;
        }
        Check("bank: the 111 old TONE entries byte for byte", oldEntries, 111);
        True("bank: the old PACK byte for byte at PACK's start (" + os["PACK"][1] + " bytes)", Same(od, os["PACK"][0], nd, ns["PACK"][0], os["PACK"][1]));
        Check("bank: PACK's body at a multiple of 0x10 (vanilla's; the user's was at +0x1C)", ns["PACK"][0] % 16, 0);
        Check("bank: JUNK sized for it", ns["JUNK"][1] % 4 + " " + (ns["JUNK"][1] >= 4), "0 True");
        Check("bank: BankCheck (the layout rules)", string.Join("; ", BankCheck.Validate(nd, 111)), "");
        var back = Nus3Bank.Load(newBank);
        Check("bank reloads: tones", back.Tones.Count, 114);
        for (int k = 0; k < 3; k++)
        {
            var t = back.Tones[111 + k];
            var dec = Idsp.Decode(back.ReadAudio(t));
            True(string.Format(IC, "bank reloads: tone {0} {1}: {2} ch, {3} Hz, {4} samples, volume {5}, loops {6}, decodes", 111 + k, t.Name, t.Channels, t.SampleRate, t.Samples, t.VolumeDb, t.Loops),
                 dec.Samples == t.Samples && t.SampleRate == 48000 && t.Codec == "IDSP");
            manifest.Add(string.Join("\t", new[] { "tone", newBank, (111 + k).ToString(IC), t.Name, t.Channels.ToString(IC), t.Loops ? "1" : "0", t.VolumeDb.ToString("R", IC) }));
        }
        Check("bank reloads: names / volumes", string.Join(",", back.Tones.Skip(111).Select(t => t.Name.Replace("snd_se_Gekkouga_", "") + " " + t.VolumeDb.ToString(IC))), "AddMono -2,AddStereo 1.5,AddLoop -6");
        Check("bank reloads: the old tones the same", string.Join(",", back.Tones.Take(111).Select(t => t.Name + t.VolumeDb + t.DataOffset)),
              string.Join(",", Nus3Bank.Load(sePath).Tones.Select(t => t.Name + t.VolumeDb + t.DataOffset)));
        var ot = File.ReadAllBytes(stbPath);
        var nt = File.ReadAllBytes(newTable);
        var otab = SoundLabelTable.Parse(ot);
        var ntab = SoundLabelTable.Parse(nt);
        int sameRows = 0;
        for (int r = 0; r < otab.Rows.Count; r++) if (r != 0x768 && Same(ot, 16 + 16 * r, nt, 16 + 16 * r, 16)) sameRows++;
        Check("table: the other 3251 rows byte for byte", sameRows, 3251);
        int pool = 16 + 16 * otab.Rows.Count;
        True("table: the old label words byte for byte (the row's new list appended)", Same(ot, pool, nt, pool, ot.Length - pool) && nt.Length == ot.Length + 4 * 101);
        Check("table: row 0x768 = its 98 labels + 111, 112, 113", string.Join(",", ntab.Labels(0x768)), string.Join(",", otab.Labels(0x768).Concat(new[] { 111, 112, 113 })));
        Check("table: the header", Same(ot, 0, nt, 0, 16), true);
        manifest.Add(string.Join("\t", new[] { "table", stbPath, newTable, "1896" }));
        // the viewer's model loads them back
        var fsb = FighterSounds.Load(saved.FighterRoot, game);
        Check("reload: the saved folder's own table", fsb.TablePath, newTable);
        var byId = fsb.Fighter.Entries.Where(e => e.Id.HasValue).ToDictionary(e => e.Id.Value, e => e);
        Check("reload: 0x07680062 / 63 / 64", string.Join(",", new uint[] { 0x07680062, 0x07680063, 0x07680064 }.Select(i => byId.ContainsKey(i) ? byId[i].Name : "-")),
              "snd_se_Gekkouga_AddMono,snd_se_Gekkouga_AddStereo,snd_se_Gekkouga_AddLoop");
        Check("reload: the old ids the same (0x07680061 IceBoom)", byId[0x07680061].Name, "snd_se_Gekkouga_IceBoom");
        Check("reload: the aliases written", string.Join(",", new uint[] { 0x07680062, 0x07680063, 0x07680064 }.Select(i => SoundAliases.Get("gekkouga", i))), "Added mono,Added stereo,Added loop");
        Check("reload: the new tones all have ids (as many tones without a label as before)", fsb.Fighter.Entries.Count(e => !e.Id.HasValue && e.Tone != null && e.Tone.HasAudio),
              FighterSounds.Load(froot, game).Fighter.Entries.Count(e => !e.Id.HasValue && e.Tone != null && e.Tone.HasAudio));

        // ---- in place: the fighter's folder and its own table, backups first
        string frootB = Stage(Path.Combine(ad, "b"), "gekkouga", new[] { sePath }, stbPath);
        var adderB = new SoundAdder(FighterSounds.Load(frootB, game));
        adderB.Pending.Add(new PendingSound { Source = input("mono44.wav"), ToneName = "snd_se_Gekkouga_InPlace" });
        var savedB = adderB.Save(null);
        Check("in place: written", savedB.Written.Count, 2);
        Check("in place: backed up first (FILE.yyyyMMdd-HHmmss.bak)", savedB.Backups.Count(b => System.Text.RegularExpressions.Regex.IsMatch(Path.GetFileName(b), @"\.\d{8}-\d{6}\.bak$")), 2);
        Check("in place: a new id's alias is the one given (none: the other copy's line for 0x07680062 goes)", SoundAliases.Get("gekkouga", 0x07680062), "");
        True("in place: the backups are the originals", File.ReadAllBytes(savedB.Backups[0]).SequenceEqual(od) && File.ReadAllBytes(savedB.Backups[1]).SequenceEqual(ot));
        True("in place: the table where it was (the mod's own)", savedB.Written[1] == FighterSounds.Load(frootB, game).TablePath);
        Check("in place: the backup isn't listed as a bank", FighterSounds.Load(frootB, game).Fighter.Banks.Count, 1);
        // a table from the picked game data: written as the mod's own (DATA/sound/config next to DATA/fighter), the picked one untouched
        string frootC = Stage(Path.Combine(ad, "c"), "gekkouga", new[] { sePath }, null);
        string pickedDir = Path.Combine(ad, "picked");
        CopyTo(stbPath, Path.Combine(Path.Combine(Path.Combine(pickedDir, "sound"), "config"), "soundlabeltable.bin"));
        var fsC = FighterSounds.Load(frootC, pickedDir);
        Check("picked table: found in the picked folder", fsC.TableFromPicked, true);
        var adderC = new SoundAdder(fsC);
        adderC.Pending.Add(new PendingSound { Source = input("mono44.wav"), ToneName = "snd_se_Gekkouga_Picked" });
        var savedC = adderC.Save(null);
        Check("picked table: written as the mod's own", savedC.Written[1], Path.Combine(Path.Combine(Path.Combine(Path.Combine(ad, "c"), "data"), "sound"), Path.Combine("config", "soundlabeltable.bin")));
        True("picked table: the picked one untouched", File.ReadAllBytes(Path.Combine(Path.Combine(Path.Combine(pickedDir, "sound"), "config"), "soundlabeltable.bin")).SequenceEqual(ot));
        Check("picked table: found next time (the mod's)", FighterSounds.Load(frootC, pickedDir).TableFromPicked, false);

        // ---- a volume change: only that float
        string frootV = Stage(Path.Combine(ad, "v"), "gekkouga", new[] { sePath }, stbPath);
        var fsV = FighterSounds.Load(frootV, game);
        var adderV = new SoundAdder(fsV);
        var step = fsV.Fighter.Banks[0].Tones[0];
        adderV.SetVolume(step, -3.25f);
        Check("volume: one change pending", adderV.VolumeEdits.Count, 1);
        var bv = adderV.Build();
        Check("volume: no problems (" + string.Join("; ", bv.Problems) + ")", bv.Ok, true);
        Check("volume: the table unchanged (not written)", bv.Table == null, true);
        var vd = bv.Banks.Values.First();
        int diffs = 0, outside = 0;
        int entryAt = Secs(od)["TONE"][0] + BitConverter.ToInt32(od, Secs(od)["TONE"][0] + 4);
        int floatAt = entryAt + step.DataBlock + 12;
        for (int i = 0; i < od.Length; i++) if (od[i] != vd[i]) { diffs++; if (i < floatAt || i >= floatAt + 4) outside++; }
        True("volume: same size, only its float's bytes differ (" + diffs + " bytes, " + outside + " outside it)", vd.Length == od.Length && diffs >= 1 && outside == 0);
        Check("volume: the float", BitConverter.ToSingle(vd, floatAt), -3.25f);
        adderV.SetVolume(step, -6.5f);
        Check("volume: set back: no change pending", adderV.VolumeEdits.Count, 0);
        adderV.SetVolume(step, 2f);
        adderV.Discard();
        Check("volume: discarded: as loaded", step.VolumeDb + " " + adderV.VolumeEdits.Count, "-6.5 0");
        // a volume change and a new tone together; a volume change on a new (pending) tone
        adderV.SetVolume(step, -1f);
        adderV.Pending.Add(new PendingSound { Source = input("mono44.wav"), ToneName = "snd_se_Gekkouga_Both", VolumeDb = 0f });
        adderV.Plan();
        adderV.SetVolume(adderV.Pending[0].Tone, 3f);
        Check("volume: a pending tone's volume", adderV.Pending[0].VolumeDb + " " + adderV.VolumeEdits.Count, "3 1");
        var both = adderV.Build();
        Check("volume + new tone: no problems (" + string.Join("; ", both.Problems) + ")", both.Ok, true);
        var bb = Nus3Bank.Load(new MemoryStream(both.Banks.Values.First()), "x");
        Check("volume + new tone: both in the bank", bb.Tones[0].VolumeDb + " " + bb.Tones[111].VolumeDb + " " + bb.Tones[111].Name, "-1 3 snd_se_Gekkouga_Both");

        // ---- a full row: labels are the id's low 16 bits (65536 a row)
        var fsF = FighterSounds.Load(froot, game);
        var full = SoundLabelTable.Parse(fsF.Table.Build());
        var many = full.Labels(0x768).ToList();
        while (many.Count < 65534) many.Add(-1);
        full.SetLabels(0x768, many);
        fsF.Table = full;
        var adderF = new SoundAdder(fsF);
        for (int k = 0; k < 3; k++) adderF.Pending.Add(new PendingSound { Source = input("mono44.wav"), ToneName = "snd_se_Gekkouga_Full" + k });
        adderF.Plan();
        True("full row: 65534 labels + 3 refused (" + string.Join("; ", adderF.PlanErrors) + ")", adderF.PlanErrors.Any(e => e.Contains("is full") && e.Contains("room for 2 more")));
        True("full row: Build refuses", !adderF.Build().Ok);
        string err2 = "";
        try { adderF.Save(Path.Combine(ad, "full")); } catch (Exception e) { err2 = e.Message; }
        True("full row: Save refuses, nothing written", err2.StartsWith("Not saved") && !Directory.Exists(Path.Combine(ad, "full")));
        adderF.Pending.RemoveAt(2);
        adderF.Plan();
        Check("full row: 2 fit (labels 65534, 65535)", string.Join(",", adderF.Pending.Select(p => p.Id.ToString("X8"))) + " " + adderF.PlanErrors.Count, "0768FFFE,0768FFFF 0");
        // a bad name, a duplicate name
        adderF.Pending[1].ToneName = "snd_se_Gekkouga_IceBoom";
        adderF.Plan();
        True("plan: a name already in the bank refused", adderF.PlanErrors.Any(e => e.Contains("another tone is named")));
        adderF.Pending[1].ToneName = "snd se bad!";
        adderF.Plan();
        True("plan: a bad name refused", adderF.PlanErrors.Any(e => e.Contains("letters, digits and _")));

        // ---- costume banks: Master's port (se 46192 and se c01 46201, both on 2028's row through SoundBanks.txt)
        var aliases = FighterSounds.LoadBankAliases(Path.Combine(Path.Combine(Application.StartupPath, "Viewer"), "SoundBanks.txt"));
        string mstb = FighterSounds.FindData(port, Path.Combine(Path.Combine("sound", "config"), "soundlabeltable.bin"), null, out fp);
        string mse = Path.Combine(Path.Combine(port, "sound"), "snd_se_Master.nus3bank"), mc01 = Path.Combine(Path.Combine(port, "sound"), "snd_se_Master_c01.nus3bank");
        string mroot = Stage(Path.Combine(ad, "m"), "master", new[] { mse, mc01 }, mstb);
        var fsM = FighterSounds.Load(mroot, game, aliases);
        var adderM = new SoundAdder(fsM);
        Check("costume: target se (own id 46192)", adderM.Target.Id, 46192u);
        Check("costume: its row (2028's)", adderM.Row, fsM.Table.RowOf(2028));
        Check("costume: the costume bank on the row", string.Join(",", adderM.Costumes().Select(b => Path.GetFileName(b.Path))), "snd_se_Master_c01.nus3bank");
        True("costume: the row's other players named (" + string.Join("; ", adderM.RowSharers(aliases)) + ")", adderM.RowSharers(aliases).Any(x => x.Contains("2028")));
        adderM.Pending.Add(new PendingSound { Source = input("stereo44.wav"), ToneName = "snd_se_Master_Added", Alias = "Master added" });
        adderM.Plan();
        int mtone = adderM.Pending[0].ToneIndex;
        Check("costume: plan ok, the tone index past both banks' tones", adderM.PlanErrors.Count + " " + mtone, "0 " + Math.Max(fsM.Fighter.Banks[0].Tones.Count, fsM.Fighter.Banks[1].Tones.Count));
        var savedM = adderM.Save(Path.Combine(ad, "mout"));
        Check("costume: both banks and the table written", savedM.Written.Count, 3);
        var fsM2 = FighterSounds.Load(savedM.FighterRoot, game, aliases);
        var m0 = fsM2.Fighter.Banks.First(b => fsM2.Fighter.Kinds[b] == "se");
        var m1 = fsM2.Fighter.Banks.First(b => fsM2.Fighter.Kinds[b] == "se c01");
        True("costume: the tone in both at " + mtone + ", the same audio", m0.Tones[mtone].Name == "snd_se_Master_Added" && m1.Tones[mtone].Name == "snd_se_Master_Added" &&
             m0.ReadAudio(m0.Tones[mtone]).SequenceEqual(m1.ReadAudio(m1.Tones[mtone])));
        uint mid = adderM.Pending.Count == 0 ? SoundLabelTable.SoundId(fsM2.Table.RowOf(2028), fsM2.Table.Labels(fsM2.Table.RowOf(2028)).Length - 1) : 0;
        Check("costume: the id reaches it in both (se and se c01 entries)", string.Join(",", fsM2.Fighter.Entries.Where(e => e.Id == mid).Select(e => e.Kind + " " + e.Name)), "se snd_se_Master_Added,se c01 snd_se_Master_Added");
        foreach (var b in new[] { m0, m1 }) Check("costume: " + Path.GetFileName(b.Path) + " BankCheck", string.Join("; ", BankCheck.Validate(File.ReadAllBytes(b.Path), mtone)), "");
        Check("costume: the bank ids kept", m0.Id + " " + m1.Id, "46192 46201");
        manifest.Add(string.Join("\t", new[] { "tone", m1.Path, mtone.ToString(IC), "snd_se_Master_Added", "2", "0", "0" }));
        // costume banks off
        string mroot2 = Stage(Path.Combine(ad, "m2"), "master", new[] { mse, mc01 }, mstb);
        var adderM2 = new SoundAdder(FighterSounds.Load(mroot2, game, aliases)) { AlsoCostumes = false };
        adderM2.Pending.Add(new PendingSound { Source = input("mono44.wav"), ToneName = "snd_se_Master_MainOnly" });
        Check("costume off: only the main bank", adderM2.Build().Banks.Count, 1);

        // ---- the layout rules against vanilla banks (they must pass them)
        foreach (var v in new[] { Path.Combine(Path.Combine(Path.Combine(game, "sound"), "se"), "snd_se_joucyu.nus3bank"), Path.Combine(Path.Combine(root, "sound"), "snd_vc_Gekkouga.nus3bank"),
                                  Path.Combine(Path.Combine(root, "sound"), "snd_vc_Gekkouga_ouen.nus3bank") })
            Check("layout rules hold for vanilla " + Path.GetFileName(v), string.Join("; ", BankCheck.Validate(File.ReadAllBytes(v), int.MaxValue, true)), "");
        File.WriteAllLines(Path.Combine(ad, "manifest.txt"), manifest.ToArray());
        // (the staged copies a / b / c / v / m / m2 / picked are deleted by sound_viewer_test.py after its checks)
    }

    static SoundEntry e0(List<SoundEntry> l) { return l[0]; }

    static void Shot(Form form, string path)
    {
        for (int i = 0; i < 20; i++) { Application.DoEvents(); System.Threading.Thread.Sleep(25); }
        var r = form.RectangleToScreen(form.ClientRectangle);      // (no window manager under Xvfb: the client area is the window)
        using (var bmp = new Bitmap(r.Width, r.Height))
        {
            using (var gr = Graphics.FromImage(bmp)) gr.CopyFromScreen(r.Location, Point.Empty, r.Size);
            bmp.Save(path, System.Drawing.Imaging.ImageFormat.Png);
        }
    }

    static void AdderGui(string root, string game, string outDir, string inDir, string ini)
    {
        Console.WriteLine("---- v1.7.33: the Sound Adder's form");
        AudioImport.UseMediaFoundation = false;
        File.WriteAllText(ini, "SoundDataFolder = " + game + "\n");
        string ad = Path.Combine(outDir, "adder");
        string sePath = Path.Combine(Path.Combine(root, "sound"), "snd_se_Gekkouga.nus3bank");
        string stbPath = FighterSounds.FindData(root, Path.Combine(Path.Combine("sound", "config"), "soundlabeltable.bin"), null, out bool fp);
        string froot = Stage(Path.Combine(ad, "g"), "gekkouga", new[] { sePath, Path.Combine(Path.Combine(root, "sound"), "snd_vc_Gekkouga.nus3bank") }, stbPath);
        try
        {
            var inserted = new List<string>();
            var form = new Sm4shCommand.GUI.SoundViewer(froot, () => null) { InsertLine = l => { inserted.Add(l); return true; }, ConfirmSave = m => true };
            form.StartPosition = FormStartPosition.Manual;
            form.Location = new Point(0, 0);
            form.Show();
            Application.DoEvents();
            int before = form.FighterGrid.Rows.Count;
            Sm4shCommand.GUI.SoundAdderDialog seen = null;
            form.AdderDialogHook = dlg =>
            {
                seen = dlg;
                dlg.StartPosition = FormStartPosition.Manual;
                dlg.Location = new Point(0, 0);
                Application.DoEvents();
                Check("dialog: the bank picked (se)", dlg.BankBox.SelectedItem.ToString().StartsWith("se  snd_se_Gekkouga.nus3bank  (row 0x768, 98 labels, 111 tones)"), true);
                dlg.AddFiles(new[] { Path.Combine(inDir, "mono44.wav"), Path.Combine(inDir, "stereo44.wav"), Path.Combine(inDir, "ding.mp3") });
                Application.DoEvents();
                Check("dialog: 3 rows", dlg.Grid.Rows.Count, 3);
                Check("dialog: names prefilled", string.Join(",", dlg.Grid.Rows.Cast<DataGridViewRow>().Select(r => (string)r.Cells["Name"].Value)),
                      "snd_se_Gekkouga_mono44,snd_se_Gekkouga_stereo44,snd_se_Gekkouga_ding");
                Check("dialog: the planned ids", string.Join(",", dlg.Grid.Rows.Cast<DataGridViewRow>().Select(r => (string)r.Cells["Id"].Value)), "0x07680062,0x07680063,0x07680064");
                // a name and an alias typed, the volume on the slider / box, loop on for the mp3
                var g = dlg.Grid;
                Action<int, string, object> type = (row, col, val) =>
                {
                    g.Rows[row].Cells[col].Value = val;
                    typeof(Sm4shCommand.GUI.SoundAdderDialog).GetMethod("CellEdited", BindingFlags.NonPublic | BindingFlags.Instance).Invoke(dlg, new object[] { row, g.Columns[col].Index });
                    for (int i = 0; i < 5; i++) Application.DoEvents();
                };
                type(0, "Name", "snd_se_Gekkouga_IceCrack");
                type(0, "Alias", "Ice crack");
                type(1, "Alias", "Crowd stereo");
                type(2, "Name", "snd_se_Gekkouga_DingLoop");
                type(2, "Loop", true);
                g.CurrentCell = g.Rows[1].Cells["File"];
                Application.DoEvents();
                dlg.VolumeBox.Value = -4.5m;
                Application.DoEvents();
                Check("dialog: the volume box sets the sound's volume and the slider", dlg.Selected.VolumeDb + " " + dlg.VolumeBar.Value, "-4.5 -45");
                dlg.VolumeBar.Value = 20;
                typeof(Sm4shCommand.GUI.SoundAdderDialog).GetMethod("SetVolume", BindingFlags.NonPublic | BindingFlags.Instance).Invoke(dlg, new object[] { 2.0m });
                Check("dialog: the slider (+2 dB)", dlg.Selected.VolumeDb + " " + dlg.VolumeBox.Value, "2 2.0");
                Check("dialog: rows after the edits", string.Join("|", g.Rows.Cast<DataGridViewRow>().Select(r => r.Cells["Name"].Value + " " + r.Cells["Alias"].Value + " " + r.Cells["Loop"].Value + " " + r.Cells["Volume"].Value)),
                      "snd_se_Gekkouga_IceCrack Ice crack False 0.0|snd_se_Gekkouga_stereo44 Crowd stereo False +2.0|snd_se_Gekkouga_DingLoop  True 0.0");
                var wav = Sm4shCommand.GUI.SoundAdderDialog.PreviewWav(dlg.Selected);
                Check("dialog: the preview WAV (stereo, 48 kHz)", BitConverter.ToInt16(wav, 22) + " " + BitConverter.ToInt32(wav, 24), "2 48000");
                True("dialog: the plan line (" + dlg.PlanLabel.Text.Replace("\n", " / ") + ")", dlg.PlanLabel.Text.Contains("ids 0x07680062 - 0x07680064") && dlg.PlanLabel.Text.Contains("none of them in use"));
                Shot(dlg, Path.Combine(outDir, "adder_dialog.png"));
            };
            form.ShowAdder();
            Check("dialog: shown", seen != null, true);
            Application.DoEvents();
            Check("list: the 3 pending rows added", form.FighterGrid.Rows.Count, before + 3);
            var newRows = form.FighterGrid.Rows.Cast<DataGridViewRow>().Where(r => ((SoundEntry)r.Tag).Pending != null).ToList();
            Check("list: pending rows marked", string.Join("|", newRows.Select(r => r.Cells["Id"].Value + " " + r.Cells["Name"].Value + " " + r.Cells["Alias"].Value + " " + r.Cells["Note"].Value)),
                  "0x07680062 snd_se_Gekkouga_IceCrack Ice crack new / unsaved|0x07680063 snd_se_Gekkouga_stereo44 Crowd stereo new / unsaved|0x07680064 snd_se_Gekkouga_DingLoop  new / unsaved");
            // filter: by name and by id
            form.Filter.Text = "IceCrack";
            Application.DoEvents();
            Check("list: filter finds a pending one by name", form.FighterGrid.Rows.Count, 1);
            form.Filter.Text = "0x7680064";
            Application.DoEvents();
            Check("list: filter finds a pending one by id", form.FighterGrid.Rows.Count == 1 && (string)form.FighterGrid.Rows[0].Cells["Name"].Value == "snd_se_Gekkouga_DingLoop", true);
            form.FighterGrid.CurrentCell = form.FighterGrid.Rows[0].Cells["Name"];
            Application.DoEvents();
            // alias typed in the list for a pending row; preview; Add to Script
            string aliasBefore = SoundAliases.Get("gekkouga", 0x07680064);     // (the non-GUI part's save wrote one for this id)
            form.FighterGrid.Rows[0].Cells["Alias"].Value = "Ding loop";
            typeof(Sm4shCommand.GUI.SoundViewer).GetMethod("AliasEdited", BindingFlags.NonPublic | BindingFlags.Instance).Invoke(form, new object[] { form.FighterGrid, 0, form.FighterGrid.Columns["Alias"].Index });
            Check("list: a pending row's alias kept with it (written at Save)", form.Adder.Pending[2].Alias + "|" + SoundAliases.Get("gekkouga", 0x07680064), "Ding loop|" + aliasBefore);
            var pw = form.PreviewWav(form.Selected);
            True("list: a pending row previews (looped ~8 s)", BitConverter.ToInt32(pw, 40) / 2 >= 8 * 48000);
            form.CommandBox.SelectedIndex = 1;
            typeof(Sm4shCommand.GUI.SoundViewer).GetMethod("AddToScript", BindingFlags.NonPublic | BindingFlags.Instance).Invoke(form, null);
            Check("list: Add to Script with a new id", inserted.Last(), "Transient_Sound_Effect(SFX=0x7680064)");
            // an existing tone's volume typed in the Volume column
            form.Filter.Text = "0x07680061";
            Application.DoEvents();
            form.FighterGrid.Rows[0].Cells["Volume"].Value = "+1.5";
            typeof(Sm4shCommand.GUI.SoundViewer).GetMethod("VolumeEdited", BindingFlags.NonPublic | BindingFlags.Instance).Invoke(form, new object[] { form.FighterGrid, 0, form.FighterGrid.Columns["Volume"].Index });
            for (int i = 0; i < 5; i++) Application.DoEvents();
            Check("list: IceBoom's volume edited (unsaved)", form.Adder.VolumeEdits.Count + " " + form.FighterGrid.Rows[0].Cells["Note"].Value, "1 volume +4.0 -> +1.5 dB (unsaved)");
            form.Filter.Text = "";
            Application.DoEvents();
            form.Filter.Text = "snd_se_Gekkouga_";
            Application.DoEvents();
            var last = form.FighterGrid.Rows.Cast<DataGridViewRow>().Last(r => ((SoundEntry)r.Tag).Pending != null);
            Check("list: the new rows right after the bank's last id (IceBoom)", (string)form.FighterGrid.Rows[last.Index - 3].Cells["Id"].Value, "0x07680061");
            form.FighterGrid.FirstDisplayedScrollingRowIndex = Math.Max(0, last.Index - 15);
            form.FighterGrid.CurrentCell = last.Cells["Name"];
            Shot(form, Path.Combine(outDir, "adder_pending.png"));
            // Save to a folder: written, reloaded from there, the new ids listed as sounds
            string outRoot = Path.Combine(ad, "gout");
            var saved = form.SaveChanges(outRoot);
            Check("form: saved", saved != null && saved.Written.Count == 2, true);
            Check("form: the viewer shows the saved folder", form.Sounds.Root, Path.Combine(Path.Combine(outRoot, "fighter"), "gekkouga"));
            var ids = form.Sounds.Fighter.Entries.Where(e => e.Id.HasValue).ToDictionary(e => e.Id.Value, e => e);
            Check("form: after saving: the new sounds", string.Join(",", new uint[] { 0x07680062, 0x07680063, 0x07680064 }.Select(i => ids[i].Name + " " + ids[i].Tone.VolumeDb.ToString(IC) + " " + ids[i].Alias)),
                  "snd_se_Gekkouga_IceCrack 0 Ice crack,snd_se_Gekkouga_stereo44 2 Crowd stereo,snd_se_Gekkouga_DingLoop 0 Ding loop");
            Check("form: after saving: IceBoom's volume", ids[0x07680061].Tone.VolumeDb, 1.5f);
            Check("form: no pending left", form.FighterGrid.Rows.Cast<DataGridViewRow>().Count(r => ((SoundEntry)r.Tag).Pending != null), 0);
            form.Filter.Text = "snd_se_Gekkouga_";
            Application.DoEvents();
            var lastSaved = form.FighterGrid.Rows.Cast<DataGridViewRow>().First(r => (string)r.Cells["Id"].Value == "0x07680064");
            form.FighterGrid.FirstDisplayedScrollingRowIndex = Math.Max(0, lastSaved.Index - 15);
            form.FighterGrid.CurrentCell = lastSaved.Cells["Name"];
            Shot(form, Path.Combine(outDir, "adder_saved.png"));
            form.Close();
        }
        finally { File.Delete(ini); }
    }
}
