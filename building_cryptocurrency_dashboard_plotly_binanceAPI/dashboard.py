# Importing libraries
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from binance.client import Client
import configparser
from binance.websockets import BinanceSocketManager
import time

##############################################################################
# Loading keys from config file
config = configparser.ConfigParser()
config.read_file(open(
    '/home/venom/GitHub/blog_code/building_cryptocurrency_dashboard_plotly_binanceAPI/secret.cfg'))
test_api_key = config.get('BINANCE', 'TEST_API_KEY')
test_secret_key = config.get('BINANCE', 'TEST_SECRET_KEY')

# Setting up connection
client = Client(test_api_key, test_secret_key)
client.API_URL = 'https://testnet.binance.vision/api'  # To change endpoint URL for test account

# Getting account info to check balance
info = client.get_account()  # Getting account info

# Saving different tokens and respective quantities into lists
assets = []
values = []
for index in range(len(info['balances'])):
    for key in info['balances'][index]:
        if key == 'asset':
            assets.append(info['balances'][index][key])
        if key == 'free':
            values.append(info['balances'][index][key])


token_usdt = {}  # Dict to hold pair price in USDT
token_pairs = []  # List to hold different token pairs

# Creating token pairs and saving into a list
for token in assets:
    if token != 'USDT':
        token_pairs.append(token + 'USDT')


def streaming_data_process(msg):
    """
    Function to process the received messages and add latest token pair price
    into the token_usdt dictionary
    :param msg: input message
    """
    global token_usdt
    token_usdt[msg['s']] = msg['c']


def total_amount_usdt(assets, values, token_usdt):
    """
    Function to calculate total portfolio value in USDT
    :param assets: Assets list
    :param values: Assets quantity
    :param token_usdt: Token pair price dict
    :return: total value in USDT
    """
    total_amount = 0
    for i, token in enumerate(assets):
        if token != 'USDT':
            total_amount += float(values[i]) * float(
                token_usdt[token + 'USDT'])
        else:
            total_amount += float(values[i]) * 1
    return total_amount


def total_amount_btc(assets, values, token_usdt):
    """
    Function to calculate total portfolio value in BTC
    :param assets: Assets list
    :param values: Assets quantity
    :param token_usdt: Token pair price dict
    :return: total value in BTC
    """
    total_amount = 0
    for i, token in enumerate(assets):
        if token != 'BTC' and token != 'USDT':
            total_amount += float(values[i]) \
                            * float(token_usdt[token + 'USDT']) \
                            / float(token_usdt['BTCUSDT'])
        if token == 'BTC':
            total_amount += float(values[i]) * 1
        else:
            total_amount += float(values[i]) \
                            / float(token_usdt['BTCUSDT'])
    return total_amount


def assets_usdt(assets, values, token_usdt):
    """
    Function to convert all assets into equivalent USDT value
    :param assets: Assets list
    :param values: Assets quantity
    :param token_usdt: Token pair price dict
    :return: list of asset values in USDT
    """
    assets_in_usdt = []
    for i, token in enumerate(assets):
        if token != 'USDT':
            assets_in_usdt.append(
                float(values[i]) * float(token_usdt[token + 'USDT'])
            )
        else:
            assets_in_usdt.append(float(values[i]) * 1)
    return assets_in_usdt


# Streaming data for tokens in the portfolio
bm = BinanceSocketManager(client)
for tokenpair in token_pairs:
    conn_key = bm.start_symbol_ticker_socket(tokenpair, streaming_data_process)
bm.start()
time.sleep(5)  # To give sufficient time for all tokenpairs to establish connection

##############################################################################
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

