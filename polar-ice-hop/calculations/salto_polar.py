"""
Salto polar: bloques de hielo lanzados por un raíl desde el polo sur de la Luna, en trayectoria
balística, para que caigan cerca del sitio del raíl de oxígeno (0,0°, 84,92°W, borde occidental
de la cara visible) y acumular allí agua.

Modelo: Luna esférica de dos cuerpos que gira (27,32 d sidéreos), sin atmósfera. El vuelo se
integra en un marco inercial y el punto de impacto se pasa al marco fijo a la Luna, así la
rotación (el sitio se mueve 4,6 m/s hacia el este) y el Coriolis salen solos. Para cada
elevación del raíl se resuelve (v0, acimut) que llevan el bloque al blanco. Luego: el raíl, la
cuna, la resistencia del hielo, la energética del impacto, el cráter y la sublimación en el sitio.

Uso:
  python salto_polar.py               # barrido de elevaciones y punto de diseño (30°, 100 g)
  python salto_polar.py ELEV G [M]    # otra elevación [°], aceleración [g] y masa del bloque [kg]
  python salto_polar.py camino        # el vuelo del punto de diseño cada 30 s, para la lámina (salto_polar_camino.json)
Deja salto_polar.json y salto_polar.log al lado.
"""
import sys, json, math
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import fsolve

# ---------------- Luna (SI; los mismos valores que lanzador_lunar/constantes.py) ----------------
MU = 4.9028e12                      # m^3/s^2
R = 1737.4e3                        # radio medio [m]
G = MU / R**2                       # 1,624 m/s^2
W = 2 * math.pi / (27.321661 * 86400)   # rotación sidérea [rad/s]
G0 = 9.80665

# ---------------- sitios ----------------
# salida: una cresta iluminada junto al cráter Shackleton, con el hielo de las sombras permanentes al lado
LANZA = dict(lat=-89.5, lon=0.0, h=1000.0)
# llegada: el llano al oeste del raíl de oxígeno (0,0°, 84,92°W); el perfil SLDEM baja allí a unos -1.500 m
BLANCO = dict(lat=0.0, lon=-84.92, h=-1500.0)

# ---------------- raíl y cuna (las convenciones de rampa_lunar.py) ----------------
F_CUNA = 0.30        # masa de la cuna / masa del bloque
ETA = 0.80           # rendimiento eléctrico del motor lineal
A_FRENO_G = 300.0    # frenado de la cuna vacía
ETA_REGEN = 0.60     # energía recuperada al frenar la cuna

# ---------------- hielo ----------------
RHO_HIELO = 920.0
SIGMA_HIELO = 8.0e6          # resistencia a compresión del hielo frío [Pa], conservadora (10-20 MPa a 100 K)
T_HIELO = 100.0              # temperatura del bloque al salir de la sombra [K]
C_HIELO = 1.8e3              # calor específico medio 100-273 K [J/kg K]
L_FUSION = 0.334e6           # J/kg
L_VAPOR = 2.26e6             # J/kg (del líquido; en vacío el agua hierve en cuanto funde)
RHO_REGOLITO = 1500.0


def xyz(lat, lon, h):
    la, lo = math.radians(lat), math.radians(lon)
    return (R + h) * np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])


def local(lat, lon):
    """Vectores unitarios arriba, este, norte en el sitio."""
    la, lo = math.radians(lat), math.radians(lon)
    up = np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])
    este = np.array([-math.sin(lo), math.cos(lo), 0.0])
    norte = np.cross(up, este)
    return up, este, norte


def f(t, s):
    r = s[:3]; d = np.linalg.norm(r)
    return [*s[3:], *(-MU * r / d**3)]


