# Investigacion teorica - Guia 2

Asignatura INFB6074, Infraestructura para Ciencia de Datos (UTEM, 2026-2).
Desarrollo de los fundamentos teoricos que sustentan los experimentos A, B, C
y D de esta guia. Las referencias numeradas corresponden a la lista de
"Referencias bibliograficas" del README raiz de `guia-2/`.

## 1. Ejecucion secuencial, paralela y distribuida

Un programa secuencial avanza mediante una unica unidad de ejecucion: cada
instruccion espera a que termine la anterior, y en cualquier instante solo
existe un punto activo de control. Esto es lo que ocurre, por ejemplo, al
recorrer un arreglo con un `for` en Python puro elemento por elemento: cada
iteracion depende de haber completado la anterior en el sentido de que
comparten el mismo hilo de control, aunque no haya una dependencia de datos
real entre ellas.

El paralelismo introduce varias unidades de ejecucion activas al mismo
tiempo, dentro de un mismo computador. Conviene distinguir dos formas,
siguiendo la clasificacion clasica de arquitecturas paralelas (Hwang,
Dongarra y Fox, 2013 [13]):

- **Paralelismo de datos**: la misma operacion se aplica simultaneamente a
  distintas particiones de un conjunto de datos. Es el caso del Experimento
  A: la transformacion (normalizar, elevar al cuadrado, raiz, suma) es
  identica para todos los elementos del arreglo; lo unico que cambia entre
  "hilos de trabajo" es el subconjunto de datos que procesan. NumPy explota
  esta forma de paralelismo a nivel vectorial/SIMD dentro de una sola
  instruccion de CPU, y `multiprocessing` la explota a nivel de proceso,
  repartiendo el arreglo en chunks (documentacion oficial de NumPy [9] y de
  `multiprocessing` [8]).
- **Paralelismo de tareas**: se ejecutan simultaneamente tareas que pueden
  ser distintas entre si y que no comparten necesariamente la misma
  secuencia de operaciones, solo la independencia entre ellas. Es el caso
  del Experimento B: cada lote de feature engineering es una tarea
  autocontenida; no hay una operacion unica que se "reparta", sino un
  conjunto de trabajos que se pueden ejecutar en cualquier orden o al mismo
  tiempo porque no dependen unos de otros.

Dentro del paralelismo local hay ademas una distincion importante entre
**multicore (hilos)** y **multiprocesamiento (procesos)**. Los hilos de un
mismo proceso comparten el mismo espacio de memoria, lo que hace que
compartir datos sea barato pero introduce la necesidad de sincronizacion
(evitar condiciones de carrera) y, en CPython especificamente, la limitacion
del *Global Interpreter Lock* (GIL): solo un hilo puede ejecutar bytecode de
Python a la vez, por lo que `ThreadPoolExecutor` no acelera trabajo
CPU-bound puro de Python, aunque si beneficia trabajo que libera el GIL
mientras espera (E/S, `time.sleep`, ciertas llamadas a C) (documentacion de
`concurrent.futures` [7]). Los procesos, en cambio, tienen memoria separada:
no hay condiciones de carrera sobre datos compartidos por defecto, pero
intercambiar datos entre procesos tiene un costo de serializacion y copia
(pickling) que no existe entre hilos. Esto se observa directamente en el
Experimento B: para cargas CPU-bound con lotes pequenos,
`ProcessPoolExecutor` puede terminar siendo mas lento que la ejecucion
secuencial, porque el costo fijo de arrancar procesos y transferir los
DataFrames supera el tiempo que toma procesar cada lote.

El paralelismo distribuido agrega un salto cualitativo adicional: las
unidades de ejecucion (nodos o procesos) no comparten memoria en absoluto, ni
siquiera la memoria fisica de la misma maquina, y colaboran exclusivamente
mediante paso de mensajes a traves de una red (Tanenbaum y van Steen [14]).
Esto introduce *overhead de comunicacion* que no existe en el paralelismo
local: latencia de red, serializacion de mensajes (en este trabajo, JSON),
posibilidad de fallas parciales (un nodo puede dejar de responder sin que
el resto del sistema se detenga), y la necesidad de un protocolo explicito
para solicitar trabajo y recibir resultados. El Experimento D es el unico de
los cuatro que es realmente distribuido en este sentido: coordinador y
workers son procesos en maquinas virtuales distintas, que no comparten
memoria y se comunican por sockets TCP.

