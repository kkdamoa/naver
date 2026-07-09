"""
네이버 오픈API(지식인 검색) → 관련 질문 주제 수집 → AI로 새 글 초안 생성 → Jekyll 포스트 파일 저장

주의:
- 지식인 원문을 그대로 복사하지 않습니다. 질문 "제목/요약"만 참고해서
  완전히 새로운 글을 생성합니다. (저작권/표절 문제 방지)
- 네이버 오픈API는 공식적으로 제공되는 검색 API이며, 지식인 페이지를
  직접 크롤링하지 않으므로 이용약관 문제가 없습니다.

필요한 환경변수 (GitHub Actions Secrets로 설정):
- NAVER_CLIENT_ID
- NAVER_CLIENT_SECRET
- GEMINI_API_KEY   (Google AI Studio에서 무료 발급, 카드 불필요)
"""

import os
import re
import sys
import json
import datetime
import requests

NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")  # 무료 티어 대상 모델

KEYWORDS_FILE = "keywords.txt"
POSTS_DIR = "_posts"
STATE_FILE = "scripts/.used_keywords.json"  # 이미 처리한 키워드 기록 (중복 방지)


def read_keywords():
    if not os.path.exists(KEYWORDS_FILE):
        print(f"{KEYWORDS_FILE} 파일이 없습니다.")
        return []
    keywords = []
    with open(KEYWORDS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            keywords.append(line)
    return keywords


def load_used_keywords():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_used_keywords(used):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(used), f, ensure_ascii=False, indent=2)


def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def search_naver_kin(keyword, display=10):
    """네이버 오픈API - 지식iN 검색 (공식 API, robots/약관 문제 없음)"""
    url = "https://openapi.naver.com/v1/search/kin.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": keyword, "display": display, "sort": "sim"}
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    questions = []
    for item in items:
        questions.append({
            "title": strip_html(item.get("title", "")),
            "description": strip_html(item.get("description", "")),
        })
    return questions


def build_prompt(keyword, questions):
    q_list = "\n".join(
        f"- {q['title']}: {q['description']}" for q in questions if q["title"]
    )
    prompt = f"""아래는 '{keyword}' 관련해서 사람들이 실제로 궁금해하는 질문 주제들이야 (제목/요약만 참고용, 그대로 베끼지 말고 새로 써줘):

{q_list}

위 질문들에서 드러나는 공통 궁금증을 바탕으로, 블로그에 올릴 새로운 글을 한국어로 작성해줘.
조건:
- 특정 질문을 그대로 옮기지 말고, 주제를 종합해서 완전히 새로 작성
- 실용적이고 구체적인 정보 포함
- 제목은 검색에 잘 걸리도록 명확하게
- 마크다운 형식, 소제목(##) 활용
- 분량은 800~1200자 내외
- 결과는 아래 JSON 형식으로만 응답 (다른 텍스트 없이):
{{"title": "글 제목", "body": "마크다운 본문"}}
"""
    return prompt


def generate_article(keyword, questions):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다.")

    prompt = build_prompt(keyword, questions)
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    resp = requests.post(
        url,
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.8},
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    # 코드블록 마크다운(```json ... ```) 제거
    text = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    parsed = json.loads(text)
    return parsed["title"], parsed["body"]


def slugify(title):
    slug = re.sub(r"[^0-9a-zA-Z가-힣]+", "-", title).strip("-")
    return slug[:60] if slug else "post"


def save_jekyll_post(title, body, keyword):
    today = datetime.date.today()
    slug = slugify(title)
    filename = f"{today.isoformat()}-{slug}.md"
    filepath = os.path.join(POSTS_DIR, filename)

    front_matter = f"""---
layout: post
title: "{title.replace('"', "'")}"
date: {today.isoformat()} 09:00:00 +0900
categories: [auto]
tags: [{keyword}]
---

"""
    os.makedirs(POSTS_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(front_matter + body)
    print(f"생성됨: {filepath}")
    return filepath


def main():
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 필요합니다.")
        sys.exit(1)

    keywords = read_keywords()
    used = load_used_keywords()
    pending = [k for k in keywords if k not in used]

    if not pending:
        print("처리할 새 키워드가 없습니다. keywords.txt에 새 키워드를 추가하세요.")
        return

    # 한 번 실행에 1개 키워드만 처리 (API 호출량 조절 목적)
    keyword = pending[0]
    print(f"키워드 처리 중: {keyword}")

    questions = search_naver_kin(keyword)
    if not questions:
        print("검색 결과가 없습니다.")
        return

    title, body = generate_article(keyword, questions)
    save_jekyll_post(title, body, keyword)

    used.add(keyword)
    save_used_keywords(used)


if __name__ == "__main__":
    main()
