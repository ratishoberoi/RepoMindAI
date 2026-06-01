import type { LucideIcon } from "lucide-react";

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export type RepositorySummary = {
  repository?: {
    id?: string;
    name?: string;
    source?: string;
    source_type?: string;
    status?: string;
  };
  scores?: Record<string, number>;
  statistics?: Record<string, number>;
  stack?: Record<string, unknown>;
  architecture?: {
    summary?: string;
    layers?: Array<Record<string, unknown>>;
    entrypoints?: Array<Record<string, unknown>>;
    data_models?: Array<Record<string, unknown>>;
    routes?: Array<Record<string, unknown>>;
  };
  knowledge_graph?: KnowledgeGraph;
  security?: {
    findings?: Finding[];
    summary?: Record<string, number>;
  };
  technical_debt?: {
    findings?: Finding[];
  };
  files?: Array<{ relative_path?: string; language?: string; size?: number }>;
};

export type KnowledgeGraph = {
  metrics?: Record<string, number>;
  domains?: Array<Record<string, unknown>>;
  hotspots?: Array<Record<string, unknown>>;
  entities?: Array<Record<string, unknown>>;
  relationships?: Array<Record<string, unknown>>;
};

export type PortfolioIntelligence = {
  portfolio_score?: number;
  repository_count?: number;
  total_repositories?: number;
  risk_concentration?: Array<Record<string, unknown>>;
  top_risks?: Array<Record<string, unknown>>;
  shared_dependencies?: Array<Record<string, unknown>>;
  frameworks?: Record<string, number>;
  languages?: Record<string, number>;
  shared_domains?: Array<Record<string, unknown>>;
  strategic_insights?: Array<Record<string, unknown>>;
  recommendations?: string[];
  repositories?: Array<Record<string, unknown>>;
};

export type Finding = {
  id?: string;
  title?: string;
  severity?: Severity | string;
  file?: string;
  line?: number;
  message?: string;
  evidence?: string;
  recommendation?: string;
};

export type PrRiskResult = {
  risk_score?: number;
  risk_level?: string;
  changed_files?: string[];
  impacted_domains?: Array<Record<string, unknown>>;
  findings?: Finding[];
  review_plan?: string[];
  test_strategy?: string[];
};

export type DriftResult = {
  drift_score?: number;
  drift_level?: string;
  added_domains?: Array<Record<string, unknown>>;
  removed_domains?: Array<Record<string, unknown>>;
  changed_dependencies?: Array<Record<string, unknown>>;
  findings?: Finding[];
};

export type DiligenceResult = {
  score?: number;
  investment_readiness?: string;
  recommendation?: string;
  executive_summary?: string;
  scorecard?: Record<string, number>;
  top_risks?: Array<Record<string, unknown>>;
  enterprise_gaps?: string[];
  critical_evidence?: string[];
  diligence_questions?: string[];
  investor_summary?: string;
  cto_summary?: string;
  security_summary?: string;
  risks?: Finding[];
  strengths?: string[];
  recommendations?: string[];
  sections?: Array<Record<string, unknown>>;
};

export type ChatResult = {
  answer?: string;
  citations?: Citation[];
  related_files?: string[];
  follow_ups?: string[];
  model_status?: Record<string, unknown>;
};

export type Citation = {
  id?: string | number;
  file?: string;
  path?: string;
  start_line?: number;
  end_line?: number;
  line_start?: number;
  line_end?: number;
  text?: string;
};

export type NavItem = {
  id: string;
  label: string;
  eyebrow: string;
  icon: LucideIcon;
};
