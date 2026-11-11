# Experimento C - Procesamiento distribuido local sobre datos particionados

Genera 16 archivos CSV sinteticos de ventas (uno por fecha, ~60.000 filas
cada uno) en `datos/`, los lee con `dask.dataframe` bajo 3 configuraciones de
particionamiento (4, 8 y 16 particiones), aplica una transformacion
(monto por unidad) y una agregacion `groupby(fecha, tienda)`, y compara
tiempo y resultado contra el equivalente en Pandas puro (concatenando todos
los CSV en memoria).

## Ejecucion

```powershell
cd experimento-c
python src/experimento_c.py
```

Requiere Dask instalado (`pip install "dask[dataframe]"`, incluido en
`requirements.txt` de la raiz de `guia-2/`). Si Dask no esta disponible, el
script termina con un mensaje explicito indicando como instalarlo, sin
fallar con un traceback críptico.

No requiere entrada manual. Corre en pocos segundos (los datos son
sinteticos y moderados en tamano para que el experimento sea reproducible
rapidamente; el objetivo es observar el costo de coordinacion del
particionamiento, no procesar un dataset masivo).

## Que genera

- `datos/ventas_AAAAMMDD.csv` x 16: los datos particionados por fecha.
- `evidencias/resultados_c.csv`: tiempo de Pandas puro y de Dask para cada
  configuracion de particionamiento.
- `evidencias/comparacion_c.png`: grafico de barras comparando los tiempos.

El script valida que el resultado agregado de Dask coincide con el de
Pandas (montos con `np.allclose`, unidades exactas) para cada configuracion
de particionamiento antes de registrar el tiempo.

## Notas

Dask en modo local (scheduler por hilos sobre un solo computador) no implica
varios nodos fisicos. Se usa aqui para observar el overhead del
particionamiento y la coordinacion del grafo de tareas de Dask frente a un
calculo equivalente sin particionar; el clúster distribuido real (varias
maquinas, red, comunicacion explicita) se implementa por separado en el
experimento D con QEMU.

## Observaciones (completar tras revisar las evidencias generadas)

- Configuracion de particionamiento mas eficiente observada y por que:
  _(completar)_
- Punto en el que el costo de coordinacion de Dask supera el beneficio del
  particionamiento (demasiadas particiones pequenas): _(completar)_
