import type {
  Lead,
  LeadSignal,
  OutreachDraft,
  OutreachLog,
  SuppressionEntry,
  DashboardStats,
  PipelineStage,
  TimeSeriesPoint,
  IndustryBreakdown,
  CityBreakdown,
  SourcePerformance,
} from "@/types";

// ─── Helpers ───────────────────────────────────────────

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString();
}

function uuid(): string {
  return crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
}

// ─── Leads ─────────────────────────────────────────────

export const MOCK_LEADS: Lead[] = [
  {
    id: "lead-001", business_name: "Café El Molino", industry: "Gastronomía",
    city: "Buenos Aires", zone: "Palermo", website_url: null,
    instagram_url: "https://instagram.com/cafeelmolino", email: null,
    phone: "+5411-4567-8901", source_id: "src-001", status: "scored",
    score: 78, quality: "high",
    llm_summary: "Café tradicional en Palermo con fuerte presencia en Instagram pero sin sitio web propio. Más de 5K seguidores y buenas reseñas en Google. Ideal para desarrollo de web con menú digital y reservas online.",
    llm_quality_assessment: "Lead de alta calidad: negocio establecido sin presencia web, con audiencia digital activa.",
    llm_suggested_angle: "Proponer una web con menú digital, sistema de reservas y galería conectada a Instagram.",
    dedup_hash: "abc123", created_at: daysAgo(5), updated_at: daysAgo(1),
    enriched_at: daysAgo(4), scored_at: daysAgo(3),
    signals: [
      { id: "sig-001", lead_id: "lead-001", signal_type: "no_website", detail: "No website URL provided", detected_at: daysAgo(4) },
      { id: "sig-002", lead_id: "lead-001", signal_type: "instagram_only", detail: "https://instagram.com/cafeelmolino", detected_at: daysAgo(4) },
    ],
    source: { id: "src-001", name: "Crawler Buenos Aires", source_type: "crawler", url: null, description: null, created_at: daysAgo(30) },
    owner: null, notes: null,
  },
  {
    id: "lead-002", business_name: "Peluquería Estilo", industry: "Belleza",
    city: "Rosario", zone: "Centro", website_url: "https://peluqueriaestilo.wixsite.com/home",
    instagram_url: "https://instagram.com/peluqueriaestilo", email: "info@peluqueriaestilo.com",
    phone: "+54341-555-1234", source_id: "src-001", status: "draft_ready",
    score: 65, quality: "high",
    llm_summary: "Peluquería con 8 años en el mercado rosarino. Usa Wix gratuito como web. Perfil activo en IG con +3K seguidores. Tiene email visible y buena reputación local.",
    llm_quality_assessment: "Buen lead: negocio consolidado con web en plataforma gratuita y disposición a tener presencia online.",
    llm_suggested_angle: "Migrar de Wix a dominio propio con sistema de turnos online y galería de trabajos.",
    dedup_hash: "def456", created_at: daysAgo(7), updated_at: daysAgo(1),
    enriched_at: daysAgo(6), scored_at: daysAgo(5),
    signals: [
      { id: "sig-003", lead_id: "lead-002", signal_type: "no_custom_domain", detail: "Hosted on wixsite.com", detected_at: daysAgo(6) },
      { id: "sig-004", lead_id: "lead-002", signal_type: "weak_seo", detail: "Missing meta description", detected_at: daysAgo(6) },
      { id: "sig-005", lead_id: "lead-002", signal_type: "has_website", detail: "HTTP 200", detected_at: daysAgo(6) },
    ],
    source: { id: "src-001", name: "Crawler Buenos Aires", source_type: "crawler", url: null, description: null, created_at: daysAgo(30) },
    owner: null, notes: null,
  },
  {
    id: "lead-003", business_name: "Taller Mecánico Rodríguez", industry: "Automotriz",
    city: "Córdoba", zone: "Barrio General Paz", website_url: null,
    instagram_url: null, email: null,
    phone: "+54351-123-4567", source_id: "src-002", status: "new",
    score: null, quality: "unknown",
    llm_summary: null, llm_quality_assessment: null, llm_suggested_angle: null,
    dedup_hash: "ghi789", created_at: daysAgo(1), updated_at: daysAgo(1),
    enriched_at: null, scored_at: null, signals: [],
    source: { id: "src-002", name: "Manual", source_type: "manual", url: null, description: null, created_at: daysAgo(30) },
    owner: null, notes: null,
  },
  {
    id: "lead-004", business_name: "Boutique Luna", industry: "Indumentaria",
    city: "Buenos Aires", zone: "Recoleta",
    website_url: "https://boutiqueluna.com", instagram_url: "https://instagram.com/boutiqueluna",
    email: "ventas@boutiqueluna.com", phone: "+5411-9876-5432",
    source_id: "src-001", status: "contacted",
    score: 42, quality: "medium",
    llm_summary: "Boutique de indumentaria femenina en Recoleta. Tiene dominio propio y web funcional pero con diseño desactualizado. E-commerce básico. Podría beneficiarse de una renovación.",
    llm_quality_assessment: "Lead medio: ya tiene web propia pero el diseño es anticuado. Menor urgencia que negocios sin web.",
    llm_suggested_angle: "Proponer rediseño moderno con mejor UX de e-commerce y optimización mobile.",
    dedup_hash: "jkl012", created_at: daysAgo(12), updated_at: daysAgo(2),
    enriched_at: daysAgo(10), scored_at: daysAgo(9),
    signals: [
      { id: "sig-006", lead_id: "lead-004", signal_type: "outdated_website", detail: "Generator: WordPress 5.2", detected_at: daysAgo(10) },
      { id: "sig-007", lead_id: "lead-004", signal_type: "has_website", detail: "HTTP 200", detected_at: daysAgo(10) },
      { id: "sig-008", lead_id: "lead-004", signal_type: "has_custom_domain", detail: "boutiqueluna.com", detected_at: daysAgo(10) },
      { id: "sig-009", lead_id: "lead-004", signal_type: "no_mobile_friendly", detail: "No viewport meta tag", detected_at: daysAgo(10) },
    ],
    source: { id: "src-001", name: "Crawler Buenos Aires", source_type: "crawler", url: null, description: null, created_at: daysAgo(30) },
    owner: null, notes: null,
  },
  {
    id: "lead-005", business_name: "Consultorio Dra. Pérez", industry: "Salud",
    city: "Mendoza", zone: "Ciudad", website_url: null,
    instagram_url: "https://instagram.com/dra.perez.odonto", email: "draperez@gmail.com",
    phone: "+54261-555-1234", source_id: "src-002", status: "replied",
    score: 72, quality: "high",
    llm_summary: "Consultorio odontológico en Mendoza con buena reputación. Solo IG como canal digital. Email personal (gmail). Necesita web profesional con turnos online.",
    llm_quality_assessment: "Alta calidad: profesional de salud sin web, rubro que necesita presencia digital profesional.",
    llm_suggested_angle: "Web profesional con sistema de turnos, ficha de tratamientos y testimonios de pacientes.",
    dedup_hash: "mno345", created_at: daysAgo(15), updated_at: daysAgo(1),
    enriched_at: daysAgo(14), scored_at: daysAgo(13),
    signals: [
      { id: "sig-010", lead_id: "lead-005", signal_type: "no_website", detail: "No website URL", detected_at: daysAgo(14) },
      { id: "sig-011", lead_id: "lead-005", signal_type: "instagram_only", detail: "IG only", detected_at: daysAgo(14) },
      { id: "sig-012", lead_id: "lead-005", signal_type: "no_visible_email", detail: "Gmail personal", detected_at: daysAgo(14) },
    ],
    source: { id: "src-002", name: "Manual", source_type: "manual", url: null, description: null, created_at: daysAgo(30) },
    owner: null, notes: "Respondió con interés. Quiere saber presupuesto.",
  },
  {
    id: "lead-006", business_name: "Gym Power Fitness", industry: "Fitness",
    city: "Buenos Aires", zone: "Belgrano", website_url: "https://powerfitness.com.ar",
    instagram_url: "https://instagram.com/powerfitnessgym", email: "info@powerfitness.com.ar",
    phone: "+5411-4444-5555", source_id: "src-001", status: "meeting",
    score: 55, quality: "medium",
    llm_summary: "Gimnasio en Belgrano con web propia pero básica. Usa WordPress antiguo. Tiene buena presencia en IG con +10K seguidores.",
    llm_quality_assessment: "Medio: tiene web pero anticuada. Buen rubro para rediseño con sistema de clases y membresías.",
    llm_suggested_angle: "Rediseño con sistema de reserva de clases, planes de membresía online y landing para nuevos miembros.",
    dedup_hash: "pqr678", created_at: daysAgo(20), updated_at: daysAgo(0),
    enriched_at: daysAgo(18), scored_at: daysAgo(17),
    signals: [
      { id: "sig-013", lead_id: "lead-006", signal_type: "outdated_website", detail: "Generator: WordPress 4.9", detected_at: daysAgo(18) },
      { id: "sig-014", lead_id: "lead-006", signal_type: "no_ssl", detail: "HTTP only", detected_at: daysAgo(18) },
      { id: "sig-015", lead_id: "lead-006", signal_type: "has_website", detail: "HTTP 200", detected_at: daysAgo(18) },
    ],
    source: { id: "src-001", name: "Crawler Buenos Aires", source_type: "crawler", url: null, description: null, created_at: daysAgo(30) },
    owner: null, notes: "Reunión pautada para el jueves.",
  },
  {
    id: "lead-007", business_name: "Inmobiliaria del Sur", industry: "Inmobiliaria",
    city: "Bahía Blanca", zone: "Centro", website_url: null,
    instagram_url: "https://instagram.com/inmobdelsur", email: "contacto@inmobdelsur.com",
    phone: "+54291-444-5555", source_id: "src-003", status: "won",
    score: 85, quality: "high",
    llm_summary: "Inmobiliaria con 15 años en Bahía Blanca. Sin web propia, opera por IG y portales. Altísimo potencial para web con listado de propiedades.",
    llm_quality_assessment: "Excelente lead: inmobiliaria sin web propia en ciudad con poca competencia digital.",
    llm_suggested_angle: "Portal de propiedades propio con búsqueda avanzada, fotos HD y contacto directo.",
    dedup_hash: "stu901", created_at: daysAgo(25), updated_at: daysAgo(3),
    enriched_at: daysAgo(23), scored_at: daysAgo(22),
    signals: [
      { id: "sig-016", lead_id: "lead-007", signal_type: "no_website", detail: "No website", detected_at: daysAgo(23) },
      { id: "sig-017", lead_id: "lead-007", signal_type: "instagram_only", detail: "IG only", detected_at: daysAgo(23) },
    ],
    source: { id: "src-003", name: "Referido", source_type: "manual", url: null, description: "Referido por cliente anterior", created_at: daysAgo(30) },
    owner: null, notes: "Cerrado! Proyecto de portal de propiedades. Presupuesto aprobado.",
  },
  {
    id: "lead-008", business_name: "Veterinaria Patitas", industry: "Veterinaria",
    city: "Rosario", zone: "Fisherton", website_url: "http://veterinariapatitas.blogspot.com",
    instagram_url: null, email: "patitas.vet@yahoo.com",
    phone: "+54341-666-7777", source_id: "src-001", status: "enriched",
    score: null, quality: "unknown",
    llm_summary: null, llm_quality_assessment: null, llm_suggested_angle: null,
    dedup_hash: "vwx234", created_at: daysAgo(3), updated_at: daysAgo(2),
    enriched_at: daysAgo(2), scored_at: null,
    signals: [
      { id: "sig-018", lead_id: "lead-008", signal_type: "no_custom_domain", detail: "Hosted on blogspot.com", detected_at: daysAgo(2) },
      { id: "sig-019", lead_id: "lead-008", signal_type: "no_ssl", detail: "HTTP only", detected_at: daysAgo(2) },
      { id: "sig-020", lead_id: "lead-008", signal_type: "weak_seo", detail: "Missing title", detected_at: daysAgo(2) },
    ],
    source: { id: "src-001", name: "Crawler Buenos Aires", source_type: "crawler", url: null, description: null, created_at: daysAgo(30) },
    owner: null, notes: null,
  },
  {
    id: "lead-009", business_name: "Estudio Contable Martínez & Asoc.", industry: "Contable",
    city: "Buenos Aires", zone: "Microcentro", website_url: null,
    instagram_url: null, email: "estudio.martinez@gmail.com",
    phone: "+5411-3333-4444", source_id: "src-002", status: "approved",
    score: 68, quality: "high",
    llm_summary: "Estudio contable con más de 20 años de trayectoria. Sin presencia digital alguna más allá de un email personal.",
    llm_quality_assessment: "Muy buen lead: servicio profesional sin web, rubro con alta necesidad de credibilidad digital.",
    llm_suggested_angle: "Web institucional con servicios, equipo, blog de novedades impositivas y formulario de contacto.",
    dedup_hash: "yza567", created_at: daysAgo(8), updated_at: daysAgo(1),
    enriched_at: daysAgo(7), scored_at: daysAgo(6),
    signals: [
      { id: "sig-021", lead_id: "lead-009", signal_type: "no_website", detail: "No website", detected_at: daysAgo(7) },
      { id: "sig-022", lead_id: "lead-009", signal_type: "no_visible_email", detail: "Gmail only", detected_at: daysAgo(7) },
    ],
    source: { id: "src-002", name: "Manual", source_type: "manual", url: null, description: null, created_at: daysAgo(30) },
    owner: null, notes: null,
  },
  {
    id: "lead-010", business_name: "Hotel Andino", industry: "Hotelería",
    city: "Mendoza", zone: "Potrerillos", website_url: "https://hotelandino.com.ar",
    instagram_url: "https://instagram.com/hotelandino", email: "reservas@hotelandino.com.ar",
    phone: "+54261-888-9999", source_id: "src-001", status: "lost",
    score: 35, quality: "low",
    llm_summary: "Hotel en zona turística con web propia funcional y dominio .com.ar. Web algo antigua pero operativa.",
    llm_quality_assessment: "Lead bajo: ya tiene web y dominio propio. Menor necesidad percibida.",
    llm_suggested_angle: "Modernización de web con motor de reservas directo y mejor SEO turístico.",
    dedup_hash: "bcd890", created_at: daysAgo(18), updated_at: daysAgo(5),
    enriched_at: daysAgo(16), scored_at: daysAgo(15),
    signals: [
      { id: "sig-023", lead_id: "lead-010", signal_type: "has_website", detail: "HTTP 200", detected_at: daysAgo(16) },
      { id: "sig-024", lead_id: "lead-010", signal_type: "has_custom_domain", detail: "hotelandino.com.ar", detected_at: daysAgo(16) },
      { id: "sig-025", lead_id: "lead-010", signal_type: "outdated_website", detail: "Generator: WordPress 5.0", detected_at: daysAgo(16) },
    ],
    source: { id: "src-001", name: "Crawler Buenos Aires", source_type: "crawler", url: null, description: null, created_at: daysAgo(30) },
    owner: null, notes: "No interesado. Dijo que ya tiene desarrollador.",
  },
];

