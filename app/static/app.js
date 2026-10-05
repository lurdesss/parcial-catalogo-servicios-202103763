'use strict';
// Todo el contenido proveniente del servidor (incluido el del Excel) se inserta con nodos de texto, nunca con innerHTML.
const state = { user: null, csrf: null, view: 'services' };
const isAdmin = () => state.user && state.user.role === 'admin';

function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (v === true) e.setAttribute(k, '');
    else e.setAttribute(k, v);
  }
  for (const c of kids.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    e.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return e;
}

async function api(method, path, body) {
  const opts = { method, headers: { Accept: 'application/json' }, credentials: 'same-origin' };
  if (body !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  if (method !== 'GET' && state.csrf) opts.headers['X-CSRF-Token'] = state.csrf;
  const r = await fetch('/api' + path, opts);
  let data = null;
  try { data = await r.json(); } catch (_) { /* sin cuerpo */ }
  if (!r.ok) {
    if (r.status === 401 && path !== '/auth/login') { state.user = null; render(); }
    const err = new Error((data && data.error && data.error.message) || ('Error ' + r.status));
    err.fields = (data && data.error && data.error.fields) || {};
    err.code = data && data.error && data.error.code;
    err.status = r.status;
    throw err;
  }
  return data;
}

const qs = (o) => Object.entries(o).filter(([, v]) => v !== '' && v !== null && v !== undefined)
  .map(([k, v]) => encodeURIComponent(k) + '=' + encodeURIComponent(v)).join('&');
const badge = (on, a = 'Activo', b = 'Inactivo') => h('span', { class: 'badge ' + (on ? 'ok' : 'off') }, on ? a : b);
const msg = (kind, text) => h('div', { class: 'msg ' + kind }, text);

// ------------------------------------------------------------------ modal y formularios
function openModal(title, content) {
  const bg = h('div', { class: 'modal-bg', onclick: (e) => { if (e.target === bg) bg.remove(); } },
    h('div', { class: 'modal', role: 'dialog' }, h('h3', {}, title), content));
  document.body.append(bg);
  return { close: () => bg.remove() };
}

async function loadOptions(path, label, query) {
  const d = await api('GET', path + (path.includes('?') ? '&' : '?') + qs({ per_page: 500, is_active: 'true', ...(query || {}) }));
  return (d.items || []).map((i) => [i.id, label(i)]);
}

// fields: {n, l, type: text|password|number|textarea|select|checkbox, req, options|optionsFn, createOnly}
async function formModal({ title, fields, values, onSubmit }) {
  const inputs = {};
  const errBox = h('div');
  const body = h('div');
  for (const f of fields) {
    let input;
    if (f.type === 'select') {
      const opts = f.options || await f.optionsFn(values || {});
      input = h('select', {}, h('option', { value: '' }, '— sin valor —'), opts.map(([v, t]) => h('option', { value: v }, t)));
      input.value = values && values[f.n] != null ? String(values[f.n]) : '';
    } else if (f.type === 'textarea') {
      input = h('textarea', {}); input.value = (values && values[f.n]) || '';
    } else if (f.type === 'checkbox') {
      input = h('input', { type: 'checkbox' }); input.checked = values ? !!values[f.n] : true;
    } else {
      input = h('input', { type: f.type || 'text' }); input.value = values && values[f.n] != null && f.type !== 'password' ? values[f.n] : '';
    }
    if (f.disabled) input.disabled = true;
    inputs[f.n] = input;
    const fe = h('div', { class: 'field' }, h('label', {}, f.l + (f.req ? ' *' : '')), input, h('div', { class: 'err', 'data-err': f.n }));
    body.append(fe);
    if (f.onchange) input.addEventListener('change', () => f.onchange(inputs));
  }
  const save = h('button', { class: 'btn primary', type: 'button' }, 'Guardar');
  const cancel = h('button', { class: 'btn', type: 'button' }, 'Cancelar');
  const m = openModal(title, h('div', {}, errBox, body, h('div', { class: 'bar' }, save, cancel)));
  cancel.onclick = m.close;
  for (const f of fields) if (f.onchange) f.onchange(inputs);
  save.onclick = async () => {
    errBox.replaceChildren(); body.querySelectorAll('[data-err]').forEach((x) => { x.textContent = ''; });
    const payload = {};
    for (const f of fields) {
      if (f.disabled) continue;
      const el = inputs[f.n];
      let v = f.type === 'checkbox' ? el.checked : el.value;
      if (f.type === 'select') v = v === '' ? null : (f.str ? v : Number(v));
      else if (f.type === 'password' && v === '') continue;
      else if (v === '') v = null;
      payload[f.n] = v;
    }
    try { await onSubmit(payload); m.close(); } catch (e) {
      errBox.append(msg('error', e.message));
      for (const [k, t] of Object.entries(e.fields || {})) { const x = body.querySelector(`[data-err="${k}"]`); if (x) x.textContent = t; }
    }
  };
}

// ---------------------------------------------------------------------- vista CRUD genérica
function crudView(cfg) {
  const root = h('div'); const list = h('div'); const top = h('div', { class: 'bar' });
  const flash = h('div'); let page = 1; const search = h('input', { placeholder: 'Buscar…', type: 'search' });
  const activeSel = h('select', {}, h('option', { value: '' }, 'Todos'), h('option', { value: 'true' }, 'Activos'), h('option', { value: 'false' }, 'Inactivos'));
  const fields = cfg.fields;

  async function load() {
    try {
      const d = await api('GET', cfg.path + '?' + qs({ q: search.value, is_active: activeSel.value, page, per_page: 25 }));
      const head = h('tr', {}, cfg.cols.map(([, t]) => h('th', {}, t)), isAdmin() ? h('th', {}, 'Acciones') : null);
      const rows = d.items.map((it) => h('tr', {},
        cfg.cols.map(([k, , fmt]) => h('td', {}, fmt ? fmt(it) : (it[k] ?? '—'))),
        isAdmin() ? h('td', {}, h('button', { class: 'btn', onclick: () => edit(it) }, 'Editar'), ' ',
          it.is_active ? h('button', { class: 'btn danger', onclick: () => deactivate(it) }, 'Desactivar')
            : h('button', { class: 'btn', onclick: () => reactivate(it) }, 'Reactivar')) : null));
      list.replaceChildren(h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, head), h('tbody', {}, rows))),
        h('div', { class: 'pager' },
          h('button', { class: 'btn', disabled: page <= 1, onclick: () => { page--; load(); } }, '‹ Anterior'),
          `Página ${d.page} de ${d.pages} · ${d.total} registro(s)`,
          h('button', { class: 'btn', disabled: page >= d.pages, onclick: () => { page++; load(); } }, 'Siguiente ›')));
    } catch (e) { list.replaceChildren(msg('error', e.message)); }
  }
  const say = (kind, t) => flash.replaceChildren(msg(kind, t));
  const create = () => formModal({ title: 'Nuevo: ' + cfg.title, fields: fields.filter((f) => !f.editOnly), onSubmit: async (p) => { await api('POST', cfg.path, p); say('ok', 'Registro creado.'); load(); } });
  const edit = (it) => formModal({
    title: 'Editar: ' + cfg.title, values: it,
    fields: fields.filter((f) => !f.createOnly).map((f) => f.createOnlyDisabled ? { ...f, disabled: true } : f),
    onSubmit: async (p) => { await api('PUT', `${cfg.path}/${it.id}`, p); say('ok', 'Cambios guardados.'); load(); },
  });
  async function deactivate(it, cascade) {
    try {
      const r = await api('DELETE', `${cfg.path}/${it.id}` + (cascade ? '?cascade=true' : ''));
      say('ok', 'Desactivado' + (r.deactivated_records > 1 ? ` (${r.deactivated_records} registros, en cascada)` : '') + '. La baja es lógica.');
      load();
    } catch (e) {
      if (e.code === 'has_dependents' && !cascade && confirm(e.message + '\n\n¿Desactivar también a todos sus dependientes (baja lógica en cascada)?')) return deactivate(it, true);
      say('error', e.message);
    }
  }
  async function reactivate(it) { try { await api('PUT', `${cfg.path}/${it.id}`, { is_active: true }); say('ok', 'Reactivado.'); load(); } catch (e) { say('error', e.message); } }
  search.addEventListener('input', () => { page = 1; load(); });
  activeSel.addEventListener('change', () => { page = 1; load(); });
  top.append(search, activeSel, h('span', { class: 'spacer' }), isAdmin() ? h('button', { class: 'btn primary', onclick: create }, '+ Nuevo') : null);
  root.append(h('h2', {}, cfg.title), flash, top, list);
  load();
  return root;
}

