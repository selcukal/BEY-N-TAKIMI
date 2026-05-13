from flask import Flask, request, jsonify, render_template_string
from openai import OpenAI
from anthropic import Anthropic
import google.generativeai as genai
import os, json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

def ask_chatgpt(system, user):
    c = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    r = c.chat.completions.create(model="gpt-4o", max_tokens=1500,
        messages=[{"role":"system","content":system},{"role":"user","content":user}])
    return r.choices[0].message.content

def ask_claude(system, user):
    c = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    r = c.messages.create(model="claude-opus-4-5", max_tokens=1500, system=system,
        messages=[{"role":"user","content":user}])
    return r.content[0].text

def ask_gemini(system, user):
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    m = genai.GenerativeModel("gemini-flash-latest", system_instruction=system)
    return m.generate_content(user).text

def ask_deepseek(system, user):
    c = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com/v1")
    r = c.chat.completions.create(model="deepseek-chat", max_tokens=1500,
        messages=[{"role":"system","content":system},{"role":"user","content":user}])
    return r.choices[0].message.content

MODELS = {"chatgpt": ask_chatgpt, "claude": ask_claude, "gemini": ask_gemini, "deepseek": ask_deepseek}
NAMES = {"chatgpt":"ChatGPT", "claude":"Claude", "gemini":"Gemini", "deepseek":"DeepSeek"}
COLORS = {"chatgpt":"#10a37f", "claude":"#c87557", "gemini":"#4285f4", "deepseek":"#7c3aed"}
ICONS = {"chatgpt":"⚡", "claude":"🎭", "gemini":"✨", "deepseek":"🔬"}

EXPERTISE = """- chatgpt: genel kültür, yaratıcı yazım, sohbet
- claude: uzun analiz, etik, kod incelemesi, yapılandırılmış düşünme
- gemini: güncel bilgi, matematik, çok dilli görevler
- deepseek: kod, algoritma, teknik problem"""

def pick_model(q):
    p = f"Soru: {q}\n\nModeller:\n{EXPERTISE}\n\nSADECE JSON: {{\"model\":\"<anahtar>\",\"reason\":\"<gerekce>\"}}"
    raw = ask_claude("Sen bir router'sın.", p)
    m = re.search(r'\{.*?\}', raw, re.DOTALL)
    if m:
        try:
            d = json.loads(m.group(0))
            if d.get("model") in MODELS:
                return d["model"], d.get("reason","")
        except: pass
    return "claude", "Varsayılan"

@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/api/route", methods=["POST"])
def api_route():
    q = request.json.get("question","").strip()
    if not q: return jsonify({"error":"Soru bos"}), 400
    chosen, reason = pick_model(q)
    return jsonify({"chosen": chosen, "name": NAMES[chosen], "reason": reason, "color": COLORS[chosen], "icon": ICONS[chosen]})

@app.route("/api/answer", methods=["POST"])
def api_answer():
    d = request.json
    q, model = d.get("question","").strip(), d.get("model","")
    if not q or model not in MODELS: return jsonify({"error":"Eksik"}), 400
    try:
        ans = MODELS[model]("Sen uzman bir asistansin. Net ve dogru cevap ver.", q)
        return jsonify({"answer": ans})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/critique", methods=["POST"])
def api_critique():
    d = request.json
    q, ans, primary = d.get("question",""), d.get("answer",""), d.get("primary","")
    critics = [m for m in MODELS if m != primary]
    results = {}
    def crit(m):
        try:
            return m, MODELS[m]("Sen elestirmensin. 4-5 cumlede dogru ve eksik noktalari soyle.",
                f"SORU:\n{q}\n\nCEVAP:\n{ans}")
        except Exception as e:
            return m, f"[Bu model su an cevap veremedi]"
    with ThreadPoolExecutor(max_workers=3) as ex:
        for f in as_completed([ex.submit(crit, m) for m in critics]):
            k, v = f.result()
            results[k] = {"name": NAMES[k], "text": v, "color": COLORS[k], "icon": ICONS[k]}
    return jsonify({"critiques": results})