// ─── Outreach Drafts ───────────────────────────────────

export const MOCK_DRAFTS: OutreachDraft[] = [
  {
    id: "draft-001", lead_id: "lead-001", lead: MOCK_LEADS[0],
    subject: "Tu café merece una web que esté a la altura",
    body: "Hola,\n\nSoy desarrollador web y noté que Café El Molino tiene una presencia increíble en Instagram pero todavía no tiene sitio web propio.\n\nPodría ayudarles a crear una web con menú digital, sistema de reservas y galería conectada a su Instagram.\n\n¿Les interesaría charlar 15 minutos esta semana?\n\nSaludos.",
    status: "pending_review", generated_at: daysAgo(2), reviewed_at: null, sent_at: null,
  },
  {
    id: "draft-002", lead_id: "lead-002", lead: MOCK_LEADS[1],
    subject: "¿Listos para dar el salto de Wix a una web profesional?",
    body: "Hola,\n\nVi que Peluquería Estilo usa Wix para su sitio web. Es un buen comienzo, pero un sitio con dominio propio y sistema de turnos online podría llevar su negocio al siguiente nivel.\n\nMe especializo en crear webs para negocios de belleza con galería de trabajos y reservas integradas.\n\n¿Podemos hablar esta semana?\n\nSaludos.",
    status: "approved", generated_at: daysAgo(4), reviewed_at: daysAgo(3), sent_at: null,
  },
  {
    id: "draft-003", lead_id: "lead-005", lead: MOCK_LEADS[4],
    subject: "Presencia digital profesional para su consultorio",
    body: "Dra. Pérez,\n\nSoy desarrollador web especializado en profesionales de la salud. Noté que su consultorio tiene presencia en Instagram pero no cuenta con un sitio web profesional.\n\nUna web con sistema de turnos online, ficha de tratamientos y testimonios de pacientes podría ayudarla a captar más pacientes.\n\n¿Le interesa una charla breve?\n\nSaludos.",
    status: "sent", generated_at: daysAgo(10), reviewed_at: daysAgo(9), sent_at: daysAgo(8),
  },
  {
    id: "draft-004", lead_id: "lead-009", lead: MOCK_LEADS[8],
    subject: "Credibilidad digital para su estudio contable",
    body: "Estimados,\n\nSoy desarrollador web y trabajo con estudios profesionales que buscan mejorar su presencia digital.\n\nUn sitio web institucional con información de servicios, equipo y un blog de novedades impositivas puede marcar la diferencia frente a la competencia.\n\n¿Les interesaría explorar opciones?\n\nSaludos.",
    status: "pending_review", generated_at: daysAgo(1), reviewed_at: null, sent_at: null,
  },
];

