# Experimento D - Clúster distribuido virtual (QEMU + Alpine)

Implementa un modelo coordinador-worker sobre 3 VMs Alpine Linux en QEMU
(nodo0 = coordinador, nodo1 y nodo2 = workers) que calculan, de forma
distribuida, el conteo de numeros primos en un intervalo configurable, y
compara el rendimiento frente a la ejecucion secuencial.

El codigo (`src/coordinator.py`, `src/worker.py`) esta implementado y
verificado de dos formas: en simulacion local, sin VMs (ver "Verificacion sin
VMs" mas abajo), y sobre el clúster real de 3 VMs, que es de donde salen los
datos entregados (ver "Evidencias capturadas en el clúster real").

## Fase 1 - Preparacion de las VMs

Seguir el checklist completo en [`scripts/instalar_nodo.md`](scripts/instalar_nodo.md)
para instalar Alpine Linux en `nodo0.qcow2`, `nodo1.qcow2` y `nodo2.qcow2`
(1 vCPU, 256 MB RAM cada una; se puede subir a 512 MB si el equipo lo permite).

Para arrancar las 3 VMs ya instaladas (arranque posterior, sin ISO), usar
[`scripts/arrancar_nodos.ps1`](scripts/arrancar_nodos.ps1), que lanza cada VM
en su propia ventana de PowerShell con el reenvio de puertos correcto:

| Nodo | Puerto host | Puerto VM | Servicio |
| --- | --- | --- | --- |
| nodo0 | 2220 | 22 | SSH coordinador |
| nodo1 | 2221 | 22 | SSH worker 1 |
| nodo2 | 2222 | 22 | SSH worker 2 |
| nodo1 | 9001 | 9000 | TCP worker 1 |
| nodo2 | 9002 | 9000 | TCP worker 2 |

## Fase 2 - Comunicacion

Verificar acceso SSH a los 3 nodos desde el anfitrion:

```powershell
ssh -p 2220 alumno@127.0.0.1   # nodo0
ssh -p 2221 alumno@127.0.0.1   # nodo1
ssh -p 2222 alumno@127.0.0.1   # nodo2
```

Transferir el worker a cada nodo trabajador:

```powershell
scp -P 2221 src\worker.py alumno@127.0.0.1:/home/alumno/
scp -P 2222 src\worker.py alumno@127.0.0.1:/home/alumno/
```

Levantar el servicio worker en cada nodo (dentro de la sesion SSH de cada
uno), escuchando en todas las interfaces (no solo loopback) para que el
reenvio de puertos de QEMU pueda alcanzarlo:

```sh
python3 worker.py 9000 nodo1   # dentro de nodo1
python3 worker.py 9000 nodo2   # dentro de nodo2
```

Verificar desde Windows que los puertos reenviados responden:

```powershell
Test-NetConnection 127.0.0.1 -Port 9001
Test-NetConnection 127.0.0.1 -Port 9002
```

Y, de forma mas directa, desde una sesion de Python dentro de nodo0 (el
coordinador ve a los workers a traves de la puerta de enlace NAT de QEMU,
`10.0.2.2`, no de `127.0.0.1`):

```python
import socket
for port in (9001, 9002):
    with socket.create_connection(("10.0.2.2", port), timeout=3):
        print("TCP disponible:", port)
```

## Fase 3 - Calculo distribuido

Protocolo (implementado en `src/worker.py` y `src/coordinator.py`):

- Una conexion TCP por solicitud, mensajes JSON UTF-8 terminados en `\n`.
- Solicitud: `{"start": <int>, "end": <int>}` (limites inclusivos).
- Respuesta: `{"worker": "<id>", "result": <int>, "processing_seconds": <float>}`,
  o `{"error": "<descripcion>"}` si la solicitud es invalida.
- El coordinador lee hasta el delimitador sin asumir que una sola lectura
  trae el mensaje completo, limita el tamano maximo del mensaje, y aplica
  timeout a toda la operacion (`TIMEOUT_SEGUNDOS` en `coordinator.py`).
- El coordinador valida tipos, rangos, y que el campo `worker` corresponda
  al esperado cuando se especifica; ante cualquier falla, el escenario queda
  marcado explicitamente como incompleto (`completo: False`), nunca se
  presenta un resultado parcial como si fuera el total.

Para el intervalo de referencia 2-500.000, el particionamiento estatico entre
2 workers queda 2-250.000 (nodo1) y 250.001-500.000 (nodo2), calculado por la
funcion `particionar()` de `coordinator.py` (sin huecos ni solapamientos para
cualquier intervalo, no solo para este caso).

Para apuntar el coordinador al clúster real, editar en
`src/coordinator.py` la asignacion:

```python
WORKERS = WORKERS_CLUSTER_REAL  # en vez de WORKERS_SIMULACION_LOCAL
```

donde `WORKERS_CLUSTER_REAL = [("10.0.2.2", 9001), ("10.0.2.2", 9002)]`.

## Fase 4 - Comparacion experimental (3 escenarios x >=3 tamanos x >=3 repeticiones)

Ejecutar, con las 2 VMs worker ya corriendo el servicio:

```powershell
cd experimento-d
python src/coordinator.py bateria
```

Esto corre automaticamente los 3 escenarios (A secuencial, B un worker
remoto, C dos workers remotos) para los tamanos 2-10.000, 2-100.000 y
2-500.000, con 3 repeticiones cada combinacion, y escribe
`evidencias/resultados_d.csv` (tiempo total, tiempos de procesamiento por
worker, residual de overhead, speedup y eficiencia respecto de A) mas
`evidencias/comparacion_d.png`.

Antes de correr la bateria contra las VMs reales, correr la prueba de
correctitud:

```powershell
python src/coordinator.py prueba
```

## Fase 5 - Correctitud

La prueba de correctitud verifica que contar primos en [2, 10] da exactamente
4, tanto localmente como via cada escenario remoto. La bateria completa
ademas compara, para cada tamano, que los 3 escenarios que si completaron
produjeron el mismo resultado (`_resultado_consistente` en `coordinator.py`),
e imprime una advertencia si no coincidieran.

## Fase 6 - Overhead

El CSV de la bateria incluye la columna `residual_s`, calculada como:

```
residual = T_total_distribuido - max_i(T_procesamiento_del_worker_i)
```

Este residual agrupa preparacion, planificacion, envio/recepcion por red y
agregacion; no es una medicion aislada de latencia de red pura (ver seccion
2.9/Fase 6 del enunciado). Analizar como crece (o no) con el tamano del
intervalo y con el numero de workers usando los datos reales capturados.

## Fase 7 - Prueba de falla

Con el coordinador y ambos workers corriendo, confirmar primero una
ejecucion correcta (Fase 4/5). Luego, detener el servicio de uno de los
workers (`Ctrl+C` en su sesion SSH, o detener el proceso `worker.py`) y
volver a correr:

```powershell
python src/coordinator.py bateria
```

Registrar: el coordinador no debe bloquearse indefinidamente (esta acotado
por `TIMEOUT_SEGUNDOS`), debe detectar la falla (connection refused o
timeout), y debe marcar el escenario afectado como incompleto, nunca como
exitoso con un resultado parcial. El codigo de `solicitar_a_worker()` ya
contempla ambos casos (ver `src/coordinator.py`).

Mejoras de disponibilidad que **no** se implementan (son extensiones
opcionales segun el enunciado, solo se mencionan en la discusion del
informe): reintentos automaticos, reinicio del worker caido, reasignacion
dinamica de la particion del worker caido hacia el worker sobreviviente.

## Verificacion sin VMs (hecha por el implementador antes de entregar)

```powershell
python src/coordinator.py simulacion
```

Este modo lanza 2 `worker.py` como subprocesos en localhost (puertos 9101 y
9102), corre la prueba de correctitud y una bateria reducida contra ellos, y
los detiene al final. Sirve para validar el protocolo (framing JSON,
timeouts, validacion de respuestas, particionamiento sin huecos) sin
depender de las VMs. Resultado de esta verificacion: prueba de correctitud
OK en los 3 escenarios, resultados consistentes entre escenarios para los 3
tamanos probados, y el escenario de falla (un worker caido) detectado
correctamente sin bloqueo. Es un atajo para probar cambios en el protocolo sin
levantar el clúster; las mediciones entregadas son las del clúster real.

## Evidencias capturadas en el clúster real

Las 7 evidencias que pide la guia estan en `evidencias/`, tomadas el 8 de
noviembre de 2026 sobre el clúster descrito arriba (QEMU 11.1.0 con acelerador
`whpx`, Alpine Linux 3.24, kernel 6.18.62-0-virt, Python 3.14.10 en cada nodo):

| # | Evidencia | Archivo |
|---|---|---|
| 1 | Las 3 VMs corriendo a la vez, con el hostname visible en cada consola | `evidencias/01_tres_vms_simultaneas.png` |
| 2 | Acceso SSH a los 3 nodos | `evidencias/02_ssh_tres_nodos.txt` |
| 3 | Ambos workers escuchando y alcanzables desde el anfitrion y desde nodo0 | `evidencias/03_workers_disponibles.txt` |
| 4 y 5 | Particion asignada a cada worker, parciales de cada uno y total agregado | `evidencias/04_particion_y_parciales.txt` |
| 6 | Bateria completa y tabla comparativa de los 3 escenarios | `evidencias/05_bateria_cluster_real.txt`, `evidencias/06_tabla_comparativa.md`, `evidencias/resultados_d.csv`, `evidencias/comparacion_d.png` |
| 7 | Falla de un worker: deteccion y escenario marcado incompleto | `evidencias/07_falla_de_un_worker.txt` |

La captura de las consolas no se hizo fotografiando ventanas del escritorio:
`scripts/capturar_consolas.py` le pide a cada VM su propio framebuffer por QMP
(`screendump`) y une las tres imagenes. Sale siempre completa, sin ventanas
ajenas encima y sin depender de que nadie toque el mouse mientras corre.

Las tres instalaciones de Alpine fueron desatendidas, no a mano: ver
`scripts/instalar_nodo.md`.

### Lo que mostraron los datos

Con la criba de Eratostenes implementada sobre `bytearray`, el computo es tan
rapido que durante tres de los cinco tamanos el reparto **pierde** contra la
ejecucion secuencial: el costo fijo de coordinacion (abrir la conexion,
serializar, esperar, agregar) es de unos 2 a 5 ms y no baja aunque el intervalo
crezca. Recien en 2..10.000.000 el computo pesa lo suficiente como para que
distribuir gane: speedup 1,08 con un worker y 1,20 con dos. El detalle esta en
`evidencias/06_tabla_comparativa.md` y se discute en el informe.

## Discusion (Fase 8, responder en el informe con evidencia real)

1. ¿En que difieren la ejecucion secuencial y la distribuida entre nodos?
2. ¿Que funcion cumple el coordinador y como se distribuyen las tareas?
3. ¿Por que se necesitan mecanismos de comunicacion y que costos adicionales aparecen?
4. ¿Dos workers siempre mejoran el rendimiento? ¿Como influye el tamano del problema?
5. ¿Que ocurre si un worker deja de responder?
6. ¿Que limitaciones tienen las VM sobre un mismo computador fisico?
7. ¿Que ventajas y desafios existirian con varios computadores fisicos conectados por red?

Estas preguntas estan respondidas en `informe_guia2.tex`, seccion de discusion,
con los numeros reales de la bateria sobre el clúster (en particular la 4 y la
5, que dependian de medir y de provocar la falla).
