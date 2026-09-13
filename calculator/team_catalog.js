// Reference choices only; this is not a learnset or format-legality validator.
const {Generations} = require('@smogon/calc');
const gen = Generations.get(9);
console.log(JSON.stringify({
  moves: [...gen.moves].map(x => x.name).sort(),
  items: [...gen.items].map(x => x.name).sort(),
  natures: [...gen.natures].map(({name, plus, minus}) => ({name, plus, minus})),
}));
