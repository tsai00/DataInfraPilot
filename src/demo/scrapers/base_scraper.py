import asyncio
import copy
import logging
import math
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from types import TracebackType
from typing import Any
from uuid import uuid4

import httpx
from tenacity import after_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential, wait_fixed

from src.demo.utils import setup_logger


class ScraperParsingError(Exception):
    pass


class ScraperError(Exception):
    pass


class RequestMethod(StrEnum):
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'


@dataclass(frozen=True)
class ScraperPageResponse:
    total_items: int
    total_pages: int
    items: list
    page: int


@dataclass(frozen=True)
class ScraperRequestDetails:
    method: RequestMethod
    url: str
    params: dict | None = None
    json: dict | None = None
    headers: dict | None = None
    cookies: dict | None = None


@dataclass
class ScraperRunMetadata:
    project: str
    run_id: str = field(default_factory=uuid4)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = None
    pages_total: int = 0
    items_total: int = 0
    items_scraped: int = 0
    is_successful: bool = False
    get_requests_sent: int = 0
    post_requests_sent: int = 0

    def capture_scraping_end_time(self) -> None:
        self.end_time = datetime.now()

    def __str__(self) -> str:
        duration_str = 'N/A'
        if self.end_time:
            duration = self.end_time - self.start_time
            total_seconds = int(duration.total_seconds())

            hours = math.floor(total_seconds / 3600)
            remaining_seconds_after_hours = total_seconds % 3600
            minutes = math.floor(remaining_seconds_after_hours / 60)
            seconds = remaining_seconds_after_hours % 60

            parts = []

            if hours > 0:
                parts.append(f'{hours} hr')
            if minutes > 0:
                parts.append(f'{minutes} min')
            if seconds > 0 or not parts:
                parts.append(f'{seconds} sec')

            duration_str = ', '.join(parts)
            if not duration_str:
                duration_str = '0 sec'

        details = {
            'Project': self.project,
            'Run ID': self.run_id,
            'Start Time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'End Time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else 'N/A',
            'Duration': duration_str,
            'Items Scraped': f'{self.items_scraped}/{self.items_total}',
            'Total pages': self.pages_total,
            'Successful': self.is_successful,
            'GET Requests Sent': self.get_requests_sent,
            'POST Requests Sent': self.post_requests_sent,
        }

        max_label_len = max(len(label) for label in details)

        formatted_output = ['\n--- Scraper Run Details ---']
        for label, value in details.items():
            formatted_output.append(f'{label.ljust(max_label_len)}: {value}')
        formatted_output.append('---------------------------')

        return '\n'.join(formatted_output)

    def to_dict(self) -> dict:
        instance_copy = copy.copy(self)
        instance_copy.run_id = str(instance_copy.run_id)
        instance_copy.start_time = instance_copy.start_time.strftime('%Y-%m-%d %H:%M:%S')
        instance_copy.end_time = (
            instance_copy.end_time.strftime('%Y-%m-%d %H:%M:%S') if instance_copy.end_time else 'N/A'
        )

        return asdict(instance_copy)


