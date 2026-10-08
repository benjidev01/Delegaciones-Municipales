# EC2 con Apache, paso a paso

Esta modalidad usa Amazon Linux 2023, Apache (`httpd`), Python 3.12, Gunicorn y PostgreSQL 17 instalados directamente. No necesita Docker ni Nginx. El programa sigue siendo Django; no necesita PHP ni MySQL.

Use una instancia dedicada a esta demostración. El instalador conserva la configuración privada y los datos en repeticiones, pero reemplaza el código instalado en `/opt/delegaciones/app`. Si ya tiene otro sitio, una base ajena o una instalación Docker del proyecto en esa máquina, revise la convivencia antes de ejecutarlo. No borre volúmenes ni bases para resolver conflictos.

## 1. Preparar la instancia desde AWS

En la consola EC2, compruebe que su instancia tenga **Amazon Linux 2023**. Se recomienda al menos 2 GiB de RAM para la demostración. Asocie una **Elastic IP** para conservar la dirección del sitio; AWS puede cobrar por los recursos y la IPv4 pública.

En el grupo de seguridad permita:

| Puerto | Origen | Uso |
|---|---|---|
| TCP 22 | Su IP personal | SSH |
| TCP 80 | 0.0.0.0/0 | Validación HTTPS y redirección |
| TCP 443 | 0.0.0.0/0 | Acceso del docente |

No abra 8000, 5432 ni 55432. La instancia necesita salida HTTPS, acceso a los repositorios de Amazon Linux y PyPI. Debe tener ruta a Internet y no bloquear 80/443 con un cortafuegos adicional.

**Captura A:** reglas entrantes del grupo de seguridad. Oculte identificadores de cuenta y cualquier información ajena al informe.

## 2. Conectarse desde su PC

Abra PowerShell en la carpeta donde guardó su clave `.pem`. Sustituya `mi-clave.pem` y `IP_PUBLICA`:

```powershell
ssh -i .\mi-clave.pem ec2-user@IP_PUBLICA
```

Los comandos siguientes se ejecutan **dentro de esa conexión SSH**, salvo el paso de abrir el navegador. Nunca suba la clave `.pem` al repositorio.

## 3. Obtener el código

```bash
sudo dnf install -y git
cd ~
git clone --branch proyecto-completo --single-branch https://github.com/benjidev01/Delegaciones-Municipales.git
cd Delegaciones-Municipales
```

Si ya tiene ese clon, use `git status` para revisar sus cambios antes de actualizarlo. La adaptación Apache está incluida en la rama `proyecto-completo`. Compruebe que existe `scripts/install_apache_amazon_linux.sh` antes de continuar. Si su clon es anterior, actualícelo después de revisar sus cambios locales.

## 4. Revisar quién ocupa los puertos

```bash
sudo ss -ltnp
```

Apache usará 80 y 443. Si `httpd` ya muestra únicamente la página de prueba, puede continuar: será el mismo servicio. Si Nginx o Docker ocupan esos puertos, detenga únicamente la demostración anterior que haya identificado, conservando sus datos. No ejecute dos servidores públicos en el mismo puerto.

## 5. Instalar la aplicación

Sustituya la IP y el correo por los suyos, sin los textos de ejemplo:

```bash
sudo bash scripts/install_apache_amazon_linux.sh IP_PUBLICA tu-correo@ejemplo.com
```

El script instala paquetes y dependencias verificadas por hashes, prepara un usuario de sistema sin inicio de sesión, genera secretos privados, configura la base local, ejecuta migraciones, carga datos ficticios y arranca Apache y Gunicorn. Usa `mod_ssl`; guarda el `ssl.conf` original de la distribución fuera de los archivos activos. Si detecta modificaciones a ese archivo u otros sitios configurados en `conf.d`, se detiene para revisarlos.

No muestra contraseñas. Su configuración privada queda en `/etc/delegaciones/config.json`; no tome capturas ni la publique. Las credenciales demo están en `/var/lib/delegaciones/demo-credentials.json`; el paso 8 permite escoger contraseñas sin mostrar ese archivo.

Antes de emitir HTTPS, la raíz del sitio responde **503** deliberadamente; solo la ruta de validación del certificado queda habilitada.

## 6. Emitir HTTPS para su IP

