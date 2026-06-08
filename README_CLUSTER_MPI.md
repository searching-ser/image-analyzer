# Guia de configuracion del cluster MPI

Esta guia describe como preparar la maquina maestra y las esclavas Ubuntu para ejecutar `image-analyzer` con MPICH 4.2.0, Tailscale y la carpeta compartida `/mnt/mirror`.

Marcadores:

```text
[ESCLAVA]  Paso que debe seguir quien configure una computadora esclava.
[MAESTRA]  Paso que solo se ejecuta en la computadora maestra.
[TODOS]    Paso que se ejecuta tanto en la maestra como en las esclavas.
```

## Ruta rapida para una computadora esclava

Si tu computadora sera una esclava, sigue principalmente estos apartados:

```text
1. [TODOS] Requisitos generales
2. [TODOS] Instalar paquetes base
3. [TODOS] Instalar y conectar Tailscale
4. [ESCLAVA] Tener SSH activo para que la maestra pueda entrar
5. [ESCLAVA] Montar carpeta compartida
6. [TODOS] Instalar MPICH 4.2.0
7. [ESCLAVA] Preparar el repositorio
8. [ESCLAVA] Compilar el proyecto
15. [ESCLAVA] Agregar una nueva esclava, si apenas se esta integrando
```

Los apartados marcados como `[MAESTRA]` normalmente los ejecuta solo quien controla el cluster.

## 1. [TODOS] Requisitos generales

Cada VM debe tener:

- Ubuntu.
- Tailscale conectado al mismo tailnet.
- SSH activo.
- Acceso a la carpeta compartida montada en `/mnt/mirror`.
- MPICH 4.2.0 instalado en `/opt/mpich-4.2.0`.
- El repo `image-analyzer` y el binario `para_image_mpi` compilado localmente.

La maestra actual usa:

```text
usuario: vboxuser
host Tailscale: ubuntu-master
repo: /home/vboxuser/image-analyzer
```

La esclava actual usa:

```text
usuario: searching_ser
host Tailscale: searchingser
repo: /home/searching_ser/image-analyzer
```

## 2. [TODOS] Instalar paquetes base

Ejecutar en la maestra y en cada esclava:

```bash
sudo apt update
sudo apt install -y build-essential gcc g++ gfortran wget tar make openssh-server git
sudo systemctl enable --now ssh
```

## 3. [TODOS] Instalar y conectar Tailscale

Ejecutar en la maestra y en cada esclava:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale status
```

Verifica que cada maquina tenga un nombre claro en Tailscale. Para este proyecto se usa:

```text
ubuntu-master
searchingser
```

Desde la maestra, verifica resolucion y conectividad:

```bash
getent hosts ubuntu-master
getent hosts searchingser
ping -c 2 searchingser
```

## 4. [MAESTRA] Configurar SSH sin contrasena

[ESCLAVA] Antes de este paso, cada esclava solo necesita tener SSH activo:

```bash
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
```

[MAESTRA] Desde la maestra:

```bash
ssh-keygen -t ed25519
ssh-copy-id searching_ser@searchingser
ssh searching_ser@searchingser hostname
```

Debe imprimir el hostname de la esclava sin pedir contrasena.

[MAESTRA] Opcionalmente, configura `~/.ssh/config` en la maestra:

```bash
nano ~/.ssh/config
```

Contenido recomendado:

```text
Host *
    ForwardX11 no
    ForwardX11Trusted no

Host searchingser
    User searching_ser
