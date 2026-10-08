# Correspondencia con el informe del usuario

Fecha: 8 de octubre de 2026. Se conserva el informe DOCX original sin cambios.

Cambios de software autorizados: expiración por inactividad de 30 minutos en
servidor y navegador, renovación por interacción, ruta de actividad protegida
por login/POST/CSRF, modo HTTPS local con DEBUG=false y certificados verificables,
pruebas adicionales y guía de capturas CP-01 a CP-15.

La demostración HTTP anterior continúa disponible para desarrollo. Para las
evidencias de HTTPS y DEBUG desactivado del informe debe usarse el modo HTTPS
documentado en pruebas-del-informe.md. No es un despliegue público.

No se pueden fabricar mediante cambios de código actividades del equipo:
roles Scrum, revisión entre integrantes, aceptación humana, ramas por
funcionalidad, commits históricos o una publicación no autorizada. Esas
secciones deben documentar actividades efectivamente realizadas. El usuario
debe revisar el código completo antes de autorizar la publicación.

La configuración admite variables de entorno y archivos privados generados
en un volumen excluido de Git y del paquete. La validación de formularios usa
HTML y mensajes del servidor al enviar; no todos los campos se validan mientras
se escribe. OWASP se evalúa con controles parciales documentados, sin afirmar
certificación o ausencia absoluta de vulnerabilidades.

El sistema permite agenda además del alcance explícito del Sprint del informe;
se conserva porque fue aprobada por el usuario. Los reportes filtran por fecha
de ingreso y estado actual. La cuenta funcionario1 del informe es un ejemplo:
en esta demostración se utiliza funcionario.norte.
