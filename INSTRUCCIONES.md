# Instrucciones de Delegaciones Municipales

La rama `proyecto-completo` incluye la aplicación, las pruebas, los scripts,
la configuración de despliegue y estos documentos. Para obtenerla:

```sh
git clone --branch proyecto-completo --single-branch https://github.com/benjidev01/Delegaciones-Municipales.git
```

También se puede seleccionar esa rama en GitHub y usar Code → Download ZIP.

## Instancia AWS: empezar aquí

- [EC2 paso a paso](docs/ec2-paso-a-paso.md): guía sencilla, comandos en orden,
  comprobaciones y solución del conflicto entre httpd y Nginx.
- [EC2 paso a paso en PDF](docs/ec2-paso-a-paso.pdf).
- [Guía técnica de EC2](docs/despliegue-ec2.md): IP pública, HTTPS, certificados,
  renovación, cuentas, respaldos y mantenimiento.
- [Guía técnica de EC2 en PDF](docs/despliegue-ec2.pdf).

## Ejecutar y probar en el PC

- [Cómo probar el software](docs/como-probar.md).
- [Cómo probar el software en PDF](docs/como-probar.pdf).
- [Pruebas del informe: CP-01 a CP-15 y capturas](docs/pruebas-del-informe.md).
- [Pruebas del informe en PDF](docs/pruebas-del-informe.pdf).

## Documentación de apoyo

- [Diseño y UML](docs/diseno.md).
- [Diccionario de datos](docs/diccionario-datos.md).
- [Pruebas del primer sprint](docs/pruebas-sprint-1.md).
- [Pruebas del segundo incremento](docs/pruebas-sprint-2.md).
- [Revisión de seguridad](docs/revision-seguridad.md).
- [Correspondencia con el informe](docs/ajustes-al-informe.md).

El despliegue en la instancia del usuario y la emisión/renovación pública del
certificado no se han realizado. Los resultados técnicos documentados
corresponden a ensayos locales; la aceptación del docente queda pendiente.

## Despliegue recomendado en su EC2: Apache

Siga [la guía Apache paso a paso](docs/apache-paso-a-paso.md) para Amazon Linux 2023, sin Docker ni Nginx. Apache atiende 80/443 y Gunicorn ejecuta Django mediante un socket privado. Las guías EC2 anteriores con Docker siguen disponibles como alternativa; use una modalidad completa.
