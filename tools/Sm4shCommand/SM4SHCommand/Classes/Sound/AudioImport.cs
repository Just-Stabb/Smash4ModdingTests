using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

namespace Sm4shCommand.Sound
{
    /// <summary>Audio read from a file: float samples (-1 .. 1), channels interleaved.</summary>
    public class PcmAudio
    {
        public float[] Samples;
        public int Channels, Rate;
        public string How = "";         // how it was read ("WAV, 16-bit", "Media Foundation", "ffmpeg ...")
        public int Frames { get { return Channels > 0 ? Samples.Length / Channels : 0; } }
        public double Seconds { get { return Rate > 0 ? Frames / (double)Rate : 0; } }
    }

    /// <summary>
    /// The Sound Adder's audio input (v1.7.33): reading a file, resampling it to the bank's rate, trimming silence,
    /// normalising and making the 16-bit PCM the encoder takes.
    /// Reading: WAV natively (PCM 8 / 16 / 24 / 32-bit, float 32 / 64-bit, WAVE_FORMAT_EXTENSIBLE; any rate, mono or
    /// stereo; more channels are mixed down to stereo). Anything else (MP3, OGG, FLAC, M4A ...): on Windows through Media
    /// Foundation (the system's decoders: MP3 / AAC / WMA from Windows 7, FLAC from Windows 10, OGG only with Microsoft's
    /// Web Media Extensions), else, or if that fails, through ffmpeg when it is on PATH (or next to Sm4shCommand.exe),
    /// which decodes to a temporary WAV. Without either, only WAV: convert first.
    /// </summary>
    public static class AudioImport
    {
        public const int BankRate = 48000;          // every vanilla se / vc tone that isn't a 47-48 kHz oddity

        public static readonly string[] Extensions = { ".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac", ".wma", ".opus", ".aif", ".aiff" };

        public static string FileFilter
        {
            get { return "Audio files (*.wav;*.mp3;*.ogg;*.flac;*.m4a;*.aac;*.wma;*.opus;*.aif;*.aiff)|*.wav;*.mp3;*.ogg;*.flac;*.m4a;*.aac;*.wma;*.opus;*.aif;*.aiff|WAV (*.wav)|*.wav|All files (*.*)|*.*"; }
        }

        /// <summary>Tests (and users who don't want Media Foundation): false skips it.</summary>
        public static bool UseMediaFoundation = true;
        /// <summary>Set to a path to use that ffmpeg; null looks on PATH and next to the exe.</summary>
        public static string FfmpegPath;

        static bool IsWindows { get { return Environment.OSVersion.Platform == PlatformID.Win32NT; } }

        /// <summary>ffmpeg (ffmpeg.exe) next to the exe or on PATH, null when there is none.</summary>
        public static string FindFfmpeg()
        {
            if (!string.IsNullOrEmpty(FfmpegPath)) return File.Exists(FfmpegPath) ? FfmpegPath : null;
            var names = IsWindows ? new[] { "ffmpeg.exe" } : new[] { "ffmpeg" };
            var dirs = new List<string>();
            try { dirs.Add(System.Windows.Forms.Application.StartupPath); } catch (Exception) { }
            foreach (var d in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(Path.PathSeparator))
                if (d.Trim().Length > 0) dirs.Add(d.Trim().Trim('"'));
            foreach (var d in dirs)
                foreach (var n in names)
                    try
                    {
                        var p = Path.Combine(d, n);
                        if (File.Exists(p)) return p;
                    }
                    catch (Exception) { }
            return null;
        }

        /// <summary>What can be read here, for the dialog / README.</summary>
        public static string Capabilities()
        {
            var ff = FindFfmpeg();
            var s = "WAV: read natively.";
            if (IsWindows && UseMediaFoundation) s += " MP3 / M4A / WMA (FLAC on Windows 10+, OGG with Web Media Extensions): Windows Media Foundation.";
            s += ff != null ? " ffmpeg: " + ff + " (any format)." : " No ffmpeg on PATH" + (IsWindows ? " (other formats: Media Foundation only, or convert them to WAV first)." : ": convert other formats to WAV first.");
            return s;
        }

