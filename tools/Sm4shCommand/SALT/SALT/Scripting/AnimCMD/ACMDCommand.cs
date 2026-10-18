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
        public override string ToString()
        {
            var inv = System.Globalization.CultureInfo.InvariantCulture;
            var syntax = this.ParamSyntax;
            var parts = new List<string>(this.Parameters.Count);
            for (int i = 0; i < this.Parameters.Count; i++)
            {
                string value;
                object p = this.Parameters[i];
                if (p is int | p is bint)
                    value = FormatInt(Convert.ToInt32(p), i < syntax.Length ? syntax[i].Trim() : "");
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
