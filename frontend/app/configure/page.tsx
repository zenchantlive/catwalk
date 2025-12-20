"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { getFormSchema, createDeployment } from "@/lib/api";
import FormBuilder from "@/components/dynamic-form/FormBuilder";
import { Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

function ConfigureContent() {
    const searchParams = useSearchParams();
    const router = useRouter();

    const serviceType = searchParams.get("service") || "custom";
    const repoUrl = searchParams.get("repo");

    // Fetch schema
    const { data: schema, isLoading, error } = useQuery({
        queryKey: ["formSchema", serviceType, repoUrl],
        queryFn: () => getFormSchema(serviceType, repoUrl),
    });

    // Submit to real API
    const mutation = useMutation({
        mutationFn: async (formData: any) => {
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
            router.push("/dashboard");
        },
        onError: (err) => {
            console.error(err);
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
                {repoUrl && (
                    <p className="text-[var(--pk-text-secondary)] text-sm break-all">
                        Repository: <span className="text-white font-mono">{repoUrl}</span>
                    </p>
                )}
            </div>

            <FormBuilder
                schema={schema}
                onSubmit={async (data) => mutation.mutateAsync(data)}
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
