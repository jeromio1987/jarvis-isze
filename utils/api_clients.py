from utils.config import ANTHROPIC_API_KEY, OPENAI_API_KEY, ISZE_CONTEXT


def ask_claude(prompt: str, system: str = None, model: str = "claude-opus-4-6") -> str:
    """
    Call Anthropic Claude and return the response text.
    Returns an error string (not raises) if the API key is missing or the call fails.
    """
    if not ANTHROPIC_API_KEY:
        return "⚠️ ANTHROPIC_API_KEY not set. Add it to your .env file."

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        messages = [{"role": "user", "content": prompt}]
        system_prompt = system or ISZE_CONTEXT

        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        return f"❌ Claude API error: {e}"


def ask_gpt(prompt: str, system: str = None, model: str = "gpt-4o") -> str:
    """
    Call OpenAI GPT and return the response text.
    Returns an error string (not raises) if the API key is missing or the call fails.
    """
    if not OPENAI_API_KEY:
        return "⚠️ OPENAI_API_KEY not set. OpenAI features are disabled."

    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        system_prompt = system or ISZE_CONTEXT

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ GPT API error: {e}"
