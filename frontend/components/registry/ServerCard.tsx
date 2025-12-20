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

    // Generate avatar letter from first char of name
    const initial = server.name.charAt(0).toUpperCase();

    return (
        <Card className="flex flex-col h-full bg-white/5 backdrop-blur-md border-white/10 hover:border-white/20 transition-all duration-300 group">
            <CardHeader className="pb-3 flex-row gap-4 items-start space-y-0">
                {/* Icon Placeholder */}
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center border border-white/10 shrink-0 group-hover:scale-105 transition-transform">
                    <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
                        {initial}
                    </span>
                </div>

                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-lg text-white truncate" title={server.name}>
                            {server.name}
                        </h3>
                        {server.trust.is_official && (
                            <div className="text-blue-400" title="Official">
                                <Badge variant="secondary" className="h-5 px-1.5 bg-blue-500/10 text-blue-400 border-blue-500/20 text-[10px]">
                                    <Check className="w-3 h-3 mr-1" />
                                    OFFICIAL
                                </Badge>
                            </div>
                        )}
                    </div>
                    <p className="text-xs text-white/50 truncate">
                        {server.namespace} • v{server.version}
                    </p>
                </div>
            </CardHeader>

            <CardContent className="flex-1 pb-4">
                <p className="text-sm text-white/70 line-clamp-3 leading-relaxed">
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
