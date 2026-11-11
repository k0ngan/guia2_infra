@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"
title Guia 2 - Infraestructura para Ciencia de Datos (INFB6074)

REM ---------------------------------------------------------------------------
REM Lanzador por partes de la Guia 2. Cada opcion corre un trozo y se detiene
REM para que la salida se pueda leer durante una presentacion.
REM
REM Usa "python" y no "py" a proposito: en este equipo "py" resuelve a 3.12,
REM que no tiene las dependencias; "python" resuelve a 3.9.13, que si las tiene.
REM
REM Se puede usar de dos formas:
REM     ejecutar.bat        -> menu interactivo
REM     ejecutar.bat 3      -> corre directo la opcion 3 y termina
REM ---------------------------------------------------------------------------

set "PY=python"
set "DIRECTO="
set "VACIAS=0"

if not "%~1"=="" (
    set "DIRECTO=1"
    set "OPCION=%~1"
    goto despacho
)

:menu
cls
echo ===========================================================================
echo   GUIA 2 - Paralelismo local y procesamiento distribuido
echo   INFB6074 Infraestructura para Ciencia de Datos - UTEM 2026-2
echo ===========================================================================
echo.
echo   PREPARACION
echo     1. Verificar entorno (Python y dependencias)
echo     2. Respaldar las evidencias antes de regenerar nada
echo.
echo   EXPERIMENTOS
echo     3. Experimento A - NumPy vs Python puro vs multiprocessing     (~40s)
echo     4. Experimento B - Hilos vs procesos, CPU-bound e I/O-bound    (~30s)
echo     5. Experimento C - Dask vs Pandas sobre datos particionados    (~20s)
echo     6. Experimento D - Simulacion local del cluster, sin VMs       (~15s)
echo     7. Experimento D - Como correrlo sobre el cluster QEMU real
echo.
echo   INFORME Y EVIDENCIAS
echo     8. Compilar informe_guia2.tex a PDF
echo     9. Abrir el informe y las carpetas de evidencias
echo.
echo   ATAJOS
echo    10. Corrida completa A + B + C
echo     0. Salir
echo.
set "OPCION="
set /p "OPCION=Elige una opcion: "

REM Si la entrada viene de una tuberia y se agota, set /p deja OPCION vacia y
REM el menu giraria para siempre. Tras tres vacias seguidas, salir.
if "%OPCION%"=="" (
    set /a VACIAS+=1
    if !VACIAS! GEQ 3 goto fin
    goto menu
)
set "VACIAS=0"

:despacho
if "%OPCION%"=="1"  goto entorno
if "%OPCION%"=="2"  goto respaldo
if "%OPCION%"=="3"  goto expA
if "%OPCION%"=="4"  goto expB
if "%OPCION%"=="5"  goto expC
if "%OPCION%"=="6"  goto expD
if "%OPCION%"=="7"  goto expDreal
if "%OPCION%"=="8"  goto informe
if "%OPCION%"=="9"  goto abrir
if "%OPCION%"=="10" goto todo
if "%OPCION%"=="0"  goto fin
if defined DIRECTO (
    echo Opcion "%OPCION%" no valida. Opciones: 1 a 10.
    popd
    endlocal
    exit /b 2
)
goto menu

REM ===========================================================================
:entorno
cls
echo === Verificacion del entorno ===
echo.
%PY% --version
if errorlevel 1 (
    echo.
    echo ERROR: no se encontro "python" en el PATH.
    goto volver
)
echo.
echo Dependencias:
for %%M in (numpy pandas matplotlib dask psutil) do (
    %PY% -c "import %%M" >nul 2>&1
    if errorlevel 1 (
        echo    FALTA  %%M
    ) else (
        echo    OK     %%M
    )
)
echo.
echo Si falta alguna:
echo     %PY% -m pip install -r requirements.txt
echo.
echo Nucleos logicos disponibles:
%PY% -c "import os; print('   ', os.cpu_count())"
goto volver

