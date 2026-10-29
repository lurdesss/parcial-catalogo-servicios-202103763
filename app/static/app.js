'use strict';
// Todo el contenido proveniente del servidor (incluido el del Excel) se inserta con nodos de texto, nunca con innerHTML.
const state = { user: null, csrf: null, view: 'services' };
const isAdmin = () => state.user && state.user.role === 'admin';
const hasServiceRole = (code) => !!(state.user && state.user.service_roles && state.user.service_roles.includes(code));
const isAgente = () => isAdmin() || hasServiceRole('agente');

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

// ------------------------------------------------------------------------------ CMDB
const CICLASSES_CFG = { title: 'Clases de CI', path: '/cmdb/ci-classes',
  cols: [['code', 'Código'], ['name', 'Nombre'], ['parent_name', 'Clase padre'], ['requires_ip', 'Requiere IP', (i) => (i.requires_ip ? 'Sí' : 'No')], activeCol],
  fields: [{ n: 'code', l: 'Código', req: 1 }, { n: 'name', l: 'Nombre', req: 1 },
    { n: 'parent_id', l: 'Clase padre', type: 'select', optionsFn: () => loadOptions('/cmdb/ci-classes', codeName, { per_page: 200 }) },
    { n: 'requires_ip', l: 'Requiere IP', type: 'checkbox' }, { n: 'is_active', l: 'Activo', type: 'checkbox', editOnly: 1 }] };
const LOCATIONS_CFG = { title: 'Ubicaciones', path: '/cmdb/locations', cols: [['code', 'Código'], ['name', 'Nombre'], activeCol],
  fields: [{ n: 'code', l: 'Código', req: 1 }, { n: 'name', l: 'Nombre', req: 1 }, { n: 'is_active', l: 'Activo', type: 'checkbox', editOnly: 1 }] };