Es importante no confundir "distribuido" con "usa un framework para datos
particionados". Dask (y de forma analoga PySpark) puede ejecutarse en modo
local, sobre un unico computador, usando hilos o procesos del propio
anfitrion como "workers" internos (documentacion de Dask [10]). En ese modo,
Dask organiza el calculo como un grafo de tareas sobre particiones de datos y
lo ejecuta con un *scheduler* local, pero sigue siendo, en terminos de
arquitectura fisica, paralelismo local: no hay nodos independientes
comunicandose por red, solo hilos/procesos de un mismo proceso Python
coordinados por el scheduler de Dask. Esta distincion es la razon por la que
el Experimento C, aunque usa Dask, se clasifica como "procesamiento
distribuido sobre datos particionados" en sentido logico/arquitectonico, pero
no como un clúster distribuido real; ese rol lo cumple exclusivamente el
Experimento D.

## 2. Arquitectura de clústeres

Un **clúster** es un conjunto de nodos computacionales coordinados que
trabajan hacia un objetivo comun, presentandose externamente (en mayor o
menor medida) como un unico sistema. Un **nodo** es cualquier unidad
computacional identificable dentro del clúster: puede ser una maquina
fisica, una maquina virtual, o incluso un contenedor, siempre que tenga
recursos de computo (CPU, memoria) y una direccion de red propia a traves de
la cual se le puede contactar.

Toda arquitectura de clúster debe resolver, de una forma u otra, cuatro
problemas:

- **Planificacion** (*scheduling*): decidir que trabajo se ejecuta, en que
  nodo y en que momento.
- **Distribucion de carga**: repartir el trabajo entre los nodos
  disponibles, idealmente de forma que ningun nodo quede ocioso mientras
  otro esta sobrecargado.
- **Particionamiento**: dividir los datos o el trabajo en unidades que
  puedan procesarse de forma independiente por distintos nodos.
- **Escalabilidad**: la capacidad del sistema de absorber mas carga
  agregando recursos, sin que el diseño tenga que rehacerse por completo.

El **modelo coordinador-worker** (tambien llamado maestro-trabajador o
*master-worker*) es una de las formas mas simples y extendidas de resolver
estos problemas. En este modelo, un nodo coordinador concentra las
decisiones de alto nivel: particiona el trabajo, asigna cada particion a un
worker, supervisa el avance (y la eventual falla) de cada worker, y agrega
los resultados parciales en un resultado final. Los nodos worker, por su
parte, no necesitan conocerse entre si ni coordinarse directamente: solo
necesitan saber como recibir una tarea del coordinador y como devolverle un
resultado. Esta simplicidad es precisamente lo que hace viable implementar
el modelo con herramientas basicas (sockets TCP y JSON) en el Experimento D,
sin requerir un framework de orquestacion.

## 3. Virtualizacion y QEMU

Una **maquina virtual (VM)** es un entorno de ejecucion aislado que emula un
computador completo (CPU, memoria, disco, dispositivos de red) sobre un
anfitrion fisico, de forma que el sistema operativo invitado "cree" estar
corriendo sobre hardware real dedicado. Cada VM tiene sus propios recursos
virtuales: numero de vCPUs, cantidad de RAM, uno o mas discos virtuales, y
una o mas interfaces de red virtuales, todos configurables de forma
independiente del hardware fisico subyacente.

**QEMU** es un emulador de maquinas que permite crear y ejecutar estas VMs
(documentacion oficial [1]). Entre sus parametros de invocacion mas
relevantes para este trabajo:

- `-m`: cantidad de memoria RAM asignada a la VM (en megabytes).
- `-smp`: numero de vCPUs (procesadores virtuales) asignados.
- `-drive file=...,format=qcow2`: disco virtual de la VM, en formato qcow2,
  un formato de disco que soporta asignacion dinamica de espacio (el archivo
  en disco crece segun el uso real, no segun el tamano nominal declarado) y
  snapshots.
- `-netdev` / `-device`: definen la red virtual de la VM y el adaptador de
  red emulado (en este trabajo, `e1000` sobre una red `user` tipo NAT;
  QEMU Project, Network emulation [2]).
- `-hostfwd`: dentro de una red `user`, reenvia un puerto del anfitrion hacia
  un puerto de la VM, permitiendo alcanzar servicios dentro de la VM desde
  el exterior sin necesitar una red puente real.

**Alpine Linux** se usa como sistema operativo invitado por ser una
distribucion minimalista (pensada originalmente para contenedores y sistemas
embebidos), lo que reduce drasticamente el tiempo de arranque y el consumo
de RAM de cada VM, factor relevante cuando se ejecutan 3 VMs simultaneamente
sobre el mismo anfitrion fisico (Alpine Linux, documentacion [3]).

