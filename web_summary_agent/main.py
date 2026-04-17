import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("Missing GOOGLE_API_KEY in .env")

client = genai.Client(api_key=api_key)

grounding_tool = types.Tool(
    google_search=types.GoogleSearch()
)

config = types.GenerateContentConfig(
    tools=[grounding_tool],
    temperature=0.2,
)

SYSTEM_PROMPT = """
You are a concise research assistant.

Your task:
1. Read the user's question.
2. Decide whether web search is needed.
3. If the question involves recent events, current facts, changing data, or verification, use Google Search.
4. If not, answer directly.
5. Return a concise, accurate summary.
6. If search was used, mention the sources clearly when available.
"""

def ask_agent(user_question: str):
    prompt = f"{SYSTEM_PROMPT}\n\nUser question: {user_question}"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=config,
    )

    return response

def main():
    print("Web Summary Bot started. Type 'exit' to quit.\n")

    while True:
        question = input("Ask: ").strip()
        if question.lower() == "exit":
            print("Bye!")
            break

        if not question:
            print("Please enter a question.\n")
            continue

        try:
            response = ask_agent(question)
            print("\nAnswer:")
            print(response.text)

            # optional: inspect grounding metadata
            candidates = getattr(response, "candidates", None)
            if candidates:
                grounding_metadata = getattr(candidates[0], "grounding_metadata", None)
                if grounding_metadata:
                    print("\n[Search was likely used with grounding metadata available]")
        except Exception as e:
            print(f"\nError: {e}")

        print()

if __name__ == "__main__":
    main()
    