#!/usr/bin/env python3
"""src/plan-a.html（原本・1枚もの）から、独立した各ページを生成する。

**生成物を直接編集しないこと。** 原本を直して `python3 build.py` を走らせる。
生成物だけを git revert しても次のビルドで元に戻ってしまうため、
原本と生成物は必ず一緒にコミットする（かみのてで踏んだ事故）。

**説明はページに1回だけ。** トップは各節の要約（名前・期間・短い一文）に
とどめ、中身の説明は下層ページで行う。原本の文章はどちらにも書かず、
下層ページ用の原文から digest() が抜き出して要約を組み立てる。

トップの並び（2026-10-03 組み直し）:
  FV → 信頼情報 → 特徴 → 人材 → 支援 → 流れ → 連携 → 会社 → グループ事業 → お知らせ → FAQ → お問い合わせ
  「特徴」「グループ事業」「お知らせ」はトップだけの節（原本の features / groupbiz / news）。

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
# 出さないため。トップには TOP_LEAD の短い文を置く）。
PAGES = {
    "service.html":  ("visas",    "人材紹介", "ご紹介できる人材", "TALENT",
                      "就労が可能な5つの在留資格すべてに対応しています。"),
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
# トップに置く一行。**下層の導入文とは別の文にする**（同じ文を2回読ませない）。
# ★「間に他社を挟みません」は使わない（提携機関を紹介しているので矛盾して読める）
TOP_LEAD = {
    "visas":    "就労が可能な5つの在留資格・人材に対応しています。",
    "support":  "特定技能で義務づけられている支援を、受入れ前・生活・就労継続の3段階でお引き受けします。",
    "flow":     "ご相談から就労開始まで、5つのステップで進めます。",
    "partners": "自社グループと提携機関で、募集から就労後まで一貫して支援。",
    "company":  "",
    "faq":      "",
}

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
ANIM_BOXES = ["visas", "feats", "vcards", "stages", "tline", "net", "flow", "partners",
              "faq-list", "gbiz", "gcards", "contact-grid"]
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
.hero-copy > *{animation:rise .7s cubic-bezier(.2,.7,.3,1) both}
.hero-copy > *:nth-child(2){animation-delay:.08s}
.hero-copy > *:nth-child(3){animation-delay:.16s}
.hero-copy > *:nth-child(4), .hero-copy > *:nth-child(5){animation-delay:.24s}
.hero-copy > *:nth-child(6){animation-delay:.32s}
.hero-ph{animation:rise .9s cubic-bezier(.2,.7,.3,1) .2s both}
.trust{animation:rise .7s cubic-bezier(.2,.7,.3,1) .4s both}

/* スクロールで出てくる分だけ、JSがあるとき（.anim）に隠しておく */
__SEL__{opacity:0}
.anim .on{animation:rise .7s cubic-bezier(.2,.7,.3,1) both}

@media (max-width:700px){ .anim .on{animation-name:riseSp} }

@media (prefers-reduced-motion:reduce){
  __SEL__{opacity:1}
  .anim .on, .hero-ph, .hero-copy > *, .trust{animation:none}
}
@media print{
  __SEL__{opacity:1 !important}
  .anim .on, .hero-ph, .hero-copy > *, .trust{animation:none !important}
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
    "partners": "グループ・提携機関を詳しく見る", "company": "企業情報を見る",
}

# トップで強みとして大きく見せる一文
TOP_LEAD_BIG = {"partners"}

def top_section(frag, sec_id, inner, more_href=None):
    """トップ用の節。見出しと要約だけを置き、説明は下層ページに任せる。"""
    en, h2, _ = sec_head(frag)
    alt = ' class="alt"' if 'class="alt' in frag[: frag.index(">") + 1] else ""
    lead = TOP_LEAD.get(sec_id, "")
    if lead:
        cls = ' class="lead-strong"' if sec_id in TOP_LEAD_BIG else ""
        lead = f"<p{cls}>{lead}</p>"
    more = ""
    if more_href:
        more = (f'    <div class="more-r"><a class="txt-link" href="{more_href}">'
                f'{MORE_LABEL.get(sec_id, "詳しく見る")} <span aria-hidden="true">→</span></a></div>\n')
    return (f'<section{alt} id="{sec_id}">\n  <div class="wrap">\n'
            f'    <div class="sec-head"><span class="en">{en}</span><h2>{h2}</h2>{lead}</div>\n'
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
    vs = re.findall(r'<div class="visa"><div class="n">(.*?)</div><h3>(.*?)</h3><p class="sum">(.*?)</p>', f, re.S)
    cards = "".join(f'<div class="vcard"><span class="n">{n}</span><h3>{t}</h3><p>{d}</p></div>' for n, t, d in vs)
    out["visas"] = top_section(f, "visas", f'<div class="vcards">{cards}</div>'
                               + div_block(f, '<div class="consult">'), "service.html")

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
    out["support"] = top_section(f, "support", '<ol class="stages">' + "".join(stages) + "</ol>"
                                 + div_block(f, '<div class="consult">'), "support.html")

    # 流れ：期間の目安（大きく）と、手順名・期間だけ。各手順の説明は flow.html。
    f = secs["flow"]
    steps = re.findall(r'<li class="step">.*?<h3>(.*?)</h3>.*?<span class="dk">(.*?)</span>(.*?)</div>', f, re.S)
    tl = "".join(f'<li class="tl"><span class="dot">{i:02d}</span><b>{t}</b>'
                 f'<span class="d"><small>{k}</small>{d}</span></li>' for i, (t, k, d) in enumerate(steps, 1))
    out["flow"] = top_section(f, "flow", div_block(f, '<div class="flow-total">')
                              + f'<ol class="tline">{tl}</ol>', "flow.html")

    # グループ・提携機関：自社グループを中央に、海外・国内の提携機関を左右に置いて連携を見せる。
    # 書いてよいのは partners 節（原本）にある事実だけ。
    f = secs["partners"]
    out["partners"] = top_section(f, "partners", (
        '<div class="net">'
        '<div class="net-col"><span class="net-k">海外の送り出し機関<em>PARTNER</em></span>'
        '<div class="net-item"><small>フィリピン</small><b>プロデンシャルエンプロイメント</b>'
        '<span>現地で企業さまご自身が面接を行うこともできます。</span></div>'
        '<div class="net-item"><small>ベトナム</small><b>POLIMEX 国際人材株式会社</b>'
        '<span>2021年8月にブリッジング協同組合と業務提携。</span></div></div>'
        '<div class="net-col net-own"><span class="net-k">自社グループ<em>OUR GROUP</em></span>'
        '<div class="net-item"><b>株式会社 A and K</b><span>募集・紹介／入国の手続き・生活の支援</span>'
        '<span class="role">登録支援機関</span></div>'
        '<div class="net-item"><b>ブリッジング協同組合</b><span>2021年8月に弊社が設立。技能実習生の受入れを、紹介から監理まで自社グループ内で。</span>'
        '<span class="role">監理団体</span></div></div>'
        '<div class="net-col"><span class="net-k">国内の提携監理団体<em>PARTNER</em></span>'
        '<div class="net-item"><small>日本（愛知）</small><b>トラスト江南協同組合</b>'
        '<span>2019年9月に業務提携。愛知・岐阜・三重の企業さまや介護施設さまへの受入れを支えています。</span></div></div>'
        '</div>'
        '<p class="net-foot">就労後も、定期的な面談・相談で支援を続けます。</p>'), "partners.html")

    # 会社について：考え方の一文と、会社の基本情報だけ。全体は company.html。
    f = secs["company"]
    pick = dict(OUTLINE)
    dl = "".join(f"<div><dt>{k}</dt><dd>{pick[k].split('<br>')[0]}</dd></div>"
                 for k in ("会社名", "代表者", "本社所在地", "許可"))
    about = div_block(f, '<div class="about">')
    about = about[: about.rindex("</div>")] + f'<dl class="about-dl">{dl}</dl></div>'
    out["company"] = top_section(f, "company", about, "company.html")
    return out

def fill_news(sec, n=3):
    """お知らせの節を news.json の最新 n 件で埋める。
    原本に直接書くと更新のたびに直すことになり、実際そのまま
    2021年で止まっていた。見出しだけを出し、本文と写真は news.html に置く。"""
    items = json.loads((SRC / "news.json").read_text(encoding="utf-8"))[:n]
    li = "".join(f'<li><a href="news.html"><time>{it["date"]}</time>'
                 f'<span>{html.escape(it["title"])}</span><i aria-hidden="true">→</i></a></li>' for it in items)
    old = sec[sec.index('<ul class="nlist-top">'): sec.index("</ul>") + 5]
    return sec.replace(old, f'<ul class="nlist-top">{li}</ul>')

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

    # トップ：何の会社か（FV・信頼・特徴）→ 人材 → 支援 → 流れ → 連携 → 会社
    #        → グループ事業 → お知らせ → FAQ。保育とお知らせは後半に控えめに置く。
    tops = digest(secs)
    body = fix_links(hero) + fix_links(secs["features"])
    for sec in ("visas", "support", "flow", "partners", "company"):
        body += fix_links(tops[sec])
    body += fix_links(secs["groupbiz"]) + fix_links(fill_news(secs["news"])) + fix_links(secs["faq"])
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

    (out_dir / "news.html").write_text(
        shell(head, header, tail, news_body(), "news.html", "過去のお知らせ"), encoding="utf-8")
    (out_dir / "contact.html").write_text(
        shell(head, header, tail, contact_body(), "contact.html", "お問い合わせ"), encoding="utf-8")
    (out_dir / "privacy.html").write_text(
        shell(head, header, tail, privacy_body(), "privacy.html", "プライバシーポリシー"), encoding="utf-8")


def group_section():
    """グループの事業。旧サイトの h1 と事業内容に、児童福祉の記載があった。
    このサイトは外国人材に絞る方針だが、**落とすのではなく紹介にとどめ、
    詳細はそれぞれのサイトへ渡す**（原則リニューアルをベースにするため）。
    トップの「グループ事業」（原本の groupbiz）から、ここ（#group）へ案内する。"""
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
