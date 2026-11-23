"""Brazo SCB v3: 3 x MG996R (base, hombro, codo) + SG90 en la pinza v2 ya impresa.
Mundo: mm, X derecha, Y adelante, Z arriba, tablero en z = 0, eje de la base en el origen."""
import math, json, os
import numpy as np
import cadquery as cq
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer

from pathlib import Path
RAIZ = Path(__file__).resolve().parents[2]          # carpeta modelo_3d del repositorio
OUT = str(RAIZ / "salida" / "brazo")                # aqui quedan los STEP y STL generados
VIEJO = str(RAIZ / "fuente" / "referencia" / "Robot_SCB_para_Fusion.step")   # pinza, muñeca y estacion
for _d in ("stl", "imprimir"): os.makedirs(f"{OUT}/{_d}", exist_ok=True)
# MG996R (marco propio: eje +z en el origen, base en z=0, cuerpo hacia -y)
L, WD, H_EAR, EAR_T, EAR_L, CASE, BOSS, SPL, OFF, FACE = 40.7, 19.7, 28.0, 2.5, 54.5, 37.0, 39.5, 43.0, 10.25, 44.0
HX, HY = 5.0, 24.75            # agujeros de las orejas (49,5 x 10)
VX, VY = 10.15, 20.65          # media ventana (20,3 x 41,3)
TH_S, TH_F = 80.0, -12.0       # pose del dibujo
LS, LF = 70.0, 76.0            # eje hombro-codo, eje codo-agujero de la muñeca

def T(x=0, y=0, z=0):
    M = np.eye(4); M[:3, 3] = [x, y, z]; return M
def Rx(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1.0]])
def Rz(d):
    c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]])
def R4(cols):
    M = np.eye(4); M[:3, :3] = np.array(cols, float).T; return M
def shp(x):
    if isinstance(x, cq.Workplane):
        v = x.vals(); return v[0] if len(v) == 1 else cq.Compound.makeCompound(v)
    return x
def mover(x, M):
    t = gp_Trsf(); t.SetValues(*[float(v) for v in M[0]], *[float(v) for v in M[1]], *[float(v) for v in M[2]])
    return cq.Shape.cast(BRepBuilderAPI_Transform(shp(x).wrapped, t, True).Shape())
def caja(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))
def cz(x, y, d, z0, h):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(d / 2).extrude(h)
def cx(y, z, d, x0, h):
    return cq.Workplane("YZ").workplane(offset=x0).center(y, z).circle(d / 2).extrude(h)

def mg996r():
    s = caja(-WD / 2, WD / 2, -OFF - L / 2, -OFF + L / 2, 0, CASE).edges("|Z").fillet(1.0)
    orej = caja(-WD / 2, WD / 2, -OFF - EAR_L / 2, -OFF + EAR_L / 2, H_EAR, H_EAR + EAR_T)
    for sx in (-1, 1):
        for sy in (-1, 1):
            orej = orej.cut(cz(sx * HX, -OFF + sy * HY, 4.5, H_EAR - 1, 5))
    return s.union(orej).union(cz(0, 0, 13, CASE, BOSS - CASE)).union(cz(0, 0, 5.8, BOSS, SPL - BOSS))
def disco():
    return cz(0, 0, 21, FACE - 2.5, 2.5).union(cz(0, 0, 9, FACE - 6, 3.5)).cut(cz(0, 0, 3, FACE - 7, 8))

# ---------------- piezas nuevas ----------------
def base():
    yc = -OFF
    s = caja(-32, 32, yc - 36, yc + 36, 0, 30).edges("|Z").fillet(4)
    s = s.cut(caja(-28, 28, yc - 32, yc + 32, -1, 25))
    s = s.cut(caja(-VX, VX, yc - VY, yc + VY, 20, 31))
    for sx in (-1, 1):
        for sy in (-1, 1):
            s = s.cut(cz(sx * HX, yc + sy * HY, 4.3, 20, 12))
    for sx in (-1, 1):                                    # aletas para atornillar al tablero (con cuña a 45 grados)
        al = (cq.Workplane("XZ").polyline([(31, 0), (44, 0), (44, 4), (32, 16), (31, 16)]).close().extrude(-18)
              .translate((0, -9, 0)))
        for yy in (yc - 22, yc + 22):
            a = al.translate((0, yy, 0)).cut(cz(38.5, yy, 4.5, -1, 20)).cut(cz(38.5, yy, 9, 4, 20))
            s = s.union(a if sx > 0 else a.mirror("YZ"))
    s = s.cut(caja(-6, 6, yc - 40, yc - 30, -1, 9))       # salida del cable
    return s
