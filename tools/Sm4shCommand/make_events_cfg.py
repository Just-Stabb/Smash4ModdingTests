#!/usr/bin/env python3
"""Writes SM4SHCommand/Events.cfg from SALT's built-in command table (SALT/SALT/Scripting/AnimCMD/CMD_INFO.cs).

  python3 make_events_cfg.py

The old Events.cfg shipped with Sm4shCommand was older than SALT's table and, since it's loaded on top
of it at startup, it replaced SALT's hitbox definitions with outdated ones (Unknown fields, X/Z
swapped). Run this after updating CMD_INFO.cs. Same format as ACMD_INFO.SaveInfo (what Tools > Command
Definitions saves).
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "SALT", "SALT", "Scripting", "AnimCMD", "CMD_INFO.cs")
DST = os.path.join(HERE, "SM4SHCommand", "Events.cfg")
LABELS = os.path.join(HERE, "param_labels.json")   # the parameter research (apply_param_labels.py)


def one_line(t):
    return " ".join(str(t).split())


def param_lines(entry, names):
    """"Param: Name = description" lines for a command's labelled parameters"""
    out = []
    for k, p in sorted(((int(k), v) for k, v in entry.items() if not k.startswith("_")), key=lambda kv: kv[0]):
        if k >= len(names) or not p.get("desc"):
            continue
        extra = "; ".join(x for x in (p.get("values") and "values: %s" % one_line(p["values"]),
                                       p.get("confidence") and "confidence: %s" % p["confidence"]) if x)
        out.append("Param: %s = %s%s" % (names[k], one_line(p["desc"]), " [%s]" % extra if extra else ""))
    return out


# Command groups for the command list (View > Commands). A command takes the first
# group whose pattern matches its name, else its real name (from _desc_extra), else, for the unk_
# commands, its research note (_note: the module its handler calls).
CATEGORIES = [
    ("Script flow & timing", r"^Thread_|^(FRAME|FRAME_\w+|WAIT|WAIT_LOOP\w*|LOOP|Loop_Rest|Set_Loop|IF|ELIF|ELSE|Else|ENDIF|SWITCH|CASE|DEFAULT|"
     r"ENDSWITCH|Goto|CALL|JUMP|Script_End|END|EXECUTE|NOP|True|False|Is_Bool|Is_Not_Bool|IS_RANDOM|"
     r"Set_Frame_Duration|Set_Frame_Speed|POOL)$"),
    ("Variables & compares", r"^(SET_INT|ADD_INT|INC_INT|SET_FLOAT|ADD_FLOAT|SUB_FLOAT\w*|ON_FLAG|OFF_FLAG|IS_FLAG)$|"
     r"^(?i:int|float)_\w*(?i:compare)|_VAR_COMPARE|COMPARE_VAR"),
    ("Item scripts (IT_)", r"^IT_"),
    ("Hitboxes", r"Hitbox|^ATTACK_(?!SE(_\d)?$)|^ATK_|^HIT_STOP_MUL$|^SET_ATTACK_HIT_STOP$|^INFLICTION_OFF$|^Set_Weight_"),
    ("Grabs & throws", r"Grab_Collision|Throw_(Specifier|Applier)|^FT_CATCH|^CTH_"),
    ("Search boxes, areas & shields", r"^Search_Collision$|^SCH_|^SEARCH_|^SET_SEARCH|AREA|Wind_Effect|^REFLECTOR$|^SHIELD_|^Shield_"),
    ("Hurtboxes & body", r"^Body_Collision$|Intangibility|Bone_Collision|^Set_Armor$|^COL_PRI$"),
    ("Trails & sword glow", r"AFTER_IMAGE|Sword_(Glow|Trace)"),
    ("Lights, flashes & overlays", r"FLASH|Flash|LIGHT|Overlay|Screen_Tint|GOLD_EYE|_CHARGE"),
    ("Effects", r"EFFECT|Graphic|PARTICLE|^EM_"),
    ("Sound", r"(^|_)SE(_|$)|Sound|SOUND|Voice|VOICE|PITCH|VOLUME|BGM|SEQUENCE|^PLAY_|^IS_PLAYING|INHIVIT"),
    ("Camera, quake & rumble", r"CAM|Camera|QUAKE|Rumble|RUMBLE|SCROLL"),
    ("Slowdown", r"Time_Manipulation"),
    ("Traces & targeting", r"TRACE|TEAM_OWNER|^SET_CURSOR$|^Track_"),
    ("Animation, model & visibility", r"^MOT_|Model|Morph|^VIS_|Visibility|SHADOW|MATERIAL|^MII_|^STRANS"),
    ("Articles (projectiles)", r"ARTICLE|Article"),
    ("Items", r"(?i:item)|^Fire_Weapon$|BULLET"),
    ("Movement & physics", r"Momentum|Movements|SPEED|ENERGY|Kinetic|KINETIC|^SET_AIR$|Direction|^TURN_|ROT$|^STICK_LR|"
     r"^SET_LR$|Ledgegrab|Edge_Slide|GROUND|BOX2D|PASSABLE|RHOMBUS|SLOPE|Slope|POS|^FT_MOTION_ANGLE$"),
]
NOTE_CATEGORIES = [                          # for unk_ commands: words in the research note
    ("Hitboxes", r"AttackModule|hitbox"), ("Grabs & throws", r"\bthrow|catch"),
    ("Trails & sword glow", r"trail|after.?image|sword"), ("Lights, flashes & overlays", r"\blight|flash|colou?r"),
    ("Effects", r"EffectModule|effect"), ("Sound", r"SoundModule|\bSE\b|sound|BGM"),
    ("Camera, quake & rumble", r"camera|quake|rumble"), ("Articles (projectiles)", r"article"),
    ("Items", r"\bitem"), ("Search boxes, areas & shields", r"AreaModule|search|shield"),
    ("Movement & physics", r"Kinetic|Physics|speed|Posture|ground|energy|position"),
    ("Animation, model & visibility", r"Motion|model|visib|ModelModule"),
    ("Variables & compares", r"WorkModule|variable|compare"), ("Traces & targeting", r"trace"),
    ("Fighter-specific", r"fighter.(specific )?(op|command)|fighter-specific|fighter op"),
]


