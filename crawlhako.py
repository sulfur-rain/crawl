import os
import re
import asyncio
import aiohttp
import tempfile
import random
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from ebooklib import epub
from PIL import Image
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

BASE_URL = 'https://docln.net'

STYLE_CSS = '''
@page { margin: 5pt; }
body {
    font-family: "Times New Roman", serif;
    line-height: 1.6;
    text-align: justify;
    margin: 10px;
}
h1 { text-align: center; color: #2c3e50; margin-top: 50px; }
.chapter-header {
    font-size: 20px;
    text-align: center;
    color: #fff;
    padding-bottom: 10px;
    margin-bottom: 30px;
}
h3 { text-align: center; color: #7f8c8d; }
p { margin: 0; text-indent: 1.5em; margin-bottom: 0.5em; }
img {
    display: block;
    margin: 20px auto;
    max-width: 100%;
    height: auto;
    border-radius: 5px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}
.intro-box { text-align: center; }
.info-list { text-align: left; margin: 20px 0; border-left: 3px solid #34495e; padding-left: 15px; }
.summary-box { text-align: left; font-style: italic; background: #f9f9f9; color: #000; padding: 15px; border-radius: 8px; }
'''

class Utils:
    @staticmethod
    def resolve_url(base_url, relative_url):
        if not relative_url: return ""
        if relative_url.startswith('http'): return relative_url
        if relative_url.startswith('//'): return 'https:' + relative_url

        parsed = urlparse(base_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        if relative_url.startswith('/'):
            return domain + relative_url
        return domain + "/" + relative_url

    @staticmethod
    def format_filename(name):
        invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        for c in invalid_chars:
            name = name.replace(c, '')
        return name.strip()[:180]

class HakoAsyncCrawler:
    def __init__(self, temp_dir):
        self.temp_dir = temp_dir
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

    async def fetch_info(self, url):
        print(f"\n[*] Đang khởi động trình duyệt tàng hình (Stealth) để vượt Cloudflare...")
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                print(f"[*] Đang truy cập: {url}")
                await page.goto(url, timeout=60000)
                await page.wait_for_selector(".series-name, .volume-list", timeout=15000)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                title_tag = soup.select_one('.series-name a')
                novel_title = title_tag.text.strip() if title_tag else "Không rõ tên truyện"

                author = "Không rõ"
                for info in soup.select('.info-item'):
                    if "Tác giả:" in info.text: 
                        author = info.select_one('.info-value').text.strip()

                genres = ", ".join([a.text.strip() for a in soup.select('.series-gernes a')])
                summary_div = soup.select_one('.summary-content')
                summary_html = str(summary_div) if summary_div else "Không có tóm tắt."

                series_cover_bytes = None
                series_cover_div = soup.select_one('.series-cover .img-in-ratio')
                if series_cover_div and 'style' in series_cover_div.attrs:
                    s_match = re.search(r"url\(['\"]?(.*?)['\"]?\)", series_cover_div['style'])
                    if s_match:
                        s_img_url = Utils.resolve_url(url, s_match.group(1))
                        # Tắt xác thực SSL ở đây
                        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                            async with session.get(s_img_url) as resp:
                                if resp.status == 200: series_cover_bytes = await resp.read()

                volumes = []
                # Tắt xác thực SSL ở đây
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                    for vol_section in soup.select('section.volume-list'):
                        vol_title_tag = vol_section.select_one('.sect-title')
                        if not vol_title_tag: continue
                        vol_title = vol_title_tag.text.replace('*', '').strip()

                        vol_cover_bytes = None
                        v_cover_div = vol_section.select_one('.volume-cover .img-in-ratio')
                        if v_cover_div and 'style' in v_cover_div.attrs:
                            v_match = re.search(r"url\(['\"]?(.*?)['\"]?\)", v_cover_div['style'])
                            if v_match:
                                v_img_url = Utils.resolve_url(url, v_match.group(1))
                                try:
                                    async with session.get(v_img_url) as resp:
                                        if resp.status == 200: vol_cover_bytes = await resp.read()
                                except: pass

                        chapters = []
                        for a_tag in vol_section.select('.list-chapters li .chapter-name a'):
                            chapters.append({
                                "title": a_tag.text.strip(),
                                "url": Utils.resolve_url(url, a_tag.get('href'))
                            })

                        if chapters:
                            volumes.append({
                                "title": vol_title,
                                "chapters": chapters,
                                "cover_bytes": vol_cover_bytes if vol_cover_bytes else series_cover_bytes
                            })

                print(f"[+] Tìm thấy truyện: {novel_title} ({len(volumes)} tập)")
                return {
                    "title": novel_title, "author": author, 
                    "genres": genres, "summary": summary_html,
                    "cover_bytes": series_cover_bytes, "volumes": volumes
                }

            except Exception as e:
                print(f"[-] Lỗi tải thông tin: {e}")
                return None
            finally:
                await browser.close()

    async def download_chapter(self, page, session, chapter_info, chapter_idx):
        try:
            await page.goto(chapter_info['url'], timeout=60000)
            await page.wait_for_selector("#chapter-content", state="attached", timeout=15000)
            raw_html = await page.locator("#chapter-content").inner_html()

            soup = BeautifulSoup(raw_html, "html.parser")

            for r in soup.select('#chapter-c-protected, p[style*="display: none"]'): r.decompose()
            for banner in soup.find_all('a', href=re.compile(r"/truyen/\d+")):
                if banner.find('img', src=re.compile(r"chapter-banners|banners")): banner.decompose()
            for social in soup.select('a[href*="discord.gg"], a[href*="facebook.com"]'): social.decompose()

            for note in soup.select('.inline-note, .note-content'):
                note.insert_before(soup.new_string(" [Chú thích: "))
                note.insert_after(soup.new_string("] "))
                if 'style' in note.attrs: del note.attrs['style']

            chapter_images = []
            tasks = []
            
            for i, img_tag in enumerate(soup.find_all('img')):
                raw_img_url = img_tag.get('src')
                if not raw_img_url: continue

                img_url = Utils.resolve_url(chapter_info['url'], raw_img_url)
                if "icon" in img_url or "tracker" in img_url:
                    img_tag.decompose()
                    continue

                img_ext = img_url.split('.')[-1].split('?')[0]
                if len(img_ext) > 4: img_ext = "jpg"
                local_name = f"chap{chapter_idx}_img{i}.{img_ext}"
                save_path = os.path.join(self.temp_dir, local_name)

                img_tag['src'] = f"images/{local_name}"
                chapter_images.append(local_name)
                
                tasks.append(self._download_image(session, img_url, save_path))

            if tasks:
                await asyncio.gather(*tasks)

            clean_content = str(soup).replace('<br>', '<br/>').replace('<hr>', '<hr/>')
            clean_content = re.sub(r'<img([^>]*?)(?<!/)>', r'<img\1/>', clean_content)
            
            return clean_content, chapter_images

        except Exception as e:
            print(f"[-] Lỗi tải chương {chapter_info['title']}: {e}")
            return "<p>Chương này bị lỗi tải nội dung.</p>", []

    async def _download_image(self, session, url, save_path):
        try:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    with open(save_path, 'wb') as f:
                        f.write(await response.read())
        except: pass

async def process_volume(vol_info, novel_data, save_dir):
    print(f"\n{'-'*40}\n[*] Đang khởi tạo luồng tải tập: {vol_info['title']}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        crawler = HakoAsyncCrawler(temp_dir)
        html_contents = []
        images_list = []
        
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            # Tắt xác thực SSL ở đây
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                chapters = vol_info['chapters']
                for idx, chapter in enumerate(chapters):
                    print(f"[*] Đang tải chương {idx+1}/{len(chapters)}: {chapter['title']}")
                    html, imgs = await crawler.download_chapter(page, session, chapter, idx)
                    html_contents.append(html)
                    images_list.append(imgs)

                    if idx < len(chapters) - 1:
                        await asyncio.sleep(random.uniform(2.0, 4.0))

            await browser.close()

        print("[*] Đang đóng gói EPUB...")
        book = epub.EpubBook()
        full_title = f"{novel_data['title']} - {vol_info['title']}"
        book.set_title(full_title)
        book.set_language('vi')
        book.add_author(novel_data['author'])

        style_item = epub.EpubItem(uid="style_nav", file_name="style/style.css", media_type="text/css", content=STYLE_CSS)
        book.add_item(style_item)

        if vol_info['cover_bytes']:
            book.set_cover("cover.jpg", vol_info['cover_bytes'])
            cover_item = epub.EpubItem(uid="cover_img", file_name="images/cover.jpg", media_type="image/jpeg", content=vol_info['cover_bytes'])
            book.add_item(cover_item)

        intro_html = f'''
            <div class="intro-box">
                <img src="images/cover.jpg"/>
                <h1>{novel_data['title']}</h1>
                <h3>{vol_info['title']}</h3>
                <div class="info-list">
                    <p><b>Tác giả:</b> {novel_data['author']}</p>
                    <p><b>Thể loại:</b> {novel_data['genres']}</p>
                </div>
                <div class="summary-box">
                    <h4 style="text-align: center;">Tóm tắt</h4>
                    {novel_data.get('summary', '')}
                </div>
            </div>
        '''
        intro_page = epub.EpubHtml(title='Giới thiệu', file_name='intro.xhtml', lang='vi')
        intro_page.add_item(style_item)
        intro_page.content = f'<html><head><link rel="stylesheet" href="style/style.css" type="text/css"/></head><body>{intro_html}</body></html>'
        book.add_item(intro_page)

        all_images = set()
        for img_sublist in images_list:
            for img_name in img_sublist:
                if img_name not in all_images:
                    img_path = os.path.join(temp_dir, img_name)
                    if os.path.exists(img_path):
                        with open(img_path, 'rb') as f: img_data = f.read()
                        ext = img_name.split('.')[-1].lower()
                        media_type = f"image/{ext}" if ext in ['png', 'gif', 'webp'] else "image/jpeg"
                        img_item = epub.EpubItem(uid=img_name, file_name=f"images/{img_name}", media_type=media_type, content=img_data)
                        book.add_item(img_item)
                        all_images.add(img_name)

        spine = ['nav', intro_page]
        epub_chapters = [intro_page]
        for idx, (chapter_info, html_content) in enumerate(zip(chapters, html_contents)):
            chapter_title = chapter_info['title']
            c = epub.EpubHtml(title=chapter_title, file_name=f"chap_{idx+1:04d}.xhtml", lang='vi')
            c.add_item(style_item)
            c.content = f'<html><head><link rel="stylesheet" href="style/style.css" type="text/css"/></head><body><h2 class="chapter-header">{chapter_title}</h2>{html_content}</body></html>'
            
            book.add_item(c)
            epub_chapters.append(c)
            spine.append(c)

        book.toc = tuple(epub_chapters)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + epub_chapters

        os.makedirs(save_dir, exist_ok=True)
        epub_filename = Utils.format_filename(full_title) + ".epub"
        epub_path = os.path.join(save_dir, epub_filename)
        epub.write_epub(epub_path, book, {})
        print(f"[+] ĐÃ TẠO XONG: {epub_path}")

async def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=== DOCLN/HAKO CRAWLER PRO (ASYNC CLI) ===")
    url = input("Nhập URL bộ truyện (VD: https://docln.net/truyen/1234): ").strip()
    if not url: return

    with tempfile.TemporaryDirectory() as tmp:
        crawler = HakoAsyncCrawler(tmp)
        novel_data = await crawler.fetch_info(url)
        
    if not novel_data: return

    print("\n--- DANH SÁCH CÁC TẬP ---")
    for i, vol in enumerate(novel_data['volumes']):
        print(f"[{i}] {vol['title']}")

    choices = input("\nNhập số thứ tự các tập cần tải (cách nhau bằng dấu phẩy, VD: 0,1,2 | Hoặc gõ 'all'): ").strip()
    
    selected_indices = []
    if choices.lower() == 'all':
        selected_indices = list(range(len(novel_data['volumes'])))
    else:
        try:
            selected_indices = [int(x.strip()) for x in choices.split(',') if x.strip().isdigit()]
        except ValueError:
            print("[-] Lựa chọn không hợp lệ.")
            return

    save_dir = Utils.format_filename(novel_data['title'])
    
    for idx in selected_indices:
        if 0 <= idx < len(novel_data['volumes']):
            await process_volume(novel_data['volumes'][idx], novel_data, save_dir)
        else:
            print(f"[-] Bỏ qua chỉ số không hợp lệ: {idx}")

    print(f"\n[+] HOÀN TẤT TẤT CẢ! Thư mục lưu: ./{save_dir}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())