> Esta guía corresponde a Docker y Nginx. Para la modalidad Apache solicitada, siga [apache-paso-a-paso.md](apache-paso-a-paso.md).

# EC2: instrucciones simples, paso a paso

Esta guía usa la instancia Amazon Linux 2023 que ya tienes. No necesitas crear
otra instancia ni comprar un dominio. Ejecuta cada paso y comprueba su resultado
antes de pasar al siguiente. Si aparece un error, guarda el mensaje y detente.
Estos son pasos para cuando decidas hacer el despliegue; no se ejecutaron en AWS.

## 1. Tener acceso al proyecto y a tu instancia

El proyecto está en la rama proyecto-completo del repositorio
benjidev01/Delegaciones-Municipales. Lo descargaremos directamente en EC2 con
Git. Necesitas la clave .pem con la que accedes a tu instancia.

En los comandos de esta guía reemplaza:

| Marcador | Qué debes escribir |
|---|---|
| IP_PUBLICA | La IPv4 pública de tu instancia |
| CORREO_REAL | Tu correo electrónico |
| C:\ruta\mi-clave.pem | La ruta de tu clave SSH en el PC |

No escribas literalmente IP_PUBLICA o CORREO_REAL. No compartas tu clave PEM.

## 2. Preparar la IP — en la consola de AWS

EC2 → Instancias → selecciona tu instancia y comprueba que está en ejecución.
Anota su IPv4 pública. Para mantener la dirección al detener y volver a iniciar
la instancia, se recomienda asociar una Elastic IP:

EC2 → Red y seguridad → Direcciones IP elásticas → Asignar dirección →
selecciona esa dirección → Acciones → Asociar → selecciona tu instancia.

Usa esa Elastic IP en los pasos siguientes. AWS cobra por IPv4 públicas y por
los recursos de la instancia; no asignes otra si ya tienes una asociada.

## 3. Abrir los puertos — en la consola de AWS

Instancia → pestaña Seguridad → abre el grupo de seguridad → Editar reglas de entrada.

| Tipo | Puerto | Origen |
|---|---:|---|
| SSH | 22 | Mi IP, para conectarte desde tu PC |
| HTTP | 80 | 0.0.0.0/0, para validar el certificado |
| HTTPS | 443 | 0.0.0.0/0, para acceder al sitio |

Guarda las reglas. No abras 5432 ni 8000. Se necesita salida a internet para
descargar imágenes y obtener certificados; las reglas de entrada no crean esa salida.

## 4. Entrar a la instancia — desde PowerShell de tu PC

```powershell
ssh -i "C:\ruta\mi-clave.pem" ec2-user@IP_PUBLICA
```

Verifica la huella SSH por un canal confiable antes de aceptar una conexión
nueva. Desde ahora los comandos se ejecutan dentro de EC2, salvo donde se
indique abrir el navegador del PC. El usuario debe ser ec2-user.

## 5. Descargar el proyecto — dentro de EC2

```sh
sudo dnf install -y git
cd /home/ec2-user
git clone --branch proyecto-completo --single-branch https://github.com/benjidev01/Delegaciones-Municipales.git
```

Resultado: se crea la carpeta Delegaciones-Municipales con el código completo.
Si el repositorio es privado, necesitarás acceso autorizado para clonarlo.

## 6. Instalar Docker — dentro de EC2

```sh
cd /home/ec2-user/Delegaciones-Municipales
sh scripts/install_amazon_linux.sh
```

Si ya existe una carpeta Delegaciones-Municipales, detente antes de clonar para
revisar esa instalación. Al terminar, sal de SSH:

```sh
exit
```

Vuelve a conectarte con el comando SSH del paso 5. Después ejecuta:

```sh
cd /home/ec2-user/Delegaciones-Municipales
docker --version
docker compose version
```

Resultado: ambos comandos muestran una versión. Reconectarse permite usar
Docker con los permisos de grupo que preparó el instalador.

## 7. Liberar 80 y 443 — dentro de EC2

Esta instalación utiliza Nginx de Docker. Comprueba los puertos:

```sh
sudo ss -ltnp '( sport = :80 or sport = :443 )'
```

Si aparece httpd y solo sirve la página de prueba de Apache, detén ese servicio:

```sh
sudo systemctl disable --now httpd
```

Si un Nginx instalado en el host también ocupa esos puertos y no sirve otro sitio:

```sh
sudo systemctl disable --now nginx
```

