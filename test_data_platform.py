import threading
import unittest
from unittest.mock import MagicMock, patch

from data_platform_refactorizado import (
    AWSCloudFactory,
    AWSEC2Compute,
    AWSS3Storage,
    AzureBlobStorage,
    AzureCloudFactory,
    AzureVMCompute,
    CloudServiceFactory,
    ConfigurationManager,
    ConnectionPrototype,
    ConnectorFactory,
    DataPlatformService,
    ExecutiveReportBuilder,
    NoSQLConnectorFactory,
    NoSQLDatabaseConnector,
    SQLConnectorFactory,
    SQLDatabaseConnector,
)


class TestSingleton(unittest.TestCase):
    def setUp(self):
        ConfigurationManager.reset()

    def test_misma_instancia(self):
        self.assertIs(ConfigurationManager("DEV"), ConfigurationManager("PROD"))

    def test_configuracion_se_carga_una_vez(self):
        with patch.object(ConfigurationManager, "_load", autospec=True) as load:
            ConfigurationManager("DEV")
            ConfigurationManager("DEV")
            self.assertEqual(load.call_count, 1)

    def test_thread_safe(self):
        instancias = []
        hilos = [threading.Thread(target=lambda: instancias.append(ConfigurationManager("DEV"))) for _ in range(50)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        self.assertEqual(len({id(i) for i in instancias}), 1)

    def test_host_por_entorno(self):
        self.assertEqual(ConfigurationManager("PROD").db_host, "prod.db.cenfotec.ac.cr")


class TestFactoryMethod(unittest.TestCase):
    def setUp(self):
        self.config = MagicMock(db_host="localhost", db_port=5432)

    def test_sql_factory(self):
        conn = SQLConnectorFactory(self.config).get_connection()
        self.assertIsInstance(conn, SQLDatabaseConnector)
        self.assertTrue(conn.connected)

    def test_nosql_factory(self):
        conn = NoSQLConnectorFactory(self.config).get_connection()
        self.assertIsInstance(conn, NoSQLDatabaseConnector)
        self.assertIn("NoSQL OK", conn.execute_query("find"))

    def test_query_sin_conexion_falla(self):
        with self.assertRaises(RuntimeError):
            SQLConnectorFactory(self.config).create_connector().execute_query("SELECT 1")

    def test_factory_abstracta_no_instanciable(self):
        with self.assertRaises(TypeError):
            ConnectorFactory(self.config)


class TestAbstractFactory(unittest.TestCase):
    def test_familia_aws(self):
        f = AWSCloudFactory()
        self.assertIsInstance(f.create_storage(), AWSS3Storage)
        self.assertIsInstance(f.create_compute(), AWSEC2Compute)

    def test_familia_azure(self):
        f = AzureCloudFactory()
        self.assertIsInstance(f.create_storage(), AzureBlobStorage)
        self.assertIsInstance(f.create_compute(), AzureVMCompute)

    def test_factory_abstracta_no_instanciable(self):
        with self.assertRaises(TypeError):
            CloudServiceFactory()


class TestBuilder(unittest.TestCase):
    def test_reporte_completo(self):
        r = (
            ExecutiveReportBuilder()
            .add_title("Q3", "Multi-Cloud")
            .add_metrics("ROI 15%", "CBO < 5")
            .add_charts("ChartBar1")
            .set_footer("Pie")
            .set_security("CONFIDENCIAL")
            .build()
        )
        self.assertEqual(r.title, "Q3")
        self.assertEqual(len(r.metrics), 2)
        self.assertTrue(r.page_numbers)
        self.assertEqual(r.confidentiality, "CONFIDENCIAL")

    def test_valores_por_defecto(self):
        r = ExecutiveReportBuilder().add_title("Mínimo").build()
        self.assertEqual(r.format_type, "PDF")
        self.assertEqual(r.metrics, [])

    def test_sin_titulo_falla(self):
        with self.assertRaises(ValueError):
            ExecutiveReportBuilder().add_metrics("ROI").build()


class TestPrototype(unittest.TestCase):
    def setUp(self):
        with patch("data_platform_refactorizado.time.sleep"):
            self.base = ConnectionPrototype.create_heavy()

    def test_clone_no_repite_inicializacion(self):
        with patch.object(ConnectionPrototype, "create_heavy") as heavy:
            self.base.clone()
            heavy.assert_not_called()

    def test_deep_clone_independiente(self):
        clon = self.base.clone()
        clon.schema_cache["version"] = 2
        self.assertEqual(self.base.schema_cache["version"], 1)
        self.assertIsNot(clon, self.base)

    def test_shallow_clone_comparte_cache(self):
        clon = self.base.shallow_clone()
        self.assertIs(clon.schema_cache, self.base.schema_cache)


class TestServicioConMocks(unittest.TestCase):
    def test_pipeline_desacoplado(self):
        connector_factory = MagicMock()
        connector_factory.get_connection.return_value.execute_query.return_value = "OK"
        cloud_factory = MagicMock()
        cloud_factory.create_storage.return_value.store.return_value = "STORE"
        cloud_factory.create_compute.return_value.run.return_value = "RUN"

        result = DataPlatformService(connector_factory, cloud_factory).run_pipeline("q", "job")

        self.assertEqual(result, {"query": "OK", "storage": "STORE", "compute": "RUN"})
        connector_factory.get_connection.assert_called_once()

    def test_integracion_azure_nosql(self):
        ConfigurationManager.reset()
        service = DataPlatformService(NoSQLConnectorFactory(ConfigurationManager("DEV")), AzureCloudFactory())
        result = service.run_pipeline("find", "etl")
        self.assertTrue(result["storage"].startswith("Azure_Blob"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
