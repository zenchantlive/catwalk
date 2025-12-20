"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { getFormSchema, getRegistryFormSchema, createDeployment, registry } from "@/lib/api";
import FormBuilder from "@/components/dynamic-form/FormBuilder";
import { Loader2, ArrowLeft, AlertCircle } from "lucide-react";
import Link from "next/link";
import { Suspense, useState } from "react";

function ConfigureContent() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const [deploymentError, setDeploymentError] = useState<any>(null);

    const serviceType = searchParams.get("service") || "custom";
    const paramRepoUrl = searchParams.get("repo");
    const registryId = searchParams.get("registryId");

    // Fetch registry data if registryId is present
    const { data: registryServer, isLoading: isRegistryLoading } = useQuery({
        queryKey: ["registryServer", registryId],
        queryFn: () => registry.get(registryId!),
        enabled: !!registryId
    });

    const isLocalOnlyRegistryServer = !!registryId && !!registryServer && !registryServer.capabilities.deployable;

    // Determine which flow to use:
    // - Registry flow: If registryId exists AND server is deployable
    // - GitHub flow: Otherwise (manual repo URL)
    const useRegistryFlow = !!registryId && registryServer?.capabilities.deployable;
    const finalRepoUrl = paramRepoUrl || registryServer?.repository_url;

    // Fetch schema using appropriate flow
    const { data: schema, isLoading: isSchemaLoading, error } = useQuery({
        queryKey: useRegistryFlow
            ? ["formSchema", "registry", registryId]
            : ["formSchema", serviceType, finalRepoUrl],
        queryFn: () => {
            if (useRegistryFlow) {
                // Fast path: Parse registry data directly (no LLM)
                return getRegistryFormSchema(registryId!);
            } else {
                // Slow path: Analyze GitHub repo with Claude (existing flow)
                return getFormSchema(serviceType, finalRepoUrl!);
            }
        },
        enabled: !isLocalOnlyRegistryServer && (useRegistryFlow ? !!registryId : !!finalRepoUrl)
    });

    const isLoading = isRegistryLoading || isSchemaLoading;

    // Submit to real API
    const mutation = useMutation({
        mutationFn: async (formData: Record<string, any>) => {
            // Segregate name from credentials
            const { name, ...credentials } = formData;

            // Build schedule_config with MCP server configuration from schema
            const schedule_config = schema?.mcp_config
                ? { mcp_config: schema.mcp_config }
                : {};

            return await createDeployment({
                name,
                credentials,
                schedule_config
            });
        },
        onSuccess: () => {
            // Clear any previous errors on success
            setDeploymentError(null);
            router.push("/dashboard");
        },
        onError: (err: any) => {
            console.error("Deployment error:", err);
            // Extract structured error from response
            // The error detail could be in err.response.data.detail or err.detail
            const errorDetail = err?.response?.data?.detail || err?.detail || {
                error: "deployment_failed",
                message: err?.message || "Failed to create deployment",
            };
            setDeploymentError(errorDetail);
            // Scroll to top so user sees the error
            window.scrollTo({ top: 0, behavior: "smooth" });
        }
    });

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="animate-spin text-[var(--pk-accent-primary-from)]" size={32} />
            </div>
        );
    }

    if (error || !schema) {
        if (isLocalOnlyRegistryServer) {
            return (
                <div className="min-h-screen flex flex-col items-center justify-center gap-4 text-center p-6">
                    <p className="text-[var(--pk-status-red)]">
                        This server is marked local-only and can’t be deployed to cloud machines.
                    </p>
                    {registryServer?.repository_url && (
                        <p className="text-[var(--pk-text-secondary)] text-sm break-all max-w-2xl">
                            Repository:{" "}
                            <span className="text-white font-mono">
                                {registryServer.repository_url}
                            </span>
                        </p>
                    )}
                    <Link href="/" className="btn-aurora">Back to Registry</Link>
                </div>
            );
        }

        return (
            <div className="min-h-screen flex flex-col items-center justify-center gap-4 text-center p-6">
                <p className="text-[var(--pk-status-red)]">Failed to load configuration form.</p>
                <Link href="/" className="btn-aurora">Go Back</Link>
            </div>
        );
    }

    return (
        <div className="min-h-screen p-6 md:p-12 max-w-2xl mx-auto space-y-8">
            <Link href="/" className="inline-flex items-center gap-2 text-[var(--pk-text-secondary)] hover:text-white transition-colors">
                <ArrowLeft size={16} />
                Back to Home
            </Link>

            <div className="space-y-2">
                <h1 className="text-3xl font-bold text-gradient">Configure Deployment</h1>
                {finalRepoUrl && (
                    <p className="text-[var(--pk-text-secondary)] text-sm break-all">
                        Repository: <span className="text-white font-mono">{finalRepoUrl}</span>
                    </p>
                )}
            </div>

            {/* Error Display */}
            {deploymentError && (
                <div className="p-4 bg-red-900/20 border border-red-500/50 rounded-lg space-y-3">
                    <div className="flex items-start gap-3">
                        <AlertCircle className="text-red-400 flex-shrink-0 mt-0.5" size={20} />
                        <div className="flex-1 space-y-2">
                            <h3 className="font-semibold text-red-300">
                                {deploymentError.error === "credential_validation_failed"
                                    ? "Missing Required Credentials"
                                    : deploymentError.error === "package_not_found"
                                    ? "Package Not Found"
                                    : "Deployment Failed"}
                            </h3>

                            {deploymentError.message && (
                                <p className="text-red-200 text-sm">{deploymentError.message}</p>
                            )}

                            {deploymentError.errors && Array.isArray(deploymentError.errors) && (
                                <ul className="list-disc list-inside text-red-200 text-sm space-y-1">
                                    {deploymentError.errors.map((err: string, idx: number) => (
                                        <li key={idx}>{err}</li>
                                    ))}
                                </ul>
                            )}

                            {deploymentError.package && (
                                <p className="text-red-300 text-sm font-mono bg-red-950/50 px-2 py-1 rounded">
                                    Package: {deploymentError.package}
                                </p>
                            )}

                            {deploymentError.help && (
                                <p className="text-red-300/80 text-sm italic border-l-2 border-red-500/30 pl-3">
                                    {deploymentError.help}
                                </p>
                            )}

                            <button
                                onClick={() => setDeploymentError(null)}
                                className="text-sm text-red-300 hover:text-red-200 underline transition-colors"
                            >
                                Dismiss
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <FormBuilder
                schema={schema}
                onSubmit={async (data) => { await mutation.mutateAsync(data); }}
                isLoading={mutation.isPending}
            />
        </div>
    );
}

export default function ConfigurePage() {
    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <ConfigureContent />
        </Suspense>
    );
}
