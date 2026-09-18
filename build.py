#!/usr/bin/env python3
"""src/plan-a.html（原本・1枚もの）から、独立した各ページを生成する。

**生成物を直接編集しないこと。** 原本を直して `python3 build.py` を走らせる。
生成物だけを git revert しても次のビルドで元に戻ってしまうため、
原本と生成物は必ず一緒にコミットする（かみのてで踏んだ事故）。

**説明はページに1回だけ。** トップは各節の要約（名前・数字・見出しだけ）に
とどめ、中身の説明は下層ページで行う。原本の文章はどちらにも書かず、
下層ページ用の原文から digest_* が抜き出して要約を組み立てる。

出力:
  index.html    トップ（各節の要約＋「詳しく見る」）
  service.html  ご紹介できる人材
  support.html  登録支援機関としての支援
  flow.html     受入れまでの流れ
  partners.html 自社グループと提携機関
  company.html  企業情報（代表ごあいさつ＋会社概要）
  faq.html      よくあるご質問
  news.html     過去のお知らせ（src/news.json から。旧サイトの全24件）
  contact.html  お問い合わせ
  privacy.html  プライバシーポリシー（旧サイトの本文を入れるまでは枠だけ）
"""
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src"

# 案 → (原本, 一言)。**ページ構成は案で変えない**（比べられなくなるため）。
# 本番サイト。デザインは案B（2026-09-18 決定）。原本は src/site.html の1つだけ。
PLANS = {
    ".": ("site.html", "本番（案B）"),
}
# ★公開前は noindex を付ける。DNSを切り替えて公開するときに False にする。
NOINDEX = True
# 原本は、build.py が差し込むCSSが使う変数を必ず定義すること。
#   --gold（差し色）／--gold-d（濃い差し色）／--serif（見出しの書体）
#   --line ／--line-s（罫線）／--muted（補助の文字）／--panel（薄い地）／--ink（文字）
# 名前は案Aから来ているが中身は案ごとに違う（案Cでは青とグレーを入れている）。

# 出力ファイル → (原本の節id, メニュー表示名, ページ見出し, 英字ラベル, 説明)
# 説明は、原本の節に導入文があればそちらを優先する（節の導入文は下層でしか
# 出さないため。トップには TOP_LEAD の短い文を置く）。
PAGES = {
    "service.html":  ("visas",    "ご紹介できる人材", "ご紹介できる人材", "SERVICE",
                      "就労が可能な5つの在留資格すべてに対応しています。"),
    "support.html":  ("support",  "支援内容",       "登録支援機関としての支援", "SUPPORT",
                      "特定技能で義務づけられている支援です。"),
    "flow.html":     ("flow",     "受入れの流れ",   "受入れまでの流れ", "FLOW",
                      "ご相談から就労開始までの目安です。"),
    "partners.html": ("partners", "提携機関",       "自社グループと提携機関", "GROUP & PARTNERS",
                      "監理団体を自社で設立しているため、一貫してお引き受けできます。"),
    "company.html":  ("company",  "企業情報",       "企業情報", "COMPANY",
                      "会社の概要と、代表からのごあいさつです。"),
    "faq.html":      ("faq",      "よくあるご質問", "よくあるご質問", "FAQ",
                      "費用や期間など、はじめてのご検討でよくいただくご質問です。"),
}
# トップに置く一行。**下層の導入文とは別の文にする**（同じ文を2回読ませない）。
TOP_LEAD = {
    "visas":    "在留資格ごとに、ご紹介できる人材が変わります。",
    "support":  "義務づけられた10項目を、外部に出さず弊社で行います。",
    "flow":     "ご相談から就労開始まで、おおむね5〜6か月です。",
    "partners": "募集から就労後の支援まで、間に他社を挟みません。",
    "company":  "",
    "faq":      "",
}

# メニューの並び（左3つ／ロゴ／右3つ）
NAV_L = [("service.html", "ご紹介できる人材"), ("support.html", "支援内容"), ("flow.html", "受入れの流れ")]
NAV_R = [("partners.html", "提携機関"), ("company.html", "企業情報"), ("contact.html", "お問い合わせ")]

# 節id → 出力ファイル。原本のアンカーをページへの参照に張り替えるのに使う
ANCHOR = {sec: out for out, (sec, *_ ) in PAGES.items()}
ANCHOR["contact"] = "contact.html"

