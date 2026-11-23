"""
gateway.py — Puente entre el Arduino UNO y el repositorio de datos.

El Arduino UNO no tiene WiFi, así que el PC hace de gateway IoT:
  Arduino --USB/serie (JSON)--> gateway.py --> SQLite (datos/scb.db)
                                            --> CSV diarios (datos/csv/)
  dashboard.py --cola de comandos en SQLite--> gateway.py --> Arduino

Uso (dejarlo corriendo durante toda la demo):
  python gateway.py                 # busca el Arduino solo
  python gateway.py --puerto COM4   # o indicar el puerto
  python gateway.py --listar        # muestra los puertos disponibles
  python gateway.py --simular       # SOLO PARA PROBAR el dashboard sin robot:
                                    # escribe en otra base (scb_simulado.db)

Si se desconecta el cable, reintenta cada 2 s sin perder lo ya guardado.
"""
import argparse
import csv
import json
import os
import random
import sys
import time
from datetime import datetime

import db

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

CSV_DIR = os.path.join(db.CARPETA, "datos", "csv")
CAMPOS_TEL = ["ts", "fecha", "seq", "ms", "estado", "dist", "peso", "ind", "cap", "fsr"]
CAMPOS_EVT = ["ts", "fecha", "ciclo", "resultado", "material", "via", "peso", "pct_ind", "pct_cap",
              "fsr_max", "intentos", "latencia_ms", "ciclo_ms"]


