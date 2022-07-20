import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS

import requests
import json
import FinanceDataReader as fdr
from bs4 import BeautifulSoup


app = Flask(__name__)
CORS(app)


@app.route("/", methods=['POST'])
def get_etf_list():
    idx = 0
    if request.is_json:
        idx = int(request.get_json()['idx'])

    sidx = idx * 10
    eidx = idx * 10 + 10

    etf_info = []
    etf_list_url = 'https://finance.naver.com/api/sise/etfItemList.nhn'
    etf_list = json.loads(requests.get(etf_list_url).text)['result']['etfItemList'][sidx:eidx]

    for etf in etf_list:
        cd = etf['itemcode']
        nm = etf['itemname']
        assets = []

        etf_url = f'https://finance.naver.com/item/main.naver?code={cd}'
        soup = BeautifulSoup(requests.get(etf_url).text, 'html.parser')
        stocks = soup.select('.etf_asset > table > tbody > tr')[2:]

        for stock in stocks:
            if stock.select_one('.ctg') is not None:
                if stock.select_one('a') is None:
                    continue
                    # code = 'NOT_KOR'
                    # name = stock.select_one('span').text
                    # weight = stock.select_one('td:nth-child(2)').text.strip()
                else:
                    code = stock.select_one('a').attrs['href'][-6:]
                    name = stock.select_one('a').text
                    weight = stock.select_one('.per').text.strip()
                if weight != "-":
                    assets.append({'cd': code, 'nm': name, 'weight': weight, 'quantity': 0})
        if len(assets) > 0:
            etf_info.append({'cd': cd, 'nm': nm, 'assets': assets})

    res = {'code': 200, 'idx': idx, 'size': len(etf_info), 'data': etf_info}

    return jsonify(res)


@app.route("/etf", methods=['POST'])
def get_etf():
    if request.is_json is False:
        return jsonify({'data': -1})

    etf_code = request.get_json()['etf_code']
    etf_name = request.get_json()['etf_name']
    assets = request.get_json()['assets']
    start = request.get_json()['start']
    end = request.get_json()['end']

    # 날짜 인덱스
    date_range = fdr.DataReader(etf_code, start, end).index.strftime('%Y-%m-%d').tolist()
    # etf 지수
    etf_value = fdr.DataReader(etf_code, start, end)['Close'].tolist()
    # etf_수익률
    etf_yield = (np.array(etf_value) - etf_value[0]) / etf_value[0]
    etf_yield = (np.round(etf_yield, 3) * 100).tolist()
    # kospi 지수
    ks_value = fdr.DataReader('KS11', start, end)['Close'].tolist()

    stock_value_sum = 0  # 주가 합
    stock_yield = []  # 주가 수익률
    c_list = []  # 기업 리스트
    c_rate = []  # 기업 비중
    for ass in assets:
        c_list.append(ass['nm'])
        stock_value = fdr.DataReader(ass['cd'], start, end)['Close'].tolist()

        quantity = int(ass['quantity'])  # 매매 주식 수 : quantity
        buy_price = stock_value[0]  # 진입 시점 매매 가격 : buy_price

        stock_value_sum += buy_price * quantity
        c_rate.append(buy_price * quantity)

        if len(stock_yield) == 0:
            stock_yield = (np.array(stock_value) - buy_price) * quantity
        else:
            stock_yield += (np.array(stock_value) - buy_price) * quantity

    # my_etf 수익률
    stock_yield = (np.round(stock_yield / stock_value_sum, 3) * 100).tolist()

    c_rate = (np.array(c_rate) / stock_value_sum).tolist()

    # 결과값
    res = {'etf_name': etf_name, 'date_idx': date_range, 'etf_value': etf_value,
           'ks_value': ks_value, 'etf_yield': etf_yield,
           'stock_yield': stock_yield, 'c_rate': c_rate, 'c_list': c_list}

    return jsonify(res)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
