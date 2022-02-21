#
# Streamlit demo for financial analysis
#

# disable SSL warnings
from asyncio.windows_events import NULL
import urllib3
urllib3.disable_warnings( urllib3.exceptions.InsecureRequestWarning )

# -------------------------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------------------------

import requests
import streamlit as st
import pandas as pd
import altair as alt
import talib  as ta
import os
import json

from yahooquery import Ticker

# -------------------------------------------------------------------------------------------------
# Globals
# -------------------------------------------------------------------------------------------------

_PARAM_FILE      = "param.json"

_DEFAULT_PORT    = [ 'SPY', 'QQQ' ]
_DEFAULT_MARKET  = [ 'NQ=F', 'ES=F', 'YM=F', 'KRW=X' ]
_DEFAULT_BENCH   = [ 'SPY' ]
_RSI_THRESHOLD_L =   30
_RSI_THRESHOLD_H =   70
_CCI_THRESHOLD_L = -100
_CCI_THRESHOLD_H =  100

attr_list = { 
    'regularMarketChangePercent':'Change(%)', 
    'regularMarketPrice':'Price',
    'trailingPE':'P/E',
    'fiftyTwoWeekHigh':'52W_H(%)',
    'fiftyTwoWeekLow':'52W_L(%)',
    'NQ=F':'NASDAQ Futures',
    'ES=F':'S&P 500 Futures',
    'YM=F':'DOW Futures',
    'KRW=X':'USD/KRW',
}
period_div_1y = {
    '1M': 12,
    '3M': 4,
    '6M': 2,
    '1Y': 1,
}
period_div_5d = {
    '6H' : 20,
    '12H': 10,
    '1D' : 5,
    '5D' : 1,
}
params = {
    'port'   : _DEFAULT_PORT,
    'market' : _DEFAULT_MARKET,
    'bench'  : _DEFAULT_BENCH,
    'RSI_L'  : _RSI_THRESHOLD_L,
    'RSI_H'  : _RSI_THRESHOLD_H,
    'CCI_L'  : _CCI_THRESHOLD_L,
    'CCI_H'  : _CCI_THRESHOLD_H,
    'market_period': '6H',
    'gain_period'  : '1M',
    'stock_period' : '1M',
    'stock_ticker' : 'SPY',
}

# -------------------------------------------------------------------------------------------------
# Functions
# -------------------------------------------------------------------------------------------------

@st.experimental_singleton
def fetch_tickers( tickers ):
    
    _list = Ticker( tickers, verify=False, asynchronous=True )
    return _list

@st.experimental_singleton
def fetch_history( _ticker_list, period, interval ):

    _hist = _ticker_list.history( period, interval )
    return _hist

@st.experimental_singleton
def fetch_history_alt( _ticker_list, period, interval ):

    _hist = _ticker_list.history( period, interval )
    return _hist    

def get_usdkrw():

    _temp = requests.get( "https://api.exchangerate-api.com/v4/latest/USD", verify=False )
    exchange_rate = _temp.json()

    return exchange_rate['rates']['KRW']

def check_oversold( entry, rsi_L, cci_L ):

    if entry[ 'RSI(14)' ] > rsi_L:
        return False

    if entry[ 'CCI(14)' ] > cci_L:
        return False

    return True

def check_overbought( entry, rsi_H, cci_H ):

    if entry[ 'RSI(14)' ] < rsi_H:
        return False      

    if entry[ 'CCI(14)' ] < cci_H:
        return False            

    return True

def highlight_negative(s):

    is_negative = s < 0
    return ['color: red' if i else '' for i in is_negative]

def get_price_chart( ticker, num_points ):

    hist = stock_histo[ 'close' ][ ticker ]
    source = pd.DataFrame( {
    'Date': hist.index[-num_points:],
    'Price': hist[-num_points:]
    } )
    ch = alt.Chart( source ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Price', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Date', 'Price' ]
    ).properties( title = 'Price' )
    return ch

