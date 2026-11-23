"""
caja_control.py — Caja de control del Proyecto SCB y su gemelo 3D (CadQuery).

Modelo paramétrico: cambiar un valor de la sección PARÁMETROS regenera todo
(caja, tapa, componentes, STEP, STL). Medidas en mm.

Contiene:
  - Base de la caja con pilares para el Arduino y la placa perforada,
    rieles deslizantes para el HX711 y el MT3608, ranura en U para cables,
    calados para USB/DC, agujero para prensaestopa PG7 y fijación a la mesa.
  - Tapa con faldón de centrado, lengüeta que cierra la ranura de cables,
    4 tornillos M3 avellanados (insertos de bronce en la base) y ventilación.
  - Volúmenes referenciales de cada componente interno (gemelo 3D).

Uso:  pip install cadquery     y luego     python caja_control.py
"""
import os

import cadquery as cq

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# =============================== PARÁMETROS ===============================
L_INT, W_INT, H_INT = 150.0, 100.0, 40.0   # interior útil
PARED = 2.4                                # 6 perímetros de 0,4 mm
PISO = 2.4
TAPA = 3.0
HOLGURA = 0.3                              # juego por lado entre piezas impresas
R_EXT = 4.0                                # radio de las esquinas exteriores

BOSS_D = 9.0                               # pilares de esquina para la tapa
INSERTO_D, INSERTO_H = 4.2, 6.0            # inserto térmico M3 x 5,7
TORN_D, AVELL_D = 3.4, 6.6                 # tornillo M3 avellanado

STANDOFF_D, STANDOFF_H = 6.5, 6.0          # pilares del Arduino
PERF_H = 5.0                               # pilares de la placa perforada
TUERCA_M3 = 5.7                            # entre caras + holgura (tuerca cautiva desde abajo)

# Ubicación de los componentes (origen = esquina interior, sobre el piso)
UNO_X, UNO_Y = 8.0, 12.0                   # esquina del PCB del Arduino (lado USB hacia x=0)
PERF_X, PERF_Y = 79.0, 12.0                # placa perforada 70 x 50
HX_X, HX_Y = 12.0, 72.0                    # HX711 en riel
MT_X, MT_Y = 100.0, 74.0                   # MT3608 en riel (entre ambos rieles queda la zona
                                           # libre por donde se deslizan los módulos)

RANURA_Y0, RANURA_Y1 = 20.0, 80.0          # ranura en U en la pared derecha (x = L)
RANURA_PROF = 14.0                         # desde el borde superior
LENGUETA = 6.0                             # cuánto baja la lengüeta de la tapa (queda 8 mm libre)
PG7_D = 12.6                               # agujero para prensaestopa PG7
PG7_X, PG7_Z = 78.0, 22.0                  # en la pared trasera (y = W), sobre la zona libre

# ---- Medidas de los componentes (hojas de datos / medición) ----
UNO = dict(l=68.6, w=53.3, t=1.6,
           agujeros=[(13.97, 2.54), (15.24, 50.8), (66.04, 7.62), (66.04, 35.56)],
           usb=dict(x0=-6.35, l=16.3, y0=31.75, w=12.1, h=10.9),
           dc=dict(x0=-1.8, l=14.2, y0=3.3, w=8.9, h=11.0))
PERF = dict(l=70.0, w=50.0, t=1.6, insert=2.5)
HX = dict(l=34.0, w=21.0, t=1.6)
MT = dict(l=37.0, w=17.0, t=1.6)

L_EXT, W_EXT, H_EXT = L_INT + 2 * PARED, W_INT + 2 * PARED, H_INT + PISO
BOSS_C = [(BOSS_D / 2, BOSS_D / 2), (L_INT - BOSS_D / 2, BOSS_D / 2),
          (BOSS_D / 2, W_INT - BOSS_D / 2), (L_INT - BOSS_D / 2, W_INT - BOSS_D / 2)]
FIJACION = [(40.0, 6.0), (118.0, 6.0), (62.0, W_INT - 5.0), (92.0, W_INT - 5.0)]


def caja_cerrada(l, w, h, r):
    return cq.Workplane("XY").box(l, w, h, centered=False).edges("|Z").fillet(r)


