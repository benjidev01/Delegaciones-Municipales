# Dependencias opcionales para construcción sin descargas de pip

Este archivo mantiene el directorio vendor en Git. Las ruedas de terceros de
vendor/wheels están excluidas de Git, pero el ZIP de entrega puede incluirlas.
Los Dockerfiles comprueban todos los paquetes con los hashes del lockfile.
Si no hay ruedas, utilizan el índice de Python por HTTPS durante la construcción.

Para preparar ruedas de producción desde una máquina con Python y pip, con
destino Docker Linux x86_64/Python 3.12:

```sh
python -m pip download --require-hashes --only-binary=:all: \
  --platform manylinux2014_x86_64 --python-version 3.12 --implementation cp --abi cp312 \
  -r requirements-prod.lock --dest vendor/wheels
```

Para Linux ARM64 cambiar la plataforma por manylinux2014_aarch64. No usar
ruedas nativas de Windows para una imagen Docker Linux. No desactivar TLS ni
alterar hashes cuando falle una descarga.
