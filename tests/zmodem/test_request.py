import sys
import os
import pytest
from szaio import main as szaio_main


def test_request():
    sys.argv = ['szaio', '--utf8', '--zdle', '23', '--request', 'easyrsa3.tgz']
    # Actually let's just see what szaio prints!
    szaio_main()
