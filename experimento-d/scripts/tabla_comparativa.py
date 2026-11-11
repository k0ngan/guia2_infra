"""Resume resultados_d.csv en una tabla legible (evidencia 6 de la guia).

El CSV trae una fila por repeticion; la tabla promedia las repeticiones de cada
combinacion tamano x escenario y deja a la vista lo que interesa comparar:
tiempo total, residual de coordinacion, speedup y eficiencia.

    python scripts/tabla_comparativa.py evidencias/06_tabla_comparativa.md

Sin argumento, escribe la tabla por pantalla.
"""
import csv
import os
import statistics as st
import sys
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(AQUI, "..", "evidencias", "resultados_d.csv")
WORKERS_POR_ESCENARIO = {"A_secuencial": 1, "B_un_worker": 1, "C_dos_workers": 2}
ORDEN = ["A_secuencial", "B_un_worker", "C_dos_workers"]


def miles(n):
    return f"{n:,}".replace(",", ".")


def tabla(ruta):
    with open(ruta, newline="", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))

    tiempos, residuales, speedups, resultados, repeticiones = (defaultdict(list) for _ in range(5))
    for r in filas:
        k = (int(r["tamano"]), r["escenario"])
        repeticiones[k].append(r["completo"] == "True")
        if r["completo"] != "True":
            continue
        tiempos[k].append(float(r["tiempo_total_s"]))
        if r["residual_s"]:
            residuales[k].append(float(r["residual_s"]))
        if r["speedup"]:
            speedups[k].append(float(r["speedup"]))
        if r["resultado"]:
            resultados[k].append(int(r["resultado"]))

    tamanos = sorted({int(r["tamano"]) for r in filas})
    n_rep = len(repeticiones[(tamanos[0], ORDEN[0])])
    salida = [
        "# Experimento D -- tabla comparativa (clúster QEMU real)",
        "",
        f"Fuente: `evidencias/resultados_d.csv` ({len(filas)} filas, {len(tamanos)} tamaños "
        f"x {len(ORDEN)} escenarios x {n_rep} repeticiones).",
        "",
        "| Intervalo | Escenario | Primos | Tiempo total medio (s) | Residual medio (s) | Speedup | Eficiencia |",
        "|---|---|---|---|---|---|---|",
    ]
    for t in tamanos:
        for e in ORDEN:
            k = (t, e)
            if not repeticiones[k]:
                continue
            if not tiempos[k]:
                salida.append(f"| 2..{miles(t)} | {e} | — | incompleto | — | — | — |")
                continue
            p = WORKERS_POR_ESCENARIO[e]
            s = st.mean(speedups[k]) if speedups[k] else 1.0
            res = st.mean(residuales[k]) if residuales[k] else 0.0
            primos = resultados[k][0] if resultados[k] else "—"
            salida.append(f"| 2..{miles(t)} | {e} | {primos} | {st.mean(tiempos[k]):.6f} | "
                          f"{res:.6f} | {s:.3f} | {s / p:.3f} |")
    salida += [
        "",
        "El residual es `T_total - max(T_procesamiento_worker)`: agrupa preparación, "
        "envío/recepción por red y agregación.",
    ]
    return "\n".join(salida) + "\n"


if __name__ == "__main__":
    texto = tabla(CSV)
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(texto)
        print(f"Tabla escrita en {sys.argv[1]}")
    else:
        sys.stdout.write(texto)