@app.route("/api/judge", methods=["POST"])
def api_judge():
    d = request.json
    q, ans, crits = d.get("question",""), d.get("answer",""), d.get("critiques",{})
    cb = "\n\n".join(f"### {v['name']}\n{v['text']}" for v in crits.values()) or "(yok)"
    msg = f"SORU:\n{q}\n\nANA CEVAP:\n{ans}\n\nELESTIRILER:\n{cb}"
    try:
        final = ask_claude("Sen hakemsin. Tum girdileri sentezle, kullaniciya yonelik tek nihai cevap yaz. Sureci anlatma.", msg)
        return jsonify({"final": final})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

HTML = """<!DOCTYPE html><html lang="tr"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="AI Council">
<title>AI Council</title>
<link rel="apple-touch-icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='22' fill='%230a0a0b'/%3E%3Ctext x='50' y='68' text-anchor='middle' font-size='60'%3E🏛️%3C/text%3E%3C/svg%3E">
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
:root{--bg:#0a0a0b;--panel:#141417;--border:#26262b;--text:#ededee;--muted:#888;--accent:#c87557}
body{font-family:-apple-system,BlinkMacSystemFont,system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex}
.sidebar{width:260px;background:#0f0f11;border-right:1px solid var(--border);padding:1rem;display:flex;flex-direction:column;gap:.5rem;overflow-y:auto;flex-shrink:0}
.sidebar h2{font-size:.75rem;text-transform:uppercase;color:var(--muted);margin:1rem 0 .5rem;letter-spacing:.5px}
.new-btn{background:var(--accent);color:#fff;border:none;padding:.7rem;border-radius:10px;cursor:pointer;font-size:.9rem;font-weight:500;margin-bottom:.5rem}
.new-btn:hover{opacity:.9}
.hist-item{padding:.6rem .8rem;background:transparent;border-radius:8px;cursor:pointer;font-size:.85rem;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border:1px solid transparent}
.hist-item:hover{background:#1a1a1d;border-color:var(--border)}
.hist-item.active{background:#1a1a1d;border-color:var(--border)}
.main{flex:1;display:flex;flex-direction:column;height:100vh;overflow:hidden}
.header{padding:1rem 1.5rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}
.header h1{font-size:1.1rem;display:flex;align-items:center;gap:.5rem}
.content{flex:1;overflow-y:auto;padding:1.5rem;max-width:900px;width:100%;margin:0 auto}
.input-area{padding:1rem 1.5rem;border-top:1px solid var(--border);background:var(--bg)}
.input-wrap{max-width:900px;margin:0 auto;background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:.8rem}
.input-wrap:focus-within{border-color:var(--accent)}
textarea{width:100%;background:transparent;border:none;color:var(--text);font-size:1rem;resize:none;outline:none;font-family:inherit;min-height:50px;max-height:200px}
.controls{display:flex;justify-content:space-between;align-items:center;margin-top:.5rem;gap:.5rem;flex-wrap:wrap}
.model-select{display:flex;gap:.3rem;flex-wrap:wrap}
.chip{padding:.35rem .7rem;background:transparent;border:1px solid var(--border);border-radius:20px;font-size:.75rem;color:var(--muted);cursor:pointer;display:flex;align-items:center;gap:.3rem}
.chip:hover{border-color:var(--text);color:var(--text)}
.chip.active{background:var(--text);color:var(--bg);border-color:var(--text)}
.send-btn{background:var(--accent);color:#fff;border:none;padding:.5rem 1.1rem;border-radius:10px;cursor:pointer;font-size:.9rem;font-weight:500}
.send-btn:hover{opacity:.9}
.send-btn:disabled{background:#444;cursor:not-allowed;opacity:.5}
.step{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:1.1rem;margin-bottom:1rem;animation:fade .4s}
.step.final{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
@keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1}}
.step-head{display:flex;align-items:center;gap:.6rem;margin-bottom:.7rem;font-weight:600;font-size:.95rem}
.step-head .badge{padding:.2rem .55rem;border-radius:6px;font-size:.7rem;font-weight:500;background:#252529;color:var(--muted)}
.step-content{color:#ccc;line-height:1.65;white-space:pre-wrap;font-size:.95rem}
.meta{color:var(--muted);font-size:.8rem;margin-bottom:.5rem}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid #333;border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.crit-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:.7rem}
.crit{background:#1a1a1d;border-radius:10px;padding:.8rem;border-left:3px solid}
.crit-name{font-weight:600;margin-bottom:.4rem;font-size:.85rem;display:flex;align-items:center;gap:.3rem}
.empty{text-align:center;color:var(--muted);padding:3rem 1rem;font-size:.95rem}
.empty h2{color:var(--text);margin-bottom:.5rem;font-size:1.4rem}
.menu-toggle{display:none;background:none;border:none;color:var(--text);font-size:1.4rem;cursor:pointer}
@media(max-width:768px){
  body{flex-direction:column}
  .sidebar{position:fixed;left:-280px;top:0;height:100vh;z-index:100;transition:left .3s;box-shadow:2px 0 20px rgba(0,0,0,.5)}
  .sidebar.open{left:0}
  .menu-toggle{display:block}
  .main{height:100vh}
  .content,.input-area{padding-left:1rem;padding-right:1rem}
  .crit-grid{grid-template-columns:1fr}
}
.overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:99}
.overlay.show{display:block}
</style></head><body>
<div class="overlay" id="overlay" onclick="toggleMenu()"></div>
<aside class="sidebar" id="sidebar">
  <button class="new-btn" onclick="newChat()">+ Yeni Sohbet</button>
  <h2>Geçmiş</h2>
  <div id="history"></div>
</aside>
<main class="main">
  <header class="header">
    <button class="menu-toggle" onclick="toggleMenu()">☰</button>
    <h1>🏛️ AI Council</h1>
    <div style="width:24px"></div>
  </header>
  <div class="content" id="content">
    <div class="empty">
      <h2>👋 Hoş geldin</h2>
      <p>Soru sor, en uygun model cevaplasın.<br>İstersen modeli kendin de seçebilirsin.</p>
    </div>
  </div>
  <div class="input-area">
    <div class="input-wrap">
      <textarea id="q" placeholder="Sorunu yaz..." rows="1" oninput="autosize(this)"></textarea>
      <div class="controls">
        <div class="model-select">
          <button class="chip active" onclick="setModel('auto', this)">🎯 Otomatik</button>
          <button class="chip" onclick="setModel('chatgpt', this)">⚡ ChatGPT</button>
          <button class="chip" onclick="setModel('claude', this)">🎭 Claude</button>
          <button class="chip" onclick="setModel('gemini', this)">✨ Gemini</button>
          <button class="chip" onclick="setModel('deepseek', this)">🔬 DeepSeek</button>
        </div>
        <button class="send-btn" id="sendBtn" onclick="run()">Sor →</button>
      </div>
    </div>
  </div>
</main>
<script>
let selectedModel = 'auto';
let history = JSON.parse(localStorage.getItem('ai_council_history') || '[]');
let currentChatId = null;
const content = document.getElementById('content');
const sendBtn = document.getElementById('sendBtn');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('overlay');
function autosize(el){el.style.height='auto';el.style.height=Math.min(el.scrollHeight,200)+'px'}
function toggleMenu(){sidebar.classList.toggle('open');overlay.classList.toggle('show')}
function setModel(m, btn){selectedModel=m;document.querySelectorAll('.chip').forEach(c=>c.classList.remove('active'));btn.classList.add('active')}
function newChat(){currentChatId=null;document.getElementById('q').value='';content.innerHTML='<div class="empty"><h2>👋 Yeni sohbet</h2><p>Sorunu yaz.</p></div>';renderHistory();if(window.innerWidth<=768)toggleMenu()}
function renderHistory(){const h=document.getElementById('history');h.innerHTML=history.slice().reverse().map(c=>`<div class="hist-item ${c.id===currentChatId?'active':''}" onclick="loadChat('${c.id}')">${escapeHtml(c.question.slice(0,40))}${c.question.length>40?'...':''}</div>`).join('')||'<div class="meta" style="padding:.5rem">Henüz sohbet yok</div>'}
function escapeHtml(s){return s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function loadChat(id){const c=history.find(x=>x.id===id);if(!c)return;currentChatId=id;content.innerHTML=c.html;renderHistory();if(window.innerWidth<=768)toggleMenu()}
function saveChat(question,html){if(currentChatId){const c=history.find(x=>x.id===currentChatId);if(c){c.question=question;c.html=html}}else{currentChatId=Date.now().toString();history.push({id:currentChatId,question,html})}if(history.length>30)history.shift();localStorage.setItem('ai_council_history',JSON.stringify(history));renderHistory()}
function step(id,title,contentHtml,meta,color){let el=document.getElementById(id);if(!el){el=document.createElement('div');el.id=id;el.className='step';content.appendChild(el)}el.innerHTML=`<div class="step-head">${title}${meta?'<span class="badge">'+meta+'</span>':''}</div><div class="step-content">${contentHtml}</div>`;if(color)el.style.borderLeft='3px solid '+color;el.scrollIntoView({behavior:'smooth',block:'end'})}
function loading(id,title){step(id,title,'<span class="spinner"></span> İşleniyor...')}
async function api(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();if(d.error)throw new Error(d.error);return d}
async function run(){
  const q=document.getElementById('q').value.trim();if(!q)return;
  content.innerHTML='';sendBtn.disabled=true;sendBtn.innerHTML='<span class="spinner"></span>';
  try{
    let chosen,name,reason,color,icon;
    if(selectedModel==='auto'){
      loading('s1','🎯 Yönlendirme');
      const r1=await api('/api/route',{question:q});
      chosen=r1.chosen;name=r1.name;reason=r1.reason;color=r1.color;icon=r1.icon;
      step('s1','🎯 Yönlendirme',reason,name,color);
    }else{
      chosen=selectedModel;
      name={chatgpt:'ChatGPT',claude:'Claude',gemini:'Gemini',deepseek:'DeepSeek'}[chosen];
      color={chatgpt:'#10a37f',claude:'#c87557',gemini:'#4285f4',deepseek:'#7c3aed'}[chosen];
      icon={chatgpt:'⚡',claude:'🎭',gemini:'✨',deepseek:'🔬'}[chosen];
      step('s1','🎯 Manuel Seçim','Bu modeli sen seçtin.',name,color);
    }
    loading('s2',icon+' '+name);
    const r2=await api('/api/answer',{question:q,model:chosen});
    step('s2',icon+' '+name+' cevaplıyor',r2.answer,'Ana Cevap',color);
    loading('s3','🔍 Diğer modeller');
    const r3=await api('/api/critique',{question:q,answer:r2.answer,primary:chosen});
    let html='<div class="crit-grid">';
    for(const k in r3.critiques){const c=r3.critiques[k];html+=`<div class="crit" style="border-left-color:${c.color}"><div class="crit-name">${c.icon} ${c.name}</div><div>${escapeHtml(c.text).replace(/\\n/g,'<br>')}</div></div>`}
    html+='</div>';
    step('s3','🔍 Eleştiriler',html);
    loading('s4','🏛️ Hakem');
    const r4=await api('/api/judge',{question:q,answer:r2.answer,critiques:r3.critiques});
    step('s4','🏛️ Nihai Cevap',r4.final,'Sentez','#c87557');
    document.getElementById('s4').classList.add('final');
    saveChat(q,content.innerHTML);
    document.getElementById('q').value='';autosize(document.getElementById('q'));
  }catch(e){step('err','⚠️ Hata',e.message)}finally{sendBtn.disabled=false;sendBtn.innerHTML='Sor →'}
}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){e.preventDefault();run()}});
renderHistory();
</script></body></html>"""

if __name__ == "__main__":
    app.run(debug=True, port=5000, host='0.0.0.0')
