# Phase 0: Settings & Key Management
**Duration**: 1-2 weeks
**Priority**: P0 (Blocks Vercel demo)
**Goal**: Enable users to paste their own API keys

---

## Overview

The Vercel demo requires users to provide their own infrastructure API keys:
- **Fly.io API Token** - For creating MCP server machines
- **Fly.io App Name** - Where to deploy MCP machines
- **OpenRouter API Key** - For Claude-powered repo analysis
- **Encryption Key** - For storing credentials securely

This is the CRITICAL PATH blocker. Nothing else matters until this works.

---

## User Experience Flow

### 1. First Visit (No Settings)
```
User visits catwalk-live.vercel.app
  ↓
Clicks "Create Deployment"
  ↓
Error: "Configure your API keys first"
  ↓
Redirected to /settings with banner:
  "⚠️ Add your API keys to get started"
```

### 2. Settings Configuration
```
/settings page shows:

┌────────────────────────────────────────────────┐
│ Quick Setup (Paste .env)                       │
├────────────────────────────────────────────────┤
│ FLY_API_TOKEN=fo1_xxxxx                        │
│ FLY_APP_NAME=my-catwalk-mcp                    │
│ OPENROUTER_API_KEY=sk-xxxxx                    │
│ ENCRYPTION_KEY=xxxxx                           │
│                                                │
│ [Parse .env File]                              │
└────────────────────────────────────────────────┘

OR

┌────────────────────────────────────────────────┐
│ Manual Configuration                           │
├────────────────────────────────────────────────┤
│ Fly.io API Token *                             │
│ [fo1_••••••••••••••1234] ✓ Valid               │
│ → How to get this                              │
│                                                │
│ Fly.io App Name *                              │
│ [my-catwalk-mcp] ✓ Valid                       │
│ → How to create app                            │
│                                                │
│ OpenRouter API Key *                           │
│ [sk-••••••••••••••5678] ✓ Valid                │
│ → Get API key                                  │
│                                                │
│ Encryption Key *                               │
│ [••••••••••••••••9012] [Generate New Key]      │
│ → What is this?                                │
│                                                │
│ [Save Settings]                                │
└────────────────────────────────────────────────┘
```

### 3. Validation Flow
```
User pastes .env or enters keys manually
  ↓
Clicks "Save Settings"
  ↓
Frontend validates format (not empty, correct prefix)
  ↓
Backend validates keys (API calls to Fly.io, OpenRouter)
  ↓
If valid: ✓ "Settings saved! You can now create deployments"
If invalid: ✗ "Fly.io token invalid: 401 Unauthorized"
  ↓
User sees clear error messages per field
```

---

## Implementation Checklist

### Backend (Week 1)

#### 1. Database Schema
- [x] Create `user_settings` table:
  ```sql
  CREATE TABLE user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fly_api_token TEXT NOT NULL,
    fly_app_name TEXT NOT NULL,
    openrouter_api_key TEXT NOT NULL,
    encryption_key TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
  );
  ```
- [x] For MVP: Single row with known ID (no multi-user)
- [x] Add Alembic migration

#### 2. Settings Model
- [x] Create `backend/app/models/user_settings.py`:
  ```python
  class UserSettings(Base):
      __tablename__ = "user_settings"
      
      id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, server_default=text("gen_random_uuid()"))
      fly_api_token: Mapped[str] = mapped_column(Text)
      fly_app_name: Mapped[str] = mapped_column(Text)
      openrouter_api_key: Mapped[str] = mapped_column(Text)
      encryption_key: Mapped[str] = mapped_column(Text)
      created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
      updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
  ```

