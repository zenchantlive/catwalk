import * as z from "zod";

export interface FormField {
    name: string;
    label: string;
    type: "text" | "password" | "select" | "number" | "checkbox";
    required: boolean;
    default?: string | number | boolean;
    options?: string[];
    description?: string;
}

export interface FormSchema {
    title: string;
    description: string;
    fields: FormField[];
    mcp_config?: Record<string, unknown>;
}

export const generateZodSchema = (fields: FormField[]) => {
    const shape: Record<string, z.ZodTypeAny> = {};

    fields.forEach((field) => {
        let validator: z.ZodTypeAny;

        switch (field.type) {
            case "number":
                validator = z.coerce.number();
                if (field.required) {
                    validator = (validator as z.ZodNumber).min(1, "Required");
                }
                break;
            case "checkbox":
                validator = z.boolean();
                break;
            default:
                validator = z.string();
                if (field.required) {
                    validator = (validator as z.ZodString).min(1, "Required");
                }
        }

        if (!field.required) {
            validator = validator.optional();
        }

        shape[field.name] = validator;
    });

    return z.object(shape);
};
