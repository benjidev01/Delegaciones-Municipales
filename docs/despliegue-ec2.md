# EC2 con Amazon Linux 2023: acceso del docente por IP y HTTPS

Para una primera instalación, seguir [instrucciones simples paso a paso](ec2-paso-a-paso.md).
Este documento conserva los detalles técnicos y procedimientos de mantenimiento.

Preparación del 8 de octubre de 2026. Los archivos se prepararon localmente con
autorización del usuario. No se ha publicado código en GitHub, conectado a su
instancia, cambiado AWS ni solicitado un certificado público real.

## Diseño preparado

Esta instalación usa Nginx dentro de Docker como único servidor público.
No instalar httpd (Apache) ni otro Nginx mediante dnf para este proyecto.
Si ya están instalados, comprobar si atienden otro sitio antes de detenerlos.

Navegador → Nginx HTTPS en 443 → Gunicorn/Django privado → PostgreSQL privado.
El puerto 80 sirve HTTP-01 y redirige el resto a HTTPS una vez activado el sitio.
Antes del certificado solo sirve desafíos; la aplicación responde 503.
No utiliza el servidor de evaluación local ni runserver para acceso público.

Docker y Compose ejecutan los servicios. Solo Nginx publica puertos. Django usa
DEBUG=false, cookies Secure/HttpOnly, CSRF y sesiones de 30 minutos de inactividad.
Nginx reemplaza las cabeceras de protocolo e IP del cliente; Django las confía
solo en este modo y en la red interna. El bloqueo de login conserva la identidad
de la IP del cliente, en vez de tratar a todos como la IP del proxy.

La cuenta PostgreSQL de la aplicación no tiene superusuario, creación de roles
ni creación de bases. Un servicio transitorio prepara esa cuenta y la extensión
btree_gist. El secreto administrador de PostgreSQL está en un volumen diferente
que no se monta en el servicio web. Los secretos se generan una vez y se conservan;
no se incluyen en Git, en ZIP ni en esta guía.

## Requisitos y costos

- Amazon Linux 2023, Docker con contenedores Linux y acceso SSH como ec2-user.
- Recomendación para esta demostración: 2 GB de RAM y aproximadamente 20 GB de
  almacenamiento. El ensayo se realizó en Linux x86_64; ARM64 no se probó físicamente.
- IPv4 pública estable. Se recomienda asociar una Elastic IP; su asignación y
  asociación son cambios en AWS que requieren autorización previa del usuario.
- AWS cobra por IPv4 públicas, instancia y almacenamiento según su cuenta/región.
- SSH 22 restringido a la IP del administrador. HTTP 80 accesible públicamente
  para que los validadores ACME alcancen el desafío. HTTPS 443 accesible al docente
  y, si se decide, al público. No abrir 5432 ni 8000.
- Salida HTTPS a Docker Hub, GitHub y los servicios ACME para imágenes,
  herramientas y certificados. La hora del servidor debe estar sincronizada.

Para HTTPS por IP se fijó Certbot 5.8.0, que soporta --ip-address y el plugin
webroot para IP. Se solicita obligatoriamente el perfil shortlived de Let's
Encrypt. Estos certificados tienen vigencia de aproximadamente seis días
(160 horas), por lo que la renovación automática es indispensable.
No hace falta dominio ni instalar certificados en el computador del docente.
Si cambia la IP, el certificado anterior no sirve para la nueva dirección.

## 1. Entregar el código, después de su revisión y permiso

El proyecto completo se publica en la rama proyecto-completo. Revisar el código
antes de autorizar el despliegue. Entrar a la instancia desde PowerShell:

```powershell
ssh -i "C:\ruta\mi-clave.pem" ec2-user@IP_PUBLICA
```

Sustituir los marcadores por la clave local y la IP de la instancia. Verificar
la huella SSH antes de aceptar una conexión nueva. Dentro de EC2:

```sh
sudo dnf install -y git
cd /home/ec2-user
git clone --branch proyecto-completo --single-branch https://github.com/benjidev01/Delegaciones-Municipales.git
cd /home/ec2-user/Delegaciones-Municipales
sh scripts/install_amazon_linux.sh
```

Si el repositorio es privado, se necesita acceso Git autorizado. No transferir
archivos .local ni compartir claves SSH, bases o credenciales privadas.

No sobrescribir a ciegas una carpeta de aplicación existente. El instalador
comprueba Amazon Linux 2023, instala Docker y, si falta Compose, descarga la
versión fijada verificando su SHA256 publicado por el proyecto oficial.
Salir de SSH y volver a entrar para aplicar el grupo docker; ese grupo permite
administrar contenedores con privilegios equivalentes a administración del host.

```sh
docker --version
docker compose version
cd /home/ec2-user/Delegaciones-Municipales
```

## 2. Comprobar y liberar los puertos 80 y 443

Apache (httpd) y el contenedor Nginx no pueden escuchar simultáneamente en la
misma dirección y puerto del host. Las reglas del grupo de seguridad permiten
tráfico, pero no liberan un puerto ocupado. Antes de arrancar el contenedor:

