using Sm4shCommand.GUI;
using Sm4shCommand.Nodes;
using Sm4shCommand.Classes;
using System;
using System.Drawing;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Windows.Forms;
using static Sm4shCommand.Runtime;
using SALT.PARAMS;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;
using System.ComponentModel;
using SALT.Moveset.MSC;

namespace Sm4shCommand
{
    public partial class AcmdMain : Form
    {
        public AcmdMain()
        {
            InitializeComponent();
            this.Text = $"{Program.Title} - ";
            Manager = new WorkspaceManager();
            ScriptFiles = new SortedList<string, IScriptCollection>();

            // The toolbar buttons had no handlers.
            saveToolStripButton.Click += saveToolStripMenuItem_Click;
            saveToolStripButton.ToolTipText = "Save all (Ctrl+S)";
            openToolStripButton.Click += fOpen_Click;

            var defs = new ToolStripMenuItem("Command Definitions..", null, commandDefinitions_Click);
            toolsToolStripMenuItem.DropDownItems.Add(defs);
            var varNames = new ToolStripMenuItem("Show variables as LA-Int[1] style") { CheckOnClick = true };
            varNames.Checked = FighterVariable.ShowDescriptiveNames = Runtime.GetSetting("DescriptiveVariableNames", false);
            varNames.CheckedChanged += (o, e) =>
            {
                FighterVariable.ShowDescriptiveNames = varNames.Checked;
                Runtime.SetSetting("DescriptiveVariableNames", varNames.Checked);
                LogMessage("Reopen a script to see the change.");
            };
            viewToolStripMenuItem.DropDownItems.Add(varNames);
            var aliases = new ToolStripMenuItem("Show Variable Aliases (e.g. OPP_HITSTUN)") { CheckOnClick = true };
            aliases.Checked = FighterVariable.ShowAliases = Runtime.GetSetting("VariableAliases", true);
            aliases.ToolTipText = "Variables with a name in the Aliases folder are shown by it. Names always compile.";
            aliases.CheckedChanged += (o, e) =>
            {
                FighterVariable.ShowAliases = aliases.Checked;
                Runtime.SetSetting("VariableAliases", aliases.Checked);
                LogMessage("Reopen a script to see the change (names and numbers both compile).");
            };
            viewToolStripMenuItem.DropDownItems.Add(aliases);

            // Int parameters as decimal / floats instead of hex (ACMDCommand.FormatInt); they compile
            // back to the same values either way.
            var decimalInts = new ToolStripMenuItem("Show Numbers as Decimal (e.g. Angle=361)") { CheckOnClick = true };
            var floatBits = new ToolStripMenuItem("Show Float Values in Int Parameters as Floats (1.5f)") { CheckOnClick = true };
            var hexParams = new ToolStripMenuItem("Parameters Always in Hex..");
            ACMDCommand.DecimalInts = decimalInts.Checked = Runtime.GetSetting("DecimalNumbers", false);
            ACMDCommand.FloatBitsAsFloats = floatBits.Checked = Runtime.GetSetting("FloatBitsAsFloats", true);
            floatBits.Enabled = decimalInts.Checked;
            string savedHex = Runtime.GetSettingText("HexParameters", null);
            if (savedHex != null)
                SetHexParams(savedHex);
            decimalInts.CheckedChanged += (o, e) =>
            {
                ACMDCommand.DecimalInts = decimalInts.Checked;
                floatBits.Enabled = decimalInts.Checked;
                Runtime.SetSetting("DecimalNumbers", decimalInts.Checked);
                LogMessage("Reopen a script to see the change (both forms compile).");
            };
            floatBits.CheckedChanged += (o, e) =>
            {
                ACMDCommand.FloatBitsAsFloats = floatBits.Checked;
                Runtime.SetSetting("FloatBitsAsFloats", floatBits.Checked);
                LogMessage("Reopen a script to see the change (both forms compile).");
            };
            hexParams.Click += (o, e) =>
            {
                string current = string.Join(", ", ACMDCommand.HexParams.OrderBy(x => x).ToArray());
                using (var dlg = new Form())
                {
                    dlg.Text = "Parameters Always in Hex";
                    dlg.FormBorderStyle = FormBorderStyle.FixedDialog;
                    dlg.MinimizeBox = dlg.MaximizeBox = false;
                    dlg.StartPosition = FormStartPosition.CenterParent;
                    dlg.ClientSize = new Size(440, 130);
                    var label = new Label { Left = 12, Top = 10, Width = 416, Height = 30, Text = "Parameter names (comma separated) shown in hex even with decimal numbers on, e.g. hashes and IDs:" };
                    var box = new TextBox { Left = 12, Top = 46, Width = 416, Text = current };
                    var ok = new Button { Text = "OK", Left = 272, Top = 92, Width = 75, DialogResult = DialogResult.OK };
                    var cancel = new Button { Text = "Cancel", Left = 353, Top = 92, Width = 75, DialogResult = DialogResult.Cancel };
                    dlg.Controls.AddRange(new Control[] { label, box, ok, cancel });
                    dlg.AcceptButton = ok;
                    dlg.CancelButton = cancel;
                    if (dlg.ShowDialog(this) != DialogResult.OK)
                        return;
                    SetHexParams(box.Text);
                    Runtime.SetSettingText("HexParameters", string.Join(", ", ACMDCommand.HexParams.ToArray()));
                    LogMessage("Reopen a script to see the change.");
                }
            };
            viewToolStripMenuItem.DropDownItems.Add(new ToolStripSeparator());
            viewToolStripMenuItem.DropDownItems.Add(decimalInts);
            viewToolStripMenuItem.DropDownItems.Add(floatBits);
            viewToolStripMenuItem.DropDownItems.Add(hexParams);

            var autoParse = new ToolStripMenuItem("Auto-Parse Animations on Open") { CheckOnClick = true };
            autoParse.Checked = Runtime.GetSetting("AutoParseAnimations", true);
            autoParse.ToolTipText = "When a file, fighter folder or project is opened, parse the fighter's motion folder\n" +
                "(found next to the opened folder or one of its parents) to name its scripts.";
            autoParse.CheckedChanged += (o, e) =>
            {
                Runtime.SetSetting("AutoParseAnimations", autoParse.Checked);
                if (autoParse.Checked && _lastOpened != null)
                    AutoParseAnimations(_lastOpened, true);
            };
            toolsToolStripMenuItem.DropDownItems.Insert(toolsToolStripMenuItem.DropDownItems.IndexOf(parseAnimationsToolStripMenuItem) + 1, autoParse);

            toolsToolStripMenuItem.DropDownItems.Add(new ToolStripSeparator());
            toolsToolStripMenuItem.DropDownItems.Add(new ToolStripMenuItem("Reload Tooltips", null, (o, e) =>
            {
                Tooltips.Load();
                LogMessage($"Tooltips: {Tooltips.Entries.Count} value tooltips.");
            }));
            toolsToolStripMenuItem.DropDownItems.Add(new ToolStripMenuItem("Open Tooltips Folder", null, (o, e) =>
            {
                try
                {
                    System.IO.Directory.CreateDirectory(Tooltips.Folder);
                    System.Diagnostics.Process.Start(Tooltips.Folder);
                }
                catch (Exception ex) { LogMessage($"Couldn't open {Tooltips.Folder}: {ex.Message}"); }
            }));
            toolsToolStripMenuItem.DropDownItems.Add(new ToolStripMenuItem("Reload Variable Aliases", null, (o, e) => LoadAliases()));
            toolsToolStripMenuItem.DropDownItems.Add(new ToolStripMenuItem("Open Aliases Folder", null, (o, e) =>
            {
                try
                {
                    System.IO.Directory.CreateDirectory(VariableAliases.Folder);
                    System.Diagnostics.Process.Start(VariableAliases.Folder);
                }
                catch (Exception ex) { LogMessage($"Couldn't open {VariableAliases.Folder}: {ex.Message}"); }
            }));

            var treeMenu = new ContextMenuStrip();
            treeMenu.Items.Add(new ToolStripMenuItem("Open", null, (o, e) => { if (FileTree.SelectedNode != null) OpenNode(FileTree.SelectedNode); }));
            treeMenu.Items.Add(new ToolStripMenuItem("Add Script..", null, addScript_Click));
            treeMenu.Items.Add(new ToolStripMenuItem("Set Name..", null, setName_Click));
            treeMenu.Items.Add(new ToolStripMenuItem("Copy Hash", null, (o, e) =>
            {
                var sn = FileTree.SelectedNode as ScriptNode;
                if (sn != null)
                    Clipboard.SetText($"0x{sn.Identifier:X8}");
            }));
            FileTree.ContextMenuStrip = treeMenu;

            ITS_EDITOR.OpenScriptRequested += OpenScriptByHash;
        }

