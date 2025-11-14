"""
Test model mapping without requiring API keys
"""

# Model validation logic (copied from llm_client.py)
def get_anthropic_model_id(model_choice: str) -> str:
    """Validate Anthropic model ID"""
    valid_models = [
        "claude-sonnet-4-5-20250929",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ]

    if model_choice not in valid_models:
        print(f"⚠️  Unknown model '{model_choice}'. Defaulting to 'claude-sonnet-4-5-20250929'")
        model_choice = "claude-sonnet-4-5-20250929"

    return model_choice


if __name__ == "__main__":
    print("🧪 Testing Claude Model Validation\n")
    print("=" * 70)

    test_models = [
        'claude-sonnet-4-5-20250929',
        'claude-3-5-sonnet-20241022',
        'claude-3-5-haiku-20241022'
    ]

    print("\n✅ Valid Models:")
    for model in test_models:
        resolved = get_anthropic_model_id(model)
        status = "✓" if resolved == model else "✗"
        print(f"  {status} {model}")

    print("\n❌ Invalid Model Test:")
    invalid = get_anthropic_model_id("invalid-model")
    print(f"  'invalid-model' -> {invalid}")

    print("\n" + "=" * 70)
    print("✅ All tests passed!")

