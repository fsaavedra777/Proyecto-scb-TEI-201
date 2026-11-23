"""
componentes_externos.py — Volúmenes referenciales de los componentes que van FUERA de la caja.

Genera ../SCB_componentes_externos.step con un cuerpo por componente, alineados
en una fila (separados 30 mm), para arrastrarlos al ensamble del robot en Fusion
y completar el gemelo 3D: servos en el brazo, sensores en la estación, fuente en
la base MDF. Medidas de hojas de datos; verifíquenlas con un pie de metro.
"""
import os

import cadquery as cq

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def caja(l, w, h, x=0, y=0, z=0):
    return cq.Workplane("XY").box(l, w, h, centered=False).translate((x, y, z))


def cil(d, h, x=0, y=0, z=0, eje="Z"):
    w = cq.Workplane({"Z": "XY", "X": "YZ", "Y": "XZ"}[eje]).circle(d / 2).extrude(h)
    return w.translate((x, y, z))


def mg996r():
    cuerpo = caja(40.7, 19.7, 36.6)
    orejas = caja(54.5, 19.7, 2.5, -6.9, 0, 26.8)
    for x in (-6.9 + 2.25, 40.7 + 6.9 - 2.25):
        for y in (4.85, 19.7 - 4.85):
            orejas = orejas.cut(cil(4.3, 4, x, y, 26))
    eje = cil(5.8, 6.3, 10.25, 9.85, 36.6)
    return cuerpo.union(orejas).union(eje).union(cil(13, 2, 10.25, 9.85, 36.6))


def sg90():
    cuerpo = caja(22.8, 12.2, 22.5)
    orejas = caja(32.2, 12.2, 2.5, -4.7, 0, 15.9)
    return cuerpo.union(orejas).union(cil(4.8, 4.0, 6.1, 6.1, 22.5)).union(cil(11.8, 4.0, 6.1, 6.1, 22.5).intersect(caja(12, 12.2, 4, 0, 0, 22.5)))


def hcsr04():
    pcb = caja(45, 20, 1.6)
    t = pcb.union(cil(16, 12, 9.5, 10, 1.6)).union(cil(16, 12, 35.5, 10, 1.6))
    return t.union(caja(10.2, 2.5, 8.5, 17.4, -2.5, -8.5 + 1.6))


def proximidad(d, largo, cara):
    cuerpo = cil(d, largo)
    tuercas = cil(d + 7, 4, 0, 0, largo * 0.35).union(cil(d + 7, 4, 0, 0, largo * 0.55))
    cable = cil(4, 15, 0, 0, -15)
    return cuerpo.union(tuercas).union(cable).union(cil(d - 1, cara, 0, 0, largo))


def celda():
    barra = caja(80, 12.7, 12.7)
    for x in (5, 20, 60, 75):
        barra = barra.cut(cil(4.2, 14, x, 6.35, -0.5))
    return barra.cut(cil(11, 14, 33.5, 6.35, -0.5).union(cil(11, 14, 46.5, 6.35, -0.5)).union(caja(13, 11, 14, 33.5, 0.85, -0.5)))


def fsr402():
    return cil(18.3, 0.5).union(caja(25, 7, 0.4, 9, -3.5, 0)).union(caja(5, 7, 2.5, 34, -3.5, -1))


def fuente():
    cuerpo = caja(99, 82, 30)
    bornera = caja(9, 70, 12, 99, 6, 4)
    return cuerpo.union(bornera)


PIEZAS = [
    ("MG996R (base, hombro, codo)", mg996r, (0.15, 0.15, 0.15)),
    ("SG90 (pinza)", sg90, (0.10, 0.30, 0.70)),
    ("HC-SR04", hcsr04, (0.10, 0.45, 0.65)),
    ("LJ12A3-4-Z/BX inductivo M12", lambda: proximidad(12, 52, 4), (0.75, 0.75, 0.72)),
    ("LJC18A3-H-Z/BX capacitivo M18", lambda: proximidad(18, 52, 6), (0.85, 0.55, 0.15)),
    ("Celda de carga 1 kg", celda, (0.78, 0.80, 0.82)),
    ("FSR-402", fsr402, (0.20, 0.20, 0.20)),
    ("Fuente S-50-5 (5 V 10 A)", fuente, (0.70, 0.72, 0.74)),
]

if __name__ == "__main__":
    asm = cq.Assembly(name="SCB_componentes_externos")
    x = 0.0
    for nombre, fn, rgb in PIEZAS:
        s = fn()
        bb = s.val().BoundingBox()
        asm.add(s.translate((x - bb.xmin, -bb.ymin, -bb.zmin)), name=nombre, color=cq.Color(*rgb, 1))
        x += bb.xlen + 30
    asm.export(os.path.join(SALIDA, "SCB_componentes_externos.step"))
    print("Listo: SCB_componentes_externos.step")