REM ===========================================================================
:respaldo
cls
echo === Respaldo de evidencias ===
echo.
call :marcadetiempo
for %%E in (a b c d) do (
    if exist "experimento-%%E\evidencias" (
        xcopy "experimento-%%E\evidencias" "experimento-%%E\evidencias_respaldo_!TS!\" /E /I /Q /Y >nul
        echo    experimento-%%E\evidencias_respaldo_!TS!\
    )
)
echo.
echo Respaldo hecho. Las corridas siguientes ya no pueden perder nada.
goto volver

REM ===========================================================================
:expA
cls
echo === EXPERIMENTO A - Paralelismo de datos y vectorizacion ===
echo.
echo Aplica la misma transformacion numerica por tres caminos (Python puro,
echo NumPy vectorizado y multiprocessing) sobre 5 tamanos, de 10^4 a 2x10^7.
echo Verifica con np.allclose que los tres dan el mismo resultado antes de
echo registrar los tiempos.
echo.
echo Genera: evidencias\resultados_a.csv, tiempo_vs_tamano.png, speedup_vs_p.png
echo.
%PY% "experimento-a\src\experimento_a.py"
goto volver

REM ===========================================================================
:expB
cls
echo === EXPERIMENTO B - Paralelismo a nivel de tareas ===
echo.
echo 24 lotes de feature engineering, en 3 tamanos de lote y 2 tipos de carga
echo (CPU-bound e I/O-bound). Compara secuencial, ThreadPoolExecutor y
echo ProcessPoolExecutor con 2, 4 y 8 workers.
echo.
echo Genera: evidencias\resultados_b.csv, comparacion_b.png
echo.
%PY% "experimento-b\src\experimento_b.py"
goto volver

REM ===========================================================================
:expC
cls
echo === EXPERIMENTO C - Procesamiento distribuido local con Dask ===
echo.
echo Genera 16 CSV particionados por fecha y los procesa con Dask en 4, 8 y 16
echo particiones, contra el equivalente en Pandas puro. Valida que el agregado
echo de Dask coincide con el de Pandas antes de registrar el tiempo.
echo.
echo AVISO: regenera ~36 MB en experimento-c\datos\. Esos datos no vienen en el
echo repositorio justamente porque este script los reconstruye.
echo.
echo Genera: evidencias\resultados_c.csv, comparacion_c.png
echo.
%PY% "experimento-c\src\experimento_c.py"
goto volver

REM ===========================================================================
:expD
cls
echo === EXPERIMENTO D - Simulacion local del cluster ===
echo.
echo Lanza dos worker.py como procesos locales (puertos 9101 y 9102), corre la
echo prueba de correctitud y una bateria reducida contra ellos, y los apaga.
echo Demuestra el protocolo coordinador-worker completo (framing JSON, timeouts,
echo particionamiento, deteccion de fallas) sin levantar las VMs.
echo.
echo IMPORTANTE: este modo SOBRESCRIBE resultados_d.csv y comparacion_d.png,
echo que son la medicion del cluster REAL y una figura del informe. Este
echo lanzador los respalda antes y los restaura despues. No se pierden.
echo.
if not defined DIRECTO pause

call :marcadetiempo
set "RESP=experimento-d\evidencias_respaldo_!TS!"
xcopy "experimento-d\evidencias" "!RESP!\" /E /I /Q /Y >nul
echo.
echo [1/4] Evidencia del cluster real respaldada en !RESP!\
echo.
echo [2/4] Corriendo la simulacion...
echo.
%PY% "experimento-d\src\coordinator.py" simulacion
echo.
if not exist "experimento-d\evidencias_simulacion" mkdir "experimento-d\evidencias_simulacion"
move /Y "experimento-d\evidencias\resultados_d.csv"  "experimento-d\evidencias_simulacion\" >nul 2>&1
move /Y "experimento-d\evidencias\comparacion_d.png" "experimento-d\evidencias_simulacion\" >nul 2>&1
echo [3/4] Salida de la simulacion guardada en experimento-d\evidencias_simulacion\
copy /Y "!RESP!\resultados_d.csv"  "experimento-d\evidencias\" >nul 2>&1
copy /Y "!RESP!\comparacion_d.png" "experimento-d\evidencias\" >nul 2>&1
echo [4/4] Evidencia del cluster real restaurada en experimento-d\evidencias\
echo.
echo Listo. La evidencia entregable quedo intacta.
goto volver

