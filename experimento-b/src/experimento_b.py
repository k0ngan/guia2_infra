"""
Experimento B - Paralelismo a nivel de tareas (batch processing).

Simula un flujo de feature engineering por lotes independientes sobre un
DataFrame sintetico. Cada lote se procesa de forma autocontenida (no depende
de otros lotes), lo que permite repartirlos entre hilos o procesos sin
coordinacion adicional.

Dos tipos de carga, ejecutadas por separado para poder compararlas:

  - CPU-bound: escalado estandar + encoding one-hot manual + features
    derivadas (razones, productos) sobre cada lote -- trabajo aritmetico real
    que mantiene el CPU ocupado.
  - I/O-bound (simulada): mismo feature engineering, mas una espera
    time.sleep() corta por lote que imita latencia de E/S (ej. leer un
    archivo o llamar a un servicio externo por lote).

Se comparan tres formas de ejecutar los lotes:
  1. Secuencial (un hilo, un proceso, sin superposicion).
  2. ThreadPoolExecutor (hilos del mismo proceso).
  3. ProcessPoolExecutor (procesos independientes).

sobre >=3 configuraciones de workers y >=3 tamanos de lote, para CPU-bound e
I/O-bound. Para CPU-bound, el GIL hace que ThreadPoolExecutor no acelere el
computo puro de Python/Pandas; para I/O-bound, los hilos si deberian ayudar
porque la espera libera el GIL.

Salidas: evidencias/resultados_b.csv, evidencias/comparacion_b.png
"""

import csv
import os
import platform
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import numpy as np
import pandas as pd

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

try:
    import psutil
    _TIENE_PSUTIL = True
except ImportError:
    psutil = None
    _TIENE_PSUTIL = False
    print("Aviso: psutil no esta instalado; se omitira la metrica de uso de CPU "
          "(instalar con 'pip install psutil' para incluirla).")

EVIDENCIAS_DIR = os.path.join(os.path.dirname(__file__), "..", "evidencias")
os.makedirs(EVIDENCIAS_DIR, exist_ok=True)

TAMANOS_LOTE = [200, 1000, 5000]
N_LOTES = 24
CONFIGURACIONES_WORKERS = [2, 4, 8]
SLEEP_IO_SEGUNDOS = 0.02


def generar_lote(n_filas, semilla):
    rng = np.random.default_rng(semilla)
    return pd.DataFrame({
        "monto": rng.normal(1000, 300, n_filas),
        "edad": rng.integers(18, 90, n_filas),
        "categoria": rng.choice(["A", "B", "C", "D"], n_filas),
        "activo": rng.integers(0, 2, n_filas),
    })


def procesar_lote_cpu(df):
    out = df.copy()
    out["monto_escalado"] = (out["monto"] - out["monto"].mean()) / (out["monto"].std() + 1e-9)
    out["edad_escalada"] = (out["edad"] - out["edad"].mean()) / (out["edad"].std() + 1e-9)
    for cat in ["A", "B", "C", "D"]:
        out[f"categoria_{cat}"] = (out["categoria"] == cat).astype(int)
    out["monto_por_edad"] = out["monto"] / out["edad"].replace(0, 1)
    out["interaccion"] = out["monto_escalado"] * out["edad_escalada"]
    return len(out)


def procesar_lote_io(df):
    resultado = procesar_lote_cpu(df)
    time.sleep(SLEEP_IO_SEGUNDOS)
    return resultado


def ejecutar_secuencial(lotes, funcion):
    return [funcion(lote) for lote in lotes]


def ejecutar_threads(lotes, funcion, n_workers):
    with ThreadPoolExecutor(max_workers=n_workers) as ex:
        return list(ex.map(funcion, lotes))


def ejecutar_procesos(lotes, funcion, n_workers):
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        return list(ex.map(funcion, lotes))


def cpu_actual():
    if _TIENE_PSUTIL:
        return psutil.cpu_percent(interval=None)
    return None


def main():
    print(f"CPU: {platform.processor() or 'no disponible'} | "
          f"nucleos logicos: {os.cpu_count()} | psutil: {'si' if _TIENE_PSUTIL else 'no'}")

    filas = []
    for tamano in TAMANOS_LOTE:
        lotes = [generar_lote(tamano, semilla=i) for i in range(N_LOTES)]

        for tipo_carga, funcion in [("cpu_bound", procesar_lote_cpu), ("io_bound", procesar_lote_io)]:
            cpu_actual()
            inicio = time.perf_counter()
            ejecutar_secuencial(lotes, funcion)
            tiempo = time.perf_counter() - inicio
            uso_cpu = cpu_actual()
            filas.append({
                "tamano_lote": tamano, "tipo_carga": tipo_carga, "modo": "secuencial",
                "n_workers": 1, "tiempo_s": tiempo, "uso_cpu_pct": uso_cpu,
            })
            print(f"tamano={tamano} carga={tipo_carga} secuencial: {tiempo:.3f}s")

            for n_workers in CONFIGURACIONES_WORKERS:
                for modo, ejecutor in [("threads", ejecutar_threads), ("procesos", ejecutar_procesos)]:
                    cpu_actual()
                    inicio = time.perf_counter()
                    ejecutor(lotes, funcion, n_workers)
                    tiempo = time.perf_counter() - inicio
                    uso_cpu = cpu_actual()
                    filas.append({
                        "tamano_lote": tamano, "tipo_carga": tipo_carga, "modo": modo,
                        "n_workers": n_workers, "tiempo_s": tiempo, "uso_cpu_pct": uso_cpu,
                    })
                    print(f"tamano={tamano} carga={tipo_carga} {modo} workers={n_workers}: {tiempo:.3f}s")

    ruta_csv = os.path.join(EVIDENCIAS_DIR, "resultados_b.csv")
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        campos = ["tamano_lote", "tipo_carga", "modo", "n_workers", "tiempo_s", "uso_cpu_pct"]
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)
    print(f"\nCSV escrito en {ruta_csv}")

    if plt is not None:
        _graficar(filas)
    else:
        print("matplotlib no disponible: no se generaron graficos.")


def _graficar(filas):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=False)
    for ax, tipo_carga in zip(axes, ["cpu_bound", "io_bound"]):
        for modo in ["secuencial", "threads", "procesos"]:
            xs, ys = [], []
            for tamano in TAMANOS_LOTE:
                candidatos = [f for f in filas if f["tipo_carga"] == tipo_carga and f["modo"] == modo
                              and f["tamano_lote"] == tamano]
                if modo == "secuencial":
                    candidatos = [c for c in candidatos]
                else:
                    # mejor configuracion de workers para ese modo/tamano
                    candidatos = sorted(candidatos, key=lambda c: c["tiempo_s"])[:1]
                if candidatos:
                    xs.append(tamano)
                    ys.append(min(c["tiempo_s"] for c in candidatos))
            if xs:
                ax.plot(xs, ys, marker="o", label=modo)
        ax.set_title(f"Carga {tipo_carga}")
        ax.set_xlabel("Tamano de lote (filas)")
        ax.set_ylabel("Tiempo total (s)")
        ax.legend()
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    ruta = os.path.join(EVIDENCIAS_DIR, "comparacion_b.png")
    plt.savefig(ruta, dpi=120)
    plt.close()
    print(f"Grafico escrito en {ruta}")


if __name__ == "__main__":
    main()
