import argparse
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from google import genai

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

def main():
    check_api_keys()
    travel_date = parse_arguments()
    print(f"✅ 입력받은 날짜: {travel_date}")
    print(f"✅ API 키 확인 완료")

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
    print(f"   - weather: {recommendation['weather']}")
    print(f"   - reason: {recommendation['reason']}")


if __name__ == "__main__":
    main()