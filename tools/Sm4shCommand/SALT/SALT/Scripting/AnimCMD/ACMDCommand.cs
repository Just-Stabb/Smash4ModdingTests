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
                    value = string.Format(inv, "0x{0:X}", p);
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
