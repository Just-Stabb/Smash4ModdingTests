using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace Sm4shCommand.Sound
{
    /// <summary>
    /// sound/config/soundlabeltable.bin (v1.7.32): how ACMD / MSC sound ids reach a bank's tones. 'STB\0', u32 version,
    /// u32 row count, u32 rows' size (16 x count), then rows of {u32 bank id (BINF), u32 label count, u32 offset, u32 0}
    /// (bank id 0xFFFFFFFF = an empty row), then the labels: per row, from its offset, one s32 tone index per label (-1 =
    /// none). A sound id is (row &lt;&lt; 16) | label: Greninja's snd_se_Gekkouga (BINF 2058) is row 0x768, so his IceBoom
    /// (label 97, tone 110) is 0x07680061; row 0 is the common bank snd_se_joucyu (2000), which every fighter plays
    /// (0x00000046, futtobi_l: the strong-launch sound). The game finds the row from the id, then the bank among the ones the
    /// fighter loaded by the row's bank id (cross_f.rpx 0x0311EC30 / 0x0311EDC4, docs/params/fighter_files.md "Sound").
    /// Build() writes it back (byte-identical when unchanged); SetLabels / UseRow are part 2's.
    /// </summary>
    public class SoundLabelTable
    {
        public class Row
        {
            public uint BankId = 0xFFFFFFFF, Count, Offset, Zero;
            public bool Empty { get { return BankId == 0xFFFFFFFF; } }
        }

        public const uint EmptyBank = 0xFFFFFFFF;
        public string Path;
        public byte[] Head = new byte[8];           // 'STB\0' + version
        public readonly List<Row> Rows = new List<Row>();
        public byte[] Pool = new byte[0];          // the labels' words
        readonly Dictionary<uint, int> rowOfBank = new Dictionary<uint, int>();

        public static SoundLabelTable Load(string path)
        {
            var t = Parse(File.ReadAllBytes(path));
            t.Path = path;
            return t;
        }

        public static SoundLabelTable Parse(byte[] d)
        {
            if (d.Length < 16 || Encoding.ASCII.GetString(d, 0, 4) != "STB\0")
                throw new InvalidDataException("not a soundlabeltable.bin (no STB)");
            uint n = Nus3Bank.U32(d, 8), size = Nus3Bank.U32(d, 12);
            if (size != 16 * n || 16 + (long)size > d.Length)
                throw new InvalidDataException("soundlabeltable.bin: bad row table");
            var t = new SoundLabelTable();
            Array.Copy(d, t.Head, 8);
            for (int i = 0; i < n; i++)
            {
                int at = 16 + 16 * i;
                t.Rows.Add(new Row { BankId = Nus3Bank.U32(d, at), Count = Nus3Bank.U32(d, at + 4), Offset = Nus3Bank.U32(d, at + 8), Zero = Nus3Bank.U32(d, at + 12) });
            }
            t.Pool = new byte[d.Length - 16 - size];
            Array.Copy(d, 16 + size, t.Pool, 0, t.Pool.Length);
            t.Index();
            return t;
        }

        void Index()
        {
            rowOfBank.Clear();
            for (int i = 0; i < Rows.Count; i++)
                if (!Rows[i].Empty && !rowOfBank.ContainsKey(Rows[i].BankId))
                    rowOfBank[Rows[i].BankId] = i;
        }

        /// <summary>The row of a bank id (the first one, as the game's lookup), -1 when none.</summary>
        public int RowOf(uint bankId)
        {
            int r;
            return rowOfBank.TryGetValue(bankId, out r) ? r : -1;
        }

        /// <summary>The row's labels: the tone index of each (-1 = none); empty when the row is empty or out of the table.</summary>
        public int[] Labels(int row)
        {
            if (row < 0 || row >= Rows.Count || Rows[row].Empty) return new int[0];
            var r = Rows[row];
            if (r.Offset + 4L * r.Count > Pool.Length) return new int[0];   // a broken row: nothing the game could play
            var l = new int[r.Count];
            for (int i = 0; i < l.Length; i++) l[i] = (int)Nus3Bank.U32(Pool, (int)r.Offset + 4 * i);
            return l;
        }

        public static uint SoundId(int row, int label) { return (uint)row << 16 | (uint)label & 0xFFFF; }
        public static int RowOfId(uint id) { return (int)(id >> 16); }
        public static int LabelOfId(uint id) { return (int)(id & 0xFFFF); }

        /// <summary>The tone index a sound id reaches (-1 none), with the row's bank id.</summary>
        public int ToneOf(uint id, out uint bankId)
        {
            int row = RowOfId(id), label = LabelOfId(id);
            bankId = row < Rows.Count ? Rows[row].BankId : EmptyBank;
            var l = Labels(row);
            return label < l.Length ? l[label] : -1;
        }

        public byte[] Build()
        {
            var b = new byte[16 + 16 * Rows.Count + Pool.Length];
            Array.Copy(Head, b, 8);
            Nus3Bank.Put32(b, 8, (uint)Rows.Count);
            Nus3Bank.Put32(b, 12, (uint)(16 * Rows.Count));
            for (int i = 0; i < Rows.Count; i++)
            {
                int at = 16 + 16 * i;
                Nus3Bank.Put32(b, at, Rows[i].BankId);
                Nus3Bank.Put32(b, at + 4, Rows[i].Count);
                Nus3Bank.Put32(b, at + 8, Rows[i].Offset);
                Nus3Bank.Put32(b, at + 12, Rows[i].Zero);
            }
            Array.Copy(Pool, 0, b, 16 + 16 * Rows.Count, Pool.Length);
            return b;
        }

        /// <summary>Part 2: gives a row in use a new label list (appended to the pool; the old words stay, unused), as
        /// tools/fighter_own_bank.py's Table.set_row. Labels already there keep their index, so ids stay put.</summary>
        public void SetLabels(int row, IList<int> tones)
        {
            if (row < 0 || row >= Rows.Count || Rows[row].Empty) throw new ArgumentException("row " + row + " isn't in use");
            Rows[row].Offset = AppendLabels(tones);
            Rows[row].Count = (uint)tones.Count;
        }

        /// <summary>Part 2: an empty row given a bank id and labels (tools/fighter_own_bank.py's add_row).</summary>
        public void UseRow(int row, uint bankId, IList<int> tones)
        {
            if (row < 0 || row >= Rows.Count || !Rows[row].Empty) throw new ArgumentException("row " + row + " is in use");
            Rows[row] = new Row { BankId = bankId, Count = (uint)tones.Count, Offset = AppendLabels(tones), Zero = 0 };
            Index();
        }

        /// <summary>v1.7.34 (Merge sound mods): any row given a bank id and labels (in use or empty; the labels appended to
        /// the pool, the old words stay), as SetLabels / UseRow; rows past the table's end are added empty first.</summary>
        public void SetRow(int row, uint bankId, IList<int> tones)
        {
            EnsureRows(row + 1);
            uint zero = Rows[row].Zero;
            Rows[row] = new Row { BankId = bankId, Count = (uint)tones.Count, Offset = AppendLabels(tones), Zero = zero };
            Index();
        }

        /// <summary>v1.7.34: grows the row table to n rows (new rows empty: bank id -1, no labels).</summary>
        public void EnsureRows(int n)
        {
            while (Rows.Count < n) Rows.Add(new Row { BankId = EmptyBank, Count = 0, Offset = 0, Zero = 0 });
        }

        uint AppendLabels(IList<int> tones)
        {
            int pad = (4 - Pool.Length % 4) % 4;
            var p = new byte[Pool.Length + pad + 4 * tones.Count];
            Array.Copy(Pool, p, Pool.Length);
            uint off = (uint)(Pool.Length + pad);
            for (int i = 0; i < tones.Count; i++) Nus3Bank.Put32(p, (int)off + 4 * i, (uint)tones[i]);
            Pool = p;
            return off;
        }

        /// <summary>Every sound id in use (rows in use, labels that reach a tone), for part 2's free-id check.</summary>
        public HashSet<uint> UsedIds()
        {
            var used = new HashSet<uint>();
            for (int r = 0; r < Rows.Count; r++)
            {
                var l = Labels(r);
                for (int i = 0; i < l.Length; i++) if (l[i] >= 0) used.Add(SoundId(r, i));
            }
            return used;
        }
    }
}
