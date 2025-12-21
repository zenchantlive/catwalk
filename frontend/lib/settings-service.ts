/**
 * Settings Service
 * 
 * Handles API calls for user settings (API keys).
 */

const API_BASE = "http://localhost:8000" // Should ideally use env var or match api.ts

export interface SettingsResponse {
    fly_api_token: string | null
    openrouter_api_key: string | null
    has_fly_token: boolean
    has_openrouter_key: boolean
    updated_at: string
}

export interface SettingsRequest {
    fly_api_token?: string | null
    openrouter_api_key?: string | null
}

export const SettingsService = {
    /**
     * Get current user settings
     */
    getSettings: async (): Promise<SettingsResponse> => {
        const res = await fetch(`${API_BASE}/api/settings`, {
            headers: {
                "Content-Type": "application/json",
            },
        })

        if (!res.ok) {
            if (res.status === 401) {
                throw new Error("Unauthorized")
            }
            throw new Error("Failed to fetch settings")
        }

        return res.json()
    },

    /**
     * Update user settings
     */
    updateSettings: async (data: SettingsRequest): Promise<SettingsResponse> => {
        const res = await fetch(`${API_BASE}/api/settings`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(data),
        })

        if (!res.ok) {
            throw new Error("Failed to update settings")
        }

        return res.json()
    },

    /**
     * Delete all user settings
     */
    deleteSettings: async (): Promise<void> => {
        const res = await fetch(`${API_BASE}/api/settings`, {
            method: "DELETE",
        })

        if (!res.ok) {
            throw new Error("Failed to delete settings")
        }
    },
}
