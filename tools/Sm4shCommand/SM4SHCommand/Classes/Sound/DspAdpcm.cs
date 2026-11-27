using System;
using System.IO;
using System.Text;

namespace Sm4shCommand.Sound
{
    /// <summary>
    /// The GameCube / Wii DSP-ADPCM encoder (v1.7.33, the Sound Adder): a C# port of tools/dspadpcm/grok.c
    /// (jackoalan/gc-dspadpcm-encode, MIT, itself from BrawlLib's AudioConverter.cs), the encoder tools/fighter_own_bank.py
    /// and tools/gekkouga_sound.py use (through tools/dspadpcm/dspenc.c) for the tones in the game today. Same arithmetic
    /// (doubles for the coefficient search, ints for the frames, lround for the coefficients), so the frames come out
    /// byte for byte as dspenc's (sound_viewer_test.py checks it).
    /// </summary>
    public static class DspAdpcm
    {
        /// <summary>One channel encoded: the 16 coefficients, the ADPCM frames (8 bytes per 14 samples, padded to an even
        /// count: whole 0x10-byte interleave blocks), the samples the DSP will decode (for the loop history).</summary>
        public class Channel
        {
            public short[] Coefs = new short[16];
            public byte[] Frames;
            public short[] Decoded;
        }

        // ---------------------------------------------------------------- coefficients (DSPCorrelateCoefs)

        // pcmHist: 28 shorts (the previous 14 at 0..13, the current 14 at 14..27); 'at' is the current block's start (14),
        // so pcm[at + x - i] reaches back into the previous block as grok.c's pointer arithmetic does.
        static void InnerProductMerge(double[] vecOut, short[] pcm, int at)
        {
            for (int i = 0; i <= 2; i++)
            {
                vecOut[i] = 0.0;
                for (int x = 0; x < 14; x++)
                    vecOut[i] -= pcm[at + x - i] * pcm[at + x];
            }
        }

        static void OuterProductMerge(double[][] mtxOut, short[] pcm, int at)
        {
            for (int x = 1; x <= 2; x++)
                for (int y = 1; y <= 2; y++)
                {
                    mtxOut[x][y] = 0.0;
                    for (int z = 0; z < 14; z++)
                        mtxOut[x][y] += pcm[at + z - x] * pcm[at + z - y];
                }
        }

        const double DblEpsilon = 2.2204460492503131e-016;     // C's DBL_EPSILON

        static bool AnalyzeRanges(double[][] mtx, int[] vecIdxsOut)
        {
            var recips = new double[3];
            double val, tmp, min, max;
            for (int x = 1; x <= 2; x++)
            {
                val = Math.Max(Math.Abs(mtx[x][1]), Math.Abs(mtx[x][2]));
                if (val < DblEpsilon) return true;
                recips[x] = 1.0 / val;
            }
            int maxIndex = 0;
            for (int i = 1; i <= 2; i++)
            {
                for (int x = 1; x < i; x++)
                {
                    tmp = mtx[x][i];
                    for (int y = 1; y < x; y++)
                        tmp -= mtx[x][y] * mtx[y][i];
                    mtx[x][i] = tmp;
                }
                val = 0.0;
                for (int x = i; x <= 2; x++)
                {
                    tmp = mtx[x][i];
                    for (int y = 1; y < i; y++)
                        tmp -= mtx[x][y] * mtx[y][i];
                    mtx[x][i] = tmp;
                    tmp = Math.Abs(tmp) * recips[x];
                    if (tmp >= val)
                    {
                        val = tmp;
                        maxIndex = x;
                    }
                }
                if (maxIndex != i)
                {
                    for (int y = 1; y <= 2; y++)
                    {
                        tmp = mtx[maxIndex][y];
                        mtx[maxIndex][y] = mtx[i][y];
                        mtx[i][y] = tmp;
                    }
                    recips[maxIndex] = recips[i];
                }
                vecIdxsOut[i] = maxIndex;
                if (mtx[i][i] == 0.0) return true;
                if (i != 2)
                {
                    tmp = 1.0 / mtx[i][i];
                    for (int x = i + 1; x <= 2; x++)
                        mtx[x][i] *= tmp;
                }
            }
            min = 1.0e10;
            max = 0.0;
            for (int i = 1; i <= 2; i++)
            {
                tmp = Math.Abs(mtx[i][i]);
                if (tmp < min) min = tmp;
                if (tmp > max) max = tmp;
            }
            return min / max < 1.0e-10;
        }

