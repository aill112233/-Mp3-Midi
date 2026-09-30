#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《软件下载站使用说明书》Word 文档（.docx）
结构：封面 → 目录 → 一、网站简介 → 二、快速开始 → 三、下载安装包 → 四、上传安装包
     → 五、公网访问 → 六、常见问题 → 七、技术支持
"""
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

BASE = os.path.dirname(os.path.abspath(__file__))
COVER = os.path.join(BASE, "static", "manual_cover.png")
OUT = os.path.join(BASE, "static", "使用说明书.docx")

ACCENT = "6B8FA3"   # Nordic Mist 主色


def configure_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    rPr = normal.element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    heading_configs = [
        ("Heading 1", 18, True, RGBColor(0x2C, 0x3E, 0x6B)),
        ("Heading 2", 14, True, RGBColor(0x6B, 0x8F, 0xA3)),
        ("Heading 3", 12, True, RGBColor(0x44, 0x44, 0x44)),
    ]
    for style_name, size_pt, bold, color in heading_configs:
        s = doc.styles[style_name]
        s.font.name = "Arial"
        s.font.size = Pt(size_pt)
        s.font.bold = bold
        s.font.color.rgb = color
        s.paragraph_format.space_before = Pt(size_pt * 0.75)
        s.paragraph_format.space_after = Pt(size_pt * 0.4)
        s.paragraph_format.keep_with_next = True
        rPr = s.element.get_or_add_rPr()
        rFonts = rPr.get_or_add_rFonts()
        rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")


def add_floating_background(doc, image_path, page_width_emu, page_height_emu):
    # 将封面图作为浮动背景插入（第 1 段）
    from docx.oxml.ns import qn as _qn
    from lxml import etree
    # 先插入一张全宽图片以建立关系
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(image_path, width=Inches(8.27))
    # 从 run 的 XML 中提取 blip embed rId
    blip = run._r.findall('.//' + _qn('a:blip'))[0]
    r_id = blip.get(_qn('r:embed'))
    # 删除该段落，改用锚定背景图
    p._p.getparent().remove(p._p)
    cx, cy = str(int(page_width_emu)), str(int(page_height_emu))
    anchor = f'''<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:r><w:drawing><wp:anchor behindDoc="1" distT="0" distB="0" distL="0" distR="0"
simplePos="0" relativeHeight="251658240" allowOverlap="1" locked="0"
xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
<wp:simplePos x="0" y="0"/>
<wp:positionH relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionH>
<wp:positionV relativeFrom="page"><wp:posOffset>0</wp:posOffset></wp:positionV>
<wp:extent cx="{cx}" cy="{cy}"/>
<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/>
<wp:docPr id="1" name="Background"/>
<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
<pic:nvPicPr><pic:cNvPr id="1" name="Background"/><pic:cNvPicPr><a:picLocks noChangeAspect="1"/></pic:cNvPicPr></pic:nvPicPr>
<pic:blipFill><a:blip r:embed="{r_id}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
</pic:pic></a:graphicData></a:graphic></wp:anchor></w:drawing></w:r></w:p>'''
    from lxml import etree
    doc.element.body.insert(0, etree.fromstring(anchor))


def add_toc(doc):
    doc.add_heading("目 录", level=0)
    p = doc.add_paragraph()
    run = p.add_run()
    fc1 = OxmlElement("w:fldChar"); fc1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve")
    it.text = 'TOC \\o "1-2" \\h \\z \\u'
    fc2 = OxmlElement("w:fldChar"); fc2.set(qn("w:fldCharType"), "separate")
    fc3 = OxmlElement("w:fldChar"); fc3.set(qn("w:fldCharType"), "end")
    run._r.extend([fc1, it, fc2, fc3])
    hint = doc.add_paragraph()
    hint.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = hint.add_run("（如目录未显示，请在 Word 中右键目录 → 更新域）")
    r.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)
    r.font.size = Pt(8.5)
    r.font.italic = True
    doc.add_page_break()


def add_header_footer(doc, title):
    section = doc.sections[0]
    header = section.header
    hp = header.paragraphs[0]
    hp.text = title
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hp.style = doc.styles["Normal"]
    hp.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)
    hp.runs[0].font.size = Pt(9)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def field(p, instr):
        run = p.add_run()
        f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
        it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr
        f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "separate")
        ph = OxmlElement("w:t"); ph.text = "1"
        f3 = OxmlElement("w:fldChar"); f3.set(qn("w:fldCharType"), "end")
        run._r.extend([f1, it, f2, ph, f3])

    fp.add_run("第 ")
    field(fp, " PAGE ")
    fp.add_run(" 页 / 共 ")
    field(fp, " NUMPAGES ")
    fp.add_run(" 页")
    for r_ in fp.runs:
        r_.font.size = Pt(9)
        r_.font.color.rgb = RGBColor(0x88, 0x88, 0x88)


def add_hyperlink(paragraph, url, text):
    part = paragraph.part
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    hl = OxmlElement("w:hyperlink")
    hl.set(qn("r:id"), r_id)
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    rStyle = OxmlElement("w:rStyle"); rStyle.set(qn("w:val"), "Hyperlink")
    color = OxmlElement("w:color"); color.set(qn("w:val"), "0563C1")
    u = OxmlElement("w:u"); u.set(qn("w:val"), "single")
    rPr.append(rStyle); rPr.append(color); rPr.append(u)
    r.append(rPr)
    t = OxmlElement("w:t"); t.text = text
    r.append(t)
    hl.append(r)
    paragraph._p.append(hl)


def add_styled_table(doc, headers, rows, widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblBorders = OxmlElement("w:tblBorders")
    for side in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        b = OxmlElement(f"w:{side}"); b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "6"); b.set(qn("w:color"), "C8D6E0")
        tblBorders.append(b)
    tblPr.append(tblBorders)

    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), "6B8FA31A")
        tcPr.append(shd)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.runs[0]
        r.bold = True
        r.font.color.rgb = RGBColor(0x2C, 0x3E, 0x6B)
    for ri, row in enumerate(rows):
        for ci, txt in enumerate(row):
            cell = table.rows[ri + 1].cells[ci]
            cell.text = str(txt)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    if widths:
        for row in table.rows:
            for ci, w in enumerate(widths):
                row.cells[ci].width = Inches(w)
    return table


def main():
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.top_margin = section.bottom_margin = Inches(1)
    section.left_margin = section.right_margin = Inches(1.1)

    configure_styles(doc)

    # ---------- 封面 ----------
    add_floating_background(doc, COVER, section.page_width.emu, section.page_height.emu)
    cover = doc.add_paragraph()
    cover.paragraph_format.space_before = Pt(190)
    cover.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cover.add_run("软件下载站")
    r.bold = True; r.font.size = Pt(40); r.font.name = "Arial"
    r.font.color.rgb = RGBColor(0x2C, 0x3E, 0x6B)
    r2 = cover.add_run("\n使用说明书")
    r2.bold = True; r2.font.size = Pt(40)
    r2.font.color.rgb = RGBColor(0x2C, 0x3E, 0x6B)
    for rr in [r, r2]:
        rPr = rr._r.get_or_add_rPr()
        rFonts = rPr.get_or_add_rFonts()
        rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.paragraph_format.space_before = Pt(16)
    rs = sub.add_run("下载 · 安装 · 上传 · 公网访问 完全指南")
    rs.font.size = Pt(15); rs.font.color.rgb = RGBColor(0x6B, 0x8F, 0xA3)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.paragraph_format.space_before = Pt(240)
    rm = meta.add_run("版本：V1.0（2026 年 9 月）")
    rm.font.size = Pt(11); rm.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
    doc.add_page_break()

    # ---------- 目录 ----------
    add_toc(doc)
    add_header_footer(doc, "软件下载站 · 使用说明书")

    # ---------- 一、网站简介 ----------
    doc.add_heading("一、网站简介", level=1)
    doc.add_paragraph(
        "软件下载站是一个安装包整合下载平台，将常用的 Windows 安装包集中在一个页面，"
        "支持一键下载、上传分享、公网访问。本站目前已收录 3 款内置软件，并支持随时上传新的安装包，"
        "上传后会自动出现在下载列表中，供所有访问者下载。"
    )
    doc.add_heading("网站功能一览", level=2)
    add_styled_table(doc,
        ["功能", "说明"],
        [
            ["下载安装包", "点击卡片上的「下载」按钮即可下载对应软件"],
            ["上传安装包", "填写信息并选择文件，上传后自动加入下载列表"],
            ["公网访问", "通过公网网址，任何设备、任何网络均可访问"],
            ["删除上传包", "上传者可以删除自己上传的安装包"],
            ["接口支持", "提供 JSON 数据接口，便于与其他系统对接"],
        ],
        widths=[1.8, 4.6],
    )

    # ---------- 二、快速开始 ----------
    doc.add_heading("二、快速开始", level=1)
    doc.add_heading("1. 打开网站", level=2)
    p = doc.add_paragraph()
    p.add_run("在浏览器地址栏输入网站地址即可访问。局域网内地址：")
    add_hyperlink(p, "http://localhost:8000", "http://localhost:8000")
    p2 = doc.add_paragraph()
    p2.add_run("公网地址（任何网络可访问）：")
    add_hyperlink(p2, "https://lqcmh-39-182-57-226.run.pinggy-free.link", "https://lqcmh-39-182-57-226.run.pinggy-free.link")

    doc.add_heading("2. 选择软件并下载", level=2)
    doc.add_paragraph("在首页的软件卡片中找到需要的软件，点击卡片右下角的「⬇ 下载」按钮，浏览器即可开始下载安装包。下载完成后，双击运行安装包，按提示完成安装。", style="List Number")
    doc.add_paragraph("如浏览器提示「此文件不是常见的下载文件」，请选择「保留」或「仍然下载」，这是对 .exe 安装包的常规安全提示。", style="List Bullet")

    # ---------- 三、下载安装包 ----------
    doc.add_heading("三、下载安装包", level=1)
    doc.add_heading("当前收录的软件", level=2)
    add_styled_table(doc,
        ["软件名称", "安装包文件", "大小", "简介"],
        [
            ["AVTools 音视频工具箱", "AVTools_Setup_1.0.0.exe", "约 37 MB", "音视频格式转换、剪辑、音轨提取、批量处理"],
            ["极致压缩工具", "CompressTool_Setup_1.0.0.exe", "约 9 MB", "高压缩率文件压缩，多格式支持、极速解压"],
            ["游戏 Mod AI 翻译器", "GameModTranslator-Setup-1.0.exe", "约 11 MB", "AI 驱动的游戏 Mod 翻译，自动识别并高质量翻译"],
        ],
        widths=[1.5, 2.2, 0.8, 2.6],
    )
    doc.add_heading("下载步骤", level=2)
    doc.add_paragraph("打开网站首页，浏览软件卡片。", style="List Number")
    doc.add_paragraph("点击软件卡片右下角的「⬇ 下载」按钮。", style="List Number")
    doc.add_paragraph("浏览器开始下载，等待下载完成。", style="List Number")
    doc.add_paragraph("双击下载的安装包，按向导完成安装。", style="List Number")

    doc.add_heading("安装提示", level=2)
    doc.add_paragraph("所有安装包均为 Windows 平台的标准安装程序，双击即可运行。安装过程中如出现 Windows SmartScreen 提示，点击「更多信息」→「仍要运行」即可继续。", style="List Bullet")

    # ---------- 四、上传安装包 ----------
    doc.add_heading("四、上传安装包", level=1)
    doc.add_paragraph("网站支持上传新的安装包。上传成功后，安装包会自动出现在首页的下载列表中，任何访问者都可以下载。")

    doc.add_heading("上传步骤", level=2)
    doc.add_paragraph("在首页底部找到「⬆️ 上传安装包」区域。", style="List Number")
    doc.add_paragraph("填写软件名称、版本号、上传者、简介（均为选填，不填也能上传）。", style="List Number")
    doc.add_paragraph("点击「选择文件」，选中要上传的安装包。", style="List Number")
    doc.add_paragraph("点击「⬆ 上传」按钮，等待进度提示「上传成功」。", style="List Number")
    doc.add_paragraph("上传完成后刷新页面，新软件即出现在下载列表中，带「🆕 用户上传」标记。", style="List Number")

    doc.add_heading("上传规则与限制", level=2)
    add_styled_table(doc,
        ["项目", "限制"],
        [
            ["文件大小", "单个文件最大 2GB"],
            ["支持格式", ".exe / .msi / .zip / .7z / .rar / .apk / .dmg / .pkg / .deb / .rpm / .sh 等"],
            ["重名处理", "系统自动按日期+内容哈希重命名，不会覆盖已有文件"],
            ["删除权限", "仅上传的安装包可删除（内置 3 款软件不可删除）"],
        ],
        widths=[1.6, 4.8],
    )

    doc.add_heading("删除上传的安装包", level=2)
    doc.add_paragraph("在对应卡片右下角点击「🗑」按钮，确认后即可删除。删除后该安装包从下载列表消失，文件同时被移除。", style="List Bullet")

    # ---------- 五、公网访问 ----------
    doc.add_heading("五、公网访问", level=1)
    doc.add_paragraph("网站通过公网隧道对外提供服务，无需公网 IP、无需路由器端口映射，任何网络环境均可直接访问。")

    doc.add_heading("公网地址", level=2)
    p3 = doc.add_paragraph()
    p3.add_run("主地址：")
    add_hyperlink(p3, "https://lqcmh-39-182-57-226.run.pinggy-free.link", "https://lqcmh-39-182-57-226.run.pinggy-free.link")
    p4 = doc.add_paragraph()
    p4.add_run("备用地址：")
    add_hyperlink(p4, "https://vbcsb-39-182-57-226.free.pinggy.net", "https://vbcsb-39-182-57-226.free.pinggy.net")

    doc.add_heading("注意事项", level=2)
    doc.add_paragraph("免费公网隧道每 60 分钟过期，过期后隧道会自动重启，但网址会随机变化。若发现网址打不开，请联系管理员获取最新地址。", style="List Bullet")
    doc.add_paragraph("若需要永久固定的网址，可以升级为付费隧道或配置自有域名，详情联系管理员。", style="List Bullet")
    doc.add_paragraph("公网下载速度受运营商网络影响，大文件建议在网络空闲时段下载。", style="List Bullet")

    # ---------- 六、常见问题 ----------
    doc.add_heading("六、常见问题（FAQ）", level=1)
    faqs = [
        ("Q1：为什么浏览器提示文件不安全？", "这是浏览器对 .exe 等可执行文件的常规安全提醒。本站所有安装包均来自可信来源，选择「保留」或「仍要下载」即可。"),
        ("Q2：下载的安装包打不开/被杀毒软件拦截？", "请确认下载文件完整（可对比文件大小）。如被杀毒软件拦截，可在杀毒软件中将其加入信任列表后重新下载。"),
        ("Q3：上传文件太大传不上去？", "单个文件上限为 2GB。超过 2GB 的安装包请压缩拆分后上传，或联系管理员处理。"),
        ("Q4：上传后看不到我的软件？", "上传完成后页面会自动跳转并显示结果。如仍看不到，请刷新页面；若列表末尾出现带「🆕 用户上传」标记的卡片即为上传成功。"),
        ("Q5：公网网址打不开？", "免费隧道约每 60 分钟更换一次地址。请刷新页面或联系管理员获取最新公网地址。"),
        ("Q6：手机/其他电脑能访问吗？", "可以。公网地址不受局域网限制，手机、平板、异地电脑均可直接访问并下载。"),
    ]
    for q, a in faqs:
        doc.add_heading(q, level=2)
        doc.add_paragraph(a)

    # ---------- 七、技术支持 ----------
    doc.add_heading("七、技术支持", level=1)
    doc.add_paragraph("如遇任何问题，可联系管理员处理：", style="List Bullet")
    doc.add_paragraph("网站地址打不开、下载失败、需要添加新软件、需要永久固定网址等。", style="List Bullet")

    doc.save(OUT)
    print("Saved:", OUT)


if __name__ == "__main__":
    main()