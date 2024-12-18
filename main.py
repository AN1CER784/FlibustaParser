from pprint import pprint
import aiohttp
import asyncio
from bs4 import BeautifulSoup



header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36',
}



class Parser:
    def __init__(self):
        self.site = "http://flibusta.is"

    async def get_html_with_retry(self, session, url, max_retries=3):
        for _ in range(max_retries):
            try:
                async with session.get(url, headers=header) as resp:
                    resp.raise_for_status()
                    return await resp.text()
            except (aiohttp.ClientError, aiohttp.ClientConnectionError) as e:
                print(f"Error fetching HTML: {e}")
                await asyncio.sleep(1)  # Пауза между повторными попытками
        return None

    def get_books(self, html, page=False):
        result = []
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find("div", id="main")
        if page:
            title = soup.find("h1", class_="title").text
            try:
                books = [self.site + link['href'] for link in div.find_all("a")
                         if str(link['href']).startswith("/b/") and not str(link['href']).endswith("/read")]
            except KeyError:
                return []
            authors = [author.text for author in div.find_all("a", href=lambda href: href and href.startswith("/a/"))][
                      1:]
            annotation = [p.text for p in div.find_all("p", class_=None)]
            annotation = annotation[0] if len(annotation) > 1 else "No annotation"
            result.append((title, authors, books, annotation))
        else:
            books_url = [self.site + link['href'] for a in div.find_all('li') for link in a.find_all('a')
                         if str(link['href']).startswith("/b/")]
            result.extend(books_url)
        return result

    async def get_book_links(self, session, links):
        result = []
        for link in links:
            html = await self.get_html_with_retry(session, link)
            if html:
                result.extend(self.get_books(html, True))
        return result

    async def parsing(self, session, message, author_mode=False):
        result = []
        search = message.strip().lower().replace(" ", "+")

        url = f"{self.site}/booksearch?ask={search}&chb=on" if not author_mode else f"{self.site}/booksearch?ask={search}&cha=on"
        html = await self.get_html_with_retry(session, url)
        if html:
            if author_mode:
                authors = self.get_author(html)
                if authors:
                    for author in authors:
                        author_html = await self.get_html_with_retry(session, author)
                        author_books = self.go_to_authors_book(author_html)
                        if author_books:
                            result.extend(await self.get_book_links(session, author_books))
                else:
                    return "The author not found!"
            else:
                books = self.get_books(html)
                if books:
                    result.extend(await self.get_book_links(session, books))
                else:
                    return "The book not found!"
        else:
            return "Error fetching HTML"
        return result

    def go_to_authors_book(self, html):
        result = []
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find("div", id="main")
        books_urls = [self.site + link['href'] for link in div.find_all('a') if str(link['href']).startswith("/b/")]
        for url in books_urls:
            if url.split('/')[-1].isdigit():
                result.append(url)
        return result

    def get_author(self, html):
        result = []
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find("div", id="main")
        author_url = [self.site + link['href'] for a in div.find_all('li') for link in a.find_all('a')
                      if str(link['href']).startswith("/a/")]
        result.extend(author_url)
        return result


async def main():
    parser = Parser()
    async with aiohttp.ClientSession() as session:
        books = await parser.parsing(session, "Мастер и маргарита", author_mode=False)
        for book in books:
            book_name = book[0]
            author = book[1]
            book_link = book[2]
            description = book[3]
            print(book_name)
            print(author)
            print(book_link)
            print(description)
            print("=====================================")


if __name__ == "__main__":
    asyncio.run(main())
