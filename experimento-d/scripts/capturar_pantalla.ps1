# Captura la pantalla completa a un PNG. Se usa para las evidencias del
# Experimento D que tienen que mostrar ventanas (las 3 VMs corriendo a la vez,
# las sesiones SSH abiertas), porque esas no se pueden demostrar con un archivo
# de texto.
#
#   .\capturar_pantalla.ps1 -Salida ..\evidencias\01_tres_vms_simultaneas.png
#
# -Segundos espera antes de capturar, para dar tiempo a ordenar las ventanas.

param(
    [Parameter(Mandatory = $true)][string]$Salida,
    [int]$Segundos = 0
)

if ($Segundos -gt 0) { Start-Sleep -Seconds $Segundos }

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$pantalla = [System.Windows.Forms.SystemInformation]::VirtualScreen
$mapa = New-Object System.Drawing.Bitmap $pantalla.Width, $pantalla.Height
$lienzo = [System.Drawing.Graphics]::FromImage($mapa)
$lienzo.CopyFromScreen($pantalla.Location, [System.Drawing.Point]::Empty, $pantalla.Size)

$carpeta = Split-Path -Parent $Salida
if ($carpeta -and -not (Test-Path $carpeta)) { New-Item -ItemType Directory -Path $carpeta | Out-Null }
$mapa.Save($Salida, [System.Drawing.Imaging.ImageFormat]::Png)

$lienzo.Dispose()
$mapa.Dispose()
Write-Host "Captura guardada en $Salida ($($pantalla.Width)x$($pantalla.Height))"
