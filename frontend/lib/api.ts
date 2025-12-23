// Backend API is currently prefix-routed via Next.js rewrites or absolute URLs

export async function analyzeRepo(repoUrl: string, force: boolean = false) {
    const res = await fetch(`/api/analyze`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ repo_url: repoUrl, force }),
    });

    if (!res.ok) {
        throw new Error("Failed to analyze repository");
    }

    return res.json();
}

export async function clearAnalysisCache(repoUrl: string) {
    const res = await fetch(`/api/analyze/cache?repo_url=${encodeURIComponent(repoUrl)}`, {
        method: "DELETE",
    });

    if (!res.ok) {
        throw new Error("Failed to clear cache");
    }

    return res.json();
}

export async function generateFormSchema(analysisId: string) {
    const res = await fetch(`/api/forms/${analysisId}`);

    if (!res.ok) {
        throw new Error("Failed to fetch form schema");
    }

    return res.json();
}

export interface Deployment {
    id: string;
    name: string;
    status: string;
    connection_url: string;
    created_at: string;
    error_message?: string;
}

export async function createDeployment(data: {
    name: string;
    credentials: Record<string, string>;
    schedule_config?: Record<string, unknown>;
}): Promise<Deployment> {
    const res = await fetch("/api/deployments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });

    if (!res.ok) {
        throw new Error("Failed to create deployment");
    }

    return res.json();
}

export async function getDeployments(): Promise<Deployment[]> {
    const res = await fetch("/api/deployments");

    if (!res.ok) {
        throw new Error("Failed to fetch deployments");
    }

    return res.json();
}

export interface RegistryServer {
    id: string;
    name: string;
    description: string;
    version: string;
    namespace: string;
    capabilities: {
        deployable: boolean;
        connectable: boolean;
    };
    trust: {
        is_official: boolean;
        last_updated: string;
    };
    install_ref?: string; repository_url?: string;
}

export const registry = {
    search: async (query?: string): Promise<RegistryServer[]> => {
        const params = new URLSearchParams();
        if (query) params.append("q", query);

        const res = await fetch(`/api/registry/search?${params.toString()}`);
        if (!res.ok) throw new Error("Failed to search registry");
        return res.json();
    },

    get: async (id: string): Promise<RegistryServer> => {
        const res = await fetch(`/api/registry/${id}`);
        if (!res.ok) throw new Error("Failed to get server details");
        return res.json();
    }
};


export async function getFormSchema(serviceType: string, repoUrl: string) {
    if (serviceType === "custom" && repoUrl) {
        // Call the forms endpoint which transforms analysis into FormSchema format
        const res = await fetch(`/api/forms/generate/${serviceType}?repo_url=${encodeURIComponent(repoUrl)}`);
        if (!res.ok) {
            throw new Error("Failed to generate form schema");
        }
        return res.json();
    }
    return null;
}

export async function getRegistryFormSchema(registryId: string) {
    /**
     * Generate form schema directly from registry API data (no LLM analysis).
     * This is much faster and cheaper than analyzing GitHub repos.
     *
     * @param registryId - Full registry ID (e.g., "ai.exa/exa")
     * @returns FormSchema with fields for environment variables and mcp_config
     * @throws Error if server not found or not deployable
     */
    const res = await fetch(
        `/api/forms/generate/registry/${encodeURIComponent(registryId)}`
    );

    if (!res.ok) {
        const error = await res.json().catch(() => ({}));
        throw new Error(error.detail || "Failed to fetch registry form schema");
    }

    return res.json();
}
