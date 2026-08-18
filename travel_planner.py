import argparse
import json
import os
import re
from datetime import datetime

from dotenv import load_dotenv

# .env 파일에 있는 API 키들을 불러오기
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")


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


def main():
    check_api_keys()
    travel_date = parse_arguments()
    print(f"✅ 입력받은 날짜: {travel_date}")
    print(f"✅ API 키 확인 완료")


if __name__ == "__main__":
    main()