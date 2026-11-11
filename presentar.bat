@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"
title Guia 2 - INFB6074 - Presentacion

REM ---------------------------------------------------------------------------
REM Guion de presentacion de la Guia 2, pensado para grabar el video.
REM
REM Siete escenas en orden. Cada una limpia la pantalla, anuncia de que se trata,
REM corre lo que tenga que correr y cierra con la conclusion calculada desde las
REM evidencias. Entre escena y escena se detiene, para poder cortar la grabacion.
REM
REM     presentar.bat        -> menu
REM     presentar.bat g      -> guiado: las 7 escenas en orden
REM     presentar.bat 4      -> solo la escena 4, para regrabarla
REM     presentar.bat p      -> comprobacion previa (ANTES de grabar)
REM
REM Usa "python" y no "py": en este equipo "py" resuelve a 3.12, que no tiene
REM las dependencias; "python" resuelve a 3.9.13, que si las tiene.
REM ---------------------------------------------------------------------------

set "PY=python"
set "GUIADO="
set "DIRECTO="
set "VACIAS=0"

if /i "%~1"=="g" (set "GUIADO=1" & goto escena1)
if not "%~1"=="" (set "DIRECTO=1" & set "ESCENA=%~1" & goto despacho)

:menu
cls
echo ===========================================================================
echo   GUIA 2 - Paralelismo local y procesamiento distribuido
echo   INFB6074 Infraestructura para Ciencia de Datos - UTEM 2026-2
echo.
echo   GUION DE PRESENTACION
echo ===========================================================================
echo.
echo     G.  Grabar todo seguido: las 7 escenas en orden   (~4 min)
echo.
echo     1.  Portada y la tesis del trabajo                 (sin ejecutar)
echo     2.  Experimento A - vectorizar vs repartir             (~40 s)
echo     3.  Experimento B - el GIL, hilos vs procesos          (~30 s)
echo     4.  Experimento C - particionar con Dask               (~20 s)
echo     5.  Experimento D - el cluster real, evidencias    (sin ejecutar)
echo     6.  Experimento D - el protocolo corriendo             (~15 s)
echo     7.  Cierre - las cuatro conclusiones               (sin ejecutar)
echo.
echo     P.  Comprobacion previa (correr ANTES de grabar)
echo     0.  Salir
echo.
set "ESCENA="
set /p "ESCENA=Escena: "
if "%ESCENA%"=="" (
    set /a VACIAS+=1
    if !VACIAS! GEQ 3 goto fin
    goto menu
)
set "VACIAS=0"

:despacho
if /i "%ESCENA%"=="g" (set "GUIADO=1" & set "DIRECTO=" & goto escena1)
if /i "%ESCENA%"=="p" goto previa
if "%ESCENA%"=="1" goto escena1
if "%ESCENA%"=="2" goto escena2
if "%ESCENA%"=="3" goto escena3
if "%ESCENA%"=="4" goto escena4
if "%ESCENA%"=="5" goto escena5
if "%ESCENA%"=="6" goto escena6
if "%ESCENA%"=="7" goto escena7
if "%ESCENA%"=="0" goto fin
if defined DIRECTO (
    echo Escena "%ESCENA%" no valida. Usa 1 a 7, G o P.
    popd & endlocal & exit /b 2
)
goto menu

REM ===========================================================================
REM  COMPROBACION PREVIA - no es una escena, es para antes de apretar grabar
REM ===========================================================================
:previa
cls
echo === COMPROBACION PREVIA (antes de grabar) ===
echo.
%PY% --version
if errorlevel 1 (
    echo ERROR: no se encontro "python" en el PATH. No grabes todavia.
    goto corte
)
echo.
for %%M in (numpy pandas matplotlib dask psutil) do (
    %PY% -c "import %%M" >nul 2>&1
    if errorlevel 1 (echo    FALTA  %%M) else (echo    OK     %%M)
)
echo.
set "LISTO=1"
for %%P in (experimento-a\evidencias\resultados_a.csv experimento-b\evidencias\resultados_b.csv experimento-c\evidencias\resultados_c.csv experimento-d\evidencias\resultados_d.csv experimento-d\evidencias\01_tres_vms_simultaneas.png) do (
    if exist "%%P" (echo    OK     %%P) else (echo    FALTA  %%P & set "LISTO=")
)
echo.
if defined LISTO (
    echo Todo en su lugar. Puedes grabar.
) else (
    echo Falta evidencia. Revisa antes de grabar.
)
echo.
echo Consejo de encuadre: deja esta ventana en pantalla completa y sube un poco
echo el tamano de fuente de la consola. Las tablas estan pensadas para 74
echo columnas, no se van a cortar.
goto corte

