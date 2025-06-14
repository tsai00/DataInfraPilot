from src.api.routers.cluster import router as cluster_router
from src.api.routers.application import router as application_router
from src.api.routers.volume import router as volume_router
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utils.tasks import repeat_every
import logging
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.apps.airflow_application import AirflowApplication, AirflowConfig
from src.core.apps.application_factory import ApplicationFactory, ApplicationMetadata
from src.core.apps.grafana_application import GrafanaApplication, GrafanaConfig
from src.core.apps.spark_application import SparkApplication, SparkConfig

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
    logging.error(f"{request}: {exc_str}")
    content = {'status_code': 10422, 'message': exc_str, 'data': None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


@app.on_event("startup")
async def register_applications():
    print("Registering applications with ApplicationFactory...")

    ApplicationFactory.register_application(
        app_id=1,
        app_class=AirflowApplication,
        config_class=AirflowConfig
    )
    ApplicationFactory.register_application(
        app_id=2,
        app_class=GrafanaApplication,
        config_class=GrafanaConfig,
        metadata=ApplicationMetadata(username_key='admin-user', password_key='admin-password')
    )
    ApplicationFactory.register_application(
        app_id=3,
        app_class=SparkApplication,
        config_class=SparkConfig,
    )

    print("Applications registration complete.")


@app.on_event("startup")
@repeat_every(seconds=60)
def remove_expired_tokens_task() -> None:
    print('Debug periodic task')


app.include_router(cluster_router)
app.include_router(application_router)
app.include_router(volume_router)
