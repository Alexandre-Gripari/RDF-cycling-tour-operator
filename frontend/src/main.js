import './style.css'
import { createIcons, icons } from 'lucide';

const API_BASE = 'http://127.0.0.1:5000/api';

const state = {
  currentView: 'chat',
  chatHistory: [],
};

const contentArea = document.getElementById('content-area');
const pageTitle = document.getElementById('page-title');
const navButtons = document.querySelectorAll('.nav-btn');

function init() {
  setupNavigation();
  renderView('chat');
  initLucide();
}

function initLucide() {
  createIcons({ icons });
}

function setupNavigation() {
  navButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      navButtons.forEach(b => {
        b.className = `flex items-center gap-3 w-full px-4 py-3 rounded-lg text-sm text-slate-400 hover:bg-bg-hover hover:text-white transition-all`;
      });
      
      const target = e.currentTarget;
      target.className = `flex items-center gap-3 w-full px-4 py-3 rounded-lg text-sm bg-brand-dim text-brand-DEFAULT border border-brand-DEFAULT/20 shadow-neon font-medium transition-all`;
      
      const view = target.id.replace('nav-', '');
      renderView(view);
    });
  });
  
  document.getElementById('nav-chat').click();
}

function renderView(view) {
  state.currentView = view;
  contentArea.innerHTML = '';
  
  const titles = {
    chat: 'AI Assistant & SPARQL Generator',
    explorer: 'Knowledge Graph Explorer',
    predict: 'Tour Recommendation Engine'
  };
  pageTitle.innerText = titles[view];

  if (view === 'chat') renderChatView();
  if (view === 'explorer') renderExplorerView();
  if (view === 'predict') renderPredictView();
  
  initLucide();
}

function renderChatView() {
  let searchMode = 'chat'; 

  contentArea.innerHTML = `
    <div class="max-w-3xl mx-auto h-full flex flex-col">
      
      <div id="chat-messages" class="flex-1 overflow-y-auto space-y-4 mb-6 pr-2 scroll-smooth">
        <div class="flex gap-4">
          <div class="w-8 h-8 rounded-full bg-brand-DEFAULT flex items-center justify-center text-bg-main font-bold shrink-0">AI</div>
          <div class="glass-panel p-4 text-slate-300 text-sm">
            Hello! I can help you in two ways: <br>
            1. <b>Assistant:</b> Ask general questions.<br>
            2. <b>Database:</b> Generate SPARQL queries.
          </div>
        </div>
      </div>
      
      <div class="flex flex-col gap-3">
        
        <div class="flex justify-center">
            <div class="bg-bg-main border border-white/10 p-1 rounded-lg flex gap-1">
                <button id="btn-mode-chat" class="px-4 py-1.5 rounded-md text-xs font-medium flex items-center gap-2 transition-all bg-brand-dim text-brand-DEFAULT border border-brand-DEFAULT/20 shadow-neon">
                    <i data-lucide="message-square-text" class="w-3 h-3"></i> Assistant
                </button>
                <button id="btn-mode-query" class="px-4 py-1.5 rounded-md text-xs font-medium flex items-center gap-2 transition-all text-slate-400 hover:text-white hover:bg-white/5 border border-transparent">
                    <i data-lucide="database" class="w-3 h-3"></i> Database Query
                </button>
            </div>
        </div>

        <div class="glass-panel p-2 flex gap-2">
          <input type="text" id="chat-input" placeholder="Ask a question..." class="flex-1 bg-transparent border-none text-white placeholder-slate-500 focus:ring-0">
          <button id="send-chat" class="bg-brand-DEFAULT hover:bg-brand-glow text-bg-main font-bold p-2 rounded-lg transition-colors">
            <i data-lucide="send-horizontal" class="w-5 h-5"></i>
          </button>
        </div>
        
        <div id="mode-indicator" class="text-center text-xs text-slate-500 font-mono h-4">
           Current: General QA Mode
        </div>
      </div>
    </div>
  `;

  const input = document.getElementById('chat-input');
  const btn = document.getElementById('send-chat');
  const messages = document.getElementById('chat-messages');
  const btnChat = document.getElementById('btn-mode-chat');
  const btnQuery = document.getElementById('btn-mode-query');
  const indicator = document.getElementById('mode-indicator');

  const setMode = (mode) => {
    searchMode = mode;
    const activeClass = "bg-brand-dim text-brand-DEFAULT border-brand-DEFAULT/20 shadow-neon";
    const inactiveClass = "text-slate-400 hover:text-white hover:bg-white/5 border-transparent";
    
    btnChat.className = `px-4 py-1.5 rounded-md text-xs font-medium flex items-center gap-2 transition-all border ${mode === 'chat' ? activeClass : inactiveClass}`;
    btnQuery.className = `px-4 py-1.5 rounded-md text-xs font-medium flex items-center gap-2 transition-all border ${mode === 'query' ? activeClass : inactiveClass}`;

    if(mode === 'chat') {
        input.placeholder = "Ex: How do I prepare for a cycling tour?";
        indicator.innerText = "Mode: Human-like text answer";
    } else {
        input.placeholder = "Ex: List all bikes cheaper than 50 euros";
        indicator.innerText = "Mode: Generate SPARQL & Data Table";
    }
    input.focus();
  };

  btnChat.onclick = () => setMode('chat');
  btnQuery.onclick = () => setMode('query');

  const handleSend = async () => {
    const text = input.value;
    if (!text) return;

    addMessage('user', text);
    input.value = '';
    
    addMessage('system', 'Thinking...');
    
    try {
      let responseText = "";
      
      if (searchMode === 'query') {
        const sparqlRes = await fetch(`${API_BASE}/text-to-sparql`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text })
        });
        const sparqlData = await sparqlRes.json();
        
        let queryStr = typeof sparqlData === 'string' ? sparqlData : sparqlData.query || sparqlData;
        queryStr = queryStr.replace(/```sparql/g, '').replace(/```/g, '').trim();

        responseText += `<div class="font-mono text-xs text-brand-DEFAULT bg-bg-main p-2 rounded mb-2 border border-slate-700 flex justify-between"><span>SPARQL GENERATED</span> <i data-lucide="check" class="w-3 h-3"></i></div>`;
        responseText += `<pre class="bg-bg-main p-3 rounded text-xs text-slate-400 overflow-x-auto mb-4 border border-slate-700"><code>${queryStr}</code></pre>`;

        const execRes = await fetch(`${API_BASE}/query`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ query: queryStr })
        });
        const results = await execRes.json();
        responseText += formatTable(results);

      } else {
        const res = await fetch(`${API_BASE}/ask`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: text })
        });
        const data = await res.json();
        responseText = data.answer.replace(/\n/g, '<br>');
      }

      messages.lastElementChild.remove();
      addMessage('ai', responseText, true);

      createIcons({ icons });

    } catch (e) {
      messages.lastElementChild.remove();
      addMessage('system', `Error: ${e.message}`);
    }
  };

  btn.onclick = handleSend;
  input.onkeypress = (e) => { if(e.key === 'Enter') handleSend() };
  
  createIcons({ icons });
}

