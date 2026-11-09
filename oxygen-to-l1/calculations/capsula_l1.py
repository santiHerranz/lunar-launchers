"""
La cápsula de oxígeno líquido que va a L1.

Sin escudo térmico ni aerocaptura: un depósito esférico de aluminio-litio con aislamiento
multicapa, un motor bipropelente almacenable para la corrección en ruta y para frenar al llegar
a L1, y lo necesario para acoplarse al depósito. El tanque tiene que aguantar 100 g en el raíl:
la columna de oxígeno líquido aprieta el fondo con rho·a·h.

Uso: python capsula_l1.py [V_LLEGADA] [HORAS] [A_G]
"""
import sys, json, math
from constantes import G0

RHO_LOX = 1141.0        # kg/m^3
H_VAP = 213e3           # J/kg
ULLAGE = 1.05
SIGMA = 300e6           # Pa admisible del Al-Li 2195 a temperatura criogénica, con margen
T_MIN = 2.0e-3          # espesor mínimo práctico [m]
RHO_AL = 2700.0
F_ACCES = 1.3           # soldaduras, bridas y soportes sobre el casco
MLI = 1.5               # kg/m^2
Q_FUGA = 1.5            # W/m^2 a través del aislamiento en el espacio
ISP = 310.0
F_SECO_PROP = 0.15
M_FIJO = 15.0           # aviónica, baliza, acoplamiento, baterías
DV_TCM, DV_ACOPLE, MARGEN = 30.0, 20.0, 1.10


def cerrar(m_lox, v_llegada=160.0, horas=330.0, a_g=100.0):
    dv = (v_llegada + DV_TCM + DV_ACOPLE) * MARGEN
    m = m_lox * 1.4
    for _ in range(80):
        vol = m_lox / RHO_LOX * ULLAGE
        r = (3 * vol / (4 * math.pi)) ** (1 / 3)
        area = 4 * math.pi * r * r
        p = RHO_LOX * a_g * G0 * 2 * r + 0.3e6           # presión en el fondo durante el disparo
        t = max(T_MIN, p * r / (2 * SIGMA))
        m_tanque = area * t * RHO_AL * F_ACCES
        m_mli = area * MLI
        evap = Q_FUGA * area * horas * 3600 / H_VAP        # se ventea durante el viaje
        m_prop = m * (1 - math.exp(-dv / (ISP * G0)))
        m_estr = (0.07 + 0.0003 * a_g) * m
        m_new = m_lox + evap + m_tanque + m_mli + m_prop * (1 + F_SECO_PROP) + m_estr + M_FIJO
        if abs(m_new - m) < 0.01:
            break
        m = m_new
    return dict(m_total=m, m_lox_llega=m_lox, evaporado=evap, fraccion_util=m_lox / m, D_tanque=2 * r, p_fondo_MPa=p / 1e6,
                espesor_mm=t * 1e3, m_tanque=m_tanque, m_mli=m_mli, m_prop=m_prop, m_estr=m_estr, dv=dv, v_llegada=v_llegada, horas=horas)


def para_total(m_total, **kw):
    """Oxígeno que llega a L1 en una cápsula de masa total dada."""
    lo, hi = 1.0, m_total
    for _ in range(60):
        mid = (lo + hi) / 2
        if cerrar(mid, **kw)["m_total"] > m_total: hi = mid
        else: lo = mid
    return cerrar(lo, **kw)


if __name__ == "__main__":
    v = float(sys.argv[1]) if len(sys.argv) > 1 else 160.0
    h = float(sys.argv[2]) if len(sys.argv) > 2 else 330.0
    ag = float(sys.argv[3]) if len(sys.argv) > 3 else 100.0
    filas = []
    print(f"llegada a L1 a {v:.0f} m/s, {h:.0f} h de viaje, disparo a {ag:.0f} g")
    for mt in (100.0, 250.0, 500.0, 1000.0):
        r = para_total(mt, v_llegada=v, horas=h, a_g=ag)
        filas.append(r)
        print(f"cápsula {mt:>5.0f} kg -> {r['m_lox_llega']:>5.0f} kg de oxígeno en L1 ({r['fraccion_util']:.0%}); tanque Ø {r['D_tanque']:.2f} m, "
              f"{r['espesor_mm']:.1f} mm, {r['m_tanque']:.0f} kg; fondo a {r['p_fondo_MPa']:.2f} MPa; aislante {r['m_mli']:.0f} kg; "
              f"evaporado {r['evaporado']:.1f} kg; propelente {r['m_prop']:.0f} kg para {r['dv']:.0f} m/s; estructura {r['m_estr']:.0f} kg")
    json.dump(filas, open("capsula_l1.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
