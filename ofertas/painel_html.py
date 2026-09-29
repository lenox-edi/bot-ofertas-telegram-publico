"""A página HTML do painel de controle (servida por painel.py)."""

PAGINA = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bot de Ofertas Telegram — Painel</title>
<style>
:root{
  --bg:#031225;--bg2:#061a32;--card:#071d36;--card2:#0a2442;--line:#12385f;
  --text:#f4f8ff;--muted:#8fb0d6;--blue:#1688ff;--cyan:#35b9ff;--green:#18d99b;
  --red:#ff3158;--yellow:#ffc629;--purple:#8b5cf6;--shadow:0 18px 45px rgba(0,0,0,.25)
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:radial-gradient(circle at 75% 0,#0a2c50 0,transparent 30%),linear-gradient(135deg,#020d1b,#061b34 55%,#031225);color:var(--text);font-family:Inter,'Segoe UI',system-ui,sans-serif;font-size:15px;line-height:1.45}
button,input{font:inherit}
button{cursor:pointer}
.layout{min-height:100vh;display:flex}
.sidebar{width:235px;position:fixed;inset:0 auto 0 0;background:rgba(2,15,30,.94);border-right:1px solid var(--line);padding:24px 14px;display:flex;flex-direction:column;z-index:20}
.brand{padding:0 10px 24px;border-bottom:1px solid var(--line);margin-bottom:18px}
.brand-logo{display:flex;gap:10px;align-items:center;font-size:38px}
.brand h1{font-size:21px;line-height:1.05;margin:8px 0 4px}
.brand h1 span{color:#17a8ff}
.brand p{margin:0;color:var(--muted);font-size:12px}
.nav{display:grid;gap:7px}
.nav button{border:0;background:transparent;color:#a9c2df;text-align:left;padding:13px 14px;border-radius:10px;display:flex;align-items:center;gap:12px;font-weight:600}
.nav button:hover,.nav button.active{background:linear-gradient(90deg,#075fc1,#087ce9);color:#fff}
.nav i{font-style:normal;font-size:20px;width:24px;text-align:center}
.side-bottom{margin-top:auto;border:1px solid #075f56;background:#062a2c;border-radius:12px;padding:14px}
.side-bottom strong{display:block;color:#35e4b0}.side-bottom small{color:var(--muted)}
.main{margin-left:235px;width:calc(100% - 235px);padding:22px 30px 42px}
.topbar{display:flex;align-items:center;gap:16px;max-width:1120px;margin:0 auto 22px}
.mobile-menu{display:none}
.page-title{flex:1}
.page-title h2{margin:0;font-size:27px}.page-title p{margin:2px 0 0;color:var(--muted)}
.connection{display:flex;align-items:center;gap:9px;border:1px solid #087b62;background:#052e2a;padding:9px 14px;border-radius:12px;font-weight:700}
.dot{width:11px;height:11px;border-radius:50%;background:#68788c}.dot.on{background:var(--green);box-shadow:0 0 0 5px rgba(24,217,155,.12)}
.content{max-width:1120px;margin:auto}
.grid-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:16px}
.stat{min-height:125px;padding:18px;border:1px solid var(--line);border-radius:14px;background:linear-gradient(145deg,rgba(9,40,72,.95),rgba(4,23,43,.96));box-shadow:var(--shadow)}
.stat .icon{width:42px;height:42px;border-radius:11px;display:grid;place-items:center;font-size:22px;margin-bottom:10px}
.stat:nth-child(1) .icon{background:#063d70}.stat:nth-child(2) .icon{background:#163a91}.stat:nth-child(3) .icon{background:#4a2397}.stat:nth-child(4) .icon{background:#76550b}
.stat small{color:#aac3df}.stat strong{display:block;font-size:23px;margin-top:2px}.stat em{font-style:normal;font-size:12px;color:var(--green)}
.card{border:1px solid var(--line);background:rgba(5,25,47,.92);border-radius:15px;padding:18px;box-shadow:var(--shadow);margin-bottom:16px}
.card-title{display:flex;align-items:center;gap:10px;margin-bottom:15px}.card-title .ico{font-size:25px}.card-title h3{margin:0;font-size:18px}.card-title p{margin:1px 0 0;color:var(--muted);font-size:12px}
.bot-control{display:grid;grid-template-columns:1fr 1fr;gap:12px}.bot-status{grid-column:1/-1;border:1px solid #087e63;background:linear-gradient(90deg,#073d38,#06302f);border-radius:12px;padding:15px;display:flex;align-items:center;gap:13px}.bot-status .bigdot{width:18px;height:18px;border-radius:50%;background:var(--green);box-shadow:0 0 0 7px rgba(24,217,155,.1)}.bot-status strong{font-size:17px}.bot-status span{display:block;color:#8fd8c3;font-size:12px}
.btn{border:1px solid var(--line);border-radius:10px;padding:13px 15px;color:#fff;background:#0b2b4d;font-weight:700;transition:.15s}.btn:hover{transform:translateY(-1px);filter:brightness(1.1)}.btn-danger{background:linear-gradient(135deg,#ff1f4d,#d91e45);border-color:#ff3158}.btn-blue{background:linear-gradient(135deg,#087ef2,#1261dc);border-color:#1688ff}.btn-green{background:#063f38;border-color:#07896d}.btn-purple{background:#38206c;border-color:#7544d8}.btn-yellow{background:#4b3905;border-color:#c79c10;color:#ffe58b}
.auto{grid-column:1/-1;display:flex;align-items:center;gap:12px;border:1px solid var(--line);border-radius:11px;padding:12px 14px}.auto .auto-icon{font-size:22px}.auto div{flex:1}.auto strong{display:block}.auto small{color:var(--muted)}.switch{width:48px;height:27px;border-radius:99px;background:#33485f;padding:3px}.switch:after{content:'';display:block;width:21px;height:21px;border-radius:50%;background:#fff;transition:.2s}.switch.on{background:#0bd89b}.switch.on:after{transform:translateX(21px)}
.flash{border:2px solid #dcae16;background:linear-gradient(100deg,#101d49,#6d4705 75%,#161007);padding:17px 20px;border-radius:15px;display:flex;align-items:center;gap:15px;margin-bottom:16px}.flash .bolt{font-size:45px;color:#ffd21c}.flash h3{margin:0;color:#ffd21c;font-size:19px}.flash p{margin:2px 0;color:#fff}.flash .spacer{flex:1}
.offers{display:grid;gap:9px}.offer{display:grid;grid-template-columns:76px 1fr auto auto;align-items:center;gap:13px;border:1px solid #103b65;background:#061b34;border-radius:12px;padding:9px}.offer img{width:76px;height:62px;object-fit:contain;border-radius:8px;background:#fff}.offer h4{margin:0;font-size:14px}.offer .store{color:#94b7db;font-size:12px}.price{color:#19dfa3;font-weight:800}.old{text-decoration:line-through;color:#657f9e;font-size:12px;margin-left:8px}.discount{background:#ff2c54;color:#fff;border-radius:99px;padding:5px 10px;font-weight:800;font-size:12px}.tag{color:#ffd21c;font-size:12px;font-weight:700}.offer-arrow{color:#65b8ff;font-size:25px}
.lower{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.mini{min-height:110px}.mini .value{font-size:20px;font-weight:800}.mini p{color:var(--muted);font-size:12px;margin:3px 0}
.section{scroll-margin-top:20px}.section-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.section-grid .wide{grid-column:1/-1}
.grp{font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:#7094bc;font-weight:800;margin:16px 0 8px}.grp:first-child{margin-top:0}
.fld{margin-bottom:11px}.fld label{display:flex;gap:8px;align-items:center;font-weight:700;font-size:13px;margin-bottom:4px}.fld input{width:100%;background:#04172b;color:#fff;border:1px solid #12385f;border-radius:8px;padding:9px 10px}.fld input:focus{outline:none;border-color:#1688ff}.help{font-size:11px;color:#7395ba;margin-top:3px}.tick{color:var(--green);font-size:11px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.muted{color:var(--muted);font-size:12px}
.nichos-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:8px}.nicho{display:flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:9px;padding:9px;background:#04172b;cursor:pointer}.nicho.on{border-color:#1688ff;background:#082f57}.nicho .ck{margin-left:auto;color:#18d99b;opacity:0}.nicho.on .ck{opacity:1}
.actions{display:flex;gap:8px;flex-wrap:wrap}.log{height:240px;overflow:auto;white-space:pre-wrap;background:#020a14;border:1px solid #12304d;border-radius:10px;padding:12px;font:12px 'Cascadia Code',Consolas,monospace;color:#b9d0e8}
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);background:#0bbd87;color:#fff;padding:10px 18px;border-radius:10px;font-weight:700;opacity:0;pointer-events:none;transition:.2s;z-index:99}.toast.show{opacity:1}.toast.err{background:#e32b4e}
.ids{margin-top:10px}.idbtn{display:block;width:100%;text-align:left;margin-top:6px}.hide{display:none}
@media(max-width:900px){.sidebar{width:190px}.main{margin-left:190px;width:calc(100% - 190px);padding:18px}.grid-stats{grid-template-columns:repeat(2,1fr)}.lower{grid-template-columns:1fr}.section-grid{grid-template-columns:1fr}}
@media(max-width:680px){
 .layout{display:block}.sidebar{display:none}.main{margin:0;width:100%;padding:12px 12px 80px}.topbar{margin-bottom:14px;align-items:flex-start}.mobile-menu{display:block;border:1px solid var(--line);background:#082443;color:#fff;border-radius:10px;padding:9px 12px;font-size:20px}.page-title h2{font-size:21px}.page-title p{font-size:11px}.connection{font-size:11px;padding:8px 9px}.grid-stats{grid-template-columns:1fr 1fr;gap:8px}.stat{min-height:108px;padding:12px}.stat .icon{width:35px;height:35px;font-size:18px}.stat strong{font-size:19px}.stat small{font-size:10px}.stat em{font-size:10px}.bot-control{grid-template-columns:1fr 1fr}.bot-status{padding:12px}.btn{padding:11px 9px;font-size:12px}.flash{padding:13px}.flash .bolt{font-size:34px}.flash h3{font-size:15px}.flash p{font-size:11px}.flash .btn{display:none}.offer{grid-template-columns:55px 1fr auto;gap:8px}.offer img{width:55px;height:52px}.offer h4{font-size:12px}.offer .old{display:none}.offer-arrow{display:none}.discount{font-size:10px;padding:4px 7px}.offer .tag{display:none}.card{padding:13px}.section{scroll-margin-top:10px}}
</style>
</head>
<body>
<div class="layout">
<aside class="sidebar">
  <div class="brand">
    <div class="brand-logo">🤖 <span>➤</span></div>
    <h1>Bot de Ofertas<br><span>Telegram</span></h1>
    <p>As melhores ofertas, direto no seu Telegram!</p>
  </div>
  <nav class="nav">
    <button class="active" onclick="ir('inicio')"><i>⌂</i> Início</button>
    <button onclick="ir('ofertas')"><i>🏷️</i> Ofertas</button>
    <button onclick="ir('config')"><i>⚙️</i> Configurações</button>
    <button onclick="ir('testes')"><i>🧪</i> Testes</button>
    <button onclick="ir('logs')"><i>▤</i> Logs</button>
  </nav>
  <div class="side-bottom"><strong>● <span id="sideStatus">Verificando…</span></strong><small>Bot de Ofertas 24/7</small></div>
</aside>

<main class="main">
  <div class="topbar" id="inicio">
    <button class="mobile-menu" onclick="document.querySelector('.sidebar').style.display=document.querySelector('.sidebar').style.display==='flex'?'none':'flex'">☰</button>
    <div class="page-title"><h2>🚀 Painel do Bot</h2><p>Acompanhe e gerencie o bot de ofertas.</p></div>
    <div class="connection"><span class="dot" id="dot"></span><span id="stt">Verificando…</span></div>
  </div>

  <div class="content">
    <section class="grid-stats">
      <div class="stat"><div class="icon">🤖</div><small>Status do Bot</small><strong id="statBot">—</strong><em id="statBotSub">verificando</em></div>
      <div class="stat"><div class="icon">📲</div><small>Telegram</small><strong id="statTelegram">—</strong><em id="statTelegramSub">configuração</em></div>
      <div class="stat"><div class="icon">🌐</div><small>Navegador</small><strong id="statBrowser">—</strong><em>Mercado Livre</em></div>
      <div class="stat"><div class="icon">⚡</div><small>Ofertas Relâmpago</small><strong>ATIVA</strong><em>prioridade no bot</em></div>
  </section>

  <section class="card">
    <div class="card-title"><span class="ico">⚡</span><div><h3>Controle do Bot</h3><p>Gerencie o funcionamento do bot.</p></div></div>
    <div class="bot-control">
      <div class="bot-status"><span class="bigdot" id="bigDot"></span><div><strong id="botLabel">Verificando…</strong><span id="botDesc">Aguarde.</span></div></div>
      <button class="btn btn-danger" id="btnStop" onclick="toggleBot()">■ Desligar Bot</button>
      <button class="btn btn-blue" onclick="toggleBot()">▶ Reiniciar / Ligar Bot</button>
      <div class="auto"><span class="auto-icon">⟳</span><div><strong>Ligar automaticamente após deploy <small style="color:#18d99b">ATIVO</small></strong><small>O bot inicia automaticamente a cada novo deploy.</small></div><span class="switch on"></span></div>
    </div>
  </section>

  <section class="flash" onclick="ir('ofertas')">
    <div class="bolt">⚡</div><div><h3>OFERTAS RELÂMPAGO!</h3><p>As melhores ofertas por tempo limitado.</p></div><div class="spacer"></div><button class="btn btn-yellow">Ver ofertas ›</button><div style="font-size:42px">🔥</div>
  </section>

  <section class="card section" id="ofertas">
    <div class="card-title"><span class="ico">🏷️</span><div><h3>Últimas Ofertas</h3><p>Ofertas recentes encontradas pelo bot.</p></div><span class="grow"></span><button class="btn" onclick="toast('As ofertas são enviadas diretamente para o Telegram.')">Ver todas ›</button></div>
    <div class="offers">
      <div class="offer"><img src="https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=160&q=80" alt=""><div><h4>Ofertas do bot</h4><div class="store">Amazon • Mercado Livre • Shopee • AliExpress</div><span class="price">Envio automático</span></div><span class="discount">ATIVO</span><span class="offer-arrow">›</span></div>
      <div class="offer"><img src="https://images.unsplash.com/photo-1546435770-a3e426bf472b?w=160&q=80" alt=""><div><h4>Ofertas Relâmpago</h4><div class="store">Prioridade ativada no pipeline</div><span class="price">⚡ prioridade</span></div><span class="discount">ATIVA</span><span class="offer-arrow">›</span></div>
      <div class="offer"><img src="https://images.unsplash.com/photo-1603351154351-5e2d0600bb77?w=160&q=80" alt=""><div><h4>Cupons</h4><div class="store">Amazon • Mercado Livre • AliExpress</div><span class="price">Republicação após 1 dia</span></div><span class="discount">ATIVO</span><span class="offer-arrow">›</span></div>
    </div>
  </section>

  <div class="lower">
    <div class="card mini"><div class="card-title"><span class="ico">🎟️</span><div><h3>Cupons</h3><p>Descontos encontrados pelo bot</p></div></div><div class="value">ATIVO</div></div>
    <div class="card mini"><div class="card-title"><span class="ico">🚀</span><div><h3>Último Deploy</h3><p>Atualização do sistema</p></div></div><div class="value" id="deployValue">Verificando…</div></div>
    <div class="card mini"><div class="card-title"><span class="ico">⚙️</span><div><h3>Configurações</h3><p>Fontes, credenciais e categorias</p></div></div><button class="btn" onclick="ir('config')">Abrir configurações ›</button></div>
  </div>

  <section class="section-grid section" id="config">
    <div class="card wide">
      <div class="card-title"><span class="ico">⚙️</span><div><h3>Configuração</h3><p>Credenciais e dados usados pelo bot.</p></div></div>
      <div id="campos"></div>
      <div class="row"><button class="btn btn-blue" onclick="salvar()">💾 Salvar configuração</button><button class="btn" onclick="detectarIds()">🔎 Detectar IDs do Telegram</button><span class="muted" id="salvoMsg"></span></div>
      <div class="ids hide" id="idsBox"></div>
    </div>

    <div class="card wide">
      <div class="card-title"><span class="ico">🎯</span><div><h3>Categorias do canal</h3><p>Nada marcado = pega ofertas de tudo.</p></div></div>
      <div class="nichos-grid" id="nichosGrid">carregando…</div>
      <div class="row" style="margin-top:13px"><button class="btn btn-blue" onclick="salvarNichos()">💾 Salvar categorias</button><button class="btn" onclick="limparNichos()">Limpar</button><span class="muted" id="nichosMsg"></span></div>
    </div>
  </section>

  <section class="card section" id="testes">
    <div class="card-title"><span class="ico">🧪</span><div><h3>Instalação e testes</h3><p>Execute uma ação e acompanhe o resultado.</p></div></div>
    <div class="actions">
      <button class="btn" onclick="acao('instalar-navegador')" id="a_nav">⬇️ Instalar navegador</button>
      <button class="btn" onclick="acao('ml-login')" id="a_ml">🔑 Login Mercado Livre</button>
      <button class="btn" onclick="acao('testar-ml')">Testar ML</button>
      <button class="btn" onclick="acao('testar-shopee')">Testar Shopee</button>
      <button class="btn" onclick="acao('testar-amazon')">Testar Amazon</button>
      <button class="btn" onclick="acao('testar-aliexpress')">Testar AliExpress</button>
      <button class="btn btn-purple" onclick="acao('testar-cupons')">🎟️ Testar cupons</button>
    </div>
  </section>

  <section class="section-grid section" id="logs">
    <div class="card"><div class="card-title"><span class="ico">▤</span><div><h3>Logs do Bot</h3><p>Saída em tempo real.</p></div></div><div class="log" id="logBot">—</div></div>
    <div class="card"><div class="card-title"><span class="ico">🧪</span><div><h3>Logs das Ações</h3><p>Testes e instalações.</p></div></div><div class="log" id="logAcao">—</div></div>
  </section>

  <p class="muted" style="text-align:center;margin-top:24px">Bot de Ofertas para Telegram • Painel moderno • Roda 24/7 no Railway</p>
</div>
</main>
</div>
<div class="toast" id="toast"></div>

<script>
const $=s=>document.querySelector(s);let CFG={},statusAtual={};
const CAMPOS=[
["TELEGRAM_BOT_TOKEN","Token do bot","Telegram",true,"Crie no @BotFather com /newbot e cole aqui."],
["TELEGRAM_OWNER_ID","Seu user ID","Telegram",false,"Use Detectar IDs depois de salvar o token."],
["TELEGRAM_CHAT_ID","ID do canal","Telegram",false,"O canal onde o bot posta. Use Detectar IDs."],
["ML_ETIQUETA","Etiqueta do afiliado","Mercado Livre",false,"A Etiqueta em uso do Linkbuilder."],
["AMAZON_TAG","Tag de associado","Amazon",false,"Sua tag do Amazon Associados."],
["AMAZON_CREDENTIAL_ID","Creators API — ID","Amazon",false,"Opcional."],
["AMAZON_CREDENTIAL_SECRET","Creators API — Secret","Amazon",true,"Opcional. Aparece só uma vez."],
["SHOPEE_APP_ID","App ID","Shopee",false,"Painel de afiliados > Abrir API."],
["SHOPEE_APP_SECRET","App Secret","Shopee",true,"Painel de afiliados > Abrir API."]
];

function ir(id){document.getElementById(id).scrollIntoView({behavior:"smooth"});if(innerWidth<681)document.querySelector(".sidebar").style.display="none"}
function montarCampos(){let h="",g="";for(const [k,r,gr,s,a] of CAMPOS){if(gr!==g){h+="<div class='grp'>"+gr+"</div>";g=gr}const set=CFG[k+"__set"];const tick=set?"<span class='tick'>✓ preenchido</span>":"";const ph=s&&set?"•••••• (preenchido — deixe em branco para manter)":"";h+="<div class='fld'><label>"+r+" "+tick+"</label><input id='f_"+k+"' type='"+(s?"password":"text")+"' placeholder='"+ph+"' value='"+(s?"":(CFG[k]||""))+"'><div class='help'>"+a+"</div></div>"}$("#campos").innerHTML=h}
async function carregarCfg(){CFG=await(await fetch("/api/config")).json();montarCampos()}
async function salvar(){const body={};for(const [k] of CAMPOS)body[k]=$("#f_"+k).value.trim();await fetch("/api/config",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});toast("Configuração salva!");await carregarCfg();atualizar()}
async function detectarIds(){const box=$("#idsBox");box.classList.remove("hide");box.innerHTML="<p class='muted'>Consultando o Telegram…</p>";const r=await(await fetch("/api/detectar-ids",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"})).json();if(r.erro){box.innerHTML="<p class='muted' style='color:#ffc629'>"+r.erro+"</p>";return}if(r.vazio){box.innerHTML="<p class='muted'>Nada encontrado ainda. No Telegram mande /start e /id para o bot e encaminhe um post do canal para ele.</p>";return}let h="";if(r.pessoas.length){h+="<p class='muted'>Clique no seu usuário (define o dono):</p>";for(const p of r.pessoas)h+="<button class='btn idbtn' onclick=\"setId('TELEGRAM_OWNER_ID','"+p.id+"')\">👤 "+p.nome+" — <code>"+p.id+"</code></button>"}if(r.canais.length){h+="<p class='muted'>Clique no seu canal:</p>";for(const c of r.canais)h+="<button class='btn idbtn' onclick=\"setId('TELEGRAM_CHAT_ID','"+c.id+"')\">📢 "+c.nome+" — <code>"+c.id+"</code></button>"}box.innerHTML=h}
function setId(c,v){$("#f_"+c).value=v;toast("Preenchido — não esqueça de salvar.")}
async function acao(nome){const r=await(await fetch("/api/acao",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({nome})})).json();if(r.erro){toast(r.erro,true);return}toast(nome==="ml-login"?"Abrindo o Chrome… faça login e feche o navegador.":"Ação iniciada. Acompanhe os logs.")}
async function toggleBot(){const rota=statusAtual.bot_rodando?"/api/stop":"/api/start";await fetch(rota,{method:"POST"});atualizar()}
async function atualizar(){statusAtual=await(await fetch("/api/status")).json();const on=statusAtual.bot_rodando;$("#dot").className="dot"+(on?" on":"");$("#stt").textContent=on?"Bot Online":(statusAtual.pronto?"Pronto para ligar":"Falta configurar");$("#sideStatus").textContent=on?"Bot Online":"Bot desligado";$("#statBot").textContent=on?"ONLINE":"OFFLINE";$("#statBotSub").textContent=on?"funcionando normalmente":"aguardando configuração";$("#statTelegram").textContent=statusAtual.pronto?"CONECTADO":"PENDENTE";$("#statTelegramSub").textContent=statusAtual.pronto?"credenciais completas":"preencha os dados";$("#statBrowser").textContent=statusAtual.navegador?"OK":"PENDENTE";$("#botLabel").textContent=on?"Bot Ligado":"Bot Desligado";$("#botDesc").textContent=on?"O bot está ativo e enviando ofertas.":"Configure o painel e ligue o bot.";$("#bigDot").style.background=on?"var(--green)":"#68788c";$("#btnStop").textContent=on?"■ Desligar Bot":"▶ Ligar Bot";$("#btnStop").className=on?"btn btn-danger":"btn btn-blue";$("#a_nav").textContent=statusAtual.navegador?"✓ Navegador instalado":"⬇️ Instalar navegador";$("#a_ml").textContent=statusAtual.sessao_ml?"✓ Login ML feito (refazer)":"🔑 Login Mercado Livre";$("#deployValue").textContent="Serviço ativo"} 
async function puxarLogs(){const [lb,la]=await Promise.all([fetch("/api/logs?bot").then(r=>r.json()),fetch("/api/logs?acao").then(r=>r.json())]);if(lb.linhas.length){const e=$("#logBot"),b=e.scrollTop+e.clientHeight>=e.scrollHeight-30;e.textContent=lb.linhas.join("\n");if(b)e.scrollTop=e.scrollHeight}if(la.linhas.length){const e=$("#logAcao"),b=e.scrollTop+e.clientHeight>=e.scrollHeight-30;e.textContent=la.linhas.join("\n");if(b)e.scrollTop=e.scrollHeight}}
let NICHOS_SEL=new Set();
async function carregarNichos(){const r=await(await fetch("/api/nichos")).json();NICHOS_SEL=new Set(r.selecionados||[]);$("#nichosGrid").innerHTML=r.catalogo.map(n=>"<div class='nicho"+(NICHOS_SEL.has(n.chave)?" on":"")+"' data-k='"+n.chave+"' onclick=\"toggleNicho('"+n.chave+"')\"><span>"+n.emoji+"</span><span>"+n.nome+"</span><span class='ck'>✓</span></div>").join("");atualizarMsgNichos()}
function toggleNicho(k){if(NICHOS_SEL.has(k))NICHOS_SEL.delete(k);else NICHOS_SEL.add(k);document.querySelector(".nicho[data-k='"+k+"']").classList.toggle("on");atualizarMsgNichos()}
function atualizarMsgNichos(){const n=NICHOS_SEL.size;$("#nichosMsg").textContent=n===0?"pegando de todas as categorias":n+" nicho(s) selecionado(s)"}
async function salvarNichos(){await fetch("/api/nichos",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({selecionados:[...NICHOS_SEL]})});toast(statusAtual.bot_rodando?"Salvo! Desligue e ligue o bot para aplicar.":"Categorias salvas!")}
function limparNichos(){NICHOS_SEL.clear();document.querySelectorAll(".nicho.on").forEach(e=>e.classList.remove("on"));atualizarMsgNichos()}
let toastT;function toast(msg,err){const t=$("#toast");t.textContent=msg;t.className="toast show"+(err?" err":"");clearTimeout(toastT);toastT=setTimeout(()=>t.className="toast"+(err?" err":""),3200)}
carregarCfg();carregarNichos();atualizar();puxarLogs();setInterval(atualizar,2500);setInterval(puxarLogs,1500);
</script>
</body>
</html>
"""
