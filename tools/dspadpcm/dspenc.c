/* GameCube / Wii DSP-ADPCM encoder front end (grok.c: jackoalan/gc-dspadpcm-encode, MIT).

   dspenc IN OUT LOOP_START
   IN: mono int16 little-endian PCM. OUT (big-endian): the 16 coefficients, the first frame's
   header byte (ps), the loop frame's (loop_ps), the two decoded samples before LOOP_START
   (loop_yn1, loop_yn2), then the ADPCM frames (8 bytes per 14 samples). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void DSPCorrelateCoefs(const short *source, int samples, short *coefsOut);
void DSPEncodeFrame(short pcmInOut[16], int sampleCount, unsigned char adpcmOut[8], const short coefsIn[8][2]);

static void be16(FILE *f, int v)
{
    fputc((v >> 8) & 255, f);
    fputc(v & 255, f);
}

int main(int argc, char **argv)
{
    if (argc != 4) {
        fprintf(stderr, "usage: dspenc IN OUT LOOP_START\n");
        return 1;
    }
    FILE *f = fopen(argv[1], "rb");
    if (!f)
        return 1;
    fseek(f, 0, SEEK_END);
    long n = ftell(f) / 2;
    fseek(f, 0, SEEK_SET);
    short *pcm = malloc(n * 2 + 32);
    if (fread(pcm, 2, n, f) != (size_t)n)
        return 1;
    fclose(f);
    long loop = atol(argv[3]);

    short coefs[16];
    DSPCorrelateCoefs(pcm, n, coefs);
    long frames = (n + 13) / 14;
    unsigned char *adpcm = calloc(frames, 8);
    short *dec = calloc(n + 16, 2);
    short buf[16] = {0};
    for (long p = 0; p < frames; p++) {
        int count = n - p * 14 < 14 ? n - p * 14 : 14;
        memset(buf + 2, 0, 28);
        memcpy(buf + 2, pcm + p * 14, count * 2);
        DSPEncodeFrame(buf, count, adpcm + p * 8, (const short (*)[2])coefs);
        memcpy(dec + p * 14, buf + 2, count * 2);   /* the encoder leaves the decoded samples */
        buf[0] = buf[14];
        buf[1] = buf[15];
    }

    FILE *o = fopen(argv[2], "wb");
    if (!o)
        return 1;
    for (int i = 0; i < 16; i++)
        be16(o, coefs[i]);
    be16(o, adpcm[0]);
    be16(o, adpcm[(loop / 14) * 8]);
    be16(o, loop > 0 ? dec[loop - 1] : 0);
    be16(o, loop > 1 ? dec[loop - 2] : 0);
    fwrite(adpcm, 8, frames, o);
    fclose(o);
    return 0;
}
