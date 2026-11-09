"""
La planta de oxígeno junto al raíl: cuánto regolito hay que excavar y cuánta energía hace falta.

Proceso: reducción con hidrógeno de la ilmenita (FeTiO3 + H2 -> Fe + TiO2 + H2O; el agua se
electroliza, el hidrógeno vuelve al reactor y el oxígeno se licúa). Energía de extremo a extremo
según Leger et al., PNAS 122, e2306146122 (2025): 24,3 ± 5,8 kWh por kg de oxígeno líquido para
un regolito con un 10 % de ilmenita, de la excavación al almacenamiento sin evaporación.

Regolito: el oxígeno que suelta la ilmenita es 16/151,7 = 10,5 % de su masa; con un 10 % de
ilmenita y una recuperación supuesta del 60 % (beneficio y conversión), salen unos 6,3 kg de
oxígeno por tonelada de regolito. La recuperación es la hipótesis más incierta: depende del
contenido real de ilmenita del sitio, que no se ha medido.

Uso: python oxigeno.py
"""
import json
import capsula_l1 as CL
import rampa_lunar as RL

KWH_KG = 24.3; KWH_KG_ERR = 5.8
ILM = 0.10; O_ILM = 16 / 151.7; RECUP = 0.60
RHO_REG = 1600.0                      # kg/m^3, regolito excavado
DIA_LUNAR_H = 29.53 * 24 / 2
W_SOLAR_M2 = 1361 * 0.30 * 0.8


def planta(t_o2_anio, solo_dia=True):
    e_mwh = t_o2_anio * 1e3 * KWH_KG / 1e3
    horas = 8766 * (0.5 if solo_dia else 1.0)
    p_mw = e_mwh / horas
    reg_t = t_o2_anio / (ILM * O_ILM * RECUP)
    return dict(o2_t_anio=t_o2_anio, energia_GWh=e_mwh / 1e3, energia_GWh_rango=(t_o2_anio * (KWH_KG - KWH_KG_ERR) / 1e3, t_o2_anio * (KWH_KG + KWH_KG_ERR) / 1e3),
                potencia_MW=p_mw, paneles_km2=p_mw * 1e6 / W_SOLAR_M2 / 1e6, regolito_t_anio=reg_t, regolito_t_dia=reg_t / 365.25,
                regolito_m3_anio=reg_t * 1e3 / RHO_REG, superficie_km2_3m=reg_t * 1e3 / RHO_REG / 3 / 1e6)


if __name__ == "__main__":
    caps = CL.para_total(500.0, v_llegada=158.0, horas=308.0, a_g=100.0)
    lox_disparo = caps["m_lox_llega"] + caps["evaporado"]            # lo que se carga en la cápsula
    ra = RL.rampa(500.0, 100.0, v=2328.2)
    out = {"capsula": caps, "rampa": ra, "cadencias": []}
    print(f"cápsula de 500 kg: carga {lox_disparo:.0f} kg de oxígeno y entrega {caps['m_lox_llega']:.0f} kg en L1; el raíl gasta {ra['E_red_MWh']:.2f} MWh por disparo")
    for n in (1, 2, 6):
        disparos = n * 8766 / 2                                          # solo de día
        t_carga = disparos * lox_disparo / 1e3
        p = planta(t_carga)
        e_rail = disparos * ra["E_red_MWh"] / 1e3
        p.update(disparos_h=n, o2_en_L1_t=disparos * caps["m_lox_llega"] / 1e3, energia_rail_GWh=e_rail,
                 cociente_planta_rail=p["energia_GWh"] / e_rail, llenados_starship=disparos * caps["m_lox_llega"] / 936e3)
        out["cadencias"].append(p)
        print(f"{n}/h de día: {p['o2_t_anio']:>6.0f} t/año de oxígeno ({p['o2_en_L1_t']:.0f} t llegan a L1, {p['llenados_starship']:.1f} llenados de Starship); "
              f"planta {p['energia_GWh']:.0f} GWh/año ({p['energia_GWh_rango'][0]:.0f}–{p['energia_GWh_rango'][1]:.0f}), {p['potencia_MW']:.1f} MW de día, "
              f"{p['paneles_km2']:.3f} km² de paneles; raíl {e_rail:.1f} GWh/año, la planta gasta {p['cociente_planta_rail']:.0f} veces más; "
              f"regolito {p['regolito_t_dia']:.0f} t/día, {p['superficie_km2_3m']:.3f} km²/año a 3 m")
    json.dump(out, open("oxigeno.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
