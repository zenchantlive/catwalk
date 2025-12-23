import { describe, test, expect } from 'vitest'
import { generateZodSchema, type FormField } from '../generate-zod-schema'

describe('generateZodSchema', () => {
    test('generates string validation for text fields', () => {
        const fields: FormField[] = [
            { name: 'name', label: 'Name', type: 'text', required: true }
        ]
        const schema = generateZodSchema(fields)

        expect(schema.parse({ name: 'Alice' })).toEqual({ name: 'Alice' })
        expect(() => schema.parse({ name: '' })).toThrow('Required')
    })

    test('generates optional fields', () => {
        const fields: FormField[] = [
            { name: 'bio', label: 'Bio', type: 'text', required: false }
        ]
        const schema = generateZodSchema(fields)

        expect(schema.parse({})).toEqual({})
        expect(schema.parse({ bio: 'Hello' })).toEqual({ bio: 'Hello' })
    })

    test('generates number validation', () => {
        const fields: FormField[] = [
            { name: 'age', label: 'Age', type: 'number', required: true }
        ]
        const schema = generateZodSchema(fields)

        expect(schema.parse({ age: '25' })).toEqual({ age: 25 }) // z.coerce.number() handles string coercion
        expect(() => schema.parse({ age: '0' })).toThrow('Required') // .min(1) was in original code
    })

    test('generates boolean validation for checkboxes', () => {
        const fields: FormField[] = [
            { name: 'agree', label: 'Agree', type: 'checkbox', required: true }
        ]
        const schema = generateZodSchema(fields)

        expect(schema.parse({ agree: true })).toEqual({ agree: true })
        expect(schema.parse({ agree: false })).toEqual({ agree: false })
    })

    test('generates multiple fields', () => {
        const fields: FormField[] = [
            { name: 'host', label: 'Host', type: 'text', required: true },
            { name: 'port', label: 'Port', type: 'number', required: true }
        ]
        const schema = generateZodSchema(fields)

        const valid = { host: 'localhost', port: '3000' }
        expect(schema.parse(valid)).toEqual({ host: 'localhost', port: 3000 })
    })
})