        public const string FileFilter =
                              "All Supported Files (*.bin, *.mscsb)|*.bin;*.mscsb|" +
                              "ACMD Binary (*.bin)|*.bin|" +
                              "MotionScript Binary (*.mscsb)|*.mscsb|" +
                              "All Files (*.*)|*.*";

        private OpenFileDialog ofDlg = new OpenFileDialog() { Filter = FileFilter };
        private SaveFileDialog sfDlg = new SaveFileDialog() { Filter = FileFilter };
        private FolderSelectDialog fsDlg = new FolderSelectDialog();

        private WorkspaceManager Manager { get; set; }
        public Project ActiveProject
        {
            get
            {
                if (FileTree.SelectedNode == null)
                    return null;

                var node = FileTree.SelectedNode;
                while (!((node = node.Parent) is Project))
                    node = node.Parent;

                if (node is Project)
                    return (Project)node;
                else
                    return null;
            }
        }

        public SortedList<string, IScriptCollection> ScriptFiles { get; set; }
        public ParamFile ParamFile { get; set; }
        public MTable MotionTable { get; set; }
        public IDE_MODE IDEMode { get; private set; }

        private void ACMDMain_Load(object sender, EventArgs e)
        {
            Runtime.LoadAnimNames();
            LogMessage($"AnimNames.txt: {Runtime.AnimNames.Count} script names.");
            Tooltips.Load();
            LogMessage($"Tooltips: {Tooltips.Entries.Count} value tooltips from {Tooltips.Folder}.");
            LoadAliases();
            Runtime.LoadCommandDefinitions();
        }
        private void LoadAliases()
        {
            var problems = VariableAliases.Load();
            LogMessage($"Variable aliases: {FighterVariable.AliasCount} from {VariableAliases.Folder}." +
                (problems.Count > 0 ? $" Skipped {problems.Count} bad line(s): " + string.Join("; ", problems.Take(5).ToArray()) : ""));
        }
        private void tabControl1_DrawItem(object sender, DrawItemEventArgs e)
        {
            if (e.Index > Viewport.TabPages.Count - 1)
                return;

            if (e.Index == Viewport.SelectedIndex)
                e.Graphics.FillRectangle(Brushes.ForestGreen, e.Bounds);
            else
                e.Graphics.FillRectangle(SystemBrushes.ActiveBorder, e.Bounds);

            e.Graphics.FillEllipse(new SolidBrush(Color.IndianRed), e.Bounds.Right - 18, e.Bounds.Top + 3, e.Graphics.MeasureString("x", Font).Width + 4, Font.Height);
            e.Graphics.DrawEllipse(Pens.Black, e.Bounds.Right - 18, e.Bounds.Top + 3, e.Graphics.MeasureString("X", Font).Width + 3, Font.Height);
            e.Graphics.DrawString("X", new Font(e.Font, FontStyle.Bold), Brushes.Black, e.Bounds.Right - 17, e.Bounds.Top + 3);
            e.Graphics.DrawString(Viewport.TabPages[e.Index].Text, e.Font, Brushes.Black, e.Bounds.Left + 17, e.Bounds.Top + 3);
            e.DrawFocusRectangle();
        }

