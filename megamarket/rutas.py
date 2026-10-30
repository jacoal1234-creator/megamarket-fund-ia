"""Sprint 1 — Ruta óptima con A* (misma lógica del notebook, datos desde CSV).

Notación de clase: g(n) costo real acumulado, h(n) heurística (haversine),
f(n) = g(n) + h(n) ordena la cola de prioridad.
"""
from heapq import heappush, heappop
from math import radians, sin, cos, asin, sqrt

from .datos import leer_csv

# =============================================================================
# 1. COORDENADAS (lat, lon) — estimadas por nomenclatura vial (±200–400 m)
# =============================================================================
_coord_df = leer_csv("coordenadas.csv")
COORDENADAS = {f["nodo"]: (float(f["lat"]), float(f["lon"])) for _, f in _coord_df.iterrows()}
TIPO_NODO = {f["nodo"]: f["tipo"] for _, f in _coord_df.iterrows()}

ORIGEN = "Bodega Olaya Herrera"
DESTINO_FINAL = "Plataforma Logística"
ACCESOS = {"Poblado": "Acceso Poblado (Aguacatala)", "Valle de Aburrá": "Acceso Sur (Itagüí Centro)"}
UMBRAL_CERCANIA_KM = 1.5


# =============================================================================
# 2. HEURÍSTICA h(n): distancia en línea recta (haversine)
# =============================================================================
def heuristica(nodo, destino):
    """Distancia en línea recta entre dos lugares, en km. Es admisible: nunca
    supera la distancia real por calles."""
    lat1, lon1 = COORDENADAS[nodo]
    lat2, lon2 = COORDENADAS[destino]
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    d_lat = lat2 - lat1
    d_lon = lon2 - lon1
    aux = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(aux))  # 6371 km = radio de la Tierra


# =============================================================================
# 3. GRAFOS DE CADA RUTA  {nodo: [(vecino, costo_km), ...]}
# =============================================================================
def conectar(red, a, b, costo):
    """Agrega una conexión en AMBOS sentidos."""
    red.setdefault(a, []).append((b, costo))
    red.setdefault(b, []).append((a, costo))


def conectar_clientes_cercanos(red, clientes, umbral=UMBRAL_CERCANIA_KM):
    """Clientes a menos de 'umbral' km en línea recta se conectan directo."""
    for i in range(len(clientes)):
        for j in range(i + 1, len(clientes)):
            a, b = clientes[i], clientes[j]
            distancia = heuristica(a, b)
            if distancia < umbral:
                conectar(red, a, b, round(distancia, 2))


def construir_red(nombre_ruta):
    """Arma el grafo de una ruta: aristas escritas a mano (aristas.csv), la
    Plataforma conectada al acceso vial y los clientes cercanos entre sí."""
    aristas = leer_csv("aristas.csv")
    red = {}
    for _, f in aristas[aristas["ruta"] == nombre_ruta].iterrows():
        conectar(red, f["origen"], f["destino"], float(f["costo_km"]))
    acceso = ACCESOS[nombre_ruta]
    conectar(red, acceso, DESTINO_FINAL, round(heuristica(acceso, DESTINO_FINAL), 1))
    conectar_clientes_cercanos(red, clientes_de_ruta(nombre_ruta))
    return red


def clientes_de_ruta(nombre_ruta):
    return [n for n, f in _coord_df.set_index("nodo").iterrows()
            if f["tipo"] == "cliente" and f["ruta"] == nombre_ruta]


RUTAS = list(ACCESOS)
REDES = {r: construir_red(r) for r in RUTAS}


# =============================================================================
# 4. A* (A-Star) — misma estructura vista en clase
# =============================================================================
def a_estrella(red, origen, destino):
    # Inicializamos la cola de prioridad con: (f(n), g(n), camino)
    cola = [(heuristica(origen, destino), 0, [origen])]
    visitados = set()

    while cola:
        # Extraemos el nodo con el menor f(n) (el más prometedor)
        f, g, camino = heappop(cola)
        nodo_actual = camino[-1]

        if nodo_actual == destino:
            return camino, g

        if nodo_actual not in visitados:
            visitados.add(nodo_actual)
            for vecino, costo in red[nodo_actual]:
                # g(n) es el costo acumulado real desde el origen
                nuevo_g = g + costo
                # f(n) = g acumulado + estimación h del vecino
                nuevo_f = nuevo_g + heuristica(vecino, destino)
                heappush(cola, (nuevo_f, nuevo_g, camino + [vecino]))

    return None, None


# =============================================================================
# 5. RECORRIDO COMPLETO (Sprint 1 + tandas de prioridad del Sprint 2)
# =============================================================================
def recorrido_completo(red, origen, clientes, destino_final=None, prioridad=None):
    """Sale de 'origen', visita cada cliente (vecino más cercano con A* en cada
    paso) y termina en 'destino_final'. 'prioridad' es opcional
    {cliente: "ALTA"/"MEDIA"/"BAJA"}: se agota toda la tanda de mayor
    prioridad antes de pasar a la siguiente. Sin prioridad, es el Sprint 1."""
    if destino_final is None:
        destino_final = origen
    if prioridad is None:
        prioridad = {c: "NORMAL" for c in clientes}
    orden_tandas = ["ALTA", "MEDIA", "BAJA", "NORMAL"]
    tandas = {nivel: [c for c in clientes if prioridad.get(c, "NORMAL") == nivel] for nivel in orden_tandas}

    paradas = [origen]
    orden_clientes = []
    posicion_actual = origen
    distancia_total = 0

    for nivel in orden_tandas:
        pendientes = tandas[nivel]
        while pendientes:
            mejor_cliente, mejor_camino, mejor_costo = None, None, float("inf")
            for cliente in pendientes:
                camino, costo = a_estrella(red, posicion_actual, cliente)
                if costo < mejor_costo:
                    mejor_cliente, mejor_camino, mejor_costo = cliente, camino, costo
            paradas.extend(mejor_camino[1:])
            orden_clientes.append(mejor_cliente)
            distancia_total += mejor_costo
            posicion_actual = mejor_cliente
            pendientes.remove(mejor_cliente)

    camino_final, costo_final = a_estrella(red, posicion_actual, destino_final)
    paradas.extend(camino_final[1:])
    distancia_total += costo_final
    return paradas, distancia_total, orden_clientes


def ruta_de_la_semana(nombre_ruta, clientes, prioridad=None):
    """Atajo: bodega -> clientes -> Plataforma Logística en la ruta indicada."""
    if not clientes:
        return [ORIGEN, DESTINO_FINAL], 0.0, []
    return recorrido_completo(REDES[nombre_ruta], ORIGEN, list(clientes), DESTINO_FINAL, prioridad)
