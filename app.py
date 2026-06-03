"""
App Streamlit para resolver el caso de cross docking MIP.
Permite subir archivos tipo TS5 y visualizar el orden de camiones, makespan y transferencias.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.solve_crossdock import parse_ts5, solve

st.set_page_config(page_title="Cross Docking MIP - LogiFast CR", layout="wide")

st.title("Optimización Cross Docking - LogiFast CR")
st.caption("Modelo de Programación Entera Mixta para secuenciar camiones de entrada y salida.")

st.sidebar.header("Parámetros operativos")
transfer_time = st.sidebar.number_input("Tiempo de traslado interno por lote (min)", min_value=0.0, value=5.0, step=1.0)
change_time = st.sidebar.number_input("Tiempo de cambio entre camiones (min)", min_value=0.0, value=10.0, step=1.0)
time_limit = st.sidebar.number_input("Límite de tiempo del solver (seg)", min_value=10, value=300, step=10)

uploaded = st.file_uploader("Sube un archivo con formato TS5", type=["txt"])

use_example = st.checkbox("Usar archivo TS5 incluido en el repositorio", value=uploaded is None)

if uploaded is not None:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    tmp.write(uploaded.getvalue())
    tmp.close()
    file_path = Path(tmp.name)
elif use_example:
    file_path = Path("data/TS5.txt")
else:
    st.info("Sube un archivo TS5 o activa el ejemplo incluido.")
    st.stop()

try:
    inst = parse_ts5(file_path)
except Exception as exc:
    st.error(f"No se pudo leer el archivo: {exc}")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("Camiones de entrada", len(inst.I))
col2.metric("Camiones de salida", len(inst.J))
col3.metric("Tipos de producto", len(inst.K))

with st.expander("Ver datos de entrada"):
    inbound_rows = []
    for (i, k), q in inst.r.items():
        if q > 0:
            inbound_rows.append({"Camión entrada": i, "Producto": k, "Cantidad": q})
    outbound_rows = []
    for (j, k), q in inst.s.items():
        if q > 0:
            outbound_rows.append({"Camión salida": j, "Producto": k, "Cantidad": q})
    c1, c2 = st.columns(2)
    c1.subheader("Mercancía recibida")
    c1.dataframe(pd.DataFrame(inbound_rows), use_container_width=True, hide_index=True)
    c2.subheader("Pedidos de salida")
    c2.dataframe(pd.DataFrame(outbound_rows), use_container_width=True, hide_index=True)

if st.button("Resolver modelo", type="primary"):
    with st.spinner("Resolviendo el modelo MIP..."):
        try:
            solution = solve(inst, transfer_time=transfer_time, change_time=change_time, time_limit=time_limit, verbose=False)
        except Exception as exc:
            st.error(f"Error al resolver el modelo: {exc}")
            st.stop()

    st.success("Modelo resuelto")
    st.metric("Makespan mínimo", f"{solution['makespan']:.2f} min")

    st.subheader("Orden óptimo de camiones")
    c1, c2 = st.columns(2)
    c1.write("**Camiones de entrada**")
    c1.dataframe(pd.DataFrame(solution["inbound_schedule"]), use_container_width=True, hide_index=True)
    c2.write("**Camiones de salida**")
    c2.dataframe(pd.DataFrame(solution["outbound_schedule"]), use_container_width=True, hide_index=True)

    st.subheader("Transferencias entre camiones")
    transfers = pd.DataFrame(solution["transfers"])
    if transfers.empty:
        st.warning("No se encontraron transferencias activas.")
    else:
        st.dataframe(transfers, use_container_width=True, hide_index=True)

    st.subheader("Resumen para defensa")
    st.write(
        f"El orden óptimo de entrada es **{solution['inbound_order']}** y el orden óptimo de salida es "
        f"**{solution['outbound_order']}**. El tiempo mínimo total de operación del sistema es "
        f"**{solution['makespan']:.2f} minutos**."
    )
