from google import genai

def main():
    client = genai.Client()

    question = input("請輸入你的問題：").strip()
    if not question:
        print("你沒有輸入問題。")
        return

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=question
    )

    print("\nGemini 回覆：")
    print(response.text)

if __name__ == "__main__":
    main()