class Registrador:
    """Recibe cada línea del Arduino y la guarda en SQLite y en CSV."""

    def __init__(self, con, guardar_csv=True):
        self.con = con
        self.guardar_csv = guardar_csv
        self.ult_seq = None
        self.perdidos = 0
        self.recibidos = 0
        self.ult_commit = time.time()
        os.makedirs(CSV_DIR, exist_ok=True)

    # ---- CSV: un archivo de telemetría por día y uno de eventos acumulado ----
    def _csv(self, nombre, campos, fila):
        if not self.guardar_csv:
            return
        ruta = os.path.join(CSV_DIR, nombre)
        nuevo = not os.path.exists(ruta)
        with open(ruta, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
            if nuevo:
                w.writeheader()
            w.writerow(fila)

    def procesar(self, linea):
        linea = linea.strip()
        if not linea:
            return
        ahora = time.time()
        try:
            d = json.loads(linea)
            tipo = d.get("t")
        except (json.JSONDecodeError, AttributeError):
            # Línea que no es JSON (por ejemplo, basura al conectar): se guarda igual
            self.con.execute("INSERT INTO mensajes (ts, tipo, texto) VALUES (?, 'raw', ?)", (ahora, linea))
            return

        if tipo == "tel":
            seq = d.get("n")
            if self.ult_seq is not None and seq is not None:
                if seq == self.ult_seq + 1:
                    pass
                elif seq > self.ult_seq + 1:
                    self.perdidos += seq - self.ult_seq - 1
                # seq menor = el Arduino se reinició: empieza de nuevo la cuenta
            self.ult_seq = seq
            self.recibidos += 1
            fila = dict(ts=ahora, seq=seq, ms=d.get("ms"), estado=d.get("est"), dist=d.get("dist"),
                        peso=d.get("peso"), ind=d.get("ind"), cap=d.get("cap"), fsr=d.get("fsr"))
            self.con.execute("INSERT INTO telemetria (ts, seq, ms, estado, dist, peso, ind, cap, fsr) "
                             "VALUES (:ts, :seq, :ms, :estado, :dist, :peso, :ind, :cap, :fsr)", fila)
            fila["fecha"] = datetime.fromtimestamp(ahora).isoformat(timespec="milliseconds")
            self._csv(f"telemetria_{datetime.now():%Y-%m-%d}.csv", CAMPOS_TEL, fila)

        elif tipo == "evt":
            fila = dict(ts=ahora, ciclo=d.get("n"), resultado=d.get("res"), material=d.get("mat"),
                        via=d.get("via"), peso=d.get("peso"), pct_ind=d.get("ind"), pct_cap=d.get("cap"),
                        fsr_max=d.get("fsr"), intentos=d.get("int"), latencia_ms=d.get("lat"),
                        ciclo_ms=d.get("ciclo"))
            self.con.execute(
                "INSERT INTO eventos (ts, ciclo, resultado, material, via, peso, pct_ind, pct_cap, fsr_max, "
                "intentos, latencia_ms, ciclo_ms) VALUES (:ts, :ciclo, :resultado, :material, :via, :peso, "
                ":pct_ind, :pct_cap, :fsr_max, :intentos, :latencia_ms, :ciclo_ms)", fila)
            fila["fecha"] = datetime.fromtimestamp(ahora).isoformat(timespec="seconds")
            self._csv("eventos.csv", CAMPOS_EVT, fila)
            print(f"{datetime.now():%H:%M:%S}  EVENTO #{fila['ciclo']}: {fila['resultado']:<15} "
                  f"{fila['material']:<9} {fila['peso']} g  ciclo {fila['ciclo_ms']} ms")
            self.con.commit()

        elif tipo == "est":
            self.con.execute("INSERT INTO estados (ts, estado) VALUES (?, ?)", (ahora, d.get("est")))
            print(f"{datetime.now():%H:%M:%S}  estado -> {d.get('est')}")

        else:  # log, ack, cfg, ang
            self.con.execute("INSERT INTO mensajes (ts, tipo, texto) VALUES (?, ?, ?)", (ahora, tipo, linea))
            if tipo in ("log", "ack"):
                print(f"{datetime.now():%H:%M:%S}  {tipo}: {d.get('msg') or d.get('cmd')}")

        if ahora - self.ult_commit > 1.0:      # guarda en disco al menos cada 1 s
            self.con.commit()
            self.ult_commit = ahora

    def comandos_pendientes(self):
        filas = self.con.execute("SELECT id, comando FROM comandos WHERE enviado_ts IS NULL ORDER BY id").fetchall()
        return [(f["id"], f["comando"]) for f in filas]

    def marcar_enviado(self, cid):
        self.con.execute("UPDATE comandos SET enviado_ts=? WHERE id=?", (time.time(), cid))
        self.con.commit()


# ---------------------------------------------------------------------------
def buscar_arduino():
    """Devuelve el puerto que parece un Arduino UNO (original o clon CH340)."""
    for p in serial.tools.list_ports.comports():
        texto = f"{p.description} {p.manufacturer or ''}".lower()
        if p.vid in (0x2341, 0x2A03, 0x1A86, 0x0403) or any(k in texto for k in ("arduino", "ch340", "usb serial")):
            return p.device
    return None


def correr_serial(reg, puerto, baudios):
    print("Gateway SCB. Ctrl+C para salir.")
    while True:
        dispositivo = puerto or buscar_arduino()
        if not dispositivo:
            print("No encuentro el Arduino. ¿Está conectado? Reintento en 2 s...")
            time.sleep(2)
            continue
        try:
            with serial.Serial(dispositivo, baudios, timeout=0.2) as ser:
                print(f"Conectado a {dispositivo} ({baudios} baudios). Guardando en {reg.con_ruta}")
                reg.ult_seq = None
                time.sleep(2)                   # el UNO se reinicia al abrir el puerto
                buffer = b""
                ult_cmd = 0
                while True:
                    buffer += ser.read(ser.in_waiting or 1)
                    while b"\n" in buffer:
                        linea, buffer = buffer.split(b"\n", 1)
                        reg.procesar(linea.decode("utf-8", errors="replace"))
                    if time.time() - ult_cmd > 0.3:   # revisa la cola de comandos del dashboard
                        ult_cmd = time.time()
                        for cid, comando in reg.comandos_pendientes():
                            ser.write((comando + "\n").encode())
                            reg.marcar_enviado(cid)
                            print(f"{datetime.now():%H:%M:%S}  comando enviado: {comando}")
        except serial.SerialException as e:
            reg.con.commit()
            print(f"Se perdió la conexión ({e}). Reintento en 2 s...")
            time.sleep(2)


# ---------------------------------------------------------------------------
class Simulador:
    """Genera las mismas líneas JSON que el firmware, para probar el dashboard
    sin el robot. Escribe en scb_simulado.db, nunca en la base real."""

    RESIDUOS = [("METAL", 14.5, "METAL"), ("METAL", 52.0, "METAL"), ("PLASTICO", 23.0, "PLASTICO"),
                ("PLASTICO", 7.5, "PLASTICO"), ("DESCARTE", 6.5, "DESCARTE"), ("DESCARTE", 18.0, "DESCARTE"),
                ("PLASTICO", 35.0, "DESCARTE"), ("DESCARTE", 4.0, "PLASTICO")]

    def __init__(self):
        self.seq = 0
        self.ciclo = 0
        self.t0 = time.time()
        self.estado = "ESPERANDO"
        self.proximo = time.time() + 5
        self.peso = 0.0

    def lineas(self):
        ahora = time.time()
        ms = int((ahora - self.t0) * 1000)
        if self.estado == "ESPERANDO" and ahora >= self.proximo:
            self.ciclo += 1
            mat, masa, _ = random.choice(self.RESIDUOS)
            r = random.random()
            res = "OK" if r < 0.85 else "FALLA_AGARRE" if r < 0.93 else "FALSA_DETECCION"
            if res == "FALSA_DETECCION":
                mat, masa = "NINGUNO", 0.2
            self.pendiente = dict(t="evt", n=self.ciclo, res=res, mat=mat, via="U", peso=round(masa, 1),
                                  ind=100 if mat == "METAL" else 0, cap=100 if mat in ("METAL", "PLASTICO") else 0,
                                  fsr=random.randint(300, 480) if res == "OK" else 60, int=1 if res == "OK" else 2,
                                  lat=random.randint(1650, 1850), ciclo=random.randint(6200, 11000))
            self.peso = masa
            self.fin_ciclo = ahora + self.pendiente["ciclo"] / 1000
            self.estado = "ANALIZANDO"
            yield json.dumps(dict(t="est", ms=ms, est=self.estado))
        elif self.estado != "ESPERANDO":
            nuevo = "RECOGIENDO" if ahora < self.fin_ciclo - 3 else "DEPOSITANDO"
            if nuevo == "DEPOSITANDO":
                self.peso = 0.0
            if ahora >= self.fin_ciclo:
                yield json.dumps(self.pendiente)
                nuevo = "ESPERANDO"
                self.proximo = ahora + random.uniform(12, 25)
            if nuevo != self.estado:
                self.estado = nuevo
                yield json.dumps(dict(t="est", ms=ms, est=nuevo))
        self.seq += 1
        dist = 8.6 if self.peso > 0 else 17.0
        yield json.dumps(dict(t="tel", n=self.seq, ms=ms, est=self.estado, dist=round(dist + random.uniform(-.2, .2), 1),
                              peso=round(self.peso + random.uniform(-.3, .3), 1), ind=0, cap=0,
                              fsr=random.randint(0, 6)))


def correr_simulado(reg):
    print("MODO SIMULADO: datos inventados en datos/scb_simulado.db (no usar para la evaluación).")
    sim = Simulador()
    while True:
        for linea in sim.lineas():
            reg.procesar(linea)
        for cid, comando in reg.comandos_pendientes():
            reg.marcar_enviado(cid)
            reg.procesar(json.dumps(dict(t="ack", cmd=comando.split()[0], ok=1, msg="simulado")))
        time.sleep(0.5)


def main():
    ap = argparse.ArgumentParser(description="Gateway del Proyecto SCB: Arduino -> SQLite/CSV")
    ap.add_argument("--puerto", help="COM3, COM4... (por defecto lo busca solo)")
    ap.add_argument("--baudios", type=int, default=115200)
    ap.add_argument("--db", help="ruta de la base (por defecto datos/scb.db)")
    ap.add_argument("--listar", action="store_true", help="muestra los puertos serie y sale")
    ap.add_argument("--simular", action="store_true", help="genera datos falsos para probar el dashboard")
    ap.add_argument("--sin-csv", action="store_true", help="no escribir los CSV de respaldo")
    a = ap.parse_args()

    if serial is None and not a.simular:
        sys.exit("Falta pyserial: pip install -r requirements.txt")
    if a.listar:
        for p in serial.tools.list_ports.comports():
            print(f"{p.device:10} {p.description}")
        return

    ruta = a.db or (db.DB_SIMULADA if a.simular else db.DB_REAL)
    reg = Registrador(db.conectar(ruta, simulada=a.simular), guardar_csv=not (a.simular or a.sin_csv))
    reg.con_ruta = ruta
    try:
        correr_simulado(reg) if a.simular else correr_serial(reg, a.puerto, a.baudios)
    except KeyboardInterrupt:
        reg.con.commit()
        total = reg.recibidos + reg.perdidos
        if total:
            print(f"\nTelemetría: {reg.recibidos} recibidos, {reg.perdidos} perdidos "
                  f"({100 * reg.perdidos / total:.2f} %).")


if __name__ == "__main__":
    main()
