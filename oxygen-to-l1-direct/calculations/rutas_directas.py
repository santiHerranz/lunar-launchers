"""
Las rutas directas a L1 que encontró sitio_l1_directo.py, comparadas por lo que de verdad importa:
cuánto oxígeno entrega una cápsula de 500 kg.

Las rutas rápidas (13-17 h) salen más deprisa del raíl y llegan a L1 a 800-1.100 m/s; la cápsula
tiene que frenar todo eso con su motor y se queda con mucho menos oxígeno. Las lentas (54-68 h)
llegan casi paradas. Para cada ruta se cierra la cápsula con capsula_l1.para_total (500 kg,
100 g, el frenado y las horas de esa ruta) y se calcula el raíl a 100 g y la energía del disparo
frente a la ruta principal (84,92°W, raíl a 30°).

Uso: python rutas_directas.py
Escribe rutas_directas.json, rutas_directas.log y las gráficas ../charts/rutas_directas_{light,dark}.svg
"""
import os, sys, json

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO = os.path.normpath(os.path.join(AQUI, "..", "..", "oxygen-to-l1", "calculations"))
sys.path.insert(0, MODELO)
import capsula_l1 as CL
from constantes import G0

A_G = 100.0
M_CAPSULA = 500.0
PRINCIPAL = (0.0, -84.92)
LIMBO = -90.0           # más al oeste, la Tierra queda bajo el horizonte casi todo el mes


def rutas():
    d = json.load(open(os.path.join(MODELO, "sitio_l1_directo.json"), encoding="utf-8"))
    filas = []
    for r in d["con_trayectoria"]:
        if not r.get("v0"):
            continue
        c = CL.para_total(M_CAPSULA, v_llegada=r["v_llegada"], horas=r["t_h"], a_g=A_G)
        filas.append(dict(lat=r["lat"], lon=round(r["lon"], 2), raíl_grados=r["tilt"], v0=r["v0"], v_llegada=r["v_llegada"], horas=r["t_h"],
                          obra_Mm3=r["volumen_Mm3"], oxigeno_entregado_kg=c["m_lox_llega"], propelente_kg=c["m_prop"], evaporado_kg=c["evaporado"],
                          dv_capsula=c["dv"], rail_km=r["v0"] ** 2 / (2 * A_G * G0) / 1e3,
                          cara_visible=r["lon"] > LIMBO, principal=(r["lat"], round(r["lon"], 2)) == PRINCIPAL))
    ref = next(f for f in filas if f["principal"])
    for f in filas:
        f["energia_frente_a_principal"] = (f["v0"] / ref["v0"]) ** 2
        f["rapida"] = f["v_llegada"] > 500
    return sorted(filas, key=lambda f: f["horas"])


# --- gráfica: horas de viaje frente a oxígeno entregado ------------------------------------------
TEMAS = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781", grid="#e1e0d9", axis="#c3c2b7",
                  s1="#2a78d6", s2="#eb6834"),
    "dark": dict(surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#898781", grid="#2c2c2a", axis="#383835",
                 s1="#3987e5", s2="#d95926"),
}
W, H = 880, 540
PL, PR, PT, PB = 70, 30, 132, 92          # márgenes del área de datos
X0, X1, Y0, Y1 = 0.0, 75.0, 0.0, 450.0
FUENTE = 'system-ui, -apple-system, &quot;Segoe UI&quot;, sans-serif'


def sx(h): return PL + (h - X0) / (X1 - X0) * (W - PL - PR)
def sy(kg): return H - PB - (kg - Y0) / (Y1 - Y0) * (H - PT - PB)
def n(x, d=0): return f"{x:,.{d}f}"


