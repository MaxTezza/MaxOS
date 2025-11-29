import os

import anthropic
import openai


class LLMAPI:
    def __init__(self):
        self.anthropic_client: anthropic.Anthropic | None = None
        self.openai_client: openai.OpenAI | None = None

        # Initialize Anthropic client if API key is available
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)

        # Initialize OpenAI client if API key is available
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if openai_api_key:
            self.openai_client = openai.OpenAI(api_key=openai_api_key)

    async def generate_text(self, prompt: str, model: str = "claude-3-5-sonnet-20241022") -> str:
        import asyncio

        if self.anthropic_client:
            try:
                # Run synchronous Anthropic client in thread pool
                message = await asyncio.to_thread(
                    self.anthropic_client.messages.create,
                    model=model,
                    max_tokens=1024,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return message.content[0].text
            except Exception as e:
                print(f"Anthropic API error: {e}")
                # Fallback to OpenAI if Anthropic fails

        if self.openai_client:
            try:
                # Run synchronous OpenAI client in thread pool
                chat_completion = await asyncio.to_thread(
                    self.openai_client.chat.completions.create,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    model="gpt-4o"
                )
                return chat_completion.choices[0].message.content
            except Exception as e:
                print(f"OpenAI API error: {e}")

        return "No LLM client available or failed to generate response."
