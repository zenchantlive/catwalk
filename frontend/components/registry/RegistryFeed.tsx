"use client";

import { useEffect, useState } from "react";
import { registry, RegistryServer } from "@/lib/api";
import { ServerCard } from "@/components/registry/ServerCard";
import { Input } from "@/components/ui/input";
import { Search, Loader2 } from "lucide-react";

export default function RegistryFeed() {
    const [servers, setServers] = useState<RegistryServer[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [debouncedQuery, setDebouncedQuery] = useState("");

    // Debounce search input
    useEffect(() => {
        const timer = setTimeout(() => setDebouncedQuery(searchQuery), 300);
        return () => clearTimeout(timer);
    }, [searchQuery]);

    // Fetch data
    useEffect(() => {
        const fetchData = async () => {
            setIsLoading(true);
            try {
                const results = await registry.search(debouncedQuery);
                setServers(results);
            } catch (error) {
                console.error("Failed to fetch registry:", error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();
    }, [debouncedQuery]);

    return (
        <div className="space-y-6">
            {/* Search Header */}
            <div className="sticky top-0 z-10 bg-black/50 backdrop-blur-xl p-4 -mx-4 border-b border-white/10">
                <div className="relative max-w-2xl mx-auto">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50 w-5 h-5" />
                    <Input
                        placeholder="Search MCP servers by name, author, or functionality..."
                        className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-white/30 focus:bg-white/10 transition-all font-light text-lg h-12 rounded-xl"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
            </div>

            {/* Grid */}
            {isLoading ? (
                <div className="flex justify-center py-20">
                    <Loader2 className="w-8 h-8 text-white/30 animate-spin" />
                </div>
            ) : servers.length === 0 ? (
                <div className="text-center py-20 text-white/30">
                    {debouncedQuery ? (
                        <>No servers found matching &quot;{debouncedQuery}&quot;</>
                    ) : (
                        <>No servers available</>
                    )}
                </div>
            ) : (
                <div className="space-y-4">
                    {/* Results count */}
                    {debouncedQuery && (
                        <div className="text-sm text-white/50 px-1">
                            Found {servers.length} server{servers.length !== 1 ? 's' : ''} matching &quot;{debouncedQuery}&quot;
                        </div>
                    )}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {servers.map((server) => (
                            <div key={server.id} className="h-full">
                                <ServerCard server={server} />
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
