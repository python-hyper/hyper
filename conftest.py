# -*- coding: utf-8 -*-
import pytest
import os
import json

# This pair of generator expressions are pretty lame, but building lists is a
# bad idea as I plan to have a substantial number of tests here.
story_directories = (
    os.path.join('test_fixtures', d) for d in os.listdir('test_fixtures')
)
story_files = (
    os.path.join(storydir, name) for storydir in story_directories
                                 for name in os.listdir(storydir)
)

@pytest.fixture(scope="class",
                params=story_files)
def story(request):
    """
    Provides a detailed HPACK story to test with.
    """
    path = request.param
    with open(path, 'r', encoding='utf-8') as f:
        details = json.loads(f.read())

    return details
