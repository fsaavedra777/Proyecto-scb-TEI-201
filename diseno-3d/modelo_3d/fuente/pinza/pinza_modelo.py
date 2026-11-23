"""Pinza corregida - Proyecto SCB.
Dos dedos con engranajes involutos (modulo 2, 16 dientes) que engranan entre si.
El servo SG90 mueve directo el dedo izquierdo (con FSR-402) usando su brazo simple;
el dedo derecho gira sobre un tornillo M3 en un poste del chasis.

Sistema de coordenadas: cara superior de la placa en z = 0, servo bajo la placa
(apoyado en sus orejas), dedos sobre la placa apuntando hacia +y.
Medidas en mm.
"""
import math
import numpy as np
import cadquery as cq
from shapely.geometry import Polygon, Point, box as sbox
from shapely.ops import unary_union
from shapely import affinity

# ------------------------- parametros -------------------------
M, Z, ALFA = 2.0, 16, math.radians(20.0)   # modulo, dientes, angulo de presion
A = 32.15                                  # distancia entre ejes (32 + 0,15 de juego)
PX, PY = A / 2, 16.0                       # ejes en (-PX, PY) motriz y (+PX, PY) esclavo
ADELG = 0.05                               # adelgazamiento del diente (juego)

# SG90 (modelo de referencia: ledalert/cadmodel-sg90)
S_CUERPO = (12.2, 22.5)        # ancho (x), largo (y)
S_ALTO = 22.5
S_OREJA_LARGO, S_OREJA_ESP = 32.2, 2.0
S_OREJA_Z = 15.75              # parte de abajo de la oreja, medida desde la base del servo
S_EJE_OFF = 5.5                # eje desplazado del centro del cuerpo
S_TORRE_D, S_TORRE_TOP = 11.6, 26.5
S_SPLINE_D, S_SPLINE_TOP = 4.8, 29.5
S_ORIF_SEP = 28.0              # entre agujeros de las orejas (27,5 a 28,5 segun fabricante)

Z_SERVO_BASE = -S_OREJA_Z      # base del servo (orejas apoyadas en z = 0)
Z_TORRE = Z_SERVO_BASE + S_TORRE_TOP      # 10,75
Z0 = 11.25                     # cara inferior de los dedos (= base del brazo del servo)
T_DEDO = 8.0                   # espesor del plano de los engranajes y brazos
H_CARA = 24.0                  # alto de la cara de agarre
X_CARA = 2.5                   # cara a 2,5 mm del centro: 5 mm entre caras con dedos paralelos
Y_PAD0, Y_PAD1 = 56.0, 78.0    # largo de la almohadilla
ESP_CARA = 5.0
FSR_D, FSR_PROF = 18.8, 0.35   # FSR-402: disco de 18,3 mm, 0,46 mm de espesor
COLA_ANCHO, COLA_PROF = 8.5, 0.6
FSR_Y, FSR_Z = (Y_PAD0 + Y_PAD1) / 2, Z0 + H_CARA / 2

PLACA_X = (-32.5, 32.5)
PLACA_Y = (-36.0, 30.0)
PLACA_T = 4.0
POSTE_TOP = Z0 - 0.5           # golilla M3 de 0,5 mm bajo el dedo esclavo
AGUJ_MONTAJE = [(-20, -30), (20, -30), (-20, -18), (20, -18)]

# brazo simple del SG90: buje 6,7 x 3,8 mm, brazo 1,4 mm hasta 16 mm del centro
BOLSILLO_BUJE_D, BOLSILLO_PUNTA_D, BOLSILLO_LARGO, BOLSILLO_PROF = 7.4, 5.2, 15.5, 4.2
ACCESO_D = 5.5


def inv(a):
    return math.tan(a) - a


def engranaje_2d(cx, cy, fase, m=M, z=Z, alfa=ALFA, adelg=ADELG, n=14):
    r = m * z / 2
    rb, ra, rf = r * math.cos(alfa), r + m, r - 1.25 * m
    psi = math.pi / (2 * z) - (adelg / 2) / r

    def theta(rho):
        if rho <= rb:
            return psi + inv(alfa)
        return psi + inv(alfa) - inv(math.acos(rb / rho))

    radios = [rf, rb] + [rb + (ra - rb) * i / n for i in range(1, n + 1)]
    paso = 2 * math.pi / z
    pts = []
    for k in range(z):
        c = fase + k * paso
        tb, ta = theta(rf), theta(ra)
        for t in np.linspace(c - paso / 2, c - tb, 4, endpoint=False):
            pts.append((rf * math.cos(t), rf * math.sin(t)))
        for rho in radios:
            t = c - theta(rho)
            pts.append((rho * math.cos(t), rho * math.sin(t)))
        for t in np.linspace(c - ta, c + ta, 5)[1:-1]:
            pts.append((ra * math.cos(t), ra * math.sin(t)))
        for rho in reversed(radios):
            t = c + theta(rho)
            pts.append((rho * math.cos(t), rho * math.sin(t)))
        for t in np.linspace(c + tb, c + paso / 2, 4, endpoint=False)[1:]:
            pts.append((rf * math.cos(t), rf * math.sin(t)))
    return Polygon([(cx + x, cy + y) for x, y in pts]).buffer(0)