function devicesView() {
  const root = h('div'); const flash = h('div'); const list = h('div'); let page = 1;
  const say = (k, t) => flash.replaceChildren(msg(k, t));
  const f = {
    q: h('input', { type: 'search', placeholder: 'Etiqueta o nombre…' }),
    ci_class_id: h('select'), status: h('select', {}, h('option', { value: '' }, 'Estado: todos'),
      ...['activo', 'inactivo', 'retirado'].map((s) => h('option', { value: s }, s))),
  };
  loadOptions('/cmdb/ci-classes', codeName, { per_page: 200 }).then((opts) =>
    f.ci_class_id.replaceChildren(h('option', { value: '' }, 'Clase: todas'), ...opts.map(([v, t]) => h('option', { value: v }, t)))).catch(() => {});

  async function load() {
    try {
      const d = await api('GET', '/cmdb/devices?' + qs({ ...Object.fromEntries(Object.entries(f).map(([k, el]) => [k, el.value])), page, per_page: 25 }));
      const rows = d.items.map((dev) => h('tr', { class: 'clickable', onclick: () => ficha(dev.id) },
        h('td', {}, dev.asset_tag), h('td', {}, dev.name), h('td', {}, dev.ci_class ? dev.ci_class.name : '—'),
        h('td', {}, dev.location ? dev.location.name : '—'), h('td', {}, dev.owner ? dev.owner.name : '—'),
        h('td', {}, dev.status), h('td', {}, dev.ip_address || '—'), h('td', {}, badge(dev.is_active))));
      list.replaceChildren(h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, h('tr', {},
        ['Etiqueta', 'Nombre', 'Clase', 'Ubicación', 'Propietario', 'Estado', 'IP', 'Activo'].map((t) => h('th', {}, t)))), h('tbody', {}, rows))),
      h('div', { class: 'pager' }, h('button', { class: 'btn', disabled: page <= 1, onclick: () => { page--; load(); } }, '‹ Anterior'),
        `Página ${d.page} de ${d.pages} · ${d.total} dispositivo(s)`, h('button', { class: 'btn', disabled: page >= d.pages, onclick: () => { page++; load(); } }, 'Siguiente ›')));
    } catch (e) { list.replaceChildren(msg('error', e.message)); }
  }

  async function ficha(id) {
    const [dev, rels, impacto, servicios] = await Promise.all([
      api('GET', '/cmdb/devices/' + id), api('GET', `/cmdb/devices/${id}/relaciones`),
      api('GET', `/cmdb/devices/${id}/impacto`), api('GET', `/cmdb/devices/${id}/servicios`)]);
    const row = (k, v) => [h('dt', {}, k), h('dd', {}, v == null || v === '' ? '—' : v)];
    const attrs = Object.entries(dev.attributes || {}).map(([k, v]) => `${k}: ${v}`).join(' · ') || '—';
    const m = openModal(`${dev.asset_tag} · ${dev.name}`, h('div', {},
      h('dl', {}, row('Clase', dev.ci_class && dev.ci_class.name), row('Estado', dev.status), row('Activo', dev.is_active ? 'Sí' : 'No'),
        row('Ubicación', dev.location && dev.location.name), row('Propietario', dev.owner && dev.owner.name),
        row('IP', dev.ip_address), row('N.º de serie', dev.serial_number), row('Atributos técnicos', attrs)),
      h('h3', {}, 'Relaciones técnicas (Grafo CMDB)'),
      h('ul', {}, rels.map((r) => h('li', {}, `${r.from_device.asset_tag} —${r.relation_type}→ ${r.to_device.asset_tag}`))),
      isAdmin() ? h('div', { class: 'bar' },
        h('button', { class: 'btn', onclick: () => relacionForm(dev, () => { m.close(); ficha(id); }) }, '+ Agregar relación')) : null,
      h('h3', {}, 'Recorrido de dependencias (impacto si este CI falla)'),
      h('ul', {}, impacto.dispositivos_relacionados.map((d2) => h('li', {}, `profundidad ${d2.profundidad} · ${d2.relation_type} · CI #${d2.device_id}`))),
      h('p', { class: 'muted' }, impacto.servicios_potencialmente_afectados.length
        ? 'Servicios potencialmente afectados (no implica interrupción confirmada):' : 'No hay servicios vinculados a este CI ni a sus dependientes.'),
      h('ul', {}, impacto.servicios_potencialmente_afectados.map((s) => h('li', {}, `${s.code} · ${s.name}`))),
      h('h3', {}, 'Servicios vinculados'),
      h('ul', {}, servicios.map((s) => h('li', {}, `${s.code} · ${s.name}`))),
      h('div', { class: 'bar' }, h('button', { class: 'btn', onclick: () => m.close() }, 'Cerrar'))));
  }

  function relacionForm(dev, onDone) {
    formModal({
      title: `Nueva relación desde ${dev.asset_tag}`,
      fields: [
        { n: 'to_device_id', l: 'CI relacionado (etiqueta o nombre)', req: 1, type: 'select',
          optionsFn: async () => (await api('GET', '/cmdb/devices?per_page=200')).items.filter((x) => x.id !== dev.id).map((x) => [x.id, `${x.asset_tag} · ${x.name}`]) },
        { n: 'relation_type', l: 'Tipo de relación', req: 1, type: 'select', str: 1,
          options: [['depende_de', 'depende_de (no admite ciclos)'], ['alojado_en', 'alojado_en (no admite ciclos)'], ['conectado_a', 'conectado_a (admite ciclos)']] },
      ],
      onSubmit: async (p) => { await api('POST', `/cmdb/devices/${dev.id}/relaciones`, p); onDone(); },
    });
  }

  for (const el of Object.values(f)) el.addEventListener(el.tagName === 'INPUT' ? 'input' : 'change', () => { page = 1; load(); });
  root.append(h('h2', {}, 'CMDB — Dispositivos'),
    h('p', { class: 'muted' }, 'Generados con `flask generate-cmdb` (reproducible por semilla; ver docs/MODELO.md).'), flash,
    h('div', { class: 'bar' }, Object.values(f)), list);
  load();
  return root;
}

