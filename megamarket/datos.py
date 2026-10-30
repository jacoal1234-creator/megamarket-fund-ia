"""Lectura de la memoria de trabajo y los datos operativos (todo vive en data/*.csv)."""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def leer_csv(nombre, data_dir=None):
    """Lee un CSV de data/. sep=None detecta si viene con "," o ";" (Excel en
    español guarda con ";") y utf-8-sig quita el BOM que agrega Excel."""
    ruta = Path(data_dir or DATA_DIR) / nombre
    return pd.read_csv(ruta, sep=None, engine="python", encoding="utf-8-sig")


def a_booleano(valor):
    """Convierte 'Sí' / 'No' del CSV a True / False."""
    return str(valor).strip().lower() in ("sí", "si")


def interpretar_stock_reportado(valor):
    """Tres estados: 'Sí' (stock bajo), 'No' (stock bien) o 'No hubo visita' (None)."""
    valor = str(valor).strip().lower()
    if valor in ("sí", "si"):
        return True
    if valor == "no":
        return False
    return None


def cargar_memoria_logistica(df=None):
    """Memoria de trabajo de esta semana como {cliente: {hechos}}.
    Se puede pasar un DataFrame ya editado (por ejemplo desde la app)."""
    df = leer_csv("memoria_trabajo_logistica.csv") if df is None else df
    memoria = {}
    for _, fila in df.iterrows():
        memoria[fila["cliente"]] = {
            "visita_mercaderista_disponible": a_booleano(fila["visita_mercaderista_disponible"]),
            "mercaderista_reporta_stock_bajo": interpretar_stock_reportado(fila["mercaderista_reporta_stock_bajo"]),
            "dias_desde_ultima_entrega": int(fila["dias_desde_ultima_entrega"]),
            "queja_urgente": a_booleano(fila["queja_urgente"]),
            "precio_actualizado_en_punto_de_venta": a_booleano(fila["precio_actualizado_en_punto_de_venta"]),
            "valor_factura_pedido": int(fila["valor_factura_pedido"]),
            "costo_flete_estimado": int(fila["costo_flete_estimado"]),
        }
    return memoria


def cargar_clientes():
    """Hechos fijos de cada cliente: ruta y rotación del producto en ese punto."""
    df = leer_csv("clientes.csv")
    return {f["cliente"]: {"ruta": f["ruta"], "rotacion_producto": f["rotacion_producto"]}
            for _, f in df.iterrows()}


def cargar_candidatos():
    """Los 8 candidatos VIABLES del Sprint 3, con su erosión supuesta."""
    df = leer_csv("candidatos_portafolio.csv")
    return {f["producto"]: {"costo_lanzamiento": int(f["costo_lanzamiento"]),
                            "espacio_bodega": int(f["espacio_bodega"]),
                            "utilidad_esperada_anual": int(f["utilidad_esperada_anual"]),
                            "erosion": float(f["erosion"])}
            for _, f in df.iterrows()}