## 4. Clúster virtual de 3 nodos

El clúster del Experimento D consiste en un anfitrion Windows, con
PowerShell como shell de control, ejecutando simultaneamente 3 VMs Alpine
mediante QEMU:

- **nodo0 (coordinador)**: particiona el trabajo, contacta a los workers,
  agrega resultados.
- **nodo1 (worker 1)** y **nodo2 (worker 2)**: reciben una particion del
  intervalo a calcular y devuelven su resultado parcial.

Cada VM tiene su propia CPU virtual, su propia RAM y su propio disco: no hay
recursos compartidos *a nivel logico* entre las VMs, aunque todas compiten
por el mismo CPU y la misma RAM fisicos del anfitrion (esto se retoma en la
seccion 10).

## 5. Redes virtuales en el clúster QEMU

El modo de red `user` de QEMU (el usado en este trabajo) implementa una red
NAT: cada VM recibe una direccion IP privada dentro de una subred virtual que
QEMU administra internamente, y el trafico saliente de la VM hacia el
exterior se traduce via NAT, de forma analoga a como un router domestico
traduce el trafico de una red local hacia Internet. Una consecuencia
importante de este modo es que **no existe, por defecto, una red Ethernet
compartida entre las VMs invitadas**: nodo1 no puede, en general, alcanzar
directamente a nodo2 por su IP interna, porque cada VM esta en su propia
subred NAT aislada administrada por su propia instancia de QEMU.

Esto tiene una implicancia de diseño directa para el Experimento D: toda la
comunicacion entre el coordinador y los workers pasa, necesariamente, a
traves del anfitrion, usando el mecanismo de reenvio de puertos (`hostfwd`).
Desde dentro de cualquier VM, `10.0.2.2` es la direccion que QEMU asigna por
convencion al anfitrion visto desde dentro de la red NAT de esa VM. Por eso,
cuando el coordinador (corriendo en nodo0) quiere contactar al worker de
nodo1, no se conecta a una IP "de nodo1" directamente: se conecta a
`10.0.2.2:9001`, es decir, al anfitrion, en el puerto que el anfitrion tiene
reenviado hacia el puerto 9000 interno de nodo1. El anfitrion actua, en la
practica, como el unico punto de paso de todo el trafico entre VMs.

La tabla de puertos usada en este trabajo:

| Nodo | Puerto host | Puerto VM | Servicio |
| --- | --- | --- | --- |
| nodo0 | 2220 | 22 | SSH coordinador |
| nodo1 | 2221 | 22 | SSH worker 1 |
| nodo2 | 2222 | 22 | SSH worker 2 |
| nodo1 | 9001 | 9000 | TCP worker 1 |
| nodo2 | 9002 | 9000 | TCP worker 2 |

## 6. SSH, SCP y SFTP

SSH (*Secure Shell*) provee acceso remoto cifrado a una terminal del sistema
invitado; en este trabajo se usa, a traves de los puertos reenviados, para
administrar cada VM (instalar paquetes, iniciar el servicio worker,
diagnosticar fallas). SCP (*Secure Copy*) reutiliza el mismo canal cifrado
de SSH para transferir archivos, y es el mecanismo usado para llevar
`worker.py` desde el anfitrion hasta cada VM worker:

```
ssh -p 2220 alumno@127.0.0.1
scp -P 2221 worker.py alumno@127.0.0.1:/home/alumno/
```

SFTP es un protocolo de transferencia de archivos equivalente a SCP en
cuanto a seguridad (tambien corre sobre SSH), pero con un modelo de sesion
mas rico (listar directorios, renombrar, reanudar transferencias); no se usa
de forma distinta a SCP en este trabajo, dado que solo se necesita copiar un
archivo por worker.

## 7. Sockets TCP y serializacion JSON

Un **socket TCP** es el extremo de una conexion orientada a flujo de bytes,
confiable y ordenada, entre dos procesos (posiblemente en maquinas
distintas). La API estandar de Python (`socket` [5], y `socketserver` [6]
para el lado servidor) expone esta primitiva directamente. Un punto
frecuentemente subestimado, y que este trabajo aborda explicitamente en el
protocolo del Experimento D, es que **TCP no preserva limites de mensaje**:
una sola llamada a `recv()` puede devolver menos bytes de los enviados, mas
de un mensaje concatenado, o un mensaje partido a la mitad; el *HOWTO* oficial
de sockets de Python lo señala como uno de los errores mas comunes al
programar con sockets [4]. Por eso el protocolo de este trabajo delimita
cada mensaje con un salto de linea (`\n`) y el lado receptor acumula bytes
hasta encontrar ese delimitador, en vez de asumir que una lectura trae el
mensaje completo.