No requiere dominio. Certbot usa el certificado de IP de corta duración de Let's Encrypt. La IP debe ser pública, estar asociada a esta EC2 y ser accesible desde Internet por el puerto 80.

Ejecute primero la prueba de emisión:

```bash
sudo bash /opt/delegaciones/app/scripts/apache_https.sh test
```

Si termina correctamente, emita el certificado real y active el sitio:

```bash
sudo bash /opt/delegaciones/app/scripts/apache_https.sh issue
sudo bash /opt/delegaciones/app/scripts/apache_https.sh activate
```

El certificado de prueba no se usa para servir el sitio. No instale un certificado de prueba en el navegador ni ignore errores TLS. Si la emisión falla, revise IP pública, reglas, ruta a Internet, reloj y salida del comando antes de volver a intentarlo.

## 7. Comprobar los servicios

```bash
sudo httpd -t
sudo systemctl --no-pager status httpd delegaciones postgresql
sudo ss -ltnp
sudo systemctl list-timers delegaciones-renew.timer
sudo bash /opt/delegaciones/app/scripts/apache_https.sh renew-test
```

Debe ver `Syntax OK`, los tres servicios `active (running)`, Apache en 80/443 y PostgreSQL solamente en direcciones de bucle local. Gunicorn usa un socket privado, sin puerto público 8000. La renovación se comprueba automáticamente cada 12 horas; mantenga la instancia y los puertos accesibles mientras el docente pruebe el sitio.

**Captura B:** `httpd -t` y estado de los servicios.

**Captura C:** listado de puertos y temporizador de renovación. No capture archivos privados ni contraseñas.

## 8. Elegir contraseñas para probar

```bash
sudo municipal-manage changepassword admin.demo
sudo municipal-manage changepassword delegado.norte
sudo municipal-manage changepassword funcionario.norte
sudo municipal-manage changepassword funcionario.sur
```

Cada comando pide la contraseña dos veces y no la muestra. Use al menos 12 caracteres y contraseñas distintas. Para el docente puede crear un usuario específico desde la administración Django y concederle el rol que necesite para sus pruebas. Entréguele usuario y contraseña por un canal privado.

## 9. Abrirlo desde el navegador de su PC

Abra `https://IP_PUBLICA/acceso/`. También pruebe desde otra conexión, por ejemplo el teléfono con datos móviles, para comprobar que el docente podrá entrar por su cuenta.

**Captura D:** página de acceso con la URL HTTPS y el detalle del certificado válido, sin contraseñas.

**Captura E:** panel después de iniciar sesión, usando datos ficticios.

Para las pruebas funcionales y de seguridad de su informe siga [pruebas-del-informe.md](pruebas-del-informe.md): allí se indican los usuarios, pasos y capturas de cada caso. Estas capturas de instalación complementan esos casos; no sustituyen las pruebas del informe.

## 10. Si aparece un error

```bash
sudo journalctl -u delegaciones -n 50 --no-pager
sudo journalctl -u httpd -n 50 --no-pager
sudo tail -n 50 /var/log/httpd/error_log
```

- **502/503 después de activar HTTPS:** revise `delegaciones`, el socket y los registros Apache.
- **Timeout desde su PC:** compruebe IP, grupo de seguridad y ruta de Internet.
- **CSS ausente:** ejecute `sudo municipal-manage collectstatic --noinput` y `sudo restorecon -R /var/www/delegaciones-static`.
- **Denegación SELinux:** consulte `sudo ausearch -m AVC -ts recent`. No desactive SELinux; revise etiquetas y la denegación concreta.
- **Cambió la IP:** la configuración y el certificado deben actualizarse conjuntamente; la Elastic IP evita este cambio habitual.

## Validación de esta adaptación

Las 115 pruebas de Django se ejecutaron correctamente. Apache 2.4.69 se comprobó con Gunicorn 26.2.0 y un certificado local de ensayo verificado: acceso HTTPS, cookie segura, CSRF, estáticos, redirección HTTP y rechazo de host desconocido. Pasaron además cinco pruebas del generador de configuración y la auditoría de las dependencias de Certbot no encontró vulnerabilidades conocidas. La descarga de paquetes desde `cdn.amazonlinux.com` está bloqueada en el entorno de desarrollo; la instalación nativa completa, SELinux en EC2, la emisión pública y la renovación real deben comprobarse en su instancia con los pasos anteriores. No se ha modificado ni desplegado nada en su AWS.
