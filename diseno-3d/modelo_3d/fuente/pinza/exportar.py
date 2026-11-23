"""Exporta STL (orientados para imprimir), STEP del ensamble y STL de referencia para las vistas."""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import cadquery as cq
import pinza_modelo as pm

OUT = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[2] / "salida" / "pinza")
os.makedirs(f"{OUT}/stl", exist_ok=True); os.makedirs(f"{OUT}/ref", exist_ok=True)
TOL, ANG = 0.01, 0.1

piezas = {
    "P1_chasis_pinza": pm.chasis(),
    "P2_dedo_izquierdo_motriz_FSR": pm.dedo(-1),
    "P3_dedo_derecho": pm.dedo(1),
    "P4_disco_FSR_TPU": pm.disco_fsr(),
    "P5_calce_0.5mm": pm.calce(0.5),
    "P6_calce_1.0mm": pm.calce(1.0),
}
for nombre, sol in piezas.items():
    bb = sol.val().BoundingBox()
    impresa = sol.translate((-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))
    cq.exporters.export(impresa, f"{OUT}/stl/{nombre}.stl", tolerance=TOL, angularTolerance=ANG)
    print(nombre, "ok", round(sol.val().Volume() / 1000, 2), "cm3")

# referencias en posicion de ensamble (para vistas y chequeos)
tor, herr = pm.eje_esclavo_ref()
refs = {"chasis": pm.chasis(), "dedo_izq": pm.dedo(-1), "dedo_der": pm.dedo(1), "servo": pm.servo_ref(),
        "brazo_servo": pm.brazo_servo_ref(), "tornillo": tor, "herraje": herr,
        "disco_fsr": pm.disco_fsr().rotate((0, 0, 0), (0, 1, 0), 90).translate((-pm.X_CARA - pm.FSR_PROF + 0.46, pm.FSR_Y, pm.FSR_Z))}
for n, s in refs.items():
    cq.exporters.export(s, f"{OUT}/ref/{n}.stl", tolerance=0.02, angularTolerance=0.2)

# STEP del ensamble de la pinza, en el mismo origen que la pinza original (placa de z = 0 hacia arriba)
sube = (0, 0, pm.PLACA_T)
asm = cq.Assembly(name="Pinza_SCB_v2")
col = {"chasis": (0.85, 0.84, 0.80), "dedo": (0.36, 0.56, 0.82), "fsr": (0.15, 0.15, 0.15), "ref": (0.55, 0.55, 0.6)}
asm.add(pm.chasis().translate(sube), name="P1_Chasis_Pinza", color=cq.Color(*col["chasis"]))
asm.add(pm.dedo(-1).translate(sube), name="P2_Dedo_Izquierdo_Motriz_FSR", color=cq.Color(*col["dedo"]))
asm.add(pm.dedo(1).translate(sube), name="P3_Dedo_Derecho", color=cq.Color(*col["dedo"]))
asm.add(refs["disco_fsr"].translate(sube), name="P4_Disco_FSR", color=cq.Color(*col["fsr"]))
asm.add(pm.servo_ref().translate(sube), name="REF_Servo_SG90_no_imprimir", color=cq.Color(0.2, 0.35, 0.8))
asm.add(pm.brazo_servo_ref().translate(sube), name="REF_Brazo_simple_SG90_no_imprimir", color=cq.Color(0.95, 0.95, 0.95))
asm.add(tor.translate(sube), name="REF_Tornillo_M3x30_no_imprimir", color=cq.Color(*col["ref"]))
asm.add(herr.translate(sube), name="REF_Golillas_y_tuerca_M3_no_imprimir", color=cq.Color(*col["ref"]))
try:
    asm.export(f"{OUT}/Pinza_SCB_v2.step")
except AttributeError:
    asm.save(f"{OUT}/Pinza_SCB_v2.step")
print("STEP ok")