```

Prueba:

```bash
ssh -x searchingser hostname
```

## 5. [ESCLAVA] Montar carpeta compartida

Todas las maquinas deben ver la misma carpeta en:

```bash
/mnt/mirror
```

Debe contener:

```bash
/mnt/mirror/input
/mnt/mirror/output
```

[TODOS] En cada maquina:

```bash
sudo mkdir -p /mnt/mirror/input /mnt/mirror/output
```

[ESCLAVA] En cada esclava, instala el cliente NFS y crea el punto de montaje:

```bash
sudo apt update
sudo apt install -y nfs-common
sudo mkdir -p /mnt/mirror
```

[ESCLAVA] Monta manualmente la carpeta compartida desde la maestra:

```bash
sudo mount -t nfs4 ubuntu-master:/mnt/mirror /mnt/mirror
```

[ESCLAVA] Si prefieres usar la IP Tailscale de la maestra, por ejemplo `100.107.65.70`:

```bash
sudo mount -t nfs4 100.107.65.70:/mnt/mirror /mnt/mirror
```

[ESCLAVA] Para montaje automatico al iniciar, edita `/etc/fstab` en cada esclava:

```bash
sudo nano /etc/fstab
```

Agrega esta linea:

```text
100.107.65.70:/mnt/mirror /mnt/mirror nfs4 defaults,_netdev 0 0
```

[ESCLAVA] Prueba el montaje automatico:

```bash
sudo umount /mnt/mirror
sudo mount -a
ls /mnt/mirror
```

Verifica que realmente sea compartida:

[MAESTRA] En la maestra:

```bash
echo "master" > /mnt/mirror/test_master.txt
```

[ESCLAVA] En la esclava:

```bash
cat /mnt/mirror/test_master.txt
echo "slave" > /mnt/mirror/test_slave.txt
```

[MAESTRA] En la maestra:

```bash
cat /mnt/mirror/test_slave.txt
```

[ESCLAVA] Tambien asegura que el servidor SSH este instalado y activo en cada esclava:

```bash
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
```

## 6. [TODOS] Instalar MPICH 4.2.0

Ejecutar en la maestra y en cada esclava.

Primero limpia instalaciones previas personalizadas de MPCIH SI EXISTEN:

```bash
sudo apt purge -y mpich libmpich-dev libmpich12 openmpi-bin openmpi-common libopenmpi-dev mpi-default-bin mpi-default-dev
sudo apt autoremove -y

sudo update-alternatives --remove-all mpi 2>/dev/null || true
sudo update-alternatives --remove-all mpirun 2>/dev/null || true

sudo rm -rf /opt/mpich-4.2.0
sudo rm -f /etc/profile.d/mpich-custom.sh
sudo rm -f /etc/ld.so.conf.d/mpich-4.2.0.conf
sudo ldconfig

hash -r

ls -l /usr/bin/mpicc /usr/bin/mpiexec 2>/dev/null
which mpicc
which mpiexec
```

Descarga, compila e instala:

```bash
sudo apt update
sudo apt install -y build-essential gcc g++ gfortran wget tar make

cd /tmp
rm -rf mpich-4.2.0 mpich-4.2.0.tar.gz

wget https://www.mpich.org/static/downloads/4.2.0/mpich-4.2.0.tar.gz
tar -xzf mpich-4.2.0.tar.gz
cd mpich-4.2.0

./configure --prefix=/opt/mpich-4.2.0
make -j$(nproc)
sudo make install

sudo tee /etc/profile.d/mpich-custom.sh > /dev/null <<'EOF'
export PATH=/opt/mpich-4.2.0/bin:$PATH
export LD_LIBRARY_PATH=/opt/mpich-4.2.0/lib:$LD_LIBRARY_PATH
EOF

source /etc/profile.d/mpich-custom.sh
hash -r
```

Configura variables de entorno:

```bash
sudo tee /etc/profile.d/mpich-custom.sh > /dev/null <<'EOF'
export PATH=/opt/mpich-4.2.0/bin:$PATH
export LD_LIBRARY_PATH=/opt/mpich-4.2.0/lib:$LD_LIBRARY_PATH
EOF

