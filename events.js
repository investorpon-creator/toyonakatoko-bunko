/* 開催予定 ── index.html（能楽堂プログラムの「次回は…」と「日程とお申し込み」）、taiken/index.html・taiken/seki/index.html（次回開催と「日程とお申し込み」）、アプリが自動で読む。
   過ぎた日付は画面から自動で消え、次の日付が繰り上がる。予定が無くなると「決まり次第ここに掲載」と出る。
   塾主の編集：下の配列に1行足す（日付は YYYY-MM-DD）。消す必要はない。
     岡崎城の回 → {d:"2027-04-19", t:"講義お稽古", url:OKAZAKI_URL, apply:OKAZAKI_APPLY}
     伊勢の回   → {d:"2027-04-01", t:"講義お稽古（伊勢）", url:ISE_URL, v:ISE_V, addr:ISE_ADDR, apply:ISE_APPLY}
   休みの回は cancel:"理由" を足す（日程表に「休講」と出る。次回の案内・申込ボタンには出さない）。
   会場が二の丸能楽堂でない回は v:"会場名", addr:"住所" を足す（アプリの「次回開催」に出る。無ければ能楽堂と出る）
   apply＝その日の申込先（MOSHのサービスごと）。時間を変えたら下の OKAZAKI_APPLY / ISE_APPLY を直す。 */
var OKAZAKI_URL = "https://mosh.jp/nakatokojuku/articles/66137";
var OKAZAKI_APPLY = [
  {time:"13:00〜14:30", n:"和儀お稽古（初心・初級）", url:"https://mosh.jp/services/363371"},
  {time:"14:45〜15:45", n:"度會神道講義", url:"https://mosh.jp/services/352233"},
  {time:"16:00〜16:50", n:"和儀お稽古（初級〜中級）", url:"https://mosh.jp/services/363372"}
];
var ISE_URL = "https://nakatokojuku.jp/taiken/seki/#apply";
var ISE_V = "伊勢 世木神社", ISE_ADDR = "三重県伊勢市吹上1丁目2-6（伊勢市駅前）";
var ISE_APPLY = [
  {time:"14:00〜15:30", n:"和儀お稽古", url:"https://mosh.jp/services/415886"},
  {time:"15:50〜17:50", n:"度會神道講義", url:"https://mosh.jp/services/415882"}
];
window.NAKATOKO_EVENTS = [
  {d:"2026-08-24", t:"講義お稽古", url:OKAZAKI_URL},
  {d:"2026-09-28", t:"講義お稽古", url:OKAZAKI_URL},
  {d:"2026-10-19", t:"講義お稽古", url:OKAZAKI_URL},
  {d:"2026-11-01", t:"講義お稽古（伊勢）", url:"https://mosh.jp/nakatokojuku", v:ISE_V, addr:ISE_ADDR},
  {d:"2026-11-16", t:"講義お稽古", url:OKAZAKI_URL, apply:OKAZAKI_APPLY},
  {d:"2026-12-01", t:"講義お稽古（伊勢）", url:ISE_URL, v:ISE_V, addr:ISE_ADDR, apply:ISE_APPLY},
  {d:"2027-01-15", t:"講義お稽古（伊勢）", v:ISE_V, addr:ISE_ADDR, cancel:"お正月のため、1月の伊勢の回はお休みします"},
  {d:"2027-01-21", t:"講義お稽古", url:OKAZAKI_URL, apply:OKAZAKI_APPLY},
  {d:"2027-02-01", t:"講義お稽古（伊勢）", url:ISE_URL, v:ISE_V, addr:ISE_ADDR, apply:ISE_APPLY},
  {d:"2027-02-22", t:"講義お稽古", url:OKAZAKI_URL, apply:OKAZAKI_APPLY},
  {d:"2027-03-01", t:"講義お稽古（伊勢）", url:ISE_URL, v:ISE_V, addr:ISE_ADDR, apply:ISE_APPLY},
  {d:"2027-03-22", t:"講義お稽古", url:OKAZAKI_URL, apply:OKAZAKI_APPLY}
];
/* 「次回は…」に続けて添える一言（空文字にすれば何も出ない） */
window.NAKATOKO_EVENTS_NOTE = "前回は満員御礼をいただきました";

/* 共通の道具 ── 今日以降の予定を日付順で返す（休講は除く）／休講も含めて返す／ISO日付を「9月28日（月）」にする */
window.nakatokoToday = function(){
  var t = new Date(); return t.getFullYear()+"-"+("0"+(t.getMonth()+1)).slice(-2)+"-"+("0"+t.getDate()).slice(-2);
};
window.nakatokoSchedule = function(){
  var today = window.nakatokoToday();
  return (window.NAKATOKO_EVENTS||[]).filter(function(e){return e.d>=today;}).sort(function(a,b){return a.d<b.d?-1:1;});
};
window.nakatokoUpcoming = function(){
  return window.nakatokoSchedule().filter(function(e){return !e.cancel;});
};
window.nakatokoFmtDate = function(iso, withYear){
  var p = iso.split("-"), dt = new Date(+p[0], +p[1]-1, +p[2]);
  var w = ["日","月","火","水","木","金","土"][dt.getDay()];
  return (withYear ? (+p[0])+"年" : "") + (+p[1]) + "月" + (+p[2]) + "日（" + w + "）";
};

