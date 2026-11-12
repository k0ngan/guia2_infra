@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"
title Guia 2 - INFB6074 - Demostracion

REM ---------------------------------------------------------------------------
REM Demostracion de la Guia 2, en seis pasos.
REM
REM Cada paso limpia la pantalla, explica de que se trata, corre lo que tenga
REM que correr y cierra con su conclusion, calculada desde las evidencias del
REM momento. Al terminar vuelve al menu, asi se controla el ritmo: se muestra
REM un paso, se explica, y recien despues se elige el siguiente.
REM
REM     ejecutar.bat        -> menu
REM     ejecutar.bat 4      -> solo el paso 4
REM     ejecutar.bat p      -> prueba que todo este bien (antes de mostrar)
REM
REM Usa "python" y no "py": en este equipo "py" resuelve a 3.12, que no tiene
REM las dependencias; "python" resuelve a 3.9.13, que si las tiene.
REM ---------------------------------------------------------------------------

set "PY=python"
set "DIRECTO="
set "VACIAS=0"

if not "%~1"=="" (set "DIRECTO=1" & set "PASO=%~1" & goto despacho)

:menu
cls
echo ===========================================================================
echo   GUIA 2 - Paralelismo local y procesamiento distribuido
echo   INFB6074 Infraestructura para Ciencia de Datos - UTEM 2026-2
echo ===========================================================================
echo.
echo     1.  De que se trata el trabajo                     (sin ejecutar)
echo     2.  Experimento A - vectorizar vs repartir             (~40 s)
echo     3.  Experimento B - el GIL, hilos vs procesos          (~30 s)
echo     4.  Experimento C - particionar con Dask               (~20 s)
echo     5.  Experimento D - el cluster distribuido             (~15 s)
echo     6.  Conclusiones                                   (sin ejecutar)
echo.
echo     P.  Probar que todo este bien
echo     0.  Salir
echo.
set "PASO="
set /p "PASO=Paso: "
if "%PASO%"=="" (
    set /a VACIAS+=1
    if !VACIAS! GEQ 3 goto fin
    goto menu
)
set "VACIAS=0"

:despacho
if /i "%PASO%"=="p" goto prueba
if "%PASO%"=="1" goto paso1
if "%PASO%"=="2" goto paso2
if "%PASO%"=="3" goto paso3
if "%PASO%"=="4" goto paso4
if "%PASO%"=="5" goto paso5
if "%PASO%"=="6" goto paso6
if "%PASO%"=="0" goto fin
if defined DIRECTO (
    echo Paso "%PASO%" no valido. Usa 1 a 6, o P.
    popd & endlocal & exit /b 2
)
goto menu

REM ===========================================================================
REM  P - Prueba previa. Correr ANTES de mostrarle el trabajo a alguien.
REM ===========================================================================
:prueba
cls
echo === PRUEBA: esta todo bien? ===
echo.
%PY% --version
if errorlevel 1 (
    echo.
    echo ERROR: no se encontro "python" en el PATH.
    echo Sin eso no corre ningun experimento.
    goto corte
)
echo.
echo Dependencias:
set "FALLA="
for %%M in (numpy pandas matplotlib dask psutil) do (
    %PY% -c "import %%M" >nul 2>&1
    if errorlevel 1 (echo    FALTA  %%M & set "FALLA=1") else (echo    OK     %%M)
)
echo.
echo Evidencias que usan los pasos:
for %%P in (
    experimento-a\evidencias\resultados_a.csv
    experimento-b\evidencias\resultados_b.csv
    experimento-c\evidencias\resultados_c.csv
    experimento-d\evidencias\resultados_d.csv
    experimento-d\evidencias\01_tres_vms_simultaneas.png
    experimento-d\evidencias\04_particion_y_parciales.txt
    experimento-d\evidencias\07_falla_de_un_worker.txt
) do (
    if exist "%%P" (echo    OK     %%P) else (echo    FALTA  %%P & set "FALLA=1")
)
echo.
echo Informe:
if exist informe_guia2.pdf (echo    OK     informe_guia2.pdf) else (echo    FALTA  informe_guia2.pdf & set "FALLA=1")
echo.
echo ---------------------------------------------------------------------------
if defined FALLA (
    echo   HAY ALGO QUE FALTA. Revisalo antes de mostrar el trabajo.
    echo   Si faltan dependencias:  %PY% -m pip install -r requirements.txt
) else (
    echo   TODO EN ORDEN. Los seis pasos van a funcionar.
    echo.
    echo   Antes de mostrar: pon esta ventana en pantalla completa y sube un
    echo   poco la fuente de la consola. Las tablas estan armadas para 74
    echo   columnas, asi no se cortan ni quedan chicas.
)
echo ---------------------------------------------------------------------------
goto corte

