"""Sprint 2 — Sistemas expertos (logística y portafolio), misma lógica del notebook."""
from .datos import cargar_clientes, cargar_memoria_logistica, leer_csv, a_booleano

# =============================================================================
# 1. BASE DE CONOCIMIENTO — logística
# =============================================================================
BASE_CONOCIMIENTO = {
    "umbrales": {
        "dias_sin_entrega": 15,        # R2: días sin entrega para activar el respaldo
        "flete_sobre_factura": 0.04,   # R4: tope de flete sobre la factura
    },
    "politicas": {"ventana_entrega_horas": (48, 72)},   # H1
    "clientes": cargar_clientes(),
    "destino_final": "Plataforma Logística",
}

NIVEL_PRIORIDAD = {"ALTA": 3, "MEDIA": 2, "BAJA": 1}
MAPA_ROTACION_PRIORIDAD = {"alta": "ALTA", "media": "MEDIA", "baja": "BAJA"}


def prioridad_mas_alta(actual, nueva):
    if actual is None or NIVEL_PRIORIDAD[nueva] > NIVEL_PRIORIDAD[actual]:
        return nueva
    return actual


def vetos(hechos_semana, umbrales=None):
    """R4 y R5: restricciones duras. Se reutilizan tal cual en el Sprint 4."""
    umbrales = umbrales or BASE_CONOCIMIENTO["umbrales"]
    lista = []
    ratio_flete = hechos_semana["costo_flete_estimado"] / hechos_semana["valor_factura_pedido"]
    if ratio_flete > umbrales["flete_sobre_factura"]:
        lista.append(
            f"R4 (VETO) - El flete (${hechos_semana['costo_flete_estimado']:,}) es el "
            f"{ratio_flete:.1%} de la factura (${hechos_semana['valor_factura_pedido']:,}), "
            f"por encima del {umbrales['flete_sobre_factura']:.0%} permitido"
        )
    if not hechos_semana["precio_actualizado_en_punto_de_venta"]:
        lista.append("R5 (VETO) - El punto de venta no ha actualizado el PVP de la "
                     "referencia según la lista vigente de MegaMarket")
    return lista


def motor_inferencia(cliente, base_conocimiento, memoria_trabajo):
    """Encadenamiento hacia adelante, una pasada por cliente: R1-R3 inclusión,
    R6 exclusión por defecto, R4-R5 veto."""
    hechos_fijos = base_conocimiento["clientes"][cliente]
    hechos_semana = memoria_trabajo[cliente]
    umbrales = base_conocimiento["umbrales"]
    razones = []
    prioridad = None

    # R1: el mercaderista vio stock bajo -> prioridad según rotación
    if hechos_semana["visita_mercaderista_disponible"] and hechos_semana["mercaderista_reporta_stock_bajo"]:
        rotacion = hechos_fijos["rotacion_producto"]
        prioridad_r1 = MAPA_ROTACION_PRIORIDAD[rotacion]
        razones.append(f"R1 - El mercaderista reportó stock bajo en su visita "
                       f"(rotación {rotacion} -> prioridad {prioridad_r1})")
        prioridad = prioridad_mas_alta(prioridad, prioridad_r1)

    # R2: respaldo por falta de visibilidad
    if (not hechos_semana["visita_mercaderista_disponible"]
            and hechos_semana["dias_desde_ultima_entrega"] > umbrales["dias_sin_entrega"]
            and hechos_fijos["rotacion_producto"] in ("media", "alta")):
        razones.append(f"R2 - Sin visita reciente del mercaderista, "
                       f"{hechos_semana['dias_desde_ultima_entrega']} días sin entrega "
                       f"(> {umbrales['dias_sin_entrega']}), rotación {hechos_fijos['rotacion_producto']}")
        prioridad = prioridad_mas_alta(prioridad, "BAJA")

    # R3: queja urgente
    if hechos_semana["queja_urgente"]:
        razones.append("R3 - Queja urgente reportada: debe visitarse primero")
        prioridad = prioridad_mas_alta(prioridad, "ALTA")

    # R6: regla por defecto
    if not razones:
        return {"incluir_en_ruta": False, "prioridad": None,
                "razones": ["R6 - Por defecto: no cumple ningún criterio de inclusión esta semana"]}

    # R4 y R5: veto
    lista_vetos = vetos(hechos_semana, umbrales)
    if lista_vetos:
        return {"incluir_en_ruta": False, "prioridad": None, "razones": razones + lista_vetos}
    return {"incluir_en_ruta": True, "prioridad": prioridad, "razones": razones}


def decidir_clientes_de_la_ruta(nombre_ruta, memoria_trabajo=None, base_conocimiento=None):
    """Corre el motor sobre todos los clientes de una ruta. Devuelve
    (incluidos, {cliente: prioridad}, {cliente: conclusión})."""
    base_conocimiento = base_conocimiento or BASE_CONOCIMIENTO
    memoria_trabajo = memoria_trabajo or cargar_memoria_logistica()
    clientes = [c for c, d in base_conocimiento["clientes"].items() if d["ruta"] == nombre_ruta]
    incluidos, prioridad, detalle = [], {}, {}
    for cliente in clientes:
        conclusion = motor_inferencia(cliente, base_conocimiento, memoria_trabajo)
        detalle[cliente] = conclusion
        if conclusion["incluir_en_ruta"]:
            incluidos.append(cliente)
            prioridad[cliente] = conclusion["prioridad"]
    return incluidos, prioridad, detalle


# =============================================================================
# 2. SISTEMA EXPERTO DE PORTAFOLIO (C1–C7)
# =============================================================================
BASE_CONOCIMIENTO_PORTAFOLIO = {
    "umbrales": {"vida_util_minima_meses": 6, "margen_minimo_pct": 12},
}

CRITERIOS_NOMBRES = {
    "C1": "Afinidad de portafolio y canal/segmento",
    "C2": "Cumplimiento legal (registro sanitario y ficha técnica)",
    "C3": "Viabilidad operativa (transporte, almacenamiento, manipulación)",
    "C4": "Estándares de calidad y presentación",
    "C5": "Complementariedad / venta cruzada",
    "C6": "Vida útil (mínimo 6 meses)",
    "C7": "Precio asequible y rentabilidad",
}


def cargar_memoria_portafolio(df=None):
    df = leer_csv("memoria_trabajo_portafolio.csv") if df is None else df
    return {f["producto"]: {c: a_booleano(f[c]) for c in CRITERIOS_NOMBRES} for _, f in df.iterrows()}


def motor_inferencia_portafolio(hechos):
    """VIABLE solo si se cumplen los 7 criterios a la vez."""
    incumplidos = [c for c in CRITERIOS_NOMBRES if not hechos[c]]
    return {"viable": not incumplidos, "incumplidos": incumplidos,
            "evaluacion": {c: hechos[c] for c in CRITERIOS_NOMBRES}}
