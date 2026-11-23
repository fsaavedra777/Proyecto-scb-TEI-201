"""Prototipo SCB completo sobre el tablero: brazo v3 (3 x MG996R + pinza SG90), estacion de sensado,
poste del HC-SR04 (pieza 19), soporte del Arduino (18), electronica, contenedores y patas (20).
Mundo: mm, origen en el eje del servo de la base sobre la cara superior del tablero, Y hacia la bandeja."""
import math, json, os, itertools
import numpy as np
import sys
import cadquery as cq
from pathlib import Path
RAIZ = Path(__file__).resolve().parents[2]          # carpeta modelo_3d del repositorio
sys.path.insert(0, str(Path(__file__).parent))

src = open(Path(__file__).with_name("modelo.py"), encoding="utf-8").read()
exec(src.split("# ---------------- armado ----------------")[0])
import arduino as ard

OUTP = str(RAIZ / "salida" / "prototipo")
os.makedirs(f"{OUTP}/imprimir", exist_ok=True)
os.makedirs(f"{OUTP}/stl", exist_ok=True)
TH_S = 85.0
P = []
def poner(nombre, codigo, color, forma, grupo):
    P.append((nombre, codigo, color, shp(forma), grupo))
GR, AZ, AZC, NEG, BL, TOR, MDF = "#cfd6df", "#5b95e6", "#7eaef0", "#2a2f38", "#eef1f5", "#3b434d", "#c9a47c"
NV, TEAL, MET = "#f2b950", "#4cc7b4", "#b9c0c9"

viejo = leer_viejo()
bb = viejo["REF_Tornillo_munieca"].BoundingBox()
E0 = np.array([0, 100 * math.cos(math.radians(75)), 77 + 100 * math.sin(math.radians(75))])
th0 = math.degrees(math.atan2((bb.zmin + bb.zmax) / 2 - E0[2], (bb.ymin + bb.ymax) / 2 - E0[1]))
M_old = T(*E0) @ Rx(th0)
XL = XW - H_EAR + FACE
XA = XL + H_EAR - FACE - 10
c, s_ = math.cos(math.radians(TH_S)), math.sin(math.radians(TH_S))
E = np.array([0, LS * c, ZS + LS * s_])

# ---- pose: centro de las almohadillas a media altura de la lata sobre la bandeja ----
Z_PISO = 10 + 12.7 + 3 + 4                      # soporte + celda + espaciador + piso de la bandeja
LATA_H = 62.0
def almohadillas(th_f):
    cf, sf = math.cos(math.radians(th_f)), math.sin(math.radians(th_f))
    a, b = LF + 114.09, -38.45
    return np.array([XA + 5, E[1] + a * cf - b * sf, E[2] + a * sf + b * cf])
lo, hi = -60.0, 20.0
for _ in range(60):
    m_ = (lo + hi) / 2
    if almohadillas(m_)[2] > Z_PISO + LATA_H / 2: hi = m_
    else: lo = m_
TH_F = (lo + hi) / 2
G = almohadillas(TH_F)
Xt, Yt = float(G[0]), float(G[1])
print(f"hombro {TH_S} grados, antebrazo {TH_F:.2f} grados, bandeja en x={Xt:.1f} y={Yt:.1f}")