source /etc/profile.d/mpich-custom.sh
hash -r
```

Verifica:

```bash
which mpicc
which mpiexec
mpichversion | grep -E "MPICH Version|MPICH Device|configure"
```

Debe mostrar:

```text
/opt/mpich-4.2.0/bin/mpicc
/opt/mpich-4.2.0/bin/mpiexec
MPICH Version: 4.2.0
MPICH Device: ch4:ofi
```

## 7. [TODOS] Preparar el repositorio

[MAESTRA] En la maestra:

```bash
cd /home/vboxuser/image-analyzer
git pull
```

[ESCLAVA] En la esclava:

```bash
cd /home/searching_ser/image-analyzer
git pull
```

[ESCLAVA] Si es una nueva esclava, clona el repo:

```bash
cd /home/searching_ser
git clone <URL_DEL_REPO> image-analyzer
cd image-analyzer
```

## 8. [TODOS] Compilar el proyecto

[MAESTRA] En la maestra:

```bash
cd /home/vboxuser/image-analyzer
/opt/mpich-4.2.0/bin/mpicc -Wall -Wextra -std=c11 -fopenmp para_image_mpi.c selec_proc.c -o para_image_mpi
chmod +x para_image_mpi
ldd ./para_image_mpi | grep mpich
```

[ESCLAVA] En la esclava:

```bash
cd /home/searching_ser/image-analyzer
/opt/mpich-4.2.0/bin/mpicc -Wall -Wextra -std=c11 -fopenmp para_image_mpi.c selec_proc.c -o para_image_mpi
chmod +x para_image_mpi
ldd ./para_image_mpi | grep mpich
```

El `ldd` debe resolver `libmpich` desde `/opt/mpich-4.2.0/lib`.

## 9. [MAESTRA] Configurar machinefile

En la maestra, edita:

```bash
nano /home/vboxuser/image-analyzer/machinefile
```

Para una maestra y una esclava:

```text
ubuntu-master:1
searching_ser@searchingser:1
```

Para agregar mas esclavas, agrega una linea por esclava:

```text
usuario@nombre-tailscale:1
```

La GUI de `main.py` lee este archivo para decidir cuantas maquinas usar. El programa lanza un proceso MPI por cada linea del `machinefile`.

El binario `para_image_mpi` reparte las imagenes entre todos los procesos MPI disponibles, incluyendo rank 0. Es decir, la maestra ya no solo asigna tareas: tambien procesa su parte de las imagenes.

## 10. [MAESTRA] Probar MPI basico

Desde la maestra:

```bash
FI_PROVIDER=tcp \
FI_TCP_IFACE=tailscale0 \
/opt/mpich-4.2.0/bin/mpiexec \
  -launcher ssh \
  -disable-x \
  -genv FI_PROVIDER tcp \
  -genv FI_TCP_IFACE tailscale0 \
  -localhost ubuntu-master \
  -f /home/vboxuser/image-analyzer/machinefile \
  -wdir /mnt/mirror \
  -prepend-rank \
  -n 2 hostname
```

Debe imprimir dos hosts, por ejemplo:

```text
[0] UbuntuRedes
[1] searchingser
```

## 11. [TODOS] Probar hello_mpi

Compila y corre `hello_mpi.c` en la maestra:

```bash
cd /home/vboxuser/image-analyzer

/opt/mpich-4.2.0/bin/mpicc hello_mpi.c -o hello_mpi

/opt/mpich-4.2.0/bin/mpich -prepend-rank -n 2 ./hello_mpi
```



[MAESTRA] Prueba distribuida:

```bash
FI_PROVIDER=tcp \
FI_TCP_IFACE=tailscale0 \
/opt/mpich-4.2.0/bin/mpiexec \
  -launcher ssh \
  -disable-x \
  -genv FI_PROVIDER tcp \
  -genv FI_TCP_IFACE tailscale0 \
  -localhost ubuntu-master \
  -f /home/vboxuser/image-analyzer/machinefile \
  -wdir /mnt/mirror \
  -prepend-rank \
  -n 1 /home/vboxuser/image-analyzer/hello_mpi \
  : \
  -wdir /mnt/mirror \
  -n 1 /home/searching_ser/image-analyzer/hello_mpi
