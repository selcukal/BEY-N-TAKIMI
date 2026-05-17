from flask import Flask, request, jsonify, render_template_string, Response
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai
import os, json, re, requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

VOICE_IDS = {
    "chatgpt":  "ErXwobaYiN019PkySvjV",
    "claude":   "VR6AewLTigWG4xSOukaG",
    "gemini":   "TxGEqnHWrfWFTfGW9XjX",
    "deepseek": "VR6AewLTigWG4xSOukaG",
    "judge":    "EXAVITQu4vr4xnSDxMaL",
}

MODES = {
    "normal":   {"name":"Normal",       "icon":"💬", "prompt":"Sen uzman bir asistansin. Net ve dogru cevap ver."},
    "research": {"name":"Araştırma",    "icon":"🔍", "prompt":"Sen bir arastirmacisin. Soruyu derinlemesine arastir, kaynaklar ve veriler sun."},
    "ideas":    {"name":"Fikir Üret",   "icon":"💡", "prompt":"Sen yaratici bir fikir uretecisin. 5-7 yenilikci fikir sun."},
    "critique": {"name":"Eleştir",      "icon":"⚔️", "prompt":"Sen sert ama yapici bir elestirmensin. Zayif yonleri ve riskleri acikca soyle."},
    "roadmap":  {"name":"Yol Haritası", "icon":"🗺️", "prompt":"Sen strateji uzmanisin. Adim adim yol haritasi cikart."},
    "report":   {"name":"Rapor",        "icon":"📊", "prompt":"Sen analistsin. Profesyonel rapor yaz: ozet, analiz, sonuc, oneriler."},
    "startup":  {"name":"Startup",      "icon":"🚀", "prompt":"Sen girisimcilik mentorisin. Fikri girisimci gozuyle ele al: guc/zayiflik, hedef kitle, gelir modeli, rakipler, ilk adimlar, riskler."},
    "ultra":    {"name":"Ultra",        "icon":"⚡", "prompt":"Sen ultra kapsamli uzmansin. Konuyu her aciyla ele al: derinlemesine arastirma, yaratici fikirler, elestirel bakis, yol haritasi, profesyonel rapor, girisimci perspektifi."},
}

def ask_chatgpt(system, user):
    c = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    r = c.chat.completions.create(model="gpt-4o", max_tokens=2000,
        messages=[{"role":"system","content":system},{"role":"user","content":user}])
    return r.choices[0].message.content

def ask_claude(system, user):
    c = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    r = c.messages.create(model="claude-opus-4-5", max_tokens=2000, system=system,
        messages=[{"role":"user","content":user}])
    return r.content[0].text

def ask_gemini(system, user):
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    m = genai.GenerativeModel("gemini-flash-latest", system_instruction=system)
    return m.generate_content(user).text

def ask_deepseek(system, user):
    c = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com/v1")
    r = c.chat.completions.create(model="deepseek-chat", max_tokens=2000,
        messages=[{"role":"system","content":system},{"role":"user","content":user}])
    return r.choices[0].message.content

MODELS = {"chatgpt":ask_chatgpt,"claude":ask_claude,"gemini":ask_gemini,"deepseek":ask_deepseek}
NAMES = {"chatgpt":"ChatGPT","claude":"Claude","gemini":"Gemini","deepseek":"DeepSeek"}
COLORS = {"chatgpt":"#10a37f","claude":"#c87557","gemini":"#4285f4","deepseek":"#7c3aed"}
ICONS = {"chatgpt":"⚡","claude":"🎭","gemini":"✨","deepseek":"🔬"}

EXPERTISE = """- chatgpt: genel kultur, yaratici yazim, sohbet
- claude: uzun analiz, etik, kod incelemesi
- gemini: guncel bilgi, matematik
- deepseek: kod, algoritma, teknik problem"""

def pick_model(q):
    p = f"Soru: {q}\n\nModeller:\n{EXPERTISE}\n\nSADECE JSON: {{\"model\":\"<anahtar>\",\"reason\":\"<gerekce>\"}}"
    raw = ask_claude("Sen bir router'sin.", p)
    m = re.search(r'\{.*?\}', raw, re.DOTALL)
    if m:
        try:
            d = json.loads(m.group(0))
            if d.get("model") in MODELS:
                return d["model"], d.get("reason","")
        except: pass
    return "claude", "Varsayilan"

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/api/route", methods=["POST"])
def api_route():
    q = request.json.get("question","").strip()
    if not q: return jsonify({"error":"Soru bos"}), 400
    chosen, reason = pick_model(q)
    return jsonify({"chosen":chosen,"name":NAMES[chosen],"reason":reason,"color":COLORS[chosen],"icon":ICONS[chosen]})

