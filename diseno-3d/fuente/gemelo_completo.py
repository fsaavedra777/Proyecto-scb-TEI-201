"""
gemelo_completo.py — Gemelo 3D del sistema completo (CadQuery).

Une dos modelos que ya están en el repositorio:
  - modelo_3d/ensamble/Prototipo_SCB_completo.step: brazo v3, pinza, estación de
    sensado, fuente, contenedores, tablero y patas;
  - SCB_caja_control_gemelo.step: la caja de control con el Arduino UNO, la placa
    perforada con borneras y condensador, el HX711 y el MT3608 adentro.

En el prototipo el Arduino va sobre un soporte abierto (18), con la protoboard y
el HX711 sueltos en el tablero. En el gemelo completo esos cuatro elementos se
reemplazan por la caja de control, que los protege y los deja reparables.

Genera ../SCB_gemelo_completo.step, que se abre en Fusion 360 con el nombre y el
color de cada pieza, y comprueba que la caja no choque con nada.

Uso:  pip install cadquery     y luego     python gemelo_completo.py
"""
import os

import cadquery as cq

AQUI = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.join(AQUI, "..", "modelo_3d", "ensamble", "Prototipo_SCB_completo.step")
CAJA = os.path.join(AQUI, "..", "SCB_caja_control_gemelo.step")
SALIDA = os.path.join(AQUI, "..", "SCB_gemelo_completo.step")

# Piezas del prototipo que quedan dentro de la caja (o que la caja reemplaza)
QUITAR = {"18_Soporte_Arduino", "E1_Arduino_UNO", "E1_conectores", "E1_USB", "E8_Protoboard", "E2_HX711"}

# Posición de la caja sobre el tablero (mismo sistema que el prototipo: origen en el eje
# del servo de la base, sobre la cara superior del tablero; Y hacia la estación; Z hacia arriba).
# Girada 90°: el USB y el conector DC del Arduino quedan hacia el borde delantero del tablero
# y la ranura de cables mira hacia el brazo. La caja queda en x [56; 160,8] e y [-192; -37,2].
GIRO = 90.0
DX, DY = 158.4, -189.6
DZ = 2.4                        # el piso de la caja mide 2,4 mm: así apoya sobre el tablero
PASACABLES = (44.0, -75.0, 16.0)  # perforación del tablero para cables (x, y, diámetro)
BASE_BRAZO_XMAX = 44.0            # borde derecho de la base 10


def main():
    loc = cq.Location(cq.Vector(DX, DY, DZ)) * cq.Location(cq.Vector(), cq.Vector(0, 0, 1), GIRO)
    proto = cq.Assembly.importStep(PROTO)
    caja = cq.Assembly.importStep(CAJA)

    g = cq.Assembly(name="SCB_gemelo_completo")
    for c in proto.children:
        if c.name not in QUITAR:
            g.add(c, name=c.name)
    g.add(caja, name="Caja_control", loc=loc)
    g.export(SALIDA)
    print("STEP:", os.path.normpath(SALIDA))

    # ---- comprobaciones ----
    cb = caja.toCompound().moved(loc)
    b = cb.BoundingBox()
    print(f"Caja: x[{b.xmin:.1f}; {b.xmax:.1f}] y[{b.ymin:.1f}; {b.ymax:.1f}] z[{b.zmin:.1f}; {b.zmax:.1f}] mm")
    choques = []
    for c in proto.children:
        if c.name in QUITAR:
            continue
        s = c.toCompound()
        sb = s.BoundingBox()
        if (sb.xmax < b.xmin or sb.xmin > b.xmax or sb.ymax < b.ymin or sb.ymin > b.ymax
                or sb.zmax < b.zmin or sb.zmin > b.zmax):
            continue
        v = cb.intersect(s).Volume()
        if v > 1e-3:
            choques.append((c.name, round(v, 2)))
    print("Interferencias con la caja:", choques if choques else "ninguna (solo apoya sobre el tablero)")
    print(f"Holguras: base del brazo {b.xmin - BASE_BRAZO_XMAX:.1f} mm, "
          f"pasacables {b.xmin - (PASACABLES[0] + PASACABLES[2] / 2):.1f} mm, "
          f"borde delantero del tablero {b.ymin + 200:.1f} mm")


if __name__ == "__main__":
    main()
