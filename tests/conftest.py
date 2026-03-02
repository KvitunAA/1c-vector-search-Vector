"""Общие фикстуры для тестов."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("CONFIG_PATH", "")
os.environ.setdefault("PROJECT_PROFILE", "default")
os.environ.setdefault("LOG_LEVEL", "WARNING")


@pytest.fixture
def tmp_dir(tmp_path):
    """Временная директория для тестов."""
    return tmp_path


@pytest.fixture
def sample_bsl_file(tmp_path):
    """Создаёт временный BSL-файл с процедурами и функциями."""
    bsl = tmp_path / "TestModule.bsl"
    bsl.write_text(
        """\
// Комментарий к процедуре
// Вторая строка комментария
Процедура ОбработкаЗаполнения(ДанныеЗаполнения, СтандартнаяОбработка)

    Если ДанныеЗаполнения = Неопределено Тогда
        Возврат;
    КонецЕсли;

КонецПроцедуры

Функция ПолучитьДанные(Параметр1, Параметр2) Экспорт

    Результат = Справочники.Номенклатура.НайтиПоНаименованию(Параметр1);
    Возврат Результат;

КонецФункции

&НаСервере
Процедура ОбработатьНаСервере()

    Документы.РеализацияТоваровУслуг.СоздатьДокумент();
    РегистрыСведений.КурсыВалют.СоздатьМенеджерЗаписи();

КонецПроцедуры
""",
        encoding="utf-8-sig",
    )
    return bsl


@pytest.fixture
def empty_bsl_file(tmp_path):
    """Пустой BSL-файл."""
    bsl = tmp_path / "Empty.bsl"
    bsl.write_text("", encoding="utf-8-sig")
    return bsl


@pytest.fixture
def module_only_bsl_file(tmp_path):
    """BSL-файл без процедур/функций (только код модуля)."""
    bsl = tmp_path / "ModuleCode.bsl"
    bsl.write_text(
        "Перем глМояПеременная;\nглМояПеременная = 42;\n",
        encoding="utf-8-sig",
    )
    return bsl


@pytest.fixture
def sample_config_tree(tmp_path):
    """Создаёт минимальное дерево конфигурации 1С."""
    config_root = tmp_path / "config"

    catalogs = config_root / "Catalogs" / "Номенклатура"
    catalogs.mkdir(parents=True)
    (catalogs / "Номенклатура.xml").write_text(
        """\
<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses"
                xmlns:v8="http://v8.1c.ru/8.3/MDClasses">
  <Catalog>
    <v8:name>Номенклатура</v8:name>
    <v8:synonym>
      <v8:item>
        <v8:presentation>Номенклатура</v8:presentation>
      </v8:item>
    </v8:synonym>
    <v8:attributes>
      <v8:name>Артикул</v8:name>
    </v8:attributes>
    <v8:attributes>
      <v8:name>Вес</v8:name>
    </v8:attributes>
  </Catalog>
</MetaDataObject>
""",
        encoding="utf-8",
    )

    mod_file = catalogs / "МодульМенеджера.bsl"
    mod_file.write_text(
        """\
Функция ПолучитьАртикул(Ссылка) Экспорт

    Возврат Справочники.Номенклатура.ПолучитьОбъект(Ссылка).Артикул;

КонецФункции
""",
        encoding="utf-8-sig",
    )

    (config_root / "Configuration.xml").write_text(
        '<Configuration xmlns="http://v8.1c.ru/8.3/MDClasses"/>',
        encoding="utf-8",
    )

    return config_root


@pytest.fixture
def graph_db_path(tmp_path):
    """Путь для временной графовой БД."""
    return str(tmp_path / "test_graph.db")