def get_bband_chart( ticker, num_points ):

    bband_up, bband_mid, bband_low = ta.BBANDS( stock_histo['close'][ ticker ], 20, 2 )
    source1 = pd.DataFrame( {
    'Metric': 'BBAND_UPPER',
    'Date'  : bband_up.index[-num_points:],
    'Price' : bband_up[-num_points:]
    } )
    source2 = pd.DataFrame( {
    'Metric': 'BBAND_MIDDLE',
    'Date'  : bband_mid.index[-num_points:],
    'Price' : bband_mid[-num_points:]
    } )
    source3 = pd.DataFrame( {
    'Metric': 'BBAND_LOWER',
    'Date'  : bband_low.index[-num_points:],
    'Price' : bband_low[-num_points:]
    } )
    source = pd.concat( [ source1, source2, source3 ] )
    ch = alt.Chart( source ).mark_line( strokeDash=[2,3] ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Price', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', 'Price' ],
        color = alt.Color( 'Metric', legend=None ),
    )
    return ch

def get_ma_chart( ticker, num_points, period, colorstr ):

    ma = ta.SMA( stock_histo['close'][ ticker ], period )
    source = pd.DataFrame( {
    'Metric': f'MA{period}',
    'Date'  : ma.index[-num_points:],
    'Price' : ma[-num_points:]
    } )
    ch = alt.Chart( source ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Price', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', 'Price' ],
        color = alt.value( colorstr ),
        strokeWidth = alt.value( 1 ),
    )
    return ch

def get_rsi_chart( ticker, num_points ):

    rsi_hist = ta.RSI( stock_histo['close'][ ticker ] )
    source = pd.DataFrame( {
    'Date': rsi_hist.index[-num_points:],
    'RSI': rsi_hist[-num_points:]
    } )
    ch = alt.Chart( source ).mark_line( point=alt.OverlayMarkDef() ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'RSI', scale=alt.Scale( domain=[10,90] )  ),
        tooltip = [ 'Date', 'RSI' ]
    ).properties( title = 'RSI(14)' )
    source_up = pd.DataFrame( {
    'Date': rsi_hist.index[-num_points:],
    'RSI': params['RSI_H']
    } )
    up = alt.Chart( source_up ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'RSI', scale=alt.Scale( domain=[10,90] )  ),
        color=alt.value("#FFAA00")
    )
    source_dn = pd.DataFrame( {
    'Date': rsi_hist.index[-num_points:],
    'RSI': params['RSI_L']
    } )
    dn = alt.Chart( source_dn ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'RSI', scale=alt.Scale( domain=[10,90] )  ),
        color=alt.value("#FFAA00")
    ) 
    return ch+up+dn

def get_cci_chart( ticker, num_points ):

    cci_hist = ta.CCI( stock_histo['high'][ ticker ], stock_histo['low'][ ticker ], stock_histo['close'][ ticker ] )
    source = pd.DataFrame( {
    'Date': cci_hist.index[-num_points:],
    'CCI': cci_hist[-num_points:]
    } )
    ch = alt.Chart( source ).mark_line( point=alt.OverlayMarkDef() ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'CCI', scale=alt.Scale( domain=[-200,200] )  ),
        tooltip = [ 'Date', 'CCI' ]
    ).properties( title = 'CCI(14)' )
    source_up = pd.DataFrame( {
    'Date': cci_hist.index[-num_points:],
    'CCI': params['CCI_H']
    } )
    up = alt.Chart( source_up ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'CCI', scale=alt.Scale( domain=[-200,200] )  ),
        color=alt.value("#FFAA00")
    )
    source_dn = pd.DataFrame( {
    'Date': cci_hist.index[-num_points:],
    'CCI': params['CCI_L']
    } )
    dn = alt.Chart( source_dn ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'CCI', scale=alt.Scale( domain=[-200,200] )  ),
        color=alt.value("#FFAA00")
    ) 
    return ch+up+dn    

def get_macd_charts( ticker, num_points ):

    macd, macdsignal, macdhist = ta.MACD( stock_histo['close'][ ticker ] )
    source1 = pd.DataFrame( {
    'Metric': 'MACD(12)',
    'Date'  : macd.index[-num_points:],
    'Value' : macd[-num_points:]
    } )
    source2 = pd.DataFrame( {
    'Metric': 'MACD(26)',
    'Date'  : macdsignal.index[-num_points:],
    'Value' : macdsignal[-num_points:]
    } )
    source3 = pd.DataFrame( {
    'Metric': 'MACDHIST',
    'Date'  : macdhist.index[-num_points:],
    'Hist'  : macdhist[-num_points:]
    } )
    source = pd.concat( [ source1, source2 ] )

    ch1 = alt.Chart( source ).mark_line( point=alt.OverlayMarkDef() ).encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Value', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', 'Value' ],
        color = alt.Color( 'Metric', legend=alt.Legend( orient="top-left" ) )
    ).properties( title = 'MACD' )
    ch2 = alt.Chart( source3 ).mark_bar().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Hist' ),
        tooltip = [ 'Date', 'Hist' ],
        color=alt.condition(
            alt.datum.Hist > 0,
            alt.value("green"),  # The positive color
            alt.value("red")  # The negative color
        )        
    )
    return ch1, ch2