# ================================ BASE ====================================
def base():
    # sólido exterior y vaciado (el origen queda en la esquina interior del piso)
    b = caja_cerrada(L_EXT, W_EXT, H_EXT, R_EXT).translate((-PARED, -PARED, -PISO))
    hueco = caja_cerrada(L_INT, W_INT, H_INT + 1, R_EXT - PARED * 0.6)
    b = b.cut(hueco)

    # pilares de esquina con inserto M3 (unidos a las paredes)
    for (x, y) in BOSS_C:
        p = cq.Workplane("XY").circle(BOSS_D / 2).extrude(H_INT).translate((x, y, 0))
        # se extiende hacia las dos paredes para que quede soldado a ellas
        sx = -1 if x < L_INT / 2 else 1
        sy = -1 if y < W_INT / 2 else 1
        p = p.union(cq.Workplane("XY").box(BOSS_D / 2 + 0.5, BOSS_D / 2 + 0.5, H_INT, centered=False)
                    .translate((x if sx > 0 else x - BOSS_D / 2 - 0.5, y if sy > 0 else y - BOSS_D / 2 - 0.5, 0)))
        b = b.union(p)
        b = b.cut(cq.Workplane("XY").circle(INSERTO_D / 2).extrude(INSERTO_H + 0.5)
                  .translate((x, y, H_INT - INSERTO_H)))

    # pilares del Arduino y de la placa perforada, con tuerca M3 cautiva por abajo
    pilares = [(UNO_X + ax, UNO_Y + ay, STANDOFF_H) for ax, ay in UNO["agujeros"]]
    i = PERF["insert"]
    pilares += [(PERF_X + px, PERF_Y + py, PERF_H) for px in (i, PERF["l"] - i) for py in (i, PERF["w"] - i)]
    for (x, y, h) in pilares:
        b = b.union(cq.Workplane("XY").circle(STANDOFF_D / 2).extrude(h).translate((x, y, 0)))
        b = b.cut(cq.Workplane("XY").circle(3.3 / 2).extrude(h + PISO + 1).translate((x, y, -PISO - 0.5)))
        b = b.cut(cq.Workplane("XY").polygon(6, TUERCA_M3 / 0.866).extrude(2.6).translate((x, y, -PISO - 0.01)))

    # rieles deslizantes: ambos se abren hacia la zona libre del medio
    b = b.union(riel(HX_X, HX_Y, HX, abierto="+x"))
    b = b.union(riel(MT_X, MT_Y, MT, abierto="-x"))

    # fijación a la mesa: agujero avellanado para tornillo de madera
    for (x, y) in FIJACION:
        b = b.cut(cq.Workplane("XY").circle(4.6 / 2).extrude(PISO + 1).translate((x, y, -PISO - 0.5)))
        b = b.cut(cq.Solid.makeCone(4.6 / 2, 9.0 / 2, 2.2, cq.Vector(x, y, -2.2 + 0.01), cq.Vector(0, 0, 1)))

    # pared izquierda (x=0): calados para el USB-B y el jack DC del Arduino
    z_pcb = STANDOFF_H + UNO["t"]
    for k in ("usb", "dc"):
        c = UNO[k]
        b = b.cut(cq.Workplane("XY").box(PARED + 2, c["w"] + 2 * 1.0, c["h"] + 2 * 1.0, centered=False)
                  .translate((-PARED - 1, UNO_Y + c["y0"] - 1.0, z_pcb - 1.0)))

    # pared derecha (x=L): ranura en U abierta hacia la tapa para los cables
    b = b.cut(cq.Workplane("XY").box(PARED + 2, RANURA_Y1 - RANURA_Y0, RANURA_PROF + 1, centered=False)
              .translate((L_INT - 1, RANURA_Y0, H_INT - RANURA_PROF)))

    # pared trasera (y=W): prensaestopa PG7 para la entrada de 5 V
    b = b.cut(cq.Workplane("XZ").circle(PG7_D / 2).extrude(-(PARED + 2)).translate((PG7_X, W_INT - 1, PG7_Z)))

    # rebaje para la etiqueta en la pared frontal (0,6 mm)
    b = b.cut(cq.Workplane("XY").box(60, 0.6, 12, centered=False).translate((L_INT / 2 - 30, -PARED - 0.01, 14)))
    return b