// ─── Activity Logs ─────────────────────────────────────

export const MOCK_LOGS: OutreachLog[] = [
  { id: "log-001", lead_id: "lead-007", draft_id: null, action: "won", actor: "user", detail: "Proyecto cerrado: portal de propiedades", created_at: daysAgo(3) },
  { id: "log-002", lead_id: "lead-005", draft_id: "draft-003", action: "replied", actor: "system", detail: "Respuesta positiva recibida", created_at: daysAgo(1) },
  { id: "log-003", lead_id: "lead-006", draft_id: null, action: "meeting", actor: "user", detail: "Reunión pautada para el jueves", created_at: daysAgo(0) },
  { id: "log-004", lead_id: "lead-002", draft_id: "draft-002", action: "approved", actor: "user", detail: null, created_at: daysAgo(3) },
  { id: "log-005", lead_id: "lead-001", draft_id: "draft-001", action: "generated", actor: "system", detail: null, created_at: daysAgo(2) },
  { id: "log-006", lead_id: "lead-009", draft_id: "draft-004", action: "generated", actor: "system", detail: null, created_at: daysAgo(1) },
  { id: "log-007", lead_id: "lead-010", draft_id: null, action: "lost", actor: "user", detail: "No interesado, tiene desarrollador", created_at: daysAgo(5) },
  { id: "log-008", lead_id: "lead-005", draft_id: "draft-003", action: "sent", actor: "user", detail: null, created_at: daysAgo(8) },
];