REM ===========================================================================
:escena1
set "ACTUAL=1"
cls
echo.
echo   ===================================================================
echo.
echo      GUIA 2 - PARALELISMO LOCAL Y PROCESAMIENTO DISTRIBUIDO
echo.
echo      INFB6074 - Infraestructura para Ciencia de Datos
echo      Universidad Tecnologica Metropolitana - 2026-2
echo.
echo   ===================================================================
echo.
echo.
echo      La pregunta del trabajo no es "como paralelizo", sino
echo      CUANDO CONVIENE PARALELIZAR.
echo.
echo      Cuatro experimentos, cada uno en un nivel distinto:
echo.
echo         A   Vectorizacion         un arreglo, un proceso
echo         B   Tareas                hilos y procesos en un computador
echo         C   Particionamiento      Dask sobre datos divididos
echo         D   Distribucion real     3 maquinas virtuales por red
echo.
echo      En tres de los cuatro, el resultado contradice la intuicion.
echo      Eso es lo que vamos a ver.
echo.
goto corte

REM ===========================================================================
:escena2
set "ACTUAL=2"
cls
echo ===========================================================================
echo   ESCENA 2 de 7 - EXPERIMENTO A - Vectorizar o repartir
echo ===========================================================================
echo.
echo   La misma transformacion numerica por tres caminos:
echo      - Python puro, elemento por elemento
echo      - NumPy vectorizado
echo      - multiprocessing, partiendo el arreglo en trozos
echo.
echo   Sobre cinco tamanos, de diez mil a veinte millones de elementos.
echo   Antes de medir, verifica con np.allclose que los tres dan el mismo
echo   resultado: si no coincidieran, el experimento se detiene.
echo.
echo   Corriendo (unos 40 segundos)...
echo.
%PY% "experimento-a\src\experimento_a.py"
%PY% "presentacion\resumen_escena.py" a
goto corte

REM ===========================================================================
:escena3
set "ACTUAL=3"
cls
echo ===========================================================================
echo   ESCENA 3 de 7 - EXPERIMENTO B - El GIL, con y contra
echo ===========================================================================
echo.
echo   Veinticuatro lotes de feature engineering, repartidos de tres formas:
echo   secuencial, con ThreadPoolExecutor y con ProcessPoolExecutor, usando
echo   2, 4 y 8 workers.
echo.
echo   Y lo importante: con DOS tipos de carga distintos. Una puramente de
echo   calculo, y otra que ademas espera, como esperaria un disco o una red.
echo   Los mismos hilos se comportan al reves en cada una.
echo.
echo   Corriendo (unos 30 segundos)...
echo.
%PY% "experimento-b\src\experimento_b.py"
%PY% "presentacion\resumen_escena.py" b
goto corte

REM ===========================================================================
:escena4
set "ACTUAL=4"
cls
echo ===========================================================================
echo   ESCENA 4 de 7 - EXPERIMENTO C - Cuanto particionar
echo ===========================================================================
echo.
echo   Dieciseis archivos CSV particionados por fecha, procesados con Dask en
echo   4, 8 y 16 particiones, contra el mismo calculo en Pandas puro.
echo.
echo   La pregunta no es si particionar sirve, sino hasta donde. Cada
echo   configuracion se valida contra el resultado de Pandas antes de aceptar
echo   su tiempo: si el agregado no coincidiera, no se registra.
echo.
echo   Corriendo (unos 20 segundos; regenera sus propios datos)...
echo.
%PY% "experimento-c\src\experimento_c.py"
%PY% "presentacion\resumen_escena.py" c
goto corte

