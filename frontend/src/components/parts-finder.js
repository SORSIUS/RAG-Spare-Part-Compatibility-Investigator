import {markdown} from './markdown.js';
import {request} from '../services/api.js';
import {textElement, safePdfUrl, renderSource} from './sources.js';

const labels = {shock_absorber: 'Shock absorber / strut', protection_kit: 'Protection kit', mounting_kit: 'Suspension mounting kit', spark_plug: 'Spark plug reference'};

export function createPartsFinder() {
  const section = textElement('section', undefined, 'parts-shop');
  section.id = 'parts-finder';
  section.innerHTML = `<div class="shop-heading"><div><span class="shop-kicker">THE RIGHT PART STARTS WITH YOUR CAR</span><h1>Find parts.<br>Check the fit.</h1><p>Choose your vehicle. See what the manufacturer lists.<br>Open the catalogue before you make a decision.</p></div><div class="garage-illustration" aria-hidden="true"><svg viewBox="0 0 480 190"><path d="M30 143h415M65 136l11-42 65-12 40-45h120l51 45 53 15 12 40"/><path d="M153 81l35-35h47v35zm94-35h45l42 35h-87z"/><circle cx="134" cy="137" r="29"/><circle cx="134" cy="137" r="13"/><circle cx="353" cy="137" r="29"/><circle cx="353" cy="137" r="13"/><path d="M168 137h150M73 104h35m282 3h19M267 95h21"/></svg><span>CHECK THE APPLICATION. KEEP THE EVIDENCE.</span></div></div>
    <form class="vehicle-finder" id="vehicle-finder"><label>Make<select id="vehicle-make" required aria-label="Vehicle make"><option>Loading vehicles…</option></select></label><label>Model<select id="vehicle-model" required aria-label="Vehicle model"></select></label><label>Year<input id="vehicle-year" type="number" min="1950" max="2100" placeholder="e.g. 2012" aria-label="Vehicle year"></label><label>Position<select id="vehicle-axle" aria-label="Part position"><option value="">Front & rear</option><option value="front">Front</option><option value="rear">Rear</option></select></label><button class="find-parts-button" type="submit">Find parts <span aria-hidden="true">→</span></button></form>
    <div class="shop-categories" aria-label="Part categories"><button type="button" id="suspension-category">Suspension <span>Shocks · mounts · protection</span></button><a href="#questions">Ask the assistant <span>Understand a part in simple words</span></a><button type="button" id="open-documents">Documents <span>Upload a PDF or text reference</span></button></div>
    <div class="results-toolbar"><div><span class="shop-kicker">CATALOGUE PARTS</span><h2 id="fitment-heading">Choose a vehicle to get started</h2></div><label>Chassis code (optional)<input id="vehicle-chassis" form="vehicle-finder" maxlength="40" placeholder="e.g. ZRE152" aria-label="Chassis code"></label></div>
    <p id="fitment-status" role="status">Loading the linked catalogue…</p><div id="fitment-results" class="part-grid" aria-live="polite"></div><div class="result-pagination" id="fitment-pagination"></div><p class="fitment-note">These are catalogue-listed candidates, not a promise of fit. Check chassis, production month, engine, steering side and market. No prices or stock are implied.</p>`;
  const $ = id => section.querySelector('#' + id);
  const categoryLabel = textElement('label', 'Part category');
  const categorySelect = document.createElement('select'); categorySelect.id='part-category';
  for (const [value,label] of [['all','All parts'],['filters','Filters'],['brakes','Brakes'],['ignition','Ignition'],['suspension','Suspension'],['engine','Engine'],['electrical','Electrical']]) {const option=textElement('option',label);option.value=value;categorySelect.append(option);}
  categoryLabel.append(categorySelect); $('vehicle-finder').querySelector('button').before(categoryLabel);
  const libraryResults = textElement('div', undefined, 'library-part-results'); section.querySelector('.results-toolbar').before(libraryResults);
  const engineLabel = textElement('label', 'Engine (optional)');
  const engineInput = document.createElement('input');
  engineInput.id = 'vehicle-engine'; engineInput.placeholder = 'e.g. 1.8 or 1ZZ-FE'; engineInput.maxLength = 40;
  engineInput.setAttribute('aria-label', 'Engine size or code');
  engineLabel.append(engineInput);
  $('vehicle-finder').querySelector('button').before(engineLabel);
  const replacement = document.createElement('details');
  replacement.className = 'replacement-finder';
  replacement.innerHTML = '<summary>Have an original part number? Find a documented alternative</summary><form class="vehicle-finder"><label>Original brand<input name="brand" required maxlength="60" value="Toyota"></label><label>Original part number<input name="part" required maxlength="40" placeholder="e.g. 48609-12500"></label><button type="submit" class="find-parts-button">Check alternatives →</button></form><p role="status">Use the number on your original part or OEM catalogue. Coverage depends on imported references.</p><div class="part-grid"></div>';
  section.querySelector('.shop-categories').after(replacement);
  replacement.querySelector('form').onsubmit = async event => {
    event.preventDefault();
    const form = event.currentTarget, button = form.querySelector('button');
    const status = replacement.querySelector('[role="status"]');
    const results = replacement.querySelector('.part-grid');
    button.disabled = true; results.replaceChildren(); status.textContent = 'Checking published references…';
    try {
      const params = new URLSearchParams(new FormData(form));
      const result = await request('replacements?' + params);
      status.textContent = result.message + (result.total ? ' Showing ' + result.records.length + ' of ' + result.total + ' reference rows. ' + result.notice : '');
      results.replaceChildren(...result.records.map(record => {
        const item = card(record);
        item.querySelector('.part-card-body').prepend(textElement('p', record.original_brand + ' ' + record.original_part + ' → ' + record.brand + ' ' + record.part_number, 'part-brand'));
        return item;
      }));
      if (!result.total) {
        const ask = textElement('button', 'Continue with the document assistant', 'outline-button');
        ask.type = 'button';
        ask.onclick = () => {
          const question = document.getElementById('question');
          question.value = 'Help me find an alternative for ' + form.elements.brand.value.trim() + ' original part ' + form.elements.part.value.trim() + '. What vehicle details do you need to search the application catalogues?';
          location.hash='#chat';
          question.focus();
        };
        results.append(ask);
      }
    } catch (error) { status.textContent = 'The lookup could not finish. Please retry. ' + error.message; }
    finally { button.disabled = false; }
  };
  let vehicles = [], offset = 0, searching = false, sequence = 0;
  const categoryBar=section.querySelector('.shop-categories');
  for(const [value,label] of [['all','All parts'],['filters','Filters'],['brakes','Brakes'],['ignition','Ignition'],['engine','Engine'],['electrical','Electrical']]) {
    const button=textElement('button',label);button.type='button';button.dataset.category=value;
    button.onclick=()=>{categorySelect.value=value;search();};categoryBar.prepend(button);
  }
  const category = $('suspension-category');category.dataset.category='suspension';
  category.onclick = () => { categorySelect.value='suspension'; search(); };
  $('open-documents').onclick = () => { const details = document.getElementById('catalogues-drawer'); location.hash='#documents'; details.open = true; };

  function fillModels() {
    const values = vehicles.filter(v => v.make === $('vehicle-make').value);
    $('vehicle-model').replaceChildren(...values.map(v => { const option = textElement('option', v.model); option.value = v.model; return option; }));
    if (values.some(v => v.model === 'Corolla')) $('vehicle-model').value = 'Corolla';
  }
  function card(record) {
    const item = textElement('article', undefined, 'part-card');
    const diagram = textElement('div', undefined, 'part-diagram');
    diagram.innerHTML = record.component === 'shock_absorber' ? '<svg viewBox="0 0 140 110" aria-hidden="true"><path d="M70 12v20m-18 0h36v53H52zm18 53v15M60 16h20M60 99h20M48 43h44M48 54h44M48 65h44M48 76h44"/></svg>' : record.component === 'mounting_kit' ? '<svg viewBox="0 0 140 110" aria-hidden="true"><ellipse cx="70" cy="59" rx="43" ry="23"/><ellipse cx="70" cy="52" rx="31" ry="18"/><ellipse cx="70" cy="49" rx="10" ry="6"/><path d="M40 45V29m60 16V29M66 33V17"/></svg>' : '<svg viewBox="0 0 140 110" aria-hidden="true"><path d="M51 20h38v10H51zm-5 10h48v10H46zm5 10h38v10H51zm-5 10h48v10H46zm5 10h38v10H51zm-5 10h48v10H46zm5 10h38v12H51z"/></svg>';
    if (record.reference_only) diagram.replaceChildren(textElement('strong', 'OEM → DENSO'));
    diagram.append(textElement('span', record.reference_only ? 'Published reference · verify vehicle application' : 'Illustration · not a product photo'));
    const body = textElement('div', undefined, 'part-card-body');
    body.append(textElement('span', record.brand + ' / ' + record.axle.toUpperCase(), 'part-brand'), textElement('h3', labels[record.component] || record.component), textElement('strong', record.part_number, 'part-number'), textElement('p', record.make + ' ' + record.model + ' · ' + record.period, 'part-vehicle'), textElement('p', 'Check the exact vehicle details before ordering.', 'part-application'));
    const detail = document.createElement('details'); detail.append(textElement('summary', 'Application details & reference'));
    detail.append(textElement('p', record.application), textElement('p', record.vehicle_label), textElement('p', 'Source: ' + record.source + ' · physical PDF page ' + record.page_number));
    if (record.oem_group.length && !record.reference_only) detail.append(textElement('p', 'OEM numbers in this application cell: ' + record.oem_group.join(', ') + '. Individual interchangeability pairs are not established.'));
    body.append(detail);
    const actions = textElement('div', undefined, 'part-card-actions');
    const link = textElement('a', 'View source page ↗'); link.href = safePdfUrl(record.pdf_url); link.target = '_blank'; link.rel = 'noopener';
    const ask = textElement('button', 'Ask about this part'); ask.type = 'button'; ask.onclick = () => {
      document.getElementById('question').value = record.reference_only ? `Explain the published replacement reference for ${record.original_brand} ${record.original_printed} to DENSO ${record.part_number}, and what vehicle details I must check.` : `Explain the catalogue listing for KYB ${record.part_number} on ${record.make} ${record.model}, ${record.axle} suspension. Application: ${record.application}. Preserve all qualifications.`;
      location.hash='#chat'; document.getElementById('question').focus();
    };
    actions.append(link, ask); body.append(actions); item.append(diagram, body); return item;
  }

  const categoryDescriptions={filters:'Air, cabin, oil and fuel filters keep contaminants out of important systems.',brakes:'Brake pads, discs, shoes and drums slow the car. Exact brake parts depend on the vehicle version.',ignition:'Spark plugs and ignition components help petrol engines ignite the fuel mixture.',suspension:'Shocks, struts and mounts help control movement and support a comfortable ride.',engine:'Engine parts include cooling, timing, sealing and lubrication components.',electrical:'Batteries, starters, alternators and sensors support the car’s electrical systems.'};
  async function search(nextOffset = 0, explain = false) {
    if (!vehicles.length) return;
    const ticket = ++sequence;
    searching = true; section.querySelector('.find-parts-button').disabled = true;
    const selected=categorySelect.value;
    for(const button of categoryBar.querySelectorAll('[data-category]')) button.setAttribute('aria-pressed',String(button.dataset.category===selected));
    $('fitment-status').textContent = 'Checking documented part candidates…';
    const params = new URLSearchParams({category:selected,make:$('vehicle-make').value,model:$('vehicle-model').value,axle:$('vehicle-axle').value,chassis:$('vehicle-chassis').value.trim(),limit:'12',offset:String(nextOffset)});
    if ($('vehicle-year').value) params.set('year',$('vehicle-year').value);
    if ($('vehicle-engine').value.trim()) params.set('engine',$('vehicle-engine').value.trim());
    try {
      libraryResults.replaceChildren();
      const categories=selected==='all'?Object.keys(categoryDescriptions):[selected];
      const grid=textElement('div',undefined,'parts-category-grid');
      for(const name of categories){
        const tile=textElement('article');tile.append(textElement('h3',name[0].toUpperCase()+name.slice(1)),textElement('p',categoryDescriptions[name]));
        const ask=textElement('button','Ask about '+name,'outline-button');ask.type='button';
        ask.onclick=()=>{location.hash='#chat';document.getElementById('question').value='Explain '+name+' for my '+[params.get('year'),params.get('make'),params.get('model'),params.get('engine')].filter(Boolean).join(' ')+'. What is documented, and what details do you need to check exact parts?';document.getElementById('question').focus();};
        tile.append(ask);grid.append(tile);
      }
      libraryResults.append(textElement('h2',selected==='all'?'Explore all part categories':categorySelect.selectedOptions[0].textContent),grid);
      const explanation=textElement('section',undefined,'parts-explanation');libraryResults.append(explanation);
      explanation.append(textElement('p',explain?'Preparing a clear explanation from the documents…':'Choose your vehicle, then press Find parts for an AI explanation. General category descriptions are shown above.'));
      const result=await request('fitments?'+params);
      if(ticket!==sequence)return;
      offset=nextOffset;
      $('fitment-heading').textContent=[params.get('make'),params.get('model'),params.get('year')].filter(Boolean).join(' ')+' — '+categorySelect.selectedOptions[0].textContent.toLowerCase();
      const groups=[...new Set(result.records.map(record=>record.category||'suspension'))];
      $('fitment-status').textContent=result.total?`${result.total} documented candidates · showing ${offset+1}–${offset+result.records.length}. This page contains ${groups.join(' and ')} listings. Other categories may need additional vehicle-specific references.`:'No verified product listings for this selection yet. The assistant can explain the category and identify what needs checking; it will not invent matching part numbers.';
      $('fitment-results').replaceChildren(...result.records.map(card));
      $('fitment-pagination').replaceChildren();
      for(const [label,position] of [['Previous',offset-12],['Next',offset+12]]){
        if(position<0||position>=result.total)continue;
        const button=textElement('button',label,'outline-button');button.type='button';button.onclick=()=>search(position);$('fitment-pagination').append(button);
      }
      if(explain){
        const response=await request('parts/overview',Object.fromEntries(params));
        if(ticket!==sequence)return;
        explanation.replaceChildren(textElement('h2','Your parts, explained'));
        if(response.message)explanation.append(textElement('p',response.message));
        for(const claim of response.claims){const block=markdown(claim.text);for(const cite of claim.citations){const source=response.sources.find(s=>s.id===cite.source_id);if(source){const a=textElement('a',' ['+cite.source_id+']','source-link');a.href=safePdfUrl(source.pdf_url);a.target='_blank';a.rel='noopener';block.append(a);}}explanation.append(block);}
        if(response.general_guidance){explanation.append(textElement('h3','General explanation'),markdown(response.general_guidance));}
        for(const unknown of response.unknowns)explanation.append(textElement('p',unknown,'answer-notice'));
        const details=document.createElement('details');details.className='parts-source-details';details.append(textElement('summary','Check the supporting sources ('+response.sources.length+')'));
        for(const source of response.sources)details.append(renderSource(source,false,()=>{}));explanation.append(details);
      }
    }catch(error){if(ticket===sequence)$('fitment-status').textContent=error.message;}
    finally{if(ticket===sequence){searching=false;section.querySelector('.find-parts-button').disabled=false;}}
  }
  categorySelect.onchange = () => search();
  $('vehicle-make').onchange = fillModels;
  $('vehicle-finder').onsubmit = event => { event.preventDefault(); if (!searching) search(0,true); };
  async function initialize() {
    try {
      const options = await request('fitments/options'); vehicles = options.vehicles;
      const makes = [...new Set(vehicles.map(v => v.make))];
      $('vehicle-make').replaceChildren(...makes.map(make => { const option = textElement('option', make); option.value = make; return option; }));
      if (makes.includes('Toyota')) $('vehicle-make').value = 'Toyota';
      fillModels();
      if (!vehicles.length) { $('fitment-status').textContent = 'No linked fitment catalogue yet. See README: import the official KYB catalogue, or use the document library below.'; return; }
      await search();
    } catch (error) { $('fitment-status').textContent = error.message; }
  }
  return {element: section, initialize};
}

