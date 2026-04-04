# SCOUTER
## Propuesta de negocio
### AI closer operativo para investigar negocios, estimar oportunidad comercial, generar demos y preparar outreach con evidencia

Documento pensado para alinear visión entre socios, definir el diferencial real del producto y priorizar qué construir primero para convertir Scouter en una herramienta comercial confiable, escalable y realmente útil para generar clientes.

---

## 1. Resumen ejecutivo

La oportunidad no está en vender “scraping + drafts”, porque eso ya es relativamente replicable. La oportunidad está en construir un sistema que transforme datos dispersos de negocios en una acción comercial concreta: investigación, entendimiento del negocio, estimación comercial, demo específica y outreach listo para enviar.

La propuesta es reposicionar Scouter como un **AI closer operativo**. Un sistema donde **Hermes** actúa como cerebro de negocio, coordina investigación con Playwright, aprovecha la data obtenida por scraping y dispara, solo cuando corresponde, workflows más caros como review premium o generación de demo personalizada.

Scouter no debería quedarse en “encontrar negocios”. Debería avanzar hasta un punto mucho más útil: dejar cada lead importante convertido en un **paquete comercial accionable** con contexto, señales, recomendación de contacto, presupuesto estimado interno y una demo confiable cuando valga la pena.

---

## 2. Problema de mercado

Hoy muchas herramientas encuentran leads, exportan listas o generan textos automáticos. El problema es que casi ninguna entiende suficientemente bien al negocio antes de hablarle. Eso provoca outreach genérico, demos poco relevantes y mucho ruido comercial.

Los problemas concretos son:

- La data suele estar desordenada y sin estructura útil para agentes.
- No hay suficiente evidencia para saber si el negocio tiene web, WhatsApp o una presencia digital débil.
- Las demos se hacen tarde, a mano o sin suficiente contexto del negocio.
- El usuario termina operando herramientas separadas en lugar de tener un cerebro que coordine todo.
- No existe una lectura comercial previa que ayude a decidir si conviene invertir tiempo humano, demo o llamada.

---

## 3. Propuesta de valor

Scouter se posiciona como una plataforma que convierte un lead en un **paquete comercial accionable**.

No solo descubre negocios: los investiga, arma un dossier, estima su potencial comercial, decide si vale la pena invertir en ellos, produce drafts mejores y puede escalar a una demo personalizada con una URL confiable.

### Nueva promesa de producto

**Scouter entiende negocios, verifica presencia digital, estima oportunidad comercial, genera demos y prepara outreach listo para cerrar.**

### Qué cambia con este posicionamiento

- Deja de ser un scraper con IA.
- Deja de ser un generador de mensajes.
- Pasa a ser un sistema operativo comercial con evidencia, criterio y capacidad de ejecución.

---

## 4. Cómo funcionaría el producto

El flujo ideal prioriza calidad sobre automatización ciega. Para leads de alta calidad, primero se investiga; después se escribe.

### Flujo general

1. Scraper incorpora leads.
2. Hermes normaliza, deduplica y puntúa calidad.
3. Si el lead es `HIGH`, se dispara un proceso de investigación.
4. Playwright recolecta evidencia y señales públicas del negocio.
5. Qwen 9B resume y estructura un dossier.
6. Reviewer 27B revisa el dossier y define la estrategia comercial.
7. Se generan drafts mejores y, si corresponde, una demo personalizada.
8. Hermes deja todo listo para decidir envío, llamada o seguimiento.

### Flujo especial para leads HIGH

Para leads `HIGH`, Scouter debería generar un bloque premium de análisis antes del contacto:

- investigación del negocio
- verificación de presencia digital
- dossier estructurado
- **High Lead Commercial Brief**
- draft de WhatsApp / email
- recomendación de contacto
- sugerencia de demo

---

## 5. High Lead Commercial Brief

Este bloque es una de las piezas más valiosas del producto. Su objetivo es que, antes de contactar a un lead importante, el equipo ya tenga una lectura comercial interna para decidir mejor.

No se trata solo de “qué decirle” al lead. Se trata de saber:

- cuánto podría valer
- qué tipo de proyecto parece necesitar
- si conviene mover tiempo humano
- si conviene llamada o no
- si tiene sentido preparar demo
- cuál sería el mejor canal de entrada

