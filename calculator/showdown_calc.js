const {calculate, Pokemon, Move, Field, Generations} = require("@smogon/calc");

function mergedData(primary, fallback) {
  return {
    get(id) { return primary.get(id) || fallback.get(id); },
    *[Symbol.iterator]() {
      const seen = new Set();
      for (const value of primary) { seen.add(value.id); yield value; }
      for (const value of fallback) if (!seen.has(value.id)) yield value;
    },
  };
}

function championsGeneration() {
  const champions = Generations.get(0);
  const standard = Generations.get(9);
  // The official Champions dataset currently contains the Champions roster,
  // while this app also accepts other calculator-supported species. Prefer all
  // Champions data and mechanics, falling back to Gen 9 only for missing data.
  return {
    num: 0,
    abilities: mergedData(champions.abilities, standard.abilities),
    items: mergedData(champions.items, standard.items),
    moves: mergedData(champions.moves, standard.moves),
    species: mergedData(champions.species, standard.species),
    types: mergedData(champions.types, standard.types),
    natures: mergedData(champions.natures, standard.natures),
  };
}

function clean(obj) {
  return obj || {};
}

function prepareBattle(input, maximumHits = false) {
  // Generation 0 is @smogon/calc's Pokémon Champions ruleset. Do not use ||
  // here because 0 is the intended default rather than a missing value.
  const generation = input.gen ?? 0;
  const gen = generation === 0 ? championsGeneration() : Generations.get(generation);

  const attackerInput = clean(input.attacker);
  const defenderInput = clean(input.defender);
  const fieldInput = clean(input.field);

  function makePokemon(data) {
    const id = String(data.name || "").toLowerCase().replace(/[^a-z0-9]/g, "");
    if (!gen.species.get(id)) throw new Error(`Unknown Pokemon: ${data.name}`);
    if (data.grounded !== undefined) {
      throw new Error("Explicit grounded overrides are unsupported; omit grounded to infer it from typing, ability, and item.");
    }
    const natureName = data.nature || "Serious";
    const natureId = natureName.toLowerCase().replace(/[^a-z0-9]/g, "");
    const nature = gen.natures.get(natureId);
    if (!nature) throw new Error(`Unknown nature: ${natureName}`);
    const options = {
      level: data.level ?? 50,
      ability: data.ability || undefined,
      item: data.item || undefined,
      nature: nature.name,
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
  const move = new Move(gen, moveData.name, {
    isCrit: !!fieldInput.critical, ability: attacker.ability, item: attacker.item,
    ...(maximumHits && Array.isArray(moveData.multihit) ? {hits: moveData.multihit[1]} : {}),
  });

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

  return {gen, attacker, defender, move, field};
}

function calculateBattle(input) {
  const {gen, attacker, defender, move, field} = prepareBattle(input);
  const result = calculate(gen, attacker, defender, move, field);

  const damage = Array.isArray(result.damage) ? result.damage : [result.damage];

  return {
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
  };
}


try {
  const input = JSON.parse(process.argv[2]);
  const result = input.operation === "survival" ? require('./bulk_planner').optimize(input, prepareBattle) : calculateBattle(input);
  console.log(JSON.stringify(result));
} catch (err) {
  console.error(JSON.stringify({
    error: err.message,
    stack: err.stack,
  }, null, 2));
  process.exit(1);
}