```

Debe pasar de `before MPI_Init` e imprimir los ranks.

## 12. [MAESTRA] Preparar imagen de prueba

En la maestra:

```bash
mkdir -p /mnt/mirror/input /mnt/mirror/output
cp /home/vboxuser/image-analyzer/input/prueba1.bmp /mnt/mirror/input/test.bmp
rm -f /mnt/mirror/output/*
```

[MAESTRA] Verifica en la esclava:

```bash
ssh searching_ser@searchingser 'ls -l /mnt/mirror/input/test.bmp /mnt/mirror/output'
```

## 13. [MAESTRA] Probar el proyecto distribuido

Desde la maestra:

```bash
FI_PROVIDER=tcp \
FI_TCP_IFACE=tailscale0 \
/opt/mpich-4.2.0/bin/mpiexec \
  -launcher ssh \
  -disable-x \
  -genv FI_PROVIDER tcp \
  -genv FI_TCP_IFACE tailscale0 \
  -genv LD_LIBRARY_PATH /opt/mpich-4.2.0/lib \
  -localhost ubuntu-master \
  -f /home/vboxuser/image-analyzer/machinefile \
  -wdir /mnt/mirror \
  -prepend-rank \
  -n 1 /home/vboxuser/image-analyzer/para_image_mpi \
  12 /mnt/mirror/output /mnt/mirror/input/test.bmp --vg \
  : \
  -wdir /mnt/mirror \
  -n 1 /home/searching_ser/image-analyzer/para_image_mpi \
  12 /mnt/mirror/output /mnt/mirror/input/test.bmp --vg
```

Verifica resultado:

```bash
ls -l /mnt/mirror/output
```

Debe aparecer:

```text
test_vg.bmp
```

## 14. [MAESTRA] Probar desde la GUI

En la maestra:

```bash
cd /home/vboxuser/image-analyzer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

La GUI usa:

```python
SHARED_ROOT = Path("/mnt/mirror")
MPI_LAUNCHER = "/opt/mpich-4.2.0/bin/mpiexec"
MPI_MASTER_HOST = "ubuntu-master"
MPI_MACHINEFILE = ".../machinefile"
```

Tambien fuerza OFI por TCP sobre Tailscale:

```python
"-genv", "FI_PROVIDER", "tcp",
"-genv", "FI_TCP_IFACE", "tailscale0",
```

## 15. [ESCLAVA] Agregar una nueva esclava

En la nueva esclava:

1. Instala paquetes base.
2. Instala Tailscale y conectala al mismo tailnet.
3. Monta `/mnt/mirror`.
4. Instala MPICH 4.2.0 en `/opt/mpich-4.2.0`.
5. Clona el repo.
6. Compila `para_image_mpi`.
7. Configura SSH sin contrasena desde la maestra.

[MAESTRA] Desde la maestra:

```bash
ssh-copy-id usuario@nuevo-host-tailscale
ssh usuario@nuevo-host-tailscale hostname
```

[MAESTRA] Agrega al `machinefile`:

```text
usuario@nuevo-host-tailscale:1
```

[MAESTRA] Actualiza `main.py`:

```python
MPI_HOSTS = [
    "ubuntu-master",
    "searching_ser@searchingser",
    "usuario@nuevo-host-tailscale",
]

MPI_HOST_EXECUTABLES = {
    "ubuntu-master": "/home/vboxuser/image-analyzer/para_image_mpi",
    "searching_ser@searchingser": "/home/searching_ser/image-analyzer/para_image_mpi",
    "usuario@nuevo-host-tailscale": "/home/usuario/image-analyzer/para_image_mpi",
}
```

[MAESTRA] Prueba:

```bash
FI_PROVIDER=tcp \
FI_TCP_IFACE=tailscale0 \
/opt/mpich-4.2.0/bin/mpiexec \
  -launcher ssh \
  -disable-x \
  -genv FI_PROVIDER tcp \
  -genv FI_TCP_IFACE tailscale0 \
  -localhost ubuntu-master \
  -f /home/vboxuser/image-analyzer/machinefile \
  -wdir /mnt/mirror \
  -prepend-rank \
  -n 3 hostname
```

## 16. [TODOS] Problemas comunes

### `hello_mpi` se queda en `MPI_Init`

Usa OFI por TCP/Tailscale:

```bash
FI_PROVIDER=tcp
FI_TCP_IFACE=tailscale0
```

Y pasa:

```bash
-genv FI_PROVIDER tcp
-genv FI_TCP_IFACE tailscale0
```

### `libmpich.so.12 => not found`

En la maquina afectada:

```bash
source /etc/profile.d/mpich-custom.sh
ldd /ruta/al/binario/para_image_mpi | grep mpich
```

Si sigue fallando:

```bash
echo /opt/mpich-4.2.0/lib | sudo tee /etc/ld.so.conf.d/mpich-4.2.0.conf
sudo ldconfig
```

### `unable to change wdir`

Usa:

```bash
-wdir /mnt/mirror
```

en cada bloque MPMD.

### `Authorization required, but no authorization protocol specified`

Usa:

```bash
-disable-x
```

y en `~/.ssh/config`:

```text
Host *
    ForwardX11 no
    ForwardX11Trusted no
```

### `Host key verification failed`

Ejecuta SSH manualmente y acepta la llave:

```bash
ssh usuario@host hostname
```

### El binario local funciona pero distribuido no

Verifica en la esclava:

```bash
ssh usuario@host 'ldd /ruta/al/para_image_mpi | grep mpich'
ssh usuario@host 'ls -l /mnt/mirror/input /mnt/mirror/output'
ssh usuario@host '/opt/mpich-4.2.0/bin/mpichversion | grep -E "MPICH Version|MPICH Device"'
```