### Contenido del High Lead Commercial Brief

#### 5.1 Presupuesto estimado interno

Scouter debería generar un **presupuesto aproximado interno**, no como cifra exacta sino como rango y tier.

Campos sugeridos:

- `budget_tier`
  - bajo
  - medio
  - alto
  - premium

- `estimated_budget_min`
- `estimated_budget_max`

Ejemplo:

- Budget Tier: Alto
- Estimated Budget Range: USD 800–1500

Este dato es **interno**. No debería mostrarse automáticamente al lead. Sirve para priorización, estrategia de contacto y decisión de esfuerzo.

#### 5.2 Tipo de proyecto probable

Scouter debería estimar qué tipo de necesidad parece tener el negocio.

Campos sugeridos:

- `estimated_scope`
  - landing simple
  - web institucional
  - catálogo
  - ecommerce
  - rediseño
  - automatización / IA
  - branding + web
  - demo primero, venta después

Esto evita que la IA “invente precios” sin contexto. Primero identifica el tipo de problema; después cae en una banda de presupuesto.

#### 5.3 Opportunity Score

Además del quality score inicial, el sistema debería entregar una señal comercial más precisa.

Campo sugerido:

- `opportunity_score` de 0 a 100

Se construye con señales como:

- no tiene web
- tiene Instagram activo
- parece negocio real y vivo
- tiene branding usable
- vende servicios o productos claros
- hay oportunidad de mejora rápida y visible
- tiene múltiples puntos de contacto
- su presencia digital actual está floja

#### 5.4 Recomendación de contacto

Scouter no debería limitarse a redactar el mensaje. También debería indicar cómo conviene abrir la conversación.

Campos sugeridos:

- `recommended_contact_method`
  - whatsapp
  - email
  - call
  - demo_first
  - manual_review

- `should_call`
  - yes
  - no
  - maybe

- `call_reason`

Ejemplos de razones:

- El proyecto parece más fácil de cerrar explicándolo.
- El negocio parece serio y con ticket medio-alto.
- Conviene validar interés por WhatsApp antes de llamar.
- Faltan datos para una llamada útil.
- La complejidad del proyecto amerita discovery temprano.

#### 5.5 Data adicional para el equipo

Además del draft de WhatsApp o email, Scouter debería devolver un bloque de lectura interna para el equipo comercial.

Campos sugeridos:

- `why_this_lead_matters`
- `main_business_signals`
- `main_digital_gaps`
- `recommended_angle`
- `demo_recommended`
- `contact_priority`

De esta forma, el draft sale acompañado por criterio de negocio.

### Ejemplo de salida ideal

```md
## Commercial Brief

- Lead Quality: HIGH
- Business Type: Estética / belleza
- Digital Presence: Instagram activo, sin web detectada
- Opportunity Score: 84/100
- Estimated Scope: Landing + WhatsApp CTA + galería de servicios
- Budget Tier: Medium
- Estimated Budget Range: USD 600–1200
- Recommended Contact Method: WhatsApp
- Should Call: Maybe
- Call Reason: Conviene si responde con interés; el negocio parece activo y visualmente vende bien
- Demo Recommended: Yes
- Why It Matters:
  - No tiene web
  - Tiene marca visual usable
  - Vende por Instagram
  - Hay mejora rápida y fácil de mostrar
```

### Principio clave

El presupuesto estimado no es una cotización final. Es una lectura interna para ayudar a decidir:

- si vale la pena invertir esfuerzo
- si conviene llamada
- si conviene demo
- si el lead merece seguimiento manual
- cómo ordenar prioridades comerciales

---

## 6. Capa de investigación con evidencia

Para los leads `HIGH`, Playwright agrega muchísimo valor porque permite investigar con pruebas reales y no solo con texto derivado.

### Qué debería investigar

- si el negocio tiene web o no
- si esa web es propia, útil y actual
- si tiene Instagram activo
- si hay links salientes en la bio o en la web
- si aparece señal clara de WhatsApp
- cómo se ve la marca
- qué vende
- qué CTA usa
- qué tan madura parece su presencia digital

### Output esperado de la investigación

