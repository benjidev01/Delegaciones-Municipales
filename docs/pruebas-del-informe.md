# Pruebas y capturas del informe Etapa 3

Preparado el 8 de octubre de 2026. Este documento explica cómo ejecutar los
CP-01 a CP-15 del informe del usuario. No constituye aceptación humana ni
afirma que las pruebas manuales del usuario ya se hayan realizado.

## Preparación en Windows

Instalar y abrir Docker Desktop. Abrir PowerShell en la carpeta que contiene
compose.yaml. Para comprobar HTTPS y DEBUG desactivado, utilizar siempre:

```powershell
docker compose -f compose.yaml -f compose.https.yaml up --build -d
docker compose -f compose.yaml -f compose.https.yaml ps
docker compose -f compose.yaml -f compose.https.yaml cp web:/app/.local/tls/localhost.crt ./localhost.crt
```

Los servicios web y db deben quedar healthy. El certificado exportado es
público; nunca exportar localhost.key ni archivos privados de configuración.
El servidor genera un certificado autofirmado solo para localhost/127.0.0.1.
Instalarlo únicamente en el PC de prueba, no en equipos ajenos:

1. Abrir localhost.crt y comprobar que pertenece a localhost.
2. Elegir Instalar certificado → Usuario actual.
3. Elegir almacén manual → Entidades de certificación raíz de confianza.
4. Completar la instalación y reiniciar Chrome o Edge.
5. Abrir https://localhost:8000/acceso/ y verificar el certificado en la
   información del sitio. Si no es confiable, revisar la instalación; no
   continuar ignorando advertencias. Si la política del equipo impide instalar
   certificados, consultar al encargado o usar un equipo de prueba autorizado.

Al terminar la evaluación, se puede retirar ese certificado específico desde
certmgr.msc. No retirar otros certificados. Este servidor TLS es una herramienta
local de evaluación, no un servidor de producción ni un despliegue público.

Elegir contraseñas propias, al menos 12 caracteres, mediante:

```powershell
docker compose -f compose.yaml -f compose.https.yaml exec web python manage.py changepassword admin.demo
docker compose -f compose.yaml -f compose.https.yaml exec web python manage.py changepassword delegado.norte
docker compose -f compose.yaml -f compose.https.yaml exec web python manage.py changepassword funcionario.norte
docker compose -f compose.yaml -f compose.https.yaml exec web python manage.py changepassword funcionario.sur
```

La terminal no muestra las contraseñas mientras se escriben. El funcionario1
del informe se corresponde con funcionario.norte en los datos preparados.
Usar solamente datos ficticios. Las contraseñas no deben aparecer en capturas.
Windows + Shift + S permite tomar una captura; guardar nombres CP-01.png,
CP-07-historial.png, etc. Mostrar la URL, el resultado y la identidad/rol cuando
corresponda. No incluir cookies, contraseñas ni configuración privada.

## Casos manuales

### CP-01 — Login válido
Ingresar con funcionario.norte y su contraseña. **CAPTURA:** inmediatamente
después del acceso, mostrar el panel, cuenta y menú. Esperado: acceso exitoso.

### CP-02 — Login inválido
Salir. Ingresar funcionario.norte con contraseña 123 una sola vez.
**CAPTURA:** formulario y mensaje de rechazo. Esperado: mensaje genérico sin
indicar cuál credencial es incorrecta ni mostrar información interna.

### CP-03 — Bloqueo por intentos
Ejecutar al final para evitar interrumpir los otros casos. Para comenzar con
contador limpio en esta instalación de prueba:
`docker compose -f compose.yaml -f compose.https.yaml exec web python manage.py axes_reset`.
Hacer cinco intentos consecutivos con contraseña incorrecta para la misma cuenta.
**CAPTURA 1:** pantalla de acceso temporalmente limitado tras el quinto intento.
Probar inmediatamente la contraseña correcta. **CAPTURA 2:** sigue bloqueado.
Esperado: bloqueo de esa combinación cuenta/IP por una hora. Esperar o ejecutar
axes_reset para continuar. No limpiar contadores entre los cinco intentos.

### CP-04 — Registro válido
Ingresar como funcionario.norte → Vecinos → Registrar vecino. RUT
11.111.111-1, nombre Vecino Prueba Informe, correo prueba@example.invalid,
dirección ficticia. Guardar. **CAPTURA:** listado con vecino y RUT normalizado.
Esperado: registro creado. Si ya existe, preparar otro RUT válido; reutilizar
un registro existente no acredita una nueva creación.

### CP-05 — Datos inválidos
Registrar datos ficticios con RUT 11.111.111-2. **CAPTURA 1:** error de dígito
verificador después de enviar. Intentar además guardar campos obligatorios
vacíos. **CAPTURA 2:** advertencia de campo obligatorio. Esperado: no crear
vecino. La advertencia del navegador acredita validación del navegador;
la suite automatizada comprueba también validación del servidor.

### CP-06 — Ingreso de solicitud
Funcionario → Solicitudes → Nueva solicitud. Elegir el vecino de CP-04,
tipo Reclamo, descripción Prueba de luminaria para el informe. Guardar y anotar
el número. **CAPTURA:** detalle recién creado con número y estado Ingresada.

### CP-07 — Estados y auditoría
Salir y entrar como delegado.norte. Asignar la solicitud a funcionario.norte
con motivo. Como funcionario.norte avanzar a En atención y luego Resuelta,
con motivos. Como delegado.norte autorizar Cerrada con motivo.
**CAPTURA 1:** detalle cerrado e historial con cuatro cambios, autores y fechas.
Como admin.demo abrir Auditoría. **CAPTURA 2:** eventos solicitud.creada,
solicitud.asignada, solicitud.atencion, solicitud.resuelta y solicitud.cerrada
para el número anotado; pueden ser necesarias varias imágenes por paginación.
Esperado: orden completo, sin saltos, y trazabilidad. Solo supervisores asignan
y cierran. Solo el responsable o un supervisor atiende y resuelve.