def vuelo(v0, az_deg, elev_deg, salida=LANZA, h_fin=None):
    """Integra el vuelo en el marco inercial (el marco fijo a la Luna coincide con él en t = 0).
    Devuelve la solución y el impacto en coordenadas fijas a la Luna."""
    h_fin = BLANCO["h"] if h_fin is None else h_fin
    up, este, norte = local(salida["lat"], salida["lon"])
    r0 = xyz(salida["lat"], salida["lon"], salida["h"])
    a, e = math.radians(az_deg), math.radians(elev_deg)
    d = math.cos(e) * (math.sin(a) * este + math.cos(a) * norte) + math.sin(e) * up
    v_rot = np.cross([0, 0, W], r0)              # el sitio ya se mueve con la Luna
    s0 = np.concatenate([r0, v0 * d + v_rot])

    def suelo(t, s): return np.linalg.norm(s[:3]) - (R + h_fin)
    suelo.terminal = True; suelo.direction = -1
    sol = solve_ivp(f, (0, 4 * 3600), s0, method="DOP853", rtol=1e-10, atol=1e-6, events=[suelo], dense_output=True)
    if not len(sol.t_events[0]):
        return None
    t = sol.t_events[0][0]; s = sol.y_events[0][0]
    # al marco fijo a la Luna: girar -W t alrededor de z
    c, sn = math.cos(-W * t), math.sin(-W * t)
    Rz = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1]])
    r_fix = Rz @ s[:3]
    v_fix = Rz @ (s[3:] - np.cross([0, 0, W], s[:3]))     # velocidad respecto al suelo
    lat = math.degrees(math.asin(r_fix[2] / np.linalg.norm(r_fix)))
    lon = math.degrees(math.atan2(r_fix[1], r_fix[0]))
    rr = np.linalg.norm(sol.y[:3], axis=0)
    upi = r_fix / np.linalg.norm(r_fix)
    v_imp = np.linalg.norm(v_fix)
    ang_imp = math.degrees(math.asin(-float(np.dot(v_fix, upi)) / v_imp))
    return dict(t=t, lat=lat, lon=lon, v_imp=v_imp, ang_imp=ang_imp, h_max=float(rr.max()) - R, sol=sol)


def arco_km(lat1, lon1, lat2, lon2):
    """Distancia sobre la esfera [km]."""
    a1, b1, a2, b2 = map(math.radians, (lat1, lon1, lat2, lon2))
    c = math.sin(a1) * math.sin(a2) + math.cos(a1) * math.cos(a2) * math.cos(b2 - b1)
    return R * math.acos(max(-1.0, min(1.0, c))) / 1e3


def fallo_km(v0, az, elev):
    """Error de impacto frente al blanco: (a lo largo del meridiano del blanco, en latitud; transversal, en longitud) [km]."""
    r = vuelo(v0, az, elev)
    if r is None:
        return np.array([1e4, 1e4])
    dlat = (r["lat"] - BLANCO["lat"]) * R * math.pi / 180 / 1e3
    dlon = (r["lon"] - BLANCO["lon"]) * R * math.pi / 180 / 1e3 * math.cos(math.radians(BLANCO["lat"]))
    return np.array([dlat, dlon])


def apuntar(elev):
    """La (v0, acimut) que deja el bloque en el blanco con esa elevación del raíl."""
    psi = arco_km(LANZA["lat"], LANZA["lon"], BLANCO["lat"], BLANCO["lon"]) * 1e3 / R
    s = math.sin(psi / 2)
    v_min = math.sqrt(2 * G * R * s / (1 + s))                      # energía mínima, Luna quieta
    e = math.radians(elev)
    # velocidad de la balística plana-esférica para esa elevación (Luna quieta), como primera estimación
    # balística sobre la esfera quieta para esa elevación: tan(psi/2) = k sin e cos e / (1 - k cos^2 e), k = v^2 / (g R)
    tp = math.tan(psi / 2)
    v_est = math.sqrt(G * R * tp / (math.sin(e) * math.cos(e) + tp * math.cos(e) ** 2))
    # el acimut inicial: hacia el blanco por el círculo máximo, girado hacia el este por lo que la Luna rota en vuelo
    up, este, norte = local(LANZA["lat"], LANZA["lon"])
    rb = xyz(BLANCO["lat"], BLANCO["lon"], 0) / (R)
    az_est = math.degrees(math.atan2(np.dot(rb, este), np.dot(rb, norte)))
    v, az = fsolve(lambda q: fallo_km(q[0], q[1], elev), [v_est, az_est + 0.4], xtol=1e-9)
    r = vuelo(v, az, elev)
    # sensibilidades por diferencias finitas
    base = fallo_km(v, az, elev)
    sens = {
        "km por m/s de v0": float(np.linalg.norm(fallo_km(v + 1, az, elev) - base)),
        "km por grado de acimut": float(np.linalg.norm(fallo_km(v, az + 1, elev) - base)),
        "km por grado de elevación": float(np.linalg.norm(fallo_km(v, az, elev + 1) - base)),
    }
    return dict(elev=elev, v0=float(v), az=float(az), v_min_quieta=v_min, psi_deg=math.degrees(psi), t_h=r["t"] / 3600, t_min=r["t"] / 60,
                h_max_km=r["h_max"] / 1e3, v_imp=r["v_imp"], ang_imp=r["ang_imp"], sens=sens)


