// vfx_trace.cpp - OpenSmash-Ultimate mod: records what Ultimate's particle engine (eft2, nn::vfx in main) does,
// frame by frame, so tools/fx_render.py can be checked against the real engine (docs/vfx-trace.md).
//
// Game 13.0.4 (main at 0x7100000000). Two functions are hooked (offsets in main, read from exefs main.bin):
//   0x89BD0  one emitter's frame (x0 the system, x1 the emitter instance): emission, then the particles'
//            update. After it: an 'E' record (the emitter) and a 'P' record per live particle.
//   0x8FBE0  one particle's initialisation (x1 the emitter instance, x5 its particle arrays, w6 the
//            particle's slot, w7 its number in this emission). After it: a 'B' record (the particle as born).
// Only emitters of effect sets whose name contains one of VFX_TRACE_SETS are recorded.
//
// Environment:
//   VFX_TRACE_SETS   comma-separated, case-insensitive parts of set names (default "PZenigame"; "*" = all)
//   VFX_TRACE_OUT    output file (default vfx_trace.bin beside this DLL)
//   VFX_TRACE_MB     stop recording at this many MB (default 400)
//
// Built two ways: with the port's own tool (python fighter_sdk\tools\build_mod.py vfx_trace.cpp <folder>),
// or freestanding with no Windows SDK (tools/opensmash/build_vfx_trace.sh, -DVFX_FREESTANDING): it needs
// kernel32 only, declared below, and writes binary records (no printf).
//
// Emitter instance (offsets from main.bin, docs/vfx-trace.md):
//   +0x1c u32 particles emitted so far     +0x28 i32 slots in use      +0x44 f32 time    +0x48 f32 time 2
//   +0x50 .. +0x6c emission timers / scales                          +0x78 emitter set   +0xa0 emitter data (VFXB EMTR binary)
//   +0xaa u16 random-vector index    +0xac u32 random state (LCG x 0x41C64E6D + 0x3039)
//   +0xb0 particle records, 32 bytes: +0 u32 id (0 free), +8 f32 birth time, +0xc f32 life
//   +0xc0 the particle arrays of a GPU emitter; +0x1d0 a CPU emitter's (calc_type, data +0x752)
//   +0x230 i32 slots   +0x340 matrix (4 columns of 4 floats, translation at +0x370)
//   +0x3c0 previous position, +0x3d0 this frame's movement (distance emission)
//   +0x600 / +0x60c / +0x618 animated scale / rotation / translation (EAES / EAER / EAET)
// Particle arrays (16 bytes a particle each): +0x00 position (w life), +0x08 velocity (w birth time),
//   +0x10 its copy, +0x18 scale, +0x20 random, +0x28 rotation, +0x30 / +0x38 colour 0 / 1 (may be null),
//   +0x40 / +0x48 / +0x50 the emitter matrix at birth (rows).
#include <stdint.h>
#include "hook.h"

// kernel32, declared here (no windows.h needed; the same in both builds)
extern "C" {
typedef void *HANDLE;
typedef unsigned long DWORD;
struct MEMORY_BASIC_INFORMATION { void *BaseAddress, *AllocationBase; DWORD AllocationProtect; uint16_t PartitionId;
                                  uint64_t RegionSize; DWORD State, Protect, Type; };
__declspec(dllimport) HANDLE __stdcall CreateFileA(const char *, DWORD, DWORD, void *, DWORD, DWORD, HANDLE);
__declspec(dllimport) int __stdcall WriteFile(HANDLE, const void *, DWORD, DWORD *, void *);
__declspec(dllimport) int __stdcall CloseHandle(HANDLE);
__declspec(dllimport) DWORD __stdcall GetEnvironmentVariableA(const char *, char *, DWORD);
__declspec(dllimport) uint64_t __stdcall VirtualQuery(const void *, MEMORY_BASIC_INFORMATION *, uint64_t);
__declspec(dllimport) void __stdcall AcquireSRWLockExclusive(void **);
__declspec(dllimport) void __stdcall ReleaseSRWLockExclusive(void **);
__declspec(dllimport) DWORD __stdcall GetModuleFileNameA(void *, char *, DWORD);
__declspec(dllimport) int __stdcall GetModuleHandleExA(DWORD, const char *, void **);
__declspec(dllimport) int __stdcall QueryPerformanceCounter(int64_t *);
#ifdef VFX_FREESTANDING
void *memcpy(void *d, const void *s, size_t n) { char *a = (char *)d; const char *b = (const char *)s; while (n--) *a++ = *b++; return d; }
void *memset(void *d, int v, size_t n) { char *a = (char *)d; while (n--) *a++ = (char)v; return d; }
int _fltused = 0;
#else
void *memcpy(void *, const void *, size_t);
void *memset(void *, int, size_t);
#endif
}

