"""
Experimento D - coordinator.py

Coordinador del clúster virtual (3 nodos QEMU) para el conteo distribuido de
numeros primos. Implementa los tres escenarios de la Fase 4:

    A. Secuencial          -- todo el calculo en el propio coordinador, sin red.
    B. Un worker remoto    -- nodo1 procesa el intervalo completo.
    C. Dos workers remotos -- nodo1 y nodo2 procesan particiones disjuntas.

Direcciones de los workers
---------------------------
Editar WORKERS_CLUSTER_REAL para apuntar al clúster QEMU real (ver seccion
2.5 de la guia: el anfitrion ve a los workers en 10.0.2.2:9001 y 10.0.2.2:9002,
porque cada puerto esta reenviado por hostfwd hacia el puerto 9000 interno de
cada VM):

    WORKERS_CLUSTER_REAL = [("10.0.2.2", 9001), ("10.0.2.2", 9002)]

Por defecto este archivo usa WORKERS_SIMULACION_LOCAL, que apunta a dos
procesos worker.py lanzados en localhost en puertos distintos. Este modo de
simulacion local permite validar el protocolo coordinador-worker (framing
JSON, timeouts, validacion de respuestas) sin tener las VMs levantadas.

Para usar el clúster real, cambiar la asignacion de WORKERS en la seccion de
configuracion mas abajo.

Ejecucion
---------
    python coordinator.py prueba        -> corre la prueba de correctitud (2..10 -> 4)
    python coordinator.py bateria       -> corre la bateria completa de comparacion
                                            (3 tamanos x 3 escenarios x 3 repeticiones)
                                            y escribe evidencias/resultados_d.csv + grafico
    python coordinator.py simulacion    -> lanza 2 workers locales como subprocesos,
                                            corre prueba + bateria contra ellos, y los
                                            detiene al terminar (uso del implementador
                                            para validar el protocolo end-to-end)
"""

import csv
import json
import os
import socket
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --------------------------- configuracion ---------------------------------

# Clúster real (VMs QEMU): descomentar y usar esta lista para apuntar a las VMs.
WORKERS_CLUSTER_REAL = [("10.0.2.2", 9001), ("10.0.2.2", 9002)]

# Simulacion local (sin VMs): dos workers lanzados en localhost.
WORKERS_SIMULACION_LOCAL = [("127.0.0.1", 9101), ("127.0.0.1", 9102)]

# Seleccion activa: el clúster real de 3 VMs QEMU, que es el entorno con el que
# se midio la bateria entregada (ver evidencias/). Para validar el protocolo sin
# VMs, el modo "simulacion" cambia esta seleccion solo.
WORKERS = WORKERS_CLUSTER_REAL

TIMEOUT_SEGUNDOS = 15
TAMANO_MAXIMO_MENSAJE = 4096

EVIDENCIAS_DIR = os.path.join(os.path.dirname(__file__), "..", "evidencias")
os.makedirs(EVIDENCIAS_DIR, exist_ok=True)

# -----------------------------------------------------------------------------


def contar_primos_local(start, end):
    """Misma criba que worker.py, usada para el escenario secuencial (sin red)."""
    if end < 2:
        return 0
    es_primo = bytearray([1]) * (end + 1)
    es_primo[0:min(2, end + 1)] = bytearray(min(2, end + 1))
    for i in range(2, int(end ** 0.5) + 1):
        if es_primo[i]:
            es_primo[i * i: end + 1: i] = bytearray(len(range(i * i, end + 1, i)))
    inicio = max(start, 2)
    return sum(es_primo[inicio:end + 1])


