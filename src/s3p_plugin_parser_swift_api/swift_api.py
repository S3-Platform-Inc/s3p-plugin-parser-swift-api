import time

from s3p_sdk.exceptions.parser import S3PPluginParserOutOfRestrictionException, S3PPluginParserFinish
from s3p_sdk.plugin.payloads.parsers import S3PParserBase
from s3p_sdk.types import S3PRefer, S3PDocument, S3PPlugin, S3PPluginRestrictions
from s3p_sdk.types.plugin_restrictions import FROM_DATE
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
import datetime


class SwiftApiParser(S3PParserBase):
    """
    Парсер, использующий базовый класс парсера S3P
    """

    def __init__(self, refer: S3PRefer, plugin: S3PPlugin, restrictions: S3PPluginRestrictions, web_driver: WebDriver,
                 url: str, timeout: int = 20):
        super().__init__(refer, plugin, restrictions)

        # Тут должны быть инициализированы свойства, характерные для этого парсера. Например: WebDriver
        self.URL = url
        self._driver = web_driver
        self._timeout = timeout
        self._wait = WebDriverWait(self._driver, timeout=self._timeout)

    def _parse(self) -> None:
        # HOST - это главная ссылка на источник, по которому будет "бегать" парсер
        self.logger.debug(F"Parser enter to {self._refer.to_logging}")

        self._driver.get(url=self.URL)
        list_of_news = self._driver.find_elements(By.CLASS_NAME, 'field-content')
        documents = []
        for i in range(len(list_of_news)):
            documents.append({})
            documents[i]['title'] = list_of_news[i].find_element(By.CLASS_NAME, 'api_title').text
            search_source = self._trying_get_info('Consumer_Name', list_of_news[i])
            consumers = search_source[1].text.split(',') if search_source[0] else None

            search_source = self._trying_get_info('Category_Name2', list_of_news[i])
            categories = search_source[1].text.split('\n') if search_source[0] else None

            documents[i]['other_data'] = {
                'consumer': consumers,
                'category': categories
            }
            documents[i]['abstract'] = self._driver.find_element(By.CLASS_NAME, 'API_Content_Summary').text
            documents[i]['href'] = self._driver.find_element(By.CLASS_NAME, 'api-card').get_attribute('href')
        for i in range(len(documents)):
            self._driver.get(documents[i]['href'])
            documents[i]['text'] = self._driver.find_element(By.CLASS_NAME, 'content').text

            document = S3PDocument(
                title=documents[i]['title'],
                abstract=documents[i]['abstract'],
                link=documents[i]['href'],
                text=documents[i]['text'],
                other=documents[i]['other_data'],
                loaded=datetime.datetime.now(),
                id=None,
                published=datetime.datetime.now(),
                storage=None
            )
            try:
                self._find(document=document)
            except S3PPluginParserOutOfRestrictionException as e:
                if e.restriction == FROM_DATE:
                    self.logger.debug(f'Document is out of date range `{self._restriction.from_date}`')
                    raise S3PPluginParserFinish(self._plugin,
                                                f'Document is out of date range `{self._restriction.from_date}`', e)

    def _trying_get_info(self, class_name: str, web_element: WebElement):
        try:
            result = web_element.find_element(By.CLASS_NAME, class_name)
            return [True, result]
        except Exception as _ex:
            self.logger.warn(_ex)
            return [False, None]

    # def _parse_page(self, url: str) -> S3PDocument:
    #     doc = self._page_init(url)
    #     return doc
    #
    # def _page_init(self, url: str) -> S3PDocument:
    #     self._initial_access_source(url)
    #     return S3PDocument()
    #
    # def _encounter_pages(self) -> str:
    #     """
    #     Формирование ссылки для обхода всех страниц
    #     """
    #     _base = self.URL
    #     _param = f'&page='
    #     page = 0
    #     while True:
    #         url = str(_base) + _param + str(page)
    #         page += 1
    #         yield url
    #
    # def _collect_doc_links(self, _url: str) -> list[str]:
    #     """
    #     Формирование списка ссылок на материалы страницы
    #     """
    #     try:
    #         self._initial_access_source(_url)
    #         self._wait.until(ec.presence_of_all_elements_located((By.CLASS_NAME, '<class контейнера>')))
    #     except Exception as e:
    #         raise NoSuchElementException() from e
    #     links = []
    #
    #     try:
    #         articles = self._driver.find_elements(By.CLASS_NAME, '<class контейнера>')
    #     except Exception as e:
    #         raise NoSuchElementException('list is empty') from e
    #     else:
    #         for article in articles:
    #             try:
    #                 doc_link = article.find_element(By.TAG_NAME, 'a').get_attribute('href')
    #             except Exception as e:
    #                 raise NoSuchElementException(
    #                     'Страница не открывается или ошибка получения обязательных полей') from e
    #             else:
    #                 links.append(doc_link)
    #     return links

    def _initial_access_source(self, url: str, delay: int = 2):
        self._driver.get(url)
        self.logger.debug('Entered on web page ' + url)
        time.sleep(delay)
