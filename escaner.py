"""Escaner nube 0.3: oportunidades experimentales, solo practica.
No conoce tus posiciones ni horarios CFD. No avisa cierres ni ejecuta ordenes.
"""
import json, math, os, re, time, tempfile, urllib.request
from pathlib import Path
from datetime import datetime, timezone
ASSETS = {}
def group(category, unit, calendar, reference, symbols):
    for symbol in symbols.split():
        ASSETS[symbol] = dict(category=category, unit=unit, calendar=calendar, reference=reference)
group('Acciones USA', 'USD', 'XNYS', False, 'AAPL MSFT NVDA AMZN GOOGL META TSLA AVGO AMD INTC QCOM MU ORCL CRM ADBE NFLX PYPL UBER JPM BAC V MA KO PEP WMT COST DIS XOM CVX NKE ADP AMAT AMGN ABT ABBV ACN AXP BA BLK BMY C CAT CB CHTR CL CMCSA COP CSCO CVS DHR DUK EMR F FDX GE GILD GM GS HD HON IBM ISRG JNJ KHC LIN LLY LMT LOW LRCX MCD MDLZ MDT MMM MO MRK MS NEE NOW PFE PG PM RTX SBUX SCHW SLB SO SPGI T TGT TMO TXN UNH UNP UPS USB VZ WFC PANW PLTR COIN HOOD RIVN SOFI AFRM APP ARM SMCI SNOW CRWD ZS NET DDOG MDB SHOP BABA JD PDD BIDU TSM ASML NVO SE MELI NU IONQ RGTI RKLB ASTS LUNR MARA RIOT MSTR SNDK CRWV IREN NBIS BE OKLO SMR U UAL DAL AAL CCL RCL DKNG ROKU SNAP PINS SPOT RBLX TTWO EA ABNB DASH XYZ WBD WDAY TEAM ANET FTNT STX WDC HPE DELL HPQ OXY EOG FANG DVN HAL BKR VLO MPC PSX PBR VALE NEM AEM WPM FCX TECK SCCO ALB MP AA NUE STLD DE MOS CF NTR ADM')
group('ETF USA', 'USD', 'XNYS', False, 'SPY QQQ IWM DIA VOO VTI EEM EFA XLF XLK XLE XLV XLI XLU XLP XLY XLB XLRE XLC GLD SLV USO GDX TLT IEF HYG LQD')
group('Acciones Alemania', 'EUR', 'XETR', False, 'SAP.DE SIE.DE ALV.DE DTE.DE BMW.DE VOW3.DE MBG.DE BAS.DE BAYN.DE RWE.DE IFX.DE ADS.DE DBK.DE')
group('Acciones Francia', 'EUR', 'XPAR', False, 'MC.PA OR.PA TTE.PA AIR.PA BNP.PA SAN.PA SU.PA RMS.PA DSY.PA')
group('Acciones España', 'EUR', 'XMAD', False, 'SAN.MC BBVA.MC IBE.MC ITX.MC REP.MC TEF.MC CABK.MC FER.MC')
group('Acciones Reino Unido', 'GBp', 'XLON', False, 'SHEL.L BP.L HSBA.L AZN.L ULVR.L RIO.L LLOY.L BARC.L RR.L VOD.L')
group('Acciones Países Bajos', 'EUR', 'XAMS', False, 'ASML.AS ADYEN.AS INGA.AS HEIA.AS')
group('Acciones Suiza', 'CHF', 'XSWX', False, 'NOVN.SW NESN.SW ROG.SW UBSG.SW')
group('Acciones Japón', 'JPY', 'XTKS', False, '7203.T 6758.T 9984.T 8306.T 8035.T')
group('Acciones Hong Kong', 'HKD', 'XHKG', False, '0700.HK 9988.HK 3690.HK 1810.HK 9618.HK')
group('Acciones Australia', 'AUD', 'XASX', False, 'BHP.AX CBA.AX CSL.AX RIO.AX')
group('Divisas', 'USD', '', False, 'EURUSD=X GBPUSD=X AUDUSD=X NZDUSD=X')
group('Divisas', 'JPY', '', False, 'USDJPY=X EURJPY=X GBPJPY=X AUDJPY=X CADJPY=X CHFJPY=X NZDJPY=X')
group('Divisas', 'CHF', '', False, 'USDCHF=X EURCHF=X')
group('Divisas', 'CAD', '', False, 'USDCAD=X EURCAD=X')
group('Divisas', 'GBP', '', False, 'EURGBP=X')
group('Divisas', 'AUD', '', False, 'EURAUD=X GBPAUD=X')
group('Divisas', 'MXN', '', False, 'USDMXN=X')
group('Divisas', 'ZAR', '', False, 'USDZAR=X')
group('Divisas', 'NOK', '', False, 'USDNOK=X')
group('Divisas', 'SEK', '', False, 'USDSEK=X')
group('Metales', 'USD/oz', '', True, 'GC=F SI=F PL=F PA=F')
group('Metales', 'USD/lb', '', True, 'HG=F')
group('Energía', 'USD/barril', '', True, 'CL=F BZ=F')
group('Energía', 'USD/MMBtu', '', True, 'NG=F')
group('Energía', 'USD/galón', '', True, 'HO=F RB=F')
group('Agrícolas', 'US cents/bushel', '', True, 'ZC=F ZW=F ZS=F')
group('Agrícolas', 'US cents/lb', '', True, 'KC=F SB=F CT=F')
group('Agrícolas', 'USD/tonelada', '', True, 'CC=F')
group('Índices futuros', 'puntos', '', True, 'ES=F NQ=F YM=F RTY=F')
group('Índices contado', 'puntos', '', True, '^GSPC ^NDX ^DJI ^VIX ^GDAXI ^FTSE ^FCHI ^STOXX50E ^IBEX ^N225 ^HSI ^AXJO')
group('Bonos futuros', 'puntos', '', True, 'ZN=F ZB=F ZF=F')
group('Cripto · depende de tu entidad', 'USD', '', True, 'BTC-USD ETH-USD SOL-USD XRP-USD ADA-USD DOGE-USD LTC-USD BCH-USD AVAX-USD LINK-USD DOT-USD')

