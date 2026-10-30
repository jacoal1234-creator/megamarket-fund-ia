"""Sprint 4 — Sistema de inferencia difusa (Mamdani) para la prioridad de despacho.

Flujo por cliente:
  1. Restricciones duras del Sprint 2 (R4 flete > 4 %, R5 PVP desactualizado): veto.
  2. Queja urgente (R3): prioridad 100, tanda ALTA. Es política, no grado.
  3. Si no: fuzzificación -> reglas D1..D11 (AND = mínimo) -> agregación
     (máximo) -> desfuzzificación por centroide -> prioridad 0–100.
  4. La etiqueta de salida con mayor pertenencia decide: Alta / Media entran
     a la ruta en esa tanda; Baja no entra esta semana.

Conjuntos y reglas viven en data/difuso_conjuntos.csv y data/difuso_reglas.csv.
"""
import numpy as np

from .datos import leer_csv, cargar_memoria_logistica, cargar_clientes
from .experto import vetos

VARIABLES_ENTRADA = ["senal_stock", "rotacion", "dias_desde_ultima_entrega", "flete_pct"]
UNIVERSO = {
    "dias_desde_ultima_entrega": (0, 30),
    "flete_pct": (0, 4),
    "senal_stock": (0, 1),
    "rotacion": (1, 5),
    "prioridad": (0, 100),
}
# Codificación numérica de los datos cualitativos del CSV
SENAL_STOCK = {True: 1.0, None: 0.5, False: 0.0}      # Sí / No hubo visita / No
ROTACION_NUM = {"baja": 1.0, "media": 3.0, "alta": 5.0}
PRIORIDAD_QUEJA = 100.0
TANDA = {"Alta": "ALTA", "Media": "MEDIA"}


# =============================================================================
# 1. FUNCIONES DE PERTENENCIA (trapezoidal; la triangular es el caso b = c)
# =============================================================================
def trapecio(x, a, b, c, d):
    """Grado de pertenencia de x a un trapecio (a, b, c, d). Funciona con
    escalares y arreglos de numpy. Si a == b (o c == d) el lado es vertical:
    es un 'hombro' en el borde del universo."""
    x = np.asarray(x, dtype=float)
    subida = np.ones_like(x) if b == a else np.clip((x - a) / (b - a), 0, 1)
    bajada = np.ones_like(x) if d == c else np.clip((d - x) / (d - c), 0, 1)
    grado = np.minimum(subida, bajada)
    return np.where((x < a) | (x > d), 0.0, grado)


def cargar_conjuntos(df=None):
    df = leer_csv("difuso_conjuntos.csv") if df is None else df
    conjuntos = {}
    for _, f in df.iterrows():
        conjuntos.setdefault(f["variable"], {})[f["conjunto"]] = (
            float(f["a"]), float(f["b"]), float(f["c"]), float(f["d"]))
    return conjuntos


def cargar_reglas(df=None):
    df = leer_csv("difuso_reglas.csv") if df is None else df
    return [f.to_dict() for _, f in df.iterrows()]


CONJUNTOS = cargar_conjuntos()
REGLAS = cargar_reglas()


# =============================================================================
# 2. FUZZIFICACIÓN
# =============================================================================
def fuzzificar(entradas, conjuntos=None):
    """{variable: valor} -> {variable: {conjunto: grado}}."""
    conjuntos = conjuntos or CONJUNTOS
    grados = {}
    for var in VARIABLES_ENTRADA:
        lo, hi = UNIVERSO[var]
        x = min(max(entradas[var], lo), hi)          # se recorta al universo
        grados[var] = {nombre: float(trapecio(x, *params)) for nombre, params in conjuntos[var].items()}
    return grados


