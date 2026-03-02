"""Тесты для parser_1c: BSLParser, MetadataParser, ConfigurationScanner."""
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from parser_1c import BSLParser, MetadataParser, ConfigurationScanner


class TestBSLParserParseModule:
    """Тесты парсинга BSL-модулей."""

    def test_parses_procedure_and_function(self, sample_bsl_file):
        chunks = BSLParser.parse_module(sample_bsl_file)
        names = [c["method_name"] for c in chunks]
        assert "ОбработкаЗаполнения" in names
        assert "ПолучитьДанные" in names
        assert "ОбработатьНаСервере" in names

    def test_detects_export(self, sample_bsl_file):
        chunks = BSLParser.parse_module(sample_bsl_file)
        by_name = {c["method_name"]: c for c in chunks}
        assert by_name["ПолучитьДанные"]["is_export"] is True
        assert by_name["ОбработкаЗаполнения"]["is_export"] is False

    def test_extracts_comments(self, sample_bsl_file):
        chunks = BSLParser.parse_module(sample_bsl_file)
        filling = next(c for c in chunks if c["method_name"] == "ОбработкаЗаполнения")
        assert len(filling["comments"]) == 2
        assert "Комментарий к процедуре" in filling["comments"][0]

    def test_extracts_params(self, sample_bsl_file):
        chunks = BSLParser.parse_module(sample_bsl_file)
        fn = next(c for c in chunks if c["method_name"] == "ПолучитьДанные")
        assert "Параметр1" in fn["params"]
        assert "Параметр2" in fn["params"]

    def test_method_type_capitalized(self, sample_bsl_file):
        chunks = BSLParser.parse_module(sample_bsl_file)
        by_name = {c["method_name"]: c for c in chunks}
        assert by_name["ОбработкаЗаполнения"]["method_type"] in ("Процедура",)
        assert by_name["ПолучитьДанные"]["method_type"] in ("Функция",)

    def test_signature_contains_name_and_params(self, sample_bsl_file):
        chunks = BSLParser.parse_module(sample_bsl_file)
        fn = next(c for c in chunks if c["method_name"] == "ПолучитьДанные")
        assert "ПолучитьДанные" in fn["signature"]
        assert "Параметр1" in fn["signature"]

    def test_empty_file_returns_empty_list(self, empty_bsl_file):
        chunks = BSLParser.parse_module(empty_bsl_file)
        assert chunks == []

    def test_module_without_procedures_returns_module_chunk(self, module_only_bsl_file):
        chunks = BSLParser.parse_module(module_only_bsl_file)
        assert len(chunks) == 1
        assert chunks[0]["method_type"] == "Module"
        assert chunks[0]["method_name"] == "ModuleCode"

    def test_nonexistent_file_returns_empty(self, tmp_path):
        fake = tmp_path / "nonexistent.bsl"
        chunks = BSLParser.parse_module(fake)
        assert chunks == []

    def test_file_path_stored_in_chunk(self, sample_bsl_file):
        chunks = BSLParser.parse_module(sample_bsl_file)
        assert all(c["file_path"] == str(sample_bsl_file) for c in chunks)

    def test_preprocessor_directives_removed(self, tmp_path):
        bsl = tmp_path / "Preprocessor.bsl"
        bsl.write_text(
            """\
#Если Сервер Тогда
Процедура Тест() Экспорт
    Возврат;
КонецПроцедуры
#КонецЕсли
""",
            encoding="utf-8-sig",
        )
        chunks = BSLParser.parse_module(bsl)
        assert len(chunks) == 1
        assert chunks[0]["method_name"] == "Тест"


