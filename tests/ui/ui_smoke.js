// Prueba de humo de la interfaz (jsdom) contra el sistema en ejecución. Sale con código 1 si algo falla.
// Variables: BASE (por defecto http://127.0.0.1:8000), STATIC_JS, EVAL_ADMIN_USER/PASSWORD, EVAL_VIEWER_USER/PASSWORD
const { JSDOM, VirtualConsole } = require('jsdom');
const fs = require('fs');
const BASE = process.env.BASE || 'http://127.0.0.1:8000';
const SRC = fs.readFileSync(process.env.STATIC_JS || '../../app/static/app.js', 'utf8');
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const failures = [];
const check = (name, ok, extra) => { console.log((ok ? '[OK]    ' : '[FALLO] ') + name + (!ok && extra ? '  ' + extra : '')); if (!ok) failures.push(name); };

async function open(user, pass) {
  let cookie = '';
  const jsErrors = [];
  const vc = new VirtualConsole(); vc.on('jsdomError', (e) => jsErrors.push(e.message));
  const w = new JSDOM('<!doctype html><body><div id="app"></div></body>', { url: BASE + '/', runScripts: 'outside-only', pretendToBeVisual: true, virtualConsole: vc }).window;
  w.fetch = async (url, o = {}) => {
    const r = await fetch(BASE + url, { ...o, headers: { ...(o.headers || {}), cookie } });
    const sc = r.headers.getSetCookie(); if (sc.length) cookie = sc.map((c) => c.split(';')[0]).join('; ');
    return r;
  };
  w.confirm = () => true;
  w.eval(SRC); await wait(500);
  const inputs = w.document.querySelectorAll('.login input'); inputs[0].value = user; inputs[1].value = pass;
  w.document.querySelector('.login button').click(); await wait(1200);
  return { w, jsErrors, $: (s) => w.document.querySelector(s), $$: (s) => [...w.document.querySelectorAll(s)] };
}

async function views(role, user, pass) {
  const s = await open(user, pass);
  check(`[${role}] inicia sesión y muestra la barra de navegación`, !!s.$('header nav'));
  for (const b of s.$$('nav button')) {
    b.click(); await wait(600);
    check(`[${role}] vista «${b.textContent}» carga sin error`, !s.$('main .msg.error'), (s.$('main .msg.error') || {}).textContent);
  }
  s.$$('nav button').find((b) => b.textContent === 'Empresas').click(); await wait(600);
  const writeButtons = s.$$('main button').filter((x) => /Nuevo|Editar|Desactivar/.test(x.textContent)).length;
  check(`[${role}] botones de escritura ${role === 'admin' ? 'visibles' : 'ocultos'}`, role === 'admin' ? writeButtons > 0 : writeButtons === 0);
  check(`[${role}] sin errores de JavaScript`, s.jsErrors.length === 0, s.jsErrors.join(' | '));
  return s;
}

(async () => {
  const a = await views('admin', process.env.EVAL_ADMIN_USER, process.env.EVAL_ADMIN_PASSWORD);
  await views('consulta', process.env.EVAL_VIEWER_USER, process.env.EVAL_VIEWER_PASSWORD);

  // Formulario de servicio N2 con responsable dependiente de la sección
  a.$$('nav button')[0].click(); await wait(600);
  a.$$('main .bar button').find((b) => b.textContent.includes('Nuevo')).click(); await wait(800);
  const field = (l) => a.$$('.modal .field').find((f) => f.querySelector('label').textContent.startsWith(l));
  const set = (l, v) => { const el = field(l).querySelector('input,select,textarea'); el.value = v; el.dispatchEvent(new a.w.Event('change')); };
  const code = 'UI.' + Date.now();
  set('Código N2', code); set('Nombre', 'Servicio creado por la prueba de UI');
  const l1 = field('Servicio nivel 1').querySelector('select'); l1.value = l1.options[1].value;
  const sec = field('Sección responsable').querySelector('select'); sec.value = sec.options[1].value; sec.dispatchEvent(new a.w.Event('change')); await wait(800);
  const resp = field('Usuario responsable').querySelector('select');
  check('el selector de responsable se llena con usuarios de la sección elegida', resp.options.length >= 2, `opciones=${resp.options.length}`);
  resp.value = resp.options[1].value;
  set('Mínimo', '10'); set('Máximo', '5');
  const save = () => a.$$('.modal button').find((b) => b.textContent === 'Guardar').click();
  save(); await wait(900);
  check('mínimo > máximo se rechaza con mensaje', /mínimo/i.test((a.$('.modal .msg.error') || {}).textContent || ''));
  set('Máximo', '50'); save(); await wait(1100);
  check('el servicio se guarda y el modal se cierra', !a.$('.modal') && /guardado/i.test((a.$('main .msg') || {}).textContent || ''));
  console.log(failures.length ? `\n${failures.length} control(es) fallaron` : '\nUI OK');
  process.exit(failures.length ? 1 : 0);
})().catch((e) => { console.error('FALLO', e); process.exit(1); });
