/* mx_glsl: Ultimate's Maxwell shader code -> GLSL, with OpenSmash-Ultimate's translator
 * (ssbu-recomp runtime/mx_translate.c). Built by tools/ult_shader_glsl.py.
 *   mx_glsl CODE STAGE     CODE: the 0x50-byte program header (SPH) followed by the instructions;
 *                          STAGE: 0 vertex, 1 fragment. GLSL on stdout, a summary on stderr. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mx_translate.h"

int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "usage: mx_glsl CODE STAGE\n"); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    unsigned char *b = malloc(n);
    if (fread(b, 1, n, f) != (size_t)n) { fclose(f); return 2; }
    fclose(f);
    MxIn in; memset(&in, 0, sizeof in);
    in.stage = atoi(argv[2]); in.code = b; in.code_len = (int)n;
    MxOut out; memset(&out, 0, sizeof out);
    if (!mx_translate(&in, &out)) { fprintf(stderr, "fail: %s (%s)\n", out.why, out.op); return 1; }
    puts(out.glsl);
    fprintf(stderr, "insns %d cbufs %x in %x out %x tex %x\n", out.insns, out.cbufs, out.in_attr, out.out_attr, out.tex_units);
    return 0;
}
