const assert = require('node:assert/strict');
const {Generations, Pokemon} = require('@smogon/calc');
const {level50Stat} = require('../public/team-stats');
const gen = Generations.get(9);
for (const name of ['Pikachu', 'Charizard-Mega-Y', 'Shedinja']) {
  for (const nature of gen.natures) {
    for (const points of [0, 1, 17, 32]) {
      const evs = Object.fromEntries(['hp','atk','def','spa','spd','spe'].map(s=>[s, points ? points*8-4 : 0]));
      const p = new Pokemon(gen, name, {level:50, nature:nature.name, evs});
      for (const stat of Object.keys(evs)) {
        assert.equal(level50Stat(p.species.baseStats[stat],stat,points,nature), p.rawStats[stat], `${name} ${nature.name} ${stat} ${points}`);
      }
    }
  }
}
console.log('1,800 level-50 stat comparisons against Smogon passed.');
