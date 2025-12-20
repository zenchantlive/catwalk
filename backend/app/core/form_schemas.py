from typing import Dict
from app.schemas.dynamic_form import FormSchema, FormField

FORM_SCHEMAS: Dict[str, FormSchema] = {
    "openai": FormSchema(
        title="Configure OpenAI",
        description="Enter your OpenAI API key to enable AI analysis features.",
        fields=[
            FormField(
                name="api_key",
                label="API Key",
                type="password",
                required=True,
                description="Starts with sk-..."
            ),
            FormField(
                name="model",
                label="Default Model",
                type="select",
                options=["gpt-4", "gpt-3.5-turbo"],
                default="gpt-4"
            )
        ]
    ),
    "anthropic": FormSchema(
        title="Configure Anthropic",
        description="Enter your Anthropic API key.",
        fields=[
            FormField(
                name="api_key",
                label="API Key",
                type="password",
                required=True,
                description="Starts with sk-ant-..."
            )
        ]
    ),
    "github": FormSchema(
        title="Configure GitHub",
        description="Connect your GitHub account.",
        fields=[
            FormField(
                name="token",
                label="Personal Access Token",
                type="password",
                required=True,
                description="GitHub PAT with repo scope"
            )
        ]
    )
}
