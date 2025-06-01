from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(Path(__file__).parent.parent.parent.absolute(), '.env'))

PATH_TO_K3S_YAML_CONFIGS = Path(Path(__file__).absolute().parent.parent.parent, 'output')

PATH_TO_K3S_YAML_CONFIGS.mkdir(exist_ok=True)
