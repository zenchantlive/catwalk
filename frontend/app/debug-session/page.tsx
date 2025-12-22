import { auth } from "@/auth"

export default async function DebugSessionPage() {
  const session = await auth()
  
  return (
    <div className="min-h-screen p-8 space-y-4">
      <h1 className="text-2xl font-bold text-white">Session Debug</h1>
      
      <div className="bg-white/5 p-6 rounded-lg border border-white/10">
        <h2 className="text-lg font-semibold text-white mb-4">Session Data:</h2>
        <pre className="text-sm text-gray-300 overflow-auto">
          {JSON.stringify(session, null, 2)}
        </pre>
      </div>

      <div className="bg-white/5 p-6 rounded-lg border border-white/10">
        <h2 className="text-lg font-semibold text-white mb-4">Checks:</h2>
        <ul className="space-y-2 text-sm">
          <li className="text-gray-300">
            Has session: {session ? "✅ Yes" : "❌ No"}
          </li>
          <li className="text-gray-300">
            Has user: {session?.user ? "✅ Yes" : "❌ No"}
          </li>
          <li className="text-gray-300">
            Has email: {session?.user?.email ? "✅ Yes" : "❌ No"}
          </li>
          <li className="text-gray-300">
            Has ID: {session?.user?.id ? "✅ Yes" : "❌ No"}
          </li>
          <li className="text-gray-300">
            User ID: {session?.user?.id || "❌ Missing"}
          </li>
          <li className="text-gray-300">
            Email: {session?.user?.email || "❌ Missing"}
          </li>
        </ul>
      </div>
    </div>
  )
}