# ---- brazo ----
servo, disc = mg996r(), disco()
poner("10_Base", "10", NV, base(), "brazo")
M1 = T(0, 0, 2)
poner("M1_MG996R_base", "M1", NEG, mover(servo, M1), "brazo"); poner("D1_Disco_base", None, BL, mover(disc, M1), "brazo")
poner("11_Torreta", "11", NV, torreta(), "brazo")
M2 = T(XW - H_EAR, 0, ZS) @ R4([[0, 0, -1], [0, 1, 0], [1, 0, 0]])
poner("M2_MG996R_hombro", "M2", NEG, mover(servo, M2), "brazo"); poner("D2_Disco_hombro", None, BL, mover(disc, M2), "brazo")
u, v = (0, c, s_), (0, -s_, c)
poner("12_Eslabon_hombro", "12", NV, mover(eslabon(), T(XL, 0, ZS) @ R4([u, v, (1, 0, 0)])), "brazo")
M3 = T(XL + H_EAR, E[1], E[2]) @ R4([v, u, (-1, 0, 0)])
poner("M3_MG996R_codo", "M3", NEG, mover(servo, M3), "brazo"); poner("D3_Disco_codo", None, BL, mover(disc, M3), "brazo")
cf, sf = math.cos(math.radians(TH_F)), math.sin(math.radians(TH_F))
poner("13_Antebrazo", "13", NV, mover(antebrazo(), T(XA, E[1], E[2]) @ R4([(0, cf, sf), (0, -sf, cf), (1, 0, 0)])), "brazo")
M_G = T(0, E[1], E[2]) @ Rx(TH_F) @ T(XA + 21.7, LF - 80.0, 0) @ np.linalg.inv(M_old)
for clave, nombre, cod, col in (("NUEVA_Munieca", "05_Munieca", "05", GR), ("REF_Tornillo_munieca", "T_Munieca_M3x20", None, TOR),
        ("REF_Tornillos_pinza_M3x12", "T_Pinza_M3x12", None, TOR), ("P1_Chasis_Pinza", "01_Chasis_pinza", "A", AZC),
        ("P2_Dedo_Izquierdo_Motriz_FSR", "02_Dedo_izquierdo", None, AZ), ("P3_Dedo_Derecho", "03_Dedo_derecho", None, AZ),
        ("P4_Disco_FSR_TPU", "04_Disco_FSR", None, NEG), ("REF_Servo_pinza_SG90", "S4_SG90_pinza", "S4", "#2b3a8a"),
        ("REF_Brazo_servo_pinza", "Brazo_servo_pinza", None, BL), ("REF_Tornillo_dedo_M3x30", "T_Dedo_M3x30", None, TOR),
        ("REF_Golillas_tuerca_dedo", "T_Dedo_golillas", None, TOR)):
    poner(nombre, cod, col, mover(viejo[clave], M_G), "brazo")

# ---- estacion de sensado (piezas del modelo anterior, trasladadas) ----
bt = viejo["08_Bandeja_Pesaje_Celda"].BoundingBox()
DESP = T(Xt - (bt.xmin + bt.xmax) / 2, Yt - (bt.ymin + bt.ymax) / 2, -45.0)
for clave, nombre, cod, col in (("08_Bandeja_Pesaje_Celda", "16_Bandeja", "16", TEAL), ("09_Soporte_Fijo_CeldaCarga", "17_Soporte_celda", "17", TEAL),
        ("07_Soporte_Proximidad_LJ12_LJC18", "15_Soporte_proximidad", "15", TEAL), ("06_Soporte_HC_SR04", "14_Soporte_HC_SR04", "14", TEAL),
        ("REF_Celda_cuerpo", "E3_Celda_de_carga", "E3", MET), ("REF_Celda_gel", "E3_Celda_gel", None, "#f4f4ef"),
        ("REF_Espaciador_bandeja", "Espaciador_bandeja", None, MET),
        ("REF_Inductivo_LJ12A3_cuerpo", "E4_Inductivo_LJ12A3", "E4", MET), ("REF_Inductivo_LJ12A3_cara", "E4_cara", None, "#f08a24"),
        ("REF_Capacitivo_LJC18A3_cuerpo", "E5_Capacitivo_LJC18A3", "E5", MET), ("REF_Capacitivo_LJC18A3_cara", "E5_cara", None, "#e85d3a"),
        ("REF_HC_SR04_placa", "E6_HC_SR04", "E6", "#1f63c6"), ("REF_HC_SR04_transductores", "E6_transductores", None, "#c9cfd6"),
        ("REF_HC_SR04_malla", "E6_malla", None, "#2a2f36"),
        ("REF_Residuo_lata", "Residuo_lata", None, "#dfe4ea"), ("REF_Residuo_lata_etiqueta", "Residuo_etiqueta", None, "#d64545")):
    poner(nombre, cod, col, mover(viejo[clave], DESP), "estacion")
Yb = Yt - 24.0
SENSORES = [(Xt - 20.5, Yb, 13.0, "LJ12A3"), (Xt + 12.5, Yb, 19.0, "LJC18A3")]
# Bandeja v2: ventana de 13,5 mm sobre el inductivo, que sube 4,7 mm (cara 0,5 mm bajo el piso de la bandeja).
# Con el piso de 4 mm de por medio el LJ12A3 quedaba a 5,2 mm de la lata: fuera de su alcance (4 mm en acero, menos en aluminio).
SUBE_E4, VENT_E4 = 4.7, 13.5
for i, (n, cod, col, f, g) in enumerate(P):
    if n == "16_Bandeja":
        P[i] = (n, cod, col, f.cut(shp(cz(Xt - 20.5, Yb, VENT_E4, 20, 20))), g)
    if n.startswith("E4_"):
        P[i] = (n, cod, col, f.translate(cq.Vector(0, 0, SUBE_E4)), g)