No instales otro httpd ni otro Nginx con dnf. Repite ss: antes del primer arranque,
los puertos deben estar libres. Si alguno sirve un sitio que necesitas conservar,
no lo detengas: hay que adaptar el despliegue antes de continuar. Si aparece un
contenedor desconocido, comprueba `docker ps` y no lo detengas a ciegas.

## 8. Preparar el sitio — dentro de EC2

Desde /home/ec2-user/Delegaciones-Municipales:

```sh
python3 scripts/prepare_ec2.py --ip IP_PUBLICA --email CORREO_REAL
sh scripts/ec2.sh bootstrap
```

Resultado: arranca el servidor que permitirá validar la IP. En el navegador de
tu PC, abrir http://IP_PUBLICA puede mostrar 503: es esperado en esta etapa.
La aplicación todavía no está activada.

## 9. Obtener HTTPS y activar — dentro de EC2

Ejecuta primero la prueba del certificado:

```sh
sh scripts/ec2.sh cert-test
```

Debe indicar emisión exitosa. Ese certificado de prueba no se usa para el sitio.
Si falla, no avances ni repitas sin revisar IP y puerto 80. Cuando funcione:

```sh
sh scripts/ec2.sh cert-issue
sh scripts/ec2.sh activate
sh scripts/ec2.sh status
```

Resultado: web y db deben estar healthy; proxy debe estar en ejecución.
init y provision deben haber terminado con código 0: es normal que estén detenidos.
La construcción puede tardar varios minutos.

## 10. Elegir las contraseñas — dentro de EC2

Ejecuta un comando a la vez:

```sh
docker compose --env-file .local/ec2.env -f compose.ec2.yaml exec web python manage.py changepassword admin.demo
docker compose --env-file .local/ec2.env -f compose.ec2.yaml exec web python manage.py changepassword delegado.norte
docker compose --env-file .local/ec2.env -f compose.ec2.yaml exec web python manage.py changepassword funcionario.norte
docker compose --env-file .local/ec2.env -f compose.ec2.yaml exec web python manage.py changepassword funcionario.sur
```

Cada comando pide escribir la contraseña dos veces. No se muestran caracteres
al escribir: es normal. Usa al menos 12 caracteres y una contraseña diferente
por cuenta. No captures ni pegues las contraseñas en el informe o el chat.

## 11. Activar renovación — dentro de EC2

El certificado dura pocos días. Configura la renovación para que el docente
pueda seguir entrando durante la evaluación:

```sh
sudo cp deploy/ec2/municipales-renew.service /etc/systemd/system/
sudo cp deploy/ec2/municipales-renew.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now municipales-renew.timer
sudo systemctl start municipales-renew.service
sudo systemctl list-timers municipales-renew.timer
```

Resultado: aparece una próxima ejecución. Si start informa un error, revisar:

```sh
sudo journalctl -u municipales-renew.service -n 30 --no-pager
```

Estas unidades requieren exactamente ec2-user y la carpeta indicada en el paso 6.

## 12. Probar y entregar — en el navegador del PC

Abre `https://IP_PUBLICA/acceso/`. Debe mostrar login sin advertencia de certificado.
Ingresa como funcionario.norte con la contraseña que elegiste. Después prueba
delegado.norte. Entrega al docente la URL y las cuentas, con las contraseñas por
un canal separado. No entregues la clave PEM ni acceso a AWS.

Para su informe, seguir [pruebas y capturas](pruebas-del-informe.md), usando esta
URL pública en lugar de localhost. Si necesita Auditoría, también necesita una
cuenta administradora de evaluación. La aceptación se registra cuando pruebe el sitio.

## Si algo falla

| Qué ocurre | Qué comprobar |
|---|---|
| No puedes clonar | Comprobar acceso al repositorio y rama proyecto-completo |
| Permission denied al usar Docker | Salir de SSH, volver a entrar y probar de nuevo |
| Address already in use / port allocated | Paso 7: comprobar ss y docker ps |
| El certificado no se emite | IP correcta, HTTP 80 público, instancia accesible y salida a internet |
| El sitio no abre después de activar | Ejecutar sh scripts/ec2.sh status y revisar errores |
| Advertencia de certificado en el navegador | No ignorarla; comprobar IP y certificado público emitido |

No ejecutes de nuevo bootstrap después de activar HTTPS: ese comando vuelve a
la configuración inicial de desafíos. No borres volúmenes para solucionar errores.
La guía técnica y los respaldos están en [despliegue EC2](despliegue-ec2.md).