#### 3. Settings Service
- [x] Create `backend/app/services/settings_service.py`:
  ```python
  class SettingsService:
      async def get_settings(self, db: AsyncSession) -> Optional[UserSettings]:
          # Return first row (single-user MVP)
          result = await db.execute(select(UserSettings).limit(1))
          return result.scalar_one_or_none()
      
      async def update_settings(self, db: AsyncSession, settings: SettingsUpdate) -> UserSettings:
          existing = await self.get_settings(db)
          if existing:
              # Update existing
              for key, value in settings.dict(exclude_unset=True).items():
                  setattr(existing, key, value)
              await db.commit()
              return existing
          else:
              # Create new
              new_settings = UserSettings(**settings.dict())
              db.add(new_settings)
              await db.commit()
              return new_settings
      
      async def validate_fly_token(self, token: str, app_name: str) -> Dict[str, Any]:
          # Call Fly.io API to verify token and app exists
          url = f"https://api.machines.dev/v1/apps/{app_name}"
          headers = {"Authorization": f"Bearer {token}"}
          async with httpx.AsyncClient() as client:
              response = await client.get(url, headers=headers)
              if response.status_code == 200:
                  return {"valid": True, "error": None}
              elif response.status_code == 401:
                  return {"valid": False, "error": "Invalid Fly.io API token"}
              elif response.status_code == 404:
                  return {"valid": False, "error": f"Fly app '{app_name}' not found"}
              else:
                  return {"valid": False, "error": f"Fly API error: {response.status_code}"}
      
      async def validate_openrouter_key(self, api_key: str) -> Dict[str, Any]:
          # Test OpenRouter API key
          url = "https://openrouter.ai/api/v1/models"
          headers = {"Authorization": f"Bearer {api_key}"}
          async with httpx.AsyncClient() as client:
              response = await client.get(url, headers=headers)
              if response.status_code == 200:
                  return {"valid": True, "error": None}
              elif response.status_code == 401:
                  return {"valid": False, "error": "Invalid OpenRouter API key"}
              else:
                  return {"valid": False, "error": f"OpenRouter API error: {response.status_code}"}
      
      def validate_encryption_key(self, key: str) -> Dict[str, Any]:
          # Check Fernet key format
          try:
              from cryptography.fernet import Fernet
              Fernet(key.encode())
              return {"valid": True, "error": None}
          except Exception as e:
              return {"valid": False, "error": f"Invalid encryption key format: {str(e)}"}
  ```

#### 4. Settings API
- [x] Create `backend/app/api/settings.py`:
  ```python
  from fastapi import APIRouter, Depends, HTTPException
  from sqlalchemy.ext.asyncio import AsyncSession
  from app.services.settings_service import SettingsService
  from app.schemas.settings import SettingsResponse, SettingsUpdate, ValidationRequest
  
  router = APIRouter(prefix="/api/settings", tags=["settings"])
  
  @router.get("/", response_model=SettingsResponse)
  async def get_settings(
      db: AsyncSession = Depends(get_db),
      service: SettingsService = Depends()
  ):
      settings = await service.get_settings(db)
      if not settings:
          raise HTTPException(404, "Settings not configured")
      
      # Mask secrets (show last 4 chars only)
      return {
          "fly_api_token": mask_secret(settings.fly_api_token),
          "fly_app_name": settings.fly_app_name,
          "openrouter_api_key": mask_secret(settings.openrouter_api_key),
          "encryption_key": mask_secret(settings.encryption_key),
          "configured": True
      }
  
  @router.post("/", response_model=SettingsResponse)
  async def update_settings(
      update: SettingsUpdate,
      db: AsyncSession = Depends(get_db),
      service: SettingsService = Depends()
  ):
      # Validate all keys
      fly_valid = await service.validate_fly_token(update.fly_api_token, update.fly_app_name)
      if not fly_valid["valid"]:
          raise HTTPException(400, {"field": "fly_api_token", "error": fly_valid["error"]})
      
      openrouter_valid = await service.validate_openrouter_key(update.openrouter_api_key)
      if not openrouter_valid["valid"]:
          raise HTTPException(400, {"field": "openrouter_api_key", "error": openrouter_valid["error"]})
      
      encryption_valid = service.validate_encryption_key(update.encryption_key)
      if not encryption_valid["valid"]:
          raise HTTPException(400, {"field": "encryption_key", "error": encryption_valid["error"]})
      
      # Save settings
      settings = await service.update_settings(db, update)
      return {"configured": True, "message": "Settings saved successfully"}
  
  @router.post("/validate", response_model=ValidationResponse)
  async def validate_keys(
      request: ValidationRequest,
      service: SettingsService = Depends()
  ):
      # Validate individual key without saving
      if request.field == "fly_api_token":
          result = await service.validate_fly_token(request.value, request.fly_app_name)
      elif request.field == "openrouter_api_key":
          result = await service.validate_openrouter_key(request.value)
      elif request.field == "encryption_key":
          result = service.validate_encryption_key(request.value)
      else:
          raise HTTPException(400, "Invalid field")
      
      return result
  
  @router.post("/generate-key", response_model=GenerateKeyResponse)
  async def generate_encryption_key():
      from cryptography.fernet import Fernet
      key = Fernet.generate_key().decode()
      return {"encryption_key": key}
  
  def mask_secret(secret: str) -> str:
      if len(secret) <= 4:
          return "••••"
      return "••••" + secret[-4:]
  ```

