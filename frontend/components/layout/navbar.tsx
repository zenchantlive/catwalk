"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useSession, signOut } from "next-auth/react"
import { Menu, X, Settings, LogOut, User } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function Navbar() {
  const { data: session, status } = useSession()
  const pathname = usePathname()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const isActive = (path: string) => pathname === path

  const handleSignOut = async () => {
    await signOut({ callbackUrl: "/" })
  }

  const navLinks = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/configure", label: "Deploy" },
  ]

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-white/10 bg-[var(--pk-bg-deep)]/95 backdrop-blur-xl">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center space-x-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-[var(--pk-accent-primary-from)] to-[var(--pk-accent-primary-to)] p-[2px]">
                <div className="flex h-full w-full items-center justify-center rounded-lg bg-[var(--pk-bg-deep)]">
                  <span className="text-lg font-bold text-gradient">C</span>
                </div>
              </div>
              <span className="text-xl font-bold text-gradient">Catwalk Live</span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          {status === "authenticated" && (
            <div className="hidden md:flex md:items-center md:space-x-1">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                    isActive(link.href)
                      ? "bg-white/10 text-white"
                      : "text-[var(--pk-text-secondary)] hover:bg-white/5 hover:text-white"
                  )}
                >
                  {link.label}
                </Link>
              ))}
            </div>
          )}

          {/* Right Section */}
          <div className="flex items-center space-x-4">
            {status === "loading" ? (
              <div className="h-8 w-8 animate-pulse rounded-full bg-white/10" />
            ) : status === "authenticated" && session?.user ? (
              <>
                {/* Desktop User Menu */}
                <div className="hidden md:block">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        className="flex items-center space-x-2 rounded-lg px-3 py-2 hover:bg-white/10"
                      >
                        {session.user.image ? (
                          <img
                            src={session.user.image}
                            alt={session.user.name || "User"}
                            className="h-8 w-8 rounded-full border-2 border-white/10"
                          />
                        ) : (
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-[var(--pk-accent-primary-from)] to-[var(--pk-accent-primary-to)]">
                            <User className="h-4 w-4 text-white" />
                          </div>
                        )}
                        <span className="text-sm font-medium text-[var(--pk-text-primary)]">
                          {session.user.name || session.user.email}
                        </span>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                      <DropdownMenuLabel className="font-normal">
                        <div className="flex flex-col space-y-1">
                          <p className="text-sm font-medium text-[var(--pk-text-primary)]">
                            {session.user.name}
                          </p>
                          <p className="text-xs text-[var(--pk-text-secondary)]">
                            {session.user.email}
                          </p>
                        </div>
                      </DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem asChild>
                        <Link href="/settings" className="flex items-center cursor-pointer">
                          <Settings className="mr-2 h-4 w-4" />
                          <span>Settings</span>
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={handleSignOut}
                        className="cursor-pointer text-[var(--pk-status-red)] focus:text-[var(--pk-status-red)]"
                      >
                        <LogOut className="mr-2 h-4 w-4" />
                        <span>Sign Out</span>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                {/* Mobile Menu Button */}
                <button
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                  className="md:hidden rounded-lg p-2 text-[var(--pk-text-secondary)] hover:bg-white/10 hover:text-white transition-colors"
                >
                  {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
                </button>
              </>
            ) : (
              <Link
                href="/?signin=true"
                className="btn-aurora px-4 py-2 text-sm rounded-lg"
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {status === "authenticated" && session?.user && mobileMenuOpen && (
        <div className="md:hidden border-t border-white/10 bg-[var(--pk-bg-deep)]">
          <div className="space-y-1 px-4 pb-3 pt-2">
            {/* User Info */}
            <div className="flex items-center space-x-3 rounded-lg bg-white/5 p-3 mb-3">
              {session.user.image ? (
                <img
                  src={session.user.image}
                  alt={session.user.name || "User"}
                  className="h-10 w-10 rounded-full border-2 border-white/10"
                />
              ) : (
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-[var(--pk-accent-primary-from)] to-[var(--pk-accent-primary-to)]">
                  <User className="h-5 w-5 text-white" />
                </div>
              )}
              <div className="flex flex-col">
                <p className="text-sm font-medium text-[var(--pk-text-primary)]">
                  {session.user.name}
                </p>
                <p className="text-xs text-[var(--pk-text-secondary)]">
                  {session.user.email}
                </p>
              </div>
            </div>

            {/* Navigation Links */}
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  "block rounded-lg px-4 py-3 text-base font-medium transition-colors",
                  isActive(link.href)
                    ? "bg-white/10 text-white"
                    : "text-[var(--pk-text-secondary)] hover:bg-white/5 hover:text-white"
                )}
              >
                {link.label}
              </Link>
            ))}

            {/* Settings */}
            <Link
              href="/settings"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center rounded-lg px-4 py-3 text-base font-medium text-[var(--pk-text-secondary)] hover:bg-white/5 hover:text-white transition-colors"
            >
              <Settings className="mr-3 h-5 w-5" />
              <span>Settings</span>
            </Link>

            {/* Sign Out */}
            <button
              onClick={() => {
                setMobileMenuOpen(false)
                handleSignOut()
              }}
              className="flex w-full items-center rounded-lg px-4 py-3 text-base font-medium text-[var(--pk-status-red)] hover:bg-white/5 transition-colors"
            >
              <LogOut className="mr-3 h-5 w-5" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      )}
    </nav>
  )
}
