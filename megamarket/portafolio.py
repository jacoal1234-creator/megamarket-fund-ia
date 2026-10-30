"""Sprint 3 — Algoritmo genético de portafolio (mochila) y extensión Minimax.

Misma lógica de los notebooks del Sprint 3. Las restricciones y la erosión
viajan en un objeto `Problema` para poder hacer escenarios "qué pasa si"
desde la app y el agente sin tocar variables globales.
"""
import itertools
import random
from dataclasses import dataclass, field

import pandas as pd

from .datos import cargar_candidatos

CANDIDATOS = cargar_candidatos()
NOMBRES = list(CANDIDATOS.keys())          # el orden define la posición de cada gen
N_GENES = len(NOMBRES)

PRESUPUESTO_TOTAL = 70_000_000
ESPACIO_BODEGA_TOTAL = 25
SEMILLA = 42


@dataclass
class Problema:
    presupuesto: int = PRESUPUESTO_TOTAL
    espacio: int = ESPACIO_BODEGA_TOTAL
    k_ataques: int = 1                      # cuántos productos ataca el rival a la vez
    factor_erosion: float = 1.0             # 0.5 = rival débil, 1.5 = rival fuerte
    erosion: dict = field(default=None)

    def __post_init__(self):
        if self.erosion is None:
            self.erosion = {n: min(0.95, CANDIDATOS[n]["erosion"] * self.factor_erosion) for n in NOMBRES}


def corto(nombre):
    return nombre.replace(" Riovalle", "")


# =============================================================================
# 1. FUNCIONES SOBRE UN INDIVIDUO (portafolio candidato)
# =============================================================================
def costo_total(ind):
    return sum(CANDIDATOS[NOMBRES[i]]["costo_lanzamiento"] for i in range(N_GENES) if ind[i] == 1)


def espacio_total(ind):
    return sum(CANDIDATOS[NOMBRES[i]]["espacio_bodega"] for i in range(N_GENES) if ind[i] == 1)


def utilidad_total(ind):
    return sum(CANDIDATOS[NOMBRES[i]]["utilidad_esperada_anual"] for i in range(N_GENES) if ind[i] == 1)


def es_portafolio_valido(ind, p):
    """Válido = respeta presupuesto Y espacio a la vez."""
    return costo_total(ind) <= p.presupuesto and espacio_total(ind) <= p.espacio


def nombre_incluidos(ind):
    return [NOMBRES[i] for i in range(N_GENES) if ind[i] == 1]


# =============================================================================
# 2. MINIMAX — el rival (MIN) ataca el producto que más daño hace
# =============================================================================
def perdidas_por_ataque(ind, p):
    return {NOMBRES[i]: CANDIDATOS[NOMBRES[i]]["utilidad_esperada_anual"] * p.erosion[NOMBRES[i]]
            for i in range(N_GENES) if ind[i] == 1}


def utilidad_peor_caso(ind, p):
    """Valor Minimax: lo que queda cuando el rival hace el máximo daño."""
    perdidas = sorted(perdidas_por_ataque(ind, p).values(), reverse=True)
    return utilidad_total(ind) - sum(perdidas[:p.k_ataques])


# =============================================================================
# 3. ALGORITMO GENÉTICO — fitness configurable
#    criterio "esperada" = Sprint 3; "peor_caso" = Minimax
# =============================================================================
def fitness(ind, criterio, p):
    if criterio == "esperada":
        return utilidad_total(ind)
    return utilidad_peor_caso(ind, p) + 0.001 * utilidad_total(ind)   # desempate por utilidad esperada


def razon(i, criterio, p):
    """Eficiencia del producto (utilidad / costo), la que usa la reparación."""
    c = CANDIDATOS[NOMBRES[i]]
    u = c["utilidad_esperada_anual"] * (1 - p.erosion[NOMBRES[i]] if criterio == "peor_caso" else 1)
    return u / c["costo_lanzamiento"]


