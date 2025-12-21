"use client"

import { useEffect, useState } from "react"
import { useSearchParams, useRouter, usePathname } from "next/navigation"
import { signIn } from "next-auth/react"
import { Github } from "lucide-react"

import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

export function SignInModal() {
    const searchParams = useSearchParams()
    const router = useRouter()
    const pathname = usePathname()
    const [isOpen, setIsOpen] = useState(false)

    useEffect(() => {
        // Check if ?signin=true is present
        if (searchParams.get("signin") === "true") {
            setIsOpen(true)
        } else {
            setIsOpen(false)
        }
    }, [searchParams])

    const handleOpenChange = (open: boolean) => {
        setIsOpen(open)
        if (!open) {
            // Remove query param when closing
            const params = new URLSearchParams(searchParams.toString())
            params.delete("signin")
            // Replace URL without push to avoid history clutter, but keep current path
            router.replace(`${pathname}?${params.toString()}`)
        }
    }

    const handleSignIn = async () => {
        await signIn("github", {
            callbackUrl: "/dashboard", // Redirect to dashboard after sign in
        })
    }

    return (
        <Dialog open={isOpen} onOpenChange={handleOpenChange}>
            <DialogContent className="sm:max-w-md bg-white/70 dark:bg-gray-900/70 backdrop-blur-md border border-white/20 dark:border-white/10 shadow-2xl">
                <DialogHeader className="space-y-4 text-center">
                    <div className="flex justify-center mb-2">
                        <div className="h-12 w-12 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center shadow-lg">
                            {/* Minimal Logo Icon */}
                            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                    </div>
                    <DialogTitle className="text-2xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-300">
                        Welcome to Catwalk
                    </DialogTitle>
                    <DialogDescription className="text-gray-500 dark:text-gray-400 text-base">
                        Sign in to manage your MCP server deployments and API keys securely.
                    </DialogDescription>
                </DialogHeader>

                <div className="py-6">
                    <Button
                        onClick={handleSignIn}
                        className="w-full h-12 text-base font-medium flex items-center justify-center gap-3 bg-[#24292F] hover:bg-[#24292F]/90 text-white dark:bg-white dark:text-[#24292F] dark:hover:bg-white/90 transition-all duration-200 shadow-md hover:shadow-lg hover:-translate-y-0.5"
                    >
                        <Github className="h-5 w-5" />
                        Continue with GitHub
                    </Button>

                    <div className="mt-4 text-center text-xs text-gray-500 dark:text-gray-500">
                        By continuing, you agree to our Terms of Service and Privacy Policy.
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    )
}
