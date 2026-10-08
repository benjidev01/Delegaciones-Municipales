# Revisión de pruebas y seguridad

Fecha: 7 de octubre de 2026. Alcance: prototipo académico de Delegaciones Municipales, código de aplicación, dependencias Python y ejecución de desarrollo. La aceptación humana permanece pendiente.

## Resultados verificados

| Comprobación | Resultado |
|---|---|
| Suite completa en el entorno directo | 106 pruebas, 106 aprobadas, sin omisiones |
| Suite completa en Docker Compose | 106 pruebas, 106 aprobadas, sin omisiones |
| Dependencias Python de aplicación | Siete paquetes consultados con pip-audit 2.10.1; cero vulnerabilidades conocidas en la consulta |
| Análisis estático | Bandit 1.9.4: 831 líneas de aplicación/configuración, cero hallazgos y cero archivos con error de análisis |
| Configuración Django de producción | `check --deploy` con `DJANGO_DEBUG=false`: sin advertencias |
| Consistencia de modelos/migraciones | Sin cambios de modelo pendientes |
| Recorridos de navegador del entorno directo | Vecinos, solicitudes, agenda, reportes, auditoría y permisos aprobados |
| Recorrido de navegador de Docker | Login, ciclo completo de solicitud, reserva/cancelación, reportes, aislamiento y auditoría aprobados |
| Instalación desde ZIP extraído | Proyecto y volúmenes independientes: 106 pruebas y recorrido funcional de navegador aprobados |
| Accesibilidad automática | 22 combinaciones de pantalla/tamaño sin infracciones automáticas evaluadas; revisión humana pendiente |
| Instalación de dependencias | Versiones fijadas y verificación de hashes mediante `requirements.lock` |

La consulta de vulnerabilidades refleja información conocida por PyPI en el momento de ejecución; no prueba ausencia de vulnerabilidades desconocidas. Bandit analiza aplicación y configuración, excluyendo pruebas y migraciones; no cubre JavaScript, imágenes base ni un despliegue externo. Las comprobaciones de configuración no demuestran que exista un despliegue HTTPS real.

Los resultados iniciales de 38 y 88 pruebas corresponden a etapas anteriores y se conservan en sus documentos. La ejecución final de esta revisión contiene 106 pruebas. Los archivos de evidencia de esta etapa están en `docs/evidencias/seguridad/` y no contienen contraseñas, archivos privados ni datos personales reales.

## Hallazgos corregidos

| Hallazgo | Corrección | Evidencia |
|---|---|---|
| Dos registros simultáneos del mismo RUT podían terminar en error interno | Capturar únicamente la violación de unicidad conocida, conservar formulario y mostrar error seguro | Prueba concurrente en PostgreSQL: una respuesta exitosa y una validación controlada, con un vecino y una auditoría |
| Cambio de contraseña desde administración no aparecía en la auditoría municipal | Registrar el evento de cambio exitoso dentro de una transacción | Prueba de cambio, evento asociado e invalidación de la sesión previa |
| Las páginas de datos no establecían explícitamente la prohibición de caché | Middleware `Cache-Control: private, no-store` | Prueba de cabeceras sobre listado de vecinos |
| Instalación fijada por versión, sin hash obligatorio | Añadir lock con hashes y exigirlos en instaladores y Docker | Instalación directa y construcción Docker completadas con verificación |
| Formularios POST completamente vacíos se trataban como no enviados | Vincular el formulario de acuerdo con el método HTTP | Prueba de mensajes de campos obligatorios |
| Se rechazaban RUT de número corto aunque su dígito verificador fuera válido | Aceptar cuerpos positivos de hasta ocho dígitos y rechazar cero | Casos de RUT corto válido y RUT cero rechazado |

También se retiró `testserver` de los hosts aceptados por defecto. Django habilita el host de pruebas dentro de su propio runner; el servidor de desarrollo acepta solo localhost y 127.0.0.1, salvo configuración explícita.

## Pruebas de seguridad ampliadas

| ID | Escenario | Resultado verificado |
|---|---|---|
| SEG-01 | Acceso anónimo a todas las pantallas privadas | Redirección al login |
| SEG-02 | Host no autorizado | HTTP 400 |
| SEG-03 | Almacenamiento de contraseña | Hash PBKDF2; comprobación correcta sin texto plano en el campo |
| SEG-04 | Cookies y cabeceras | HttpOnly, SameSite=Lax, X-Frame-Options=DENY, nosniff, referrer policy y no-store |
| SEG-05 | Cookies con configuración de producción | Secure en sesión y CSRF |
| SEG-06 | Login sin CSRF | HTTP 403 |
| SEG-07 | Redirección externa manipulada después de login | Se utiliza el destino local permitido |
| SEG-08 | Logout mediante GET | HTTP 405; no se cierra sesión sin POST |
| SEG-09 | Cuenta desactivada con sesión previa | Se rechaza la siguiente petición autenticada |
| SEG-10 | Cambio de delegación con sesión previa | La siguiente petición aplica el nuevo ámbito |
| SEG-11 | Cambio de rol con sesión previa | La siguiente petición aplica los nuevos permisos |
| SEG-12 | Cambio de contraseña por administrador | Nueva contraseña válida, evento auditado y sesión antigua invalidada |
| SEG-13 | Contraseña débil desde administración | Rechazo sin cambiar la contraseña ni crear evento exitoso |
| SEG-14 | Funcionario intenta cambiar contraseña ajena desde admin | No se modifica la cuenta objetivo |
| SEG-15 | Credenciales fallidas y auditoría | No se persisten contraseña ni nombre enviado en el evento municipal |
| SEG-16 | Error interno con DEBUG desactivado | HTTP 500 con mensaje seguro, sin detalle interno en el cuerpo |
| SEG-17 | POST vacío | Mensajes de campos obligatorios |
| SEG-18 | Registro simultáneo del mismo RUT | Un éxito y un error de validación; sin duplicados |

