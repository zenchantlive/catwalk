"use client"

import { useEffect, useState } from "react"
import { Eye, EyeOff, Save, Trash2, Key, CheckCircle2, Shield } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useToast } from "@/components/ui/use-toast"
// Re-implenting simple confirmation dialog via state instead of missing AlertDialog component. 

import { SettingsService, type SettingsRequest, type SettingsResponse } from "@/lib/settings-service"

export default function SettingsPage() {
  const { toast } = useToast()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [settings, setSettings] = useState<SettingsResponse | null>(null)

  const [flyToken, setFlyToken] = useState("")
  const [openRouterKey, setOpenRouterKey] = useState("")

  const [showFlyToken, setShowFlyToken] = useState(false)
  const [showOpenRouterKey, setShowOpenRouterKey] = useState(false)

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        setLoading(true)
        const data = await SettingsService.getSettings()
        setSettings(data)
        setFlyToken("")
        setOpenRouterKey("")
      } catch (error) {
        console.error("Failed to load settings", error)
        toast({
          variant: "destructive",
          title: "Error loading settings",
          description: "Please check your connection and try again.",
        })
      } finally {
        setLoading(false)
      }
    }

    fetchSettings()
  }, [toast])

  const handleSave = async () => {
    try {
      setSaving(true)

      const payload: SettingsRequest = {}
      if (flyToken.trim()) payload.fly_api_token = flyToken.trim()
      if (openRouterKey.trim()) payload.openrouter_api_key = openRouterKey.trim()

      const updated = await SettingsService.updateSettings(payload)
      setSettings(updated)
      setFlyToken("")
      setOpenRouterKey("")

      toast({
        title: "Settings saved",
        description: "Your API keys have been updated successfully.",
      })
    } catch (error) {
      console.error("Failed to save settings", error)
      toast({
        variant: "destructive",
        title: "Error saving settings",
        description: "Could not save changes.",
      })
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteAll = async () => {
    if (
      !window.confirm(
        "Are you sure you want to delete all your API keys? This cannot be undone."
      )
    ) {
      return
    }

    try {
      await SettingsService.deleteSettings()
      setSettings(null)
      setFlyToken("")
      setOpenRouterKey("")

      toast({
        title: "Settings deleted",
        description: "All API keys have been removed.",
      })
    } catch (error) {
      console.error("Failed to delete settings", error)
      toast({
        variant: "destructive",
        title: "Error deleting settings",
        description: "Could not delete settings.",
      })
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50/50 p-4 font-sans dark:bg-gray-950/50 sm:p-8">
      <div className="mx-auto max-w-4xl space-y-8">

        {/* Header */}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
              Settings
            </h1>
            <p className="text-gray-500 dark:text-gray-400">
              Manage your API keys and credentials.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
              <Shield className="h-3.5 w-3.5" />
              End-to-End Encrypted
            </span>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid gap-6">
          <Card className="border-0 shadow-sm ring-1 ring-gray-200 dark:bg-gray-900 dark:ring-gray-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="h-5 w-5 text-indigo-500" />
                API Credentials
              </CardTitle>
              <CardDescription>
                Provide your API keys to enable deployment and AI features. Keys are stored securely with
                Fernet encryption.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">

              {/* Fly.io Token */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label htmlFor="fly-token" className="text-base font-medium">
                    Fly.io API Token
                  </Label>
                  {settings?.has_fly_token && (
                    <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-500">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Saved
                    </span>
                  )}
                </div>
                <div className="relative">
                  <Input
                    id="fly-token"
                    type={showFlyToken ? "text" : "password"}
                    placeholder="Fly.io Access Token (starts with fly_...)"
                    value={flyToken}
                    onChange={(e) => setFlyToken(e.target.value)}
                    className="pr-10 font-mono transition-all focus:ring-2 focus:ring-indigo-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowFlyToken(!showFlyToken)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    {showFlyToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Required for deploying servers. Get it from your{" "}
                  <a
                    href="https://fly.io/user/personal_access_tokens"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                  >
                    Fly.io Dashboard
                  </a>
                  .
                </p>
              </div>

              <div className="h-px bg-gray-100 dark:bg-gray-800" />

              {/* OpenRouter Key */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label htmlFor="openrouter-key" className="text-base font-medium">
                    OpenRouter API Key
                  </Label>
                  {settings?.has_openrouter_key && (
                    <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-500">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Saved
                    </span>
                  )}
                </div>
                <div className="relative">
                  <Input
                    id="openrouter-key"
                    type={showOpenRouterKey ? "text" : "password"}
                    placeholder="sk-or-..."
                    value={openRouterKey}
                    onChange={(e) => setOpenRouterKey(e.target.value)}
                    className="pr-10 font-mono transition-all focus:ring-2 focus:ring-indigo-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowOpenRouterKey(!showOpenRouterKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    {showOpenRouterKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Required for AI analysis. Get it from{" "}
                  <a
                    href="https://openrouter.ai/keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                  >
                    OpenRouter settings
                  </a>
                  .
                </p>
              </div>
            </CardContent>
            <CardFooter className="flex flex-col gap-4 border-t bg-gray-50/50 p-6 dark:bg-gray-900/50 sm:flex-row sm:items-center sm:justify-between">
              <Button
                variant="ghost"
                onClick={handleDeleteAll}
                className="text-red-500 hover:bg-red-50 hover:text-red-600 dark:text-red-400 dark:hover:bg-red-900/20"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Clear All Keys
              </Button>
              <Button
                onClick={handleSave}
                disabled={saving}
                className="min-w-[120px] bg-indigo-600 text-white hover:bg-indigo-700"
              >
                {saving ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Save Changes
                  </>
                )}
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>
    </div>
  )
}
