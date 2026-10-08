#!/bin/sh
# Run only on the user's authorized Amazon Linux 2023 instance.
set -eu
. /etc/os-release
if [ "$ID" != amzn ] || [ "$VERSION_ID" != 2023 ]; then
  echo 'Este instalador requiere Amazon Linux 2023.' >&2
  exit 1
fi
sudo dnf install -y docker python3 curl tar gzip
sudo systemctl enable --now docker
if ! docker compose version >/dev/null 2>&1; then
  compose_version=v2.39.4
  architecture=$(uname -m)
  case "$architecture" in x86_64|aarch64) ;; *) echo 'Arquitectura no soportada.' >&2; exit 1;; esac
  filename="docker-compose-linux-$architecture"
  task_tmp=$(mktemp -d)
  trap 'rm -rf "$task_tmp"' EXIT HUP INT TERM
  curl --fail --location --proto '=https' --tlsv1.2 \
    "https://github.com/docker/compose/releases/download/$compose_version/$filename" -o "$task_tmp/$filename"
  curl --fail --location --proto '=https' --tlsv1.2 \
    "https://github.com/docker/compose/releases/download/$compose_version/checksums.txt" -o "$task_tmp/checksums.txt"
  awk -v file="$filename" '{name=$2; sub(/^\*/, "", name); if (name == file) print}' "$task_tmp/checksums.txt" > "$task_tmp/selected.sha256"
  test -s "$task_tmp/selected.sha256"
  (cd "$task_tmp" && sha256sum --check --strict selected.sha256)
  sudo mkdir -p /usr/local/lib/docker/cli-plugins
  sudo install -m 0755 "$task_tmp/$filename" /usr/local/lib/docker/cli-plugins/docker-compose
fi
sudo usermod -aG docker ec2-user
echo 'Docker preparado. Salga de SSH y vuelva a ingresar para activar el grupo docker.'