app.layout = html.Div([
    html.Div([
        html.Div([
            dcc.Graph(
                id='figure-1',
                figure={
                    'data': [
                        go.Indicator(
                            mode="number",
                            value=total_amount_usdt(assets, values, token_usdt),
                        )
                    ],
                    'layout':
                        go.Layout(
                            title="Portfolio Value (USDT)"
                        )
                }
            )], style={'width': '30%', 'height': '300px',
                       'display': 'inline-block'}),
        html.Div([
            dcc.Graph(
                id='figure-2',
                figure={
                    'data': [
                        go.Indicator(
                            mode="number",
                            value=total_amount_btc(assets, values, token_usdt),
                            number={'valueformat': 'g'}
                        )
                    ],
                    'layout':
                        go.Layout(
                            title="Portfolio Value (BTC)"
                        )
                }
            )], style={'width': '30%', 'height': '300px',
                       'display': 'inline-block'}),
        html.Div([
            dcc.Graph(
                id='figure-3',
                figure={
                    'data': [
                        go.Indicator(
                            mode="number",
                            value=float(token_usdt['BNBUSDT']),
                            number={'valueformat': 'g'}
                        )
                    ],
                    'layout':
                        go.Layout(
                            title="BNB/USDT"
                        )
                }
            )],
            style={'width': '30%', 'height': '300px', 'display': 'inline-block'})
    ]),
    html.Div([
        html.Div([
            dcc.Graph(
                id='figure-4',
                figure={
                    'data': [
                        go.Pie(
                            labels=assets,
                            values=assets_usdt(assets, values, token_usdt),
                            hoverinfo="label+percent"
                        )
                    ],
                    'layout':
                        go.Layout(
                            title="Portfolio Distribution (in USDT)"
                        )
                }
            )], style={'width': '50%', 'display': 'inline-block'}),
        html.Div([
            dcc.Graph(
                id='figure-5',
                figure={
                    'data': [
                        go.Bar(
                            x=assets,
                            y=values,
                            name="Token Quantities For Different Assets",
                        )
                    ],
                    'layout':
                        go.Layout(
                            showlegend=False,
                            title="Tokens distribution"
                        )
                }
            )], style={'width': '50%', 'display': 'inline-block'}),
        dcc.Interval(
            id='1-second-interval',
            interval=1000,  # 1000 milliseconds
            n_intervals=0
        )
    ]),
])


@app.callback(Output('figure-1', 'figure'),
              Output('figure-2', 'figure'),
              Output('figure-3', 'figure'),
              Output('figure-4', 'figure'),
              Output('figure-5', 'figure'),
              Input('1-second-interval', 'n_intervals'))
def update_layout(n):
    figure1 = {
        'data': [
            go.Indicator(
                mode="number",
                value=total_amount_usdt(assets, values, token_usdt),
            )
        ],
        'layout':
            go.Layout(
                title="Portfolio Value (USDT)"
            )
    }
    figure2 = {
        'data': [
            go.Indicator(
                mode="number",
                value=total_amount_btc(assets, values, token_usdt),
                number={'valueformat': 'g'}
            )
        ],
        'layout':
            go.Layout(
                title="Portfolio Value (BTC)"
            )
    }
    figure3 = {
        'data': [
            go.Indicator(
                mode="number",
                value=float(token_usdt['BNBUSDT']),
                number={'valueformat': 'g'}
            )
        ],
        'layout':
            go.Layout(
                title="BNB/USDT"
            )
    }
    figure4 = {
        'data': [
            go.Pie(
                labels=assets,
                values=assets_usdt(assets, values, token_usdt),
                hoverinfo="label+percent"
            )
        ],
        'layout':
            go.Layout(
                title="Portfolio Distribution (in USDT)"
            )
    }
    figure5 = {
        'data': [
            go.Bar(
                x=assets,
                y=values,
                name="Token Quantities For Different Assets",
            )
        ],
        'layout':
            go.Layout(
                showlegend=False,
                title="Tokens distribution"
            )
    }

    return figure1, figure2, figure3, figure4, figure5


if __name__ == '__main__':
    app.run_server(host='127.0.0.1', port='8050', debug=True)