const codeName = (i) => `${i.code} · ${i.name}`;
const activeCol = ['is_active', 'Estado', (i) => badge(i.is_active)];
const ORG = {
  companies: { title: 'Empresas', path: '/org/companies', cols: [['code', 'Código'], ['name', 'Nombre'], activeCol],
    fields: [{ n: 'code', l: 'Código', req: 1 }, { n: 'name', l: 'Nombre', req: 1 }, { n: 'is_active', l: 'Activo', type: 'checkbox', editOnly: 1 }] },
  areas: { title: 'Áreas', path: '/org/areas', cols: [['code', 'Código'], ['name', 'Nombre'], ['parent_name', 'Empresa'], activeCol],
    fields: [{ n: 'company_id', l: 'Empresa', req: 1, type: 'select', optionsFn: () => loadOptions('/org/companies', codeName), createOnlyDisabled: 1 },
      { n: 'code', l: 'Código', req: 1 }, { n: 'name', l: 'Nombre', req: 1 }] },
  departments: { title: 'Departamentos', path: '/org/departments', cols: [['code', 'Código'], ['name', 'Nombre'], ['parent_name', 'Área'], activeCol],
    fields: [{ n: 'area_id', l: 'Área', req: 1, type: 'select', optionsFn: () => loadOptions('/org/areas', codeName), createOnlyDisabled: 1 },
      { n: 'code', l: 'Código', req: 1 }, { n: 'name', l: 'Nombre', req: 1 }] },
  sections: { title: 'Secciones', path: '/org/sections', cols: [['code', 'Código'], ['name', 'Nombre'], ['parent_name', 'Departamento'], activeCol],
    fields: [{ n: 'department_id', l: 'Departamento', req: 1, type: 'select', optionsFn: () => loadOptions('/org/departments', codeName), createOnlyDisabled: 1 },
      { n: 'code', l: 'Código', req: 1 }, { n: 'name', l: 'Nombre', req: 1 }] },
  positions: { title: 'Puestos', path: '/org/positions', cols: [['code', 'Código'], ['name', 'Nombre'], ['parent_name', 'Sección'], activeCol],
    fields: [{ n: 'section_id', l: 'Sección', req: 1, type: 'select', optionsFn: () => loadOptions('/org/sections', codeName), createOnlyDisabled: 1 },
      { n: 'code', l: 'Código', req: 1 }, { n: 'name', l: 'Nombre', req: 1 }] },
  users: { title: 'Usuarios', path: '/users',
    cols: [['name', 'Nombre'], ['username', 'Usuario / correo'], ['role', 'Rol'], ['organization', 'Organización', (u) => (u.organization ? u.organization.text : '—')], activeCol],
    fields: [{ n: 'name', l: 'Nombre', req: 1 }, { n: 'username', l: 'Usuario o correo', req: 1 },
      { n: 'password', l: 'Contraseña (mín. 8; en edición solo si desea cambiarla)', type: 'password' },
      { n: 'role', l: 'Rol', req: 1, type: 'select', str: 1, options: [['admin', 'admin'], ['consulta', 'consulta']] },
      { n: 'position_id', l: 'Puesto', req: 1, type: 'select', optionsFn: () => loadOptions('/org/positions', (p) => `${p.code} · ${p.name} (${p.parent_name})`) }] },
};
const CATALOGS = ['classes', 'criticalities', 'types'].map((k) => [k, { classes: 'Clases de servicio', criticalities: 'Criticidades', types: 'Tipos de servicio' }[k]]);
const catalogCfg = (k, t) => ({ title: t, path: '/catalogs/' + k, cols: [['name', 'Nombre'], ['sort_order', 'Orden'], activeCol],
  fields: [{ n: 'name', l: 'Nombre', req: 1 }, { n: 'sort_order', l: 'Orden', type: 'number' }, { n: 'is_active', l: 'Activo', type: 'checkbox', editOnly: 1 }] });
