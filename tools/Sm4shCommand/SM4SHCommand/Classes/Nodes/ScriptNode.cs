using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Windows.Forms;
using Sm4shCommand.Classes;
using SALT.Moveset;

namespace Sm4shCommand.Nodes
{
    public class ScriptNode : BaseNode
    {
        private static ContextMenuStrip _menu;
        static ScriptNode()
        {
            _menu = new ContextMenuStrip();
        }

        public ScriptNode()
        {
            this.ContextMenuStrip = _menu;
            Scripts = new Dictionary<string, IScript>(4);

        }
        public ScriptNode(uint ident, string text) : this()
        {
            Identifier = ident;
            this.Text = text;
        }
        public ScriptNode(uint ident, string text, IScript script) : this(ident, text)
        {
            Identifier = ident;
            Scripts.Add("Script", script);
        }

        public Dictionary<string, IScript> Scripts { get; set; }
        public uint Identifier { get; set; }

        /// <summary>
        /// Index in motion.mtable, or -1 for a script that isn't in it (an "unlisted" script, e.g. one
        /// only reached through JUMP/CALL) or when there's no motion table (single-file mode).
        /// </summary>
        public int MotionIndex { get; set; } = -1;

        /// <summary>
        /// Shows the script's name (or hash) the way its mode lists it.
        /// </summary>
        public void UpdateText()
        {
            string label = Runtime.ScriptLabel(Identifier);
            if (MotionIndex >= 0)
                Text = $"{MotionIndex:X} - {label}";
            else if (Unlisted)
                Text = $"[unlisted] {label}";
            else
                Text = label;
            ToolTipText = $"0x{Identifier:X8}" + (Unlisted ? " - not in motion.mtable (reached through JUMP/CALL, or unused)" : "");
        }

        /// <summary>
        /// True for a fighter's script that isn't in motion.mtable.
        /// </summary>
        public bool Unlisted { get; set; }
    }
}
