// Reference choices only; this is not a learnset or format-legality validator.
const {Generations, Move} = require('@smogon/calc');
const gen = Generations.get(9);
console.log(JSON.stringify({
  moves: [...gen.moves].map(x => x.name).sort(),
  move_traits: Object.fromEntries([...gen.moves].map(data => {
    const move = new Move(gen, data.name);
    return [data.id, {flags: move.flags, secondaries: !!move.secondaries, recoil: !!move.recoil, hasCrashDamage: move.hasCrashDamage, isZ: move.isZ, isMax: move.isMax}];
  })),
  items: [...gen.items].map(x => x.name).sort(),
  natures: [...gen.natures].map(({name, plus, minus}) => ({name, plus, minus})),
}));
