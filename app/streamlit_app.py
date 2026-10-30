"""MegaMarket · Centro de decisiones — app de Streamlit (Sprints 1–4).

Correr localmente:  streamlit run app/streamlit_app.py
"""
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from megamarket import agente, difuso, experto, portafolio as pf, rutas  # noqa: E402
from megamarket.datos import cargar_memoria_logistica, leer_csv  # noqa: E402

st.set_page_config(page_title="MegaMarket · Centro de decisiones", page_icon="🚚", layout="wide")

AZUL, AZUL_SUAVE, TINTA, GRIS = "#2f5bea", "#e8eefc", "#0b1020", "#8a90a2"
COLOR_SET = {"Baja": "#b9bfcc", "Media": "#7c9cf5", "Alta": AZUL, "Reciente": "#b9bfcc", "Normal": "#7c9cf5",
             "Vencido": AZUL, "Bajo": "#b9bfcc", "Medio": "#7c9cf5", "Alto": AZUL, "Sin alerta": "#b9bfcc",
             "Incierto": "#7c9cf5"}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.block-container {{ padding-top: 2rem; max-width: 1200px; }}
.hero .titulo {{ font-family: 'Inter', sans-serif; font-size: 3rem; line-height: 1.08; font-weight: 700; color: {TINTA}; margin: 0 0 .8rem; letter-spacing: -0.03em; }}
.hero .titulo span {{ color: {AZUL}; }}
.hero p {{ font-size: 1.1rem; color: #4a5068; max-width: 720px; }}
.kpi {{ border: 1px solid #e6e8ef; border-radius: 18px; padding: 1.1rem 1.3rem; background: #fff; }}
.kpi b {{ display: block; font-size: 1.9rem; color: {TINTA}; }}
.kpi span {{ color: {GRIS}; font-size: .9rem; }}
.card {{ border: 1px solid #e6e8ef; border-radius: 18px; padding: 1.2rem 1.3rem; background: #fafbff; height: 100%; }}
.card small {{ color: {AZUL}; font-weight: 600; letter-spacing: .04em; }}
.card h4 {{ margin: .3rem 0 .4rem; }}
.pill {{ display: inline-block; padding: .15rem .65rem; border-radius: 999px; font-size: .8rem; font-weight: 600; }}
.stTabs [data-baseweb="tab-list"] {{ gap: .4rem; }}
.stTabs [data-baseweb="tab"] {{ border-radius: 999px; padding: .4rem 1rem; background: #f3f5fa; }}
.stTabs [aria-selected="true"] {{ background: {AZUL} !important; color: white !important; }}
</style>""", unsafe_allow_html=True)


def millones(x):
    return f"${x / 1e6:,.1f} M"


# =============================================================================
# Encabezado
# =============================================================================
st.markdown("""<div class="hero">
<div class="titulo">Decisiones <span>precisas</span>,<br>despachos <span>inmediatos</span></div>
<p>MegaMarket SAS conecta rutas con A*, reglas de negocio, lógica difusa y algoritmos genéticos
en un solo flujo: quién recibe pedido esta semana, en qué orden, y qué productos Riovalle lanzar.</p>
</div>""", unsafe_allow_html=True)

tab_inicio, tab_despacho, tab_difuso, tab_portafolio, tab_agente = st.tabs(
    ["Inicio", "Despacho semanal", "Lógica difusa", "Portafolio", "Agente IA"])

# =============================================================================
# INICIO
# =============================================================================
with tab_inicio:
    km_p = rutas.ruta_de_la_semana("Poblado", rutas.clientes_de_ruta("Poblado"))[1]
    km_s = rutas.ruta_de_la_semana("Valle de Aburrá", rutas.clientes_de_ruta("Valle de Aburrá"))[1]
    c = st.columns(4)
    for col, valor, texto in zip(c, [f"{km_p:.1f} km", f"{km_s:.1f} km", "$122 M", "11 reglas"],
                                 ["Ruta Poblado completa (A*)", "Ruta Sur completa (A*)",
                                  "Utilidad anual óptima del portafolio", "Base de reglas difusas (Sprint 4)"]):
        col.markdown(f'<div class="kpi"><b>{valor}</b><span>{texto}</span></div>', unsafe_allow_html=True)
    st.write("")
    c = st.columns(4)
    tarjetas = [
        ("SPRINT 1", "Ruta óptima con A*", "Bodega Olaya Herrera → clientes → Plataforma Logística. h(n) = haversine, "
                                             "vecino más cercano entre paradas."),
        ("SPRINT 2", "Sistemas expertos", "Reglas R1–R6 para la ruta semanal y criterios C1–C7 para nuevas "
                                           "categorías. Memoria de trabajo en CSV."),
        ("SPRINT 3", "Algoritmo genético", "Mochila con presupuesto y bodega. Extensión Minimax: ¿y si un rival "
                                            "copia el producto?"),
        ("SPRINT 4", "Lógica difusa + agente", "Prioridad de despacho 0–100 (Mamdani) en vez de sí/no, y un agente "
                                                "que consulta los modelos."),
    ]
    for col, (tag, titulo, texto) in zip(c, tarjetas):
        col.markdown(f'<div class="card"><small>{tag}</small><h4>{titulo}</h4>{texto}</div>', unsafe_allow_html=True)
    st.write("")
    st.info("Los montos del portafolio y la erosión del competidor son supuestos ilustrativos. "
            "Las coordenadas son estimadas por nomenclatura vial (±200–400 m).")

# =============================================================================
# DESPACHO SEMANAL — difuso (Sprint 4) vs experto (Sprint 2) + A*
# =============================================================================
with tab_despacho:
    st.subheader("¿Quién recibe pedido esta semana y en qué orden?")
    st.caption("Edita la memoria de trabajo (lo que reporta el mercaderista) y la decisión se recalcula. "
               "Los cambios viven solo en esta sesión; el CSV del repositorio no se modifica.")

    memoria_df = leer_csv("memoria_trabajo_logistica.csv")
    memoria_editada = st.data_editor(
        memoria_df, use_container_width=True, hide_index=True, disabled=["cliente"],
        column_config={
            "visita_mercaderista_disponible": st.column_config.SelectboxColumn(options=["Sí", "No"]),
            "mercaderista_reporta_stock_bajo": st.column_config.SelectboxColumn(options=["Sí", "No", "No hubo visita"]),
            "queja_urgente": st.column_config.SelectboxColumn(options=["Sí", "No"]),
            "precio_actualizado_en_punto_de_venta": st.column_config.SelectboxColumn(options=["Sí", "No"]),
        })
    memoria = cargar_memoria_logistica(memoria_editada)

    col1, col2 = st.columns([1, 1])
    ruta = col1.radio("Ruta", rutas.RUTAS, horizontal=True)
    metodo = col2.radio("Sistema de decisión", ["Lógica difusa (Sprint 4)", "Sistema experto (Sprint 2)"],
                        horizontal=True)

    inc_d, pri_d, det_d = difuso.decidir_ruta_difusa(ruta, memoria)
    inc_e, pri_e, det_e = experto.decidir_clientes_de_la_ruta(ruta, memoria)
    incluidos, prioridad = (inc_d, pri_d) if metodo.startswith("Lógica") else (inc_e, pri_e)
    paradas, km, orden = rutas.ruta_de_la_semana(ruta, incluidos, prioridad)

    tabla = pd.DataFrame([{
        "Cliente": c,
        "Difuso: prioridad": None if det_d[c]["prioridad"] is None else round(det_d[c]["prioridad"], 1),
        "Difuso: decisión": det_d[c]["decision"] + (f" · {det_d[c]['tanda']}" if det_d[c]["tanda"] else ""),
        "Experto: decisión": ("INCLUIDO · " + det_e[c]["prioridad"]) if det_e[c]["incluir_en_ruta"] else "EXCLUIDO",
        "Orden de visita": str(orden.index(c) + 1) if c in orden else "No entra en la ruta",
    } for c in det_d])
    st.dataframe(tabla, use_container_width=True, hide_index=True,
                 column_config={"Difuso: prioridad": st.column_config.ProgressColumn(
                     min_value=0, max_value=100, format="%.1f")})

    m1, m2, m3 = st.columns(3)
    m1.metric("Clientes en ruta", f"{len(incluidos)} de {len(det_d)}")
    m2.metric("Distancia del recorrido", f"{km:.1f} km")
    otro_km = rutas.ruta_de_la_semana(ruta, *((inc_e, pri_e) if metodo.startswith("Lógica") else (inc_d, pri_d)))[1]
    m3.metric("Con el otro sistema", f"{otro_km:.1f} km", delta=f"{km - otro_km:+.1f} km", delta_color="inverse")

    st.markdown("**Recorrido:** " + " → ".join(paradas))

    # Mapa
    puntos = pd.DataFrame([{"nodo": n, "lat": lat, "lon": lon, "tipo": rutas.TIPO_NODO[n],
                            "en_ruta": n in incluidos or rutas.TIPO_NODO[n] != "cliente"}
                           for n, (lat, lon) in rutas.COORDENADAS.items()
                           if n in rutas.REDES[ruta] or n in (rutas.ORIGEN, rutas.DESTINO_FINAL)])
    puntos["color"] = puntos.apply(lambda f: [47, 91, 234] if f["en_ruta"] and f["tipo"] == "cliente"
                                   else [11, 16, 32] if f["tipo"] in ("bodega", "destino")
                                   else [138, 144, 162] if f["tipo"] == "acceso" else [210, 214, 224], axis=1)
    camino = [{"path": [[rutas.COORDENADAS[n][1], rutas.COORDENADAS[n][0]] for n in paradas]}]
    st.pydeck_chart(pdk.Deck(
        initial_view_state=pdk.ViewState(latitude=puntos["lat"].mean(), longitude=puntos["lon"].mean(), zoom=12.3),
        layers=[pdk.Layer("PathLayer", camino, get_path="path", get_color=[47, 91, 234], width_min_pixels=4),
                pdk.Layer("ScatterplotLayer", puntos, get_position=["lon", "lat"], get_fill_color="color",
                          get_radius=110, pickable=True)],
        tooltip={"text": "{nodo}"}, map_style=None))
    st.caption("El trazo une las paradas en línea recta; la distancia sale del grafo (aristas a mano + haversine), "
               "no de un ruteador vial.")

    with st.expander("Por qué se decidió así cada cliente"):
        for c in det_d:
            st.markdown(f"**{c}** — difuso: {det_d[c]['decision']} · experto: "
                        f"{'INCLUIDO' if det_e[c]['incluir_en_ruta'] else 'EXCLUIDO'}")
            for r in det_d[c]["razones"]:
                st.markdown(f"- {r}")
            for r in det_e[c]["razones"]:
                st.markdown(f"- *Sprint 2:* {r}")

# =============================================================================
# LÓGICA DIFUSA — funciones de pertenencia, reglas y simulador
# =============================================================================
with tab_difuso:
    st.subheader("Sistema de inferencia difusa (Mamdani)")
    st.markdown("Primero se aplican las **restricciones duras** del Sprint 2 (R4 flete > 4 %, R5 PVP "
                "desactualizado) y la **queja urgente** (R3). Lo que queda pasa por el motor difuso: "
                "fuzzificación → reglas (AND = mínimo) → agregación (máximo) → **centroide**.")

    def grafica_variable(var, x_marca=None):
        lo, hi = difuso.UNIVERSO[var]
        x = np.linspace(lo, hi, 400)
        fig, ax = plt.subplots(figsize=(4.2, 2.2))
        for nombre, params in difuso.CONJUNTOS[var].items():
            ax.plot(x, difuso.trapecio(x, *params), color=COLOR_SET.get(nombre, AZUL), lw=2, label=nombre)
        if x_marca is not None:
            ax.axvline(x_marca, color=TINTA, ls="--", lw=1)
        ax.set_ylim(0, 1.08)
        ax.set_title(var.replace("_", " "), fontsize=10, loc="left")
        ax.legend(fontsize=7, frameon=False, loc="upper center", ncol=3, bbox_to_anchor=(0.5, -0.18))
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        fig.tight_layout()
        return fig

    st.markdown("#### Simulador")
    s1, s2, s3, s4 = st.columns(4)
    stock = s1.selectbox("Reporte del mercaderista", ["Sí", "No hubo visita", "No"],
                         help="¿Reportó stock bajo en su visita?")
    rot = s2.selectbox("Rotación en el punto", ["alta", "media", "baja"])
    dias = s3.slider("Días desde la última entrega", 0, 30, 18)
    flete = s4.slider("Flete (% de la factura)", 0.0, 4.0, 2.5, 0.1)
    entradas = {"senal_stock": {"Sí": 1.0, "No": 0.0, "No hubo visita": 0.5}[stock],
                "rotacion": difuso.ROTACION_NUM[rot], "dias_desde_ultima_entrega": dias, "flete_pct": flete}
    inf = difuso.inferir(entradas)

    r1, r2 = st.columns([1, 2])
    with r1:
        st.metric("Prioridad de despacho", f"{inf['prioridad']:.1f} / 100")
        etiqueta = inf["etiqueta"]
        st.markdown(f'<span class="pill" style="background:{AZUL_SUAVE};color:{AZUL}">'
                    f'{etiqueta} → {"entra en tanda " + difuso.TANDA[etiqueta] if etiqueta in difuso.TANDA else "no entra esta semana"}'
                    f'</span>', unsafe_allow_html=True)
        st.write("")
        activas = [a for a in inf["activaciones"] if a["fuerza"] > 0]
        st.dataframe(pd.DataFrame([{"Regla": a["regla"], "Fuerza": round(a["fuerza"], 2), "Salida": a["prioridad"]}
                                   for a in activas]), hide_index=True, use_container_width=True)
    with r2:
        fig, ax = plt.subplots(figsize=(7, 2.8))
        y = inf["universo_salida"]
        for nombre, params in difuso.CONJUNTOS["prioridad"].items():
            ax.plot(y, difuso.trapecio(y, *params), color=COLOR_SET[nombre], lw=1.5, ls=":", label=nombre)
        ax.fill_between(y, inf["agregado"], color=AZUL, alpha=0.25, label="Salida agregada")
        ax.axvline(inf["prioridad"], color=TINTA, lw=2, label=f"Centroide = {inf['prioridad']:.1f}")
        ax.set_xlabel("Prioridad (0–100)")
        ax.set_ylim(0, 1.08)
        ax.legend(fontsize=8, frameon=False, ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.2))
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        fig.tight_layout()
        st.pyplot(fig)

    st.markdown("#### Funciones de pertenencia (data/difuso_conjuntos.csv)")
    g = st.columns(4)
    for col, var in zip(g, difuso.VARIABLES_ENTRADA):
        col.pyplot(grafica_variable(var, entradas[var]))

    st.markdown("#### Base de reglas (data/difuso_reglas.csv)")
    st.dataframe(leer_csv("difuso_reglas.csv"), hide_index=True, use_container_width=True)
    st.caption("“*” significa que la variable no importa en esa regla. Supuesto del modelo: “No hubo visita” se "
               "codifica como 0,5 en la señal de stock (incertidumbre), y la rotación alta/media/baja como 5/3/1.")

# =============================================================================
# PORTAFOLIO — sistema experto C1–C7, AG y Minimax
# =============================================================================
with tab_portafolio:
    st.subheader("Sprint 2 · ¿La categoría es viable?")
    filas = []
    for prod, hechos in experto.cargar_memoria_portafolio().items():
        r = experto.motor_inferencia_portafolio(hechos)
        filas.append({"Categoría": prod, **{c: "✅" if v else "❌" for c, v in r["evaluacion"].items()},
                      "Veredicto": "VIABLE" if r["viable"] else "NO VIABLE"})
    st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)

    st.subheader("Sprint 3 · ¿Qué combinación de productos Riovalle lanzar?")
    a1, a2, a3, a4, a5 = st.columns(5)
    criterio = a1.radio("Criterio", ["esperada", "peor_caso"],
                        format_func=lambda c: "Utilidad esperada" if c == "esperada" else "Minimax (rival)")
    presupuesto = a2.number_input("Presupuesto (COP)", 20_000_000, 160_000_000, pf.PRESUPUESTO_TOTAL, 5_000_000)
    espacio = a3.number_input("Posiciones de bodega", 5, 50, pf.ESPACIO_BODEGA_TOTAL)
    factor = a4.select_slider("Fuerza del rival (× erosión)", [0.5, 0.75, 1.0, 1.25, 1.5], 1.0)
    k = a5.select_slider("Productos que ataca", [1, 2], 1)
    p = pf.Problema(presupuesto=int(presupuesto), espacio=int(espacio), factor_erosion=factor, k_ataques=k)

    mejor, hist = pf.ag_portafolio(criterio, p)
    optimo, empates = pf.fuerza_bruta(criterio, p)
    res = pf.resumen_portafolio(mejor, p)
    valor_ag = res["utilidad_esperada"] if criterio == "esperada" else res["utilidad_peor_caso"]

    b1, b2, b3, b4 = st.columns(4)
    b1.metric("Utilidad esperada", millones(res["utilidad_esperada"]))
    b2.metric("Peor caso (rival ataca " + str(res["producto_que_ataca_el_rival"]) + ")", millones(res["utilidad_peor_caso"]))
    b3.metric("Costo", millones(res["costo"]), f"de {millones(p.presupuesto)}", delta_color="off")
    b4.metric("Bodega", f"{res['espacio']} de {p.espacio}")
    st.markdown("**Portafolio del AG:** " + ", ".join(res["productos"]))
    if abs(valor_ag - optimo) < 1e-6:
        st.success(f"La fuerza bruta (256 combinaciones) confirma el óptimo: {millones(optimo)}. "
                   f"Portafolios empatados: {len(empates)}.")
    else:
        st.warning(f"El AG quedó en {millones(valor_ag)}; la fuerza bruta encuentra {millones(optimo)}. "
                   "Un AG no garantiza el óptimo: prueba con otro escenario o más generaciones.")
    with st.expander("Portafolios óptimos según fuerza bruta"):
        st.dataframe(pd.DataFrame([pf.resumen_portafolio(c, p) for c in empates]), hide_index=True,
                     use_container_width=True)

    fig, ax = plt.subplots(figsize=(9, 2.8))
    col_mejor = "Mejor utilidad esperada" if criterio == "esperada" else "Mejor peor caso"
    ax.plot(hist["Generación"], hist[col_mejor] / 1e6, color=AZUL, lw=2.2, label=col_mejor)
    ax.plot(hist["Generación"], hist["Utilidad promedio"] / 1e6, color=GRIS, lw=1.5, label="Utilidad promedio")
    ax2 = ax.twinx()
    ax2.bar(hist["Generación"], hist["Diversidad"], color=AZUL_SUAVE, alpha=0.8, label="Diversidad")
    ax2.set_ylabel("Portafolios distintos", fontsize=8)
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)
    ax.set_ylabel("Millones COP")
    ax.set_xlabel("Generación")
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    for s in ("top",):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    st.pyplot(fig)

# =============================================================================
# AGENTE IA
# =============================================================================
with tab_agente:
    st.subheader("Pregúntale al centro de decisiones")
    st.caption(f"Modelo: {agente.MODELO}. El agente solo usa números que devuelven las herramientas del proyecto "
               "(A*, sistema experto, lógica difusa, AG, Minimax).")

    clave = None
    try:
        clave = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        pass
    clave = clave or os.environ.get("ANTHROPIC_API_KEY")
    if not clave:
        clave = st.text_input("API key de Anthropic (solo se usa en esta sesión)", type="password")

    if "historial" not in st.session_state:
        st.session_state.historial, st.session_state.chat = [], []

    sugerencias = ["¿A quién despacho esta semana en la ruta Poblado y por qué?",
                   "¿Por qué Five Sisters entra con la lógica difusa?",
                   "¿Qué portafolio conviene si el rival es fuerte (erosión × 1,5)?",
                   "Compara el sistema experto y el difuso en la ruta Sur"]
    cols = st.columns(len(sugerencias))
    pregunta_boton = None
    for col, s in zip(cols, sugerencias):
        if col.button(s, use_container_width=True):
            pregunta_boton = s

    for rol, texto, trazas in st.session_state.chat:
        with st.chat_message(rol):
            for nombre, entrada, _ in trazas:
                st.caption(f"🔧 {nombre}({entrada})")
            st.markdown(texto)

    pregunta = st.chat_input("Escribe tu pregunta") or pregunta_boton
    if pregunta:
        if not clave:
            st.warning("Falta la API key. Configúrala en los secrets de Streamlit (ANTHROPIC_API_KEY) "
                       "o escríbela arriba. El resto de la app funciona sin ella.")
        else:
            import anthropic
            st.session_state.chat.append(("user", pregunta, []))
            st.session_state.historial.append({"role": "user", "content": pregunta})
            with st.chat_message("user"):
                st.markdown(pregunta)
            with st.chat_message("assistant"):
                with st.spinner("Consultando los modelos..."):
                    try:
                        texto, trazas = agente.responder(st.session_state.historial,
                                                         anthropic.Anthropic(api_key=clave))
                    except anthropic.AuthenticationError:
                        texto, trazas = "La API key no es válida.", []
                    except anthropic.RateLimitError:
                        texto, trazas = "Se alcanzó el límite de uso de la API. Intenta en un momento.", []
                    except anthropic.APIStatusError as e:
                        texto, trazas = f"Error de la API ({e.status_code}).", []
                    except anthropic.APIConnectionError:
                        texto, trazas = "No hay conexión con la API de Anthropic.", []
                for nombre, entrada, _ in trazas:
                    st.caption(f"🔧 {nombre}({entrada})")
                st.markdown(texto)
            st.session_state.chat.append(("assistant", texto, trazas))
