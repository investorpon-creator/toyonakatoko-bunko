/* 開催予定 ── index.html（能楽堂プログラムの「次回は…」）と taiken/index.html（次回開催）が自動で読む。
   過ぎた日付は画面から自動で消え、次の日付が繰り上がる。予定が無くなると「決まり次第ここに掲載」と出る。
   塾主の編集：下の配列に1行足す（日付は YYYY-MM-DD）。消す必要はない。
   {d:"2026-11-16", t:"講義お稽古", url:"https://mosh.jp/nakatokojuku/articles/66137"} */
window.NAKATOKO_EVENTS = [
  {d:"2026-08-24", t:"講義お稽古", url:"https://mosh.jp/nakatokojuku/articles/66137"},
  {d:"2026-09-28", t:"講義お稽古", url:"https://mosh.jp/nakatokojuku/articles/66137"},
  {d:"2026-10-19", t:"講義お稽古", url:"https://mosh.jp/nakatokojuku/articles/66137"}
];
/* 「次回は…」に続けて添える一言（空文字にすれば何も出ない） */
window.NAKATOKO_EVENTS_NOTE = "前回は満員御礼をいただきました";

/* 共通の道具 ── 今日以降の予定を日付順で返す／ISO日付を「9月28日（月）」にする */
window.nakatokoUpcoming = function(){
  var t = new Date(); var today = t.getFullYear()+"-"+("0"+(t.getMonth()+1)).slice(-2)+"-"+("0"+t.getDate()).slice(-2);
  return (window.NAKATOKO_EVENTS||[]).filter(function(e){return e.d>=today;}).sort(function(a,b){return a.d<b.d?-1:1;});
};
window.nakatokoFmtDate = function(iso, withYear){
  var p = iso.split("-"), dt = new Date(+p[0], +p[1]-1, +p[2]);
  var w = ["日","月","火","水","木","金","土"][dt.getDay()];
  return (withYear ? (+p[0])+"年" : "") + (+p[1]) + "月" + (+p[2]) + "日（" + w + "）";
};