def category(name, entry):
    for text in (None if name.startswith("unk_") else name,
                 re.sub(r"^\(Real name: (\S+).*", r"\1", entry.get("_desc_extra", "")) or None):
        if text:
            for cat, pat in CATEGORIES:
                if re.search(pat, text):
                    return cat
    for cat, pat in NOTE_CATEGORIES:
        if re.search(pat, entry.get("_note", ""), re.I):
            return cat
    if any(v.get("name") == "Graphic" for k, v in entry.items() if not k.startswith("_")):
        return "Effects"
    return "Other"


def table(text, name):
    i = text.index("Dictionary<uint, %s> %s" % ("int" if name == "CMD_SIZES" else "string", name))
    j = text.index("};", i)
    body = text[i:j]
    if name == "CMD_SIZES":
        return {int(k, 16): int(v) for k, v in re.findall(r"\{\s*0x([0-9A-Fa-f]+)\s*,\s*(\d+)\s*\}", body)}
    return {int(k, 16): v for k, v in re.findall(r'\{\s*0x([0-9A-Fa-f]+)\s*,\s*"((?:[^"\\]|\\.)*)"\s*\}', body)}


def main():
    text = open(SRC, encoding="utf-8-sig").read()
    names, fmt, syn, desc = (table(text, n) for n in ("CMD_NAMES", "PARAM_FORMAT", "PARAM_SYNTAX", "CMD_DESC"))
    labels = {int(k, 16): v for k, v in json.load(open(LABELS)).items()} if os.path.exists(LABELS) else {}
    sizes = table(text, "CMD_SIZES")
    out = [
        "// Sm4shCommand ACMD command definitions. Read at startup on top of the built-in ones.",
        "// One block per command, blocks separated by a blank line:",
        "//   identifier (hex CRC32 of the command)",
        "//   name",
        "//   parameter types, comma separated: 0 int, 1 float, 2 decimal, 3 variable (or NONE)",
        "//   parameter names, comma separated (or NONE)",
        "//   description shown in tooltips (optional; NONE = no description)",
        "//   Category: group   (optional: the command list's group, View > Commands)",
        "//   Param: Name = description   (optional, one line per parameter, also shown in tooltips)",
        "// Lines starting with // are comments. Tools > Command Definitions edits this file.",
    ]
    for crc, name in sorted(names.items(), key=lambda kv: kv[1].upper()):
        f = fmt.get(crc, "NONE") or "NONE"
        s = syn.get(crc, "NONE") or "NONE"
        # The size is what the parser trusts; the file stores it as (parameter count + 1). Pad a
        # definition whose list is shorter than its size (Intensity_Special_Hitbox: size 48, 46 listed).
        want = sizes.get(crc, 1) - 1
        have = 0 if f == "NONE" else len(f.split(","))
        if want > have:
            f = ",".join(([] if f == "NONE" else f.split(",")) + ["0"] * (want - have))
            s = ",".join(([] if s == "NONE" else s.split(",")) + ["Unknown"] * (want - have))
        if f == "NONE":
            s = "NONE"
        elif s == "NONE" or len(s.split(",")) != len(f.split(",")):
            n = len(f.split(","))
            have = [] if s == "NONE" else s.split(",")
            s = ",".join((have + ["Unknown"] * n)[:n])
        d = desc.get(crc, "NONE").replace('\\"', '"') or "NONE"
        entry = labels.get(crc, {})
        if d == "NONE" and entry.get("_note"):
            d = one_line(entry["_note"])
        if entry.get("_desc_extra"):                  # e.g. the command's real (hash-verified) name
            d = one_line(entry["_desc_extra"]) if d == "NONE" else "%s %s" % (d, one_line(entry["_desc_extra"]))
        out += ["", "%08X" % crc, name, f, s, d, "Category: " + category(name, entry)]
        out += param_lines(entry, [] if s == "NONE" else s.split(","))
    open(DST, "w", newline="\r\n").write("\n".join(out) + "\n")
    print("%d commands -> %s" % (len(names), DST))


if __name__ == "__main__":
    main()
