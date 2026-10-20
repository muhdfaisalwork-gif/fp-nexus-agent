import sys
import os
import json
import traceback
from typing import Dict, Any, List, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.db.database import init_db, get_connection
from core.llm.client import UniversalLLMClient
from core.brain.brain import BrainManager
from core.skills.gig_optimizer import GigOptimizer
from core.skills.proposal_writer import ProposalWriter
from core.skills.profile_optimizer import ProfileOptimizer
from core.skills.project_uploader import ProjectUploader
from core.skills.client_outreach import ClientOutreach
from core.skills.inbox_handler import InboxHandler
from core.seo.platform_seo import PlatformSEO
from core.reach.scanner import CompetitorScanner

class FPNexusMCPServer:
    """
    JSON-RPC 2.0 Stdio MCP Server for FP Nexus Agent (Freelancing Platforms).
    Complies with Model Context Protocol specification.
    """

    def __init__(self):
        init_db()
        self.llm = UniversalLLMClient()
        self.brain = BrainManager()
        self.gig_opt = GigOptimizer(self.llm, self.brain)
        self.prop_writer = ProposalWriter(self.llm, self.brain)
        self.prof_opt = ProfileOptimizer(self.llm, self.brain)
        self.proj_uploader = ProjectUploader(self.llm, self.brain)
        self.outreach = ClientOutreach(self.llm, self.brain)
        self.inbox = InboxHandler(self.llm, self.brain)
        self.seo = PlatformSEO(self.llm)
        self.scanner = CompetitorScanner(llm=self.llm)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "optimize_gig",
                "description": "Drafts or optimizes a complete freelance gig (Fiverr / Upwork Project Catalog) with title, 5 search tags, 3-tier packages, FAQs, requirements, and strict 82-rule humanizer compliance.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Core service topic (e.g. 'Python Playwright Web Scraper' or 'FastAPI Microservice')."
                        },
                        "target_keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of target buyer search keywords."
                        },
                        "platform": {
                            "type": "string",
                            "enum": ["fiverr", "upwork", "freelancer"],
                            "default": "fiverr"
                        }
                    },
                    "required": ["topic"]
                }
            },
            {
                "name": "draft_proposal",
                "description": "Drafts a high-converting, human-natural proposal for a client job posting or buyer request, addressing the client's problem in Line 1 and citing verified Story Bank receipts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "job_description": {
                            "type": "string",
                            "description": "The client's job posting or project requirements."
                        },
                        "client_budget": {
                            "type": "string",
                            "description": "Client's stated budget or hourly rate."
                        },
                        "platform": {
                            "type": "string",
                            "enum": ["upwork", "fiverr", "freelancer"],
                            "default": "upwork"
                        }
                    },
                    "required": ["job_description"]
                }
            },
            {
                "name": "audit_gig_seo",
                "description": "Calculates the quantitative Freelance SEO Score (0-100), keyword density, tag alignment, and algorithmic suggestions for a gig.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Gig title"},
                        "description": {"type": "string", "description": "Gig description"},
                        "search_tags": {"type": "array", "items": {"type": "string"}, "description": "List of search tags"},
                        "primary_keyword": {"type": "string", "description": "Target primary keyword"}
                    },
                    "required": ["title", "description"]
                }
            },
            {
                "name": "format_portfolio_project",
                "description": "Formats a finished technical project into an authoritative case study brief and records verified metrics to the Cognitive Brain.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_title": {"type": "string", "description": "Project title"},
                        "category": {"type": "string", "description": "Industry or tech category"},
                        "problem_solved": {"type": "string", "description": "What problem the client had"},
                        "tech_stack": {"type": "string", "description": "Technologies and libraries used"},
                        "results_or_metrics": {"type": "string", "description": "Concrete measured outcome (e.g. latency, hours saved)"},
                        "deliverables": {"type": "string", "description": "Artifacts delivered to client"}
                    },
                    "required": ["project_title", "problem_solved", "tech_stack", "results_or_metrics"]
                }
            },
            {
                "name": "reply_to_client",
                "description": "Classifies an incoming client message in your inbox (pricing, scope, deadline, revision) and drafts a persuasive, natural response.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "client_message": {"type": "string", "description": "The client's message"},
                        "conversation_context": {"type": "string", "description": "Background details or previous messages"},
                        "gig_or_project_name": {"type": "string", "description": "Service name"},
                        "freelancer_rate": {"type": "string", "description": "Freelancer rate or hourly pricing anchor"}
                    },
                    "required": ["client_message"]
                }
            },
            {
                "name": "scan_competitor_gig",
                "description": "Uses Reach Eyes to scrape and reverse-engineer a competitor gig URL on Fiverr or Upwork, extracting their tags, pricing, and counter-strategy.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Full URL of the competitor gig or profile"},
                        "platform": {"type": "string", "enum": ["fiverr", "upwork"], "default": "fiverr"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "get_freelance_receipts",
                "description": "Queries verified past project metrics, benchmarks, and deliverables from the local Cognitive Brain Story Bank.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query (e.g. 'latency', 'scraping', 'saas', 'api')"}
                    }
                }
            },
            {
                "name": "run_biweekly_seo_audit",
                "description": "Triggers the bi-weekly deep SEO audit on all active gigs to ensure search ranking freshness.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "draft_outreach",
                "description": "Drafts a short, high-conversion value-first cold outreach message to prospective freelance clients based on observations and real receipts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prospect_name_or_company": {"type": "string", "description": "Target prospect or company name"},
                        "prospect_problem_or_tech": {"type": "string", "description": "Their tech stack or potential bottleneck"},
                        "outreach_channel": {"type": "string", "description": "E.g. direct_message, email, or upwork", "default": "direct_message"},
                        "specific_observation": {"type": "string", "description": "Concrete observation regarding their site, repo, or API"}
                    },
                    "required": ["prospect_name_or_company", "prospect_problem_or_tech"]
                }
            },
            {
                "name": "optimize_profile",
                "description": "Generates an authoritative, human-sounding freelancer profile (bio, headline, skills) for Fiverr or Upwork.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "primary_role": {"type": "string", "description": "Primary role (e.g. 'Backend Engineer', 'Full-Stack Developer')"},
                        "core_skills": {"type": "array", "items": {"type": "string"}, "description": "Core skills list"},
                        "years_experience": {"type": "integer", "default": 5},
                        "platform": {"type": "string", "enum": ["fiverr", "upwork"], "default": "fiverr"},
                        "specialty_niche": {"type": "string", "description": "Specialty niche or sub-discipline"}
                    },
                    "required": ["primary_role", "core_skills"]
                }
            }
        ]


    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name == "optimize_gig":
            topic = arguments.get("topic", "")
            keywords = arguments.get("target_keywords", [])
            platform = arguments.get("platform", "fiverr")
            return self.gig_opt.optimize_gig(topic=topic, target_keywords=keywords, platform_name=platform)

        elif name == "draft_proposal":
            job_desc = arguments.get("job_description", "")
            budget = arguments.get("client_budget")
            platform = arguments.get("platform", "upwork")
            return self.prop_writer.draft_proposal(job_description=job_desc, client_budget=budget, platform_name=platform)

        elif name == "audit_gig_seo":
            return self.seo.audit_gig_seo(gig_data=arguments, primary_keyword=arguments.get("primary_keyword", ""))

        elif name == "format_portfolio_project":
            return self.proj_uploader.format_project_case_study(
                project_title=arguments.get("project_title", ""),
                niche_or_category=arguments.get("category", "General"),
                problem_solved=arguments.get("problem_solved", ""),
                tech_stack=arguments.get("tech_stack", ""),
                results_or_metrics=arguments.get("results_or_metrics", ""),
                deliverables=arguments.get("deliverables", ""),
                save_to_brain=True
            )

        elif name == "reply_to_client":
            return self.inbox.reply_to_client(
                client_message=arguments.get("client_message", ""),
                conversation_context=arguments.get("conversation_context", ""),
                gig_or_project_name=arguments.get("gig_or_project_name", ""),
                freelancer_rate=arguments.get("freelancer_rate")
            )

        elif name == "scan_competitor_gig":
            url = arguments.get("url", "")
            platform = arguments.get("platform", "fiverr")
            return self.scanner.scan_competitor_url(url=url, platform_name=platform)

        elif name == "get_freelance_receipts":
            q = arguments.get("query", "")
            return self.brain.get_receipts(query=q)

        elif name == "run_biweekly_seo_audit":
            from core.scheduler.seo_cron import SEOScheduler
            scheduler = SEOScheduler(self.seo)
            return scheduler.check_and_run_scheduled_audits()

        elif name == "draft_outreach":
            return self.outreach.draft_outreach(
                prospect_name_or_company=arguments.get("prospect_name_or_company", ""),
                prospect_problem_or_tech=arguments.get("prospect_problem_or_tech", ""),
                outreach_channel=arguments.get("outreach_channel", "direct_message"),
                specific_observation=arguments.get("specific_observation", "")
            )

        elif name == "optimize_profile":
            return self.prof_opt.optimize_profile(
                primary_role=arguments.get("primary_role", ""),
                core_skills=arguments.get("core_skills", []),
                years_experience=arguments.get("years_experience", 5),
                platform_name=arguments.get("platform", "fiverr"),
                specialty_niche=arguments.get("specialty_niche", "")
            )

        else:
            raise ValueError(f"Unknown tool: {name}")


    def handle_request(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "fp-nexus-agent",
                        "version": "1.0.0"
                    }
                }
            }

        elif method == "notifications/initialized":
            return None

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": self.get_tool_definitions()
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                result = self.execute_tool(tool_name, tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2, default=str) if isinstance(result, (dict, list)) else str(result)
                            }
                        ]
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32603,
                        "message": str(e),
                        "data": traceback.format_exc()
                    }
                }

        else:
            if msg_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found."
                    }
                }
            return None


def run_stdio_server():
    server = FPNexusMCPServer()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = server.handle_request(req)
            if resp:
                sys.stdout.write(json.dumps(resp, default=str) + "\n")
                sys.stdout.flush()
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"}
            }
            sys.stdout.write(json.dumps(err_resp, default=str) + "\n")
            sys.stdout.flush()