const L1CFG = { title: 'Servicios de nivel 1', path: '/services/l1',
  cols: [['code', 'Código'], ['name', 'Nombre'], ['source_range', 'Origen (Excel)'], activeCol],
  fields: [{ n: 'code', l: 'Código', req: 1 }, { n: 'name', l: 'Nombre', req: 1 }, { n: 'is_active', l: 'Activo', type: 'checkbox', editOnly: 1 }] };

// ----------------------------------------------------------------------- servicios N2
function servicesView() {
  const root = h('div'); const flash = h('div'); const list = h('div'); let page = 1;
  const f = {
    q: h('input', { type: 'search', placeholder: 'Código o nombre…' }),
    level1_id: h('select'), is_active: h('select', {}, h('option', { value: '' }, 'Estado: todos'), h('option', { value: 'true' }, 'Activos'), h('option', { value: 'false' }, 'Inactivos')),
    class_id: h('select'), criticality_id: h('select'), type_id: h('select'),
    review_status: h('select', {}, h('option', { value: '' }, 'Revisión: todos'), h('option', { value: 'revisar' }, 'Por revisar'), h('option', { value: 'ok' }, 'OK')),
  };
  const fill = async (sel, path, label, all) => {
    const opts = await loadOptions(path, label, { is_active: '' });
    sel.replaceChildren(h('option', { value: '' }, all), ...opts.map(([v, t]) => h('option', { value: v }, t)));
  };
  Promise.all([fill(f.level1_id, '/services/l1', codeName, 'Nivel 1: todos'), fill(f.class_id, '/catalogs/classes', (i) => i.name, 'Clase: todas'),
    fill(f.criticality_id, '/catalogs/criticalities', (i) => i.name, 'Criticidad: todas'), fill(f.type_id, '/catalogs/types', (i) => i.name, 'Tipo: todos')]).catch(() => {});
  const say = (k, t) => flash.replaceChildren(msg(k, t));

  async function load() {
    try {
      const d = await api('GET', '/services/l2?' + qs({ ...Object.fromEntries(Object.entries(f).map(([k, el]) => [k, el.value])), page, per_page: 20 }));
      const rows = d.items.map((s) => h('tr', { class: 'clickable', onclick: () => ficha(s.id) },
        h('td', {}, s.code), h('td', {}, s.name), h('td', {}, s.level1.code), h('td', {}, s.class ? s.class.name : '—'),
        h('td', {}, s.criticality ? s.criticality.name : '—'), h('td', {}, s.type ? s.type.name : '—'),
        h('td', {}, s.activo_excel || (s.activo_raw ? '? ' + s.activo_raw : '—')),
        h('td', {}, s.section ? s.section.name : '—'), h('td', {}, badge(s.is_active)),
        h('td', {}, s.review_status === 'revisar' ? h('span', { class: 'badge warn' }, 'Revisar') : '')));
      list.replaceChildren(h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, h('tr', {},
        ['Código', 'Servicio', 'N1', 'Clase', 'Criticidad', 'Tipo', 'ACTIVO', 'Sección', 'Estado', ''].map((t) => h('th', {}, t)))), h('tbody', {}, rows))),
      h('div', { class: 'pager' }, h('button', { class: 'btn', disabled: page <= 1, onclick: () => { page--; load(); } }, '‹ Anterior'),
        `Página ${d.page} de ${d.pages} · ${d.total} servicio(s)`, h('button', { class: 'btn', disabled: page >= d.pages, onclick: () => { page++; load(); } }, 'Siguiente ›')));
    } catch (e) { list.replaceChildren(msg('error', e.message)); }
  }

  async function ficha(id) {
    const s = await api('GET', '/services/l2/' + id);
    const row = (k, v) => [h('dt', {}, k), h('dd', {}, v == null || v === '' ? '—' : v)];
    const actions = isAdmin() ? h('div', { class: 'bar' },
      h('button', { class: 'btn primary', onclick: () => { m.close(); editForm(s); } }, 'Editar'),
      s.is_active ? h('button', { class: 'btn danger', onclick: async () => { try { await api('DELETE', '/services/l2/' + id); m.close(); say('ok', 'Servicio desactivado.'); load(); } catch (e) { say('error', e.message); } } }, 'Desactivar')
        : h('button', { class: 'btn', onclick: async () => { try { await api('PUT', '/services/l2/' + id, { is_active: true }); m.close(); say('ok', 'Servicio reactivado.'); load(); } catch (e) { say('error', e.message); } } }, 'Reactivar')) : null;
    const m = openModal(`${s.code} · ${s.name}`, h('div', {},
      h('dl', {}, row('Servicio nivel 1', `${s.level1.code} · ${s.level1.name}`), row('Código (original Excel)', s.code_original), row('ACTIVO (Excel)', s.activo_excel || (s.activo_raw ? 'Desconocido: ' + s.activo_raw : null)),
        row('Clase de servicio', s.class && s.class.name), row('Criticidad', s.criticality && s.criticality.name), row('Tipo de servicio', s.type && s.type.name),
        row('Descripción', s.description), row('Métrica', s.metric), row('Mínimo', s.min_value), row('Máximo', s.max_value),
        row('Sección responsable', s.section && s.section.text), row('Usuario responsable', s.responsible && `${s.responsible.name} (${s.responsible.username})`),
        row('Estado', s.is_active ? 'Activo' : 'Inactivo'), row('Revisión', s.review_status), row('Origen en el Excel', `${s.source_sheet || ''} ${s.source_range || ''}`)),
      s.source_notes ? h('details', {}, h('summary', {}, 'Notas de importación'), h('pre', {}, JSON.stringify(s.source_notes, null, 2))) : null,
      actions, h('div', { class: 'bar' }, h('button', { class: 'btn', onclick: () => m.close() }, 'Cerrar'))));
  }

  function editForm(s) {
    const sectionsFn = () => loadOptions('/org/sections', (x) => `${x.code} · ${x.name} (${x.parent_name})`);
    const respFn = async (vals) => {
      const sec = vals && vals.section_id;
      return sec ? loadOptions('/users', (u) => `${u.name} (${u.username})`, { section_id: sec }) : [];
    };
    const base = s ? { code: s.code, name: s.name, level1_id: s.level1.id, activo_excel: s.activo_excel, class_id: s.class && s.class.id, criticality_id: s.criticality && s.criticality.id,
      type_id: s.type && s.type.id, description: s.description, metric: s.metric, min_value: s.min_value, max_value: s.max_value,
      section_id: s.section && s.section.id, responsible_user_id: s.responsible && s.responsible.id, review_status: s.review_status } : { review_status: 'ok' };
    formModal({
      title: s ? 'Editar servicio N2' : 'Nuevo servicio N2', values: base,
      fields: [
        { n: 'code', l: 'Código N2', req: 1, disabled: !!(s && s.code_original) }, { n: 'name', l: 'Nombre', req: 1 },
        { n: 'level1_id', l: 'Servicio nivel 1', req: 1, type: 'select', optionsFn: () => loadOptions('/services/l1', codeName) },
        { n: 'activo_excel', l: 'ACTIVO (S/N)', type: 'select', str: 1, options: [['S', 'S'], ['N', 'N']] },
        { n: 'class_id', l: 'Clase de servicio', type: 'select', optionsFn: () => loadOptions('/catalogs/classes', (i) => i.name) },
        { n: 'criticality_id', l: 'Criticidad', type: 'select', optionsFn: () => loadOptions('/catalogs/criticalities', (i) => i.name) },
        { n: 'type_id', l: 'Tipo de servicio', type: 'select', optionsFn: () => loadOptions('/catalogs/types', (i) => i.name) },
        { n: 'description', l: 'Descripción', type: 'textarea' }, { n: 'metric', l: 'Métrica' },
        { n: 'min_value', l: 'Mínimo', type: 'number' }, { n: 'max_value', l: 'Máximo', type: 'number' },
        { n: 'section_id', l: 'Sección responsable', type: 'select', optionsFn: sectionsFn,
          onchange: async (inputs) => {
            const sel = inputs.responsible_user_id; if (!sel) return;
            const keep = sel.value; const opts = await respFn({ section_id: inputs.section_id.value });
            sel.replaceChildren(h('option', { value: '' }, '— sin responsable —'), ...opts.map(([v, t]) => h('option', { value: v }, t)));
            sel.value = opts.some(([v]) => String(v) === keep) ? keep : (s && s.responsible && inputs.section_id.value == (s.section && s.section.id) ? String(s.responsible.id) : '');
          } },
        { n: 'responsible_user_id', l: 'Usuario responsable (de la sección elegida)', type: 'select', options: [] },
        { n: 'review_status', l: 'Estado de revisión', type: 'select', str: 1, options: [['ok', 'ok'], ['revisar', 'revisar']] },
      ],
      onSubmit: async (p) => {
        if (s) await api('PUT', '/services/l2/' + s.id, p); else await api('POST', '/services/l2', p);
        say('ok', 'Servicio guardado.'); load();
      },
    });
  }

  for (const el of Object.values(f)) el.addEventListener(el.tagName === 'INPUT' ? 'input' : 'change', () => { page = 1; load(); });
  root.append(h('h2', {}, 'Catálogo de servicios (nivel 2)'), flash,
    h('div', { class: 'bar' }, Object.values(f), h('span', { class: 'spacer' }), isAdmin() ? h('button', { class: 'btn primary', onclick: () => editForm(null) }, '+ Nuevo servicio N2') : null), list);
  load();
  return root;
}

