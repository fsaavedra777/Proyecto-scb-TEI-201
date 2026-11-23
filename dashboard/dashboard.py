"""
dashboard.py — Panel del Proyecto SCB (Streamlit).

Convierte los datos que guarda gateway.py en información para decidir:
  En vivo       (operario)       estado, sensores, alertas y llenado de contenedores
  Indicadores   (administrador)  composición, masa reciclable, éxito, tiempos, tendencia
  Validación                     anotar el material real y medir el acierto
  Datos                          tabla completa y descarga en CSV

Uso:  python -m streamlit run dashboard.py      (se abre en http://localhost:8501)
"""
import json
import time
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import db
import indicadores as ind

st.set_page_config(page_title="SCB · Panel", page_icon="♻️", layout="wide")
st.markdown("""<style>
  [data-testid="stSidebar"] button[kind="primary"] {background:#c62828;border-color:#c62828;}
  [data-testid="stMetricValue"] {font-size:1.7rem;}
</style>""", unsafe_allow_html=True)

# Paleta validada (CVD y normal) para los materiales; amarillo = plástico como en NCh 3322
COLOR = {"METAL": "#2a78d6", "PLASTICO": "#eda100", "DESCARTE": "#e87ba4"}
NOMBRE = {"METAL": "Metal", "PLASTICO": "Plástico", "DESCARTE": "Descarte"}
TINTA, TINTA_2, GRILLA = "#0b0b0b", "#52514e", "#e6e5e1"


def estilo(fig, alto=230, titulo=None):
    fig.update_layout(height=alto, margin=dict(l=8, r=8, t=36 if titulo else 8, b=8),
                      title=dict(text=titulo, font=dict(size=14, color=TINTA)) if titulo else None,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=TINTA_2, size=12), hoverlabel=dict(bgcolor="white"),
                      legend=dict(orientation="h", y=1.12, x=0))
    fig.update_xaxes(showgrid=False, linecolor=GRILLA)
    fig.update_yaxes(gridcolor=GRILLA, zeroline=False)
    return fig


# ------------------------------------------------------------------ barra lateral
with st.sidebar:
    st.header("♻️ SCB")
    origen = st.radio("Base de datos", ["Real", "Simulada (solo pruebas)"], horizontal=False)
    ruta = db.DB_REAL if origen == "Real" else db.DB_SIMULADA
    con = db.conectar(ruta, simulada=(origen != "Real"))

    periodo = st.selectbox("Período de los indicadores", ["Última hora", "Hoy", "Últimas 24 h", "Todo"], index=1)
    ahora = datetime.now()
    desde = {"Última hora": ahora - timedelta(hours=1),
             "Hoy": ahora.replace(hour=0, minute=0, second=0, microsecond=0),
             "Últimas 24 h": ahora - timedelta(hours=24), "Todo": None}[periodo]
    desde_ts = desde.timestamp() if desde else None

    st.subheader("Contenedores")
    cap_u = st.number_input("Capacidad (unidades)", 1, 500, 15)
    cap_g = st.number_input("Capacidad (gramos)", 10, 20000, 400, step=50)
    umbral = st.slider("Avisar al llegar a (%)", 50, 95, 80, step=5)

    st.subheader("Control del Arduino")
    c1, c2 = st.columns(2)
    if c1.button("⏸ Pausar", width="stretch"):
        db.encolar_comando(con, "PAUSA"); st.toast("Pausa enviada")
    if c2.button("▶ Reanudar", width="stretch"):
        db.encolar_comando(con, "SEGUIR"); st.toast("Reanudar enviado")
    if c1.button("⚖ Tarar", width="stretch", help="Solo con la bandeja vacía"):
        db.encolar_comando(con, "TARA"); st.toast("Tara enviada")
    if c2.button("ⓘ Estado", width="stretch"):
        db.encolar_comando(con, "ESTADO")
    if st.button("⛔ PARO", type="primary", width="stretch"):
        db.encolar_comando(con, "PARO"); st.toast("PARO enviado")
    st.caption(f"Base: `{ruta}`")

