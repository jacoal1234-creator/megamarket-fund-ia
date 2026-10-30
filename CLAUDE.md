# CLAUDE.md — Fund IA / MegaMarket SAS

Proyecto universitario acumulativo de **Fundamentos de Analítica (Fund IA)**, Universidad EIA (Medellín). Caso: **MegaMarket SAS**, distribuidora de alimentos del Valle de Aburrá (Colombia). Se trabaja por sprints. Los entregables son notebooks de **Google Colab** (compatibles con Colab, Python 3.10) y un HTML autocontenido para sustentar.

Equipo: Jacobo Argote, Andrés Cardona, Miguel Valencia, Juan José Gil. Comunicación con el usuario: **español informal**.

## Cómo quiero que trabajes
- Sé objetivo y pragmático. Nada de sycophancy: si algo está mal planteado o es débil, dilo.
- **Review-first:** antes de escribir código, explícame en lenguaje simple la lógica o las reglas que vas a implementar y espera mi validación.
- Prefiero entregables completos y cohesivos (un notebook, un HTML), no piezas sueltas.
- No inventes datos, coordenadas ni resultados. Si algo falla (por ejemplo geocodificación) o falta información, repórtalo y pregunta.
- Lógica con fundamento operativo real, no proxies convenientes.
- Los datos operativos van en **CSV externos**, no en diccionarios hardcodeados en el código.
- Los datos ausentes se representan explícitamente (ej. "No hubo visita"), nunca como celda vacía.
- Los notebooks replican la estructura y la notación de los cuadernos del profesor. Se declara "CÓDIGO GENERADO CON CLAUDE" en el encabezado.
- Estilo de notebooks: celdas markdown que explican el porqué en lenguaje de clase, bloques de código con secciones numeradas, semilla fija para reproducibilidad, y celdas de apoyo visual con `# @title` (ocultas).
- Si algo contradice este archivo, avísame en vez de asumir.

## Estructura del repo
- `megamarket/` — paquete con la lógica de cada sprint: `rutas.py` (S1), `experto.py` (S2), `portafolio.py` (S3 + Minimax), `difuso.py` y `agente.py` (S4). Es la fuente de verdad que usan la app y el notebook del S4.
- `data/` — todos los CSV: `coordenadas`, `aristas`, `clientes` (ruta y rotación), `memoria_trabajo_logistica`, `memoria_trabajo_portafolio`, `candidatos_portafolio` (con erosión), `difuso_conjuntos`, `difuso_reglas`.
- `app/streamlit_app.py` — app funcional (Inicio, Despacho semanal, Lógica difusa, Portafolio, Agente IA).
- `notebooks/` — notebooks originales de los Sprints 1–3 y `Sprint4_LogicaDifusa_Despacho.ipynb`.
- `docs/` — landing estilo PUY (`index.html`, para GitHub Pages) y las presentaciones HTML de los Sprints 1–3 en `docs/sprints/`.

