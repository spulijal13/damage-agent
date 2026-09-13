// Gen 9, attacker-only base-power modifiers from @smogon/calc gen789 mechanics.
// This preview excludes STAB, items, field conditions, and opponent interactions.
function abilityMovePreview(move, ability, traits = {}) {
  let type = move.type, modifier = 4096;
  const flags = traits.flags || {};
  const exceptions = ['Revelation Dance','Judgment','Nature Power','Techno Blast','Multi-Attack','Natural Gift','Weather Ball','Terrain Pulse','Struggle'];
  const canChange = !traits.isZ && !exceptions.includes(move.name);
  const ate = {Pixilate:'Fairy', Aerilate:'Flying', Refrigerate:'Ice', Galvanize:'Electric'};
  if (canChange) {
    if (ate[ability] && move.type === 'Normal') { type = ate[ability]; modifier = 4915; }
    else if (ability === 'Normalize') { type = 'Normal'; modifier = 4915; }
    else if (ability === 'Liquid Voice' && flags.sound) type = 'Water';
  }
  if (traits.isMax) modifier = 4096;
  const damaging = move.category !== 'Status' && move.basePower > 0 && !move.damage && !move.damageCallback;
  if (damaging) {
    if ((ability === 'Technician' && move.basePower <= 60 && !move.basePowerCallback) ||
        (ability === 'Mega Launcher' && flags.pulse) || (ability === 'Strong Jaw' && flags.bite) ||
        (ability === 'Sharpness' && flags.slicing) || (ability === 'Steely Spirit' && type === 'Steel')) modifier = 6144;
    if ((ability === 'Tough Claws' && flags.contact) || (ability === 'Punk Rock' && flags.sound) ||
        (ability === 'Sheer Force' && !traits.isMax && (traits.secondaries || ['Electro Shot','Order Up'].includes(move.name)))) modifier = 5325;
    if ((ability === 'Iron Fist' && flags.punch) || (ability === 'Reckless' && (traits.recoil || traits.hasCrashDamage))) modifier = 4915;
  }
  const adjustedPower = damaging && modifier !== 4096 && !move.basePowerCallback
    ? Math.max(1, Math.ceil(move.basePower * modifier / 4096 - 0.5)) : null;
  let note = type !== move.type ? `${ability}: ${move.type} → ${type}. ` : '';
  if (adjustedPower !== null) note += `${ability} power preview; excludes STAB, items, and battle conditions.`;
  else if (damaging && move.basePowerCallback && (modifier !== 4096 || ability === 'Technician')) note += 'Power depends on battle conditions; adjusted power is calculated in battle.';
  const conditional = ['Blaze','Torrent','Overgrow','Swarm','Sand Force','Flare Boost','Toxic Boost','Analytic','Rivalry','Supreme Overlord'];
  if (conditional.includes(ability)) note += `${ability} depends on battle conditions; no boost assumed here.`;
  return {type, adjustedPower, note};
}
if (typeof module !== 'undefined') module.exports = {abilityMovePreview};