        private void cboMode_SelectedIndexChanged(object sender, EventArgs e)
        {
            Runtime.WorkingEndian = (Endianness)cboMode.SelectedIndex;
        }
        private void aboutToolStripMenuItem_Click_1(object sender, EventArgs e)
        {
            var abtBox = new AboutBox();
            abtBox.ShowDialog();
        }

        private void fOpen_Click(object sender, EventArgs e)
        {
            if (ofDlg.ShowDialog() == DialogResult.OK)
                OpenFile(ofDlg.FileName);
        }

        /// <summary>
        /// Opens a path given on the command line (or dropped on the exe): a folder opens as a
        /// fighter, a file as a single file.
        /// </summary>
        public void OpenPath(string path)
        {
            if (Directory.Exists(path))
                OpenFighter(path);
            else if (File.Exists(path))
                OpenFile(path);
            else
                LogMessage($"Not found: {path}");
        }

        public unsafe void OpenFile(string fileName)
        {
            {
                this.Reset();
                if (fileName.EndsWith(".bin"))
                {
                    DataSource source = new DataSource(FileMap.FromFile(fileName));
                    if (*(buint*)source.Address == 0x41434D44) // ACMD
                    {
                        if (*(byte*)(source.Address + 0x04) == 0x02)
                            Runtime.WorkingEndian = Endianness.Little;
                        else if ((*(byte*)(source.Address + 0x04) == 0x00))
                            Runtime.WorkingEndian = Endianness.Big;

                        var f = new ACMDFile(source);
                        ScriptFiles.Add(fileName, f);
                        ScriptComments.Load(fileName, f);
                        var node = new TreeNode("ACMD") { Name = "nACMD" };
                        foreach (var keypair in f.Scripts)
                        {
                            var sn = new ScriptNode(keypair.Key, "", keypair.Value);
                            sn.UpdateText();
                            node.Nodes.Add(sn);
                        }
                        FileTree.Nodes.Add(node);
                    }
                    else if (*(buint*)source.Address == 0xFFFF0000)
                    {
                        source.Close();
                        ParamFile = new ParamFile(fileName);
                        var node = new TreeNode("PARAMS") { Name = "nPARAMS" };
                        FileTree.Nodes.Add(node);
                        PopulateParams();
                    }
                }
                else if (fileName.EndsWith(".mscsb")) // MSC
                {
                    var f = new MSCFile(fileName);
                    ScriptFiles.Add(fileName, f);

                    var node = new TreeNode("MSC") { Name = "nMSC" };
                    for (int i = 0; i < f.Scripts.Count; i++)
                    {
                        var sn = new ScriptNode((uint)i, $"{i:D8}", f.Scripts.Values[i]);
                        if (((MSCScript)f.Scripts.Values[i]).IsEntrypoint)
                            sn.Text = "Entrypoint";
                        else if (i == 0)
                            sn.Text = "Init";

                        node.Nodes.Add(sn);
                    }
                    FileTree.Nodes.Add(node);
                }
                IDEMode = IDE_MODE.File;
                this.Text += fileName;
            }
            AutoParseAnimations(fileName);
        }
        private void fitOpen_Click(object sender, EventArgs e)
        {
            if (fsDlg.ShowDialog() == DialogResult.OK)
                OpenFighter(fsDlg.SelectedPath);
        }

