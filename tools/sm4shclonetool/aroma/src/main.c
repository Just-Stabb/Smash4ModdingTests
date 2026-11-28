/*
 * Sm4shCloneTool Aroma plugin: applies a Sm4shCloneTool clone patch to Super Smash Bros. for Wii U (v288) in
 * memory, so the console runs the game's own cross_f.rpx (no modified executable is installed).
 *
 * At every application start:
 *   1. the running title must be Smash 4 (USA / EUR / JPN); its update's version is read (MCP);
 *   2. the patch file the tool wrote is read from the SD card:
 *        sd:/wiiu/sm4shclonetool/<title id>.patch   (e.g. 0005000010144F00.patch), else sd:/wiiu/sm4shclonetool/sm4sh.patch
 *   3. patch_core.c checks it (magic, format, CRC-32, the title in its list, the update version), compares every word
 *      of the game the patch changes with the original the file records (one mismatch: nothing is written), copies the
 *      code cave into this plugin's memory (cave.S) at an address = the file's link base modulo 0x10000 and relocates
 *      it, and writes the game's words;
 *   4. the game's words go through the kernel (KernelCopyData on physical addresses: the game's code is read-only to
 *      applications); the caches are flushed / invalidated.
 * The file format: ../README.md; the tool's writer and the same algorithm in Python: sm4shclonetool/patchset.py.
 *
 * MIT License, the Sm4shCloneTool authors.
 */
#include <wups.h>

#include <coreinit/cache.h>
#include <coreinit/debug.h>
#include <coreinit/mcp.h>
#include <coreinit/memorymap.h>
#include <coreinit/title.h>
#include <kernel/kernel.h>
#include <notifications/notifications.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "patch_core.h"

WUPS_PLUGIN_NAME("Sm4shCloneTool");
WUPS_PLUGIN_DESCRIPTION("New fighter / stage slots for Smash 4 v288 (Sm4shCloneTool), without a modified cross_f.rpx");
WUPS_PLUGIN_VERSION("v1.5.0");
WUPS_PLUGIN_AUTHOR("the Sm4shCloneTool authors");
WUPS_PLUGIN_LICENSE("MIT");

WUPS_USE_WUT_DEVOPTAB();

#define PATCH_DIR "fs:/vol/external01/wiiu/sm4shclonetool"
#define MAX_FILE  (8u * 1024 * 1024)

/* cave.S: the cave's buffer in this plugin's .text */
extern uint8_t s4ct_cave[], s4ct_cave_end[];
static uint32_t sWord __attribute__((aligned(0x40)));
static int sNotify = 0;

static void say(int error, const char *msg) {
    OSReport("[Sm4shCloneTool] %s\n", msg);
    if (sNotify) {
        char buf[300];
        snprintf(buf, sizeof(buf), "Sm4shCloneTool: %s", msg);
        if (error)
            NotificationModule_AddErrorNotification(buf);
        else
            NotificationModule_AddInfoNotification(buf);
    }
}

static int is_smash(uint64_t tid) {
    return tid == 0x0005000010144F00ULL || tid == 0x0005000010145000ULL || tid == 0x0005000010110E00ULL;
}

/* the update's title version (0005000E-<low>), -1 when MCP can't tell */
static int update_version(uint64_t tid) {
    int h = MCP_Open();
    if (h < 0)
        return -1;
    MCPTitleListType info;
    memset(&info, 0, sizeof(info));
    int v = -1;
    if (MCP_GetTitleInfo(h, 0x0005000E00000000ULL | (tid & 0xFFFFFFFFULL), &info) == 0)
        v = info.titleVersion;
    MCP_Close(h);
    return v;
}

static uint32_t game_read(void *ctx, uint32_t addr) {
    (void) ctx;
    return *(volatile uint32_t *) addr;
}

static int game_mapped(void *ctx, uint32_t addr) {
    (void) ctx;
    return OSEffectiveToPhysical(addr) != 0;
}

/* one word of the game, through the kernel (its code is read-only to applications) */
static void game_write(void *ctx, uint32_t addr, uint32_t value) {
    (void) ctx;
    sWord = value;
    DCFlushRange(&sWord, 4);
    KernelCopyData(OSEffectiveToPhysical(addr), OSEffectiveToPhysical((uint32_t) &sWord), 4);
    DCFlushRange((void *) addr, 4);
    ICInvalidateRange((void *) addr, 4);
}

static void cave_flush(void *ctx, void *p, uint32_t n) {
    (void) ctx;
    DCFlushRange(p, n);
    ICInvalidateRange(p, n);
}

static uint8_t *read_file(const char *path, uint32_t *size) {
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *buf = NULL;
    if (n > 0 && n <= (long) MAX_FILE) {
        buf = (uint8_t *) malloc((size_t) n);
        if (buf && fread(buf, 1, (size_t) n, f) != (size_t) n) {
            free(buf);
            buf = NULL;
        }
    }
    fclose(f);
    *size = (uint32_t) n;
    return buf;
}

static void apply_patch(uint64_t tid) {
    char path[128];
    uint32_t n = 0;
    snprintf(path, sizeof(path), PATCH_DIR "/%016llX.patch", (unsigned long long) tid);
    uint8_t *d = read_file(path, &n);
    if (!d) {
        snprintf(path, sizeof(path), PATCH_DIR "/sm4sh.patch");
        d = read_file(path, &n);
    }
    if (!d) {
        OSReport("[Sm4shCloneTool] no patch file for %016llX: the game runs unpatched\n", (unsigned long long) tid);
        return;
    }
    s4ct_env env = {game_read, game_mapped, game_write, cave_flush, NULL};
    s4ct_result res;
    uint32_t room = (uint32_t) (s4ct_cave_end - s4ct_cave);
    int r = s4ct_apply(d, n, tid, update_version(tid), s4ct_cave, room, (uint32_t) s4ct_cave, &env, &res);
    if (r == S4CT_OK) {
        say(0, res.msg);
    } else {
        char msg[280];
        snprintf(msg, sizeof(msg), "%s: nothing patched", res.msg);
        say(1, msg);
    }
    free(d);
}

INITIALIZE_PLUGIN() {
    sNotify = NotificationModule_InitLibrary() == NOTIFICATION_MODULE_RESULT_SUCCESS;
}

DEINITIALIZE_PLUGIN() {
    if (sNotify)
        NotificationModule_DeInitLibrary();
    sNotify = 0;
}

ON_APPLICATION_START() {
    uint64_t tid = OSGetTitleID();
    if (is_smash(tid))
        apply_patch(tid);
}
