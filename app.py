from flask import Flask, request, jsonify, render_template_string, Response
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai
import os, json, re, requests
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)

ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY","")
VOICE_IDS = {"chatgpt":"ErXwobaYiN019PkySvjV","claude":"VR6AewLTigWG4xSOukaG","gemini":"TxGEqnHWrfWFTfGW9XjX","deepseek":"VR6AewLTigWG4xSOukaG","judge":"EXAVITQu4vr4xnSDxMaL"}
MODES = {
    "normal":{"name":"Normal","icon":"💬","prompt":"Sen uzman bir asistansin. Net cevap ver."},
    "research":{"name":"Araştırma","icon":"🔍","prompt":"Derinlemesine arastir, kaynaklar sun."},
    "ideas":{"name":"Fikir","icon":"💡","prompt":"5-7 yaratici fikir sun."},
    "critique":{"name":"Eleştir","icon":"⚔️","prompt":"Zayif yonleri ve riskleri acikca soyle."},
    "roadmap":{"name":"Yol Haritası","icon":"🗺️","prompt":"Adim adim yol haritasi cikart."},
    "report":{"name":"Rapor","icon":"📊","prompt":"Profesyonel rapor yaz."},
    "startup":{"name":"Startup","icon":"🚀","prompt":"Girisimci gozuyle ele al: guc, hedef kitle, gelir, rakipler, adimlar, riskler."},
    "ultra":{"name":"Ultra","icon":"⚡","prompt":"Her aciyla ele al: arastirma, fikirler, elestirel bakis, yol haritasi, rapor, girisimci perspektifi."},
}

def ask_chatgpt(s,u):
    c=OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    r=c.chat.completions.create(model="gpt-4o",max_tokens=2000,messages=[{"role":"system","content":s},{"role":"user","content":u}])
    return r.choices[0].message.content

def ask_claude(s,u):
    c=Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    r=c.messages.create(model="claude-opus-4-5",max_tokens=2000,system=s,messages=[{"role":"user","content":u}])
    return r.content[0].text

def ask_gemini(s,u):
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    m=genai.GenerativeModel("gemini-flash-latest",system_instruction=s)
    return m.generate_content(u).text

def ask_deepseek(s,u):
    c=OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"],base_url="https://api.deepseek.com/v1")
    r=c.chat.completions.create(model="deepseek-chat",max_tokens=2000,messages=[{"role":"system","content":s},{"role":"user","content":u}])
    return r.choices[0].message.content

MODELS={"chatgpt":ask_chatgpt,"claude":ask_claude,"gemini":ask_gemini,"deepseek":ask_deepseek}
NAMES={"chatgpt":"ChatGPT","claude":"Claude","gemini":"Gemini","deepseek":"DeepSeek"}
COLORS={"chatgpt":"#10a37f","claude":"#c87557","gemini":"#4285f4","deepseek":"#7c3aed"}
ICONS={"chatgpt":"⚡","claude":"🎭","gemini":"✨","deepseek":"🔬"}

def pick_model(q):
    p=f"Soru: {q}\nSADECE JSON: {{\"model\":\"chatgpt/claude/gemini/deepseek\",\"reason\":\"gerekce\"}}"
    raw=ask_claude("Router'sin. En uygun modeli sec.",p)
    m=re.search(r'\{.*?\}',raw,re.DOTALL)
    if m:
        try:
            d=json.loads(m.group(0))
            if d.get("model") in MODELS: return d["model"],d.get("reason","")
        except: pass
    return "claude","Varsayilan"

@app.route("/")
def home(): return render_template_string(HTML)

@app.route("/api/route",methods=["POST"])
def api_route():
    q=request.json.get("question","").strip()
    if not q: return jsonify({"error":"bos"}),400
    c,r=pick_model(q)
    return jsonify({"chosen":c,"name":NAMES[c],"reason":r,"color":COLORS[c],"icon":ICONS[c]})

