// Species base stats are fixed; display the calculated stat at level 50 / 31 IVs.
function level50Stat(base, stat, points, nature) {
  const evs = points > 0 ? points * 8 - 4 : 0;
  let value = Math.floor((2 * base + 31 + Math.floor(evs / 4)) * 50 / 100);
  if (stat === 'hp') return base === 1 ? 1 : value + 60;
  value += 5;
  const multiplier = nature.plus === nature.minus ? 100 : nature.plus === stat ? 110 : nature.minus === stat ? 90 : 100;
  return Math.floor(value * multiplier / 100);
}
if (typeof module !== 'undefined') module.exports = {level50Stat};