def solicitar_a_worker(direccion, start, end, worker_esperado=None):
    """Abre una conexion TCP, envia la solicitud y espera la respuesta validada.

    Devuelve dict con 'ok': True/False. Si ok=False, incluye 'motivo'.
    Nunca lanza excepcion hacia el llamador: cualquier falla de red, timeout
    o respuesta malformada se traduce en ok=False para que el coordinador
    pueda seguir e informar un resultado global incompleto.
    """
    host, puerto = direccion
    inicio_total = time.perf_counter()
    try:
        with socket.create_connection((host, puerto), timeout=TIMEOUT_SEGUNDOS) as sock:
            sock.settimeout(TIMEOUT_SEGUNDOS)
            solicitud = json.dumps({"start": start, "end": end}) + "\n"
            sock.sendall(solicitud.encode("utf-8"))

            buffer = b""
            while b"\n" not in buffer:
                fragmento = sock.recv(4096)
                if not fragmento:
                    break
                buffer += fragmento
                if len(buffer) > TAMANO_MAXIMO_MENSAJE:
                    return {"ok": False, "motivo": "respuesta excede tamano maximo permitido",
                            "direccion": direccion}

            if b"\n" not in buffer:
                return {"ok": False, "motivo": "conexion cerrada sin respuesta completa",
                        "direccion": direccion}

            linea = buffer.split(b"\n", 1)[0].decode("utf-8")
            datos = json.loads(linea)
    except (socket.timeout, TimeoutError):
        return {"ok": False, "motivo": f"timeout tras {TIMEOUT_SEGUNDOS}s", "direccion": direccion}
    except (ConnectionRefusedError, OSError) as exc:
        return {"ok": False, "motivo": f"error de conexion: {exc}", "direccion": direccion}
    except json.JSONDecodeError as exc:
        return {"ok": False, "motivo": f"respuesta no es JSON valido: {exc}", "direccion": direccion}

    tiempo_total_solicitud = time.perf_counter() - inicio_total

    if "error" in datos:
        return {"ok": False, "motivo": f"worker reporto error: {datos['error']}", "direccion": direccion}

    for campo, tipo in [("worker", str), ("result", int), ("processing_seconds", (int, float))]:
        if campo not in datos:
            return {"ok": False, "motivo": f"falta campo '{campo}' en la respuesta", "direccion": direccion}
        if not isinstance(datos[campo], tipo) or isinstance(datos[campo], bool):
            return {"ok": False, "motivo": f"campo '{campo}' tiene tipo invalido", "direccion": direccion}

    if datos["result"] < 0:
        return {"ok": False, "motivo": "'result' no puede ser negativo", "direccion": direccion}
    if datos["processing_seconds"] < 0:
        return {"ok": False, "motivo": "'processing_seconds' no puede ser negativo", "direccion": direccion}
    if worker_esperado is not None and datos["worker"] != worker_esperado:
        return {"ok": False, "motivo": f"worker respondio con id '{datos['worker']}', se esperaba '{worker_esperado}'",
                "direccion": direccion}

    return {
        "ok": True,
        "worker": datos["worker"],
        "result": datos["result"],
        "processing_seconds": datos["processing_seconds"],
        "tiempo_total_solicitud": tiempo_total_solicitud,
        "direccion": direccion,
        "start": start,
        "end": end,
    }


def particionar(start, end, n_partes):
    """Particiona [start, end] en n_partes contiguas, inclusivas, sin huecos ni solape."""
    total = end - start + 1
    base = total // n_partes
    resto = total % n_partes
    partes = []
    cursor = start
    for i in range(n_partes):
        tamano = base + (1 if i < resto else 0)
        if tamano == 0:
            continue
        partes.append((cursor, cursor + tamano - 1))
        cursor += tamano
    return partes


def escenario_secuencial(start, end):
    inicio = time.perf_counter()
    resultado = contar_primos_local(start, end)
    tiempo_total = time.perf_counter() - inicio
    return {
        "escenario": "A_secuencial", "n_workers": 0, "resultado": resultado,
        "completo": True, "tiempo_total_s": tiempo_total,
        "tiempos_procesamiento": [tiempo_total], "detalle": [],
    }


def escenario_un_worker(start, end):
    direccion = WORKERS[0]
    inicio = time.perf_counter()
    respuesta = solicitar_a_worker(direccion, start, end)
    tiempo_total = time.perf_counter() - inicio

    if not respuesta["ok"]:
        return {
            "escenario": "B_un_worker", "n_workers": 1, "resultado": None,
            "completo": False, "tiempo_total_s": tiempo_total,
            "tiempos_procesamiento": [], "detalle": [respuesta],
            "error": respuesta["motivo"],
        }
    return {
        "escenario": "B_un_worker", "n_workers": 1, "resultado": respuesta["result"],
        "completo": True, "tiempo_total_s": tiempo_total,
        "tiempos_procesamiento": [respuesta["processing_seconds"]], "detalle": [respuesta],
    }


def escenario_dos_workers(start, end):
    partes = particionar(start, end, 2)
    inicio = time.perf_counter()
    respuestas = []
    with ThreadPoolExecutor(max_workers=2) as ex:
        futuros = {
            ex.submit(solicitar_a_worker, WORKERS[i], partes[i][0], partes[i][1]): WORKERS[i]
            for i in range(2)
        }
        for futuro in as_completed(futuros):
            respuestas.append(futuro.result())
    tiempo_total = time.perf_counter() - inicio

    fallidas = [r for r in respuestas if not r["ok"]]
    if fallidas:
        return {
            "escenario": "C_dos_workers", "n_workers": 2, "resultado": None,
            "completo": False, "tiempo_total_s": tiempo_total,
            "tiempos_procesamiento": [r["processing_seconds"] for r in respuestas if r["ok"]],
            "detalle": respuestas,
            "error": "; ".join(f"{r['direccion']}: {r['motivo']}" for r in fallidas),
        }

    resultado_total = sum(r["result"] for r in respuestas)
    return {
        "escenario": "C_dos_workers", "n_workers": 2, "resultado": resultado_total,
        "completo": True, "tiempo_total_s": tiempo_total,
        "tiempos_procesamiento": [r["processing_seconds"] for r in respuestas],
        "detalle": respuestas,
    }


