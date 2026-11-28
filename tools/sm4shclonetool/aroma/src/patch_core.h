/*
 * Sm4shCloneTool patch files: parse, check and apply (the plugin's core, free of Wii U calls so the same code is
 * tested on a PC against the tool's Python implementation, sm4shclonetool/patchset.py apply()).
 * MIT License, the Sm4shCloneTool authors.
 */
#ifndef S4CT_PATCH_CORE_H
#define S4CT_PATCH_CORE_H

#include <stddef.h>
#include <stdint.h>

#define S4CT_FORMAT 1
#define S4CT_HEADER_SIZE 44
#define S4CT_ALIGN 0x10000

enum { S4CT_K_ABS = 0, S4CT_K_HA16 = 1, S4CT_K_ADDR32 = 2, S4CT_K_REL24 = 3 };

enum {
    S4CT_OK = 0,
    S4CT_ERR_FILE,      /* not a patch file / damaged / truncated */
    S4CT_ERR_FORMAT,    /* a format this code does not read */
    S4CT_ERR_TITLE,     /* not for the running title */
    S4CT_ERR_VERSION,   /* not for the game's update version */
    S4CT_ERR_ROOM,      /* the cave does not fit the buffer, or is not reachable */
    S4CT_ERR_ORIGINAL,  /* a word of the game is not the original the file records */
    S4CT_ERR_BRANCH,    /* a hook can't reach the cave */
    S4CT_ERR_MEMORY,
};

typedef struct s4ct_env {
    /* a word of the game's memory (the running code) */
    uint32_t (*read)(void *ctx, uint32_t addr);
    /* 1 if addr is mapped */
    int (*mapped)(void *ctx, uint32_t addr);
    /* write one word of the game (through the kernel on the console) */
    void (*write)(void *ctx, uint32_t addr, uint32_t value);
    /* make the copied cave visible to instruction fetch (data cache flush, instruction cache invalidate); may be NULL */
    void (*flush)(void *ctx, void *p, uint32_t n);
    void *ctx;
} s4ct_env;

typedef struct s4ct_result {
    uint32_t base;       /* where the cave went (the game's address) */
    uint32_t cave_size;
    uint32_t words;      /* game words written */
    uint32_t bad;        /* words that are not the originals (S4CT_ERR_ORIGINAL) */
    uint32_t first_bad;
    uint32_t version;    /* the file's game version */
    char msg[200];
} s4ct_result;

/* file: the .patch bytes; tid: the running title; update_version: the update's title version (-1: unknown);
 * cave / cave_room: the buffer for the cave (our pointer), cave_addr: its address as the game sees it (the same on the
 * console). Nothing of the game is written unless every check passes. Returns S4CT_OK or an S4CT_ERR_*. */
int s4ct_apply(const uint8_t *file, uint32_t n, uint64_t tid, int update_version, uint8_t *cave, uint32_t cave_room,
               uint32_t cave_addr, const s4ct_env *env, s4ct_result *res);

/* the relocation of one word (kinds S4CT_K_*), delta = cave base - link base; 0 if a branch can't reach */
int s4ct_site_word(uint32_t w, uint32_t kind, uint32_t delta, uint32_t addr, uint32_t *out);

uint32_t s4ct_crc32(const uint8_t *p, uint32_t n);

#endif