#### 5. Schemas
- [x] Create `backend/app/schemas/settings.py`:
  ```python
  from pydantic import BaseModel, Field
  
  class SettingsUpdate(BaseModel):
      fly_api_token: str = Field(..., min_length=1)
      fly_app_name: str = Field(..., min_length=1)
      openrouter_api_key: str = Field(..., min_length=1)
      encryption_key: str = Field(..., min_length=1)
  
  class SettingsResponse(BaseModel):
      fly_api_token: str
      fly_app_name: str
      openrouter_api_key: str
      encryption_key: str
      configured: bool
  
  class ValidationRequest(BaseModel):
      field: str
      value: str
      fly_app_name: Optional[str] = None
  
  class ValidationResponse(BaseModel):
      valid: bool
      error: Optional[str] = None
  
  class GenerateKeyResponse(BaseModel):
      encryption_key: str
  ```

#### 6. Integration with Deployment Flow
- [x] Update `backend/app/api/deployments.py`:
  ```python
  @router.post("/")
  async def create_deployment(
      deployment: DeploymentCreate,
      db: AsyncSession = Depends(get_db)
  ):
      # Check settings exist
      settings = await SettingsService().get_settings(db)
      if not settings:
          raise HTTPException(400, {
              "error": "settings_not_configured",
              "message": "Configure your API keys in Settings first",
              "redirect": "/settings"
          })
      
      # Use user-provided keys
      fly_service = FlyDeploymentService(
          api_token=settings.fly_api_token,
          app_name=settings.fly_app_name
      )
      
      # ... rest of deployment logic
  ```

#### 7. Tests
- [x] Create `backend/tests/test_settings.py`:
  - Test get settings (empty, existing)
  - Test update settings
  - Test validate Fly token (valid, invalid, wrong app)
  - Test validate OpenRouter key
  - Test validate encryption key
  - Test generate encryption key

---

### Frontend (Week 2)

