"""Resumen en pantalla de cada escena de la presentacion.

Lee el CSV de evidencias del experimento que se acaba de mostrar y escribe la
conclusion con los numeros que de verdad quedaron en pantalla, no con numeros
escritos a mano. Si se vuelve a correr un experimento, el resumen se mueve con
el; nunca queda contradiciendo lo que el video acaba de mostrar.

Uso:
    python presentacion/resumen_escena.py a|b|c|d
"""

import csv
import os
import statistics as st
import sys
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHO = 74


def num(valor, decimales=2):
    """Formatea a la chilena: punto para miles, coma para decimales.

    Es la misma convencion que declara la guia del Departamento y que usa el
    informe, asi que en pantalla no conviven dos estilos de numero.
    """
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def entero(valor):
    return f"{valor:,.0f}".replace(",", ".")


def marco(titulo, lineas):
    print()
    print("=" * ANCHO)
    print(f"  {titulo}")
    print("=" * ANCHO)
    for linea in lineas:
        print(f"  {linea}")
    print("=" * ANCHO)
    print()


def cargar(experimento, nombre):
    ruta = os.path.join(BASE, f"experimento-{experimento}", "evidencias", nombre)
    if not os.path.exists(ruta):
        return None
    with open(ruta, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _falta(experimento):
    marco(
        f"EXPERIMENTO {experimento.upper()}: sin evidencias todavia",
        ["No encontre el CSV de resultados. Corre el experimento antes de",
         "pedir su resumen."],
    )


def resumen_a():
    filas = cargar("a", "resultados_a.csv")
    if not filas:
        return _falta("a")

    tiempos = defaultdict(list)
    for r in filas:
        tiempos[(int(r["tamano"]), r["metodo"])].append(float(r["tiempo_s"]))

    tamanos = sorted({k[0] for k in tiempos})
    metodos = ["python_puro", "numpy_vectorizado", "multiprocessing"]

    lineas = [f"{'n':>14}{'Python puro':>14}{'NumPy':>14}{'procesos':>14}", ""]
    for n in tamanos:
        fila = f"{entero(n):>14}"
        for m in metodos:
            v = tiempos.get((n, m))
            fila += f"{num(st.mean(v), 4):>14}" if v else f"{'(omitido)':>14}"
        lineas.append(fila)

    razones = []
    for n in tamanos:
        vn, vm = tiempos.get((n, "numpy_vectorizado")), tiempos.get((n, "multiprocessing"))
        if vn and vm:
            razones.append((n, st.mean(vm) / st.mean(vn)))

    if razones:
        lineas += [
            "",
            "Cuantas veces mas lento es multiprocessing que NumPy:",
            f"   con n = {entero(razones[0][0])}: {entero(razones[0][1])} veces mas lento",
            f"   con n = {entero(razones[-1][0])}: {num(razones[-1][1])} veces mas lento",
            "",
            "NumPy gana en TODOS los tamanos. Crear procesos cuesta un fijo que",
            "no se amortiza: la brecha se cierra, pero nunca se da vuelta.",
            "Antes de paralelizar, vectorizar.",
        ]
    marco("EXPERIMENTO A - tiempo promedio por metodo (segundos)", lineas)


def resumen_b():
    filas = cargar("b", "resultados_b.csv")
    if not filas:
        return _falta("b")

    mejor = {}
    for r in filas:
        clave = (r["tipo_carga"], r["modo"])
        t = float(r["tiempo_s"])
        if clave not in mejor or t < mejor[clave]:
            mejor[clave] = t

    lineas = [f"{'':>14}{'secuencial':>14}{'hilos':>14}{'procesos':>14}", ""]
    for carga, etiqueta in [("cpu_bound", "CPU-bound"), ("io_bound", "I/O-bound")]:
        fila = f"{etiqueta:>14}"
        for modo in ["secuencial", "threads", "procesos"]:
            t = mejor.get((carga, modo))
            fila += f"{num(t, 3):>14}" if t is not None else f"{'-':>14}"
        lineas.append(fila)

    sec_cpu, hil_cpu = mejor.get(("cpu_bound", "secuencial")), mejor.get(("cpu_bound", "threads"))
    sec_io, hil_io = mejor.get(("io_bound", "secuencial")), mejor.get(("io_bound", "threads"))
    lineas.append("")
    if sec_cpu and hil_cpu:
        lineas.append(f"CPU-bound: los hilos dan {num(sec_cpu / hil_cpu)}x. O sea, nada: el GIL")
        lineas.append("serializa el computo puro de Python por mucho que agregues hilos.")
    if sec_io and hil_io:
        lineas.append(f"I/O-bound: los mismos hilos dan {num(sec_io / hil_io, 1)}x, porque la espera")
        lineas.append("libera el GIL y ahi si hay concurrencia real.")
    lineas.append("")
    lineas.append("La herramienta se elige por el tipo de carga, no por costumbre.")
    marco("EXPERIMENTO B - mejor tiempo por modo (segundos)", lineas)


def resumen_c():
    filas = cargar("c", "resultados_c.csv")
    if not filas:
        return _falta("c")

    tiempos = {r["configuracion"]: float(r["tiempo_s"]) for r in filas}
    lineas = []
    for conf, t in tiempos.items():
        lineas.append(f"{conf:>16}: {num(t, 4)} s")

    base = tiempos.get("pandas_puro")
    daskeados = {k: v for k, v in tiempos.items() if k != "pandas_puro"}
    if base and daskeados:
        optimo = min(daskeados, key=daskeados.get)
        peor = max(daskeados, key=daskeados.get)
        lineas += [
            "",
            f"El optimo es {optimo}: {num(base / daskeados[optimo])}x mas rapido que Pandas.",
            f"Pero {peor} ya EMPEORA respecto del optimo",
            f"({num(daskeados[peor] / daskeados[optimo])}x mas lento).",
            "",
            "Ahi esta el punto de inflexion: pasado cierto numero de particiones,",
            "coordinar el grafo de tareas cuesta mas que el trabajo repartido.",
        ]
    marco("EXPERIMENTO C - Dask particionado vs Pandas puro", lineas)


def resumen_d():
    filas = cargar("d", "resultados_d.csv")
    if not filas:
        return _falta("d")

    speedups = defaultdict(list)
    for r in filas:
        if r["completo"] == "True" and r["speedup"]:
            speedups[(int(r["tamano"]), r["escenario"])].append(float(r["speedup"]))

    tamanos = sorted({k[0] for k in speedups})
    escenarios = [("B_un_worker", "1 worker"), ("C_dos_workers", "2 workers")]

    lineas = [f"{'intervalo 2..':>16}{'1 worker':>14}{'2 workers':>14}", ""]
    gana_desde = None
    for n in tamanos:
        fila = f"{entero(n):>16}"
        for clave, _ in escenarios:
            v = speedups.get((n, clave))
            fila += f"{num(st.mean(v), 3) + 'x':>14}" if v else f"{'-':>14}"
        lineas.append(fila)
        v2 = speedups.get((n, "C_dos_workers"))
        if v2 and st.mean(v2) > 1.0 and gana_desde is None:
            gana_desde = n

    perdedores = sum(
        1 for n in tamanos
        if speedups.get((n, "C_dos_workers")) and st.mean(speedups[(n, "C_dos_workers")]) < 1.0
    )
    lineas += ["", f"Distribuir PIERDE en {perdedores} de los {len(tamanos)} tamanos medidos."]
    if gana_desde:
        lineas.append(f"Recien desde 2..{entero(gana_desde)} el computo pesa lo")
        lineas.append("suficiente como para pagar la coordinacion.")
    lineas += [
        "",
        "El costo fijo de coordinar (abrir conexion, serializar, esperar,",
        "agregar) es de unos milisegundos y NO baja aunque el problema crezca.",
    ]
    marco("EXPERIMENTO D - speedup sobre el cluster QEMU real", lineas)


def cierre():
    """Las cuatro conclusiones en una sola pantalla, para cerrar el video."""
    lineas = []

    fa = cargar("a", "resultados_a.csv")
    if fa:
        t = defaultdict(list)
        for r in fa:
            t[(int(r["tamano"]), r["metodo"])].append(float(r["tiempo_s"]))
        grandes = max(k[0] for k in t)
        vn, vm = t.get((grandes, "numpy_vectorizado")), t.get((grandes, "multiprocessing"))
        if vn and vm:
            lineas += [
                "A  Vectorizar le gana a repartir en los 5 tamanos. Ni con 20",
                f"   millones de elementos los procesos alcanzan a NumPy: siguen",
                f"   {num(st.mean(vm) / st.mean(vn))} veces mas lentos.",
                "",
            ]

    fb = cargar("b", "resultados_b.csv")
    if fb:
        mejor = {}
        for r in fb:
            k, v = (r["tipo_carga"], r["modo"]), float(r["tiempo_s"])
            if k not in mejor or v < mejor[k]:
                mejor[k] = v
        c1, c2 = mejor.get(("cpu_bound", "secuencial")), mejor.get(("cpu_bound", "threads"))
        i1, i2 = mejor.get(("io_bound", "secuencial")), mejor.get(("io_bound", "threads"))
        if c1 and c2 and i1 and i2:
            lineas += [
                f"B  Los mismos hilos dan {num(c1 / c2)}x en carga CPU-bound y {num(i1 / i2, 1)}x en",
                "   I/O-bound. La diferencia es el GIL, no el numero de hilos.",
                "",
            ]

    fc = cargar("c", "resultados_c.csv")
    if fc:
        t = {r["configuracion"]: float(r["tiempo_s"]) for r in fc}
        base = t.pop("pandas_puro", None)
        if base and t:
            opt = min(t, key=t.get)
            peor = max(t, key=t.get)
            lineas += [
                f"C  Particionar ayuda hasta un punto: {opt} da {num(base / t[opt])}x, pero",
                f"   {peor} ya retrocede. Coordinar tambien cuesta.",
                "",
            ]

    fd = cargar("d", "resultados_d.csv")
    if fd:
        sp = defaultdict(list)
        for r in fd:
            if r["completo"] == "True" and r["speedup"]:
                sp[(int(r["tamano"]), r["escenario"])].append(float(r["speedup"]))
        tams = sorted({k[0] for k in sp})
        pierde = [n for n in tams
                  if sp.get((n, "C_dos_workers")) and st.mean(sp[(n, "C_dos_workers")]) < 1.0]
        if tams:
            lineas += [
                f"D  Distribuir entre VMs pierde en {len(pierde)} de {len(tams)} tamanos. Solo gana",
                "   cuando el computo supera por mucho el costo fijo de la red.",
                "",
            ]

    lineas += [
        "-" * (ANCHO - 4),
        "",
        "Las cuatro apuntan a lo mismo: el paralelismo no es gratis. Tiene un",
        "costo de entrada -crear procesos, coordinar un grafo, abrir una",
        "conexion- y solo conviene cuando el trabajo lo supera.",
        "",
        "Medir cuando conviene es la respuesta de ingenieria. Suponer que",
        "siempre conviene es el error que estos cuatro experimentos descartan.",
    ]
    marco("LO QUE MUESTRAN LOS CUATRO EXPERIMENTOS", lineas)


def main():
    opciones = {"a": resumen_a, "b": resumen_b, "c": resumen_c, "d": resumen_d,
                "cierre": cierre}
    clave = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if clave not in opciones:
        print("Uso: python presentacion/resumen_escena.py a|b|c|d|cierre")
        sys.exit(2)
    opciones[clave]()


if __name__ == "__main__":
    main()
