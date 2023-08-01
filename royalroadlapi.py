# pyright: strict

from bs4 import BeautifulSoup
from tornado import httpclient
from tornado.concurrent import Future
from tornado.httpclient import HTTPResponse
from typing import Tuple, List, cast, Dict


class fic:
    fic_id: int
    url: str
    title: str
    cover_image_url: str
    author: str
    description: str
    genres: List[str]
    ratings: float
    stats: List[str]
    chapter_links: List[str]
    num_chapters: int
    chapter_contents: Dict[int, str]
    chapter_titles: Dict[int, str]

    _fic_page_soup: BeautifulSoup

    async def get_fiction_object(
        self, client: httpclient.AsyncHTTPClient
    ) -> BeautifulSoup:
        resp = client.fetch(self.url)
        html = await resp

        soup = BeautifulSoup(html.body.decode("utf-8"), "lxml")
        assert soup is not None

        assert self._fiction_active()

        return soup

    async def get_chapters(
        self,
        http_client: httpclient.AsyncHTTPClient,
        chapter_indexes: List[int],
    ):

        chapter_futures: List[Tuple[int, Future[HTTPResponse]]] = []
        for i in chapter_indexes:
            chapter_id = self.chapter_links[i]
            url = "https://www.royalroad.com" + str(chapter_id)
            print(url)
            chapter_futures.append(
                (
                    i,
                    http_client.fetch(
                        url.strip(),
                        True,
                        method="GET",
                        connect_timeout=10000,
                        request_timeout=10000,
                    ),
                )
            )

        for i, chap in chapter_futures:
            resp = await chap
            content, title = self.extract_chapter_html_title(resp)
            self.chapter_contents[i] = content
            self.chapter_titles[i] = title

    def __init__(self, fiction_id: int) -> None:
        self.fic_id = fiction_id
        self.url = "https://www.royalroad.com/fiction/" + str(self.fic_id)
        self.chapter_titles = {}
        self.chapter_contents = {}

    # hack since __init__ doesn't mix well with async
    async def initialize(self, client: httpclient.AsyncHTTPClient) -> None:
        self._fic_page_soup = await self.get_fiction_object(client)
        assert self._fic_page_soup is not None

        self.title = self._get_fiction_title()
        self.cover_image_url = self._get_fiction_cover_image_url()
        self.author = self._get_fiction_author()
        self.description = self._get_fiction_description()
        self.genres = self.get_fiction_genres()
        self.ratings = self.get_fiction_rating()
        self.stats = self.get_fiction_statistics()
        self.chapter_links = self.extract_chapter_links()
        self.num_chapters = len(self.chapter_links)

    def _get_fiction_cover_image_url(self) -> str:
        image_elt = self._fic_page_soup.find("meta", attrs={"property": "og:image"})
        assert image_elt is not None
        cover_image = cast(str, image_elt.get("content"))

        return cover_image

    def _get_fiction_title(self) -> str:
        title_elt = self._fic_page_soup.find("meta", attrs={"name": "twitter:title"})
        assert title_elt is not None, self._fic_page_soup
        title = cast(str, title_elt.get("content"))

        return title

    def _get_fiction_author(self) -> str:
        author_elt = self._fic_page_soup.find(
            "meta", attrs={"property": "books:author"}
        )
        assert author_elt is not None

        return cast(str, author_elt.get("content"))

    def _fiction_active(self) -> bool:
        not_active = self._fic_page_soup.find(
            "div", attrs={"class": "number font-red-sunglo"}
        )
        if not not_active:
            return True

        return False

    def _get_fiction_description(self) -> str:
        descr_elt = self._fic_page_soup.find("div", attrs={"class": "description"})

        assert descr_elt is not None
        description = descr_elt.text.strip()

        if description == "":
            return "No Description"

        return description

    def get_fiction_genres(self) -> List[str]:
        genres: List[str] = []
        genre_tags_part1 = self._fic_page_soup.findAll(
            "span", attrs={"class": "label label-default label-sm bg-blue-hoki"}
        )
        genre_tags_part2 = self._fic_page_soup.findAll(
            "span", attrs={"property": "genre"}
        )
        for tag in genre_tags_part1:
            genres.append(tag.text.strip())
        for tag in genre_tags_part2:
            genres.append(tag.text.strip())
        return genres

    def get_fiction_rating(self) -> float:
        rating_value = cast(
            str,
            self._fic_page_soup.find(
                "meta", attrs={"property": "books:rating:value"}
            ).get("content"),
        )
        rating_scale = cast(
            str,
            self._fic_page_soup.find(
                "meta", attrs={"property": "books:rating:scale"}
            ).get("content"),
        )
        assert rating_scale == "5"

        return float(rating_value)

    def get_fiction_statistics(self) -> List[str]:
        return [
            stat.text.strip()
            for stat in self._fic_page_soup.findAll(
                "li", attrs={"class": "bold uppercase font-red-sunglo"}
            )
        ][:6]

    def extract_chapter_links(self) -> List[str]:
        chapter_links = [
            tag.get("data-url")
            for tag in self._fic_page_soup.findAll(
                "tr", attrs={"style": "cursor: pointer"}
            )
        ]
        return chapter_links

    async def obtain_and_save_image(
        self,
        client: httpclient.AsyncHTTPClient,
        directory: str,
        cover_image_url: str,
    ):
        image_data = await self.download_image_data(client, cover_image_url)

        with open(directory + "cover.jpg", "wb") as cover_image_file:
            cover_image_file.write(image_data)

    async def download_image_data(
        self, cli: httpclient.AsyncHTTPClient, cover_image_url: str
    ):
        resp = await cli.fetch(
            cover_image_url,
            raise_error=False,
        )
        assert resp.code == 200, cover_image_url
        return resp.body

    def extract_chapter_html_title(self, response: HTTPResponse) -> Tuple[str, str]:
        assert response.code == 200

        html = response.body.decode("utf-8")

        assert (
            "Could not find host | www.royalroad.com | Cloudflare".lower()
            not in html.lower()
        )

        soup = BeautifulSoup(html, "lxml")
        chapter_title = soup.find(
            "h1", attrs={"style": "margin-top: 10px", "class": "font-white"}
        )

        assert chapter_title is not None

        chapter_title = chapter_title.text.strip()
        content_html = soup.find(
            "div", attrs={"class": "chapter-inner chapter-content"}
        )
        content_html = str(content_html)
        return content_html, chapter_title
