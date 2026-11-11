# Experimento A - Paralelismo de datos y vectorizacion

Compara tres formas de aplicar la misma transformacion numerica (normalizar,
elevar al cuadrado, raiz cuadrada, suma) sobre arreglos de 5 tamanos distintos
(10^4 a 2x10^7 elementos): Python puro, NumPy vectorizado y `multiprocessing`
con particionamiento en chunks.

## Ejecucion

```powershell
cd experimento-a
python src/experimento_a.py
```

No requiere entrada manual. Corre en aproximadamente 30-40 segundos en el
equipo de desarrollo (AMD Ryzen, 16 nucleos logicos; ajustar `TAMANOS` en el
script si el equipo de ejecucion es mas lento).

## Que genera

- `evidencias/resultados_a.csv`: una fila por (tamano, metodo, p, repeticion)
  con tiempo, resultado agregado, speedup y eficiencia.
- `evidencias/tiempo_vs_tamano.png`: tiempo promedio por metodo vs tamano
  (escala log-log).
- `evidencias/speedup_vs_p.png`: speedup de `multiprocessing` respecto de
  NumPy vectorizado, para cada tamano grande, en funcion de p.

El script verifica con `np.allclose` que los 3 metodos producen el mismo
resultado agregado antes de registrar las mediciones (si no coincidieran, el
`assert` interrumpe la ejecucion).

## Notas sobre el parametro p

Para la via NumPy vectorizado no se identifica un "p" controlado por este
script: NumPy puede delegar en hilos BLAS internos, pero el numero exacto no
esta expuesto de forma confiable en todos los entornos, asi que ese metodo se
reporta con p = "no_identificable" y no se le calcula eficiencia cuantitativa,
siguiendo la seccion 2.9 del enunciado. Para `multiprocessing`, p es el
numero de procesos del `Pool`, que es directamente controlado por el script.

## Observaciones (completar tras revisar las evidencias generadas)

- Tamano a partir del cual `multiprocessing` supera a NumPy vectorizado: _(completar)_
- Tamano a partir del cual el overhead de crear procesos deja de pagarse: _(completar)_
- Comportamiento de Python puro para los dos tamanos mas grandes (se omite
  deliberadamente por tiempo prohibitivo; ver codigo): _(completar)_
