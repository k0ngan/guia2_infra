"""Muestra, para un intervalo, que particion recibio cada worker, que devolvio
cada uno y como se agrega el resultado final.

La bateria de `coordinator.py bateria` mide tiempos, pero resume: no deja ver
el reparto ni los parciales, que son dos de las evidencias que pide la guia
(Fase 3). Este script reutiliza las mismas funciones del coordinador -no
reimplementa el protocolo- y solo imprime lo que pasa por dentro.

Se ejecuta en nodo0, junto al coordinador:

    python3 scripts/evidencia_particion.py 2 500000
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from coordinator import (WORKERS, contar_primos_local, particionar,  # noqa: E402
                         solicitar_a_worker)


def main(inicio, fin):
    print(f"Intervalo solicitado: [{inicio}, {fin}]")
    print(f"Workers configurados: {WORKERS}\n")

    partes = particionar(inicio, fin, len(WORKERS))
    print("-- Particion estatica calculada por el coordinador")
    cubierto = 0
    for direccion, (a, b) in zip(WORKERS, partes):
        print(f"   {direccion[0]}:{direccion[1]}  ->  [{a}, {b}]  ({b - a + 1} numeros)")
        cubierto += b - a + 1
    print(f"   suma de las particiones: {cubierto} numeros "
          f"(intervalo completo: {fin - inicio + 1}) -> "
          f"{'sin huecos ni solapamientos' if cubierto == fin - inicio + 1 else 'INCONSISTENTE'}\n")

    print("-- Resultados parciales, uno por worker")
    total = 0
    for direccion, (a, b) in zip(WORKERS, partes):
        r = solicitar_a_worker(direccion, a, b)
        if not r["ok"]:
            print(f"   {direccion} -> FALLO: {r['motivo']}")
            return 1
        print(f"   worker '{r['worker']}' en {direccion[0]}:{direccion[1]}  "
              f"[{a}, {b}]  ->  {r['result']} primos  "
              f"(procesamiento: {r['processing_seconds']:.4f} s)")
        total += r["result"]

    print(f"\n-- Resultado final agregado por el coordinador: {total} primos")
    referencia = contar_primos_local(inicio, fin)
    print(f"-- Conteo secuencial en nodo0, para contrastar:  {referencia} primos")
    print("-- Coinciden" if total == referencia else "-- NO COINCIDEN: revisar")
    return 0 if total == referencia else 1


if __name__ == "__main__":
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    b = int(sys.argv[2]) if len(sys.argv) > 2 else 500_000
    sys.exit(main(a, b))
