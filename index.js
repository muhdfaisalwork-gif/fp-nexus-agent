/**
 * FP Nexus Agent - Node.js / JavaScript Client SDK
 * Lightweight client to connect to local or remote FP Nexus Agent APIs.
 */

class FPNexusClient {
  constructor(baseUrl = "http://localhost:8001") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async healthCheck() {
    const res = await fetch(`${this.baseUrl}/api/health`);
    if (!res.ok) {
      throw new Error(`Health check failed with status ${res.status}`);
    }
    return await res.json();
  }

  async optimizeGig(options) {
    const res = await fetch(`${this.baseUrl}/api/gigs/optimize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Gig optimization failed: ${res.statusText}`);
    }
    return await res.json();
  }

  async draftProposal(options) {
    const res = await fetch(`${this.baseUrl}/api/proposals/draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Proposal drafting failed: ${res.statusText}`);
    }
    return await res.json();
  }

  async auditSeo(options) {
    const res = await fetch(`${this.baseUrl}/api/seo/audit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `SEO audit failed: ${res.statusText}`);
    }
    return await res.json();
  }

  async weeklyRefresh(options) {
    const res = await fetch(`${this.baseUrl}/api/seo/weekly-refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Weekly refresh failed: ${res.statusText}`);
    }
    return await res.json();
  }

  async replyToInbox(options) {
    const res = await fetch(`${this.baseUrl}/api/inbox/reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Inbox reply failed: ${res.statusText}`);
    }
    return await res.json();
  }
}

module.exports = { FPNexusClient };
