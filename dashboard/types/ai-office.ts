export interface AgentInfo {
  name: string;
  role: string;
  model: string;
  status: string;
  [key: string]: unknown;
}

export interface AiOfficeStatus {
  agents: {
    mote: AgentInfo;
    scout: AgentInfo;
    executor: AgentInfo;
    reviewer: AgentInfo;
  };
  outcomes: {
    total_won: number;
    total_lost: number;
  };
}

export interface DecisionRecord {
  id: string;
  function_name: string;
  role: string;
  model: string | null;
  status: string;
  latency_ms: number | null;
  fallback_used: boolean;
  target_type: string | null;
  prompt_id: string | null;
  prompt_version: string | null;
  created_at: string | null;
}

export interface InvestigationRecord {
  id: string;
  lead_id: string;
  agent_model: string;
  pages_visited: { url: string; title: string | null }[];
  findings: Record<string, unknown>;
  loops_used: number;
  duration_ms: number;
  error: string | null;
  created_at: string | null;
}
