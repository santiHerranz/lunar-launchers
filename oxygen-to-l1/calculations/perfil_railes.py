"""
Perfil del terreno a lo largo de los dos raíles de L1, para el medallón del juego (codigo/juego).

Rehace el encaje de cada raíl sobre la fila del SLDEM2015 guardada en lola/ con las mismas
funciones que lo eligieron, y comprueba que sale la misma obra:
  plano:  2,75°N 14,25°W, horizontal (sitio_lunar.py 100 l1 -> sitio_l1.json, el primero)
  ladera: 0,0° 84,92°W, a 30° (sitio_l1_directo.py -> sitio_l1_directo.json)

Guarda en perfil_railes.json, para cada raíl, el terreno cada píxel (~59 m) desde 4,2 km antes
de la boca hasta 3,2 km después, en horizontal, con la cota del raíl en la boca.

Uso: python perfil_railes.py
"""
import os, json, math
import numpy as np
from constantes import KM_POR_GRADO_M
import sitio_lunar as S
import sitio_l1_directo as D
import rampa_lunar as RL

ANTES_M, DESPUES_M = 4200.0, 3200.0


def perfil(z, lon_min, lon, lat, elev, L_acel, L_freno, horizontal):
    """horizontal: las longitudes del raíl ya son horizontales (sitio_lunar, elev 0) o van a lo
    largo de la recta y hay que proyectarlas (sitio_l1_directo)."""
    dx = KM_POR_GRADO_M * 1e3 / S.PPD * math.cos(math.radians(lat))
    i = int(round((lon - lon_min) * S.PPD - 0.5))
    c = 1.0 if horizontal else math.cos(math.radians(elev))
    n_a, n_f = int(L_acel * c / dx), int(L_freno * c / dx)
    seg = z[i - n_a:i + n_f]
    x = (np.arange(i - n_a, i + n_f) - i) * dx
    enc = S.encajar(seg, x, elev)
    k0, k1 = int(ANTES_M / dx), int(DESPUES_M / dx)
    zs = z[i - k0:i + k1 + 1]
    return dict(lat=lat, lon=lon, elev=elev, L_acel_m=L_acel, L_freno_m=L_freno, dx_m=dx,
                x0_m=-k0 * dx, z_m=[round(float(v), 1) for v in zs], **enc)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    ra = RL.rampa(500.0, 100.0, v=2328.2)
    plano = json.load(open("sitio_l1.json", encoding="utf-8"))["mejores"][0]
    ladera = next(r for r in json.load(open("sitio_l1_directo.json", encoding="utf-8"))["con_trayectoria"]
                  if r["lat"] == 0.0 and abs(r["lon"] + 84.92) < 0.01 and r["tilt"] == 30.0)
    out = {
        "plano": perfil(S.filas_lat(plano["lat"]), S.LON_MIN, plano["lon"], plano["lat"], 0.0,
                        ra["L_km"] * 1e3, ra["L_freno_km"] * 1e3, True),
        "ladera": perfil(D.fila(ladera["lat"]), D.LON_MIN, ladera["lon"], ladera["lat"], 30.0,
                         D.L_ACEL, D.L_FRENO, False),
    }
    for k, ref in (("plano", plano), ("ladera", ladera)):
        o = out[k]
        print(f"{k}: boca a {o['z_boca']:+.1f} m (antes {ref['z_boca']:+.1f}), desmonte {o['desmonte_max']:.1f} m "
              f"({ref['desmonte_max']:.1f}), relleno {o['relleno_max']:.1f} m ({ref['relleno_max']:.1f}), "
              f"{o['volumen_Mm3']:.3f} Mm³ ({ref['volumen_Mm3']:.3f}); {len(o['z_m'])} puntos cada {o['dx_m']:.1f} m")
    json.dump(out, open("perfil_railes.json", "w", encoding="utf-8"), ensure_ascii=False)