#### 1. Settings Page
- [x] Create `frontend/app/settings/page.tsx`:
  ```typescript
  "use client";
  
  import { useState } from "react";
  import { getSettings, updateSettings, validateKey, generateEncryptionKey } from "@/lib/api";
  
  export default function SettingsPage() {
    const [mode, setMode] = useState<"paste" | "manual">("paste");
    const [envText, setEnvText] = useState("");
    const [settings, setSettings] = useState({
      fly_api_token: "",
      fly_app_name: "",
      openrouter_api_key: "",
      encryption_key: ""
    });
    const [validation, setValidation] = useState<Record<string, { valid: boolean, error?: string }>>({});
    
    const handlePasteEnv = () => {
      // Parse .env format
      const lines = envText.split("\n");
      const parsed: Record<string, string> = {};
      
      for (const line of lines) {
        const [key, value] = line.split("=");
        if (key && value) {
          parsed[key.trim()] = value.trim();
        }
      }
      
      setSettings({
        fly_api_token: parsed.FLY_API_TOKEN || "",
        fly_app_name: parsed.FLY_APP_NAME || "",
        openrouter_api_key: parsed.OPENROUTER_API_KEY || "",
        encryption_key: parsed.ENCRYPTION_KEY || ""
      });
      
      setMode("manual");
    };
    
    const handleGenerateKey = async () => {
      const { encryption_key } = await generateEncryptionKey();
      setSettings({ ...settings, encryption_key });
    };
    
    const handleValidate = async (field: string) => {
      const result = await validateKey(field, settings[field], settings.fly_app_name);
      setValidation({ ...validation, [field]: result });
    };
    
    const handleSave = async () => {
      try {
        await updateSettings(settings);
        alert("Settings saved!");
      } catch (error) {
        alert("Error saving settings: " + error.message);
      }
    };
    
    return (
      <div className="max-w-2xl mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">Settings</h1>
        
        {mode === "paste" ? (
          <div>
            <h2 className="text-lg font-semibold mb-2">Quick Setup</h2>
            <p className="text-gray-600 mb-4">Paste your .env file:</p>
            <textarea
              value={envText}
              onChange={(e) => setEnvText(e.target.value)}
              className="w-full h-32 p-3 border rounded font-mono text-sm"
              placeholder={`FLY_API_TOKEN=fo1_xxxxx\nFLY_APP_NAME=my-catwalk-mcp\nOPENROUTER_API_KEY=sk-xxxxx\nENCRYPTION_KEY=xxxxx`}
            />
            <button onClick={handlePasteEnv} className="btn mt-2">
              Parse .env File
            </button>
            <div className="mt-4 text-center">
              <button onClick={() => setMode("manual")} className="text-blue-600">
                Or configure manually →
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block font-medium mb-1">
                Fly.io API Token *
                <a href="https://fly.io/user/personal_access_tokens" target="_blank" className="text-blue-600 text-sm ml-2">
                  → Get token
                </a>
              </label>
              <input
                type="password"
                value={settings.fly_api_token}
                onChange={(e) => setSettings({ ...settings, fly_api_token: e.target.value })}
                onBlur={() => handleValidate("fly_api_token")}
                className="w-full p-2 border rounded"
              />
              {validation.fly_api_token && (
                <div className={validation.fly_api_token.valid ? "text-green-600" : "text-red-600"}>
                  {validation.fly_api_token.valid ? "✓ Valid" : `✗ ${validation.fly_api_token.error}`}
                </div>
              )}
            </div>
            
            <div>
              <label className="block font-medium mb-1">
                Fly.io App Name *
                <a href="https://fly.io/docs/apps/create/" target="_blank" className="text-blue-600 text-sm ml-2">
                  → Create app
                </a>
              </label>
              <input
                type="text"
                value={settings.fly_app_name}
                onChange={(e) => setSettings({ ...settings, fly_app_name: e.target.value })}
                className="w-full p-2 border rounded"
                placeholder="my-catwalk-mcp"
              />
            </div>
            
            <div>
              <label className="block font-medium mb-1">
                OpenRouter API Key *
                <a href="https://openrouter.ai/keys" target="_blank" className="text-blue-600 text-sm ml-2">
                  → Get key
                </a>
              </label>
              <input
                type="password"
                value={settings.openrouter_api_key}
                onChange={(e) => setSettings({ ...settings, openrouter_api_key: e.target.value })}
                onBlur={() => handleValidate("openrouter_api_key")}
                className="w-full p-2 border rounded"
              />
              {validation.openrouter_api_key && (
                <div className={validation.openrouter_api_key.valid ? "text-green-600" : "text-red-600"}>
                  {validation.openrouter_api_key.valid ? "✓ Valid" : `✗ ${validation.openrouter_api_key.error}`}
                </div>
              )}
            </div>
            
            <div>
              <label className="block font-medium mb-1">
                Encryption Key *
                <span className="text-gray-500 text-sm ml-2">(for storing credentials)</span>
              </label>
              <div className="flex gap-2">
                <input
                  type="password"
                  value={settings.encryption_key}
                  onChange={(e) => setSettings({ ...settings, encryption_key: e.target.value })}
                  className="flex-1 p-2 border rounded"
                />
                <button onClick={handleGenerateKey} className="btn-secondary">
                  Generate New Key
                </button>
              </div>
            </div>
            
            <button onClick={handleSave} className="btn w-full">
              Save Settings
            </button>
          </div>
        )}
      </div>
    );
  }
  ```

#### 2. API Client Updates
- [x] Update `frontend/lib/api.ts`:
  ```typescript
  export async function getSettings(): Promise<SettingsResponse> {
    const res = await fetch("/api/settings");
    if (!res.ok) throw new Error("Failed to fetch settings");
    return res.json();
  }
  
  export async function updateSettings(settings: SettingsUpdate): Promise<void> {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings)
    });
    if (!res.ok) throw new Error("Failed to update settings");
  }
  
  export async function validateKey(field: string, value: string, flyAppName?: string): Promise<ValidationResponse> {
    const res = await fetch("/api/settings/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ field, value, fly_app_name: flyAppName })
    });
    return res.json();
  }
  
  export async function generateEncryptionKey(): Promise<{ encryption_key: string }> {
    const res = await fetch("/api/settings/generate-key", { method: "POST" });
    return res.json();
  }
  ```

#### 3. Settings Guard
- [x] Create `frontend/lib/useSettings.ts`:
  ```typescript
  import { useQuery } from "@tanstack/react-query";
  import { getSettings } from "./api";
  
  export function useSettings() {
    return useQuery({
      queryKey: ["settings"],
      queryFn: getSettings,
      retry: false
    });
  }
  
  export function useRequireSettings() {
    const { data, isLoading, error } = useSettings();
    
    if (error || (!isLoading && !data?.configured)) {
      return { configured: false, redirect: "/settings" };
    }
    
    return { configured: true };
  }
  ```