def reparar_portafolio(ind, criterio, p):
    """Retira, de a uno, el producto con peor utilidad/costo hasta que quepa."""
    ind = list(ind)
    while not es_portafolio_valido(ind, p):
        incluidos = [i for i in range(N_GENES) if ind[i] == 1]
        ind[min(incluidos, key=lambda i: razon(i, criterio, p))] = 0
    return tuple(ind)


def crear_poblacion(tamano, criterio, p):
    return [reparar_portafolio(tuple(random.choice([0, 1]) for _ in range(N_GENES)), criterio, p)
            for _ in range(tamano)]


def seleccionar_por_ruleta(poblacion, criterio, p):
    valores = [fitness(ind, criterio, p) for ind in poblacion]
    base = min(valores)
    pesos = [(v - base) / 1_000_000 + 1 for v in valores]            # fitness escalado
    return random.choices(poblacion, weights=pesos, k=1)[0]


def cruzar(p1, p2, criterio, p):
    corte = random.randint(1, N_GENES - 1)
    return reparar_portafolio(p1[:corte] + p2[corte:], criterio, p)


def mutar(ind, criterio, p, probabilidad=0.10):
    if random.random() >= probabilidad:
        return ind
    pos = random.randrange(N_GENES)
    mutado = list(ind)
    mutado[pos] = 1 - mutado[pos]
    return reparar_portafolio(mutado, criterio, p)


def ag_portafolio(criterio="esperada", p=None, tamano_poblacion=30, generaciones=40,
                  probabilidad_mutacion=0.10, elitismo=1, semilla=SEMILLA):
    """Ejecuta el AG y devuelve (mejor portafolio, historial por generación)."""
    p = p or Problema()
    random.seed(semilla)
    poblacion = crear_poblacion(tamano_poblacion, criterio, p)
    historial = []
    for gen in range(generaciones + 1):
        poblacion.sort(key=lambda ind: fitness(ind, criterio, p), reverse=True)
        historial.append({"Generación": gen,
                          "Mejor utilidad esperada": utilidad_total(poblacion[0]),
                          "Mejor peor caso": utilidad_peor_caso(poblacion[0], p),
                          "Utilidad promedio": sum(utilidad_total(i) for i in poblacion) / tamano_poblacion,
                          "Diversidad": len(set(poblacion))})
        if gen == generaciones:
            break
        nueva = poblacion[:elitismo]
        while len(nueva) < tamano_poblacion:
            hijo = cruzar(seleccionar_por_ruleta(poblacion, criterio, p),
                          seleccionar_por_ruleta(poblacion, criterio, p), criterio, p)
            nueva.append(mutar(hijo, criterio, p, probabilidad_mutacion))
        poblacion = nueva
    return poblacion[0], pd.DataFrame(historial)


def fuerza_bruta(criterio="esperada", p=None):
    """Control fuera del AG: revisa las 2^8 combinaciones."""
    p = p or Problema()
    valor = utilidad_total if criterio == "esperada" else (lambda c: utilidad_peor_caso(c, p))
    validas = [c for c in itertools.product([0, 1], repeat=N_GENES) if es_portafolio_valido(c, p)]
    mejor = max(valor(c) for c in validas)
    return mejor, [c for c in validas if abs(valor(c) - mejor) < 1e-6]


def resumen_portafolio(ind, p=None):
    """Diccionario legible de un portafolio (lo usan la app y el agente)."""
    p = p or Problema()
    perdidas = perdidas_por_ataque(ind, p)
    ataque = max(perdidas, key=perdidas.get) if perdidas else None
    return {"productos": [corto(n) for n in nombre_incluidos(ind)],
            "costo": costo_total(ind), "espacio": espacio_total(ind),
            "utilidad_esperada": utilidad_total(ind),
            "utilidad_peor_caso": utilidad_peor_caso(ind, p),
            "producto_que_ataca_el_rival": corto(ataque) if ataque else None}
