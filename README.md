# ATeMto

**ATeMto** es el nombre comercial de **PB2-MULTIAGENTE-ATM-BCN**

**ATeMto** es un empleado sintetico capaz de calcular el trayecto entre dos estaciones de la red ATM de Barcelona (sistema integrado que permite utilizar diferentes medios de transporte como metro, autobuses, Ferrocarrils, TRAMvia y Rodalies), calcular los abonos necesario a adquirir, así como dar información sobre sus tarifas y condiciones de uso, además de ser capaz de calcular el tiempo que tardará llegar el siguiente metro (TMB) dada una estación concreta (no se incluye el calculo del tiempo de llegada de convoys a las estaciones de FGC, Rodalíes, TRAMvia y autobuses ya que está fuera del scope del proyecto).

**ATeMto** es una ampliación de **PB-RAG-ASISTENTE-TARIFAS-ATM-BCN** que es un asistente de tarifas y abonos para la red ATM de Barcelona - sistema tarifario integrado que permite utilizar diferentes medios de transporte (metro, autobuses, Ferrocarrils, TRAMvia y Rodalies). No es asistente de rutas, solo tarifas y abonos. Solo asiste tarifas de a ATM, no asiste tarifas de medio de transporte individual.

**ATeMto** utiliza el RAG construido en **PB-RAG-ASISTENTE-TARIFAS-ATM-BCN**.

## Estructura del proyecto

```text
PB2-MULTIAGENTE-ATM-BCN/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── main.py                     # CLI: prepare / index / query / ask.
├── app_rag.py                  # Asistente de tarifas - RAG en Streamlit.
├── app_agent.py                # Multiagente en Streamlit.
├── .streamlit/                 # Configuración streamlit    
├── assets/                     
│   ├── estacions.csv           # Lista de estaciones para extraer el ID necesaria para la API de TMB.
│   └── plano_ATM.jpg           # Plano para la el especialista de recorridos.
├── common/                     # Carpeta donde guardamos ficheros comunes como comfig o utils.
│   ├── config.py               # Se definen parametros generales del sistema.
│   ├── carga_api_key.py        # Carga de API key de gemini.
│   └── utils.py                # Funciones genéricas auxiliares y reutilizables.
├── data/                       # Corpus del RAG
├── entregables/                # informe final.
│   ├── informe_agent.md        # informe final de la parte de multiagente.
│   └── informe_rag.md          # informe final de la parte de rag.
├── img/                        # Imagenes varias de apoyo.
├── multiagent/                 # Carpeta donde guardamos los ficheros de la capa de negocio del multiagente.
│   ├── __init__.py
│   ├── agent.py                # procesar_turno, aprobar_plan, run_demo
│   ├── graph.py                # StateGraph multiagente + MemorySaver + HITL
│   ├── llm.py                  # ChatGoogleGenerativeAI
│   ├── state.py                # estado de producto (UI / resumen)
│   └── tools/
│       ├── __init__.py         # allowlist (@tool) + ejecutar_tool
│       ├── api_tiempos_tmb.py  # Tool, para más detalle ver memoría.
│       ├── info_estacion.py    # Tool, para más detalle ver memoría.
│       ├── rag_tarifas.py      # Tool, para más detalle ver memoría.
│       ├── ruta_plano.py       # Tool, para más detalle ver memoría.
│       └── zonas.py            # Tool, para más detalle ver memoría.
├── output/                     # Ficheros generados entre ellos el indice de chromaDB
├── queries/                    # preguntas de evaluación para el RAG
├── rag/                        # Carpeta donde guardamos los ficheros de la capa de negocio del RAG.
│   ├── pipeline.py             # Orquestador de la ingesta y otras llamadas.
│   ├── load.py                 # Revisa los ficheros del corpues y lo carga con metadatos.
│   ├── chunk.py                # Construye los chunks
│   ├── embed.py                # Genera el embedding
│   ├── index.py                # Genera el indice de ChromaDB
│   ├── retrieve.py             # Embedding de la consulta
│   ├── clean.py                # Limpieza de documentos. Podría estar en utils.py
│   ├── context.py              # Formatea contexto. Podría estar en utils.py
│   ├── eval_retrieval.py       # Para la opción --eval
│   ├── prompts.py              # Construye el prompt 
│   └── generate.py             # Llama al modelo para el RAG.
└── services/                   # Carpeta donde se encuentras los servicios que llamara Streamlit u otros.
    ├── multiagent_service.py   # Servicios que ejecutar el multiagente. 
    └── rag_service.py          # Servicios relacionados con RAG. 


```

## Instalación del entorno de desarrollo y APIs

Obtención del código fuente via git:

```text
git clone https://github.com/rmolinao-stack/PB2-MULTIAGENTE-TARIFAS-ATM-BCN
```

Se recomienda la instalación de un entorno virtual como Conda o Env. Ejemplo:

```text
python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate
```

