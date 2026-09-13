const assert = require('node:assert/strict');
const {Move, Generations} = require('@smogon/calc');
const moves = require('../data/moves.json');
const {abilityMovePreview} = require('../public/move-abilities');
const gen = Generations.get(9);
function preview(name, ability) {
  const move = moves[name.toLowerCase().replace(/[^a-z0-9]/g,'')];
  return abilityMovePreview(move, ability, new Move(gen,name));
}
assert.equal(preview('Hyper Voice','Pixilate').type,'Fairy');
assert.equal(preview('Hyper Voice','Pixilate').adjustedPower,108);
assert.equal(preview('Hyper Voice','Liquid Voice').type,'Water');
assert.equal(preview('Hyper Voice','Liquid Voice').adjustedPower,null);
assert.equal(preview('Quick Attack','Technician').adjustedPower,60);
assert.equal(preview('Thunderbolt','Technician').adjustedPower,null);
assert.equal(preview('Ice Punch','Iron Fist').adjustedPower,90);
assert.equal(preview('Bite','Strong Jaw').adjustedPower,90);
assert.equal(preview('Air Slash','Sharpness').adjustedPower,112);
assert.equal(preview('Thunderbolt','Sheer Force').adjustedPower,117);
assert.equal(preview('Protect','Pixilate').adjustedPower,null);
assert.equal(preview('Seismic Toss','Pixilate').adjustedPower,null);
assert.equal(preview('Weather Ball','Pixilate').type,'Normal');
assert.equal(preview('Weather Ball','Pixilate').adjustedPower,null);
assert.equal(preview('Hyper Voice','Cute Charm').type,'Normal');
assert.equal(preview('Hyper Voice','Cute Charm').adjustedPower,null);
assert.equal(preview('Flamethrower','Blaze').adjustedPower,null);
console.log('17 ability preview checks passed.');
