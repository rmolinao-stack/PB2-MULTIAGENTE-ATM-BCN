# INFORME DE RESULTADOS

En este apartado se describen los 4 experimentos u observaciones solicitadas por la academia.

Modelos utilizados para generar el informe:
* EMBEDDING_MODEL = "gemini-embedding-2"
* GEMINI_MODEL ="gemini-3.1-flash-lite-preview"

## Chunking

| Configuración| Chunks Generados | Cohesión Semántica | Resultado o Problema Detectado | 
|-|-|-|-|
|Opción A: Size 500 / Overlap 50| 157 | Baja |Corta reglas de transbordo e incompatibilidades entre dos fragmentos distintos.|
|Opción B (Elegida): Size 1000 / Overlap 150| 91 |Óptima |Equilibrada. Mantiene las condiciones completas de títulos (ej. T-usual, T-casual) en un solo bloque.|
|Opción C: Size 2000 / Overlap 300| 62 | Excesiva | Sin mejora de precisión y duplicamos el número de información que le pasamos al modelo a riesgo de aumentar el coste.|

**Nota sobre datos estructurados**: Para el CSV de municipios se descartó la fragmentación por fila ya que generaba más de 300 chunks (micro-chunks) y se implementó una extracción determinista previa mediante Pandas, evitando la saturación del vector store.

### Evidencias

* CHUNK_SIZE = 500 
* CHUNK_OVERLAP = 50

```text
--- Resumen ingesta ---
  Documentos cargados:      65
  Tras limpieza:            58
  Chunks generados:         157
  Chunks por fuente:
    11_Intro_sistema_tarifario_integrado.pdf: 5
    12_sistema_tarifario_integrado.pdf: 23
    21_Tarifa_metropolitana.pdf: 5
    22_tarifas_transporte_abonos_normales.csv: 15
    23_Descripcion_tipos_billetes_ATM.pdf: 63
    25_Otros_titulos_integrados_y_sus_tarifas.pdf: 19
    31_Condiciones_de_uso_titulos_transporte.pdf: 27
```

* CHUNK_SIZE = 1000 
* CHUNK_OVERLAP = 150
```text
--- Resumen ingesta ---
  Documentos cargados:      65
  Tras limpieza:            58
  Chunks generados:         91
  Chunks por fuente:
    11_Intro_sistema_tarifario_integrado.pdf: 2
    12_sistema_tarifario_integrado.pdf: 13
    21_Tarifa_metropolitana.pdf: 3
    22_tarifas_transporte_abonos_normales.csv: 15
    23_Descripcion_tipos_billetes_ATM.pdf: 35
    25_Otros_titulos_integrados_y_sus_tarifas.pdf: 8
    31_Condiciones_de_uso_titulos_transporte.pdf: 15
```

* CHUNK_SIZE = 2000 
* CHUNK_OVERLAP = 300
```text
--- Resumen ingesta ---
  Documentos cargados:      65
  Tras limpieza:            58
  Chunks generados:         62
  Chunks por fuente:
    11_Intro_sistema_tarifario_integrado.pdf: 1
    12_sistema_tarifario_integrado.pdf: 8
    21_Tarifa_metropolitana.pdf: 1
    22_tarifas_transporte_abonos_normales.csv: 15
    23_Descripcion_tipos_billetes_ATM.pdf: 22
    25_Otros_titulos_integrados_y_sus_tarifas.pdf: 7
    31_Condiciones_de_uso_titulos_transporte.pdf: 8
```

## Retrieval

Se han lanzado el juego de pruebas [preguntas_eval.md](../queries/preguntas_eval.md) con top-k=1 y top-k=5.

Se puede observar que con top-k=1 hay preguntas que deberái responder sin problema, que al no tener contexto no las puede resolver.

[Resultadod top-k=1](../queries/preguntas_respuestas_topk1.md)

[Resultadod top-k=5](../queries/preguntas_respuestas_topk5.md)

## Generación

En el juego de pruebas [preguntas_eval.md](../queries/preguntas_eval.md) se pueden observar varias preguntas que debe abstenerse.

Si miramos el resultado con el top-k=5, que es el establecido, veremos que els sistema cumple con lo esperado: [Resultadod top-k=5](../queries/preguntas_respuestas_topk5.md)

## Fallos y mejoras

### Fallos detectados:

1.- Generación de fichero embeddings.json con baja utilidad. Tiene mas sentido separar ingesta de embedding y juntar embedding de indexación o directamente hacer un prepare con los tres puntos y evitar generar estos ficheros.

2.- Dilución semántica en nombres de ciudades: La búsqueda por embeddings puros en tablas densas confunde municipios de nombres parecidos o ignora entidades.

3.- Límites de cuotas en Free Tier (429 RESOURCE_EXHAUSTED): Bloqueos puntuales al procesar embeddings en lote durante la ingesta si no se implementa una espera activa.

4.- Ausencia de estado conversacional: Al responder cada consulta de forma aislada, el sistema no puede resolver repreguntas contextuales (ej. "¿Y cuánto cuesta ese billete?").

### Mejoras futuras:

1.- Unificación de embedding e indexación y separación de ingesta (esto ya está hecho)

2.- Uso de BBDDs para tablas con estructura de CSV y dejar de usarlos en la BBDD Vectorial y en el embedding y usar consultas SQL.

3.- Uso de Tier de pago en entorno de producción.

4.- Uso de sistema con memoria.