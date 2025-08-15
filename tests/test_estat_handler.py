import pytest
import pandas as pd
import io
from unittest.mock import MagicMock

from src.estat_handler import fetch_and_process_population_data, YEAR_LIST

# e-Stat APIからのレスポンスを模倣したダミーデータ
# ヘッダー前の不要な行、複数カテゴリ、国全体のデータなどを含む
DUMMY_CSV_DATA_2020 = '''
"RESULT", "OK"
"METADATA", "..."

"VALUE"
"tab_code","cat01_code","area_code","time_code","unit","value","note"
"010","A1101","00000","2020100000","人","123456789",""
"010","A1101","01000","2020100000","人","5224614",""
"010","A1101","13000","2020100000","人","14047594",""
"010","A1101","99000","2020100000","人","***","ダミー注釈"
"010","A1201","13000","2020100000","人","999999","別カテゴリ"
'''

DUMMY_CSV_DATA_2015 = '''
"RESULT", "OK"
"VALUE"
"tab_code","cat01_code","area_code","time_code","unit","value","note"
"010","A1101","01000","2015100000","人","5381733",""
"010","A1101","13000","2015100000","人","13515271",""
'''

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
        # テスト対象外の年は空のデータフレームを返すようにする
        res.text = '"RESULT","OK"\n"VALUE"\n"tab_code","cat01_code","area_code","time_code","unit","value","note"'
    return res


def test_fetch_and_process_population_data(mocker):
    """
    fetch_and_process_population_data関数が、
    ダミーのAPIレスポンスを正しく処理できるかテストする
    """
    # requests.getをモックに置き換え
    mocker.patch("requests.get", side_effect=mock_requests_get)

    # テスト対象の関数を実行
    # YEAR_LISTをテスト用に短いものに差し替え
    mocker.patch("src.estat_handler.YEAR_LIST", ["2015", "2020"])
    result = fetch_and_process_population_data(app_id="dummy_app_id")

    # --- 検証 ---
    assert "2020" in result
    assert "2015" in result

    # 2020年のデータ検証
    data_2020 = result["2020"]
    assert "北海道" in data_2020
    assert data_2020["北海道"]["total_population"] == 5224614
    assert "東京都" in data_2020
    assert data_2020["東京都"]["total_population"] == 14047594
    # 欠損値(***)が0に変換されているか
    assert "不明な地域" in data_2020 # area_code 99000 は '地域' 列がないので '不明な地域' になるはず
    assert data_2020["不明な地域"]["total_population"] == 0

    # 2015年のデータ検証
    data_2015 = result["2015"]
    assert "北海道" in data_2015
    assert data_2015["北海道"]["total_population"] == 5381733

    # 不要なデータが除外されているか
    assert "全国" not in data_2020 # area_code 00000
    assert len(result["2020"]) == 3 # 北海道, 東京都, 不明な地域
    assert len(result["2015"]) == 2 # 北海道, 東京都