        static void BidirectionalFilter(double[][] mtx, int[] vecIdxs, double[] vecOut)
        {
            double tmp;
            for (int i = 1, x = 0; i <= 2; i++)
            {
                int index = vecIdxs[i];
                tmp = vecOut[index];
                vecOut[index] = vecOut[i];
                if (x != 0)
                    for (int y = x; y <= i - 1; y++)
                        tmp -= vecOut[y] * mtx[i][y];
                else if (tmp != 0.0)
                    x = i;
                vecOut[i] = tmp;
            }
            for (int i = 2; i > 0; i--)
            {
                tmp = vecOut[i];
                for (int y = i + 1; y <= 2; y++)
                    tmp -= vecOut[y] * mtx[i][y];
                vecOut[i] = tmp / mtx[i][i];
            }
            vecOut[0] = 1.0;
        }

        static bool QuadraticMerge(double[] inOutVec)
        {
            double v0, v1, v2 = inOutVec[2];
            double tmp = 1.0 - (v2 * v2);
            if (tmp == 0.0) return true;
            v0 = (inOutVec[0] - (v2 * v2)) / tmp;
            v1 = (inOutVec[1] - (inOutVec[1] * v2)) / tmp;
            inOutVec[0] = v0;
            inOutVec[1] = v1;
            return Math.Abs(v1) > 1.0;
        }

        static void FinishRecord(double[] inV, double[] outV)
        {
            for (int z = 1; z <= 2; z++)
            {
                if (inV[z] >= 1.0) inV[z] = 0.9999999999;
                else if (inV[z] <= -1.0) inV[z] = -0.9999999999;
            }
            outV[0] = 1.0;
            outV[1] = (inV[2] * inV[1]) + inV[1];
            outV[2] = inV[2];
        }

        static void MatrixFilter(double[] src, double[] dst)
        {
            var mtx = new[] { new double[3], new double[3], new double[3] };
            mtx[2][0] = 1.0;
            for (int i = 1; i <= 2; i++)
                mtx[2][i] = -src[i];
            for (int i = 2; i > 0; i--)
            {
                double val = 1.0 - (mtx[i][i] * mtx[i][i]);
                for (int y = 1; y <= i; y++)
                    mtx[i - 1][y] = ((mtx[i][i] * mtx[i][y]) + mtx[i][y]) / val;
            }
            dst[0] = 1.0;
            for (int i = 1; i <= 2; i++)
            {
                dst[i] = 0.0;
                for (int y = 1; y <= i; y++)
                    dst[i] += mtx[i][y] * dst[i - y];
            }
        }

        static void MergeFinishRecord(double[] src, double[] dst)
        {
            var tmp = new double[3];
            double val = src[0];
            dst[0] = 1.0;
            for (int i = 1; i <= 2; i++)
            {
                double v2 = 0.0;
                for (int y = 1; y < i; y++)
                    v2 += dst[y] * src[i - y];
                if (val > 0.0)
                    dst[i] = -(v2 + src[i]) / val;
                else
                    dst[i] = 0.0;
                tmp[i] = dst[i];
                for (int y = 1; y < i; y++)
                    dst[y] += dst[i] * dst[i - y];
                val *= 1.0 - (dst[i] * dst[i]);
            }
            FinishRecord(tmp, dst);
        }

