# Diccionario de datos

Campos del modelo propio. No incluye valores ni credenciales.


## delegaciones.Delegacion

| Campo | Tipo | Nulo | Relación |
|---|---|---|---|
| id | BigAutoField | No | — |
| nombre | CharField | No | — |
| direccion | CharField | No | — |
| activa | BooleanField | No | — |

## cuentas.Usuario

| Campo | Tipo | Nulo | Relación |
|---|---|---|---|
| id | BigAutoField | No | — |
| password | CharField | No | — |
| last_login | DateTimeField | Sí | — |
| is_superuser | BooleanField | No | — |
| username | CharField | No | — |
| first_name | CharField | No | — |
| last_name | CharField | No | — |
| email | CharField | No | — |
| is_staff | BooleanField | No | — |
| is_active | BooleanField | No | — |
| date_joined | DateTimeField | No | — |
| rol | CharField | No | — |
| delegacion | ForeignKey | Sí | delegaciones.Delegacion |

## vecinos.Vecino

| Campo | Tipo | Nulo | Relación |
|---|---|---|---|
| id | BigAutoField | No | — |
| delegacion | ForeignKey | No | delegaciones.Delegacion |
| rut | CharField | No | — |
| nombre | CharField | No | — |
| email | CharField | No | — |
| telefono | CharField | No | — |
| direccion | CharField | No | — |

## solicitudes.Solicitud

| Campo | Tipo | Nulo | Relación |
|---|---|---|---|
| id | BigAutoField | No | — |
| folio | UUIDField | No | — |
| delegacion | ForeignKey | No | delegaciones.Delegacion |
| vecino | ForeignKey | No | vecinos.Vecino |
| tipo | CharField | No | — |
| descripcion | TextField | No | — |
| estado | CharField | No | — |
| creador | ForeignKey | No | cuentas.Usuario |
| responsable | ForeignKey | Sí | cuentas.Usuario |
| creada_en | DateTimeField | No | — |
| actualizada_en | DateTimeField | No | — |

## solicitudes.Observacion

| Campo | Tipo | Nulo | Relación |
|---|---|---|---|
| id | BigAutoField | No | — |
| solicitud | ForeignKey | No | solicitudes.Solicitud |
| autor | ForeignKey | No | cuentas.Usuario |
| texto | TextField | No | — |
| fecha | DateTimeField | No | — |

## solicitudes.CambioEstado

| Campo | Tipo | Nulo | Relación |
|---|---|---|---|
| id | BigAutoField | No | — |
| solicitud | ForeignKey | No | solicitudes.Solicitud |
| actor | ForeignKey | No | cuentas.Usuario |
| anterior | CharField | No | — |
| nuevo | CharField | No | — |
| motivo | TextField | No | — |
| fecha | DateTimeField | No | — |

## auditoria.Evento

| Campo | Tipo | Nulo | Relación |
|---|---|---|---|
| id | BigAutoField | No | — |
| actor | ForeignKey | Sí | cuentas.Usuario |
| accion | CharField | No | — |
| entidad | CharField | No | — |
| objeto_id | CharField | No | — |
| fecha | DateTimeField | No | — |

## agenda.Cita

| Campo | Tipo | Nulo | Relación |
|---|---|---|---|
| id | BigAutoField | No | — |
| delegacion | ForeignKey | No | delegaciones.Delegacion |
| vecino | ForeignKey | No | vecinos.Vecino |
| funcionario | ForeignKey | No | cuentas.Usuario |
| solicitud | ForeignKey | Sí | solicitudes.Solicitud |
| inicio | DateTimeField | No | — |
| fin | DateTimeField | No | — |
| estado | CharField | No | — |
| motivo | CharField | No | — |
| creador | ForeignKey | No | cuentas.Usuario |
| creada_en | DateTimeField | No | — |
| actualizada_en | DateTimeField | No | — |

## agenda.CambioCita

| Campo | Tipo | Nulo | Relación |
|---|---|---|---|
| id | BigAutoField | No | — |
| cita | ForeignKey | No | agenda.Cita |
| actor | ForeignKey | No | cuentas.Usuario |
| anterior | CharField | No | — |
| nuevo | CharField | No | — |
| motivo | TextField | No | — |
| fecha | DateTimeField | No | — |
