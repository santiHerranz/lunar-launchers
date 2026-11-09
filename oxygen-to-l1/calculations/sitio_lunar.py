"""
Emplazamiento de la rampa lunar sobre el relieve real.

Datos: mapa combinado LOLA + Kaguya TC (SLDEM2015), 512 px/°, ~59 m, ±60° de
latitud, de USGS Astrogeology. Es un GeoTIFF de 22 GB guardado por filas
completas este-oeste; como la rampa tira hacia el este, cada fila es justo un
perfil a lo largo del tiro. Solo se descargan unas pocas filas por latitud
(lectura por rangos HTTP) y se guardan en lola/ para no repetir.

Para cada latitud, longitud de boca y elevación del raíl:
  1. Raíl recto (aceleración + frenado de la cuna) encajado en el terreno: se
     elige la cota que minimiza el movimiento de tierras; se miden el desmonte
     máximo, el terraplén o pilar máximo y el volumen.
  2. Despeje: la cápsula sale a v0 con la elevación del raíl y sube despacio
     (hipérbola lunar). Se mide la altura mínima sobre el terreno en los 400 km
     siguientes.
  3. Coste en velocidad: v0 que pide la transferencia en esa longitud y
     elevación (de transferencia_barrido.json).

Aproximaciones: a latitud no nula, la trayectoria hacia el este se aparta del
paralelo unos kilómetros en 400 km; se usa el mismo perfil (media de 3 filas).

Uso:
  python sitio_lunar.py [A_G]
"""
import os, sys, json, math
import numpy as np
from constantes import R_M, MU_M, KM_POR_GRADO_M
import rampa_lunar as RL

URL = "/vsicurl/https://planetarymaps.usgs.gov/mosaic/LolaKaguya_Topo/Lunar_LRO_LOLAKaguya_DEMmerge_60N60S_512ppd.tif"
PPD = 512
LATS = np.arange(-3.0, 3.001, 0.25)
LON_MIN, LON_MAX = -85.0, 20.0           # se lee la fila entera; esto es lo que se guarda
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lola")
ANCHO_RAIL = 12.0                        # m, para el volumen de tierras
DESPEJE_KM = 400.0
ELEVS = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0)
X_DESPEJE0 = 1500.0                     # m; antes, la cápsula va sobre el tramo de frenado
DESPEJE_MIN, OBRA_MAX = 50.0, 100.0


def filas_lat(lat):
    """Perfil medio (3 filas, ±59 m) a la latitud dada, en metros sobre 1737,4 km."""
    os.makedirs(CACHE, exist_ok=True)
    fn = os.path.join(CACHE, f"fila_{lat:+.2f}.npy")
    if os.path.exists(fn):
        return np.load(fn)
    import rasterio
    from rasterio.windows import Window
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MAX_RETRY="4",
                      GDAL_HTTP_RETRY_DELAY="2"):
        with rasterio.open(URL) as d:
            fila0 = int(round((60.0 - lat) * PPD))
            c0 = int((LON_MIN + 180.0) * PPD); c1 = int((LON_MAX + 180.0) * PPD)
            z = d.read(1, window=Window(c0, fila0 - 1, c1 - c0, 3)).astype(np.float32)
            z = np.where(z == d.nodata, np.nan, z) * d.scales[0] + d.offsets[0]
    perfil = np.nanmean(z, axis=0)
    np.save(fn, perfil)
    return perfil


def altura_vuelo(x, v0, elev, z0):
    """Altura sobre el radio de referencia de la cápsula a una distancia x [m] por la
    superficie desde la boca (cónica lunar, sin Tierra: vale para los primeros minutos)."""
    r0 = R_M + z0
    e = math.radians(elev)
    h = r0 * v0 * math.cos(e)
    p = h * h / MU_M
    eps = 0.5 * v0 * v0 - MU_M / r0
    ec = math.sqrt(1 + 2 * eps * h * h / MU_M**2)
    nu0 = math.acos(max(-1.0, min(1.0, (p / r0 - 1) / ec)))
    if e < 0:
        nu0 = -nu0
    th = x / R_M
    return p / (1 + ec * np.cos(nu0 + th)) - R_M