def rail(v0, a_g, m_bloque):
    a = a_g * G0
    m_cuna = F_CUNA * m_bloque
    L = v0**2 / (2 * a); t = v0 / a
    E_cin = 0.5 * (m_bloque + m_cuna) * v0**2
    E_red = E_cin / ETA - ETA_REGEN * 0.5 * m_cuna * v0**2
    return dict(a_g=a_g, L_m=L, t_s=t, m_cuna=m_cuna, F_kN=(m_bloque + m_cuna) * a / 1e3, P_pico_MW=(m_bloque + m_cuna) * a * v0 / ETA / 1e6,
                E_disparo_kWh=E_red / 3.6e6, L_freno_m=v0**2 / (2 * A_FRENO_G * G0), presion_hielo_MPa=None)


def bloque(m, a_g, esbeltez=1.3):
    """Un cilindro de hielo de masa m, largo = esbeltez x diámetro, empujado por la base a a_g."""
    V = m / RHO_HIELO
    D = (4 * V / (math.pi * esbeltez)) ** (1 / 3); L = esbeltez * D
    p = RHO_HIELO * a_g * G0 * L           # presión sobre la base del bloque (la cuna la reparte)
    return dict(m=m, V_m3=V, D_m=D, L_m=L, presion_MPa=p / 1e6, margen=SIGMA_HIELO / p, L_max_m=SIGMA_HIELO / (RHO_HIELO * a_g * G0))


def impacto(v_imp, m, f_proyectil=(0.3, 0.5, 0.7)):
    """Energética: qué parte del bloque puede evaporarse según la fracción de energía que se queda en el hielo."""
    ke = 0.5 * v_imp**2
    calentar = C_HIELO * (273.15 - T_HIELO)
    out = dict(ke_MJ_kg=ke / 1e6, calentar_MJ_kg=calentar / 1e6, fundir_MJ_kg=L_FUSION / 1e6, evaporar_MJ_kg=L_VAPOR / 1e6, casos=[])
    for fp in f_proyectil:
        q = fp * ke
        fundido = min(1.0, max(0.0, (q - calentar) / L_FUSION)) if q > calentar else 0.0
        vapor = min(1.0, max(0.0, (q - calentar - L_FUSION) / L_VAPOR))
        # el agua fundida hierve en el vacío y se congela otra vez: para volver a hielo pierde L_fusion/L_vapor de sí misma
        flash = (fundido - vapor) * L_FUSION / L_VAPOR if fundido > vapor else 0.0
        out["casos"].append(dict(f_proyectil=fp, fraccion_fundida=fundido, fraccion_vapor=vapor, fraccion_flash=flash, hielo_recuperable_max=1 - vapor - flash))
    # cráter en regolito suelto, régimen de gravedad (Holsapple-Housen, arena: mu 0,41, K_R ~ 0,9): orden de magnitud
    a_p = (3 * m / (4 * math.pi * RHO_HIELO)) ** (1 / 3)
    pi2 = G * a_p / v_imp**2
    R_cr = 0.9 * (m / RHO_REGOLITO) ** (1 / 3) * pi2 ** (-0.17)
    out["crater_diam_m"] = 2 * R_cr; out["crater_prof_m"] = R_cr / 4
    return out


