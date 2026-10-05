# Reglas de negocio

## Autenticación y autorización
- Login local con usuario/correo (se guarda en minúsculas, único) y contraseña; hash **scrypt con sal** (Werkzeug). Mínimo 8 caracteres.
- Sesión del lado del servidor: tabla `user_sessions` (se guarda SHA-256 del token). La cookie firmada solo lleva el token. **Logout elimina la fila**, de modo que reutilizar la cookie falla. Desactivar al usuario o cambiarle la contraseña revoca sus sesiones.
- Roles: `admin` (escribe usuarios, organización, catálogos, servicios, importación) y `consulta` (solo lectura; nunca ve `password_hash`).
- Defecto-denegar: sin sesión → 401; escritura sin ser admin → 403; sin CSRF válido → 403.
- Protecciones: no se puede desactivar a uno mismo ni al último admin activo.

## Jerarquía organizacional
Empresa → Área → Departamento → Sección → Puesto → Usuario. Un único padre por registro. Código de empresa único global;
códigos subordinados únicos **dentro de su padre** (sin distinguir mayúsculas). La empresa de un usuario se deriva de su puesto.
El padre de una unidad existente no se puede cambiar (limitación declarada); un usuario sí puede cambiar de puesto.

## Política de bajas (desactivación lógica)
1. Nunca se borra información.
2. Desactivar con dependientes activos → 409 `has_dependents`. Con `?cascade=true` se desactivan **explícitamente** todos los dependientes y la respuesta informa cuántos.
3. Una sección o usuario con **servicios N2 activos asignados** no puede desactivarse (ni en cascada): hay que reasignar → 409 `has_services`.
4. No se crean asociaciones nuevas con padres inactivos (409 `inactive_parent`). Reactivar exige padre activo.
5. Catálogos (clase/criticidad/tipo): baja lógica; los servicios existentes conservan su referencia, pero no se asigna un valor inactivo a servicios nuevos o a un campo cambiado.
6. Desactivar un N1 con N2 activos exige confirmación en cascada.

## Catálogo de servicios
- N1 y N2 con código único cada uno; N2 pertenece a un N1. Se conservan todos los campos del Excel.
- `mínimo ≤ máximo` cuando ambos existen; ausente ≠ 0.
- `activo_excel` ∈ {S, N, NULL}; valores raros se guardan en `activo_raw`. `is_active` es la baja lógica del sistema (distinta de ACTIVO del Excel).
- `review_status` = `revisar` cuando faltan ACTIVO/clase/criticidad/tipo, hay conflicto o valor fuera de catálogo.
- Responsable: el N2 se asigna a una **sección**; el usuario responsable (opcional) debe pertenecer a esa sección, estar activo, y requiere sección.
- Códigos de servicios importados no se editan (rompería la idempotencia de la importación).
- Reimportar actualiza solo campos provenientes del Excel; no toca sección, responsable ni `is_active`.
