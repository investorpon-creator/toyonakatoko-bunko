/* 中常塾アプリ ── 画面の切り替えと中身の組み立て。
   中身はサイトと同じ /kotoba.js（一節・一言）/tayori.js（たより）/bunko/kaidan/kaidan.js（階段）/events.js（開催予定）を読む。
   ここに文章は書かない。直すのはサイト側のその四つのファイル。 */
(function(){
  /* 七十二候の表（index.html の KO と同じもの。暦を直すときは両方を揃える） */
const KO = [
  [1,5,"小寒","芹乃栄","せりすなわちさかう"],[1,10,"小寒","水泉動","しみずあたたかをふくむ"],[1,15,"小寒","雉始雊","きじはじめてなく"],
  [1,20,"大寒","款冬華","ふきのはなさく"],[1,25,"大寒","水沢腹堅","さわみずこおりつめる"],[1,30,"大寒","鶏始乳","にわとりはじめてとやにつく"],
  [2,4,"立春","東風解凍","はるかぜこおりをとく"],[2,9,"立春","黄鶯睍睆","うぐいすなく"],[2,14,"立春","魚上氷","うおこおりをいずる"],
  [2,19,"雨水","土脉潤起","つちのしょううるおいおこる"],[2,24,"雨水","霞始靆","かすみはじめてたなびく"],[3,1,"雨水","草木萌動","そうもくめばえいずる"],
  [3,6,"啓蟄","蟄虫啓戸","すごもりむしとをひらく"],[3,11,"啓蟄","桃始笑","ももはじめてさく"],[3,16,"啓蟄","菜虫化蝶","なむしちょうとなる"],
  [3,21,"春分","雀始巣","すずめはじめてすくう"],[3,26,"春分","桜始開","さくらはじめてひらく"],[3,31,"春分","雷乃発声","かみなりすなわちこえをはっす"],
  [4,5,"清明","玄鳥至","つばめきたる"],[4,10,"清明","鴻雁北","こうがんかえる"],[4,15,"清明","虹始見","にじはじめてあらわる"],
  [4,20,"穀雨","葭始生","あしはじめてしょうず"],[4,25,"穀雨","霜止出苗","しもやみてなえいずる"],[4,30,"穀雨","牡丹華","ぼたんはなさく"],
  [5,5,"立夏","蛙始鳴","かわずはじめてなく"],[5,10,"立夏","蚯蚓出","みみずいずる"],[5,15,"立夏","竹笋生","たけのこしょうず"],
  [5,21,"小満","蚕起食桑","かいこおきてくわをはむ"],[5,26,"小満","紅花栄","べにばなさかう"],[5,31,"小満","麦秋至","むぎのときいたる"],
  [6,5,"芒種","蟷螂生","かまきりしょうず"],[6,10,"芒種","腐草為螢","くされたるくさほたるとなる"],[6,16,"芒種","梅子黄","うめのみきばむ"],
  [6,21,"夏至","乃東枯","なつかれくさかるる"],[6,26,"夏至","菖蒲華","あやめはなさく"],[7,1,"夏至","半夏生","はんげしょうず"],
  [7,7,"小暑","温風至","あつかぜいたる"],[7,12,"小暑","蓮始開","はすはじめてひらく"],[7,17,"小暑","鷹乃学習","たかすなわちわざをならう"],
  [7,22,"大暑","桐始結花","きりはじめてはなをむすぶ"],[7,28,"大暑","土潤溽暑","つちうるおうてむしあつし"],[8,2,"大暑","大雨時行","たいうときどきにふる"],
  [8,7,"立秋","涼風至","すずかぜいたる"],[8,12,"立秋","寒蝉鳴","ひぐらしなく"],[8,17,"立秋","蒙霧升降","ふかききりまとう"],
  [8,23,"処暑","綿柎開","わたのはなしべひらく"],[8,28,"処暑","天地始粛","てんちはじめてさむし"],[9,2,"処暑","禾乃登","こくものすなわちみのる"],
  [9,7,"白露","草露白","くさのつゆしろし"],[9,12,"白露","鶺鴒鳴","せきれいなく"],[9,17,"白露","玄鳥去","つばめさる"],
  [9,22,"秋分","雷乃収声","かみなりすなわちこえをおさむ"],[9,27,"秋分","蟄虫坏戸","むしかくれてとをふさぐ"],[10,2,"秋分","水始涸","みずはじめてかるる"],
  [10,8,"寒露","鴻雁来","こうがんきたる"],[10,13,"寒露","菊花開","きくのはなひらく"],[10,18,"寒露","蟋蟀在戸","きりぎりすとにあり"],
  [10,23,"霜降","霜始降","しもはじめてふる"],[10,28,"霜降","霎時施","こさめときどきふる"],[11,2,"霜降","楓蔦黄","もみじつたきばむ"],
  [11,7,"立冬","山茶始開","つばきはじめてひらく"],[11,12,"立冬","地始凍","ちはじめてこおる"],[11,17,"立冬","金盞香","きんせんかさく"],
  [11,22,"小雪","虹蔵不見","にじかくれてみえず"],[11,27,"小雪","朔風払葉","きたかぜこのはをはらう"],[12,2,"小雪","橘始黄","たちばなはじめてきばむ"],
  [12,7,"大雪","閉塞成冬","そらさむくふゆとなる"],[12,12,"大雪","熊蟄穴","くまあなにこもる"],[12,16,"大雪","鱖魚群","さけのうおむらがる"],
  [12,21,"冬至","乃東生","なつかれくさしょうず"],[12,26,"冬至","麋角解","さわしかのつのおつる"],[12,31,"冬至","雪下出麦","ゆきわたりてむぎいづる"]
];
// 新着のたよりの本体は /tayori.js（＋階段の公開分 /bunko/kaidan/kaidan.js）。ここは読み込み失敗時の控え。
const TAYORI = [{d:"2026-05-25",t:"中常塾を開塾しました"}];
  const VENUE = {name:"岡崎城 二の丸能楽堂", addr:"愛知県岡崎市康生町561（岡崎公園内）"};
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const now = new Date(), y = now.getFullYear(), m = now.getMonth()+1, d = now.getDate();
  const todayISO = y+"-"+("0"+m).slice(-2)+"-"+("0"+d).slice(-2);
  const week = ["日","月","火","水","木","金","土"];
  let curIdx = KO.length-1;
  for (let i=0;i<KO.length;i++){ if (m>KO[i][0]||(m===KO[i][0]&&d>=KO[i][1])) curIdx=i; }
  const D = window.NAKATOKO_DAILY || {pool:{}, kou:[]};

  /* ── 今日の日付・暦 ── */
  $("hdDate").textContent = "令和"+(y-2018)+"年 "+m+"月"+d+"日（"+week[now.getDay()]+"）";
  $("hdKouName").textContent = KO[curIdx][2]+" ── "+KO[curIdx][3];
  $("hdKou").textContent = KO[curIdx][4];

  /* ── 一言：今日から遡って七十二候ぶん ── */
  function kouDate(idx){ const yy = idx>curIdx ? y-1 : y; return {iso: yy+"-"+("0"+KO[idx][0]).slice(-2)+"-"+("0"+KO[idx][1]).slice(-2), label: KO[idx][0]+"月"+KO[idx][1]+"日〜"}; }
  function kouItem(idx){ const p = D.kou && D.kou[idx]; const q = p && D.pool[p.q]; return {idx, kou:KO[idx], h:p?p.h:"", q:q||null, date:kouDate(idx)}; }
  const items = []; for (let i=0;i<KO.length;i++){ items.push(kouItem((curIdx-i+KO.length)%KO.length)); }
  $("hitokotoList").innerHTML = items.map(it => '<a class="row" href="#hitokoto/'+it.idx+'"><span class="row-t">'+esc(it.h ? (it.h.length>22 ? it.h.slice(0,22)+"…" : it.h) : it.kou[3])+'</span><span class="row-d">'+esc(it.kou[3])+' ・ '+esc(it.date.label)+'</span></a>').join("");
  function renderHitokoto(idx){
    const it = kouItem(idx);
    $("hitokotoDetail").innerHTML =
      '<div class="dt-head"><div class="dt-kou">'+esc(it.kou[2])+' ── '+esc(it.kou[3])+'</div><div class="dt-yomi">'+esc(it.kou[4])+' ・ '+esc(it.date.label)+'</div></div><div class="dt-body">'+
      (it.q ? '<div class="cap" style="margin-left:0;margin-right:0">一節</div><blockquote class="issetsu">'+esc(it.q.t)+'<span class="src">── '+esc(it.q.s)+'</span></blockquote>' : '')+
      (it.h ? '<div class="cap" style="margin-left:0;margin-right:0">塾主の一言</div><p class="hitokoto">'+esc(it.h)+'</p>' : '<p class="hitokoto muted">この候の一言は、まだ書かれていません。</p>')+'</div>';
  }
  const today = items[0];
  $("topHitokoto").innerHTML = (today.q ? '<blockquote class="issetsu">'+esc(today.q.t)+'<span class="src">── '+esc(today.q.s)+'</span></blockquote>' : '') + (today.h ? '<p class="hitokoto">'+esc(today.h)+'</p>' : '') + '<a class="more" href="#hitokoto/'+today.idx+'">この候の頁 ／ 前の候を読む ▸</a>';

  /* ── たより：tayori.js ＋ 階段の公開分。今日より先の日付は出さない ── */
  let list = (window.NAKATOKO_TAYORI || []).slice();
  (window.NAKATOKO_KAIDAN || []).forEach(k => { if(!k.d) return; const tt=k.t.split("──")[0].trim(); const lab=/^「/.test(tt)?tt:"「"+tt+"」"; list.push({d:k.d, t:"一節ずつの階段に"+lab+"を加えました", url:k.url}); });
  list = list.filter(t => t.d<=todayISO).sort((a,b)=> a.d<b.d?1:(a.d>b.d?-1:0));
  const fmtISO = iso => { const p=iso.split("-"); return (+p[0])+"年"+(+p[1])+"月"+(+p[2])+"日"; };
  const abs = u => /^https?:/.test(u) ? u : "https://nakatokojuku.jp"+u;
  $("tayoriList").innerHTML = list.length ? list.map((t,i) => '<a class="row" href="#tayori/'+i+'"><span class="row-t">'+esc(t.t.length>40 ? t.t.slice(0,40)+"…" : t.t)+'</span><span class="row-d">'+esc(fmtISO(t.d))+'</span></a>').join("") : '<p class="muted pad">まだ、たよりはありません。</p>';
  function renderTayori(i){
    const t = list[i]; if(!t){ $("tayoriDetail").innerHTML=""; return; }
    $("tayoriDetail").innerHTML = '<div class="dt-head"><div class="dt-kou" style="font-size:1rem">中常だより</div><div class="dt-yomi">'+esc(fmtISO(t.d))+'</div></div><div class="dt-body"><p class="hitokoto" style="margin-top:12px">'+esc(t.t)+'</p>'+(t.url ? '<p style="padding:6px 0 12px"><a class="btn" href="'+esc(abs(t.url))+'" target="_blank" rel="noopener">読む</a></p>' : '')+'</div>';
  }
  $("topTayori").innerHTML = list.slice(0,3).map((t,i) => '<a class="mini" href="#tayori/'+i+'"><span class="mini-d">'+esc(t.d.slice(5).replace("-","/"))+'</span>'+esc(t.t.length>34 ? t.t.slice(0,34)+"…" : t.t)+'</a>').join("");

  /* ── 開催予定：events.js。会場は行に v:（会場名）addr:（住所）が無ければ二の丸能楽堂 ── */
  const up = window.nakatokoUpcoming ? window.nakatokoUpcoming() : [];
  const fmtD = iso => window.nakatokoFmtDate ? window.nakatokoFmtDate(iso, true) : iso;
  $("kaisaiList").innerHTML = up.length ? up.map(e => '<div class="ev"><div class="ev-d">'+esc(fmtD(e.d))+'</div><div class="ev-t">'+esc(e.t)+'</div><div class="ev-v">'+esc(e.v||VENUE.name)+'<br><span class="muted">'+esc(e.addr||VENUE.addr)+'</span></div>'+(e.url ? '<a class="btn" href="'+esc(e.url)+'" target="_blank" rel="noopener">お申し込み</a>' : '')+'</div>').join("")
    : '<p class="muted pad">次回の日程は、決まり次第ここに掲載します。</p>';
  $("topNext").textContent = up.length ? "次回 "+fmtD(up[0].d).replace(/^\d+年/,"") : "決まり次第掲載";

  /* ── 画面の切り替え（#top #hitokoto #hitokoto/12 #tayori #tayori/0 #kaisai #menu #access #howto #privacy） ── */
  const views = ["top","hitokoto","hitokotoDetail","tayori","tayoriDetail","kaisai","menu","access","howto","privacy"];
  function route(){
    const h = (location.hash||"#top").slice(1).split("/"); let v = h[0]||"top";
    if (v==="hitokoto" && h[1]!==undefined){ renderHitokoto(+h[1]); v="hitokotoDetail"; }
    if (v==="tayori" && h[1]!==undefined){ renderTayori(+h[1]); v="tayoriDetail"; }
    if (!views.includes(v)) v="top";
    views.forEach(id => { const el=$("v-"+id); if(el) el.hidden = (id!==v); });
    const tab = {top:"top",hitokoto:"hitokoto",hitokotoDetail:"hitokoto",tayori:"tayori",tayoriDetail:"tayori",kaisai:"top"}[v] || "menu";
    document.querySelectorAll(".tab").forEach(a => a.classList.toggle("on", a.dataset.tab===tab));
    window.scrollTo(0,0);
  }
  window.addEventListener("hashchange", route); route();
  document.querySelectorAll(".back").forEach(b => b.addEventListener("click", e => { e.preventDefault(); if (history.length>1) history.back(); else location.hash = b.getAttribute("href"); }));

  /* ── ホーム画面に追加の案内：すでにアプリとして開いていれば出さない ── */
  const standalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone===true;
  if (standalone) document.body.classList.add("standalone");
  if ("serviceWorker" in navigator && location.protocol==="https:") navigator.serviceWorker.register("/app/sw.js").catch(()=>{});
})();
