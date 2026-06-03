# Caso 1 - Programación Entera Mixta: Cross Docking

Este repositorio contiene una propuesta elaborada para resolver el caso de programación de camiones en un centro de almacenamiento tipo cross docking.

## Objetivo

Minimizar el tiempo total de operación del almacén, conocido como **makespan**, considerando:

- Orden de atención de camiones de entrada.
- Orden de atención de camiones de salida.
- Asignación de productos entre camiones de entrada y salida.
- Tiempos de carga, descarga, traslado interno y cambio entre camiones.

## Estructura

```text
Caso1_CrossDock_GitHub/
│
├── README.md
├── requirements.txt
├── data/
│   └── TS5.txt
├── src/
│   └── solve_crossdock.py
└── ampl/
    ├── crossdock.mod
    └── TS5.dat
```

## Archivos principales

### `src/solve_crossdock.py`

Implementa el modelo MIP en Python usando `scipy.optimize.milp`.

El programa:

1. Lee automáticamente un archivo con formato TS5.
2. Valida que la oferta total de cada producto sea igual a la demanda total.
3. Construye el modelo de programación entera mixta.
4. Resuelve el problema.
5. Imprime el orden de camiones y el makespan.

## Cómo ejecutar

Desde la carpeta principal:

```bash
pip install -r requirements.txt
python src/solve_crossdock.py data/TS5.txt
```

## Resultado obtenido para TS5

Con el modelo implementado, para la instancia TS5 se obtuvo:

- **Makespan mínimo:** 1308 minutos
- **Orden de camiones de entrada:** 5 → 3 → 2 → 4 → 1
- **Orden de camiones de salida:** 3 → 2 → 1

## Formulación general

### Conjuntos

- `I`: conjunto de camiones de entrada.
- `J`: conjunto de camiones de salida.
- `K`: conjunto de productos.

### Parámetros

- `r[i,k]`: cantidad del producto `k` que llega en el camión de entrada `i`.
- `s[j,k]`: cantidad del producto `k` requerida por el camión de salida `j`.
- `p_in[i]`: tiempo total de descarga del camión de entrada `i`.
- `p_out[j]`: tiempo total de carga del camión de salida `j`.
- `t_trans`: tiempo de traslado interno.
- `t_cambio`: tiempo de cambio entre camiones.
- `M`: constante grande.

### Variables

- `x[i,j,k]`: cantidad del producto `k` transferida del camión de entrada `i` al camión de salida `j`.
- `v[i,j]`: variable binaria que indica si existe transferencia entre `i` y `j`.
- `A[i]`: inicio de descarga del camión de entrada `i`.
- `D[i]`: finalización de descarga del camión de entrada `i`.
- `S[j]`: inicio de carga del camión de salida `j`.
- `L[j]`: salida del camión de salida `j`.
- `y[i,i']`: binaria de precedencia entre camiones de entrada.
- `z[j,j']`: binaria de precedencia entre camiones de salida.
- `Cmax`: tiempo total de operación.

### Función objetivo

Minimizar el tiempo total de operación:

```text
min Cmax
```

## Nota

La formulación está construida para poder leer nuevas instancias con el mismo formato que TS5, sin tener que redigitar manualmente todos los datos.

## Aplicación Streamlit

Además de ejecutar el modelo desde consola, el repositorio incluye una interfaz web sencilla con Streamlit.

### Ejecutar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

La app permite:

- Cargar un archivo con formato TS5.
- Resolver la instancia usando el modelo MIP en Python.
- Mostrar el makespan mínimo.
- Mostrar el orden de camiones de entrada y salida.
- Mostrar las transferencias activas entre camiones.

### Publicar en Streamlit Community Cloud

1. Subir este proyecto a GitHub.
2. Entrar a Streamlit Community Cloud.
3. Crear una nueva app.
4. Seleccionar el repositorio.
5. En Main file path escribir:

```text
app.py
```

6. Presionar Deploy.
