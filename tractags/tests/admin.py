# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Odd Simon Simonsen <oddsimons@gmail.com>
# Copyright (C) 2012 Steffen Hoffmann <hoff.st@web.de>
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import shutil
import tempfile
import unittest

from trac.test import EnvironmentStub, Mock

from tractags.admin import TagChangeAdminPanel


class TagChangeAdminPanelTestCase(unittest.TestCase):

    def setUp(self):
        self.env = EnvironmentStub(
                enable=['trac.*', 'tractags.*'])
        self.env.path = tempfile.mkdtemp()

        self.tag_cap = TagChangeAdminPanel(self.env)

    def tearDown(self):
        shutil.rmtree(self.env.path)

    def test_init(self):
        # Empty test just to confirm that setUp and tearDown works
        pass


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TagChangeAdminPanelTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