function addMessage(role, html, isHtml = false) {
  const messages = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `flex gap-4 ${role === 'user' ? 'flex-row-reverse' : ''}`;
  
  const avatarColor = role === 'user' ? 'bg-slate-600' : (role === 'system' ? 'bg-orange-500' : 'bg-brand-DEFAULT');
  const avatarTxt = role === 'user' ? 'ME' : (role === 'system' ? 'SYS' : 'AI');
  const bubbleStyle = role === 'user' ? 'bg-bg-hover text-white' : 'glass-panel text-slate-300';

  div.innerHTML = `
    <div class="w-8 h-8 rounded-full ${avatarColor} flex items-center justify-center text-bg-main font-bold shrink-0 text-xs">${avatarTxt}</div>
    <div class="${bubbleStyle} p-4 text-sm max-w-[80%] overflow-hidden">
      ${isHtml ? html : html.replace(/</g, "&lt;")}
    </div>
  `;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function renderExplorerView() {
  contentArea.innerHTML = `
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
      <div class="lg:col-span-1 flex flex-col gap-4">
        <div class="glass-panel p-4 flex-1 flex flex-col">
          <label class="text-xs font-mono text-slate-400 mb-2 uppercase tracking-wider">SPARQL Query Editor</label>
          
          <textarea id="sparql-input" class="flex-1 font-mono text-xs leading-relaxed bg-bg-main resize-none p-4 focus:ring-1 focus:ring-brand-DEFAULT transition-all" spellcheck="false" placeholder="Enter SPARQL query...">
PREFIX cs: <http://data.cyclingtour.fr/schema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?mountain ?label ?sameAs
WHERE { 
  ?mountain a cs:Mountain ;
            rdfs:label ?label ;
            owl:sameAs ?sameAs .
} LIMIT 20
          </textarea>

          <div class="mt-4 border-t border-white/5 pt-3">
             <label class="text-[10px] uppercase font-bold text-slate-500 mb-2 block">DBpedia Enrichment Fields:</label>
             <div class="flex gap-4 mb-3">
                <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer hover:text-white">
                    <input type="checkbox" value="image" class="enrich-opt accent-brand-DEFAULT" checked> Image
                </label>
                <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer hover:text-white">
                    <input type="checkbox" value="description" class="enrich-opt accent-brand-DEFAULT"> Desc.
                </label>
                <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer hover:text-white">
                    <input type="checkbox" value="website" class="enrich-opt accent-brand-DEFAULT"> Web
                </label>
             </div>

             <div class="flex gap-2">
                <button id="run-query" class="flex-1 bg-slate-700 hover:bg-slate-600 text-white font-bold py-2 rounded-lg flex items-center justify-center gap-2 text-xs transition-colors">
                  <i data-lucide="play" class="w-3 h-3"></i> Run Raw
                </button>
                <button id="enrich-query" class="flex-1 bg-brand-DEFAULT hover:bg-brand-glow text-bg-main font-bold py-2 rounded-lg flex items-center justify-center gap-2 text-xs transition-all shadow-neon">
                    <i data-lucide="sparkles" class="w-3 h-3"></i> Run & Enrich
                </button>
             </div>
          </div>
        </div>
      </div>

      <div class="lg:col-span-2 glass-panel p-4 flex flex-col overflow-hidden">
         <div class="flex justify-between items-center mb-2">
            <label class="text-xs font-mono text-slate-400 uppercase tracking-wider">Results</label>
            <span id="result-count" class="text-xs text-brand-DEFAULT font-mono"></span>
         </div>
         <div id="query-results" class="flex-1 overflow-auto bg-bg-main rounded-lg border border-slate-700 p-0 relative scroll-smooth">
            <div class="absolute inset-0 flex items-center justify-center text-slate-600 text-sm pointer-events-none">
               Execute a query to see results...
            </div>
         </div>
      </div>
    </div>
  `;
  
  const textarea = document.getElementById('sparql-input');
  textarea.addEventListener('keydown', function(e) {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = this.selectionStart;
      const end = this.selectionEnd;
      this.value = this.value.substring(0, start) + "  " + this.value.substring(end);
      this.selectionStart = this.selectionEnd = start + 2;
    }
  });

  document.getElementById('run-query').onclick = () => executeRawQuery(false);
  document.getElementById('enrich-query').onclick = () => executeRawQuery(true);
  
  createIcons({ icons });
}

