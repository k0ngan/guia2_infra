"""
Experimento A - Paralelismo de datos y vectorizacion.

Compara tres formas de aplicar la misma transformacion numerica sobre arreglos
de distinto tamano:

  1. Python puro (loop secuencial, sin NumPy).
  2. NumPy vectorizado (SIMD/BLAS internos, sin paralelismo explicito a nivel
     de Python; el numero de hilos BLAS usados no es controlado por este
     script y en general no es identificable como "p" de forma confiable).
  3. multiprocessing.Pool, partiendo el arreglo en chunks y usando p procesos.

Transformacion aplicada a cada elemento x del arreglo (normalizado entre 0 y 1
respecto del maximo absoluto del arreglo original):
    y = sqrt(|x_norm| ** 2) + x_norm
que en la practica es: elevar a potencia 2, raiz cuadrada y sumar el valor
normalizado. Se eligio una transformacion con costo aritmetico moderado
(potencia + raiz) para que el overhead de multiprocessing sea comparable
al trabajo util en arreglos grandes, sin volver el experimento demasiado lento.

Al final se reduce con una suma (agregacion) para obtener un escalar por via,
lo que permite verificar equivalencia numerica entre las tres implementaciones.

Salidas: evidencias/resultados_a.csv, evidencias/tiempo_vs_tamano.png,
evidencias/speedup_vs_p.png
"""

import csv
import math
import multiprocessing as mp
import os
import platform
import time

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

EVIDENCIAS_DIR = os.path.join(os.path.dirname(__file__), "..", "evidencias")
os.makedirs(EVIDENCIAS_DIR, exist_ok=True)

TAMANOS = [10_000, 100_000, 1_000_000, 5_000_000, 20_000_000]
REPETICIONES = 3
PROCESOS_A_PROBAR = [2, 4, 8]


def transformar_python_puro(datos):
    maximo = max(abs(x) for x in datos) or 1.0
    total = 0.0
    for x in datos:
        xn = x / maximo
        total += math.sqrt(xn * xn) + xn
    return total


def transformar_numpy(arr):
    maximo = np.max(np.abs(arr)) or 1.0
    xn = arr / maximo
    return float(np.sum(np.sqrt(xn ** 2) + xn))


def _chunk_sum(args):
    chunk, maximo = args
    xn = chunk / maximo
    return float(np.sum(np.sqrt(xn ** 2) + xn))


def transformar_multiprocessing(arr, n_procesos):
    maximo = float(np.max(np.abs(arr))) or 1.0
    chunks = np.array_split(arr, n_procesos)
    with mp.Pool(processes=n_procesos) as pool:
        parciales = pool.map(_chunk_sum, [(c, maximo) for c in chunks])
    return float(sum(parciales))


def describir_entorno():
    info = {
        "sistema_operativo": platform.platform(),
        "python": platform.python_version(),
        "cpu": platform.processor() or "no disponible",
        "nucleos_logicos": mp.cpu_count(),
        "numpy_version": np.__version__,
    }
    return info


def medir(func, *args, repeticiones=REPETICIONES):
    tiempos = []
    resultado = None
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        resultado = func(*args)
        tiempos.append(time.perf_counter() - inicio)
    return resultado, tiempos


