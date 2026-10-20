export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface OptimizeGigOptions {
  service_topic: string;
  platform?: "fiverr" | "upwork" | "freelancer";
  experience_level?: "expert" | "intermediate" | "beginner";
}

export interface DraftProposalOptions {
  job_description: string;
  platform_name?: "fiverr" | "upwork" | "freelancer";
  client_name?: string;
}

export interface AuditSeoOptions {
  title: string;
  description: string;
  search_tags: string[] | string;
  faqs?: Array<{ question: string; answer: string }>;
  primary_keyword?: string;
}

export interface WeeklyRefreshOptions {
  current_tags: string[] | string;
  gig_title?: string;
  gig_category?: string;
}

export interface ReplyInboxOptions {
  client_message: string;
  client_name?: string;
  freelancer_rate?: number;
}

export declare class FPNexusClient {
  constructor(baseUrl?: string);
  healthCheck(): Promise<HealthResponse>;
  optimizeGig(options: OptimizeGigOptions): Promise<any>;
  draftProposal(options: DraftProposalOptions): Promise<any>;
  auditSeo(options: AuditSeoOptions): Promise<any>;
  weeklyRefresh(options: WeeklyRefreshOptions): Promise<any>;
  replyToInbox(options: ReplyInboxOptions): Promise<any>;
}