        /// <summary>Reads an audio file (see the class's notes on formats).</summary>
        public static PcmAudio Read(string path)
        {
            var errors = new List<string>();
            bool wav = Path.GetExtension(path).Equals(".wav", StringComparison.OrdinalIgnoreCase);
            if (wav)
            {
                try { return ReadWav(File.ReadAllBytes(path)); }
                catch (Exception ex) { errors.Add("WAV: " + ex.Message); }
            }
            else
            {
                // a WAV under another name still reads natively
                try
                {
                    var head = new byte[12];
                    using (var f = File.OpenRead(path)) f.Read(head, 0, 12);
                    if (Encoding.ASCII.GetString(head, 0, 4) == "RIFF" && Encoding.ASCII.GetString(head, 8, 4) == "WAVE")
                        return ReadWav(File.ReadAllBytes(path));
                }
                catch (Exception) { }
            }
            if (IsWindows && UseMediaFoundation)
            {
                try { return MediaFoundation.Decode(path); }
                catch (Exception ex) { errors.Add("Media Foundation: " + ex.Message); }
            }
            var ff = FindFfmpeg();
            if (ff != null)
            {
                try { return ReadWithFfmpeg(ff, path); }
                catch (Exception ex) { errors.Add("ffmpeg: " + ex.Message); }
            }
            else
                errors.Add("no ffmpeg on PATH");
            throw new InvalidDataException(Path.GetFileName(path) + " couldn't be read (" + string.Join("; ", errors.ToArray()) + "). " +
                "Convert it to a WAV first (Audacity: File > Export > WAV, 16-bit PCM), or put ffmpeg on PATH.");
        }

        /// <summary>ffmpeg decodes the file to a temporary 16-bit WAV (mono or stereo: more channels mixed down), read here.</summary>
        public static PcmAudio ReadWithFfmpeg(string ffmpeg, string path)
        {
            string tmp = Path.Combine(Path.GetTempPath(), "sm4shcommand_" + Process.GetCurrentProcess().Id + "_" + Guid.NewGuid().ToString("N").Substring(0, 8) + ".wav");
            try
            {
                var psi = new ProcessStartInfo(ffmpeg, "-v error -y -i \"" + path + "\" -vn -acodec pcm_s16le -af \"aformat=channel_layouts=mono|stereo\" \"" + tmp + "\"")
                {
                    UseShellExecute = false, CreateNoWindow = true, RedirectStandardError = true, RedirectStandardOutput = true,
                };
                using (var p = Process.Start(psi))
                {
                    string err = p.StandardError.ReadToEnd();
                    p.StandardOutput.ReadToEnd();
                    if (!p.WaitForExit(120000)) { try { p.Kill(); } catch (Exception) { } throw new TimeoutException("ffmpeg took over 2 minutes"); }
                    if (p.ExitCode != 0 || !File.Exists(tmp)) throw new InvalidDataException("ffmpeg failed: " + err.Trim());
                }
                var a = ReadWav(File.ReadAllBytes(tmp));
                a.How = "ffmpeg (" + Path.GetExtension(path).TrimStart('.').ToUpperInvariant() + " -> 16-bit PCM, " + a.Rate + " Hz)";
                return a;
            }
            finally { try { if (File.Exists(tmp)) File.Delete(tmp); } catch (Exception) { } }
        }

        static int U16(byte[] b, int at) { return b[at] | b[at + 1] << 8; }
        static int S32(byte[] b, int at) { return b[at] | b[at + 1] << 8 | b[at + 2] << 16 | b[at + 3] << 24; }