        static double ContrastVectors(double[] source1, double[] source2)
        {
            double val = (source2[2] * source2[1] + -source2[1]) / (1.0 - source2[2] * source2[2]);
            double val1 = (source1[0] * source1[0]) + (source1[1] * source1[1]) + (source1[2] * source1[2]);
            double val2 = (source1[0] * source1[1]) + (source1[1] * source1[2]);
            double val3 = source1[0] * source1[2];
            return val1 + (2.0 * val * val2) + (2.0 * (-source2[1] * val + -source2[2]) * val3);
        }

        static void FilterRecords(double[][] vecBest, int exp, double[][] records, int recordCount)
        {
            var bufferList = new double[8][];
            for (int i = 0; i < 8; i++) bufferList[i] = new double[3];
            var buffer1 = new int[8];
            var buffer2 = new double[3];
            for (int x = 0; x < 2; x++)
            {
                for (int y = 0; y < exp; y++)
                {
                    buffer1[y] = 0;
                    for (int i = 0; i <= 2; i++) bufferList[y][i] = 0.0;
                }
                for (int z = 0; z < recordCount; z++)
                {
                    int index = 0;
                    double value = 1.0e30;
                    for (int i = 0; i < exp; i++)
                    {
                        double tempVal = ContrastVectors(vecBest[i], records[z]);
                        if (tempVal < value)
                        {
                            value = tempVal;
                            index = i;
                        }
                    }
                    buffer1[index]++;
                    MatrixFilter(records[z], buffer2);
                    for (int i = 0; i <= 2; i++) bufferList[index][i] += buffer2[i];
                }
                for (int i = 0; i < exp; i++)
                    if (buffer1[i] > 0)
                        for (int y = 0; y <= 2; y++) bufferList[i][y] /= buffer1[i];
                for (int i = 0; i < exp; i++)
                    MergeFinishRecord(bufferList[i], vecBest[i]);
            }
        }

        /// <summary>C's lround to a short as grok.c writes the coefficients (clamped; NaN, a silent clip's, as x86's
        /// lround gives it: 0x8000000000000000, whose low 16 bits are 0).</summary>
        static short Coef(double d)
        {
            if (double.IsNaN(d)) return 0;
            if (d > 0.0) return d > 32767.0 ? (short)32767 : (short)Math.Round(d, MidpointRounding.AwayFromZero);
            return d < -32768.0 ? (short)-32768 : (short)Math.Round(d, MidpointRounding.AwayFromZero);
        }

