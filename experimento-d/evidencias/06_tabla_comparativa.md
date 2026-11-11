# Experimento D -- tabla comparativa (clúster QEMU real)

Fuente: `evidencias/resultados_d.csv` (45 filas, 5 tamaños x 3 escenarios x 3 repeticiones).

| Intervalo | Escenario | Primos | Tiempo total medio (s) | Residual medio (s) | Speedup | Eficiencia |
|---|---|---|---|---|---|---|
| 2..10.000 | A_secuencial | 1229 | 0.000082 | 0.000000 | 1.000 | 1.000 |
| 2..10.000 | B_un_worker | 1229 | 0.002225 | 0.002088 | 0.048 | 0.048 |
| 2..10.000 | C_dos_workers | 1229 | 0.004273 | 0.004183 | 0.021 | 0.010 |
| 2..100.000 | A_secuencial | 9592 | 0.000554 | 0.000000 | 1.000 | 1.000 |
| 2..100.000 | B_un_worker | 9592 | 0.003412 | 0.002779 | 0.189 | 0.189 |
| 2..100.000 | C_dos_workers | 9592 | 0.003633 | 0.003207 | 0.156 | 0.078 |
| 2..500.000 | A_secuencial | 41538 | 0.003637 | 0.000000 | 1.000 | 1.000 |
| 2..500.000 | B_un_worker | 41538 | 0.006998 | 0.004179 | 0.563 | 0.563 |
| 2..500.000 | C_dos_workers | 41538 | 0.007992 | 0.005262 | 0.469 | 0.234 |
| 2..2.000.000 | A_secuencial | 148933 | 0.015178 | 0.000000 | 1.000 | 1.000 |
| 2..2.000.000 | B_un_worker | 148933 | 0.024130 | 0.003883 | 0.649 | 0.649 |
| 2..2.000.000 | C_dos_workers | 148933 | 0.018112 | 0.005013 | 0.859 | 0.430 |
| 2..10.000.000 | A_secuencial | 664579 | 0.083291 | 0.000000 | 1.000 | 1.000 |
| 2..10.000.000 | B_un_worker | 664579 | 0.079851 | 0.005060 | 1.079 | 1.079 |
| 2..10.000.000 | C_dos_workers | 664579 | 0.074629 | 0.004218 | 1.197 | 0.598 |

El residual es `T_total - max(T_procesamiento_worker)`: agrupa preparación, envío/recepción por red y agregación.