# =============================================================================
# 3. INFERENCIA MAMDANI + CENTROIDE
# =============================================================================
def inferir(entradas, conjuntos=None, reglas=None, resolucion=1001):
    """Devuelve la prioridad (0–100), la etiqueta ganadora y la traza de reglas."""
    conjuntos = conjuntos or CONJUNTOS
    reglas = reglas or REGLAS
    grados = fuzzificar(entradas, conjuntos)

    # Fuerza de disparo de cada regla: AND = mínimo; "*" = no importa
    activaciones = []
    for r in reglas:
        partes = [grados[var][r[var]] for var in VARIABLES_ENTRADA if r[var] != "*"]
        fuerza = min(partes) if partes else 0.0
        activaciones.append({"regla": r["regla"], "fuerza": fuerza, "prioridad": r["prioridad"],
                             "explicacion": r["explicacion"]})

    # Implicación (recorte por mínimo) y agregación (máximo) sobre el universo de salida
    y = np.linspace(*UNIVERSO["prioridad"], resolucion)
    agregado = np.zeros_like(y)
    for a in activaciones:
        if a["fuerza"] > 0:
            recorte = np.minimum(a["fuerza"], trapecio(y, *conjuntos["prioridad"][a["prioridad"]]))
            agregado = np.maximum(agregado, recorte)

    if agregado.sum() == 0:            # ninguna regla disparó
        prioridad = 0.0
    else:
        prioridad = float((y * agregado).sum() / agregado.sum())   # centroide

    grados_salida = {n: float(trapecio(prioridad, *p)) for n, p in conjuntos["prioridad"].items()}
    etiqueta = max(grados_salida, key=grados_salida.get)
    return {"prioridad": prioridad, "etiqueta": etiqueta, "grados_entrada": grados,
            "grados_salida": grados_salida, "activaciones": activaciones,
            "universo_salida": y, "agregado": agregado}


# =============================================================================
# 4. DE LA MEMORIA DE TRABAJO A LAS ENTRADAS DIFUSAS
# =============================================================================
def entradas_desde_hechos(hechos_semana, hechos_fijos):
    return {
        "senal_stock": SENAL_STOCK[hechos_semana["mercaderista_reporta_stock_bajo"]
                                   if hechos_semana["visita_mercaderista_disponible"] else None],
        "rotacion": ROTACION_NUM[hechos_fijos["rotacion_producto"]],
        "dias_desde_ultima_entrega": hechos_semana["dias_desde_ultima_entrega"],
        "flete_pct": 100 * hechos_semana["costo_flete_estimado"] / hechos_semana["valor_factura_pedido"],
    }


def evaluar_cliente(cliente, memoria=None, clientes=None):
    """Decisión completa para un cliente: veto, queja o inferencia difusa."""
    memoria = memoria or cargar_memoria_logistica()
    clientes = clientes or cargar_clientes()
    hechos_semana, hechos_fijos = memoria[cliente], clientes[cliente]
    entradas = entradas_desde_hechos(hechos_semana, hechos_fijos)
    base = {"cliente": cliente, "ruta": hechos_fijos["ruta"], "entradas": entradas}

    lista_vetos = vetos(hechos_semana)
    if lista_vetos:
        return {**base, "decision": "EXCLUIDO", "motivo": "veto", "prioridad": None,
                "tanda": None, "razones": lista_vetos, "inferencia": None}

    if hechos_semana["queja_urgente"]:
        return {**base, "decision": "INCLUIDO", "motivo": "queja urgente", "prioridad": PRIORIDAD_QUEJA,
                "tanda": "ALTA", "razones": ["R3 - Queja urgente: entra con prioridad máxima (política, no grado)"],
                "inferencia": inferir(entradas)}

    inf = inferir(entradas)
    activas = sorted([a for a in inf["activaciones"] if a["fuerza"] > 0], key=lambda a: -a["fuerza"])
    razones = [f"{a['regla']} ({a['fuerza']:.2f}) -> {a['prioridad']}: {a['explicacion']}" for a in activas]
    incluido = inf["etiqueta"] in TANDA
    return {**base, "decision": "INCLUIDO" if incluido else "NO ENTRA ESTA SEMANA",
            "motivo": "inferencia difusa", "prioridad": inf["prioridad"],
            "tanda": TANDA.get(inf["etiqueta"]), "razones": razones, "inferencia": inf}


def decidir_ruta_difusa(nombre_ruta, memoria=None):
    """Evalúa todos los clientes de la ruta. Devuelve (incluidos, prioridad, detalle)."""
    memoria = memoria or cargar_memoria_logistica()
    clientes = cargar_clientes()
    detalle = {c: evaluar_cliente(c, memoria, clientes) for c, d in clientes.items() if d["ruta"] == nombre_ruta}
    incluidos = [c for c, r in detalle.items() if r["decision"] == "INCLUIDO"]
    return incluidos, {c: detalle[c]["tanda"] for c in incluidos}, detalle
