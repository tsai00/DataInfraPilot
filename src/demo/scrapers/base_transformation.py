import ast
import unicodedata
from abc import ABC, abstractmethod
from typing import Any
from src.demo.utils import setup_logger
import pandas as pd


class TransformationError(Exception):
    pass


class BaseTransformation(ABC):
    def __init__(self, name: str):
        self.name = name

        self._logger = setup_logger(name)

        self._logger.info(f'Starting {name} transformation')

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        pass

    @staticmethod
    def select_columns(df: pd.DataFrame, cols_to_select: list[str]) -> pd.DataFrame:
        return df.copy()[cols_to_select]

    @staticmethod
    def rename_columns(df: pd.DataFrame, map_old_new_names: dict[str, str]) -> pd.DataFrame:
        return df.copy().rename(columns=map_old_new_names)

    @staticmethod
    def drop_columns(df: pd.DataFrame, cols_to_drop: list[str]) -> pd.DataFrame:
        return df.copy().drop(columns=cols_to_drop)

    @staticmethod
    def get_dict_element(dict_element: dict | str, dict_key: str | None = None) -> dict | Any:
        loaded_dict = ast.literal_eval(dict_element) if isinstance(dict_element, str) else dict_element
        return loaded_dict.get(dict_key) if dict_key is not None else loaded_dict

    @staticmethod
    def explode_columns(df: pd.DataFrame, columns: list[str], keep_original_column: bool = False) -> pd.DataFrame:
        df_new = df.copy()

        for col in columns:
            df_tmp = pd.json_normalize(df_new[col].astype(object)).add_prefix(f'{col}.')
            df_new = pd.concat([df_new.reset_index(drop=True), df_tmp.reset_index(drop=True)], axis=1)

        return df_new if keep_original_column else df_new.drop(columns=columns)

    @staticmethod
    def normalize_string(string):
        return ''.join(c for c in unicodedata.normalize('NFKD', string) if not unicodedata.combining(c))

    @staticmethod
    def map_values_with_validation(df: pd.DataFrame, column: str, mapping: dict) -> pd.DataFrame:
        unknown_values = set(df[column].unique().tolist()).difference(set(mapping.keys()))
        if unknown_values:
            raise TransformationError(f'There are unmapped values in column {column}: {unknown_values}')

        df[column] = df[column].map(mapping)

        return df
