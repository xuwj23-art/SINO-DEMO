# -*- coding: utf-8 -*-
"""Generate the demo's synthetic *internal* AML/CFT policy PDF (Traditional Chinese).

Throwaway demo asset (see docs/demo/DEMO-NOTES.zh-CN.md). The content is written
to reflect the PRE-June-2023 rules of the SFC AML/CFT Guideline, so that the
regulatory "push" (the 24 May 2023 SFC circular, refNo 23EC21) genuinely
supersedes several clauses — letting the demo show AI reading the old policy and
proposing concrete edits. Not a real company policy; synthetic material only.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "demo" / "assets"
OUT_PATH = OUT_DIR / "demo_internal_aml_policy_v2022_TC.pdf"

# A real TrueType font (Microsoft JhengHei, Traditional Chinese) is embedded so
# the PDF carries a proper ToUnicode CMap and text extraction works. The Adobe
# CID font (MSung-Light) renders on screen but extracts as garbage, which would
# break the RAG pipeline — do not switch back to it.
CJK_FONT = "MSJH"
CJK_FONT_PATH = "C:/Windows/Fonts/msjh.ttc"

COMPANY = "盛富證券有限公司（示範）"
TITLE = "內部反洗錢及反恐怖分子資金籌集政策"
TITLE_EN = "Internal Anti-Money Laundering and Counter-Financing of Terrorism Policy"

SECTIONS = [
    (
        "第一節　目的與適用範圍",
        [
            "本政策依據《打擊洗錢及恐怖分子資金籌集條例》（AMLO）、《證券及期貨條例》（SFO），"
            "以及證券及期貨事務監察委員會（證監會）《打擊洗錢及恐怖分子資金籌集指引（適用於持牌法團）》"
            "（2021年9月版）制定。",
            "本政策適用於本公司全體董事、員工及所有業務單位，旨在防止本公司被利用作洗錢或恐怖分子資金籌集用途。",
        ],
    ),
    (
        "第二節　客戶盡職審查（CDD）與身分核實",
        [
            "於建立業務關係或開立賬戶前，本公司須識別客戶並核實其身分，包括全名、出生日期、國籍、"
            "身分證明文件及住址證明。",
            "客戶所提供的住址證明文件（如水電費賬單、銀行月結單、政府發出之信件），其簽發日期不得超過三個月；"
            "超過三個月者，須要求客戶重新提供近三個月內之有效證明。",
            "對於非面對面（non-face-to-face）開戶的客戶，本公司須採取額外核實措施以降低冒認風險。",
            "身分證明文件須為有效且未過期之正本或經核證副本。本公司須核實證件號碼之格式與校驗位，"
            "並比對客戶所提供之身分資料是否與證件一致。",
        ],
    ),
    (
        "第三節　政治人物（PEP）",
        [
            "本公司對現任及曾任政治人物，不論屬香港或非香港，一律持續適用強化客戶盡職審查。",
            "所有政治人物（包括已卸任者）的開戶及交易，均須經高級管理層批准。",
            "上述強化措施一經適用即長期持續，本公司現行政策不設任何解除或豁免機制。",
            "本公司識別政治人物時，應參考商業資料庫，並結合了解客戶之職業及僱主等資訊綜合判斷，"
            "不得僅依賴單一資料庫。",
        ],
    ),
    (
        "第四節　受益所有人",
        [
            "就信託客戶，本公司須識別並核實其受益所有人。",
            "本公司現行對信託受益所有人的界定範圍，包括信託的財產授予人（settlor）、受託人（trustee）及受益人（beneficiary）。",
        ],
    ),
    (
        "第五節　資金來源與財富來源核實",
        [
            "於開立賬戶時，本公司須了解並記錄客戶之財富來源（source of wealth）及資金來源（source of funds），"
            "包括收入、儲蓄、投資收益、遺產、物業出售等。",
            "客戶申報之資金來源須與其收入水平、淨資產及預期交易規模相符。"
            "若申報之資金來源與客戶之收入或財務狀況明顯不符，本公司須要求客戶提供進一步證明文件，"
            "並轉介合規部門人工覆核，未完成覆核前不得為該客戶開立賬戶。",
            "對於大額入金（單筆或短期內累計超過港幣八十萬元或等值），本公司須要求客戶提供資金來源之"
            "佐證文件（如銀行月結單、薪金單、物業買賣合約等）。",
            "客戶須就投資資金之合法性及來源作出聲明。以可疑或偽造文件開立之賬戶，本公司將予以關閉。",
        ],
    ),
    (
        "第六節　風險評級",
        [
            "本公司依據客戶之身分、職業、地域、產品、交易模式等因素，將客戶劃分為高、中、低三個風險等級。",
            "具備以下任一情形之客戶，應評為高風險：政治人物（PEP）、資金來源與收入明顯不符、"
            "來自高風險司法管轄區、申請保證金或衍生產品等高槓桿賬戶、預期交易規模與其財務狀況不匹配。",
            "高風險客戶須適用強化盡職審查（EDD），包括取得高級管理層批准、了解財富及資金來源、"
            "提高監察頻率。低風險客戶在符合條件時可適用簡化盡職審查。",
        ],
    ),
    (
        "第七節　電匯與匯款信息（旅行規則）",
        [
            "就電子資金轉賬，本公司須取得並保存匯款人（發起人）及收款人的所需信息。",
            "本公司於發出電匯後的一個營業日內，向受益機構傳送所需的匯款人及收款人信息。",
            "所需信息不完整的電匯指示，須經合規部門覆核後方可執行。",
        ],
    ),
    (
        "第八節　持續監察與記錄保存",
        [
            "本公司對客戶的交易進行持續監察，以識別並向聯合財富情報組呈報可疑交易。",
            "與客戶身分、業務關係及交易相關的記錄，自交易完成或業務關係終止起，保存不少於五年。",
        ],
    ),
    (
        "第九節　虛擬資產",
        [
            "本公司現階段不從事任何虛擬資產相關業務。",
            "因此，本政策未就虛擬資產的洗錢／恐怖分子資金籌集風險設立專門的風險評估及監控章節。",
        ],
    ),
    (
        "第十節　開戶審核總覽",
        [
            "本公司於為任何客戶開立賬戶前，須完成下列開戶審核項：身分核實、住址證明時效核驗、"
            "政治人物（PEP）核查、受益所有人識別、資金來源與財富來源核實、客戶風險評級。",
            "上述審核項中，任一項被判定為不通過（fail）者，本公司不得為該客戶開立賬戶，"
            "並須將個案轉介合規部門作進一步人工覆核。",
            "任一項被判定為待人工覆核（review）者，須待合規部門完成覆核並確認後，方可繼續開戶流程。",
            "全部審核項均為通過（pass）時，方可進入開戶下一步，但仍須由合規人員作最終人工確認。",
        ],
    ),
    (
        "第十一節　員工培訓與違規處理",
        [
            "本公司每年為相關員工提供打擊洗錢及反恐怖分子資金籌集培訓。",
            "任何違反本政策的行為，將按本公司內部紀律程序處理，情節嚴重者將呈報合規部門及管理層。",
        ],
    ),
]


def _register_font() -> None:
    pdfmetrics.registerFont(TTFont(CJK_FONT, CJK_FONT_PATH, subfontIndex=0))


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CJKTitle",
            fontName=CJK_FONT,
            fontSize=18,
            leading=24,
            textColor=colors.HexColor("#102033"),
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CJKSubTitle",
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#526070"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CJKMeta",
            fontName=CJK_FONT,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#526070"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CJKSection",
            fontName=CJK_FONT,
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#173b5f"),
            spaceBefore=12,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CJKBody",
            fontName=CJK_FONT,
            fontSize=11,
            leading=17,
            textColor=colors.HexColor("#1f2a3d"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CJKFooter",
            fontName=CJK_FONT,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#7b8794"),
        )
    )
    return styles


def build() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _register_font()
    styles = _styles()

    doc = SimpleDocTemplate(
        str(OUT_PATH),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title=f"{COMPANY} {TITLE}",
        author="Demo synthetic policy (not a real company document)",
    )

    story = [
        Paragraph(COMPANY, styles["CJKTitle"]),
        Paragraph(TITLE, styles["CJKTitle"]),
        Paragraph(TITLE_EN, styles["CJKSubTitle"]),
        Table(
            [
                ["版本", "2022.01", "分類", "內部（示範文件）"],
                ["生效日期", "2022年1月1日", "編制依據", "證監會 AML/CFT 指引（2021年9月版）"],
            ],
            colWidths=[24 * mm, 44 * mm, 24 * mm, 78 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f6fa")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8e0ea")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d8e0ea")),
                    ("FONTNAME", (0, 0), (-1, -1), CJK_FONT),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1f2a3d")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            ),
        ),
        Spacer(1, 8),
        Paragraph(
            "示範聲明：本文件為 AI 演示用之合成文件，內容參照證監會《打擊洗錢及反恐怖分子資金籌集指引》"
            "（2021年9月版）編寫，僅供展示，不代表任何真實公司之政策，且不含任何真實客戶資料。",
            styles["CJKMeta"],
        ),
    ]

    for section_title, paragraphs in SECTIONS:
        story.append(Paragraph(section_title, styles["CJKSection"]))
        for idx, text in enumerate(paragraphs, start=1):
            story.append(Paragraph(f"{idx}. {text}", styles["CJKBody"]))

    story.append(Spacer(1, 14))
    story.append(Paragraph("— 本示範政策文件結束 —", styles["CJKFooter"]))

    def _footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont(CJK_FONT, 8)
        canvas.setFillColor(colors.HexColor("#7b8794"))
        canvas.drawString(
            20 * mm,
            10 * mm,
            f"{COMPANY}｜內部 AML/CFT 政策 v2022.01（示範）｜第 {canvas.getPageNumber()} 頁",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(f"Generated: {OUT_PATH}")


if __name__ == "__main__":
    build()
