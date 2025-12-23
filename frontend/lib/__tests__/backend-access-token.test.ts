import { describe, test, expect, vi, beforeEach } from 'vitest'
import { createBackendAccessToken } from '../backend-access-token'
import { SignJWT } from 'jose'

const mockSignJWTMethods = {
    setProtectedHeader: vi.fn().mockReturnThis(),
    setSubject: vi.fn().mockReturnThis(),
    setIssuer: vi.fn().mockReturnThis(),
    setAudience: vi.fn().mockReturnThis(),
    setIssuedAt: vi.fn().mockReturnThis(),
    setExpirationTime: vi.fn().mockReturnThis(),
    sign: vi.fn().mockResolvedValue('mocked-token')
}

vi.mock('jose', () => ({
    SignJWT: vi.fn().mockImplementation(() => mockSignJWTMethods)
}))

describe('backend-access-token.ts', () => {
    const mockUser = {
        id: 'user-123',
        email: 'test@example.com',
        name: 'Test User',
        image: 'https://example.com/image.jpg'
    }

    const originalEnv = { ...process.env }

    beforeEach(() => {
        vi.clearAllMocks()
        process.env = { ...originalEnv, AUTH_SECRET: 'test-secret' }
    })

    test('creates a valid backend access token', async () => {
        const token = await createBackendAccessToken(mockUser)

        expect(token).toBe('mocked-token')
        expect(SignJWT).toHaveBeenCalledWith({
            email: mockUser.email,
            name: mockUser.name,
            picture: mockUser.image
        })
    })

    test('throws error if AUTH_SECRET is missing', async () => {
        delete process.env.AUTH_SECRET
        await expect(createBackendAccessToken(mockUser)).rejects.toThrow('AUTH_SECRET is not set')
    })

    test('uses default issuer and audience if env vars not set', async () => {
        await createBackendAccessToken(mockUser)

        expect(mockSignJWTMethods.setIssuer).toHaveBeenCalledWith('catwalk-live')
        expect(mockSignJWTMethods.setAudience).toHaveBeenCalledWith('catwalk-live-backend')
    })
})