- screenshots
- HTML snapshot o metadata útil
- señales detectadas
- URLs encontradas
- evidencia visual para review interno
- resumen estructurado para Hermes y Qwen

### Lógica de confianza

Scouter no debería hablar en absolutos cuando la fuente es parcial. En su lugar, debería manejar niveles de confianza.

Campos sugeridos:

- `website_confidence`
- `instagram_confidence`
- `whatsapp_confidence`

Ejemplo para WhatsApp:

- `confirmed`
- `probable`
- `unknown`
- `mismatch`

Eso vuelve al sistema mucho más serio y creíble.

---

## 7. Arquitectura de agentes propuesta

### Hermes 8B

Líder operativo. Lee memoria, decide siguiente acción, administra modos de trabajo y coordina el pipeline.

Responsabilidades:

- leer contexto del lead
- decidir si escalar a research, review o demo
- consolidar outputs
- generar el “next best action”
- actuar como interfaz principal del sistema

### Qwen 9B

Modelo de alto volumen para tareas baratas.

Responsabilidades:

- normalización de datos
- resúmenes
- drafts iniciales
- scoring preliminar
- estructuración del dossier

### Qwen 27B Reviewer

Revisión selectiva para leads `HIGH`.

Responsabilidades:

- revisar coherencia comercial
- mejorar tono
- detectar riesgos
- validar el dossier
- validar el Commercial Brief
- decidir si draft y estrategia están listos

### Claude Code

Worker premium para ejecución.

Responsabilidades:

- producir demos
- adaptar plantillas
- generar artifacts técnicos
- dejar URLs compartibles y prolijas

### Playwright

Capa de investigación y evidencia.

Responsabilidades:

- abrir web y perfiles
- sacar screenshots
- detectar señales visibles
- dejar material objetivo para review

---

## 8. Diferencial competitivo

El diferencial no debería apoyarse en una sola tecnología. Debería aparecer en la combinación de capacidades y en la experiencia operativa del producto.

### El diferencial real sería

- investigación previa al contacto
- criterio comercial antes del draft
- presupuesto estimado interno para leads HIGH
- recomendación de contacto y llamada
- demo personalizada solo cuando vale la pena
- artifacts confiables y trazables
- un cockpit central donde todo se entiende rápido

### En una frase

**Scouter no solo encuentra leads. Los convierte en oportunidades priorizadas, entendidas y accionables.**

---

## 9. Experiencia de producto

La interfaz ideal se comporta como un **AI operations cockpit** y no como un CRM tradicional. El usuario debería sentir que entra a un cerebro central capaz de mostrar estado, contexto y acción en un solo lugar.

### Layout sugerido

#### Navegación izquierda

- Inbox
- Leads
- Dossiers
- Commercial Briefs
- Demos
- Campaigns
- Artifacts
- Runtime
- Settings

#### Centro

Chat con Hermes para:

- pedir acciones
- filtrar leads
- explicar decisiones
- disparar jobs
- ver próximos pasos

#### Panel derecho

- estado del lead
- score
- señales verificadas
- budget tier
- presupuesto estimado
- draft actual
- recomendación de contacto
- recomendación de llamada
- demo URL
- screenshots
- jobs y logs resumidos

### Runtime simple

Modos operativos:

- `Safe`
- `Assisted`
- `Auto`

Toggles por módulos:

- scraper
- research
- review
- demo
- send

La operación tiene que ser simple de prender, pausar y apagar.

---

## 10. Demos y confianza de entrega

La demo tiene que sentirse seria y confiable, tanto para el equipo como para el lead.

### Reglas sugeridas

- usar una URL clara y prolija
- separar preview interna de share link pública
- guardar artifacts ligados al lead
- registrar versión de la demo
- mantener trazabilidad entre dossier, Commercial Brief, draft y demo

### Idea de dominio

- `demo.scouter.ai`
- `preview.scouter.ai`
- subdominio por lead o campaña

La demo no debería verse como algo improvisado. Tiene que sostener la confianza comercial del producto.

---

## 11. Export y estructura de datos

Exportar sigue siendo útil, pero no como feature principal sino como **asset operativo**.

### Qué debería exportarse

- CSV/XLSX para análisis y trabajo comercial
- JSON estructurado para agentes
- artifacts ZIP para leads HIGH