# dos destinos: "leo" (transferencia.py, tiro al este) y "l1" (l1_transferencia.py, tiro al este)
MODOS = {"leo": dict(tabla="transferencia_barrido.json", lon=(-80.0, -2.0), v=2521.2, salida="sitio_lunar.json"),
         "l1": dict(tabla="l1_barrido.json", lon=(-40.0, 6.0), v=2328.2, salida="sitio_l1.json")}


def v0_tabla(modo="leo", clave="v0"):
    d = json.load(open(MODOS[modo]["tabla"], encoding="utf-8"))
    filas = d["filas"] if isinstance(d, dict) else d
    tab = {}
    for f in filas:
        if f["az"] == 90.0 and clave in f:
            tab.setdefault(f["elev"], []).append((f["lon"], f[clave]))
    return {e: (np.array([a for a, _ in sorted(v)]), np.array([b for _, b in sorted(v)])) for e, v in tab.items() if len(v) > 1}


def v0_de(tab, lon, elev):
    els = sorted(tab)
    vals = []
    for e in els:
        lo, vv = tab[e]
        vals.append(np.interp(lon, lo, vv, left=np.nan, right=np.nan))
    return float(np.interp(elev, els, vals))


def encajar(z, x, elev):
    """Mejor cota del raíl recto con pendiente elev sobre el perfil z(x) (x hacia el este,
    0 = boca). Devuelve desmonte y relleno máximos, volumen y cota de boca."""
    linea = x * math.tan(math.radians(elev))
    dz = z - linea
    c = np.median(dz)                         # minimiza la suma de |terreno - raíl|
    res = dz - c                              # >0: el terreno queda por encima (desmonte)
    dx = abs(x[1] - x[0])
    return dict(desmonte_max=float(res.max()), relleno_max=float(-res.min()),
                volumen_Mm3=float(np.abs(res).sum() * dx * ANCHO_RAIL / 1e6),
                z_boca=float(c + 0.0))


def estudiar(a_g=100.0, m_cap=500.0, modo="leo"):
    tab = v0_tabla(modo)
    tab_ll = v0_tabla(modo, "v_llegada") if modo == "l1" else None
    lon_a, lon_b = MODOS[modo]["lon"]
    ra = RL.rampa(m_cap, a_g, v=MODOS[modo]["v"])
    L_acel, L_freno = ra["L_km"] * 1e3, ra["L_freno_km"] * 1e3
    res = []
    for lat in LATS:
        z = filas_lat(lat)
        dxm = KM_POR_GRADO_M * 1e3 / PPD * math.cos(math.radians(lat))
        lon_px = LON_MIN + (np.arange(z.size) + 0.5) / PPD
        n_acel = int(L_acel / dxm); n_freno = int(L_freno / dxm)
        n_desp = int(DESPEJE_KM * 1e3 / dxm)
        paso = max(1, int(1000 / dxm))        # bocas cada ~1 km
        for i in range(n_acel, z.size - n_desp, paso):
            lon = lon_px[i]
            if lon < lon_a or lon > lon_b:
                continue
            for elev in ELEVS:
                v0 = v0_de(tab, lon, elev)
                if not np.isfinite(v0):
                    continue
                # el raíl: aceleración (detrás de la boca) y frenado de la cuna (delante,
                # en la misma recta, que también tiene que encajar)
                seg = slice(i - n_acel, i + n_freno)
                x = (np.arange(seg.start, seg.stop) - i) * dxm
                zz = z[seg]
                if np.isnan(zz).any():
                    continue
                enc = encajar(zz, x, elev)
                # despeje desde la boca (el frenado va por debajo de la trayectoria)
                i0 = int(X_DESPEJE0 / dxm)
                xs = np.arange(i0, n_desp) * dxm
                zt = z[i + i0:i + n_desp]
                hv = altura_vuelo(xs, v0, elev, enc["z_boca"])
                desp = hv - zt
                k = int(np.nanargmin(desp))
                extra = {"v_llegada": v0_de(tab_ll, lon, elev)} if tab_ll else {}
                res.append(dict(lat=float(lat), lon=float(lon), elev=elev, v0=v0, **extra, **enc,
                                despeje_min=float(desp[k]), despeje_x_km=float(xs[k] / 1e3)))
    return ra, res


