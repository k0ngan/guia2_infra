"""
Experimento D - worker.py

Servidor TCP que cuenta numeros primos en un intervalo [start, end] inclusivo.
Escucha en 0.0.0.0 (todas las interfaces de la VM, no solo loopback) en el
puerto indicado, para que el coordinador pueda conectarse desde el anfitrion
vía el reenvio de puertos de QEMU (hostfwd).

Protocolo (ver seccion 2.7 / Fase 3 de la guia):
  - Una conexion TCP por solicitud.
  - Solicitud: una linea JSON UTF-8 terminada en '\\n':
        {"start": <int>, "end": <int>}
  - Respuesta: una linea JSON UTF-8 terminada en '\\n':
        {"worker": "<id>", "result": <int>, "processing_seconds": <float>}
    o, si la solicitud es invalida:
        {"error": "<descripcion>"}

Uso:
    python worker.py [puerto] [worker_id]

Por defecto puerto=9000 y worker_id=hostname de la maquina. En las VMs Alpine
del clúster real se ejecuta como:
    python3 worker.py 9000 nodo1
    python3 worker.py 9000 nodo2
"""

import json
import socket
import socketserver
import sys
import time

TAMANO_MAXIMO_MENSAJE = 4096  # bytes; una solicitud JSON razonable no supera esto


def contar_primos(start, end):
    """Cuenta primos en [start, end] inclusivo mediante criba de Eratostenes.

    Se usa una criba (no trial division) porque el intervalo puede llegar a
    cientos de miles de numeros y la criba es asintoticamente mas eficiente
    para contar TODOS los primos de un rango que empieza cerca de 0.
    """
    if end < 2:
        return 0
    es_primo = bytearray([1]) * (end + 1)
    es_primo[0:min(2, end + 1)] = bytearray(min(2, end + 1))
    for i in range(2, int(end ** 0.5) + 1):
        if es_primo[i]:
            es_primo[i * i: end + 1: i] = bytearray(len(range(i * i, end + 1, i)))
    inicio = max(start, 2)
    return sum(es_primo[inicio:end + 1])


def leer_mensaje_delimitado(sock_file):
    """Lee hasta '\\n' sin asumir que una sola lectura trae el mensaje completo."""
    linea = sock_file.readline(TAMANO_MAXIMO_MENSAJE + 1)
    if len(linea) > TAMANO_MAXIMO_MENSAJE:
        raise ValueError("mensaje excede el tamano maximo permitido")
    return linea.decode("utf-8").strip()


def validar_solicitud(datos):
    if not isinstance(datos, dict):
        raise ValueError("la solicitud debe ser un objeto JSON")
    if "start" not in datos or "end" not in datos:
        raise ValueError("faltan campos 'start' y/o 'end'")
    start, end = datos["start"], datos["end"]
    if not isinstance(start, int) or isinstance(start, bool):
        raise ValueError("'start' debe ser entero")
    if not isinstance(end, int) or isinstance(end, bool):
        raise ValueError("'end' debe ser entero")
    if start < 0 or end < 0:
        raise ValueError("'start' y 'end' deben ser no negativos")
    if start > end:
        raise ValueError("'start' no puede ser mayor que 'end'")
    return start, end


class ManejadorPrimos(socketserver.StreamRequestHandler):
    timeout = 10

    def handle(self):
        try:
            linea = leer_mensaje_delimitado(self.rfile)
            if not linea:
                return
            datos = json.loads(linea)
            start, end = validar_solicitud(datos)

            inicio_proc = time.perf_counter()
            resultado = contar_primos(start, end)
            duracion = time.perf_counter() - inicio_proc

            respuesta = {
                "worker": self.server.worker_id,
                "result": resultado,
                "processing_seconds": duracion,
            }
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            respuesta = {"error": str(exc)}
        except Exception as exc:  # defensivo: nunca dejar la conexion sin respuesta
            respuesta = {"error": f"error interno: {exc}"}

        self.wfile.write((json.dumps(respuesta) + "\n").encode("utf-8"))


class ServidorPrimos(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, direccion, handler, worker_id):
        super().__init__(direccion, handler)
        self.worker_id = worker_id


def main():
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    worker_id = sys.argv[2] if len(sys.argv) > 2 else socket.gethostname()

    servidor = ServidorPrimos(("0.0.0.0", puerto), ManejadorPrimos, worker_id)
    print(f"worker '{worker_id}' escuchando en 0.0.0.0:{puerto}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nworker detenido por el usuario")
        servidor.shutdown()


if __name__ == "__main__":
    main()
