/*
 * The Aroma plugin's patch code (aroma/src/patch_core.c) on a PC, for patchset_test.py: the game's memory is the
 * word list MEMDUMP gives (big-endian address / word pairs; any other address is unmapped), the cave buffer is at
 * CAVE_ADDR (1 MB + 64 KB, the plugin's default).
 *
 *   plugin_host PATCH MEMDUMP CAVE_ADDR TITLE_ID UPDATE_VERSION OUT_CAVE > report
 *
 * report: "rc N", "msg ...", "base 0x...", "size N", then "w ADDR WORD" per game word written (in order); OUT_CAVE gets
 * the cave's bytes (size bytes from base).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../aroma/src/patch_core.h"

typedef struct {
    uint32_t *addr, *word;
    size_t n;
    uint32_t cave_lo, cave_hi;
} mem_t;

static uint8_t *slurp(const char *path, uint32_t *n) {
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *b = malloc(len > 0 ? (size_t) len : 1);
    if (fread(b, 1, (size_t) len, f) != (size_t) len)
        len = 0;
    fclose(f);
    *n = (uint32_t) len;
    return b;
}

static uint32_t be(const uint8_t *p) {
    return ((uint32_t) p[0] << 24) | ((uint32_t) p[1] << 16) | ((uint32_t) p[2] << 8) | p[3];
}

static long find(mem_t *m, uint32_t a) {
    size_t lo = 0, hi = m->n;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (m->addr[mid] < a)
            lo = mid + 1;
        else
            hi = mid;
    }
    return lo < m->n && m->addr[lo] == a ? (long) lo : -1;
}

static uint32_t rd(void *ctx, uint32_t a) {
    mem_t *m = ctx;
    long i = find(m, a);
    return i < 0 ? 0xDEADBEEF : m->word[i];
}

static int mapped(void *ctx, uint32_t a) {
    mem_t *m = ctx;
    return find(m, a) >= 0 || (a >= m->cave_lo && a < m->cave_hi);
}

static void wr(void *ctx, uint32_t a, uint32_t w) {
    mem_t *m = ctx;
    long i = find(m, a);
    if (i >= 0)
        m->word[i] = w;
    printf("w 0x%08X 0x%08X\n", a, w);
}

int main(int argc, char **argv) {
    if (argc != 7) {
        fprintf(stderr, "usage: plugin_host PATCH MEMDUMP CAVE_ADDR TITLE_ID UPDATE_VERSION OUT_CAVE\n");
        return 2;
    }
    uint32_t n, dn;
    uint8_t *patch = slurp(argv[1], &n), *dump = slurp(argv[2], &dn);
    if (!patch || !dump)
        return 2;
    mem_t m;
    m.n = dn / 8;
    m.addr = malloc(4 * (m.n + 1));
    m.word = malloc(4 * (m.n + 1));
    for (size_t i = 0; i < m.n; i++) {
        m.addr[i] = be(dump + 8 * i);
        m.word[i] = be(dump + 8 * i + 4);
    }
    uint32_t cave_addr = (uint32_t) strtoul(argv[3], NULL, 0);
    uint64_t tid = strtoull(argv[4], NULL, 0);
    int ver = atoi(argv[5]);
    uint32_t room = 1024u * 1024 + 0x10000;
    uint8_t *cave = malloc(room);
    memset(cave, 0xA5, room);
    m.cave_lo = cave_addr;
    m.cave_hi = cave_addr + room;
    s4ct_env env = {rd, mapped, wr, NULL, &m};
    s4ct_result res;
    int rc = s4ct_apply(patch, n, tid, ver, cave, room, cave_addr, &env, &res);
    printf("rc %d\nmsg %s\nbase 0x%08X\nsize %u\n", rc, res.msg, res.base, res.cave_size);
    FILE *o = fopen(argv[6], "wb");
    if (o) {
        if (rc == S4CT_OK)
            fwrite(cave + (res.base - cave_addr), 1, res.cave_size, o);
        fclose(o);
    }
    return 0;
}
