"""
Sitios para la ruta directa a L1: un raíl muy inclinado (20-45°) apoyado en una ladera que sube
hacia el este, cerca del limbo occidental.

1. Relieve: filas este-oeste del SLDEM2015 (LOLA + Kaguya, 59 m) entre 105°W y 45°W, de 5°S a
   5°N cada 0,5°, leídas por rangos HTTP y guardadas en lola/.
2. Para cada boca (cada ~240 m) y cada inclinación, el raíl recto de 2,76 km (más 0,92 km de
   frenado que siguen la misma recta, sobre pilares si hace falta) se encaja en el perfil; vale si
   el desmonte y el relleno no pasan de 150 m y el tiro despeja el suelo por 50 m en 400 km.
3. Con los mejores candidatos se calcula la trayectoria real a L1 (l1_transferencia.resolver, a la
   latitud del sitio): velocidad en la boca, velocidad que queda en L1 y tiempo de vuelo.

Uso: python sitio_l1_directo.py
"""
import os, json, math
import numpy as np
from constantes import KM_POR_GRADO_M
import sitio_lunar as S
import l1_transferencia as T

LON_MIN, LON_MAX = -105.0, -45.0
LATS = np.arange(-5.0, 5.001, 0.5)
L_ACEL, L_FRENO = 2762.0, 921.0
TILTS = (20.0, 25.0, 30.0, 35.0, 40.0, 45.0)
OBRA_MAX, DESPEJE_MIN = 150.0, 50.0
V0_APROX = 2328.0


def fila(lat):
    os.makedirs(S.CACHE, exist_ok=True)
    fn = os.path.join(S.CACHE, f"oeste_{lat:+.2f}.npy")
    if os.path.exists(fn):
        return np.load(fn)
    import rasterio
    from rasterio.windows import Window
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2"):
        with rasterio.open(S.URL) as d:
            r0 = int(round((60.0 - lat) * S.PPD))
            c0 = int((LON_MIN + 180.0) * S.PPD); c1 = int((LON_MAX + 180.0) * S.PPD)
            z = d.read(1, window=Window(c0, r0, c1 - c0, 1)).astype(np.float32)[0]
            z = np.where(z == d.nodata, np.nan, z) * d.scales[0] + d.offsets[0]
    np.save(fn, z)
    return z


def buscar():
    cand = []
    for lat in LATS:
        z = fila(lat)
        dx = KM_POR_GRADO_M * 1e3 / S.PPD * math.cos(math.radians(lat))
        lon_px = LON_MIN + (np.arange(z.size) + 0.5) / S.PPD
        n_desp = int(S.DESPEJE_KM * 1e3 / dx)
        for tilt in TILTS:
            c = math.cos(math.radians(tilt))
            n_a = int(L_ACEL * c / dx); n_f = int(L_FRENO * c / dx)
            for i in range(n_a, z.size - n_desp, 4):
                seg = z[i - n_a:i + n_f]
                if np.isnan(seg).any():
                    continue
                x = (np.arange(i - n_a, i + n_f) - i) * dx
                enc = S.encajar(seg, x, tilt)
                if enc["desmonte_max"] > OBRA_MAX or enc["relleno_max"] > OBRA_MAX:
                    continue
                i0 = n_f + 4
                xs = np.arange(i0, n_desp) * dx
                zt = z[i + i0:i + n_desp]
                desp = S.altura_vuelo(xs, V0_APROX, tilt, enc["z_boca"]) - zt
                if np.nanmin(desp) < DESPEJE_MIN:
                    continue
                cand.append(dict(lat=float(lat), lon=float(lon_px[i]), tilt=tilt, despeje_min=float(np.nanmin(desp)),
                                 subida_m=float(L_ACEL * math.sin(math.radians(tilt))), **enc))
        print(f"lat {lat:+.1f}: {len(cand)} candidatos acumulados", flush=True)
    return cand


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cand = buscar()
    # agrupar: el mejor (menos obra) de cada zona de 0,5° x 1°, y luego la trayectoria a L1
    cand.sort(key=lambda r: r["volumen_Mm3"])
    zonas = []
    for r in cand:
        if any(abs(r["lat"] - s["lat"]) < 0.5 and abs(r["lon"] - s["lon"]) < 1.0 for s in zonas):
            continue
        zonas.append(r)
    print(f"{len(cand)} encajes válidos en {len(zonas)} zonas; trayectorias de las 40 con menos obra")
    res = []
    for r in zonas[:40]:
        t = T.resolver(r["lon"], 90.0, r["tilt"], r["lat"])
        r.update({k: t[k] for k in ("v0", "v_llegada", "t_h") if k in t})
        if "fallo" in t: r["fallo"] = t["fallo"]
        res.append(r)
        print(f"  {r['lat']:+.1f}° {r['lon']:+7.2f}°  raíl a {r['tilt']:.0f}° (sube {r['subida_m']:.0f} m)  "
              f"obra {r['volumen_Mm3']:.2f} Mm³, desmonte {r['desmonte_max']:.0f} m, relleno {r['relleno_max']:.0f} m  -> "
              + (f"v0 {r['v0']:.1f} m/s, frena {r['v_llegada']:.0f} m/s en L1, {r['t_h']:.0f} h" if "v0" in r else r.get("fallo", "")), flush=True)
    json.dump({"candidatos": len(cand), "zonas": zonas[:200], "con_trayectoria": res},
              open("sitio_l1_directo.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
