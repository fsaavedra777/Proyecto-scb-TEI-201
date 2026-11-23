"""
planos.py — Planos técnicos de la caja de control (A3, escala 1:1, primer diedro ISO-E).

Las vistas son proyecciones exactas del modelo de caja_control.py (algoritmo de
líneas ocultas de OpenCascade). Las cotas se escriben desde los mismos parámetros,
así que si cambian una medida y regeneran, los planos quedan coherentes.

Genera ../planos/planos_caja_control.pdf  (3 hojas: base, tapa, ensamble).
Uso:  pip install cadquery reportlab     y luego     python planos.py
"""
import os
from datetime import date

from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

import caja_control as C

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "..", "planos")
RENDERS = os.path.join(AQUI, "..", "renders")
W_PAG, H_PAG = landscape(A3)

VISTAS = {  # nombre: (dirección hacia el observador, eje x de la vista)
    "superior": ((0, 0, 1), (1, 0, 0)), "inferior": ((0, 0, -1), (1, 0, 0)),
    "frontal": ((0, -1, 0), (1, 0, 0)), "posterior": ((0, 1, 0), (-1, 0, 0)),
    "izquierda": ((-1, 0, 0), (0, -1, 0)), "derecha": ((1, 0, 0), (0, 1, 0)),
}


# ------------------------------------------------------------------ proyección
def _polilineas(compuesto):
    out = []
    if compuesto is None or compuesto.IsNull():
        return out
    ex = TopExp_Explorer(compuesto, TopAbs_EDGE)
    while ex.More():
        e = TopoDS.Edge_s(ex.Current())
        curva = BRepAdaptor_Curve(e)
        disc = GCPnts_QuasiUniformDeflection(curva, 0.02)
        if disc.IsDone() and disc.NbPoints() > 1:
            out.append([(disc.Value(i).X(), disc.Value(i).Y()) for i in range(1, disc.NbPoints() + 1)])
        ex.Next()
    return out


def proyectar(forma, vista, ocultas=True):
    n, x = VISTAS[vista]
    algo = HLRBRep_Algo()
    algo.Add(forma.val().wrapped if hasattr(forma, "val") else forma.wrapped)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*n), gp_Dir(*x))))
    algo.Update(); algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    vis = _polilineas(h.VCompound()) + _polilineas(h.OutLineVCompound()) + _polilineas(h.Rg1LineVCompound())
    occ = (_polilineas(h.HCompound()) + _polilineas(h.OutLineHCompound())) if ocultas else []
    pts = [p for l in vis for p in l]
    caja = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
    return vis, occ, caja