def riel(x0, y0, m, abierto="+x"):
    """Dos rieles con ranura para el PCB del módulo y un tope en el extremo cerrado.
    El módulo entra deslizando por el extremo abierto y se saca igual: sin tornillos."""
    alto, ancho, z_pcb, lip = 6.0, 3.0, 3.0, 1.2
    largo = m["l"] + 1.0
    w = m["w"] + 2 * HOLGURA
    r = cq.Workplane("XY")
    for lado in (0, 1):
        y = y0 - ancho + lip if lado == 0 else y0 + w - lip
        bloque = cq.Workplane("XY").box(largo, ancho, alto, centered=False).translate((x0, y, 0))
        ranura_y = y + ancho - lip if lado == 0 else y
        bloque = bloque.cut(cq.Workplane("XY").box(largo + 1, lip, m["t"] + 0.3, centered=False)
                            .translate((x0 - 0.5, ranura_y, z_pcb)))
        r = r.union(bloque)
    xt = x0 - 2.0 if abierto == "+x" else x0 + largo
    tope = cq.Workplane("XY").box(2.0, w + 2 * (ancho - lip), alto, centered=False).translate((xt, y0 - ancho + lip, 0))
    return r.union(tope)


# ================================ TAPA ====================================
def tapa():
    t = caja_cerrada(L_EXT, W_EXT, TAPA, R_EXT).translate((-PARED, -PARED, H_INT))
    # faldón que centra la tapa dentro de las paredes (con holgura)
    fl, fw, fh, fe = L_INT - 2 * HOLGURA, W_INT - 2 * HOLGURA, 2.5, 1.6
    falda = caja_cerrada(fl, fw, fh, R_EXT - PARED).cut(
        caja_cerrada(fl - 2 * fe, fw - 2 * fe, fh + 1, max(R_EXT - PARED - fe, 0.5)).translate((fe, fe, -0.5)))
    falda = falda.translate((HOLGURA, HOLGURA, H_INT - fh))
    # el faldón no debe chocar con los pilares de esquina
    for (x, y) in BOSS_C:
        falda = falda.cut(cq.Workplane("XY").circle(BOSS_D / 2 + 1.5).extrude(fh + 1).translate((x, y, H_INT - fh - 0.5)))
    t = t.union(falda)
    # lengüeta que cierra parte de la ranura de cables (deja 8 mm libres)
    t = t.union(cq.Workplane("XY").box(PARED - HOLGURA, RANURA_Y1 - RANURA_Y0 - 2 * HOLGURA, LENGUETA, centered=False)
                .translate((L_INT + HOLGURA, RANURA_Y0 + HOLGURA, H_INT - LENGUETA)))
    # tornillos M3 avellanados
    for (x, y) in BOSS_C:
        t = t.cut(cq.Workplane("XY").circle(TORN_D / 2).extrude(TAPA + 2).translate((x, y, H_INT - 1)))
        t = t.cut(cq.Solid.makeCone(TORN_D / 2, AVELL_D / 2, (AVELL_D - TORN_D) / 2,
                                    cq.Vector(x, y, H_INT + TAPA - (AVELL_D - TORN_D) / 2 + 0.01), cq.Vector(0, 0, 1)))
    # ventilación sobre el MT3608 y el regulador del Arduino
    for k in range(5):
        t = t.cut(cq.Workplane("XY").box(30, 2.0, TAPA + 2, centered=False)
                  .translate((MT_X + 3, MT_Y - 2 + k * 4.5, H_INT - 1)))
    # rebaje para la etiqueta de la tapa
    t = t.cut(cq.Workplane("XY").box(70, 22, 0.6, centered=False).translate((PERF_X - 5, 30, H_INT + TAPA - 0.6 + 0.01)))
    return t


# ========================= COMPONENTES (gemelo 3D) =========================
def bloque(l, w, h, x, y, z):
    return cq.Workplane("XY").box(l, w, h, centered=False).translate((x, y, z))


def arduino():
    z = STANDOFF_H
    pcb = bloque(UNO["l"], UNO["w"], UNO["t"], UNO_X, UNO_Y, z)
    for ax, ay in UNO["agujeros"]:
        pcb = pcb.cut(cq.Workplane("XY").circle(1.6).extrude(5).translate((UNO_X + ax, UNO_Y + ay, z - 1)))
    zt = z + UNO["t"]
    partes = [pcb]
    for k in ("usb", "dc"):
        c = UNO[k]
        partes.append(bloque(c["l"], c["w"], c["h"], UNO_X + c["x0"], UNO_Y + c["y0"], zt))
    partes += [bloque(48.0, 2.5, 8.5, UNO_X + 17.0, UNO_Y + 50.3, zt),   # header digital
               bloque(40.0, 2.5, 8.5, UNO_X + 26.0, UNO_Y + 0.6, zt),    # header de poder y analógico
               bloque(35.0, 9.5, 4.0, UNO_X + 30.0, UNO_Y + 18.0, zt)]   # ATmega328P
    return partes