        /// <summary>A RIFF WAVE file: PCM 8 / 16 / 24 / 32-bit or IEEE float 32 / 64-bit (also as WAVE_FORMAT_EXTENSIBLE).
        /// A data chunk of size 0 / -1 (a stream's) runs to the end of the file.</summary>
        public static PcmAudio ReadWav(byte[] b)
        {
            if (b.Length < 12 || Encoding.ASCII.GetString(b, 0, 4) != "RIFF" || Encoding.ASCII.GetString(b, 8, 4) != "WAVE")
                throw new InvalidDataException("not a WAV file (no RIFF / WAVE)");
            int q = 12, fmt = -1, channels = 0, rate = 0, bits = 0, align = 0;
            int dataAt = -1;
            long dataSize = 0;
            while (q + 8 <= b.Length)
            {
                string id = Encoding.ASCII.GetString(b, q, 4);
                long size = (uint)S32(b, q + 4);
                int body = q + 8;
                if (id == "fmt " && body + 16 <= b.Length)
                {
                    fmt = U16(b, body);
                    channels = U16(b, body + 2);
                    rate = S32(b, body + 4);
                    align = U16(b, body + 12);
                    bits = U16(b, body + 14);
                    if (fmt == 0xFFFE && size >= 40 && body + 40 <= b.Length)
                        fmt = U16(b, body + 24);         // the sub-format GUID's first word (1 PCM, 3 float)
                }
                else if (id == "data")
                {
                    dataAt = body;
                    dataSize = size == 0 || size == 0xFFFFFFFF || body + size > b.Length ? b.Length - body : size;
                    break;
                }
                q = body + (int)Math.Min(size + (size & 1), int.MaxValue - body);
                if (size > b.Length) break;
            }
            if (fmt < 0) throw new InvalidDataException("WAV: no fmt chunk");
            if (dataAt < 0) throw new InvalidDataException("WAV: no data chunk");
            if (channels < 1 || channels > 32 || rate < 1000 || rate > 384000) throw new InvalidDataException("WAV: " + channels + " channels at " + rate + " Hz?");
            bool isFloat = fmt == 3;
            if (fmt != 1 && fmt != 3)
                throw new InvalidDataException("WAV: format " + fmt + " (compressed: ADPCM / MP3 in a WAV ...) isn't read natively");
            if (isFloat ? bits != 32 && bits != 64 : bits != 8 && bits != 16 && bits != 24 && bits != 32)
                throw new InvalidDataException("WAV: " + bits + "-bit " + (isFloat ? "float" : "PCM") + " isn't read");
            int bps = bits / 8;
            if (align < bps * channels) align = bps * channels;
            long frames = dataSize / align;
            var s = new float[frames * channels];
            for (long f = 0; f < frames; f++)
                for (int c = 0; c < channels; c++)
                {
                    int at = (int)(dataAt + f * align + c * bps);
                    float v;
                    if (isFloat)
                        v = bits == 32 ? BitConverter.ToSingle(b, at) : (float)BitConverter.ToDouble(b, at);
                    else if (bits == 8) v = (b[at] - 128) / 128f;
                    else if (bits == 16) v = (short)(b[at] | b[at + 1] << 8) / 32768f;
                    else if (bits == 24) v = ((b[at] << 8 | b[at + 1] << 16 | b[at + 2] << 24) >> 8) / 8388608f;
                    else v = S32(b, at) / 2147483648f;
                    s[f * channels + c] = v;
                }
            var a = new PcmAudio { Samples = s, Channels = channels, Rate = rate, How = "WAV (" + bits + "-bit " + (isFloat ? "float" : "PCM") + ", " + rate + " Hz)" };
            return channels > 2 ? Downmix(a) : a;
        }

        /// <summary>More than two channels mixed to stereo (odd channels left, even right; a 5.1 file's front pair and the
        /// rest averaged in).</summary>
        public static PcmAudio Downmix(PcmAudio a)
        {
            int ch = a.Channels, n = a.Frames;
            var o = new float[n * 2];
            int left = (ch + 1) / 2, right = ch / 2;
            for (int f = 0; f < n; f++)
            {
                double l = 0, r = 0;
                for (int c = 0; c < ch; c++)
                    if ((c & 1) == 0) l += a.Samples[f * ch + c]; else r += a.Samples[f * ch + c];
                o[f * 2] = (float)(l / left);
                o[f * 2 + 1] = (float)(right > 0 ? r / right : l / left);
            }
            return new PcmAudio { Samples = o, Channels = 2, Rate = a.Rate, How = a.How + ", " + ch + " channels mixed to stereo" };
        }

