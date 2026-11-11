# Experimento B - Paralelismo a nivel de tareas

Procesa 24 lotes independientes de feature engineering (escalado, encoding
one-hot manual, features derivadas) sobre un DataFrame sintetico de ventas,
en 3 tamanos de lote (200, 1000, 5000 filas) y 2 tipos de carga: CPU-bound
(solo computo) e I/O-bound simulada (computo + `time.sleep` corto por lote).
Compara ejecucion secuencial, `ThreadPoolExecutor` y `ProcessPoolExecutor`
con 2, 4 y 8 workers.

## Ejecucion

```powershell
cd experimento-b
python src/experimento_b.py
```

No requiere entrada manual. Corre en aproximadamente 25-30 segundos.

Si `psutil` no esta instalado, el script lo detecta, avisa por consola y
sigue funcionando sin la columna de uso de CPU (instalar con
`pip install psutil` para incluirla).

## Que genera

- `evidencias/resultados_b.csv`: tiempo total y (si psutil esta disponible)
  uso de CPU por combinacion de tamano de lote, tipo de carga, modo de
  ejecucion y numero de workers.
- `evidencias/comparacion_b.png`: dos paneles (CPU-bound e I/O-bound) con el
  mejor tiempo logrado por cada modo, por tamano de lote.

## Observaciones (completar tras revisar las evidencias generadas)

- Para carga CPU-bound, `ThreadPoolExecutor` no deberia acelerar frente a
  secuencial (el GIL serializa el computo puro de Python/Pandas); confirmar
  con los numeros obtenidos: _(completar)_
- Para carga I/O-bound, el beneficio esperado de los hilos (la espera libera
  el GIL) frente a secuencial: _(completar)_
- Costo de arrancar un `ProcessPoolExecutor` (overhead de crear procesos)
  frente al tamano real del trabajo por lote, especialmente con lotes
  pequenos: _(completar)_
