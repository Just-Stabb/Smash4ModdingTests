#!/usr/bin/env python3
"""Writes SM4SHCommand/AnimNames.txt: standard Smash 4 animation names Sm4shCommand recognises.

  python3 make_anim_names.py

Scripts are stored by the CRC32 of their lower-case animation name, so a name only shows for a script
whose hash matches it; extra names cost nothing. The list is a base vocabulary plus common suffixes
(_c2/_c3 camera variants, l/r, start/loop/end, ...) and specialair* forms of the special names. Checked
on Kirby, Captain Falcon and Bowser: it names roughly half of each fighter's game.bin scripts; the rest
(copy abilities, subroutines) need Tools > Parse Animations or right-click > Set Name, which add to the
file. Running this again replaces those additions, so copy them first if you want to keep them.
"""
import os

BASE = """wait wait1 wait2 wait3 wait4 waititem walkslow walkmiddle walkfast walkbrake walk dash run runbrake turn turnrun turnrunbrake turndash
jumpsquat jumpf jumpb jumpfmini jumpbmini jumpaerialf jumpaerialb fallf fallb fall fallaerial fallaerialf fallaerialb fallspecial fallspecialf fallspecialb
landingheavy landinglight landingfallspecial landingairn landingairf landingairb landingairhi landingairlw landingair stepjump stepback stepfall steppose
squat squatwait squatrv squatwalkf squatwalkb squatf squatb squatwaitlr passive passivewallf passivewallb passivewalljump passiveceil passivestandf passivestandb passivewalljumpb
guardon guard guardoff guarddamage escapen escapef escapeb escapeair escapeairslide
attack11 attack12 attack13 attack100 attack100start attack100end attack100sub attackdash attacks3 attacks3hi attacks3s attacks3lw attackhi3 attacklw3 attacks4 attacks4hi attacks4s attacks4lw attacks4charge attacks4start attackhi4 attackhi4charge attackhi4start attacklw4 attacklw4charge attacklw4start
attackairn attackairf attackairb attackairhi attackairlw
catch catchdash catchturn catchwait catchattack catchcut catchpull catchdashpull catchturnpull throwf throwb throwhi throwlw
capturepulledhi capturepulledlw capturewaithi capturewaitlw capturedamagehi capturedamagelw capturecut capturejump captureattack
throwndashf throwndashb thrownf thrownb thrownhi thrownlw thrownfb thrownff thrownfhi thrownflw throwndx throwndxb throwndxf
damagehi1 damagehi2 damagehi3 damagen1 damagen2 damagen3 damagelw1 damagelw2 damagelw3 damageair1 damageair2 damageair3 damageelec damageflyhi damageflyn damageflylw damageflytop damageflyroll damagefallhi damagefall damageflymeteor
downbounddu downbounddd downwaitu downwaitd downstandu downstandd downattacku downattackd downforwardu downforwardd downbacku downbackd downdamageu downdamaged downdamageu3 downdamaged3 downeatu downeatd downspotu downspotd
cliffcatch cliffwait cliffclimbquick cliffclimbslow cliffattackquick cliffattackslow cliffescapequick cliffescapeslow clifjumpquick1 cliffjumpquick1 cliffjumpquick2 cliffjumpslow1 cliffjumpslow2 cliffcatchmove
appealhir appealhil appealsr appealsl appeallwr appeallwl appealhi appeals appeallw
win1 win1wait win2 win2wait win3 win3wait lose entryr entryl entry
itempickuplight itempickupheavy itemthrowf itemthrowb itemthrowhi itemthrowlw itemthrowdash itemthrowairf itemthrowairb itemthrowairhi itemthrowairlw itemheavythrowf itemheavythrowb itemheavythrowhi itemheavythrowlw itemlightpickup itemheavypickup
itemswingup itemswings1 itemswings3 itemswings4 itemswings4start itemswings4hold itemswinghi4 itemswinglw4 itemswingdash itemscrewjump itemscrewjumpaerial itemscrewfall itemshootwait itemshootwalkf itemshootwalkb itemshootair
swim swimrise swimup swimend swimturn swimdrown swimdrownout ladderwait ladderup ladderdown laddercatchl laddercatchr ladderend
dead deadupfall deadupstar deadupstarfall rebirth sleep sleepstart sleepend furafura furafuraend furafurastartu furafurastartd furasleepstart furasleeploop furasleepend stun stunstart stunend
finalready final finalair finalend finalstart finalloop finalairstart finalairend glide glidestart glideend glidewing glideland glideattack
specialn specialnstart specialnloop specialnend specialnhold specialncancel specialnhit specialncharge specialnmax specialnshoot specialnfire specialnturn specialnjump specialnfall specialnland specialnwait specialnswallow specialnspit specialnspitwait specialndrink specialnwalk specialnwalkf specialnwalkb specialnloopwait specialnswallowwait specialnthrow specialnthrowf specialnthrowb specialnthrowhi specialnthrowlw specialnstartup specialnstartdown specialnwaitstart specialnloopstart specialnspitend specialnswallowend specialnstartloop specialnstartend specialnsearch specialnsearchturn
specials specialsstart specialsend specialshold specialsloop specialscharge specialsmax specialsmaxs specialsmaxe specialsswing specialsholdwait specialsholdwalk specialsholdturn specialsholdjumpsquat specialsholdjump specialsholdfall specialsholdlanding specialsholdpass specialsloopstart specialswait specialsjump specialslanding specialsdash specialsattack specialshit specialscancel specialscatch specialsthrow specialsfall
specialhi specialhistart specialhiend specialhifall specialhifall2 specialhilanding specialhiloop specialhijump specialhihold specialhicharge specialhiattack specialhiwait specialhi1 specialhi2 specialhi3 specialhi4
speciallw speciallwstart speciallwend speciallwloop speciallwhold speciallwfall speciallwlanding speciallwwait speciallwhit speciallwattack speciallwcharge speciallwstone speciallwturn
heavyitemwait heavyitemwalk heavyitemwalkf heavyitemturn heavyitemthrow
"""

SUFFIXES = ("_c2", "_c3", "l", "r", "f", "b", "1", "2", "3", "4", "s", "e", "start", "end", "loop", "wait")


def names():
    c = set(BASE.split())
    for w in list(c):
        if w.startswith("special") and not w.startswith("specialair"):
            c.add("specialair" + w[7:])
    for w in list(c):
        for suf in SUFFIXES:
            c.add(w + suf)
    for i in range(1, 8):
        c.add("jumpaerialf%d" % i)
        c.add("jumpaerialb%d" % i)
    return sorted(c)


def main():
    out = [
        "// Script names Sm4shCommand recognises: one animation name per line (its CRC32 is the script hash).",
        "// A name only shows for a script whose hash matches it, so extra names do no harm.",
        "// \"0xHASH = label\" gives a hash whose real name isn't known a label of your own.",
        "// Tools > Parse Animations and right-click > Set Name add to the end of this file.",
    ] + names()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SM4SHCommand", "AnimNames.txt")
    open(path, "w", newline="\r\n").write("\n".join(out) + "\n")
    print("%d names -> %s" % (len(out) - 4, path))


if __name__ == "__main__":
    main()