static const uint64_t MAIN = 0x7100000000ull;
static const uint64_t A_EMITTER_FRAME = MAIN + 0x89BD0;
static const uint64_t A_PARTICLE_INIT = MAIN + 0x8FBE0;
static const uint64_t A_RANDOM_VECTORS = MAIN + 0x52A39F0;     // -> -> 512 vec4 (shape / velocity random vectors)

static const HookApi *api;
static HookOrig o_frame, o_init;
static void *g_file;
static void *g_lock;
static uint64_t g_written, g_limit = 400ull << 20;
static int g_full, g_table_done;
static char g_sets[16][48];
static int g_nsets, g_all;

// ---------------------------------------------------------------- small helpers (no CRT)
static int lower(int c) { return c >= 'A' && c <= 'Z' ? c + 32 : c; }
static int contains(const char *hay, const char *needle) {
    for (; *hay; hay++) {
        const char *h = hay, *n = needle;
        while (*n && *h && lower(*h) == lower(*n)) { h++; n++; }
        if (!*n) return 1;
    }
    return 0;
}
static void copy_name(char *dst, const char *src, int n) {
    int i = 0;
    for (; i < n - 1 && src[i] >= 0x20 && src[i] < 0x7f; i++) dst[i] = src[i];
    for (; i < n; i++) dst[i] = 0;
}
static void say(const char *a, uint64_t v = 0, int show = 0) {
    char line[200]; int n = 0;
    for (const char *p = "[vfx_trace] "; *p; p++) line[n++] = *p;
    for (; *a && n < 160; a++) line[n++] = *a;
    if (show) {
        line[n++] = ' '; line[n++] = '0'; line[n++] = 'x';
        int started = 0;
        for (int s = 60; s >= 0; s -= 4) {
            int d = (int)(v >> s) & 15;
            if (d || started || !s) { line[n++] = (char)(d < 10 ? '0' + d : 'a' + d - 10); started = 1; }
        }
    }
    line[n] = 0;
    api->log(line);
}

// ---------------------------------------------------------------- output (binary records)
static char g_buf[1 << 20];
static uint32_t g_used;
static void flush_locked() {
    if (g_used && g_file) { DWORD w = 0; WriteFile(g_file, g_buf, g_used, &w, 0); }
    g_used = 0;
}
// a record: u8 type, 3 bytes 0, u32 payload size, payload
static void put(char type, const void *a, uint32_t na, const void *b = 0, uint32_t nb = 0) {
    if (!g_file || g_full) return;
    uint32_t total = 8 + na + nb;
    if (g_used + total > sizeof g_buf || g_used > (256u << 10)) flush_locked();   // on disk every 256 KB
    char hdr[8] = {type, 0, 0, 0};
    uint32_t sz = na + nb;
    memcpy(hdr + 4, &sz, 4);
    memcpy(g_buf + g_used, hdr, 8); g_used += 8;
    memcpy(g_buf + g_used, a, na); g_used += na;
    if (nb) { memcpy(g_buf + g_used, b, nb); g_used += nb; }
    g_written += total;
    if (g_written > g_limit) { g_full = 1; flush_locked(); say("size limit reached: recording stopped"); }
}

// ---------------------------------------------------------------- which effect set an emitter belongs to
// The emitter data is the EMTR section's binary inside the loaded VFXB. Its set is the nearest ESET section
// before it whose size covers it (section: magic, u32 size, children, next, attributes, binary offset, ...);
// the set's name is at its binary + 16.
struct Known { uint64_t data; int keep; char set[64], emitter[64]; };
static Known g_known[2048];
static int g_nknown;