        /// <summary>The 8 coefficient pairs for a channel (grok.c DSPCorrelateCoefs).</summary>
        public static short[] CorrelateCoefs(short[] source, int offset, int samples)
        {
            int numFrames = (samples + 13) / 14;
            var blockBuffer = new short[0x3800];
            var hist = new short[28];               // pcmHistBuffer[2][14], contiguous
            var vec1 = new double[3];
            var vec2 = new double[3];
            var mtx = new[] { new double[3], new double[3], new double[3] };
            var vecIdxs = new int[3];
            var records = new double[numFrames * 2 + 1][];
            for (int i = 0; i < records.Length; i++) records[i] = new double[3];
            int recordCount = 0;
            var vecBest = new double[8][];
            for (int i = 0; i < 8; i++) vecBest[i] = new double[3];
            int src = offset;
            for (int x = samples; x > 0;)
            {
                int frameSamples;
                if (x > 0x3800)
                {
                    frameSamples = 0x3800;
                    x -= 0x3800;
                }
                else
                {
                    frameSamples = x;
                    for (int z = 0; z < 14 && z + frameSamples < 0x3800; z++)
                        blockBuffer[frameSamples + z] = 0;
                    x = 0;
                }
                Array.Copy(source, src, blockBuffer, 0, frameSamples);
                src += frameSamples;
                for (int i = 0; i < frameSamples;)
                {
                    for (int z = 0; z < 14; z++) hist[z] = hist[14 + z];
                    for (int z = 0; z < 14; z++) hist[14 + z] = blockBuffer[i++];
                    InnerProductMerge(vec1, hist, 14);
                    if (Math.Abs(vec1[0]) > 10.0)
                    {
                        OuterProductMerge(mtx, hist, 14);
                        if (!AnalyzeRanges(mtx, vecIdxs))
                        {
                            BidirectionalFilter(mtx, vecIdxs, vec1);
                            if (!QuadraticMerge(vec1))
                            {
                                FinishRecord(vec1, records[recordCount]);
                                recordCount++;
                            }
                        }
                    }
                }
            }
            vec1[0] = 1.0;
            vec1[1] = 0.0;
            vec1[2] = 0.0;
            for (int z = 0; z < recordCount; z++)
            {
                MatrixFilter(records[z], vecBest[0]);
                for (int y = 1; y <= 2; y++) vec1[y] += vecBest[0][y];
            }
            for (int y = 1; y <= 2; y++) vec1[y] /= recordCount;
            MergeFinishRecord(vec1, vecBest[0]);
            int exp = 1;
            for (int w = 0; w < 3;)
            {
                vec2[0] = 0.0;
                vec2[1] = -1.0;
                vec2[2] = 0.0;
                for (int i = 0; i < exp; i++)
                    for (int y = 0; y <= 2; y++)
                        vecBest[exp + i][y] = (0.01 * vec2[y]) + vecBest[i][y];
                ++w;
                exp = 1 << w;
                FilterRecords(vecBest, exp, records, recordCount);
            }
            var coefs = new short[16];
            for (int z = 0; z < 8; z++)
            {
                coefs[z * 2] = Coef(-vecBest[z][1] * 2048.0);
                coefs[z * 2 + 1] = Coef(-vecBest[z][2] * 2048.0);
            }
            return coefs;
        }

        // ---------------------------------------------------------------- frames (DSPEncodeFrame)

        static readonly double Half = (double)0.4999999f;     // grok.c's 0.4999999f, a float promoted to double

        /// <summary>One frame: pcmInOut[0..1] the history, [2..15] the samples (left decoded, as grok.c leaves them).</summary>
        public static void EncodeFrame(short[] pcmInOut, int sampleCount, byte[] adpcmOut, int outAt, short[] coefs)
        {
            var inSamples = new int[8, 16];
            var outSamples = new int[8, 14];
            int bestIndex = 0;
            var scale = new int[8];
            var distAccum = new double[8];
            for (int i = 0; i < 8; i++)
            {
                int c0 = coefs[i * 2], c1 = coefs[i * 2 + 1];
                int v1, v2, v3, distance, index;
                inSamples[i, 0] = pcmInOut[0];
                inSamples[i, 1] = pcmInOut[1];
                distance = 0;
                for (int s = 0; s < sampleCount; s++)
                {
                    inSamples[i, s + 2] = v1 = ((pcmInOut[s] * c1) + (pcmInOut[s + 1] * c0)) / 2048;
                    v2 = pcmInOut[s + 2] - v1;
                    v3 = (v2 >= 32767) ? 32767 : (v2 <= -32768) ? -32768 : v2;
                    if (Math.Abs(v3) > Math.Abs(distance)) distance = v3;
                }
                for (scale[i] = 0; (scale[i] <= 12) && ((distance > 7) || (distance < -8)); scale[i]++, distance /= 2) { }
                scale[i] = (scale[i] <= 1) ? -1 : scale[i] - 2;
                do
                {
                    scale[i]++;
                    distAccum[i] = 0;
                    index = 0;
                    for (int s = 0; s < sampleCount; s++)
                    {
                        v1 = ((inSamples[i, s] * c1) + (inSamples[i, s + 1] * c0));
                        v2 = ((pcmInOut[s + 2] << 11) - v1) / 2048;
                        v3 = (v2 > 0) ? (int)((double)v2 / (1 << scale[i]) + Half) : (int)((double)v2 / (1 << scale[i]) - Half);
                        if (v3 < -8)
                        {
                            if (index < (v3 = -8 - v3)) index = v3;
                            v3 = -8;
                        }
                        else if (v3 > 7)
                        {
                            if (index < (v3 -= 7)) index = v3;
                            v3 = 7;
                        }
                        outSamples[i, s] = v3;
                        v1 = (v1 + ((v3 * (1 << scale[i])) << 11) + 1024) >> 11;
                        inSamples[i, s + 2] = v2 = (v1 >= 32767) ? 32767 : (v1 <= -32768) ? -32768 : v1;
                        v3 = pcmInOut[s + 2] - v2;
                        distAccum[i] += v3 * (double)v3;
                    }
                    for (int x = index + 8; x > 256; x >>= 1)
                        if (++scale[i] >= 12) scale[i] = 11;
                } while ((scale[i] < 12) && (index > 1));
            }
            double min = double.MaxValue;
            for (int i = 0; i < 8; i++)
                if (distAccum[i] < min)
                {
                    min = distAccum[i];
                    bestIndex = i;
                }
            for (int s = 0; s < sampleCount; s++)
                pcmInOut[s + 2] = (short)inSamples[bestIndex, s + 2];
            adpcmOut[outAt] = (byte)((bestIndex << 4) | (scale[bestIndex] & 0xF));
            for (int s = sampleCount; s < 14; s++) outSamples[bestIndex, s] = 0;
            for (int y = 0; y < 7; y++)
                adpcmOut[outAt + y + 1] = (byte)((outSamples[bestIndex, y * 2] << 4) | (outSamples[bestIndex, y * 2 + 1] & 0xF));
        }