class TestBSLParserExtractMetadataReferences:
    """Тесты извлечения ссылок на метаданные из кода."""

    def test_extracts_catalogs(self):
        code = 'Справочники.Номенклатура.НайтиПоНаименованию("Тест");'
        refs = BSLParser.extract_metadata_references_from_code(code)
        assert ("Catalogs", "Номенклатура") in refs

    def test_extracts_documents(self):
        code = "Документы.РеализацияТоваровУслуг.СоздатьДокумент();"
        refs = BSLParser.extract_metadata_references_from_code(code)
        assert ("Documents", "РеализацияТоваровУслуг") in refs

    def test_extracts_information_registers(self):
        code = "РегистрыСведений.КурсыВалют.СоздатьМенеджерЗаписи();"
        refs = BSLParser.extract_metadata_references_from_code(code)
        assert ("InformationRegisters", "КурсыВалют") in refs

    def test_multiple_refs_no_duplicates(self):
        code = """
        Справочники.Номенклатура.НайтиПоНаименованию("A");
        Справочники.Номенклатура.НайтиПоКоду("B");
        Документы.Заказ.СоздатьДокумент();
        """
        refs = BSLParser.extract_metadata_references_from_code(code)
        assert len(refs) == 2
        types = [r[0] for r in refs]
        assert "Catalogs" in types
        assert "Documents" in types

    def test_no_refs_in_plain_text(self):
        code = "Сообщить('Привет мир');"
        refs = BSLParser.extract_metadata_references_from_code(code)
        assert refs == []

    def test_case_insensitive(self):
        code = "справочники.Тест.НайтиПоНаименованию();"
        refs = BSLParser.extract_metadata_references_from_code(code)
        assert len(refs) == 1

    def test_all_collection_types(self):
        code = """
        Справочники.A.F();
        Документы.B.F();
        РегистрыСведений.C.F();
        РегистрыНакопления.D.F();
        РегистрыБухгалтерии.E.F();
        ПланыСчетов.F.F();
        Перечисления.G.F();
        ОбщиеМодули.H.F();
        Обработки.I.F();
        Отчеты.J.F();
        """
        refs = BSLParser.extract_metadata_references_from_code(code)
        assert len(refs) == 10


class TestMetadataParser:
    """Тесты парсинга XML метаданных."""

    def test_parses_catalog_xml(self, sample_config_tree):
        xml_path = sample_config_tree / "Catalogs" / "Номенклатура" / "Номенклатура.xml"
        result = MetadataParser.parse_object_metadata(xml_path)
        assert result is not None
        assert result["name"] == "Номенклатура"
        assert result["attributes_count"] == 2
        attr_names = [a["name"] for a in result["attributes"]]
        assert "Артикул" in attr_names
        assert "Вес" in attr_names

    def test_detects_modules(self, sample_config_tree):
        xml_path = sample_config_tree / "Catalogs" / "Номенклатура" / "Номенклатура.xml"
        result = MetadataParser.parse_object_metadata(xml_path)
        assert "ManagerModule" in result["has_modules"]

    def test_invalid_xml_returns_none(self, tmp_path):
        bad_xml = tmp_path / "bad.xml"
        bad_xml.write_text("not xml at all", encoding="utf-8")
        result = MetadataParser.parse_object_metadata(bad_xml)
        assert result is None

    def test_nonexistent_xml_returns_none(self, tmp_path):
        fake = tmp_path / "nonexistent.xml"
        result = MetadataParser.parse_object_metadata(fake)
        assert result is None

    def test_synonym_extracted(self, sample_config_tree):
        xml_path = sample_config_tree / "Catalogs" / "Номенклатура" / "Номенклатура.xml"
        result = MetadataParser.parse_object_metadata(xml_path)
        assert result["synonym"] == "Номенклатура"


class TestConfigurationScanner:
    """Тесты сканера конфигурации."""

    def test_scan_all_modules(self, sample_config_tree):
        scanner = ConfigurationScanner(sample_config_tree)
        modules = scanner.scan_all_modules()
        assert len(modules) >= 1
        file_path, obj_full_name, methods = modules[0]
        assert "Catalogs" in obj_full_name
        assert len(methods) >= 1

    def test_scan_all_metadata(self, sample_config_tree):
        scanner = ConfigurationScanner(sample_config_tree)
        metadata = scanner.scan_all_metadata()
        assert len(metadata) >= 1
        names = [m["name"] for m in metadata]
        assert "Номенклатура" in names

    def test_scan_empty_config(self, tmp_path):
        empty = tmp_path / "empty_config"
        empty.mkdir()
        scanner = ConfigurationScanner(empty)
        assert scanner.scan_all_modules() == []
        assert scanner.scan_all_metadata() == []
        assert scanner.scan_all_forms() == []
