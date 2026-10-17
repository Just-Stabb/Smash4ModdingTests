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
        public static readonly string Version = "v1.3.0";
        public static readonly string Title;
        public static readonly string Description;
        public static readonly string Copyright;
        public static readonly string InformationalVersion;

        static Program()
        {
            Application.EnableVisualStyles();
            
            Title = ((AssemblyTitleAttribute)Assembly.GetExecutingAssembly().GetCustomAttributes(typeof(AssemblyTitleAttribute), false)[0]).Title;
            Description = ((AssemblyDescriptionAttribute)Assembly.GetExecutingAssembly().GetCustomAttributes(typeof(AssemblyDescriptionAttribute), false)[0]).Description;
            Copyright = ((AssemblyCopyrightAttribute)Assembly.GetExecutingAssembly().GetCustomAttributes(typeof(AssemblyCopyrightAttribute), false)[0]).Copyright;
            InformationalVersion = ((AssemblyInformationalVersionAttribute)Assembly.GetExecutingAssembly().GetCustomAttributes(typeof(AssemblyInformationalVersionAttribute), false)[0]).InformationalVersion;
            Title = $"{Title} {Version}";
        }

        /// <summary>
        /// The main entry point for the application.
        /// </summary>
        [STAThread]
        static void Main(string[] args)
        {
            Thread.CurrentThread.CurrentCulture = new CultureInfo("en-US");
            // Any crash is written (with its stack trace) to Sm4shCommand_errors.log next to the exe.
            Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);
            Application.ThreadException += (o, e) => ReportError(e.Exception, true);
            AppDomain.CurrentDomain.UnhandledException += (o, e) => ReportError(e.ExceptionObject as Exception, false);
            if (args.Length > 0) // a file or fighter folder given on the command line / dropped on the exe
                Runtime.Instance.Shown += (o, e) => Runtime.Instance.OpenPath(args[0]);
            Application.Run(Runtime.Instance);
        }

        static void ReportError(Exception e, bool canContinue)
        {
            string log = System.IO.Path.Combine(Application.StartupPath, "Sm4shCommand_errors.log");
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
