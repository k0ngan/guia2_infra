# Guía 2: Paralelismo Local y Procesamiento Distribuido en Data Science

Asignatura: INFB6074 · Infraestructura para Ciencia de Datos (UTEM, 2026-2).

Trabajo individual o en parejas, duracion 2 semanas.

## Estado

| Experimento | Estado | Contenido |
| --- | --- | --- |
| [Investigacion teorica](investigacion/README.md) | Redactada | Secuencial/paralelo/distribuido, clústeres, QEMU, redes virtuales, SSH, sockets/JSON, particionamiento, metricas, escalabilidad, disponibilidad |
| [Experimento A](experimento-a/README.md) | Implementado y ejecutado | Vectorizacion NumPy vs Python puro vs multiprocessing, 5 tamanos |
| [Experimento B](experimento-b/README.md) | Implementado y ejecutado | Secuencial vs ThreadPoolExecutor vs ProcessPoolExecutor, CPU-bound e I/O-bound |
| [Experimento C](experimento-c/README.md) | Implementado y ejecutado | Dask local vs Pandas sobre datos particionados por fecha |
| [Experimento D](experimento-d/README.md) | Implementado y ejecutado sobre el clúster real | Coordinador-worker TCP/JSON sobre clúster virtual QEMU (3 nodos Alpine) |

El experimento D se midio sobre el clúster de 3 VMs los dias 7 y 8 de
noviembre de 2026 (QEMU 11.1.0 con acelerador `whpx`, Alpine Linux 3.24,
kernel 6.18.62-0-virt, Python 3.14.10 en cada nodo). Las 7 evidencias que
pide la guia estan en `experimento-d/evidencias/`.

El informe (`informe_guia2.tex`) esta completo y compilado: 23 secciones, 12
paginas, las 5 figuras incluidas y ningun marcador pendiente. El PDF
entregable es `informe_guia2.pdf`.

## Herramientas usadas

- Python 3.9, NumPy, Pandas, Matplotlib, Dask (`dask[dataframe]`), psutil
  (opcional, para metricas de CPU en el Experimento B).
- `multiprocessing`, `concurrent.futures`, `socket`/`socketserver`, `json` de
  la biblioteca estandar (Experimentos A, B y D).
- QEMU + Alpine Linux para el clúster virtual del Experimento D.
- No se dispone de GPU en el equipo de desarrollo; los experimentos A-C
  comparan exclusivamente vectorizacion (NumPy), multicore local
  (`multiprocessing`/`concurrent.futures`) y distribucion local (Dask), sin
  aceleracion por GPU, segun lo permitido por el enunciado cuando no hay GPU
  disponible.
- Entorno de ejecucion y verificacion: Windows 11, AMD Ryzen (16 nucleos
  logicos), ver detalle impreso por cada script al correr (`platform` /
  `os.cpu_count()`).

## Como ejecutarlo

En Windows, el camino corto es el lanzador `ejecutar.bat`, que corre cada
parte por separado y se detiene para que la salida se pueda leer:

```powershell
.\ejecutar.bat        # menu interactivo
.\ejecutar.bat 3      # corre directo la opcion 3 y termina
```

El menu verifica el entorno, respalda las evidencias, corre los experimentos
A, B, C y D por separado, compila el informe y abre los resultados.

A mano, sin el lanzador, primero las dependencias:

```powershell
pip install -r requirements.txt
```

y despues cada experimento, que se ejecuta solo y sin entrada manual (los
scripts resuelven sus rutas respecto de su propia ubicacion, asi que da lo
mismo desde que carpeta se invoquen):

```powershell
python experimento-a/src/experimento_a.py     # ~40 s
python experimento-b/src/experimento_b.py     # ~30 s
python experimento-c/src/experimento_c.py     # ~20 s
python experimento-d/src/coordinator.py simulacion
```

### Dos advertencias que conviene leer antes

**El experimento C regenera sus datos.** Los 16 CSV particionados de
`experimento-c/datos/` pesan unos 36 MB y no se versionan: el propio
`experimento_c.py` los reconstruye al arrancar. Si la carpeta esta vacia, no
falta nada.

**Correr el experimento D sobrescribe la evidencia del clúster real.** Tanto
`coordinator.py simulacion` como `coordinator.py bateria` reescriben
`experimento-d/evidencias/resultados_d.csv` y `comparacion_d.png`, que son la
medicion sobre las VMs y una de las figuras del informe. La opcion 6 de
`ejecutar.bat` respalda ambos antes de correr, deja la salida de la
simulacion en `evidencias_simulacion/` y restaura los originales al terminar.
Si se corre el coordinador a mano, hay que respaldarlos primero.

## Reproducir el clúster del experimento D desde cero

El clúster ya fue montado y medido; estos pasos son para rehacerlo en otro
equipo, no para completar algo pendiente.

1. **Instalar las 3 VMs Alpine en QEMU** siguiendo
   [`experimento-d/scripts/instalar_nodo.md`](experimento-d/scripts/instalar_nodo.md).
   Las tres instalaciones son desatendidas, por answer file.
2. **Arrancar las 3 VMs simultaneamente** con
   [`experimento-d/scripts/arrancar_nodos.ps1`](experimento-d/scripts/arrancar_nodos.ps1)
   y transferir `worker.py` a nodo1 y nodo2 por SCP.
3. **Levantar el servicio worker** en nodo1 y nodo2
   (`python3 worker.py 9000 nodoN`), verificar que
   `WORKERS = WORKERS_CLUSTER_REAL` en `coordinator.py`, y correr desde nodo0
   `python3 src/coordinator.py prueba` y despues
   `python3 src/coordinator.py bateria`.
4. **Capturar las evidencias** con los scripts de
   `experimento-d/scripts/` (`capturar_consolas.py` pide a cada VM su propio
   framebuffer por QMP, sin fotografiar ventanas del escritorio).

El detalle completo, fase por fase, esta en
[`experimento-d/README.md`](experimento-d/README.md).

## Compilar el informe

```powershell
pdflatex -interaction=nonstopmode informe_guia2.tex   # dos veces, por el indice
```

Requiere una distribucion LaTeX (MiKTeX o TeX Live) con `inputenc`, `babel`,
`graphicx`, `hyperref` y `amsmath`. Verificado con MiKTeX 25.12: compila sin
errores y genera las 12 paginas con sus 5 figuras. Tambien esta como opcion 8
de `ejecutar.bat`.

## Declaracion de uso de IA

Se utilizo asistencia de IA (Claude, Anthropic) para estructurar el
andamiaje de archivos de la guia, redactar comentarios y documentacion, y
revisar la correctitud de la implementacion del protocolo coordinador-worker
y de los experimentos A-C. El diseño experimental, la validacion de
resultados (ejecucion real de los scripts y verificacion de equivalencia
numerica entre metodos) y las decisiones de arquitectura fueron revisados y
validados antes de la entrega, segun lo exigido por la seccion de integridad
academica del enunciado.
