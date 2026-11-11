"""Captura la consola de cada VM pidiendosela a QEMU por QMP (screendump).

Es mas fiable que fotografiar ventanas del escritorio: toma el framebuffer de
la VM, siempre completo, sin ventanas ajenas encima y sin depender de que el
usuario no mueva nada mientras corre.

    python capturar_consolas.py ../evidencias/01_tres_vms_simultaneas.png

Requiere que las VMs esten corriendo con -qmp tcp:127.0.0.1:590N (lo hace
arrancar_nodos.ps1) y, en el anfitrion, Pillow para unir las tres imagenes.
"""
import json
import socket
import sys
import tempfile
from pathlib import Path

NODOS = [("nodo0", 5900), ("nodo1", 5901), ("nodo2", 5902)]


def qmp(puerto, comando):
    with socket.create_connection(("127.0.0.1", puerto), timeout=10) as s:
        s.settimeout(10)
        archivo = s.makefile("rwb")
        archivo.readline()                       # saludo QMP
        archivo.write(b'{"execute":"qmp_capabilities"}\n')
        archivo.flush()
        archivo.readline()
        archivo.write((json.dumps(comando) + "\n").encode())
        archivo.flush()
        while True:
            linea = archivo.readline()
            if not linea:
                raise RuntimeError("QMP cerro la conexion sin responder")
            respuesta = json.loads(linea)
            if "event" in respuesta:              # eventos asincronos: ignorar
                continue
            if "error" in respuesta:
                raise RuntimeError(f"QMP: {respuesta['error']}")
            return respuesta


def capturar(nodo, puerto, destino):
    qmp(puerto, {"execute": "screendump", "arguments": {"filename": str(destino)}})
    if not destino.exists() or destino.stat().st_size == 0:
        raise RuntimeError(f"{nodo}: screendump no produjo imagen")
    return destino


def main(salida):
    salida = Path(salida).resolve()
    temporal = Path(tempfile.mkdtemp(prefix="consolas_"))
    partes = []
    for nodo, puerto in NODOS:
        ruta = capturar(nodo, puerto, temporal / f"{nodo}.ppm")
        print(f"{nodo}: consola capturada ({ruta.stat().st_size} bytes)")
        partes.append((nodo, ruta))

    from PIL import Image, ImageDraw
    imagenes = [(nodo, Image.open(r).convert("RGB")) for nodo, r in partes]
    margen, titulo = 12, 26
    ancho = sum(i.width for _, i in imagenes) + margen * (len(imagenes) + 1)
    alto = max(i.height for _, i in imagenes) + titulo + margen * 2
    lienzo = Image.new("RGB", (ancho, alto), (24, 24, 24))
    pincel = ImageDraw.Draw(lienzo)
    x = margen
    for nodo, imagen in imagenes:
        pincel.text((x, margen // 2), f"{nodo}  (consola de la VM)", fill=(230, 230, 230))
        lienzo.paste(imagen, (x, titulo + margen // 2))
        x += imagen.width + margen
    salida.parent.mkdir(parents=True, exist_ok=True)
    lienzo.save(salida)
    print(f"Imagen combinada: {salida} ({lienzo.width}x{lienzo.height})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../evidencias/01_tres_vms_simultaneas.png")