# ------------------------------------------------------------------ encabezado
st.title("Clasificador de residuos SCB")
st.caption("Separa metal, plástico y descarte en el origen y registra qué llega, cuánto se recupera y "
           "cuándo hay que intervenir.")
if db.es_simulada(con):
    st.error("**DATOS SIMULADOS.** Esta base la generó `gateway.py --simular` para probar el panel. "
             "En la demo usen la base Real con el Arduino conectado.", icon="⚠️")

tab_vivo, tab_ind, tab_val, tab_datos = st.tabs(["En vivo", "Indicadores", "Validación", "Datos"])

# ================================================================== EN VIVO
with tab_vivo:
    @st.fragment(run_every="1s")
    def panel_vivo():
        tel = ind.cargar_telemetria(con, desde=time.time() - 120)
        ult = tel.iloc[-1] if len(tel) else None
        if ult is None:
            fila = con.execute("SELECT * FROM telemetria ORDER BY id DESC LIMIT 1").fetchone()
            ult = dict(fila) if fila else None
        ev_rec = ind.cargar_eventos(con, desde=time.time() - 3600)
        llen = ind.llenado_contenedores(con, cap_u, cap_g)
        _, _, perdida = ind.perdida_telemetria(tel)

        # --- estado y sensores
        k = st.columns([1.1, 1.3, 1, 1, 1.4])
        if ult is None:
            k[0].metric("Conexión", "Sin datos")
        else:
            edad = time.time() - ult["ts"]
            k[0].metric("Conexión", "En línea" if edad < 3 else "Sin señal", f"hace {edad:.0f} s",
                        delta_color="off", delta_arrow="off")
            k[1].metric("Estado", str(ult["estado"]).replace("_", " ").capitalize())
            k[2].metric("Peso en bandeja", f"{ult['peso']:.1f} g")
            k[3].metric("Distancia", "sin eco" if ult["dist"] is None or ult["dist"] < 0 else f"{ult['dist']:.1f} cm")
            k[4].metric("Sensores", f"{'● metal' if ult['ind'] else '○ metal'}  {'● cap.' if ult['cap'] else '○ cap.'}",
                        f"FSR {ult['fsr']}", delta_color="off", delta_arrow="off")

        # --- alertas con la acción que corresponde
        lista = ind.alertas(ult, ev_rec, llen, umbral, perdida)
        if lista:
            for nivel, msg, accion in lista:
                getattr(st, nivel)(f"**{msg}.** {accion}",
                                   icon={"error": "🚨", "warning": "⚠️", "info": "ℹ️"}[nivel])
        else:
            st.success("Todo en orden: sin alertas activas.", icon="✅")

        # --- contenedores
        st.subheader("Contenedores")
        cc = st.columns(3)
        for i, (_, c) in enumerate(llen.iterrows()):
            with cc[i]:
                st.markdown(f"**{NOMBRE[c['contenedor']]}** · {c['unidades']} uds · {c['gramos']:.0f} g")
                st.progress(int(c["pct"]), text=f"{c['pct']:.0f} % lleno")
                if st.button("Marcar vaciado", key=f"vaciar_{c['contenedor']}", width="stretch"):
                    db.registrar_vaciado(con, c["contenedor"])
                    st.toast(f"Contenedor {NOMBRE[c['contenedor']]} vaciado")

        # --- señales de los últimos 2 minutos (dos gráficos: escalas distintas)
        g1, g2 = st.columns(2)
        if len(tel):
            f1 = go.Figure(go.Scatter(x=tel["hora"], y=tel["peso"], mode="lines", line=dict(width=2, color="#2a78d6"),
                                      name="Peso", hovertemplate="%{x|%H:%M:%S}<br>%{y:.1f} g<extra></extra>"))
            f1.add_hline(y=5, line=dict(width=1, dash="dot", color=TINTA_2),
                         annotation_text="5 g: mínimo", annotation_font_color=TINTA_2)
            g1.plotly_chart(estilo(f1, titulo="Peso en la bandeja (g), últimos 2 min"), width="stretch")
            d = tel["dist"].where(tel["dist"] >= 0)
            f2 = go.Figure(go.Scatter(x=tel["hora"], y=d, mode="lines", line=dict(width=2, color="#2a78d6"),
                                      name="Distancia", connectgaps=False,
                                      hovertemplate="%{x|%H:%M:%S}<br>%{y:.1f} cm<extra></extra>"))
            f2.add_hline(y=12, line=dict(width=1, dash="dot", color=TINTA_2),
                         annotation_text="12 cm: hay objeto", annotation_font_color=TINTA_2)
            g2.plotly_chart(estilo(f2, titulo="Distancia del ultrasónico (cm)"), width="stretch")
        else:
            g1.info("Sin telemetría en los últimos 2 minutos.")

        # --- último residuo y mensajes del Arduino
        u1, u2 = st.columns(2)
        if len(ev_rec):
            e = ev_rec.iloc[-1]
            u1.markdown(f"**Último residuo** ({e['hora']:%H:%M:%S}): {NOMBRE.get(e['material'], e['material'])} · "
                        f"{e['resultado'].replace('_', ' ').lower()} · {e['peso']:.1f} g · "
                        f"ciclo {e['ciclo_ms'] / 1000:.1f} s · {e['intentos']} intento(s)")
        msgs = con.execute("SELECT ts, tipo, texto FROM mensajes WHERE tipo IN ('log','ack') "
                           "ORDER BY id DESC LIMIT 3").fetchall()
        if msgs:
            textos = []
            for m in msgs:
                d = json.loads(m["texto"])
                textos.append(f"{datetime.fromtimestamp(m['ts']):%H:%M:%S} {d.get('msg') or d.get('cmd')}")
            u2.caption("Arduino: " + " · ".join(textos))

    panel_vivo()

