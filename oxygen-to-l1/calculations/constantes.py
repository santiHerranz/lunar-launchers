"""
Constantes compartidas del lanzador lunar.

Unidades SI. Las cifras de la Luna y la Tierra son valores estándar (IAU / JPL);
la atmósfera es la US-1976 tabulada en densidad, que llega a 200 km (el modelo
del lanzador de Canarias paraba en 86 km y extrapolaba a temperatura fija, lo
que subestima la densidad justo donde empieza la aerocaptura).
"""
import math
import numpy as np

# ---------------- Tierra ----------------
MU_E = 3.986004418e14          # m^3/s^2
R_E = 6371.0e3                 # radio medio [m] (el mismo que el proyecto de Canarias)
G0 = 9.80665
W_E = 7.2921159e-5             # rotación terrestre [rad/s]
H_EI = 120.0e3                 # interfaz de entrada atmosférica [m]

# ---------------- Luna ----------------
MU_M = 4.9028e12               # m^3/s^2
R_M = 1737.4e3                 # radio medio [m]
G_M = MU_M / R_M**2            # 1,624 m/s^2 en superficie
V_ESC_M = math.sqrt(2 * MU_M / R_M)   # 2.376 m/s
V_CIRC_M = math.sqrt(MU_M / R_M)      # 1.680 m/s
KM_POR_GRADO_M = R_M * math.pi / 180 / 1e3   # 30,32 km/°

# ---------------- órbita de la Luna (geocéntrica, kepleriana media) ----------------
A_M = 384748.0e3               # semieje mayor [m]
E_M = 0.0549                   # excentricidad
MU_EM = MU_E + MU_M
N_M = math.sqrt(MU_EM / A_M**3)        # movimiento medio [rad/s] -> 27,32 d sidéreo
T_SID = 2 * math.pi / N_M

# ---------------- LEO de destino ----------------
H_LEO = 400.0e3                # órbita circular de entrega [m]

# ---------------- atmósfera US-1976, densidad [kg/m^3] ----------------
ATM_H = np.array([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80,
                  85, 90, 95, 100, 110, 120, 130, 140, 150, 160, 180, 200], float) * 1e3
ATM_RHO = np.array([1.225, 7.364e-1, 4.135e-1, 1.948e-1, 8.891e-2, 4.008e-2, 1.841e-2,
                    8.463e-3, 3.996e-3, 1.966e-3, 1.027e-3, 5.680e-4, 3.097e-4, 1.632e-4,
                    8.283e-5, 3.992e-5, 1.846e-5, 8.220e-6, 3.416e-6, 1.393e-6, 5.604e-7,
                    9.708e-8, 2.222e-8, 8.152e-9, 3.831e-9, 2.076e-9, 1.233e-9, 5.194e-10,
                    2.541e-10])
_LOG_RHO = np.log(ATM_RHO)


def densidad(h):
    """Densidad US-1976 [kg/m^3], interpolación log-lineal; 0 por encima de 200 km."""
    if h >= ATM_H[-1]:
        return 0.0
    if h <= 0.0:
        return ATM_RHO[0]
    return math.exp(np.interp(h, ATM_H, _LOG_RHO))