@app.route("/api/answer", methods=["POST"])
def api_answer():
    d = request.json
    q = d.get("question","").strip()
    model = d.get("model","")
    modes = d.get("modes", ["normal"])
    if not q or model not in MODELS: return jsonify({"error":"Eksik"}), 400
    if len(modes) == 1:
        prompt = MODES.get(modes[0], MODES["normal"])["prompt"]
    else:
        parts = [MODES.get(m, MODES["normal"])["prompt"] for m in modes]
        prompt = "Su talimatlarin HEPSINI ayni anda uygula: " + " | ".join(parts)
    try:
        ans = MODELS[model](prompt, q)
        return jsonify({"answer":ans})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/api/critique_one", methods=["POST"])
def api_critique_one():
    d = request.json
    q, ans, critic = d.get("question",""), d.get("answer",""), d.get("critic","")
    if critic not in MODELS: return jsonify({"error":"Yanlis"}), 400
    try:
        text = MODELS[critic]("Sen elestirmensin. 3-4 cumlede eksik ve yanlis noktalari soyle.",
            f"SORU:\n{q}\n\nCEVAP:\n{ans}")
        return jsonify({"text":text,"name":NAMES[critic],"color":COLORS[critic],"icon":ICONS[critic]})
    except Exception as e:
        return jsonify({"text":"[Cevap alinamadi]","name":NAMES[critic],"color":COLORS[critic],"icon":ICONS[critic]})

@app.route("/api/defend", methods=["POST"])
def api_defend():
    d = request.json
    q, ans, crits, primary = d.get("question",""), d.get("answer",""), d.get("critiques",{}), d.get("primary","")
    if primary not in MODELS: return jsonify({"error":"Yanlis"}), 400
    cb = "\n".join(f"{v['name']}: {v['text']}" for v in crits.values())
    msg = f"SORU:\n{q}\n\nCEVABIN:\n{ans}\n\nELESTIRILER:\n{cb}\n\nElestirilere yanit ver. 4-5 cumle."
    try:
        text = MODELS[primary]("Elestirilere yanit veriyorsun.", msg)
        return jsonify({"text":text,"name":NAMES[primary],"color":COLORS[primary],"icon":ICONS[primary]})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/api/critique_round2", methods=["POST"])
def api_critique_round2():
    d = request.json
    q, ans, defense, critic = d.get("question",""), d.get("answer",""), d.get("defense",""), d.get("critic","")
    if critic not in MODELS: return jsonify({"error":"Yanlis"}), 400
    try:
        text = MODELS[critic]("Sen elestirmensin. Savunma tatmin edici mi? 3-4 cumle.",
            f"SORU:\n{q}\n\nILK CEVAP:\n{ans}\n\nSAVUNMA:\n{defense}")
        return jsonify({"text":text,"name":NAMES[critic],"color":COLORS[critic],"icon":ICONS[critic]})
    except Exception as e:
        return jsonify({"text":"[Cevap alinamadi]","name":NAMES[critic],"color":COLORS[critic],"icon":ICONS[critic]})

@app.route("/api/judge", methods=["POST"])
def api_judge():
    d = request.json
    q, ans, crits = d.get("question",""), d.get("answer",""), d.get("critiques",{})
    cb = "\n\n".join(f"{v['name']}: {v['text']}" for v in crits.values()) or "(yok)"
    msg = f"SORU:\n{q}\n\nANA CEVAP:\n{ans}\n\nELESTIRILER:\n{cb}"
    judge_model, _ = pick_model(q)
    try:
        final = MODELS[judge_model]("Sen hakemsin. Tum girdileri sentezle, tek nihai cevap yaz.", msg)
        return jsonify({"final":final,"judge_name":NAMES[judge_model]})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/api/transcribe", methods=["POST"])
def api_transcribe():
    if 'audio' not in request.files: return jsonify({"error":"ses yok"}), 400
    f = request.files['audio']
    try:
        c = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        r = c.audio.transcriptions.create(model="whisper-1", file=("audio.webm", f.read(), "audio/webm"), language="tr")
        return jsonify({"text":r.text})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/api/tts", methods=["POST"])