JSON se usa como formato de serializacion por ser human-readable, tener
soporte nativo en la biblioteca estandar de Python (`json`), y ser
suficiente para la estructura de datos de este protocolo (un objeto plano
con un par de campos enteros o un string y un float). La solicitud
`{"start": 2, "end": 500000}` y la respuesta
`{"worker": "nodo1", "result": 41538, "processing_seconds": 0.18}` son
ejemplos directos de este formato aplicados al caso de conteo de primos.

Para que el coordinador pueda contactar a ambos workers sin que la espera
de uno bloquee el contacto con el otro, se usa
`concurrent.futures.ThreadPoolExecutor` [7]: cada solicitud a un worker es
una tarea enviada al pool de hilos, y el coordinador recoge las respuestas a
medida que llegan (`as_completed`). Esto es paralelismo de E/S pura (esperar
respuestas de red), un caso donde los hilos de Python si aportan, pese al
GIL, porque la espera de red libera el GIL mientras el socket aguarda datos.

## 8. Distribucion de tareas y particionamiento

El particionamiento puede ser **estatico** (decidido antes de iniciar la
ejecucion, sin reajustarse segun el avance real de cada worker) o
**dinamico** (decidido o reajustado en tiempo de ejecucion, por ejemplo
asignando nuevo trabajo a quien termine primero). Este trabajo usa
particionamiento estatico: el coordinador calcula de antemano, con una
funcion determinista (`particionar()`), los limites exactos que le
corresponden a cada worker.

El ejemplo de referencia de la guia -- contar primos entre 2 y 500.000,
repartido en 2-250.000 para un worker y 250.001-500.000 para el otro --
ilustra el requisito central de cualquier particionamiento correcto: cubrir
el intervalo completo sin huecos (ningun numero del intervalo original debe
quedar sin asignar a ningun worker) y sin solapamientos (ningun numero debe
contarse dos veces). La implementacion de `particionar()` en
`coordinator.py` generaliza esto a un numero arbitrario de partes y a
intervalos de cualquier tamano, incluyendo el caso en que el tamano del
intervalo no es divisible exactamente entre el numero de partes (el resto se
reparte dando una unidad adicional a las primeras particiones).

## 9. Medicion de rendimiento: tiempo, speedup, eficiencia

El **tiempo de ejecucion** medido en este trabajo es siempre una duracion de
pared (*wall-clock*), obtenida con `time.perf_counter()`, que es el
cronometro recomendado por la documentacion de Python para medir intervalos
cortos con la mayor resolucion disponible, precisamente porque no esta
sujeto a ajustes del reloj del sistema.

El **speedup** con p unidades de paralelismo se define como:

```
S(p) = T_secuencial / T_distribuido(p)
```

y la **eficiencia** como:

```
E(p) = S(p) / p
```

Una eficiencia cercana a 1 indica que agregar unidades de paralelismo se
traduce casi integramente en una reduccion proporcional del tiempo; una
eficiencia que cae rapidamente con p indica que el overhead (comunicacion,
coordinacion, contencion de recursos) esta consumiendo una fraccion
creciente del beneficio teorico.

Es crucial que "p" signifique cosas distintas segun el experimento, y este
trabajo lo respeta explicitamente en cada caso:

- En A y B, p es el numero de procesos o hilos efectivamente usados por el
  propio script (controlado directamente por `Pool(processes=p)` o
  `max_workers=p`). Para la via NumPy vectorizada del Experimento A no se
  reporta p ni eficiencia cuantitativa, porque el numero de hilos BLAS
  internos no esta garantizado ni expuesto de forma confiable en todos los
  entornos.
- En C, p no tiene sentido como "numero de particiones": las particiones de
  Dask no son unidades de paralelismo por si mismas, sino la granularidad
  del trabajo; el paralelismo real lo dan los workers de computo del
  scheduler local de Dask.
- En D, p es el numero de workers remotos (0 para el escenario secuencial
  que no usa red, 1 o 2 para los escenarios distribuidos), con el escenario
  secuencial como referencia de speedup y eficiencia iguales a 1 por
  definicion.

