
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useState } from "react";
import { Loader2, Eye, EyeOff } from "lucide-react";
import clsx from "clsx";

// Types corresponding to our backend schema
interface FormField {
    name: string;
    label: string;
    type: "text" | "password" | "select" | "number" | "checkbox";
    required: boolean;
    default?: string | number | boolean;
    options?: string[];
    description?: string;
}

interface FormSchema {
    title: string;
    description: string;
    fields: FormField[];
}

interface FormBuilderProps {
    schema: FormSchema;
    onSubmit: (data: Record<string, unknown>) => Promise<void>;
    isLoading?: boolean;
}

export default function FormBuilder({ schema, onSubmit, isLoading }: FormBuilderProps) {
    const [showPassword, setShowPassword] = useState<Record<string, boolean>>({});

    // Dynamically generate Zod schema based on props
    const generateZodSchema = (fields: FormField[]) => {
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

    const zodSchema = generateZodSchema(schema.fields);
    type FormData = z.infer<typeof zodSchema>;

    const {
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<FormData>({
        resolver: zodResolver(zodSchema),
        defaultValues: schema.fields.reduce((acc, field) => {
            if (field.default !== undefined) acc[field.name] = field.default;
            return acc;
        }, {} as Record<string, unknown>),
    });

    const togglePassword = (fieldName: string) => {
        setShowPassword((prev) => ({ ...prev, [fieldName]: !prev[fieldName] }));
    };

    return (
        <div className="card-glass p-6 md:p-8 w-full max-w-lg mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h2 className="text-2xl font-semibold mb-2 text-gradient">{schema.title}</h2>
            <p className="text-[var(--pk-text-secondary)] mb-6 text-sm">{schema.description}</p>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                {schema.fields.map((field) => (
                    <div key={field.name} className="space-y-1.5">
                        <label htmlFor={field.name} className="block text-sm font-medium text-[var(--pk-text-secondary)]">
                            {field.label} {field.required && <span className="text-[var(--pk-status-red)]">*</span>}
                        </label>

                        <div className="relative">
                            {field.type === "select" ? (
                                <div className="relative">
                                    <select
                                        {...register(field.name)}
                                        id={field.name}
                                        className="input-aurora appearance-none cursor-pointer"
                                    >
                                        {field.options?.map((opt) => (
                                            <option key={opt} value={opt}>
                                                {opt}
                                            </option>
                                        ))}
                                    </select>
                                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-[var(--pk-text-secondary)]">
                                        <svg className="h-4 w-4 fill-current" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" /></svg>
                                    </div>
                                </div>
                            ) : (
                                <div className="relative">
                                    <input
                                        {...register(field.name)}
                                        id={field.name}
                                        type={
                                            field.type === "password"
                                                ? showPassword[field.name]
                                                    ? "text"
                                                    : "password"
                                                : field.type
                                        }
                                        className={clsx("input-aurora pr-10", errors[field.name] && "ring-1 ring-[var(--pk-status-red)] focus:ring-[var(--pk-status-red)]")}
                                    />

                                    {field.type === "password" && (
                                        <button
                                            type="button"
                                            onClick={() => togglePassword(field.name)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--pk-text-secondary)] hover:text-white transition-colors"
                                        >
                                            {showPassword[field.name] ? <EyeOff size={18} /> : <Eye size={18} />}
                                        </button>
                                    )}
                                </div>
                            )}
                        </div>

                        {field.description && <p className="text-xs text-[var(--pk-text-secondary)]/70">{field.description}</p>}
                        {errors[field.name] && (
                            <p className="text-xs text-[var(--pk-status-red)] mt-1 animate-in slide-in-from-top-1">
                                {errors[field.name]?.message as string}
                            </p>
                        )}
                    </div>
                ))}

                <button
                    type="submit"
                    disabled={isLoading}
                    className="btn-aurora w-full mt-2 flex items-center justify-center gap-2"
                >
                    {isLoading && <Loader2 className="animate-spin" size={18} />}
                    {isLoading ? "Saving..." : "Save Configuration"}
                </button>
            </form>
        </div>
    );
}
