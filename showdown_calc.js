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

  function makePokemon(data) {
    const id = String(data.name || "").toLowerCase().replace(/[^a-z0-9]/g, "");
    if (!gen.species.get(id)) throw new Error(`Unknown Pokemon: ${data.name}`);
    if (data.grounded !== undefined) {
      throw new Error("Explicit grounded overrides are unsupported; omit grounded to infer it from typing, ability, and item.");
    }
    const options = {
      level: data.level ?? 50,
      ability: data.ability || undefined,
      item: data.item || undefined,
      nature: data.nature || "Serious",
      evs: data.evs || {}, ivs: data.ivs || {}, boosts: data.boosts || {},
      status: data.status || undefined,
    };
    const pokemon = new Pokemon(gen, data.name, options);
    const percent = data.current_hp_percent ?? 100;
    if (typeof percent !== "number" || !Number.isFinite(percent) || percent <= 0 || percent > 100) {
      throw new Error("current_hp_percent must be greater than 0 and at most 100.");
    }
    return new Pokemon(gen, data.name, {
      ...options, curHP: Math.max(1, Math.floor(pokemon.maxHP() * percent / 100)),
    });
  }
  const attacker = makePokemon(attackerInput);
  const defender = makePokemon(defenderInput);
  const moveId = String(input.move || "").toLowerCase().replace(/[^a-z0-9]/g, "");
  const moveData = gen.moves.get(moveId);
  if (!moveData) {
    throw new Error(`Unknown move: ${input.move}. Please restate your battle question with the intended move's full name.`);
  }
  const move = new Move(gen, moveData.name, {isCrit: !!fieldInput.critical});

  const field = new Field({
    gameType: fieldInput.is_double_battle === false ? "Singles" : "Doubles",
    weather: fieldInput.weather || undefined,
    terrain: fieldInput.terrain || undefined,
    defenderSide: {
      isReflect: !!fieldInput.reflect,
      isLightScreen: !!fieldInput.light_screen,
      isAuroraVeil: !!fieldInput.aurora_veil,
    },
  });

  const result = calculate(gen, attacker, defender, move, field);

  const damage = Array.isArray(result.damage) ? result.damage : [result.damage];

  console.log(JSON.stringify({
    attacker: attacker.name,
    defender: defender.name,
    move: move.name,
    damage: damage,
    min_damage: result.range()[0],
    max_damage: result.range()[1],
    defender_hp: defender.maxHP(),
    defender_current_hp: defender.curHP(),
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