// ─── Suppression ───────────────────────────────────────

export const MOCK_SUPPRESSION: SuppressionEntry[] = [
  { id: "sup-001", email: "noquiero@empresa.com", domain: "empresa.com", phone: null, reason: "Pidió no ser contactado", business_name: "Empresa X", added_at: daysAgo(10) },
  { id: "sup-002", email: "admin@otrositio.com", domain: null, phone: null, reason: "Bounce permanente", business_name: "Otro Sitio SA", added_at: daysAgo(15) },
];

// ─── Dashboard Stats ───────────────────────────────────

export const MOCK_STATS: DashboardStats = {
  total_leads: 247,
  new_today: 12,
  qualified: 89,
  approved: 34,
  contacted: 56,
  replied: 23,
  meetings: 8,
  won: 5,
  lost: 14,
  suppressed: 7,
  avg_score: 58.3,
  conversion_rate: 0.089,
  open_rate: 0.64,
  reply_rate: 0.41,
  positive_reply_rate: 0.28,
  meeting_rate: 0.14,
  pipeline_velocity: 4.2,
};

export const MOCK_PIPELINE: PipelineStage[] = [
  { stage: "new",         label: "Nuevos",      count: 47,  percentage: 1.0,   color: "#94a3b8" },
  { stage: "enriched",    label: "Enriquecidos", count: 38,  percentage: 0.81,  color: "#60a5fa" },
  { stage: "scored",      label: "Puntuados",   count: 35,  percentage: 0.74,  color: "#818cf8" },
  { stage: "qualified",   label: "Calificados", count: 28,  percentage: 0.60,  color: "#a78bfa" },
  { stage: "draft_ready", label: "Draft Listo", count: 24,  percentage: 0.51,  color: "#c084fc" },
  { stage: "approved",    label: "Aprobados",   count: 20,  percentage: 0.43,  color: "#22d3ee" },
  { stage: "contacted",   label: "Contactados", count: 18,  percentage: 0.38,  color: "#fbbf24" },
  { stage: "opened",      label: "Abiertos",    count: 12,  percentage: 0.26,  color: "#fb923c" },
  { stage: "replied",     label: "Respondieron", count: 8,   percentage: 0.17,  color: "#34d399" },
  { stage: "meeting",     label: "Reunión",     count: 5,   percentage: 0.11,  color: "#2dd4bf" },
  { stage: "won",         label: "Ganados",     count: 3,   percentage: 0.064, color: "#22c55e" },
];

