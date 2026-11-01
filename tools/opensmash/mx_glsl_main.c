/* mx_glsl: Ultimate's Maxwell shader code -> GLSL, with OpenSmash-Ultimate's translator
 * (ssbu-recomp runtime/mx_translate.c). Built by tools/ult_shader_glsl.py.
 *   mx_glsl CODE STAGE [CDATA]   CODE: the 0x50-byte program header (SPH) followed by the instructions;
 *                                STAGE: 0 vertex, 1 fragment; CDATA: constant buffer 1's contents (the
 *                                immediates NVN stores after the code). GLSL on stdout, a summary on stderr. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mx_translate.h"

static unsigned char *slurp(const char *path, long *n) {
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(2); }
    fseek(f, 0, SEEK_END); *n = ftell(f); fseek(f, 0, SEEK_SET);
    unsigned char *b = malloc(*n + 1);
    if (fread(b, 1, *n, f) != (size_t)*n) exit(2);
    fclose(f);
    return b;
}

int main(int argc, char **argv) {
    if (argc != 3 && argc != 4) { fprintf(stderr, "usage: mx_glsl CODE STAGE [CDATA]\n"); return 2; }
    long n, cn = 0;
    unsigned char *b = slurp(argv[1], &n), *c = argc == 4 ? slurp(argv[3], &cn) : NULL;
    MxIn in; memset(&in, 0, sizeof in);
    in.stage = atoi(argv[2]); in.code = b; in.code_len = (int)n;
    in.cdata = c; in.cdata_size = (uint32_t)cn;
    MxOut out; memset(&out, 0, sizeof out);
    if (!mx_translate(&in, &out)) { fprintf(stderr, "fail: %s (%s)\n", out.why, out.op); return 1; }
    puts(out.glsl);
    fprintf(stderr, "insns %d cbufs %x in %x out %x tex %x\n", out.insns, out.cbufs, out.in_attr, out.out_attr, out.tex_units);
    return 0;
}
