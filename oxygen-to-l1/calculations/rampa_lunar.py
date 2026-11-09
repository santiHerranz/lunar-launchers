"""
Rampa lunar: un motor lineal recto en superficie, sin aire, que lanza la cápsula
dentro de una cuna (sabot) reutilizable. La cuna se frena en un tramo final del
mismo raíl y su energía se recupera en parte.

Para cada masa de cápsula y aceleración: longitud, tiempo, fuerza, potencia de
pico, energía por disparo, tramo de frenado de la cuna y, con la cadencia,
potencia media, toneladas al año y la planta solar con o sin almacenamiento para
la noche lunar.

Uso:
  python rampa_lunar.py [V_BOCA] [ELEV_GRADOS]
"""
import sys, json, math
from constantes import G0, G_M

V_BOCA = 2521.2              # m/s, de transferencia.py (sitio ~53°W, tiro al este, gamma_EI -6°)
ELEV = 0.0                   # inclinación del raíl sobre la horizontal [°]
F_CUNA = 0.30                # masa de la cuna / masa de la cápsula
ETA = 0.80                   # red -> energía cinética (motor lineal síncrono + electrónica)
ETA_REGEN = 0.60             # energía recuperada al frenar la cuna
A_FRENO_G = 300.0            # frenado de la cuna vacía [g]
DIA_LUNAR_H = 29.53 * 24 / 2 # horas de sol (y de noche) en el ecuador
W_SOLAR_M2 = 1361 * 0.30 * 0.8   # paneles al 30 %, factor de coseno medio y pérdidas
BAT_WH_KG = 250.0            # almacenamiento a nivel de sistema


def rampa(m_cap, a_g, v=V_BOCA, elev=ELEV):
    a = a_g * G0
    m = m_cap * (1 + F_CUNA)
    gs = G_M * math.sin(math.radians(elev))           # la gravedad frena en un raíl inclinado
    L = v * v / (2 * (a - gs))
    t = v / (a - gs)
    E_cin = 0.5 * m * v * v
    E_pot = m * gs * L
    E_red = (E_cin + E_pot) / ETA - ETA_REGEN * 0.5 * (m_cap * F_CUNA) * v * v
    L_freno = v * v / (2 * A_FRENO_G * G0)
    return dict(m_cap=m_cap, a_g=a_g, v=v, elev=elev, m_total=m, L_km=L / 1e3, t_s=t,
                L_freno_km=L_freno / 1e3, L_total_km=(L + L_freno) / 1e3,
                F_kN=m * a / 1e3, P_pico_MW=m * a * v / ETA / 1e6,
                E_cin_MWh=E_cin / 3.6e9, E_red_MWh=E_red / 3.6e9,
                E_por_kg_MJ=E_red / m_cap / 1e6,
                altura_rampa_m=L * math.sin(math.radians(elev)))


def planta(E_red_MWh, disparos_h, nocturno=True):
    """Planta solar en el ecuador lunar. nocturno: dispara también de noche con baterías."""
    P_med = E_red_MWh * disparos_h                    # MW medios mientras dispara
    if nocturno:
        P_dia = 2 * P_med                             # de día carga lo de la noche
        E_noche = P_med * DIA_LUNAR_H                 # MWh
        bat_t = E_noche * 1e6 / BAT_WH_KG / 1e3
    else:
        P_dia, E_noche, bat_t = P_med, 0.0, 0.0
    area = P_dia * 1e6 / W_SOLAR_M2
    return dict(P_med_MW=P_med, P_paneles_MW=P_dia, area_km2=area / 1e6,
                E_noche_MWh=E_noche, baterias_t=bat_t)


if __name__ == "__main__":
    v = float(sys.argv[1]) if len(sys.argv) > 1 else V_BOCA
    el = float(sys.argv[2]) if len(sys.argv) > 2 else ELEV
    filas = []
    print(f"boca a {v:.1f} m/s, raíl a {el:.1f}°, cuna {F_CUNA:.0%} de la cápsula, rendimiento {ETA:.0%}")
    print(f"{'cápsula':>8} {'acel':>6} {'raíl':>8} {'t':>6} {'fuerza':>8} {'P pico':>8} {'E red':>8} {'MJ/kg':>6} {'freno':>6}")
    for m in (100, 250, 500, 1000):
        for ag in (10, 20, 30, 50, 100, 200, 500, 1000):
            r = rampa(m, ag, v, el)
            filas.append(r)
            print(f"{m:>6} kg {ag:>4} g {r['L_km']:>6.2f} km {r['t_s']:>5.1f}s {r['F_kN']:>6.0f} kN "
                  f"{r['P_pico_MW']:>6.0f} MW {r['E_red_MWh']:>6.2f} MWh {r['E_por_kg_MJ']:>5.2f} {r['L_freno_km']:>5.2f}")
    # cadencia y planta para el caso de referencia y un intervalo de cadencias
    ref = rampa(500, 100, v, el)
    cad = []
    print("\nCADENCIA (cápsula de 500 kg a 100 g):")
    for n in (1, 2, 6, 12):
        for noct in (False, True):
            p = planta(ref["E_red_MWh"], n, noct)
            t_anio = 500 * n * 24 * 365.25 / 1e3 * (1.0 if noct else 0.5)
            p.update(disparos_h=n, nocturno=noct, t_anio=t_anio)
            cad.append(p)
            print(f"  {n:>2}/h {'día y noche' if noct else 'solo de día':<12} {p['P_med_MW']:>6.1f} MW medios, "
                  f"{p['area_km2']:.3f} km² de paneles, {p['baterias_t']:>7.0f} t de baterías, {t_anio:>7.0f} t/año de cápsulas")
    json.dump({"v": v, "elev": el, "F_CUNA": F_CUNA, "ETA": ETA, "filas": filas, "ref": ref, "cadencia": cad},
              open("rampa_lunar.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
