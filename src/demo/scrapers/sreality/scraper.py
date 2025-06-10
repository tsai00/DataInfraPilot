import json
from typing import Literal

import httpx

from src.demo.scrapers.base_scraper import BaseScraper, ScraperPageResponse, ScraperRequestDetails, RequestMethod, \
    ScraperParsingError


class SrealityScraper(BaseScraper):
    BASE_URL = 'https://www.sreality.cz'

    def __init__(self, listing_type: Literal['rent', 'sale']):
        if listing_type == 'rent':
            self.listing_type = 'pronajem'
        elif listing_type == 'sale':
            self.listing_type = 'prodej'
        else:
            raise ValueError(f'Unknown listing type: {listing_type}')

        self._api_version = '1.0.358'  # Start API version (will be increased dynamically if needed)

        super().__init__('SrealityScraper', 22, 1)

        self._check_api_version_availability()

        self._logger.info(f'Scraping {listing_type} listings')

    def _check_api_version_availability(self):
        self._logger.info(f"Checking availability of API version {self._api_version}...")
        max_attempts = 50
        valid_api_version = None

        while valid_api_version is None and max_attempts > 0:
            response = self.send_get_request(f'{self.BASE_URL}/_next/data/{self._api_version}/cs/hledani/{self.listing_type}/byty/praha.json')
            if response.status_code == 404:
                next_api_version = f'1.0.{int(self._api_version.split(".")[-1]) + 1}'
                self._logger.warning(f"API version {self._api_version} is not available. Will try {next_api_version}.")

                self._api_version = next_api_version
                max_attempts -= 1
            else:
                self._logger.info(f"API version {self._api_version} is available and will be used.")
                break

    def _build_request_details(self, page: int = 1) -> ScraperRequestDetails:
        base_params = {
            'strana': page,
            'slug': f'{self.listing_type}&slug=byty&slug=praha',
        }

        return ScraperRequestDetails(
            method=RequestMethod.GET,
            url=f'{self.BASE_URL}/_next/data/{self._api_version}/cs/hledani/{self.listing_type}/byty/praha.json',
            params=base_params,
        )

    def _parse_response(self, response: httpx.Response, page: int) -> ScraperPageResponse:
        try:
            data = response.json()['pageProps']['dehydratedState']['queries'][1]['state']['data']

            total_listings = data['pagination']['total']
            page_size = data['pagination']['limit']

            listings = data['results']

            total_pages = self.calculate_number_of_pages(total_listings, page_size)

            return ScraperPageResponse(total_items=total_listings, items=listings, page=page, total_pages=total_pages)
        except (KeyError, json.JSONDecodeError) as e:
            self._logger.error(
                f"Failed to parse response for page {response.url}: {e}. Response text: {response.text[:500]} -> Retrying...")
            raise ScraperParsingError('Failed to parse response')
        except Exception as e:
            self._logger.error(
                f"An unexpected error occurred while parsing page {response.url}: {e}. Response text: {response.text[:500]}... -> Retrying...")
            raise ScraperParsingError('An unexpected error occurred while parsing response')