// ----------------------------------------------------------------------- colas (Service Desk)
function queuesView() {
  const root = h('div'); const flash = h('div'); const list = h('div');
  const say = (k, t) => flash.replaceChildren(msg(k, t));
  async function load() {
    const d = await api('GET', '/queues?per_page=100');
    const rows = d.items.map((qu) => h('tr', {}, h('td', {}, qu.code), h('td', {}, qu.name), h('td', {}, qu.process.name),
      h('td', {}, qu.support_level), h('td', {}, badge(qu.is_active)),
      h('td', {}, isAdmin() ? h('button', { class: 'btn', onclick: () => permisos(qu) }, 'Permisos') : null)));
    list.replaceChildren(h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, h('tr', {},
      ['Código', 'Nombre', 'Proceso', 'Nivel', 'Activa', ''].map((t) => h('th', {}, t)))), h('tbody', {}, rows))));
  }
  async function permisos(qu) {
    const full = await api('GET', '/queues/' + qu.id);
    const rows = full.permissions.map((p) => h('tr', {}, h('td', {}, p.principal_role || (p.principal_user && p.principal_user.name)),
      ['can_view', 'can_work', 'can_transfer', 'can_approve', 'can_manage'].map((k) => h('td', {}, p[k] ? '✓' : '')),
      h('td', {}, h('button', { class: 'btn danger', onclick: async () => { await api('DELETE', `/queues/${qu.id}/permisos/${p.id}`); m.close(); permisos(qu); } }, 'Quitar'))));
    const add = h('button', { class: 'btn primary', onclick: () => formModal({
      title: 'Agregar permiso', fields: [
        { n: 'principal_role', l: 'Rol (o deje vacío y use usuario abajo)', type: 'select', str: 1,
          options: [['admin', 'admin'], ['consulta', 'consulta'], ['solicitante', 'solicitante'], ['agente', 'agente'], ['aprobador', 'aprobador']] },
        { n: 'principal_user_id', l: 'Usuario (alternativa a rol)', type: 'select', optionsFn: () => loadOptions('/users', (u) => `${u.name} (${u.username})`) },
        { n: 'can_view', l: 'Consultar', type: 'checkbox' }, { n: 'can_work', l: 'Atender', type: 'checkbox' },
        { n: 'can_transfer', l: 'Transferir', type: 'checkbox' }, { n: 'can_approve', l: 'Aprobar', type: 'checkbox' },
        { n: 'can_manage', l: 'Administrar', type: 'checkbox' },
      ], onSubmit: async (p) => { await api('POST', `/queues/${qu.id}/permisos`, p); m.close(); permisos(qu); },
    }) }, '+ Agregar permiso');
    const m = openModal(`Permisos de ${full.code}`, h('div', {}, h('div', { class: 'table-wrap' },
      h('table', {}, h('thead', {}, h('tr', {}, ['Principal', 'Ver', 'Atender', 'Transferir', 'Aprobar', 'Administrar', ''].map((t) => h('th', {}, t)))),
        h('tbody', {}, rows))), h('div', { class: 'bar' }, add), h('div', { class: 'bar' }, h('button', { class: 'btn', onclick: () => m.close() }, 'Cerrar'))));
  }
  root.append(h('h2', {}, 'Colas'), flash,
    isAdmin() ? h('div', { class: 'bar' }, h('button', { class: 'btn primary', onclick: () => formModal({
      title: 'Nueva cola', fields: [{ n: 'code', l: 'Código', req: 1 }, { n: 'name', l: 'Nombre', req: 1 },
        { n: 'process_id', l: 'Proceso', req: 1, type: 'select', optionsFn: () => api('GET', '/processes').then((ps) => ps.map((p) => [p.id, p.name])) },
        { n: 'support_level', l: 'Nivel de soporte', type: 'select', str: 1, options: [['nivel0', 'nivel0'], ['nivel1', 'nivel1'], ['nivel2', 'nivel2'], ['nivel3', 'nivel3'], ['nivel4', 'nivel4']] }],
      onSubmit: async (p) => { await api('POST', '/queues', p); say('ok', 'Cola creada.'); load(); },
    }) }, '+ Nueva cola')) : null, list);
  load();
  return root;
}

