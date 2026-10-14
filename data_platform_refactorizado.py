import copy
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ConfigurationManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, env="DEV"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._load(env)
                    cls._instance = instance
        return cls._instance

    def _load(self, env):
        print(f"[CONFIG] Cargando configuración única para entorno {env}...")
        self.env = env
        self.db_host = "localhost" if env == "DEV" else "prod.db.cenfotec.ac.cr"
        self.db_port = 5432

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._instance = None


class DatabaseConnector(ABC):
    def __init__(self, config):
        self.config = config
        self.connected = False

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def execute_query(self, query):
        pass


class SQLDatabaseConnector(DatabaseConnector):
    def connect(self):
        print(f"[SQL CONNECT] PostgreSQL en {self.config.db_host}:{self.config.db_port}")
        self.connected = True
        return self

    def execute_query(self, query):
        if not self.connected:
            raise RuntimeError("Conector SQL no conectado")
        return f"SQL OK: {query}"


class NoSQLDatabaseConnector(DatabaseConnector):
    def connect(self):
        print(f"[NOSQL CONNECT] MongoDB en {self.config.db_host}")
        self.connected = True
        return self

    def execute_query(self, query):
        if not self.connected:
            raise RuntimeError("Conector NoSQL no conectado")
        return f"NoSQL OK: {query}"


class ConnectorFactory(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def create_connector(self):
        pass

    def get_connection(self):
        return self.create_connector().connect()


class SQLConnectorFactory(ConnectorFactory):
    def create_connector(self):
        return SQLDatabaseConnector(self.config)


class NoSQLConnectorFactory(ConnectorFactory):
    def create_connector(self):
        return NoSQLDatabaseConnector(self.config)


class StorageService(ABC):
    @abstractmethod
    def store(self, name):
        pass


class ComputeService(ABC):
    @abstractmethod
    def run(self, job):
        pass


class AWSS3Storage(StorageService):
    def store(self, name):
        return f"AWS_S3:{name}"


class AWSEC2Compute(ComputeService):
    def run(self, job):
        return f"AWS_EC2:{job}"


class AzureBlobStorage(StorageService):
    def store(self, name):
        return f"Azure_Blob:{name}"


class AzureVMCompute(ComputeService):
    def run(self, job):
        return f"Azure_VM:{job}"


class CloudServiceFactory(ABC):
    @abstractmethod
    def create_storage(self):
        pass

    @abstractmethod
    def create_compute(self):
        pass


class AWSCloudFactory(CloudServiceFactory):
    def create_storage(self):
        return AWSS3Storage()

    def create_compute(self):
        return AWSEC2Compute()


class AzureCloudFactory(CloudServiceFactory):
    def create_storage(self):
        return AzureBlobStorage()

    def create_compute(self):
        return AzureVMCompute()


@dataclass
class ExecutiveReport:
    title: str
    subtitle: str = ""
    author: str = ""
    date: str = ""
    metrics: list = field(default_factory=list)
    charts: list = field(default_factory=list)
    logo: str = ""
    footer: str = ""
    page_numbers: bool = False
    watermark: bool = False
    confidentiality: str = "PUBLICO"
    format_type: str = "PDF"


class ExecutiveReportBuilder:
    def __init__(self):
        self._data = {}

    def add_title(self, title, subtitle=""):
        self._data["title"] = title
        self._data["subtitle"] = subtitle
        return self

    def add_author(self, author, date):
        self._data["author"] = author
        self._data["date"] = date
        return self

    def add_metrics(self, *metrics):
        self._data.setdefault("metrics", []).extend(metrics)
        return self

    def add_charts(self, *charts):
        self._data.setdefault("charts", []).extend(charts)
        return self

    def set_logo(self, logo):
        self._data["logo"] = logo
        return self

    def set_footer(self, footer, page_numbers=True):
        self._data["footer"] = footer
        self._data["page_numbers"] = page_numbers
        return self

    def set_security(self, confidentiality, watermark=True):
        self._data["confidentiality"] = confidentiality
        self._data["watermark"] = watermark
        return self

    def set_format(self, format_type):
        self._data["format_type"] = format_type
        return self

    def build(self):
        if "title" not in self._data:
            raise ValueError("El reporte requiere un título")
        report = ExecutiveReport(**self._data)
        print(f"[REPORT BUILD] {report.format_type}: '{report.title}' con {len(report.metrics)} métricas")
        return report


class ConnectionPrototype:
    def __init__(self, socket, schema_cache):
        self.socket = socket
        self.schema_cache = schema_cache

    @classmethod
    def create_heavy(cls):
        print("[HEAVY SETUP] Inicializando conexión pesada...")
        time.sleep(0.5)
        return cls("active_socket_1092", {"tables": ["ventas", "clientes"], "version": 1})

    def clone(self):
        return copy.deepcopy(self)

    def shallow_clone(self):
        return copy.copy(self)


class DataPlatformService:
    def __init__(self, connector_factory, cloud_factory):
        self.connector_factory = connector_factory
        self.cloud_factory = cloud_factory

    def run_pipeline(self, query, job):
        connection = self.connector_factory.get_connection()
        result = connection.execute_query(query)
        storage = self.cloud_factory.create_storage().store("resultado.parquet")
        compute = self.cloud_factory.create_compute().run(job)
        return {"query": result, "storage": storage, "compute": compute}


if __name__ == "__main__":
    print("=== SISTEMA REFACTORIZADO CON PATRONES CREACIONALES ===")

    config1 = ConfigurationManager("DEV")
    config2 = ConfigurationManager("DEV")
    print(f"¿Misma instancia de config?: {config1 is config2}")

    service = DataPlatformService(SQLConnectorFactory(config1), AWSCloudFactory())
    print(service.run_pipeline("SELECT * FROM ventas", "etl_q3"))

    service_azure = DataPlatformService(NoSQLConnectorFactory(config1), AzureCloudFactory())
    print(service_azure.run_pipeline("db.ventas.find()", "etl_q3"))

    report = (
        ExecutiveReportBuilder()
        .add_title("Reporte Financiero Q3", "Análisis Multi-Cloud")
        .add_author("Estudiante Cenfotec", "2026-10-10")
        .add_metrics("ROI 15%", "CBO < 5")
        .add_charts("ChartBar1")
        .set_logo("Logo.png")
        .set_footer("Pie de página")
        .set_security("CONFIDENCIAL")
        .set_format("PDF")
        .build()
    )
    print("Reporte generado:", report.title)

    base = ConnectionPrototype.create_heavy()
    clon = base.clone()
    clon.schema_cache["version"] = 2
    print(f"Clon independiente: base v{base.schema_cache['version']} / clon v{clon.schema_cache['version']}")