@app.route("/api/answer",methods=["POST"])
def api_answer():
    d=request.json
    q,model,modes=d.get("question",""),d.get("model",""),d.get("modes",["normal"])
    if not q or model not in MODELS: return jsonify({"error":"eksik"}),400
    if len(modes)==1: prompt=MODES.get(modes[0],MODES["normal"])["prompt"]
    else: prompt="Su talimatlarin hepsini uygula: "+" | ".join(MODES.get(m,MODES["normal"])["prompt"] for m in modes)
    try: return jsonify({"answer":MODELS[model](prompt,q)})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route("/api/critique_one",methods=["POST"])
def api_critique_one():
    d=request.json
    q,ans,critic=d.get("question",""),d.get("answer",""),d.get("critic","")
    if critic not in MODELS: return jsonify({"error":"yanlis"}),400
    try:
        t=MODELS[critic]("Elestirmensin. 3-4 cumlede eksik ve yanlis noktalari soyle.",f"SORU:\n{q}\n\nCEVAP:\n{ans}")
        return jsonify({"text":t,"name":NAMES[critic],"color":COLORS[critic],"icon":ICONS[critic]})
    except: return jsonify({"text":"[Cevap alinamadi]","name":NAMES[critic],"color":COLORS[critic],"icon":ICONS[critic]})

@app.route("/api/defend",methods=["POST"])
def api_defend():
    d=request.json
    q,ans,crits,primary=d.get("question",""),d.get("answer",""),d.get("critiques",{}),d.get("primary","")
    if primary not in MODELS: return jsonify({"error":"yanlis"}),400
    cb="\n".join(f"{v['name']}: {v['text']}" for v in crits.values())
    try:
        t=MODELS[primary]("Elestirilere yanit ver.",f"CEVAP:\n{ans}\n\nELESTIRILER:\n{cb}\n\n4-5 cumlede yanit ver.")
        return jsonify({"text":t,"name":NAMES[primary],"color":COLORS[primary],"icon":ICONS[primary]})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route("/api/critique_round2",methods=["POST"])
def api_critique_round2():
    d=request.json
    q,ans,defense,critic=d.get("question",""),d.get("answer",""),d.get("defense",""),d.get("critic","")
    if critic not in MODELS: return jsonify({"error":"yanlis"}),400
    try:
        t=MODELS[critic]("Savunma tatmin edici mi? 3-4 cumle.",f"CEVAP:\n{ans}\n\nSAVUNMA:\n{defense}")
        return jsonify({"text":t,"name":NAMES[critic],"color":COLORS[critic],"icon":ICONS[critic]})
    except: return jsonify({"text":"[Cevap alinamadi]","name":NAMES[critic],"color":COLORS[critic],"icon":ICONS[critic]})

@app.route("/api/judge",methods=["POST"])
def api_judge():
    d=request.json
    q,ans,crits=d.get("question",""),d.get("answer",""),d.get("critiques",{})
    cb="\n\n".join(f"{v['name']}: {v['text']}" for v in crits.values()) or "(yok)"
    jm,_=pick_model(q)
    try:
        f=MODELS[jm]("Hakemsin. Tek nihai cevap yaz.",f"SORU:\n{q}\n\nCEVAP:\n{ans}\n\nELESTIRILER:\n{cb}")
        return jsonify({"final":f,"judge_name":NAMES[jm]})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route("/api/transcribe",methods=["POST"])
def api_transcribe():
    if 'audio' not in request.files: return jsonify({"error":"ses yok"}),400
    try:
        c=OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        r=c.audio.transcriptions.create(model="whisper-1",file=("a.webm",request.files['audio'].read(),"audio/webm"),language="tr")
        return jsonify({"text":r.text})
    except Exception as e: return jsonify({"error":str(e)}),500

