# Plan de pruebas y resultados — Sprint 1

Fecha: 7 de octubre de 2026. Estado: implementación y verificación técnica terminadas; aceptación humana pendiente.

## Objetivo, alcance y entorno

Se verifica el acceso, la gestión de vecinos y el recorrido completo de una solicitud municipal, incluida la separación por delegación y la trazabilidad. Se utiliza Python 3.12.14, Django 5.2.18, PostgreSQL 17 y django-axes 7.1.0. Las pruebas de navegador utilizan Chromium local y Playwright 1.63.0; la revisión automática de accesibilidad utiliza axe-core 4.10.3.

No se evalúan agenda y reportes, aún pendientes de implementación. No se realiza una auditoría integral de producción, certificación ISO ni una validación jurídica. Los datos utilizados son ficticios.

## Casos y criterios de aceptación

| ID | Tipo | Caso | Resultado esperado | Resultado observado |
|---|---|---|---|---|
| CP-01 | Integración | Acceso válido, salida y sesión | Acceso autenticado y cierre de sesión | Aprobado |
| CP-02 | Seguridad | Credenciales erróneas y repetición | Mensaje seguro y bloqueo después de cinco fallos | Aprobado |
| CP-03 | Unidad | RUT normalizado y dígito verificador | Aceptar RUT válido y rechazar inválidos | Aprobado |
| CP-04 | Integración | RUT duplicado y contacto faltante | Rechazo controlado; unicidad por delegación | Aprobado |
| CP-05 | Seguridad | Manipular delegación y vecino seleccionado | No transferir ni crear registros fuera del ámbito autorizado | Aprobado |
| CP-06 | Funcional | Ciclo completo de solicitud | Ingresada, asignada, en atención, resuelta y cerrada | Aprobado |
| CP-07 | Seguridad | Funcionario asigna o cierra; colega inicia atención | Denegar operaciones sin permiso | Aprobado |
| CP-08 | Integración | Responsable ajeno o inactivo | Rechazar asignación | Aprobado |
| CP-09 | Unidad/integración | Saltos de estado o motivo vacío | Rechazar transición sin alterar registros | Aprobado |
| CP-10 | Integración | Fallo al guardar auditoría | Revertir estado, observación e historial | Aprobado |
| CP-11 | Concurrencia | Dos asignaciones simultáneas | Una confirmación, un conflicto y un solo cambio persistido | Aprobado en PostgreSQL |
| CP-12 | Seguridad | Listados y detalles de otra delegación | No revelar datos; responder 404 al detalle ajeno | Aprobado |
| CP-13 | Seguridad | CSRF y mutaciones mediante GET | Rechazar POST sin token y GET de modificación | Aprobado |
| CP-14 | Seguridad | Contenido XSS y búsqueda SQL manipulada | Escapar HTML; consulta sin inyección | Aprobado |
| CP-15 | Seguridad | Auditoría y administración | Solo administrador; auditoría sin edición desde interfaz | Aprobado |
| CP-16 | Integración | Delegación inactiva y cambio del responsable | Rechazar operaciones incompatibles con el ámbito | Aprobado |
| CP-17 | Funcional | Observaciones y solicitud cerrada | Auditar observaciones y bloquear nuevas tras cierre | Aprobado |
| CP-18 | Usabilidad | Error de formulario de transición | Conservar entradas y mostrar errores | Aprobado |
| CP-19 | Navegador | Registro y recorrido con funcionario/delegado | Completar ciclo y mostrar cuatro cambios | Aprobado |
| CP-20 | Navegador | PC/tablet y enlace de salto | Sin desborde de página y enlace operable con teclado | Aprobado |
| CP-21 | Accesibilidad | Siete vistas, dos tamaños | Sin infracciones automáticas WCAG A/AA evaluadas | Aprobado; revisión humana pendiente |
| CP-22 | Configuración | Migrations y comprobación Django | Sin cambios de modelo pendientes ni errores | Aprobado |
| CP-23 | Repetibilidad | Reinstalación y datos demo | Conservar datos y contraseñas; no duplicar semillas | Aprobado |
| CP-24 | Aceptación humana | Uso por funcionario y delegado reales | Confirmar claridad y adecuación del flujo | Pendiente de revisión del usuario |

Los IDs agrupan escenarios; no corresponden uno a uno a métodos de prueba. La suite ejecutó **38 pruebas**, con **38 aprobadas**, sin fallos ni omisiones. El recorrido de navegador completó operaciones reales contra el servidor y la base local. Se revisaron 14 combinaciones de vista y tamaño: 1440×1024 y 768×1024, sin infracciones automáticas ni desborde horizontal de página. Las tablas pueden desplazarse dentro de su contenedor.