## Sprint 1 — Ruta óptima con A*
**Problema:** despachar Uva Pasa (Riovalle) desde la Bodega Olaya Herrera (Medellín) a dos rutas de clientes. Cada ruta es un solo viaje abierto: bodega → todos los clientes → **Plataforma Logística** (parqueadero en Guayabal, Cra. 51C #12B Sur-76), sin volver a la bodega.
- **Ruta Poblado (8):** Fruver del Río, Fruver Visitación, Five Sisters, Supermercado Merka 10, Hotel Four Points, Mercados Verona, EAFIT La Bodeguita, Redetrans. Acceso vial: Aguacatala.
- **Ruta Valle de Aburrá Sur (4 CEDIs):** Vaquita Itagüí, Euro La Estrella, Merkepaisa, Supermú. Acceso vial: Itagüí Centro.

**Implementación:**
- Notación de clase: g(n) costo real acumulado, h(n) heurística, f = g + h. Cola de prioridad con `heapq`, tuplas `(f, g, camino)`, conjunto de visitados.
- h(n) = distancia haversine (radio 6371 km) entre coordenadas. Es admisible.
- Grafos como `{nodo: [(vecino, costo_km)]}`. `conectar()` agrega aristas en ambos sentidos.
- Clientes a menos de `UMBRAL_CERCANIA_KM = 1.5` km en línea recta se conectan directo entre sí.
- La Plataforma Logística se conecta al acceso vial de cada ruta, con costo = haversine redondeado a 1 decimal.
- `a_estrella(red, origen, destino)` mantiene la estructura de la función del profesor. **No cambiar su lógica.**
- `recorrido_completo()`: vecino más cercano (A* hacia el cliente pendiente más próximo en cada paso) y tramo final A* a la Plataforma.
- Resultados: Poblado 16,8 km; Sur 18,0 km.

**Limitaciones conocidas:**
- Vecino más cercano no es óptimo global (habría que probar permutaciones / TSP). A* solo es óptimo por tramo.
- Coordenadas estimadas a partir de nomenclatura vial (±200–400 m). Las de la Plataforma son aproximadas.
- Costos de aristas con los accesos viales escritos a mano, no vienen de OSRM.
- El sandbox de ejecución tiene red restringida: Nominatim y OSRM devuelven HTTP 403. Por eso las coordenadas están fijas.
- Historia del alcance: antes se trabajó con 10 sedes reales (5 Supermú y 5 Euro, excluyendo Rionegro y Llanogrande) y ciclo cerrado. Luego se corrigió a un solo recorrido y después a ruta abierta. La versión vigente es la de dos rutas de arriba.

## Sprint 2 — Sistemas expertos (sin metaheurísticas)
Dos sistemas basados en reglas, independientes, con memoria de trabajo en CSV.

**Logística:** decide qué clientes entran a la ruta semanal. Reglas basadas en la observación del mercaderista sobre rotación por punto de venta, no en porcentajes genéricos de stock. Políticas:
- No despachar si el flete supera el 4% de la factura.
- No despachar si el precio en el punto de venta no está actualizado.
- Queja urgente genera visita prioritaria.
- Entrega en ventana de 48–72 h.

**Portafolio:** `motor_inferencia_portafolio` evalúa 7 criterios del gerente general (C1–C7), todos deben cumplirse para ser VIABLE: afinidad, cumplimiento legal, viabilidad operativa (riesgo de contaminación cruzada), calidad y presentación, venta cruzada, vida útil mínima de 6 meses, precio y rentabilidad. Resultados: aseo NO viable (afinidad y contaminación), lácteos Alquería NO viable (solo vida útil), bebidas VIABLES.

**HTML de sustentación:** pestañas por sistema, diagramas de arquitectura, manifiesto de reglas, tarjetas de caso expandibles, matriz comparativa. Autocontenido.

Límite: es binario, no compara candidatos ni dice cuántos se pueden lanzar a la vez. Eso motiva el Sprint 3.

## Sprint 3 — Algoritmo genético de portafolio (mochila)
**Problema:** 8 candidatos ya VIABLES (Sprint 2), pero el presupuesto y la bodega no alcanzan para todos. Elegir el subconjunto que maximice la utilidad. Montos ficticios.

**Restricciones:** `PRESUPUESTO_TOTAL = 70_000_000` COP, `ESPACIO_BODEGA_TOTAL = 25` posiciones. Lanzar los 8 costaría 152 M y ocuparía 49 posiciones.

| Producto | Costo | Espacio | Utilidad anual |
|---|---|---|---|
| Higo Deshidratado Riovalle | 18 M | 6 | 32 M |
| Mix de Frutos Secos Riovalle | 25 M | 8 | 48 M |
| Barra Energética Riovalle | 15 M | 4 | 22 M |
| Granola Riovalle | 20 M | 7 | 30 M |
| Jugo Natural Riovalle | 30 M | 10 | 52 M |
| Snack de Plátano Riovalle | 12 M | 5 | 17 M |
| Compota Riovalle | 10 M | 3 | 14 M |
| Café Molido Riovalle | 22 M | 6 | 38 M |

**Diseño:**
- Cromosoma binario de 8 genes, en el orden de `NOMBRES = list(CANDIDATOS.keys())`.
- Válido = respeta presupuesto Y espacio.
- **Reparación** (no penalización): se retira el producto incluido con peor utilidad/costo, de a uno, hasta que sea válido.
- Fitness = utilidad total + 1 (evita pesos cero en la ruleta).
- Selección por ruleta (`random.choices` con pesos = fitness). Cruce de un punto con corte en [1, 7] más reparación. Mutación: probabilidad 0,10, voltea un gen y repara.
- Parámetros: población 10, 15 generaciones, elitismo 1, `SEMILLA = 42`.
- Historial por generación en un DataFrame: mejor utilidad, utilidad promedio, diversidad.
- Fuerza bruta sobre las 256 combinaciones solo como control, fuera del AG.

**Resultados:**
- El AG llega a 122 M con Higo + Jugo Natural + Café Molido (costo 70 M, 22 de 25 posiciones).
- La fuerza bruta confirma 122 M como máximo, con otra combinación: Mix de Frutos Secos + Barra Energética + Jugo Natural (también 70 M y 22 posiciones). Hay más de un óptimo.
- La mejor utilidad llega a su máximo en la generación 1. La diversidad cae a 1 entre las generaciones 6 y 10 y luego sube por la mutación.

**Extensión Minimax (hecha):** erosión supuesta por producto (fracción de utilidad que se pierde si el rival entra), matriz 2×2 con Nash para el Jugo Natural, y AG con fitness = peor caso (el rival ataca el producto que más daño hace). Población 30, 40 generaciones. Minimax elige Higo + Mix + Barra + Snack: $119 M esperados, $95,0 M en el peor caso (contra $90,8 M del portafolio de $122 M). Con semilla 42, el AG Minimax no llega al óptimo de la fuerza bruta con erosión ×0,5 (106,4 vs 107,0) ni ×1,5 (83,0 vs 85,5). La app lo muestra.

## Sprint 4 — Lógica difusa + agente de IA
**Flujo por cliente:** vetos R4/R5 (duros) → queja urgente R3 (prioridad 100) → Mamdani.
- Entradas: `senal_stock` (Sí = 1, No hubo visita = 0,5, No = 0), `rotacion` (baja/media/alta = 1/3/5), `dias_desde_ultima_entrega` (0–30) y `flete_pct` (0–4).
- 11 reglas D1–D11. AND = mínimo, agregación = máximo, centroide sobre 0–100.
- La etiqueta con mayor pertenencia decide: Alta y Media entran en esa tanda; Baja no entra.
- Conjuntos y reglas están en CSV.

**Resultados:** entran los mismos clientes que en el Sprint 2. Five Sisters sube a MEDIA (38,7), un caso frontera porque el cruce Baja/Media está en ≈ 36. La ruta Poblado baja de 9,9 a 9,4 km; la Sur se queda en 14,9 km.

**Agente:** Claude (`claude-opus-5-5`, effort low, `fallbacks="default"`) con bucle manual de tool use y 5 herramientas que envuelven las funciones del paquete. El modelo se cambia con la variable `MEGAMARKET_MODELO`. La key va en los secrets de Streamlit.

## Pendientes y siguientes pasos
- Publicar en GitHub, desplegar en Streamlit Cloud, activar GitHub Pages y actualizar `REPO` en el notebook del S4 y `ENLACES` en `docs/index.html`.
- Inconsistencia de los datos originales del S2: el CSV de portafolio de la carpeta "CON LOS CAMBIOS" tenía invertidos C6 de Alquería y Bebidas. El repo usa la versión correcta (carpeta "IA").
- **Opción 1 (sprint futuro):** AG de permutación para el orden de visita de clientes, con cruce de orden (OX), reemplazando el vecino más cercano de `recorrido_completo`. Partiría de los clientes que filtra el sistema experto de logística.
- **Sustentación del Sprint 3:** Jacobo explica el AG inicial (fitness = utilidad anual). Las demás partes se reparten entre los cuatro.

## Proyecto relacionado (aparte)
Pronóstico de ventas de Riovalle con el stack Nixtla (StatsForecast, MLForecast): AutoARIMA, AutoETS, AutoCES, LightGBM y otros, 8 modelos sobre 10 SKUs (Ciruela Pasa, Uva Pasa, Pistacho...), horizonte de 6 meses, validación cruzada de 3 ventanas. Sirve para planear la compra de materia prima.

## Comandos útiles
- Ejecutar un notebook localmente: `jupyter nbconvert --to notebook --execute <archivo>.ipynb --output <salida>.ipynb`
- Dependencias de los notebooks: `pandas`, `matplotlib` (el resto es biblioteca estándar: `heapq`, `math`, `random`, `itertools`).
- Antes de entregar, verifica que el notebook corre de arriba abajo en un kernel limpio, sin depender de archivos locales que Colab no tenga.