def svg(filas, tema):
    t = TEMAS[tema]
    rap = [f for f in filas if f["rapida"]]; len_ = [f for f in filas if not f["rapida"]]
    ref = next(f for f in filas if f["principal"]); top = min(filas, key=lambda f: f["horas"])
    o = []
    def tx(x, y, s, size=13, color=None, weight=400, anchor="start"):
        o.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{color or t["ink2"]}" text-anchor="{anchor}">{s}</text>')
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FUENTE}" role="img" '
             f'aria-labelledby="t d"><title id="t">Faster direct routes deliver less oxygen</title>'
             f'<desc id="d">Flight time to L1 against liquid oxygen delivered by a 500 kg capsule, for the {len(filas)} direct routes found by the slope search. '
             f'Routes of {n(rap[0]["horas"])}-{n(rap[-1]["horas"])} h deliver {n(min(f["oxigeno_entregado_kg"] for f in rap))}-{n(max(f["oxigeno_entregado_kg"] for f in rap))} kg; '
             f'routes of {n(len_[0]["horas"])}-{n(len_[-1]["horas"])} h deliver {n(min(f["oxigeno_entregado_kg"] for f in len_))}-{n(max(f["oxigeno_entregado_kg"] for f in len_))} kg. '
             f'The main route, 84.92 W, takes {n(ref["horas"])} h and delivers {n(ref["oxigeno_entregado_kg"])} kg.</desc>')
    o.append(f'<rect width="{W}" height="{H}" rx="10" fill="{t["surface"]}"/>')
    # título, subtítulo y leyenda
    tx(28, 40, "Faster direct routes deliver less oxygen", 20, t["ink"], 600)
    tx(28, 64, f"Direct routes from the Moon to L1: flight time against liquid oxygen delivered by a {n(M_CAPSULA)} kg capsule", 13.5)
    ly = 98
    for i, (col, lab) in enumerate([(t["s1"], "Near side, east of 90°W"), (t["s2"], "Beyond the 90°W limb: Earth below the horizon most of the month")]):
        x = 28 + i * 220
        o.append(f'<circle cx="{x + 6}" cy="{ly - 4}" r="6" fill="{col}"/>'); tx(x + 18, ly, lab, 13, t["ink2"])
    # rejilla y ejes
    for kg in range(0, 401, 100):
        y = sy(kg)
        o.append(f'<line x1="{PL}" x2="{W - PR}" y1="{y:.1f}" y2="{y:.1f}" stroke="{t["axis"] if kg == 0 else t["grid"]}" stroke-width="1"/>')
        tx(PL - 10, y + 4, n(kg), 12, t["muted"], anchor="end")
    for h in range(0, 71, 10):
        tx(sx(h), H - PB + 20, n(h), 12, t["muted"], anchor="middle")
    tx((PL + W - PR) / 2, H - PB + 44, "Flight time to L1 (h)", 13, t["ink2"], anchor="middle")
    o.append(f'<text transform="translate(20 {(PT + H - PB) / 2:.1f}) rotate(-90)" font-size="13" fill="{t["ink2"]}" text-anchor="middle">Oxygen delivered (kg)</text>')
    # anotaciones de los dos grupos
    ax = sx(22)
    tx(ax, sy(282), f"Fast: {n(rap[0]['horas'])}–{n(rap[-1]['horas'])} h, but they reach L1 at {n(min(f['v_llegada'] for f in rap))}–{n(max(f['v_llegada'] for f in rap))} m/s", 13, t["ink"], 600)
    tx(ax, sy(282) + 19, f"The capsule burns {n(min(f['propelente_kg'] for f in rap))}–{n(max(f['propelente_kg'] for f in rap))} kg of propellant to stop there,", 13)
    tx(ax, sy(282) + 37, f"and the rail fires at up to {n(max(f['v0'] for f in rap))} m/s ({(max(f['energia_frente_a_principal'] for f in rap) - 1) * 100:.0f} % more energy per shot)", 13)
    bx = sx(len_[-1]["horas"]) + 4
    tx(bx, sy(318), f"Slow: {n(len_[0]['horas'])}–{n(len_[-1]['horas'])} h, arriving at {n(min(f['v_llegada'] for f in len_))}–{n(max(f['v_llegada'] for f in len_))} m/s", 13, t["ink"], 600, "end")
    tx(bx, sy(318) + 19, f"{n(min(f['propelente_kg'] for f in len_))}–{n(max(f['propelente_kg'] for f in len_))} kg of propellant is enough", 13, anchor="end")
    # puntos: anillo de superficie de 2 px para que no se fundan los que se solapan
    for f in filas:
        col = t["s1"] if f["cara_visible"] else t["s2"]
        o.append(f'<circle cx="{sx(f["horas"]):.1f}" cy="{sy(f["oxigeno_entregado_kg"]):.1f}" r="6" fill="{col}" stroke="{t["surface"]}" stroke-width="2"/>')
    # la ruta principal y la más rápida, etiquetadas
    px, py = sx(ref["horas"]), sy(ref["oxigeno_entregado_kg"])
    o.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="11" fill="none" stroke="{t["ink"]}" stroke-width="1.5"/>')
    o.append(f'<line x1="{px - 8:.1f}" y1="{py - 8:.1f}" x2="{px - 30:.1f}" y2="{sy(422):.1f}" stroke="{t["ink2"]}" stroke-width="1"/>')
    tx(px - 34, sy(422) - 4, f"Main route · 84.92°W, rail at 30°", 13, t["ink"], 600, "end")
    tx(px - 34, sy(422) + 13, f"{n(ref['horas'])} h · {n(ref['oxigeno_entregado_kg'])} kg delivered · brakes {n(ref['v_llegada'])} m/s", 12.5, anchor="end")
    qx, qy = sx(top["horas"]), sy(top["oxigeno_entregado_kg"])
    o.append(f'<line x1="{qx:.1f}" y1="{qy + 9:.1f}" x2="{qx:.1f}" y2="{qy + 34:.1f}" stroke="{t["ink2"]}" stroke-width="1"/>')
    tx(qx - 6, qy + 50, f"Fastest · {abs(top['lon']):.1f}°W", 13, t["ink"], 600)
    tx(qx - 6, qy + 67, f"{n(top['horas'])} h · {n(top['oxigeno_entregado_kg'])} kg · brakes {n(top['v_llegada'])} m/s", 12.5)
    # nota al pie
    tx(28, H - 22, f"Only 84.92°W is on the equator; off the equator, a rail aimed due east misses L1 out of plane. Capsule model: capsula_l1.py, {n(M_CAPSULA)} kg, 100 g, Isp 310 s.", 11.5, t["muted"])
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    os.chdir(AQUI)
    filas = rutas()
    json.dump(filas, open("rutas_directas.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    log = [f"{'lat':>5} {'lon':>7} {'raíl':>4}  {'v0':>7}  {'llega':>6}  {'horas':>5}  {'O2 kg':>5}  {'prop':>4}  {'raíl km':>7}  {'energía':>7}  cara"]
    for f in filas:
        log.append(f"{f['lat']:+5.1f} {f['lon']:7.2f} {f['raíl_grados']:3.0f}°  {f['v0']:7.1f}  {f['v_llegada']:6.1f}  {f['horas']:5.1f}  {f['oxigeno_entregado_kg']:5.0f}  "
                   f"{f['propelente_kg']:4.0f}  {f['rail_km']:7.2f}  {f['energia_frente_a_principal']:6.2f}x  {'visible' if f['cara_visible'] else 'más allá del limbo'}"
                   f"{'  <- principal' if f['principal'] else ''}")
    print("\n".join(log))
    open("rutas_directas.log", "w", encoding="utf-8").write("\n".join(log) + "\n")
    os.makedirs(os.path.join("..", "charts"), exist_ok=True)
    for tema in TEMAS:
        open(os.path.join("..", "charts", f"rutas_directas_{tema}.svg"), "w", encoding="utf-8").write(svg(filas, tema))