```sh
sudo ss -ltnp '( sport = :80 or sport = :443 )'
sudo systemctl status httpd --no-pager
sudo systemctl status nginx --no-pager
docker ps --format 'table {{.Names}}\t{{.Ports}}'
```

Que systemctl indique que una unidad no existe es normal si no está instalada.
Si aparece httpd y esta instancia está dedicada a esta demostración, sin otro
sitio que deba mantenerse, detenerlo y evitar que ocupe el puerto al reiniciar:

```sh
sudo systemctl disable --now httpd
```

Si existe un Nginx instalado directamente en el host y tampoco sirve otro sitio:

```sh
sudo systemctl disable --now nginx
```

El comando anterior afecta el servicio del host, no el Nginx de Docker. No
desinstalar servicios ni detener contenedores de otros proyectos a ciegas.
Si Apache u otro servidor aloja un sitio que se debe conservar, mantenerlo
activo y adaptar la arquitectura antes de continuar; no ejecutar los comandos
de detención. La configuración entregada supone que 80 y 443 están disponibles.

Volver a ejecutar ss. Antes del primer arranque del proyecto, no debe aparecer
ningún proceso escuchando en esos puertos. Después de bootstrap, es correcto
que Docker/Nginx los ocupe. Si aparece "address already in use" o "port is already
allocated", revisar ss y docker ps antes de volver a intentarlo.

No cambiar el puerto público del desafío a 8080 para resolver el conflicto:
la validación HTTP-01 necesita acceso al puerto 80. Se podría conservar Apache
como entrada y configurar allí el proxy y el desafío, pero sería un despliegue
distinto de los archivos entregados.

## 3. Preparar la IP y arrancar el servicio de desafíos

Estos comandos implican ejecutar el despliegue y se usan después de autorizarlo.
Sustituir IP_PUBLICA y CORREO_REAL por los datos correspondientes:

```sh
python3 scripts/prepare_ec2.py --ip IP_PUBLICA --email CORREO_REAL
sh scripts/ec2.sh bootstrap
sh scripts/ec2.sh status
```

El script acepta una IPv4 pública y crea .local/ec2.env y la configuración
inicial de Nginx, sin imprimir secretos. No sobrescribe una configuración
distinta preexistente. Desde otro computador, HTTP debe responder 503 al abrir
la IP; no mostrará aún la aplicación ni un formulario inseguro de login.

**CAPTURA EC2-01:** consola AWS con sistema operativo e IP asociada, ocultando
identificadores innecesarios. **CAPTURA EC2-02:** reglas de entrada del grupo de
seguridad, mostrando solo los puertos que corresponde publicar.

## 4. Comprobar ACME y emitir HTTPS

Probar primero con el servicio staging para no consumir límites de emisión:

```sh
sh scripts/ec2.sh cert-test
```

El certificado staging no es confiable para navegadores y no activa el sitio.
Si falla, revisar IP, puerto 80, grupo de seguridad, rutas de la subred y el
desafío HTTP-01. No repetir intentos sin diagnosticar el error.

Cuando staging haya funcionado:

```sh
sh scripts/ec2.sh cert-issue
sh scripts/ec2.sh activate
sh scripts/ec2.sh status
```

La activación exige los archivos del certificado, arranca PostgreSQL/Gunicorn,
ejecuta migraciones y collectstatic, comprueba check --deploy y prueba Nginx
antes de recargarlo. Si nginx -t falla, restaura el archivo HTTP de preparación.
El certificado de staging se guarda separado del certificado público.

Abrir desde otro computador `https://IP_PUBLICA/acceso/`. Debe mostrar login sin
advertencias de certificado. HTTP debe redirigir a HTTPS. Nunca ignorar un error
de certificado para marcar esta prueba como aprobada.

**CAPTURA EC2-03:** dirección HTTPS y login desde el computador del docente.
**CAPTURA EC2-04:** información del certificado, emisor, IP SAN y vigencia.
No mostrar archivos de claves, variables privadas ni cookies.

## 5. Renovación automática

La renovación se ejecutará cada doce horas con un retraso aleatorio máximo de
una hora. Copiar las unidades solo cuando se haya autorizado operar en EC2:

```sh
sudo cp deploy/ec2/municipales-renew.service /etc/systemd/system/
sudo cp deploy/ec2/municipales-renew.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now municipales-renew.timer
sudo systemctl start municipales-renew.service
sudo systemctl status municipales-renew.service --no-pager
sudo systemctl list-timers municipales-renew.timer
```

Las unidades suponen ec2-user y /home/ec2-user/Delegaciones-Municipales. Si la
carpeta o usuario son otros, adaptar esos campos antes de instalarlas.
`ec2.sh renew` usa la configuración de emisión guardada por Certbot y solicita
solo municipal-ip; comprueba y recarga Nginx después de una ejecución exitosa.
No fuerza emisión cada doce horas: Certbot decide cuándo corresponde renovar.

