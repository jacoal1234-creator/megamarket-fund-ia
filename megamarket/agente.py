"""Sprint 4 — Agente de IA (Claude + tool use).

El agente NO calcula nada por su cuenta: cada número sale de una herramienta
que llama a las funciones de los sprints (A*, sistema experto, lógica difusa,
AG, Minimax). El modelo solo decide qué herramienta usar y explica el resultado.
"""
import json
import os

from . import difuso, experto, portafolio as pf, rutas

MODELO = os.environ.get("MEGAMARKET_MODELO", "claude-opus-5-5")

SISTEMA = """Eres el asistente de decisiones de MegaMarket SAS, una distribuidora de alimentos del \
Valle de Aburrá (Colombia) con marca propia Riovalle. Respondes en español, en tono claro y breve.

Tienes herramientas que ejecutan los modelos del proyecto:
- Sprint 1: rutas con A* (bodega Olaya Herrera -> clientes -> Plataforma Logística).
- Sprint 2: sistema experto de logística (reglas R1–R6) y de portafolio (criterios C1–C7).
- Sprint 3: algoritmo genético de portafolio (mochila) y extensión Minimax contra un competidor.
- Sprint 4: lógica difusa (Mamdani) que da una prioridad de despacho de 0 a 100.

Reglas:
- Todo número que digas debe venir de una herramienta. Si no hay herramienta para algo, dilo.
- Los montos del portafolio y la erosión son supuestos ilustrativos; las coordenadas son estimadas (±200–400 m).
- Cuando expliques una decisión, nombra las reglas que la producen (R4, D1, C6...)."""

