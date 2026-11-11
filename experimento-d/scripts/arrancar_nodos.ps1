# Experimento D - arranque posterior de las 3 VMs del cluster virtual.
#
# Requiere que las 3 imagenes qcow2 ya existan y tengan Alpine instalado
# (ver instalar_nodo.md). Este script NO instala nada: solo arranca los
# discos ya preparados, con el reenvio de puertos (hostfwd) que necesita
# el protocolo coordinador-worker.
#
# IMPORTANTE: cada bloque de qemu-system-x86_64 debe ejecutarse en SU PROPIA
# ventana de PowerShell, porque QEMU bloquea la consola mientras la VM esta
# corriendo. Hay dos formas de hacerlo:
#
#   1) Manual: abrir 3 ventanas de PowerShell y copiar un bloque en cada una.
#   2) Automatica: ejecutar este script tal cual: usa Start-Process para
#      lanzar cada VM en su propia ventana nueva, dejando la ventana actual libre.
#
# Las imagenes se buscan en el mismo directorio que este script, salvo que se
# pase -DiscoDir con otra ruta: los discos de la corrida entregada viven fuera
# del repositorio, para no versionar medio giga de qcow2.
#
#   .\arrancar_nodos.ps1 -DiscoDir D:\vms\experimento-d
#
# -Accel elige el acelerador: whpx usa el hipervisor de Windows -lo que se uso
# en la corrida medida- y tcg emula por software si whpx no esta disponible.

param(
    [string]$DiscoDir = $PSScriptRoot,
    [string]$Accel = "whpx",
    [string]$Qemu = "C:\Program Files\qemu\qemu-system-x86_64.exe"
)

$discoDir = $DiscoDir
if (-not (Test-Path $Qemu)) { $Qemu = "qemu-system-x86_64" }
$comun = "-accel $Accel -m 512 -smp 1"
# Puerto QMP por nodo (5900/5901/5902): permite pedirle a QEMU una captura
# de la consola de cada VM (screendump) sin depender de las ventanas del
# escritorio. Lo usa capturar_consolas.py para las evidencias.
$qmp0 = "-qmp tcp:127.0.0.1:5900,server=on,wait=off"
$qmp1 = "-qmp tcp:127.0.0.1:5901,server=on,wait=off"
$qmp2 = "-qmp tcp:127.0.0.1:5902,server=on,wait=off"

$nodo0 = "$comun $qmp0 -name nodo0 -drive file=$discoDir\nodo0.qcow2,format=qcow2 " +
         "-netdev user,id=net0,hostfwd=tcp:127.0.0.1:2220-:22 -device e1000,netdev=net0"

$nodo1 = "$comun $qmp1 -name nodo1 -drive file=$discoDir\nodo1.qcow2,format=qcow2 " +
         "-netdev user,id=net1,hostfwd=tcp:127.0.0.1:2221-:22,hostfwd=tcp:127.0.0.1:9001-:9000 " +
         "-device e1000,netdev=net1"

$nodo2 = "$comun $qmp2 -name nodo2 -drive file=$discoDir\nodo2.qcow2,format=qcow2 " +
         "-netdev user,id=net2,hostfwd=tcp:127.0.0.1:2222-:22,hostfwd=tcp:127.0.0.1:9002-:9000 " +
         "-device e1000,netdev=net2"

Write-Host "Lanzando nodo0 (coordinador) en una nueva ventana..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$Qemu' $nodo0"

Write-Host "Lanzando nodo1 (worker1) en una nueva ventana..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$Qemu' $nodo1"

Write-Host "Lanzando nodo2 (worker2) en una nueva ventana..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$Qemu' $nodo2"

Write-Host ""
Write-Host "Las 3 VMs deberian estar arrancando en ventanas separadas."
Write-Host "Verificar disponibilidad de los workers con, por ejemplo:"
Write-Host "    Test-NetConnection 127.0.0.1 -Port 9001"
Write-Host "    Test-NetConnection 127.0.0.1 -Port 9002"
Write-Host "y acceso SSH con:"
Write-Host "    ssh -p 2220 alumno@127.0.0.1   # nodo0"
Write-Host "    ssh -p 2221 alumno@127.0.0.1   # nodo1"
Write-Host "    ssh -p 2222 alumno@127.0.0.1   # nodo2"

# Comandos equivalentes para ejecutar manualmente, uno por ventana:
#
# qemu-system-x86_64 -m 256 -smp 1 -drive file=nodo0.qcow2,format=qcow2 -netdev user,id=net0,hostfwd=tcp:127.0.0.1:2220-:22 -device e1000,netdev=net0
#
# $net1 = 'user,id=net1,hostfwd=tcp:127.0.0.1:2221-:22,hostfwd=tcp:127.0.0.1:9001-:9000'
# qemu-system-x86_64 -m 256 -smp 1 -drive file=nodo1.qcow2,format=qcow2 -netdev $net1 -device e1000,netdev=net1
#
# $net2 = 'user,id=net2,hostfwd=tcp:127.0.0.1:2222-:22,hostfwd=tcp:127.0.0.1:9002-:9000'
# qemu-system-x86_64 -m 256 -smp 1 -drive file=nodo2.qcow2,format=qcow2 -netdev $net2 -device e1000,netdev=net2