# ---- 19: poste del HC-SR04 (marco en U: la placa 14 baja por dos ranuras verticales) ----
Y_US = Yt + 65.0                                 # plano medio de la placa 14
Z_TOPE = Z_PISO + 35.0 + 13.0                    # borde superior de la placa 14 (haz a 35 mm del piso de la bandeja)
Z_RAN = Z_TOPE - 26.0                            # fondo de las ranuras = borde inferior de la placa 14
def poste():
    xc, yp = Xt, Y_US
    s = caja(xc - 42, xc + 42, yp - 12, yp + 22, 0, 4).edges("|Z").fillet(4)
    for sx in (-1, 1):
        x0, x1 = (xc + 23.5, xc + 32) if sx > 0 else (xc - 32, xc - 23.5)
        s = s.union(caja(x0, x1, yp - 7, yp + 14, 0, Z_TOPE).edges("|Z").edges(">Y").fillet(2))
        g0, g1 = (xc + 23.4, xc + 26.6) if sx > 0 else (xc - 26.6, xc - 23.4)
        s = s.cut(caja(g0, g1, yp - 2.3, yp + 2.3, Z_RAN, Z_TOPE + 1))
    s = s.union(caja(xc - 32, xc + 32, yp + 10, yp + 14, 0, 48))      # muro trasero, bajo la placa del sensor
    for sx in (-1, 1):
        for y in (yp - 6, yp + 17):
            x = xc + 37 * sx
            s = s.cut(cz(x, y, 4.0, -1, 6))
            s = s.cut(cq.Workplane("XY").workplane(offset=2.0).center(x, y).circle(2.0).workplane(offset=2.01).circle(4.1).loft())
    return s
poner("19_Poste_HC_SR04", "19", NV, poste(), "estacion")

# ---- 18: soporte del Arduino y electronica ----
ROT_A = -90.0                                    # USB y jack hacia el borde trasero
CA = (0.0, -112.0)                               # centro del soporte
cx0, cy0 = (ard.X0 + ard.X1) / 2, (ard.Y0 + ard.Y1) / 2
M_SA = T(CA[0], CA[1], 0) @ Rz(ROT_A) @ T(-cx0, -cy0, 0)
poner("18_Soporte_Arduino", "18", NV, mover(ard.soporte(), M_SA), "electronica")
pcb, negro, metal = ard.arduino_ref()
MA = M_SA @ T(0, 0, ard.Z_PCB)
poner("E1_Arduino_UNO", "E1", "#00878f", mover(pcb, MA), "electronica")
poner("E1_conectores", None, NEG, mover(negro, MA), "electronica")
poner("E1_USB", None, "#c9cfd6", mover(metal, MA), "electronica")
FUENTE = (-178.0, -66.0, -176.0, -88.0)          # x0, x1, y0, y1
poner("E7_Fuente_5V_10A", "E7", "#9aa3ad", caja(FUENTE[0], FUENTE[1], FUENTE[2], FUENTE[3], 0, 40).edges("|Z").fillet(2), "electronica")
PROTO = (58.0, 140.5, -150.0, -95.5)
pb = caja(PROTO[0], PROTO[1], PROTO[2], PROTO[3], 0, 9.5).edges("|Z").fillet(1.5)
for i in range(30):
    pb = pb.cut(caja(PROTO[0] + 3 + i * 2.54, PROTO[0] + 4.2 + i * 2.54, PROTO[2] + 8, PROTO[3] - 8, 8.5, 10))
poner("E8_Protoboard", "E8", "#f4f4f2", pb, "electronica")
HX = (Xt - 122.0, Xt - 88.0, Yt + 6.0, Yt + 27.0)
poner("E2_HX711", "E2", "#2e8b57", caja(HX[0], HX[1], HX[2], HX[3], 4, 5.6).union(caja(HX[0], HX[1], HX[2], HX[3], 0, 4).cut(caja(HX[0] + 3, HX[1] - 3, HX[2] + 3, HX[3] - 3, -1, 5))), "estacion")

