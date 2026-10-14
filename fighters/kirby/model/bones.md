# Kirby bones (`model.vbn`)

Generated with `python3 tools/vbn_bones.py fighters/kirby/model/model.vbn`. The index is the bone number `ModelModule` takes, e.g. `ModelModule(0x1, 0xE, x, y, z)` rotates `LShoulderJ`.

| Index | Bone | Parent |
|---|---|---|
| 0x0 | TransN | - |
| 0x1 | RotN | TransN |
| 0x2 | HipN | RotN |
| 0x3 | LLegJ | HipN |
| 0x4 | LKneeJ | LLegJ |
| 0x5 | LFootJ | LKneeJ |
| 0x6 | LToeN | LFootJ |
| 0x7 | RLegJ | HipN |
| 0x8 | RKneeJ | RLegJ |
| 0x9 | RFootJ | RKneeJ |
| 0xA | RToeN | RFootJ |
| 0xB | WaistN | HipN |
| 0xC | BustN | WaistN |
| 0xD | LShoulderN | BustN |
| 0xE | LShoulderJ | LShoulderN |
| 0xF | LArmJ | LShoulderJ |
| 0x10 | LHandN | LArmJ |
| 0x11 | RShoulderN | BustN |
| 0x12 | RShoulderJ | RShoulderN |
| 0x13 | RArmJ | RShoulderJ |
| 0x14 | RHandN | RArmJ |
| 0x15 | NeckN | BustN |
| 0x16 | HeadN | NeckN |
| 0x17 | RHaveN | RHandN |
| 0x18 | LHaveN | LHandN |
| 0x19 | ThrowN | RotN |
| 0x1A | BodyBN | BustN |
| 0x1B | MouthN | BodyBN |
| 0x1C | MouthL1stN | MouthN |
| 0x1D | MouthR1stN | MouthN |
| 0x1E | MouthL2ndN | MouthN |
| 0x1F | MouthR2ndN | MouthN |
| 0x20 | MouthL3rdN | MouthN |
| 0x21 | MouthR3rdN | MouthN |
| 0x22 | MouthL4thN | MouthN |
| 0x23 | MouthR4thN | MouthN |
| 0x24 | MouthL5rdN | MouthN |
| 0x25 | MouthR5rdN | MouthN |
| 0x26 | MouthShitaN | MouthN |
| 0x27 | MouthShitaNb | MouthShitaN |
| 0x28 | CheekN | MouthN |
| 0x29 | HukumiN | MouthN |

Arms: `LShoulderJ` 0xE → `LArmJ` 0xF → `LHandN` 0x10 (→ `LHaveN` 0x18), and `RShoulderJ` 0x12 → `RArmJ` 0x13 → `RHandN` 0x14 (→ `RHaveN` 0x17).

At rest each shoulder's local X runs along the arm, local Z is vertical and local Y points forward, so a Y rotation swings the arm up/down. The left and right sides are mirrored: +Y raises the left arm and lowers the right.
