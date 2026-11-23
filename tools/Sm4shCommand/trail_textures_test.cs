// Sm4shCommand v1.7.31 (Mono): Corrin's new trail texture ids 272 / 273 (tools/kamui_trail_cave.py): Sword_Glow /
// Sword_Glow2's changed help and its examples (each compiles and comes back the same after decompile -> compile), the
// names table (TrailNames.cs), the value tooltips (Tooltips/trails.txt: the names in the texture parameters, Corrin's
// own first when she is open) and the Hitbox Viewer finding the textures in fighter/kamui/effect/kamui/trail.
// Run (next to SM4SHCommand.exe, its Events.cfg and Tooltips folder; tools/kamui_trail_cave_test.py --sm4shcommand
// builds and runs it): mono TtTest.exe Events.cfg FIGHTER_ROOT X Y ARGB
//   FIGHTER_ROOT: a folder fighter/kamui (with effect/kamui/trail/TexKamuiSwordTraceCyan(Add).nut); ARGB: the trail
//   texture's pixel (X, Y) as tools/nut.py read_ntp3 decodes it (hex)
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;
using Sm4shCommand.Classes;
using Sm4shCommand.Viewer;

class TtTest
{
    static int fails = 0, oks = 0;

    static void Check(string what, object got, object want)
    {
        bool ok = Equals(got, want);
        if (ok) oks++; else fails++;
        Console.WriteLine((ok ? "ok   " : "FAIL ") + what + (ok ? "" : $": got {got} (want {want})"));
    }

    static byte[] Bytes(ACMDScript s)
    {
        return s.Commands.Cast<ACMDCommand>().SelectMany(c => c.GetBytes(Endianness.Big)).ToArray();
    }

    static string Hex(byte[] b) { return BitConverter.ToString(b).Replace("-", ""); }

    static ACMDScript Compile(string text)
    {
        var s = new ACMDScript(0x1234);
        s.Serialize(text);
        return s;
    }

    static uint Crc(string name)
    {
        return ACMD_INFO.CMD_NAMES.First(kv => kv.Value == name).Key;
    }

