// Copyright (c) 2018 Sammi Husky. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;

namespace SALT.Moveset.AnimCMD
{
    public class ACMDCommand : ICommand
    {
        public ACMDCommand(uint crc)
        {
            this.Ident = crc;
            this.Parameters = new List<object>();
        }

        public uint Ident { get; set; }
        public bool Dirty { get; set; }
        public int Size { get { return this.WordSize * 4; } }
        public string Name { get { return ACMD_INFO.CMD_NAMES[this.Ident]; } }
        public int WordSize { get { return ACMD_INFO.CMD_SIZES[this.Ident]; } }
        public int[] ParamSpecifiers
        {
            get
            {
                if (!string.IsNullOrEmpty(ACMD_INFO.PARAM_FORMAT[this.Ident]))
                {
                    return ACMD_INFO.PARAM_FORMAT[this.Ident].Split(',').
                        Select(x => int.Parse(x)).ToArray();
                }
                else
                {
                    return new int[0];
                }
            }
        }

        public string[] ParamSyntax =>
              ACMD_INFO.PARAM_SYNTAX[this.Ident].Split(',');

        public List<object> Parameters { get; set; }

        // ------------------------------------------------- how int parameters are shown

        /// <summary>
        /// Off (default): int parameters are shown in hex (0x169), as the game's data and FITX show them.
        /// On: shown as decimal (361) when that reads better; values that are float bits (some
        /// commands store X/Y/Z or sizes in int parameters) as floats with an f (1.5f); IDs, hashes and
        /// bit fields (large values, and parameters in <see cref="HexParams"/>) stay hex. Every form
        /// compiles back to the same value.
        /// </summary>
        public static bool DecimalInts { get; set; }

        /// <summary>Parameter names always shown in hex (hashes, effect / sound IDs, bit fields).</summary>
        public static readonly HashSet<string> HexParams = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "Hash", "Graphic", "GFXLeft", "GFXRight", "SFX", "HitBits", "Flag", "Variable1", "Variable2", "Variable3",
        };

        /// <summary>Show float bits as floats (only when <see cref="DecimalInts"/> is on).</summary>
        public static bool FloatBitsAsFloats { get; set; } = true;

        public static string FormatInt(int v, string paramName)
        {
            var inv = System.Globalization.CultureInfo.InvariantCulture;
            string hex = string.Format(inv, "0x{0:X}", v);
            if (!DecimalInts || HexParams.Contains(paramName))
                return hex;
            if (FloatBitsAsFloats)
            {
                string f = LooksLikeFloat(v);
                if (f != null)
                    return f;
            }
            if (v >= -0x10000 && v <= 0xFFFF)
                return v.ToString(inv);
            return hex;
        }

        /// <summary>
        /// "1.5f" when the bits are a short, ordinary float (at most 7 characters, magnitude 0.001 to
        /// 100000), else null. Small integers (exponent field 0) are never floats; random bits such as
        /// hashes almost never give a short float.
        /// </summary>
        public static string LooksLikeFloat(int bits)
        {
            int exp = (bits >> 23) & 0xFF;
            if (exp == 0 || exp == 0xFF || (bits & 0x7FFFFFFF) < 0x30000000)
                return null;
            float f = BitConverter.ToSingle(BitConverter.GetBytes(bits), 0);
            float a = Math.Abs(f);
            if (a < 0.001f || a > 100000f)
                return null;
            string s = f.ToString("R", System.Globalization.CultureInfo.InvariantCulture);
            if (s.Length > 7 || s.Contains("E"))
                return null;
            return (s.Contains(".") ? s : s + ".0") + "f";
        }

        /// <summary>The name a variable ID is shown by (a New_Var's, else an alias), when names are shown.</summary>
        public static bool TryVariableName(uint raw, out string name)
        {
            name = null;
            if (!FighterVariable.ShowAliases)
                return false;
            FighterVariable.NewVarInfo nv;
            if (FighterVariable.TryGetNewVar(raw, out nv))
                name = nv.Name;
            else if (!FighterVariable.TryGetAlias(raw, out name))
                return false;
            return true;
        }