def api_tts():
    d = request.json
    text = d.get("text","").strip()
    model = d.get("model","claude")
    if not text: return jsonify({"error":"metin yok"}), 400
    if not ELEVENLABS_KEY: return jsonify({"error":"key yok"}), 500
    voice_id = VOICE_IDS.get(model, VOICE_IDS["judge"])
    clean = re.sub(r'[#*_`]','',text).strip()[:2500]
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        headers = {"xi-api-key":ELEVENLABS_KEY,"Content-Type":"application/json"}
        body = {"text":clean,"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.5,"similarity_boost":0.75}}
        r = requests.post(url, json=body, headers=headers, stream=True)
        if r.status_code != 200: return jsonify({"error":f"ElevenLabs:{r.status_code}"}), 500
        return Response((chunk for chunk in r.iter_content(4096) if chunk), mimetype="audio/mpeg")
    except Exception as e:
        return jsonify({"error":str(e)}), 500

HTML = '''<!DOCTYPE html><html lang="tr"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Beyin Takimi">
<title>Beyin Takimi</title>
<link rel="apple-touch-icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='22' fill='%23fff'/%3E%3Ctext x='50' y='72' text-anchor='middle' font-size='68'%3E%F0%9F%A7%A0%3C/text%3E%3C/svg%3E">
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
:root{--bg:#fff;--panel:#f5f5f7;--border:#e5e5ea;--text:#1c1c1e;--muted:#8e8e93;--accent:#c87557}
[data-theme=dark]{--bg:#0a0a0b;--panel:#141417;--border:#26262b;--text:#ededee;--muted:#888}
body{font-family:-apple-system,BlinkMacSystemFont,system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;transition:background .2s,color .2s}
.sidebar{width:240px;background:var(--panel);border-right:1px solid var(--border);padding:1rem;display:flex;flex-direction:column;gap:.4rem;overflow-y:auto;flex-shrink:0}
.sidebar-title{font-size:.7rem;text-transform:uppercase;color:var(--muted);margin:.8rem 0 .3rem;letter-spacing:.5px;font-weight:600}
.new-btn{background:var(--accent);color:#fff;border:none;padding:.7rem;border-radius:12px;cursor:pointer;font-size:.9rem;font-weight:600}
.side-btn{background:transparent;border:1px solid var(--border);color:var(--text);padding:.55rem .7rem;border-radius:10px;cursor:pointer;font-size:.82rem;text-align:left;display:flex;align-items:center;gap:.4rem}
.side-btn:hover{background:var(--bg)}
.hist-item{padding:.55rem .7rem;border-radius:8px;cursor:pointer;font-size:.82rem;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border:1px solid transparent}
.hist-item:hover,.hist-item.active{background:var(--bg);border-color:var(--border)}
.main{flex:1;display:flex;flex-direction:column;height:100vh;overflow:hidden}
.header{padding:.85rem 1.2rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--bg);position:relative}
.header h1{font-size:1.05rem;font-weight:700;display:flex;align-items:center;gap:.4rem}
.head-btns{display:flex;gap:.3rem}
.icon-btn{background:transparent;border:1px solid var(--border);color:var(--text);padding:.38rem .55rem;border-radius:10px;cursor:pointer;font-size:.9rem;line-height:1}
.icon-btn:hover{background:var(--panel)}
.icon-btn.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.models-panel{display:none;position:absolute;top:56px;right:1rem;background:var(--bg);border:1px solid var(--border);border-radius:14px;padding:.8rem;box-shadow:0 8px 24px rgba(0,0,0,.12);z-index:200;min-width:190px}
.models-panel.open{display:block}
.mp-title{font-weight:600;font-size:.82rem;margin-bottom:.5rem;color:var(--text)}
.mp-item{display:flex;align-items:center;gap:.5rem;padding:.4rem .3rem;font-size:.88rem;border-radius:8px;cursor:pointer}
.mp-item:hover{background:var(--panel)}
.mp-item input{width:16px;height:16px;accent-color:var(--accent)}
.content{flex:1;overflow-y:auto;padding:1.2rem;max-width:860px;width:100%;margin:0 auto}
.input-area{padding:.7rem 1.2rem 1rem;background:var(--bg);border-top:1px solid var(--border)}
.input-wrap{max-width:860px;margin:0 auto;background:var(--panel);border:1px solid var(--border);border-radius:18px;padding:.7rem}
.input-wrap:focus-within{border-color:var(--accent)}
textarea{width:100%;background:transparent;border:none;color:var(--text);font-size:1rem;resize:none;outline:none;font-family:inherit;min-height:44px;max-height:180px}
.controls{display:flex;justify-content:space-between;align-items:center;margin-top:.4rem;gap:.4rem}
.selectors{display:flex;gap:.35rem;flex:1;min-width:0}
.sel-wrap{position:relative;flex:1}
.sel-btn{width:100%;padding:.42rem .65rem;background:var(--bg);border:1px solid var(--border);border-radius:10px;color:var(--text);font-size:.78rem;cursor:pointer;display:flex;align-items:center;justify-content:space-between;font-family:inherit;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sel-btn:hover{border-color:var(--accent)}
.sel-menu{display:none;position:absolute;bottom:calc(100% + 4px);left:0;background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:.3rem;box-shadow:0 8px 24px rgba(0,0,0,.12);z-index:50;min-width:170px;max-height:300px;overflow-y:auto}
.sel-menu.open{display:block}
.sel-item{padding:.48rem .65rem;border-radius:8px;cursor:pointer;font-size:.85rem;display:flex;align-items:center;gap:.4rem;white-space:nowrap}
.sel-item:hover{background:var(--panel)}
.sel-item.on{background:var(--accent);color:#fff}
.ultra-item{background:linear-gradient(135deg,#f97316,#c87557);color:#fff;font-weight:600;margin-top:.3rem}
.ultra-item:hover{opacity:.9}
.btns{display:flex;gap:.35rem;flex-shrink:0}
.btn{border:none;padding:.48rem .85rem;border-radius:12px;cursor:pointer;font-size:.9rem;font-weight:600;line-height:1}
.send{background:var(--accent);color:#fff}
.send:disabled{background:#bbb;cursor:not-allowed}
.mic{background:var(--panel);border:1px solid var(--border);color:var(--text)}
.mic.rec{background:#dc2626;color:#fff;border-color:#dc2626;animation:pulse 1s infinite}
.stop{background:#dc2626;color:#fff;display:none}
.stop.on{display:inline-block}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.6}}
.step{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:1rem;margin-bottom:.9rem;animation:fade .35s}
.step.final{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent)}
.step.speaking{box-shadow:0 0 0 2px #4ade80}
@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.sh{display:flex;align-items:center;gap:.5rem;margin-bottom:.6rem;font-weight:600;font-size:.92rem}
.badge{padding:.18rem .5rem;border-radius:6px;font-size:.7rem;font-weight:500;background:var(--bg);color:var(--muted);border:1px solid var(--border)}
.sc{color:var(--text);line-height:1.65;white-space:pre-wrap;font-size:.93rem;opacity:.9}
.spin{display:inline-block;width:13px;height:13px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.empty{text-align:center;color:var(--muted);padding:3rem 1rem}
.empty h2{color:var(--text);margin-bottom:.5rem;font-size:1.3rem}
.menu-toggle{display:none;background:none;border:none;color:var(--text);font-size:1.4rem;cursor:pointer;padding:0;margin-right:.3rem}
@media(max-width:720px){
  body{flex-direction:column}
  .sidebar{position:fixed;left:-260px;top:0;height:100vh;z-index:100;transition:left .3s;box-shadow:2px 0 20px rgba(0,0,0,.1)}
  .sidebar.open{left:0}
  .menu-toggle{display:block}
  .main{height:100vh}
  .content,.input-area{padding-left:.9rem;padding-right:.9rem}
  .header{padding:.7rem .9rem}
}
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:99}
.overlay.show{display:block}
</style></head><body data-theme="light">
<div class="overlay" id="ov" onclick="closeAll()"></div>
<aside class="sidebar" id="sb">
  <button class="new-btn" onclick="newChat()">+ Yeni Sohbet</button>
  <button class="side-btn" onclick="exportChat()">📥 Sohbeti İndir</button>
  <button class="side-btn" onclick="requestFeature()">✨ Özellik İste</button>
  <div class="sidebar-title">Geçmiş</div>
  <div id="hist"></div>
</aside>
<main class="main">
  <header class="header">
    <button class="menu-toggle" onclick="toggleSB()">☰</button>
    <h1>🧠 Beyin Takımı</h1>
    <div class="head-btns">
      <button class="icon-btn" id="themeBtn" onclick="toggleTheme()">☀️</button>
      <button class="icon-btn" id="mBtn" onclick="toggleMP()">🤖</button>
      <button class="icon-btn" id="dbBtn" onclick="toggleDebate()">🥊</button>
      <button class="icon-btn on" id="voiceBtn" onclick="toggleVoice()">🔊</button>
    </div>
    <div class="models-panel" id="mp">
      <div class="mp-title">Katılacak Modeller</div>
      <label class="mp-item"><input type="checkbox" id="mc_chatgpt" checked onchange="updateModels()"> ⚡ ChatGPT</label>
      <label class="mp-item"><input type="checkbox" id="mc_claude" checked onchange="updateModels()"> 🎭 Claude</label>
      <label class="mp-item"><input type="checkbox" id="mc_gemini" checked onchange="updateModels()"> ✨ Gemini</label>
      <label class="mp-item"><input type="checkbox" id="mc_deepseek" checked onchange="updateModels()"> 🔬 DeepSeek</label>
      <div style="font-size:.72rem;color:var(--muted);margin-top:.4rem">En az 2 model seçili olmalı</div>
    </div>
  </header>
  <div class="content" id="content">
    <div class="empty"><h2>🧠 Beyin Takımı</h2><p>Modu ve modeli seç, sorunu yaz.</p></div>
  </div>
  <div class="input-area">
    <div class="input-wrap">
      <textarea id="q" placeholder="Sorunu yaz..." rows="1" oninput="resize(this)"></textarea>
      <div class="controls">
        <div class="selectors">
          <div class="sel-wrap">
            <button class="sel-btn" id="modeBtn" onclick="toggleDrop('modeDrop')"><span id="modeLbl">💬 Normal</span> ▾</button>
            <div class="sel-menu" id="modeDrop">
              <div class="sel-item on" data-m="normal" onclick="pickMode(this)">💬 Normal</div>
              <div class="sel-item" data-m="research" onclick="pickMode(this)">🔍 Araştırma</div>
              <div class="sel-item" data-m="ideas" onclick="pickMode(this)">💡 Fikir Üret</div>
              <div class="sel-item" data-m="critique" onclick="pickMode(this)">⚔️ Eleştir</div>
              <div class="sel-item" data-m="roadmap" onclick="pickMode(this)">🗺️ Yol Haritası</div>
              <div class="sel-item" data-m="report" onclick="pickMode(this)">📊 Rapor</div>
              <div class="sel-item" data-m="startup" onclick="pickMode(this)">🚀 Startup</div>
              <div class="sel-item ultra-item" onclick="pickUltra()">⚡ Ultra (Hepsi)</div>
            </div>
          </div>
          <div class="sel-wrap">
            <button class="sel-btn" id="modelBtn" onclick="toggleDrop('modelDrop')"><span id="modelLbl">🎯 Otomatik</span> ▾</button>
            <div class="sel-menu" id="modelDrop">
              <div class="sel-item on" data-v="auto" onclick="pickModel(this)">🎯 Otomatik</div>
              <div class="sel-item" data-v="chatgpt" onclick="pickModel(this)">⚡ ChatGPT</div>
              <div class="sel-item" data-v="claude" onclick="pickModel(this)">🎭 Claude</div>
              <div class="sel-item" data-v="gemini" onclick="pickModel(this)">✨ Gemini</div>
              <div class="sel-item" data-v="deepseek" onclick="pickModel(this)">🔬 DeepSeek</div>
            </div>
          </div>
        </div>
        <div class="btns">
          <button class="btn stop" id="stopBtn" onclick="stopAudio()">⏹</button>
          <button class="btn mic" id="micBtn" onclick="toggleMic()">🎤</button>
          <button class="btn send" id="sendBtn" onclick="run()">Sor →</button>
        </div>
      </div>
    </div>
  </div>
</main>
<script>
var selModel='auto', selModes=['normal'], voiceOn=true, debateOn=false;
var activeModels=['chatgpt','claude','gemini','deepseek'];
var hist=JSON.parse(localStorage.getItem('bt')||'[]'), chatId=null;
var recorder=null, chunks=[], recOn=false, curAudio=null;
var content=document.getElementById('content');
var sendBtn=document.getElementById('sendBtn');
var micBtn=document.getElementById('micBtn');
var stopBtn=document.getElementById('stopBtn');

// Theme
var theme=localStorage.getItem('bt_theme')||'light';
document.body.dataset.theme=theme;
document.getElementById('themeBtn').textContent=theme==='light'?'☀️':'🌙';
function toggleTheme(){theme=theme==='light'?'dark':'light';document.body.dataset.theme=theme;localStorage.setItem('bt_theme',theme);document.getElementById('themeBtn').textContent=theme==='light'?'☀️':'🌙';}

// Dropdown
function toggleDrop(id){document.querySelectorAll('.sel-menu').forEach(function(m){if(m.id!==id)m.classList.remove('open');});document.getElementById(id).classList.toggle('open');}
document.addEventListener('click',function(e){if(!e.target.closest('.sel-wrap')){document.querySelectorAll('.sel-menu').forEach(function(m){m.classList.remove('open');});}});

// Mode
function pickMode(el){
  var m=el.dataset.m;
  if(el.classList.contains('on')&&selModes.length>1){el.classList.remove('on');selModes=selModes.filter(function(x){return x!==m;});}
  else{el.classList.add('on');if(selModes.indexOf(m)<0)selModes.push(m);}
  updateModeLbl();
  document.getElementById('modeDrop').classList.remove('open');
}
function pickUltra(){
  selModes=['ultra'];
  document.querySelectorAll('#modeDrop .sel-item').forEach(function(i){i.classList.remove('on');});
  document.querySelector('.ultra-item').classList.add('on');
  document.getElementById('modeLbl').textContent='⚡ Ultra';
  document.getElementById('modeDrop').classList.remove('open');
  debateOn=true;document.getElementById('dbBtn').classList.add('on');
}
function updateModeLbl(){
  var icons={normal:'💬 Normal',research:'🔍 Araştırma',ideas:'💡 Fikir',critique:'⚔️ Eleştir',roadmap:'🗺️ Yol H.',report:'📊 Rapor',startup:'🚀 Startup'};
  document.getElementById('modeLbl').textContent=selModes.length===1?(icons[selModes[0]]||selModes[0]):selModes.length+' Mod';
}

// Model
function pickModel(el){selModel=el.dataset.v;document.querySelectorAll('#modelDrop .sel-item').forEach(function(i){i.classList.remove('on');});el.classList.add('on');document.getElementById('modelLbl').textContent=el.textContent.trim();document.getElementById('modelDrop').classList.remove('open');}

// Active models
function updateModels(){
  var all=['chatgpt','claude','gemini','deepseek'];
  var sel=all.filter(function(m){return document.getElementById('mc_'+m).checked;});
  if(sel.length<2){alert('En az 2 model!');event.target.checked=true;return;}
  activeModels=sel;
}

// Toggle
function toggleDebate(){debateOn=!debateOn;document.getElementById('dbBtn').classList.toggle('on',debateOn);}
function toggleVoice(){voiceOn=!voiceOn;document.getElementById('voiceBtn').classList.toggle('on',voiceOn);if(!voiceOn)stopAudio();}
function toggleMP(){document.getElementById('mp').classList.toggle('open');}
document.addEventListener('click',function(e){if(!e.target.closest('#mp')&&!e.target.closest('#mBtn'))document.getElementById('mp').classList.remove('open');});

// Sidebar
function toggleSB(){document.getElementById('sb').classList.toggle('open');document.getElementById('ov').classList.toggle('show');}
function closeAll(){document.getElementById('sb').classList.remove('open');document.getElementById('ov').classList.remove('show');}

// Audio
async function speak(text,model,eid){
  if(!voiceOn||!text)return;
  return new Promise(function(resolve){
    fetch('/api/tts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text,model:model})})
    .then(function(r){if(!r.ok){resolve();return null;}return r.blob();})
    .then(function(blob){
      if(!blob){resolve();return;}
      var url=URL.createObjectURL(blob);
      var audio=new Audio(url);curAudio=audio;
      if(eid){var el=document.getElementById(eid);if(el)el.classList.add('speaking');}
      stopBtn.classList.add('on');
      audio.onended=function(){if(eid){var el=document.getElementById(eid);if(el)el.classList.remove('speaking');}URL.revokeObjectURL(url);curAudio=null;stopBtn.classList.remove('on');resolve();};
      audio.onerror=function(){URL.revokeObjectURL(url);resolve();};
      audio.play().catch(function(){resolve();});
    }).catch(function(){resolve();});
  });
}
function stopAudio(){if(curAudio){curAudio.pause();curAudio=null;}document.querySelectorAll('.step.speaking').forEach(function(e){e.classList.remove('speaking');});stopBtn.classList.remove('on');}

// Mic
function toggleMic(){
  if(recOn){recorder.stop();return;}
  navigator.mediaDevices.getUserMedia({audio:true}).then(function(stream){
    recorder=new MediaRecorder(stream);chunks=[];
    recorder.ondataavailable=function(e){chunks.push(e.data);};
    recorder.onstop=function(){
      stream.getTracks().forEach(function(t){t.stop();});
      var blob=new Blob(chunks,{type:'audio/webm'});
      var fd=new FormData();fd.append('audio',blob,'audio.webm');
      micBtn.innerHTML='<span class="spin"></span>';micBtn.classList.remove('rec');recOn=false;
      fetch('/api/transcribe',{method:'POST',body:fd}).then(function(r){return r.json();}).then(function(d){
        if(d.text){document.getElementById('q').value=d.text;resize(document.getElementById('q'));run();}
      }).catch(function(){}).finally(function(){micBtn.textContent='🎤';});
    };
    recorder.start();recOn=true;micBtn.classList.add('rec');micBtn.textContent='⏺';
  }).catch(function(e){alert('Mikrofon izni: '+e.message);});
}

// Helpers
function resize(el){el.style.height='auto';el.style.height=Math.min(el.scrollHeight,180)+'px';}
function esc(s){return String(s).replace(/[&<>"']/g,function(c){return({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]);});}
function newChat(){chatId=null;document.getElementById('q').value='';content.innerHTML='<div class="empty"><h2>🧠 Yeni sohbet</h2><p>Sorunu yaz.</p></div>';renderHist();stopAudio();closeAll();}
function renderHist(){
  var h=document.getElementById('hist');
  h.innerHTML=hist.slice().reverse().map(function(c){
    return '<div class="hist-item'+(c.id===chatId?' active':'')+'" onclick="loadChat(\''+c.id+'\')">'+esc(c.q.slice(0,38))+(c.q.length>38?'...':'')+'</div>';
  }).join('')||'<div style="font-size:.78rem;color:var(--muted);padding:.3rem">Henuz yok</div>';
}
function loadChat(id){var c=hist.find(function(x){return x.id===id;});if(!c)return;chatId=id;content.innerHTML=c.html;renderHist();closeAll();}
function saveChat(q,html){
  if(chatId){var c=hist.find(function(x){return x.id===chatId;});if(c){c.q=q;c.html=html;}}
  else{chatId=String(Date.now());hist.push({id:chatId,q:q,html:html});}
  if(hist.length>50)hist.shift();
  localStorage.setItem('bt',JSON.stringify(hist));renderHist();
}
function step(id,title,body,badge,color){
  var el=document.getElementById(id);
  if(!el){el=document.createElement('div');el.id=id;el.className='step';content.appendChild(el);}
  el.innerHTML='<div class="sh">'+title+(badge?'<span class="badge">'+badge+'</span>':'')+'</div><div class="sc">'+body+'</div>';
  if(color)el.style.borderLeft='3px solid '+color;
  el.scrollIntoView({behavior:'smooth',block:'end'});
  return el;
}
function loading(id,title){step(id,title,'<span class="spin"></span> İşleniyor...');}
function apicall(path,body){
  return fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
  .then(function(r){return r.json();})
  .then(function(d){if(d.error)throw new Error(d.error);return d;});
}

// Export
function exportChat(){
  if(!chatId){alert('Once bir sohbet ac!');return;}
  var c=hist.find(function(x){return x.id===chatId;});if(!c)return;
  var tmp=document.createElement('div');tmp.innerHTML=c.html;
  var txt='BEYIN TAKIMI\nTarih: '+new Date().toLocaleString('tr-TR')+'\nSoru: '+c.q+'\n'+'='.repeat(50)+'\n\n';
  tmp.querySelectorAll('.step').forEach(function(s){
    var h=s.querySelector('.sh');var b=s.querySelector('.sc');
    if(h&&b)txt+=h.textContent.trim()+'\n'+'-'.repeat(40)+'\n'+b.textContent.trim()+'\n\n';
  });
  var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([txt],{type:'text/plain;charset=utf-8'}));
  a.download='beyin-takimi-'+Date.now()+'.txt';document.body.appendChild(a);a.click();document.body.removeChild(a);
}

// Feature request
function requestFeature(){
  var f=prompt('Ne ozellik eklemek istiyorsun?');
  if(!f||!f.trim())return;
  window.open('https://claude.ai/new?q='+encodeURIComponent('Beyin Takimi uygulamama su ozelligi ekle: '+f),'_blank');
}

// Main run
async function run(){
  var q=document.getElementById('q').value.trim();if(!q)return;
  content.innerHTML='';sendBtn.disabled=true;sendBtn.textContent='...';stopAudio();
  try{
    var chosen,name,reason,color,icon;
    if(selModel==='auto'){
      loading('s1','🎯 Yönlendirme');
      var r1=await apicall('/api/route',{question:q});
      chosen=r1.chosen;name=r1.name;reason=r1.reason;color=r1.color;icon=r1.icon;
      step('s1','🎯 Yönlendirme',esc(reason),name,color);
    }else{
      chosen=selModel;
      var nm={chatgpt:'ChatGPT',claude:'Claude',gemini:'Gemini',deepseek:'DeepSeek'};
      var cl={chatgpt:'#10a37f',claude:'#c87557',gemini:'#4285f4',deepseek:'#7c3aed'};
      var ic={chatgpt:'⚡',claude:'🎭',gemini:'✨',deepseek:'🔬'};
      name=nm[chosen];color=cl[chosen];icon=ic[chosen];
      step('s1','🎯 Manuel',esc(name),'Sen sectin',color);
    }
    loading('s2',icon+' '+name);
    var r2=await apicall('/api/answer',{question:q,model:chosen,modes:selModes});
    step('s2',icon+' '+name,esc(r2.answer),'Ana Cevap',color);
    await speak(r2.answer,chosen,'s2');

    var critics=activeModels.filter(function(m){return m!==chosen;});
    var critiques={};
    for(var i=0;i<critics.length;i++){
      var critic=critics[i];var cid='c_'+critic;
      loading(cid,'🔍 '+NAMES_JS[critic]);
      try{
        var cr=await apicall('/api/critique_one',{question:q,answer:r2.answer,critic:critic});
        step(cid,cr.icon+' '+cr.name,esc(cr.text),'Elestiri',cr.color);
        critiques[critic]={name:cr.name,text:cr.text};
        await speak(cr.text,critic,cid);
      }catch(e){}
    }

    if(debateOn){
      loading('d1',icon+' '+name+' savunuyor');
      try{
        var dr=await apicall('/api/defend',{question:q,answer:r2.answer,critiques:critiques,primary:chosen});
        step('d1',dr.icon+' '+dr.name,esc(dr.text),'Savunma',dr.color);
        await speak(dr.text,chosen,'d1');
        for(var j=0;j<critics.length;j++){
          var c2=critics[j];var c2id='r2_'+c2;
          loading(c2id,'⚔️ 2. Tur: '+NAMES_JS[c2]);
          try{
            var cr2=await apicall('/api/critique_round2',{question:q,answer:r2.answer,defense:dr.text,critic:c2});
            step(c2id,cr2.icon+' '+cr2.name,esc(cr2.text),'2. Tur',cr2.color);
            critiques[c2]={name:cr2.name,text:cr2.text};
            await speak(cr2.text,c2,c2id);
          }catch(e){}
        }
      }catch(e){}
    }

    loading('s4','🏛️ Hakem');
    var r4=await apicall('/api/judge',{question:q,answer:r2.answer,critiques:critiques});
    var fe=step('s4','🏛️ Nihai Cevap',esc(r4.final),'Hakem: '+r4.judge_name,'#c87557');
    fe.classList.add('final');
    await speak(r4.final,'judge','s4');
    saveChat(q,content.innerHTML);
    document.getElementById('q').value='';resize(document.getElementById('q'));
  }catch(e){step('err','⚠️ Hata',esc(e.message));}
  finally{sendBtn.disabled=false;sendBtn.textContent='Sor →';}
}

var NAMES_JS={chatgpt:'ChatGPT',claude:'Claude',gemini:'Gemini',deepseek:'DeepSeek'};

document.getElementById('q').addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();run();}});
document.addEventListener('keydown',function(e){if((e.metaKey||e.ctrlKey)&&e.shiftKey&&e.key.toLowerCase()==='m'){e.preventDefault();document.getElementById('q').focus();toggleMic();}});
renderHist();
</script></body></html>'''

if __name__ == "__main__":
    app.run(debug=True, port=5000, host='0.0.0.0')
