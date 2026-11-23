"""
Esquemático eléctrico del Proyecto SCB (genera esquematico_scb.pdf / .svg / .png).

Se dibuja con schemdraw usando etiquetas de red (los cables con el mismo nombre
están conectados), como en KiCad o EasyEDA. Para regenerarlo:
    pip install schemdraw matplotlib
    python esquematico_scb.py
"""
import schemdraw
import schemdraw.elements as elm

FS = 9           # tamaño de letra de los pines
TAGW = 2.1       # ancho de las etiquetas de red


def tag(d, punto, nombre, lado="right", largo=0.8):
    """Línea corta desde un pin y etiqueta de red con su nombre."""
    if lado == "right":
        d.add(elm.Line().at(punto).right(largo))
        d.add(elm.Tag(width=TAGW).right().label(nombre, fontsize=FS))
    else:
        d.add(elm.Line().at(punto).left(largo))
        d.add(elm.Tag(width=TAGW).left().label(nombre, fontsize=FS))


def tierra(d, punto, lado="left", largo=0.8):
    d.add(elm.Line().at(punto).tox(punto[0] + (largo if lado == "right" else -largo)))
    d.add(elm.Ground())


def ic(d, x, y, titulo, izq=(), der=(), ancho=4.0, espacio=1.0):
    # schemdraw ubica el primer pin abajo: se invierten para leerlos de arriba hacia abajo
    pines = [elm.IcPin(name=n, side="left") for n in reversed(izq)] + \
            [elm.IcPin(name=n, side="right") for n in reversed(der)]
    filas = max(len(izq), len(der))
    # .right() fija la orientación: si no, el bloque hereda la dirección del último cable dibujado
    bloque = elm.Ic(pins=pines, size=(ancho, (filas + 1) * espacio), pinspacing=espacio, plblsize=FS,
                    lblsize=10).right().at((x, y)).anchor("center").label(titulo, loc="top", fontsize=10, ofst=0.25)
    return d.add(bloque)