def prueba_correctitud():
    print("Prueba de correctitud: contar primos en [2, 10] (esperado: 4)")
    resultado = contar_primos_local(2, 10)
    assert resultado == 4, f"fallo prueba local: se obtuvo {resultado}, se esperaba 4"
    print(f"  local (sin red): {resultado} -> OK")

    r_b = escenario_un_worker(2, 10)
    if r_b["completo"]:
        estado = "OK" if r_b["resultado"] == 4 else f"FALLO (obtuvo {r_b['resultado']})"
        print(f"  un worker remoto: {r_b['resultado']} -> {estado}")
    else:
        print(f"  un worker remoto: NO DISPONIBLE ({r_b.get('error')})")

    r_c = escenario_dos_workers(2, 10)
    if r_c["completo"]:
        estado = "OK" if r_c["resultado"] == 4 else f"FALLO (obtuvo {r_c['resultado']})"
        print(f"  dos workers remotos: {r_c['resultado']} -> {estado}")
    else:
        print(f"  dos workers remotos: NO DISPONIBLE ({r_c.get('error')})")

    return resultado == 4


def ejecutar_bateria(tamanos=(10_000, 100_000, 500_000), repeticiones=3):
    filas = []
    tiempo_a_por_tamano = {}

    for inicio_intervalo, fin_intervalo in [(2, t) for t in tamanos]:
        tiempos_a = []
        for rep in range(repeticiones):
            r = escenario_secuencial(inicio_intervalo, fin_intervalo)
            tiempos_a.append(r["tiempo_total_s"])
            filas.append(_fila_desde_resultado(r, rep, tamano=fin_intervalo, t_referencia=None))
        tiempo_a_referencia = statistics.mean(tiempos_a)
        tiempo_a_por_tamano[fin_intervalo] = tiempo_a_referencia

        for funcion, p in [(escenario_un_worker, 1), (escenario_dos_workers, 2)]:
            for rep in range(repeticiones):
                r = funcion(inicio_intervalo, fin_intervalo)
                filas.append(_fila_desde_resultado(r, rep, tamano=fin_intervalo,
                                                     t_referencia=tiempo_a_referencia, p=p))

        print(f"tamano={fin_intervalo}: completado "
              f"(T_A promedio={tiempo_a_referencia:.4f}s)")

    _resultado_consistente(filas, tamanos)

    ruta_csv = os.path.join(EVIDENCIAS_DIR, "resultados_d.csv")
    campos = ["tamano", "repeticion", "escenario", "n_workers", "resultado", "completo",
              "tiempo_total_s", "tiempos_procesamiento", "residual_s", "speedup", "eficiencia", "error"]
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)
    print(f"\nCSV escrito en {ruta_csv}")

    _graficar_bateria(filas)
    return filas


def _fila_desde_resultado(r, rep, tamano, t_referencia, p=0):
    tiempos_proc = r["tiempos_procesamiento"]
    max_proc = max(tiempos_proc) if tiempos_proc else None
    residual = (r["tiempo_total_s"] - max_proc) if max_proc is not None else None

    if t_referencia is None:
        speedup, eficiencia = 1.0, 1.0
    elif r["completo"] and p > 0:
        speedup = t_referencia / r["tiempo_total_s"] if r["tiempo_total_s"] > 0 else float("inf")
        eficiencia = speedup / p
    else:
        speedup, eficiencia = "", ""

    return {
        "tamano": tamano, "repeticion": rep, "escenario": r["escenario"], "n_workers": r["n_workers"],
        "resultado": r["resultado"], "completo": r["completo"], "tiempo_total_s": r["tiempo_total_s"],
        "tiempos_procesamiento": ";".join(f"{t:.6f}" for t in tiempos_proc),
        "residual_s": residual if residual is not None else "",
        "speedup": speedup, "eficiencia": eficiencia, "error": r.get("error", ""),
    }