REM ===========================================================================
:expDreal
cls
echo === EXPERIMENTO D - Sobre el cluster QEMU real ===
echo.
echo Este menu NO lo ejecuta: necesita las 3 VMs Alpine levantadas y buena
echo parte del procedimiento es manual (sesiones SSH abiertas en paralelo).
echo.
echo Procedimiento:
echo.
echo   1. Arrancar las 3 VMs, cada una en su ventana:
echo        powershell -File experimento-d\scripts\arrancar_nodos.ps1
echo.
echo   2. Copiar el worker a los dos nodos trabajadores:
echo        scp -P 2221 experimento-d\src\worker.py alumno@127.0.0.1:/home/alumno/
echo        scp -P 2222 experimento-d\src\worker.py alumno@127.0.0.1:/home/alumno/
echo.
echo   3. Dentro de nodo1 y nodo2 (SSH a los puertos 2221 y 2222):
echo        python3 worker.py 9000 nodo1
echo        python3 worker.py 9000 nodo2
echo.
echo   4. En coordinator.py verificar: WORKERS = WORKERS_CLUSTER_REAL
echo.
echo   5. Desde nodo0 (SSH al puerto 2220):
echo        python3 src/coordinator.py prueba
echo        python3 src/coordinator.py bateria 10000,100000,500000,2000000,10000000 3
echo.
echo   Detalle completo en experimento-d\README.md y en
echo   experimento-d\scripts\instalar_nodo.md
echo.
echo ---------------------------------------------------------------------------
if exist "experimento-d\scripts\nodo0.qcow2" (
    echo Los discos de las VMs estan presentes en este equipo.
) else (
    echo OJO: los discos nodo0/1/2.qcow2 NO estan en este equipo. La corrida
    echo entregada ya fue hecha y sus 7 evidencias estan en
    echo experimento-d\evidencias\. Para rehacer el cluster desde cero hay que
    echo reinstalar las VMs siguiendo scripts\instalar_nodo.md.
)
goto volver

REM ===========================================================================
:informe
cls
echo === Compilacion del informe ===
echo.
where pdflatex >nul 2>&1
if errorlevel 1 (
    echo ERROR: no se encontro pdflatex en el PATH. Hace falta MiKTeX o TeX Live.
    goto volver
)
echo Primera pasada...
pdflatex -interaction=nonstopmode informe_guia2.tex >nul
echo Segunda pasada (para el indice)...
pdflatex -interaction=nonstopmode informe_guia2.tex >nul
echo.
if exist informe_guia2.pdf (
    echo Listo: informe_guia2.pdf
) else (
    echo Fallo la compilacion. Revisar informe_guia2.log
)
goto volver

REM ===========================================================================
:abrir
cls
echo Abriendo el informe y las carpetas de evidencias...
if exist informe_guia2.pdf start "" "informe_guia2.pdf"
for %%E in (a b c d) do (
    if exist "experimento-%%E\evidencias" start "" "experimento-%%E\evidencias"
)
goto volver

REM ===========================================================================
:todo
cls
echo === Corrida completa A + B + C ===
echo.
echo Unos 90 segundos en total. El experimento D va aparte (opcion 6).
echo.
if not defined DIRECTO pause
if not defined DIRECTO cls
echo --- Experimento A ---
%PY% "experimento-a\src\experimento_a.py"
echo.
echo --- Experimento B ---
%PY% "experimento-b\src\experimento_b.py"
echo.
echo --- Experimento C ---
%PY% "experimento-c\src\experimento_c.py"
echo.
echo === Los tres experimentos terminaron ===
goto volver

REM ===========================================================================
:marcadetiempo
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
exit /b

:volver
echo.
echo ---------------------------------------------------------------------------
if defined DIRECTO goto fin
pause
goto menu

:fin
popd
endlocal
exit /b 0
