"""
Del raíl lunar a L1 de la Tierra y la Luna, en el problema restringido de tres cuerpos (CR3BP).

Marco que gira con la Luna, unidades adimensionales: distancia Tierra-Luna = 1, movimiento
medio = 1. La Tierra está en (-mu, 0), la Luna en (1-mu, 0) y L1 entre las dos, a unos
58.000 km de la Luna. La Luna gira de forma síncrona, así que el sitio del raíl está quieto
en este marco y la velocidad de la boca es directamente la velocidad en el marco.

Coordenadas selenográficas IAU: longitud este positiva; el punto subterrestre es 0°, 0°.
En el marco giratorio, "arriba" en el punto subterrestre es -x y el este es -y.

El objetivo: cruzar el plano x = x_L1 justo por L1 (y = 0) yendo hacia la Tierra, con la
menor velocidad posible respecto a L1: esa velocidad es lo que hay que frenar al llegar.
La energía mínima la da la constante de Jacobi: v0_min = sqrt(2 Omega(sitio) - C_L1).

Uso:
  python l1_transferencia.py prueba
  python l1_transferencia.py caso LON AZ ELEV
  python l1_transferencia.py barrido
  python l1_transferencia.py sensibilidad LON AZ ELEV
"""
import sys, json, math, time
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from constantes import MU_E, MU_M, R_M

MU = MU_M / (MU_E + MU_M)
LU = 384400e3                                # m
NU = math.sqrt((MU_E + MU_M) / LU**3)        # rad/s
TU = 1 / NU                                  # s
VU = LU * NU                                 # m/s
RM = R_M / LU
XM = 1 - MU
HORA = 3600.0
RTOL, ATOL = 1e-11, 1e-13


def omega(x, y, z=0.0):
    r1 = math.sqrt((x + MU)**2 + y * y + z * z); r2 = math.sqrt((x - XM)**2 + y * y + z * z)
    return 0.5 * (x * x + y * y) + (1 - MU) / r1 + MU / r2


def f(t, s):
    x, y, z, vx, vy, vz = s
    r1 = ((x + MU)**2 + y * y + z * z) ** 1.5; r2 = ((x - XM)**2 + y * y + z * z) ** 1.5
    ax = x + 2 * vy - (1 - MU) * (x + MU) / r1 - MU * (x - XM) / r2
    ay = y - 2 * vx - (1 - MU) * y / r1 - MU * y / r2
    az = -(1 - MU) * z / r1 - MU * z / r2
    return [vx, vy, vz, ax, ay, az]


def l1():
    g = lambda x: x - (1 - MU) / (x + MU)**2 + MU / (x - XM)**2
    return brentq(g, 0.5, XM - 1e-3)


XL1 = l1()
CL1 = 2 * omega(XL1, 0.0)


def sitio(lon, lat=0.0):
    la, lo = math.radians(lat), math.radians(lon)
    up = np.array([-math.cos(la) * math.cos(lo), -math.cos(la) * math.sin(lo), math.sin(la)])
    este = np.cross([0, 0, 1.0], up); este /= np.linalg.norm(este)
    norte = np.cross(up, este)
    return up, este, norte


def estado0(v0, lon, az, elev, lat=0.0, h0=0.0):
    up, este, norte = sitio(lon, lat)
    a, e = math.radians(az), math.radians(elev)
    d = math.cos(e) * (math.sin(a) * este + math.cos(a) * norte) + math.sin(e) * up
    r = np.array([XM, 0, 0]) + (RM + h0 / LU) * up
    return np.concatenate([r, v0 / VU * d])


def v0_min(lon, lat=0.0):
    up, _, _ = sitio(lon, lat)
    r = np.array([XM, 0, 0]) + RM * up
    return math.sqrt(max(0.0, 2 * omega(*r) - CL1)) * VU