if __name__ == "__main__":
    a_g = float(sys.argv[1]) if len(sys.argv) > 1 else 100.0
    modo = sys.argv[2] if len(sys.argv) > 2 else "leo"
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    ra, res = estudiar(a_g, modo=modo)
    print(f"raíl de {ra['L_km']:.2f} km + frenado {ra['L_freno_km']:.2f} km ({a_g:.0f} g)")
    # válidos: despeje de 50 m desde 1,5 km, desmonte y relleno de 100 m como máximo
    ok = [r for r in res if r["despeje_min"] > DESPEJE_MIN and r["desmonte_max"] < OBRA_MAX and r["relleno_max"] < OBRA_MAX]
    print(f"{len(res)} combinaciones, {len(ok)} válidas")
    vmin = min(r["v0"] for r in res)
    amin = min((r["v_llegada"] for r in res if "v_llegada" in r and np.isfinite(r["v_llegada"])), default=0.0)
    for r in ok:
        # coste: energía de más por la v0 (en m/s equivalentes) + obra (1 Mm³ ~ 10 m/s). Hacia L1
        # pesa sobre todo la velocidad de llegada, que frena el propelente de la cápsula; la v0 de
        # más solo cuesta electricidad: cuenta una décima parte
        if modo == "l1":
            r["coste"] = (r["v_llegada"] - amin) + 0.1 * (r["v0"] - vmin) + 10 * r["volumen_Mm3"]
        else:
            r["coste"] = (r["v0"] - vmin) + 10 * r["volumen_Mm3"]
    ok = [r for r in ok if np.isfinite(r["coste"])]
    ok.sort(key=lambda r: r["coste"])
    vistos = []
    for r in ok:
        if any(abs(r["lat"] - s["lat"]) < 0.6 and abs(r["lon"] - s["lon"]) < 1.5 for s in vistos):
            continue
        vistos.append(r)
        if len(vistos) >= 12:
            break
    for r in vistos:
        print(f"  {r['lat']:+.2f}° {r['lon']:+7.2f}°  raíl a {r['elev']:>4.1f}°  v0 {r['v0']:.1f} m/s  "
              f"desmonte {r['desmonte_max']:.0f} m, relleno {r['relleno_max']:.0f} m, {r['volumen_Mm3']:.2f} Mm³  "
              f"despeje {r['despeje_min']:.0f} m a {r['despeje_x_km']:.0f} km  boca a {r['z_boca']:+.0f} m"
              + (f"  llegada a L1 {r['v_llegada']:.0f} m/s" if "v_llegada" in r else ""))
    # por elevación: cuántos sitios valen
    for e in ELEVS:
        n = sum(1 for r in ok if r["elev"] == e)
        print(f"  elevación {e:>4.1f}°: {n} bocas válidas")
    json.dump({"a_g": a_g, "rampa": ra, "mejores": vistos,
               "por_elev": {str(e): sum(1 for r in ok if r["elev"] == e) for e in ELEVS},
               "validas_por_lat": {f"{la:+.2f}": sum(1 for r in ok if r["lat"] == la) for la in LATS}}, open(MODOS[modo]["salida"], "w", encoding="utf-8"), ensure_ascii=False)
