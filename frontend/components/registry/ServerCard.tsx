import { RegistryServer } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Check, Rocket, Link as LinkIcon } from "lucide-react";
import Link from "next/link";

interface ServerCardProps {
    server: RegistryServer;
}

export function ServerCard({ server }: ServerCardProps) {
    const isDeployable = server.capabilities.deployable;

    // Generate avatar letter from namespace (author) instead of name for better differentiation
    const initial = server.namespace.charAt(0).toUpperCase();
    
    // Generate unique colors based on namespace for visual differentiation
    const getAvatarStyle = (namespace: string) => {
        const colorSets = [
            { bg: 'from-indigo-500/20 to-purple-500/20', text: 'from-indigo-400 to-purple-400' },
            { bg: 'from-blue-500/20 to-cyan-500/20', text: 'from-blue-400 to-cyan-400' },
            { bg: 'from-green-500/20 to-emerald-500/20', text: 'from-green-400 to-emerald-400' },
            { bg: 'from-yellow-500/20 to-orange-500/20', text: 'from-yellow-400 to-orange-400' },
            { bg: 'from-red-500/20 to-pink-500/20', text: 'from-red-400 to-pink-400' },
            { bg: 'from-purple-500/20 to-violet-500/20', text: 'from-purple-400 to-violet-400' },
        ];
        
        // Simple hash function to get consistent color for same namespace
        let hash = 0;
        for (let i = 0; i < namespace.length; i++) {
            hash = ((hash << 5) - hash + namespace.charCodeAt(i)) & 0xffffffff;
        }
        return colorSets[Math.abs(hash) % colorSets.length];
    };
    
    const avatarStyle = getAvatarStyle(server.namespace);

    // Enhanced creator highlighting with distinctive colors
    const getCreatorStyle = (namespace: string) => {
        const creatorColorSets = [
            { color: 'text-indigo-300', bg: 'bg-indigo-500/10', border: 'border-indigo-500/20' },
            { color: 'text-blue-300', bg: 'bg-blue-500/10', border: 'border-blue-500/20' },
            { color: 'text-green-300', bg: 'bg-green-500/10', border: 'border-green-500/20' },
            { color: 'text-yellow-300', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20' },
            { color: 'text-red-300', bg: 'bg-red-500/10', border: 'border-red-500/20' },
            { color: 'text-purple-300', bg: 'bg-purple-500/10', border: 'border-purple-500/20' },
            { color: 'text-cyan-300', bg: 'bg-cyan-500/10', border: 'border-cyan-500/20' },
            { color: 'text-pink-300', bg: 'bg-pink-500/10', border: 'border-pink-500/20' },
            { color: 'text-orange-300', bg: 'bg-orange-500/10', border: 'border-orange-500/20' },
            { color: 'text-emerald-300', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
        ];
        
        // Use same hash function for consistency
        let hash = 0;
        for (let i = 0; i < namespace.length; i++) {
            hash = ((hash << 5) - hash + namespace.charCodeAt(i)) & 0xffffffff;
        }
        return creatorColorSets[Math.abs(hash) % creatorColorSets.length];
    };

    const creatorStyle = getCreatorStyle(server.namespace);

    return (
        <Card className={`flex flex-col h-full bg-white/5 backdrop-blur-md border-white/10 hover:border-white/20 transition-all duration-300 group hover:shadow-lg hover:shadow-white/5`}>
            <CardHeader className="pb-3 flex-row gap-4 items-start space-y-0">
                {/* Icon Placeholder */}
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${avatarStyle.bg} flex items-center justify-center border border-white/10 shrink-0 group-hover:scale-105 transition-transform`}>
                    <span className={`text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r ${avatarStyle.text}`}>
                        {initial}
                    </span>
                </div>

                <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-2 mb-1">
                        <h3 className="font-semibold text-lg text-white leading-tight" title={`${server.name} (${server.id})`}>
                            {server.name}
                        </h3>
                        {server.trust.is_official && (
                            <div className="text-blue-400 flex-shrink-0 mt-0.5" title="Official">
                                <Badge variant="secondary" className="h-5 px-1.5 bg-blue-500/10 text-blue-400 border-blue-500/20 text-[10px]">
                                    <Check className="w-3 h-3 mr-1" />
                                    OFFICIAL
                                </Badge>
                            </div>
                        )}
                    </div>
                    {/* Enhanced creator highlighting with distinctive colors */}
                    <div className="flex items-center gap-2 text-sm">
                        <span className="text-white/70">by</span>
                        <span className={`px-2 py-0.5 rounded-md font-semibold border ${creatorStyle.color} ${creatorStyle.bg} ${creatorStyle.border} transition-colors`}>
                            {server.namespace}
                        </span>
                        <span className="text-white/40">•</span>
                        <span className="text-white/50">v{server.version}</span>
                    </div>
                    {/* Show full ID for clarity */}
                    <p className="text-xs text-white/40 mt-1 font-mono truncate" title={server.id}>
                        {server.id}
                    </p>
                </div>
            </CardHeader>

            <CardContent className="flex-1 pb-4">
                <p className="text-sm text-white/70 line-clamp-2 leading-relaxed">
                    {server.description || "No description provided."}
                </p>
            </CardContent>

            <CardFooter className="pt-0 gap-2">
                {isDeployable ? (
                    <Link href={`/configure?registryId=${encodeURIComponent(server.id)}`} className="w-full">
                        <Button className="w-full bg-white/10 hover:bg-white/20 text-white border border-white/10 backdrop-blur-sm">
                            <Rocket className="w-4 h-4 mr-2" />
                            Deploy
                        </Button>
                    </Link>
                ) : (
                    <Link href={`/configure?registryId=${encodeURIComponent(server.id)}&mode=connect`} className="w-full">
                        <Button variant="outline" className="w-full border-white/10 text-white/70 hover:text-white hover:bg-white/5">
                            <LinkIcon className="w-4 h-4 mr-2" />
                            Connect
                        </Button>
                    </Link>
                )}
            </CardFooter>
        </Card>
    );
}
