"""
Repostar en L1 de la Tierra y la Luna para ir a Marte.

1. Delta-v con cónicas (sin la Luna en la salida, sin pérdidas):
   - LEO (400 km) -> L1, en dos impulsos: perigeo y llegada a L1 igualando su velocidad.
   - L1 -> salida hacia Marte con un sobrevuelo propulsado de la Tierra: en L1 se anula casi
     toda la velocidad (cae hacia la Tierra), y en el perigeo (200 km) se enciende hasta la
     energía de escape C3 que pide la ventana.
   - LEO -> salida hacia Marte directa, para comparar.
   Contraste: el estudio de ULA y SpaceWorks (2012) da 1.770 m/s desde L1 para C3 = 28,2 km²/s²
   (230 en L1, 230 en un sobrevuelo lunar, 1.310 en el perigeo).
2. Una nave de la clase Starship (cifras públicas aproximadas: 1.200 t de propelente, 120 t en
   seco, Isp de vacío 380 s, mezcla O/F 3,6 -> 78 % de oxígeno): cuánta carga lleva hacia Marte
   con los tanques llenos en LEO o en L1, y cuánto oxígeno lunar consume cada misión.

Uso: python marte.py
"""
import json, math
from constantes import MU_E, R_E, G0

R_L1 = 326380.9e3                    # l1_transferencia.py
W_L = math.sqrt((MU_E + 4.9028e12) / 384400e3**3)   # giro del sistema Tierra-Luna
V_L1 = W_L * R_L1                    # velocidad de L1 respecto a la Tierra
R_LEO = R_E + 400e3
R_PER = R_E + 200e3


def vis(r, a): return math.sqrt(MU_E * (2 / r - 1 / a))


def leo_a_l1():
    a = (R_LEO + R_L1) / 2
    return (vis(R_LEO, a) - math.sqrt(MU_E / R_LEO)) + (V_L1 - vis(R_L1, a))


def l1_a_marte(c3):
    a = (R_L1 + R_PER) / 2
    dv1 = V_L1 - vis(R_L1, a)                        # frenar en L1 para caer al perigeo
    v_per = vis(R_PER, a)
    dv2 = math.sqrt(c3 * 1e6 + 2 * MU_E / R_PER) - v_per
    return dv1, dv2


def leo_a_marte(c3):
    return math.sqrt(c3 * 1e6 + 2 * MU_E / R_LEO) - math.sqrt(MU_E / R_LEO)


# nave de la clase Starship
PROP, SECA, ISP, F_OX = 1200e3, 120e3, 380.0, 0.78


CARGA = 100e3                         # carga útil hacia Marte
VE = ISP * G0
DV_TOTAL = VE * math.log((SECA + CARGA + PROP) / (SECA + CARGA))   # con los tanques llenos


def prop_para(dv, seca):
    """Propelente que gasta una nave de masa final `seca` para dar dv."""
    return seca * (math.exp(dv / VE) - 1)


if __name__ == "__main__":
    dv_l1 = leo_a_l1()
    out = {"leo_a_l1": dv_l1, "V_L1": V_L1, "dv_tanques_llenos": DV_TOTAL, "casos": []}
    print(f"LEO 400 km -> L1: {dv_l1:.0f} m/s;  nave llena con {CARGA / 1e3:.0f} t de carga: {DV_TOTAL:.0f} m/s en total")
    # A: llenar en LEO con propelente de la Tierra y salir a Marte desde LEO
    # B: subir de LEO a L1 con propelente de la Tierra, llenar en L1 (oxígeno lunar + metano subido
    #    por un petrolero desde LEO) y salir a Marte desde L1
    met = PROP * (1 - F_OX)
    petrolero = prop_para(dv_l1, SECA + met)          # el petrolero sube el metano a L1 (y vuelve aerofrenando)
    subir = prop_para(dv_l1, SECA + CARGA)            # la nave sube de LEO a L1 casi vacía
    print(f"{'C3':>5}  {'desde L1':>8}  {'desde LEO':>9}  {'le quedan desde L1':>18}  {'le quedan desde LEO':>19}")
    for c3 in (8.9, 12.0, 16.0, 20.0, 28.2):
        d1, d2 = l1_a_marte(c3)
        dl = leo_a_marte(c3)
        out["casos"].append(dict(c3=c3, l1_frenar=d1, l1_perigeo=d2, l1_total=d1 + d2, leo_total=dl,
                                 resto_l1=DV_TOTAL - (d1 + d2), resto_leo=DV_TOTAL - dl))
        print(f"{c3:>5.1f}  {d1 + d2:>6.0f} m/s  {dl:>7.0f} m/s  {DV_TOTAL - d1 - d2:>15.0f} m/s  {DV_TOTAL - dl:>16.0f} m/s")
    tierra_A = PROP
    tierra_B = subir + met + petrolero
    out.update(oxigeno_lunar_t=PROP * F_OX / 1e3, metano_t=met / 1e3, subir_a_l1_t=subir / 1e3, petrolero_t=petrolero / 1e3,
               propelente_tierra_A_t=tierra_A / 1e3, propelente_tierra_B_t=tierra_B / 1e3)
    print(f"\nPropelente subido de la Tierra por misión (nave llena al salir hacia Marte):")
    print(f"  A, llenando en LEO:  {tierra_A / 1e3:.0f} t")
    print(f"  B, llenando en L1:   {tierra_B / 1e3:.0f} t  = {subir / 1e3:.0f} t para subir la nave a L1 + {met / 1e3:.0f} t de metano + {petrolero / 1e3:.0f} t que gasta el petrolero que lo sube")
    print(f"  y además {PROP * F_OX / 1e3:.0f} t de oxígeno lunar")
    json.dump(out, open("marte.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
