// Variables in the Extra hitbox commands' Damage / Angle / KBG / FKB / BKB / Size (exe_v43) in SALT / Sm4shCommand
// v1.4.11 (Mono): the words they compile to (names, New_Vars, IDs, |FOLLOW / |WORLD / |NEG), the text they show
// (names on and off), decompile -> compile round trips, numbers as before, errors, the conversion the Hitbox Viewer
// uses (the executable's: tools/hitbox_var_test.py), and every new command's examples.
// Build (next to the built SM4SHCommand.exe / SALT.dll): csc -out:HvTest.exe -r:SALT.dll -r:SM4SHCommand.exe -r:<mono 4.5>/mscorlib.dll
// -r:<mono 4.5>/System.dll -r:<mono 4.5>/System.Core.dll -nostdlib hitbox_var_test.cs. Run: mono HvTest.exe Events.cfg Aliases
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;

class HvTest
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

    static string Error(string text)
    {
        try { Compile(text); return null; }
        catch (ACMDCompileException e) { return e.Reason; }
        catch (Exception e) { return "other: " + e.Message; }
    }

    static void LoadAliases(string dir)
    {
        foreach (var f in System.IO.Directory.GetFiles(dir, "*.txt").OrderBy(x => x))
            foreach (var raw in System.IO.File.ReadAllLines(f))
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

    // an Extra_Special_Hitbox line with Damage ... Size given (the rest fixed)
    static string Hb(string dmg, string ang, string kbg, string fkb, string bkb, string size, string cmd = "Extra_Special_Hitbox")
    {
        string rest = "X=0, Y=8, Z=6, Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=2, " +
                      "SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=1, HitBits=0x3F, Unk41=0, CollisionPart=0xF, NoScale=0, " +
                      "Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0, HitAllStates=0, FacingRestrict=3, " +
                      "NoGrabRelease=0, TeamDamage=0, DisableHitlag=0, NoGFX=0, Flinchless=0, " +
                      (cmd == "Extra_Special_Hitbox" ? "Shape=0, " : "X2=0, Y2=8, Z2=14, ") +
                      "HitstunMul=0, HitstopMul=0, HitstopFrames=0, SelfHitstopMul=0, SelfHitstopFrames=0, DIMul=0";
        return $"{cmd}(ID=0, Part=0, Bone=0, Damage={dmg}, Angle={ang}, KBG={kbg}, FKB={fkb}, BKB={bkb}, Size={size}, {rest})";
    }

    // the words of parameters 3-8 (Damage ... Size) of the script's first command
    static string Fields(ACMDScript s)
    {
        var b = Bytes(s);
        return Hex(b.Skip(16).Take(24).ToArray());
    }

    static string Field(ACMDScript s, string name)
    {
        string t = s.Deserialize().Split('\n')[0];
        int at = t.IndexOf(", " + name + "=");
        int end = t.IndexOf(", ", at + 2);
        return t.Substring(at + 3 + name.Length, end - at - 3 - name.Length);
    }

    static int Main(string[] args)
    {
        var errors = new List<string>();
        ACMD_INFO.OverrideInfo(args[0], errors);
        Check("Events.cfg loads with no errors", string.Join("; ", errors), "");
        LoadAliases(args[1]);
        Check("aliases: STICK_ANGLE / ROT_X", FighterVariable.TryParseAlias("STICK_ANGLE", out uint sa) + " " + sa.ToString("X8") + " " +
              (FighterVariable.TryParseAlias("rot_x", out uint rx) ? rx.ToString("X8") : "-"), "True 0F0003C0 0F0003C6");
        Check("parameters 3-8 are Damage, Angle, KBG, FKB, BKB, Size (both commands)",
              string.Join(",", new ACMDCommand(ACMDCommand.ExtraHitboxIdent).ParamSyntax.Skip(3).Take(6)) + " " +
              string.Join(",", new ACMDCommand(ACMDCommand.ExtraExtHitboxIdent).ParamSyntax.Skip(3).Take(6)),
              "Damage,Angle,KBG,FKB,BKB,Size Damage,Angle,KBG,FKB,BKB,Size");

        // ---- numbers: as before
        var s = Compile(Hb("12", "361", "100", "0", "40", "5"));
        Check("numbers: the words", Fields(s), "41400000" + "00000169" + "00000064" + "00000000" + "00000028" + "40A00000");
        Check("numbers: shown as before", Field(s, "Angle") + " " + Field(s, "Damage") + " " + Field(s, "Size"), "0x169 12 5");

        // ---- variables
        FighterVariable.ClearNewVars();
        Compile("New_Var(Name=charge, Type=float, Initial=4, Scope=move)");
        s = Compile(Hb("VAR_0", "STICK_ANGLE", "VAR_2|NEG", "0x0F000303", "charge|FOLLOW", "VAR_5|FOLLOW"));
        Check("variables: the words (Damage float field = the ID's bits; flags in bits 20-23)", Fields(s),
              "0F000300" + "0F0003C0" + "0F400302" + "0F000303" + "0F100380" + "0F100305");
        Check("variables: shown by name with their flags", string.Join(" ", new[] { "Damage", "Angle", "KBG", "FKB", "BKB", "Size" }.Select(n => Field(s, n))),
              "VAR_0 STICK_ANGLE VAR_2|NEG VAR_3 charge|FOLLOW VAR_5|FOLLOW");
        Check("variables: decompile -> compile, the same bytes", Hex(Bytes(Compile(s.Deserialize()))), Hex(Bytes(s)));
        s = Compile(Hb("vAr_0|follow", "stick_angle_raw|World|FOLLOW", "1", "2", "3", "4"));
        Check("any case; several flags in any order", Field(s, "Damage") + " " + Field(s, "Angle"), "VAR_0|FOLLOW STICK_ANGLE_RAW|FOLLOW|WORLD");
        Check("... the words", Fields(s).Substring(0, 16), "0F1003000F3003C1");
        s = Compile(Hb("0x10000005", "0x0F000301|NEG", "0x1F000385", "0", "0", "0x0F000306"));
        Check("IDs (a game int, a New_Var int ID): their words", Fields(s),
              "10000005" + "0F400301" + "1F000385" + "00000000" + "00000000" + "0F000306");
        Check("... round trip", Hex(Bytes(Compile(s.Deserialize()))), Hex(Bytes(s)));
        s = Compile(Hb("ROT_X", "ROT_X|NEG", "1", "1", "1", "CSTICK_LEN", "Extra_Extended_Special_Hitbox"));
        Check("Extra_Extended_Special_Hitbox too", Fields(s), "0F0003C6" + "0F4003C6" + "00000001" + "00000001" + "00000001" + "0F0003C5");
        Check("... shown", Field(s, "Angle") + " " + Field(s, "Size"), "ROT_X|NEG CSTICK_LEN");
        Check("... round trip", Hex(Bytes(Compile(s.Deserialize()))), Hex(Bytes(s)));

        // ---- names off: the ID in hex (with the flags), which compiles back
        s = Compile(Hb("VAR_0|FOLLOW", "STICK_ANGLE", "1", "1", "1", "1"));
        FighterVariable.ShowAliases = false;
        string off = s.Deserialize();
        FighterVariable.ShowAliases = true;
        Check("names off: hex", Field(Compile(off), "Damage") + " / " + off.Substring(0, off.IndexOf(", KBG")),
              "VAR_0|FOLLOW / Extra_Special_Hitbox(ID=0x0, Part=0x0, Bone=0x0, Damage=0x0F000300|FOLLOW, Angle=0x0F0003C0");
        Check("... compiles back", Hex(Bytes(Compile(off))), Hex(Bytes(s)));

        // ---- other commands / other fields: unchanged (a name there is still an error / a plain alias)
        Check("Special_Hitbox's Damage: a variable is still an error", Error(
              "Special_Hitbox(ID=0, Part=0, Bone=0, Damage=VAR_0, Angle=361, KBG=100, FKB=0, BKB=40, Size=5, X=0, Y=8, Z=6, Effect=0, Trip=0, Hitlag=1, SDI=1, Clang=1, Rebound=1, ShieldDamage=0, SFXLevel=2, SFXType=1, Ground/Air=3, Direct/Indirect=1, Type=1, HitBits=0x3F, Unk41=0, CollisionPart=0xF, NoScale=0, Shieldable=1, Reflectable=0, Absorbable=0, Rehit=0, IgnoreInvuln=0, HitAllStates=0, FacingRestrict=3, NoGrabRelease=0, TeamDamage=0, DisableHitlag=0, NoGFX=0, Flinchless=0, Shape=0)") != null, true);
        s = Compile(Hb("1", "2", "3", "4", "5", "6").Replace("X=0, Y=8", "X=0x0F000300, Y=8"));
        Check("X (not a variable field): a hex value is float bits, shown as a number", Field(s, "X").Contains("|") || Field(s, "X") == "VAR_0", false);

        // ---- errors
        Check("unknown name", Error(Hb("nope_var", "1", "1", "1", "1", "1")),
              "Extra_Special_Hitbox parameter Damage: unknown variable \"nope_var\" (a name from the Aliases folder, a New_Var, or an ID such as 0x0F000300)");
        Check("unknown name in an int field", Error(Hb("1", "nope_var", "1", "1", "1", "1")),
              "Extra_Special_Hitbox parameter Angle: unknown variable \"nope_var\" (a name from the Aliases folder, a New_Var, or an ID such as 0x0F000300)");
        Check("unknown flag", Error(Hb("1", "VAR_0|FAST", "1", "1", "1", "1")),
              "Extra_Special_Hitbox parameter Angle: unknown flag \"FAST\" (FOLLOW, WORLD or NEG)");
        Check("not a variable ID with a flag", Error(Hb("1", "0x169|FOLLOW", "1", "1", "1", "1")),
              "Extra_Special_Hitbox parameter Angle: 0x169 (0x00000169) can't be used here: a hitbox variable is an ID from 0x01000000 to 0x1FFFFFFF without bits 0x00F00000 (0x0F000300 VAR_0 ..., a New_Var, a game int / float)");
        Check("a flag ID (0x2xxxxxxx) name with a flag", Error(Hb("1", "0x2100000D|FOLLOW", "1", "1", "1", "1")) != null, true);

        // ---- the conversion (as the executable's hv_value; the Hitbox Viewer draws with it)
        Func<int, uint, float, float, float> V = (f, w, v, facing) => ACMDCommand.HitboxVarValue(f, w, v, facing);
        Check("Angle -30 -> 330, 725 -> 5, 359.6 -> 0, 361 -> 361, 369 -> 9, -0.5 -> 359",
              string.Join(",", new[] { -30f, 725f, 359.6f, 361f, 369f, -0.5f }.Select(v => V(1, 0x0F000300, v, 1))), "330,5,0,361,9,359");
        Check("WORLD facing left 30 -> 150; NEG 30 -> 330; NEG|WORLD left 30 -> 210",
              V(1, 0x0F200300, 30, -1) + "," + V(1, 0x0F400300, 30, 1) + "," + V(1, 0x0F600300, 30, -1), "150,330,210");
        Check("KBG 70.5 -> 71, -3 -> 0; Damage -4 -> 0, 7.25 -> 7.25", V(2, 0x0F000300, 70.5f, 1) + "," + V(2, 0x0F000300, -3, 1) + "," +
              V(0, 0x0F000300, -4, 1) + "," + V(0, 0x0F000300, 7.25f, 1), "71,0,0,7.25");

        // ---- every new command's examples compile, and come back the same after decompile -> compile
        int exampleBlocks = 0;
        foreach (var kv in ACMD_INFO.CMD_EXAMPLE.Where(x => ACMD_INFO.GetCategory(x.Key).StartsWith("New Commands")))
        {
            var blocks = new List<List<string>> { new List<string>() };
            foreach (var l in kv.Value) { if (l.Length == 0) blocks.Add(new List<string>()); else blocks.Last().Add(l); }
            int i = 0;
            foreach (var blk in blocks.Where(x => x.Count > 0))
            {
                i++;
                exampleBlocks++;
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
        // the user's two examples: their words
        var ex = ACMD_INFO.CMD_EXAMPLE[ACMDCommand.ExtraHitboxIdent];
        Func<int, string> block = n =>
        {
            var bl = new List<List<string>> { new List<string>() };
            foreach (var l in ex) { if (l.Length == 0) bl.Add(new List<string>()); else bl.Last().Add(l); }
            return string.Join("\n", bl.Where(x => x.Count > 0).ElementAt(n - 1));
        };
        var e4 = Compile(block(4));
        var hb4 = e4.Commands.Cast<ACMDCommand>().First(c => c.Ident == ACMDCommand.ExtraHitboxIdent);
        Check("example 4 (stick angle): Angle = STICK_ANGLE's ID", ACMDCommand.ParamWord(hb4.Parameters[4]).ToString("X8"), "0F0003C0");
        var e6 = Compile(block(6));
        var hb6 = e6.Commands.Cast<ACMDCommand>().First(c => c.Ident == ACMDCommand.ExtraHitboxIdent);
        Check("example 6 (rotation): Rotation_Get into VAR_1, then Angle = VAR_1",
              e6.Commands.Cast<ACMDCommand>().First(c => c.Name == "Rotation_Get").ToString() + " / " +
              ACMDCommand.ParamWord(hb6.Parameters[4]).ToString("X8"),
              "Rotation_Get(Target=0x0, Axis=0x0, Variable=VAR_1) / 0F000301");
        // ---- the Hitbox Viewer: the script's SET_FLOAT of the variable, else a stand-in; listed in Extras
        var run = new Sm4shCommand.Viewer.HitboxRunner().Run(Compile("SET_FLOAT(Value=-30, Variable=VAR_1)\nSET_FLOAT(Value=7.5, Variable=charge)\n" +
            Hb("charge|FOLLOW", "VAR_1", "STICK_LEN", "1", "1", "VAR_9|NEG")).Commands, 2);
        var vh = run[0].Hitboxes.Single();
        Check("viewer: Damage 7.5 (SET_FLOAT), Angle 330 (-30), KBG 100 (stand-in), Size 0 (stand-in 4, NEG)",
              vh.Damage + " " + vh.Angle + " " + vh.KBG + " " + vh.Size, "7.5 330 100 0");
        Check("viewer: Extras column", vh.ExtrasText, "Damage=charge|FOLLOW = 7.5, Angle=VAR_1 = 330, KBG=STICK_LEN drawn as 100, Size=VAR_9|NEG drawn as 0");
        Console.WriteLine($"{exampleBlocks} example blocks");
        Console.WriteLine($"{oks} ok, {fails} failures");
        return fails == 0 ? 0 : 1;
    }
}
