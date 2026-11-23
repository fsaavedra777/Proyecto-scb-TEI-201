"""
db.py — Repositorio de datos del Proyecto SCB (SQLite).

Una sola base de datos en un archivo (datos/scb.db), con histórico completo.
La escribe gateway.py y la lee dashboard.py al mismo tiempo (modo WAL).

Tablas
  telemetria  una fila cada 500 ms: estado y lectura de cada sensor
  eventos     una fila por residuo: material, resultado, tiempos y el
              material real que anota el operario (para medir el acierto)
  estados     cada cambio de estado de la máquina
  mensajes    logs, respuestas a comandos y configuración del Arduino
  comandos    cola de órdenes del dashboard hacia el Arduino
  vaciados    cuándo se vació cada contenedor
  meta        datos de la base (por ejemplo, si es simulada)
"""
import os
import sqlite3
import time

CARPETA = os.path.dirname(os.path.abspath(__file__))
DB_REAL = os.path.join(CARPETA, "datos", "scb.db")
DB_SIMULADA = os.path.join(CARPETA, "datos", "scb_simulado.db")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS telemetria (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,            -- hora del PC (segundos Unix)
    seq INTEGER,                 -- correlativo del Arduino (detecta pérdidas)
    ms INTEGER,                  -- millis() del Arduino
    estado TEXT,
    dist REAL,                   -- cm, -1 = sin eco
    peso REAL,                   -- g
    ind INTEGER,                 -- 1 = inductivo detecta metal
    cap INTEGER,                 -- 1 = capacitivo detecta
    fsr INTEGER                  -- 0-1023
);
CREATE INDEX IF NOT EXISTS idx_tel_ts ON telemetria(ts);

CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    ciclo INTEGER,               -- número de ciclo del Arduino (desde su encendido)
    resultado TEXT,              -- OK, FALLA_AGARRE, SOBREPESO, FALSA_DETECCION, PARO
    material TEXT,               -- METAL, PLASTICO, DESCARTE, NINGUNO (lo que decidió)
    via TEXT,                    -- U = ultrasónico, P = masa
    peso REAL,
    pct_ind INTEGER,
    pct_cap INTEGER,
    fsr_max INTEGER,
    intentos INTEGER,
    latencia_ms INTEGER,         -- detección -> material decidido
    ciclo_ms INTEGER,            -- detección -> vuelta a reposo
    material_real TEXT,          -- lo anota el operario en el dashboard
    nota TEXT
);
CREATE INDEX IF NOT EXISTS idx_evt_ts ON eventos(ts);

CREATE TABLE IF NOT EXISTS estados (id INTEGER PRIMARY KEY, ts REAL NOT NULL, estado TEXT);
CREATE TABLE IF NOT EXISTS mensajes (id INTEGER PRIMARY KEY, ts REAL NOT NULL, tipo TEXT, texto TEXT);
CREATE TABLE IF NOT EXISTS comandos (id INTEGER PRIMARY KEY, ts REAL NOT NULL, comando TEXT NOT NULL,
                                     enviado_ts REAL);
CREATE TABLE IF NOT EXISTS vaciados (id INTEGER PRIMARY KEY, ts REAL NOT NULL, contenedor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS meta (clave TEXT PRIMARY KEY, valor TEXT);
"""

MATERIALES = ["METAL", "PLASTICO", "DESCARTE"]


def conectar(ruta=DB_REAL, simulada=False):
    """Abre (o crea) la base y deja el esquema listo."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    con = sqlite3.connect(ruta, timeout=10, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")      # lector y escritor a la vez
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript(ESQUEMA)
    if simulada:
        con.execute("INSERT OR REPLACE INTO meta VALUES ('origen', 'simulado')")
    else:
        con.execute("INSERT OR IGNORE INTO meta VALUES ('origen', 'real')")
    con.commit()
    return con


def es_simulada(con):
    fila = con.execute("SELECT valor FROM meta WHERE clave='origen'").fetchone()
    return bool(fila) and fila["valor"] == "simulado"


def encolar_comando(con, comando):
    """El dashboard deja una orden; el gateway la envía al Arduino."""
    con.execute("INSERT INTO comandos (ts, comando) VALUES (?, ?)", (time.time(), comando.strip().upper()))
    con.commit()


def registrar_vaciado(con, contenedor):
    con.execute("INSERT INTO vaciados (ts, contenedor) VALUES (?, ?)", (time.time(), contenedor))
    con.commit()


def anotar_material_real(con, evento_id, material_real):
    con.execute("UPDATE eventos SET material_real=? WHERE id=?", (material_real or None, evento_id))
    con.commit()
