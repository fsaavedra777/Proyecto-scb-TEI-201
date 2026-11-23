"""
analizar_pruebas.py — Calcula los resultados del protocolo de pruebas a partir de los datos reales.

Lee la base que guardó el gateway (dashboard/datos/scb.db) y, si existen, las planillas
que se llenan a mano (datos/pesaje.csv y datos/deteccion.csv). Escribe:
  resultados/reporte_pruebas.md     tablas con cada indicador, la meta y si se cumple
  resultados/*.png                  gráficos para el informe y las diapositivas

Uso:
  python analizar_pruebas.py                                   # todo el histórico
  python analizar_pruebas.py --desde "2026-11-23 10:00" --hasta "2026-11-23 12:00"
  python analizar_pruebas.py --db ruta/a/otra.db
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "dashboard"))
import indicadores as ind                       # noqa: E402  (mismo cálculo que el dashboard)
from db import MATERIALES                       # noqa: E402

RES = os.path.join(AQUI, "resultados")
DATOS = os.path.join(AQUI, "datos")
AZUL, TINTA, TINTA2, GRILLA = "#2a78d6", "#0b0b0b", "#52514e", "#e6e5e1"
META_PESAJE_G = 2.0
META_DETECCION = 100.0


def estilo_ejes(ax):
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.spines["left"].set_color(GRILLA); ax.spines["bottom"].set_color(GRILLA)
    ax.tick_params(colors=TINTA2, labelsize=9)
    ax.yaxis.grid(True, color=GRILLA, linewidth=0.8); ax.set_axisbelow(True)


def cumple(valor, meta, mayor=True):
    if valor is None or pd.isna(valor):
        return "sin datos"
    return "✅ cumple" if (valor >= meta if mayor else valor <= meta) else "❌ no cumple"


def main():
    global RES, DATOS
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(AQUI, "..", "dashboard", "datos", "scb.db"))
    ap.add_argument("--desde"); ap.add_argument("--hasta")
    ap.add_argument("--datos", default=DATOS, help="carpeta con pesaje.csv y deteccion.csv")
    ap.add_argument("--salida", default=RES, help="carpeta donde escribir el reporte y los gráficos")
    a = ap.parse_args()
    RES, DATOS = a.salida, a.datos
    if not os.path.exists(a.db):
        sys.exit(f"No existe {a.db}. Corran gateway.py durante las pruebas o indiquen --db.")
    os.makedirs(RES, exist_ok=True)

    con = sqlite3.connect(a.db)
    desde = datetime.fromisoformat(a.desde).timestamp() if a.desde else None
    hasta = datetime.fromisoformat(a.hasta).timestamp() if a.hasta else None
    ev = ind.cargar_eventos(con, desde)
    tel = ind.cargar_telemetria(con, desde)
    if hasta:
        ev, tel = ev[ev["ts"] <= hasta], tel[tel["ts"] <= hasta]
    simulada = con.execute("SELECT valor FROM meta WHERE clave='origen'").fetchone()
    simulada = bool(simulada) and simulada[0] == "simulado"

    r = ind.resumen(ev)
    cm = ind.matriz_confusion(ev)
    tabla, glob = ind.acierto_por_clase(cm)
    perd, rec, pct_perd = ind.perdida_telemetria(tel)
    ok = ev[ev["resultado"] == "OK"]

    L = []
    L.append("# Resultados del protocolo de pruebas — Proyecto SCB\n")
    if simulada:
        L.append("> ⚠️ **Estos datos vienen de una base SIMULADA. No sirven como evidencia.**\n")
    periodo = f"{ev['hora'].min():%d-%m-%Y %H:%M} a {ev['hora'].max():%d-%m-%Y %H:%M}" if len(ev) else "sin eventos"
    L.append(f"Generado el {datetime.now():%d-%m-%Y %H:%M} desde `{os.path.basename(a.db)}`. Período: {periodo}.\n")

    L.append("## P3 · Identificación de material\n")
    L.append("| Material real | Anotados | Correctos | Acierto | Meta | Resultado |\n|---|---|---|---|---|---|")
    for _, f in tabla.iterrows():
        ac = "—" if pd.isna(f["acierto_pct"]) else f"{f['acierto_pct']:.0f} %"
        L.append(f"| {f['material']} | {f['n']} | {f['correctos']} | {ac} | ≥ {f['meta_pct']:.0f} % | "
                 f"{cumple(f['acierto_pct'], f['meta_pct'])} |")
    L.append(f"\nAcierto global: **{'—' if glob is None else f'{glob:.0f} %'}** sobre {int(cm.values.sum())} residuos anotados.\n")
    L.append("Matriz de confusión (filas = material real, columnas = lo que decidió el sistema):\n")
    L.append("| | " + " | ".join(MATERIALES) + " |\n|---|" + "---|" * len(MATERIALES))
    for m in MATERIALES:
        L.append(f"| **{m}** | " + " | ".join(str(int(cm.loc[m, c])) for c in MATERIALES) + " |")

    L.append("\n## P4 · Agarre y depósito\n")
    L.append("| Indicador | Valor | Meta | Resultado |\n|---|---|---|---|")
    ex = r["exito_pct"]
    L.append(f"| Residuos que terminaron en un contenedor (OK / (OK + falla de agarre)) | "
             f"{'—' if ex is None else f'{ex:.0f} %'} ({r['OK']} de {r['OK'] + r['FALLA_AGARRE']}) | ≥ {ind.META_EXITO_AGARRE:.0f} % | "
             f"{cumple(ex, ind.META_EXITO_AGARRE)} |")
    L.append(f"| Residuos que necesitaron 2 intentos | {r['reintentos']} | — | informativo |")
    L.append(f"| Sobrepeso detectado y rechazado | {r['SOBREPESO']} | — | informativo |")

    L.append("\n## P5 · Tiempos\n")
    L.append("| Indicador | Media | Desv. estándar | p95 | Máximo | Meta | Resultado |\n|---|---|---|---|---|---|---|")
    if len(ok):
        cs, ls = ok["ciclo_ms"] / 1000, ok["latencia_ms"] / 1000
        L.append(f"| Tiempo de ciclo (s) | {cs.mean():.1f} | {cs.std():.1f} | {cs.quantile(.95):.1f} | {cs.max():.1f} | "
                 f"≤ {ind.META_CICLO_S:.0f} | {cumple(cs.mean(), ind.META_CICLO_S, mayor=False)} |")
        L.append(f"| Latencia de clasificación (s) | {ls.mean():.2f} | {ls.std():.2f} | {ls.quantile(.95):.2f} | {ls.max():.2f} | "
                 f"≤ 3 | {cumple(ls.mean(), 3, mayor=False)} |")
    else:
        L.append("| — | sin residuos OK | | | | | |")

    L.append("\n## P6 · Continuidad de la captura y persistencia\n")
    dur = (tel["ts"].iloc[-1] - tel["ts"].iloc[0]) / 60 if len(tel) > 1 else 0
    L.append("| Indicador | Valor | Meta | Resultado |\n|---|---|---|---|")
    L.append(f"| Duración registrada | {dur:.1f} min | ≥ 30 min | {cumple(dur, 30)} |")
    L.append(f"| Paquetes de telemetría recibidos / perdidos | {rec} / {perd} | — | — |")
    L.append(f"| Telemetría perdida | {pct_perd:.2f} % | ≤ {ind.META_PERDIDA_PCT:.0f} % | {cumple(pct_perd, ind.META_PERDIDA_PCT, mayor=False)} |")
    if len(tel) > 1:
        dt = tel["ts"].diff().dropna()
        L.append(f"| Periodo medio entre paquetes | {dt.median() * 1000:.0f} ms | 500 ms | informativo |")

    # ---- P1 pesaje (planilla manual)
    ruta_p = os.path.join(DATOS, "pesaje.csv")
    L.append("\n## P1 · Exactitud de la balanza\n")
    if os.path.exists(ruta_p):
        p = pd.read_csv(ruta_p, comment="#").dropna()
        p["error_g"] = p["lectura_g"] - p["masa_patron_g"]
        g = p.groupby("masa_patron_g")["error_g"].agg(["count", "mean", "std", lambda s: s.abs().max()])
        g.columns = ["n", "error medio", "desv. est.", "error máx. abs."]
        L.append("| Masa patrón (g) | n | Error medio (g) | Desv. est. (g) | Error máx. (g) |\n|---|---|---|---|---|")
        for m, f in g.iterrows():
            L.append(f"| {m:g} | {int(f['n'])} | {f['error medio']:+.2f} | {f['desv. est.']:.2f} | {f['error máx. abs.']:.2f} |")
        emax = p["error_g"].abs().max()
        L.append(f"\nError máximo: **{emax:.2f} g** (meta ±{META_PESAJE_G:g} g) → {cumple(emax, META_PESAJE_G, mayor=False)}\n")
        fig, ax = plt.subplots(figsize=(6, 3.2))
        ax.scatter(p["masa_patron_g"], p["error_g"], s=36, color=AZUL, edgecolor="white", linewidth=1.5, zorder=3)
        for y in (META_PESAJE_G, -META_PESAJE_G):
            ax.axhline(y, color=TINTA2, linestyle=":", linewidth=1)
        ax.text(p["masa_patron_g"].max(), META_PESAJE_G, f" ±{META_PESAJE_G:g} g", color=TINTA2, va="bottom", ha="right", fontsize=8)
        ax.set_xlabel("Masa patrón (g)", color=TINTA2); ax.set_ylabel("Error (g)", color=TINTA2)
        ax.set_title("Error de la balanza por masa patrón", color=TINTA, fontsize=11, loc="left")
        estilo_ejes(ax); fig.tight_layout(); fig.savefig(os.path.join(RES, "pesaje_error.png"), dpi=160); plt.close(fig)
        L.append("![Error de pesaje](pesaje_error.png)\n")
    else:
        L.append("Sin datos: llenen `datos/pesaje.csv` (ver `datos/plantilla_pesaje.csv`).\n")

    # ---- P2 detección (planilla manual)
    ruta_d = os.path.join(DATOS, "deteccion.csv")
    L.append("## P2 · Detección de llegada\n")
    if os.path.exists(ruta_d):
        d = pd.read_csv(ruta_d, comment="#").dropna(subset=["situacion", "detecto"])
        d["detecto"] = d["detecto"].astype(str).str.lower().str.startswith("s")
        obj = d[d["situacion"].str.lower() == "residuo"]
        otro = d[d["situacion"].str.lower() != "residuo"]
        tasa = 100 * obj["detecto"].mean() if len(obj) else None
        falsos = int(otro["detecto"].sum())
        L.append("| Indicador | Valor | Meta | Resultado |\n|---|---|---|---|")
        L.append(f"| Residuos detectados | {'—' if tasa is None else f'{tasa:.0f} %'} ({int(obj['detecto'].sum())} de {len(obj)}) | "
                 f"{META_DETECCION:.0f} % | {cumple(tasa, META_DETECCION)} |")
        L.append(f"| Falsas detecciones (mano, brazo, nada) | {falsos} de {len(otro)} | 0 | "
                 f"{'✅ cumple' if falsos == 0 and len(otro) else ('sin datos' if not len(otro) else '❌ no cumple')} |")
        via = ev["via"].value_counts()
        L.append(f"\nEn la base: {int(via.get('U', 0))} llegadas confirmadas por ultrasónico y {int(via.get('P', 0))} por masa "
                 f"(objetos sin eco); {r['FALSA_DETECCION']} falsas detecciones descartadas por masa.\n")
    else:
        L.append("Sin datos: llenen `datos/deteccion.csv` (ver `datos/plantilla_deteccion.csv`).\n")

    # ---- gráficos de la base
    if len(ok):
        fig, ax = plt.subplots(figsize=(6, 3.2))
        ax.hist(ok["ciclo_ms"] / 1000, bins=12, color=AZUL, edgecolor="white", linewidth=2)
        ax.axvline(ind.META_CICLO_S, color=TINTA2, linestyle=":", linewidth=1)
        ax.text(ind.META_CICLO_S, ax.get_ylim()[1] * 0.95, f" meta {ind.META_CICLO_S:.0f} s", color=TINTA2, fontsize=8, va="top")
        ax.set_xlabel("Tiempo de ciclo (s)", color=TINTA2); ax.set_ylabel("Residuos", color=TINTA2)
        ax.set_title("Distribución del tiempo de ciclo", color=TINTA, fontsize=11, loc="left")
        estilo_ejes(ax); fig.tight_layout(); fig.savefig(os.path.join(RES, "tiempo_ciclo.png"), dpi=160); plt.close(fig)
        L.append("![Tiempo de ciclo](tiempo_ciclo.png)\n")
    if cm.values.sum():
        fig, ax = plt.subplots(figsize=(4.4, 3.6))
        ax.imshow(cm.values, cmap="Blues")
        for i in range(3):
            for j in range(3):
                v = int(cm.values[i, j])
                ax.text(j, i, v, ha="center", va="center", fontsize=11,
                        color="white" if v > cm.values.max() * 0.55 else TINTA)
        ax.set_xticks(range(3), [m.capitalize() for m in MATERIALES]); ax.set_yticks(range(3), [m.capitalize() for m in MATERIALES])
        ax.set_xlabel("Decidió el sistema", color=TINTA2); ax.set_ylabel("Material real", color=TINTA2)
        ax.set_title("Matriz de confusión", color=TINTA, fontsize=11, loc="left")
        ax.tick_params(colors=TINTA2, labelsize=9)
        fig.tight_layout(); fig.savefig(os.path.join(RES, "matriz_confusion.png"), dpi=160); plt.close(fig)
        L.append("![Matriz de confusión](matriz_confusion.png)\n")

    L.append("## Composición del lote (validación contra el problema)\n")
    tot = sum(r["composicion"].values()) or 1
    L.append("| Material | Residuos | % |\n|---|---|---|")
    for m in MATERIALES:
        L.append(f"| {m} | {r['composicion'][m]} | {100 * r['composicion'][m] / tot:.0f} % |")
    pct_rec = "—" if r["reciclable_pct"] is None else f"{r['reciclable_pct']:.0f} %"
    L.append(f"\nMasa clasificada: {r['masa_total_g']:.0f} g, de la cual {r['masa_reciclable_g']:.0f} g es reciclable "
             f"(metal + plástico) = {pct_rec}.")

    with open(os.path.join(RES, "reporte_pruebas.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\nEscrito en {os.path.join(RES, 'reporte_pruebas.md')}")


if __name__ == "__main__":
    main()