### CP-08 — Integración y reportes
Crear otra solicitud que permanezca Ingresada. Como delegado.norte abrir
Reportes y elegir período que incluya las fechas de ingreso. Contar las
solicitudes por estado en todo el detalle, incluidas otras páginas y registros
preexistentes. **CAPTURAS:** filtros, totales y detalle, tantas como se necesiten.
Esperado: totales coinciden. Los filtros se aplican a fecha de ingreso y estado
actual, no a fecha de cierre ni al estado histórico de una fecha pasada.

### CP-09 — Inyección SQL
Salir. Usuario literal: `' OR '1'='1`, contraseña cualquiera. Intentar acceder
una vez. **CAPTURA:** rechazo sin error de base de datos. Esperado: no acceder.
Este intento concreto no demuestra ausencia de toda inyección SQL.

### CP-10 — XSS
Funcionario → crear solicitud con descripción literal
`<script>alert(1)</script>`. **CAPTURA 1:** detalle con ese texto visible y sin
alerta. Con F12 inspeccionar la descripción. **CAPTURA 2:** texto escapado dentro
del elemento, no un elemento script ejecutable. Esperado: contenido no ejecutado.

### CP-11 — CSRF
Como funcionario autenticado, abrir F12 → Consola y escribir:

```javascript
fetch('/vecinos/nuevo/', {
  method: 'POST', credentials: 'same-origin',
  body: new URLSearchParams({rut: '11.111.111-1', nombre: 'Prueba CSRF',
    email: 'csrf@example.invalid', direccion: 'Dirección ficticia'})
}).then(r => console.log('Estado HTTP:', r.status));
```

No envía token CSRF. **CAPTURA:** en Red/Network seleccionar la petición y
mostrar estado 403 y respuesta de rechazo CSRF. No capturar cookies.
Esperado: no guardar datos. Solo ejecutar contra la propia instalación local.

### CP-12 — Acceso por rol
Como funcionario.norte escribir https://localhost:8000/auditoria/ y luego
/reportes/. **CAPTURAS:** URL y acceso denegado. Esperado: HTTP 403, sin datos.
Abrir /admin/: puede redirigir al login administrativo, pero nunca permitir el
panel al funcionario. Como funcionario.sur intentar abrir la solicitud de
Norte: debe dar 404 sin revelar el registro.

### CP-13 — Inactividad real
Iniciar sesión nueva como funcionario. Anotar hora y tomar **CAPTURA 1** del
panel con reloj. Dejar esa cuenta sin actividad en todas sus pestañas durante
más de 30 minutos, manteniendo el PC despierto. No hacer clic, escribir ni
desplazarse. **CAPTURA 2:** login tras la expiración automática; mostrar reloj.
Si el PC estuvo suspendido, abrir una página privada al volver: debe pedir login.
Esperado: sesión rechazada por servidor tras 30 minutos sin actividad aceptada;
el navegador abierto redirige al login sin requerir recarga manual.
Comprobación adicional: en otra ejecución, interactuar antes de 30 minutos y
comprobar que la sesión sigue activa después de cumplirse 30 minutos desde el
login, pero antes de 30 minutos desde la última interacción. El navegador
comunica interacciones con un máximo de una petición cada 10 segundos.

### CP-14 — PC, tablet y teclado
F12 → Ctrl + Shift + M. Configurar 1440×900 y después 768×1024. Probar panel,
formulario de vecino y solicitudes. **CAPTURAS:** las mismas tres pantallas en
ambos tamaños, con dimensiones visibles. Comprobar botones, etiquetas, errores,
foco con Tab/Shift+Tab y tablas desplazables en su contenedor. Esperado: uso
operable sin desbordamiento de toda la página. Es emulación de viewport, no
prueba física de tablet; indicar esa diferencia en el informe.

### CP-15 — Aceptación humana
Un evaluador funcionario completa login, vecino y solicitud; otro delegado
completa asignación, cierre y reporte. **CAPTURAS:** resultados del recorrido.
Registrar fecha, evaluador, rol, observaciones y decisión expresa de aceptación.
Una captura del sistema o una suite aprobada no sustituye esa confirmación.

## Pruebas automatizadas y evidencia técnica

```powershell
docker compose -f compose.yaml -f compose.https.yaml exec web python manage.py test apps
docker compose -f compose.yaml -f compose.https.yaml exec web python manage.py check --deploy
```

**CAPTURA:** comando completo y resultado final de la suite con cantidad,
duración y OK o fallos. La suite actual, incluidos los controles del proxy EC2, contiene 115 pruebas.
**CAPTURA:** check --deploy y resultado sin incidencias, si efectivamente pasa.
Para HTTPS capturar además información del certificado en el navegador.
Para hashes de contraseñas utilizar el test automatizado correspondiente;
no revelar hashes reales ni archivos de credenciales como evidencia.

En cada fila de resultados: fecha, cuenta/rol, datos, resultado observado,
Aprobado/Fallido/Pendiente, nombre de captura y observaciones. Las pruebas
automáticas no certifican cumplimiento legal total, ISO ni todo OWASP Top 10.

Detener sin borrar datos:
`docker compose -f compose.yaml -f compose.https.yaml down`.
No agregar -v. No publicar este servidor en Internet.