EXTRA_CSS = """
/* ---- 下層ページの見出し（build.py が差し込む） ---- */
.page-head{padding:64px 0 0; text-align:center}
.page-head .en{font-family:var(--serif); font-weight:300; color:var(--gold);
  font-size:12px; letter-spacing:.28em; display:block; margin-bottom:14px}
.page-head h1{font-family:var(--serif); font-weight:300; font-size:clamp(23px,3.2vw,31px);
  letter-spacing:.16em; margin:0 0 14px}
.page-head p{color:var(--muted); font-size:14px; margin:0; letter-spacing:.04em}
.crumb{font-size:12px; color:var(--muted); letter-spacing:.06em; padding:16px 0 0}
.crumb a{text-decoration:none}
.crumb a:hover{color:var(--gold)}
/* 下層では節の見出しを重ねて出さない（ページ見出しと二重になる） */
.sub .sec-head{display:none}
.sub section{padding:44px 0 86px}
/* トップの各節に付ける「詳しく見る」 */
.more{text-align:center; margin-top:40px}

/* ---- トップの要約（説明は下層ページに置く） ---- */
.chips{display:flex; flex-wrap:wrap; gap:10px; justify-content:center}
.chip{border:1px solid var(--line); background:#fff; padding:11px 20px;
  font-size:14.5px; letter-spacing:.06em; white-space:nowrap}
.chips .num{color:var(--gold,#b39861); font-size:12px; margin-right:8px;
  font-variant-numeric:tabular-nums}
.chips-note{text-align:center; color:var(--muted); font-size:13px; margin:16px 0 0;
  letter-spacing:.04em}
.tsteps{display:flex; flex-wrap:wrap; gap:10px; justify-content:center;
  list-style:none; margin:0; padding:0}
.tstep{border:1px solid var(--line); background:#fff; padding:14px 18px; text-align:center;
  flex:1 1 150px; max-width:230px}
.tstep .num{display:block; color:var(--gold,#b39861); font-size:11.5px; letter-spacing:.14em;
  margin-bottom:6px; font-variant-numeric:tabular-nums}
.tstep b{display:block; font-weight:400; font-size:15px; letter-spacing:.05em}
.tstep span{display:block; color:var(--muted); font-size:12px; margin-top:6px}
.qlist{list-style:none; margin:0; padding:0; max-width:760px; margin-inline:auto}
.qlist li{border-bottom:1px solid var(--line)}
.qlist a{display:block; padding:18px 4px; text-decoration:none; font-size:14.5px;
  letter-spacing:.04em}
.qlist a:hover{color:var(--gold,#b39861)}
/* トップのごあいさつは見出しと署名だけなので、お写真と高さが揃わない */
.top-greet{align-items:center}
.top-greet .ph{aspect-ratio:4/5}

/* ---- 過去のお知らせ ---- */
.nlist{padding:52px 0 86px}
.nitem{display:grid; grid-template-columns:140px 1fr; gap:34px;
  padding:32px 0; border-bottom:1px solid var(--line)}
.nitem:first-child{border-top:1px solid var(--line)}
/* ★グリッドの子は既定で min-width:auto。中に長い英数字があると列が縮まず、
   320pxで箱からはみ出す（案Cのお知らせで実際に出た）。 */
.nitem > *{min-width:0}
.nitem time{font-family:var(--serif); color:var(--gold-d); font-size:15px;
  letter-spacing:.08em; font-variant-numeric:tabular-nums; padding-top:2px}
.nbody p{margin:0 0 10px; font-size:14.5px; letter-spacing:.02em;
  overflow-wrap:break-word}
.nbody p:first-child{font-family:var(--serif); font-weight:400; font-size:17px;
  letter-spacing:.08em; line-height:1.8; margin-bottom:14px}
.nbody p:last-child{margin-bottom:0}
.ngal{display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
  gap:12px; margin-top:18px}
.ngal img{width:100%; height:170px; object-fit:cover}

/* ---- 会社概要の表 ---- */
.outline{width:100%; border-collapse:collapse; margin-top:56px; font-size:14px}
.outline th,.outline td{text-align:left; padding:16px 18px; border-bottom:1px solid var(--line);
  vertical-align:top; letter-spacing:.02em}
.outline th{width:190px; font-family:var(--serif); font-weight:400; color:var(--gold-d);
  letter-spacing:.1em; white-space:nowrap}

/* ---- グループの事業 ---- */
.gcards{display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:18px}
.gcard{background:#fff; border:1px solid var(--line); padding:22px 24px}
.gcard h3{font-size:16.5px; margin:0 0 6px}
.gcard .gtag{font-size:11.5px; color:var(--gold,#b39861); margin-bottom:8px; letter-spacing:.06em}
.gcard p{font-size:13.5px; color:var(--muted); margin:0; line-height:1.9}

/* ---- お問い合わせ ---- */
.contact-grid{display:grid; grid-template-columns:1fr 1fr; gap:48px; margin-top:20px}
.contact-box{border:1px solid var(--line); padding:34px 32px}
.contact-box h3{font-family:var(--serif); font-weight:400; font-size:18px;
  letter-spacing:.12em; margin:0 0 14px}
.contact-box .big{font-family:var(--serif); font-size:29px; letter-spacing:.06em; line-height:1.4}
/* メールアドレスは1語なので、狭い幅では折り返せず箱からはみ出す（390pxで
   scrollW 421 になった）。長い語を折り返させ、字送りも詰める。 */
.contact-box .big.mail{font-size:21px; letter-spacing:.02em; overflow-wrap:anywhere; word-break:break-all}
.contact-box p{font-size:13.5px; color:var(--muted); margin:8px 0 0}
.plain{font-size:14px; letter-spacing:.02em}

@media (max-width:760px){
  /* 「住居の確保・生活に必要な契約の支援」は390pxで1行に収まらない */
  .chip{padding:9px 15px; font-size:13.5px; white-space:normal}
  .tstep{flex:1 1 128px; padding:12px 10px}
  .nitem{grid-template-columns:1fr; gap:10px; padding:24px 0}
  .nlist{padding:32px 0 56px}
  .outline th{width:auto; display:block; border-bottom:none; padding-bottom:0}
  .outline td{display:block; padding-top:4px}
  .contact-grid{grid-template-columns:1fr; gap:26px}
  .sub section{padding:28px 0 56px}
}
"""