class BaseScraper(ABC):
    def __init__(
        self, scraper_name: str, page_size: int, dynamic_params_options: list[dict] | None = None, start_page: int = 1
    ) -> None:
        self._logger = setup_logger(scraper_name)
        self.page_size = page_size
        self.start_page = start_page
        self.scraper_name = scraper_name

        api_key = os.environ.get('SCRAPERAPI_KEY')

        if api_key is None:
            raise ValueError('SCRAPERAPI_KEY environment variable is not set')

        self._proxy = f'http://scraperapi.keep_headers=true:{api_key}@proxy-server.scraperapi.com:8001'

        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

        self.scraper_run_metadata = ScraperRunMetadata(scraper_name.replace('Scraper', ''))

        self.dynamic_params_options = dynamic_params_options or [{}]

        self._logger.info(f'Starting {scraper_name} scraper run with ID {self.scraper_run_metadata.run_id}')

    def __enter__(self) -> 'BaseScraper':
        self._logger.debug('Entering synchronous context. Initializing httpx.Client.')

        if self._sync_client is None:
            self._sync_client = httpx.Client(proxy=self._proxy, verify=False, timeout=120)

        self._logger.debug(f'Starting {self.scraper_name} scraper run (sync context)')

        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        if self._sync_client:
            self._logger.debug('Exiting synchronous context. Closing httpx.Client.')
            self._sync_client.close()
            self._sync_client = None

        self.scraper_run_metadata.capture_scraping_end_time()
        self.scraper_run_metadata.is_successful = exc_type is None
        self._logger.debug(f'Finished {self.scraper_name} scraper run (sync exit)')
        self._logger.info(self.scraper_run_metadata)

    async def __aenter__(self) -> 'BaseScraper':
        self._logger.debug('Entering asynchronous context. Initializing httpx.AsyncClient.')

        if self._async_client is None:
            self._async_client = httpx.AsyncClient(proxy=self._proxy, verify=False, timeout=120)

        self._logger.debug(f'Starting {self.scraper_name} scraper run (async context)')

        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        if self._async_client:
            self._logger.debug('Exiting asynchronous context. Closing httpx.AsyncClient.')
            await self._async_client.aclose()
            self._async_client = None

        self.scraper_run_metadata.capture_scraping_end_time()
        self.scraper_run_metadata.is_successful = exc_type is None
        self._logger.debug(f'Finished {self.scraper_name} scraper run (async exit)')
        self._logger.info(self.scraper_run_metadata)

    def scrape(self) -> list[Any]:
        self._logger.debug(f'Starting synchronous scrape for {self.scraper_name}')
        all_scraped_items = []

        if self.dynamic_params_options and len(self.dynamic_params_options) > 1:
            self._logger.debug(
                f'Processing dynamic synchronous scrape with {len(self.dynamic_params_options)} combinations.'
            )
            for params_combo in self.dynamic_params_options:
                self._logger.info(f'Initiating sub-scrape with parameters: {params_combo}')
                try:
                    sub_scrape_items, sub_scrape_total_items, sub_scrape_total_pages = self._process_pagination_sync(
                        start_page=self.start_page,
                        dynamic_params=params_combo,
                    )
                    all_scraped_items.extend(sub_scrape_items)
                    self.scraper_run_metadata.items_total += sub_scrape_total_items
                    self.scraper_run_metadata.pages_total += sub_scrape_total_pages
                except Exception as e:
                    self._logger.exception(
                        f'Error during synchronous sub-scrape with parameters {params_combo}: {e}', exc_info=True
                    )
        else:
            self._logger.debug(f'Processing standard (non-dynamic) synchronous scrape for {self.scraper_name}')
            items, total_items, total_pages = self._process_pagination_sync(
                start_page=self.start_page,
                dynamic_params=self.dynamic_params_options[0] if self.dynamic_params_options else {},
            )
            all_scraped_items.extend(items)
            self.scraper_run_metadata.items_total += total_items
            self.scraper_run_metadata.pages_total += total_pages

        self.scraper_run_metadata.items_scraped = len(all_scraped_items)
        return all_scraped_items

    async def scrape_async(self, concurrency: int = 10) -> list[Any]:
        self._logger.debug(f'Starting asynchronous scrape for {self.scraper_name}')
        all_scraped_items = []

        if self.dynamic_params_options and len(self.dynamic_params_options) > 1:
            self._logger.debug(
                f'Processing dynamic asynchronous scrape with {len(self.dynamic_params_options)} combinations.'
            )
            # For simplicity, iterate sub-scrapes sequentially, but each sub-scrape will be async.
            # If true parallel sub-scrapes are desired, you'd collect tasks here.
            for params_combo in self.dynamic_params_options:
                self._logger.info(f'Initiating async sub-scrape with parameters: {params_combo}')
                try:
                    (
                        sub_scrape_items,
                        sub_scrape_total_items,
                        sub_scrape_total_pages,
                    ) = await self._process_pagination_async(
                        start_page=self.start_page, dynamic_params=params_combo, concurrency=concurrency
                    )
                    all_scraped_items.extend(sub_scrape_items)
                    self.scraper_run_metadata.items_total += sub_scrape_total_items
                    self.scraper_run_metadata.pages_total += sub_scrape_total_pages
                except Exception as e:
                    self._logger.exception(
                        f'Error during asynchronous sub-scrape with parameters {params_combo}: {e}', exc_info=True
                    )
                    raise ValueError(f'Error during asynchronous sub-scrape with parameters {params_combo}: {e}') from e
        else:
            self._logger.debug(f'Processing standard (non-dynamic) asynchronous scrape for {self.scraper_name}')
            items, total_items, total_pages = await self._process_pagination_async(
                start_page=self.start_page,
                dynamic_params=self.dynamic_params_options[0] if self.dynamic_params_options else {},
                concurrency=concurrency,
            )
            all_scraped_items.extend(items)
            self.scraper_run_metadata.items_total += total_items
            self.scraper_run_metadata.pages_total += total_pages

        self.scraper_run_metadata.items_scraped = len(all_scraped_items)
        return all_scraped_items

    @abstractmethod
    def _build_request_details(self, page: int, dynamic_params: dict | None = None) -> ScraperRequestDetails:
        pass

    @abstractmethod
    def _parse_response(self, response: httpx.Response, page: int) -> ScraperPageResponse:
        pass

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, ScraperParsingError)),
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        after=after_log(logging.getLogger(__name__), logging.WARNING),
        reraise=True,
    )
    def _scrape_and_parse_page_sync(self, page: int, dynamic_params: dict | None = None) -> ScraperPageResponse:
        self._logger.debug(f'Attempting to scrape and parse page {page} with dynamic params {dynamic_params} (sync)')
        request_details = self._build_request_details(page, dynamic_params)

        response = self._send_request(
            method=request_details.method,
            url=request_details.url,
            json=request_details.json,
            params=request_details.params,
            headers=request_details.headers,
            cookies=request_details.cookies,
        )

        parsed_response = self._parse_response(response, page)
        self._logger.debug(f'Successfully scraped and parsed page {page} (sync)')
        return parsed_response

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, ScraperParsingError)),
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        after=after_log(logging.getLogger(__name__), logging.WARNING),
        reraise=True,
    )
    async def _scrape_and_parse_page_async(self, page: int, dynamic_params: dict | None = None) -> ScraperPageResponse:
        self._logger.debug(f'Attempting to scrape and parse page {page} with dynamic params {dynamic_params} (async)')
        request_details = self._build_request_details(page, dynamic_params)

        response = await self._send_request_async(
            method=request_details.method,
            url=request_details.url,
            json=request_details.json,
            params=request_details.params,
            headers=request_details.headers,
            cookies=request_details.cookies,
        )

        parsed_response = self._parse_response(response, page)
        self._logger.debug(f'Successfully scraped and parsed page {page} (async)')
        return parsed_response

    def calculate_number_of_pages(self, num_of_items: int, page_size: int = None) -> int:
        page_size = page_size or self.page_size

        if num_of_items <= 0:
            return 0

        return num_of_items // page_size if num_of_items % page_size == 0 else num_of_items // page_size + 1

    def send_get_request(
        self, url: str, params: dict | None = None, headers: dict | None = None, cookies: dict | None = None
    ) -> httpx.Response:
        return self._send_request(method=RequestMethod.GET, url=url, params=params, headers=headers, cookies=cookies)

    async def send_get_request_async(
        self, url: str, params: dict | None = None, headers: dict | None = None, cookies: dict | None = None
    ) -> httpx.Response:
        return await self._send_request_async(
            method=RequestMethod.GET, url=url, params=params, headers=headers, cookies=cookies
        )

    def send_post_request(
        self, url: str, json: dict = None, params: dict = None, headers: dict = None, cookies: dict = None
    ) -> httpx.Response:
        return self._send_request(
            method=RequestMethod.POST, url=url, json=json, params=params, headers=headers, cookies=cookies
        )

    async def send_post_request_async(
        self, url: str, json: dict = None, params: dict = None, headers: dict = None, cookies: dict = None
    ) -> httpx.Response:
        return await self._send_request_async(
            method=RequestMethod.POST, url=url, json=json, params=params, headers=headers, cookies=cookies
        )

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        after=after_log(logging.getLogger(__name__), logging.WARNING),
        reraise=True,
    )
    def _send_request(
        self,
        method: RequestMethod,
        url: str,
        json: dict = None,
        params: dict = None,
        headers: dict = None,
        cookies: dict = None,
    ) -> httpx.Response:
        # If scraper is running as a context manager, self._sync_client will be set.
        # Otherwise, create a temporary client for this single request.
        client_to_use = (
            self._sync_client if self._sync_client else httpx.Client(proxy=self._proxy, verify=False, timeout=120)
        )

        self._logger.debug(
            f'Sending {method} sync request to {url} with params: {params}, headers: {headers}, cookies: {cookies}, json: {json}'
        )

        try:
            response = client_to_use.request(
                method=method, url=url, json=json, params=params, headers=headers, cookies=cookies, timeout=120
            )

            return self._handle_response(response)
        finally:
            # If we created a temporary client, close it immediately
            if client_to_use is not self._sync_client:
                client_to_use.close()

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        after=after_log(logging.getLogger(__name__), logging.WARNING),
        reraise=True,
    )
    async def _send_request_async(
        self,
        method: RequestMethod,
        url: str,
        json: dict = None,
        params: dict = None,
        headers: dict = None,
        cookies: dict = None,
    ) -> httpx.Response:
        # If scraper is running as an async context manager, self._async_client will be set.
        # Otherwise, create a temporary async client for this single request.
        client_to_use = (
            self._async_client
            if self._async_client
            else httpx.AsyncClient(proxy=self._proxy, verify=False, timeout=120)
        )

        self._logger.debug(
            f'Sending {method} async request to {url} with params: {params}, headers: {headers}, cookies: {cookies}, json: {json}'
        )

        try:
            response = await client_to_use.request(
                method=method, url=url, json=json, params=params, headers=headers, cookies=cookies, timeout=120
            )

            return self._handle_response(response)
        finally:
            # If we created a temporary client, close it immediately
            if client_to_use is not self._async_client:
                await client_to_use.aclose()

    def _handle_response(self, response: httpx.Response) -> httpx.Response:
        if response.request.method == RequestMethod.GET:
            self.scraper_run_metadata.get_requests_sent += 1
        elif response.request.method == RequestMethod.POST:
            self.scraper_run_metadata.post_requests_sent += 1

        status_code = response.status_code

        response_url = str(response.url)

        if 200 <= status_code < 300:
            return response
        elif status_code == 404:
            self._logger.exception(f'Page not found (404) for {response_url}.', exc_info=False)
            return response
        else:
            self._logger.warning(
                f'Wrong status code ({status_code}) for page {response_url}, trying again - {response.text[:100]}...'
            )
            response.raise_for_status()
            return response

    def _process_pagination_sync(
        self,
        start_page: int = 1,
        dynamic_params: dict | None = None,
    ) -> tuple[list[Any], int, int]:
        self._logger.debug(f'Processing pagination (sync), starting at page {start_page}')

        first_page_r_parsed = self._scrape_and_parse_page_sync(page=start_page, dynamic_params=dynamic_params)

        num_of_pages = first_page_r_parsed.total_pages
        num_of_items = first_page_r_parsed.total_items

        self._logger.debug(f'Found {num_of_items} items on {num_of_pages} pages (sequentially)')

        all_items = []
        all_items.extend(first_page_r_parsed.items)
        self._logger.info(
            f'On page {start_page}: {len(first_page_r_parsed.items)} items (scraped in total for this sub-run: {len(all_items)})'
        )

        for page in range(start_page + 1, num_of_pages + 1 if start_page != 0 else num_of_pages):
            page_r_parsed = self._scrape_and_parse_page_sync(page=page, dynamic_params=dynamic_params)

            page_items = page_r_parsed.items
            all_items.extend(page_items)

            self._logger.info(
                f'On page {page} for {dynamic_params}: {len(page_items)} products (scraped in total for this sub-run: {len(all_items)})'
            )

        return all_items, num_of_items, num_of_pages

    async def _process_pagination_async(
        self, start_page: int = 1, dynamic_params: dict | None = None, concurrency: int = 10
    ) -> tuple[list[Any], int, int]:
        self._logger.debug(f'Processing pagination (async, concurrency {concurrency}), starting at page {start_page}')

        first_page_r_parsed = await self._scrape_and_parse_page_async(page=start_page, dynamic_params=dynamic_params)

        num_of_pages = first_page_r_parsed.total_pages
        num_of_items = first_page_r_parsed.total_items

        self._logger.info(f'Found {num_of_items} items on {num_of_pages} pages (asynchronously)')

        first_page_items = [
            {**x, '_scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')} for x in first_page_r_parsed.items
        ]
        all_items = []
        all_items.extend(first_page_items)

        self._logger.info(
            f'On page {start_page}: {len(first_page_r_parsed.items)} items (scraped in total for this sub-run: {len(all_items)})'
        )

        pages_to_scrape = list(range(start_page + 1, num_of_pages + 1 if start_page != 0 else num_of_pages))
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_and_parse_page_task(page_num: int, current_dynamic_params: dict) -> ScraperPageResponse:
            async with semaphore:
                try:
                    parsed_response = await self._scrape_and_parse_page_async(
                        page=page_num, dynamic_params=current_dynamic_params
                    )
                    return parsed_response
                except Exception as e:
                    self._logger.exception(
                        f'Failed to scrape or parse page {page_num} after all retries: {e}', exc_info=True
                    )
                    # If all retries fail, return an empty ScraperPageResponse for this page
                    # The main loop will continue but this page's items will be empty.
                    return ScraperPageResponse(total_items=0, total_pages=0, items=[], page=page_num)

        tasks = [fetch_and_parse_page_task(p, dynamic_params) for p in pages_to_scrape]

        for future in asyncio.as_completed(tasks):
            result = await future

            page_items = [{**x, '_scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')} for x in result.items]

            all_items.extend(page_items)
            self._logger.info(
                f'On page {result.page}: {len(page_items)} products (scraped in total: {len(all_items)}/{num_of_items})'
            )

        return all_items, num_of_items, num_of_pages
