# Custom effects for new fighters

Fully custom effects (our own emitters, textures and effect models) in a new fighter's own effect
bank (`fighter/<name>/effect/<name>/`: `.efc` effect list, `.ptcl` particles (EFTF), `model/Eff*`
effect models; ACMD ids `0x3KKnnnnn`, Supamario `0x341`). Format research in progress: the `.ptcl`
(EFTF) reader / writer and the `.efc` + effect models.

## First: Supamario's Kamehameha

Look (user): **blue, like the original** (Dragon Ball's): a near-white core with a cyan to deep blue
glow around it.
- Charge: a blue energy orb between the hands, growing, with small sparks drawn inward and a soft
  blue glow; white-hot centre.
- Beam: an effect model (a cylinder / tapered beam with a scrolling energy texture: white core, cyan
  edge, blue falloff, additive) from the hands forward, with a wider glow sheath and particles
  streaming along it; a bulbous head at the front.
- Impact: a blue-white burst with a shockwave ring and scattered sparks.

Plan: a small self-authored test effect first (prove the chain in game), then the three parts, then
the move (animations, ACMD hitboxes, MSC charge logic).