ZT = 2 + FACE                                              # cara inferior de la torreta (46)
ZS = ZT + 5 + 6 + WD / 2 + 0.3                             # altura del eje del hombro
XW = 11.0                                                  # cara +X de la pared de la torreta
def torreta():
    yc = -OFF
    s = caja(-28, 36, -46, 26, ZT, ZT + 5).edges("|Z").fillet(6)
    pared = caja(XW - 5, XW, yc - 31.75, yc + 31.75, ZT, ZT + 38)
    pared = pared.edges("|X").edges(">Z").fillet(4)
    s = s.union(pared)
    for y0 in (yc - 31.75, yc + 27.75):                    # refuerzos a los dos lados de la pared
        for pts in ([(XW - 0.5, ZT + 4), (XW + 15, ZT + 4), (XW - 0.5, ZT + 30)], [(XW - 4.5, ZT + 4), (XW - 23, ZT + 4), (XW - 4.5, ZT + 30)]):
            s = s.union(cq.Workplane("XZ").polyline(pts).close().extrude(-4).translate((0, y0, 0)))
    s = s.cut(caja(XW - 6, XW + 1, yc - VY, yc + VY, ZS - VX, ZS + VX))
    for sy in (-1, 1):
        for sz in (-1, 1):
            s = s.cut(cx(yc + sy * HY, ZS + sz * HX, 4.3, XW - 6, 8))
    return s.cut(cz(0, 0, 9, ZT - 1, 8))
def eslabon():
    """Marco propio: u = X (eje del hombro en 0, eje del codo en LS), v = Y, espesor en Z de 0 a 6."""
    uc = LS - OFF
    s = (cq.Workplane("XY").polyline([(0, -14), (30, -17), (LS + 20, -17), (LS + 20, 17), (30, 17), (0, 14)]).close().extrude(6)
         .edges("|Z").edges(">X").fillet(5)).union(cz(0, 0, 28, 0, 6))
    s = s.cut(caja(uc - VY, uc + VY, -VX, VX, -1, 7)).cut(cz(0, 0, 9, -1, 8))
    for su in (-1, 1):
        for sv in (-1, 1):
            s = s.cut(cz(uc + su * HY, sv * HX, 4.3, -1, 8))
    return s
def antebrazo():
    """Marco propio: a = X (eje del codo en 0, agujero de la muñeca en LF), b = Y, espesor en Z de 0 a 10."""
    s = (cq.Workplane("XY").polyline([(0, -15), (58, -8), (LF + 8, -8), (LF + 8, 8), (58, 8), (0, 15)]).close().extrude(10)
         ).union(cz(0, 0, 30, 0, 10))
    s = s.cut(cz(0, 0, 9, -1, 12)).cut(cz(LF, 0, 3.3, -1, 12))
    return s.cut(cq.Workplane("XY").center(37, 0).slot2D(26, 8, 0).extrude(12).translate((0, 0, -1)))

# ---------------- piezas ya impresas (del STEP anterior) ----------------
def leer_viejo():
    doc = TDocStd_Document(TCollection_ExtendedString("d"))
    r = STEPCAFControl_Reader(); r.SetNameMode(True); r.ReadFile(VIEJO); r.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()); raiz = TDF_LabelSequence(); st.GetFreeShapes(raiz)
    out = {}
    def rec(lab, loc):
        comps = TDF_LabelSequence(); XCAFDoc_ShapeTool.GetComponents_s(lab, comps)
        for i in range(1, comps.Length() + 1):
            c = comps.Value(i); ref = c
            if XCAFDoc_ShapeTool.IsReference_s(c):
                ref = TDF_Label(); XCAFDoc_ShapeTool.GetReferredShape_s(c, ref)
            nm = TDataStd_Name(); n = "?"
            if c.FindAttribute(TDataStd_Name.GetID_s(), nm): n = nm.Get().ToExtString()
            l2 = loc.Multiplied(XCAFDoc_ShapeTool.GetLocation_s(c))
            if XCAFDoc_ShapeTool.IsAssembly_s(ref): rec(ref, l2)
            else: out[n] = cq.Shape.cast(XCAFDoc_ShapeTool.GetShape_s(ref).Moved(l2))
    rec(raiz.Value(1), TopLoc_Location()); return out