REM ===========================================================================
:paso1
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
:paso2
cls
echo ===========================================================================
echo   PASO 2 de 6 - EXPERIMENTO A - Vectorizar o repartir
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
:paso3
cls
echo ===========================================================================
echo   PASO 3 de 6 - EXPERIMENTO B - El GIL, con y contra
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
:paso4
cls
echo ===========================================================================
echo   PASO 4 de 6 - EXPERIMENTO C - Cuanto particionar
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
:paso5
cls
echo ===========================================================================
echo   PASO 5 de 6 - EXPERIMENTO D - El cluster distribuido
echo ===========================================================================
echo.
echo   Tres maquinas virtuales Alpine Linux sobre QEMU: nodo0 coordina, nodo1
echo   y nodo2 trabajan. Se comunican por TCP con mensajes JSON, una conexion
echo   por solicitud. Cuentan numeros primos repartiendose el intervalo.
echo.
echo   Este paso tiene dos partes:
echo      1) Las evidencias del cluster real, capturado el 7 y 8 de noviembre.
echo      2) El protocolo corriendo aqui y ahora, con workers locales.
echo.
echo   ---------------------------------------------------------------------
echo   PARTE 1 - Las tres VMs encendidas a la vez
echo   ---------------------------------------------------------------------
echo   (se abre la imagen; las consolas se le pidieron a QEMU por QMP, no son
echo    fotos de ventanas del escritorio)
echo.
if exist "experimento-d\evidencias\01_tres_vms_simultaneas.png" (
    start "" "experimento-d\evidencias\01_tres_vms_simultaneas.png"
)
if not defined DIRECTO pause

cls
echo   ---------------------------------------------------------------------
echo   El reparto del intervalo y los resultados parciales
echo   ---------------------------------------------------------------------
echo.
type "experimento-d\evidencias\04_particion_y_parciales.txt"
echo.
if not defined DIRECTO pause

cls
echo   ---------------------------------------------------------------------
echo   Que pasa cuando un worker se cae
echo   ---------------------------------------------------------------------
echo.
type "experimento-d\evidencias\07_falla_de_un_worker.txt"
echo.
%PY% "presentacion\resumen_escena.py" d
if not defined DIRECTO pause

cls
echo   ---------------------------------------------------------------------
echo   PARTE 2 - El protocolo, corriendo ahora
echo   ---------------------------------------------------------------------
echo.
echo   Las VMs no estan encendidas, pero el protocolo es el mismo. Esto
echo   levanta dos workers como procesos locales y corre contra ellos todo lo
echo   que corrio contra el cluster: la prueba de correctitud, el reparto sin
echo   huecos, los timeouts y la agregacion.
echo.
echo   Lo unico que cambia es por donde viajan los mensajes.
echo.
if not defined DIRECTO pause

REM --- La bateria sobrescribe la evidencia del cluster real: respaldar ---
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
set "RESP=experimento-d\evidencias_respaldo_!TS!"
xcopy "experimento-d\evidencias" "!RESP!\" /E /I /Q /Y >nul

cls
echo   Corriendo la simulacion del protocolo...
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
echo    asi que el paso la respalda y la restaura.)
goto corte

REM ===========================================================================
:paso6
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
if defined DIRECTO goto fin
echo ---------------------------------------------------------------------------
pause
goto menu

:fin
popd
endlocal
exit /b 0