REM ===========================================================================
:escena5
set "ACTUAL=5"
cls
echo ===========================================================================
echo   ESCENA 5 de 7 - EXPERIMENTO D - El cluster de verdad
echo ===========================================================================
echo.
echo   Tres maquinas virtuales Alpine Linux sobre QEMU: nodo0 coordina, nodo1
echo   y nodo2 trabajan. Se comunican por TCP con mensajes JSON. Cuentan
echo   numeros primos repartiendose el intervalo.
echo.
echo   Esto no se puede mostrar corriendo ahora -son tres VMs y varias
echo   sesiones SSH a la vez-, asi que vamos a las evidencias capturadas el 7
echo   y 8 de noviembre.
echo.
echo   ---------------------------------------------------------------------
echo   Evidencia 1: las tres VMs encendidas al mismo tiempo
echo   ---------------------------------------------------------------------
echo   (se abre la imagen; las consolas se pidieron a QEMU por QMP, no son
echo    fotos de ventanas del escritorio)
echo.
if exist "experimento-d\evidencias\01_tres_vms_simultaneas.png" (
    start "" "experimento-d\evidencias\01_tres_vms_simultaneas.png"
)
if not defined DIRECTO pause
cls
echo   ---------------------------------------------------------------------
echo   Evidencias 4 y 5: el reparto y los resultados parciales
echo   ---------------------------------------------------------------------
echo.
type "experimento-d\evidencias\04_particion_y_parciales.txt"
echo.
if not defined DIRECTO pause
cls
echo   ---------------------------------------------------------------------
echo   Evidencia 7: que pasa cuando un worker se cae
echo   ---------------------------------------------------------------------
echo.
type "experimento-d\evidencias\07_falla_de_un_worker.txt"
echo.
%PY% "presentacion\resumen_escena.py" d
goto corte

REM ===========================================================================
:escena6
set "ACTUAL=6"
cls
echo ===========================================================================
echo   ESCENA 6 de 7 - EXPERIMENTO D - El protocolo, en vivo
echo ===========================================================================
echo.
echo   Las VMs no estan encendidas, pero el protocolo es el mismo. Este modo
echo   levanta dos workers como procesos locales y corre contra ellos todo lo
echo   que corrio contra el cluster: la prueba de correctitud, el reparto sin
echo   huecos, los timeouts y la agregacion.
echo.
echo   Lo unico que cambia es por donde viajan los mensajes.
echo.
if not defined DIRECTO pause

REM --- Proteccion: la bateria sobrescribe la evidencia del cluster real ---
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
set "RESP=experimento-d\evidencias_respaldo_!TS!"
xcopy "experimento-d\evidencias" "!RESP!\" /E /I /Q /Y >nul

cls
echo   Corriendo la simulacion...
echo.
%PY% "experimento-d\src\coordinator.py" simulacion

if not exist "experimento-d\evidencias_simulacion" mkdir "experimento-d\evidencias_simulacion"
move /Y "experimento-d\evidencias\resultados_d.csv"  "experimento-d\evidencias_simulacion\" >nul 2>&1
move /Y "experimento-d\evidencias\comparacion_d.png" "experimento-d\evidencias_simulacion\" >nul 2>&1
copy /Y "!RESP!\resultados_d.csv"  "experimento-d\evidencias\" >nul 2>&1
copy /Y "!RESP!\comparacion_d.png" "experimento-d\evidencias\" >nul 2>&1
rmdir /S /Q "!RESP!" >nul 2>&1

echo.
echo   (La salida de esta simulacion quedo en evidencias_simulacion\. La
echo    medicion del cluster real quedo intacta: este modo la sobrescribe,
echo    asi que el guion la respalda y la restaura.)
goto corte

REM ===========================================================================
:escena7
set "ACTUAL=7"
cls
%PY% "presentacion\resumen_escena.py" cierre
echo.
echo   El informe completo, con las 23 secciones, el marco teorico y la
echo   discusion de las siete preguntas de la guia, esta en informe_guia2.pdf
echo.
echo   Codigo y evidencias: github.com/k0ngan/guia2_infra
echo.
goto corte

REM ===========================================================================
:corte
echo.
if defined GUIADO (
    echo ---------------------------------------------------------------------------
    echo   Fin de la escena. Corta la grabacion si quieres, y pulsa una tecla.
    echo ---------------------------------------------------------------------------
    pause >nul
    set /a SIG=!ACTUAL!+1
    if !SIG! GTR 7 goto fin
    set "ESCENA=!SIG!"
    goto despacho
)
if defined DIRECTO goto fin
echo ---------------------------------------------------------------------------
pause
goto menu

:fin
popd
endlocal
exit /b 0