// ---------------------------------------------------------------------------- importación
function importView() {
  const root = h('div'); const out = h('div');
  async function load() {
    const d = await api('GET', '/import/runs?per_page=10');
    out.replaceChildren(h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, h('tr', {}, ['#', 'Inicio', 'Estado', 'Creados', 'Actualizados', 'Omitidos', 'Observados', 'N1', 'N2', ''].map((t) => h('th', {}, t)))),
      h('tbody', {}, d.items.map((r) => h('tr', {}, [r.id, r.started_at, r.status, r.created, r.updated, r.skipped, r.observed, r.n1_codes, r.n2_codes].map((v) => h('td', {}, v)),
        h('td', {}, h('button', { class: 'btn', onclick: () => detail(r.id) }, 'Ver incidencias'))))))));
  }
  async function detail(id) {
    const r = await api('GET', '/import/runs/' + id);
    openModal(`Importación #${id}`, h('div', {}, h('pre', {}, JSON.stringify(r.summary, null, 2)),
      h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, h('tr', {}, ['Tipo', 'Código', 'Origen', 'Detalle'].map((t) => h('th', {}, t)))),
        h('tbody', {}, r.observations.map((o) => h('tr', {}, h('td', {}, o.kind), h('td', {}, o.code || ''), h('td', {}, o.row_ref || ''), h('td', {}, o.detail)))))),
      h('div', { class: 'bar' }, h('button', { class: 'btn', onclick: (e) => e.target.closest('.modal-bg').remove() }, 'Cerrar'))));
  }
  const run = h('button', { class: 'btn primary', onclick: async () => {
    run.disabled = true;
    try { const r = await api('POST', '/import/run'); out.before(msg('ok', `Importación #${r.id}: creados ${r.created}, actualizados ${r.updated}, omitidos ${r.skipped}, observados ${r.observed}.`)); await load(); } catch (e) { out.before(msg('error', e.message)); }
    run.disabled = false;
  } }, 'Ejecutar importación del Excel original');
  root.append(h('h2', {}, 'Importación del catálogo'), h('p', { class: 'muted' }, 'Procesa data/CatalogoServicios.xlsx. Es repetible: no duplica registros y deja un reporte de incidencias.'),
    isAdmin() ? run : null, out);
  load();
  return root;
}

