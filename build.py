#!/usr/bin/env python3
"""src/plan-a.html（原本・1枚もの）から、独立した各ページを生成する。

**生成物を直接編集しないこと。** 原本を直して `python3 build.py` を走らせる。
生成物だけを git revert しても次のビルドで元に戻ってしまうため、
原本と生成物は必ず一緒にコミットする（かみのてで踏んだ事故）。

**説明はページに1回だけ。** トップは各節の要約（名前・期間・短い一文）に
とどめ、中身の説明は下層ページで行う。原本の文章はどちらにも書かず、
下層ページ用の原文から digest() が抜き出して要約を組み立てる。

トップの並び（2026-10-18 改善案その2。「何を頼めるか」と具体的なサービスを先に）:
  FV → 信頼の帯 → 人材 → 選ばれる3つの理由 → 現地での取り組み → 支援 → 流れ
  → よくあるご質問 → 会社・グループ（ABOUT US）→ お知らせ → お問い合わせ
  reasons / field / aboutus / news はトップだけの節。人材・支援・流れは
  下層ページ用の原文から digest() が要約を作る。トップは <div class="top"> で包む。

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
  privacy.html  プライバシーポリシー（旧サイトの本文を src/old/policy.txt から）
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
# 出さないため。トップの節見出しには説明文を置かない）。
PAGES = {
    "service.html":  ("visas",    "人材紹介", "ご紹介できる人材", "TALENT",
                      "企業のニーズに応じた5つの人材カテゴリーに対応しています。"),
    "support.html":  ("support",  "支援内容",       "登録支援機関としての支援", "SUPPORT",
                      "特定技能で義務づけられている支援です。"),
    "flow.html":     ("flow",     "受入れの流れ",   "受入れまでの流れ", "FLOW",
                      "ご相談から就労開始までの目安です。"),
    "partners.html": ("partners", "提携機関",       "自社グループと提携機関", "GROUP & PARTNERS",
                      "監理団体を自社で設立しているため、一貫してお引き受けできます。"),
    "company.html":  ("company",  "企業情報",       "企業情報", "COMPANY",
                      "会社の概要と、グループの事業をご紹介します。"),
    "faq.html":      ("faq",      "よくあるご質問", "よくあるご質問", "FAQ",
                      "費用や期間など、はじめてのご検討でよくいただくご質問です。"),
}
# トップの節の英字ラベル（下層のページ見出しは PAGES の英字のまま）
TOP_EN = {"visas": "OUR SERVICES", "support": "SUPPORT", "flow": "PROCESS"}
# ★トップでは節見出しのすぐ下に説明文を置かない（松本さんのご指示）。説明は下層ページで。

# メニューの並び（左3つ／ロゴ／右3つ）
NAV_L = [("service.html", "人材紹介"), ("support.html", "支援内容"), ("flow.html", "受入れの流れ")]
# お問い合わせはヘッダー上段右端のボタン1つにする（上下で重複していた）
NAV_R = [("partners.html", "提携機関"), ("company.html", "企業情報")]

# 節id → 出力ファイル。原本のアンカーをページへの参照に張り替えるのに使う
ANCHOR = {sec: out for out, (sec, *_ ) in PAGES.items()}
ANCHOR["contact"] = "contact.html"

EXTRA_CSS = """
/* ---- 下層ページの見出し（build.py が差し込む） ---- */
.page-head{padding:44px 0 40px; background:var(--panel); border-bottom:1px solid var(--line-s)}
.page-head .en{color:var(--blue); font-size:11px; font-weight:700; letter-spacing:.18em; display:block; margin-bottom:8px}
.page-head h1{font-weight:700; font-size:clamp(25px,3.2vw,34px); line-height:1.4; margin:0 0 14px; color:var(--ink)}
.page-head p{color:#4a5866; font-size:15px; margin:0; line-height:1.9; max-width:46em}
.page-head h1 .count{display:inline-block; vertical-align:middle; margin-left:14px; padding:3px 10px;
  border:1px solid var(--blue-line); border-radius:3px; font-size:11px;
  font-weight:700; letter-spacing:.14em; color:var(--blue-dd)}
.crumb{font-size:12px; color:var(--muted); letter-spacing:.06em; padding:16px 0 0; background:var(--panel)}
.crumb a{text-decoration:none}
.crumb a:hover{color:var(--blue-dd)}
/* 下層の本文は白地。節の見出しはページ見出しと重なるので、build.py が取り除いている */
.sub section, .sub section.alt{padding:56px 0 96px; background:#fff; border:0}
.sub section.gsec{background:var(--panel); padding:72px 0 88px}
/* 企業情報：考え方の一文 → 会社概要 を続けて読ませる */
.sub #company{padding-bottom:0}
.sub .about{display:block; max-width:46em}
.sub #company + section{padding-top:64px}
.outline{margin-top:0}

/* ---- 過去のお知らせ ---- */
.nlist{padding:52px 0 86px}
.nitem{display:grid; grid-template-columns:140px 1fr; gap:34px;
  padding:32px 0; border-bottom:1px solid var(--line)}
.nitem:first-child, .nfilter + .nitem{border-top:1px solid var(--line)}
.nitem{scroll-margin-top:96px}
.nitem .ncat{display:table; margin:8px 0 0}
.nfilter{display:flex; flex-wrap:wrap; gap:8px; margin-bottom:28px}
.nfilter button{font:inherit; font-size:13.5px; font-weight:700; padding:7px 16px; min-height:40px; cursor:pointer;
  background:#fff; color:var(--navy); border:1px solid var(--line); border-radius:2px}
.nfilter button.on{background:var(--navy); border-color:var(--navy); color:#fff}
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
.outline th{width:190px; font-weight:700; color:var(--blue-dd);
  letter-spacing:.1em; white-space:nowrap}

/* ---- グループの事業 ---- */
.gcards{display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:18px}
.gcard{background:#fff; border:1px solid var(--line); border-radius:6px; padding:22px 24px}
.gcard h3{font-size:16.5px; margin:0 0 6px}
.gcard .gtag{font-size:12px; font-weight:700; color:var(--blue-dd); margin-bottom:8px}
.gcard p{font-size:13.5px; color:var(--muted); margin:0; line-height:1.9}

/* ---- お問い合わせ ---- */
.contact-grid{display:grid; grid-template-columns:1fr 1fr; gap:48px; margin-top:20px}
.contact-box{border:1px solid var(--line); border-radius:6px; padding:34px 32px}
.contact-box h3{font-family:var(--serif); font-weight:400; font-size:18px;
  letter-spacing:.12em; margin:0 0 14px}
.contact-box .big{font-family:var(--serif); font-size:29px; letter-spacing:.06em; line-height:1.4}
/* メールアドレスは1語なので、狭い幅では折り返せず箱からはみ出す（390pxで
   scrollW 421 になった）。長い語を折り返させ、字送りも詰める。 */
.contact-box .big.mail{font-size:21px; letter-spacing:.02em; overflow-wrap:anywhere; word-break:break-all}
.contact-box p{font-size:13.5px; color:var(--muted); margin:8px 0 0}
.plain{font-size:14px; letter-spacing:.02em}
.pp{max-width:760px}
.pp h2{font-size:17px; font-weight:700; margin:40px 0 0; padding-bottom:10px; border-bottom:1px solid var(--line)}
.pp > p:first-child{margin-top:0}
.pp p, .pp li{font-size:15px; line-height:2}
.pp p{margin:14px 0 0}
.pp ul{margin:12px 0 0; padding-left:1.4em}
.pp-contact{margin-top:20px; padding:22px 26px; background:var(--panel); border-left:3px solid var(--gold)}
.pp-contact p{margin:0; line-height:1.9}

@media (max-width:760px){
  .nitem{grid-template-columns:1fr; gap:10px; padding:24px 0}
  .nlist{padding:32px 0 56px}
  .outline th{width:auto; display:block; border-bottom:none; padding-bottom:0}
  .outline td{display:block; padding-top:4px}
  .contact-grid{grid-template-columns:1fr; gap:26px}
  .sub section, .sub section.alt{padding:36px 0 64px}
  .sub section.gsec{padding:52px 0 60px}
  .page-head{padding:28px 0 28px}
}
"""


# ============ 開いたときの動き ============
# かみのて保育園のサイト（kaminote-design/plan-a.html）と同じ仕組みをそのまま
# 持ってきている。**隠す指定（ANIM_SEL_CSS）と、JSが探す並び（ANIM_SEL_JS）は
# 必ず同じにすること。** 食い違うと、隠れたまま出てこない要素ができる。
#
# 中身を先に出す箱（カードの並びなど）は、箱ごとではなく中身を1枚ずつ出す。
# そのため箱自身は :not() で外す。ここも2つの並びで揃える。
ANIM_BOXES = ["visas", "rsn", "fcards", "stl", "why3", "tn3", "tn-jump", "vcards", "stages", "tline", "flow", "partners",
              "faq-list", "ncards", "gcards", "contact-grid"]
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
@keyframes zoomOut{ from{transform:scale(1.12)} to{transform:none} }

/* ヒーローとお知らせ帯はJSを使わずCSSだけで動かす。JSがクラスを付けるのを
   待つと、待っている間に文字が見えてしまう（環境が遅いほど長く見える）。 */
.hero .bg img{animation:zoomOut 9s cubic-bezier(.16,.6,.3,1) both}
.hero-copy .wrap > *{animation:rise .7s cubic-bezier(.2,.7,.3,1) both}
.hero-copy .wrap > *:nth-child(1){animation-delay:.15s}
.hero-copy .wrap > *:nth-child(2){animation-delay:.30s}
.hero-copy .wrap > *:nth-child(3){animation-delay:.45s}
.hero-copy .wrap > *:nth-child(4){animation-delay:.60s}
.trust{animation:rise .7s cubic-bezier(.2,.7,.3,1) .4s both}

/* スクロールで出てくる分だけ、JSがあるとき（.anim）に隠しておく */
__SEL__{opacity:0}
.anim .on{animation:rise .7s cubic-bezier(.2,.7,.3,1) both}

@media (max-width:700px){ .anim .on{animation-name:riseSp} }

@media (prefers-reduced-motion:reduce){
  __SEL__{opacity:1}
  .anim .on, .hero .bg img, .hero-copy .wrap > *, .trust{animation:none}
}
@media print{
  __SEL__{opacity:1 !important}
  .anim .on, .hero .bg img, .hero-copy .wrap > *, .trust{animation:none !important}
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
    header = s[s.index('<header>'): s.index('</header>') + len('</header>')] + "\n\n"
    # ヒーロー＝ファーストビューと信頼情報（最初の <section> の手前まで）
    h0 = s.index('<div class="hero">')
    hero = s[h0: s.index('<section', h0)]
    if hero.rstrip().endswith("-->"):                  # 次の節の説明コメントは持ってこない
        hero = hero[: hero.rindex("<!--")].rstrip() + "\n\n"
    cta = s[s.index('<div class="cta" id="contact">'): s.index("<footer>")]
    footer = s[s.index("<footer>"): s.index('<div class="note">')]
    note = s[s.index('<div class="note">'):]
    secs = {}
    for m in re.finditer(r'<section[^>]*id="(\w+)".*?</section>\s*', s, re.S):
        secs[m.group(1)] = m.group(0)
    return head, header, hero, cta, footer, note, secs

MORE_LABEL = {
    "visas": "人材ごとの説明を見る", "support": "支援内容を詳しく見る（全10項目）", "flow": "各ステップを詳しく見る",
}

def top_section(frag, sec_id, inner, more_href=None):
    """トップ用の節。見出しと要約だけを置き、説明は下層ページに任せる。"""
    en, h2, _ = sec_head(frag)
    en = TOP_EN.get(sec_id, en)
    alt = ' class="alt"' if 'class="alt' in frag[: frag.index(">") + 1] else ""
    more = ""
    if more_href:
        more = (f'    <div class="more-r"><a class="txt-link" href="{more_href}">'
                f'{MORE_LABEL.get(sec_id, "詳しく見る")} <span aria-hidden="true">→</span></a></div>\n')
    return (f'<section{alt} id="{sec_id}">\n  <div class="wrap">\n'
            f'    <div class="sec-head"><span class="en">{en}</span><h2>{h2}</h2></div>\n'
            f"    {inner}\n" + more + "  </div>\n</section>\n\n")

# 会社概要。旧サイトの会社案内ページの内容をそのまま引き継ぐ（トップの要約にも使う）
OUTLINE = [
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

def digest(secs):
    """トップに並べる要約を、下層ページ用の原文から組み立てる。
    **原文をそのまま貼らない**（同じ説明が2ページに出てしまうため）。
    **原本に無い事実（数字・役割・実績）をここで書き足さない。**"""
    out = {}

    # 人材：名前と一行（.sum）だけ。詳しい説明は service.html。
    # ★実績の数字（受入企業数・累計紹介人数・対応国籍）は、お客さまから実数が届くまで出さない。
    f = secs["visas"]
    vs = re.findall(r'<div class="visa" id="([\w-]+)"><div class="n">(.*?)</div><h3>(.*?)</h3><p class="sum">(.*?)</p>', f, re.S)
    assert len(vs) == 5
    cards = "".join(f'<a class="vcard" href="service.html#{i}"><span class="n">{n}</span><h3>{t}</h3><p>{d}</p>'
                    f'<span class="go">詳しく見る <span aria-hidden="true">→</span></span></a>' for i, n, t, d in vs)
    out["visas"] = top_section(f, "visas", f'<div class="vcards">{cards}</div>', "service.html")

    # 支援：3段階の名前と、各段階の項目名だけ。項目の説明は support.html。
    f = secs["support"]
    stages = []
    for i, g in enumerate(f.split('<div class="sgrp">')[1:], 1):
        en = re.search(r'<span class="en">(.*?)</span>', g).group(1)
        h3 = re.search(r"<h3>(.*?)</h3>", g).group(1)
        p = re.search(r'<div class="sgrp-h">.*?<p>(.*?)</p>', g, re.S).group(1)
        items = "".join(f"<li>{x}</li>" for x in re.findall(r"<h4>(.*?)</h4>", g))
        stages.append(f'<li class="stage"><div class="stage-h"><span class="stage-n">{i:02d}</span>'
                      f'<span class="stage-en">{en}</span></div><h3>{h3}</h3><p>{p}</p>'
                      f'<ul class="checks">{items}</ul></li>')
    out["support"] = top_section(f, "support", '<ol class="stages">' + "".join(stages) + "</ol>", "support.html")

    # 流れ：期間の目安（大きく）と、手順名・期間だけ。各手順の説明は flow.html。
    f = secs["flow"]
    steps = re.findall(r'<li class="step">.*?<h3>(.*?)</h3>.*?<span class="dk">(.*?)</span>(.*?)</div>', f, re.S)
    tl = "".join(f'<li class="tl"><span class="dot">{i:02d}</span><b>{t}</b>'
                 f'<span class="d"><small>{k}</small>{d}</span></li>' for i, (t, k, d) in enumerate(steps, 1))
    out["flow"] = top_section(f, "flow", div_block(f, '<div class="flow-total">')
                              + f'<ol class="tline">{tl}</ol>', "flow.html")

    return out

# お知らせの分類。news.json に分類の欄は無いので、言葉から決める。
# ★本文は見ず、見出しで決まらないときだけ本文を見る（卒園式の本文に「フィリピン」が出てくるため）。
#   見出しでは 会社情報 → 保育・福祉 → 外国人材支援 の順、本文では 外国人材支援 → 保育・福祉 の順。
NEWS_CATS = [("hr", "外国人材支援"), ("care", "保育・福祉"), ("co", "会社情報")]
NEWS_KW = {
    "co": ("地鎮祭", "事務所", "社屋"),
    "care": ("保育", "卒園", "KIDS", "児童", "デイサービス"),
    "hr": ("フィリピン", "ベトナム", "実習", "監理団体", "登録支援", "送り出し", "外国人人材", "ブリッジング", "TESDA"),
}

def news_cat(it):
    for c in ("co", "care", "hr"):
        if any(k in it["title"] for k in NEWS_KW[c]):
            return c
    body = "".join(it["body"])
    for c in ("hr", "care"):
        if any(k in body for k in NEWS_KW[c]):
            return c
    return "co"

def news_items():
    """news.json に、分類（cat, cat_name）と、一覧での位置（anchor）を足して返す。"""
    items = json.loads((SRC / "news.json").read_text(encoding="utf-8"))
    seen = {}
    for it in items:
        it["cat"] = news_cat(it)
        it["cat_name"] = dict(NEWS_CATS)[it["cat"]]
        a = "n" + it["date"].replace(".", "")
        seen[a] = seen.get(a, 0) + 1
        it["anchor"] = a if seen[a] == 1 else f"{a}-{seen[a]}"
    return items

def fill_news(sec):
    """お知らせの節を、分類ごとの最新1件（計3件）で埋める。
    ★news.json の見出しは旧サイトの1行目で、語の途中で切れているものがある。本文をつなげて3行で切る。最新3件だけだと保育の話が並び、
    主事業の外国人材支援が見えなくなるため（2026-10-18 改善案）。
    日付・見出し・1枚目の写真だけを出し、リンクは一覧の該当記事の位置へ。"""
    items, picked = news_items(), []
    for c, _n in NEWS_CATS:
        it = next((x for x in items if x["cat"] == c), None)
        if it:
            picked.append(it)
    picked.sort(key=lambda x: x["date"], reverse=True)
    li = ""
    for it in picked:
        img = (f'<img src="img/news/{it["images"][0]}" alt="" loading="lazy">' if it["images"]
               else '<img src="img/logo-mark.jpg" alt="" loading="lazy" style="object-fit:contain">')
        cat = f'<em class="ncat c-{it["cat"]}">{it["cat_name"]}</em>'
        li += (f'<li><a href="news.html#{it["anchor"]}"><figure>{img}</figure><time>{it["date"]}{cat}</time>'
               f'<span>{html.escape(it["title"] + "".join(it["body"]))}</span></a></li>')
    old = sec[sec.index('<ul class="ncards">'): sec.index("</ul>") + 5]
    return sec.replace(old, f'<ul class="ncards">{li}</ul>')

def about_dl():
    """ABOUT US に置く会社の基本情報（OUTLINE から。原本に二重に書かない）。"""
    pick = dict(OUTLINE)
    dl = "".join(f"<div><dt>{k}</dt><dd>{pick[k].split('<br>')[0]}</dd></div>"
                 for k in ("会社名", "代表者", "本社所在地", "許可"))
    return f'<dl class="about-dl">{dl}</dl>'

def strip_sec_head(frag):
    """下層ページでは、節の見出し（英字ラベル・見出し・導入文）を取り除く。
    ページ見出し（.page-head）と同じ題が2回続かないようにするため。
    CSSで隠すだけだと、読み上げや検索には同じ題が二重に残る。"""
    return frag.replace(div_block(frag, '<div class="sec-head">'), "", 1)

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

    # トップ：FV・信頼の帯 → 人材 → 選ばれる3つの理由 → 現地での取り組み → 支援 → 流れ
    #        → よくあるご質問 → 会社・グループ → お知らせ
    tops = digest(secs)
    body = fix_links(hero) + fix_links(tops["visas"])
    for sec in ("reasons", "field"):
        body += fix_links(secs[sec])
    for sec in ("support", "flow"):
        body += fix_links(tops[sec])
    # FAQ はトップでは見出しのすぐ下の説明文を外す（下層ではページ見出しの説明に使う）
    faq = re.sub(r"(<h2>.*?</h2>)\s*<p>.*?</p>", r"\1", secs["faq"], count=1, flags=re.S)
    body += fix_links(faq)
    body += fix_links(secs["aboutus"].replace("<!--ABOUT_DL-->", about_dl())) + fix_links(fill_news(secs["news"]))
    body = '<div class="top">\n' + body + '</div>\n'
    (out_dir / "index.html").write_text(
        shell(head, header, tail, body, "index.html", "外国人材の受入れ支援"), encoding="utf-8")

    for out, (sec, _menu, ttl, en, desc) in PAGES.items():
        frag = secs[sec]
        # 節の導入文はページ見出しに上げ、節の見出しそのものは取り除く（題の二重を防ぐ）
        lead = sec_head(frag)[2] or html.escape(desc)
        frag = strip_sec_head(frag)
        ph = (f'<div class="crumb"><div class="wrap"><a href="index.html">ホーム</a> ／ {html.escape(ttl)}</div></div>\n'
              f'<div class="page-head"><div class="wrap"><span class="en">{html.escape(en)}</span>'
              f'<h1>{html.escape(ttl)}{"<span class=" + chr(34) + "count" + chr(34) + ">5 TYPES</span>" if sec == "visas" else ""}</h1>'
              f'<p>{lead}</p></div></div>\n')
        extra = (outline_table() + group_section()) if out == "company.html" else ""
        (out_dir / out).write_text(
            shell(head, header, tail, '<div class="sub">' + ph + fix_links(frag) + extra + "</div>",
                  out, ttl), encoding="utf-8")

    # 人材紹介も専用の組み方（2026-10-18 改善案）で上書きする
    (out_dir / "service.html").write_text(
        shell(head, header, tail, service_body(secs), "service.html", "ご紹介できる人材"), encoding="utf-8")
    # 支援内容は専用の組み方（2026-10-18 改善案）で上書きする
    (out_dir / "support.html").write_text(
        shell(head, header, tail, support_body(secs), "support.html", "登録支援機関としての支援"), encoding="utf-8")

    (out_dir / "news.html").write_text(
        shell(head, header, tail, news_body(), "news.html", "過去のお知らせ"), encoding="utf-8")
    (out_dir / "contact.html").write_text(
        shell(head, header, fix_links(footer) + note, contact_body(), "contact.html", "お問い合わせ"), encoding="utf-8")
    (out_dir / "privacy.html").write_text(
        shell(head, header, tail, privacy_body(), "privacy.html", "プライバシーポリシー"), encoding="utf-8")


# ============ 支援内容ページ（2026-10-18 改善案） ============
# 支援10項目の文言は原本の #support から取る（二重に書かない）。ここで足すのは見せ方と、
# 原本・partners 節にある事実から書いた「WHY A and K」「FAQ」だけ。
# ★費用・対応言語・トラブル時の具体的な体制は、お客さまに確認できるまで書かない。
SUP_EN = {"BEFORE": "BEFORE ARRIVAL", "LIFE": "DAILY LIFE SUPPORT", "CONTINUE": "CONTINUOUS SUPPORT"}
# 写真は会社の実際のもの（旧サイトのお知らせ）だけ。合う写真が無い段は None（写真なしで組む）
SUP_PHOTO = {
    "hero": ("img/news/20190725-3.jpg", "フィリピンの送り出し機関を訪問したときの様子", "2019年 フィリピンの送り出し機関にて"),
    1: ("img/news/20221108-2.jpeg", "フィリピンの送り出し機関の教室を訪ねたときの様子", "2022年 フィリピンの送り出し機関にて"),
    2: None,
    3: None,
}
_SV = '<svg viewBox="0 0 24 24" aria-hidden="true">{}</svg>'
SUP_ICON = {
    "01": '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4M9.5 11h6M9.5 14.5h6M9.5 18h4"/>',
    "02": '<path d="M2.5 13.5l19-7-5 15-4-6.5z"/><path d="M12.5 15l9-8.5"/>',
    "03": '<path d="M3.5 11L12 4l8.5 7"/><path d="M5.5 9.5V20h13V9.5M10 20v-5.5h4V20"/>',
    "04": '<path d="M4 5.5C6.5 4.5 9.5 4.5 12 6c2.5-1.5 5.5-1.5 8-.5V19c-2.5-1-5.5-1-8 .5-2.5-1.5-5.5-1.5-8-.5z"/><path d="M12 6v13.5"/>',
    "05": '<path d="M3 20h18M5 20V10M19 20V10M9 20v-6h6v6M3 10l9-6 9 6z"/>',
    "06": '<path d="M4 5h16v11H9l-5 4z"/><path d="M8.5 9h7M8.5 12h4.5"/>',
    "07": '<path d="M5 13a7 7 0 0 1 14 0v4"/><path d="M5 13v4h3v-5H5M19 13v4h-3v-5h3M19 17c0 2-2 3-5 3"/>',
    "08": '<circle cx="8" cy="8" r="3"/><circle cx="16.5" cy="9" r="2.5"/><path d="M2.5 20c.5-3.5 2.8-5.5 5.5-5.5s5 2 5.5 5.5M14 14.6c3.2-.4 6 1.5 6.5 5.4"/>',
    "09": '<path d="M4 8h13l-3-3M20 16H7l3 3"/>',
    "10": '<rect x="3.5" y="5" width="17" height="15" rx="1.5"/><path d="M3.5 9.5h17M8 3v4M16 3v4M8.5 14.5l2.2 2.2 4.8-4.7"/>',
}
STL_ICON = {1: "02", 2: "08", 3: "10"}
WHY_ICON = {
    "net": '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.4 2.5 3.6 5.5 3.6 9s-1.2 6.5-3.6 9c-2.4-2.5-3.6-5.5-3.6-9S9.6 5.5 12 3z"/></svg>',
    "one": '<svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3"/><path d="M3.5 20c0-3.2 2.5-5.8 5.5-5.8s5.5 2.6 5.5 5.8"/><circle cx="17" cy="9" r="2.4"/><path d="M16.2 14.3c2.6.4 4.3 2.8 4.3 5.7"/></svg>',
    "local": '<svg viewBox="0 0 24 24"><path d="M3 21h18M5 21V8.5L12 4l7 4.5V21M9.5 21v-4.5h5V21M9 11.5h.01M12 11.5h.01M15 11.5h.01"/></svg>',
}
SUP_FAQ = [
    ("登録支援機関には、どこまで委託できますか。",
     "特定技能で義務づけられている支援（このページの10項目）の実施を、登録支援機関としてお引き受けします。"
     "なお、支援を委託した場合も、受入れ企業さまご自身が行う届出などがあります。"),
    ("外国人材を初めて受け入れる企業でも相談できますか。",
     "はじめての企業さまがほとんどです。どの制度が合うか分からない段階から、社内の受入れ体制づくりまでご一緒します。"),
    ("外国人材との言葉の問題にはどう対応しますか。",
     "入国前の事前ガイダンスや、仕事・暮らしの相談への対応は、本人が分かる言葉で行います。日本語学習の機会もご案内します。"),
    ("受入れ後にトラブルが発生した場合はどうなりますか。",
     "仕事や暮らしの相談・苦情に、本人が分かる言葉で応じます。法令違反などがあれば行政機関へ通報します。"
     "会社の都合で雇用が終わるときは、次の受入れ先探しをお手伝いします。"),
]


def support_body(secs):
    f = secs["support"]
    groups = []
    for g in f.split('<div class="sgrp">')[1:]:
        en = re.search(r'<span class="en">(.*?)</span>', g).group(1)
        h3 = re.search(r"<h3>(.*?)</h3>", g).group(1)
        p = re.search(r'<div class="sgrp-h">.*?<p>(.*?)</p>', g, re.S).group(1)
        items = re.findall(r'<div class="sup"><span class="c">(\d+)</span><h4>(.*?)</h4><p>(.*?)</p></div>', g)
        groups.append((en, h3, p, items))
    assert [len(x[3]) for x in groups] == [3, 5, 2], [len(x[3]) for x in groups]
    nwmap = re.search(r'<svg class="nw-map".*?</svg>', secs["partners"], re.S).group(0)

    src, alt, cap = SUP_PHOTO["hero"]
    out = ('<div class="sp-hero"><div class="sp-hero-t">'
           '<div class="sp-crumb"><a href="index.html">ホーム</a> ／ 支援内容</div>'
           '<span class="sp-en">TOTAL HUMAN RESOURCE SUPPORT</span>'
           '<p class="sp-k">登録支援機関としての支援</p>'
           '<h1><span>国境を越えた挑戦に</span><br><span>途切れない安心を</span></h1>'
           '<p class="lead">外国人材の受入れ準備から、日本での暮らし、就労後の定着まで。<br>'
           'A and K は登録支援機関として、企業と外国人材の双方に寄り添い、安心して働き続けられる環境づくりを支えます。</p>'
           '<a class="btn gold" href="contact.html">ご相談・お問い合わせ <span aria-hidden="true">→</span></a></div>'
           f'<figure class="sp-hero-ph"><img src="{src}" alt="{alt}"><figcaption>{cap}</figcaption></figure></div>\n'
           '<div class="sp-reg"><div class="wrap"><span class="en">REGISTERED SUPPORT ORGANIZATION</span>'
           '<b>登録支援機関　登録番号 19登-000975</b></div></div>\n')

    li = ""
    for i, (en, h3, p, items) in enumerate(groups, 1):
        ic = _SV.format(SUP_ICON[STL_ICON[i]])
        li += (f'<li><a href="#step{i}"><div class="stl-top"><span class="stl-n">{i:02d}</span><span class="stl-ic">{ic}</span></div>'
               f'<span class="stl-en">{SUP_EN.get(en, en)}</span><b>{h3}</b><small>{p}</small><em>{len(items)}項目</em></a></li>')
    out += ('<section id="total"><div class="wrap">'
            '<div class="sec-head"><span class="en">TOTAL SUPPORT</span><h2>受入れから定着まで<br>安心をつなぐ3つのステップ</h2></div>'
            f'<ol class="stl">{li}</ol></div></section>\n')

    for i, (en, h3, p, items) in enumerate(groups, 1):
        rows = ""
        for n, t, d in items:
            tag = '<em class="si-tag">必要な場合のみ</em>' if n == "09" else ""
            rows += (f'<li><span class="si-ic">{_SV.format(SUP_ICON[n])}</span><span class="si-n">{n}</span>'
                     f'<div><h3>{t}{tag}</h3><p>{d}</p></div></li>')
        head = (f'<div class="sp-step-h"><span class="sp-step-n">STEP<b>{i:02d}</b></span>'
                f'<span class="en">{SUP_EN.get(en, en)}</span><h2>{h3}</h2></div>')
        ph = SUP_PHOTO.get(i)
        if ph:
            fig = f'<figure class="sp-ph"><img src="{ph[0]}" alt="{ph[1]}" loading="lazy"><figcaption>{ph[2]}</figcaption></figure>'
            body = fig + f'<div class="sp-step-b">{head}<ol class="sitems">{rows}</ol></div>'
            cls = "sp-step-in"
        else:
            body = f'<div class="sp-step-b">{head}</div><ol class="sitems">{rows}</ol>'
            cls = "sp-step-in noph"
        out += f'<section class="sp-step sp-s{i}" id="step{i}"><div class="wrap {cls}">{body}</div></section>\n'

    out += ('<section class="sp-why"><div class="sp-why-map" aria-hidden="true">' + nwmap + '</div><div class="wrap">'
            '<div class="sec-head"><span class="en">WHY A and K</span><h2>制度への対応だけでなく<br>人と企業に寄り添う支援を</h2></div>'
            '<ul class="why3">'
            f'<li><span class="ic" aria-hidden="true">{WHY_ICON["net"]}</span><h3>国内外のネットワーク</h3>'
            '<p>グループ内の監理団体ブリッジング協同組合と、フィリピン・ベトナムの送り出し機関が連携しています。</p></li>'
            f'<li><span class="ic" aria-hidden="true">{WHY_ICON["one"]}</span><h3>一貫した支援体制</h3>'
            '<p>監理団体を自社で設立しているため、募集から入国、就労後の支援までを一貫してお引き受けできます。</p></li>'
            f'<li><span class="ic" aria-hidden="true">{WHY_ICON["local"]}</span><h3>地域に根ざした活動</h3>'
            '<p>岐阜県可児市が拠点です。グループで保育園や児童発達支援・放課後等デイサービスを運営し、外国にルーツのあるお子さまをお預かりしてきました。</p></li>'
            '</ul><div class="more-r"><a class="txt-link" href="partners.html">グループ・提携機関を見る <span aria-hidden="true">→</span></a></div>'
            '</div></section>\n')

    qs = "".join(f'<details><summary>{q}</summary><div class="a"><p style="margin:0">{a}</p></div></details>'
                 for q, a in SUP_FAQ)
    out += ('<section class="faq"><div class="wrap">'
            '<div class="sec-head"><span class="en">FAQ</span><h2>よくあるご質問</h2></div>'
            f'<div class="faq-list">{qs}</div>'
            '<div class="more-r"><a class="txt-link" href="faq.html">すべてのご質問を見る <span aria-hidden="true">→</span></a></div>'
            '</div></section>\n')
    return '<div class="top sp">\n' + out + '</div>\n'


# ============ 人材紹介ページ（2026-10-18 改善案） ============
# 5つの人材の名前・一言（.sum）・説明は原本の #visas から取る。ここで足すのは見せ方と、
# 制度そのものの事実（特定技能・技能実習の目的、育成就労への移行予定）だけ。
# ★A and K の育成就労への対応、対応できる業種・職種は、お客さまに確認できるまで書かない。
TN_EN = {"v-tokutei": "SPECIFIED SKILLED WORKER", "v-ginou": "TECHNICAL INTERN TRAINING",
         "v-ryugaku": "INTERNATIONAL STUDENTS", "v-kodo": "PROFESSIONAL TALENT", "v-nikkei": "RESIDENT TALENT"}
TN_PHOTO = {"hero": ("img/news/20190315-1.jpg", "フィリピンの職業訓練庁（TESDA）を訪問したときの様子", "2019年 フィリピンの職業訓練庁（TESDA）にて"),
            "v-ginou": ("img/hero-trainees.jpg", "提携する送り出し機関での日本語授業の様子", "提携する送り出し機関での日本語授業"),
            "net1": ("img/news/20200122-1.jpg", "ベトナムでの実習生の面接の様子", "2020年 ベトナムでの面接"),
            "net2": ("img/news/20191011-1.jpg", "フィリピン出張で現地の若者と", "2019年 フィリピン出張にて")}
# 比較（主な検討シーン）。制度の事実と、原本の説明から書く
TN_CMP = {
    "v-tokutei": "国が定める分野で、一定の技能と日本語の力を持つ人材を採用したい",
    "v-ginou": "技能の習得を目的とした受入れ（実習）を検討したい",
    "v-ryugaku": "資格外活動の範囲でのアルバイトや、特定技能への資格変更による採用を検討したい",
    "v-kodo": "専門的な知識や技術を持つ人材を、職種に合わせて採用したい",
    "v-nikkei": "就労に制限のない、国内に住む人材を採用したい",
}
TN_FAQ = [
    ("外国人材を初めて採用する場合、どの制度が適していますか。",
     "職種・人数・時期によって合う制度が変わります。どの制度が合うか分からない段階からご相談ください。お話を伺い、合う在留資格をご提案します。"),
    ("特定技能と技能実習には、どのような違いがありますか。",
     "技能実習は、技能の習得を目的とした制度です（2027年4月1日から育成就労制度へ移行する予定です）。"
     "特定技能は、国が定める分野で一定の技能と日本語の力を持つ人が働くための在留資格で、受入れ後の支援が義務づけられています。"
     "弊社は登録支援機関として、その支援をお引き受けします。"),
    ("どのような職種で外国人材を採用できますか。",
     "在留資格ごとに、働ける仕事の範囲が決まっています。ご希望の職種をお伺いして、合う制度をご案内します。介護人材のご紹介にも力を入れています。"),
    ("採用までにどのくらいの期間がかかりますか。",
     "海外の送り出し機関を通じて採用する場合、ご相談から就労開始までおおむね5〜6か月が目安です（在留資格によって異なります）。"),
    ("採用後の生活支援も依頼できますか。",
     "特定技能の方は、登録支援機関として、住まい探しや生活に必要な契約、生活オリエンテーション、定期的な面談などをお引き受けします。"),
]


def service_body(secs):
    f = secs["visas"]
    vs = re.findall(r'<div class="visa" id="([\w-]+)"><div class="n">(.*?)</div><h3>(.*?)</h3>'
                    r'<p class="sum">(.*?)</p>\s*<p>(.*?)</p></div>', f, re.S)
    assert [v[0] for v in vs] == ["v-tokutei", "v-ginou", "v-ryugaku", "v-kodo", "v-nikkei"], [v[0] for v in vs]
    V = {v[0]: v for v in vs}
    src, alt, cap = TN_PHOTO["hero"]
    out = ('<div class="sp-hero"><div class="sp-hero-t">'
           '<div class="sp-crumb"><a href="index.html">ホーム</a> ／ ご紹介できる人材</div>'
           '<span class="sp-en">GLOBAL TALENT SOLUTIONS</span>'
           '<p class="sp-k">ご紹介できる人材</p>'
           '<h1><span>世界の可能性を</span><br><span>企業の新しい力に</span></h1>'
           '<p class="lead">特定技能、技能実習、高度人材など、幅広い外国人材の採用をサポート。'
           'A and K は、企業の事業内容や採用ニーズに合わせた人材との出会いを支援します。</p>'
           '<a class="btn gold" href="contact.html">人材のご相談をする <span aria-hidden="true">→</span></a></div>'
           f'<figure class="sp-hero-ph"><img src="{src}" alt="{alt}"><figcaption>{cap}</figcaption></figure></div>\n'
           '<div class="sp-reg"><div class="wrap"><span class="en">REGISTERED SUPPORT ORGANIZATION</span>'
           '<b>登録支援機関　登録番号 19登-000975</b></div></div>\n')

    jump = "".join(f'<li><a href="#{i}"><span>{n}</span>{t}</a></li>' for i, n, t, _s, _d in vs)
    out += ('<section class="tn-intro"><div class="wrap">'
            '<div class="sec-head"><span class="en">OUR TALENT</span><h2>企業のニーズに合わせた<br>5つの人材カテゴリー</h2></div>'
            f'<ol class="tn-jump">{jump}</ol></div></section>\n')

    def head(v):
        i, n, t, _s, _d = v
        return (f'<div class="tn-head"><span class="tn-n">{n}</span><div><span class="tn-en">{TN_EN[i]}</span>'
                f'<h2>{t}</h2></div></div>')

    # 01 特定技能（紺のパネル）
    v = V["v-tokutei"]
    out += ('<section class="tn-big" id="v-tokutei"><div class="wrap tn-big-in">'
            '<div class="tn-vis tn-panel" aria-hidden="true"><span class="num">01</span>'
            '<span class="big">Specified<br><em>Skilled</em> Worker</span>'
            '<span class="meta">登録支援機関　登録番号 19登-000975</span></div>'
            f'<div class="tn-body">{head(v)}<h3 class="tn-catch">現場を支える新たな力を</h3>'
            '<p>特定技能は、国が定める分野で、一定の技能と日本語の力を持つ外国人材が働くための在留資格です。'
            f'{v[4]}</p>'
            '<ul class="checks"><li>受入れ後に義務づけられた支援（10項目）の実施をお引き受け</li>'
            '<li>特定技能試験に合格した留学生の、特定技能への資格変更にも対応</li>'
            '<li>介護人材のご紹介にも力を入れています</li></ul>'
            '<a class="btn line" href="support.html">受入れ後の支援について詳しく見る <span aria-hidden="true">→</span></a>'
            '</div></div></section>\n')

    # 02 技能実習（写真）
    v = V["v-ginou"]
    src, alt, cap = TN_PHOTO["v-ginou"]
    out += ('<section class="tn-big rev alt" id="v-ginou"><div class="wrap tn-big-in">'
            f'<figure class="tn-vis"><img src="{src}" alt="{alt}" loading="lazy"><figcaption>{cap}</figcaption></figure>'
            f'<div class="tn-body">{head(v)}<h3 class="tn-catch">人材の育成を通じて未来につなぐ</h3>'
            f'<p>{v[4]}</p>'
            '<p class="tn-note"><b>育成就労制度への移行</b><br>技能実習制度は、2027年4月1日から育成就労制度へ移行する予定です。</p>'
            '<ul class="checks"><li>ブリッジング協同組合<small>（自社グループの監理団体）</small></li>'
            '<li>フィリピン・ベトナムの送り出し機関と提携</li></ul>'
            '<a class="btn line" href="partners.html">グループ・提携機関を見る <span aria-hidden="true">→</span></a>'
            '</div></div></section>\n')

    # 03〜05
    li = ""
    for i in ("v-ryugaku", "v-kodo", "v-nikkei"):
        _i, n, t, sm, d = V[i]
        li += (f'<li id="{i}"><span class="tn-n">{n}</span><span class="tn-en">{TN_EN[i]}</span><h3>{t}</h3>'
               f'<p class="sum">{sm}</p><p>{d}</p></li>')
    out += f'<section class="tn-more"><div class="wrap"><ul class="tn3">{li}</ul></div></section>\n'

    # 比較
    rows = "".join(f'<tr><th scope="row"><span>{n}</span>{t}</th><td data-k="主な検討シーン">{TN_CMP[i]}</td>'
                   f'<td class="a" data-k="A and K の対応">{sm}</td></tr>' for i, n, t, sm, _d in vs)
    out += ('<section class="alt"><div class="wrap">'
            '<div class="sec-head"><span class="en">FIND YOUR TALENT</span><h2>企業のニーズに合わせて<br>合う人材を</h2></div>'
            '<table class="cmp"><thead><tr><th scope="col">人材カテゴリー</th><th scope="col">主な検討シーン</th>'
            f'<th scope="col">A and K の対応</th></tr></thead><tbody>{rows}</tbody></table>'
            '<p class="cmp-note">※実際に採用できる職種や働き方は、在留資格・許可の内容・制度の要件によって異なります。</p>'
            '<div class="cmp-cta"><div><b>自社に合う制度が分からなくても、ご安心ください。</b>'
            '<p>採用したい職種・人数・時期などをお伺いし、企業さまの状況に合った人材採用をご提案します。</p></div>'
            '<a class="btn" href="contact.html">自社に合う人材について相談する <span aria-hidden="true">→</span></a></div>'
            '</div></section>\n')

    # GLOBAL RECRUITMENT NETWORK
    p1, p2 = TN_PHOTO["net1"], TN_PHOTO["net2"]
    out += ('<section class="tn-net"><div class="wrap tn-net-in"><div class="tn-net-t">'
            '<div class="sec-head"><span class="en">GLOBAL RECRUITMENT NETWORK</span><h2>世界とつながり<br>人材の可能性を広げる</h2></div>'
            '<p>グループ内の監理団体と、フィリピン・ベトナムの送り出し機関が連携しています。'
            'フィリピンでは、企業さまご自身が現地で面接を行うこともできます。</p>'
            '<ul class="tn-net-l"><li><span>JAPAN</span>ブリッジング協同組合（自社グループ）</li>'
            '<li><span>PHILIPPINES</span>プロデンシャルエンプロイメント</li>'
            '<li><span>VIETNAM</span>POLIMEX 国際人材株式会社</li></ul>'
            '<a class="txt-link" href="partners.html">海外ネットワークを見る <span aria-hidden="true">→</span></a></div>'
            f'<div class="tn-ph2"><figure><img src="{p1[0]}" alt="{p1[1]}" loading="lazy"><figcaption>{p1[2]}</figcaption></figure>'
            f'<figure><img src="{p2[0]}" alt="{p2[1]}" loading="lazy"><figcaption>{p2[2]}</figcaption></figure></div>'
            '</div></section>\n')

    # WHY A and K
    out += ('<section class="tn-why"><div class="wrap">'
            '<div class="sec-head"><span class="en">WHY A and K</span><h2>人材との出会いから<br>その先の定着まで</h2></div>'
            '<ul class="why3 light">'
            f'<li><span class="wn">01</span><span class="ic" aria-hidden="true">{WHY_ICON["one"]}</span><h3>幅広い人材への対応</h3>'
            '<p>特定技能・技能実習・留学生・高度人材・日系人／定住者の5つに対応。合う制度選びからご一緒します。</p></li>'
            f'<li><span class="wn">02</span><span class="ic" aria-hidden="true">{WHY_ICON["net"]}</span><h3>国内外との連携</h3>'
            '<p>自社グループの監理団体と、フィリピン・ベトナムの送り出し機関とのネットワークがあります。</p></li>'
            f'<li><span class="wn">03</span><span class="ic" aria-hidden="true">{WHY_ICON["local"]}</span><h3>受入れ後までの支援</h3>'
            '<p>登録支援機関として、入国前の説明から就労後の定期的な面談まで支援を続けます。</p></li>'
            '</ul></div></section>\n')

    # 流れへの導線
    out += ('<section class="tn-proc"><div class="wrap"><div class="tn-proc-in"><div>'
            '<div class="sec-head"><span class="en">RECRUITMENT PROCESS</span><h2><span>ご相談から採用まで</span><br><span>安心して進められるように</span></h2></div>'
            '<p class="tn-proc-f">ご相談から就労開始まで <b>約5〜6か月</b>（海外の送り出し機関を通じて採用する場合の目安）</p></div>'
            '<a class="btn gold" href="flow.html">受入れまでの流れを見る <span aria-hidden="true">→</span></a>'
            '</div></div></section>\n')

    qs = "".join(f'<details><summary>{q}</summary><div class="a"><p style="margin:0">{a}</p></div></details>'
                 for q, a in TN_FAQ)
    out += ('<section class="faq"><div class="wrap">'
            '<div class="sec-head"><span class="en">FAQ</span><h2>よくあるご質問</h2></div>'
            f'<div class="faq-list">{qs}</div>'
            '<div class="more-r"><a class="txt-link" href="faq.html">すべてのご質問を見る <span aria-hidden="true">→</span></a></div>'
            '</div></section>\n')
    return '<div class="top sp tn">\n' + out + '</div>\n'


def group_section():
    """グループの事業。旧サイトの h1 と事業内容に、児童福祉の記載があった。
    このサイトは外国人材に絞る方針だが、**落とすのではなく紹介にとどめ、
    詳細はそれぞれのサイトへ渡す**（原則リニューアルをベースにするため）。
    トップの ABOUT US（原本の aboutus）から、ここ（#group）へ案内する。"""
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
        # f文字列の中にバックスラッシュを書くと Python 3.11 以前で動かないので外に出す
        gtag = f'<div class="gtag">{tag}</div>' if tag else ""
        items += (f'<div class="gcard"><h3>{name}</h3>'
                  f'{gtag}'
                  f'<p>{desc}</p>{link}</div>')
    return ('<section class="gsec" id="group"><div class="wrap">'
            '<div class="sec-head"><span class="en">GROUP</span>'
            '<h2>グループの事業</h2>'
            '<p>外国人材の受入れ支援のほか、保育園と児童発達支援・放課後等デイサービスを運営しています。</p></div>'
            f'<div class="gcards">{items}</div></div></section>')


def outline_table():
    """会社概要（OUTLINE）。代表ごあいさつは正式な文章が届くまで載せないので、企業情報の中心になる。"""
    tr = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in OUTLINE)
    return ('<section><div class="wrap"><div class="sec-head">'
            '<span class="en">COMPANY PROFILE</span><h2>会社概要</h2></div>'
            f'<table class="outline">{tr}</table></div></section>')


def news_body():
    items = news_items()
    arts = []
    for it in items:
        body = "".join(f"<p>{html.escape(l)}</p>" for l in ([it["title"]] + it["body"]) if l)
        gal = ""
        if it["images"]:
            gal = '<div class="ngal">' + "".join(
                f'<img src="img/news/{n}" alt="" loading="lazy">' for n in it["images"]) + "</div>"
        arts.append(f'      <article class="nitem" id="{it["anchor"]}" data-cat="{it["cat"]}"><time>{it["date"]}'
                    f'<em class="ncat c-{it["cat"]}">{it["cat_name"]}</em></time>'
                    f'<div class="nbody">{body}{gal}</div></article>')
    btns = '<button type="button" class="on" data-cat="">すべて</button>' + "".join(
        f'<button type="button" data-cat="{c}">{n}</button>' for c, n in NEWS_CATS)
    filt = (f'<div class="nfilter" role="group" aria-label="分類で絞り込む">{btns}</div>\n'
            + NEWS_FILTER_JS)
    return ('<div class="crumb"><div class="wrap"><a href="index.html">ホーム</a> ／ 過去のお知らせ</div></div>\n'
            '<div class="page-head"><div class="wrap"><span class="en">NEWS &amp; TOPICS</span>'
            '<h1>過去のお知らせ</h1></div></div>\n'
            '<div class="nlist"><div class="wrap">\n' + filt + "\n".join(arts) + "\n</div></div>\n")


NEWS_FILTER_JS = """<script>
// 分類で絞り込む。JS が無いときは全件がそのまま見える
document.addEventListener('click', function (e) {
  var b = e.target.closest('.nfilter button');
  if (!b) return;
  var c = b.getAttribute('data-cat');
  [].forEach.call(document.querySelectorAll('.nfilter button'), function (x) { x.classList.toggle('on', x === b); });
  [].forEach.call(document.querySelectorAll('.nitem'), function (it) {
    it.hidden = !!c && it.getAttribute('data-cat') !== c;
  });
});
</script>
"""


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
    """旧サイトのプライバシーポリシー（src/old/policy.txt。2026-10-03 取得）をそのまま引き継ぐ。
    ★旧サイトの問い合わせ窓口の住所は「〒509-0255 岐阜県可児市光陽台2-87」で、今の本社（今渡3-11）と違う。
      窓口は本社の連絡先にしてあるので、お客さまに確認すること（README の「確認すること」）。"""
    lines = [l for l in (SRC / "old" / "policy.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    start = lines.index("プライバシーポリシー（個人情報保護方針）") + 1
    end = next(i for i, l in enumerate(lines) if l.startswith("７．"))
    out, ul = [], []
    def flush():
        if ul:
            out.append("<ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in ul) + "</ul>")
            ul.clear()
    for l in lines[start:end + 2]:                     # 「７．お問い合わせ窓口」と、その説明文まで
        if l.startswith("・"):
            ul.append(l[1:]); continue
        flush()
        if re.match(r"^[１-９]．", l):
            out.append(f"<h2>{html.escape(l)}</h2>")
        else:
            out.append(f"<p>{html.escape(l)}</p>")
    flush()
    out.append('<div class="pp-contact"><p><b>株式会社 A and K</b></p>'
               '<p>〒509-0207 岐阜県可児市今渡3-11</p>'
               '<p>Tel 0574-66-3511／Fax 0574-66-7311</p>'
               '<p>E-mail <a href="mailto:info@aandkcorp.com">info@aandkcorp.com</a></p></div>')
    return ('<div class="crumb"><div class="wrap"><a href="index.html">ホーム</a> ／ プライバシーポリシー</div></div>\n'
            '<div class="page-head"><div class="wrap"><span class="en">PRIVACY POLICY</span>'
            '<h1>プライバシーポリシー</h1><p>個人情報保護方針</p></div></div>\n'
            '<section><div class="wrap"><div class="pp">' + "\n".join(out) + '</div></div></section>\n')

if __name__ == "__main__":
    main()
