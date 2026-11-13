// Sm4shCommand v1.4.9 GUI pieces under Mono + Xvfb: View > Commands' New_Var page and the editor hover on a name.
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Windows.Forms;
using SALT.Moveset;
using SALT.Moveset.AnimCMD;

class GuiTest
{
    static int Main(string[] args)
    {
        var errors = new List<string>();
        ACMD_INFO.OverrideInfo(args[0], errors);
        int fails = 0;
        FighterVariable.ClearNewVars();
        var s = new ACMDScript(1);
        s.Serialize("New_Var(Name=charge, Type=int, Initial=0, Scope=move)\nNew_Var(Name=power, Initial=1.5)\nINC_INT(Variable=charge)");
        var form = new Sm4shCommand.CommandListForm(() => null);
        var show = typeof(Sm4shCommand.CommandListForm).GetMethod("ShowCommand", BindingFlags.NonPublic | BindingFlags.Instance);
        show.Invoke(form, new object[] { (uint?)FighterVariable.NewVarIdent });
        var info = (RichTextBox)typeof(Sm4shCommand.CommandListForm).GetField("info", BindingFlags.NonPublic | BindingFlags.Instance).GetValue(form);
        string text = info.Text;
        Console.WriteLine(text);
        foreach (var want in new[] { "Parameters (5)", "5. Slot", "Declared in the open scripts", "charge  \u2014  slot 0 (0x0F000380), int, scope move, initial 0",
                                     "power  \u2014  slot 1 (0x0F000381), float, scope object, initial 1.5",
                                     "New_Var(Name=my_var, Type=float, Initial=0, Scope=object)", "Example 1" })
        {
            bool ok = text.Contains(want);
            if (!ok) fails++;
            Console.WriteLine((ok ? "ok   " : "FAIL ") + "command page has: " + want);
        }
        bool noText = !text.Contains("Text1");
        if (!noText) fails++;
        Console.WriteLine((noText ? "ok   " : "FAIL ") + "the name's words (Text1-6) aren't listed");
        // hover on a name in a script line (Tooltips.Describe)
        string d = Sm4shCommand.Classes.Tooltips.Describe("charge", "INC_INT", "Variable", "3", 1);
        bool hov = d.Contains("New_Var charge (int, scope move, initial 0): slot 0, variable 0x0F000380");
        if (!hov) fails++;
        Console.WriteLine((hov ? "ok   " : "FAIL ") + "hover on charge: " + d.Replace("\n", " / "));
        Console.WriteLine(fails + " failures");
        return fails;
    }
}