### Para leads HIGH

Cada paquete exportable podría incluir:

- lead base
- dossier
- Commercial Brief
- drafts
- screenshots
- URLs detectadas
- demo URL si existe

Eso permite que humanos y agentes trabajen sobre la misma base.

---

## 12. Modelo comercial posible

Scouter puede venderse como herramienta, como servicio asistido o como sistema híbrido.

### Enfoque inicial recomendado

Empezar como producto con fuerte componente de servicio:

- validación en un rubro concreto
- foco en leads HIGH
- dossier + Commercial Brief + draft + demo selectiva
- feedback directo del equipo

Después, productizar lo que demuestre más valor.

### Posibles formatos

- licencia mensual
- fee por uso premium en demos / research avanzado
- servicio asistido para cohortes de leads HIGH
- modalidad híbrida con setup + operación

---

## 13. Roadmap sugerido de 90 días

### Fase 1 — Dossier Engine

- modelo `lead_research_report`
- Playwright worker
- screenshots y evidencia
- heurísticas de señales y confianza

### Fase 2 — Commercial Brief

- modelo `commercial_brief`
- budget tier y presupuesto estimado
- recommended contact method
- should call / call reason
- output listo para panel derecho y export

### Fase 3 — Draft Intelligence

- drafts condicionados por dossier + brief
- review solo en `HIGH`
- razones comerciales visibles

### Fase 4 — Demo Factory

- plantilla base
- `demo_job`
- deploy estable
- artifact `demo_url`

### Fase 5 — Cockpit UI

- chat central con Hermes
- contexto vivo a la derecha
- runtime controlado
- artifacts y logs

---

## 14. Métricas que deberían importar

- leads `HIGH` investigados por semana
- tiempo promedio desde lead nuevo hasta dossier listo
- tiempo promedio desde dossier hasta Commercial Brief
- porcentaje de leads HIGH con budget tier útil
- porcentaje de drafts aprobados sin cambios mayores
- cantidad de demos generadas y compartidas
- tasa de respuesta por canal y por vertical
- tasa de reunión agendada y de cierre por cohortes

---

## 15. Riesgos y principios de diseño

- No sobreprometer verificaciones absolutas cuando las fuentes son parciales o públicas.
- No hacer depender el sistema de una sola UI o de hacks frágiles de automatización.
- Mantener los costos bajo control: review y demo solo donde el ticket potencial lo justifique.
- Privilegiar una arquitectura confiable, prendible y apagable, por encima de automatización ciega.
- Diseñar para evidencia y trazabilidad: cada decisión importante debería poder explicarse.
- No convertir el presupuesto estimado en cotización automática.

---

## 16. Decisión estratégica recomendada

La mejor apuesta es fortalecer el equipo actual de modelos y construir encima de él una capa de negocio, evidencia y operación.

Antes de pensar en un líder más grande, conviene ganar en:

- dossier
- Commercial Brief
- review selectivo
- demo pipeline
- confiabilidad de producto

### Cierre de la idea

Scouter debería convertirse en un sistema capaz de pasar de lead frío a **dossier, Commercial Brief, demo y outreach listo para cerrar**, con un líder visible, una operación clara y artifacts confiables.

La propuesta no compite por “tener IA”. Compite por **entender mejor al negocio, priorizar mejor, vender mejor y ejecutar mejor**.

Ese es el diferencial que vale la pena construir.

---

## 17. Próximo paso sugerido

Aprobar esta visión y bajar el producto a:

- entidades de base de datos
- jobs y colas
- endpoints
- layout exacto del cockpit
- reglas de scoring y budget estimation

### Tres decisiones inmediatas

#### 1. MVP de validación comercial

- procesar una cohorte chica de leads HIGH de un rubro concreto
- generar dossier, Commercial Brief, draft y demo solo para los casos con oportunidad clara
- medir respuesta, reuniones y feedback de los socios

#### 2. Tabla interna de pricing

Definir la matriz base que Scouter usará para inferir presupuesto estimado por tipo de proyecto y complejidad.

#### 3. Política de contacto

Definir reglas claras para:

- cuándo sugerir llamada
- cuándo sugerir WhatsApp
- cuándo sugerir demo
- cuándo dejar manual review

