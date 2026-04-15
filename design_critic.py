"""
Design Critic Agent
-------------------
An opinionated AI design critic for modern design.
Submit a description, image URL, or paste design details — get a sharp critique back.

Usage:
    python design_critic.py

Set your API key first:
    set ANTHROPIC_API_KEY=sk-ant-...
"""

import os
import sys
import anthropic

SYSTEM_PROMPT = """You are a razor-sharp design critic with deep expertise in modern design — \
graphic design, UI/UX, branding, typography, spatial design, product design, and visual culture. \
You write with the authority of someone who has spent decades studying Dieter Rams, \
Jan Tschichold, Paula Scher, Massimo Vignelli, and contemporary studios like \
Pentagram, Collins, and Teenage Engineering.

Your critique style:
- Be direct, specific, and confident. No hedging, no "it depends."
- Lead with the most important observation, not a compliment.
- Call out lazy trends (glassmorphism for its own sake, gratuitous gradients, \
"brutalism" used as an excuse for poor hierarchy, Figma default shadows, etc.).
- Reference relevant design history, precedents, or principles when they sharpen the point.
- Distinguish between aesthetic preference and objective design failures \
(poor contrast, broken grid, illegible type, misaligned visual weight).
- End each critique with one concrete, actionable recommendation.
- When something genuinely works, say so — but explain precisely why.

Tone: knowledgeable and candid, like a trusted senior designer giving honest feedback \
— not cruel, but never vague or sycophantic.

Format your critiques clearly with these sections when relevant:
**First Impression** — gut reaction in one or two sentences
**What Works** — specific strengths (skip if there are none worth noting)
**What Doesn't** — the most critical issues, ordered by severity
**The Fix** — one concrete, prioritized recommendation"""


def stream_critique(client: anthropic.Anthropic, messages: list) -> str:
    """Stream a critique and return the full text."""
    full_text = ""
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=64000,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
    ) as stream:
        for event in stream:
            if event.type == "content_block_start":
                if event.content_block.type == "thinking":
                    print("\033[2m[thinking...]\033[0m", end="", flush=True)
            elif event.type == "content_block_delta":
                if event.delta.type == "thinking_delta":
                    pass  # don't print raw thinking
                elif event.delta.type == "text_delta":
                    # Clear "thinking..." indicator on first text token
                    if not full_text:
                        print("\r" + " " * 20 + "\r", end="", flush=True)
                    print(event.delta.text, end="", flush=True)
                    full_text += event.delta.text

    return full_text


def run():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.")
        print("Run:  set ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    messages = []

    print("=" * 60)
    print("  DESIGN CRITIC")
    print("  Honest feedback on modern design")
    print("=" * 60)
    print("Describe a design, paste details, or share an image URL.")
    print("Type 'quit' or 'exit' to leave.\n")

    while True:
        try:
            user_input = input("\033[1mYou:\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break

        messages.append({"role": "user", "content": user_input})

        print("\n\033[1mCritic:\033[0m ", end="", flush=True)
        try:
            reply = stream_critique(client, messages)
        except anthropic.AuthenticationError:
            print("\nError: Invalid API key. Check your ANTHROPIC_API_KEY.")
            break
        except anthropic.RateLimitError:
            print("\nRate limited — please wait a moment and try again.")
            messages.pop()  # remove the failed user turn
            continue
        except anthropic.APIConnectionError:
            print("\nNetwork error — check your connection and try again.")
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": reply})
        print("\n")


if __name__ == "__main__":
    run()
