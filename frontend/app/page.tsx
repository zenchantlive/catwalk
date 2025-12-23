"use client";

import { ArrowRight, Search, Zap, Loader2, Globe, Github } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { useMutation } from "@tanstack/react-query";
import { analyzeRepo } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import RegistryFeed from "@/components/registry/RegistryFeed";

export default function Home() {
  const [repoUrl, setRepoUrl] = useState("");
  const router = useRouter();

  const { mutate, isPending: isAnalyzing, error } = useMutation({
    mutationFn: (repoUrl: string) => analyzeRepo(repoUrl, false),
    onSuccess: () => {
      const serviceType = "custom";
      router.push(`/configure?service=${serviceType}&repo=${encodeURIComponent(repoUrl)}`);
    }
  });

  const handleAnalyze = (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl) return;
    mutate(repoUrl);
  };

  return (
    <div className="min-h-screen flex flex-col items-center p-6 relative overflow-hidden bg-background">

      {/* Background Gradient Blob */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-[var(--pk-accent-primary-from)]/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Header */}
      <header className="absolute top-0 w-full p-6 flex justify-between items-center z-20 max-w-7xl">
        <div className="flex items-center gap-2">
          {/* Logo placeholder if needed */}
        </div>
        <nav>
          <AuthButton />
        </nav>
      </header>

      <main className="relative z-10 w-full max-w-5xl text-center space-y-10 pt-20">

        {/* Hero Text */}
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-8 duration-700">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-[var(--pk-text-accent)] mb-4">
            <Zap size={12} className="text-[var(--pk-status-green)]" />
            <span>Catwalk Live v0.2</span>
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-white mb-2">
            Build your <span className="text-gradient">AI Toolchain</span>
          </h1>
          <p className="text-lg text-[var(--pk-text-secondary)] max-w-2xl mx-auto">
            Discover, deploy, and connect MCP servers securely.
          </p>
        </div>

        {/* Main Content Area */}
        <div className="animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-200 text-left">
          <Tabs defaultValue="registry" className="w-full">
            <div className="flex justify-center mb-8">
              <TabsList className="bg-white/5 border border-white/10 p-1 rounded-xl">
                <TabsTrigger value="manual" className="data-[state=active]:bg-white/10 rounded-lg px-6">
                  <Github className="w-4 h-4 mr-2" />
                  Import from GitHub
                </TabsTrigger>
                <TabsTrigger value="registry" className="data-[state=active]:bg-white/10 rounded-lg px-6">
                  <Globe className="w-4 h-4 mr-2" />
                  Browse Registry
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="manual" className="max-w-xl mx-auto mt-10">
              <form onSubmit={handleAnalyze} className="relative group">
                <div className="absolute inset-0 bg-gradient-to-r from-[var(--pk-accent-primary-from)] to-[var(--pk-accent-primary-to)] rounded-2xl blur opacity-20 group-hover:opacity-40 transition-opacity duration-500" />
                <div className="relative flex items-center bg-[#0B0C15] border border-white/10 rounded-2xl p-2 shadow-2xl">
                  <Search className="ml-4 text-[var(--pk-text-secondary)]" size={20} />
                  <input
                    type="text"
                    placeholder="Enter GitHub Repository URL..."
                    className="flex-1 bg-transparent border-none outline-none text-white px-4 py-3 placeholder:text-[var(--pk-text-secondary)]/50"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                  />
                  <button
                    type="submit"
                    disabled={isAnalyzing}
                    className="bg-white text-black font-semibold px-6 py-3 rounded-xl hover:bg-white/90 transition-colors flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="animate-spin" size={18} />
                        <span>Analyzing...</span>
                      </>
                    ) : (
                      <>
                        <span>Analyze</span>
                        <ArrowRight size={18} />
                      </>
                    )}
                  </button>
                </div>
              </form>
              {error && (
                <p className="text-[var(--pk-status-red)] text-center mt-4 animate-in fade-in">
                  {(error as Error).message || "Analysis failed. Please try again."}
                </p>
              )}
            </TabsContent>

            <TabsContent value="registry" className="pt-4">
              <RegistryFeed />
            </TabsContent>
          </Tabs>
        </div>

        <div className="mt-20 flex items-center justify-center gap-6 text-sm text-[var(--pk-text-secondary)]">
          <Link href="/dashboard" className="hover:text-white transition-colors">Go to Dashboard</Link>
          <span>•</span>
          <a href="https://github.com/zenchantlive/catwalk" target="_blank" className="hover:text-white transition-colors">Docs</a>
        </div>

      </main>
    </div>
  );
}

function AuthButton() {
  const { data: session } = useSession();

  if (session) {
    return (
      <Link
        href="/dashboard"
        className="px-4 py-2 text-sm font-medium text-white bg-white/10 hover:bg-white/20 rounded-lg transition-colors"
      >
        Dashboard
      </Link>
    )
  }

  return (
    <Link
      href="/?signin=true"
      className="px-4 py-2 text-sm font-medium text-black bg-white hover:bg-gray-100 rounded-lg transition-colors"
    >
      Sign In
    </Link>
  )
}
