// Names only, using the same Champions + generation-9 fallback as damage calculation.
const {Generations} = require('@smogon/calc');
const generations = [Generations.get(0), Generations.get(9)];
console.log(JSON.stringify(Object.fromEntries(
  ['moves', 'items', 'abilities', 'natures'].map(kind => [kind,
    [...new Set(generations.flatMap(gen => [...gen[kind]].map(value => value.name)))].sort(),
  ])
)));
