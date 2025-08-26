import pytest
import pandas as pd
import io
from unittest.mock import MagicMock, patch
import datetime

from src.estat_handler import fetch_and_process_population_data

# e-Stat APIからのレスポンスを模倣したダミーデータ
# ヘッダー前の不要な行、複数カテゴリ、国全体のデータなどを含む
# 地域列を追加し、不安定なテストの原因となる99000の行を削除
DUMMY_CSV_DATA_2020 = '''
"RESULT", "OK"
"METADATA", "..."

"VALUE"
"tab_code","cat01_code","area_code","地域","time_code","unit","value","note"
"010","A1101","00000","全国","2020100000","人","123456789",""
"010","A1101","01000","北海道","2020100000","人","5224614",""
"010","A1101","13000","東京都","2020100000","人","14047594",""
"010","A1201","13000","東京都","2020100000","人","999999","別カテゴリ"
'''

DUMMY_CSV_DATA_2015 = '''
"RESULT", "OK"
"VALUE"
"tab_code","cat01_code","area_code","地域","time_code","unit","value","note"
"010","A1101","01000","北海道","2015100000","人","5381733",""
"010","A1101","13000","東京都","2015100000","人","13515271",""
'''

# 空のデータ（ヘッダーのみ）
DUMMY_EMPTY_DATA = '"RESULT","OK"\n"VALUE"\n"tab_code","cat01_code","area_code","地域","time_code","unit","value","note"'

# `requests.get`のモック関数
def mock_requests_get(*args, **kwargs):
    res = MagicMock()
    res.raise_for_status.return_value = None
    year = kwargs.get("params", {}).get("cdTime", "")[:4]
    if year == "2020":
        res.text = DUMMY_CSV_DATA_2020
    elif year == "2015":
        res.text = DUMMY_CSV_DATA_2015
    else:
        # テスト対象外の年は空のデータを返す
        res.text = DUMMY_EMPTY_DATA
    return res


@patch('src.estat_handler.datetime')
def test_fetch_and_process_population_data_dynamic(mock_dt, mocker):
    """
    動的年リスト生成ロジックが、ダミーのAPIレスポンスを正しく処理できるかテストする
    """
    # --- 準備 ---
    # 現在時刻を2021年に固定 -> 候補年は1995, 2000, 2005, 2010, 2015, 2020
    mock_dt.datetime.now.return_value = datetime.datetime(2021, 1, 1)

    # requests.getをモックに置き換え
    mocker.patch("requests.get", side_effect=mock_requests_get)

    # テスト対象の関数を実行
    result = fetch_and_process_population_data(app_id="dummy_app_id")

    # --- 検証 ---
    # 1995, 2000, 2005, 2010年は空データなので結果に含まれない
    assert "1995" not in result
    assert "2000" not in result
    assert "2005" not in result
    assert "2010" not in result
    # 2015, 2020年は含まれる
    assert "2020" in result
    assert "2015" in result

    # 2020年のデータ検証
    data_2020 = result["2020"]
    assert "北海道" in data_2020
    assert data_2020["北海道"]["total_population"] == 5224614
    assert "東京都" in data_2020
    assert data_2020["東京都"]["total_population"] == 14047594

    # 2015年のデータ検証
    data_2015 = result["2015"]
    assert "北海道" in data_2015
    assert data_2015["北海道"]["total_population"] == 5381733

    # 不要なデータが除外されているか
    assert "全国" not in data_2020 # area_code 00000
    assert len(result["2020"]) == 2 # 北海道, 東京都
    assert len(result["2015"]) == 2 # 北海道, 東京都