def get_market_chart( ticker, num_points ):

        hist = market_histo[ 'close' ][ ticker ]
        source = pd.DataFrame( {
        'Date': hist.index[-num_points:],
        'Price': hist[-num_points:]
        } )
        ch = alt.Chart( source ).mark_line().encode(
            x=alt.X( 'Date' ),
            y=alt.Y( 'Price', scale=alt.Scale( zero=False )  ),
            tooltip = [ 'Date', 'Price' ]
        )

        prev_close = market_list.price[ option ][ 'regularMarketPreviousClose' ]
        source = pd.DataFrame( {
        'Date': hist.index[-num_points:],
        'Price': prev_close
        } )

        delta = ( hist[-1] - prev_close ) / prev_close * 100.
        prev = alt.Chart( source ).mark_line().encode(
            x=alt.X( 'Date' ),
            y=alt.Y( 'Price' ),
            color=alt.value("#FFAA00"),
            tooltip = [ 'Date', 'Price' ]
        ).properties( title = f'{attr_list[ option ]} ({delta:.2f}%)' )

        return ch+prev

def get_btest_chart( num_points ):

    # get benchmark data
    _source = []    
    for ticker in params['bench']:

        data = bench_histo[ 'close' ][ ticker ]
        data /= data[-num_points]
        data -= 1
        data *= 100

        _temp = pd.DataFrame( {
        'Metric': ticker,
        'Date'  : data.index[-num_points:],
        'Gain' : data[-num_points:]
        } )
        _source.append( _temp )

    # get portfolio data
    for index, ticker in enumerate( params['port'] ):
        _temp = stock_histo[ 'close' ][ ticker ]
        _temp /= _temp[-num_points]
        _temp -= 1
        _temp *= 100
        if index == 0: _data  = _temp
        else:          _data += _temp
    _data /= len( params['port'] )

    _temp = pd.DataFrame( {
        'Metric': 'Portfolio',
        'Date'  : _data.index[-num_points:],
        'Gain' : _data[-num_points:]
    } )
    _source.append( _temp )

    # concat data
    source = pd.concat( _source )

    # benchmark chart
    ch = alt.Chart( source ).mark_line().encode(
        x=alt.X( 'Date' ),
        y=alt.Y( 'Gain', scale=alt.Scale( zero=False )  ),
        tooltip = [ 'Metric', 'Date', 'Gain' ],
        color = alt.Color( 'Metric', legend=alt.Legend( orient="top-left" ) )
    )

    return ch

def fill_table( stock_list ):

    # data from Ticker.price
    _table_data = {}
    
    for key, val in stock_list.price.items():
        
        # initialize
        entry = {}

        try:
            # for each items
            for sub_key, sub_val in val.items():
                if sub_key in attr_list:
                    if "Percent" in sub_key: sub_val *= 100.
                    entry[ attr_list[ sub_key ] ] = sub_val

            # compute RSI
            rsi = ta.RSI( stock_histo['close'][ key ] )[-1]
            entry[ 'RSI(14)' ] = rsi

            # compute CCI
            cci = ta.CCI( stock_histo['high'][ key ], stock_histo['low'][ key ], stock_histo['close'][ key ] )[-1]
            entry[ 'CCI(14)' ] = cci
        
            # replace
            _table_data[ key ] = entry
        except:
            pass

    # data from Ticker.summary_detail
    for key, val in stock_list.summary_detail.items():
        
        # initialize
        entry = _table_data[ key ]

        try:
            for sub_key, sub_val in val.items():
                if sub_key in attr_list:
                    if "Percent" in sub_key: sub_val *= 100.
                    if sub_key == 'fiftyTwoWeekHigh' or sub_key == 'fiftyTwoWeekLow':
                        sub_val = ( entry[ 'Price' ]-sub_val ) / sub_val * 100.
                    entry[ attr_list[ sub_key ] ] = sub_val

            _table_data[ key ] = entry
        except:
            pass

    return _table_data

