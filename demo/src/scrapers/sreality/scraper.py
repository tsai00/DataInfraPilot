import json
from typing import Literal

import httpx

from src.scrapers.base_scraper import (
    BaseScraper,
    RequestMethod,
    ScraperError,
    ScraperPageResponse,
    ScraperParsingError,
    ScraperRequestDetails,
)


class SrealityScraper(BaseScraper):
    BASE_URL = 'https://www.sreality.cz'

    def __init__(self, listing_type: Literal['rent', 'sale']) -> None:
        if listing_type == 'rent':
            self.listing_type = 'pronajem'
        elif listing_type == 'sale':
            self.listing_type = 'prodej'
        else:
            raise ValueError(f'Unknown listing type: {listing_type}')

        self._api_version = '1.0.359'  # Start API version (will be increased dynamically if needed)

        disposition_batches = [
            {'velikost': '1+1,1+kk,3+1,4+1,4+kk,5+1,5+kk,6-a-vice,atypicky,pokoj'},
            {'velikost': '2+1,2+kk,3+kk'},
        ]

        super().__init__('SrealityScraper', 22, disposition_batches, 1)

        self._check_api_version_availability()

        self._logger.info(
            f'Scraping {listing_type} listings with {len(self.dynamic_params_options)} custom "velikost" batches.'
        )
        self._logger.debug(f'Dynamic parameter combinations: {self.dynamic_params_options}')

    def _check_api_version_availability(self) -> None:
        self._logger.info(f'Checking availability of API version {self._api_version}...')
        max_attempts = 50
        valid_api_version = None

        while valid_api_version is None and max_attempts > 0:
            response = self.send_get_request(
                f'{self.BASE_URL}/_next/data/{self._api_version}/cs/hledani/{self.listing_type}/byty/praha.json'
            )
            if response.status_code == 404:
                next_api_version = f'1.0.{int(self._api_version.split(".")[-1]) + 1}'
                self._logger.warning(f'API version {self._api_version} is not available. Will try {next_api_version}.')

                self._api_version = next_api_version
                max_attempts -= 1
            else:
                self._logger.info(f'API version {self._api_version} is available and will be used.')
                break

    def _build_request_details(self, page: int = 1, dynamic_params: dict | None = None) -> ScraperRequestDetails:
        base_params = {
            'strana': page,
            'slug': f'{self.listing_type}&slug=byty',
        }

        if dynamic_params and 'velikost' in dynamic_params:
            base_params['velikost'] = dynamic_params['velikost']

        return ScraperRequestDetails(
            method=RequestMethod.GET,
            url=f'{self.BASE_URL}/_next/data/{self._api_version}/cs/hledani/{self.listing_type}/byty.json',
            params=base_params,
        )

    def _parse_response(self, response: httpx.Response, page: int) -> ScraperPageResponse:
        try:
            data = response.json()['pageProps']['dehydratedState']['queries'][1]['state']['data']

            total_listings = data['pagination']['total']
            page_size = data['pagination']['limit']

            listings = data['results']

            if total_listings > 9988:
                raise ScraperError(
                    f'Sreality only show max 454 pages (9988 listings). '
                    f'Current search returned {total_listings}. Please update input parameters.'
                )

            total_pages = self.calculate_number_of_pages(total_listings, page_size)

            return ScraperPageResponse(total_items=total_listings, items=listings, page=page, total_pages=total_pages)
        except (KeyError, json.JSONDecodeError) as e:
            self._logger.exception(
                f'Failed to parse response for page {response.url}. Response text: {response.text[:500]} -> Retrying...'
            )
            raise ScraperParsingError('Failed to parse response') from e
        except Exception as e:
            self._logger.exception(
                f'An unexpected error occurred while parsing page {response.url}. '
                f'Response text: {response.text[:500]}... -> Retrying...'
            )
            raise ScraperParsingError('An unexpected error occurred while parsing response') from e