        public void OpenFighter(string folder)
        {
            {
                this.Reset();
                foreach (var p in Directory.EnumerateFiles(folder))
                {
                    if (p.EndsWith(".bin"))
                    {
                        var acmd = new ACMDFile(p);
                        ScriptFiles.Add(p, acmd);
                        ScriptComments.Load(p, acmd);
                        Runtime.WorkingEndian = acmd.Endian;
                    }
                }
                var mtable = Path.Combine(folder, "motion.mtable");
                if (File.Exists(mtable))
                    MotionTable = new MTable(mtable, Runtime.WorkingEndian);
                else
                {
                    MotionTable = new MTable(new List<uint>(), Runtime.WorkingEndian);
                    LogMessage("No motion.mtable in this folder; every script is listed as unlisted.");
                }

                var acmdnode = new TreeNode("ACMD") { Name = "nACMD" };
                FileTree.Nodes.Add(acmdnode);
                PopulateFighterScripts();
                IDEMode = IDE_MODE.Fighter;
                this.Text += folder;
            }
            AutoParseAnimations(folder);
        }

        /// <summary>
        /// Lists a fighter's scripts: one node per motion.mtable entry, then every script that isn't in
        /// the motion table ("unlisted": subroutines reached through JUMP/CALL, and unused ones).
        /// </summary>
        void PopulateFighterScripts()
        {
            var acmdnode = FileTree.Nodes.Find("nACMD", false).FirstOrDefault();
            if (acmdnode == null)
                return;
            FileTree.BeginUpdate();
            acmdnode.Nodes.Clear();
            for (int i = 0; i < MotionTable.Count; i++)
                acmdnode.Nodes.Add(MakeFighterNode(MotionTable[i], i, false));

            var listed = new HashSet<uint>(MotionTable.ToList());
            var unlisted = new SortedSet<uint>();
            foreach (var file in ScriptFiles.Values)
                foreach (var crc in file.Scripts.Keys)
                    if (!listed.Contains(crc))
                        unlisted.Add(crc);
            foreach (var crc in unlisted.OrderBy(x => Runtime.ScriptLabel(x), StringComparer.OrdinalIgnoreCase))
                acmdnode.Nodes.Add(MakeFighterNode(crc, -1, true));
            FileTree.EndUpdate();
            _nodeCache = null;
        }

        ScriptNode MakeFighterNode(uint crc, int motionIndex, bool unlisted)
        {
            var node = new ScriptNode(crc, "") { MotionIndex = motionIndex, Unlisted = unlisted };
            foreach (var keypair in ScriptFiles)
            {
                if (keypair.Value.Scripts.Keys.Contains(crc))
                    node.Scripts.Add(Path.GetFileNameWithoutExtension(keypair.Key), keypair.Value.Scripts[crc]);
            }
            if (unlisted)
                node.ForeColor = Color.DimGray;
            node.UpdateText();
            return node;
        }
        private void projOpen_Click(object sender, EventArgs e)
        {
            ProjectWizard dlg = new ProjectWizard();
            dlg.ShowDialog();
            if (dlg.DialogResult == DialogResult.OK)
            {
                Manager.OpenProject(dlg.Project.ProjPath);
                IDEMode = IDE_MODE.Project;
                AutoParseAnimations(dlg.Project.ProjPath);
            }
        }
        private void saveToolStripMenuItem_Click(object sender, EventArgs e)
        {
            // Scripts open in tabs only reach the file when they're compiled, which used to happen
            // only when their tab was closed, so saving with tabs open saved nothing new.
            if (!ApplyOpenEditors())
                return;

            if (IDEMode == IDE_MODE.Project)
            {
                if (Manager.Projects.Count > 0)
                    foreach (var proj in Manager.Projects.Values)
                        proj.Save();
            }
            else if (IDEMode == IDE_MODE.Fighter)
            {
                // Each file goes back where it was opened from (this used to write to the working directory).
                foreach (var keypair in ScriptFiles)
                {
                    keypair.Value.Export(keypair.Key);
                    ScriptComments.Save(keypair.Key, keypair.Value);
                }
                MotionTable.Export(
                    Path.Combine(Path.GetDirectoryName(ScriptFiles.Keys[0]), "motion.mtable"));
            }
            else if (IDEMode == IDE_MODE.File)
            {
                if (ScriptFiles.Count > 0)
                {
                    ScriptFiles.Values[0].Export(ScriptFiles.Keys[0]);
                    ScriptComments.Save(ScriptFiles.Keys[0], ScriptFiles.Values[0]);
                }
                else if (ParamFile != null)
                {
                    ParamFile.Export(ParamFile.Filepath);
                }
            }
            else
                return;
            LogMessage("Saved.");
        }

