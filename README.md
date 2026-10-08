# Delegaciones Municipales

Prototipo académico en Django y PostgreSQL. Incorpora acceso por roles, vecinos, solicitudes, transiciones autorizadas, historial, auditoría, agenda de atenciones y reportes. La aceptación humana y la documentación académica final están pendientes.

## Requisitos

El código completo está en la rama `proyecto-completo`:

```sh
git clone --branch proyecto-completo --single-branch https://github.com/benjidev01/Delegaciones-Municipales.git
cd Delegaciones-Municipales
```

En GitHub también se puede seleccionar esa rama y usar Code → Download ZIP.

Para probar la entrega con Docker Desktop, basta descargar y extraer el ZIP y ejecutar `docker compose up --build -d`. No es necesario instalar Python o PostgreSQL por separado. La guía completa, incluidos los comandos para elegir contraseñas y el recorrido de cada rol, está en [docs/como-probar.md](docs/como-probar.md). Esta modalidad se verificó en Linux x86_64; Windows/macOS y ARM64 requieren su propia comprobación.

Los siguientes requisitos corresponden a la modalidad de desarrollo directamente sobre el entorno cloud:

Python 3.12, `uv` y Docker con el servicio activo. La base local usa PostgreSQL 17, volumen `delegaciones-pgdata` y puerto 55432, expuesto únicamente a la máquina local. No se usa SQLite como sustituto de las pruebas.

## Instalar y ejecutar

Desde la raíz del repositorio:

```sh
sh scripts/install.sh
sh scripts/start.sh
```

La aplicación escucha en el puerto local 8000. Los scripts pueden repetirse: no restablecen contraseñas ni eliminan datos existentes. La configuración privada se genera en `.local/config.json`. Las cuentas ficticias `admin.demo`, `delegado.norte`, `funcionario.norte` y `funcionario.sur` reciben contraseñas aleatorias, disponibles solo en `.local/demo-credentials.json`. Esos archivos están excluidos de Git; no se deben compartir ni publicar. Para definir una contraseña propia desde una terminal autorizada:

```sh
.venv/bin/python manage.py changepassword admin.demo
```

El administrador gestiona usuarios y delegaciones desde la administración Django. Los registros de auditoría son de consulta; no se habilitan altas, cambios ni eliminaciones desde esa interfaz. La creación de datos demo no elimina ni altera cuentas existentes. El prototipo utiliza datos ficticios y no emite certificados ni permisos oficiales.

## Agenda y reportes

La agenda permite reservar una atención futura de 15, 30, 45 o 60 minutos con un funcionario activo de la misma delegación que el vecino. Se puede vincular una solicitud del mismo vecino que aún no esté cerrada. Se muestran las fechas en America/Santiago y se rechazan horas inexistentes o ambiguas por cambios estacionales. No se configura un horario de oficina fijo en este prototipo.

PostgreSQL impide reservas programadas superpuestas del mismo funcionario mediante una restricción de exclusión; se admiten horarios adyacentes. Todos los roles pueden gestionar la agenda dentro de su ámbito. Cancelar conserva historial y libera el horario. Solo el funcionario de la cita, un delegado de su delegación o un administrador pueden marcar la atención como realizada, después del inicio. Para reprogramar se cancela y se crea una nueva reserva. No hay notificaciones por correo o SMS.

Los reportes son exclusivos de delegados y administradores. Incluyen filtros por estado actual, delegación y fecha de ingreso de la solicitud, con días inicial y final inclusivos en horario de Chile. Las fechas inválidas, intervalos invertidos o delegaciones no autorizadas muestran errores sin ampliar la consulta. Se presentan totales por estado, por delegación y el detalle paginado. No se incluyen exportaciones de datos personales.

La migración de agenda instala la extensión PostgreSQL `btree_gist`. La cuenta de desarrollo dispone de permisos; en producción, su instalación debe prepararse con una cuenta autorizada antes de aplicar restricciones.

