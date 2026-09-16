const {calculate, Pokemon, Move, Field, Generations} = require("@smogon/calc");

function clean(obj) {
  return obj || {};
}

function prepareBattle(input) {
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

function optimizeSurvival(input) {
  const prepared = input.battles.map(prepareBattle);
  const {gen, defender: base} = prepared[0];
  for (const battle of prepared) {
    if (battle.move.category === "Status" || ["Fissure", "Guillotine", "Horn Drill", "Sheer Cold"].includes(battle.move.name)) {
      throw new Error("Choose direct damaging moves for survival optimization.");
    }
  }
  const individual = prepared.map(() => null);
  let minimum = null, fullBudget = null, reference = null;
  const pointsToEVs = p => p > 0 ? 8 * p - 4 : 0;
  const score = stats => (input.bias / stats.def + 1 / stats.spd) / stats.hp;
  const better = (candidate, current) => !current || candidate.score < current.score;
  function evaluate(points) {
    const defender = new Pokemon(gen, base.name, {
      ...input.battles[0].defender,
      evs: {...base.evs, hp: pointsToEVs(points[0]), def: pointsToEVs(points[1]), spd: pointsToEVs(points[2])},
    });
    const currentHP = Math.max(1, Math.floor(defender.maxHP() * input.current_hp_percent / 100));
    defender.originalCurHP = currentHP;
    const reports = prepared.map((battle, index) => {
      const hits = input.hits[index];
      function sequence(maximum) {
        let hp = currentHP;
        const rolls = [];
        for (let hit = 0; hit < hits && hp > 0; hit++) {
          const target = defender.clone(); target.originalCurHP = hp;
          const range = calculate(gen, battle.attacker, target, battle.move, battle.field).range();
          const damage = range[maximum ? 1 : 0];
          rolls.push(damage); hp -= damage;
        }
        return {hp, rolls, damage: rolls.reduce((a,b) => a+b, 0)};
      }
      const worst = sequence(true), best = sequence(false);
      return {attacker: battle.attacker.name, move: battle.move.name, hits,
        min_damage: best.damage, max_damage: worst.damage, max_rolls: worst.rolls,
        starting_hp: currentHP, remaining_hp: Math.max(0, worst.hp), survives: worst.hp > 0};
    });
    const stats = {hp: defender.maxHP(), def: defender.rawStats.def, spd: defender.rawStats.spd};
    return {points, total: points.reduce((a,b) => a+b, 0), stats, score: score(stats), reports};
  }
  for (let total = 0; total <= input.budget; total++) {
    // Once the joint minimum is known, only the full-budget optimum remains.
    if (minimum && total > minimum.total && total < input.budget) continue;
    for (let hp = 0; hp <= Math.min(32, total); hp++) {
      for (let def = 0; def <= Math.min(32, total-hp); def++) {
        const spd = total-hp-def;
        if (spd < 0 || spd > 32) continue;
        if (Object.entries(input.locked).some(([stat, value]) => ({hp, def, spd})[stat] !== value)) continue;
        const candidate = evaluate([hp, def, spd]);
        if (total === input.budget && better(candidate, reference)) reference = candidate;
        candidate.reports.forEach((report, i) => {
          if (report.survives && (!individual[i] || (individual[i].total === total && better(candidate, individual[i])))) {
            individual[i] = candidate;
          }
        });
        if (candidate.reports.every(report => report.survives)) {
          if ((!minimum || minimum.total === total) && better(candidate, minimum)) minimum = candidate;
          if (total === input.budget && better(candidate, fullBudget)) fullBudget = candidate;
        }
      }
    }
  }
  return {minimum, full_budget: fullBudget, individual, reference};
}

try {
  const input = JSON.parse(process.argv[2]);
  const result = input.operation === "survival" ? optimizeSurvival(input) : calculateBattle(input);
  console.log(JSON.stringify(result));
} catch (err) {
  console.error(JSON.stringify({
    error: err.message,
    stack: err.stack,
  }, null, 2));
  process.exit(1);
}