def save_params():
    with open( _PARAM_FILE, 'w' ) as fp:
        json.dump( params, fp, indent=4 )
    return

def load_params():
    with open( _PARAM_FILE, 'r' ) as fp:
        ret = json.load( fp )
    return ret

# -------------------------------------------------------------------------------------------------
# Layout
# -------------------------------------------------------------------------------------------------

# add sidebar
st.sidebar.title( 'Financial Stream' )
menu = st.sidebar.radio( "MENU", ( 'Market', 'Portfolio', 'Stock' ) )

# -------------------------------------------------------------------------------------------------
# Fetch data
# -------------------------------------------------------------------------------------------------

# check if param file exists
if os.path.isfile( _PARAM_FILE ): params=load_params()
else: save_params()

stock_list   = fetch_tickers    ( params['port'  ] )
bench_list   = fetch_tickers    ( params['bench' ] )
market_list  = fetch_tickers    ( params['market'] )
stock_histo  = fetch_history    ( stock_list,  period='1y', interval='1d' )
bench_histo  = fetch_history_alt( bench_list,  period='1y', interval='1d' )
market_histo = fetch_history    ( market_list, period='5d', interval='5m' )

# -------------------------------------------------------------------------------------------------
# Generate data
# -------------------------------------------------------------------------------------------------

# fill data from stock list
table_data = fill_table( stock_list )

# -------------------------------------------------------------------------------------------------
# Portfolio
# -------------------------------------------------------------------------------------------------

if menu == 'Portfolio':
    # enter ticker list
    ticker_str = st.text_input( "Ticker list", ' '.join( params['port'] ) )
    new_port_tickers = ticker_str.split( ' ' )
    
    if params['port'] != new_port_tickers:
        
        # update ticker file
        params['port'] = new_port_tickers
        save_params()

        # clear cache
        st.experimental_singleton.clear()

        # update table
        stock_list   = fetch_tickers( params['port'] )
        stock_histo  = fetch_history( stock_list,  period='1y', interval='1d' )
        table_data   = fill_table   ( stock_list )

    # ---------------------------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------------------------

    st.subheader( 'Portfolio' )
    df = pd.DataFrame.from_dict( table_data, orient='index' ).sort_values( by='RSI(14)' )
    df = df.style.set_precision( 2 ).apply( highlight_negative, axis=1 ).set_na_rep("-")
    st.write( df )

    # ---------------------------------------------------------------------------------------------
    # Backtest
    # ---------------------------------------------------------------------------------------------

    with st.expander( "Accumulated Gain (%)" ):
        # points selector
        values = [ '1M', '3M', '6M', '1Y' ]
        period = st.selectbox( 'Period', values, index=values.index( params['gain_period'] ) )
        num_points = int( len( bench_histo[ 'close' ] ) / period_div_1y[ period ] )

        # update parameter
        params['gain_period'] = period
        save_params()
        
        btest_chart = get_btest_chart( num_points )
        st.altair_chart( btest_chart, use_container_width=True )

    # ---------------------------------------------------------------------------------------------
    # Oversold & Overbought
    # ---------------------------------------------------------------------------------------------

    st.subheader( 'Over stocks' )

    # range selector
    col1, col2 = st.columns(2)
    with col1:
        # RSI margin
        rsi_L, rsi_H = st.select_slider(
            'Normal RSI Range',
            options=[ i for i in range( 0, 105, 5 ) ],
            value = (params['RSI_L'], params['RSI_H']) )
        # update parameters
        params['RSI_L'] = rsi_L
        params['RSI_H'] = rsi_H
        save_params()
    with col2:
        # CCI margin
        cci_L, cci_H = st.select_slider(
            'Normal CCI Range',
            options=[ i for i in range( -200, 210, 10 ) ],
            value = (params['CCI_L'], params['CCI_H']) )
        # update parameters
        params['CCI_L'] = cci_L
        params['CCI_H'] = cci_H
        save_params()

    # generate oversold and overbought data
    oversold_data   = {}
    overbought_data = {}
    for key, val in table_data.items():
        if check_oversold  ( val, rsi_L, cci_L ): oversold_data  [ key ] = val
        if check_overbought( val, rsi_H, cci_H ): overbought_data[ key ] = val

    # sub title
    st.markdown( '##### Oversold' )

    # write noted list
    st.text( f'RSI<{rsi_L} and CCI<{cci_L}' )
    
    if oversold_data != {}:
        df = pd.DataFrame.from_dict( oversold_data, orient='index' ).sort_values( by='RSI(14)' )
        df = df.style.set_precision( 2 ).apply( highlight_negative, axis=1 ).set_na_rep("-")
        st.write( df )

    # sub title
    st.markdown( '##### Overbought' )

    # write noted list
    st.text( f'RSI>{rsi_H} and CCI>{cci_H}' )
    
    if overbought_data != {}:
        df = pd.DataFrame.from_dict( overbought_data, orient='index' ).sort_values( by='RSI(14)' )
        df = df.style.set_precision( 2 ).apply( highlight_negative, axis=1 ).set_na_rep("-")
        st.write( df )

