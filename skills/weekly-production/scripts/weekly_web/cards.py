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
    'landscape': ('cover-wechat-2.35x1.jpg', (1410, 600)),
    'square': ('cover-wechat-1x1.jpg', (1080, 1080)),
}


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
        """Compose both feed formats from the character art, not a cropped video frame."""
        outputs = {}
        for name, (filename, size) in WECHAT_COVERS.items():
            out = Path(assets) / filename
            self.wechat_cover(issue, assets, out, size)
            outputs[name] = out
        return outputs

    def wechat_cover(self, issue, assets, out, size):
        width, height = size
        square = width == height
        im = Image.new('RGB', size, PAPER)
        d = ImageDraw.Draw(im)
        for y in range(8, height, 18):
            for x in range(8, width, 18):
                d.rectangle((x, y, x + 1, y + 1), fill='#cbd1b8')
        d.rectangle((24, 24, width - 24, height - 24), outline=INK, width=3)
        d.rectangle((44, 42, 100, 98), fill='#c8e4d9', outline=INK, width=2)
        self.text(d, (51, 44), 'AI', 32)
        self.text(d, (116, 40), 'AI GIRL WEEKLY', 24, GREEN)
        self.text(d, (117, 76), 'AI 娘创作放映室', 16, GREEN)
        badge = 'ISSUE ' + str(issue['number'])
        d.rectangle((width - 275, 42, width - 44, 98), fill=YELLOW, outline=INK, width=2)
        self.text(d, (width - 257, 47), badge, 29, width=197, lines=1)

        left, top, right, bottom = (40, 126, width - 40, height - 74)
        d.rectangle((left, top, right, bottom), fill=MINT, outline=INK, width=3)
        for x in range(left + 27, right, 27):
            d.line((x, top + 2, x, bottom - 2), fill='#c8dcd0')
        for y in range(top + 27, bottom, 27):
            d.line((left + 2, y, right - 2, y), fill='#c8dcd0')

        label_size = 23
        label_width = min(370, max(160, int(d.textlength(issue['label'], font=self.font(label_size))) + 32))
        d.rectangle((76, 153, 76 + label_width, 195), fill=CORAL, outline=INK, width=2)
        self.text(d, (91, 154), issue['label'], label_size, width=label_width - 30, lines=1)

        name = self.settings.site_name.replace('AI 娘', 'AI娘')
        title_width, title_size = (420, 125) if square else (740, 112)
        title = name[:-2] + '\n周刊' if square and name.endswith('周刊') else name
        while title_size > 24 and max(d.textlength(line, font=self.font(title_size)) for line in title.split('\n')) > title_width:
            title_size -= 1
        title_xy = (70, 242 if square else 219)
        self.text(d, (title_xy[0] + 5, title_xy[1] + 5), title, title_size, '#fffaf0')
        self.text(d, title_xy, title, title_size, INK)

        if square:
            self.text(d, (77, 643), '模型下班，\n角色上场。', 40, GREEN)
            self.text(d, (79, 810), str(len(issue['works'])) + ' 部作品', 27)
            self.text(d, (79, 856), str(issue['authors']) + ' 位创作者', 27)
            art_box = (494, 206, right - 3, bottom - 3)
            art_size = (535, 780)
            circle = (489, 390, 1095, 996)
        else:
            self.text(d, (77, 374), '模型下班，角色上场。', 34, GREEN)
            self.text(d, (79, 454), f"{len(issue['works'])} 部作品 · {issue['authors']} 位创作者", 25)
            art_box = (848, top + 3, right - 3, bottom - 3)
            art_size = (486, 730)
            circle = (848, 167, 1370, 689)

        art = Image.new('RGBA', (art_box[2] - art_box[0], art_box[3] - art_box[1]))
        ad = ImageDraw.Draw(art)
        ad.ellipse(tuple(value - art_box[i % 2] for i, value in enumerate(circle)), fill='#bad6de', outline=INK, width=3)
        with Image.open(Path(assets) / Path(issue['host']).name) as source:
            host = source.convert('RGBA')
        bounds = host.getbbox()
        if bounds:
            host = host.crop(bounds)
        host.thumbnail(art_size, Image.Resampling.LANCZOS)
        art.alpha_composite(host, ((art.width - host.width) // 2, 9 if square else 12))
        im.paste(art, art_box[:2], art)

        sx, sy = (466, 655) if square else (783, 306)
        points = [(sx - 11, sy - 27), (sx + 11, sy - 27), (sx + 11, sy - 11), (sx + 27, sy - 11),
                  (sx + 27, sy + 11), (sx + 11, sy + 11), (sx + 11, sy + 27), (sx - 11, sy + 27),
                  (sx - 11, sy + 11), (sx - 27, sy + 11), (sx - 27, sy - 11), (sx - 11, sy - 11)]
        d.polygon([(x + 3, y + 4) for x, y in points], fill=INK)
        d.polygon(points, fill=CORAL)
        self.text(d, (47, height - 61), issue['period_label'], 19, GREEN, width=width - 430, lines=1)
        self.text(d, (width - 356, height - 61), issue['basis_label'] + ' / ' + issue['date'], 18, GREEN, width=310, lines=1)
        im.save(out, quality=95, subsampling=0, optimize=True)

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
