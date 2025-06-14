import numpy as np
import pandas as pd

from src.demo.scrapers.base_transformation import BaseTransformation


class SrealityTransformation(BaseTransformation):
    def __init__(self):
        super().__init__('SrealityTransformation')

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        cols_to_select = [
            'name',
            'id',
            'categorySubCb',
            'categoryTypeCb',
            'locality',
            'priceCzk',
            'priceUnitCb',
            '_scraped_at'
        ]

        cols_to_explode = ['locality']
        cols_to_drop = [
            'categorySubCb', 'priceUnitCb', 'locality.citySeoName', 'locality.cityPartSeoName',
            'locality.country', 'locality.countryId', 'locality.districtId', 'locality.districtSeoName',
            'locality.entityType', 'locality.geoHash', 'locality.inaccuracyType', 'locality.municipality',
            'locality.municipalityId', 'locality.municipalitySeoName', 'locality.quarter', 'locality.quarterId',
            'locality.regionId', 'locality.regionSeoName', 'locality.streetId', 'locality.streetSeoName',
            'locality.ward', 'locality.wardId', 'locality.wardSeoName', 'locality.zip', 'categoryTypeCb',
            'locality.streetNumber', 'locality.houseNumber', 'locality.district'
        ]

        map_old_new_names = {
            'id': 'internal_id',
            'priceCzk': 'price',
            'locality.city': 'city',
            'locality.cityPart': 'city_part',
            'locality.latitude': 'lat',
            'locality.longitude': 'lon',
            'locality.region': 'region',
            'locality.street': 'street',
        }

        df_transformed = (
            df
            .pipe(self.select_columns, cols_to_select)
            .pipe(self.convert_columns)
            .pipe(self.explode_columns, cols_to_explode)
            .pipe(self.add_new_columns)
            .pipe(self.filter_data)
            .pipe(self.drop_columns, cols_to_drop)
            .pipe(self.rename_columns, map_old_new_names)
        )

        return df_transformed

    def convert_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy()

        df_copy['locality'] = df_copy['locality'].apply(self.get_dict_element)

        return df_copy

    def _construct_url(self, row: dict):
        disposition = row['disposition']
        city = row['locality.citySeoName']
        district = row['locality.cityPartSeoName']
        street = row['locality.streetSeoName']
        internal_id = row['id']
        category = row['categoryTypeCb']

        return f'https://www.sreality.cz/detail/{category}/byt/{disposition}/{city}-{district}-{street}/{internal_id}'

    def add_new_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy()

        df_copy['area'] = df_copy['name'].str.extract(r"(\d{1,}) m²").astype(int)

        df_copy['priceUnitCb'] = df_copy['priceUnitCb'].apply(self.get_dict_element, dict_key='name')

        df_copy['categoryTypeCb'] = df_copy['categoryTypeCb'].apply(self.get_dict_element, dict_key='name').str.lower()
        df_copy['categoryTypeCb'] = df_copy['categoryTypeCb'].apply(self.normalize_string)

        df_copy['disposition'] = df_copy['categorySubCb'].apply(self.get_dict_element, dict_key='name').str.lower()
        df_copy['disposition'] = df_copy['disposition'].apply(self.normalize_string)

        df_copy['url'] = df_copy.apply(lambda row: self._construct_url(row), axis=1)

        df_copy['priceCzk'] = np.where(df_copy['priceUnitCb'] == 'za m²', df_copy['priceCzk'] * df_copy['area'], df_copy['priceCzk'])

        return df_copy

    def filter_data(self, df: pd.DataFrame) -> pd.DataFrame:
        self._logger.info(f'Number of records before filtering: {len(df)}')

        price_period_exclude = ['za měsíc'] if df['categoryTypeCb'].tolist()[0] == 'prodej' else []

        df_filtered = df[
            (~df['priceUnitCb'].isin(price_period_exclude))
        ]

        self._logger.info(f'Number of records after filtering: {len(df_filtered)}')

        return df_filtered