def placa_perforada():
    z = PERF_H
    i = PERF["insert"]
    pcb = bloque(PERF["l"], PERF["w"], PERF["t"], PERF_X, PERF_Y, z)
    for px in (i, PERF["l"] - i):
        for py in (i, PERF["w"] - i):
            pcb = pcb.cut(cq.Workplane("XY").circle(1.6).extrude(5).translate((PERF_X + px, PERF_Y + py, z - 1)))
    zt = z + PERF["t"]
    partes = [pcb]
    # borneras KF301 hacia la ranura de cables (6 de 2 polos en el borde +x, 2 en el borde +y)
    for k in range(4):
        partes.append(bloque(7.5, 10.2, 10.0, PERF_X + PERF["l"] - 8.5, PERF_Y + 4 + k * 10.8, zt))
    for k in range(2):
        partes.append(bloque(10.2, 7.5, 10.0, PERF_X + 30 + k * 11, PERF_Y + PERF["w"] - 8.5, zt))
    # conectores de servos (4 x 3 pines) y condensador de 1000 µF
    partes.append(bloque(10.2, 7.7, 8.5, PERF_X + 30, PERF_Y + 6, zt))
    partes.append(bloque(10.2, 7.7, 8.5, PERF_X + 30, PERF_Y + 16, zt))
    partes.append(cq.Workplane("XY").circle(5.0).extrude(20.0).translate((PERF_X + 15, PERF_Y + 35, zt)))
    return partes


def modulo(x0, y0, m, extras):
    z = 3.0
    partes = [bloque(m["l"], m["w"], m["t"], x0, y0 + HOLGURA, z)]
    for (l, w, h, dx, dy) in extras:
        partes.append(bloque(l, w, h, x0 + dx, y0 + HOLGURA + dy, z + m["t"]))
    return partes


def componentes():
    """Diccionario nombre -> (lista de sólidos, color RGB)."""
    return {
        "Arduino UNO R3": (arduino(), (0.0, 0.45, 0.65)),
        "Placa perforada + borneras": (placa_perforada(), (0.55, 0.42, 0.25)),
        "HX711": (modulo(HX_X, HX_Y, HX, [(10, 6.5, 1.6, 12, 7), (10.2, 2.5, 8.5, 1, 9), (2.5, 10.2, 8.5, 30, 5)]),
                  (0.10, 0.50, 0.20)),
        "MT3608": (modulo(MT_X, MT_Y, MT, [(7, 7, 4, 15, 5), (9.5, 4.5, 10, 3, 6), (3, 3, 1.2, 25, 7)]),
                   (0.10, 0.25, 0.60)),
    }


# ================================ SALIDAS =================================
def exportar():
    os.makedirs(os.path.join(SALIDA, "stl"), exist_ok=True)
    b, t = base(), tapa()
    asm = cq.Assembly(name="SCB_caja_control")
    asm.add(b, name="Base caja", color=cq.Color(0.86, 0.86, 0.84, 1))
    asm.add(t, name="Tapa", color=cq.Color(0.95, 0.75, 0.10, 1))
    for nombre, (solidos, rgb) in componentes().items():
        sub = cq.Assembly(name=nombre)
        for k, s in enumerate(solidos):
            sub.add(s, name=f"{nombre} {k + 1}", color=cq.Color(*rgb, 1))
        asm.add(sub, name=nombre)
    asm.export(os.path.join(SALIDA, "SCB_caja_control_gemelo.step"))
    cq.exporters.export(b, os.path.join(SALIDA, "stl", "caja_base.stl"), tolerance=0.05, angularTolerance=0.2)
    # la tapa se imprime boca abajo
    t_imp = t.rotate((0, 0, 0), (1, 0, 0), 180)
    cq.exporters.export(t_imp, os.path.join(SALIDA, "stl", "caja_tapa.stl"), tolerance=0.05, angularTolerance=0.2)
    return b, t


if __name__ == "__main__":
    b, t = exportar()
    print("Base:", [round(v, 1) for v in b.val().BoundingBox().toTuple()[:6]] if hasattr(b.val().BoundingBox(), "toTuple") else "")
    print("Listo: SCB_caja_control_gemelo.step y stl/")
