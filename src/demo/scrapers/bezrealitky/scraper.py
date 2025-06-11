import json
from typing import Literal

import httpx

from src.demo.scrapers.base_scraper import BaseScraper, ScraperPageResponse, ScraperRequestDetails, RequestMethod, \
    ScraperParsingError


class BezrealitkyScraper(BaseScraper):
    BASE_URL = 'https://api.bezrealitky.cz/graphql/'    # Keep trailing slash, otherwise will get 404

    def __init__(self, listing_type: Literal['rent', 'sale']):
        if listing_type == 'rent':
            self.listing_type = 'PRONAJEM'
        elif listing_type == 'sale':
            self.listing_type = 'PRODEJ'
        else:
            raise ValueError(f'Unknown listing type: {listing_type}')

        super().__init__('BezrealitkyScraper', 15, 0)

        self._logger.info(f'Scraping {listing_type} listings')

    def _build_request_details(self, page: int = 0, dynamic_params: dict | None = None) -> ScraperRequestDetails:
        json_data = {
            "operationName": "AdvertList",
            "variables": {
                "limit": self.page_size,
                "offset": self.page_size * page,
                "order": "TIMEORDER_DESC",
                "locale": "CS",
                "offerType": [
                    self.listing_type
                ],
                "estateType": [
                    "BYT"
                ],
                "regionOsmIds": [],
                "location": "exact",
                "currency": "CZK",
                "construction": []
            },
            "query": f"query AdvertList($locale: Locale!, $estateType: [EstateType], $offerType: [OfferType], $disposition: [Disposition], $landType: [LandType], $region: ID, $regionOsmIds: [ID], $limit: Int = {self.page_size}, $offset: Int = {self.page_size * page}, $order: ResultOrder = TIMEORDER_DESC, $petFriendly: Boolean, $balconyFrom: Float, $balconyTo: Float, $loggiaFrom: Float, $loggiaTo: Float, $terraceFrom: Float, $terraceTo: Float, $cellarFrom: Float, $cellarTo: Float, $frontGardenFrom: Float, $frontGardenTo: Float, $parking: Boolean, $garage: Boolean, $lift: Boolean, $ownership: [Ownership], $condition: [Condition], $construction: [Construction], $equipped: [Equipped], $priceFrom: Int, $priceTo: Int, $surfaceFrom: Int, $surfaceTo: Int, $surfaceLandFrom: Int, $surfaceLandTo: Int, $advertId: [ID], $roommate: Boolean, $includeImports: Boolean, $includeShortTerm: Boolean, $boundaryPoints: [GPSPointInput], $discountedOnly: Boolean, $discountedOnlyByEstimate: Boolean, $barrierFree: Boolean, $polygonBuffer: Int, $availableFrom: DateTime, $importType: AdvertImportType, $currency: Currency, $searchPriceWithCharges: Boolean, $lowEnergy: Boolean) {{\n  listAdverts(\n    offerType: $offerType\n    estateType: $estateType\n    disposition: $disposition\n    landType: $landType\n    limit: $limit\n    regionId: $region\n    regionOsmIds: $regionOsmIds\n    offset: $offset\n    order: $order\n    petFriendly: $petFriendly\n    balconySurfaceFrom: $balconyFrom\n    balconySurfaceTo: $balconyTo\n    loggiaSurfaceFrom: $loggiaFrom\n    loggiaSurfaceTo: $loggiaTo\n    terraceSurfaceFrom: $terraceFrom\n    terraceSurfaceTo: $terraceTo\n    cellarSurfaceFrom: $cellarFrom\n    cellarSurfaceTo: $cellarTo\n    frontGardenSurfaceFrom: $frontGardenFrom\n    frontGardenSurfaceTo: $frontGardenTo\n    parking: $parking\n    garage: $garage\n    lift: $lift\n    ownership: $ownership\n    condition: $condition\n    construction: $construction\n    equipped: $equipped\n    priceFrom: $priceFrom\n    priceTo: $priceTo\n    surfaceFrom: $surfaceFrom\n    surfaceTo: $surfaceTo\n    surfaceLandFrom: $surfaceLandFrom\n    surfaceLandTo: $surfaceLandTo\n    ids: $advertId\n    roommate: $roommate\n    includeImports: $includeImports\n    includeShortTerm: $includeShortTerm\n    boundaryPoints: $boundaryPoints\n    discountedOnly: $discountedOnly\n    discountedOnlyByEstimate: $discountedOnlyByEstimate\n    polygonBuffer: $polygonBuffer\n    barrierFree: $barrierFree\n    availableFrom: $availableFrom\n    importType: $importType\n    currency: $currency\n    searchPriceWithCharges: $searchPriceWithCharges\n    lowEnergy: $lowEnergy\n  ) {{\n    list {{\n      id\n      uri\n      estateType\n      offerType\n      disposition\n      landType\n      imageAltText(locale: $locale)\n      mainImage {{\n        id\n        url(filter: RECORD_THUMB)\n        __typename\n      }}\n      publicImages(limit: 3) {{\n        id\n        size(filter: RECORD_MAIN) {{\n          height\n          width\n          __typename\n        }}\n        url(filter: RECORD_MAIN)\n        type\n        originalImage {{\n          id\n          __typename\n        }}\n        __typename\n      }}\n      address(locale: $locale)\n      surface\n      surfaceLand\n      tags(locale: $locale)\n      price\n      charges\n      currency\n      petFriendly\n      reserved\n      highlighted\n      roommate\n      project {{\n        id\n        __typename\n      }}\n      gps {{\n        lat\n        lng\n        __typename\n      }}\n      mortgageData(locale: $locale) {{\n        rateLow\n        rateHigh\n        loan\n        years\n        __typename\n      }}\n      originalPrice\n      isDiscounted\n      nemoreport {{\n        id\n        status\n        timeCreated\n        __typename\n      }}\n      isNew\n      videos {{\n        id\n        previewUrl\n        status\n        __typename\n      }}\n      links {{\n        id\n        url\n        type\n        status\n        __typename\n      }}\n      type\n      dataJson\n      shortTerm\n      __typename\n    }}\n    totalCount\n    __typename\n  }}\n  actionList: listAdverts(\n    offerType: $offerType\n    estateType: $estateType\n    disposition: $disposition\n    landType: $landType\n    regionId: $region\n    regionOsmIds: $regionOsmIds\n    order: $order\n    petFriendly: $petFriendly\n    balconySurfaceFrom: $balconyFrom\n    balconySurfaceTo: $balconyTo\n    loggiaSurfaceFrom: $loggiaFrom\n    loggiaSurfaceTo: $loggiaTo\n    terraceSurfaceFrom: $terraceFrom\n    terraceSurfaceTo: $terraceTo\n    cellarSurfaceFrom: $cellarFrom\n    cellarSurfaceTo: $cellarTo\n    parking: $parking\n    garage: $garage\n    lift: $lift\n    ownership: $ownership\n    condition: $condition\n    construction: $construction\n    equipped: $equipped\n    priceFrom: $priceFrom\n    priceTo: $priceTo\n    surfaceFrom: $surfaceFrom\n    surfaceTo: $surfaceTo\n    surfaceLandFrom: $surfaceLandFrom\n    surfaceLandTo: $surfaceLandTo\n    ids: $advertId\n    roommate: $roommate\n    includeImports: $includeImports\n    includeShortTerm: $includeShortTerm\n    boundaryPoints: $boundaryPoints\n    discountedOnly: true\n    limit: 3\n    availableFrom: $availableFrom\n    searchPriceWithCharges: $searchPriceWithCharges\n    lowEnergy: $lowEnergy\n  ) {{\n    totalCount\n    __typename\n  }}\n}}"
        }

        return ScraperRequestDetails(
            method=RequestMethod.POST,
            url=self.BASE_URL,
            json=json_data,
        )

    def _parse_response(self, response: httpx.Response, page: int) -> ScraperPageResponse:
        try:
            data = response.json()['data']['listAdverts']

            total_listings = data['totalCount']
            listings = data['list']

            total_pages = self.calculate_number_of_pages(total_listings)

            return ScraperPageResponse(total_items=total_listings, items=listings, page=page, total_pages=total_pages)
        except (KeyError, json.JSONDecodeError) as e:
            self._logger.error(
                f"Failed to parse response for page {response.url}: {e}. Response text: {response.text} -> Retrying...")
            raise ScraperParsingError('Failed to parse response')
        except Exception as e:
            self._logger.error(
                f"An unexpected error occurred while parsing page {response.url}: {e}. Response text: {response.text[:500]}... -> Retrying...")
            raise ScraperParsingError('An unexpected error occurred while parsing response')