def sublimacion():
    """Cuánto dura un bloque al sol del ecuador: sublimación limitada por la energía que absorbe (albedo del hielo sucio 0,5,
    más la radiación del suelo a 390 K bajo él), 2,83 MJ/kg de hielo a vapor."""
    q_sol = 1361 * 0.5; q_suelo = 5.67e-8 * 390**4 * 0.5
    flujo = (q_sol + q_suelo) / (C_HIELO * (273.15 - T_HIELO) + L_FUSION + L_VAPOR)     # kg/m^2 s
    return dict(flujo_kg_m2_h=flujo * 3600, mm_por_hora=flujo * 3600 / RHO_HIELO * 1e3, nota="de noche (suelo a 100 K) la pérdida es despreciable")


def camino(elev_d=30.0, paso_s=30.0):
    """El vuelo del punto de diseño, denso, en el marco fijo a la Luna: [lat, lon, h_km, t_min] cada paso_s segundos,
    para la lámina. Deja salto_polar_camino.json."""
    d = apuntar(elev_d)
    r = vuelo(d["v0"], d["az"], elev_d)
    pts = []
    for t in np.arange(0.0, r["t"], paso_s).tolist() + [r["t"]]:
        s = r["sol"].sol(t)
        c, sn = math.cos(-W * t), math.sin(-W * t)
        rf = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1]]) @ s[:3]
        rad = np.linalg.norm(rf)
        pts.append([round(math.degrees(math.asin(rf[2] / rad)), 4), round(math.degrees(math.atan2(rf[1], rf[0])), 4), round((rad - R) / 1e3, 2), round(t / 60, 3)])
    out = dict(salida=LANZA, blanco=BLANCO, elev=elev_d, v0=d["v0"], az=d["az"], t_min=d["t_min"], h_max_km=d["h_max_km"], v_imp=d["v_imp"], ang_imp=d["ang_imp"], sens=d["sens"], camino=pts)
    json.dump(out, open("salto_polar_camino.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"camino: {len(pts)} puntos cada {paso_s:.0f} s; v0 {d['v0']:.1f} m/s, {d['t_min']:.1f} min, apoapsis {d['h_max_km']:.0f} km")
    return out


def estudio(elev_d=30.0, a_g=100.0, m_bloque=940.0):
    log = []
    P = lambda s="": (log.append(s), print(s))
    d_km = arco_km(LANZA["lat"], LANZA["lon"], BLANCO["lat"], BLANCO["lon"])
    P(f"salida {LANZA['lat']}°, {LANZA['lon']}° a {LANZA['h']:.0f} m; blanco {BLANCO['lat']}°, {BLANCO['lon']}° a {BLANCO['h']:.0f} m; {d_km:.0f} km de arco")
    P(f"el blanco se mueve {W * R * math.cos(math.radians(BLANCO['lat'])):.1f} m/s hacia el este con la rotación de la Luna")
    P()
    P(" elev    v0 [m/s]  acimut   vuelo   h máx   impacto  ángulo   km/(m/s)  km/° az  km/° elev")
    barrido = []
    for e in (15.0, 20.0, 22.5, 25.0, 30.0, 35.0, 40.0, 45.0):
        r = apuntar(e); barrido.append(r)
        P(f" {e:4.1f}°  {r['v0']:8.1f}  {r['az']:6.2f}°  {r['t_min']:5.1f} min  {r['h_max_km']:5.0f} km  {r['v_imp']:6.1f}  {r['ang_imp']:5.1f}°   {r['sens']['km por m/s de v0']:6.2f}   {r['sens']['km por grado de acimut']:6.1f}   {r['sens']['km por grado de elevación']:6.1f}")
    P()
    d = apuntar(elev_d)
    P(f"PUNTO DE DISEÑO: raíl a {elev_d:.0f}°, {a_g:.0f} g, bloque de {m_bloque:.0f} kg")
    P(f"  salida {d['v0']:.1f} m/s (mínima con la Luna quieta {d['v_min_quieta']:.1f}), acimut {d['az']:.2f}°; vuelo {d['t_min']:.1f} min, apoapsis {d['h_max_km']:.0f} km")
    P(f"  impacto a {d['v_imp']:.0f} m/s con {d['ang_imp']:.1f}° sobre el suelo; 1 m/s en la boca = {d['sens']['km por m/s de v0']:.1f} km, 0,1° de acimut = {d['sens']['km por grado de acimut'] / 10:.1f} km")
    rl = rail(d["v0"], a_g, m_bloque); bl = bloque(m_bloque, a_g)
    P(f"  raíl: {rl['L_m']:.0f} m acelerando ({rl['t_s']:.2f} s), {rl['L_freno_m']:.0f} m de freno de la cuna; empuje {rl['F_kN']:.0f} kN, pico {rl['P_pico_MW']:.0f} MW, {rl['E_disparo_kWh']:.0f} kWh netos por disparo")
    P(f"  bloque: cilindro de {bl['D_m']:.2f} m de diámetro y {bl['L_m']:.2f} m ({bl['V_m3']:.2f} m³); {bl['presion_MPa']:.2f} MPa sobre la base, margen {bl['margen']:.0f}x; podría medir hasta {bl['L_max_m']:.1f} m")
    im = impacto(d["v_imp"], m_bloque)
    P(f"  impacto: {im['ke_MJ_kg']:.2f} MJ/kg frente a {im['calentar_MJ_kg']:.2f} para calentar, {im['fundir_MJ_kg']:.2f} para fundir y {im['evaporar_MJ_kg']:.2f} para evaporar")
    for c in im["casos"]:
        P(f"    si el hielo se queda el {c['f_proyectil']:.0%} de la energía: funde el {c['fraccion_fundida']:.0%}, se evapora el {c['fraccion_vapor']:.0%} en el choque y el {c['fraccion_flash']:.0%} al recongelarse en el vacío: queda como mucho el {c['hielo_recuperable_max']:.0%}")
    P(f"  cráter en regolito suelto: unos {im['crater_diam_m']:.0f} m de diámetro y {im['crater_prof_m']:.1f} m de hondo (orden de magnitud)")
    sb = sublimacion()
    P(f"  al sol del ecuador el hielo expuesto pierde {sb['flujo_kg_m2_h']:.1f} kg/m²·h ({sb['mm_por_hora']:.0f} mm/h); {sb['nota']}")
    P()
    P("CADENCIA para distintas necesidades de agua (bloque de diseño):")
    P("   agua/año   bloques/año   uno cada     energía/año")
    cad = []
    for agua_t in (54.0, 500.0, 5000.0):
        n = agua_t * 1e3 / m_bloque
        cad.append(dict(agua_t=agua_t, bloques=n, cada_h=8766 / n, GWh=n * rl["E_disparo_kWh"] / 1e6))
        P(f"   {agua_t:7.0f} t   {n:9.0f}     {8766 / n:7.1f} h    {n * rl['E_disparo_kWh'] / 1e3:8.1f} MWh")
    P()
    P("NOTAS: Luna esférica y de dos cuerpos; la Tierra cambia el impacto menos de 1 km en 40 min. Las cotas de salida y llegada son supuestas:")
    P("  SLDEM2015 llega solo a 60° de latitud, el polo pide el LDEM polar de LOLA. La fracción recuperada del impacto es la gran incógnita.")
    res = dict(salida=LANZA, blanco=BLANCO, arco_km=d_km, barrido=[{k: v for k, v in r.items()} for r in barrido], diseno=dict(trayectoria=d, rail=rl, bloque=bl, impacto=im, sublimacion=sb, cadencia=cad))
    json.dump(res, open("salto_polar.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open("salto_polar.log", "w", encoding="utf-8").write("\n".join(log) + "\n")


if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if len(sys.argv) >= 2 and sys.argv[1] == "camino":
        camino(float(sys.argv[2]) if len(sys.argv) > 2 else 30.0)
    elif len(sys.argv) >= 3:
        estudio(float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]) if len(sys.argv) > 3 else 940.0)
    else:
        estudio()