        /// <summary>
        /// Compiles every open script tab into its script. On an error, shows that tab and the line
        /// and returns false (nothing should be saved then).
        /// </summary>
        bool ApplyOpenEditors()
        {
            foreach (TabPage page in Viewport.TabPages)
            {
                var editor = page as CodeEditor;
                if (editor == null)
                    continue;
                TabControl tabs = (TabControl)editor.Controls[0];
                foreach (TabPage sub in tabs.TabPages)
                {
                    var box = sub.Controls[0] as ITS_EDITOR;
                    string error;
                    if (box != null && !box.TryApplyChanges(out error))
                    {
                        Viewport.SelectedTab = page;
                        tabs.SelectedTab = sub;
                        box.Focus();
                        MessageBox.Show(this, $"{page.Text} ({sub.Text}) doesn't compile, so nothing was saved.\n\n{error}",
                            "Script error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                        return false;
                    }
                }
            }
            return true;
        }
        private void saveAsToolStripMenuItem_Click(object sender, EventArgs e)
        {
            if (!ApplyOpenEditors())
                return;

            if (IDEMode == IDE_MODE.Project)
            {
                if (fsDlg.ShowDialog() == DialogResult.OK)
                {
                    throw new NotImplementedException("Saving workspaces not yet supported");

                    //if (Manager.Projects.Count > 0)
                    //    foreach (var proj in Manager.Projects.Values)
                    //        proj.Save();
                }
            }
            else if (IDEMode == IDE_MODE.Fighter)
            {
                if (fsDlg.ShowDialog() == DialogResult.OK)
                {
                    foreach (var keypair in ScriptFiles)
                    {
                        keypair.Value.Export(Path.Combine(fsDlg.SelectedPath, Path.GetFileName(keypair.Key)));
                        ScriptComments.Save(Path.Combine(fsDlg.SelectedPath, Path.GetFileName(keypair.Key)), keypair.Value);
                    }
                    MotionTable.Export(Path.Combine(fsDlg.SelectedPath, "motion.mtable"));
                }
            }
            else if (IDEMode == IDE_MODE.File)
            {
                if (ScriptFiles.Count > 0)
                {
                    sfDlg.FileName = Path.GetFileNameWithoutExtension(ScriptFiles.Keys[0]);
                    if (sfDlg.ShowDialog() == DialogResult.OK)
                    {
                        ScriptFiles.Values[0].Export(sfDlg.FileName);
                        ScriptComments.Save(sfDlg.FileName, ScriptFiles.Values[0]);
                    }
                }
                else if (ParamFile != null)
                {
                    sfDlg.FileName = Path.GetFileNameWithoutExtension(ParamFile.Filepath);
                    if (sfDlg.ShowDialog() == DialogResult.OK)
                        ParamFile.Export(sfDlg.FileName);
                }
            }
        }

        private void ProjectToolStripMenuItem_Click(object sender, EventArgs e)
        {
            using (var dlg = new OpenFileDialog())
            {
                dlg.Filter = "All Files (*.*)|*.*|Project (*.fitproj)|*.fitproj";
                if (dlg.ShowDialog() == DialogResult.OK)
                {
                    Manager.OpenProject(dlg.FileName);
                    AutoParseAnimations(dlg.FileName);
                }
            }
        }

        private void FileTree_NodeMouseDoubleClick(object sender, TreeNodeMouseClickEventArgs e)
        {
            OpenNode(e.Node);
        }

        /// <summary>
        /// Opens a script or parameter node in a tab (or switches to its tab).
        /// </summary>
        public void OpenNode(TreeNode node)
        {
            TabPage p = null;
            if (node is ScriptNode)
            {
                TreeNode root = node;
                while (root.Parent != null)
                    root = root.Parent;

                if (root?.Name == "nACMD")
                    p = new CodeEditor(node as ScriptNode, ACMD_INFO.CMD_NAMES.Values.ToArray());
                else if (root?.Name == "nMSC")
                    p = new CodeEditor(node as ScriptNode, MSC_INFO.NAMES.Values.ToArray());
                else
                    p = new CodeEditor(node as ScriptNode);

            }
            else if (node is ParamListNode)
                p = new ParamEditor(node as ParamListNode);

            if (p != null)
            {
                p.Name = (node is ScriptNode) ? $"script_{((ScriptNode)node).Identifier:X8}" : node.Text + node.Index;
                p.Text = node.Text;
                if (Viewport.TabPages.ContainsKey(p.Name))
                {
                    Viewport.SelectTab(p.Name);
                    return;
                }
                else
                {
                    Viewport.TabPages.Insert(0, p);
                    Viewport.SelectTab(0);
                }
            }
        }

        /// <summary>
        /// An ACMD script node (file, fighter or project mode), as opposed to an MSC one.
        /// </summary>
        static bool IsAcmdNode(ScriptNode node)
        {
            return node.Parent != null && node.Parent.Text == "ACMD";
        }

        IEnumerable<TreeNode> AllNodes(TreeNodeCollection nodes)
        {
            foreach (TreeNode n in nodes)
            {
                yield return n;
                foreach (var c in AllNodes(n.Nodes))
                    yield return c;
            }
        }

        /// <summary>
        /// Opens the script with this hash (Ctrl+click on a JUMP/CALL target).
        /// </summary>
        public void OpenScriptByHash(uint crc)
        {
            if (textBox1.Text.Length > 0)
                textBox1.Text = ""; // the filter may be hiding it
            var node = AllNodes(FileTree.Nodes).OfType<ScriptNode>().FirstOrDefault(x => x.Identifier == crc && IsAcmdNode(x));
            if (node == null)
            {
                MessageBox.Show(this, $"There's no script 0x{crc:X8} ({Runtime.ScriptLabel(crc)}) in the open files.",
                    "Open script", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            FileTree.SelectedNode = node;
            node.EnsureVisible();
            OpenNode(node);
        }
        private void FileTree_NodeMouseClick(object sender, TreeNodeMouseClickEventArgs e)
        {
            FileTree.SelectedNode = FileTree.GetNodeAt(e.Location);
        }

        private void tabControl1_MouseClick(object sender, MouseEventArgs e)
        {
            for (int i = 0; i < Viewport.TabCount; i++)
            {
                Rectangle r = Viewport.GetTabRect(i);
                Rectangle closeButton = new Rectangle(r.Right - 18, r.Top + 3, 13, Font.Height);
                if (closeButton.Contains(e.Location))
                {
                    TabPage p = null;
                    if (Viewport.TabPages[i] is CodeEditor)
                    {
                        p = Viewport.TabPages[i] as CodeEditor;
                        TabControl tmp = (TabControl)p.Controls[0];
                        for (int x = 0; x < tmp.TabCount; x++)
                        {
                            ITS_EDITOR box = (ITS_EDITOR)tmp.TabPages[x].Controls[0];
                            string error;
                            if (!box.TryApplyChanges(out error))
                            {
                                tmp.SelectedIndex = x;
                                var answer = MessageBox.Show(this,
                                    $"{p.Text} ({tmp.TabPages[x].Text}) doesn't compile:\n\n{error}\n\nClose it anyway and lose these changes?",
                                    "Script error", MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
                                if (answer != DialogResult.Yes)
                                    return;
                            }
                        }
                    }
                    else if (Viewport.TabPages[i] is ParamEditor)
                    {
                        var tmp = Viewport.TabPages[i] as ParamEditor;
                        p = tmp;
                        var node = tmp.Node;

                        ParamFile file;
                        if (IDEMode == IDE_MODE.Project)
                            file = ActiveProject.Fighter_Param_vl;
                        else
                            file = ParamFile;

                        ((ParamGroup)file.Groups[node.Group]).Chunks[node.Entry] = node.Parameters.ToArray();
                    }
                    if (p != null)
                        Viewport.TabPages.Remove(p);
                    return;
                }
            }
        }
        static void SetHexParams(string list)
        {
            ACMDCommand.HexParams.Clear();
            foreach (var name in list.Split(','))
                if (name.Trim().Length > 0)
                    ACMDCommand.HexParams.Add(name.Trim());
        }

        // ------------------------------------------------------ automatic parsing

        string _lastOpened;
        readonly HashSet<string> _parsedMotionFolders = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        /// <summary>
        /// Tools > Parse Animations, done automatically on the fighter's motion folder when something
        /// is opened (when the setting is on). Each folder is parsed once per session unless forced.
        /// </summary>
        void AutoParseAnimations(string openedPath, bool force = false)
        {
            _lastOpened = openedPath;
            Tooltips.Fighter = Tooltips.FighterFromPath(openedPath);
            if (!Runtime.GetSetting("AutoParseAnimations", true))
                return;
            string motion = Runtime.FindMotionFolder(openedPath);
            if (motion == null)
            {
                LogMessage("Auto-parse: no motion folder found next to this path; use Tools > Parse Animations.. to pick one.");
                return;
            }
            if (!force && _parsedMotionFolders.Contains(motion))
                return;
            try
            {
                Cursor = Cursors.WaitCursor;
                var dict = Runtime.ParseAnimations(motion);
                int before = Runtime.AnimNames.Count;
                Runtime.SaveAnimNames(dict);
                _parsedMotionFolders.Add(motion);
                LogMessage($"Auto-parse: {motion}: {dict.Count} names found, {Runtime.AnimNames.Count - before} new.");
                RefreshScriptNames();
            }
            catch (Exception ex)
            {
                LogMessage($"Auto-parse failed ({motion}): {ex.Message}");
            }
            finally
            {
                Cursor = Cursors.Default;
            }
        }

        private void parseAnimationsToolStripMenuItem_Click(object sender, EventArgs e)
        {
            if (fsDlg.ShowDialog() == DialogResult.OK)
            {
                var dict = Runtime.ParseAnimations(fsDlg.SelectedPath);
                int before = Runtime.AnimNames.Count;
                Runtime.SaveAnimNames(dict); // remembered in AnimNames.txt for next time
                LogMessage($"Parse Animations: {dict.Count} names found, {Runtime.AnimNames.Count - before} new (saved to AnimNames.txt).");
                RefreshScriptNames();
            }
        }

        void RefreshScriptNames()
        {
            FileTree.BeginUpdate();
            foreach (var node in AllNodes(FileTree.Nodes).OfType<ScriptNode>())
            {
                if (IsAcmdNode(node))
                    node.UpdateText();
            }
            if (_nodeCache != null && _childCache != null) // filtered: also the hidden ACMD nodes
            {
                for (int r = 0; r < _nodeCache.Length; r++)
                    if (_nodeCache[r].Text == "ACMD")
                        foreach (var node in _childCache[r].OfType<ScriptNode>())
                            node.UpdateText();
            }
            FileTree.EndUpdate();
        }

        // ------------------------------------------------------------- tree menu

        private void setName_Click(object sender, EventArgs e)
        {
            var node = FileTree.SelectedNode as ScriptNode;
            if (node == null)
                return;
            using (var dlg = new RenameForm(Runtime.AnimNames.ContainsKey(node.Identifier) ? Runtime.AnimNames[node.Identifier] : ""))
            {
                dlg.Text = $"Name for 0x{node.Identifier:X8}";
                if (dlg.ShowDialog(this) != DialogResult.OK || dlg.NewName.Trim().Length == 0)
                    return;
                string name = dlg.NewName.Trim();
                if (System.Security.Cryptography.Crc32.Compute(name.ToLower()) != node.Identifier)
                {
                    var answer = MessageBox.Show(this,
                        $"\"{name}\" isn't this script's animation name (its CRC32 is 0x{System.Security.Cryptography.Crc32.Compute(name.ToLower()):X8}, not 0x{node.Identifier:X8}).\n\nUse it as a label for this script anyway?",
                        "Set name", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
                    if (answer != DialogResult.Yes)
                        return;
                }
                Runtime.SaveAnimName(node.Identifier, name);
                RefreshScriptNames();
            }
        }

        private void addScript_Click(object sender, EventArgs e)
        {
            var acmdFiles = ScriptFiles.Where(x => x.Value is ACMDFile).ToList();
            var acmdnode = FileTree.Nodes.Find("nACMD", false).FirstOrDefault();
            if (acmdFiles.Count == 0 || acmdnode == null || (IDEMode != IDE_MODE.File && IDEMode != IDE_MODE.Fighter))
            {
                MessageBox.Show(this, "Open an ACMD file (File > Open > File..) or a fighter folder (File > Open > Fighter..) first.",
                    "Add script", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            uint crc;
            string name;
            using (var dlg = new RenameForm(""))
            {
                dlg.Text = "Add script: animation name or 0xHASH";
                if (dlg.ShowDialog(this) != DialogResult.OK)
                    return;
                name = dlg.NewName.Trim();
            }
            if (name.Length == 0)
                return;
            if (name.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
            {
                if (!uint.TryParse(name.Substring(2), System.Globalization.NumberStyles.HexNumber, null, out crc))
                {
                    MessageBox.Show(this, $"\"{name}\" isn't a hex hash.", "Add script", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }
            }
            else
            {
                crc = System.Security.Cryptography.Crc32.Compute(name.ToLower());
                if (!Runtime.AnimNames.ContainsKey(crc))
                    Runtime.SaveAnimName(crc, name);
            }

            if (acmdFiles.All(x => x.Value.Scripts.ContainsKey(crc)))
            {
                MessageBox.Show(this, $"0x{crc:X8} ({Runtime.ScriptLabel(crc)}) already has a script.", "Add script", MessageBoxButtons.OK, MessageBoxIcon.Information);
                OpenScriptByHash(crc);
                return;
            }

            if (textBox1.Text.Length > 0)
                textBox1.Text = "";

            // A new script (just Script_End) in every ACMD file that doesn't have one yet
            // (in a fighter folder: game, effect, sound and expression).
            foreach (var pair in acmdFiles)
                if (!pair.Value.Scripts.ContainsKey(crc))
                    pair.Value.Scripts.Add(crc, ACMDScript.CreateEmpty(crc));

            if (IDEMode == IDE_MODE.Fighter)
            {
                if (!MotionTable.Contains(crc))
                {
                    var answer = MessageBox.Show(this,
                        "Also add it to motion.mtable?\n\nYes for an animation the game plays (a new motion).\n" +
                        "No for a script only reached through JUMP/CALL (it's listed as [unlisted]).",
                        "Add script", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
                    if (answer == DialogResult.Yes)
                        MotionTable.Add(crc);
                }
                PopulateFighterScripts();
            }
            else
            {
                var file = acmdFiles[0].Value;
                var sn = new ScriptNode(crc, "", file.Scripts[crc]);
                sn.UpdateText();
                acmdnode.Nodes.Add(sn);
                _nodeCache = null;
            }
            LogMessage($"Added script 0x{crc:X8} ({Runtime.ScriptLabel(crc)}). Save to write it to the file.");
            OpenScriptByHash(crc);
        }

        private void commandDefinitions_Click(object sender, EventArgs e)
        {
            using (var dlg = new CommandDefinitionsForm())
                dlg.ShowDialog(this);
        }

        public void PopulateParams()
        {
            int group = 0;
            foreach (var grp in ParamFile.Groups)
            {
                var groupnode = new TreeNode($"Group[{group}]");
                if (grp is ParamGroup)
                {
                    int entry = 0;
                    foreach (var chunk in ((ParamGroup)grp).Chunks)
                    {
                        var node = new ParamListNode(group, entry) { Text = $"Entry[{entry}]" };
                        foreach (var val in chunk)
                            node.Parameters.Add(val);
                        groupnode.Nodes.Add(node);
                        entry++;
                    }
                }
                else
                {
                    var node = new ParamListNode(group, 0) { Text = $"Values[{group}]" };
                    foreach (var col in grp.Values)
                    {
                        node.Parameters.Add(new ParamEntry(col.Value, col.Type));
                    }
                    groupnode.Nodes.Add(node);
                }

                var paramnode = FileTree.Nodes.Find("nPARAMS", false)[0];
                paramnode?.Nodes.Add(groupnode);
                group++;
            }
        }
        public void Reset()
        {
            this.Text = $"{Program.Title} - ";
            FileTree.Nodes.Clear();
            ScriptFiles.Clear();
            Viewport.TabPages.Clear();
            ParamFile = null;
            Manager = new WorkspaceManager();
            MotionTable = null;
            IDEMode = IDE_MODE.NONE;
            _nodeCache = null;

        }

        public enum IDE_MODE
        {
            File,
            Fighter,
            Project,
            NONE
        }

        private void closeToolStripMenuItem_Click(object sender, EventArgs e)
        {
            this.Reset();
        }

        TreeNode[] _nodeCache;
        private void textBox1_TextChanged(object sender, EventArgs e)
        {
            if (_nodeCache == null)
            {
                _nodeCache = new TreeNode[FileTree.Nodes.Count];
                FileTree.Nodes.CopyTo(_nodeCache, 0);
                _childCache = _nodeCache.Select(x => x.Nodes.Cast<TreeNode>().ToArray()).ToArray();
            }
            bool addAll = string.IsNullOrEmpty(textBox1.Text);

            FileTree.BeginUpdate();
            for (int r = 0; r < _nodeCache.Length; r++)
            {
                TreeNode root = _nodeCache[r];
                root.Nodes.Clear();
                foreach (TreeNode leaf in _childCache[r])
                {
                    if (addAll || leaf.Text.Contains(textBox1.Text, StringComparison.OrdinalIgnoreCase))
                        root.Nodes.Add(leaf);
                }
            }
            if (!addAll)
                FileTree.ExpandAll();
            FileTree.EndUpdate();
            if (addAll)
                _nodeCache = null; // everything is back in place; later tree changes rebuild the cache
        }
        TreeNode[][] _childCache;
    }
}