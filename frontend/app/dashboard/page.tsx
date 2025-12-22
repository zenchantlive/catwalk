"use client";

import { Plus, AlertCircle, Copy, Info } from "lucide-react";
import Link from "next/link";

import { useQuery } from "@tanstack/react-query";
import { getDeployments } from "@/lib/api";
import { Navbar } from "@/components/layout/navbar";

export default function DashboardPage() {
    const { data: deployments, isLoading } = useQuery({
        queryKey: ["deployments"],
        queryFn: getDeployments,
    });

    return (
        <>
            <Navbar />
            <div className="min-h-screen p-6 md:p-12 space-y-8">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
                    <p className="text-[var(--pk-text-secondary)]">Overview of your active agents.</p>
                </div>
                <Link
                    href="/"
                    className="bg-[var(--pk-primary)] text-white px-4 py-2 rounded-lg hover:bg-opacity-90 transition-all flex items-center gap-2"
                >
                    <Plus size={18} />
                    <span>New Deployment</span>
                </Link>
            </header>

            <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {isLoading ? (
                    <div className="text-[var(--pk-text-secondary)]">Loading deployments...</div>
                ) : deployments?.map((deploy) => (
                    <div key={deploy.id} className="glass-card p-6 space-y-4 hover:border-[var(--pk-primary)]/50 transition-colors group">
                        <div className="flex items-center justify-between">
                            <h3 className="font-semibold text-lg text-white group-hover:text-[var(--pk-primary)] transition-colors">
                                {deploy.name}
                            </h3>
                            <span className={`px-2 py-1 rounded text-xs font-medium uppercase tracking-wider ${deploy.status === 'active' ? 'bg-green-500/10 text-green-400' : 'bg-gray-500/10 text-gray-400'
                                }`}>
                                {deploy.status}
                            </span>
                        </div>

                        {deploy.status === 'failed' && deploy.error_message && (
                            <div className="bg-red-500/10 border border-red-500/20 rounded p-3 space-y-2">
                                <div className="flex items-start gap-2 text-red-400 text-sm">
                                    <AlertCircle size={16} className="mt-0.5 shrink-0" />
                                    <div className="flex-1 break-words">
                                        <p className="font-semibold text-xs uppercase mb-1">Deployment Failed</p>
                                        <p className="text-xs">{deploy.error_message}</p>
                                    </div>
                                    <button
                                        onClick={(e) => {
                                            e.preventDefault();
                                            navigator.clipboard.writeText(deploy.error_message || "");
                                            // You might want to add a toast here
                                        }}
                                        className="text-red-400 hover:text-red-300 p-1 rounded hover:bg-red-500/20 transition-colors"
                                        title="Copy Error"
                                    >
                                        <Copy size={14} />
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Debug Info Toggle */}
                        <details className="group/debug">
                            <summary className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-[var(--pk-text-secondary)] hover:text-white cursor-pointer select-none">
                                <Info size={10} />
                                <span>Debug Info</span>
                            </summary>
                            <div className="mt-2 text-[10px] font-mono text-gray-500 bg-black/20 p-2 rounded overflow-auto max-h-32 whitespace-pre-wrap">
                                {JSON.stringify(deploy, null, 2)}
                            </div>
                        </details>

                        <div className="space-y-2">
                            <p className="text-xs text-[var(--pk-text-secondary)] uppercase font-semibold tracking-wider">Connection URL</p>
                            <code className="block bg-black/30 p-2 rounded text-xs font-mono text-[var(--pk-text-accent)] break-all select-all cursor-pointer">
                                {deploy.connection_url}
                            </code>
                        </div>

                        <div className="pt-2 flex items-center gap-2 text-sm text-[var(--pk-text-secondary)]">
                            <p className="text-xs text-[var(--pk-text-secondary)]">Created: {new Date(deploy.created_at).toLocaleDateString()}</p>
                        </div>
                    </div>
                ))}

                {(!deployments || deployments.length === 0) && !isLoading && (
                    <div className="col-span-full py-12 text-center text-[var(--pk-text-secondary)] bg-white/5 rounded-2xl border border-dashed border-white/10">
                        No active deployments found. Create one to get started.
                    </div>
                )}
            </section>
            </div>
        </>
    );
}