/* 「日程とお申し込み」の表 ── 日付ごとに会場と、受けたいものごとの申込ボタンを並べる。休講の回は理由を添えて残す。
   使い方：<div class="nk-sched" data-venue="all|okazaki|ise"></div> を置き、このファイルを読むだけ。 */
(function(){
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c];});}
  var css = ".nk-sched{margin:0;text-align:left;line-height:1.6;letter-spacing:.02em}"+
    ".nk-sched .nk-row{border-top:1px solid rgba(128,128,128,.35);padding:.9rem 0}"+
    ".nk-sched .nk-row:last-child{border-bottom:1px solid rgba(128,128,128,.35)}"+
    ".nk-sched .nk-head{display:flex;flex-wrap:wrap;gap:.2rem .8rem;align-items:baseline;margin-bottom:.5rem}"+
    ".nk-sched .nk-d{font-weight:700;letter-spacing:.06em}"+
    ".nk-sched .nk-v{font-size:.85em;opacity:.8}"+
    ".nk-sched .nk-btns{display:flex;flex-wrap:wrap;gap:.45rem}"+
    ".nk-sched .nk-btn{display:inline-block;padding:.5rem .85rem;border:1px solid currentColor;border-radius:3px;font-size:.82em;line-height:1.45;text-decoration:none;color:inherit}"+
    ".nk-sched .nk-btn:hover{background:rgba(128,128,128,.12)}"+
    ".nk-sched .nk-btn b{font-weight:700;margin-right:.35em}"+
    ".nk-sched .nk-off .nk-d{opacity:.6}"+
    ".nk-sched .nk-tag{display:inline-block;padding:.05rem .5rem;border-radius:2px;background:#9b2c2c;color:#fff;font-size:.78em;letter-spacing:.1em}"+
    ".nk-sched .nk-why{font-size:.85em;margin:0}"+
    ".nk-sched .nk-empty{opacity:.75}"+
    ".nk-sched .nk-foot{font-size:.78em;opacity:.75;margin:.7rem 0 0}";
  function isIse(e){return !!(e.v && e.v.indexOf("世木")>-1);}
  function render(el){
    var want = el.getAttribute("data-venue")||"all";
    /* 当日の回はMOSHの受付が前日のうちに締まるので、申込表には翌日以降だけを出す */
    var today = window.nakatokoToday();
    var list = window.nakatokoSchedule().filter(function(e){
      if(e.d<=today) return false;
      if(!e.apply && !e.cancel) return false;
      return want==="all" || (want==="ise" ? isIse(e) : !isIse(e));
    });
    if(!list.length){ el.innerHTML='<p class="nk-empty">次回の日程は、決まり次第ここに掲載します。</p>'; return; }
    var h = list.map(function(e){
      var v = e.v || "岡崎城 二の丸能楽堂";
      var head = '<div class="nk-head"><span class="nk-d">'+esc(window.nakatokoFmtDate(e.d, e.d.slice(0,4)!==window.nakatokoToday().slice(0,4)))+'</span>'+
        (want==="all" ? '<span class="nk-v">'+esc(v)+'</span>' : '')+(e.cancel?'<span class="nk-tag">休講</span>':'')+'</div>';
      if(e.cancel) return '<div class="nk-row nk-off">'+head+'<p class="nk-why">'+esc(e.cancel)+'</p></div>';
      return '<div class="nk-row">'+head+'<div class="nk-btns">'+e.apply.map(function(a){
        return '<a class="nk-btn" href="'+esc(a.url)+'" target="_blank" rel="noopener noreferrer"><b>'+esc(a.time)+'</b>'+esc(a.n)+'を申し込む ▸</a>';
      }).join("")+'</div></div>';
    }).join("");
    el.innerHTML = h + '<p class="nk-foot">講義とお稽古は、それぞれ別にお申し込みください。ボタンからは外部の申込ページ（MOSH）へ移ります。日にちは申込ページで選べます。</p>';
  }
  function run(){
    var els = document.querySelectorAll(".nk-sched"); if(!els.length) return;
    if(!document.getElementById("nk-sched-css")){ var s=document.createElement("style"); s.id="nk-sched-css"; s.textContent=css; document.head.appendChild(s); }
    for(var i=0;i<els.length;i++) render(els[i]);
  }
  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded", run); else run();
})();