def volar(v0, lon, az, elev, lat=0.0, t_max_h=400.0):
    """Primer cruce del plano de L1 hacia la Tierra. Devuelve y del cruce (km), velocidad
    respecto a L1 (m/s), tiempo (h)."""
    s0 = estado0(v0, lon, az, elev, lat)

    def plano(t, s): return s[0] - XL1
    plano.terminal = True; plano.direction = -1

    def choque(t, s): return math.sqrt((s[0] - XM)**2 + s[1]**2 + s[2]**2) - RM * 0.999
    choque.terminal = True; choque.direction = -1

    def lejos(t, s): return math.sqrt((s[0] - XM)**2 + s[1]**2 + s[2]**2) - 0.6
    lejos.terminal = True; lejos.direction = 1

    sol = solve_ivp(f, (0, t_max_h * HORA / TU), s0, method="DOP853", rtol=RTOL, atol=ATOL,
                    events=[plano, choque, lejos])
    if len(sol.t_events[0]):
        s = sol.y_events[0][0]
        return {"y_km": s[1] * LU / 1e3, "z_km": s[2] * LU / 1e3, "v_llegada": float(np.linalg.norm(s[3:]) * VU),
                "vx": s[3] * VU, "vy": s[4] * VU, "t_h": sol.t_events[0][0] * TU / HORA}
    if len(sol.t_events[1]):
        return {"fallo": "cae a la Luna"}
    if len(sol.t_events[2]):
        return {"fallo": "se aleja"}
    return {"fallo": "no llega"}


def resolver(lon, az, elev, lat=0.0, paso=2.0):
    """v0 con la que el primer cruce del plano de L1 pasa justo por L1 (y = 0). Si hay
    varias, la de menor velocidad de llegada."""
    vm = v0_min(lon, lat)
    sols, prev = [], None
    for v in np.arange(math.floor(vm) + 0.5, vm + 260.0, paso):
        r = volar(v, lon, az, elev, lat)
        val = r.get("y_km")
        if prev is not None and val is not None and prev[1] is not None and prev[1] * val < 0 and abs(prev[1] - val) < 20000:
            try:
                vs = brentq(lambda q: volar(q, lon, az, elev, lat).get("y_km", float("nan")), prev[0], v, xtol=1e-6)
                rr = volar(vs, lon, az, elev, lat)
                if "y_km" in rr and abs(rr["y_km"]) < 1.0:
                    rr.update(v0=vs, v0_min=vm, lon=lon, az=az, elev=elev, lat=lat)
                    sols.append(rr)
            except ValueError:
                pass
        prev = (v, val)
    if not sols:
        return {"fallo": "sin solución", "v0_min": vm, "lon": lon, "az": az, "elev": elev}
    return min(sols, key=lambda s: s["v_llegada"])


