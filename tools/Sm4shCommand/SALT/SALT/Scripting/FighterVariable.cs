using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

namespace SALT.Moveset
{
    public class FighterVariable
    {
        public FighterVariable(uint raw)
        {
            Raw = raw;
        }
        public FighterVariable()
        {
            Raw = 0;
        }
        public FighterVariable(string text)
        {
            ParseFromText(text);
        }
        public uint Raw { get; set; }
        public VarDataType DataType
        {
            get
            {
                return (VarDataType)((Raw & 0xF0000000) >> 28);
            }
            set
            {
                Raw |= (uint)value << 28;
            }
        }
        public VarSourceType SourceType
        {
            get
            {
                return (VarSourceType)((Raw & 0x0F000000) >> 24);
            }
            set
            {
                Raw |= (uint)value << 24;
            }
        }
        public uint VariableID
        {
            get
            {
                return Raw & 0x00FFFFFF;
            }
            set
            {
                Raw |= value;
            }
        }
        /// <summary>
        /// When false (the default), variables are shown as their raw value (0x2100000D), the way
        /// FITX and the game's own code refer to them. When true, the old "RA-Flag[13]" form.
        /// Both forms are accepted when compiling.
        /// </summary>
        public static bool ShowDescriptiveNames { get; set; }

        // ------------------------------------------------------------ aliases
        // Names for variables (e.g. OPP_HITSTUN for 0x0F000048), loaded by the editor from its Aliases
        // folder. Shown instead of the number when ShowAliases is on; always accepted when compiling.
        static readonly Dictionary<string, uint> aliasToRaw = new Dictionary<string, uint>(StringComparer.OrdinalIgnoreCase);
        static readonly Dictionary<uint, string> rawToAlias = new Dictionary<uint, string>();
        static readonly Regex aliasName = new Regex(@"^[A-Za-z_][A-Za-z0-9_]*$");

        public static bool ShowAliases { get; set; } = true;
        public static int AliasCount { get { return aliasToRaw.Count; } }

        public static void ClearAliases()
        {
            aliasToRaw.Clear();
            rawToAlias.Clear();
        }

        /// <summary>A name made of letters, digits and _ (not starting with a digit).</summary>
        public static bool IsAliasName(string name)
        {
            return name != null && aliasName.IsMatch(name);
        }

        /// <summary>Adds or replaces an alias; the last name given for a value is the one shown.</summary>
        public static bool AddAlias(string name, uint raw)
        {
            if (!IsAliasName(name))
                return false;
            uint old;
            if (aliasToRaw.TryGetValue(name, out old) && rawToAlias.ContainsKey(old) &&
                string.Equals(rawToAlias[old], name, StringComparison.OrdinalIgnoreCase))
                rawToAlias.Remove(old);
            aliasToRaw[name] = raw;
            rawToAlias[raw] = name;
            return true;
        }

        public static bool TryGetAlias(uint raw, out string name)
        {
            return rawToAlias.TryGetValue(raw, out name);
        }

        public static bool TryParseAlias(string name, out uint raw)
        {
            raw = 0;
            return name != null && aliasToRaw.TryGetValue(name.Trim(), out raw);
        }

        public override string ToString()
        {
            string alias;
            if (ShowAliases && rawToAlias.TryGetValue(Raw, out alias))
                return alias;
            if (ShowDescriptiveNames)
            {
                var s1 = Enum.GetName(typeof(VarSourceType), SourceType);
                var s2 = Enum.GetName(typeof(VarDataType), DataType);
                if (s1 != null && s2 != null)
                    return $"{s1}-{s2}[{VariableID}]";
            }
            return "0x" + Raw.ToString("X8");
        }
        public void ParseFromText(string text)
        {
            text = text.Trim();
            if (text.StartsWith("var ", StringComparison.InvariantCultureIgnoreCase)) // FITX style
                text = text.Substring(4).Trim();
            uint aliased;
            if (aliasToRaw.TryGetValue(text, out aliased))
            {
                Raw = aliased;
            }
            else if (text.StartsWith("0x", StringComparison.InvariantCultureIgnoreCase))
            {
                Raw = uint.Parse(text.Substring(2), NumberStyles.HexNumber);
            }
            else if (text.IndexOf('-') < 0 || text.IndexOf('[') < 0)
            {
                throw new FormatException($"unknown variable or alias \"{text}\"");
            }
            else
            {
                var strSType = text.Substring(0, text.IndexOf('-'));
                var strDType = text.Substring(text.IndexOf('-') + 1, text.IndexOf('[') - (text.IndexOf('-') + 1));
                var stype = (VarSourceType)Enum.Parse(typeof(VarSourceType), strSType);
                var dtype = (VarDataType)Enum.Parse(typeof(VarDataType), strDType);

                uint ID = 0;
                string strID = text.Substring(text.IndexOf('[') + 1, text.IndexOf(']') - (text.IndexOf('[') + 1));
                if (strID.StartsWith("0x", StringComparison.InvariantCultureIgnoreCase))
                {
                    ID = uint.Parse(strID.Substring(2), NumberStyles.HexNumber);
                }
                else
                {
                    ID = uint.Parse(strID);
                }
                VariableID = ID;
                DataType = dtype;
                SourceType = stype;
            }
        }
    }
    public enum VarSourceType
    {
        // Standard types // 
        LA = 0,
        RA = 1,

        // parameter file groups //
        fighter_param_common = 2,
        fighter_param = 3,
        unk4 = 4,
        SpecialN = 5,
        SpecialS = 6,
        SpecialHi = 7,
        SpecialLw = 8,
        fighter_param_equipment_ability = 9,

        // status transition //
        STrans = 14,
        STransGroup = 15,
        
        undefined = 255
    }
    public enum VarDataType
    {
        Float = 0,
        Int = 1,
        Flag = 2
    }
}