        // ---------------------------------------------------------------- resampling

        const int Taps = 32;                // half-width of the sinc kernel in input samples (at the cutoff's scale)
        const int Steps = 512;              // kernel table points per input sample

        static double Bessel0(double x)
        {
            double sum = 1, term = 1, q = x * x / 4;
            for (int k = 1; k < 50; k++)
            {
                term *= q / (k * (double)k);
                sum += term;
                if (term < 1e-12 * sum) break;
            }
            return sum;
        }

        /// <summary>Band-limited resampling (a Kaiser-windowed sinc, beta 9, 32 zero crossings a side, the cutoff at the
        /// lower rate's Nyquist x 0.97), each channel on its own; the length becomes frames x to / from.</summary>
        public static PcmAudio Resample(PcmAudio a, int to)
        {
            if (a.Rate == to) return a;
            int ch = a.Channels, n = a.Frames;
            double ratio = to / (double)a.Rate;                 // output samples per input sample
            double fc = Math.Min(1.0, ratio) * 0.97;            // cutoff, as a fraction of the input's Nyquist
            int half = (int)Math.Ceiling(Taps / fc);            // input samples each side
            const double beta = 9.0;
            double i0b = Bessel0(beta);
            // the kernel k(t) = fc sinc(fc t) w(t / half), t in input samples, tabulated over [0, half]
            var table = new double[half * Steps + 2];
            for (int i = 0; i < table.Length; i++)
            {
                double t = i / (double)Steps;
                double x = t / half;
                double w = x >= 1 ? 0 : Bessel0(beta * Math.Sqrt(1 - x * x)) / i0b;
                double arg = Math.PI * fc * t;
                table[i] = w * fc * (t == 0 ? 1 : Math.Sin(arg) / arg);
            }
            long outN = (long)Math.Round(n * ratio);
            var o = new float[outN * ch];
            for (long j = 0; j < outN; j++)
            {
                double t = j / ratio;                       // the output sample's place in input samples
                long i0 = (long)Math.Floor(t);
                long lo = Math.Max(0, i0 - half + 1), hi = Math.Min(n - 1, i0 + half);
                for (int c = 0; c < ch; c++)
                {
                    double acc = 0;
                    for (long i = lo; i <= hi; i++)
                    {
                        double d = Math.Abs(t - i) * Steps;
                        int k = (int)d;
                        if (k >= table.Length - 1) continue;
                        double frac = d - k;
                        acc += a.Samples[i * ch + c] * (table[k] + (table[k + 1] - table[k]) * frac);
                    }
                    o[j * ch + c] = (float)acc;
                }
            }
            return new PcmAudio { Samples = o, Channels = ch, Rate = to, How = a.How + ", resampled " + a.Rate + " -> " + to + " Hz" };
        }

        // ---------------------------------------------------------------- trimming, level, 16-bit

        /// <summary>Leading / trailing silence cut: the frames before the first and after the last whose peak (any channel)
        /// reaches thresholdDb (dBFS; tools/gekkouga_sound.py's -45 dB, ffmpeg silenceremove's peak detection).</summary>
        public static PcmAudio TrimSilence(PcmAudio a, double thresholdDb, bool start = true, bool end = true)
        {
            double th = Math.Pow(10, thresholdDb / 20);
            int ch = a.Channels, n = a.Frames;
            int first = 0, last = n - 1;
            Func<int, bool> loud = f => { for (int c = 0; c < ch; c++) if (Math.Abs(a.Samples[f * ch + c]) >= th) return true; return false; };
            if (start) while (first < n && !loud(first)) first++;
            if (end) while (last >= first && !loud(last)) last--;
            if (first > last) return new PcmAudio { Samples = new float[0], Channels = ch, Rate = a.Rate, How = a.How };
            if (first == 0 && last == n - 1) return a;
            var o = new float[(last - first + 1) * ch];
            Array.Copy(a.Samples, first * ch, o, 0, o.Length);
            return new PcmAudio { Samples = o, Channels = ch, Rate = a.Rate, How = a.How };
        }