# ---------------- armado ----------------
P = []   # (nombre, codigo, color, forma, grupo de explosion)
def poner(nombre, codigo, color, forma, grupo): P.append((nombre, codigo, color, shp(forma), grupo))
GR, AZ, AZC, NEG, BL, TOR, MDF = "#cfd6df", "#5b95e6", "#7eaef0", "#2a2f38", "#eef1f5", "#3b434d", "#c9a47c"
NV = "#f2b950"   # piezas nuevas

servo, disc = mg996r(), disco()
poner("Tablero_MDF", None, MDF, caja(-90, 90, -70, 250, -9, 0).edges("|Z").fillet(8), "tablero")
poner("10_Base", "10", NV, base(), "base")
M1 = T(0, 0, 2)
poner("M1_MG996R_base", "M1", NEG, mover(servo, M1), "m1"); poner("D1_Disco_base", "D1", BL, mover(disc, M1), "d1")
poner("11_Torreta", "11", NV, torreta(), "torreta")
M2 = T(XW - H_EAR, 0, ZS) @ R4([[0, 0, -1], [0, 1, 0], [1, 0, 0]])
poner("M2_MG996R_hombro", "M2", NEG, mover(servo, M2), "m2"); poner("D2_Disco_hombro", "D2", BL, mover(disc, M2), "d2")
XL = XW - H_EAR + FACE                                     # cara -X del eslabon (27)
c, s_ = math.cos(math.radians(TH_S)), math.sin(math.radians(TH_S))
u, v = (0, c, s_), (0, -s_, c)
M_L = T(XL, 0, ZS) @ R4([u, v, (1, 0, 0)])
poner("12_Eslabon_hombro", "12", NV, mover(eslabon(), M_L), "eslabon")
E = np.array([0, LS * c, ZS + LS * s_])
M3 = T(XL + H_EAR, E[1], E[2]) @ R4([v, u, (-1, 0, 0)])
poner("M3_MG996R_codo", "M3", NEG, mover(servo, M3), "m3"); poner("D3_Disco_codo", "D3", BL, mover(disc, M3), "d3")
XA = XL + H_EAR - FACE - 10                                # cara -X del antebrazo (1)
cf, sf = math.cos(math.radians(TH_F)), math.sin(math.radians(TH_F))
M_A = T(XA, E[1], E[2]) @ R4([(0, cf, sf), (0, -sf, cf), (1, 0, 0)])
poner("13_Antebrazo", "13", NV, mover(antebrazo(), M_A), "antebrazo")

