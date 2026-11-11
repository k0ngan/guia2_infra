# Checklist de instalacion manual de un nodo Alpine (QEMU)

Repetir este procedimiento completo 3 veces (nodo0, nodo1, nodo2), cambiando
solo el nombre del disco y el hostname/usuario cuando corresponda.

> **Las tres VMs entregadas no se instalaron asi.** Se instalaron de forma
> desatendida, con el answer file de `setup-alpine -f` escrito por la consola
> serial de QEMU (ver "Instalacion desatendida" al final). Esta checklist
> manual queda porque explica, paso a paso, lo que hace el proceso automatico
> y porque es el camino a seguir si algo falla y hay que intervenir a mano.

## 1. Descargar la ISO de Alpine Linux

- Ir a https://alpinelinux.org/downloads/ y descargar la imagen `virt`
  (x86_64), la mas liviana, apropiada para una VM sin hardware grafico real.
- Guardar como `alpine.iso` en el mismo directorio donde se crearan los discos.

## 2. Crear el disco virtual (qcow2)

```powershell
qemu-img create -f qcow2 nodo0.qcow2 2G
```

Repetir cambiando el nombre para `nodo1.qcow2` y `nodo2.qcow2`.

## 3. Arrancar la VM con la ISO montada (instalacion)

```powershell
qemu-system-x86_64 -m 256 -smp 1 -drive file=nodo0.qcow2,format=qcow2 -cdrom alpine.iso -boot d -netdev user,id=net0 -device e1000,netdev=net0
```

## 4. Dentro de Alpine: instalar el sistema en el disco

- Iniciar sesion como `root` (sin contrasena en el live system).
- Ejecutar el asistente de instalacion:

  ```sh
  setup-alpine
  ```

- Responder el asistente: teclado, hostname (usar `nodo0`, `nodo1` o `nodo2`
  segun corresponda), interfaz de red (`eth0`, DHCP), contrasena de root,
  zona horaria, proxy (ninguno), espejo de paquetes (el que ofrezca por
  defecto), SSH server (elegir `openssh`), disco de instalacion (elegir el
  disco virtual detectado, modo `sys`).
- Al terminar, el instalador puede pedir reiniciar. Si no lo hace automatico,
  apagar con `poweroff`.

## 5. Retirar la ISO y reiniciar desde el disco

- Cerrar la ventana de QEMU (la VM ya esta apagada tras `poweroff`).
- Volver a arrancar la VM **sin** `-cdrom` ni `-boot d`, usando el comando de
  arranque posterior (ver `scripts/arrancar_nodos.ps1`), por ejemplo para nodo0:

```powershell
qemu-system-x86_64 -m 256 -smp 1 -drive file=nodo0.qcow2,format=qcow2 -netdev user,id=net0,hostfwd=tcp:127.0.0.1:2220-:22 -device e1000,netdev=net0
```

Para nodo1 y nodo2 agregar tambien el reenvio del puerto 9000 (ver el script
`arrancar_nodos.ps1`, que ya incluye los mapeos completos de los 3 nodos).

## 6. Dentro de la VM ya instalada: paquetes y servicios

Iniciar sesion como `root` y ejecutar:

```sh
apk update
apk add python3 openssh
rc-update add sshd default
rc-service sshd start
python3 --version
ip addr
ip route
```

Verificar que `sshd` quedo escuchando y que la VM tiene una direccion IP
asignada por DHCP (normalmente `10.0.2.15` en la red user-mode de QEMU).

## 7. Crear el usuario de trabajo

```sh
adduser alumno
```

Seguir las instrucciones (contrasena, datos opcionales). Este es el usuario
que se usara para SSH/SCP desde el anfitrion Windows:

```powershell
ssh -p 2220 alumno@127.0.0.1   # nodo0
ssh -p 2221 alumno@127.0.0.1   # nodo1
ssh -p 2222 alumno@127.0.0.1   # nodo2
```

## 8. Repetir para los 3 nodos

Repetir los pasos 2 a 7 para `nodo1` (hostname `nodo1`) y `nodo2` (hostname
`nodo2`). Usar discos y, si se arrancan simultaneamente para instalar, puertos
SSH temporales distintos (o instalar una VM a la vez, que es mas simple).

## 9. Transferir el codigo del worker a cada worker

Desde el anfitrion, con las VMs corriendo en modo arranque posterior:

```powershell
scp -P 2221 ..\src\worker.py alumno@127.0.0.1:/home/alumno/
scp -P 2222 ..\src\worker.py alumno@127.0.0.1:/home/alumno/
```

## 10. Verificacion final antes de pasar a la Fase 2 de la guia

- `ssh -p 2220 alumno@127.0.0.1`, `-p 2221`, `-p 2222` deben conectar sin error.
- `python3 --version` debe responder en los 3 nodos.
- `worker.py` debe existir en `/home/alumno/` de nodo1 y nodo2.

Con esto el clúster queda listo para la Fase 2 (comunicacion) y Fase 3
(calculo distribuido) descritas en `experimento-d/README.md`.


## Instalacion desatendida (lo que se uso realmente)

Tres instalaciones a mano son tres veces el mismo tecleo y tres oportunidades
de equivocarse en un campo. `setup-alpine` acepta `-f answerfile`, asi que todo
el cuestionario se responde de una vez:

```sh
KEYMAPOPTS="us us"
HOSTNAMEOPTS="nodo0"
DEVDOPTS="mdev"
INTERFACESOPTS="auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
    hostname nodo0
"
DNSOPTS="-n 8.8.8.8 1.1.1.1"
TIMEZONEOPTS="America/Santiago"
PROXYOPTS="none"
APKREPOSOPTS="-1"
SSHDOPTS="openssh"
NTPOPTS="none"
DISKOPTS="-m sys /dev/sda"
LBUOPTS="none"
APKCACHEOPTS="none"
```

El archivo se escribe **dentro** de la VM por la consola serial, con un
heredoc, sin discos auxiliares ni ISO adicional. Para que la consola sea
manejable desde el anfitrion, la VM se arranca con el serial sobre TCP:

```powershell
qemu-system-x86_64 -accel whpx -m 512 -smp 1 `
  -drive file=nodo0.qcow2,format=qcow2 -cdrom alpine-virt-3.24.4-x86_64.iso -boot d `
  -display none -monitor none -serial tcp:127.0.0.1:4555,server=on,wait=off `
  -netdev user,id=net0,hostfwd=tcp:127.0.0.1:2220-:22 -device e1000,netdev=net0
```

Y del otro lado se conecta un socket que espera cada prompt y responde. Tres
preguntas quedan fuera del answer file y hay que contestarlas igual: la clave
de root, `Setup a user? [no]` (el usuario se crea despues, con su clave SSH ya
puesta) y la confirmacion de borrado del disco, que se evita de entrada
exportando `ERASE_DISKS=/dev/sda` antes de llamar a `setup-alpine`.

Despues de instalar, la VM se arranca ya sin ISO y se le aplican, por la misma
consola, los pasos 6 y 7 de esta checklist: `apk add python3`, `adduser -D
alumno`, la clave publica en `authorized_keys` y `rc-update add sshd default`.

Tiempo real del proceso completo en este equipo: unos 12 minutos por nodo para
la instalacion (nodo1 y nodo2 se instalaron en paralelo) y menos de 2 minutos
para el aprovisionamiento de cada uno.