# ============ 開いたときの動き ============
# かみのて保育園のサイト（kaminote-design/plan-a.html）と同じ仕組みをそのまま
# 持ってきている。**隠す指定（ANIM_SEL_CSS）と、JSが探す並び（ANIM_SEL_JS）は
# 必ず同じにすること。** 食い違うと、隠れたまま出てこない要素ができる。
#
# 中身を先に出す箱（カードの並びなど）は、箱ごとではなく中身を1枚ずつ出す。
# そのため箱自身は :not() で外す。ここも2つの並びで揃える。
ANIM_BOXES = ["visas", "support", "flow", "partners", "chips", "tsteps",
              "qlist", "gcards", "stats", "contact-grid"]
_NOT = "".join(f":not(.{c})" for c in ANIM_BOXES)
_CHILDREN = ",\n".join(f".anim .{c} > *" for c in ANIM_BOXES)

ANIM_SEL_CSS = (f".anim section > .wrap > *{_NOT},\n"
                f"{_CHILDREN},\n"
                ".anim .nlist > .wrap > *,\n"
                ".anim .cta > .wrap > *")

ANIM_SEL_JS = ("section > .wrap > *" + _NOT + ","
               + ",".join(f".{c} > *" for c in ANIM_BOXES) + ","
               + ".nlist > .wrap > *,"
               + ".cta > .wrap > *")

ANIM_HEAD = """
<!-- ============ 開いたときの動き（前半：先に隠す） ============
     ★<head> に置くこと。ページの一番下に置くと、いったん普通に描かれてから
     隠れるので、一瞬ちらついてから動き出す。
     ・動かすのは透明度と位置だけ（レイアウトは動かさない）
     ・「動きを減らす」設定と印刷のときは動かさない                        -->
<style>
@keyframes rise   { from{opacity:0; transform:translateY(14px)} to{opacity:1; transform:none} }
@keyframes riseSp { from{opacity:0; transform:translateY(9px)}  to{opacity:1; transform:none} }
@keyframes zoomOut{ from{transform:scale(1.06)} to{transform:none} }

/* ヒーローとお知らせ帯はJSを使わずCSSだけで動かす。JSがクラスを付けるのを
   待つと、待っている間に文字が見えてしまう（環境が遅いほど長く見える）。 */
.hero .bg img{animation:zoomOut 1.8s cubic-bezier(.2,.7,.3,1) both}
.hero-copy .wrap > *{animation:rise .7s cubic-bezier(.2,.7,.3,1) both}
.hero-copy .wrap > *:nth-child(1){animation-delay:.15s}
.hero-copy .wrap > *:nth-child(2){animation-delay:.30s}
.hero-copy .wrap > *:nth-child(3){animation-delay:.45s}
.hero-copy .wrap > *:nth-child(4){animation-delay:.60s}
.hero-copy .wrap > *:nth-child(5){animation-delay:.75s}
.newsband{animation:rise .7s cubic-bezier(.2,.7,.3,1) .55s both}
.badges{animation:rise .7s cubic-bezier(.2,.7,.3,1) .45s both}

/* スクロールで出てくる分だけ、JSがあるとき（.anim）に隠しておく */
__SEL__{opacity:0}
.anim .on{animation:rise .7s cubic-bezier(.2,.7,.3,1) both}

@media (max-width:700px){ .anim .on{animation-name:riseSp} }

@media (prefers-reduced-motion:reduce){
  __SEL__{opacity:1}
  .anim .on, .hero .bg img, .hero-copy .wrap > *, .newsband, .badges{animation:none}
}
@media print{
  __SEL__{opacity:1 !important}
  .anim .on, .hero .bg img, .hero-copy .wrap > *, .newsband, .badges{animation:none !important}
}
</style>
<script>
// 最初の描画より前に付ける（あとから付けると、見えていたものが消えてから動く）
document.documentElement.classList.add('anim');
// 保険: 下のJSが動かなかったときは、隠したままにしない
setTimeout(function(){
  if(!window.__animReady){ document.documentElement.classList.remove('anim'); }
}, 4000);
</script>
""".replace("__SEL__", ANIM_SEL_CSS)

