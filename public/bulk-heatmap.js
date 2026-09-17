// Safe DOM-only renderer for structured calculator output. No HTML evaluation.
window.renderBulkHeatmap = function(container, data) {
  if (!Array.isArray(data.cells) || !Array.isArray(data.threats) || !data.threats.length) return;
  const details=document.createElement('details'); details.className='bulk-map';
  const summary=document.createElement('summary'); summary.textContent=`Explore KO odds · ${data.budget} defensive points`;
  details.append(summary); container.append(details);
  let built=false;
  details.addEventListener('toggle',()=>{
    if(!details.open || built) return; built=true;
    const controls=document.createElement('div'); controls.className='bulk-map-controls';
    function selector(label, options) {
      const wrap=document.createElement('label'); wrap.textContent=label+' ';
      const select=document.createElement('select');
      options.forEach((text,i)=>{const o=document.createElement('option');o.value=i;o.textContent=text;select.append(o);});
      wrap.append(select);controls.append(wrap);return select;
    }
    const threat=selector('Attack',data.threats), turns=selector('Metric',['KO by 1 use','KO by 2 uses','KO by 3 uses']);
    const help=document.createElement('p');help.textContent='Rows: HP points. Columns: Defense points. SpD = budget − HP − Def. Green: lower KO risk; red: higher. ★ recommended. Gray: unavailable. Hover, focus, or tap a cell for details.';
    const readout=document.createElement('p');readout.className='bulk-map-readout';readout.setAttribute('aria-live','polite');readout.textContent='Select a cell to see its spread and damage.';
    const scroll=document.createElement('div');scroll.className='bulk-map-scroll';
    const table=document.createElement('table');scroll.append(table);
    details.append(controls,help,readout,scroll);
    const lookup=new Map(data.cells.map(c=>[c.points[0]+','+c.points[1],c]));
    function describe(c) {
      const r=c.threats[Number(threat.value)], p=100*r.ko[Number(turns.value)];
      let text=`${c.points[0]} HP / ${c.points[1]} Def / ${c.points[2]} SpD points. Stats: ${c.stats.hp} HP / ${c.stats.def} Def / ${c.stats.spd} SpD. First-use damage: ${r.range[0]}–${r.range[1]}. ${turns.options[turns.selectedIndex].text}: ${p.toFixed(2)}%.`;
      const neighbor=lookup.get(c.points[0]+','+(c.points[1]-1));
      if(neighbor) {
        const n=neighbor.threats[Number(threat.value)];
        if(n.ko[Number(turns.value)]===r.ko[Number(turns.value)]) text+=' Moving one point from SpD to Def from the cell to the left does not change these KO odds.';
        if(n.range[0]===r.range[0] && n.range[1]===r.range[1]) text+=' Its damage range is unchanged too.';
      }
      return text;
    }
    function draw() {
      table.replaceChildren();
      const header=document.createElement('tr');
      for(let d=-1;d<=32;d++){const th=document.createElement('th');th.textContent=d<0?'HP / Def':d;th.scope='col';header.append(th);}
      const head=document.createElement('thead');head.append(header);table.append(head);
      const body=document.createElement('tbody');
      for(let h=0;h<=32;h++) {
        const row=document.createElement('tr'), label=document.createElement('th');label.scope='row';label.textContent=h;row.append(label);
        for(let d=0;d<=32;d++) {
          const td=document.createElement('td'), c=lookup.get(h+','+d);
          if(c) {
            const probability=c.threats[Number(threat.value)].ko[Number(turns.value)];
            const button=document.createElement('button');button.type='button';
            const selected=JSON.stringify(c.points)===JSON.stringify(data.recommended);
            button.textContent=(selected?'★ ':'')+(100*probability).toFixed(0)+'%';
            button.style.backgroundColor=`hsl(${120*(1-probability)} 50% 23%)`;
            const description=describe(c);button.title=description;button.setAttribute('aria-label',description);
            const show=()=>{readout.textContent=description;};button.onfocus=show;button.onmouseenter=show;button.onclick=show;td.append(button);
          } else {td.textContent='—';td.className='unavailable';}
          row.append(td);
        }
        body.append(row);
      }
      table.append(body);
    }
    threat.onchange=draw;turns.onchange=draw;draw();
  });
};