        public static double PeakDb(PcmAudio a)
        {
            double p = 0;
            foreach (var v in a.Samples) p = Math.Max(p, Math.Abs(v));
            return p > 0 ? 20 * Math.Log10(p) : double.NegativeInfinity;
        }

        /// <summary>16-bit PCM, the peak at peakDb (dBFS) when normalise (tools/fighter_own_bank.py's -0.5 dB), else as
        /// it is (clipped).</summary>
        public static short[] ToPcm16(PcmAudio a, bool normalise, double peakDb = -0.5)
        {
            double g = 1;
            if (normalise)
            {
                double p = 0;
                foreach (var v in a.Samples) p = Math.Max(p, Math.Abs(v));
                if (p > 1e-9) g = Math.Pow(10, peakDb / 20) / p;
            }
            var o = new short[a.Samples.Length];
            for (int i = 0; i < o.Length; i++)
            {
                double v = Math.Round(a.Samples[i] * g * 32767);
                o[i] = (short)(v > 32767 ? 32767 : v < -32768 ? -32768 : v);
            }
            return o;
        }

        /// <summary>16-bit PCM as floats.</summary>
        public static PcmAudio FromPcm16(short[] pcm, int channels, int rate)
        {
            var s = new float[pcm.Length];
            for (int i = 0; i < s.Length; i++) s[i] = pcm[i] / 32768f;
            return new PcmAudio { Samples = s, Channels = channels, Rate = rate, How = "PCM" };
        }

        /// <summary>A 16-bit WAV from floats (tests, and saving what will go in).</summary>
        public static byte[] Wav(PcmAudio a)
        {
            var pcm = new short[a.Samples.Length];
            for (int i = 0; i < pcm.Length; i++)
            {
                double v = Math.Round(a.Samples[i] * 32767);
                pcm[i] = (short)(v > 32767 ? 32767 : v < -32768 ? -32768 : v);
            }
            return Idsp.Wav(pcm, a.Channels, a.Rate);
        }
    }

    /// <summary>
    /// Windows Media Foundation's source reader as a decoder (v1.7.33): MFCreateSourceReaderFromURL, the first audio
    /// stream set to 16-bit PCM, ReadSample to the end. Windows only (Vista and later; the codecs are the system's).
    /// Not run here (no Windows in the build / test environment): the Sound Adder falls back to ffmpeg or asks for a WAV
    /// when it throws.
    /// </summary>
    static class MediaFoundation
    {
        const int MF_VERSION = 0x00020070;          // MF_SDK_VERSION 2 << 16 | MF_API_VERSION 0x70 (Windows 7)
        const int FirstAudioStream = unchecked((int)0xFFFFFFFD);
        const int AllStreams = unchecked((int)0xFFFFFFFE);
        const int EndOfStream = 0x2;
        static readonly Guid MT_MAJOR_TYPE = new Guid("48eba18e-f8c9-4687-bf11-0a74c9f96a8f");
        static readonly Guid MT_SUBTYPE = new Guid("f7e34c9a-42e8-4714-b74b-cb29d72c35e5");
        static readonly Guid MT_AUDIO_NUM_CHANNELS = new Guid("37e48bf5-645e-4c5b-89de-ada9e29b696a");
        static readonly Guid MT_AUDIO_SAMPLES_PER_SECOND = new Guid("5faeeae7-0290-4c31-9e8a-c534f68d9dba");
        static readonly Guid MT_AUDIO_BITS_PER_SAMPLE = new Guid("f2deb57f-40fa-4764-aa33-ed4f2d1ff669");
        static readonly Guid MediaType_Audio = new Guid("73647561-0000-0010-8000-00AA00389B71");
        static readonly Guid AudioFormat_PCM = new Guid("00000001-0000-0010-8000-00AA00389B71");

