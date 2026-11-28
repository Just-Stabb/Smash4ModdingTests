/* The code cave's home: zeros in this plugin's .text, so it is in memory the plugin's own code runs from
 * (executable, below 0x02000000 where the game's absolute branches reach it). The game also writes data the patch
 * keeps in the cave (the random pools, Kirby's copy table, the new characters' records): this relies on Aroma's
 * plugin memory being writable as well (see ../README.md, "Not confirmed on a console"). */
#ifndef CAVE_KB
#define CAVE_KB 1024
#endif
    .section .text.s4ct_cave, "ax", @progbits
    .balign 256
    .global s4ct_cave
s4ct_cave:
    .space (CAVE_KB * 1024 + 0x10000)
    .global s4ct_cave_end
s4ct_cave_end:
