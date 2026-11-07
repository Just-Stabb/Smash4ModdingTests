using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Serialization;
using Sm4shFileExplorer;
using Sm4shFileExplorer.Globals;
using Sm4shFileExplorer.Objects;

class MergeTest
{
    static int fails = 0;
    static void Check(bool c, string what) { Console.WriteLine((c ? "ok    " : "FAIL  ") + what); if (!c) fails++; }
    static void Make(string root, params string[] files)
    {
        foreach (string f in files) { string p = Path.Combine(root, f); Directory.CreateDirectory(Path.GetDirectoryName(p)); File.WriteAllText(p, "x"); }
    }
    static object SetField(object o, Type t, string name, object v)
    {
        FieldInfo f = t.GetField(name, BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static);
        f.SetValue(o, v); return v;
    }
    static int Main(string[] args)
    {
        string root = args[0];
        string ws = Path.Combine(root, "ws") + "/";
        string src = Path.Combine(root, "src");
        Directory.SetCurrentDirectory(root);
        Sm4shMod mod = new Sm4shMod();
        mod.ProjectWorkplaceFolder = ws;
        SetField(null, typeof(PathHelper), "_Project", mod);
        try { SetField(null, typeof(LogHelper), "_Project", mod); } catch (Exception) { }
        // the game's folders: data/ui, data/param/fighter, data/fighter/edge/model/body; data(us_en)/ui/message
        string patch = PathHelper.GetWorkplaceFolder(PathHelperEnum.FOLDER_PATCH);
        Make(patch, "data/ui/lumen/x.lm", "data/param/fighter/x.bin", "data/fighter/edge/model/body/c00/model.nud",
             "data/stage/melee/Battle/x.lvd", "data(us_en)/ui/message/melee.msbt");
        Sm4shProject p = (Sm4shProject)FormatterServices.GetUninitializedObject(typeof(Sm4shProject));
        var cols = new List<ResourceCollection>();
        foreach (string part in new[] { "data", "data(us_en)" })
        {
            var rc = (ResourceCollection)FormatterServices.GetUninitializedObject(typeof(ResourceCollection));
            foreach (var pi in typeof(ResourceCollection).GetProperties())
                if (pi.Name == "PartitionName" && pi.CanWrite) pi.SetValue(rc, part);
            foreach (var fi in typeof(ResourceCollection).GetFields(BindingFlags.NonPublic | BindingFlags.Instance))
            {
                if (fi.FieldType == typeof(string) && fi.Name == "_name") fi.SetValue(rc, part);
            }
            rc.Resources = new Dictionary<string, ResourceItem>();
            cols.Add(rc);
        }
        SetField(p, typeof(Sm4shProject), "_resCols", cols.ToArray());
        SetField(p, typeof(Sm4shProject), "_Plugins", Activator.CreateInstance(typeof(Sm4shProject).GetField("_Plugins", BindingFlags.NonPublic | BindingFlags.Instance).FieldType));
        MethodInfo mr = typeof(Sm4shProject).GetMethod("MergeReason", BindingFlags.NonPublic | BindingFlags.Instance);

        // dropped folders
        Make(src, "data/ui/lumen/new.lm", "data/param/ui/a.bin",
             "param/fighter/b.bin",
             "smashrun_ui/ui/info/c.flx", "smashrun_ui/param/item/d.bin",
             "edge2/model/body/c00/model.nud", "edge2/motion/body/main.pac",
             "c08/model.nud",
             "ui/lumen/e.lm",
             "mixed/ui/f.lm", "mixed/newthing/g.bin",
             "data(us_en)/ui/message/menu.msbt",
             "SR_Room00/model/m.nud", "SR_Room00/param/p.lvd");
        Func<string, string, string> reason = (f, t) => (string)mr.Invoke(p, new object[] { Path.Combine(src, f), t });
        Check(reason("data", "data/") != null, "data on data: merged (" + reason("data", "data/") + ")");
        Check(reason("data(us_en)", "data(us_en)/") != null, "data(us_en) on data(us_en): merged");
        Check(reason("param", "data/param/") != null, "param on param: merged");
        Check(reason("smashrun_ui", "data/") != null, "a package folder (ui/, param/) on data: merged (" + reason("smashrun_ui", "data/") + ")");
        Check(reason("edge2", "data/fighter/") == null, "a new fighter folder on fighter: a folder of its own");
        Check(reason("c08", "data/fighter/edge/model/body/") == null, "a new costume (files only): a folder of its own");
        Check(reason("ui", "data/") == null, "ui on data: into data/ui as before (already the same place)");
        Check(reason("mixed", "data/") == null, "a folder with one new subfolder: a folder of its own");
        Check(reason("SR_Room00", "data/stage/melee/") == null, "a new stage on stage/melee: a folder of its own");

        // end to end: AddFileToWorkspace copies
        p.AddFileToWorkspace(Path.Combine(src, "data"), "data/");
        Check(File.Exists(patch + "data/ui/lumen/new.lm") && File.Exists(patch + "data/param/ui/a.bin") && !Directory.Exists(patch + "data/data"),
              "add data on data: data/ui/lumen/new.lm, data/param/ui/a.bin, no data/data");
        p.AddFileToWorkspace(Path.Combine(src, "smashrun_ui"), "data/");
        Check(File.Exists(patch + "data/ui/info/c.flx") && File.Exists(patch + "data/param/item/d.bin") && !Directory.Exists(patch + "data/smashrun_ui"),
              "add smashrun_ui on data: data/ui/info/c.flx, data/param/item/d.bin");
        p.AddFileToWorkspace(Path.Combine(src, "param"), "data/param/");
        Check(File.Exists(patch + "data/param/fighter/b.bin") && !Directory.Exists(patch + "data/param/param"), "add param on param: data/param/fighter/b.bin");
        p.AddFileToWorkspace(Path.Combine(src, "edge2"), "data/fighter/");
        Check(File.Exists(patch + "data/fighter/edge2/model/body/c00/model.nud"), "add edge2 on fighter: data/fighter/edge2/...");
        p.AddFileToWorkspace(Path.Combine(src, "data(us_en)"), "data(us_en)/");
        Check(File.Exists(patch + "data(us_en)/ui/message/menu.msbt") && File.Exists(patch + "data(us_en)/ui/message/melee.msbt"),
              "add data(us_en) on data(us_en): data(us_en)/ui/message/menu.msbt");
        p.AddFileToWorkspace(Path.Combine(src, "ui"), "data/");
        Check(File.Exists(patch + "data/ui/lumen/e.lm"), "add ui on data: data/ui/lumen/e.lm (as before)");
        Console.WriteLine(fails + " failures");
        return fails == 0 ? 0 : 1;
    }
}