Se deben instalar los paquetes requeridos:

```text
pip install -r requirements.txt
```

Se deben crear las API KEY en .env usando el ejemplo:

```text
cp .env.example .env
```

### API Keys necesarias:

* **GEMINI_API_KEY**: Api key del LLM de Gemini. Necesario tanto para el embedding del RAG, como para la ejecución del asistente de tarifas, como del multiagente.
* **TMB_API_ID**: Identificador de la aplicación dada de alta en developer.tmb.cat. Para más información ver apartado especial de esta API en la memoria y visitar: https://developer.tmb.cat/docs/getting-started
* **TMB_API_KEY**: Api Key para conectar al servicio de iMetro para conocer en tiempo real cuando llega el siguiente tren a una estación. Para más información ver apartado especial de esta API en la memoria y visitar: https://developer.tmb.cat/docs/getting-started

## Modos de Ejecución 

### Construcción de RAG y ejecución aislada

Hay dos modos de ejecución:

* Modo 1: Por línea de comandos usando python main.py y su correspondiente parámetro. Se usa principalmente para la ingesta, el embedding, la indexación y la realización de juego de pruebas del RAG.

```text
  python main.py --prepare                 #"Ingesta + embeddings (tiempo estimado de ejecución ~ 10 min)"
  python main.py --solo-ingesta            #"Solo realizar la ingesta sin ejecutar embeddings"
  python main.py --index                   #"Indexar en ChromaDB"
  python main.py --recreate-index          #"Borra la colección de ChromaDB antes de indexar"
  python main.py --query                   #"Pregunta de prueba que solo ataca al retrieval (recuperación de contexto)"
  python main.py --ask                     #"Pregunta con respusta generada por el modelo (RAG completo)"
  python main.py --eval                    #"Evaluación con preguntas preestablecidas"
  python main.py --top-k                   #"Sobreescribe TOP-K"
  ```

  * Modo 2: Desde línea de comandos usar *streamlit run app_rag.py*. Ejecuta el servidor de streamlit y abre un chat para interactuar con el asistente.

```text
streamlit run app_rag.py
```

### Para ejecutar el multiagente:

Hay dos modos de ejecución:

* Modo 1: Por línea de comandos usando python main.py y su correspondiente parámetro. Se usa principalmente para ejecutar una demo completa del multiagnete y para hacer una verificación interactiva del mismo solo por línea de comandos..

```text
  python main.py --agente-interactivo           # Ejecuta el workflow del multiagente por CLI en modo interactivo
  python main.py --agente-demo                  # Ejecuta una demo del workflow del multiagente por CLI. Por defecto autoaprueba las acciones.
  python main.py --agente-max-turns 4           # Limita el número máximo de turnos del workflow del multiagente
  python main.py --agente-max-steps 4           # Limita el número máximo de pasos del workflow del multiagente
  python main.py --agente-sin-auto-aprobar      # Solo para --agente-demo. Desactiva la autoaprobación de acciones.
```

  * Modo 2: Desde línea de comandos usar *streamlit run app_agent.py*. Ejecuta el servidor de streamlit y abre un chat para interactuar con el asistente.

```text
streamlit run app_agent.py
```

### Testeo de tools:

```text
  python main.py --test-tool-rag-tarifas      # Ejecuta un test de pruebas para la tool rag-tarifas.
  python main.py --test-tool-plano            # Ejecuta un juego de pruebas para la tool calcular_ruta_plano.
  python main.py --test-tool-zonas            # Ejecuta un test de pruebas para la tool de obtención de la zona de varias poblaciones.
  python main.py --test-tool-id-estacion      # Ejecuta un test de pruebas para la tool de obtención del ID_ESTACION a partir del nombre de la estación.
  python main.py --test-tool-llegada-tren     # Ejecuta un test de pruebas para la tool de obtención de los tiempos de llegada de trenes en TMB.
```

## Orden de ejecución estandar

* Paso 1: Cargar corpus, embedding y recrear index:

```text
python main.py --prepare --index --recreate-index
```

* Paso 2: Ejecutar servidor streamlit e interactuar el multiagente:

```text
streamlit run app_agent.py
```
## Memoría del proyecto

**Memoria de la construcción del multiagente**: [Pulsa aquí](./entregables/memoria_agent.md)
* En este memoría podrás encontrar los detalles de arquitectura del multiagente, tales como el workflow de LangGraph que se ha implementado, la descripción de los especialistas, las tools incluidas en el proyecto y detalles sobre la API de iMetro utilizada entre otros detalles.

**Memoria de la construcción del RAG**: [Pulsa aquí](./entregables/memoria_rag.md)
* En esta memoría podrás encontrar los detalles de arquitectura específicos del RAG que se utliza en la tool rag_tarifas y que viee hererada del proyecto PB-RAG-ASISTENTE-TARIFAS-ATM-BCN

#  **A PARTIR DE AQUI MEMORIA - PENDIENTE**