// ---------------------------------------------------------------------- procesos (Grafo 2)
function processesView() {
  const root = h('div'); const out = h('div');
  const sel = h('select');
  api('GET', '/processes').then((ps) => {
    sel.replaceChildren(...ps.map((p) => h('option', { value: p.code }, p.name)));
    load(ps[0].code);
  });
  async function load(code) {
    const g = await api('GET', `/processes/${code}/grafo`);
    out.replaceChildren(
      h('h3', {}, 'Estados'),
      h('ul', {}, g.states.map((s) => h('li', {}, `${s.code} — ${s.name}` + (s.is_initial ? ' (inicial)' : '') + (s.is_final ? ' (final)' : '')))),
      h('h3', {}, 'Transiciones (aristas del grafo)'),
      h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, h('tr', {}, ['Desde', 'Acción', 'Hacia', 'Permiso requerido'].map((t) => h('th', {}, t)))),
        h('tbody', {}, g.transitions.map((t) => h('tr', {}, h('td', {}, t.from), h('td', {}, t.action), h('td', {}, t.to), h('td', {}, t.required_perm || '—')))))));
  }
  sel.addEventListener('change', () => load(sel.value));
  root.append(h('h2', {}, 'Procesos — Grafo de estados y transiciones'),
    h('p', { class: 'muted' }, 'Cada ticket solo puede avanzar por una arista existente de este grafo (ver app/workflow.py).'),
    h('div', { class: 'bar' }, sel), out);
  return root;
}

// -------------------------------------------------------------------------------- tickets
const PROCESS_DETAIL_FIELDS = {
  incidentes: [{ n: 'category', l: 'Categoría (I0–I6)', req: 1, type: 'select', str: 1, options: ['I0', 'I1', 'I2', 'I3', 'I4', 'I5', 'I6'].map((c) => [c, c]) },
    { n: 'redundancy_available', l: '¿Existe redundancia disponible?', type: 'checkbox' }],
  eventos: [{ n: 'category', l: 'Categoría (E0–E3)', req: 1, type: 'select', str: 1, options: ['E0', 'E1', 'E2', 'E3'].map((c) => [c, c]) }],
  cambios: [{ n: 'change_type', l: 'Tipo de cambio', type: 'select', str: 1, options: [['normal', 'normal'], ['estandar', 'estándar'], ['emergencia', 'emergencia']] },
    { n: 'risk_level', l: 'Nivel de riesgo' }, { n: 'test_plan', l: 'Plan de pruebas', type: 'textarea' }, { n: 'rollback_plan', l: 'Plan de reversión', type: 'textarea' }],
  problemas: [{ n: 'root_cause', l: 'Causa raíz (si se conoce)', type: 'textarea' }],
  accesos: [{ n: 'beneficiary_user_id', l: 'Usuario beneficiario', req: 1, type: 'select', optionsFn: () => loadOptions('/users', (u) => `${u.name} (${u.username})`) },
    { n: 'resource', l: 'Recurso solicitado', req: 1 }, { n: 'permission_requested', l: 'Permiso solicitado' }],
  nuevos_servicios: [{ n: 'proposed_name', l: 'Nombre del servicio propuesto', req: 1 },
    { n: 'proposed_level1_id', l: 'Servicio de nivel 1', req: 1, type: 'select', optionsFn: () => loadOptions('/services/l1', codeName) }],
  servicios_tecnologia: [],
};

