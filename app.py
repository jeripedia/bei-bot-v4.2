import numpy as np, pandas as pd, yfinance as yf, streamlit as st
import plotly.graph_objects as go
from pathlib import Path

OUT=Path("output");OUT.mkdir(exist_ok=True)
T=[x.strip() for x in open("tickers.txt") if x.strip()]

def ema(s,n):return s.ewm(span=n,adjust=False).mean()
def rsi(s,n=14):
 d=s.diff();g=d.clip(lower=0);l=-d.clip(upper=0)
 a=g.ewm(alpha=1/n,adjust=False,min_periods=n).mean();b=l.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
 return (100-100/(1+a/b.replace(0,np.nan))).fillna(50)
def rp(p):
 t=1 if p<200 else 2 if p<500 else 5 if p<2000 else 10 if p<5000 else 25
 return int(round(float(p)/t)*t)

@st.cache_data(ttl=600)
def prices(t,mode):
 if mode=="Swing Trading": period,interval="2y","1d"
 else: period,interval="5d","5m"
 d=yf.download(t+".JK",period=period,interval=interval,auto_adjust=False,progress=False)
 if d.empty:return d
 if isinstance(d.columns,pd.MultiIndex):d.columns=d.columns.get_level_values(0)
 d=d[["Open","High","Low","Close","Volume"]].dropna()
 for n in [5,20,50,200]:d[f"E{n}"]=ema(d.Close,n)
 d["RSI"]=rsi(d.Close);d["MACD"]=ema(d.Close,12)-ema(d.Close,26);d["SIG"]=ema(d.MACD,9)
 pc=d.Close.shift();tr=pd.concat([d.High-d.Low,(d.High-pc).abs(),(d.Low-pc).abs()],axis=1).max(axis=1)
 d["ATR"]=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
 d["VR"]=d.Volume/d.Volume.rolling(20).mean().replace(0,np.nan)
 d["RES20"]=d.High.shift(1).rolling(20).max();d["RES50"]=d.High.shift(1).rolling(50).max()
 d["R20"]=d.Close.pct_change(20);d["R60"]=d.Close.pct_change(60)
 return d

@st.cache_data(ttl=3600)
def fund(t):
 try:i=yf.Ticker(t+".JK").info or {}
 except:i={}
 return {"PER":i.get("trailingPE"),"PBV":i.get("priceToBook"),"ROE":i.get("returnOnEquity"),
 "ROA":i.get("returnOnAssets"),"DER":i.get("debtToEquity"),"Revenue Growth":i.get("revenueGrowth"),
 "Earnings Growth":i.get("earningsGrowth"),"Profit Margin":i.get("profitMargins")}

def fscore(f):
 s=0;avail=0
 for v in f.values():
  if v is not None:
   try:
    if np.isfinite(v):avail+=1
   except:pass
 pe=f["PER"];pb=f["PBV"];roe=f["ROE"];roa=f["ROA"];der=f["DER"];rg=f["Revenue Growth"];eg=f["Earnings Growth"];pm=f["Profit Margin"]
 if pe is not None and pe>0:s+=15 if pe<=15 else 10 if pe<=25 else 5 if pe<=40 else 0
 if pb is not None and pb>0:s+=10 if pb<=2 else 7 if pb<=4 else 3 if pb<=7 else 0
 if roe is not None:s+=15 if roe>=.2 else 10 if roe>=.12 else 5 if roe>0 else 0
 if roa is not None:s+=10 if roa>=.1 else 7 if roa>=.05 else 3 if roa>0 else 0
 if der is not None:s+=10 if der<=50 else 7 if der<=100 else 3 if der<=200 else 0
 if rg is not None:s+=10 if rg>=.15 else 7 if rg>=.05 else 3 if rg>0 else 0
 if eg is not None:s+=15 if eg>=.2 else 10 if eg>=.05 else 5 if eg>0 else 0
 if pm is not None:s+=15 if pm>=.2 else 10 if pm>=.1 else 5 if pm>0 else 0
 return min(s,100),round(avail/8*100,1)

def daily_score(r):
 s=0;why=[]
 if r.Close>r.E5>r.E20>r.E50:s+=20;why.append("EMA intraday bullish")
 elif r.Close>r.E20:s+=10
 if 55<=r.RSI<=70:s+=15;why.append("RSI sehat")
 if r.MACD>r.SIG:s+=15;why.append("MACD bullish")
 if pd.notna(r.VR) and r.VR>=2:s+=20;why.append("volume spike")
 elif pd.notna(r.VR) and r.VR>=1.2:s+=10
 if pd.notna(r.RES20) and r.Close>r.RES20:s+=20;why.append("breakout")
 elif pd.notna(r.RES20) and r.Close>=.98*r.RES20:s+=10
 if r.Close>r.Open:s+=10
 return min(s,100),why

