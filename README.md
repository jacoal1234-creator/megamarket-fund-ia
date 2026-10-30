# MegaMarket · Centro de decisiones

Proyecto acumulativo de **Fundamentos de Analítica (Fund IA)**, Universidad EIA (Medellín).
Caso **MegaMarket SAS**, distribuidora de alimentos del Valle de Aburrá con marca propia **Riovalle**.

> **Código generado con Claude.** Los montos del portafolio y la erosión del competidor son supuestos ilustrativos.
> Las coordenadas están estimadas por nomenclatura vial (±200–400 m).

Equipo: Jacobo Argote, Andrés Cardona, Miguel Valencia y Juan José Gil.

## Qué hay aquí

| Sprint | Pregunta | Técnica | Resultado |
|---|---|---|---|
| 1 | ¿Por dónde va el camión? | A* con h(n) = haversine + vecino más cercano | Poblado 16,8 km · Sur 18,0 km |
| 2 | ¿Quién entra a la ruta? ¿La categoría es viable? | Sistemas expertos (R1–R6, C1–C7) | Aseo y Alquería no viables, Bebidas viable |
| 3 | ¿Qué productos lanzar con 70 M y 25 posiciones? | Algoritmo genético (mochila) + Minimax | $122 M (esperada) · $95 M peor caso con Minimax |
| **4** | **¿Qué tan urgente es despachar a cada cliente?** | **Lógica difusa (Mamdani) + agente de IA** | **Prioridad 0–100 por cliente** |

### Sprint 4: lógica difusa

1. Los vetos del Sprint 2 se mantienen duros: R4 (flete > 4 % de la factura) y R5 (precio desactualizado).
2. Queja urgente (R3): prioridad 100.
3. El resto pasa por el motor difuso:
   - **Entradas:** señal del mercaderista (Sí = 1, No hubo visita = 0,5, No = 0), rotación en el punto (1–5), días desde la última entrega (0–30) y flete como % de la factura (0–4).
   - **Reglas:** 11 reglas D1–D11. AND = mínimo, agregación = máximo.
   - **Salida:** desfuzzificación por centroide.
4. La etiqueta de salida decide: **Alta** y **Media** entran en esa tanda; **Baja** no entra esta semana. El recorrido sale de A* (Sprint 1).

Con la memoria de trabajo actual entran los mismos clientes que en el Sprint 2, pero cada uno con un puntaje. Five Sisters pasa a la tanda MEDIA (38,7), y la ruta Poblado baja de 9,9 a 9,4 km.

### Agente de IA

Un agente con Claude (tool use) que responde preguntas en español. Usa como herramientas las funciones del proyecto: `despacho_semana`, `detalle_cliente`, `simular_prioridad`, `optimizar_portafolio` y `viabilidad_categorias`. Cada número que da sale de una herramienta.

## Estructura

```
├── app/streamlit_app.py      App funcional (5 pestañas)
├── megamarket/               Lógica de los sprints como paquete de Python
│   ├── rutas.py              Sprint 1 — A*
│   ├── experto.py            Sprint 2 — sistemas expertos
│   ├── portafolio.py         Sprint 3 — AG + Minimax
│   ├── difuso.py             Sprint 4 — inferencia difusa
│   └── agente.py             Sprint 4 — agente con Claude
├── data/                     Memoria de trabajo y datos operativos (CSV)
├── notebooks/                Notebooks de Colab de cada sprint
└── docs/                     Landing (GitHub Pages) y presentaciones HTML de los sprints
```

Todos los datos operativos están en `data/*.csv`: coordenadas, aristas, clientes, memoria de trabajo, candidatos, y conjuntos y reglas difusas. Ninguno está escrito dentro del código.

## Correr la app localmente

```bash
pip install -r requirements.txt
```

```bash
streamlit run app/streamlit_app.py
```

El agente necesita una API key de Anthropic. Ponla en `.streamlit/secrets.toml` (está en `.gitignore`) como `ANTHROPIC_API_KEY = "..."`, o escríbela en la pestaña del agente. Sin la key, el resto de la app funciona igual.

## Publicar

- **App:** en [share.streamlit.io](https://share.streamlit.io), conecta este repositorio y elige `app/streamlit_app.py` como archivo principal. Pon `ANTHROPIC_API_KEY` en *Secrets*.
- **Landing:** en *Settings → Pages*, publica desde la rama `main`, carpeta `/docs`. Después actualiza los enlaces `ENLACES` al final de `docs/index.html`.
- **Notebook del Sprint 4 en Colab:** cambia `REPO` en la primera celda por la URL de este repositorio.

## Limitaciones conocidas

- El orden de visita sale de vecino más cercano por tandas. No es el óptimo global (TSP); A* solo es óptimo en cada tramo.
- Los costos entre los accesos viales y los clientes están escritos a mano; no vienen de un ruteador vial (OSRM).
- Los conjuntos y las reglas difusas son juicio experto y se deben calibrar con el mercaderista.
- Five Sisters (38,7) queda cerca del cruce Baja/Media (≈ 36): es un caso frontera.
- El AG no garantiza el óptimo. Por eso la app lo compara siempre con la fuerza bruta (256 combinaciones).
