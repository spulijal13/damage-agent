const {calculate, Pokemon, Move, Field, Generations} = require("@smogon/calc");

function clean(obj) {
  return obj || {};
}

function main() {
  const input = JSON.parse(process.argv[2]);

  const gen = Generations.get(input.gen || 9);

  const attackerInput = clean(input.attacker);
  const defenderInput = clean(input.defender);
  const fieldInput = clean(input.field);

  const attacker = new Pokemon(gen, attackerInput.name, {
    level: attackerInput.level || 50,
    ability: attackerInput.ability || undefined,
    item: attackerInput.item || undefined,
    nature: attackerInput.nature || "Serious",
    evs: attackerInput.evs || {},
    ivs: attackerInput.ivs || {},
    boosts: attackerInput.boosts || {},
    status: attackerInput.status || undefined,
  });

  const defender = new Pokemon(gen, defenderInput.name, {
    level: defenderInput.level || 50,
    ability: defenderInput.ability || undefined,
    item: defenderInput.item || undefined,
    nature: defenderInput.nature || "Serious",
    evs: defenderInput.evs || {},
    ivs: defenderInput.ivs || {},
    boosts: defenderInput.boosts || {},
    status: defenderInput.status || undefined,
  });

  const move = new Move(gen, input.move);

  const field = new Field({
    gameType: fieldInput.is_double_battle === false ? "Singles" : "Doubles",
    weather: fieldInput.weather || undefined,
    terrain: fieldInput.terrain || undefined,
    isReflect: fieldInput.reflect || false,
    isLightScreen: fieldInput.light_screen || false,
    isAuroraVeil: fieldInput.aurora_veil || false,
  });

  const result = calculate(gen, attacker, defender, move, field);

  const damage = Array.isArray(result.damage) ? result.damage : [result.damage];

  console.log(JSON.stringify({
    attacker: attacker.name,
    defender: defender.name,
    move: move.name,
    damage: damage,
    min_damage: Math.min(...damage),
    max_damage: Math.max(...damage),
    description: result.desc(),
    full_description: result.fullDesc(),
    range: result.range(),
  }, null, 2));
}

try {
  main();
} catch (err) {
  console.error(JSON.stringify({
    error: err.message,
    stack: err.stack,
  }, null, 2));
  process.exit(1);
}