STALE_SECONDS = 180
def evaluate(frame, now):
    """No futuros ni velas abiertas; rechaza huecos en los 21 últimos cierres."""
    import pandas as pd
    if frame is None or frame.empty or frame.index.tz is None:return None
    f=frame[['Open','High','Low','Close']].copy().sort_index()
    f=f.loc[~f.index.duplicated(keep='last')]
    f=f[f.index+pd.Timedelta(minutes=5)<=now].dropna()
    if len(f)<21:return None
    last=f.index[-1].tz_convert('UTC')
    age=(now-last-pd.Timedelta(minutes=5)).total_seconds()
    if not 0<=age<=STALE_SECONDS:return None
    recent=f.tail(21)
    if any((b-a).total_seconds()!=300 for a,b in zip(recent.index,recent.index[1:])):return None
    vals=recent.to_numpy(dtype=float)
    if not all(math.isfinite(v) and v>0 for row in vals for v in row):return None
    for o,h,l,c in vals:
        if h<max(o,c,l) or l>min(o,c):return None
    closes=list(recent['Close'].astype(float))
    fast=sum(closes[-5:])/5;slow=sum(closes[-20:])/20
    pf=sum(closes[-6:-1])/5;ps=sum(closes[-21:-1])/20
    side='LONG' if pf<=ps and fast>slow else 'SHORT' if pf>=ps and fast<slow else None
    ranges=[max(float(f.iloc[i]['High']-f.iloc[i]['Low']),abs(float(f.iloc[i]['High']-f.iloc[i-1]['Close'])),abs(float(f.iloc[i]['Low']-f.iloc[i-1]['Close']))) for i in range(len(f)-14,len(f))]
    price=closes[-1];distance=max(sum(ranges)/14*1.5,price*.005)
    return dict(bar=last.isoformat(),bar_close=(last+pd.Timedelta(minutes=5)).isoformat(),
                expires=(last+pd.Timedelta(minutes=5,seconds=STALE_SECONDS)).isoformat(),
                price=price,side=side,fast=fast,slow=slow,distance=distance)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def save(state):
    path=Path('estado_nube.json');tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(state,allow_nan=False));os.replace(tmp,path)

def current(row,now):
    return 0 <= (now-datetime.fromisoformat(row['bar_close'])).total_seconds() <= STALE_SECONDS

