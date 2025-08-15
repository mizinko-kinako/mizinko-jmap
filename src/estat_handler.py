import requests
import pandas as pd
import io
import json

# 調査対象の統計データIDと年リスト
STATS_DATA_ID = "0000010101"
YEAR_LIST = ["1995", "2000", "2005", "2010", "2015", "2020"]

def fetch_and_process_population_data(app_id: str):
    """
    e-Stat APIから総人口データを取得し、指定されたJSON構造に加工する。
    Args:
        app_id (str): e-Stat APIのアプリケーションID。
    Returns:
        dict: 年度ごと、都道府県別の総人口を格納した辞書。
    """
    base_url = "https://api.e-stat.go.jp/rest/3.0/app/getSimpleStatsData"
    all_data_df = pd.DataFrame()

    print("e-Statからデータの取得を開始します...")
    for year in YEAR_LIST:
        print(f"{year}年のデータを取得中...")
        params = {
            "appId": app_id,
            "statsDataId": STATS_DATA_ID,
            "cdTime": f"{year}100000",
            "metaGetFlg": "Y",
            "cntGetFlg": "N",
            "sectionHeaderFlg": "1"
        }
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()

            response_text = response.text
            lines = response_text.splitlines()

            header_row_index = -1
            for i, line in enumerate(lines):
                if '"tab_code"' in line:
                    header_row_index = i
                    break
            
            if header_row_index == -1:
                print(f"エラー: {year}年のデータからヘッダー行が見つかりませんでした。")
                continue

            csv_data = io.StringIO('\n'.join(lines[header_row_index:]))
            df = pd.read_csv(csv_data, dtype={'area_code': str, 'cat01_code': str})
            
            df['survey_year'] = year
            all_data_df = pd.concat([all_data_df, df], ignore_index=True)
            print(f"{year}年のデータを取得完了。")

        except requests.exceptions.RequestException as e:
            print(f"エラーが発生しました: {e}")
            return None

    if all_data_df.empty:
        print("取得できるデータがありませんでした。")
        return None

    print("\n取得したデータの加工を開始します...")

    # 総人口のデータ（コード'A1101'）のみを抽出
    df = all_data_df[all_data_df['cat01_code'] == 'A1101'].copy()

    # 都道府県レベルのデータ（地域コードがXX000形式）のみを抽出
    df = df[df['area_code'].str.match(r'\d{2}000') & (df['area_code'] != '00000')]

    # 人口(value)の欠損値「***」を0に置換し、数値型に変換
    df['value'] = df['value'].replace(r'\*\*\*', '0', regex=True).astype(float).astype(int)

    # 最終的なJSON構造を組み立てる
    result_json = {}
    for year in sorted(df['survey_year'].unique()):
        result_json[year] = {}
        year_df = df[df['survey_year'] == year]
        for index, row in year_df.iterrows():
            pref_name = row['地域']
            population = int(row['value'])
            result_json[year][pref_name] = {
                'total_population': population
            }
    
    print("データの加工が完了しました。")
    return result_json