static int readable(uint64_t a, uint64_t *lo) {
    MEMORY_BASIC_INFORMATION mi;
    if (!VirtualQuery((const void *)(uintptr_t)a, &mi, sizeof mi)) return 0;
    if (mi.State != 0x1000) return 0;                              // MEM_COMMIT
    *lo = (uint64_t)(uintptr_t)mi.BaseAddress;
    return 1;
}
static Known *lookup(uint64_t data) {
    for (int i = 0; i < g_nknown; i++) if (g_known[i].data == data) return &g_known[i];
    if (g_nknown >= 2048) return 0;
    Known *k = &g_known[g_nknown++];
    k->data = data; k->keep = 0;
    copy_name(k->set, "?", 64);
    uint64_t lo;
    if (!data || !readable(data, &lo)) { copy_name(k->emitter, "?", 64); return k; }
    copy_name(k->emitter, (const char *)(uintptr_t)(data + 0x10), 64);
    uint64_t stop = data > (8ull << 20) ? data - (8ull << 20) : 0;
    for (uint64_t p = (data - 4) & ~3ull; p >= stop; p -= 4) {
        if (p < lo) {                                              // the previous region, if the file spans several
            uint64_t lo2;
            if (!readable(p, &lo2)) break;
            lo = lo2;
        }
        const uint32_t *w = (const uint32_t *)(uintptr_t)p;
        if (w[0] == 0x54455345u) {                                 // "ESET"
            uint32_t size = w[1], bin = w[5];
            if (p + size > data && bin < 0x1000) copy_name(k->set, (const char *)(uintptr_t)(p + bin + 16), 64);
            break;
        }
    }
    k->keep = g_all;
    for (int i = 0; i < g_nsets && !k->keep; i++) k->keep = contains(k->set, g_sets[i]);
    if (k->keep) {
        struct { uint64_t data; char set[64], emitter[64]; uint8_t calc, follow, pad[6]; } r;
        r.data = data;
        memcpy(r.set, k->set, 64); memcpy(r.emitter, k->emitter, 64);
        r.calc = *(const uint8_t *)(uintptr_t)(data + 0x752);
        r.follow = *(const uint8_t *)(uintptr_t)(data + 0x753);
        memset(r.pad, 0, 6);
        put('S', &r, sizeof r);
    }
    return k;
}