La **ley de Amdahl** acota el speedup maximo alcanzable cuando una fraccion
f del trabajo es inherentemente secuencial (no paralelizable):

```
S(p) <= 1 / (f + (1 - f) / p)
```

Esta ley explica por que, en el Experimento D, agregar un segundo worker no
necesariamente duplica el speedup del primero: parte del tiempo total (la
preparacion de la solicitud, la agregacion final de resultados) no se
paraleliza por mas workers que se agreguen, y ese residuo fijo limita el
speedup maximo alcanzable sin importar cuantos workers se sumen.

## 10. Escalabilidad vertical y horizontal

La **escalabilidad vertical** consiste en dar mas recursos a un nodo ya
existente (mas vCPUs, mas RAM). La **escalabilidad horizontal** consiste en
agregar mas nodos al sistema, manteniendo (o no) los recursos de cada nodo
individual. En el Experimento D, pasar de 1 a 2 workers remotos es, en
apariencia, un caso de escalabilidad horizontal: se agrega un nodo mas al
clúster. Sin embargo, es importante señalar su limitacion especifica en este
contexto: como las 3 VMs corren sobre el mismo anfitrion fisico, agregar un
worker no agrega capacidad fisica real de CPU o memoria al sistema global,
solo reparte el trabajo entre procesos que de todas formas compiten por los
mismos nucleos fisicos subyacentes. Por eso este trabajo caracteriza ese
escalamiento como "horizontal virtual": tiene la forma logica de escalar
horizontalmente (mas nodos, cada uno con su propia direccion y su propio
sistema operativo), pero no el respaldo fisico que tendria en un clúster
real de varios computadores.

## 11. Disponibilidad, fallas y verificacion funcional

Un nodo se considera **disponible** si responde dentro de un tiempo
razonable a una solicitud. El **timeout** es el mecanismo que impide que el
sistema completo quede bloqueado indefinidamente esperando una respuesta que
nunca llegara (por ejemplo, porque el proceso worker se detuvo o la VM se
apago); sin timeout, una sola falla de un nodo podria inutilizar al
coordinador completo. En este trabajo, cada solicitud a un worker tiene un
timeout explicito (`TIMEOUT_SEGUNDOS` en `coordinator.py`), y una falla de
conexion o de timeout se traduce en un resultado marcado como incompleto
para ese escenario, nunca en un bloqueo indefinido ni en un resultado parcial
presentado como correcto.

La **verificacion funcional real** va mas alla de solo comprobar que un nodo
"responde": consiste en enviarle una tarea de resultado conocido y validar
que la respuesta sea exactamente la esperada. En este trabajo, esa prueba es
contar primos entre 2 y 10 inclusive, cuyo resultado correcto es exactamente
4 (los primos 2, 3, 5 y 7); la funcion `prueba_correctitud()` del
coordinador aplica esta verificacion tanto de forma local como contra cada
escenario remoto antes de ejecutar la bateria completa de comparacion.

## Referencias

1. QEMU Project. *QEMU system emulation and invocation*. https://www.qemu.org/docs/master/system/
2. QEMU Project. *Network emulation*. https://www.qemu.org/docs/master/system/devices/net.html
3. Alpine Linux. *Alpine Linux documentation*. https://docs.alpinelinux.org/
4. Python Software Foundation. *Socket programming HOWTO*. https://docs.python.org/3/howto/sockets.html
5. Python Software Foundation. *socket*. https://docs.python.org/3/library/socket.html
6. Python Software Foundation. *socketserver*. https://docs.python.org/3/library/socketserver.html
7. Python Software Foundation. *concurrent.futures*. https://docs.python.org/3/library/concurrent.futures.html
8. Python Software Foundation. *multiprocessing*. https://docs.python.org/3/library/multiprocessing.html
9. NumPy Developers. *NumPy documentation*. https://numpy.org/doc/
10. Dask. *Dask documentation*. https://docs.dask.org/
11. Apache Spark. *Apache Spark documentation*. https://spark.apache.org/docs/
12. NVIDIA. *CUDA Zone*. https://developer.nvidia.com/cuda-zone
13. Hwang, K., Dongarra, J. y Fox, G. (2013). *Distributed and Cloud Computing*. Morgan Kaufmann.
14. Tanenbaum, A. S. y van Steen, M. *Distributed Systems*. https://www.distributed-systems.net/
15. Kleppmann, M. (2017). *Designing Data-Intensive Applications*. O'Reilly Media.
16. Material complementario de la asignatura: 8.2 - Ejemplo de Cluster con QEMU.
