import json
from google import genai

client = genai.Client()

MODEL_NAME = "gemini-3-flash-preview"


def search_with_gemini(query: str):
    prompt = f"""
Search the web for: "{query}"

Return the top 5 most relevant web results as JSON.
For each result, include:
- title
- url
- snippet

Rules:
- Output valid JSON only.
- Use this schema:
{{
  "query": "string",
  "results": [
    {{
      "title": "string",
      "url": "string",
      "snippet": "string"
    }}
  ]
}}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={
            "tools": [{"google_search": {}}],
            "response_mime_type": "application/json",
            "response_json_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "url": {"type": "string"},
                                "snippet": {"type": "string"},
                            },
                            "required": ["title", "url", "snippet"],
                        },
                    },
                },
                "required": ["query", "results"],
            },
        },
    )

    return json.loads(response.text), response


def print_results(data):
    print(f"\nSearch query: {data['query']}\n")

    results = data.get("results", [])
    if not results:
        print("No results found.")
        return

    for i, item in enumerate(results, start=1):
        print(f"{i}. {item['title']}")
        print(f"   URL: {item['url']}")
        print(f"   Snippet: {item['snippet']}")
        print()


def print_grounding_info(response):
    try:
        metadata = response.candidates[0].grounding_metadata

        print("Grounding info:")
        if getattr(metadata, "web_search_queries", None):
            print("  Web search queries used:")
            for q in metadata.web_search_queries:
                print(f"   - {q}")

        if getattr(metadata, "grounding_chunks", None):
            print("  Sources:")
            for chunk in metadata.grounding_chunks:
                web = getattr(chunk, "web", None)
                if web:
                    print(f"   - {web.title}: {web.uri}")
        print()
    except Exception:
        print("No grounding metadata available.\n")


def main():
    query = input("Enter your search query: ").strip()

    if not query:
        print("Please enter a valid query.")
        return

    try:
        data, raw_response = search_with_gemini(query)
        print_results(data)
        print_grounding_info(raw_response)
    except Exception as e:
        print("Search request failed:", e)


if __name__ == "__main__":
    main()