ANIM_JS = """
<!-- ============ 開いたときの動き（後半：順に出す） ============
     隠す指定と対象の並びは <head> 側にある。ここでは出す順番だけを決める。 -->
<script>
(function () {
  // ★ここの並びは <head> の隠す指定と必ず同じにすること
  var ANIM_SEL = '__SEL__';
  var units = [].slice.call(document.querySelectorAll(ANIM_SEL));

  function sweep() {
    var vh = window.innerHeight || document.documentElement.clientHeight;
    var shown = [];
    for (var i = units.length - 1; i >= 0; i--) {
      var r = units[i].getBoundingClientRect();
      if (r.top < vh * 0.92 && r.bottom > 0) {
        shown.push(units[i]);
        units.splice(i, 1);                            // 一度出したら見張らない
      }
    }
    if (!shown.length) { return; }
    shown.sort(function (a, b) {
      return a.getBoundingClientRect().top - b.getBoundingClientRect().top;
    }).forEach(function (el, i) {
      el.style.animationDelay = (i * 0.06) + 's';      // 並んでいるものは少しずつずらす
      el.classList.add('on');
    });
    if (!units.length) {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    }
  }

  var waiting = false;
  function onScroll() {
    if (waiting) { return; }
    waiting = true;
    requestAnimationFrame(function () { waiting = false; sweep(); });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  sweep();                                             // 最初から見えている分
  window.addEventListener('load', sweep);              // 画像が入って位置が確定したあと

  window.__animReady = true;                           // <head> の保険に「動いた」と伝える

  // 保険: スクロールを拾えない環境でも、中身が消えたままにはしない
  setTimeout(function () {
    units.forEach(function (el) { el.classList.add('on'); });
    units.length = 0;
  }, 5000);
})();
</script>
""".replace("__SEL__", ANIM_SEL_JS)


# 案Bは見出しが左揃えなので、要約も左に寄せる（案Aは中央揃え）。
PLAN_CSS = {
    "b": """
.chips,.tsteps{justify-content:flex-start}
.chips-note{text-align:left}
.qlist{max-width:none; margin-inline:0}
""",
    # 案Cは参考サイトに合わせて、下層のページ見出しを「巨大な英字＋小さな和文」の
    # 左寄せにし、うしろに薄いグレーの地紋を敷く。表は罫線を使わず縞にする。
    "c": """
.crumb{padding:16px 0 0; color:var(--muted)}
.page-head{text-align:left; padding:34px 0 46px; position:relative; overflow:hidden}
/* 薄いグレーの地紋。上だけに出して下へ消す（参考サイトの見出し背景） */
.page-head::before{content:""; position:absolute; left:0; right:0; top:0; height:150px; z-index:0;
  background:
    linear-gradient(180deg,rgba(255,255,255,0) 0%,#fff 88%),
    repeating-linear-gradient(90deg,#eef1f2 0 74px,transparent 74px 90px),
    repeating-linear-gradient(0deg,#eef1f2 0 22px,transparent 22px 40px)}
.page-head .wrap{position:relative; z-index:1}
.page-head .en{font-family:var(--serif); font-weight:600; color:var(--ink);
  font-size:clamp(28px,5vw,50px); letter-spacing:.24em; line-height:1.15; margin-bottom:6px}
.page-head h1{font-family:var(--sans); font-weight:400; color:var(--muted);
  font-size:clamp(13px,1.6vw,15px); letter-spacing:.14em; margin:0 0 14px}
.page-head p{color:var(--muted); max-width:60em}
.sub section{padding:56px 0 86px}
/* お知らせ */
.nitem{border-bottom:1px solid var(--line)}
.nitem:first-child{border-top:1px solid var(--line)}
.nitem time{font-family:var(--serif); font-weight:600; color:var(--muted); letter-spacing:.08em}
.nbody p:first-child{font-family:var(--sans); font-weight:700; color:var(--ink); font-size:16.5px}
/* 会社概要は罫線を引かず、行の縞で読ませる（参考サイトと同じ） */
.outline{margin-top:48px}
.outline th,.outline td{border-bottom:none; padding:18px 22px}
.outline tr:nth-child(odd) th,.outline tr:nth-child(odd) td{background:var(--line-s)}
.outline th{font-family:var(--sans); font-weight:700; color:var(--ink); letter-spacing:.06em}
/* グループの事業・お問い合わせ */
.gcard{border:none; box-shadow:0 2px 14px rgba(0,31,63,.08); border-right:3px solid var(--blue)}
.gcard h3{color:var(--blue)}
.gcard .gtag{color:var(--muted); letter-spacing:.12em}
.contact-box{border:none; box-shadow:0 2px 14px rgba(0,31,63,.08); border-top:3px solid var(--blue)}
.contact-box h3{font-family:var(--sans); font-weight:700; color:var(--ink); letter-spacing:.08em}
.contact-box .big{font-family:var(--serif); color:var(--blue); font-weight:700}
/* トップの要約 */
.chip{border-radius:0; border-color:var(--line); box-shadow:0 2px 10px rgba(0,31,63,.06)}
.chips .num{color:var(--muted); letter-spacing:.14em}
.tstep{border:none; box-shadow:0 2px 12px rgba(0,31,63,.07); border-top:3px solid var(--blue)}
.tstep .num{font-family:var(--serif); color:var(--muted); font-weight:600; letter-spacing:.24em}
.qlist li{border-bottom:1px solid var(--line)}
.qlist a{color:var(--ink); font-weight:700}
.qlist a:hover{color:var(--blue)}
/* トップのごあいさつは見出しと署名だけなので、縦長のお写真だと余白が空く */
.top-greet .ph{aspect-ratio:1/1}
@media (max-width:760px){
  .page-head{padding:22px 0 30px}
  .sub section{padding:34px 0 58px}
  .outline th,.outline td{padding:12px 16px}
}
""",
}


