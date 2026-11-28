/*
 * Sm4shCloneTool patch files: parse, check and apply. See patch_core.h and ../README.md (the file format).
 * MIT License, the Sm4shCloneTool authors.
 */
#include "patch_core.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t be32(const uint8_t *p) {
    return ((uint32_t) p[0] << 24) | ((uint32_t) p[1] << 16) | ((uint32_t) p[2] << 8) | p[3];
}

static void put32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t) (v >> 24);
    p[1] = (uint8_t) (v >> 16);
    p[2] = (uint8_t) (v >> 8);
    p[3] = (uint8_t) v;
}

static uint64_t be64(const uint8_t *p) {
    return ((uint64_t) be32(p) << 32) | be32(p + 4);
}

uint32_t s4ct_crc32(const uint8_t *p, uint32_t n) {
    uint32_t c = 0xFFFFFFFFu;
    for (uint32_t i = 0; i < n; i++) {
        c ^= p[i];
        for (int k = 0; k < 8; k++)
            c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u)));
    }
    return ~c;
}

static int32_t branch_offset(uint32_t w) {
    int32_t off = (int32_t) (w & 0x03FFFFFCu);
    if (off & 0x02000000)
        off -= 0x04000000;
    return off;
}

int s4ct_site_word(uint32_t w, uint32_t kind, uint32_t delta, uint32_t addr, uint32_t *out) {
    switch (kind) {
        case S4CT_K_ABS:
            *out = w;
            return 1;
        case S4CT_K_HA16: /* the high half of a cave address: += delta >> 16 (delta is a multiple of 0x10000) */
            *out = (w & 0xFFFF0000u) | ((w + (delta >> 16)) & 0xFFFFu);
            return 1;
        case S4CT_K_ADDR32:
            *out = w + delta;
            return 1;
        case S4CT_K_REL24: { /* a branch into the cave: absolute (ba / bla) when the cave is below 0x02000000 */
            uint32_t target = ((w & 2u) ? 0u : addr) + (uint32_t) branch_offset(w) + delta;
            if (target < 0x02000000u) {
                *out = (w & 0xFC000001u) | 2u | target;
                return 1;
            }
            int64_t rel = (int64_t) (int32_t) (target - addr);
            if (rel < -0x02000000 || rel >= 0x02000000)
                return 0;
            *out = (w & 0xFC000001u) | ((uint32_t) rel & 0x03FFFFFCu);
            return 1;
        }
    }
    return 0;
}

static int fail(s4ct_result *res, int code, const char *msg) {
    snprintf(res->msg, sizeof(res->msg), "%s", msg);
    return code;
}

