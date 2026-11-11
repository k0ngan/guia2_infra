# Ordena las 3 ventanas de QEMU una al lado de la otra y captura SOLO esa
# region de la pantalla. Es la evidencia 1 del Experimento D: las tres VMs
# corriendo al mismo tiempo, con el hostname visible en cada consola.
#
#   .\capturar_vms.ps1 -Salida ..\evidencias\01_tres_vms_simultaneas.png
#
# Captura un recorte y no el escritorio completo, para no arrastrar al informe
# ventanas ajenas al experimento.

param(
    [Parameter(Mandatory = $true)][string]$Salida,
    [int]$Ancho = 740,
    [int]$Alto = 480
)

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Ventanas {
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr tras, int x, int y, int cx, int cy, uint flags);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
}
"@

$qemu = Get-Process qemu-system-x86_64 -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowTitle -match "QEMU" } |
        Sort-Object MainWindowTitle

if ($qemu.Count -lt 1) { throw "No hay ventanas de QEMU visibles." }
Write-Host "Ventanas encontradas: $($qemu.MainWindowTitle -join ', ')"

# HWND_TOPMOST mientras dura la captura: si no, cualquier ventana de encima
# (la terminal desde la que se lanza esto, sin ir mas lejos) tapa las consolas.
$TOPMOST = [IntPtr](-1)
$NOTOPMOST = [IntPtr](-2)
$i = 0
foreach ($p in $qemu) {
    [Ventanas]::ShowWindow($p.MainWindowHandle, 9) | Out-Null          # restaurar
    [Ventanas]::SetWindowPos($p.MainWindowHandle, $TOPMOST,
                             $i * $Ancho, 0, $Ancho, $Alto, 0x0040) | Out-Null
    Start-Sleep -Milliseconds 400
    $i++
}
Start-Sleep -Seconds 2

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$w = $Ancho * $qemu.Count
$mapa = New-Object System.Drawing.Bitmap $w, $Alto
$lienzo = [System.Drawing.Graphics]::FromImage($mapa)
$lienzo.CopyFromScreen(0, 0, 0, 0, (New-Object System.Drawing.Size $w, $Alto))

$carpeta = Split-Path -Parent $Salida
if ($carpeta -and -not (Test-Path $carpeta)) { New-Item -ItemType Directory -Path $carpeta | Out-Null }
$mapa.Save($Salida, [System.Drawing.Imaging.ImageFormat]::Png)
$lienzo.Dispose(); $mapa.Dispose()

foreach ($p in $qemu) {
    [Ventanas]::SetWindowPos($p.MainWindowHandle, $NOTOPMOST, 0, 0, 0, 0, 0x0003) | Out-Null
}
Write-Host "Captura de $($qemu.Count) VMs guardada en $Salida (${w}x${Alto})"
