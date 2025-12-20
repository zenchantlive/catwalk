"use client";

import { ArrowRight, Search, Zap, Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { analyzeRepo } from "@/lib/api";

export default function Home() {
  const [repoUrl, setRepoUrl] = useState("");
  const router = useRouter();

  const { mutate, isPending: isAnalyzing, error } = useMutation({
    mutationFn: analyzeRepo,
    onSuccess: (data) => {
      // Redirect to configure page with result data or just the type if we know it
      // For now, let's assume we want to configure "openai" by default or infer from data
      // In a real scenario, data.data might contain "detected_service"

      const serviceType = "custom"; // Default/Fallback for now until analysis is detailed
      router.push(`/configure?service=${serviceType}&repo=${encodeURIComponent(repoUrl)}`);
    }
  });

  const handleAnalyze = (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl) return;
    mutate(repoUrl);
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 relative overflow-hidden">

      {/* Background Gradient Blob */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-[var(--pk-accent-primary-from)]/20 rounded-full blur-[120px] pointer-events-none" />

      <main className="relative z-10 w-full max-w-3xl text-center space-y-10">

        {/* Hero Text */}
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-8 duration-700">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-[var(--pk-text-accent)] mb-4">
            <Zap size={12} className="text-[var(--pk-status-green)]" />
            <span>Catwalk Live v0.1</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-white">
            Orchestrate your <br />
            <span className="text-gradient">AI Agents</span> securely.
          </h1>
          <p className="text-lg md:text-xl text-[var(--pk-text-secondary)] max-w-2xl mx-auto">
            Deploy, manage, and monitor your MCP servers and LLM agents with a modern, secure dashboard.
          </p>
        </div>

        {/* Input Action */}
        <div className="animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-200">
          <form onSubmit={handleAnalyze} className="relative max-w-xl mx-auto group">
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

          <div className="mt-8 flex items-center justify-center gap-6 text-sm text-[var(--pk-text-secondary)]">
            <Link href="/dashboard" className="hover:text-white transition-colors">Skip to Dashboard</Link>
            <span>•</span>
            <a href="https://github.com/zenchantlive/catwalk" target="_blank" className="hover:text-white transition-colors">View Documentation</a>
          </div>
        </div>
      </main>
    </div>
  );
}