# -------------------------------------------------------------------------------------------------
# Each stock
# -------------------------------------------------------------------------------------------------

if menu == 'Stock':
    # sub title
    st.subheader( 'Stock chart' )

    # stock selector
    option = st.selectbox( 'Ticker', params['port'], index=params['port'].index( params['stock_ticker'] ) )

    # points selector
    values = [ '1M', '3M', '6M', '1Y' ]
    period = st.selectbox( 'Period', values, index=values.index( params['stock_period'] ) )
    num_points = int( len( bench_histo[ 'close' ] ) / period_div_1y[ period ] )

    # update parameter
    params['stock_ticker'] = option
    params['stock_period'] = period
    save_params()

    # ---------------------------------------------------------------------------------------------
    # price history chart
    # ---------------------------------------------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        bband_flag = st.checkbox( 'Bollinger band' )
    with col2:
        ma20_flag  = st.checkbox( 'MA20 (RED)' )
    with col3:
        ma60_flag  = st.checkbox( 'MA60 (GREEN)' )
    with col4:
        ma120_flag  = st.checkbox( 'MA120 (ORANGE)' )

    # price chart
    price_chart = get_price_chart( option, num_points )

    # bollinger band chart
    if bband_flag:
        price_chart += get_bband_chart( option, num_points )

    # MA20 chart
    if ma20_flag:
        price_chart += get_ma_chart( option, num_points, 20, 'red' )

    # MA60 chart
    if ma60_flag:
        price_chart += get_ma_chart( option, num_points, 60, 'green' )

    # MA120 chart
    if ma120_flag:
        price_chart += get_ma_chart( option, num_points, 120, 'orange' )

    # draw
    st.altair_chart( price_chart, use_container_width=True )

    # ---------------------------------------------------------------------------------------------
    # RSI history chart
    # ---------------------------------------------------------------------------------------------

    # rsi chart
    rsi_chart = get_rsi_chart( option, num_points )

    # draw
    st.altair_chart( rsi_chart, use_container_width=True )

    # ---------------------------------------------------------------------------------------------
    # CCI history chart
    # ---------------------------------------------------------------------------------------------

    # rsi chart
    cci_chart = get_cci_chart( option, num_points )

    # draw
    st.altair_chart( cci_chart, use_container_width=True )    

    # ---------------------------------------------------------------------------------------------
    # MACD history chart
    # ---------------------------------------------------------------------------------------------
    
    # macd chart
    macd_chart, macd_hist_chart = get_macd_charts( option, num_points )

    # draw
    st.altair_chart( macd_chart,      use_container_width=True )
    st.altair_chart( macd_hist_chart, use_container_width=True )

# -------------------------------------------------------------------------------------------------
# Market
# -------------------------------------------------------------------------------------------------

if menu == 'Market':
    # sub title
    st.subheader( 'Market chart' )

    # points selector
    values = [ '6H', '12H', '1D', '5D' ]
    period = st.selectbox( 'Period', values, index=values.index( params['market_period'] ) )
    num_points = int( len( bench_histo[ 'close' ] ) / period_div_5d[ period ] )

    # update parameter
    params['market_period'] = period
    save_params()
    
    # refresh button
    if st.button( 'Refresh' ):
        st.experimental_singleton.clear()

    for option in params['market']:
        market_chart = get_market_chart( option, num_points )
        st.altair_chart( market_chart, use_container_width=True )