function ticketCreateModal(onDone) {
  // El formulario genérico (formModal) no soporta cambiar de campos dinámicamente según otro
  // campo, así que primero se elige el proceso y luego se abre un formulario propio de ese proceso.
  const pickProcess = h('select', {}, Object.keys(PROCESS_DETAIL_FIELDS).map((c) => h('option', { value: c }, c)));
  const go = () => { m.close(); ticketCreateFormFor(pickProcess.value, onDone); };
  const m = openModal('Nuevo ticket', h('div', {}, h('div', { class: 'field' }, h('label', {}, 'Proceso'), pickProcess),
    h('div', { class: 'bar' }, h('button', { class: 'btn primary', onclick: go }, 'Continuar'), h('button', { class: 'btn', onclick: () => m.close() }, 'Cancelar'))));
}

function ticketCreateFormFor(processCode, onDone) {
  formModal({
    title: `Nuevo ticket — ${processCode}`,
    fields: [
      { n: 'title', l: 'Título', req: 1 }, { n: 'description', l: 'Descripción', type: 'textarea' },
      { n: 'queue_id', l: 'Cola', req: 1, type: 'select', optionsFn: () => api('GET', '/queues?per_page=200').then((d) => d.items.filter((q) => q.process.code === processCode).map((q) => [q.id, `${q.code} · ${q.name}`])) },
      { n: 'service_l2_id', l: 'Servicio (nivel 2)', req: processCode !== 'accesos' && processCode !== 'nuevos_servicios', type: 'select', optionsFn: () => loadOptions('/services/l2', codeName) },
      { n: 'priority', l: 'Prioridad', type: 'select', str: 1, options: [['baja', 'baja'], ['media', 'media'], ['alta', 'alta']] },
      { n: 'channel', l: 'Canal', type: 'select', str: 1, options: [['portal', 'portal'], ['telefono', 'teléfono'], ['correo', 'correo']] },
      ...(PROCESS_DETAIL_FIELDS[processCode] || []).map((f) => ({ ...f, n: 'detail.' + f.n })),
    ],
    onSubmit: async (p) => {
      const detail = {};
      for (const k of Object.keys(p)) if (k.startsWith('detail.')) { detail[k.slice(7)] = p[k]; delete p[k]; }
      await api('POST', '/tickets', { ...p, process_code: processCode, detail });
      onDone();
    },
  });
}

