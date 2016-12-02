import hyper
import imp
import pytest
import sys


class TestImportPython2(object):
    @pytest.mark.skipif(sys.version_info[0] == 3, reason="Python 2 only")
    def test_cannot_import_python_2(self, monkeypatch):
        monkeypatch.setattr(sys, 'version_info', (2, 6, 5, 'final', 0))
        with pytest.raises(ImportError):
            imp.reload(hyper)


class TestImportPython3(object):
    @pytest.mark.skipif(sys.version_info[0] == 2, reason="Python 3 only")
    def test_cannot_import_python_32(self, monkeypatch):
        monkeypatch.setattr(sys, 'version_info', (3, 2, 3, 'final', 0))
        with pytest.raises(ImportError):
            imp.reload(hyper)