        /// <summary>Parses an int parameter: 0x hex, decimal, or a float (1.5f / 1.5) stored as its bits.</summary>
        public static int ParseInt(string p)
        {
            var inv = System.Globalization.CultureInfo.InvariantCulture;
            p = p.Trim();
            if (p.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
                return (int)uint.Parse(p.Substring(2), System.Globalization.NumberStyles.HexNumber, inv);
            if (p.StartsWith("-0x", StringComparison.OrdinalIgnoreCase))
                return -(int)uint.Parse(p.Substring(3), System.Globalization.NumberStyles.HexNumber, inv);
            if (p.EndsWith("f", StringComparison.OrdinalIgnoreCase) || p.Contains(".") || p.Contains("E") || p.Contains("e"))
            {
                float f = float.Parse(p.TrimEnd('f', 'F'), System.Globalization.NumberStyles.Float, inv);
                return BitConverter.ToInt32(BitConverter.GetBytes(f), 0);
            }
            if (p.StartsWith("-"))
                return int.Parse(p, System.Globalization.NumberStyles.Integer, inv);
            return (int)uint.Parse(p, System.Globalization.NumberStyles.Integer, inv);
        }
        // ------------------------------------------------- variables in the Extra hitbox commands (exe_v43)
        // Extra_Special_Hitbox / Extra_Extended_Special_Hitbox's Damage, Angle, KBG, FKB, BKB and Size (parameters
        // 3-8) take a variable: the word is the variable's ID (0x01000000-0x1FFFFFFF: no number a hitbox uses is
        // there), with flags in bits 20-23 (tools/acmd_ext_cave.py HV_*). Text: a variable's name or ID, then
        // |FOLLOW (read again every frame), |WORLD (Angle: a screen angle, mirrored when facing left), |NEG (minus
        // it), e.g. Angle=STICK_ANGLE|FOLLOW, Damage=VAR_0, Size=charge (a New_Var). The word goes in the parameter
        // as it is (a float parameter holds its bits).

        public const uint ExtraHitboxIdent = 0x974EA5BE, ExtraExtHitboxIdent = 0x5C8A67C9;
        public const int HitboxVarFirst = 3, HitboxVarCount = 6;
        public const uint HitboxVarFlagMask = 0x00F00000;
        public static readonly string[] HitboxVarFlags = { "FOLLOW", "WORLD", "NEG" };   // 0x00100000 << i
        public static readonly string[] HitboxVarFields = { "Damage", "Angle", "KBG", "FKB", "BKB", "Size" };

        /// <summary>Parameter index of a command that takes a variable (the Extra hitboxes' Damage ... Size).</summary>
        public static bool IsHitboxVarField(uint ident, int index)
        {
            return (ident == ExtraHitboxIdent || ident == ExtraExtHitboxIdent) &&
                   index >= HitboxVarFirst && index < HitboxVarFirst + HitboxVarCount;
        }

        /// <summary>A word such a parameter reads as a variable (with its flags).</summary>
        public static bool IsHitboxVarWord(uint word)
        {
            return word >= 0x01000000 && word < 0x20000000;
        }

        /// <summary>The word in a parameter (an int's value, a float's bits).</summary>
        public static uint ParamWord(object p)
        {
            if (p is float) return BitConverter.ToUInt32(BitConverter.GetBytes((float)p), 0);
            if (p is bfloat) return BitConverter.ToUInt32(BitConverter.GetBytes((float)(bfloat)p), 0);
            if (p is FighterVariable) return ((FighterVariable)p).Raw;
            try { return unchecked((uint)Convert.ToInt64(p)); } catch { return 0; }
        }

        /// <summary>"VAR_0|FOLLOW" (a name, or the ID in hex, then its flags), or null for a number / unknown flag bits.</summary>
        public static string FormatHitboxVar(uint word)
        {
            if (!IsHitboxVarWord(word))
                return null;
            uint id = word & ~HitboxVarFlagMask, flags = word & HitboxVarFlagMask;
            string name;
            if (!IsHitboxVarWord(id) || !TryVariableName(id, out name))
                name = "0x" + id.ToString("X8");
            var sb = new System.Text.StringBuilder(name);
            for (int i = 0; i < HitboxVarFlags.Length; i++)
                if ((flags & (0x00100000u << i)) != 0)
                {
                    sb.Append('|').Append(HitboxVarFlags[i]);
                    flags &= ~(0x00100000u << i);
                }
            return flags == 0 ? sb.ToString() : "0x" + word.ToString("X8");
        }

        /// <summary>
        /// A variable in such a parameter: NAME or 0xID, then |FLAG.. (FOLLOW, WORLD, NEG; any case). False for
        /// anything else (a number: parsed as before). Throws FormatException for a bad flag or a name / ID that
        /// isn't a variable.
        /// </summary>
        public static bool TryParseHitboxVar(string text, out uint word)
        {
            word = 0;
            if (text == null)
                return false;
            var parts = text.Split('|');
            string first = parts[0].Trim();
            uint raw;
            bool named = FighterVariable.TryParseAlias(first, out raw);
            if (!named)
            {
                if (parts.Length == 1)
                    return false;           // a number (or nonsense: the usual error)
                if (!first.StartsWith("0x", StringComparison.OrdinalIgnoreCase) ||
                    !uint.TryParse(first.Substring(2), System.Globalization.NumberStyles.HexNumber,
                                   System.Globalization.CultureInfo.InvariantCulture, out raw))
                    throw new FormatException($"\"{first}\" isn't a variable (a name such as VAR_0, STICK_ANGLE or a New_Var, or an ID such as 0x0F000300)");
            }
            if (!IsHitboxVarWord(raw) || (raw & HitboxVarFlagMask) != 0)
                throw new FormatException($"{first} (0x{raw:X8}) can't be used here: a hitbox variable is an ID from 0x01000000 to 0x1FFFFFFF without bits 0x00F00000 (0x0F000300 VAR_0 ..., a New_Var, a game int / float)");
            for (int i = 1; i < parts.Length; i++)
            {
                string f = parts[i].Trim();
                int k = Array.FindIndex(HitboxVarFlags, x => x.Equals(f, StringComparison.OrdinalIgnoreCase));
                if (k < 0)
                    throw new FormatException($"unknown flag \"{f}\" (FOLLOW, WORLD or NEG)");
                raw |= 0x00100000u << k;
            }
            word = raw;
            return true;
        }

        /// <summary>
        /// The value a field gets from its variable's value v, as the executable works it out (hv_value): NEG first;
        /// Angle: WORLD with facing &lt; 0 makes it 180 - v, rounded (halves away from 0), 361-368 kept, else wrapped
        /// into 0-359; KBG / FKB / BKB rounded, at least 0; Damage / Size at least 0.
        /// </summary>
        public static float HitboxVarValue(int field, uint word, float v, float facing = 1)
        {
            if ((word & 0x00400000) != 0) v = -v;
            if (field == 0 || field == 5)
                return v >= 0 ? v : 0;      // (NaN: 0)
            if (field == 1 && (word & 0x00200000) != 0 && facing < 0) v = 180 - v;
            double r = v >= 0 ? Math.Floor(v + 0.5) : -Math.Floor(-v + 0.5);
            int n = double.IsNaN(r) || r > int.MaxValue || r < int.MinValue ? int.MinValue : (int)r;
            if (field != 1)
                return n > 0 ? n : 0;
            if (n >= 361 && n <= 368)
                return n;
            n %= 360;
            return n < 0 ? n + 360 : n;
        }

        public override string ToString()
        {
            var inv = System.Globalization.CultureInfo.InvariantCulture;
            if (this.Ident == FighterVariable.NewVarIdent)
            {
                string nv = NewVarText(this);
                if (nv != null)
                    return nv;
            }
            var syntax = this.ParamSyntax;
            var parts = new List<string>(this.Parameters.Count);
            for (int i = 0; i < this.Parameters.Count; i++)
            {
                string value;
                object p = this.Parameters[i];
                string hv = IsHitboxVarField(this.Ident, i) ? FormatHitboxVar(ParamWord(p)) : null;
                if (hv != null)
                    value = hv;     // a variable in an Extra hitbox's Damage ... Size
                else if (p is int | p is bint)
                {
                    string pname = i < syntax.Length ? syntax[i].Trim() : "";
                    value = FormatInt(Convert.ToInt32(p), pname);
                    // an int parameter holding a variable ID (SUB_FLOAT_2's, Float_Var_Compare_Var's, ...): its name, as
                    // variable parameters show it, when it has one (a New_Var's or an alias)
                    string vname;
                    if (pname.IndexOf("var", StringComparison.OrdinalIgnoreCase) >= 0 &&
                        TryVariableName(unchecked((uint)Convert.ToInt32(p)), out vname))
                        value = vname;
                }
                else if (p is float)
                    value = ((float)p).ToString("R", inv); // exact round trip
                else if (p is bfloat)
                    value = ((float)(bfloat)p).ToString("R", inv);
                else if (p is decimal)
                    value = ((decimal)p).ToString(inv);
                else
                    value = Convert.ToString(p, inv);

                if (this.ParamSpecifiers.Length > 0 && i < syntax.Length && syntax[i].Length > 0)
                    value = $"{syntax[i]}={value}";
                parts.Add(value);
            }

            return $"{this.Name}({string.Join(", ", parts.ToArray())})";
        }

        // ------------------------------------------------- New_Var (tools/acmd_ext_cave.py)
        // Binary: Name (the variable ID 0x0F000380 + slot), Type (0 float, 1 int), Initial (float), Scope (0 object,
        // 1 move), then the name's ASCII in 6 words (4 characters each, zero-padded). Text:
        //     New_Var(Name=charge, Type=int, Initial=0, Scope=object, Slot=0)
        // (Slot is shown; when compiling it can be left out: the name's slot, else the lowest free one.)

        public const int NewVarParams = 4 + NewVarNameWords;
        public const int NewVarNameWords = 6;

        /// <summary>The name a New_Var command carries (null if it has none / isn't a valid name).</summary>
        public static string NewVarName(ACMDCommand c)
        {
            if (c == null || c.Ident != FighterVariable.NewVarIdent || c.Parameters.Count != NewVarParams)
                return null;
            var sb = new System.Text.StringBuilder();
            for (int i = 0; i < NewVarNameWords; i++)
            {
                uint w = unchecked((uint)Convert.ToInt32(c.Parameters[4 + i]));
                for (int b = 3; b >= 0; b--)
                {
                    char ch = (char)((w >> (8 * b)) & 0xFF);
                    if (ch == 0)
                        goto done;
                    sb.Append(ch);
                }
            }
        done:
            string name = sb.ToString();
            return FighterVariable.IsAliasName(name) ? name : null;
        }

        /// <summary>The 6 words holding a name (ASCII, zero-padded).</summary>
        public static int[] NewVarNameWordsOf(string name)
        {
            var words = new int[NewVarNameWords];
            for (int i = 0; i < name.Length && i < 4 * NewVarNameWords; i++)
                words[i / 4] |= (name[i] & 0xFF) << (8 * (3 - i % 4));
            return words;
        }

        static uint NewVarRaw(ACMDCommand c)
        {
            var v = c.Parameters[0] as FighterVariable;
            return v != null ? v.Raw : unchecked((uint)Convert.ToInt32(c.Parameters[0]));
        }

        /// <summary>Remembers the variable a New_Var command declares (on loading a file), so its name shows and
        /// compiles everywhere. False if the command has no valid name or slot.</summary>
        public static bool RegisterNewVar(ACMDCommand c)
        {
            string name = NewVarName(c);
            if (name == null)
                return false;
            return FighterVariable.DeclareNewVar(name, NewVarRaw(c), Convert.ToInt32(c.Parameters[1]),
                Convert.ToInt32(c.Parameters[3]), Convert.ToSingle(c.Parameters[2]));
        }

        /// <summary>"New_Var(Name=charge, Type=int, Initial=0, Scope=object, Slot=0)", or null when the command can't be
        /// written that way (no valid name: it's then shown with its raw parameters).</summary>
        public static string NewVarText(ACMDCommand c)
        {
            string name = NewVarName(c);
            if (name == null)
                return null;
            var inv = System.Globalization.CultureInfo.InvariantCulture;
            uint raw = NewVarRaw(c);
            int type = Convert.ToInt32(c.Parameters[1]);
            int scope = Convert.ToInt32(c.Parameters[3]);
            float init = Convert.ToSingle(c.Parameters[2]);
            string t = type == 0 ? "float" : type == 1 ? "int" : type.ToString(inv);
            string sc = scope == 0 ? "object" : scope == 1 ? "move" : scope.ToString(inv);
            string iv = init == (float)Math.Truncate(init) && Math.Abs(init) < 1e7f ? ((long)init).ToString(inv)
                : init.ToString("R", inv);
            string slot = FighterVariable.IsNewVarSlot(raw) ? (raw - FighterVariable.NewVarBase).ToString(inv)
                : "0x" + raw.ToString("X8");
            return $"New_Var(Name={name}, Type={t}, Initial={iv}, Scope={sc}, Slot={slot})";
        }

        public virtual byte[] GetBytes(Endianness endian)
        {
            byte[] tmp = new byte[this.Size];
            Util.SetWord(ref tmp, this.Ident, 0, endian);
            for (int i = 0; i < this.ParamSpecifiers.Length; i++)
            {
                if (this.ParamSpecifiers[i] == 0)
                {
                    Util.SetWord(ref tmp, Convert.ToInt32(this.Parameters[i]), (i + 1) * 4, endian);
                }
                else if (this.ParamSpecifiers[i] == 1)
                {
                    double _hex = Convert.ToDouble(this.Parameters[i]);
                    float flt = (float)_hex;
                    byte[] bytes = BitConverter.GetBytes(flt);
                    int dec = BitConverter.ToInt32(bytes, 0);
                    string _hexval = dec.ToString("X");

                    Util.SetWord(ref tmp, int.Parse(_hexval, System.Globalization.NumberStyles.HexNumber), (i + 1) * 4, endian);
                }
                else if (this.ParamSpecifiers[i] == 2)
                {
                    Util.SetWord(ref tmp, (long)Convert.ToDecimal(this.Parameters[i]), (i + 1) * 4, endian);
                }
                else if (this.ParamSpecifiers[i] == 3)
                {
                    Util.SetWord(ref tmp, ((FighterVariable)this.Parameters[i]).Raw, (i + 1) * 4, endian);
                }
            }

            return tmp;
        }
    }
}
