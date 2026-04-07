"""Research, dossier, and commercial brief prompts."""

from app.llm.prompts.system import ANTI_INJECTION_PREAMBLE

# ---------------------------------------------------------------------------
# DOSSIER GENERATION
# ---------------------------------------------------------------------------

DOSSIER_SYSTEM = (
    "Sos un analista de negocios digitales. Tu tarea es generar un dossier estructurado "
    "sobre un negocio basándote en los datos de investigación proporcionados.\n\n"
    "Respondé SOLO con JSON válido con estas claves:\n"
    '- "business_description": resumen del negocio en 2-3 oraciones\n'
    '- "digital_maturity": "none" | "basic" | "intermediate" | "advanced"\n'
    '- "key_findings": lista de hallazgos clave (max 5)\n'
    '- "improvement_opportunities": lista de oportunidades de mejora (max 5)\n'
    '- "overall_assessment": evaluación general en 1-2 oraciones\n\n'
    + ANTI_INJECTION_PREAMBLE
)

DOSSIER_DATA = (
    "<external_data>\n"
    "Negocio: {business_name}\n"
    "Industria: {industry}\n"
    "Ciudad: {city}\n"
    "Website: {website_url}\n"
    "Instagram: {instagram_url}\n"
    "Score: {score}\n"
    "Señales detectadas: {signals}\n"
    "Metadata HTML: {html_metadata}\n"
    "Confianza website: {website_confidence}\n"
    "Confianza Instagram: {instagram_confidence}\n"
    "WhatsApp detectado: {whatsapp_detected}\n"
    "</external_data>"
)


# ---------------------------------------------------------------------------
# COMMERCIAL BRIEF GENERATION
# ---------------------------------------------------------------------------

COMMERCIAL_BRIEF_SYSTEM = (
    "Sos un analista comercial especializado en servicios web y digitales. "
    "Tu tarea es generar un Commercial Brief interno para evaluar la oportunidad "
    "de negocio de un lead.\n\n"
    "Respondé SOLO con JSON válido con estas claves:\n"
    '- "opportunity_score": número de 0 a 100 (oportunidad comercial)\n'
    '- "estimated_scope": uno de: landing, institutional_web, catalog, '
    "ecommerce, redesign, automation, branding_web\n"
    '- "recommended_contact_method": uno de: whatsapp, email, call, '
    "demo_first, manual_review\n"
    '- "should_call": uno de: yes, no, maybe\n'
    '- "call_reason": razón para llamar o no (1-2 oraciones)\n'
    '- "why_this_lead_matters": por qué este lead importa (1-2 oraciones)\n'
    '- "main_business_signals": lista de señales positivas del negocio '
    "(max 5)\n"
    '- "main_digital_gaps": lista de gaps digitales detectados (max 5)\n'
    '- "recommended_angle": ángulo comercial recomendado (1 oración)\n'
    '- "demo_recommended": true o false\n\n'
    + ANTI_INJECTION_PREAMBLE
)

COMMERCIAL_BRIEF_DATA = (
    "<external_data>\n"
    "Negocio: {business_name}\n"
    "Industria: {industry}\n"
    "Ciudad: {city}\n"
    "Website: {website_url}\n"
    "Instagram: {instagram_url}\n"
    "Score actual: {score}\n"
    "Resumen IA: {llm_summary}\n"
    "Señales: {signals}\n"
    "Datos de investigación: {research_data}\n"
    "Matriz de precios: {pricing_matrix}\n"
    "</external_data>"
)
