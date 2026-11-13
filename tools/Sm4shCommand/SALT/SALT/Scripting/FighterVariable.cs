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

        /// <summary>An alias (VAR_0, SELF_HIT, ..) or a New_Var name declared in the open scripts.</summary>
        public static bool TryParseAlias(string name, out uint raw)
        {
            raw = 0;
            if (name == null)
                return false;
            return aliasToRaw.TryGetValue(name.Trim(), out raw) || TryParseNewVar(name, out raw);
        }

        /// <summary>A name from the Aliases folder only (not a New_Var name).</summary>
        public static bool IsFileAlias(string name)
        {
            return name != null && aliasToRaw.ContainsKey(name.Trim());
        }

        // ------------------------------------------------------------ New_Var names
        // New_Var(Name=charge, ...) (a new command, tools/acmd_ext_cave.py) declares a variable: slot k is the ID
        // 0x0F000380 + k (k < 64), and the command keeps the name, so it is known again whenever a file with it is
        // opened (ACMDFile registers every New_Var it reads) or a script with it compiles. Names are shown like
        // aliases (when ShowAliases is on) and compile in every variable parameter; case doesn't matter.

        /// <summary>New_Var's identifier (CRC32 of "New_Var").</summary>
        public const uint NewVarIdent = 0xA321746C;
        public const uint NewVarBase = 0x0F000380;
        public const int NewVarSlots = 64;
        public const int NewVarNameMax = 24;

        public class NewVarInfo
        {
            public string Name;
            public uint Raw;
            public int Type;     // 0 float, 1 int
            public int Scope;    // 0 object, 1 move
            public float Initial;
            public int Slot { get { return (int)(Raw - NewVarBase); } }
            public string TypeName { get { return Type == 1 ? "int" : "float"; } }
            public string ScopeName { get { return Scope == 1 ? "move" : "object"; } }
        }

        static readonly Dictionary<string, NewVarInfo> newVarByName = new Dictionary<string, NewVarInfo>(StringComparer.OrdinalIgnoreCase);
        static readonly Dictionary<uint, NewVarInfo> newVarByRaw = new Dictionary<uint, NewVarInfo>();

        /// <summary>Forgets every New_Var name (a new file / fighter / project is opened).</summary>
        public static void ClearNewVars()
        {
            newVarByName.Clear();
            newVarByRaw.Clear();
        }

        /// <summary>The New_Var names known, by slot.</summary>
        public static List<NewVarInfo> NewVars
        {
            get { return newVarByRaw.Values.OrderBy(v => v.Raw).ToList(); }
        }

        public static bool IsNewVarSlot(uint raw)
        {
            return raw >= NewVarBase && raw < NewVarBase + NewVarSlots;
        }

        /// <summary>
        /// Remembers a New_Var: name -> ID (and the ID's name, the last one given wins). False (nothing changed) if
        /// the name isn't a valid one, is an alias from the Aliases folder, or the ID isn't a New_Var slot.
        /// </summary>
        public static bool DeclareNewVar(string name, uint raw, int type, int scope, float initial)
        {
            if (!IsAliasName(name) || name.Length > NewVarNameMax || aliasToRaw.ContainsKey(name) || !IsNewVarSlot(raw))
                return false;
            NewVarInfo old;
            if (newVarByName.TryGetValue(name, out old) && old.Raw != raw && newVarByRaw.ContainsKey(old.Raw) &&
                string.Equals(newVarByRaw[old.Raw].Name, name, StringComparison.OrdinalIgnoreCase))
                newVarByRaw.Remove(old.Raw);
            var info = new NewVarInfo { Name = name, Raw = raw, Type = type, Scope = scope, Initial = initial };
            newVarByName[name] = info;
            newVarByRaw[raw] = info;
            return true;
        }

        public static bool TryGetNewVar(uint raw, out NewVarInfo info)
        {
            return newVarByRaw.TryGetValue(raw, out info);
        }

        public static bool TryGetNewVar(string name, out NewVarInfo info)
        {
            info = null;
            return name != null && newVarByName.TryGetValue(name.Trim(), out info);
        }

        public static bool TryParseNewVar(string name, out uint raw)
        {
            NewVarInfo info;
            raw = 0;
            if (!TryGetNewVar(name, out info))
                return false;
            raw = info.Raw;
            return true;
        }

        /// <summary>The slot a new name gets: the lowest one no known name uses, or -1 when all 64 are taken.</summary>
        public static int FreeNewVarSlot()
        {
            var used = new HashSet<uint>(newVarByName.Values.Select(v => v.Raw));
            for (int k = 0; k < NewVarSlots; k++)
                if (!used.Contains(NewVarBase + (uint)k))
                    return k;
            return -1;
        }

        public override string ToString()
        {
            string alias;
            NewVarInfo nv;
            if (ShowAliases && newVarByRaw.TryGetValue(Raw, out nv))
                return nv.Name;
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
            if (aliasToRaw.TryGetValue(text, out aliased) || TryParseNewVar(text, out aliased))
            {
                Raw = aliased;
            }
            else if (text.StartsWith("0x", StringComparison.InvariantCultureIgnoreCase))
            {
                Raw = uint.Parse(text.Substring(2), NumberStyles.HexNumber);
            }
            else if (text.IndexOf('-') < 0 || text.IndexOf('[') < 0)
            {
                throw new FormatException($"unknown variable or alias \"{text}\"" +
                    (IsAliasName(text) ? $" (a new variable needs New_Var(Name={text}) in one of the fighter's scripts)" : ""));
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