def parts(src_name, key=""):
    """原本を、使い回す部品に切り分ける。"""
    s = (SRC / src_name).read_text(encoding="utf-8")
    head = s[: s.index("</head>")]
    head = head.replace("</style>", EXTRA_CSS + PLAN_CSS.get(key, "") + "</style>")
    header = s[s.index('<div class="utility">'): s.index('<div class="hero">')]
    hero = s[s.index('<div class="hero">'): s.index('<section id="visas">')]
    cta = s[s.index('<div class="cta" id="contact">'): s.index("<footer>")]
    footer = s[s.index("<footer>"): s.index('<div class="note">')]
    note = s[s.index('<div class="note">'):]
    secs = {}
    for m in re.finditer(r'<section[^>]*id="(\w+)".*?</section>\s*', s, re.S):
        secs[m.group(1)] = m.group(0)
    return head, header, hero, cta, footer, note, secs


def sec_head(frag):
    """節の見出し（英字ラベル・見出し・導入文）を取り出す。導入文は下層ページの
    ページ見出しに回す。原本にHTML（<strong>）が入るのでエスケープしない。"""
    en = re.search(r'<span class="en">(.*?)</span>', frag, re.S)
    h2 = re.search(r"<h2>(.*?)</h2>", frag, re.S)
    ld = re.search(r"<h2>.*?</h2>\s*<p>(.*?)</p>", frag, re.S)
    return (en.group(1).strip() if en else "",
            h2.group(1).strip() if h2 else "",
            ld.group(1).strip() if ld else "")


def div_block(frag, marker):
    """marker で始まる div を、対応する閉じタグまで丸ごと取り出す。
    入れ子があるので単純な正規表現では切れない。"""
    i = frag.index(marker)
    depth = 0
    for m in re.finditer(r"<div\b|</div>", frag[i:]):
        depth += 1 if m.group(0) == "<div" else -1
        if depth == 0:
            return frag[i: i + m.end()]
    raise ValueError(marker)


def top_section(frag, sec_id, inner, more_href):
    """トップ用の節。見出しと要約だけを置き、説明は下層ページに任せる。"""
    en, h2, _ = sec_head(frag)
    alt = ' class="alt"' if 'class="alt' in frag[: frag.index(">") + 1] else ""
    lead = TOP_LEAD.get(sec_id, "")
    return (f'<section{alt} id="{sec_id}">\n  <div class="wrap">\n'
            f'    <div class="sec-head"><span class="en">{en}</span><h2>{h2}</h2>'
            f'{f"<p>{lead}</p>" if lead else ""}</div>\n'
            f"    {inner}\n"
            f'    <div class="more"><a class="btn-more" href="{more_href}">'
            f"<span>詳しく見る</span></a></div>\n  </div>\n</section>\n\n")


def chips(items):
    return ('<div class="chips">'
            + "".join(f'<span class="chip">{n}</span>' for n in items)
            + "</div>")


