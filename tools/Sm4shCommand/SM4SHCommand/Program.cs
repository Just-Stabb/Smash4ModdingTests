using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Threading;
using Sm4shCommand.Classes;
using System.Reflection;
using System.Globalization;

namespace Sm4shCommand
{
    static class Program
    {
        public static readonly string Version = "v1.7.34";
        public static readonly string Title;
        public static readonly string Description;
        public static readonly string Copyright;
        public static readonly string InformationalVersion;

        static Program()
        {
            // (Application.EnableVisualStyles is in Main, after the command-line modes: they run with no window)
            // Missing assembly attributes must not stop the program from starting.
            Title = Attr<AssemblyTitleAttribute>(a => a.Title) ?? "SM4SHCommand";
            Description = Attr<AssemblyDescriptionAttribute>(a => a.Description) ?? "";
            Copyright = Attr<AssemblyCopyrightAttribute>(a => a.Copyright) ?? "";
            InformationalVersion = Attr<AssemblyInformationalVersionAttribute>(a => a.InformationalVersion) ?? Version;
            Title = $"{Title} {Version}";
        }

        static string Attr<T>(Func<T, string> get) where T : Attribute
        {
            try
            {
                var attrs = Assembly.GetExecutingAssembly().GetCustomAttributes(typeof(T), false);
                return attrs.Length > 0 ? get((T)attrs[0]) : null;
            }
            catch
            {
                return null;
            }
        }

        /// <summary>
        /// The main entry point for the application.
        /// </summary>
        [STAThread]
        static void Main(string[] args)
        {
            // Any crash is written (with its stack trace) to Sm4shCommand_errors.log next to the exe.
            AppDomain.CurrentDomain.UnhandledException += (o, e) => ReportError(e.ExceptionObject as Exception, false);
            // (No SetUnhandledExceptionMode: it throws once any control exists, and the default mode
            // already routes UI-thread exceptions to ThreadException.)
            Application.ThreadException += (o, e) => ReportError(e.Exception, true);
            Thread.CurrentThread.CurrentCulture = new CultureInfo("en-US");
            if (args.Length > 0 && args[0].Equals("--merge-sounds", StringComparison.OrdinalIgnoreCase))
            {
                // v1.7.34: Merge sound mods from the command line (no window)
                Environment.ExitCode = MergeSoundsCommandLine(args);
                return;
            }
            Application.EnableVisualStyles();
            AcmdMain main;
            try
            {
                main = Runtime.Instance; // creates the main window
            }
            catch (Exception e)
            {
                ReportError(e is TypeInitializationException && e.InnerException != null ? e.InnerException : e, false);
                return;
            }
            if (args.Length > 0) // a file or fighter folder given on the command line / dropped on the exe
                main.Shown += (o, e) => main.OpenPath(args[0]);
            Application.Run(main);
        }

        [System.Runtime.InteropServices.DllImport("kernel32.dll")]
        static extern bool AttachConsole(int pid);

        const string MergeUsage =
            "SM4SHCommand.exe --merge-sounds OUT_DIR MOD1 MOD2 [MOD3 ...] [options]\n" +
            "  Merges sound mods (folders or .zips, each with its sound/config/soundlabeltable.bin and fighter banks) into the\n" +
            "  new folder OUT_DIR (the Sound Effect Viewer's Merge sound mods..). Writes OUT_DIR/MERGE_REPORT.txt; prints it.\n" +
            "  --base PATH            the base soundlabeltable.bin, or the game data folder holding sound/config/soundlabeltable.bin\n" +
            "                         (default: the viewer's Game data folder, SoundDataFolder in Sm4shCommand.ini)\n" +
            "  --later-wins           a conflict takes the later mod's (default: the first mod's)\n" +
            "  --no-scripts           don't rewrite the mods' ACMD scripts to their remapped ids\n" +
            "  --take-unbanked-rows   take rows a mod changed without shipping their banks (default: the base's kept)\n" +
            "  --copy-all             copy the mods' other files too (a complete install folder)\n" +
            "  --dry-run              write nothing: print the report (OUT_DIR is then left out: every name is a mod)\n" +
            "Exit code 0: merged (or checked) with no error; 1: errors (nothing written); 2: bad arguments.";