export const MOCK_TIME_SERIES: TimeSeriesPoint[] = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.now() - (29 - i) * 86400000).toISOString().slice(0, 10),
  leads: Math.floor(Math.random() * 15) + 3,
  outreach: Math.floor(Math.random() * 8) + 1,
  replies: Math.floor(Math.random() * 4),
  conversions: Math.floor(Math.random() * 2),
}));

export const MOCK_INDUSTRY_BREAKDOWN: IndustryBreakdown[] = [
  { industry: "Gastronomía",  count: 45, avg_score: 67.2, conversion_rate: 0.12 },
  { industry: "Belleza",      count: 38, avg_score: 62.1, conversion_rate: 0.11 },
  { industry: "Salud",        count: 32, avg_score: 71.4, conversion_rate: 0.15 },
  { industry: "Inmobiliaria", count: 28, avg_score: 74.8, conversion_rate: 0.18 },
  { industry: "Fitness",      count: 22, avg_score: 55.3, conversion_rate: 0.09 },
  { industry: "Indumentaria", count: 20, avg_score: 48.7, conversion_rate: 0.07 },
  { industry: "Automotriz",   count: 18, avg_score: 52.1, conversion_rate: 0.06 },
  { industry: "Hotelería",    count: 15, avg_score: 44.2, conversion_rate: 0.05 },
  { industry: "Contable",     count: 14, avg_score: 66.0, conversion_rate: 0.14 },
  { industry: "Veterinaria",  count: 12, avg_score: 58.9, conversion_rate: 0.10 },
];