def cuerpo_dedo_izq_2d():
    """Cuello + brazo + base de la almohadilla del dedo izquierdo (sin el engranaje)."""
    px = -PX
    cuello = unary_union([Point(px, PY).buffer(6.5, 64), sbox(px - 3.5, PY + 26, px + 3.5, PY + 27)]).convex_hull
    brazo = sbox(px - 3.5, PY + 26, px + 3.5, Y_PAD0 + 2)
    base = sbox(px - 3.5, Y_PAD0, -X_CARA, Y_PAD1)
    forma = unary_union([cuello, brazo, base])
    return forma.buffer(-1.5, 32).buffer(1.5, 32)


def contorno_dedo(lado):
    """Contorno 2D completo (engranaje + brazo) en la posicion paralela. lado -1 izquierdo, +1 derecho."""
    if lado < 0:
        g = engranaje_2d(-PX, PY, 0.0)                 # un diente apunta al otro engranaje
        cuerpo = cuerpo_dedo_izq_2d()
    else:
        g = engranaje_2d(PX, PY, math.pi + math.pi / Z)  # medio paso: queda un hueco frente al diente
        cuerpo = affinity.scale(cuerpo_dedo_izq_2d(), xfact=-1, yfact=1, origin=(0, 0))
    return unary_union([g, cuerpo])


def extruir(poligono, z0, h):
    ext = list(poligono.exterior.coords)[:-1]
    return cq.Workplane("XY").workplane(offset=z0).polyline(ext).close().extrude(h)


