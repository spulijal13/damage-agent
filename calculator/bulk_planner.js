// Exact roll probabilities for repeated single-hit attacks under fixed conditions.
// HP-dependent damage is recalculated at each reachable HP, not just the max path.
const {calculate, Pokemon} = require('@smogon/calc');

function optimize(input, prepareBattle) {
  const templates = input.battles.map(b => prepareBattle(b, true));
  const model = templates[0] || prepareBattle({defender: input.defender,
    attacker: {name: input.defender.name}, move: 'Tackle'});
  const {gen, defender: base} = model;
  for (const battle of templates) {
    if (battle.move.category === 'Status' || battle.move.hits > 1 ||
        battle.attacker.hasAbility('Parental Bond') ||
        ['Fissure', 'Guillotine', 'Horn Drill', 'Sheer Cold'].includes(battle.move.name)) {
      throw new Error('Probability optimization currently supports single-hit damaging moves. Choose a single-hit attack.');
    }
  }
  const chance = input.survival_chance ?? 1;
  const compare = (a,b) => a.score-b.score || b.points[0]-a.points[0] || a.points[1]-b.points[1];
  const better = (a,b) => !b || compare(a,b)<0;
  let minimum=null, full=null, reference=null, fallback=null;
  const individual=templates.map(()=>null), cells=[];
  const ev = p => p ? 8*p-4 : 0;
  function evaluate(points) {
    const defender = new Pokemon(gen, base.name, {...(input.defender || input.battles[0].defender),
      evs: {...base.evs, hp:ev(points[0]), def:ev(points[1]), spd:ev(points[2])}});
    const hp = Math.max(1, Math.floor(defender.maxHP()*input.current_hp_percent/100));
    const reports=templates.map((battle,index)=>{
      const cache=new Map();
      const hpSensitive = defender.hasAbility('Multiscale','Shadow Shield','Tera Shell') ||
        ['Brine','Crush Grip','Wring Out','Hard Press','Super Fang','Nature’s Madness',"Nature's Madness",'Ruination','Endeavor','Pain Split'].includes(battle.move.name);
      function rollsAt(current) {
        const key=hpSensitive ? current : 'fixed';
        if (!cache.has(key)) {
          const target=defender.clone(); target.originalCurHP=current;
          const result=calculate(gen,battle.attacker,target,battle.move,battle.field);
          const rolls=typeof result.damage==='number' ? [result.damage] : result.damage;
          if (!rolls.every(Number.isFinite)) throw new Error('Unsupported multi-hit probability distribution.');
          cache.set(key,rolls);
        }
        return cache.get(key);
      }
      let states=new Map([[hp,1]]), ko=[];
      // Keep an absorbing fainted state, so KO by turn n includes earlier KOs.
      for (let use=0;use<3;use++) {
        const next=new Map();
        for (const [current,probability] of states) {
          if (!current) { next.set(0,(next.get(0)||0)+probability); continue; }
          const rolls=rollsAt(current);
          for (const damage of rolls) {
            const remaining=Math.max(0,current-damage);
            next.set(remaining,(next.get(remaining)||0)+probability/rolls.length);
          }
        }
        states=next; ko.push(Math.min(1,Math.max(0,states.get(0)||0)));
      }
      const hits=input.hits[index];
      let worstHP=hp, maxRolls=[];
      for(let n=0;n<hits && worstHP>0;n++) {
        const damage=Math.max(...rollsAt(worstHP)); maxRolls.push(damage); worstHP-=damage;
      }
      const first=rollsAt(hp), survival=1-ko[hits-1];
      return {attacker:battle.attacker.name,move:battle.move.name,hits,ko,
        survival_probability:survival,survives:survival>=chance,
        min_damage:Math.min(...first),max_damage:Math.max(...first),damage_rolls:first,max_rolls:maxRolls,
        starting_hp:hp,remaining_hp:Math.max(0,worstHP)};
    });
    const stats={hp:defender.maxHP(),def:defender.rawStats.def,spd:defender.rawStats.spd};
    return {points,total:points.reduce((a,b)=>a+b,0),stats,
      score:(input.bias/stats.def+1/stats.spd)/stats.hp,reports,
      worst_probability:Math.min(1,...reports.map(r=>r.survival_probability))};
  }
  for(let total=0;total<=input.budget;total++) {
    if(minimum && total>minimum.total && total<input.budget) continue;
    for(let hp=0;hp<=Math.min(32,total);hp++) for(let def=0;def<=Math.min(32,total-hp);def++) {
      const spd=total-hp-def;
      if(spd<0 || spd>32 || Object.entries(input.locked).some(([s,v])=>({hp,def,spd})[s]!==v)) continue;
      const c=evaluate([hp,def,spd]), passes=c.reports.every(r=>r.survives);
      c.reports.forEach((r,i)=>{if(r.survives && (!individual[i] || (individual[i].total===total && better(c,individual[i])))) individual[i]=c;});
      if(passes && (!minimum || minimum.total===total) && better(c,minimum)) minimum=c;
      if(total===input.budget) {
        if(better(c,reference)) reference=c;
        if(passes && better(c,full)) full=c;
        if(!fallback || c.worst_probability>fallback.worst_probability ||
          (c.worst_probability===fallback.worst_probability && better(c,fallback))) fallback=c;
        cells.push({points:c.points,stats:c.stats,score:c.score,
          threats:c.reports.map(r=>({ko:r.ko,range:[r.min_damage,r.max_damage],hp:r.starting_hp}))});
      }
    }
  }
  // Describe only retained recommendations, not every heatmap candidate.
  for (const candidate of new Set([minimum,full,reference,fallback,...individual].filter(Boolean))) {
    candidate.reports.forEach((report,index)=>{
      const battle=templates[index];
      const defender=new Pokemon(gen,base.name,{...(input.defender || input.battles[0].defender),
        evs:{...base.evs,hp:ev(candidate.points[0]),def:ev(candidate.points[1]),spd:ev(candidate.points[2])},
        curHP:report.starting_hp});
      const result=calculate(gen,battle.attacker,defender,battle.move,battle.field);
      // Smogon's KO text includes residual/recovery mechanics that this planner
      // excludes. Use our propagated probabilities for the KO wording instead.
      report.damage_description=result.fullDesc('%',false).split(' -- ')[0]
        .replace(/\b(\d+)([+-]?) (HP|Atk|Def|SpA|SpD|Spe)\b/g,
          (_,value,nature,stat)=>`${Number(value) ? (Number(value)+4)/8 : 0}${nature} ${stat}`);
    });
  }
  return {minimum,full_budget:full,reference,fallback,individual,cells};
}
module.exports={optimize};
