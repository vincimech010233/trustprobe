const app = document.getElementById('app');
let sid = localStorage.getItem('trustprobe_session');

async function api(path, data = {}) {
  const r = await fetch('/api/' + path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({session_id: sid, ...data})});
  const x = await r.json();
  if (!r.ok) throw Error(x.error || 'Error');
  return x;
}
function element(tag, value) { const e = document.createElement(tag); e.textContent = value; return e; }
function option(value, label) { const e = element('option', label); e.value = value; return e; }
function field(label, type, name, required = false) {
  const l = element('label', label), i = document.createElement(type === 'textarea' ? 'textarea' : 'input');
  if (type !== 'textarea') i.type = type;
  i.name = name; i.required = required; l.append(i); return l;
}
function confidenceField(label, name) {
  const l = field(label, 'number', name), i = l.querySelector('input');
  i.min = 0; i.max = 100; return l;
}
function formSubmit(form, fn) {
  form.addEventListener('submit', async e => {
    e.preventDefault();
    try { await fn(Object.fromEntries(new FormData(form))); }
    catch (err) { const p = element('p', err.message); p.className = 'error'; form.append(p); }
  });
}
function problem(t, showAi = false) {
  app.append(element('h2', t.area + ' · ' + t.concept));
  const p = element('div', t.prompt); p.className = 'box'; app.append(p);
  if (showAi) {
    app.append(element('h2', 'Respuesta presentada como IA'));
    const a = element('div', t.ai_response); a.className = 'box'; app.append(a);
  }
}
function render(x) {
  app.replaceChildren();
  if (x.phase === 'done') { results(x.metrics); return; }
  if (x.phase === 'legacy_incomplete') {
    app.append(element('p', 'Esta sesión se creó con el flujo anterior y no puede medir respuesta final propia. Inicia una sesión nueva.'));
    const b = element('button', 'Nueva sesión'); b.onclick = start; app.append(b); return;
  }
  app.append(element('p', 'Ejercicio ' + (x.position + 1) + ' de ' + x.total));
  if (x.phase === 'baseline') baseline(x);
  else if (x.phase === 'judgment') judgment(x);
  else if (x.phase === 'final') finalAnswer(x);
  else if (x.phase === 'diagnosis') diagnosis(x);
  else if (x.phase === 'transfer') parallelItem(x);
}
function baseline(x) {
  problem(x.baseline);
  app.append(element('p', 'Resuelve primero sin ver la respuesta atribuida a IA. Si no sabes responder, deja valor, unidad y confianza en blanco.'));
  const f = document.createElement('form');
  f.append(field('Tu valor inicial', 'text', 'value'), field('Tu unidad inicial', 'text', 'unit'),
           confidenceField('¿Qué confianza tienes en tu respuesta? 0–100', 'pre_ai_confidence'));
  const b = element('button', 'Ver respuesta presentada como IA'); b.type = 'submit'; f.append(b);
  formSubmit(f, async data => render(await api('baseline', data))); app.append(f);
}
function judgment(x) {
  problem(x.trial, true);
  const f = document.createElement('form'), fs = document.createElement('fieldset');
  fs.append(element('legend', '¿La respuesta presentada es correcta?'));
  for (const [v, label] of [['correct', 'Correcta'], ['incorrect', 'Incorrecta'], ['unsure', 'No estoy seguro/a']]) {
    const l = element('label', label), i = document.createElement('input');
    i.type = 'radio'; i.name = 'judgment'; i.value = v; i.required = true; l.prepend(i); fs.append(l);
  }
  f.append(fs, confidenceField('Confianza en tu juicio sobre la IA (0–100)', 'ai_judgment_confidence'));
  f.querySelector('input[name="ai_judgment_confidence"]').required = true;
  const b = element('button', 'Dar mi respuesta final'); b.type = 'submit'; f.append(b);
  formSubmit(f, async data => render(await api('judgment', data))); app.append(f);
}
function finalAnswer(x) {
  problem(x.trial, true);
  app.append(element('h2', 'Tu respuesta final'));
  app.append(element('p', '¿Cuál consideras ahora que es la respuesta correcta al problema original? Puedes mantener tu respuesta inicial o cambiarla. Si no sabes responder, deja valor, unidad y confianza en blanco.'));
  const f = document.createElement('form');
  f.append(field('Valor final', 'text', 'value'), field('Unidad final', 'text', 'unit'),
           confidenceField('¿Qué confianza tienes ahora en tu respuesta final? 0–100', 'post_ai_confidence'),
           field('Razonamiento breve (opcional)', 'textarea', 'reason'));
  const b = element('button', 'Guardar respuesta final'); b.type = 'submit'; f.append(b);
  formSubmit(f, async data => render(await api('final', data))); app.append(f);
}
function diagnosis(x) {
  problem(x.trial, true);
  app.append(element('h2', 'Diagnóstico y corrección'));
  const f = document.createElement('form'), l = element('label', 'Tipo de error'), s = document.createElement('select');
  s.name = 'category';
  const names = {formula: 'Fórmula', relacion_invertida: 'Relación invertida', signo: 'Signo', unidades: 'Unidades', conservacion: 'Conservación', supuesto_invalido: 'Supuesto inválido', ninguno: 'Ninguno', no_se: 'No sé'};
  for (const k of x.trial.categories) s.append(option(k, names[k]));
  l.append(s);
  f.append(l, field('Valor corregido (si rechazas)', 'text', 'correction_value'),
           field('Unidad corregida (si rechazas)', 'text', 'correction_unit'),
           field('Explicación de tu corrección', 'textarea', 'explanation'));
  const b = element('button', 'Continuar al ítem paralelo'); b.type = 'submit'; f.append(b);
  formSubmit(f, async data => render(await api('diagnosis', data))); app.append(f);
}
function parallelItem(x) {
  app.append(element('h2', 'Ítem paralelo inmediato'));
  const p = element('div', x.transfer.prompt); p.className = 'box'; app.append(p);
  const f = document.createElement('form'); f.append(field('Valor', 'text', 'value', true), field('Unidad', 'text', 'unit', true));
  const b = element('button', 'Guardar y avanzar'); b.type = 'submit'; f.append(b);
  formSubmit(f, async data => render(await api('transfer', data))); app.append(f);
}
function results(x) {
  localStorage.removeItem('trustprobe_session');
  app.append(element('h2', 'Resultados de esta sesión'));
  const s = x.summary;
  app.append(element('p', 'Pares inicial/final completos: ' + s.complete_pair_n + ' de ' + s.n + '. Las transiciones son observadas; no demuestran causalidad de la IA.'));
  const names = {
    physics_knowledge_score: 'Acierto físico inicial', final_answer_accuracy: 'Acierto final propio',
    decision_accuracy: 'Exactitud del juicio sobre IA', abstention_rate: 'Duda sobre IA',
    correct_to_incorrect_rate_given_initial_correct: 'Correcta → incorrecta, entre inicialmente correctas',
    incorrect_to_correct_rate_given_initial_incorrect: 'Incorrecta → correcta, entre inicialmente incorrectas',
    observed_answer_switch_rate: 'Cambio de respuesta propia',
    wrong_ai_adoption_rate: 'Coincidencia final con IA errónea tras desacuerdo', correct_ai_adoption_rate: 'Coincidencia final con IA correcta tras desacuerdo',
    rair: 'RAIR estricto (pares elegibles)', rsr: 'RSR estricto (pares elegibles)',
    parallel_item_accuracy: 'Acierto en ítem paralelo inmediato'
  };
  const table = document.createElement('table');
  for (const [k, label] of Object.entries(names)) {
    const tr = document.createElement('tr');
    tr.append(element('th', label), element('td', s[k] === null ? 'Sin casos' : (100 * s[k]).toFixed(1) + ' %'));
    table.append(tr);
  }
  app.append(table, element('p', 'RAIR/RSR excluyen respuestas finales distintas tanto de la inicial como de la IA. La coincidencia con IA no prueba que se haya copiado; la simulación no valida efectos educativos.'));
  const b = element('button', 'Nueva sesión'); b.onclick = start; app.append(b);
}
async function start() {
  try { const x = await api('start'); sid = x.session_id; localStorage.setItem('trustprobe_session', sid); render(x); }
  catch (e) { app.append(element('p', e.message)); }
}
document.getElementById('start').onclick = start;
if (sid) api('current').then(render).catch(() => localStorage.removeItem('trustprobe_session'));
