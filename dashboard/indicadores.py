"""
indicadores.py — Convierte los datos crudos en información para decidir.

Lo usan el dashboard y el análisis de pruebas (testing/analizar_pruebas.py),
así ambos calculan los indicadores exactamente igual.
"""
import time
from datetime import datetime

import pandas as pd

from db import MATERIALES

# Metas de los requerimientos (Avance 2). Si cambian, cambiarlas aquí.
META_ACIERTO = {"METAL": 90.0, "PLASTICO": 80.0, "DESCARTE": 80.0}
META_EXITO_AGARRE = 95.0       # % de residuos que terminan en un contenedor
META_CICLO_S = 15.0            # tiempo máximo de ciclo
META_PERDIDA_PCT = 1.0         # % máximo de telemetría perdida
RESULTADOS_CICLO = ("OK", "FALLA_AGARRE", "PARO")   # intentos reales de clasificar


def cargar_eventos(con, desde=None):
    q = "SELECT * FROM eventos" + (" WHERE ts >= ?" if desde else "") + " ORDER BY ts"
    df = pd.read_sql_query(q, con, params=(desde,) if desde else ())
    df["hora"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.tz_convert(_zona()).dt.tz_localize(None)
    return df


def cargar_telemetria(con, desde=None, limite=None):
    q = "SELECT * FROM telemetria" + (" WHERE ts >= ?" if desde else "") + " ORDER BY ts"
    if limite:
        q = f"SELECT * FROM ({q[:-len(' ORDER BY ts')]} ORDER BY ts DESC LIMIT {int(limite)}) ORDER BY ts"
    df = pd.read_sql_query(q, con, params=(desde,) if desde else ())
    df["hora"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.tz_convert(_zona()).dt.tz_localize(None)
    return df


def _zona():
    """Zona horaria del PC (la hora que ve el operario)."""
    return datetime.now().astimezone().tzinfo


def resumen(ev):
    """Indicadores principales de un conjunto de eventos."""
    r = dict(total=len(ev))
    for res in ("OK", "FALLA_AGARRE", "SOBREPESO", "FALSA_DETECCION", "PARO"):
        r[res] = int((ev["resultado"] == res).sum()) if len(ev) else 0
    intentos = r["OK"] + r["FALLA_AGARRE"]
    r["exito_pct"] = 100 * r["OK"] / intentos if intentos else None
    ok = ev[ev["resultado"] == "OK"] if len(ev) else ev
    r["ciclo_medio_s"] = ok["ciclo_ms"].mean() / 1000 if len(ok) else None
    r["ciclo_p95_s"] = ok["ciclo_ms"].quantile(0.95) / 1000 if len(ok) else None
    r["latencia_media_s"] = ok["latencia_ms"].mean() / 1000 if len(ok) else None
    r["masa_total_g"] = float(ok["peso"].sum()) if len(ok) else 0.0
    rec = ok[ok["material"].isin(["METAL", "PLASTICO"])] if len(ok) else ok
    r["masa_reciclable_g"] = float(rec["peso"].sum()) if len(rec) else 0.0
    r["reciclable_pct"] = 100 * r["masa_reciclable_g"] / r["masa_total_g"] if r["masa_total_g"] else None
    r["composicion"] = {m: int((ok["material"] == m).sum()) if len(ok) else 0 for m in MATERIALES}
    r["reintentos"] = int((ok["intentos"] > 1).sum()) if len(ok) else 0
    return r


def matriz_confusion(ev):
    """Filas = material real (anotado), columnas = lo que decidió el sistema."""
    et = ev[ev["material_real"].isin(MATERIALES) & ev["material"].isin(MATERIALES)] if len(ev) else ev
    m = pd.crosstab(pd.Categorical(et["material_real"], MATERIALES), pd.Categorical(et["material"], MATERIALES),
                    rownames=["real"], colnames=["sistema"], dropna=False) if len(et) else \
        pd.DataFrame(0, index=MATERIALES, columns=MATERIALES)
    return m.reindex(index=MATERIALES, columns=MATERIALES, fill_value=0)


def acierto_por_clase(cm):
    """% de residuos de cada material real que el sistema identificó bien."""
    filas = []
    for m in MATERIALES:
        n = int(cm.loc[m].sum())
        bien = int(cm.loc[m, m])
        filas.append(dict(material=m, n=n, correctos=bien, acierto_pct=100 * bien / n if n else None,
                          meta_pct=META_ACIERTO[m]))
    total = int(cm.values.sum())
    global_pct = 100 * sum(cm.loc[m, m] for m in MATERIALES) / total if total else None
    return pd.DataFrame(filas), global_pct


def llenado_contenedores(con, cap_unidades, cap_gramos):
    """Unidades y masa en cada contenedor desde su último vaciado."""
    filas = []
    for m in MATERIALES:
        v = con.execute("SELECT MAX(ts) FROM vaciados WHERE contenedor=?", (m,)).fetchone()[0] or 0
        n, g = con.execute("SELECT COUNT(*), COALESCE(SUM(peso),0) FROM eventos "
                           "WHERE resultado='OK' AND material=? AND ts > ?", (m, v)).fetchone()
        pct = max(100 * n / cap_unidades if cap_unidades else 0, 100 * g / cap_gramos if cap_gramos else 0)
        filas.append(dict(contenedor=m, unidades=n, gramos=g, pct=min(pct, 100.0), vaciado_ts=v or None))
    return pd.DataFrame(filas)


def perdida_telemetria(tel):
    """Paquetes perdidos según los saltos del número de secuencia."""
    if len(tel) < 2:
        return 0, len(tel), 0.0
    s = tel["seq"].dropna().astype(int).to_numpy()
    d = s[1:] - s[:-1]
    perdidos = int(d[d > 1].sum() - (d > 1).sum())     # un salto de 1 a 4 = 2 perdidos
    recibidos = len(s)
    return perdidos, recibidos, 100 * perdidos / (perdidos + recibidos)


def alertas(ultima_tel, ev_recientes, llenado, umbral_llenado, perdida_pct):
    """Lista de (nivel, mensaje, acción sugerida). nivel: error | warning | info."""
    out = []
    ahora = time.time()
    if ultima_tel is None:
        out.append(("error", "No hay datos del Arduino", "Inicie gateway.py y revise el cable USB."))
    else:
        edad = ahora - ultima_tel["ts"]
        if edad > 5:
            out.append(("error", f"Sin telemetría hace {edad:.0f} s",
                        "Revise que gateway.py siga corriendo y el cable USB."))
        est = ultima_tel["estado"]
        if est == "SIN_CALIBRAR":
            out.append(("warning", "Brazo sin calibrar", "Guarde las poses con PAUSA / MOVER / GUARDAR."))
        elif est == "PARADO":
            out.append(("error", "PARO de emergencia activo", "Retire el residuo de la pinza y pulse Reanudar."))
        elif est == "RETIRO_MANUAL":
            out.append(("warning", "Retiro manual pendiente", "Saque el residuo de la bandeja."))
        elif est == "PAUSADO":
            out.append(("info", "Sistema en pausa", "Pulse Reanudar para seguir clasificando."))
        if est in ("ESPERANDO", "PAUSADO") and ultima_tel["peso"] is not None and ultima_tel["peso"] < -3:
            out.append(("warning", f"Balanza marca {ultima_tel['peso']:.1f} g con la bandeja vacía",
                        "Pulse Tarar con la bandeja vacía."))

    for _, c in llenado.iterrows():
        if c["pct"] >= 100:
            out.append(("error", f"Contenedor {c['contenedor']} lleno",
                        "Vacíelo ahora y marque «vaciado»; pause si no puede vaciarlo."))
        elif c["pct"] >= umbral_llenado:
            out.append(("warning", f"Contenedor {c['contenedor']} al {c['pct']:.0f} %",
                        "Programe el vaciado en los próximos residuos."))

    ult = ev_recientes.tail(5) if len(ev_recientes) else ev_recientes
    fallas = int((ult["resultado"] == "FALLA_AGARRE").sum()) if len(ult) else 0
    if fallas >= 2:
        out.append(("warning", f"{fallas} fallas de agarre en los últimos 5 ciclos",
                    "Revise la pinza, recalibre la pose BANDEJA o baje el umbral del FSR."))
    hora = ev_recientes[ev_recientes["ts"] > ahora - 3600] if len(ev_recientes) else ev_recientes
    falsas = int((hora["resultado"] == "FALSA_DETECCION").sum()) if len(hora) else 0
    if falsas >= 3:
        out.append(("warning", f"{falsas} falsas detecciones en la última hora",
                    "Revise que nada pase frente al ultrasónico (brazo, manos, cables)."))
    if len(hora) and (hora["resultado"] == "SOBREPESO").sum() >= 2:
        out.append(("info", "Llegan residuos sobre 100 g", "Separe a mano vidrio y objetos pesados antes de la bandeja."))
    if perdida_pct > META_PERDIDA_PCT:
        out.append(("warning", f"Se perdió el {perdida_pct:.1f} % de la telemetría",
                    "Cambie el cable USB o aléjelo de los cables de los servos."))
    return out