// ---------------------------------------------------------------- records
struct Arrays { uint64_t inst, arrays; };                          // the arrays an instance's particles use (from 0x8FBE0's x5)
static Arrays g_arrays[4096];
static int g_narrays;
static uint64_t arrays_of(uint64_t inst) {
    for (int i = 0; i < g_narrays; i++) if (g_arrays[i].inst == inst) return g_arrays[i].arrays;
    uint64_t data = *(const uint64_t *)(uintptr_t)(inst + 0xa0);
    return *(const uint8_t *)(uintptr_t)(data + 0x752) ? *(const uint64_t *)(uintptr_t)(inst + 0xc0) : inst + 0x1d0;
}
static void remember_arrays(uint64_t inst, uint64_t arrays) {
    for (int i = 0; i < g_narrays; i++) if (g_arrays[i].inst == inst) { g_arrays[i].arrays = arrays; return; }
    if (g_narrays < 4096) { g_arrays[g_narrays].inst = inst; g_arrays[g_narrays].arrays = arrays; g_narrays++; }
}
static void vec4(float *out, uint64_t arrays, int slot, int idx) {
    uint64_t base = *(const uint64_t *)(uintptr_t)(arrays + slot);
    if (base) memcpy(out, (const void *)(uintptr_t)(base + 16ull * idx), 16);
    else memset(out, 0, 16);
}
struct Particle {                                                  // 'P' (each frame) and 'B' (at birth)
    uint64_t inst;
    int32_t slot, number;                                          // number: its place in this emission ('B'), -1 for 'P'
    uint32_t id, pad;
    float birth, life, time;
    float pos[4], vec[4], vec2[4], scale[4], random[4], rot[4], col0[4], col1[4], m[12];
};
static void particle(char type, uint64_t inst, uint64_t arrays, int slot, int number) {
    Particle r;
    memset(&r, 0, sizeof r);
    uint64_t rec = *(const uint64_t *)(uintptr_t)(inst + 0xb0) + 32ull * slot;
    r.inst = inst; r.slot = slot; r.number = number;
    r.id = *(const uint32_t *)(uintptr_t)rec;
    r.birth = *(const float *)(uintptr_t)(rec + 8);
    r.life = *(const float *)(uintptr_t)(rec + 12);
    r.time = *(const float *)(uintptr_t)(inst + 0x44);
    vec4(r.pos, arrays, 0x00, slot); vec4(r.vec, arrays, 0x08, slot); vec4(r.vec2, arrays, 0x10, slot);
    vec4(r.scale, arrays, 0x18, slot); vec4(r.random, arrays, 0x20, slot); vec4(r.rot, arrays, 0x28, slot);
    vec4(r.col0, arrays, 0x30, slot); vec4(r.col1, arrays, 0x38, slot);
    vec4(r.m + 0, arrays, 0x40, slot); vec4(r.m + 4, arrays, 0x48, slot); vec4(r.m + 8, arrays, 0x50, slot);
    put(type, &r, sizeof r);
}
struct Emitter {                                                   // 'E'
    int64_t clock;
    uint64_t inst, data, set;
    float time, time2;
    int32_t emitted, used, slots, next;
    uint32_t rng; uint16_t vec_index, pad;
    float timers[8];                                               // +0x50 .. +0x6c
    float m[16];                                                   // +0x340 (columns)
    float prev[4], move[4];                                        // +0x3c0, +0x3d0
    float anim[9];                                                 // +0x600 scale, +0x60c rotation, +0x618 translation
    float setm[24];                                                // set +0x40 .. +0x9c (its matrix, unconfirmed)
};
static void emitter(uint64_t inst, Known *k) {
    Emitter r;
    memset(&r, 0, sizeof r);
    QueryPerformanceCounter(&r.clock);
    r.inst = inst; r.data = k->data;
    r.set = *(const uint64_t *)(uintptr_t)(inst + 0x78);
    r.time = *(const float *)(uintptr_t)(inst + 0x44);
    r.time2 = *(const float *)(uintptr_t)(inst + 0x48);
    r.emitted = *(const int32_t *)(uintptr_t)(inst + 0x1c);
    r.used = *(const int32_t *)(uintptr_t)(inst + 0x28);
    r.slots = *(const int32_t *)(uintptr_t)(inst + 0x230);
    r.next = *(const int32_t *)(uintptr_t)(inst + 0x234);
    r.rng = *(const uint32_t *)(uintptr_t)(inst + 0xac);
    r.vec_index = *(const uint16_t *)(uintptr_t)(inst + 0xaa);
    memcpy(r.timers, (const void *)(uintptr_t)(inst + 0x50), 32);
    memcpy(r.m, (const void *)(uintptr_t)(inst + 0x340), 64);
    memcpy(r.prev, (const void *)(uintptr_t)(inst + 0x3c0), 16);
    memcpy(r.move, (const void *)(uintptr_t)(inst + 0x3d0), 16);
    memcpy(r.anim, (const void *)(uintptr_t)(inst + 0x600), 36);
    if (r.set) memcpy(r.setm, (const void *)(uintptr_t)(r.set + 0x40), 96);
    put('E', &r, sizeof r);
    uint64_t arrays = arrays_of(inst);
    uint64_t recs = *(const uint64_t *)(uintptr_t)(inst + 0xb0);
    int n = r.slots < 8192 ? r.slots : 8192;
    if (!recs || !arrays) return;
    for (int i = 0; i < n; i++) {
        uint64_t rec = recs + 32ull * i;
        if (!*(const uint32_t *)(uintptr_t)rec) continue;
        float birth = *(const float *)(uintptr_t)(rec + 8), life = *(const float *)(uintptr_t)(rec + 12);
        if (r.time - birth - life > 1.0f) continue;                // dead (kept one frame past, to see the end)
        particle('P', inst, arrays, i, -1);
    }
}
static void random_table() {
    g_table_done = 1;
    uint64_t p = *(const uint64_t *)(uintptr_t)A_RANDOM_VECTORS;
    uint64_t lo;
    if (!p || !readable(p, &lo)) return;
    uint64_t t = *(const uint64_t *)(uintptr_t)p;
    if (t && readable(t, &lo)) put('T', (const void *)(uintptr_t)t, 512 * 16);
}