class Hoja:
    def __init__(self, c, titulo, nro, total, escala="1:1"):
        self.c, self.titulo, self.nro, self.total, self.escala = c, titulo, nro, total, escala
        self.marco()

    # ---- marco y rótulo ----
    def marco(self):
        c = self.c
        c.setLineWidth(0.7); c.rect(20 * mm, 10 * mm, W_PAG - 30 * mm, H_PAG - 20 * mm)
        x0, y0, w, h = W_PAG - 10 * mm - 185 * mm, 10 * mm, 185 * mm, 38 * mm
        c.rect(x0, y0, w, h)
        for yy in (y0 + 12 * mm, y0 + 24 * mm):
            c.line(x0, yy, x0 + w, yy)
        for xx in (x0 + 110 * mm, x0 + 145 * mm):
            c.line(xx, y0, xx, y0 + 24 * mm)
        c.setFont("Helvetica-Bold", 12); c.drawString(x0 + 3 * mm, y0 + 28 * mm, "PROYECTO SCB - " + self.titulo)
        c.setFont("Helvetica", 7.5)
        c.drawString(x0 + 3 * mm, y0 + 17 * mm, "TEI201 Taller de Diseño en Ingeniería - Universidad Adolfo Ibáñez")
        c.drawString(x0 + 3 * mm, y0 + 14 * mm, "Dibujó: F. Saavedra, M. Jara, M. Olivares")
        c.drawString(x0 + 3 * mm, y0 + 5 * mm, "Material: PLA, impresión FDM, capa 0,2 mm. Medidas en mm.")
        c.drawString(x0 + 113 * mm, y0 + 17 * mm, "Escala")
        c.drawString(x0 + 148 * mm, y0 + 17 * mm, "Hoja")
        c.drawString(x0 + 113 * mm, y0 + 5 * mm, "Proyección ISO-E (1er diedro)")
        c.drawString(x0 + 148 * mm, y0 + 5 * mm, f"Fecha {date.today():%d-%m-%Y}")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x0 + 113 * mm, y0 + 13.5 * mm, self.escala)
        c.drawString(x0 + 148 * mm, y0 + 13.5 * mm, f"{self.nro} / {self.total}")
        self.simbolo_primer_diedro(x0 + 166 * mm, y0 + 13 * mm)

    def simbolo_primer_diedro(self, x, y):
        c = self.c; c.setLineWidth(0.35)
        c.circle(x + 12 * mm, y + 3 * mm, 3 * mm); c.circle(x + 12 * mm, y + 3 * mm, 1.3 * mm)
        p = c.beginPath(); p.moveTo(x, y + 1 * mm); p.lineTo(x + 6 * mm, y); p.lineTo(x + 6 * mm, y + 6 * mm)
        p.lineTo(x, y + 5 * mm); p.close(); c.drawPath(p)

    # ---- vistas ----
    def vista(self, datos, x0, y0, escala=1.0, nombre=None, dy_nombre=7):
        """Dibuja una vista con la esquina inferior izquierda de su caja en (x0, y0) mm."""
        vis, occ, (u0, v0, u1, v1) = datos
        c = self.c
        T = lambda u, v: ((x0 + (u - u0) * escala) * mm, (y0 + (v - v0) * escala) * mm)
        c.setLineWidth(0.25); c.setDash(2.2, 1.2); c.setStrokeGray(0.35)
        for l in occ:
            self._linea(l, T)
        c.setDash(); c.setStrokeGray(0); c.setLineWidth(0.5)
        for l in vis:
            self._linea(l, T)
        if nombre:
            c.setFont("Helvetica-Bold", 8.5)
            c.drawCentredString((x0 + (u1 - u0) * escala / 2) * mm, (y0 - dy_nombre) * mm, nombre)
        # devuelve una función que pasa de coordenadas de la vista a mm de la hoja
        return lambda u, v: (x0 + (u - u0) * escala, y0 + (v - v0) * escala)

    def _linea(self, l, T):
        p = self.c.beginPath()
        p.moveTo(*T(*l[0]))
        for q in l[1:]:
            p.lineTo(*T(*q))
        self.c.drawPath(p, stroke=1, fill=0)

    # ---- cotas ----
    def _flecha(self, x, y, dx, dy):
        c = self.c
        import math
        a = math.atan2(dy, dx); L, w = 2.6, 0.45
        p = c.beginPath(); p.moveTo(x * mm, y * mm)
        p.lineTo((x - L * math.cos(a - w)) * mm, (y - L * math.sin(a - w)) * mm)
        p.lineTo((x - L * math.cos(a + w)) * mm, (y - L * math.sin(a + w)) * mm); p.close()
        c.drawPath(p, stroke=0, fill=1)

    def cota_h(self, a, b, y, texto, ya=None, yb=None):
        """Cota horizontal entre los puntos a y b (mm de hoja), línea de cota a la altura y."""
        c = self.c; c.setLineWidth(0.18)
        for (x, yp) in ((a[0], a[1] if ya is None else ya), (b[0], b[1] if yb is None else yb)):
            s = 1 if y > yp else -1
            c.line(x * mm, (yp + s * 1.0) * mm, x * mm, (y + s * 1.5) * mm)
        c.line(a[0] * mm, y * mm, b[0] * mm, y * mm)
        self._flecha(b[0], y, 1, 0); self._flecha(a[0], y, -1, 0)
        c.setFont("Helvetica", 7.5); c.drawCentredString((a[0] + b[0]) / 2 * mm, (y + 0.9) * mm, texto)

    def cota_v(self, a, b, x, texto):
        c = self.c; c.setLineWidth(0.18)
        for (xp, yp) in (a, b):
            s = 1 if x > xp else -1
            c.line((xp + s * 1.0) * mm, yp * mm, (x + s * 1.5) * mm, yp * mm)
        c.line(x * mm, a[1] * mm, x * mm, b[1] * mm)
        self._flecha(x, b[1], 0, 1); self._flecha(x, a[1], 0, -1)
        c.saveState(); c.translate((x - 0.9) * mm, (a[1] + b[1]) / 2 * mm); c.rotate(90)
        c.setFont("Helvetica", 7.5); c.drawCentredString(0, 0, texto); c.restoreState()

    def llamada(self, p, q, texto, lado=None):
        """Línea de referencia desde el punto p hasta q, con texto en q.
        lado='der' fuerza el texto a la derecha de q (para no salir de la hoja)."""
        c = self.c; c.setLineWidth(0.18)
        c.line(p[0] * mm, p[1] * mm, q[0] * mm, q[1] * mm)
        self._flecha(p[0], p[1], p[0] - q[0], p[1] - q[1])
        c.setFont("Helvetica", 7.2)
        if lado == "der" or (lado is None and q[0] >= p[0]):
            c.line(q[0] * mm, q[1] * mm, (q[0] + 3) * mm, q[1] * mm); c.drawString((q[0] + 3.6) * mm, (q[1] - 1) * mm, texto)
        else:
            c.line(q[0] * mm, q[1] * mm, (q[0] - 3) * mm, q[1] * mm); c.drawRightString((q[0] - 3.6) * mm, (q[1] - 1) * mm, texto)

    def notas(self, x, y, lineas, titulo="NOTAS", tam=7.6):
        c = self.c
        c.setFont("Helvetica-Bold", 8.5); c.drawString(x * mm, y * mm, titulo)
        c.setFont("Helvetica", tam)
        for k, l in enumerate(lineas):
            c.drawString(x * mm, (y - 4.6 * (k + 1)) * mm, l)