        /// <summary>A channel (pcm interleaved with 'channels', this one at 'channel') encoded as dspenc.c does: the
        /// coefficients over the whole channel, then each frame from the previous frame's decoded history.</summary>
        public static Channel Encode(short[] pcm, int channels, int channel)
        {
            int n = pcm.Length / channels;
            var mono = new short[n];
            for (int i = 0; i < n; i++) mono[i] = pcm[(long)i * channels + channel];
            var ch = new Channel { Coefs = CorrelateCoefs(mono, 0, n) };
            int frames = (n + 13) / 14;
            int padded = frames + (frames & 1);
            ch.Frames = new byte[padded * 8];
            ch.Decoded = new short[n];
            var buf = new short[16];
            for (int p = 0; p < frames; p++)
            {
                int count = n - p * 14 < 14 ? n - p * 14 : 14;
                for (int k = 2; k < 16; k++) buf[k] = 0;
                Array.Copy(mono, p * 14, buf, 2, count);
                EncodeFrame(buf, count, ch.Frames, p * 8, ch.Coefs);
                Array.Copy(buf, 2, ch.Decoded, p * 14, count);
                buf[0] = buf[14];
                buf[1] = buf[15];
            }
            return ch;
        }
    }

    public static class IdspWriter
    {
        /// <summary>The DSP's nibble address of a sample (2 header nibbles per 16).</summary>
        public static int Nibble(int sample) { return sample / 14 * 16 + 2 + sample % 14; }

        static void BE32(byte[] b, int at, int v) { b[at] = (byte)(v >> 24); b[at + 1] = (byte)(v >> 16); b[at + 2] = (byte)(v >> 8); b[at + 3] = (byte)v; }
        static void BE16(byte[] b, int at, int v) { b[at] = (byte)(v >> 8); b[at + 1] = (byte)v; }