def send(topic,lines):
    message=('PRACTICA - Posibles oportunidades, no ordenes.\n'
             'Precios externos; confirma CFD abierto y spread en Trading 212.\n'
             + '\n'.join(lines) + '\nNo sigue tus posiciones ni sustituye stops.')
    payload=json.dumps(dict(topic=topic,title='Escaner CFD - Revision experimental',message=message,priority=3)).encode()
    req=urllib.request.Request('https://ntfy.sh/',data=payload,method='POST',headers={'Content-Type':'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=15) as response:
            if response.status!=200:raise ValueError()
    except Exception:
        raise RuntimeError('No se pudo confirmar el envio a ntfy; no se repite automaticamente.') from None

def choose(candidates,seen,now):
    fresh=[r for r in candidates if current(r,now) and seen.get(r['symbol'])!=r['bar']]
    return sorted(fresh,key=lambda r:(r['bar_close'],r['symbol']),reverse=True)[:10]

def main():
    import pandas as pd
    import yfinance as yf
    import exchange_calendars as xc
    import certifi
    from curl_cffi.requests import Session
    from curl_cffi import CurlOpt
    topic=os.environ.get('NTFY_TOPIC','').strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',topic):raise ValueError('Falta el secreto NTFY_TOPIC o no es valido.')
    path=Path('estado_nube.json')
    state=json.loads(path.read_text()) if path.exists() else dict(seen={},day='',messages=0,cursor=0)
    if not isinstance(state.get('seen'),dict):raise ValueError('Estado incompatible; revisar cache.')
    now=pd.Timestamp.now(tz='UTC');day=now.date().isoformat()
    if state.get('day')!=day:state.update(day=day,messages=0)
    calendars={name:xc.get_calendar(name) for name in {a['calendar'] for a in ASSETS.values()} if name}
    symbols=list(ASSETS);offset=int(state.get('cursor',0))%len(symbols)
    symbols=symbols[offset:]+symbols[:offset]
    eligible=[s for s in symbols if not ASSETS[s]['calendar'] or calendars[ASSETS[s]['calendar']].is_open_on_minute(now.floor('min'))]
    candidates=[];coverage=0;attempted=0;started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='cfd_cloud_') as cache:
        yf.set_tz_cache_location(cache)
        session=Session(impersonate='chrome',verify=True,curl_options={CurlOpt.CAINFO:certifi.where()})
        for i in range(0,len(eligible),10):
            # Bound run duration; next run resumes the rotation rather than starving the tail.
            if time.monotonic()-started>210:break
            batch=eligible[i:i+10]
            try:
                frame=yf.download(batch,period='5d',interval='5m',auto_adjust=False,prepost=False,
                                  group_by='ticker',multi_level_index=True,threads=False,session=session,progress=False,timeout=6)
            except Exception:
                frame=None
            checked=pd.Timestamp.now(tz='UTC')
            for sym in batch:
                attempted+=1
                state['cursor']=(list(ASSETS).index(sym)+1)%len(ASSETS)
                a=ASSETS[sym]
                if a['calendar'] and not calendars[a['calendar']].is_open_on_minute(checked.floor('min')):continue
                try:x=evaluate(frame[sym],checked) if frame is not None else None
                except (KeyError,ValueError,TypeError,IndexError):x=None
                if not x:continue
                coverage+=1
                if x['side']:candidates.append(dict(symbol=sym,**x))
    now=datetime.now(timezone.utc)
    chosen=choose(candidates,state['seen'],now)
    lines=[]
    for r in chosen:
        a=ASSETS[r['symbol']];direction='POSIBLE COMPRA' if r['side']=='LONG' else 'POSIBLE CORTO'
        label=' [REFERENCIA: otro producto]' if a['reference'] else ''
        if r['symbol']=='GC=F':label=' [ORO FUTURO, NO XAUUSD SPOT]'
        expiry=datetime.fromisoformat(r['expires']).astimezone(timezone.utc).strftime('%H:%M:%S UTC')
        lines.append(f"{direction} {r['symbol']}{label}; ref. {r['price']:.6g} {a['unit']}; caduca {expiry}")
    if lines and int(state.get('messages',0))<180:
        # Save intent before network: an uncertain publish must not be blindly repeated.
        for r in chosen:state['seen'][r['symbol']]=r['bar']
        state['messages']=int(state.get('messages',0))+1;save(state)
        send(topic,lines)
        print('Notificacion publicada: hasta 10 posibles oportunidades; no ordenes.')
    elif lines:print('Limite prudente de 180 mensajes/dia UTC alcanzado; no se envia.')
    else:print('Sin oportunidades nuevas vigentes al finalizar. No se envia notificacion.')
    save(state)
    print(f'Consultados {attempted}/{len(ASSETS)} candidatos; {coverage} con datos validos al consultar. No son precios CFD verificados.')
    print('Avisos por lotes; el retraso puede descartar cruces. Esta version no sigue operaciones ni envia cierres.')

if __name__=='__main__':
    main()
