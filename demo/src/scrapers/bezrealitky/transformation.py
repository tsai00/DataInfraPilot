import re

import pandas as pd

from src.scrapers.base_transformation import BaseTransformation, TransformationError


class BezrealitkyTransformation(BaseTransformation):
    def __init__(self) -> None:
        self._known_disposition_types = {
            'DISP_3_1': '3+1',
            'DISP_2_KK': '2+kk',
            'DISP_3_KK': '3+kk',
            'DISP_2_1': '2+1',
            'DISP_1_KK': '1+kk',
            'UNDEFINED': 'undefined',
            'DISP_1_1': '1+1',
            'DISP_2_IZB': '2',
            'GARSONIERA': 'garsoniera',
            'DISP_4_1': '4+1',
            'DISP_4_KK': '4+kk',
            'DISP_6_1': '6+1',
            'DISP_1_IZB': '1',
            'DISP_3_IZB': '3',
            'DISP_5_1': '5',
            'DISP_4_IZB': '4',
            'OSTATNI': 'other',
            'DISP_5_KK': '5+kk',
            'DISP_7_1': '7+1',
            'DISP_6_KK': '6+kk',
            'DISP_7_KK': '7+kk',
        }

        super().__init__('BezrealitkyTransformation')

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        cols_to_select = [
            'id',
            'uri',
            'disposition',
            'imageAltText',
            'address',
            'surface',
            'price',
            'currency',
            'gps',
            '_scraped_at',
        ]

        cols_to_drop = ['gps', 'currency', 'address']

        map_old_new_names = {
            'id': 'internal_id',
            'uri': 'url',
            'imageAltText': 'name',
            'surface': 'area',
        }

        df_transformed = (
            df.pipe(self.select_columns, cols_to_select)
            .pipe(self.map_values_with_validation, 'disposition', self._known_disposition_types)
            .pipe(self.filter_data)
            .pipe(self.add_new_columns)
            .pipe(self.rename_columns, map_old_new_names)
            .pipe(self.drop_columns, cols_to_drop)
        )

        return df_transformed

    @staticmethod
    def _parse_address(row: dict) -> tuple[str | None, str, str, str | None]:
        # Note: the following parsing function is only intended for Czech addresses
        # (~ apply after currency filtering)
        address = row['address']
        address_elements = re.split(r', | - ', address)

        if len(address_elements) == 2:
            city, city_part = address_elements
            street, region = None, None
        elif len(address_elements) == 3:
            street, city, city_part = address_elements

            region = 'Hlavní město Praha' if city == 'Praha' else None
        elif len(address_elements) == 4:
            street, city, city_part, region = address_elements
        else:
            raise TransformationError(f'Unknown value type for address: {address}')

        return region, city, city_part, street

    def add_new_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy()

        df_copy['uri'] = 'https://www.bezrealitky.cz/nemovitosti-byty-domy/' + df_copy['uri'].astype(str)

        df_copy[['region', 'city', 'city_part', 'street']] = df_copy.apply(
            self._parse_address, axis=1, result_type='expand'
        )

        df_copy['lat'] = df_copy['gps'].apply(self.get_dict_element, dict_key='lat').astype(float)
        df_copy['lon'] = df_copy['gps'].apply(self.get_dict_element, dict_key='lng').astype(float)

        return df_copy

    def filter_data(self, df: pd.DataFrame) -> pd.DataFrame:
        self._logger.info(f'Number of records before filtering: {len(df)}')

        df_filtered = df[(df['currency'] == 'CZK')]

        self._logger.info(f'Number of records after filtering: {len(df_filtered)}')

        return df_filtered