        /// <summary>
        /// A Namco IDSP file as the game's own tones are (v1.7.33; read from vanilla snd_se_Gekkouga / snd_se_joucyu /
        /// snd_vc_Gekkouga_ouen): 0x40-byte header ('IDSP', 0, channels, rate, samples, loop start, loop end (samples; 0, 0
        /// for a one-shot), interleave 0x10, 0x40, 0x60, data offset 0x40 + 0x60 x channels, the data size per channel),
        /// a 0x60-byte DSP header per channel (samples, nibbles = Nibble(n - 1) + 1, rate, loop flag, format 0, loop
        /// start / end nibbles (Nibble(0) = 2 and Nibble(n - 1) for a one-shot), current address 2, the coefficients,
        /// gain 0, ps (the first frame's header byte), yn1 / yn2 0, the loop frame's ps and the two decoded samples before
        /// the loop start), then the ADPCM: each channel's frames padded to an even count (whole 0x10 blocks) and
        /// interleaved every 0x10 bytes. Mono, the layout tools/fighter_own_bank.py's idsp_oneshot writes.
        /// </summary>
        public static byte[] Encode(short[] pcm, int channels, int rate, bool loop, int loopStart = 0, int loopEnd = -1)
        {
            if (channels < 1 || channels > 2) throw new ArgumentException("1 or 2 channels");
            int n = pcm.Length / channels;
            if (n < 1) throw new ArgumentException("no samples");
            if (loopEnd < 0 || loopEnd >= n) loopEnd = n - 1;
            if (loopStart < 0 || loopStart > loopEnd) loopStart = 0;
            var chans = new DspAdpcm.Channel[channels];
            for (int c = 0; c < channels; c++) chans[c] = DspAdpcm.Encode(pcm, channels, c);
            int size = chans[0].Frames.Length;
            int dataOffset = 0x40 + 0x60 * channels;
            var b = new byte[dataOffset + size * channels];
            Encoding.ASCII.GetBytes("IDSP").CopyTo(b, 0);
            BE32(b, 0x08, channels);
            BE32(b, 0x0C, rate);
            BE32(b, 0x10, n);
            BE32(b, 0x14, loop ? loopStart : 0);
            BE32(b, 0x18, loop ? loopEnd : 0);
            BE32(b, 0x1C, 0x10);
            BE32(b, 0x20, 0x40);
            BE32(b, 0x24, 0x60);
            BE32(b, 0x28, dataOffset);
            BE32(b, 0x2C, size);
            for (int c = 0; c < channels; c++)
            {
                int h = 0x40 + 0x60 * c;
                var ch = chans[c];
                BE32(b, h + 0x00, n);
                BE32(b, h + 0x04, Nibble(n - 1) + 1);
                BE32(b, h + 0x08, rate);
                BE16(b, h + 0x0C, loop ? 1 : 0);
                BE16(b, h + 0x0E, 0);
                BE32(b, h + 0x10, loop ? Nibble(loopStart) : Nibble(0));
                BE32(b, h + 0x14, Nibble(loop ? loopEnd : n - 1));
                BE32(b, h + 0x18, 2);
                for (int k = 0; k < 16; k++) BE16(b, h + 0x1C + 2 * k, ch.Coefs[k]);
                BE16(b, h + 0x3C, 0);                       // gain
                BE16(b, h + 0x3E, ch.Frames[0]);            // ps
                // yn1 / yn2 (h + 0x40 / 0x42) 0
                if (loop)
                {
                    BE16(b, h + 0x44, ch.Frames[loopStart / 14 * 8]);
                    BE16(b, h + 0x46, loopStart > 0 ? ch.Decoded[loopStart - 1] : 0);
                    BE16(b, h + 0x48, loopStart > 1 ? ch.Decoded[loopStart - 2] : 0);
                }
            }
            if (channels == 1)
                Array.Copy(chans[0].Frames, 0, b, dataOffset, size);
            else
                for (int blk = 0; blk < size / 0x10; blk++)
                    for (int c = 0; c < channels; c++)
                        Array.Copy(chans[c].Frames, blk * 0x10, b, dataOffset + (blk * channels + c) * 0x10, 0x10);
            return b;
        }
    }
}