#### 4. Deployment Page Guard
- [x] Update `frontend/app/configure/page.tsx`:
  ```typescript
  import { useRequireSettings } from "@/lib/useSettings";
  
  export default function ConfigurePage() {
    const { configured, redirect } = useRequireSettings();
    
    if (!configured) {
      return (
        <div className="p-6">
          <div className="bg-yellow-50 border border-yellow-200 rounded p-4">
            <h3 className="font-semibold mb-2">⚠️ Settings Required</h3>
            <p>Configure your API keys before creating deployments.</p>
            <a href="/settings" className="btn mt-4 inline-block">
              Go to Settings →
            </a>
          </div>
        </div>
      );
    }
    
    // ... rest of deployment form
  }
  ```

---

## Testing Checklist

### Backend Tests
- [x] Test settings CRUD (create, read, update)
- [x] Test Fly token validation (valid, invalid, wrong app)
- [x] Test OpenRouter key validation
- [x] Test encryption key validation (valid Fernet, invalid format)
- [x] Test encryption key generation
- [x] Test deployment creation blocks if settings missing

### Frontend Tests
- [x] Test .env paste parsing
- [x] Test manual key entry
- [x] Test validation feedback (green checkmark, red error)
- [x] Test "Generate Key" button
- [x] Test save flow
- [x] Test deployment guard (redirects to settings if not configured)

### End-to-End Tests
1. Fresh install (no settings)
   - Try to create deployment → Error + redirect
   - Go to /settings
   - Paste .env → Fields populated
   - Save → Success
   - Create deployment → Works

2. Invalid keys
   - Enter invalid Fly token → Red error
   - Enter valid token → Green checkmark
   - Save with one invalid → Error message

3. Generate encryption key
   - Click "Generate" → Key appears
   - Save settings → Works
   - Use in deployment → Credentials encrypt correctly

---

## Documentation Needs

### 1. Settings Page Help Text
- [x] Fly.io token: How to create, what permissions needed
- [x] Fly.io app: How to create app, naming conventions
- [x] OpenRouter: Why needed, how to get free credits
- [x] Encryption key: What it's for, why random is important

### 2. Vercel Demo Setup Guide
- [x] Prerequisites section
- [x] Step-by-step Fly.io setup
- [x] Step-by-step OpenRouter setup
- [x] Screenshot guide
- [x] Troubleshooting FAQ

### 3. Self-Hosting Guide Update
- [x] Environment variables section
- [x] How to set in Vercel
- [x] How to set in Docker
- [x] How to set in Fly.io (backend deployment)

---

## Success Criteria

### Must-Have
- ✅ Users can paste .env file
- ✅ Users can enter keys manually
- ✅ Keys validated before saving
- ✅ Deployment creation blocked if settings missing
- ✅ Clear error messages per field
- ✅ Help text links to docs

### Nice-to-Have
- Settings export (download .env)
- Settings reset (clear all)
- Key rotation warning (if >90 days old)
- Usage tracking (API call counts)

---

## Deployment Plan

### Week 1: Backend
1. Day 1-2: Schema + models + migration
2. Day 3-4: Service + API endpoints
3. Day 5: Tests + deployment integration

### Week 2: Frontend
1. Day 1-2: Settings page UI
2. Day 3: .env parser + validation
3. Day 4: Deployment guard + error handling
4. Day 5: End-to-end testing

### Week 3 (Buffer): Polish
- Documentation
- Video walkthrough
- Help text refinement
- Edge case handling

---

## Risk Mitigation

### Risk: Fly.io API rate limits during validation
**Mitigation**: Cache validation results for 5 minutes

### Risk: Users don't understand what keys to get
**Mitigation**: Video tutorial + step-by-step guide with screenshots

### Risk: .env parsing breaks on complex formats
**Mitigation**: Support both `KEY=value` and `KEY="value"` formats

### Risk: Encryption key format confusing
**Mitigation**: "Generate Key" button + clear explanation

---

## Next Steps After Phase 0

Once settings work:
1. Test end-to-end deployment flow
2. Deploy to Vercel (backend stays on Fly.io)
3. Private beta with 5-10 users
4. Fix critical bugs
5. Public launch (HN, Reddit, Twitter)

Phase 0 is THE blocker. Everything else can wait.