function ticketsView() {
  const root = h('div'); const flash = h('div'); const list = h('div'); let page = 1;
  const say = (k, t) => flash.replaceChildren(msg(k, t));
  const f = {
    q: h('input', { type: 'search', placeholder: 'Número o título…' }),
    state: h('input', { placeholder: 'Estado…' }),
    priority: h('select', {}, h('option', { value: '' }, 'Prioridad: todas'), ...['baja', 'media', 'alta'].map((p) => h('option', { value: p }, p))),
  };
  const soloMios = h('input', { type: 'checkbox', id: 'solo-mios' });
  async function load() {
    try {
      const params = { ...Object.fromEntries(Object.entries(f).map(([k, el]) => [k, el.value])), page, per_page: 20 };
      if (soloMios.checked) params.requester_user_id = state.user.id;
      const d = await api('GET', '/tickets?' + qs(params));
      const rows = d.items.map((t) => h('tr', { class: 'clickable', onclick: () => ficha(t.id) },
        h('td', {}, t.number), h('td', {}, t.title), h('td', {}, t.process.name), h('td', {}, t.queue.name),
        h('td', {}, t.state), h('td', {}, t.priority), h('td', {}, t.assignee ? t.assignee.name : '—'),
        h('td', {}, t.requester ? t.requester.name : '—'), h('td', {}, (t.created_at || '').slice(0, 16).replace('T', ' '))));
      list.replaceChildren(h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, h('tr', {},
        ['Número', 'Título', 'Proceso', 'Cola', 'Estado', 'Prioridad', 'Responsable', 'Solicitante', 'Creado'].map((t) => h('th', {}, t)))), h('tbody', {}, rows))),
      h('div', { class: 'pager' }, h('button', { class: 'btn', disabled: page <= 1, onclick: () => { page--; load(); } }, '‹ Anterior'),
        `Página ${d.page} de ${d.pages} · ${d.total} ticket(s)`, h('button', { class: 'btn', disabled: page >= d.pages, onclick: () => { page++; load(); } }, 'Siguiente ›')));
    } catch (e) { list.replaceChildren(msg('error', e.message)); }
  }

  async function ficha(id) {
    const t = await api('GET', '/tickets/' + id);
    const graph = await api('GET', `/processes/${t.process.code}/grafo`).catch(() => ({ transitions: [] }));
    const validActions = graph.transitions.filter((tr) => tr.from === t.state);
    const row = (k, v) => [h('dt', {}, k), h('dd', {}, v == null || v === '' ? '—' : v)];
    const detailRows = t.detail ? Object.entries(t.detail).map(([k, v]) => row(k, typeof v === 'object' ? JSON.stringify(v) : v)).flat() : [];

    const acciones = h('div', { class: 'bar' },
      !t.assignee ? h('button', { class: 'btn', onclick: async () => { try { await api('POST', `/tickets/${id}/tomar`); m.close(); say('ok', 'Ticket tomado.'); ficha(id); } catch (e) { say('error', e.message); } } }, 'Tomar') : null,
      h('button', { class: 'btn', onclick: () => transferirForm(t, () => { m.close(); ficha(id); }) }, 'Transferir'),
      ...validActions.map((tr) => h('button', { class: 'btn primary', onclick: async () => {
        try { await api('POST', `/tickets/${id}/transicion`, { action: tr.action }); m.close(); say('ok', `Acción «${tr.action}» aplicada.`); load(); ficha(id); }
        catch (e) { say('error', e.message); }
      } }, tr.action)));

    const comentarios = h('div', {}, t.comments.map((c) => h('div', { class: 'comment' },
      h('b', {}, c.author ? c.author.name : '—'), ' · ', h('span', { class: 'muted' }, c.visibility), ' · ', h('span', { class: 'muted' }, (c.created_at || '').slice(0, 16).replace('T', ' ')),
      h('p', {}, c.body))));
    const nuevoComentario = h('textarea', { placeholder: 'Nuevo comentario…' });
    const visibilidad = h('select', {}, h('option', { value: 'publico' }, 'Público (visible al solicitante)'), h('option', { value: 'interno' }, 'Nota interna'));
    const enviarComentario = h('button', { class: 'btn', onclick: async () => {
      try { await api('POST', `/tickets/${id}/comentarios`, { body: nuevoComentario.value, visibility: visibilidad.value }); m.close(); ficha(id); } catch (e) { say('error', e.message); }
    } }, 'Agregar comentario');

    const adjuntos = h('ul', {}, t.attachments.map((a) => h('li', {}, h('a', { href: `/api/tickets/${id}/adjuntos/${a.id}/descarga` }, a.filename), ` (${a.content_type}, ${a.size_bytes} bytes)`)));
    const fileInput = h('input', { type: 'file' });
    const subirAdjunto = h('button', { class: 'btn', onclick: async () => {
      const file = fileInput.files[0]; if (!file) return;
      const b64 = await new Promise((res) => { const r = new FileReader(); r.onload = () => res(r.result.split(',')[1]); r.readAsDataURL(file); });
      try { await api('POST', `/tickets/${id}/adjuntos`, { filename: file.name, content_type: file.type || 'application/octet-stream', content_base64: b64 }); m.close(); ficha(id); }
      catch (e) { say('error', e.message); }
    } }, 'Subir adjunto');

    const m = openModal(`${t.number} · ${t.title}`, h('div', {},
      h('dl', {}, row('Proceso', t.process.name), row('Cola', t.queue.name), row('Estado', t.state), row('Prioridad', t.priority),
        row('Servicio', t.service_l2 && `${t.service_l2.code} · ${t.service_l2.name}`), row('Solicitante', t.requester && t.requester.name),
        row('Responsable', t.assignee && t.assignee.name), row('Canal', t.channel), row('Descripción', t.description),
        ...detailRows, row('Creado', t.created_at), row('Resuelto', t.resolved_at), row('Cerrado', t.closed_at)),
      h('h3', {}, 'Acciones'), acciones,
      h('h3', {}, 'Comentarios'), comentarios, h('div', { class: 'field' }, h('label', {}, 'Nuevo comentario'), nuevoComentario, visibilidad, enviarComentario),
      h('h3', {}, 'Adjuntos'), adjuntos, h('div', { class: 'bar' }, fileInput, subirAdjunto),
      h('h3', {}, 'Bitácora'), h('ul', {}, t.history.slice().reverse().map((hh) => h('li', {}, `${(hh.created_at || '').slice(0, 16).replace('T', ' ')} · ${hh.action}` + (hh.field ? ` (${hh.field})` : '') + (hh.new_value ? ` → ${hh.new_value}` : '')))),
      h('div', { class: 'bar' }, h('button', { class: 'btn', onclick: () => m.close() }, 'Cerrar'))));
  }

  function transferirForm(t, onDone) {
    formModal({
      title: `Transferir ${t.number}`,
      fields: [{ n: 'queue_id', l: 'Cola destino', req: 1, type: 'select',
        optionsFn: () => api('GET', '/queues?per_page=200').then((d) => d.items.filter((q) => q.process.code === t.process.code && q.id !== t.queue.id).map((q) => [q.id, `${q.code} · ${q.name}`])) },
        { n: 'reason', l: 'Motivo' }],
      onSubmit: async (p) => { await api('POST', `/tickets/${t.id}/transferir`, p); onDone(); },
    });
  }

  for (const el of Object.values(f)) el.addEventListener(el.tagName === 'INPUT' ? 'input' : 'change', () => { page = 1; load(); });
  soloMios.addEventListener('change', () => { page = 1; load(); });
  root.append(h('h2', {}, 'Tickets'), flash,
    h('div', { class: 'bar' }, Object.values(f), h('label', {}, soloMios, ' Solo mis tickets (portal del solicitante)'),
      h('span', { class: 'spacer' }), h('button', { class: 'btn primary', onclick: () => ticketCreateModal(() => load()) }, '+ Nuevo ticket')),
    list);
  load();
  return root;
}

