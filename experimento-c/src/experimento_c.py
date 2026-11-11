"""
Experimento C - Procesamiento distribuido local sobre datos particionados (Dask).

Genera datos sinteticos de transacciones particionados en varios archivos CSV
(uno por fecha), los lee con dask.dataframe bajo distintas configuraciones de
particionamiento, aplica una transformacion y una agregacion (groupby), y
compara tiempo y resultado contra el equivalente en Pandas puro (leyendo y
concatenando todos los CSV en memoria).

Dask en modo local (scheduler por hilos/procesos sobre un solo computador) no
implica varios nodos fisicos: el objetivo aqui es observar el costo de
coordinacion de un grafo de tareas particionado, no un clustering real
(eso se aborda en el experimento D con un clúster virtual QEMU).

Salidas: evidencias/resultados_c.csv, evidencias/comparacion_c.png
"""

import csv
import os
import time

import numpy as np
import pandas as pd

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

try:
    import dask.dataframe as dd
except ImportError:
    raise SystemExit(
        "Dask no esta instalado. Instalar con: pip install \"dask[dataframe]\"\n"
        "o bien: pip install -r ../requirements.txt"
    )

BASE_DIR = os.path.dirname(__file__)
DATOS_DIR = os.path.join(BASE_DIR, "..", "datos")
EVIDENCIAS_DIR = os.path.join(BASE_DIR, "..", "evidencias")
os.makedirs(DATOS_DIR, exist_ok=True)
os.makedirs(EVIDENCIAS_DIR, exist_ok=True)

N_ARCHIVOS = 16
FILAS_POR_ARCHIVO = 60_000
CONFIGURACIONES_PARTICIONES = [4, 8, 16]
TIENDAS = ["norte", "sur", "centro", "oriente"]


def generar_datos():
    rng = np.random.default_rng(7)
    rutas = []
    fecha_base = pd.Timestamp("2026-01-01")
    for i in range(N_ARCHIVOS):
        fecha = fecha_base + pd.Timedelta(days=i)
        df = pd.DataFrame({
            "fecha": fecha.strftime("%Y-%m-%d"),
            "tienda": rng.choice(TIENDAS, FILAS_POR_ARCHIVO),
            "monto": rng.gamma(shape=2.0, scale=5000, size=FILAS_POR_ARCHIVO),
            "unidades": rng.integers(1, 10, FILAS_POR_ARCHIVO),
        })
        ruta = os.path.join(DATOS_DIR, f"ventas_{fecha.strftime('%Y%m%d')}.csv")
        df.to_csv(ruta, index=False)
        rutas.append(ruta)
    return rutas


def agregacion_pandas(rutas):
    partes = [pd.read_csv(r) for r in rutas]
    df = pd.concat(partes, ignore_index=True)
    df["monto_por_unidad"] = df["monto"] / df["unidades"]
    resultado = df.groupby(["fecha", "tienda"]).agg(
        total_monto=("monto", "sum"),
        total_unidades=("unidades", "sum"),
        promedio_monto_por_unidad=("monto_por_unidad", "mean"),
    ).reset_index()
    return resultado.sort_values(["fecha", "tienda"]).reset_index(drop=True)


def agregacion_dask(rutas, npartitions):
    ddf = dd.read_csv(rutas)
    ddf = ddf.repartition(npartitions=npartitions)
    ddf["monto_por_unidad"] = ddf["monto"] / ddf["unidades"]
    resultado = ddf.groupby(["fecha", "tienda"]).agg(
        total_monto=("monto", "sum"),
        total_unidades=("unidades", "sum"),
        promedio_monto_por_unidad=("monto_por_unidad", "mean"),
    ).compute().reset_index()
    return resultado.sort_values(["fecha", "tienda"]).reset_index(drop=True)


def main():
    print(f"Generando {N_ARCHIVOS} archivos de {FILAS_POR_ARCHIVO} filas en {DATOS_DIR} ...")
    rutas = generar_datos()

    filas_csv = []

    inicio = time.perf_counter()
    resultado_pandas = agregacion_pandas(rutas)
    tiempo_pandas = time.perf_counter() - inicio
    filas_csv.append({"configuracion": "pandas_puro", "npartitions": 1, "tiempo_s": tiempo_pandas,
                       "n_filas_resultado": len(resultado_pandas)})
    print(f"Pandas puro: {tiempo_pandas:.3f}s, {len(resultado_pandas)} grupos")

    for npart in CONFIGURACIONES_PARTICIONES:
        inicio = time.perf_counter()
        resultado_dask = agregacion_dask(rutas, npart)
        tiempo_dask = time.perf_counter() - inicio
        filas_csv.append({"configuracion": f"dask_{npart}part", "npartitions": npart, "tiempo_s": tiempo_dask,
                           "n_filas_resultado": len(resultado_dask)})
        print(f"Dask npartitions={npart}: {tiempo_dask:.3f}s, {len(resultado_dask)} grupos")

        comparables = resultado_pandas.merge(
            resultado_dask, on=["fecha", "tienda"], suffixes=("_pd", "_dd")
        )
        assert len(comparables) == len(resultado_pandas), (
            f"Dask (npartitions={npart}) no cubrio todos los grupos de Pandas"
        )
        assert np.allclose(comparables["total_monto_pd"], comparables["total_monto_dd"], rtol=1e-6), (
            f"Discrepancia en total_monto entre Pandas y Dask (npartitions={npart})"
        )
        assert (comparables["total_unidades_pd"] == comparables["total_unidades_dd"]).all(), (
            f"Discrepancia en total_unidades entre Pandas y Dask (npartitions={npart})"
        )

    print("Verificacion de equivalencia Pandas vs Dask: OK para todas las configuraciones.")

    ruta_csv = os.path.join(EVIDENCIAS_DIR, "resultados_c.csv")
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        campos = ["configuracion", "npartitions", "tiempo_s", "n_filas_resultado"]
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas_csv)
    print(f"CSV escrito en {ruta_csv}")

    if plt is not None:
        plt.figure(figsize=(7, 5))
        etiquetas = [f["configuracion"] for f in filas_csv]
        tiempos = [f["tiempo_s"] for f in filas_csv]
        plt.bar(etiquetas, tiempos, color=["#555"] + ["#2a7"] * len(CONFIGURACIONES_PARTICIONES))
        plt.ylabel("Tiempo (s)")
        plt.title("Experimento C: Pandas puro vs Dask por configuracion de particionamiento")
        plt.xticks(rotation=20)
        plt.tight_layout()
        ruta = os.path.join(EVIDENCIAS_DIR, "comparacion_c.png")
        plt.savefig(ruta, dpi=120)
        plt.close()
        print(f"Grafico escrito en {ruta}")
    else:
        print("matplotlib no disponible: no se genero grafico.")


if __name__ == "__main__":
    main()