def _resultado_consistente(filas, tamanos):
    for tamano in tamanos:
        resultados = {f["resultado"] for f in filas if f["tamano"] == tamano and f["completo"] and f["resultado"] is not None}
        if len(resultados) > 1:
            print(f"ADVERTENCIA: resultados distintos entre escenarios para tamano={tamano}: {resultados}")
        elif len(resultados) == 1:
            print(f"tamano={tamano}: resultado consistente entre escenarios completos ({resultados.pop()} primos)")


def _graficar_bateria(filas):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib no disponible: no se genero grafico de la bateria D.")
        return

    import collections
    promedios = collections.defaultdict(list)
    for f in filas:
        if f["completo"]:
            promedios[(f["escenario"], f["tamano"])].append(f["tiempo_total_s"])

    tamanos = sorted({f["tamano"] for f in filas})
    plt.figure(figsize=(7, 5))
    for escenario in ["A_secuencial", "B_un_worker", "C_dos_workers"]:
        xs, ys = [], []
        for t in tamanos:
            valores = promedios.get((escenario, t))
            if valores:
                xs.append(t)
                ys.append(sum(valores) / len(valores))
        if xs:
            plt.plot(xs, ys, marker="o", label=escenario)
    # Escalas logaritmicas: los tamanos van de 10^4 a 10^7 y los tiempos de
    # 10^-5 a 10^-1 s. En ejes lineales los tres tamanos chicos se apilan sobre
    # el cero y se pierde justo el tramo donde el overhead domina al computo.
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Tamano del intervalo (hasta N, escala log)")
    plt.ylabel("Tiempo total promedio en segundos (escala log)")
    plt.title("Experimento D: tiempo por escenario y tamano (cluster QEMU)")
    plt.legend()
    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    ruta = os.path.join(EVIDENCIAS_DIR, "comparacion_d.png")
    plt.savefig(ruta, dpi=120)
    plt.close()
    print(f"Grafico escrito en {ruta}")


def _lanzar_workers_simulacion():
    base_dir = os.path.dirname(__file__)
    procesos = []
    for host, puerto in WORKERS_SIMULACION_LOCAL:
        worker_id = f"worker_sim_{puerto}"
        proc = subprocess.Popen(
            [sys.executable, os.path.join(base_dir, "worker.py"), str(puerto), worker_id],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        procesos.append(proc)
    time.sleep(1.0)  # dar tiempo a que cada worker abra su socket de escucha
    return procesos


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "prueba"

    if modo == "prueba":
        ok = prueba_correctitud()
        sys.exit(0 if ok else 1)

    if modo == "bateria":
        # Opcional: tamanos y repeticiones por linea de comandos, para poder
        # extender la bateria mas alla de los tres tamanos de referencia sin
        # editar el archivo.
        #   python3 coordinator.py bateria 10000,100000,500000 3
        tamanos = tuple(int(x) for x in sys.argv[2].split(",")) if len(sys.argv) > 2 \
            else (10_000, 100_000, 500_000)
        repeticiones = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        ejecutar_bateria(tamanos=tamanos, repeticiones=repeticiones)
        return

    if modo == "simulacion":
        global WORKERS
        WORKERS = WORKERS_SIMULACION_LOCAL
        print(f"Lanzando workers de simulacion local en {WORKERS_SIMULACION_LOCAL} ...")
        procesos = _lanzar_workers_simulacion()
        try:
            ok = prueba_correctitud()
            if ok:
                ejecutar_bateria(tamanos=(10_000, 50_000, 200_000), repeticiones=3)
        finally:
            for p in procesos:
                p.terminate()
            for p in procesos:
                p.wait(timeout=5)
            print("workers de simulacion detenidos")
        return

    if modo == "grafico":
        # Regenera comparacion_d.png desde un resultados_d.csv ya medido. Sirve
        # cuando la bateria corrio en nodo0 (Alpine, sin matplotlib) y el CSV se
        # trajo por SCP al anfitrion, que si tiene matplotlib.
        ruta_csv = os.path.join(EVIDENCIAS_DIR, "resultados_d.csv")
        with open(ruta_csv, newline="", encoding="utf-8") as f:
            filas = [
                {
                    "tamano": int(r["tamano"]),
                    "escenario": r["escenario"],
                    "completo": r["completo"] == "True",
                    "tiempo_total_s": float(r["tiempo_total_s"]) if r["tiempo_total_s"] else None,
                }
                for r in csv.DictReader(f)
            ]
        print(f"{len(filas)} filas leidas de {ruta_csv}")
        _graficar_bateria(filas)
        return

    print("Uso: python coordinator.py [prueba|bateria|simulacion|grafico]")
    sys.exit(2)


if __name__ == "__main__":
    main()