def f(v):
    return f"{v:.1f}".replace(".", ",").replace(",0", "") if abs(v - round(v)) < 0.05 else f"{v:.1f}".replace(".", ",")


# ================================================================== HOJA 1: BASE
def hoja_base(c, base):
    h = Hoja(c, "CAJA DE CONTROL: BASE", 1, 3)
    P = C.PARED
    fr = proyectar(base, "frontal", ocultas=False)
    sup = proyectar(base, "superior", ocultas=False)
    izq = proyectar(base, "izquierda", ocultas=False)
    der = proyectar(base, "derecha", ocultas=False)

    # posiciones (mm de hoja)
    T_sup = h.vista(sup, 32, 64, nombre="VISTA SUPERIOR (sin tapa)", dy_nombre=13.5)
    T_fr = h.vista(fr, 32, 205, nombre="VISTA FRONTAL")
    T_izq = h.vista(izq, 212, 205, nombre="VISTA LATERAL IZQUIERDA (USB y DC)", dy_nombre=14)
    T_der = h.vista(der, 212, 112, nombre="VISTA DESDE LA DERECHA (ranura de cables)", dy_nombre=14)

    # --- vista superior: coordenadas del mundo (x, y) -> vista (u=x, v=y)
    s = lambda x, y: T_sup(x, y)
    h.cota_h(s(-P, -P), s(C.L_INT + P, -P), 57.5, f"{f(C.L_EXT)} ±0,3")
    h.cota_v(s(C.L_INT + P, -P), s(C.L_INT + P, C.W_INT + P), s(C.L_INT + P, 0)[0] + 9, f"{f(C.W_EXT)} ±0,3")
    h.cota_h(s(0, C.W_INT), s(C.L_INT, C.W_INT), s(0, C.W_INT + P)[1] + 5, f"{f(C.L_INT)} interior")
    # patrón de agujeros del Arduino
    a = [(C.UNO_X + ax, C.UNO_Y + ay) for ax, ay in C.UNO["agujeros"]]
    h.cota_h(s(*a[0]), s(*a[3]), s(0, C.UNO_Y)[1] - 6.5, f"{f(a[3][0] - a[0][0])}")
    h.cota_v(s(*a[0]), s(*a[1]), s(*a[0])[0] - 5.5, f"{f(a[1][1] - a[0][1])}")
    yb = 44  # llamadas bajo la vista superior
    h.llamada(s(*a[2]), (60, yb), "4x pilar Ø6,5 h6, agujero Ø3,3 ±0,1, tuerca M3 cautiva abajo (patrón Arduino UNO)", lado="der")
    i = C.PERF["insert"]
    pp = (C.PERF_X + C.PERF["l"] - i, C.PERF_Y + i)
    h.llamada(s(*pp), (60, yb - 6), "4x pilar Ø6,5 h5 para la placa perforada 70x50 (entre ejes 65x45)", lado="der")
    fx = C.FIJACION[0]
    h.llamada(s(*fx), (60, yb - 12), "4x Ø4,6 pasante, avellanado 90° a Ø9 (fijación a la base MDF)", lado="der")
    ya = 182  # llamadas sobre la vista superior
    hx = (C.HX_X + 6, C.HX_Y + C.HX["w"] + 0.6)
    h.llamada(s(*hx), (40, ya), f"Riel HX711: ranura {f(C.HX['t'] + 0.3)} a z=3, ancho {f(C.HX['w'] + 2 * C.HOLGURA)}, abierto hacia +x", lado="der")
    mt = (C.MT_X + C.MT["l"] - 6, C.MT_Y + C.MT["w"] + 0.6)
    h.llamada(s(*mt), (128, ya), f"Riel MT3608: ancho {f(C.MT['w'] + 2 * C.HOLGURA)}, abierto hacia -x", lado="der")
    bc = C.BOSS_C[3]
    h.llamada(s(*bc), (128, ya + 6), f"4x pilar Ø{f(C.BOSS_D)}, agujero Ø{f(C.INSERTO_D)} +0,1/0 prof. {f(C.INSERTO_H)} (inserto M3)", lado="der")

    # --- vista frontal (u=x, v=z)
    fz = lambda x, z: T_fr(x, z)
    h.cota_v(fz(-P, -C.PISO), fz(-P, C.H_INT), fz(-P, 0)[0] - 6, f"{f(C.H_EXT)} ±0,3")
    h.cota_h(fz(C.L_INT / 2 - 30, 26), fz(C.L_INT / 2 + 30, 26), fz(0, C.H_INT)[1] + 7, "60 (rebaje etiqueta 0,6 prof.)",
             ya=fz(0, 26)[1], yb=fz(0, 26)[1])

    # --- vista lateral izquierda (u = -y, v = z): calados USB y DC
    def zi(y, z):
        return T_izq(-y, z)
    z_pcb = C.STANDOFF_H + C.UNO["t"]
    usb, dc = C.UNO["usb"], C.UNO["dc"]
    yu0, yu1 = C.UNO_Y + usb["y0"] - 1, C.UNO_Y + usb["y0"] + usb["w"] + 1
    yd0, yd1 = C.UNO_Y + dc["y0"] - 1, C.UNO_Y + dc["y0"] + dc["w"] + 1
    h.cota_h(zi(yu1, z_pcb + usb["h"] + 1), zi(yu0, z_pcb + usb["h"] + 1), zi(0, C.H_INT)[1] + 7,
             f"USB {f(usb['w'] + 2)} +0,3/0")
    h.cota_h(zi(yd1, z_pcb + dc["h"] + 1), zi(yd0, z_pcb + dc["h"] + 1), zi(0, C.H_INT)[1] + 13,
             f"DC {f(dc['w'] + 2)} +0,3/0")
    h.cota_v(zi(yd0, -C.PISO), zi(yd0, z_pcb - 1), zi(-P, 0)[0] + 6, f"{f(z_pcb - 1 + C.PISO)}")
    h.cota_v(zi(yd0, z_pcb - 1), zi(yd0, z_pcb + dc["h"] + 1), zi(-P, 0)[0] + 12, f"{f(dc['h'] + 2)}")
    h.cota_h(zi(0, -C.PISO), zi(yd0, -C.PISO), zi(0, 0)[1] - 8, f"{f(yd0)}", ya=zi(0, -C.PISO)[1], yb=zi(0, -C.PISO)[1])

    # --- vista desde la derecha (u = y, v = z): ranura en U
    def zd(y, z):
        return T_der(y, z)
    h.cota_h(zd(C.RANURA_Y0, C.H_INT), zd(C.RANURA_Y1, C.H_INT), zd(0, C.H_INT)[1] + 6,
             f"{f(C.RANURA_Y1 - C.RANURA_Y0)} +0,5/0")
    h.cota_v(zd(C.RANURA_Y1, C.H_INT - C.RANURA_PROF), zd(C.RANURA_Y1, C.H_INT), zd(C.W_INT + P, 0)[0] + 6,
             f"{f(C.RANURA_PROF)}")
    h.cota_h(zd(-P, C.H_INT - C.RANURA_PROF), zd(C.RANURA_Y0, C.H_INT - C.RANURA_PROF),
             zd(0, -C.PISO)[1] - 7, f"{f(C.RANURA_Y0 + P)}", ya=zd(0, -C.PISO)[1], yb=zd(0, -C.PISO)[1])

    h.notas(335, 150, [
        "1. Tolerancias generales ISO 2768-m salvo indicación.",
        f"2. Holgura de ajuste entre piezas impresas: {f(C.HOLGURA)} mm por lado.",
        f"3. Paredes y piso de {f(C.PARED)} mm (6 perímetros de 0,4).",
        "4. Imprimir con la boca hacia arriba, sin soportes,",
        "   relleno 20 %. Masa estimada: unos 100 g de PLA.",
        "5. Insertos M3x5,7 de bronce: colocar con cautín",
        "   a 220 °C antes de armar.",
        f"6. Prensaestopa PG7 (Ø{f(C.PG7_D)}) en la pared posterior,",
        f"   centro x={f(C.PG7_X + P)} desde el borde izquierdo,",
        f"   z={f(C.PG7_Z + C.PISO)} desde la base (ver hoja 3).",
        "7. La ranura en U se cierra parcialmente con la",
        "   lengüeta de la tapa: quedan 8 mm libres para cables.",
        "8. Los módulos HX711 y MT3608 entran deslizando en",
        "   sus rieles por la zona libre central: sin tornillos.",
    ])
    c.showPage()