// --------------------------------------------------------------------------- tablero
function dashboardView() {
  const root = h('div'); const out = h('div');
  async function load() {
    const [resumen, ind] = await Promise.all([api('GET', '/dashboard/resumen'), api('GET', '/dashboard/indicadores')]);
    const tbl = (obj, cols) => h('div', { class: 'table-wrap' }, h('table', {}, h('thead', {}, h('tr', {}, cols.map((c) => h('th', {}, c)))),
      h('tbody', {}, Object.entries(obj).map(([k, v]) => h('tr', {}, h('td', {}, k), h('td', {}, v))))));
    const resumenTbl = h('div', { class: 'table-wrap' }, h('table', {}, h('tbody', {},
      h('tr', {}, h('td', {}, 'Total de tickets'), h('td', {}, resumen.total)),
      h('tr', {}, h('td', {}, 'Abiertos'), h('td', {}, resumen.abiertos)),
      h('tr', {}, h('td', {}, 'Antigüedad promedio (h, abiertos)'), h('td', {}, ind.antiguedad_horas_promedio_abiertos ?? '—')),
      h('tr', {}, h('td', {}, 'Primera atención promedio (h)'), h('td', {}, ind.primera_atencion_horas_promedio ?? '—')),
      h('tr', {}, h('td', {}, 'Resolución promedio (h)'), h('td', {}, ind.resolucion_horas_promedio ?? '—')),
      h('tr', {}, h('td', {}, 'Cumplimiento de objetivo'), h('td', {}, ind.cumplimiento_objetivo_pct != null ? ind.cumplimiento_objetivo_pct + '%' : '—')),
      h('tr', {}, h('td', {}, 'Tiempo usado para los cálculos'), h('td', {}, ind.tiempo)))));
    out.replaceChildren(
      h('div', { class: 'bar' }, resumenTbl),
      h('h3', {}, 'Por estado'), tbl(resumen.por_estado, ['Estado', 'Tickets']),
      h('h3', {}, 'Por prioridad'), tbl(resumen.por_prioridad, ['Prioridad', 'Tickets']),
      h('h3', {}, 'Por cola'), tbl(resumen.por_cola, ['Cola', 'Tickets']),
      h('h3', {}, 'Por proceso'), tbl(resumen.por_proceso, ['Proceso', 'Tickets']));
  }
  root.append(h('h2', {}, 'Tablero de indicadores'),
    h('p', { class: 'muted' }, 'Cálculo de cada indicador documentado en app/api/dashboard.py y docs/PROCESOS.md.'), out);
  load();
  return root;
}