# ================================================================== INDICADORES
with tab_ind:
    @st.fragment(run_every="5s")
    def panel_indicadores():
        ev = ind.cargar_eventos(con, desde=desde_ts)
        r = ind.resumen(ev)
        cm = ind.matriz_confusion(ev)
        tabla_acierto, acierto_global = ind.acierto_por_clase(cm)

        k = st.columns(5)
        k[0].metric("Residuos clasificados", r["OK"], f"{r['total']} eventos en total", delta_color="off", delta_arrow="off")
        k[1].metric("Éxito de agarre", "—" if r["exito_pct"] is None else f"{r['exito_pct']:.0f} %",
                    f"meta ≥ {ind.META_EXITO_AGARRE:.0f} %", delta_color="off", delta_arrow="off")
        k[2].metric("Ciclo medio", "—" if r["ciclo_medio_s"] is None else f"{r['ciclo_medio_s']:.1f} s",
                    f"meta ≤ {ind.META_CICLO_S:.0f} s", delta_color="off", delta_arrow="off")
        k[3].metric("Masa reciclable recuperada", f"{r['masa_reciclable_g']:.0f} g",
                    "—" if r["reciclable_pct"] is None else f"{r['reciclable_pct']:.0f} % de lo clasificado",
                    delta_color="off", delta_arrow="off")
        k[4].metric("Acierto de material", "—" if acierto_global is None else f"{acierto_global:.0f} %",
                    f"{int(cm.values.sum())} residuos anotados", delta_color="off", delta_arrow="off")

        if not len(ev):
            st.info("No hay residuos en este período.")
            return

        c1, c2 = st.columns([1, 1.4])
        # Composición: barras horizontales con etiqueta directa (no torta)
        comp = r["composicion"]
        tot = sum(comp.values()) or 1
        f = go.Figure()
        for m in db.MATERIALES[::-1]:
            f.add_bar(y=[NOMBRE[m]], x=[comp[m]], orientation="h", marker=dict(color=COLOR[m], cornerradius=4),
                      text=f"{comp[m]} ({100 * comp[m] / tot:.0f} %)", textposition="outside",
                      textfont=dict(color=TINTA), name=NOMBRE[m],
                      hovertemplate=f"{NOMBRE[m]}: %{{x}} residuos<extra></extra>")
        f.update_layout(showlegend=False, bargap=0.35)
        f.update_xaxes(range=[0, max(comp.values()) * 1.35 + 1], showgrid=True, gridcolor=GRILLA)
        c1.plotly_chart(estilo(f, 240, "Composición de lo clasificado"), width="stretch")

        # Residuos por hora, apilados por material
        ok = ev[ev["resultado"] == "OK"].copy()
        if len(ok):
            ok["bloque"] = ok["hora"].dt.floor("h" if periodo != "Última hora" else "5min")
            por = ok.pivot_table(index="bloque", columns="material", values="id", aggfunc="count", fill_value=0)
            f = go.Figure()
            for m in db.MATERIALES:
                if m in por:
                    f.add_bar(x=por.index, y=por[m], name=NOMBRE[m], marker=dict(color=COLOR[m], line=dict(width=2, color="white")),
                              hovertemplate=f"{NOMBRE[m]}: %{{y}}<extra>%{{x|%H:%M}}</extra>")
            f.update_layout(barmode="stack", bargap=0.25, legend_traceorder="normal")
            c2.plotly_chart(estilo(f, 240, "Residuos clasificados por " + ("hora" if periodo != "Última hora" else "5 min")),
                            width="stretch")

        c3, c4 = st.columns([1.4, 1])
        # Tiempo de ciclo de cada residuo contra la meta
        if len(ok):
            f = go.Figure()
            for m in db.MATERIALES:
                s = ok[ok["material"] == m]
                if len(s):
                    f.add_scatter(x=s["hora"], y=s["ciclo_ms"] / 1000, mode="markers", name=NOMBRE[m],
                                  marker=dict(size=9, color=COLOR[m], line=dict(width=2, color="white")),
                                  hovertemplate=f"{NOMBRE[m]}<br>%{{x|%H:%M:%S}}<br>%{{y:.1f}} s<extra></extra>")
            f.add_hline(y=ind.META_CICLO_S, line=dict(width=1, dash="dot", color=TINTA_2),
                        annotation_text=f"meta {ind.META_CICLO_S:.0f} s", annotation_font_color=TINTA_2)
            f.update_yaxes(rangemode="tozero", title="s")
            c3.plotly_chart(estilo(f, 250, "Tiempo de ciclo por residuo"), width="stretch")
        # Resultados (incluye fallas): qué tan seguido hay que intervenir
        res = ev["resultado"].value_counts().rename_axis("Resultado").reset_index(name="Eventos")
        res["Resultado"] = res["Resultado"].str.replace("_", " ").str.capitalize()
        c4.markdown("**Resultados del período**")
        c4.dataframe(res, hide_index=True, width="stretch")
        lat = "—" if r["latencia_media_s"] is None else f"{r['latencia_media_s']:.2f} s"
        c4.caption(f"Reintentos que terminaron bien: {r['reintentos']}. Latencia media de clasificación: {lat}.")

    panel_indicadores()