Se verificó la configuración de producción mediante `DJANGO_DEBUG=false .venv/bin/python manage.py check --deploy`, sin advertencias. Esto valida opciones de Django, no un despliegue HTTPS real. La configuración de desarrollo conserva HTTP y depuración, por lo que la misma comprobación sin esa variable presenta cinco advertencias esperadas. La aplicación no se declara lista para producción.

## Ejecución y evidencias

```sh
.venv/bin/python manage.py test apps
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
DJANGO_DEBUG=false .venv/bin/python manage.py check --deploy
.venv/bin/python scripts/smoke_browser.py
.venv/bin/python scripts/check_accessibility.py /tmp/municipal-axe/package/axe.min.js
```

El servidor debe estar iniciado para las comprobaciones de navegador. El último comando necesita una copia verificada de axe-core; la ruta de ejemplo corresponde a esta ejecución. La herramienta señala también comprobaciones manuales pendientes; ausencia de infracciones automáticas no implica conformidad WCAG completa.

Las capturas y resultados resumidos se conservan en `docs/evidencias/`. Los logs de trabajo y las credenciales están en `.local/`, excluidos de Git. Las capturas contienen exclusivamente datos ficticios.

## Controles de seguridad de este sprint

Referencia educativa: OWASP Top 10, edición 2021. Esta matriz identifica controles parciales y límites; no declara conformidad total con el estándar.

| Categoría | Control o verificación | Límite pendiente |
|---|---|---|
| A01 Control de acceso | Roles, filtros por delegación, verificación en servicio, auditoría restringida y CSRF | Revisión del conjunto completo al incorporar agenda/reportes |
| A02 Fallos criptográficos | Hash de contraseñas Django y secretos fuera de Git; configuración de cookies seguras en producción | HTTPS real, gestión de claves, cifrado de respaldos |
| A03 Inyección | ORM, formularios y escape automático; pruebas SQL y XSS | Escaneo más amplio de entradas y futuras exportaciones |
| A04 Diseño inseguro | Máquina de estados, transacciones, validación de responsable y prueba de concurrencia | Modelo de amenazas del sistema completo |
| A05 Configuración insegura | Configuración diferenciada, hosts permitidos y comprobación de despliegue | Despliegue real y endurecimiento de infraestructura |
| A06 Componentes vulnerables | Dependencias fijadas e imagen con digest | Análisis actualizado de vulnerabilidades y seguimiento de versiones |
| A07 Identificación/autenticación | Validadores de contraseña, sesiones, bloqueo persistido en DB y pruebas de acceso | MFA, recuperación de cuenta y pruebas de límites a mayor escala |
| A08 Integridad de software/datos | Migraciones versionadas, transacciones y rollback ante fallo de auditoría | Pipeline firmado y verificación de respaldos |
| A09 Registro/monitoreo | Auditoría de acceso, vecinos, solicitudes y administración | Alertas, retención definida y protección externa contra alteración |
| A10 SSRF | No hay función que solicite URLs externas aportadas por usuarios | Revisar si se incorporan integraciones |

La Ley 21.459 se abordará en el informe final mediante análisis de acceso autorizado, integridad y trazabilidad, con referencias y sin afirmar que un control técnico por sí solo garantiza cumplimiento legal. Tampoco se afirma una certificación ISO 27000.

## Deficiencias detectadas y correcciones

| Deficiencia | Corrección | Verificación |
|---|---|---|
| Detalle con responsable vacío provocaba error de plantilla | Condicional explícito para mostrar «Pendiente de asignación» | Suite y navegador aprobados |
| Cambio de delegación de vecino o responsable podía romper relaciones | Bloquear transferencia de vecino y cambio de responsable con solicitudes pendientes | Pruebas de formularios/modelo aprobadas |
| Formulario de transición perdía entradas ante error | Renderizar formulario vinculado con sus errores | Prueba de conservación de texto aprobada |
| Prueba de teclado suponía foco inicial incorrecto | Partir del foco de usuario y verificar Shift+Tab al enlace de salto | Recorrido de navegador aprobado |

La descarga de Chromium desde Playwright fue rechazada por la política de red. Se utilizó el Chromium ya instalado, sin modificar la política ni desactivar verificación de descargas. La incidencia quedó resuelta para las comprobaciones de este entorno.

## Revisión propuesta al usuario

El usuario revisará el registro de vecino, los campos de la solicitud, las etiquetas de estados y los permisos de cada rol. Tras su aprobación se implementarán agenda y reportes. La entrega final incluirá el plan ampliado, resultados, correcciones, UML actualizado y documentación académica según la pauta.
