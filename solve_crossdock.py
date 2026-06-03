"""
Modelo MIP para programación de camiones en cross docking.
Lee archivos tipo TS5 y resuelve con scipy.optimize.milp.

Uso:
    python src/solve_crossdock.py data/TS5.txt
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from itertools import combinations, product
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.optimize import linprog


@dataclass
class Instance:
    I: list[int]
    J: list[int]
    K: list[int]
    r: dict[tuple[int, int], float]
    s: dict[tuple[int, int], float]


def parse_ts5(path: str | Path) -> Instance:
    path = Path(path)
    I_count = J_count = K_count = None
    r: dict[tuple[int, int], float] = {}
    s: dict[tuple[int, int], float] = {}

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        tag = parts[0].lower()
        if tag == "i":
            I_count = int(parts[1])
        elif tag == "o":
            J_count = int(parts[1])
        elif tag == "n":
            K_count = int(parts[1])
        elif tag == "r":
            _, i, k, q = parts
            r[(int(i), int(k))] = float(q)
        elif tag == "s":
            _, j, k, q = parts
            s[(int(j), int(k))] = float(q)

    if I_count is None or J_count is None or K_count is None:
        raise ValueError("El archivo debe incluir líneas i, o y n.")

    I = list(range(1, I_count + 1))
    J = list(range(1, J_count + 1))
    K = list(range(1, K_count + 1))

    for i, k in product(I, K):
        r.setdefault((i, k), 0.0)
    for j, k in product(J, K):
        s.setdefault((j, k), 0.0)

    for k in K:
        rin = sum(r[(i, k)] for i in I)
        sout = sum(s[(j, k)] for j in J)
        if abs(rin - sout) > 1e-6:
            raise ValueError(f"Producto {k}: oferta {rin} no coincide con demanda {sout}.")

    return Instance(I, J, K, r, s)


class VarIndex:
    def __init__(self):
        self.name_to_idx: dict[tuple, int] = {}
        self.idx_to_name: list[tuple] = []

    def add(self, name: tuple) -> int:
        idx = len(self.idx_to_name)
        self.name_to_idx[name] = idx
        self.idx_to_name.append(name)
        return idx

    def __getitem__(self, name: tuple) -> int:
        return self.name_to_idx[name]

    def __len__(self):
        return len(self.idx_to_name)


def add_eq(rows, lbs, ubs, n, coefs: dict[int, float], rhs: float):
    row = np.zeros(n)
    for idx, val in coefs.items():
        row[idx] = val
    rows.append(row); lbs.append(rhs); ubs.append(rhs)


def add_le(rows, lbs, ubs, n, coefs: dict[int, float], rhs: float):
    row = np.zeros(n)
    for idx, val in coefs.items():
        row[idx] = val
    rows.append(row); lbs.append(-np.inf); ubs.append(rhs)


def solve(inst: Instance, transfer_time=5.0, change_time=10.0, time_limit=300, verbose=True):
    I, J, K = inst.I, inst.J, inst.K
    r, s = inst.r, inst.s
    p_in = {i: sum(r[(i, k)] for k in K) for i in I}
    p_out = {j: sum(s[(j, k)] for k in K) for j in J}
    total_units = sum(p_in.values())
    big_m = total_units + change_time * (len(I) + len(J)) + transfer_time + 1000

    V = VarIndex()
    V.add(("Cmax",))
    for i in I: V.add(("A", i))      # inicio descarga entrada
    for i in I: V.add(("D", i))      # fin descarga entrada
    for j in J: V.add(("S", j))      # inicio carga salida
    for j in J: V.add(("L", j))      # fin carga salida
    for i, j, k in product(I, J, K): V.add(("x", i, j, k))
    for i, j in product(I, J): V.add(("v", i, j))
    in_pairs = list(combinations(I, 2))
    out_pairs = list(combinations(J, 2))
    for i, ip in in_pairs: V.add(("y", i, ip))
    for j, jp in out_pairs: V.add(("z", j, jp))

    n = len(V)
    c = np.zeros(n); c[V[("Cmax",)]] = 1
    lb = np.zeros(n); ub = np.full(n, np.inf)
    integrality = np.zeros(n)

    for i, j in product(I, J):
        idx = V[("v", i, j)]; ub[idx] = 1; integrality[idx] = 1
    for i, ip in in_pairs:
        idx = V[("y", i, ip)]; ub[idx] = 1; integrality[idx] = 1
    for j, jp in out_pairs:
        idx = V[("z", j, jp)]; ub[idx] = 1; integrality[idx] = 1

    rows, lbs, ubs = [], [], []

    # D_i = A_i + p_i
    for i in I:
        add_eq(rows, lbs, ubs, n, {V[("D", i)]: 1, V[("A", i)]: -1}, p_in[i])
    # L_j = S_j + p_j
    for j in J:
        add_eq(rows, lbs, ubs, n, {V[("L", j)]: 1, V[("S", j)]: -1}, p_out[j])
    # Cmax >= L_j
    for j in J:
        add_le(rows, lbs, ubs, n, {V[("L", j)]: 1, V[("Cmax",)]: -1}, 0)
    # oferta entrada
    for i, k in product(I, K):
        add_eq(rows, lbs, ubs, n, {V[("x", i, j, k)]: 1 for j in J}, r[(i, k)])
    # demanda salida
    for j, k in product(J, K):
        add_eq(rows, lbs, ubs, n, {V[("x", i, j, k)]: 1 for i in I}, s[(j, k)])
    # x <= M_ijk v
    for i, j, k in product(I, J, K):
        cap = min(r[(i, k)], s[(j, k)])
        add_le(rows, lbs, ubs, n, {V[("x", i, j, k)]: 1, V[("v", i, j)]: -cap}, 0)
    # secuencia entrada para cada par i<ip
    for i, ip in in_pairs:
        y = V[("y", i, ip)]
        # A_ip >= D_i + cambio - M(1-y) -> D_i - A_ip + M y <= M-cambio
        add_le(rows, lbs, ubs, n, {V[("D", i)]: 1, V[("A", ip)]: -1, y: big_m}, big_m - change_time)
        # A_i >= D_ip + cambio - M y -> D_ip - A_i - M y <= -cambio
        add_le(rows, lbs, ubs, n, {V[("D", ip)]: 1, V[("A", i)]: -1, y: -big_m}, -change_time)
    # secuencia salida
    for j, jp in out_pairs:
        z = V[("z", j, jp)]
        add_le(rows, lbs, ubs, n, {V[("L", j)]: 1, V[("S", jp)]: -1, z: big_m}, big_m - change_time)
        add_le(rows, lbs, ubs, n, {V[("L", jp)]: 1, V[("S", j)]: -1, z: -big_m}, -change_time)
    # salida no puede irse antes de recibir productos desde entrada
    for i, j in product(I, J):
        # D_i + transfer - L_j <= M(1-v) -> D_i - L_j + M v <= M-transfer
        add_le(rows, lbs, ubs, n, {V[("D", i)]: 1, V[("L", j)]: -1, V[("v", i, j)]: big_m}, big_m - transfer_time)

    constraints = LinearConstraint(np.vstack(rows), np.array(lbs), np.array(ubs))
    result = milp(c=c, integrality=integrality, bounds=Bounds(lb, ub), constraints=constraints,
                  options={"time_limit": time_limit, "mip_rel_gap": 0})
    if not result.success:
        print("ADVERTENCIA: el solver no reportó optimalidad completa.")
        print(result.message)

    xval = result.x
    def val(name): return xval[V[name]]

    inbound_order = sorted(I, key=lambda i: val(("A", i)))
    outbound_order = sorted(J, key=lambda j: val(("S", j)))

    inbound_schedule = [
        {"Camión": i, "Inicio descarga": round(val(("A", i)), 2), "Fin descarga": round(val(("D", i)), 2), "Unidades": round(p_in[i], 0)}
        for i in inbound_order
    ]
    outbound_schedule = [
        {"Camión": j, "Inicio carga": round(val(("S", j)), 2), "Fin carga": round(val(("L", j)), 2), "Unidades": round(p_out[j], 0)}
        for j in outbound_order
    ]
    transfers = []
    for i, j in product(I, J):
        if val(("v", i, j)) > 0.5:
            transfers.append({"Entrada": i, "Salida": j})

    solution = {
        "makespan": float(val(("Cmax",))),
        "inbound_order": inbound_order,
        "outbound_order": outbound_order,
        "inbound_schedule": inbound_schedule,
        "outbound_schedule": outbound_schedule,
        "transfers": transfers,
        "success": bool(result.success),
        "message": result.message,
    }

    if verbose:
        print("=== RESULTADOS ===")
        print(f"Makespan mínimo: {solution['makespan']:.2f} minutos")
        print("Orden camiones de entrada:", inbound_order)
        for row in inbound_schedule:
            print(f"  Entrada {row['Camión']}: inicio {row['Inicio descarga']:.2f}, salida {row['Fin descarga']:.2f}, unidades {row['Unidades']:.0f}")
        print("Orden camiones de salida:", outbound_order)
        for row in outbound_schedule:
            print(f"  Salida {row['Camión']}: inicio {row['Inicio carga']:.2f}, salida {row['Fin carga']:.2f}, unidades {row['Unidades']:.0f}")
        print("\nTransferencias usadas v_ij = 1:")
        for row in transfers:
            print(f"  Entrada {row['Entrada']} -> Salida {row['Salida']}")

    return solution


if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "data/TS5.txt"
    instance = parse_ts5(file_path)
    solve(instance)