def digest(secs):
    """トップに並べる要約を、下層ページ用の原文から組み立てる。
    **原文をそのまま貼らない**（同じ説明が2ページに出てしまうため）。"""
    out = {}

    # 在留資格は名前だけ。実績の数字はトップだけに置く（下層からは外す）。
    f = secs["visas"]
    names = re.findall(r'<div class="visa">.*?<h3>(.*?)</h3>', f, re.S)
    out["visas"] = top_section(f, "visas", chips(names) + div_block(f, '<div class="stats">'),
                               "service.html")

    # 支援は代表的な4つだけ挙げ、10項目の中身は support.html で説明する。
    f = secs["support"]
    sups = re.findall(r'<div class="sup"><span class="c">\d+</span>(.*?)</div>', f, re.S)
    pick = [sups[i] for i in (2, 3, 5, 6) if i < len(sups)]
    out["support"] = top_section(
        f, "support",
        chips(pick) + f'<p class="chips-note">ほか、事前ガイダンスや送迎など全{len(sups)}項目。</p>',
        "support.html")

    # 流れは手順名と期間だけ。各手順の説明は flow.html で行う。
    f = secs["flow"]
    steps = re.findall(r'<div class="step">.*?<div class="n">(.*?)</div>\s*<h3>(.*?)</h3>'
                       r'.*?<div class="d">(.*?)</div>', f, re.S)
    out["flow"] = top_section(
        f, "flow",
        '<ol class="tsteps">' + "".join(
            f'<li class="tstep"><span class="num">{n}</span><b>{t}</b><span>{d}</span></li>'
            for n, t, d in steps) + "</ol>",
        "flow.html")

    # 提携先は名称と国だけ。設立の経緯や写真は partners.html に置く。
    f = secs["partners"]
    grp = re.search(r'<div class="group-lead">.*?<h3>(.*?)</h3>', f, re.S)
    prs = re.findall(r'<div class="partner">.*?<h3>(.*?)</h3>\s*<div class="cc">(.*?)</div>', f, re.S)
    cards = [f'<span class="chip"><span class="num">自社グループ</span>{grp.group(1)}</span>'] if grp else []
    cards += [f'<span class="chip"><span class="num">{cc}</span>{nm}</span>' for nm, cc in prs]
    out["partners"] = top_section(f, "partners", '<div class="chips">' + "".join(cards) + "</div>",
                                  "partners.html")

    # ごあいさつはお写真と見出しだけ。本文は company.html で読んでいただく。
    f = secs["company"]
    h3 = re.search(r'<div class="greet">.*?<h3>(.*?)</h3>', f, re.S)
    photo = div_block(f, '<div class="ph">')
    sign = div_block(f, '<div class="sign">')
    out["company"] = top_section(
        f, "company",
        f'<div class="greet top-greet">{photo}<div><h3>{h3.group(1)}</h3>{sign}</div></div>',
        "company.html")

    # よくあるご質問は質問だけ。答えは faq.html に置く。
    f = secs["faq"]
    qs = re.findall(r"<summary>(.*?)</summary>", f, re.S)
    out["faq"] = top_section(
        f, "faq",
        '<ul class="qlist">' + "".join(
            f'<li><a href="faq.html">{q.strip()}</a></li>' for q in qs) + "</ul>",
        "faq.html")
    return out


def fill_newsband(hero, n=3):
    """ヒーロー下のお知らせ帯を news.json の最新 n 件で埋める。
    原本に直接書くと更新のたびに2案とも直すことになり、実際そのまま
    2021年で止まっていた。見出しだけを出し、本文と写真は news.html に置く。"""
    items = json.loads((SRC / "news.json").read_text(encoding="utf-8"))[:n]
    li = "".join(f'<li><time>{it["date"]}</time>'
                 f'<a href="news.html">{html.escape(it["title"])}</a></li>' for it in items)
    band = hero[hero.index('<div class="newsband">'):]
    old = band[band.index("<ul>"): band.index("</ul>") + 5]
    return hero.replace(old, f"<ul>{li}</ul>")


def nav_html(current):
    """メニュー。いま見ているページには印を付ける。"""
    def col(items):
        out = []
        for href, label in items:
            on = ' class="on"' if href == current else ""
            out.append(f'<a href="{href}"{on}>{label}</a>')
        return '<nav class="gnav">' + "".join(out) + "</nav>"
    return col(NAV_L), col(NAV_R)


def fix_links(frag, current=None):
    """原本のアンカー（#visas など）をページへの参照に張り替える。
    画像は a/ b/ の1階層下から参照するので ../ を前置する。"""
    for sec, out in ANCHOR.items():
        frag = frag.replace(f'href="#{sec}"', f'href="{out}"')
    pass  # 画像は生成物と同じ階層の img/ を指す（本番は1階層）
    return frag