@app.route("/api/tts",methods=["POST"])
def api_tts():
    d=request.json
    text,model=d.get("text","").strip(),d.get("model","claude")
    if not text: return jsonify({"error":"bos"}),400
    if not ELEVENLABS_KEY: return jsonify({"error":"key yok"}),500
    clean=re.sub(r'[#*_`]','',text)[:2500]
    try:
        r=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_IDS.get(model,VOICE_IDS['judge'])}/stream",
            json={"text":clean,"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.5,"similarity_boost":0.75}},
            headers={"xi-api-key":ELEVENLABS_KEY},stream=True)
        if r.status_code!=200: return jsonify({"error":f"EL:{r.status_code}"}),500
        return Response((c for c in r.iter_content(4096) if c),mimetype="audio/mpeg")
    except Exception as e: return jsonify({"error":str(e)}),500

HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Beyin Takimi">
<title>Beyin Takimi</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,system-ui,sans-serif;background:#1a1a1a;color:#eee;display:flex;height:100vh;overflow:hidden}
.sb{width:220px;background:#111;border-right:1px solid #333;padding:.8rem;display:flex;flex-direction:column;gap:.4rem;overflow-y:auto;flex-shrink:0}
.sb-title{font-size:.7rem;text-transform:uppercase;color:#666;margin:.6rem 0 .2rem;letter-spacing:.5px}
.nb{background:#c87557;color:#fff;border:none;padding:.65rem;border-radius:10px;cursor:pointer;font-size:.88rem;font-weight:600;width:100%}
.sbb{background:transparent;border:1px solid #333;color:#eee;padding:.5rem .65rem;border-radius:8px;cursor:pointer;font-size:.8rem;text-align:left;width:100%}
.sbb:hover{background:#222}
.hi{padding:.5rem .65rem;border-radius:7px;cursor:pointer;font-size:.8rem;color:#ccc;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border:1px solid transparent}
.hi:hover,.hi.on{background:#222;border-color:#333}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.hdr{padding:.8rem 1rem;border-bottom:1px solid #333;display:flex;align-items:center;justify-content:space-between;background:#111;flex-shrink:0}
.hdr h1{font-size:1rem;font-weight:700}
.hbtns{display:flex;gap:.3rem}
.ib{background:transparent;border:1px solid #333;color:#eee;padding:.35rem .5rem;border-radius:8px;cursor:pointer;font-size:.85rem}
.ib:hover{background:#222}
.ib.on{background:#c87557;border-color:#c87557;color:#fff}
.content{flex:1;overflow-y:auto;padding:1rem;max-width:820px;width:100%;margin:0 auto}
.ia{padding:.7rem 1rem 1rem;border-top:1px solid #333;background:#111;flex-shrink:0}
.iw{max-width:820px;margin:0 auto;background:#222;border:1px solid #333;border-radius:16px;padding:.7rem}
.iw:focus-within{border-color:#c87557}
textarea{width:100%;background:transparent;border:none;color:#eee;font-size:.95rem;resize:none;outline:none;font-family:inherit;min-height:42px;max-height:160px}
.ctrl{display:flex;justify-content:space-between;align-items:center;margin-top:.4rem;gap:.4rem}
.sels{display:flex;gap:.3rem;flex:1}
.sw{position:relative;flex:1}
.sb2{width:100%;padding:.38rem .6rem;background:#111;border:1px solid #333;border-radius:8px;color:#eee;font-size:.78rem;cursor:pointer;text-align:left;font-family:inherit;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sb2:hover{border-color:#c87557}
.sm{display:none;position:absolute;bottom:calc(100% + 4px);left:0;background:#1a1a1a;border:1px solid #333;border-radius:10px;padding:.3rem;box-shadow:0 8px 20px rgba(0,0,0,.4);z-index:999;min-width:160px;max-height:280px;overflow-y:auto}
.sm.open{display:block}
.si{padding:.45rem .6rem;border-radius:7px;cursor:pointer;font-size:.83rem;color:#eee;white-space:nowrap}
.si:hover{background:#333}
.si.on{background:#c87557;color:#fff}
.ultra{background:linear-gradient(135deg,#f97316,#c87557);color:#fff;font-weight:600;margin-top:.3rem}
.ultra:hover{opacity:.9}
.rbtns{display:flex;gap:.3rem;flex-shrink:0}
.btn{border:none;padding:.45rem .8rem;border-radius:10px;cursor:pointer;font-size:.88rem;font-weight:600}
.send{background:#c87557;color:#fff}
.send:disabled{background:#555;cursor:not-allowed}
.mic{background:#222;border:1px solid #333;color:#eee}
.mic.rec{background:#dc2626;color:#fff;border-color:#dc2626}
.stop{background:#dc2626;color:#fff;display:none}
.stop.on{display:inline-block}
.step{background:#222;border:1px solid #333;border-radius:12px;padding:.9rem;margin-bottom:.8rem;animation:fd .3s}
.step.final{border-color:#c87557}
.step.spk{box-shadow:0 0 0 2px #4ade80}
@keyframes fd{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}
.sh{display:flex;align-items:center;gap:.5rem;margin-bottom:.55rem;font-weight:600;font-size:.9rem}
.bdg{padding:.15rem .45rem;border-radius:5px;font-size:.68rem;background:#111;color:#888;border:1px solid #333}
.sc{color:#ddd;line-height:1.6;white-space:pre-wrap;font-size:.9rem}
.spin{display:inline-block;width:12px;height:12px;border:2px solid #444;border-top-color:#c87557;border-radius:50%;animation:sp .7s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.empty{text-align:center;color:#666;padding:3rem 1rem}
.empty h2{color:#eee;margin-bottom:.4rem}
.mt{display:none;background:none;border:none;color:#eee;font-size:1.3rem;cursor:pointer;margin-right:.3rem}
.ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:99}
.ov.on{display:block}
.mp{display:none;position:absolute;top:52px;right:.8rem;background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:.8rem;box-shadow:0 8px 20px rgba(0,0,0,.4);z-index:200;min-width:185px}
.mp.open{display:block}
.mp-t{font-weight:600;font-size:.8rem;margin-bottom:.5rem;color:#eee}
.mc{display:flex;align-items:center;gap:.5rem;padding:.38rem .3rem;font-size:.85rem;border-radius:7px;cursor:pointer;color:#ddd}
.mc:hover{background:#333}
.mc input{width:15px;height:15px;accent-color:#c87557}
@media(max-width:680px){
  body{flex-direction:column}
  .sb{position:fixed;left:-230px;top:0;height:100vh;z-index:100;transition:left .25s}
  .sb.open{left:0}
  .mt{display:block}
  .main{height:100vh}
  .content,.ia{padding-left:.8rem;padding-right:.8rem}
}
</style>
</head>
<body>
<div class="ov" id="ov" onclick="closeSB()"></div>
<aside class="sb" id="sb">
  <button class="nb" onclick="newChat()">+ Yeni Sohbet</button>
  <button class="sbb" onclick="exportChat()">📥 İndir</button>
  <button class="sbb" onclick="featureReq()">✨ Özellik İste</button>
  <div class="sb-title">Geçmiş</div>
  <div id="hist"></div>
</aside>
<main class="main">
  <header class="hdr" style="position:relative">
    <div style="display:flex;align-items:center;gap:.4rem">
      <button class="mt" id="mt" onclick="toggleSB()">☰</button>
      <h1>🧠 Beyin Takımı</h1>
    </div>
    <div class="hbtns">
      <button class="ib" id="mBtn" onclick="toggleMP(event)">🤖</button>
      <button class="ib" id="dbBtn" onclick="toggleDB()">🥊</button>
      <button class="ib on" id="vBtn" onclick="toggleV()">🔊</button>
    </div>
    <div class="mp" id="mp">
      <div class="mp-t">Katılacak Modeller</div>
      <label class="mc"><input type="checkbox" id="mc_chatgpt" checked onchange="updateAM()"> ⚡ ChatGPT</label>
      <label class="mc"><input type="checkbox" id="mc_claude" checked onchange="updateAM()"> 🎭 Claude</label>
      <label class="mc"><input type="checkbox" id="mc_gemini" checked onchange="updateAM()"> ✨ Gemini</label>
      <label class="mc"><input type="checkbox" id="mc_deepseek" checked onchange="updateAM()"> 🔬 DeepSeek</label>
      <div style="font-size:.7rem;color:#666;margin-top:.4rem">En az 2 seçili olmalı</div>
    </div>
  </header>
  <div class="content" id="content">
    <div class="empty"><h2>🧠 Beyin Takımı</h2><p>Modu seç, sorunu yaz veya mikrofona bas.</p></div>
  </div>
  <div class="ia">
    <div class="iw">
      <textarea id="q" placeholder="Sorunu yaz..." rows="1" oninput="rsz(this)"></textarea>
      <div class="ctrl">
        <div class="sels">
          <div class="sw">
            <button class="sb2" id="modeBtn" onclick="openDrop(event,'modeDrop')">💬 Normal ▾</button>
            <div class="sm" id="modeDrop">
              <div class="si on" data-m="normal" onclick="pickMode(event,this)">💬 Normal</div>
              <div class="si" data-m="research" onclick="pickMode(event,this)">🔍 Araştırma</div>
              <div class="si" data-m="ideas" onclick="pickMode(event,this)">💡 Fikir Üret</div>
              <div class="si" data-m="critique" onclick="pickMode(event,this)">⚔️ Eleştir</div>
              <div class="si" data-m="roadmap" onclick="pickMode(event,this)">🗺️ Yol Haritası</div>
              <div class="si" data-m="report" onclick="pickMode(event,this)">📊 Rapor</div>
              <div class="si" data-m="startup" onclick="pickMode(event,this)">🚀 Startup</div>
              <div class="si ultra" onclick="pickUltra(event)">⚡ Ultra</div>
            </div>
          </div>
          <div class="sw">
            <button class="sb2" id="modelBtn" onclick="openDrop(event,'modelDrop')">🎯 Otomatik ▾</button>
            <div class="sm" id="modelDrop">
              <div class="si on" data-v="auto" onclick="pickModel(event,this)">🎯 Otomatik</div>
              <div class="si" data-v="chatgpt" onclick="pickModel(event,this)">⚡ ChatGPT</div>
              <div class="si" data-v="claude" onclick="pickModel(event,this)">🎭 Claude</div>
              <div class="si" data-v="gemini" onclick="pickModel(event,this)">✨ Gemini</div>
              <div class="si" data-v="deepseek" onclick="pickModel(event,this)">🔬 DeepSeek</div>
            </div>
          </div>
        </div>
        <div class="rbtns">
          <button class="btn stop" id="stopBtn" onclick="stopA()">⏹</button>
          <button class="btn mic" id="micBtn" onclick="toggleMic()">🎤</button>
          <button class="btn send" id="sendBtn" onclick="run()">Sor →</button>
        </div>
      </div>
    </div>
  </div>
</main>
<script>
var SM='auto',SMODES=['normal'],VX=true,DBX=false;
var AM=['chatgpt','claude','gemini','deepseek'];
var HIST=JSON.parse(localStorage.getItem('bt2')||'[]'),CID=null;
var REC=null,CH=[],RON=false,CAU=null;
var NAMES={chatgpt:'ChatGPT',claude:'Claude',gemini:'Gemini',deepseek:'DeepSeek'};
var COLORS={chatgpt:'#10a37f',claude:'#c87557',gemini:'#4285f4',deepseek:'#7c3aed'};

function openDrop(e,id){
  e.stopPropagation();
  var el=document.getElementById(id);
  var wasOpen=el.classList.contains('open');
  document.querySelectorAll('.sm').forEach(function(m){m.classList.remove('open');});
  if(!wasOpen)el.classList.add('open');
}
document.addEventListener('click',function(){
  document.querySelectorAll('.sm').forEach(function(m){m.classList.remove('open');});
  document.getElementById('mp').classList.remove('open');
});

function pickMode(e,el){
  e.stopPropagation();
  var m=el.dataset.m;
  if(el.classList.contains('on')&&SMODES.length>1){
    el.classList.remove('on');
    SMODES=SMODES.filter(function(x){return x!==m;});
  } else {
    el.classList.add('on');
    if(SMODES.indexOf(m)<0)SMODES.push(m);
  }
  var lbl={normal:'💬 Normal',research:'🔍 Araştırma',ideas:'💡 Fikir',critique:'⚔️ Eleştir',roadmap:'🗺️ Yol H.',report:'📊 Rapor',startup:'🚀 Startup'};
  document.getElementById('modeBtn').textContent=(SMODES.length===1?(lbl[SMODES[0]]||SMODES[0]):SMODES.length+' Mod')+' ▾';
}

function pickUltra(e){
  e.stopPropagation();
  SMODES=['ultra'];
  document.querySelectorAll('#modeDrop .si').forEach(function(i){i.classList.remove('on');});
  document.querySelector('.ultra').classList.add('on');
  document.getElementById('modeBtn').textContent='⚡ Ultra ▾';
  document.getElementById('modeDrop').classList.remove('open');
  DBX=true;document.getElementById('dbBtn').classList.add('on');
}

function pickModel(e,el){
  e.stopPropagation();
  SM=el.dataset.v;
  document.querySelectorAll('#modelDrop .si').forEach(function(i){i.classList.remove('on');});
  el.classList.add('on');
  document.getElementById('modelBtn').textContent=el.textContent.trim()+' ▾';
  document.getElementById('modelDrop').classList.remove('open');
}

function updateAM(){
  var all=['chatgpt','claude','gemini','deepseek'];
  var sel=all.filter(function(m){return document.getElementById('mc_'+m).checked;});
  if(sel.length<2){alert('En az 2 model!');event.target.checked=true;return;}
  AM=sel;
}

function toggleMP(e){e.stopPropagation();document.getElementById('mp').classList.toggle('open');}
function toggleDB(){DBX=!DBX;document.getElementById('dbBtn').classList.toggle('on',DBX);}
function toggleV(){VX=!VX;document.getElementById('vBtn').classList.toggle('on',VX);if(!VX)stopA();}
function toggleSB(){document.getElementById('sb').classList.toggle('open');document.getElementById('ov').classList.toggle('on');}
function closeSB(){document.getElementById('sb').classList.remove('open');document.getElementById('ov').classList.remove('on');}

function stopA(){if(CAU){CAU.pause();CAU=null;}document.querySelectorAll('.spk').forEach(function(e){e.classList.remove('spk');});document.getElementById('stopBtn').classList.remove('on');}

async function speak(text,model,eid){
  if(!VX||!text)return;
  return new Promise(function(res){
    fetch('/api/tts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text,model:model})})
    .then(function(r){return r.ok?r.blob():null;})
    .then(function(blob){
      if(!blob){res();return;}
      var url=URL.createObjectURL(blob),au=new Audio(url);CAU=au;
      if(eid){var el=document.getElementById(eid);if(el)el.classList.add('spk');}
      document.getElementById('stopBtn').classList.add('on');
      au.onended=function(){if(eid){var el=document.getElementById(eid);if(el)el.classList.remove('spk');}URL.revokeObjectURL(url);CAU=null;document.getElementById('stopBtn').classList.remove('on');res();};
      au.onerror=function(){URL.revokeObjectURL(url);res();};
      au.play().catch(res);
    }).catch(res);
  });
}

function toggleMic(){
  if(RON){REC.stop();return;}
  navigator.mediaDevices.getUserMedia({audio:true}).then(function(stream){
    REC=new MediaRecorder(stream);CH=[];
    REC.ondataavailable=function(e){CH.push(e.data);};
    REC.onstop=function(){
      stream.getTracks().forEach(function(t){t.stop();});
      var fd=new FormData();fd.append('audio',new Blob(CH,{type:'audio/webm'}),'a.webm');
      var mb=document.getElementById('micBtn');mb.innerHTML='<span class="spin"></span>';mb.classList.remove('rec');RON=false;
      fetch('/api/transcribe',{method:'POST',body:fd}).then(function(r){return r.json();}).then(function(d){
        if(d.text){document.getElementById('q').value=d.text;rsz(document.getElementById('q'));run();}
      }).finally(function(){mb.textContent='🎤';});
    };
    REC.start();RON=true;
    var mb=document.getElementById('micBtn');mb.classList.add('rec');mb.textContent='⏺';
  }).catch(function(e){alert('Mikrofon: '+e.message);});
}

function rsz(el){el.style.height='auto';el.style.height=Math.min(el.scrollHeight,160)+'px';}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function newChat(){CID=null;document.getElementById('q').value='';document.getElementById('content').innerHTML='<div class="empty"><h2>🧠 Yeni sohbet</h2><p>Sorunu yaz.</p></div>';renderH();stopA();closeSB();}
function renderH(){
  var h=document.getElementById('hist');
  h.innerHTML=HIST.slice().reverse().map(function(c){
    return '<div class="hi'+(c.id===CID?' on':'')+'" onclick="loadC(\''+c.id+'\')">'+esc(c.q.slice(0,36))+(c.q.length>36?'...':'')+'</div>';
  }).join('')||'<div style="font-size:.75rem;color:#555;padding:.3rem">Henuz yok</div>';
}
function loadC(id){var c=HIST.find(function(x){return x.id===id;});if(!c)return;CID=id;document.getElementById('content').innerHTML=c.html;renderH();closeSB();}
function saveC(q,html){
  if(CID){var c=HIST.find(function(x){return x.id===CID;});if(c){c.q=q;c.html=html;}}
  else{CID=String(Date.now());HIST.push({id:CID,q:q,html:html});}
  if(HIST.length>50)HIST.shift();
  localStorage.setItem('bt2',JSON.stringify(HIST));renderH();
}

function stp(id,title,body,badge,color){
  var el=document.getElementById(id);
  if(!el){el=document.createElement('div');el.id=id;el.className='step';document.getElementById('content').appendChild(el);}
  el.innerHTML='<div class="sh">'+title+(badge?'<span class="bdg">'+badge+'</span>':'')+'</div><div class="sc">'+body+'</div>';
  if(color)el.style.borderLeft='3px solid '+color;
  el.scrollIntoView({behavior:'smooth',block:'end'});
  return el;
}
function ld(id,title){stp(id,title,'<span class="spin"></span> İşleniyor...');}
function api(path,body){
  return fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
  .then(function(r){return r.json();}).then(function(d){if(d.error)throw new Error(d.error);return d;});
}

function exportChat(){
  if(!CID){alert('Once sohbet ac!');return;}
  var c=HIST.find(function(x){return x.id===CID;});if(!c)return;
  var tmp=document.createElement('div');tmp.innerHTML=c.html;
  var txt='BEYIN TAKIMI\n'+new Date().toLocaleString('tr-TR')+'\nSoru: '+c.q+'\n'+'='.repeat(50)+'\n\n';
  tmp.querySelectorAll('.step').forEach(function(s){
    var h=s.querySelector('.sh'),b=s.querySelector('.sc');
    if(h&&b)txt+=h.textContent.trim()+'\n'+'-'.repeat(30)+'\n'+b.textContent.trim()+'\n\n';
  });
  var a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([txt],{type:'text/plain;charset=utf-8'}));
  a.download='bt-'+Date.now()+'.txt';document.body.appendChild(a);a.click();document.body.removeChild(a);
}

function featureReq(){
  var f=prompt('Ne ozellik eklemek istiyorsun?');
  if(f&&f.trim())window.open('https://claude.ai/new?q='+encodeURIComponent('Beyin Takimi Flask uygulamama su ozelligi ekle: '+f),'_blank');
}

async function run(){
  var q=document.getElementById('q').value.trim();if(!q)return;
  document.getElementById('content').innerHTML='';
  var sb=document.getElementById('sendBtn');sb.disabled=true;sb.textContent='...';
  stopA();
  try{
    var chosen,name,color,icon;
    if(SM==='auto'){
      ld('s1','🎯 Yönlendirme');
      var r1=await api('/api/route',{question:q});
      chosen=r1.chosen;name=r1.name;color=r1.color;icon=r1.icon;
      stp('s1','🎯 Yönlendirme',esc(r1.reason),name,color);
    } else {
      chosen=SM;name=NAMES[chosen];color=COLORS[chosen];
      icon={chatgpt:'⚡',claude:'🎭',gemini:'✨',deepseek:'🔬'}[chosen];
      stp('s1','🎯 Manuel',esc(name),'Sen sectin',color);
    }
    ld('s2',icon+' '+name);
    var r2=await api('/api/answer',{question:q,model:chosen,modes:SMODES});
    stp('s2',icon+' '+name,esc(r2.answer),'Ana Cevap',color);
    await speak(r2.answer,chosen,'s2');

    var critics=AM.filter(function(m){return m!==chosen;});
    var critiques={};
    for(var i=0;i<critics.length;i++){
      var cr=critics[i];ld('c_'+cr,'🔍 '+NAMES[cr]);
      try{
        var c1=await api('/api/critique_one',{question:q,answer:r2.answer,critic:cr});
        stp('c_'+cr,c1.icon+' '+c1.name,esc(c1.text),'Elestiri',c1.color);
        critiques[cr]={name:c1.name,text:c1.text};
        await speak(c1.text,cr,'c_'+cr);
      }catch(e){}
    }

    if(DBX){
      ld('d1',icon+' savunuyor');
      try{
        var dr=await api('/api/defend',{question:q,answer:r2.answer,critiques:critiques,primary:chosen});
        stp('d1',dr.icon+' '+dr.name,esc(dr.text),'Savunma',dr.color);
        await speak(dr.text,chosen,'d1');
        for(var j=0;j<critics.length;j++){
          var c2=critics[j];ld('r2_'+c2,'⚔️ 2. Tur: '+NAMES[c2]);
          try{
            var cr2=await api('/api/critique_round2',{question:q,answer:r2.answer,defense:dr.text,critic:c2});
            stp('r2_'+c2,cr2.icon+' '+cr2.name,esc(cr2.text),'2. Tur',cr2.color);
            critiques[c2]={name:cr2.name,text:cr2.text};
            await speak(cr2.text,c2,'r2_'+c2);
          }catch(e){}
        }
      }catch(e){}
    }

    ld('s4','🏛️ Hakem');
    var r4=await api('/api/judge',{question:q,answer:r2.answer,critiques:critiques});
    var fe=stp('s4','🏛️ Nihai Cevap',esc(r4.final),'Hakem: '+r4.judge_name,'#c87557');
    fe.classList.add('final');
    await speak(r4.final,'judge','s4');
    saveC(q,document.getElementById('content').innerHTML);
    document.getElementById('q').value='';rsz(document.getElementById('q'));
  } catch(e){stp('err','⚠️ Hata',esc(e.message));}
  finally{sb.disabled=false;sb.textContent='Sor →';}
}

document.getElementById('q').addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();run();}});
document.addEventListener('keydown',function(e){if((e.metaKey||e.ctrlKey)&&e.shiftKey&&e.key.toLowerCase()==='m'){e.preventDefault();toggleMic();}});
renderH();
</script>
</body>
</html>"""

if __name__ == "__main__":
    app.run(debug=True, port=5000, host='0.0.0.0')