viejo = leer_viejo()
bb = viejo["REF_Tornillo_munieca"].BoundingBox()
E0 = np.array([0, 100 * math.cos(math.radians(75)), 77 + 100 * math.sin(math.radians(75))])
th0 = math.degrees(math.atan2((bb.zmin + bb.zmax) / 2 - E0[2], (bb.ymin + bb.ymax) / 2 - E0[1]))
M_old = T(*E0) @ Rx(th0)
M_G = T(0, E[1], E[2]) @ Rx(TH_F) @ T(XA + 21.7, LF - 80.0, 0) @ np.linalg.inv(M_old)
for clave, nombre, cod, col, grupo in (("NUEVA_Munieca", "05_Munieca", "05", GR, "munieca"),
        ("REF_Tornillo_munieca", "T4_Tornillo_munieca_M3x20", None, TOR, "munieca"),
        ("REF_Tornillos_pinza_M3x12", "T5_Tornillos_pinza_M3x12", None, TOR, "t5"),
        ("P1_Chasis_Pinza", "01_Chasis_pinza", "A", AZC, "pinza"), ("P2_Dedo_Izquierdo_Motriz_FSR", "02_Dedo_izquierdo", None, AZ, "pinza"),
        ("P3_Dedo_Derecho", "03_Dedo_derecho", None, AZ, "pinza"), ("P4_Disco_FSR_TPU", "04_Disco_FSR", None, NEG, "pinza"),
        ("REF_Servo_pinza_SG90", "S4_SG90_pinza", "S4", "#2b3a8a", "pinza"), ("REF_Brazo_servo_pinza", "Brazo_servo_pinza", None, BL, "pinza"),
        ("REF_Tornillo_dedo_M3x30", "T1_Tornillo_dedo_M3x30", None, TOR, "pinza"), ("REF_Golillas_tuerca_dedo", "T1_Golillas_tuerca", None, TOR, "pinza")):
    poner(nombre, cod, col, mover(viejo[clave], M_G), grupo)

# ---------------- exportar ----------------
def stl(forma, ruta, tol=0.03):
    BRepMesh_IncrementalMesh(forma.wrapped, tol, False, 0.2, True)
    w = StlAPI_Writer(); w.ASCIIMode = False; w.Write(forma.wrapped, ruta)
asm = cq.Assembly(name="Garra_SCB_v3_MG996R"); info = []
for i, (n, cod, col, f, g) in enumerate(P):
    h = col.lstrip("#"); asm.add(f, name=n, color=cq.Color(*[int(h[k:k + 2], 16) / 255 for k in (0, 2, 4)]))
    ruta = f"{OUT}/stl/{i:02d}_{n}.stl"; stl(f, ruta)
    b = f.BoundingBox()
    info.append({"nombre": n, "codigo": cod, "color": col, "grupo": g, "stl": ruta, "bbox": [round(x, 1) for x in (b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax)]})
asm.export(f"{OUT}/Garra_SCB_v3_MG996R.step")
json.dump({"partes": info, "E": E.tolist(), "ZS": ZS, "ZT": ZT}, open(f"{OUT}/partes.json", "w"), indent=1)
# piezas nuevas, orientadas para imprimir
imp = {"10_base_MG996R_x1.stl": mover(base(), T(0, 0, 30) @ Rx(180)),
       "11_torreta_MG996R_x1.stl": mover(torreta(), T(0, 0, -ZT)),
       "12_eslabon_hombro_MG996R_x1.stl": mover(eslabon(), Rz(45)),
       "13_antebrazo_MG996R_x1.stl": antebrazo()}
for n, f in imp.items():
    f = shp(f); b = f.BoundingBox()
    f = mover(f, T(-(b.xmin + b.xmax) / 2, -(b.ymin + b.ymax) / 2, -b.zmin)); stl(f, f"{OUT}/imprimir/{n}", 0.02)
    cq.exporters.export(cq.Workplane().add(f), f"{OUT}/imprimir/{n.replace('_x1.stl', '.step')}")
    b = f.BoundingBox(); print(f"{n:36s} {b.xlen:6.1f} x {b.ylen:6.1f} x {b.zlen:5.1f} mm  vol {f.Volume()/1000:.1f} cm3")
print("eje hombro z =", round(ZS, 1), "codo", E.round(1), "piezas", len(P))
# choques entre piezas
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
import itertools
for (n1, _, _, f1, _), (n2, _, _, f2, _) in itertools.combinations(P, 2):
    a, b = f1.BoundingBox(), f2.BoundingBox()
    if a.xmax < b.xmin or b.xmax < a.xmin or a.ymax < b.ymin or b.ymax < a.ymin or a.zmax < b.zmin or b.zmax < a.zmin: continue
    cm = BRepAlgoAPI_Common(f1.wrapped, f2.wrapped)
    if cm.IsDone():
        gp = GProp_GProps(); BRepGProp.VolumeProperties_s(cm.Shape(), gp)
        if gp.Mass() > 1: print(f"CHOQUE {gp.Mass():8.1f} mm3  {n1} <-> {n2}")