# ================================================================== HOJA 2: TAPA
def hoja_tapa(c, tapa):
    h = Hoja(c, "CAJA DE CONTROL: TAPA", 2, 3)
    P = C.PARED
    sup = proyectar(tapa, "superior", ocultas=True)
    inf = proyectar(tapa, "inferior", ocultas=False)
    fr = proyectar(tapa, "frontal", ocultas=False)
    der = proyectar(tapa, "derecha", ocultas=False)

    T_sup = h.vista(sup, 32, 100, nombre="VISTA SUPERIOR", dy_nombre=14)
    T_fr = h.vista(fr, 32, 232, nombre="VISTA FRONTAL", dy_nombre=8)
    T_inf = h.vista(inf, 215, 100, nombre="VISTA INFERIOR (faldón y lengüeta)", dy_nombre=15)
    T_der = h.vista(der, 215, 232, nombre="VISTA DESDE LA DERECHA", dy_nombre=8)

    s = lambda x, y: T_sup(x, y)
    h.cota_h(s(-P, -P), s(C.L_INT + P, -P), 92.5, f"{f(C.L_EXT)} ±0,3")
    h.cota_v(s(-P, -P), s(-P, C.W_INT + P), s(-P, 0)[0] - 6, f"{f(C.W_EXT)} ±0,3")
    b0, b1, b2 = C.BOSS_C[0], C.BOSS_C[1], C.BOSS_C[2]
    h.cota_h(s(*b2), s(C.BOSS_C[3][0], b2[1]), s(0, C.W_INT + P)[1] + 6, f"{f(b1[0] - b0[0])} entre ejes",
             ya=s(*b2)[1], yb=s(*b2)[1])
    h.cota_v(s(*b1), s(b1[0], C.BOSS_C[3][1]), s(C.L_INT + P, 0)[0] + 7, f"{f(C.BOSS_C[3][1] - b1[1])} entre ejes")
    h.llamada(s(*b0), (s(*b0)[0] + 14, s(*b0)[1] - 7),
              f"4x Ø{f(C.TORN_D)} pasante, avellanado 90° a Ø{f(C.AVELL_D)} (M3x8 DIN 7991)")
    vx = (C.MT_X + 18, C.MT_Y + 7)
    h.llamada(s(*vx), (s(*vx)[0] - 30, s(*vx)[1] + 14), "5x ranura 30x2, paso 4,5 (ventilación del MT3608)")
    et = (C.PERF_X + 30, 41)
    h.llamada(s(*et), (s(*et)[0] - 40, s(*et)[1] - 10), "Rebaje 70x22x0,6 para etiqueta")

    fz = lambda x, z: T_fr(x, z)
    h.cota_v(fz(-P, C.H_INT), fz(-P, C.H_INT + C.TAPA), fz(-P, 0)[0] - 6, f"{f(C.TAPA)}")
    h.cota_v(fz(C.HOLGURA + 5, C.H_INT - 2.5), fz(C.HOLGURA + 5, C.H_INT), fz(-P, 0)[0] - 12, "2,5")

    zd = lambda y, z: T_der(y, z)
    h.cota_h(zd(C.RANURA_Y0 + C.HOLGURA, C.H_INT - C.LENGUETA), zd(C.RANURA_Y1 - C.HOLGURA, C.H_INT - C.LENGUETA),
             zd(0, C.H_INT + C.TAPA)[1] + 6, f"{f(C.RANURA_Y1 - C.RANURA_Y0 - 2 * C.HOLGURA)} (lengüeta)")
    h.cota_v(zd(C.RANURA_Y1, C.H_INT - C.LENGUETA), zd(C.RANURA_Y1, C.H_INT), zd(C.W_INT + P, 0)[0] + 6,
             f"{f(C.LENGUETA)}")

    # vista inferior (u = x, v = -y)
    ii = lambda x, y: T_inf(x, -y)
    h.cota_h(ii(C.HOLGURA, C.W_INT - C.HOLGURA), ii(C.L_INT - C.HOLGURA, C.W_INT - C.HOLGURA),
             ii(0, C.W_INT + P)[1] - 6, f"{f(C.L_INT - 2 * C.HOLGURA)} -0,2/0 (faldón)",
             ya=ii(0, C.W_INT - C.HOLGURA)[1], yb=ii(0, C.W_INT - C.HOLGURA)[1])
    h.cota_v(ii(C.L_INT - C.HOLGURA, C.W_INT - C.HOLGURA), ii(C.L_INT - C.HOLGURA, C.HOLGURA),
             ii(C.L_INT + P, 0)[0] + 7, f"{f(C.W_INT - 2 * C.HOLGURA)} -0,2/0")

    h.notas(32, 72, [
        "1. Tolerancias generales ISO 2768-m salvo indicación.",
        f"2. El faldón (espesor 1,6, alto 2,5) centra la tapa dentro de las paredes con {f(C.HOLGURA)} mm de juego por lado.",
        f"3. La lengüeta baja {f(C.LENGUETA)} mm en la ranura de cables: los cables se sacan levantando la tapa, sin desconectar.",
        "4. Imprimir boca abajo (cara superior sobre la cama), sin soportes. Masa estimada: unos 50 g de PLA.",
        "5. Se abre con un destornillador Phillips: 4 tornillos M3x8 avellanados sobre insertos de bronce de la base.",
        "6. Las ranuras de ventilación quedan sobre el MT3608 (único componente que se entibia).",
    ])
    c.showPage()


