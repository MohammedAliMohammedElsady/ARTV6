# ARTV3 Release and Deployment Guide

This guide explains how to:

- Build the ARTV3 Docker image.
- Bundle required images into a single tar.
- Collect deployment assets.
- Create a distributable archive for the infra team.

Use Linux/macOS/WSL for best results. Prefix commands with `sudo` if required by your Docker setup.

## 1) Prerequisites

- Docker Engine 20.10+ and Docker Compose v2+ installed.
- Access to the project root (contains `Dockerfile`, `docker-compose.yml`, `docker/`, `DB_SCRIPTS/`, `DGUM_Cetificates/`).
- Optional: Redis image `redis:7` will be bundled along with `artv3:latest`.

## 2) Build the ARTV3 Image

```bash
# From project root
docker build -t artv3:latest --target dev .
```

- To make sure Redis is present locally:

```bash
docker pull redis:7
```

## 3) Save Images to a Single TAR

```bash
# Bundle ARTV3 and Redis images together
docker save -o artv3_bundle.tar artv3:latest redis:7


sudo docker save -o artv3_hdb.tar artv3:latest redis:7
```

- Verify the tar contains both images:

```bash
tar -tf artv3_bundle.tar | head -50

tar -tf artv3_hdb.tar | head -50
```

## 4) Assemble the Release Folder

```bash
RELEASE_DIR="artv3_release_$(date +%Y%m%d)"
mkdir -p "$RELEASE_DIR"

# Copy required assets
cp -r docker "$RELEASE_DIR"/
cp docker-compose.yml "$RELEASE_DIR"/
cp -r DB_SCRIPTS "$RELEASE_DIR"/
cp -r DGUM_Cetificates "$RELEASE_DIR"/

Copy-Item -Recurse docker "$RELEASE_DIR\"   powershell

# Add images bundle
mv artv3_hdb.tar "$RELEASE_DIR"/

```

Expected layout:

$RELEASE_DIR/
docker/
docker-compose.yml
DB_SCRIPTS/
DGUM_Cetificates/
artv3_bundle.tar

## 5) Create the Compressed Archive

```bash
tar -czf "${RELEASE_DIR}.tar.gz" "$RELEASE_DIR"
```

(Optional) Generate checksums to verify integrity after transfer:

```bash
sha256sum "${RELEASE_DIR}.tar.gz" > "${RELEASE_DIR}.tar.gz.sha256"
```

## 6) What to Send to Infra

- The file: `${RELEASE_DIR}.tar.gz`
- Optional: `${RELEASE_DIR}.tar.gz.sha256`

ARTV3 Release Guide v1.0