def shell(head, header, footer_html, body, current, title):
    h = re.sub(r"<title>.*?</title>",
               f"<title>{html.escape(title)}｜株式会社 A and K</title>", head, count=1, flags=re.S)
    l, r = nav_html(current)
    hdr = re.sub(r'<nav class="gnav">.*?</nav>', "\x00", header, count=2, flags=re.S)
    hdr = hdr.replace("\x00", l, 1).replace("\x00", r, 1)
    # 公開前は検索に載せない。公開時に NOINDEX=False にすると外れる
    if NOINDEX and 'name="robots"' not in h:
        h = h.replace("</title>", '</title>\n<meta name="robots" content="noindex, nofollow, noarchive">', 1)
    elif not NOINDEX:
        h = re.sub(r'\s*<meta name="robots"[^>]*>', "", h)
    return (h + ANIM_HEAD + "</head>\n<body>\n\n"
            + fix_links(hdr) + body + footer_html + ANIM_JS)


def main():
    for key, (src_name, tagline) in PLANS.items():
        out_dir = ROOT / key
        out_dir.mkdir(exist_ok=True)
        build_plan(out_dir, src_name, "")
        print(f"  ← {src_name}  （{tagline}）  noindex={NOINDEX}")


def build_plan(out_dir, src_name, key=""):
    """1案ぶんの全ページを作る。**ページ構成は案で変えない。**"""
    head, header, hero, cta, footer, note, secs = parts(src_name, key)
    tail = fix_links(cta) + fix_links(footer) + note

    tops = digest(secs)
    body = fix_links(fill_newsband(hero))
    for out, (sec, _menu, _t, _en, _d) in PAGES.items():
        body += fix_links(tops[sec])
    (out_dir / "index.html").write_text(
        shell(head, header, tail, body, "index.html", "外国人材の受入れ支援"), encoding="utf-8")

    for out, (sec, _menu, ttl, en, desc) in PAGES.items():
        frag = secs[sec]
        # 節の導入文はページ見出しに上げる（下層では sec-head を隠しているため、
        # そのままだと本文が読まれない）。実績の数字はトップにだけ置く。
        lead = sec_head(frag)[2] or html.escape(desc)
        if sec == "visas":
            frag = frag.replace(div_block(frag, '<div class="stats">'), "")
        ph = (f'<div class="crumb"><div class="wrap"><a href="index.html">ホーム</a> ／ {html.escape(ttl)}</div></div>\n'
              f'<div class="page-head"><div class="wrap"><span class="en">{html.escape(en)}</span>'
              f'<h1>{html.escape(ttl)}</h1><p>{lead}</p></div></div>\n')
        extra = (outline_table() + group_section()) if out == "company.html" else ""
        (out_dir / out).write_text(
            shell(head, header, tail, '<div class="sub">' + ph + fix_links(frag) + extra + "</div>",
                  out, ttl), encoding="utf-8")

    (out_dir / "news.html").write_text(
        shell(head, header, tail, news_body(), "news.html", "過去のお知らせ"), encoding="utf-8")
    (out_dir / "contact.html").write_text(
        shell(head, header, tail, contact_body(), "contact.html", "お問い合わせ"), encoding="utf-8")
    (out_dir / "privacy.html").write_text(
        shell(head, header, tail, privacy_body(), "privacy.html", "プライバシーポリシー"), encoding="utf-8")


def group_section():
    """グループの事業。旧サイトの h1 と事業内容に、児童福祉の記載があった。
    このサイトは外国人材に絞る方針だが、**落とすのではなく紹介にとどめ、
    詳細はそれぞれのサイトへ渡す**（原則リニューアルをベースにするため）。"""
    cards = [
        ("かみのて保育園", "こども家庭庁所管 企業主導型保育事業",
         "2022年7月開園。外国にルーツのあるお子さまをお預かりしています。",
         "https://www.kaminote-hoikuen.com/"),
        ("かみのて今渡保育園", "可児市 小規模認可保育園",
         "2023年10月開園。可児市の待機児童の解消と、地域の子育て支援に取り組んでいます。", None),
        ("かみのてKIDS・かみのてSMILE", "児童発達支援・放課後等デイサービス",
         "2025年6月にかみのてKIDSが新築移転し、受け入れ人数を増やしました。", None),
        ("一時預かり事業", "",
         "新社屋の2階で、一時預かりも行っています。", None),
    ]
    items = ""
    for name, tag, desc, url in cards:
        link = (f'<p style="margin-top:8px"><a href="{url}" target="_blank" rel="noopener">'
                f'サイトを見る</a></p>' if url else "")
        items += (f'<div class="gcard"><h3>{name}</h3>'
                  f'{f"<div class=\"gtag\">{tag}</div>" if tag else ""}'
                  f'<p>{desc}</p>{link}</div>')
    return ('<section class="alt"><div class="wrap">'
            '<div class="sec-head" style="display:block"><span class="en">GROUP</span>'
            '<h2>グループの事業</h2>'
            '<p>外国人材の受入れ支援のほか、保育園と児童発達支援・放課後等デイサービスを運営しています。</p></div>'
            f'<div class="gcards">{items}</div></div></section>')