with schemdraw.Drawing(show=False) as d:
    d.config(fontsize=FS, unit=2.0, lw=1.1)

    # ================= ARDUINO UNO (centro) =================
    der = ["D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "A0", "A1", "A2"]
    uno = ic(d, 0, 0, "Arduino UNO R3", izq=["5V", "USB", "GND"], der=der, ancho=4.4)
    # Mapa de pines del prototipo (igual a firmware/garra_scb_iot/config.h)
    redes = {"D2": "IND", "D3": "SRV_BASE", "D4": "CAP", "D5": "SRV_HOMBRO", "D6": "SRV_CODO", "D7": "TRIG",
             "D8": "ECHO", "D9": "SRV_PINZA", "A0": "HX_DT", "A1": "HX_SCK", "A2": "FSR"}
    for p, n in redes.items():
        tag(d, getattr(uno, p), n)
    d.add(elm.Line().at(uno.USB).left(1.0))
    d.add(elm.Label().label("al notebook\n(gateway.py, 115200)", fontsize=8, halign="right"))
    d.add(elm.Line().at(uno["5V"]).left(1.0))
    d.add(elm.Vdd().label("+5V", fontsize=FS))
    tierra(d, uno.GND, "left", 1.0)

    # ================= ALIMENTACIÓN (izquierda arriba) =================
    fu = ic(d, -15, 8.5, "Fuente S-50-5 (5 V 10 A)", izq=["L", "N", "PE"], der=["+V", "-V"], ancho=3.6)
    for p, n in (("L", "220 V fase"), ("N", "220 V neutro"), ("PE", "tierra de protección")):
        d.add(elm.Line().at(getattr(fu, p)).left(0.8))
        d.add(elm.Label().label(n, fontsize=8, halign="right"))
    d.add(elm.Line().at(fu["+V"]).right(2.5))
    nodo = d.here
    d.add(elm.Dot())
    d.add(elm.Line().right(1.2))
    d.add(elm.Tag(width=2.6).right().label("+5V_SRV", fontsize=FS))
    d.add(elm.Capacitor(polar=True).at(nodo).down(2.0).label("1000 µF\n16 V", loc="bottom", fontsize=8, ofst=0.3))
    d.add(elm.Ground())
    tierra(d, fu["-V"], "right", 0.8)

    mt = ic(d, -15, 3.2, "MT3608 (ajustar a 12 V)", izq=["IN+", "IN-"], der=["OUT+", "OUT-"], ancho=3.6)
    tag(d, getattr(mt, "IN+"), "+5V_SRV", "left")
    tierra(d, getattr(mt, "IN-"), "left")
    tag(d, getattr(mt, "OUT+"), "+12V")
    tierra(d, getattr(mt, "OUT-"), "right")

    # ================= SERVOS (izquierda abajo) =================
    servos = [("MG996R base", "SRV_BASE"), ("MG996R hombro", "SRV_HOMBRO"),
              ("MG996R codo", "SRV_CODO"), ("SG90 pinza", "SRV_PINZA")]
    for i, (nom, red) in enumerate(servos):
        x = -17.5 + (i % 2) * 7.5
        y = -3.0 - (i // 2) * 5.0
        s = ic(d, x, y, nom, izq=["SEÑAL", "+", "-"], ancho=2.6)
        tag(d, s["SEÑAL"], red, "left")
        tag(d, s["+"], "+5V_SRV", "left")
        tierra(d, s["-"], "left")

    # ================= SENSORES (derecha) =================
    X = 15.0
    hc = ic(d, X, 9.0, "HC-SR04", izq=["VCC", "TRIG", "ECHO", "GND"], ancho=3.0)
    d.add(elm.Line().at(hc.VCC).left(0.8)); d.add(elm.Vdd().label("+5V", fontsize=FS))
    tag(d, hc.TRIG, "TRIG", "left")
    tag(d, hc.ECHO, "ECHO", "left")
    tierra(d, hc.GND, "left")

    hx = ic(d, X, 2.5, "HX711", izq=["VCC", "GND", "DT", "SCK"], der=["E+", "E-", "A-", "A+"], ancho=3.0)
    d.add(elm.Line().at(hx.VCC).left(0.8)); d.add(elm.Vdd().label("+5V", fontsize=FS))
    tierra(d, hx.GND, "left")
    tag(d, hx.DT, "HX_DT", "left")
    tag(d, hx.SCK, "HX_SCK", "left")
    cel = ic(d, X + 7.0, 2.5, "Celda de carga 1 kg", izq=["ROJO", "NEGRO", "BLANCO", "VERDE"], ancho=3.4)
    for a, b in (("E+", "ROJO"), ("E-", "NEGRO"), ("A-", "BLANCO"), ("A+", "VERDE")):
        d.add(elm.Line().at(hx[a]).to(cel[b]))

    # Inductivo y capacitivo: salida NPN a colector abierto, protegida con diodo
    for k, (nom, red, mod) in enumerate((("LJ12A3-4-Z/BX\ninductivo (metal)", "IND", "ind"),
                                          ("LJC18A3-H-Z/BX\ncapacitivo (plástico)", "CAP", "cap"))):
        y = -4.5 - k * 5.5
        s = ic(d, X + 3.5, y, nom, izq=["CAFÉ", "NEGRO", "AZUL"], ancho=3.6)
        tag(d, s["CAFÉ"], "+12V", "left")
        tierra(d, s.AZUL, "left")
        d.add(elm.Line().at(s.NEGRO).left(0.6))
        d.add(elm.Diode().left(2.0).reverse().label("1N4148", fontsize=8, loc="top"))
        d.add(elm.Line().left(0.5))
        d.add(elm.Tag(width=TAGW).left().label(red, fontsize=FS))

    # FSR: divisor de tensión hacia A2
    d.add(elm.Vdd().at((8.5, -9.5)).label("+5V", fontsize=FS))
    d.add(elm.ResistorVar().at((8.5, -9.5)).down(2.4).label("FSR-402\n(en el dedo)", loc="bottom", fontsize=8, ofst=0.25))
    nodo = d.here
    d.add(elm.Dot())
    d.add(elm.Resistor().down(2.4).label("10 kΩ", loc="bottom", fontsize=8, ofst=0.25))
    d.add(elm.Ground())
    d.add(elm.Line().at(nodo).left(1.2))
    d.add(elm.Tag(width=TAGW).left().label("FSR", fontsize=FS))

    # ================= NOTAS Y ROTULO =================
    notas = ("NOTAS\n"
             "1. Las etiquetas con el mismo nombre están conectadas.\n"
             "2. GND común: Arduino, fuente de 5 V y MT3608.\n"
             "3. Los servos van al riel +5V_SRV, NUNCA al 5V del Arduino.\n"
             "4. Ajusten el MT3608 a 12 V con el multímetro ANTES de conectar los sensores.\n"
             "5. El diodo deja que el sensor tire el pin a 0 V, pero bloquea los 12 V\n"
             "    (el pin usa INPUT_PULLUP). Si el capacitivo es /BY (PNP): quitar el diodo\n"
             "    y usar un divisor 15 kΩ (serie) / 10 kΩ (a GND), y poner\n"
             "    CAPACITIVO_ACTIVO_EN_BAJO = false en config.h.\n"
             "6. Arduino, HC-SR04, HX711 y FSR se alimentan desde el USB del notebook.")
    d.add(elm.Label().at((-20.5, -15.0)).label(notas, fontsize=9, halign="left", valign="top"))
    d.add(elm.Label().at((6.5, -19.5)).label(
        "PROYECTO SCB — Esquemático eléctrico v3.0   |   TEI201 Taller de Diseño en Ingeniería, UAI   |   "
        "F. Saavedra, M. Jara, M. Olivares   |   noviembre 2026   |   Hoja 1/1",
        fontsize=9, halign="center"))

    d.save("esquematico_scb.svg")
    d.save("esquematico_scb.pdf")
    d.save("esquematico_scb.png", dpi=170)
print("listo")
