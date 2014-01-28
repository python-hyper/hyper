# -*- coding: utf-8 -*-
import pytest
import os
import json

@pytest.fixture(scope="class",
                params=os.listdir('test_fixtures'))
def story(request):
    """
    Provides a detailed HPACK story to test with.
    """
    path = os.path.join('test_fixtures', request.param)
    with open(path, 'r', encoding='utf-8') as f:
        details = json.loads(f.read())

    return details