        static int MergeSoundsCommandLine(string[] args)
        {
            try { if (Environment.OSVersion.Platform == PlatformID.Win32NT) AttachConsole(-1); } catch { }
            var names = new List<string>();
            string basePath = null;
            var opt = new Sm4shCommand.Sound.MergeOptions();
            bool dry = false;
            for (int i = 1; i < args.Length; i++)
            {
                string a = args[i];
                if (a == "--base" && i + 1 < args.Length) basePath = args[++i];
                else if (a == "--later-wins") opt.LaterWins = true;
                else if (a == "--no-scripts") opt.RewriteScripts = false;
                else if (a == "--take-unbanked-rows") opt.TakeUnbankedRows = true;
                else if (a == "--copy-all") opt.CopyOtherFiles = true;
                else if (a == "--dry-run") dry = true;
                else if (a.StartsWith("--")) { Console.Error.WriteLine("Unknown option " + a + "\n\n" + MergeUsage); return 2; }
                else names.Add(a);
            }
            if (names.Count < (dry ? 2 : 3)) { Console.Error.WriteLine(MergeUsage); return 2; }
            string outDir = dry ? null : names[0];
            var mods = dry ? names : names.Skip(1).ToList();
            try { SALT.Moveset.AnimCMD.ACMD_INFO.OverrideInfo(System.IO.Path.Combine(Application.StartupPath, "Events.cfg"), new List<string>()); } catch { }
            if (basePath == null)
            {
                try
                {
                    var ini = System.IO.Path.Combine(Application.StartupPath, "Sm4shCommand.ini");
                    if (System.IO.File.Exists(ini))
                        foreach (var line in System.IO.File.ReadAllLines(ini))
                        {
                            int eq = line.IndexOf('=');
                            if (eq > 0 && line.Substring(0, eq).Trim() == "SoundDataFolder") basePath = line.Substring(eq + 1).Trim();
                        }
                }
                catch { }
            }
            string table = basePath;
            if (basePath != null && !System.IO.File.Exists(basePath))
            {
                bool p;
                table = Sm4shCommand.Sound.FighterSounds.FindData(null, System.IO.Path.Combine(System.IO.Path.Combine("sound", "config"), "soundlabeltable.bin"), basePath, out p);
            }
            if (table == null) { Console.Error.WriteLine("No base soundlabeltable.bin: give --base (a soundlabeltable.bin or the game's data folder).\n\n" + MergeUsage); return 2; }
            var merger = new Sm4shCommand.Sound.SoundMerger(table, mods, opt, Sm4shCommand.Sound.FighterSounds.LoadBankAliases(Sm4shCommand.Sound.FighterSounds.BankAliasesPath)) { Version = Version };
            var r = merger.Run(outDir);
            Console.WriteLine(r.Report);
            return r.Ok ? 0 : 1;
        }

        static void ReportError(Exception e, bool canContinue)
        {
            string log;
            try { log = System.IO.Path.Combine(Application.StartupPath, "Sm4shCommand_errors.log"); }
            catch { log = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "Sm4shCommand_errors.log"); }
            try
            {
                System.IO.File.AppendAllText(log, $"==== {DateTime.Now:yyyy-MM-dd HH:mm:ss} {Title}{Environment.NewLine}{e}{Environment.NewLine}{Environment.NewLine}");
            }
            catch { }
            string msg = $"{e?.GetType().Name}: {e?.Message}\n\nDetails were written to {log}.";
            if (canContinue)
                msg += "\n\nContinue? (No closes the program.)";
            var answer = MessageBox.Show(msg, "Sm4shCommand error", canContinue ? MessageBoxButtons.YesNo : MessageBoxButtons.OK, MessageBoxIcon.Error);
            if (canContinue && answer == DialogResult.No)
                Application.Exit();
        }

        private static void RegisterFileAssociations()
        {
            /***********************************/
            /**** Key1: Create ".abc" entry ****/
            /***********************************/
            Microsoft.Win32.RegistryKey key1 = Microsoft.Win32.Registry.CurrentUser.OpenSubKey("Software", true);

            key1.CreateSubKey("Classes");
            key1 = key1.OpenSubKey("Classes", true);

            key1.CreateSubKey(".wrkspc");
            key1 = key1.OpenSubKey(".wrkspc", true);
            key1.SetValue("", "Workspace"); // Set default key value

            key1.Close();

            /*******************************************************/
            /**** Key2: Create "DemoKeyValue\DefaultIcon" entry ****/
            /*******************************************************/
            Microsoft.Win32.RegistryKey key2 = Microsoft.Win32.Registry.CurrentUser.OpenSubKey("Software", true);

            key2.CreateSubKey("Classes");
            key2 = key2.OpenSubKey("Classes", true);

            key2.CreateSubKey("Workspace");
            key2 = key2.OpenSubKey("Workspace", true);

            key2.Close();

            /**************************************************************/
            /**** Key3: Create "DemoKeyValue\shell\open\command" entry ****/
            /**************************************************************/
            Microsoft.Win32.RegistryKey key3 = Microsoft.Win32.Registry.CurrentUser.OpenSubKey("Software", true);

            key3.CreateSubKey("Classes");
            key3 = key3.OpenSubKey("Classes", true);

            key3.CreateSubKey("Workspace");
            key3 = key3.OpenSubKey("Workspace", true);

            key3.CreateSubKey("shell");
            key3 = key3.OpenSubKey("shell", true);

            key3.CreateSubKey("open");
            key3 = key3.OpenSubKey("open", true);

            key3.CreateSubKey("command");
            key3 = key3.OpenSubKey("command", true);
            key3.SetValue("", "\"" + Application.ExecutablePath + "\"" + " \"%1\""); // Set default key value

            key3.Close();
            SHChangeNotify(0x8000000, 0x1000, IntPtr.Zero, IntPtr.Zero);
        }
        [System.Runtime.InteropServices.DllImport("Shell32.dll")]
        private static extern int SHChangeNotify(int eventId, int flags, IntPtr item1, IntPtr item2);
    }
}