def caja(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cilindro_z(cx, cy, d, z0, h):
    return cq.Workplane("XY").workplane(offset=z0).center(cx, cy).circle(d / 2).extrude(h)


def dedo(lado):
    s = lado
    plano = extruir(contorno_dedo(lado), Z0, T_DEDO)
    x_in, x_out = (-X_CARA, -X_CARA - ESP_CARA) if s < 0 else (X_CARA, X_CARA + ESP_CARA)
    cara = caja(min(x_in, x_out), max(x_in, x_out), Y_PAD0, Y_PAD1, Z0, Z0 + H_CARA)
    cara = cara.edges("|Z").fillet(1.5)
    sol = plano.union(cara)
    px = s * PX
    if s < 0:
        # bolsillo para el brazo simple del servo (abierto hacia abajo) + acceso al tornillo
        bols = (cq.Workplane("XY").workplane(offset=Z0 - 0.01)
                .center(px, PY).circle(BOLSILLO_BUJE_D / 2).extrude(BOLSILLO_PROF + 0.01))
        brazo_h = (cq.Workplane("XY").workplane(offset=Z0 - 0.01)
                   .polyline(list(unary_union([Point(px, PY).buffer(BOLSILLO_BUJE_D / 2 - 0.4, 48),
                                               Point(px, PY + BOLSILLO_LARGO).buffer(BOLSILLO_PUNTA_D / 2, 48)]
                                              ).convex_hull.exterior.coords)[:-1])
                   .close().extrude(BOLSILLO_PROF + 0.01))
        acceso = cilindro_z(px, PY, ACCESO_D, Z0 - 1, T_DEDO + 2)
        sol = sol.cut(bols).cut(brazo_h).cut(acceso)
        # rebaje para el FSR en la cara interna + canal para su cola
        rebaje = (cq.Workplane("YZ").workplane(offset=-X_CARA - FSR_PROF)
                  .center(FSR_Y, FSR_Z).circle(FSR_D / 2).extrude(FSR_PROF + 0.5))
        canal = caja(-X_CARA - COLA_PROF, -X_CARA + 0.5, Y_PAD0 - 1, FSR_Y,
                     FSR_Z - COLA_ANCHO / 2, FSR_Z + COLA_ANCHO / 2)
        sol = sol.cut(rebaje).cut(canal)
    else:
        sol = sol.cut(cilindro_z(px, PY, 3.4, Z0 - 1, T_DEDO + 2))   # eje M3
    return sol


def chasis():
    x0, x1 = PLACA_X
    y0, y1 = PLACA_Y
    placa = caja(x0, x1, y0, y1, -PLACA_T, 0).edges("|Z").fillet(4)
    cx, cy = -PX, PY - S_EJE_OFF                     # centro del cuerpo del servo
    ventana = caja(cx - (S_CUERPO[0] + 0.4) / 2, cx + (S_CUERPO[0] + 0.4) / 2,
                   cy - (S_CUERPO[1] + 0.7) / 2, cy + (S_CUERPO[1] + 0.7) / 2, -PLACA_T - 1, 1)
    placa = placa.cut(ventana)
    for sy in (-1, 1):   # agujeros guia para los tornillos de las orejas (ranura 27,2 a 28,8 mm)
        ran = (cq.Workplane("XY").workplane(offset=-PLACA_T - 1).center(cx, cy + sy * S_ORIF_SEP / 2)
               .slot2D(2.7, 1.9, 90).extrude(PLACA_T + 2))
        placa = placa.cut(ran)
    poste = (cilindro_z(PX, PY, 14, 0, 2).union(cilindro_z(PX, PY, 9, 0, POSTE_TOP))
             .faces(">Z").edges().chamfer(0.4))
    placa = placa.union(poste)
    placa = placa.cut(cilindro_z(PX, PY, 3.3, -PLACA_T - 1, POSTE_TOP + PLACA_T + 2))
    for (x, y) in AGUJ_MONTAJE:
        placa = placa.cut(cilindro_z(x, y, 3.3, -PLACA_T - 1, PLACA_T + 2))
    return placa


def disco_fsr():
    return cilindro_z(0, 0, 12, 0, 2.5).edges(">Z").fillet(0.6)


def calce(espesor):
    return cilindro_z(0, 0, 8, 0, espesor).cut(cilindro_z(0, 0, 3.4, -1, espesor + 2))


# ------------------------- referencias (no se imprimen) -------------------------
def servo_ref():
    cx, cy = -PX, PY - S_EJE_OFF
    w, l = S_CUERPO
    cuerpo = caja(cx - w / 2, cx + w / 2, cy - l / 2, cy + l / 2, Z_SERVO_BASE, Z_SERVO_BASE + S_ALTO)
    orejas = caja(cx - w / 2, cx + w / 2, cy - S_OREJA_LARGO / 2, cy + S_OREJA_LARGO / 2, 0, S_OREJA_ESP)
    torre = cilindro_z(-PX, PY, S_TORRE_D, Z_SERVO_BASE + S_ALTO - 1, Z_TORRE - (Z_SERVO_BASE + S_ALTO - 1))
    spline = cilindro_z(-PX, PY, S_SPLINE_D, Z_TORRE - 1, S_SPLINE_TOP - S_TORRE_TOP + 1)
    return cuerpo.union(orejas).union(torre).union(spline)


def brazo_servo_ref():
    buje = cilindro_z(-PX, PY, 6.7, Z0, 3.8)
    pts = list(unary_union([Point(-PX, PY).buffer(3, 32), Point(-PX, PY + 14).buffer(2, 32)]).convex_hull.exterior.coords)[:-1]
    brazo = cq.Workplane("XY").workplane(offset=Z0).polyline(pts).close().extrude(1.4)
    return buje.union(brazo).cut(cilindro_z(-PX, PY, S_SPLINE_D, Z0 - 0.1, 3.0))


def eje_esclavo_ref():
    tornillo = cilindro_z(PX, PY, 3.0, -PLACA_T - 2.0, PLACA_T + 2.0 + Z0 + T_DEDO + 0.5 + 4.5)
    cabeza = cilindro_z(PX, PY, 5.5, -PLACA_T - 2.0, 2.0)
    gol1 = cilindro_z(PX, PY, 7.0, POSTE_TOP, 0.5).cut(cilindro_z(PX, PY, 3.2, POSTE_TOP - 1, 2.5))
    gol2 = cilindro_z(PX, PY, 7.0, Z0 + T_DEDO, 0.5).cut(cilindro_z(PX, PY, 3.2, Z0 + T_DEDO - 1, 2.5))
    tuerca = (cq.Workplane("XY").workplane(offset=Z0 + T_DEDO + 0.5).center(PX, PY)
              .polygon(6, 6.4).extrude(4.0).cut(cilindro_z(PX, PY, 3.0, Z0 + T_DEDO, 6)))
    return tornillo.union(cabeza), gol1.union(gol2).union(tuerca)


def girar_dedo(sol, lado, grados):
    """Abre (grados > 0) o cierra el dedo alrededor de su eje."""
    px = lado * PX
    ang = grados if lado < 0 else -grados
    return sol.rotate((px, PY, 0), (px, PY, 1), ang)
