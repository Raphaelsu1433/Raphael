import requests
import json
import time
import os
from datetime import datetime

FACTS_FILE = "facts.json"
API_URL = "https://uselessfacts.jsph.pl/api/v2/facts/random"


def load_facts():
    """讀取本地 fact.json，如果檔案不存在就回傳空列表"""
    if not os.path.exists(FACTS_FILE):
        return []

    try:
        with open(FACTS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_facts(facts):
    """把 facts 寫回 fact.json"""
    with open(FACTS_FILE, "w", encoding="utf-8") as file:
        json.dump(facts, file, ensure_ascii=False, indent=4)


def fetch_fact():
    """從 API 抓一則 fact"""
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("text")
    except requests.RequestException as e:
        print("抓取失敗：", e)
        return None


def is_duplicate(new_fact, facts):
    """檢查 fact 是否已存在"""
    for fact in facts:
        if fact.get("text") == new_fact:
            return True
    return False


def add_fact(new_fact):
    """加入新 fact，如果重複就不加入"""
    if not new_fact:
        return

    facts = load_facts()

    if is_duplicate(new_fact, facts):
        print("這筆 fact 已存在，跳過：")
        print(new_fact)
        return

    facts.append({
        "text": new_fact,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    save_facts(facts)
    print("已新增新 fact：")
    print(new_fact)


def main():
    """每隔一段時間自動抓取一次"""
    interval_seconds = 60  # 每 60 秒抓一次，可自行修改

    print("開始自動收集 facts...")
    while True:
        fact = fetch_fact()
        add_fact(fact)
        print(f"{interval_seconds} 秒後再次抓取...\n")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()