## Verificación

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test apps
```

Las pruebas crean una base temporal de PostgreSQL. La cuenta local de desarrollo puede crear bases de pruebas; una cuenta de producción deberá tener privilegios limitados.

Para la prueba opcional de navegador, con el servidor iniciado y Chromium instalado en `/usr/bin/chromium`:

```sh
UV_CACHE_DIR="$PWD/.local/uv-cache" uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python scripts/smoke_browser.py
.venv/bin/python scripts/smoke_sprint_2.py
```

Los recorridos de navegador añaden una solicitud ficticia y citas ficticias para verificar sus ciclos, los conflictos de horario y los reportes. Guardan capturas en `.local/browser/`. La auditoría automática de accesibilidad se ejecuta con `scripts/check_accessibility.py RUTA_A_AXE_MIN_JS`, usando una copia local verificada de axe-core 4.10.3. No sustituye la aceptación humana ni demuestra conformidad completa con WCAG.

## Seguridad y límites

La configuración local habilita HTTP y depuración exclusivamente para desarrollo. Para producción, establecer `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` y las variables `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` y `POSTGRES_PORT`; usar HTTPS, una cuenta de base con privilegios mínimos y un servidor WSGI de producción. No ejecutar `runserver` en producción. Si se usa un proxy, configurar sus cabeceras solo después de verificar la frontera de confianza.

Los permisos se verifican en el servidor y las consultas se restringen por delegación. Django aporta CSRF, escape HTML, ORM y hashing; django-axes limita accesos fallidos. El historial no es inviolable frente a administradores de base de datos. El prototipo no declara certificación ISO ni cumplimiento legal integral.

La revisión ampliada pasó 106 pruebas en el entorno directo y dentro de Docker. Se auditaron los siete paquetes de aplicación mediante pip-audit y el código de aplicación mediante Bandit. Los resultados y su alcance están en [docs/revision-seguridad.md](docs/revision-seguridad.md). `requirements.lock` fija paquetes y hashes; los instaladores verifican integridad. Las páginas privadas usan `Cache-Control: private, no-store`. Los cambios de contraseña desde administración tienen auditoría e invalidan sesiones anteriores del usuario afectado.

Diseño y UML: [docs/diseno.md](docs/diseno.md). Plan y resultados del primer sprint: [docs/pruebas-sprint-1.md](docs/pruebas-sprint-1.md). Agenda, reportes y resultados del segundo incremento: [docs/pruebas-sprint-2.md](docs/pruebas-sprint-2.md).

## Ajustes para el informe Etapa 3

La guía [pruebas del informe](docs/pruebas-del-informe.md) contiene los CP-01 a
CP-15 y señala cada captura. Para sus evidencias HTTPS utilizar:
`docker compose -f compose.yaml -f compose.https.yaml up --build -d`,
instalar el certificado público local siguiendo esa guía y abrir
`https://localhost:8000`. La sesión tiene cierre por inactividad de 30 minutos.
La suite actual contiene 115 pruebas. La vista [código completo](docs/codigo-completo.html)
incluye todos los archivos de código propio, pruebas y migraciones para revisión.
El servidor HTTPS local se utiliza para evaluación, no para publicar en Internet.

## Preparación para EC2, sin dominio

Empezar por [EC2 paso a paso](docs/ec2-paso-a-paso.md), con comandos en orden y
el resultado esperado de cada etapa.

[Guía de Amazon Linux 2023](docs/despliegue-ec2.md): `compose.ec2.yaml` y
`Dockerfile.ec2` preparan Nginx, Gunicorn y PostgreSQL privado. Certbot 5.8 permite
certificados para IPv4 públicas con el perfil shortlived; se incluye un timer de
renovación y configuración por IP validada. La cuenta de base de la aplicación
no es superusuario y no recibe el secreto administrador. Esta configuración
se ensayó localmente y se publica en esta rama; el despliegue en la cuenta AWS del usuario sigue pendiente.