export const MOCK_CITY_BREAKDOWN: CityBreakdown[] = [
  { city: "Buenos Aires", count: 98,  avg_score: 61.5, reply_rate: 0.38 },
  { city: "Rosario",      count: 42,  avg_score: 58.2, reply_rate: 0.42 },
  { city: "Córdoba",      count: 38,  avg_score: 55.7, reply_rate: 0.35 },
  { city: "Mendoza",      count: 28,  avg_score: 63.1, reply_rate: 0.44 },
  { city: "Bahía Blanca", count: 15,  avg_score: 68.3, reply_rate: 0.52 },
  { city: "Tucumán",      count: 12,  avg_score: 54.0, reply_rate: 0.30 },
  { city: "Mar del Plata",count: 10,  avg_score: 57.8, reply_rate: 0.36 },
];

export const MOCK_SOURCE_PERFORMANCE: SourcePerformance[] = [
  { source: "Crawler BA",  leads: 120, avg_score: 58.4, reply_rate: 0.35, conversion_rate: 0.08 },
  { source: "Manual",      leads: 65,  avg_score: 67.2, reply_rate: 0.48, conversion_rate: 0.15 },
  { source: "Referidos",   leads: 35,  avg_score: 74.1, reply_rate: 0.62, conversion_rate: 0.22 },
  { source: "Import CSV",  leads: 27,  avg_score: 45.3, reply_rate: 0.22, conversion_rate: 0.04 },
];