int s4ct_apply(const uint8_t *d, uint32_t n, uint64_t tid, int update_version, uint8_t *cave, uint32_t cave_room,
               uint32_t cave_addr, const s4ct_env *env, s4ct_result *res) {
    memset(res, 0, sizeof(*res));
    if (n < S4CT_HEADER_SIZE + 4 || memcmp(d, "S4CTPTCH", 8) != 0)
        return fail(res, S4CT_ERR_FILE, "not a Sm4shCloneTool patch file");
    if (s4ct_crc32(d, n - 4) != be32(d + n - 4))
        return fail(res, S4CT_ERR_FILE, "the patch file is damaged (CRC)");
    uint32_t format = be32(d + 8), version = be32(d + 12), link = be32(d + 16), align = be32(d + 20);
    uint32_t cave_size = be32(d + 24), nsites = be32(d + 28), nrel = be32(d + 32), ntitles = be32(d + 36);
    uint32_t nmeta = be32(d + 40);
    res->version = version;
    if (format != S4CT_FORMAT || align != S4CT_ALIGN)
        return fail(res, S4CT_ERR_FORMAT, "the patch file's format is not this plugin's: update the plugin");
    /* the sections, with every size checked against the file's length */
    uint64_t o = S4CT_HEADER_SIZE;
    int listed = 0;
    if (o + 8ull * ntitles > n)
        return fail(res, S4CT_ERR_FILE, "the patch file is truncated");
    for (uint32_t i = 0; i < ntitles; i++, o += 8)
        listed |= be64(d + o) == tid;
    o += nmeta + ((4 - nmeta % 4) % 4);
    uint64_t sites = o, rels = sites + 16ull * nsites, blob = rels + 4ull * nrel;
    if (blob + cave_size + 4 != n || (cave_size & 3u))
        return fail(res, S4CT_ERR_FILE, "the patch file is truncated");
    if (!listed)
        return fail(res, S4CT_ERR_TITLE, "the patch file is not for this game");
    if (update_version >= 0 && (uint32_t) update_version != version) {
        snprintf(res->msg, sizeof(res->msg), "the game's update is v%d, the patch is for v%u", update_version, version);
        return S4CT_ERR_VERSION;
    }
    /* the cave's place: = link (mod 0x10000) in the buffer, below 0x02000000 */
    uint32_t base = (cave_addr & ~0xFFFFu) | (link & 0xFFFFu);
    if (base < cave_addr)
        base += 0x10000u;
    res->cave_size = cave_size;
    res->base = base;
    if ((uint64_t) base + cave_size > (uint64_t) cave_addr + cave_room) {
        snprintf(res->msg, sizeof(res->msg), "the cave needs %u KB, the plugin has %u KB (rebuild it with a larger "
                 "CAVE_KB)", cave_size >> 10, cave_room > 0x10000 ? (cave_room - 0x10000) >> 10 : 0);
        return S4CT_ERR_ROOM;
    }
    if ((uint64_t) base + cave_size > 0x02000000ull || !env->mapped(env->ctx, base)) {
        snprintf(res->msg, sizeof(res->msg), "the plugin's memory (0x%08X) is out of the game's branches' reach", base);
        return S4CT_ERR_ROOM;
    }
    uint32_t delta = base - link;
    /* every original first */
    for (uint32_t i = 0; i < nsites; i++) {
        const uint8_t *s = d + sites + 16ull * i;
        uint32_t addr = be32(s), orig = be32(s + 4);
        if (!env->mapped(env->ctx, addr) || env->read(env->ctx, addr) != orig) {
            if (!res->bad++)
                res->first_bad = addr;
        }
    }
    if (res->bad) {
        snprintf(res->msg, sizeof(res->msg), "%u word(s) of the game are not v288's (first 0x%08X: another mod, or "
                 "the tool's patched cross_f.rpx installed too?)", res->bad, res->first_bad);
        return S4CT_ERR_ORIGINAL;
    }
    /* the game's new words, all computed before anything is written */
    uint32_t *words = (uint32_t *) malloc(4u * (nsites ? nsites : 1u));
    if (!words)
        return fail(res, S4CT_ERR_MEMORY, "out of memory");
    for (uint32_t i = 0; i < nsites; i++) {
        const uint8_t *s = d + sites + 16ull * i;
        if (!s4ct_site_word(be32(s + 8), be32(s + 12), delta, be32(s), &words[i])) {
            snprintf(res->msg, sizeof(res->msg), "the hook at 0x%08X can't reach the cave", be32(s));
            free(words);
            return S4CT_ERR_BRANCH;
        }
    }
    /* the cave: copied (zeros around it), relocated */
    uint8_t *c = cave + (base - cave_addr);
    memset(cave, 0, cave_room);
    memcpy(c, d + blob, cave_size);
    for (uint32_t i = 0; i < nrel; i++) {
        uint32_t v = be32(d + rels + 4ull * i), off = v & 0x0FFFFFFFu, kind = v >> 28;
        uint32_t w;
        if (off + 4u <= cave_size && s4ct_site_word(be32(c + off), kind, delta, base + off, &w))
            put32(c + off, w);
    }
    if (env->flush)
        env->flush(env->ctx, cave, cave_room);
    /* the game's words (the cave is in place before any hook points at it) */
    for (uint32_t i = 0; i < nsites; i++)
        env->write(env->ctx, be32(d + sites + 16ull * i), words[i]);
    res->words = nsites;
    free(words);
    snprintf(res->msg, sizeof(res->msg), "clone patch applied: %u words, a %u KB cave at 0x%08X", nsites,
             cave_size >> 10, base);
    return S4CT_OK;
}