# ---- contenedores ----
def contenedor(a=72.0, h=75.0, e=2.2):
    ext = caja(-a / 2, a / 2, -a / 2, a / 2, 0, h).edges("|Z").fillet(6)
    return ext.cut(caja(-a / 2 + e, a / 2 - e, -a / 2 + e, a / 2 - e, e, h + 1).edges("|Z").fillet(6 - e))
CONT = [("C1_Contenedor_metal", "C1", "#a9b3bf", 40.0, 150.0), ("C2_Contenedor_plastico", "C2", "#f3c447", 140.0, 150.0),
        ("C3_Contenedor_descarte", "C3", "#59626e", 180.0, 150.0)]
for nombre, cod, col, ang, r in CONT:
    a = math.radians(ang)
    poner(nombre, cod, col, mover(contenedor(), T(r * math.cos(a), r * math.sin(a), 0) @ Rz(ang - 90)), "contenedores")

# ---- tablero y patas (20) ----
TX0, TX1, TY0, TY1 = -200, 200, -200, 300        # MDF 400 x 500 x 9 mm
PASACABLES = (44.0, -75.0, 16.0)
for n, cod, col, f, g in P:                      # todo debe quedar dentro del tablero
    b = f.BoundingBox()
    if b.zmax > 0 and (b.xmin < TX0 + 5 or b.xmax > TX1 - 5 or b.ymin < TY0 + 5 or b.ymax > TY1 - 5): print("FUERA DEL TABLERO:", n)
tab = caja(TX0, TX1, TY0, TY1, -9, 0).edges("|Z").fillet(10)
M5_CELDA = [(Xt - 47.5, Yt), (Xt - 62.5, Yt)]     # cabezas de los M5 que sujetan la celda: se aprietan desde abajo
for x, y, d, _ in SENSORES + [PASACABLES + ("cables",)] + [(x, y, 10.0, "M5") for x, y in M5_CELDA]:
    tab = tab.cut(cz(x, y, d, -10, 12))
poner("Tablero_MDF_9mm", None, MDF, tab, "tablero")
H_PATA = 50.0
def pata():
    s = cz(0, 0, 30, 0, H_PATA).edges(">Z or <Z").chamfer(1.0)
    return s.cut(cz(0, 0, 20, -1, H_PATA - 8)).cut(cz(0, 0, 4.0, H_PATA - 10, 12))   # tubo con tapa de 9 mm arriba
PATAS = [(TX0 + 30, TY0 + 30), (TX1 - 30, TY0 + 30), (TX0 + 30, TY1 - 30), (TX1 - 30, TY1 - 30)]
for i, (x, y) in enumerate(PATAS):
    poner(f"20_Pata_{i + 1}", "20" if i == 0 else None, NV, mover(pata(), T(x, y, -9 - H_PATA)), "patas")
print(f"tablero x[{TX0}, {TX1}] y[{TY0}, {TY1}] -> {TX1 - TX0} x {TY1 - TY0} mm")

# ---- marcas de perforacion en el tablero ----
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_OUT
LARGOS = (10, 12, 16, 20, 25, 30)
PERF = []
for n, cod, col, f, g in P:
    if g in ("tablero", "patas", "contenedores") or n.startswith("E") or abs(f.BoundingBox().zmin) > 0.05: continue
    vistos = []
    for e in f.Edges():
        if e.geomType() != "CIRCLE" or not e.IsClosed(): continue
        cc = e.Center()
        if abs(cc.z) > 0.05 or e.radius() > 10: continue
        if any(abs(cc.x - q[0]) < 0.3 and abs(cc.y - q[1]) < 0.3 for q in vistos): continue
        vistos.append((cc.x, cc.y)); r = e.radius()
        cls = BRepClass3d_SolidClassifier(); cls.Load(f.wrapped); asiento = None
        for k in range(1, 120):                  # altura donde apoya la cabeza del tornillo
            z = k * 0.25; cls.Perform(gp_Pnt(cc.x + r + 0.6, cc.y, z), 1e-4)
            if cls.State() == TopAbs_OUT: asiento = z; break
        PERF.append({"pieza": n, "x": round(cc.x, 1), "y": round(cc.y, 1), "d": round(2 * r, 1), "asiento": asiento})
