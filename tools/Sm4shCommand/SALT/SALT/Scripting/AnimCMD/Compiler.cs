using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.IO;
using System.Globalization;

namespace SALT.Moveset.AnimCMD
{
    public static class ACMDCompiler
    {
        static ACMDCompiler()
        {
            Commands = new List<ACMDCommand>();
        }

        private static List<ACMDCommand> Commands { get; set; }

        /// <summary>
        /// Opens and compiles the contents of a plaintext script file.
        /// </summary>
        /// <param name="filepath">The path to the file to compile</param>
        /// <returns></returns>
        public static List<MoveDef> CompileFile(string filepath)
        {
            return Compile(File.ReadAllText(filepath));
        }

        private static List<MoveDef> Compile(string input)
        {
            MoveDef move = null;
            StringToken lastToken = new StringToken();
            string curLine = "", codeRegion = "";

            List<string> lines = new List<string>();
            List<MoveDef> movedefs = new List<MoveDef>();
            bool CodeBlock = false;
            int bracketScope = 0;

            foreach (var tok in Tokenizer.Tokenize(input))
            {
                if (tok.Token == "MoveDef")
                {
                    if (move != null)
                        movedefs.Add(move);

                    move = new MoveDef();
                }
                if (lastToken.Token == "MoveDef")
                {
                    move.AnimName = tok.Token;
                    goto end;
                }
                if (tok.Token == "Unlisted")
                {
                    move.Unlisted = true;
                    goto end;
                }
                else if (tok.TokType == TokenType.Bracket)
                {
                    if (tok.Token == "{")
                        bracketScope++;

                    // End of a code block, try and compile
                    if (CodeBlock && tok.TokType == TokenType.Bracket && bracketScope == 2)
                    {
                        var commands = ACMDCompiler.CompileCommands(lines.ToArray()).ToList();
                        if (commands.Count > 0)
                        {
                            move[codeRegion] = commands;
                        }

                        CodeBlock = false;
                        codeRegion = string.Empty;
                        lines.Clear();

                    }
                    else if (bracketScope > 2)
                        curLine += tok.Token;

                    // Marks the beginning of a code block, indicates that we should start
                    // adding tokens together to form a command string.
                    if (lastToken.Token == "Main" || lastToken.Token == "Effect" ||
                        lastToken.Token == "Expression" || lastToken.Token == "Sound")
                    {
                        CodeBlock = true;
                        codeRegion = lastToken.Token;
                    }

                    if (tok.Token == "}")
                        bracketScope--;
                }
                else if (CodeBlock && tok.Token != "\n" && tok.Token != "\r") // if this isn't a newline, add the token to the code line.
                {
                    curLine += tok.Token;
                    goto end;
                }
                else if (CodeBlock && tok.Token == "\n") // Add the completed code line to the list of lines for compilation
                {
                    if (string.IsNullOrEmpty(curLine))
                        goto end;

                    curLine += tok.Token;
                    lines.Add(curLine);
                    curLine = string.Empty;
                }

            end:
                if (tok.TokType != TokenType.Seperator)
                    lastToken = tok;
            }
            if (move != null)
                movedefs.Add(move);

            // clean up in case we compile more than one file
            Commands.Clear();
            return movedefs;
        }