        [DllImport("mfplat.dll", ExactSpelling = true)] static extern int MFStartup(int version, int flags);
        [DllImport("mfplat.dll", ExactSpelling = true)] static extern int MFShutdown();
        [DllImport("mfplat.dll", ExactSpelling = true)] static extern int MFCreateMediaType(out IMFMediaType type);
        [DllImport("mfreadwrite.dll", ExactSpelling = true)]
        static extern int MFCreateSourceReaderFromURL([MarshalAs(UnmanagedType.LPWStr)] string url, IntPtr attributes, out IMFSourceReader reader);

        // IMFAttributes' 30 methods then IMFMediaType's 5; only the ones called have real signatures (the others hold
        // their vtable slots).
        [ComImport, Guid("44ae0fa8-ea31-4109-8d2e-4cae4997c555"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        interface IMFMediaType
        {
            void GetItem(); void GetItemType(); void CompareItem(); void Compare();
            [PreserveSig] int GetUINT32([In] ref Guid key, out int value);
            void GetUINT64(); void GetDouble(); void GetGUID(); void GetStringLength(); void GetString(); void GetAllocatedString();
            void GetBlobSize(); void GetBlob(); void GetAllocatedBlob(); void GetUnknown(); void SetItem(); void DeleteItem(); void DeleteAllItems();
            [PreserveSig] int SetUINT32([In] ref Guid key, int value);
            void SetUINT64(); void SetDouble();
            [PreserveSig] int SetGUID([In] ref Guid key, [In] ref Guid value);
            void SetString(); void SetBlob(); void SetUnknown(); void LockStore(); void UnlockStore(); void GetCount(); void GetItemByIndex(); void CopyAllItems();
            void GetMajorType(); void IsCompressedFormat(); void IsEqual(); void GetRepresentation(); void FreeRepresentation();
        }

        [ComImport, Guid("70ae66f2-c809-4e4f-8915-bdcb406b7993"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        interface IMFSourceReader
        {
            void GetStreamSelection();
            [PreserveSig] int SetStreamSelection(int stream, [MarshalAs(UnmanagedType.Bool)] bool selected);
            void GetNativeMediaType();
            [PreserveSig] int GetCurrentMediaType(int stream, out IMFMediaType type);
            [PreserveSig] int SetCurrentMediaType(int stream, IntPtr reserved, IMFMediaType type);
            void SetCurrentPosition();
            [PreserveSig] int ReadSample(int stream, int flags, out int actualStream, out int streamFlags, out long timestamp, out IMFSample sample);
            void Flush(); void GetServiceForStream(); void GetPresentationAttribute();
        }

        // IMFAttributes' 30 methods, then IMFSample's 14
        [ComImport, Guid("c40a00f2-b93a-4d80-ae8c-5a1c634f58e4"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        interface IMFSample
        {
            void A01(); void A02(); void A03(); void A04(); void A05(); void A06(); void A07(); void A08(); void A09(); void A10();
            void A11(); void A12(); void A13(); void A14(); void A15(); void A16(); void A17(); void A18(); void A19(); void A20();
            void A21(); void A22(); void A23(); void A24(); void A25(); void A26(); void A27(); void A28(); void A29(); void A30();
            void GetSampleFlags(); void SetSampleFlags(); void GetSampleTime(); void SetSampleTime(); void GetSampleDuration(); void SetSampleDuration();
            void GetBufferCount(); void GetBufferByIndex();
            [PreserveSig] int ConvertToContiguousBuffer(out IMFMediaBuffer buffer);
            void AddBuffer(); void RemoveBufferByIndex(); void RemoveAllBuffers(); void GetTotalLength(); void CopyToBuffer();
        }

        [ComImport, Guid("045FA593-8799-42b8-BC8D-8968C6453507"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        interface IMFMediaBuffer
        {
            [PreserveSig] int Lock(out IntPtr buffer, out int maxLength, out int currentLength);
            [PreserveSig] int Unlock();
            void GetCurrentLength(); void SetCurrentLength(); void GetMaxLength();
        }

        static void Ok(int hr, string what)
        {
            if (hr < 0) throw new COMException(what + " failed (0x" + hr.ToString("X8", CultureInfo.InvariantCulture) + ")", hr);
        }

        public static PcmAudio Decode(string path)
        {
            Ok(MFStartup(MF_VERSION, 0), "MFStartup");
            IMFSourceReader reader = null;
            try
            {
                Ok(MFCreateSourceReaderFromURL(Path.GetFullPath(path), IntPtr.Zero, out reader), "opening the file");
                Ok(reader.SetStreamSelection(AllStreams, false), "SetStreamSelection");
                Ok(reader.SetStreamSelection(FirstAudioStream, true), "SetStreamSelection (audio)");
                IMFMediaType want;
                Ok(MFCreateMediaType(out want), "MFCreateMediaType");
                Guid k1 = MT_MAJOR_TYPE, v1 = MediaType_Audio, k2 = MT_SUBTYPE, v2 = AudioFormat_PCM, k3 = MT_AUDIO_BITS_PER_SAMPLE;
                Ok(want.SetGUID(ref k1, ref v1), "SetGUID");
                Ok(want.SetGUID(ref k2, ref v2), "SetGUID");
                Ok(want.SetUINT32(ref k3, 16), "SetUINT32");
                Ok(reader.SetCurrentMediaType(FirstAudioStream, IntPtr.Zero, want), "asking for 16-bit PCM");
                Marshal.ReleaseComObject(want);
                IMFMediaType got;
                Ok(reader.GetCurrentMediaType(FirstAudioStream, out got), "GetCurrentMediaType");
                int channels, rate, bits;
                Guid kc = MT_AUDIO_NUM_CHANNELS, kr = MT_AUDIO_SAMPLES_PER_SECOND, kb = MT_AUDIO_BITS_PER_SAMPLE;
                Ok(got.GetUINT32(ref kc, out channels), "channels");
                Ok(got.GetUINT32(ref kr, out rate), "rate");
                Ok(got.GetUINT32(ref kb, out bits), "bits");
                Marshal.ReleaseComObject(got);
                if (bits != 16 || channels < 1) throw new InvalidDataException("Media Foundation gave " + bits + "-bit audio, " + channels + " channels");
                var data = new MemoryStream();
                while (true)
                {
                    int actual, flags;
                    long ts;
                    IMFSample sample;
                    Ok(reader.ReadSample(FirstAudioStream, 0, out actual, out flags, out ts, out sample), "ReadSample");
                    if (sample != null)
                    {
                        IMFMediaBuffer buf;
                        Ok(sample.ConvertToContiguousBuffer(out buf), "ConvertToContiguousBuffer");
                        IntPtr p;
                        int max, len;
                        Ok(buf.Lock(out p, out max, out len), "Lock");
                        var chunk = new byte[len];
                        Marshal.Copy(p, chunk, 0, len);
                        buf.Unlock();
                        data.Write(chunk, 0, len);
                        Marshal.ReleaseComObject(buf);
                        Marshal.ReleaseComObject(sample);
                    }
                    if ((flags & EndOfStream) != 0) break;
                    if (data.Length > 1L << 30) throw new InvalidDataException("over 1 GB of audio");
                }
                var raw = data.ToArray();
                var s = new float[raw.Length / 2 / channels * channels];
                for (int i = 0; i < s.Length; i++) s[i] = (short)(raw[2 * i] | raw[2 * i + 1] << 8) / 32768f;
                var a = new PcmAudio { Samples = s, Channels = channels, Rate = rate, How = "Media Foundation (" + Path.GetExtension(path).TrimStart('.').ToUpperInvariant() + " -> 16-bit PCM, " + rate + " Hz)" };
                return channels > 2 ? AudioImport.Downmix(a) : a;
            }
            finally
            {
                if (reader != null) Marshal.ReleaseComObject(reader);
                MFShutdown();
            }
        }
    }
}