Estas pruebas se añaden a las de CSRF, SQL/XSS, permisos, concurrencia de solicitudes y agenda, estados y rollback documentadas en los dos incrementos previos.

## Matriz OWASP de alcance

Se conserva como referencia educativa la edición **OWASP Top 10 2021**, indicada en los documentos anteriores. Se evalúan controles aplicables al prototipo, no una certificación ni un porcentaje de cumplimiento integral.

| Categoría | Evidencia disponible | Alcance o pendiente |
|---|---|---|
| A01 Control de acceso | Roles, ámbito por delegación, rutas protegidas, CSRF y pruebas de objetos ajenos | Verificado para operaciones implementadas; revisión humana pendiente |
| A02 Fallos criptográficos | Hash de contraseña, secretos fuera del ZIP/Git, cookies seguras en configuración de producción | HTTPS real, rotación de claves y cifrado de respaldos no comprobados |
| A03 Inyección | ORM, escape HTML y validación; casos SQL y XSS rechazados/escapados | No es un pentest exhaustivo |
| A04 Diseño inseguro | Estados autorizados, límites de reservas, transacciones y pruebas con conexiones concurrentes | Modelo de amenazas parcial del prototipo |
| A05 Configuración insegura | Hosts restringidos, cabeceras, no-store, DEBUG diferenciado y check de despliegue | Configuración real de infraestructura/TLS pendiente |
| A06 Componentes vulnerables | Siete paquetes auditados sin vulnerabilidades conocidas; versiones y hashes fijados | No se analizaron vulnerabilidades del sistema operativo o imágenes base |
| A07 Autenticación | Validadores de contraseña, sesiones, bloqueo de login, invalidación tras cambio de contraseña | No incorpora MFA ni recuperación por correo |
| A08 Integridad de software/datos | Hashes, migraciones, restricciones PostgreSQL y rollback probado | No se ejecutaron pruebas de restauración de respaldos ni firma de pipeline |
| A09 Registro/monitoreo | Login, vecinos, solicitudes, agenda, administración y cambio de contraseña auditados | No hay alertas externas ni registro inviolable frente al administrador de DB |
| A10 SSRF | El sistema no obtiene URLs externas aportadas por el usuario | No aplica a una función existente; revisar antes de añadir integraciones |

La excepción concurrente de registro se maneja de forma controlada; no se silencian errores de base de datos ajenos a la restricción conocida. No se han deshabilitado validadores, TLS, hashes o aserciones para obtener resultados aprobados.

## Consideraciones normativas y de calidad

La pauta menciona la Ley 21.459 y estándares de la familia ISO 27000. Los controles de autorización, trazabilidad e integridad del prototipo ayudan a prevenir usos no autorizados y a investigar acciones, pero no garantizan por sí solos cumplimiento jurídico.

Se utiliza exclusivamente información ficticia en las pruebas. La operación municipal con datos reales requiere definir responsabilidades, finalidad y acceso a datos, retención, respaldos y respuesta a incidentes. El análisis normativo detallado y la bibliografía del informe académico se prepararán en la etapa de entrega, utilizando las fuentes correspondientes.

No se declara certificación ISO, auditoría de producción completa ni «100% OWASP». La configuración Docker entregada es de desarrollo y usa HTTP local; publicar para terceros requiere un diseño de despliegue con TLS y permisos de base de datos adecuados.

## Distribución verificable

Se preparó Docker Compose con inicialización de configuración privada, PostgreSQL y aplicación. La base no expone puertos al equipo anfitrión y la web se publica solo en el loopback local. La aplicación corre con usuario no root, sistema raíz de solo lectura y configuración en volumen persistente.

La primera construcción en cloud falló por DNS externo de Docker. Se resolvió incluyendo ruedas Python descargadas por TLS y verificadas contra el lock. La construcción completada volvió a comprobar hashes, sin conectarse a PyPI dentro del contenedor. Las imágenes base están fijadas por digest. La configuración privada y los datos de la instancia no forman parte del ZIP.

La guía `docs/como-probar.md` permite realizar una aceptación humana: preparación, elección de contraseñas, recorrido de roles, comprobación de permisos, agenda, reportes y ejecución de la suite. El informe final y la aceptación del usuario siguen pendientes.