// ------------------------------------------------------------------------------- FAQ (nivel 0)
const FAQ = [
  ['¿Cómo reinicio mi contraseña?', 'Solicite un acceso (proceso "Gestión de accesos") indicando el recurso "Contraseña de usuario"; un aprobador autorizado la restablecerá.'],
  ['¿Cómo reporto una falla?', 'Cree un ticket del proceso "Gestión de incidentes" desde Tickets → Nuevo ticket, indicando el servicio afectado y la categoría (I0–I6) según la interrupción.'],
  ['¿Qué diferencia hay entre un incidente y un problema?', 'Un incidente es una interrupción puntual; un problema es la causa raíz detrás de uno o varios incidentes repetidos.'],
  ['¿Cómo solicito un servicio nuevo?', 'Use el proceso "Gestión de nuevos servicios"; se analiza viabilidad antes de aprobarse y crear o vincular el servicio en el catálogo.'],
  ['¿Dónde veo mis tickets?', 'En Tickets, active la casilla "Solo mis tickets" (portal del solicitante).'],
];
function faqView() {
  return h('div', {}, h('h2', {}, 'Base de conocimiento / FAQ (nivel 0 — autoservicio)'),
    h('p', { class: 'muted' }, 'Autoservicio simple; no requiere crear un ticket para resolver estas dudas comunes.'),
    h('div', {}, FAQ.map(([q, a]) => h('details', {}, h('summary', {}, q), h('p', {}, a)))));
}

// -------------------------------------------------------------------------------- shell
const VIEWS = [
  ['services', 'Servicios', servicesView, false], ['l1', 'Nivel 1', () => crudView(L1CFG), false],
  ['companies', 'Empresas', () => crudView(ORG.companies), false], ['areas', 'Áreas', () => crudView(ORG.areas), false],
  ['departments', 'Departamentos', () => crudView(ORG.departments), false], ['sections', 'Secciones', () => crudView(ORG.sections), false],
  ['positions', 'Puestos', () => crudView(ORG.positions), false], ['users', 'Usuarios', () => crudView(ORG.users), false],
  ...CATALOGS.map(([k, t]) => ['cat_' + k, t, () => crudView(catalogCfg(k, t)), false]),
  ['import', 'Importación', importView, false],
  ['faq', 'FAQ', faqView, false],
  ['tickets', 'Tickets', ticketsView, false],
  ['dashboard', 'Tablero', dashboardView, false],
  ['processes', 'Procesos', processesView, false],
  ['queues', 'Colas', queuesView, false],
  ['devices', 'CMDB — Dispositivos', devicesView, false],
  ['ci_classes', 'CMDB — Clases', () => crudView(CICLASSES_CFG), false],
  ['locations', 'CMDB — Ubicaciones', () => crudView(LOCATIONS_CFG), false],
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