async function executeRawQuery(enrich) {
  const query = document.getElementById('sparql-input').value;
  const resultDiv = document.getElementById('query-results');
  const countSpan = document.getElementById('result-count');
  
  resultDiv.innerHTML = '<div class="h-full flex flex-col items-center justify-center gap-3"><div class="w-6 h-6 border-2 border-brand-DEFAULT border-t-transparent rounded-full animate-spin"></div><div class="text-brand-DEFAULT text-xs animate-pulse">Querying Knowledge Graph...</div></div>';
  countSpan.innerText = '';

  try {
    const endpoint = enrich ? '/enrich' : '/query';
    
    const checkedBoxes = document.querySelectorAll('.enrich-opt:checked');
    const selectedFields = Array.from(checkedBoxes).map(cb => cb.value);

    const payload = enrich ? { query, fields: selectedFields } : { query };
    
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    const data = await res.json();
    
    resultDiv.innerHTML = formatTable(data);
    countSpan.innerText = Array.isArray(data) ? `${data.length} rows found` : '';
    
  } catch (e) {
    resultDiv.innerHTML = `<div class="p-4 text-red-400 font-mono text-xs">Error: ${e.message}</div>`;
  }
}

function formatTable(data) {
  if (!data || data.length === 0) return '<div class="h-full flex items-center justify-center text-slate-500 italic">No results found.</div>';
  if (data.error) return `<div class="p-4 text-red-400">Error: ${data.error}</div>`;
  
  const allHeaders = new Set();
  data.forEach(row => Object.keys(row).forEach(k => allHeaders.add(k)));
  const headers = Array.from(allHeaders);

  if (headers.includes('image')) {
      headers.splice(headers.indexOf('image'), 1);
      headers.unshift('image');
  }
  
  let html = `<table class="w-full text-left border-collapse min-w-max">`;
  
  html += `<thead class="bg-bg-main sticky top-0 z-10 shadow-sm"><tr>`;
  headers.forEach(h => html += `<th class="p-3 text-xs font-mono text-brand-DEFAULT/80 uppercase border-b border-slate-700 bg-bg-main">${h}</th>`);
  html += `</tr></thead>`;
  
  html += `<tbody class="divide-y divide-slate-800/50">`;
  
  data.forEach(row => {
    html += `<tr class="hover:bg-white/5 transition-colors group">`;
    headers.forEach(h => {
        let val = row[h];
        
        if (val === undefined || val === null) {
            html += `<td class="p-3 text-sm text-slate-600 italic"> - </td>`;
            return;
        }

        if (h === 'image' || (typeof val === 'string' && (val.endsWith('.jpg') || val.endsWith('.png') || val.includes('commons.wikimedia.org')))) {
            val = `<div class="w-12 h-12 rounded overflow-hidden bg-slate-800 border border-slate-600">
                     <img src="${val}" class="w-full h-full object-cover hover:scale-150 transition-transform cursor-zoom-in" loading="lazy" alt="Img">
                   </div>`;
        } 
        else if (typeof val === 'string' && val.startsWith('http')) {
            const shortName = val.split(/[#/]/).pop();
            val = `<a href="${val}" target="_blank" class="text-blue-400 hover:text-blue-300 hover:underline truncate max-w-[200px] block font-mono text-xs" title="${val}">
                    ${shortName || 'link'} <i data-lucide="external-link" class="inline w-3 h-3 opacity-50"></i>
                   </a>`;
        }
        else if (h === 'description' && val.length > 100) {
            val = `<div class="max-w-[300px] text-xs text-slate-300 line-clamp-2" title="${val}">${val}</div>`;
        }

        html += `<td class="p-3 text-sm text-slate-300 align-middle">${val}</td>`;
    });
    html += `</tr>`;
  });
  
  html += `</tbody></table>`;
  
  setTimeout(() => createIcons({ icons }), 0);

  return html;
}

function renderPredictView() {
  contentArea.innerHTML = `
    <div class="max-w-2xl mx-auto mt-10">
      <div class="glass-panel p-8 text-center mb-8">
        <div class="w-16 h-16 bg-brand-dim rounded-full flex items-center justify-center mx-auto mb-4 text-brand-DEFAULT">
          <i data-lucide="brain-circuit" class="w-8 h-8"></i>
        </div>
        <h3 class="text-xl font-bold text-white mb-2">Recommendation Engine</h3>
        <p class="text-slate-400 text-sm mb-6">Enter a Client URI to predict their next best tour package based on similarity graphs.</p>
        
        <div class="flex gap-2">
          <input type="text" id="client-uri" placeholder="http://data.cyclingtour.fr/data#Client_bruno_rcr_pro_team_dura_ace_di2_signature_0" class="flex-1">
          <button id="get-pred" class="bg-brand-DEFAULT text-bg-main font-bold px-6 rounded-lg">Predict</button>
        </div>
      </div>

      <div id="pred-result" class="hidden glass-panel p-6 border-l-4 border-l-brand-DEFAULT">
        <h4 class="text-sm font-mono text-slate-400 uppercase mb-4">Top Recommendation</h4>
        <div class="flex justify-between items-start">
           <div>
              <div class="text-2xl text-white font-bold mb-1" id="rec-tour">Tour Name</div>
              <div class="text-slate-400 text-sm" id="rec-reason">Reasoning...</div>
           </div>
           <div class="text-brand-DEFAULT font-mono text-xl font-bold" id="rec-score">98%</div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('get-pred').onclick = async () => {
    const uri = document.getElementById('client-uri').value;
    const resDiv = document.getElementById('pred-result');
    
    if(!uri) return alert("Please enter a URI");

    try {
      const res = await fetch(`${API_BASE}/prediction`, {
         method: 'POST', headers: {'Content-Type': 'application/json'},
         body: JSON.stringify({ client_uri: uri })
      });
      const data = await res.json();
      
      document.getElementById('rec-tour').innerText = data.tour_uri;
      document.getElementById('rec-reason').innerText = data.reason;
      document.getElementById('rec-score').innerText = (data.score * 100).toFixed(0) + '% Match';
      
      resDiv.classList.remove('hidden');
    } catch(e) {
      alert("Error fetching prediction");
    }
  };
}

init();