// -------------------------------------------------------------------------------- shell
const VIEWS = [
  ['services', 'Servicios', servicesView, false], ['l1', 'Nivel 1', () => crudView(L1CFG), false],
  ['companies', 'Empresas', () => crudView(ORG.companies), false], ['areas', 'Áreas', () => crudView(ORG.areas), false],
  ['departments', 'Departamentos', () => crudView(ORG.departments), false], ['sections', 'Secciones', () => crudView(ORG.sections), false],
  ['positions', 'Puestos', () => crudView(ORG.positions), false], ['users', 'Usuarios', () => crudView(ORG.users), false],
  ...CATALOGS.map(([k, t]) => ['cat_' + k, t, () => crudView(catalogCfg(k, t)), false]),
  ['import', 'Importación', importView, false],
];

function loginView() {
  const user = h('input', { type: 'text', autocomplete: 'username', required: true });
  const pass = h('input', { type: 'password', autocomplete: 'current-password', required: true });
  const err = h('div');
  const go = async () => {
    err.replaceChildren();
    try { const r = await api('POST', '/auth/login', { username: user.value, password: pass.value }); state.user = r.user; state.csrf = r.csrf_token; render(); } catch (e) { err.append(msg('error', e.message)); }
  };
  pass.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
  return h('div', { class: 'login' }, h('h2', {}, 'Catálogo de Servicios de TI'), err,
    h('div', { class: 'field' }, h('label', {}, 'Usuario o correo'), user), h('div', { class: 'field' }, h('label', {}, 'Contraseña'), pass),
    h('button', { class: 'btn primary', onclick: go }, 'Ingresar'));
}

function render() {
  const app = document.getElementById('app');
  if (!state.user) { app.replaceChildren(loginView()); return; }
  const current = VIEWS.find((v) => v[0] === state.view) || VIEWS[0];
  app.replaceChildren(
    h('header', {}, h('h1', {}, 'Catálogo de Servicios'),
      h('nav', {}, VIEWS.map(([k, t]) => h('button', { class: k === current[0] ? 'active' : '', onclick: () => { state.view = k; render(); } }, t))),
      h('span', { class: 'muted' }, `${state.user.name} · ${state.user.role}`),
      h('button', { class: 'btn', onclick: async () => { try { await api('POST', '/auth/logout'); } catch (_) { /* ya cerrada */ } state.user = null; state.csrf = null; render(); } }, 'Salir')),
    h('main', {}, current[2]()));
}

(async () => {
  try { const r = await api('GET', '/auth/me'); state.user = r.user; state.csrf = r.csrf_token; } catch (_) { /* sin sesión */ }
  render();
})();