def outline_table():
    """会社概要。旧サイトの会社案内ページの内容をそのまま引き継ぐ。"""
    rows = [
        ("会社名", "株式会社 A and K"),
        ("本社所在地", "〒509-0207 岐阜県可児市今渡3-11<br>Tel 0574-66-3511／Fax 0574-66-7311"),
        ("可児今渡事務所", "〒509-0207 岐阜県可児市今渡1149-1 2F<br>Tel・Fax 0574-50-5048"),
        ("代表者", "代表取締役　兼松 厚志"),
        ("E-mail", '<a href="mailto:info@aandkcorp.com">info@aandkcorp.com</a>'),
        ("営業時間", "9:00〜18:00"),
        ("定休日", "土曜日、日曜日"),
        ("許可", "登録支援機関 登録番号 19登-000975"),
        ("事業内容", "・技能実習生の紹介及び手続き代行業務<br>・外国人留学生の紹介業務<br>"
                     "・特定技能登録支援機関<br>・外国籍児童の保育園経営<br>"
                     "・内閣府所管企業主導型保育園経営<br>・認可保育園経営<br>"
                     "・児童発達支援事業・放課後デイサービス事業"),
        ("取引銀行", "岐阜商工信用組合 可児支店<br>十六銀行 西可児支店<br>東濃信用金庫 西可児支店"),
        ("顧問", "高橋法律事務所<br>各務税理士事務所<br>NAKA社会保険労務士事務所"),
    ]
    tr = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    return ('<section><div class="wrap"><div class="sec-head" style="display:block">'
            '<span class="en">OUTLINE</span><h2>会社概要</h2></div>'
            f'<table class="outline">{tr}</table></div></section>')


def news_body():
    items = json.loads((SRC / "news.json").read_text(encoding="utf-8"))
    arts = []
    for it in items:
        body = "".join(f"<p>{html.escape(l)}</p>" for l in ([it["title"]] + it["body"]) if l)
        gal = ""
        if it["images"]:
            gal = '<div class="ngal">' + "".join(
                f'<img src="img/news/{n}" alt="" loading="lazy">' for n in it["images"]) + "</div>"
        arts.append(f'      <article class="nitem"><time>{it["date"]}</time>'
                    f'<div class="nbody">{body}{gal}</div></article>')
    return ('<div class="crumb"><div class="wrap"><a href="index.html">ホーム</a> ／ 過去のお知らせ</div></div>\n'
            '<div class="page-head"><div class="wrap"><span class="en">NEWS &amp; TOPICS</span>'
            '<h1>過去のお知らせ</h1></div></div>\n'
            '<div class="nlist"><div class="wrap">\n' + "\n".join(arts) + "\n</div></div>\n")


def contact_body():
    return ('<div class="crumb"><div class="wrap"><a href="index.html">ホーム</a> ／ お問い合わせ</div></div>\n'
            '<div class="page-head"><div class="wrap"><span class="en">CONTACT</span>'
            '<h1>お問い合わせ</h1><p>ご相談・お見積りは無料です。制度の説明だけでも承ります。</p></div></div>\n'
            '<section><div class="wrap"><div class="contact-grid">'
            '<div class="contact-box"><h3>お電話でのお問い合わせ</h3>'
            '<div class="big">0574-66-3511</div>'
            '<p>平日 9:00〜18:00（土曜日・日曜日を除く）</p></div>'
            '<div class="contact-box"><h3>メールでのお問い合わせ</h3>'
            '<div class="big mail"><a href="mailto:info@aandkcorp.com" style="text-decoration:none">info@aandkcorp.com</a></div>'
            '<p>お問い合わせフォームは公開時にご用意します。<br>'
            '職種・ご希望の人数・時期をお書き添えいただけると、ご案内がスムーズです。</p></div>'
            '</div></div></section>\n')


def privacy_body():
    return ('<div class="crumb"><div class="wrap"><a href="index.html">ホーム</a> ／ プライバシーポリシー</div></div>\n'
            '<div class="page-head"><div class="wrap"><span class="en">PRIVACY POLICY</span>'
            '<h1>プライバシーポリシー</h1></div></div>\n'
            '<section><div class="wrap"><p class="plain">'
            '現在のホームページに掲載されているプライバシーポリシーの本文を、そのまま引き継ぎます。'
            '（この見本では枠だけご用意しています。）</p></div></section>\n')


if __name__ == "__main__":
    main()