HERRAMIENTAS = [
    {
        "name": "despacho_semana",
        "description": "Decide qué clientes entran a la ruta de esta semana con el sistema difuso del Sprint 4 "
                       "(vetos R4/R5, queja urgente R3 y prioridad difusa), y calcula el recorrido con A*. "
                       "Puede comparar contra el sistema experto binario del Sprint 2.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ruta": {"type": "string", "enum": ["Poblado", "Valle de Aburrá"]},
                "metodo": {"type": "string", "enum": ["difuso", "experto"],
                           "description": "difuso = Sprint 4; experto = Sprint 2"},
            },
            "required": ["ruta", "metodo"],
            "additionalProperties": False,
        },
    },
    {
        "name": "detalle_cliente",
        "description": "Explica la decisión para un cliente: entradas difusas, grados de pertenencia, "
                       "reglas activadas y la decisión del sistema experto del Sprint 2.",
        "input_schema": {
            "type": "object",
            "properties": {"cliente": {"type": "string", "description": "Nombre exacto del cliente"}},
            "required": ["cliente"],
            "additionalProperties": False,
        },
    },
    {
        "name": "simular_prioridad",
        "description": "Calcula la prioridad difusa de un caso hipotético (qué pasa si...).",
        "input_schema": {
            "type": "object",
            "properties": {
                "stock": {"type": "string", "enum": ["Sí", "No", "No hubo visita"],
                          "description": "Lo que reporta el mercaderista sobre stock bajo"},
                "rotacion": {"type": "string", "enum": ["alta", "media", "baja"]},
                "dias_desde_ultima_entrega": {"type": "integer"},
                "flete_pct": {"type": "number", "description": "Flete como % de la factura (0 a 4)"},
            },
            "required": ["stock", "rotacion", "dias_desde_ultima_entrega", "flete_pct"],
            "additionalProperties": False,
        },
    },
    {
        "name": "optimizar_portafolio",
        "description": "Corre el algoritmo genético del Sprint 3 y lo valida con fuerza bruta. "
                       "criterio 'esperada' maximiza la utilidad anual; 'peor_caso' es Minimax frente a un rival.",
        "input_schema": {
            "type": "object",
            "properties": {
                "criterio": {"type": "string", "enum": ["esperada", "peor_caso"]},
                "presupuesto": {"type": "integer", "description": "COP. Por defecto 70000000"},
                "espacio": {"type": "integer", "description": "Posiciones de bodega. Por defecto 25"},
                "factor_erosion": {"type": "number", "description": "Fuerza del rival. 1.0 = supuesto base"},
                "k_ataques": {"type": "integer", "description": "Productos que ataca el rival a la vez"},
            },
            "required": ["criterio"],
            "additionalProperties": False,
        },
    },
    {
        "name": "viabilidad_categorias",
        "description": "Resultado del sistema experto de portafolio (Sprint 2, criterios C1–C7) para las "
                       "categorías evaluadas.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


# =============================================================================
# Implementación de las herramientas (todo sale de las funciones de los sprints)
# =============================================================================
def _redondear(x):
    return None if x is None else round(float(x), 1)


def despacho_semana(ruta, metodo):
    if metodo == "difuso":
        incluidos, prioridad, detalle = difuso.decidir_ruta_difusa(ruta)
        clientes = {c: {"decision": d["decision"], "prioridad_0_100": _redondear(d["prioridad"]),
                        "tanda": d["tanda"], "razones": d["razones"]} for c, d in detalle.items()}
    else:
        incluidos, prioridad, detalle = experto.decidir_clientes_de_la_ruta(ruta)
        clientes = {c: {"incluir": d["incluir_en_ruta"], "prioridad": d["prioridad"], "razones": d["razones"]}
                    for c, d in detalle.items()}
    paradas, km, orden = rutas.ruta_de_la_semana(ruta, incluidos, prioridad)
    return {"ruta": ruta, "metodo": metodo, "clientes": clientes, "orden_de_visita": orden,
            "recorrido": paradas, "distancia_km": round(km, 1)}


def detalle_cliente(cliente):
    clientes = experto.BASE_CONOCIMIENTO["clientes"]
    if cliente not in clientes:
        return {"error": f"Cliente no encontrado. Opciones: {list(clientes)}"}
    d = difuso.evaluar_cliente(cliente)
    inf = d["inferencia"]
    sprint2 = experto.motor_inferencia(cliente, experto.BASE_CONOCIMIENTO, difuso.cargar_memoria_logistica())
    return {"cliente": cliente, "entradas": {k: round(v, 2) for k, v in d["entradas"].items()},
            "decision_difusa": d["decision"], "prioridad_0_100": _redondear(d["prioridad"]),
            "tanda": d["tanda"], "razones": d["razones"],
            "grados_entrada": None if inf is None else
            {v: {k: round(g, 2) for k, g in gs.items()} for v, gs in inf["grados_entrada"].items()},
            "sistema_experto_sprint2": sprint2}


def simular_prioridad(stock, rotacion, dias_desde_ultima_entrega, flete_pct):
    senal = {"Sí": 1.0, "No": 0.0, "No hubo visita": 0.5}[stock]
    inf = difuso.inferir({"senal_stock": senal, "rotacion": difuso.ROTACION_NUM[rotacion],
                          "dias_desde_ultima_entrega": dias_desde_ultima_entrega, "flete_pct": flete_pct})
    nota = "Ojo: con flete > 4 % la regla R4 veta el despacho antes de la lógica difusa." if flete_pct > 4 else None
    return {"prioridad_0_100": round(inf["prioridad"], 1), "etiqueta": inf["etiqueta"],
            "reglas_activas": [{"regla": a["regla"], "fuerza": round(a["fuerza"], 2), "salida": a["prioridad"]}
                               for a in inf["activaciones"] if a["fuerza"] > 0], "nota": nota}


def optimizar_portafolio(criterio, presupuesto=pf.PRESUPUESTO_TOTAL, espacio=pf.ESPACIO_BODEGA_TOTAL,
                         factor_erosion=1.0, k_ataques=1):
    p = pf.Problema(presupuesto=presupuesto, espacio=espacio, factor_erosion=factor_erosion, k_ataques=k_ataques)
    mejor, hist = pf.ag_portafolio(criterio, p)
    optimo, empates = pf.fuerza_bruta(criterio, p)
    valor_ag = pf.utilidad_total(mejor) if criterio == "esperada" else pf.utilidad_peor_caso(mejor, p)
    return {"criterio": criterio, "mejor_del_ag": pf.resumen_portafolio(mejor, p),
            "optimo_fuerza_bruta": optimo, "ag_llego_al_optimo": abs(valor_ag - optimo) < 1e-6,
            "portafolios_empatados": [pf.resumen_portafolio(c, p) for c in empates],
            "generaciones": len(hist) - 1}


def viabilidad_categorias():
    return {prod: {**experto.motor_inferencia_portafolio(h),
                   "nombres_incumplidos": [experto.CRITERIOS_NOMBRES[c] for c in
                                           experto.motor_inferencia_portafolio(h)["incumplidos"]]}
            for prod, h in experto.cargar_memoria_portafolio().items()}


FUNCIONES = {"despacho_semana": despacho_semana, "detalle_cliente": detalle_cliente,
             "simular_prioridad": simular_prioridad, "optimizar_portafolio": optimizar_portafolio,
             "viabilidad_categorias": viabilidad_categorias}


def ejecutar_herramienta(nombre, entrada):
    try:
        return json.dumps(FUNCIONES[nombre](**entrada), ensure_ascii=False, default=str), False
    except Exception as e:  # el error vuelve al modelo como tool_result con is_error
        return f"{type(e).__name__}: {e}", True


# =============================================================================
# Bucle del agente (manual, para mostrar en la app cada herramienta usada)
# =============================================================================
def responder(historial, cliente=None, max_vueltas=8):
    """historial: lista de mensajes {role, content} (se modifica en sitio).
    Devuelve (texto_final, trazas) donde trazas = [(herramienta, entrada, salida)]."""
    import anthropic

    cliente = cliente or anthropic.Anthropic()
    trazas = []
    for _ in range(max_vueltas):
        respuesta = cliente.beta.messages.create(
            model=MODELO,
            max_tokens=16000,
            system=SISTEMA,
            tools=HERRAMIENTAS,
            messages=historial,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if respuesta.stop_reason == "refusal":
            return "El modelo no pudo responder esta solicitud.", trazas

        historial.append({"role": "assistant", "content": respuesta.content})
        if respuesta.stop_reason != "tool_use":
            texto = "\n".join(b.text for b in respuesta.content if b.type == "text")
            return texto, trazas

        resultados = []
        for bloque in respuesta.content:
            if bloque.type == "tool_use":
                salida, es_error = ejecutar_herramienta(bloque.name, bloque.input)
                trazas.append((bloque.name, bloque.input, salida))
                resultados.append({"type": "tool_result", "tool_use_id": bloque.id,
                                   "content": salida, "is_error": es_error})
        historial.append({"role": "user", "content": resultados})
    return "Se alcanzó el máximo de pasos sin una respuesta final.", trazas