**CAPTURA EC2-05:** temporizador activo, próxima ejecución y resultado del servicio.
Revisar fallos con `sudo journalctl -u municipales-renew.service --since today`.
Además de probar la primera emisión, confirmar una renovación real y que el
navegador muestra la nueva vigencia. Eso queda pendiente hasta ejecutarlo en AWS.

## 6. Cuentas y prueba del docente

Cambiar las contraseñas aleatorias antes de entregar cuentas; cada comando
solicita el nuevo valor sin mostrarlo:

```sh
docker compose --env-file .local/ec2.env -f compose.ec2.yaml exec web python manage.py changepassword admin.demo
docker compose --env-file .local/ec2.env -f compose.ec2.yaml exec web python manage.py changepassword delegado.norte
docker compose --env-file .local/ec2.env -f compose.ec2.yaml exec web python manage.py changepassword funcionario.norte
docker compose --env-file .local/ec2.env -f compose.ec2.yaml exec web python manage.py changepassword funcionario.sur
```

Entregar al docente la URL y las cuentas funcionario.norte y delegado.norte.
Si necesita ejecutar CP-07/CP-12 sobre Auditoría o administración, entregar también
una cuenta administradora de evaluación por un canal separado y acordado. Nunca
dar acceso SSH, clave PEM, consola AWS ni contraseña de PostgreSQL al docente.

Seguir [CP-01 a CP-15](pruebas-del-informe.md), sustituyendo https://localhost:8000
por https://IP_PUBLICA. No instalar el certificado autofirmado de la guía local:
EC2 debe presentar un certificado públicamente confiable. Usar solo datos ficticios.
La prueba de bloqueo se hace al final; afecta la combinación de cuenta/IP.
La aceptación humana se registra cuando el docente realiza los recorridos.

## 7. Verificar y conservar evidencia

```sh
docker compose --env-file .local/ec2.env -f compose.ec2.yaml exec web python manage.py check --deploy --fail-level WARNING
python3 scripts/smoke_ec2.py
```

El verificador usa la confianza TLS pública, crea cuentas QA y una solicitud
ficticia con su ciclo completo, verifica roles/reportes/auditoría/CSRF/XSS,
comprueba privilegios de base y desactiva las cuentas QA al terminar. No muestra
credenciales. Guardar su resultado, no los archivos privados.

**CAPTURA EC2-06:** check --deploy sin incidencias y verificador exitoso.
La suite completa contiene 115 pruebas. Se ejecuta en el entorno de desarrollo
con permisos para crear una base temporal, no concediendo CREATEDB al usuario
de aplicación pública. Comando en el entorno de desarrollo:
`.venv/bin/python manage.py test apps`, o el equivalente de compose.yaml local.

## 8. Reinicio, respaldos y cierre de la demostración

Los servicios persistentes tienen restart unless-stopped y Docker arranca al
iniciar la instancia. Después de reiniciar verificar status, login y TLS desde
otro equipo. Volúmenes separados conservan datos, secretos y certificados.

Respaldo SQL antes de cambios, desde la carpeta del proyecto:

```sh
mkdir -p .local/backups
chmod 700 .local/backups
umask 077
docker compose --env-file .local/ec2.env -f compose.ec2.yaml exec -T db pg_dump -U postgres delegaciones > .local/backups/delegaciones.sql
test -s .local/backups/delegaciones.sql
```

pg_dump se conecta por el socket local del propio contenedor de base. El acceso
a Docker está restringido al operador. El respaldo contiene datos de aplicación;
guardarlo de forma privada. No incluirlo en ZIP, Git o capturas. Para respaldos
EBS consistentes se requiere un procedimiento adicional; esta guía no equivale
a una estrategia de recuperación probada.

Para detener sin borrar datos:

```sh
sudo systemctl disable --now municipales-renew.timer
sh scripts/ec2.sh down
```

No agregar -v. Detener contenedores no detiene cargos de AWS. Tras la evaluación,
decidir con el usuario si detener la instancia, conservar EBS y liberar Elastic
IP. Esas acciones requieren autorización, y liberar la IP rompe la URL entregada.

## Fuentes y límites de la verificación

- [Certbot 5.8: opciones CLI](https://github.com/certbot/certbot/blob/v5.8.0/certbot/docs/cli-help.txt).
- [Certbot: changelog, soporte webroot para IP desde 5.4](https://github.com/certbot/certbot/blob/v5.8.0/certbot/CHANGELOG.md).
- [Let's Encrypt: perfiles de certificados](https://letsencrypt.org/docs/profiles/).
- [Docker Compose: versión fijada del instalador](https://github.com/docker/compose/releases/tag/v2.39.4).
- [AWS: direcciones Elastic IP](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html).

El ensayo local verificó servicios Docker, configuración de Nginx, Gunicorn,
TLS con una CA de ensayo validada, autenticación, permisos y flujo de solicitudes.
No verifica el sistema operativo de la instancia del usuario, sus reglas AWS,
emisión pública ACME, renovación real ni acceso del docente. Esas pruebas solo
pueden completarse después de autorizar y realizar el despliegue.
