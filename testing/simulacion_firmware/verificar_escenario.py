"""
Verifica automáticamente la salida de `./sim escenario`.

Revisa que:
  1. Toda línea que envía el Arduino sea JSON válido (lo que necesita el gateway).
  2. La telemetría llegue cada ~500 ms y su número de secuencia no tenga saltos.
  3. Cada residuo del escenario termine con el resultado y el material esperados.
  4. Los comandos inválidos o fuera de lugar se rechacen.

Uso:  python3 verificar_escenario.py salida.tsv
"""
import json
import statistics
import sys

ESPERADO = [  # (resultado, material) en el orden del escenario de sim.cpp
    ("OK", "METAL"),             # lata de aluminio
    ("OK", "PLASTICO"),          # botella PET
    ("OK", "DESCARTE"),          # papel arrugado sin eco: se detecta por masa
    ("OK", "PLASTICO"),          # envase resbaloso: 2 intentos
    ("SOBREPESO", "NINGUNO"),    # frasco de 250 g
    ("FALSA_DETECCION", "NINGUNO"),  # mano sobre la bandeja
    ("FALLA_AGARRE", "DESCARTE"),    # objeto imposible de tomar
    ("FALLA_AGARRE", "METAL"),       # tapa que se cae al levantar
    ("PARO", "METAL"),               # PARO de emergencia en pleno ciclo
    ("OK", "PLASTICO"),          # vaso plástico (con PAUSA pedida durante el ciclo)
]
RECHAZOS_ESPERADOS = {"SEGUIR", "XYZ", "TARA"}   # sin calibrar, desconocido, en PARO


def main(ruta):
    lineas, malas = [], []
    for fila in open(ruta, encoding="utf-8"):
        ms, _, texto = fila.rstrip("\n").partition("\t")
        try:
            lineas.append((int(ms), json.loads(texto)))
        except json.JSONDecodeError:
            malas.append(texto)

    ok = True
    def check(cond, msg):
        nonlocal ok
        print(("  OK   " if cond else "  FALLA") + "  " + msg)
        ok &= cond

    print("1. Formato")
    check(not malas, f"{len(lineas)} líneas JSON válidas, {len(malas)} inválidas")

    print("2. Telemetría")
    tel = [(ms, d) for ms, d in lineas if d["t"] == "tel"]
    seq = [d["n"] for _, d in tel]
    saltos = sum(1 for a, b in zip(seq, seq[1:]) if b != a + 1)
    dts = [b - a for (a, _), (b, _) in zip(tel, tel[1:])]
    check(saltos == 0, f"{len(tel)} paquetes, {saltos} saltos de secuencia")
    # La tara y la calibración bloquean ~1,5-2 s a propósito; se excluyen
    dts_normales = [d for d in dts if d < 1500]
    check(statistics.median(dts_normales) <= 520,
          f"periodo mediano {statistics.median(dts_normales):.0f} ms, p95 "
          f"{sorted(dts_normales)[int(0.95 * len(dts_normales))]:.0f} ms (objetivo 500 ms)")
    check(max(dts) < 2500, f"mayor hueco {max(dts)} ms (durante tara/calibración)")

    print("3. Eventos por residuo")
    evts = [d for _, d in lineas if d["t"] == "evt"]
    check(len(evts) == len(ESPERADO), f"{len(evts)} eventos (esperados {len(ESPERADO)})")
    for e, (res, mat) in zip(evts, ESPERADO):
        check(e["res"] == res and e["mat"] == mat,
              f"#{e['n']:<2} {e['res']:<16} {e['mat']:<9} via={e['via']} intentos={e['int']} "
              f"latencia={e['lat']} ms ciclo={e['ciclo']} ms (esperado {res}/{mat})")
    oks = [e for e in evts if e["res"] == "OK"]
    if oks:
        print(f"       ciclo medio de los OK: {statistics.mean(e['ciclo'] for e in oks) / 1000:.1f} s; "
              f"latencia media de clasificación: {statistics.mean(e['lat'] for e in oks) / 1000:.2f} s")

    print("4. Comandos")
    rechazados = {d["cmd"] for _, d in lineas if d["t"] == "ack" and d["ok"] == 0}
    check(rechazados == RECHAZOS_ESPERADOS, f"rechazados: {sorted(rechazados)}")
    cfgs = [d for _, d in lineas if d["t"] == "cfg"]
    check(cfgs and abs(cfgs[-1]["factor"] - 400) < 5,
          f"CAL 100 dejó factor {cfgs[-1]['factor']} (celda simulada: 400 cuentas/g)")

    print("\nRESULTADO:", "TODO OK" if ok else "HAY FALLAS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "salida.tsv"))