def swing_score(r):
 s=0;why=[]
 # Trend medium/long term
 if r.Close>r.E20>r.E50>r.E200:s+=25;why.append("uptrend EMA20>50>200")
 elif r.Close>r.E20>r.E50:s+=18;why.append("trend menengah bullish")
 elif r.Close>r.E50:s+=8
 # Momentum
 if 50<=r.RSI<=65:s+=15;why.append(f"RSI swing sehat {r.RSI:.1f}")
 elif 45<=r.RSI<50 or 65<r.RSI<=72:s+=8
 if r.MACD>r.SIG and r.MACD>0:s+=15;why.append("MACD bullish positif")
 elif r.MACD>r.SIG:s+=8
 # Breakout
 if pd.notna(r.RES50) and r.Close>r.RES50:s+=20;why.append("breakout 50 hari")
 elif pd.notna(r.RES20) and r.Close>r.RES20:s+=15;why.append("breakout 20 hari")
 elif pd.notna(r.RES20) and r.Close>=.97*r.RES20:s+=8;why.append("dekat resistance")
 # Volume
 if pd.notna(r.VR) and r.VR>=1.5:s+=10;why.append("volume konfirmasi")
 elif pd.notna(r.VR) and r.VR>=1.1:s+=5
 # Performance
 if pd.notna(r.R60) and r.R60>.15:s+=10;why.append("momentum 3 bulan kuat")
 elif pd.notna(r.R20) and r.R20>.05:s+=7
 # Candle
 if r.Close>r.Open:s+=5
 return min(s,100),why

def analyze(t,mode,tw):
 d=prices(t,mode)
 minimum=220 if mode=="Swing Trading" else 60
 if len(d)<minimum:return None,None,None
 r=d.iloc[-1]
 ts,why=swing_score(r) if mode=="Swing Trading" else daily_score(r)
 f=fund(t);fs,complete=fscore(f);combined=ts*tw+fs*(1-tw)
 res=float(r.RES50 if mode=="Swing Trading" and pd.notna(r.RES50) else r.RES20 if pd.notna(r.RES20) else r.Close)
 atr=float(r.ATR)
 if mode=="Swing Trading":
  entry=rp(max(float(r.Close),res)+.10*atr);risk=max(1.8*atr,entry*.035)
  tp1=rp(entry+1.5*risk);tp2=rp(entry+3*risk);hold="5–20 hari bursa"
 else:
  entry=rp(max(float(r.Close),res)+.10*atr);risk=max(1.2*atr,entry*.015)
  tp1=rp(entry+risk);tp2=rp(entry+2*risk);hold="Intraday / sangat pendek"
 row={"Saham":t,"Mode":mode,"Harga":rp(r.Close),"Technical Score":ts,"Fundamental Score":fs,
 "Combined Score":round(combined,1),"Data Fundamental %":complete,"Entry":entry,"TP1":tp1,"TP2":tp2,
 "Stop Loss":rp(entry-risk),"Holding Plan":hold,
 "Sinyal":"STRONG SWING" if mode=="Swing Trading" and combined>=80 else "SWING WATCH" if mode=="Swing Trading" and combined>=70 else "STRONG WATCH" if combined>=80 else "WATCH" if combined>=70 else "NEUTRAL+" if combined>=60 else "SKIP",
 "Alasan":"; ".join(why[:6])}
 return row,d,{"Saham":t,**f,"Fundamental Score":fs}

st.set_page_config(page_title="BEI Bot V4.2 Swing",layout="wide")
st.title("BEI Trading Bot V4.2")
st.caption("Daily Trading + Swing Trading • Technical + Fundamental")
with st.sidebar:
 mode=st.radio("Mode Analisis",["Daily Trading","Swing Trading"])
 n=st.slider("Top kandidat",5,20,10);tw=st.slider("Bobot Teknikal %",50,90,70,5)/100
 run=st.button("Scan Sekarang",type="primary")
if run or st.session_state.get("mode")!=mode:
 rows=[];charts={};fd=[]
 with st.spinner(f"Menjalankan {mode} scanner..."):
  for t in T:
   try:
    r,d,f=analyze(t,mode,tw)
    if r:rows.append(r);charts[t]=d;fd.append(f)
   except Exception:pass
 st.session_state.rows=pd.DataFrame(rows).sort_values("Combined Score",ascending=False).head(n) if rows else pd.DataFrame()
 st.session_state.charts=charts;st.session_state.fd=pd.DataFrame(fd);st.session_state.mode=mode
r=st.session_state.rows
st.dataframe(r,use_container_width=True,hide_index=True)
if not r.empty:
 sel=st.selectbox("Pilih saham",r.Saham.tolist());d=st.session_state.charts[sel]
 fig=go.Figure([go.Candlestick(x=d.index,open=d.Open,high=d.High,low=d.Low,close=d.Close)])
 for c in (["E20","E50","E200"] if mode=="Swing Trading" else ["E5","E20","E50"]):
  fig.add_trace(go.Scatter(x=d.index,y=d[c],name=c))
 fig.update_layout(height=620,xaxis_rangeslider_visible=False,title=f"{sel} — {mode}");st.plotly_chart(fig,use_container_width=True)
 row=r[r.Saham==sel].iloc[0]
 st.info(f'Sinyal: {row.Sinyal} | Combined {row["Combined Score"]}\\n\\nEntry {row.Entry} | TP1 {row.TP1} | TP2 {row.TP2} | SL {row["Stop Loss"]} | Holding: {row["Holding Plan"]}\\n\\nAlasan: {row.Alasan}')
 path=OUT/"Laporan_Trading_BEI_V4_2.xlsx"
 with pd.ExcelWriter(path,engine="openpyxl") as x:
  r.to_excel(x,sheet_name="Top Signals",index=False);st.session_state.fd.to_excel(x,sheet_name="Fundamental",index=False)
 with open(path,"rb") as f:st.download_button("Download Laporan Excel",f,"Laporan_Trading_BEI_V4_2.xlsx")
st.warning("Swing signal memakai data harian dan aturan rule-based. Verifikasi data fundamental dan harga dengan sumber resmi. Bukan jaminan keuntungan.")