# ================================================================== HOJA 3: ENSAMBLE
def hoja_ensamble(c, base):
    h = Hoja(c, "CAJA DE CONTROL: ENSAMBLE Y DETALLES", 3, 3, escala="1:1 / s.e.")
    P = C.PARED
    img = os.path.join(RENDERS, "caja_explosionada.png")
    if os.path.exists(img):
        c.drawImage(img, 22 * mm, 150 * mm, width=150 * mm, height=122 * mm, mask="auto", preserveAspectRatio=True)
    c.setFont("Helvetica-Bold", 8.5); c.drawString(65 * mm, 146 * mm, "VISTA EXPLOSIONADA (sin escala)")

    post = proyectar(base, "posterior", ocultas=False)
    inf = proyectar(base, "inferior", ocultas=False)
    T_post = h.vista(post, 215, 228, nombre="VISTA POSTERIOR (prensaestopa PG7)", dy_nombre=15)
    T_inf = h.vista(inf, 215, 100, nombre="VISTA INFERIOR")
    pz = lambda x, z: T_post(-x, z)
    h.llamada(pz(C.PG7_X, C.PG7_Z + C.PG7_D / 2), (pz(C.PG7_X, 0)[0] + 18, pz(0, C.H_INT)[1] + 5),
              f"Ø{f(C.PG7_D)} +0,2/0 para PG7")
    h.cota_h(pz(C.L_INT + P, -C.PISO), pz(C.PG7_X, -C.PISO), pz(0, -C.PISO)[1] - 7, f"{f(C.L_INT + P - C.PG7_X)}",
             ya=pz(0, -C.PISO)[1], yb=pz(0, -C.PISO)[1])
    h.cota_v(pz(C.PG7_X, -C.PISO), pz(C.PG7_X, C.PG7_Z), pz(C.L_INT + P, 0)[0] - 5, f"{f(C.PG7_Z + C.PISO)}")
    iv = lambda x, y: T_inf(x, -y)
    a = (C.UNO_X + C.UNO["agujeros"][0][0], C.UNO_Y + C.UNO["agujeros"][0][1])
    h.llamada(iv(*a), (300, 86), "8x hexágono 5,7 e/c, prof. 2,6 (tuerca M3)", lado="der")

    # lista de piezas
    filas = [("N°", "Pieza", "Cant.", "Fijación / cómo se saca"),
             ("1", "Base de la caja (PLA)", "1", "4 tornillos para madera a la base MDF"),
             ("2", "Tapa (PLA)", "1", "4 tornillos M3x8 avellanados + insertos"),
             ("3", "Arduino UNO R3", "1", "4 tornillos M3x6 sobre pilares"),
             ("4", "Placa perforada 70x50 con borneras", "1", "4 tornillos M3x6 sobre pilares"),
             ("5", "Módulo HX711", "1", "Riel deslizante, sin tornillos"),
             ("6", "Módulo MT3608", "1", "Riel deslizante, sin tornillos"),
             ("7", "Insertos de bronce M3x5,7", "4", "Termofijados en la base"),
             ("8", "Tuercas M3", "8", "Cautivas bajo los pilares"),
             ("9", "Prensaestopa PG7", "1", "Tuerca por dentro")]
    x0, y0, an = 22, 100, [8, 70, 12, 95]
    c.setFont("Helvetica-Bold", 8.5); c.drawString(x0 * mm, (y0 + 3) * mm, "LISTA DE PIEZAS")
    for k, fila in enumerate(filas):
        y = y0 - 4.6 * k
        c.setFont("Helvetica-Bold" if k == 0 else "Helvetica", 7.4)
        xx = x0
        for w, txt in zip(an, fila):
            c.drawString((xx + 1) * mm, (y - 3.3) * mm, txt); xx += w
        c.setLineWidth(0.2); c.line(x0 * mm, (y - 4.6) * mm, (x0 + sum(an)) * mm, (y - 4.6) * mm)
    h.notas(22, 136, [
        "REPARACIÓN EN TERRENO (sin herramientas especiales, sin soldar):",
        "1. Quitar los 4 tornillos de la tapa (Phillips n.º 1) y levantarla: los cables salen por la ranura en U.",
        "2. Arduino o placa: soltar las borneras o los conectores y los 4 tornillos M3; las tuercas quedan cautivas.",
        "3. HX711 o MT3608: desconectar y deslizar el módulo hacia el centro de la caja hasta sacarlo del riel.",
        "4. Servo o sensor externo: se cambia en su bornera o conector; luego PAUSA / MOVER / GUARDAR desde el",
        "   dashboard o el Monitor Serie para recalibrar sus poses, sin reprogramar el Arduino.",
    ], titulo="")
    c.showPage()


if __name__ == "__main__":
    os.makedirs(SALIDA, exist_ok=True)
    base, tapa = C.base(), C.tapa()
    ruta = os.path.join(SALIDA, "planos_caja_control.pdf")
    c = canvas.Canvas(ruta, pagesize=landscape(A3))
    c.setTitle("Proyecto SCB - Planos de la caja de control")
    hoja_base(c, base)
    hoja_tapa(c, tapa)
    hoja_ensamble(c, base)
    c.save()
    print("Listo:", ruta)
