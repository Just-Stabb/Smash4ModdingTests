// New_Var in SALT / Sm4shCommand v1.4.9 (Mono): compile / decompile round trips, names surviving a saved file,
// errors, and every new command's examples. Run: mono NvTest.exe Events.cfg Aliases BODY_DIR TMP_DIR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;

class NvTest
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

    static ACMDScript Compile(string text, uint crc = 0x1234)
    {
        var s = new ACMDScript(crc);
        s.Serialize(text);
        return s;
    }

    static string Error(string text)
    {
        try { Compile(text); return null; }
        catch (ACMDCompileException e) { return e.Reason; }
        catch (Exception e) { return "other: " + e.Message; }
    }

    static void LoadAliases(string dir)
    {
        foreach (var f in Directory.GetFiles(dir, "*.txt").OrderBy(x => x))
            foreach (var raw in File.ReadAllLines(f))
            {
                var line = raw.Trim();
                if (line.Length == 0 || line.StartsWith("#") || line.StartsWith("//")) continue;
                int eq = line.IndexOf('=');
                if (eq < 0) continue;
                string v = line.Substring(eq + 1);
                foreach (var m in new[] { "#", "//" }) { int at = v.IndexOf(m); if (at >= 0) v = v.Substring(0, at); }
                v = v.Trim();
                if (v.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
                    FighterVariable.AddAlias(line.Substring(0, eq).Trim(), Convert.ToUInt32(v.Substring(2), 16));
            }
    }

    static void WriteAcmd(ACMDFile f, string path)
    {
        var orig = File.ReadAllBytes(path);
        var keys = f.Scripts.Keys.OrderBy(k => k).ToList();
        var body = new List<byte>();
        var table = new List<byte>();
        int baseOff = 0x10 + 8 * keys.Count, total = 0;
        Func<uint, byte[]> be = v => new[] { (byte)(v >> 24), (byte)(v >> 16), (byte)(v >> 8), (byte)v };
        foreach (var k in keys)
        {
            var sc = (ACMDScript)f.Scripts[k];
            table.AddRange(be(k));
            table.AddRange(be((uint)(baseOff + body.Count)));
            body.AddRange(Bytes(sc));
            total += sc.Count;
        }
        var outb = new List<byte>(orig.Take(8));
        outb.AddRange(be((uint)keys.Count));
        outb.AddRange(be((uint)total));
        outb.AddRange(table);
        outb.AddRange(body);
        File.WriteAllBytes(path, outb.ToArray());
    }

    static int Main(string[] args)
    {
        var errors = new List<string>();
        int n = ACMD_INFO.OverrideInfo(args[0], errors);
        Check("Events.cfg loads with no errors", string.Join("; ", errors), "");
        Check("commands", ACMD_INFO.CMD_NAMES.Count, 619);
        Check("New_Var known: size 11, group", ACMD_INFO.CMD_SIZES[FighterVariable.NewVarIdent] + " " +
              ACMD_INFO.GetCategory(FighterVariable.NewVarIdent), "11 New Commands / Variables");
        Check("commands with help", ACMD_INFO.CMD_HELP.Count, 35);
        Check("group help blocks", ACMD_INFO.GROUP_HELP.Count, 9);
        LoadAliases(args[1]);
        Check("aliases loaded", FighterVariable.AliasCount > 500, true);

        // ---- a declaration, its bytes and its text
        FighterVariable.ClearNewVars();
        var s = Compile("New_Var(Name=charge, Type=int, Initial=0, Scope=move)\nINC_INT(Variable=charge)");
        var b = Bytes(s);
        Check("New_Var bytes", Hex(b.Take(44).ToArray()),
              "A321746C" + "0F000380" + "00000001" + "00000000" + "00000001" + "63686172" + "67650000" + "00000000" +
              "00000000" + "00000000" + "00000000");
        Check("INC_INT(charge) -> 0x0F000380", Hex(b.Skip(44).Take(8).ToArray()), "8827F88C0F000380");
        Check("decompiled", s.Deserialize(), string.Join(Environment.NewLine, "New_Var(Name=charge, Type=int, Initial=0, Scope=move, Slot=0)",
              "INC_INT(Variable=charge)", "Script_End()"));
        var s2 = Compile(s.Deserialize());
        Check("decompile -> compile: the same bytes", Hex(Bytes(s2)), Hex(b));

        // ---- defaults, positional, numbers, a second name, use before the declaration
        s = Compile("SET_FLOAT(Value=2.5, Variable=power)\nNew_Var(power)\nNew_Var(Name=hits, Type=1, Initial=3, Scope=1)\n" +
                    "Int_Var_Compare(Variable=hits, Method=3, Value=2)\nSUB_FLOAT_2(Variable=power, SourceVariable=hits)\n" +
                    "Hit_Get(Target=0, When=0, Variable=power)");
        var lines = s.Deserialize().Split(new[] { Environment.NewLine }, StringSplitOptions.None);
        Check("used above its declaration", lines[0], "SET_FLOAT(Value=2.5, Variable=power)");
        Check("defaults: float, 0, object, the next free slot", lines[1], "New_Var(Name=power, Type=float, Initial=0, Scope=object, Slot=1)");
        Check("numbers for Type / Scope", lines[2], "New_Var(Name=hits, Type=int, Initial=3, Scope=move, Slot=2)");
        Check("Int_Var_Compare by name", lines[3], "Int_Var_Compare(Variable=hits, Method=0x3, Value=0x2)");
        Check("an int parameter (SUB_FLOAT_2) by name", lines[4], "SUB_FLOAT_2(Variable=power, SourceVariable=hits)");
        Check("a new command's Variable by name", lines[5], "Hit_Get(Target=0x0, When=0x0, Variable=power)");
        Check("their IDs", Hex(Bytes(s).Skip(4).Take(8).ToArray()), "402000000F000381");
        // another script uses the names without declaring them; a name's slot is kept when declared again
        s = Compile("INC_INT(Variable=CHARGE)\nNew_Var(Name=charge, Type=int)");
        Check("another script: the same name (any case) -> the same ID; re-declared: the same slot",
              Hex(Bytes(s).Take(8).ToArray()) + " " + s.Deserialize().Split('\n')[1].Trim(),
              "8827F88C0F000380 New_Var(Name=charge, Type=int, Initial=0, Scope=object, Slot=0)");
        s = Compile("New_Var(Name=fixed, Initial=-1.25, Slot=40)\nSET_INT(Value=1, Variable=fixed)");
        Check("Slot=40, Initial -1.25", s.Deserialize().Split('\n')[0].Trim(), "New_Var(Name=fixed, Type=float, Initial=-1.25, Scope=object, Slot=40)");
        Check("... its ID 0x0F0003A8", Hex(Bytes(s).Skip(4).Take(4).ToArray()), "0F0003A8");
        s = Compile("New_Var(Name=next)");
        Check("auto slot skips the taken ones (0, 1, 2, 40)", s.Deserialize().Split('\n')[0].Trim(),
              "New_Var(Name=next, Type=float, Initial=0, Scope=object, Slot=3)");
        s = Compile("New_Var(Name=name_of_24_characters_ab, Type=int, Initial=7)");
        Check("24 characters (all 6 words)", s.Deserialize().Split('\n')[0].Trim(),
              "New_Var(Name=name_of_24_characters_ab, Type=int, Initial=7, Scope=object, Slot=4)");
        Check("raw form (10 parameters) still compiles", Hex(Bytes(Compile(
              "New_Var(Name=0x0F000385, Type=0, Initial=0, Scope=0, Text1=0x6162, Text2=0, Text3=0, Text4=0, Text5=0, Text6=0)")).Take(28).ToArray()),
              "A321746C0F0003850000000000000000000000000000616200000000");

        // ---- errors
        Check("unknown name", Error("INC_INT(Variable=nothing_here)"),
              "unknown variable or alias \"nothing_here\" (a new variable needs New_Var(Name=nothing_here) in one of the fighter's scripts)");
        Check("an alias name", Error("New_Var(Name=VAR_0)"), "New_Var: VAR_0 is already a variable name (Aliases folder): pick another");
        Check("a command name", Error("New_Var(Name=frame)"), "New_Var: frame is a command's name: pick another");
        Check("too long", Error("New_Var(Name=name_of_25_characters_abc)"), "New_Var: \"name_of_25_characters_abc\" is longer than 24 characters");
        Check("not a name", Error("New_Var(Name=2fast)"), "New_Var: \"2fast\" isn't a name (letters, digits and _, not starting with a digit)");
        Check("no name", Error("New_Var(Type=int)"), "New_Var needs a Name (e.g. New_Var(Name=charge))");
        Check("bad type", Error("New_Var(Name=x1, Type=double)"), "New_Var: Type is float or int, not \"double\"");
        Check("bad slot", Error("New_Var(Name=x1, Slot=64)"), "New_Var: Slot must be 0-63 (or auto), not \"64\"");
        Check("unknown key", Error("New_Var(Name=x1, Value=3)") != null, true);

        // ---- 64 slots
        FighterVariable.ClearNewVars();
        Compile(string.Join("\n", Enumerable.Range(0, 64).Select(i => $"New_Var(Name=v{i})")));
        Check("64 names: slots 0-63", FighterVariable.NewVars.Select(v => v.Slot).SequenceEqual(Enumerable.Range(0, 64)), true);
        Check("a 65th: an error", Error("New_Var(Name=v64)"), "New_Var: all 64 slots have names already (give Slot= to share one)");
        Check("a 65th sharing a slot", Error("New_Var(Name=v64, Slot=3)"), null);

        // ---- aliases off: hex, which compiles back
        FighterVariable.ClearNewVars();
        s = Compile("New_Var(Name=charge, Type=int)\nINC_INT(Variable=charge)");
        FighterVariable.ShowAliases = false;
        string off = s.Deserialize();
        FighterVariable.ShowAliases = true;
        Check("aliases off: the use in hex, New_Var still named", off.Split('\n')[1].Trim(), "INC_INT(Variable=0x0F000380)");
        Check("... compiles back", Hex(Bytes(Compile(off))), Hex(Bytes(s)));

        // ---- names survive a saved file (new session: no names known until the file is opened)
        string body = args[2], tmp = args[3];
        Directory.CreateDirectory(tmp);
        string path = Path.Combine(tmp, "game.bin");
        File.Copy(Path.Combine(body, "game.bin"), path, true);
        FighterVariable.ClearNewVars();
        var file = new ACMDFile(path);
        var keys = file.Scripts.Keys.Take(2).ToArray();
        var a = (ACMDScript)file.Scripts[keys[0]];
        var bscr = (ACMDScript)file.Scripts[keys[1]];
        string aText = "New_Var(Name=charge, Type=int, Initial=0, Scope=move)\nFRAME(Frames=5)\nINC_INT(Variable=charge)\n" +
                       "Int_Var_Compare(Variable=charge, Method=3, Value=20)\nTrue(Offset=0){\n    SET_FLOAT(Value=1.5, Variable=boost)\n}\n" + a.Deserialize();
        string bText = "New_Var(Name=boost, Initial=1, Scope=object)\nFloat_Var_Compare(Variable=boost, Method=5, Value=1)\n" + bscr.Deserialize();
        bscr.Serialize(bText);      // (boost is declared in B: compiled first, so A can use it)
        a.Serialize(aText);
        string aWant = a.Deserialize(), bWant = bscr.Deserialize();
        byte[] aBytes = Bytes(a), bBytes = Bytes(bscr);
        string saved = Path.Combine(tmp, "game_saved.bin");
        File.Copy(path, saved, true);
        WriteAcmd(file, saved);     // (SALT's Export maps a temp file, which Mono refuses: the same bytes by hand)
        FighterVariable.ClearNewVars();
        Check("a new session: no names", FighterVariable.NewVars.Count, 0);
        var again = new ACMDFile(saved);
        Check("reopened: the names from the file", string.Join(",", FighterVariable.NewVars.Select(v => v.Name + "=" + v.Slot + "/" + v.TypeName + "/" + v.ScopeName)),
              "boost=0/float/object,charge=1/int/move");
        Check("reopened: script A's text (names everywhere)", ((ACMDScript)again.Scripts[keys[0]]).Deserialize(), aWant);
        Check("reopened: script B's text", ((ACMDScript)again.Scripts[keys[1]]).Deserialize(), bWant);
        Check("reopened: the bytes", Hex(Bytes((ACMDScript)again.Scripts[keys[0]])) + Hex(Bytes((ACMDScript)again.Scripts[keys[1]])),
              Hex(aBytes) + Hex(bBytes));
        Check("script A's first lines", string.Join(" | ", aWant.Split('\n').Take(6).Select(x => x.Trim())),
              "New_Var(Name=charge, Type=int, Initial=0, Scope=move, Slot=1) | FRAME(Frames=5) | INC_INT(Variable=charge) | " +
              "Int_Var_Compare(Variable=charge, Method=0x3, Value=0x14) | True(Offset=0x5){ | SET_FLOAT(Value=1.5, Variable=boost)");

        // ---- every script of the fighter's four files: decompile -> compile gives the same bytes (no regressions)
        foreach (var name in new[] { "game.bin", "effect.bin", "sound.bin", "expression.bin" })
        {
            var f = new ACMDFile(Path.Combine(body, name));
            int bad = 0, total = 0;
            foreach (var kv in f.Scripts)
            {
                var sc = (ACMDScript)kv.Value;
                total++;
                try { if (Hex(Bytes(Compile(sc.Deserialize()))) != Hex(Bytes(sc))) bad++; }
                catch (Exception) { bad++; }
            }
            Check($"{name}: every script round-trips ({total}; effect.bin: its 5 else-if chains differ, as upstream)", bad, name == "effect.bin" ? 5 : 0);
        }

        // ---- every new command's examples compile, and come back the same after decompile -> compile
        foreach (var kv in ACMD_INFO.CMD_EXAMPLE.Where(x => ACMD_INFO.GetCategory(x.Key).StartsWith("New Commands")))
        {
            var ex = kv.Value;
            var blocks = new List<List<string>> { new List<string>() };
            foreach (var l in ex) { if (l.Length == 0) blocks.Add(new List<string>()); else blocks.Last().Add(l); }
            int i = 0;
            foreach (var blk in blocks.Where(x => x.Count > 0))
            {
                i++;
                string what = $"{ACMD_INFO.CMD_NAMES[kv.Key]} example {i}";
                try
                {
                    var c1 = Compile(string.Join("\n", blk));
                    var c2 = Compile(c1.Deserialize());
                    Check(what + ": compiles, round-trips", Hex(Bytes(c2)), Hex(Bytes(c1)));
                }
                catch (Exception e) { Check(what + ": compiles", e.Message, ""); }
            }
        }
        Console.WriteLine($"{oks} ok, {fails} failures");
        return fails == 0 ? 0 : 1;
    }
}
