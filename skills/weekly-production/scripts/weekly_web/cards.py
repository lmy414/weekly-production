# SPDX-License-Identifier: GPL-3.0-only
"""Code-drawn share cards using the same pixel studio palette as the site."""
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from .settings import Settings

INK = '#243746'
PAPER = '#f6f1e2'
MINT = '#deebe1'
GREEN = '#28635b'
CORAL = '#ffa38d'
YELLOW = '#f4da87'
WECHAT_COVERS = {
    'master': ('cover-wechat-master.jpg', (2538, 1080)),
    'landscape': ('cover-wechat-preview-2.35x1.png', (1410, 600)),
    'square': ('cover-wechat-preview-1x1.png', (1080, 1080)),
}
WECHAT_SQUARE_BOX = (729, 0, 1809, 1080)


class Cards:
    def __init__(self, font, settings=None):
        self.fontfile = str(font)
        self.settings = settings or Settings()

    @lru_cache(maxsize=24)
    def font(self, size):
        f = ImageFont.truetype(self.fontfile, size)
        try: f.set_variation_by_axes([600])
        except (OSError, ValueError): pass
        return f

    def wrap(self, draw, text, width, size, max_lines=3):
        lines, line = [], ''
        for ch in text:
            if ch == '\n' or draw.textlength(line + ch, font=self.font(size)) > width:
                lines.append(line); line = '' if ch == '\n' else ch
            else: line += ch
        if line: lines.append(line)
        if len(lines)>max_lines:
            lines=lines[:max_lines]
            while draw.textlength(lines[-1]+'…', font=self.font(size))>width: lines[-1]=lines[-1][:-1]
            lines[-1]+='…'
        return lines

    def text(self, draw, xy, text, size, fill=INK, width=None, lines=3):
        x,y=xy
        content=self.wrap(draw,str(text),width,size,lines) if width else str(text).split('\n')
        for line in content:
            draw.text((x,y),line,font=self.font(size),fill=fill,stroke_width=0)
            y += int(size*1.48)
        return y

    def background(self, height):
        image=Image.new('RGB',(1200,height),PAPER)
        d=ImageDraw.Draw(image)
        for y in range(8,height,18):
            for x in range(8,1200,18): d.rectangle((x,y,x+1,y+1),fill='#cbd1b8')
        d.rectangle((24,24,1176,height-24),outline=INK,width=3)
        return image,d

    def wechat_covers(self, issue, assets):
        """One upload master; both previews are pixel crops of the encoded upload."""
        outputs = {name: Path(assets) / filename for name, (filename, _) in WECHAT_COVERS.items()}
        master = self.wechat_master(issue, assets)
        master.save(outputs['master'], quality=95, subsampling=0, optimize=True)
        with Image.open(outputs['master']) as encoded:
            uploaded = encoded.convert('RGB')
        uploaded.resize(WECHAT_COVERS['landscape'][1], Image.Resampling.LANCZOS).save(outputs['landscape'], optimize=True)
        uploaded.crop(WECHAT_SQUARE_BOX).save(outputs['square'], optimize=True)
        return outputs

    def wechat_master(self, issue, assets):
        width, height = WECHAT_COVERS['master'][1]
        center_left = WECHAT_SQUARE_BOX[0]
        im = Image.new('RGB', (width, height), PAPER)
        d = ImageDraw.Draw(im)
        for y in range(8, height, 18):
            for x in range(8, width, 18):
                d.rectangle((x, y, x + 1, y + 1), fill='#cbd1b8')
        d.rectangle((24, 24, width - 24, height - 24), outline=INK, width=3)
        left, top, right, bottom = 40, 126, width - 40, height - 74
        d.rectangle((left, top, right, bottom), fill=MINT, outline=INK, width=3)
        for x in range(left + 27, right, 27):
            d.line((x, top + 2, x, bottom - 2), fill='#c8dcd0')
        for y in range(top + 27, bottom, 27):
            d.line((left + 2, y, right - 2, y), fill='#c8dcd0')

        # All essential branding lives in the central 1080px square.
        d.rectangle((center_left + 44, 42, center_left + 100, 98), fill='#c8e4d9', outline=INK, width=2)
        self.text(d, (center_left + 51, 44), 'AI', 32)
        self.text(d, (center_left + 116, 40), 'AI GIRL WEEKLY', 24, GREEN)
        self.text(d, (center_left + 117, 76), 'AI 娘创作放映室', 16, GREEN)
        d.rectangle((center_left + 805, 42, center_left + 1036, 98), fill=YELLOW, outline=INK, width=2)
        self.text(d, (center_left + 823, 47), 'ISSUE ' + str(issue['number']), 29, width=197, lines=1)
        label_width = min(370, max(160, int(d.textlength(issue['label'], font=self.font(23))) + 32))
        d.rectangle((center_left + 76, 153, center_left + 76 + label_width, 195), fill=CORAL, outline=INK, width=2)
        self.text(d, (center_left + 91, 154), issue['label'], 23, width=label_width - 30, lines=1)
        name = self.settings.site_name.replace('AI 娘', 'AI娘')
        title = name[:-2] + '\n周刊' if name.endswith('周刊') else name
        title_size = 125
        while title_size > 24 and max(d.textlength(line, font=self.font(title_size)) for line in title.split('\n')) > 420:
            title_size -= 1
        self.text(d, (center_left + 75, 247), title, title_size, '#fffaf0', width=420, lines=2)
        self.text(d, (center_left + 70, 242), title, title_size, INK, width=420, lines=2)
        self.text(d, (center_left + 77, 643), '模型下班，\n角色上场。', 40, GREEN)
        self.text(d, (center_left + 79, 810), str(len(issue['works'])) + ' 部作品', 27)
        self.text(d, (center_left + 79, 856), str(issue['authors']) + ' 位创作者', 27)

        art_box = (center_left + 494, 206, center_left + 1037, bottom - 3)
        art = Image.new('RGBA', (art_box[2] - art_box[0], art_box[3] - art_box[1]))
        ad = ImageDraw.Draw(art)
        ad.ellipse((-5, 184, 601, 790), fill='#bad6de', outline=INK, width=3)
        with Image.open(Path(assets) / Path(issue['host']).name) as source:
            host = source.convert('RGBA')
        bounds = host.getbbox()
        if bounds:
            host = host.crop(bounds)
        host.thumbnail((535, 780), Image.Resampling.LANCZOS)
        art.alpha_composite(host, ((art.width - host.width) // 2, 9))
        im.paste(art, art_box[:2], art)
        self.text(d, (center_left + 70, 1018), issue['basis_label'], 23, GREEN)
        self.text(d, (center_left + 810, 1018), issue['date'], 22, GREEN)

        # The wings only add context; losing them in the square crop loses no identity.
        self.text(d, (88, 44), 'AI 娘创作放映室', 32, GREEN)
        self.text(d, (92, 225), issue['label'], 46, GREEN, width=540, lines=1)
        self.text(d, (88, 360), '每一份创作，\n都值得被看见。', 62, INK, width=555, lines=2)
        self.text(d, (94, 620), '剧情 / 音乐 / 动画 / 整活', 24, GREEN)
        self.text(d, (47, 1018), issue['period_label'], 24, GREEN, width=620, lines=1)
        self.text(d, (1924, 225), '本期片单', 42, GREEN)
        self.text(d, (1910, 332), str(len(issue['works'])), 215)
        self.text(d, (1930, 617), '部作品', 52, GREEN)
        self.text(d, (1930, 713), str(issue['authors']) + ' 位创作者', 42, INK)
        self.text(d, (1930, 843), '原作 · 指标 · 计分细则', 25, GREEN)
        for sx, sy in ((575, 785), (2320, 380)):
            points = [(sx-11,sy-27),(sx+11,sy-27),(sx+11,sy-11),(sx+27,sy-11),
                      (sx+27,sy+11),(sx+11,sy+11),(sx+11,sy+27),(sx-11,sy+27),
                      (sx-11,sy+11),(sx-27,sy+11),(sx-27,sy-11),(sx-11,sy-11)]
            d.polygon([(x+3,y+4) for x,y in points], fill=INK)
            d.polygon(points, fill=CORAL)
        return im

    def heading(self,d,issue):
        d.rectangle((48,48,105,105),fill='#c8e4d9',outline=INK,width=2)
        self.text(d,(56,50),'AI',31)
        self.text(d,(120,45),self.settings.site_name,31,width=710,lines=1)
        self.text(d,(122,90),'AI GIRL WEEKLY',12,GREEN)
        self.text(d,(868,52),'ISSUE '+issue['number'],22)
        self.text(d,(868,87),issue['date'],15,GREEN)
        d.line((48,125,1152,125),fill=INK,width=2)

    def bottom(self,image,d,issue,y,work=None):
        d.line((48,y,1152,y),fill=INK,width=2)
        self.text(d,(56,y+20),'模型下班，角色上场。',26,GREEN)
        from urllib.parse import urlsplit
        url=self.settings.qr_target(issue,work)
        website=self.settings.site_url
        label=urlsplit(website).netloc.encode('ascii').decode('idna') if website else '作品出处见文字榜单'
        self.text(d,(56,y+65),label,22,width=900,lines=1)
        hint='扫码阅读本期' if self.settings.qr_source=='website' or not work else '扫码查看作品'
        self.text(d,(56,y+105),'作品版权归原作者所有'+(' · '+hint if url else ''),15,'#71806a')
        if url:
            import qrcode
            qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=1,border=4)
            qr.add_data(url);qr.make(fit=True)
            pixels=qr.make_image(fill_color='black',back_color='white').convert('RGB')
            scale=max(1,164//pixels.width)
            pixels=pixels.resize((pixels.width*scale,pixels.height*scale),Image.Resampling.NEAREST)
            image.paste(pixels,(1160-pixels.width,y+5+(164-pixels.height)//2))

    def entire(self,issue,assets,out):
        height=650+len(issue['works'])*151+205
        im,d=self.background(height);self.heading(d,issue)
        d.rectangle((48,149,1152,572),fill=MINT,outline=INK,width=2)
        for x in range(48,1152,27): d.line((x,150,x,571),fill='#c8dcd0')
        for y in range(149,572,27): d.line((49,y,1151,y),fill='#c8dcd0')
        d.rectangle((80,180,243,222),fill=CORAL,outline=INK,width=2)
        self.text(d,(92,183),issue['label'],23)
        self.text(d,(79,245),'AI 娘\n周刊',79)
        self.text(d,(84,483),f"{len(issue['works'])} 部新作，放进这一期。",26,GREEN)
        host=Image.open(assets/Path(issue['host']).name).convert('RGBA')
        host.thumbnail((540,470),Image.Resampling.LANCZOS)
        im.paste(host,(620+(510-host.width)//2,572-host.height),host)
        self.text(d,(52,600),issue['period_label']+' / '+issue['basis_label'],20,GREEN)
        y=650
        for w in issue['works']:
            d.rectangle((48,y,1152,y+141),fill='#fffaf0',outline=INK,width=2)
            self.text(d,(62,y+37),f"{w['rank']:02d}",40,GREEN)
            cover=Image.open(assets/Path(w['cover']).name).convert('RGB')
            cover=ImageOps.fit(cover,(212,119),method=Image.Resampling.LANCZOS)
            im.paste(cover,(133,y+11))
            self.text(d,(363,y+13),w['short_title'],26,width=550,lines=2)
            self.text(d,(365,y+95),w['author'],18,'#77836b',width=500,lines=1)
            self.text(d,(957,y+29),f"{w['score']:,}",23)
            self.text(d,(984,y+80),'综合得分',14,'#77836b')
            y+=151
        self.bottom(im,d,issue,y+14)
        im.save(out,optimize=True)

    def work(self,issue,w,assets,out):
        im,d=self.background(1490);self.heading(d,issue)
        d.rectangle((48,149,1152,203),fill=MINT,outline=INK,width=2)
        self.text(d,(66,157),issue['label']+' / '+issue['basis_label'],22,GREEN)
        d.rectangle((1006,221,1151,341),fill=YELLOW,outline=INK,width=2)
        self.text(d,(1038,232),f"{w['rank']:02d}",50)
        self.text(d,(1034,302),'本期名次',17)
        self.text(d,(54,226),w['title'],35,width=903,lines=2)
        self.text(d,(57,344),'UP主 / '+w['author'],22,'#6b7d66',width=1020,lines=1)
        cover=Image.open(assets/Path(w['cover']).name).convert('RGB')
        cover=ImageOps.fit(cover,(1100,619),method=Image.Resampling.LANCZOS)
        im.paste(cover,(50,397));d.rectangle((48,395,1152,1018),outline=INK,width=2)
        self.text(d,(58,1042),'综合得分',18,GREEN)
        self.text(d,(54,1078),f"{w['score']:,}",58)
        for n,(key,label) in enumerate([('view','播放'),('coin','投币'),('favorite','收藏'),('like','点赞')]):
            x=490+n*163
            self.text(d,(x,1063),label,18,'#7b876f')
            self.text(d,(x,1106),f"{w['metrics'][key]:,}",23)
        self.text(d,(58,1191),w['summary'],22,'#62775e',width=1060,lines=2)
        self.bottom(im,d,issue,1300,w)
        im.save(out,optimize=True)