// ---------------------------------------------------------------- hooks
static void h_frame(Ctx *c, void *) {
    uint64_t inst = c->x[1];
    o_frame(c);
    if (!inst || g_full) return;
    AcquireSRWLockExclusive(&g_lock);
    uint64_t data = *(const uint64_t *)(uintptr_t)(inst + 0xa0);
    Known *k = data ? lookup(data) : 0;
    if (k && k->keep) {
        if (!g_table_done) random_table();
        emitter(inst, k);
    }
    ReleaseSRWLockExclusive(&g_lock);
}
static void h_init(Ctx *c, void *) {
    uint64_t inst = c->x[1], arrays = c->x[5];
    int slot = (int)(uint32_t)c->x[6], number = (int)(uint32_t)c->x[7];
    o_init(c);
    if (!(c->x[0] & 1) || !inst || g_full) return;
    AcquireSRWLockExclusive(&g_lock);
    remember_arrays(inst, arrays);
    uint64_t data = *(const uint64_t *)(uintptr_t)(inst + 0xa0);
    Known *k = data ? lookup(data) : 0;
    if (k && k->keep) particle('B', inst, arrays, slot, number);
    ReleaseSRWLockExclusive(&g_lock);
}

// ---------------------------------------------------------------- set-up
static void read_sets() {
    char v[512];
    DWORD n = GetEnvironmentVariableA("VFX_TRACE_SETS", v, sizeof v);
    if (!n || n >= sizeof v) { copy_name(g_sets[0], "PZenigame", 48); g_nsets = 1; return; }
    int i = 0;
    while (v[i] && g_nsets < 16) {
        int j = 0;
        while (v[i] && v[i] != ',' && j < 47) g_sets[g_nsets][j++] = v[i++];
        g_sets[g_nsets][j] = 0;
        if (j == 1 && g_sets[g_nsets][0] == '*') g_all = 1;
        if (j) g_nsets++;
        while (v[i] && v[i] != ',') i++;
        if (v[i] == ',') i++;
    }
}
static void open_output() {
    char path[600];
    DWORD n = GetEnvironmentVariableA("VFX_TRACE_OUT", path, 520);
    if (!n || n >= 520) {
        void *self = 0;
        GetModuleHandleExA(6, (const char *)(void *)&open_output, &self);   // FROM_ADDRESS | UNCHANGED_REFCOUNT
        n = GetModuleFileNameA(self, path, 520);
        int cut = 0;
        for (DWORD i = 0; i < n; i++) if (path[i] == '\\' || path[i] == '/') cut = (int)i + 1;
        const char *name = "vfx_trace.bin";
        int j = 0;
        while (name[j]) { path[cut + j] = name[j]; j++; }
        path[cut + j] = 0;
    }
    char mb[32];
    if (GetEnvironmentVariableA("VFX_TRACE_MB", mb, sizeof mb)) {
        uint64_t v = 0;
        for (int i = 0; mb[i] >= '0' && mb[i] <= '9'; i++) v = v * 10 + (uint64_t)(mb[i] - '0');
        if (v) g_limit = v << 20;
    }
    g_file = CreateFileA(path, 0x40000000, 1, 0, 2, 0x80, 0);          // GENERIC_WRITE, share read, CREATE_ALWAYS
    if (g_file == (void *)(intptr_t)-1) { g_file = 0; say("cannot create the output file"); return; }
    const char head[16] = {'V', 'F', 'X', 'T', 'R', 'C', '1', 0, 1, 0, 0, 0, 0, 0, 0, 0};
    DWORD w = 0;
    WriteFile(g_file, head, 16, &w, 0);
    say(path);
}

extern "C" __declspec(dllexport) void mod_init(const HookApi *a) {
    api = a;
    read_sets();
    open_output();
    int h1 = api->install(A_EMITTER_FRAME, h_frame, 0, &o_frame);
    int h2 = api->install(A_PARTICLE_INIT, h_init, 0, &o_init);
    if (!h1 || !h2) say(api->error ? api->error() : "install failed");
    say("hooks installed, emitter frame / particle init ids", (uint64_t)h1 << 32 | (uint32_t)h2, 1);
}

extern "C" int __stdcall DllMain(void *, DWORD reason, void *) {
    if (reason == 0 && g_file) {                                    // DLL_PROCESS_DETACH: write what is left
        flush_locked();
        CloseHandle(g_file);
        g_file = 0;
    }
    return 1;
}