    static int Main(string[] args)
    {
        var errors = new List<string>();
        ACMD_INFO.OverrideInfo(args[0], errors);
        Check("Events.cfg loads with no errors", string.Join("; ", errors), "");

        // ---- the changed commands: help, group, examples
        uint glow = Crc("Sword_Glow"), glow2 = Crc("Sword_Glow2");
        Check("Sword_Glow keeps its group", ACMD_INFO.GetCategory(glow), "Trails & sword glow");
        Check("Sword_Glow2 keeps its group", ACMD_INFO.GetCategory(glow2), "Trails & sword glow");
        var help = string.Join("\n", ACMD_INFO.GetHelp(glow));
        Check("Sword_Glow's help: the changed texture ids (272 / 273 new)", help.Contains("changed in v1.7.31: 272 / 273 are new") &&
              help.Contains("272 TexKamuiSwordTraceCyan") && help.Contains("273 TexKamuiSwordTraceCyanAdd") &&
              help.Contains("kamui_trail_cave.py"), true);
        Check("Sword_Glow2's help: 272 / 273", string.Join("\n", ACMD_INFO.GetHelp(glow2)).Contains("272 / 273"), true);
        Check("New Commands' group text lists the new values", ACMD_INFO.GROUP_HELP.ContainsKey("New Commands") &&
              string.Join("\n", ACMD_INFO.GROUP_HELP["New Commands"]).Contains("## New values in vanilla commands"), true);
        foreach (var crc in new[] { glow, glow2 })
        {
            var blocks = new List<List<string>> { new List<string>() };
            foreach (var l in ACMD_INFO.GetExample(crc)) { if (l.Length == 0) blocks.Add(new List<string>()); else blocks.Last().Add(l); }
            int i = 0, cyan = 0;
            foreach (var blk in blocks.Where(x => x.Count > 0))
            {
                i++;
                string what = $"{ACMD_INFO.CMD_NAMES[crc]} example {i}";
                try
                {
                    var c1 = Compile(string.Join("\n", blk));
                    var c2 = Compile(c1.Deserialize());
                    Check(what + ": compiles, round-trips", Hex(Bytes(c2)), Hex(Bytes(c1)));
                    foreach (ACMDCommand c in c1.Commands)
                        if (c.Ident == crc && Convert.ToInt32(c.Parameters[0]) == 272) cyan++;
                }
                catch (Exception e) { Check(what + ": compiles", e.Message, ""); }
            }
            Check($"{ACMD_INFO.CMD_NAMES[crc]}: the game's example and ours", i >= 2, true);
            Check($"{ACMD_INFO.CMD_NAMES[crc]}: an example with texture 272", cyan >= 1, true);
        }
        // the first cyan example's Sword_Glow: its words (0x110 / 0x111 in the first two)
        var ex = ACMD_INFO.GetExample(glow);
        var line = ex.First(l => l.StartsWith("Sword_Glow(Texture1=272, Texture2=273"));
        var sc = Compile(line);
        var cmd = (ACMDCommand)sc.Commands[0];
        Check("Sword_Glow(Texture1=272, Texture2=273, ...): the first words", Hex(cmd.GetBytes(Endianness.Big).Take(12).ToArray()),
              glow.ToString("X8") + "00000110" + "00000111");
        var dec = sc.Deserialize();
        Check("... decompiled as 0x110 / 0x111", dec.Substring(0, Math.Min(dec.Length, 53)), "Sword_Glow(Texture1=0x110, Texture2=0x111, BlurLength");

        // ---- the names (the Hitbox Viewer's table)
        Check("TrailNames: 273 names", TrailNames.Names.Length, 273);
        Check("TrailNames 240 / 241 (Corrin's own)", TrailNames.Name(240) + " " + TrailNames.Name(241), "TexKamuiSwordTrace TexKamuiSwordTraceAdd");
        Check("TrailNames 270 / 271 (Byleth's)", TrailNames.Name(270) + " " + TrailNames.Name(271), "TexMasterSwordTrace TexMasterSwordTraceAdd");
        Check("TrailNames 272 / 273 (new)", TrailNames.Name(272) + " " + TrailNames.Name(273), "TexKamuiSwordTraceCyan TexKamuiSwordTraceCyanAdd");
        Check("TrailNames 274: none", TrailNames.Name(274), null);

        // ---- the tooltips
        Tooltips.Load();
        Tooltips.Fighter = null;
        var t = Tooltips.Find(0x110, "Sword_Glow", "Texture1", "int", 1);
        Check("tooltip: Sword_Glow Texture1=0x110 (any fighter)", t.Count > 0 ? t[0].Name : "", "TexKamuiSwordTraceCyan");
        t = Tooltips.Find(0x111, "Sword_Glow", "Texture2", "int", 2);
        Check("tooltip: Sword_Glow Texture2=0x111", t.Count > 0 ? t[0].Name : "", "TexKamuiSwordTraceCyanAdd");
        t = Tooltips.Find(0x110, "Sword_Glow2", "Color", "int", 1);
        Check("tooltip: Sword_Glow2 Color=0x110", t.Count > 0 ? t[0].Name : "", "TexKamuiSwordTraceCyan");
        t = Tooltips.Find(0x110, "Sword_Glow", "BlurLength", "int", 3);
        Check("tooltip: not in another parameter (BlurLength=0x110)", t.Count, 0);
        t = Tooltips.Find(0xF0, "Sword_Glow", "Texture1", "int", 1);
        Check("tooltip: Sword_Glow Texture1=0xF0", t.Count > 0 ? t[0].Name : "", "TexKamuiSwordTrace");
        Tooltips.Fighter = "kamui";
        t = Tooltips.Find(0x110, "Sword_Glow", "Texture1", "int", 1);
        Check("tooltip (Corrin open): her own entry first", t.Count > 0 ? t[0].Name + " | " + t[0].Description.Substring(0, 13) : "",
              "TexKamuiSwordTraceCyan | NEW (v1.7.31)");
        var d = Tooltips.Describe("0x110", "Sword_Glow", "Texture1", "int", 1);
        Check("hover text (Corrin open): name, use, the executable it needs", d.Contains("0x110: TexKamuiSwordTraceCyan") &&
              d.Contains("Texture1=272") && d.Contains("kamui_trail_cave.py"), true);
        Tooltips.Fighter = null;

        // ---- the Hitbox Viewer finds the textures
        var lib = new EffectLibrary(args[1]);
        var tx = lib.TrailTexture(272);
        var tx2 = lib.TrailTexture(273);
        Check("viewer: texture 272 found in effect/kamui/trail (128 x 128)", tx != null ? tx.Width + "x" + tx.Height : "none", "128x128");
        Check("viewer: texture 273 found (128 x 128)", tx2 != null ? tx2.Width + "x" + tx2.Height : "none", "128x128");
        int x = int.Parse(args[2]), y = int.Parse(args[3]);
        uint want = uint.Parse(args[4], NumberStyles.HexNumber);
        Check($"viewer: texture 272's pixel ({x}, {y}) as tools/nut.py decodes it", tx != null ? ((uint)tx.Argb[y * tx.Width + x]).ToString("X8") : "none",
              want.ToString("X8"));
        Console.WriteLine($"{oks} ok, {fails} failures");
        return fails == 0 ? 0 : 1;
    }
}
