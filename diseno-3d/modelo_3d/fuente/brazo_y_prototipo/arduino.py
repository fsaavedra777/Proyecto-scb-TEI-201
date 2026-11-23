"""Soporte para Arduino UNO (pieza 18) y un UNO simplificado de referencia.
Marco de la placa: origen en la esquina inferior izquierda del PCB (lado del USB y el jack en x = 0),
x a lo largo de 68,58 mm, y a lo largo de 53,34 mm. Medidas del dibujo oficial del UNO R3."""
import cadquery as cq
from pathlib import Path
RAIZ = Path(__file__).resolve().parents[2]          # carpeta modelo_3d del repositorio
OUT = str(RAIZ / "salida" / "base")

PCB_X, PCB_Y, PCB_T = 68.58, 53.34, 1.6
AGUJEROS = [(13.97, 2.54), (15.24, 50.80), (66.04, 7.62), (66.04, 35.56)]
PISO, PILAR, GAP, MURO, H_MURO = 3.0, 6.0, 1.0, 2.0, 8.5
Z_PCB = PISO + PILAR                      # cara inferior de la placa (9 mm)
X0, X1 = -GAP - MURO, PCB_X + GAP + MURO  # exterior de la bandeja
Y0, Y1 = -GAP - MURO, PCB_Y + GAP + MURO
OREJA = 10.0
TORN_MDF = [(X0 - OREJA / 2, Y0 + 7), (X0 - OREJA / 2, Y1 - 7), (X1 + OREJA / 2, Y0 + 7), (X1 + OREJA / 2, Y1 - 7)]

def caja(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))

def cz(x, y, d, z0, h):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(d / 2).extrude(h)

def soporte():
    s = caja(X0, X1, Y0, Y1, 0, PISO).edges("|Z").fillet(3)
    muro = caja(X0, X1, Y0, Y1, 0, H_MURO).edges("|Z").fillet(3).cut(caja(X0 + MURO, X1 - MURO, Y0 + MURO, Y1 - MURO, -1, H_MURO + 1))
    s = s.union(muro)
    for (y0, y1) in ((1.0, 15.0), (30.0, 46.0)):          # pasos del jack y del USB en el muro izquierdo
        s = s.cut(caja(X0 - 1, X0 + MURO + 0.5, y0, y1, PISO, H_MURO + 1))
    s = s.cut(caja(X1 - MURO - 0.5, X1 + 1, 18, 36, PISO, H_MURO + 1))   # paso de cables a la derecha
    for x, y in AGUJEROS:
        s = s.union(cz(x, y, 6.0, 0, Z_PCB))
    for x, y in AGUJEROS:
        s = s.cut(cz(x, y, 2.7, 1.0, Z_PCB))               # M3 autorroscante
    for x0, x1 in ((X0 - OREJA, X0 + 1), (X1 - 1, X1 + OREJA)):
        for (yc) in (Y0 + 7, Y1 - 7):
            s = s.union(caja(x0, x1, yc - 7, yc + 7, 0, PISO).edges("|Z").edges(">X or <X").fillet(3))
    for x, y in TORN_MDF:
        s = s.cut(cz(x, y, 4.0, -1, 6))
        s = s.cut(cq.Workplane("XY").workplane(offset=PISO - 2.0).center(x, y).circle(2.0).workplane(offset=2.01).circle(4.1).loft())
    for i, (x0, x1) in enumerate(((20, 30), (36, 46))):    # ventanas en el piso (ahorran material y dejan pasar amarras)
        s = s.cut(caja(x0, x1, 14, 40, -1, PISO + 1).edges("|Z").fillet(2))
    return s

def arduino_ref():
    """UNO simplificado, apoyado con su cara inferior en z = 0. Devuelve (pcb, piezas negras, piezas metalicas)."""
    pcb = caja(0, PCB_X, 0, PCB_Y, 0, PCB_T).edges("|Z").fillet(1.5)
    for x, y in AGUJEROS:
        pcb = pcb.cut(cz(x, y, 3.2, -1, 4))
    t = PCB_T
    negro = (caja(-1.8, 12.4, 3.3, 12.3, t, t + 11)                                     # jack
             .union(caja(17.5, 43.2, 49.5, 52.1, t, t + 8.5)).union(caja(44.5, 64.8, 49.5, 52.1, t, t + 8.5))
             .union(caja(27.9, 48.3, 1.3, 3.8, t, t + 8.5)).union(caja(50.8, 66.0, 1.3, 3.8, t, t + 8.5))
             .union(caja(29.0, 65.0, 14.5, 24.5, t, t + 6.0)))                            # ATmega en su zocalo
    metal = caja(-6.35, 9.9, 32.1, 44.1, t, t + 10.9)                                   # USB-B
    return pcb, negro, metal

if __name__ == "__main__":
    import trimesh, os
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.StlAPI import StlAPI_Writer
    s = soporte().val()
    bb = s.BoundingBox()
    print("soporte", round(bb.xlen, 1), "x", round(bb.ylen, 1), "x", round(bb.zlen, 1), "mm, vol", round(s.Volume() / 1000, 1), "cm3, valido", s.isValid())
    s2 = s.translate(cq.Vector(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, 0))
    os.makedirs(f"{OUT}/imprimir", exist_ok=True)
    BRepMesh_IncrementalMesh(s2.wrapped, 0.02, False, 0.2, True)
    w = StlAPI_Writer(); w.ASCIIMode = False; w.Write(s2.wrapped, f"{OUT}/imprimir/18_soporte_arduino_UNO_x1.stl")
    cq.exporters.export(cq.Workplane().add(s), f"{OUT}/18_soporte_arduino_UNO.step")
    m = trimesh.load(f"{OUT}/imprimir/18_soporte_arduino_UNO_x1.stl", force="mesh")
    print("stl", m.extents.round(1).tolist(), "estanca", m.is_watertight)
    # choque placa/soporte
    pcb, negro, metal = arduino_ref()
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    for nom, p in (("pcb", pcb), ("negro", negro), ("metal", metal)):
        q = p.translate((0, 0, Z_PCB)).val()
        c = BRepAlgoAPI_Common(s.wrapped, q.wrapped); g = GProp_GProps(); BRepGProp.VolumeProperties_s(c.Shape(), g)
        print("choque soporte-", nom, round(g.Mass(), 2), "mm3")