        /// <summary>
        /// Compile a single ACMD command from plaintext. Throws an <see cref="ACMDCompileException"/>
        /// that names the problem (unknown command, wrong number of parameters, bad value).
        /// </summary>
        /// <param name="line"></param>
        /// <returns></returns>
        public static ACMDCommand CompileSingleCommand(string line)
        {
            string s = line.Trim();
            if (s.EndsWith("{"))
                s = s.Substring(0, s.Length - 1).TrimEnd();
            int open = s.IndexOf('(');
            int close = s.LastIndexOf(')');
            if (open < 0 || close < open)
                throw new ACMDCompileException(line, "expected a command like Name(parameters)");
            if (close != s.Length - 1)
                throw new ACMDCompileException(line, $"unexpected text after ')': \"{s.Substring(close + 1)}\"");

            var name = s.Substring(0, open).Trim();
            var inner = s.Substring(open + 1, close - open - 1);
            var parameters = inner.Trim().Length == 0 ? new string[0] : inner.Split(',');
            for (int i = 0; i < parameters.Length; i++)
            {
                string param = parameters[i];
                if (param.Contains("="))
                    parameters[i] = param.Remove(0, param.IndexOf("=") + 1);
                parameters[i] = parameters[i].Trim();
            }

            uint crc;
            if (!ACMD_INFO.TryGetIdent(name, out crc))
            {
                // unk_XXXXXXXX also works for a known command written by its identifier
                if (!(name.StartsWith("unk_", StringComparison.OrdinalIgnoreCase) &&
                    uint.TryParse(name.Substring(4), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out crc) &&
                    ACMD_INFO.CMD_NAMES.ContainsKey(crc)))
                    throw new ACMDCompileException(line, $"unknown command \"{name}\" (add it in Tools > Command Definitions)");
            }

            ACMDCommand cmd = new ACMDCommand(crc);
            var specs = cmd.ParamSpecifiers;
            if (parameters.Length != specs.Length)
                throw new ACMDCompileException(line, $"{cmd.Name} takes {specs.Length} parameter{(specs.Length == 1 ? "" : "s")} but {parameters.Length} {(parameters.Length == 1 ? "was" : "were")} given");

            for (int i = 0; i < specs.Length; i++)
            {
                string p = parameters[i];
                try
                {
                    switch (specs[i])
                    {
                        case 0: // 0x1A, 26, or a float stored as its bits (1.5f)
                            cmd.Parameters.Add(ACMDCommand.ParseInt(p));
                            break;
                        case 1: // 1.5, 1.5f, or its bits in hex (0x3FC00000, as an int parameter shows it)
                            cmd.Parameters.Add(ParseFloat(p));
                            break;
                        case 2:
                            cmd.Parameters.Add(decimal.Parse(p, NumberStyles.Float, CultureInfo.InvariantCulture));
                            break;
                        case 3:
                            cmd.Parameters.Add(new FighterVariable(p));
                            break;
                    }
                }
                catch (Exception e) when (!(e is ACMDCompileException))
                {
                    string kind = specs[i] == 0 ? "a whole number (e.g. 5 or 0x1A) or a float stored in an int (e.g. 1.5f)" :
                                  specs[i] == 3 ? "a variable (e.g. 0x2100000D)" :
                                  specs[i] == 1 ? "a number (e.g. 1.5 or 250.0)" : "a number";
                    string pname = i < cmd.ParamSyntax.Length ? cmd.ParamSyntax[i] : $"#{i + 1}";
                    throw new ACMDCompileException(line, $"{cmd.Name} parameter {pname} must be {kind}, not \"{p}\"");
                }
            }

            return cmd;
        }
        /// <summary>A float parameter: 1.5, 1.5f, or the float's bits in hex (0x3FC00000; up to 0xFFFF: that number).</summary>
        public static float ParseFloat(string p)
        {
            p = p.Trim();
            bool neg = p.StartsWith("-0x", StringComparison.OrdinalIgnoreCase);
            if (neg || p.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
            {
                uint bits = uint.Parse(p.Substring(neg ? 3 : 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture);
                // small values are numbers (0x5 = 5), as int parameters show them; larger ones are float bits
                float f = bits <= 0xFFFF ? bits : BitConverter.ToSingle(BitConverter.GetBytes(bits), 0);
                return neg ? -f : f;
            }
            return float.Parse(p.TrimEnd('f', 'F'), NumberStyles.Float, CultureInfo.InvariantCulture);
        }
        /// <summary>
        /// Compile an array of code lines.
        /// </summary>
        /// <param name="lines">Array of plaintext code lines.</param>
        /// <returns></returns>
        public static ACMDCommand[] CompileCommands(string[] lines)
        {
            try
            {
                return CompileCommandsUnchecked(lines);
            }
            catch (ArgumentOutOfRangeException)
            {
                throw new ACMDCompileException("", "a '{' block isn't closed with '}' (or a Set_Loop has no Goto)");
            }
        }

        /// <summary>
        /// The code without comments: "// ..." (a whole line, or after a command) and "/* ... */"
        /// (anywhere, over several lines) are removed, then blank lines. Comments never reach the
        /// binary; Sm4shCommand keeps them in a .comments file next to it.
        /// </summary>
        public static List<string> StripComments(IEnumerable<string> lines)
        {
            var output = new List<string>();
            bool inBlock = false;
            foreach (var raw in lines)
            {
                string line = raw ?? "";
                var sb = new StringBuilder();
                int i = 0;
                while (i < line.Length)
                {
                    if (inBlock)
                    {
                        int end = line.IndexOf("*/", i, StringComparison.Ordinal);
                        if (end < 0) { i = line.Length; break; }
                        inBlock = false;
                        i = end + 2;
                    }
                    else if (string.CompareOrdinal(line, i, "/*", 0, 2) == 0)
                    {
                        inBlock = true;
                        i += 2;
                    }
                    else if (string.CompareOrdinal(line, i, "//", 0, 2) == 0)
                        break;
                    else
                        sb.Append(line[i++]);
                }
                string code = sb.ToString().Trim();
                if (code.Length > 0)
                    output.Add(code);
            }
            return output;
        }

        private static ACMDCommand[] CompileCommandsUnchecked(string[] lines)
        {
            var tmpList = StripComments(lines);
            Commands.Clear();
            for (int i = 0; i < tmpList.Count; i++)
            {
                string lineText = tmpList[i];
                if (lineText == "}")
                    throw new ACMDCompileException(lineText, "'}' without a matching '{'");

                ACMDCommand cmd = CompileSingleCommand(tmpList[i]);
                uint ident = cmd.Ident;

                if (HandleSpecialCommands(ref i, ident, ref tmpList) > 0)
                {
                    continue;
                }
                else
                {
                    Commands.Add(cmd);
                }
            }
            return Commands.ToArray();
        }

        /// <summary>Thread_Start(Offset, ID, Flags){ ... } (a new command, tools/acmd_ext_cave.py): its block runs
        /// on its own; the script jumps over it like True. The block must end with Script_End (added if missing).</summary>
        public const uint ThreadStart = 0x4C0DBE48;
        const uint ScriptEndIdent = 0x5766F889;

        private static int HandleSpecialCommands(ref int index, uint ident, ref List<string> lines)
        {
            switch (ident)
            {
                case ThreadStart:
                case 0x895B9275:
                case 0xC31DF569:
                case 0x47810508:
                case 0x870CF021:
                case 0xA5BD4F32:
                    return CompileConditional(ref index, ref lines);
                case 0x0EB375E3:
                    return CompileLoop(ref index, ref lines);
            }

            return 0;
        }

        private static int CompileConditional(ref int Index, ref List<string> lines)
        {
            ACMDCommand cmd = CompileSingleCommand(lines[Index]);
            int len = cmd.Size / 4;
            Commands.Add(cmd);

            while (lines[++Index].Trim() != "}")
            {
                ACMDCommand tmp = CompileSingleCommand(lines[Index]);
                if (IsCmdHandled(tmp.Ident))
                {
                    //recursively add the size of any nested handled statements
                    len += HandleSpecialCommands(ref Index, tmp.Ident, ref lines);
                }
                else
                {
                    len += tmp.Size / 4;
                    Commands.Add(tmp);
                }
            }

            // a thread's block ends with Script_End, which stops the thread (the script itself jumps over it)
            if (cmd.Ident == ThreadStart && Commands[Commands.Count - 1].Ident != ScriptEndIdent)
            {
                ACMDCommand end = new ACMDCommand(ScriptEndIdent);
                len += end.Size / 4;
                Commands.Add(end);
            }

            //check for Else statement. If the next command is Else, set True/False size parameter (current len + Else len)
            //if the True/False statements don't have an Else afterward then just set their size to current len
            if (Index + 1 < lines.Count && lines[Index + 1] != "}"
                && CompileSingleCommand(lines[Index + 1]).Ident == 0x895B9275
                && IsCmdCondition(cmd.Ident))
            {
                ACMDCommand tmp = CompileSingleCommand(lines[++Index]);
                Commands[Commands.IndexOf(cmd)].Parameters[0] = len + tmp.Size / 4;
                //increment handled command length by the size of the Else statement
                len += HandleSpecialCommands(ref Index, tmp.Ident, ref lines);
            }
            else
            {
                Commands[Commands.IndexOf(cmd)].Parameters[0] = len;
            }

            // Next line should be closing bracket, ignore and skip it
            return len;
        }

        private static int CompileLoop(ref int Index, ref List<string> lines)
        {
            int start = Index;

            Commands.Add(CompileSingleCommand(lines[Index]));
            while (CompileSingleCommand(lines[++Index]).Ident != 0x38A3EC78)
            {
                ACMDCommand tmp = CompileSingleCommand(lines[Index]);
                if (IsCmdHandled(tmp.Ident))
                {
                    HandleSpecialCommands(ref Index, tmp.Ident, ref lines);
                }
                else
                {
                    Commands.Add(tmp);
                }
            }

            decimal len = 0;
            int gotoIndex = Index;
            while (--gotoIndex > start)
            {
                if (lines[gotoIndex] == "}")
                    continue;

                var cmd = CompileSingleCommand(lines[gotoIndex]);
                len += cmd.Size / 4;
            }

            ACMDCommand endLoop = CompileSingleCommand(lines[Index]);

            endLoop.Parameters[0] = len / -1;
            Commands.Add(endLoop);

            if (Index + 1 < lines.Count && lines[Index + 1].Trim() == "}")
                Index++;

            // Next line should be closing bracket, ignore and skip it
            return (int)len + 4;
        }

        private static bool IsCmdHandled(uint ident)
        {
            switch (ident)
            {
                case ThreadStart:
                case 0x895B9275://Else
                case 0xC31DF569:
                case 0x47810508:
                case 0x870CF021:
                case 0xA5BD4F32:
                    return true;
                case 0x0EB375E3:
                    return true;
            }

            return false;
        }

        private static bool IsCmdCondition(uint ident)
        {
            switch (ident)
            {
                case 0xC31DF569:
                case 0x47810508:
                case 0x870CF021:
                case 0xA5BD4F32:
                    return true;
            }

            return false;
        }
    }

    /// <summary>
    /// A line of ACMD text that couldn't be compiled. <see cref="LineText"/> is the line as written.
    /// </summary>
    public class ACMDCompileException : Exception
    {
        public ACMDCompileException(string lineText, string message)
            : base($"{message}\n    {lineText.Trim()}")
        {
            this.LineText = lineText;
            this.Reason = message;
        }

        public string LineText { get; private set; }
        public string Reason { get; private set; }
    }

    public class MoveDef
    {
        public string AnimName { get; set; }
        public uint CRC
        {
            get
            {
                uint hash = 0;
                if (AnimName.StartsWith("0x"))
                    hash = UInt32.Parse(AnimName.Substring(2), System.Globalization.NumberStyles.HexNumber);
                else
                    hash = System.Security.Cryptography.Crc32.Compute(AnimName.ToLower());
                return hash;
            }
        }

        public bool Unlisted { get; set; }

        public List<ACMDCommand> Game { get; set; }
        public List<ACMDCommand> Effect { get; set; }
        public List<ACMDCommand> Sound { get; set; }
        public List<ACMDCommand> Expression { get; set; }

        public List<ACMDCommand> this[string id]
        {
            get
            {
                switch (id)
                {
                    case "Main":
                        return Game;
                    case "Effect":
                        return Effect;
                    case "Sound":
                        return Sound;
                    case "Expression":
                        return Expression;
                    default:
                        throw new Exception($"{id} is not a valid event list identifier");
                }
            }
            set
            {
                switch (id)
                {
                    case "Main":
                        Game = value;
                        break;
                    case "Effect":
                        Effect = value;
                        break;
                    case "Sound":
                        Sound = value;
                        break;
                    case "Expression":
                        Expression = value;
                        break;
                    default:
                        throw new Exception($"{id} is not a valid event list identifier");
                }
            }
        }
        public List<ACMDCommand> this[int index]
        {
            get
            {
                switch (index)
                {
                    case 0:
                        return Game;
                    case 1:
                        return Effect;
                    case 2:
                        return Sound;
                    case 3:
                        return Expression;
                    default:
                        throw new Exception($"Could not get event list with index of {index}");
                }
            }
            set
            {
                switch (index)
                {
                    case 0:
                        Game = value;
                        break;
                    case 1:
                        Effect = value;
                        break;
                    case 2:
                        Sound = value;
                        break;
                    case 3:
                        Expression = value;
                        break;
                    default:
                        throw new Exception($"Could not set event list with index of {index}");
                }
            }
        }
    }

    public static class Tokenizer
    {
        static char[] seps = { '=', ',', '(', ')', ' ', '\n', '\r', '\t', ':' };
        static char[] integers = { '-', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9' };

        public static StringToken[] Tokenize(string data)
        {
            List<StringToken> _tokens = new List<StringToken>();
            int i = 0;
            while (i < data.Length)
            {
                StringToken str = new StringToken();
                str.Index = i;
                if (seps.Contains(data[i]))
                    _tokens.Add(new StringToken() { Index = i, Token = data[i++].ToString(), TokType = TokenType.Seperator });
                else
                {
                    while (i < data.Length && !seps.Contains(data[i]))
                    {
                        str.Token += data[i];
                        i++;
                    }

                    if (str.Token.TrimStart().StartsWith("0x", StringComparison.InvariantCultureIgnoreCase))
                        str.TokType = TokenType.Integer;
                    else if (integers.Contains(str.Token[0]))
                        str.TokType = TokenType.FloatingPoint;
                    else if (i < data.Length && data[i] == '=')
                        str.TokType = TokenType.Syntax;
                    else if (str.Token == "{" || str.Token == "}")
                        str.TokType = TokenType.Bracket;
                    else
                        str.TokType = TokenType.String;

                    _tokens.Add(str);
                }
            }
            return _tokens.ToArray();
        }
    }
    public struct StringToken
    {
        public int Index { get { return _index; } set { _index = value; } }
        private int _index;
        public int Length { get { return Token.Length; } }
        public string Token { get { return _strToken; } set { _strToken = value; } }
        private string _strToken;
        public TokenType TokType { get { return _type; } set { _type = value; } }
        private TokenType _type;
    }

    public enum TokenType
    {
        String,
        Syntax,
        Integer,
        FloatingPoint,
        Seperator,
        Bracket,
        NewLine,
    }
}
