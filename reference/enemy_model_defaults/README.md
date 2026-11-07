# Model-folder defaults for the converted Smash Run enemies

`tools/s3ds_enemy.py` writes these into every converted enemy model folder (`model/enemy/KIND/PART/cNN/`):

- `model.sb` (12 bytes, `' BWS'`, no swing bones) and `model.nhb` (64 bytes, `' BHN'`, no helper bones): the
  empty files the Ultimate fighter ports use (Cloud's / Kirby's, docs/ultimate-fighter-port.md). The model loader
  (0x0330466C, file slots 4 / 5) copies them to the model's +0x6FC / +0x700 (0x034205FC); a model instance makes
  its helper object (+0x20, 0x03327448 in 0x0330DE5C) only when one of them exists, and the bone-matrix getter
  0x0331915C (the motion module's node matrices, 0x02C64588, asked for by the enemy model module 0x02DA7A10 when
  an effect or hitbox follows a node) reads it unchecked: without them the game crashes once an enemy's
  effect / attack asks for a bone (Smash Run step 2a, Cemu log IP 0x03319218).
- `model.xmb`: a fighter body's (type fighter, light set 0, shadow caster, object type 1, main + normal-map
  draws). Without a model.xmb the enemies drew black.