def main():
    entorno = describir_entorno()
    print("Entorno de ejecucion:")
    for k, v in entorno.items():
        print(f"  {k}: {v}")
    print()

    filas = []
    tiempo_secuencial_por_tamano = {}

    for n in TAMANOS:
        rng = np.random.default_rng(42)
        arr = rng.normal(loc=0.0, scale=10.0, size=n)

        # Python puro solo para tamanos manejables: crece demasiado lento
        # en arreglos de millones de elementos (seria el "peor caso" del
        # paralelismo, pero no aporta mas evidencia y rompe el limite de tiempo).
        usar_python_puro = n <= 1_000_000

        resultado_np, tiempos_np = medir(transformar_numpy, arr)
        tiempo_secuencial_por_tamano[n] = min(tiempos_np)

        if usar_python_puro:
            datos_lista = arr.tolist()
            resultado_py, tiempos_py = medir(transformar_python_puro, datos_lista)
            assert np.isclose(resultado_py, resultado_np, rtol=1e-6), (
                f"Discrepancia Python puro vs NumPy en n={n}: {resultado_py} != {resultado_np}"
            )
            for t in tiempos_py:
                filas.append({
                    "tamano": n, "metodo": "python_puro", "p": 1,
                    "tiempo_s": t, "resultado": resultado_py,
                })
        else:
            print(f"n={n}: se omite Python puro (tiempo prohibitivo), referencia = NumPy")

        for t in tiempos_np:
            filas.append({
                "tamano": n, "metodo": "numpy_vectorizado", "p": "no_identificable",
                "tiempo_s": t, "resultado": resultado_np,
            })

        for p in PROCESOS_A_PROBAR:
            resultado_mp, tiempos_mp = medir(transformar_multiprocessing, arr, p)
            assert np.isclose(resultado_mp, resultado_np, rtol=1e-6), (
                f"Discrepancia multiprocessing(p={p}) vs NumPy en n={n}: {resultado_mp} != {resultado_np}"
            )
            for t in tiempos_mp:
                filas.append({
                    "tamano": n, "metodo": "multiprocessing", "p": p,
                    "tiempo_s": t, "resultado": resultado_mp,
                })

        print(f"n={n}: completado (python_puro={'si' if usar_python_puro else 'no'})")

    for fila in filas:
        n = fila["tamano"]
        t_sec = tiempo_secuencial_por_tamano[n]
        p = fila["p"]
        if isinstance(p, int) and p > 0:
            speedup = t_sec / fila["tiempo_s"] if fila["tiempo_s"] > 0 else float("inf")
            fila["speedup_vs_numpy"] = speedup
            fila["eficiencia"] = speedup / p
        else:
            fila["speedup_vs_numpy"] = ""
            fila["eficiencia"] = ""

    ruta_csv = os.path.join(EVIDENCIAS_DIR, "resultados_a.csv")
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        campos = ["tamano", "metodo", "p", "tiempo_s", "resultado", "speedup_vs_numpy", "eficiencia"]
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)
    print(f"\nCSV escrito en {ruta_csv}")

    if plt is not None:
        _graficar(filas)
    else:
        print("matplotlib no disponible: no se generaron graficos.")


def _graficar(filas):
    import collections

    # Grafico 1: tiempo promedio vs tamano, una serie por metodo (p=mejor caso para mp)
    promedios = collections.defaultdict(list)
    for fila in filas:
        if fila["metodo"] == "multiprocessing" and fila["p"] != max(PROCESOS_A_PROBAR):
            continue
        clave = fila["metodo"]
        promedios[(clave, fila["tamano"])].append(fila["tiempo_s"])

    plt.figure(figsize=(7, 5))
    for metodo in ["python_puro", "numpy_vectorizado", "multiprocessing"]:
        xs, ys = [], []
        for n in TAMANOS:
            valores = promedios.get((metodo, n))
            if valores:
                xs.append(n)
                ys.append(sum(valores) / len(valores))
        if xs:
            plt.plot(xs, ys, marker="o", label=metodo)
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Tamano del arreglo (elementos)")
    plt.ylabel("Tiempo promedio (s)")
    plt.title("Experimento A: tiempo vs tamano por metodo")
    plt.legend()
    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    ruta = os.path.join(EVIDENCIAS_DIR, "tiempo_vs_tamano.png")
    plt.savefig(ruta, dpi=120)
    plt.close()
    print(f"Grafico escrito en {ruta}")

    # Grafico 2: speedup vs p (multiprocessing), una serie por tamano grande
    plt.figure(figsize=(7, 5))
    for n in TAMANOS:
        xs, ys = [], []
        for fila in filas:
            if fila["metodo"] == "multiprocessing" and fila["tamano"] == n and fila["speedup_vs_numpy"] != "":
                xs.append(fila["p"])
                ys.append(fila["speedup_vs_numpy"])
        if xs:
            agregados = collections.defaultdict(list)
            for p, s in zip(xs, ys):
                agregados[p].append(s)
            ps = sorted(agregados)
            plt.plot(ps, [sum(agregados[p]) / len(agregados[p]) for p in ps], marker="o", label=f"n={n}")
    plt.xlabel("Numero de procesos (p)")
    plt.ylabel("Speedup respecto de NumPy vectorizado")
    plt.title("Experimento A: speedup de multiprocessing vs p")
    plt.axhline(1.0, color="gray", linestyle="--", linewidth=0.8)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    ruta = os.path.join(EVIDENCIAS_DIR, "speedup_vs_p.png")
    plt.savefig(ruta, dpi=120)
    plt.close()
    print(f"Grafico escrito en {ruta}")


if __name__ == "__main__":
    main()