def prueba():
    out = {"mu": MU, "x_L1": XL1, "L1_desde_Luna_km": (XM - XL1) * LU / 1e3, "L1_desde_Tierra_km": (XL1 + MU) * LU / 1e3,
           "C_L1": CL1, "VU": VU, "TU_h": TU / HORA}
    # L1 es un equilibrio: un punto quieto en L1 sigue quieto unas horas (y se va: es inestable)
    s = [XL1, 0, 0, 0, 0, 0]
    sol = solve_ivp(f, (0, 48 * HORA / TU), s, method="DOP853", rtol=RTOL, atol=ATOL)
    out["deriva_48h_km"] = float(np.linalg.norm(sol.y[:3, -1] - np.array(s[:3])) * LU / 1e3)
    # la constante de Jacobi se conserva en un vuelo cualquiera
    s0 = estado0(2350.0, 0.0, 90.0, 20.0)
    J = lambda s: 2 * omega(*s[:3]) - (s[3]**2 + s[4]**2 + s[5]**2)
    sol = solve_ivp(f, (0, 100 * HORA / TU), s0, method="DOP853", rtol=RTOL, atol=ATOL)
    out["jacobi_deriva_rel"] = float(max(abs(J(sol.y[:, k]) - J(s0)) for k in range(sol.y.shape[1])) / abs(J(s0)))
    out["v0_min_subterrestre"] = v0_min(0.0)
    out["v0_min_limbo"] = v0_min(90.0)
    return out


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "prueba"
    t0 = time.time()
    if modo == "prueba":
        print(json.dumps(prueba(), indent=1, ensure_ascii=False))
    elif modo == "caso":
        lon, az, elev = map(float, sys.argv[2:5])
        print(json.dumps(resolver(lon, az, elev), indent=1, ensure_ascii=False))
    elif modo == "sensibilidad":
        # cuánto se aparta de L1 el cruce por cada error en la boca, y cuánto corrige un impulso en ruta
        lon, az, elev = map(float, sys.argv[2:5])
        lat = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
        b = resolver(lon, az, elev, lat)
        def cruce(dv=0.0, de=0.0, da=0.0):
            r = volar(b["v0"] + dv, lon, az + da, elev + de, lat)
            return r.get("y_km", float("nan")), r.get("z_km", 0.0), r.get("v_llegada", float("nan"))
        y0, _, va0 = cruce()
        sens = {}
        for nm, kw, h in [("km por m/s de v0", {"dv": 0.01}, 0.01), ("km por grado de elevación", {"de": 0.001}, 0.001), ("km por grado de azimut", {"da": 0.001}, 0.001)]:
            y1, z1, _ = cruce(**kw)
            sens[nm] = math.hypot(y1 - y0, z1) / h
        # corrección a lo largo de la velocidad a las 24 y 72 h
        s0 = estado0(b["v0"], lon, az, elev, lat)
        for th in (12.0, 24.0, 72.0):
            sol = solve_ivp(f, (0, th * HORA / TU), s0, method="DOP853", rtol=RTOL, atol=ATOL)
            s1 = sol.y[:, -1].copy(); u = s1[3:] / np.linalg.norm(s1[3:])
            def plano(t, s): return s[0] - XL1
            plano.terminal = True; plano.direction = -1
            ys = []
            for dv in (0.0, 0.01):
                s2 = s1.copy(); s2[3:] += dv / VU * u
                so = solve_ivp(f, (0, 500 * HORA / TU), s2, method="DOP853", rtol=RTOL, atol=ATOL, events=[plano])
                ys.append(so.y_events[0][0][1] * LU / 1e3 if len(so.t_events[0]) else float("nan"))
            sens[f"km por m/s de corrección a las {th:.0f} h"] = abs(ys[1] - ys[0]) / 0.01
        b["sens"] = sens
        print(json.dumps(b, indent=1, ensure_ascii=False))
        json.dump(b, open("l1_sensibilidad.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    elif modo == "trayectoria":
        # el camino completo de un caso, en km respecto a la Luna (marco giratorio), para la lámina
        lon, az, elev = map(float, sys.argv[2:5])
        r = resolver(lon, az, elev)
        s0 = estado0(r["v0"], lon, az, elev)
        sol = solve_ivp(f, (0, r["t_h"] * HORA / TU), s0, method="DOP853", rtol=RTOL, atol=ATOL, dense_output=True)
        ts = np.linspace(0, r["t_h"] * HORA / TU, 400)
        pts = [[(sol.sol(t)[0] - XM) * LU / 1e3, sol.sol(t)[1] * LU / 1e3, t * TU / HORA] for t in ts]
        r["camino_km_h"] = pts
        r["L1_km"] = [(XL1 - XM) * LU / 1e3, 0.0]
        json.dump(r, open("l1_trayectoria.json", "w", encoding="utf-8"), ensure_ascii=False)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        print(f"v0 {r['v0']:.1f} m/s, llegada {r['v_llegada']:.0f} m/s, {r['t_h']:.0f} h; x {min(xs):.0f}..{max(xs):.0f} km, y {min(ys):.0f}..{max(ys):.0f} km")
    elif modo == "directos":
        # rutas directas (sin vuelta a la Luna): raíl inclinado, al este, longitudes del oeste
        filas = []
        for elev in (10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0):
            for lon in range(-90, -19, 4):
                r = resolver(float(lon), 90.0, elev)
                filas.append(r)
                print(elev, lon, round(r["v0"], 1) if "v0" in r else r["fallo"], round(r["v_llegada"], 1) if "v_llegada" in r else "",
                      round(r["t_h"], 1) if "t_h" in r else "", flush=True)
        json.dump(filas, open("l1_directos.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    elif modo == "barrido":
        filas = []
        for elev in (0.0, 5.0, 10.0, 20.0, 30.0, 45.0):
            for az in (90.0, 270.0):
                for lon in range(-80, 81, 8):
                    r = resolver(float(lon), az, elev)
                    filas.append(r)
                    print(elev, az, lon, round(r["v0"], 1) if "v0" in r else r["fallo"],
                          round(r["v_llegada"], 1) if "v_llegada" in r else "", round(r["t_h"], 1) if "t_h" in r else "", flush=True)
        json.dump(filas, open("l1_barrido.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"[{time.time() - t0:.1f} s]")