for q in PERF:
    if q["d"] > 9: q["tipo"] = "pasante"
    else:
        a_ = q["asiento"] or 0
        ok = [L for L in LARGOS if a_ + 5 <= L <= a_ + 8]
        q["tipo"], q["tornillo"] = "guia", (f"3,5 x {ok[-1]}" if ok else f"3,5 x ? (asiento {a_} mm)")
    print(q)

# ---- exportar ----
def stl(forma, ruta, tol=0.03):
    BRepMesh_IncrementalMesh(forma.wrapped, tol, False, 0.2, True)
    w = StlAPI_Writer(); w.ASCIIMode = False; w.Write(forma.wrapped, ruta)
asm = cq.Assembly(name="Prototipo_SCB_completo"); info = []
for i, (n, cod, col, f, g) in enumerate(P):
    h = col.lstrip("#"); asm.add(f, name=n, color=cq.Color(*[int(h[k:k + 2], 16) / 255 for k in (0, 2, 4)]))
    ruta = f"{OUTP}/stl/{i:02d}_{n}.stl"; stl(f, ruta)
    b = f.BoundingBox()
    info.append({"nombre": n, "codigo": cod, "color": col, "grupo": g, "stl": ruta,
                 "bbox": [round(x, 1) for x in (b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax)]})
asm.export(f"{OUTP}/Prototipo_SCB_completo.step")
json.dump({"partes": info, "tablero": [TX0, TX1, TY0, TY1], "bandeja": [Xt, Yt], "sensores": SENSORES, "patas": PATAS,
           "arduino": CA, "pasacables": PASACABLES, "m5": M5_CELDA, "perforaciones": PERF, "fuente": FUENTE, "proto": PROTO, "hx711": HX, "Y_US": Y_US,
           "contenedores": [(n, ang, r, r * math.cos(math.radians(ang)), r * math.sin(math.radians(ang))) for n, _, _, ang, r in CONT],
           "TH_F": TH_F}, open(f"{OUTP}/proyecto.json", "w"), indent=1)
# piezas para imprimir, orientadas
BANDEJA_V2 = [f for n, _, _, f, _ in P if n == "16_Bandeja"][0]
for n, f in (("19_poste_HC_SR04_x1.stl", shp(poste())), ("20_pata_x4.stl", mover(pata(), Rx(180))), ("16_bandeja_v2_x1.stl", BANDEJA_V2)):
    b = f.BoundingBox(); f = mover(f, T(-(b.xmin + b.xmax) / 2, -(b.ymin + b.ymax) / 2, -b.zmin))
    stl(f, f"{OUTP}/imprimir/{n}", 0.02); b = f.BoundingBox()
    print(f"{n:28s} {b.xlen:6.1f} x {b.ylen:6.1f} x {b.zlen:5.1f} mm  vol {f.Volume() / 1000:.1f} cm3")
# ---- choques ----
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
esperados = {("Residuo_lata", "04_Disco_FSR"), ("Residuo_lata", "02_Dedo_izquierdo"), ("Residuo_lata", "03_Dedo_derecho"), ("Residuo_etiqueta", "04_Disco_FSR"), ("Residuo_etiqueta", "02_Dedo_izquierdo"), ("Residuo_etiqueta", "03_Dedo_derecho"),
             ("M1_MG996R_base", "D1_Disco_base"), ("M2_MG996R_hombro", "D2_Disco_hombro"), ("M3_MG996R_codo", "D3_Disco_codo")}
for (n1, _, _, f1, _), (n2, _, _, f2, _) in itertools.combinations(P, 2):
    a, b = f1.BoundingBox(), f2.BoundingBox()
    if a.xmax < b.xmin or b.xmax < a.xmin or a.ymax < b.ymin or b.ymax < a.ymin or a.zmax < b.zmin or b.zmax < a.zmin: continue
    cm = BRepAlgoAPI_Common(f1.wrapped, f2.wrapped)
    if cm.IsDone():
        gp = GProp_GProps(); BRepGProp.VolumeProperties_s(cm.Shape(), gp)
        if gp.Mass() > 1 and (n1, n2) not in esperados and (n2, n1) not in esperados:
            print(f"CHOQUE {gp.Mass():8.1f} mm3  {n1} <-> {n2}")
print("listo", len(P), "piezas")
