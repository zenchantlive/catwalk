import pytest
from app.schemas.dynamic_form import FormSchema, FormField

def test_form_schema_serialization():
    # Arrange: Create a sample form definition
    schema = FormSchema(
        title="Test Form",
        description="A form for testing",
        fields=[
            FormField(
                name="api_key",
                label="API Key",
                type="password",
                required=True,
                description="Your secret key"
            ),
            FormField(
                name="model",
                label="Model Name",
                type="select",
                options=["gpt-4", "gpt-3.5"],
                default="gpt-4"
            )
        ]
    )

    # Act: Serialize to JSON (dict)
    data = schema.model_dump()

    # Assert: Verify structure
    assert data["title"] == "Test Form"
    assert len(data["fields"]) == 2
    
    field_0 = data["fields"][0]
    assert field_0["name"] == "api_key"
    assert field_0["type"] == "password"
    assert field_0["required"] is True
    
    field_1 = data["fields"][1]
    assert field_1["name"] == "model"
    assert field_1["type"] == "select"
    assert field_1["options"] == ["gpt-4", "gpt-3.5"]
    assert field_1["default"] == "gpt-4"

def test_field_validation():
    # Test that 'select' type SHOULD generally have options (though not strictly enforced by Pydantic type, logic might/should enforce it)
    # For now, we just test basic Pydantic validation
    
    # Valid field
    field = FormField(name="test", label="Test", type="text")
    assert field.name == "test"
    
    # Missing required fields
    with pytest.raises(ValueError):
        FormField(name="test") # type and label missing
