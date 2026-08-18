import argparse
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from google import genai
import requests

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)


def parse_arguments():
    """터미널에서 --date 옵션을 입력받는 부분"""
    parser = argparse.ArgumentParser(description="국내 여행지 추천 프로그램")
    parser.add_argument("--date", required=True, help="여행 날짜 (예: 2026-03-15)")
    args = parser.parse_args()

    # 날짜 형식이 YYYY-MM-DD 인지 확인
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        print("❌ 날짜 형식이 올바르지 않습니다. 예: --date \"2026-03-15\"")
        exit(1)

    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("❌ 존재하지 않는 날짜입니다. 다시 확인해주세요.")
        exit(1)

    return args.date


def check_api_keys():
    """API 키가 설정되어 있는지 확인"""
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY가 설정되어 있지 않습니다.")
        print("   .env 파일에 GEMINI_API_KEY=발급받은키 형식으로 넣어주세요.")
        exit(1)
    if not KAKAO_REST_API_KEY:
        print("❌ KAKAO_REST_API_KEY가 설정되어 있지 않습니다.")
        print("   .env 파일에 KAKAO_REST_API_KEY=발급받은키 형식으로 넣어주세요.")
        exit(1)

def get_travel_recommendation(travel_date):
    """Gemini에게 여행 날짜를 주고 여행지 추천을 JSON으로 받아오는 함수"""

    prompt = f"""
당신은 국내 여행 전문가입니다. 아래 날짜에 여행하기 좋은 국내 지역을 추천해주세요.

여행 날짜: {travel_date}

반드시 아래 JSON 형식으로만 답변하세요. 다른 설명, 마크다운 기호(```json 등)는 절대 포함하지 마세요.

{{
  "recommended_city": "추천 도시명 (예: 제주)",
  "weather": "해당 시기 일반적인 날씨 요약 (한 문장)",
  "events": ["행사/축제 후보1", "행사/축제 후보2"],
  "reason": "추천 근거 2~4문장"
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        result_json = json.loads(response.text)
        return result_json, None
    except json.JSONDecodeError:
        try:
            retry_prompt = prompt + "\n\n반드시 유효한 JSON 형식으로만 다시 답변하세요."
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=retry_prompt,
                config={"response_mime_type": "application/json"},
            )
            result_json = json.loads(response.text)
            return result_json, None
        except Exception as e:
            return None, {"step": "llm_recommendation", "type": "JSON_PARSE_ERROR", "message": str(e)}
    except Exception as e:
        return None, {"step": "llm_recommendation", "type": "API_ERROR", "message": str(e)}

def search_restaurants(city_name):
    """Kakao Local API로 해당 도시의 맛집을 검색하는 함수"""

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
    }
    params = {
        "query": f"{city_name} 맛집",
        "category_group_code": "FD6",  # 음식점 카테고리
        "size": 5  # 5곳만 검색
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 401 or response.status_code == 403:
            return [], {"step": "place_search", "type": "AUTH_ERROR", "message": f"HTTP {response.status_code}"}

        response.raise_for_status()
        data = response.json()
        documents = data.get("documents", [])

        if len(documents) == 0:
            return [], {"step": "place_search", "type": "EMPTY_RESULT", "message": f"0 results for query={city_name} 맛집"}

        restaurants = []
        for place in documents:
            restaurants.append({
                "name": place.get("place_name", ""),
                "address": place.get("address_name", ""),
                "category": place.get("category_name", ""),
                "url": place.get("place_url", ""),
                "x": place.get("x", ""),
                "y": place.get("y", "")
            })

        return restaurants, None

    except requests.exceptions.RequestException as e:
        return [], {"step": "place_search", "type": "NETWORK_ERROR", "message": str(e)}

def generate_final_report(travel_date, recommendation, restaurants, errors):
    """1차 추천 + 맛집 목록을 합쳐서 최종 Markdown 리포트를 생성하는 함수"""

    restaurant_text = "데이터 없음"
    if restaurants:
        restaurant_lines = [f"- {r['name']} ({r['category']}) - {r['address']}" for r in restaurants]
        restaurant_text = "\n".join(restaurant_lines)

    events_text = ", ".join(recommendation.get("events", []))

    prompt = f"""
아래 정보를 바탕으로 국내 여행 리포트를 Markdown 형식으로 작성해주세요.

여행 날짜: {travel_date}
추천 지역: {recommendation['recommended_city']}
날씨: {recommendation['weather']}
행사/축제: {events_text}
추천 이유: {recommendation['reason']}

맛집 목록:
{restaurant_text}

아래 형식을 반드시 따라주세요:

# {travel_date} 국내 여행 추천 리포트
## 추천 지역
## 추천 이유
## 날씨 요약
## 행사/축제
## 맛집 추천
## 1일 일정 제안 (오전/오후/저녁)

마크다운 코드블록 기호(```)는 사용하지 말고, 순수 마크다운 텍스트만 출력하세요.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        report_text = response.text

        # 오류 요약 섹션 추가
        if errors:
            report_text += "\n\n## 오류 요약(errors)\n"
            for err in errors:
                report_text += f"- [{err['type']}] {err['step']}: {err['message']}\n"
        else:
            report_text += "\n\n## 오류 요약(errors)\n- 없음\n"

        return report_text, None
    except Exception as e:
        return None, {"step": "final_report", "type": "API_ERROR", "message": str(e)}


def save_results(travel_date, recommendation, restaurants, report_text, errors):
    """결과 데이터(JSON)와 최종 리포트(Markdown)를 results/ 폴더에 저장하는 함수"""

    os.makedirs("results", exist_ok=True)

    # 원본 데이터 JSON 저장
    data = {
        "recommendation": recommendation,
        "restaurants": restaurants,
        "errors": errors,
    }
    json_path = f"results/{travel_date}_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 최종 리포트 Markdown 저장
    report_path = f"results/{travel_date}_travel_plan.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return json_path, report_path

def main():
    check_api_keys()
    travel_date = parse_arguments()
    print(f"✅ 입력받은 날짜: {travel_date}")

    errors = []

    print("[1/3] 1차 추천 생성 중(LLM)...")
    recommendation, error = get_travel_recommendation(travel_date)

    if error:
        errors.append(error)
        print(f"   ❌ 오류 발생: {error['message']}")
        exit(1)

    print(f"   - recommended_city: \"{recommendation['recommended_city']}\"")

    print("[2/3] 맛집 검색 중(지도/장소 API)...")
    restaurants, place_error = search_restaurants(recommendation['recommended_city'])

    if place_error:
        errors.append(place_error)
        print(f"   ⚠️ {place_error['type']}: {place_error['message']}")
        print("   - 맛집 섹션은 '데이터 없음'으로 처리하고 계속 진행합니다.")
        restaurants = []
    else:
        print(f"   - 맛집 {len(restaurants)}곳 검색 완료")

    print("[3/3] 최종 리포트 생성 중(LLM)...")
    report_text, report_error = generate_final_report(travel_date, recommendation, restaurants, errors)

    if report_error:
        errors.append(report_error)
        print(f"   ❌ 오류 발생: {report_error['message']}")
        exit(1)

    print("   - 리포트 생성 완료")

    json_path, report_path = save_results(travel_date, recommendation, restaurants, report_text, errors)

    print(f"\n완료! {report_path} 를 확인하세요.")


if __name__ == "__main__":
    main()