# ================================================================== VALIDACIÓN
with tab_val:
    st.markdown("Anoten el **material real** de cada residuo de prueba. Con eso el panel calcula el acierto "
                "por material contra las metas (metal ≥ 90 %, plástico ≥ 80 %).")
    ev_all = ind.cargar_eventos(con, desde=desde_ts)
    cand = ev_all[ev_all["material"].isin(db.MATERIALES)].tail(60).iloc[::-1]
    if len(cand):
        vista = cand[["id", "hora", "material", "resultado", "peso", "pct_ind", "pct_cap", "material_real"]].copy()
        vista["hora"] = vista["hora"].dt.strftime("%H:%M:%S")
        editado = st.data_editor(
            vista, hide_index=True, width="stretch", disabled=[c for c in vista.columns if c != "material_real"],
            column_config={
                "id": None,
                "material": "Sistema dijo", "resultado": "Resultado", "peso": st.column_config.NumberColumn("Peso (g)", format="%.1f"),
                "pct_ind": st.column_config.NumberColumn("Inductivo %"), "pct_cap": st.column_config.NumberColumn("Capacitivo %"),
                "material_real": st.column_config.SelectboxColumn("Material real", options=db.MATERIALES),
            }, key="editor_validacion")
        if st.button("Guardar anotaciones", type="primary"):
            cambios = 0
            for _, f in editado.iterrows():
                original = cand.loc[cand["id"] == f["id"], "material_real"].iloc[0]
                nuevo = f["material_real"] if isinstance(f["material_real"], str) else None
                if nuevo != (original if isinstance(original, str) else None):
                    db.anotar_material_real(con, int(f["id"]), nuevo)
                    cambios += 1
            st.success(f"{cambios} anotaciones guardadas.")
            st.rerun()
    else:
        st.info("Todavía no hay residuos clasificados en este período.")

    cm = ind.matriz_confusion(ind.cargar_eventos(con, desde=desde_ts))
    tabla, glob = ind.acierto_por_clase(cm)
    v1, v2 = st.columns(2)
    with v1:
        st.markdown("**Matriz de confusión** (filas: real · columnas: lo que decidió el sistema)")
        m = cm.copy()
        m.index = [NOMBRE[i] for i in m.index]
        m.columns = [NOMBRE[c] for c in m.columns]
        st.dataframe(m.style.background_gradient(cmap="Blues", axis=None), width="stretch")
    with v2:
        st.markdown("**Acierto por material**" + ("" if glob is None else f" · global {glob:.0f} %"))
        t = tabla.copy()
        t["material"] = t["material"].map(NOMBRE)
        t["cumple"] = t.apply(lambda f: "—" if pd.isna(f["acierto_pct"]) else
                              ("✅ sí" if f["acierto_pct"] >= f["meta_pct"] else "❌ no"), axis=1)
        # Sin residuos anotados se muestra "—" en vez de "None"
        t["acierto_pct"] = t["acierto_pct"].map(lambda v: "—" if pd.isna(v) else f"{v:.0f}")
        st.dataframe(t.rename(columns={"material": "Material", "n": "Anotados", "correctos": "Correctos",
                                       "acierto_pct": "Acierto %", "meta_pct": "Meta %", "cumple": "Cumple"}),
                     hide_index=True, width="stretch")

# ================================================================== DATOS
with tab_datos:
    ev = ind.cargar_eventos(con, desde=desde_ts)
    st.markdown(f"**{len(ev)} eventos** en el período «{periodo.lower()}».")
    st.dataframe(ev.drop(columns=["ts"]).iloc[::-1], hide_index=True, width="stretch", height=320)
    d1, d2 = st.columns(2)
    d1.download_button("Descargar eventos (CSV)", ev.to_csv(index=False).encode("utf-8"),
                       f"scb_eventos_{datetime.now():%Y%m%d_%H%M}.csv", "text/csv", width="stretch")
    tel = ind.cargar_telemetria(con, desde=desde_ts)
    d2.download_button(f"Descargar telemetría ({len(tel)} filas, CSV)", tel.to_csv(index=False).encode("utf-8"),
                       f"scb_telemetria_{datetime.now():%Y%m%d_%H%M}.csv", "text/csv", width="stretch")
    perd, rec, pct = ind.perdida_telemetria(tel)
    st.caption(f"Continuidad de la captura en el período: {rec} paquetes recibidos, {perd} perdidos ({pct:.2f} %).")
