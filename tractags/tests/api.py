# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Odd Simon Simonsen <oddsimons@gmail.com>
# Copyright (C) 2012,2013 Steffen Hoffmann <hoff.st@web.de>
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import doctest
import shutil
import tempfile
import unittest

from trac.db.api import DatabaseManager
from trac.perm import PermissionCache, PermissionError, PermissionSystem
from trac.resource import Resource
from trac.test import EnvironmentStub, Mock

import tractags.api

from tractags.db import TagSetup
from tractags.ticket import TicketTagProvider
from tractags.wiki import WikiTagProvider


class TagSystemTestCase(unittest.TestCase):

    def setUp(self):
        self.env = EnvironmentStub(default_data=True,
                                   enable=['trac.*', 'tractags.*'])
        self.env.path = tempfile.mkdtemp()
        self.perms = PermissionSystem(self.env)
        self.req = Mock(authname='editor')

        self.actions = ['TAGS_ADMIN', 'TAGS_MODIFY', 'TAGS_VIEW']
        self.db = self.env.get_db_cnx()
        setup = TagSetup(self.env)
        # Current tractags schema is setup with enabled component anyway.
        #   Revert these changes for getting default permissions inserted.
        self._revert_tractags_schema_init()
        setup.upgrade_environment(self.db)
        self.tag_s = tractags.api.TagSystem(self.env)

    def tearDown(self):
        self.db.close()
        # Really close db connections.
        self.env.shutdown()
        shutil.rmtree(self.env.path)

    # Helpers

    def _revert_tractags_schema_init(self):
        cursor = self.db.cursor()
        cursor.execute("DROP TABLE IF EXISTS tags")
        cursor.execute("DROP TABLE IF EXISTS tags_change")
        cursor.execute("DELETE FROM system WHERE name='tags_version'")
        cursor.execute("DELETE FROM permission WHERE action %s"
                       % self.db.like(), ('TAGS_%',))

    # Tests

    def test_available_actions(self):
        for action in self.actions:
            self.failIf(action not in self.perms.get_actions())

    def test_available_providers(self):
        # Standard implementations of DefaultTagProvider should be registered.
        seen = []
        for provider in [TicketTagProvider(self.env),
                         WikiTagProvider(self.env)]:
            self.failIf(provider not in self.tag_s.tag_providers)
            # Ensure unique provider references, a possible bug in Trac-0.11.
            self.failIf(provider in seen)
            seen.append(provider)

    def test_set_tags_no_perms(self):
        resource = Resource('wiki', 'WikiStart')
        tags = ['tag1']
        # Mock an anonymous request.
        self.req.perm = PermissionCache(self.env)
        self.assertRaises(PermissionError, self.tag_s.set_tags, self.req,
                          resource, tags)

    def test_set_tags(self):
        resource = Resource('wiki', 'WikiStart')
        tags = ['tag1']
        self.req.perm = PermissionCache(self.env, username='editor')
        # Shouldn't raise an error with appropriate permission.
        self.tag_s.set_tags(self.req, resource, tags)

    def test_query_no_args(self):
        # Regression test for query without argument,
        #   reported as th:ticket:7857.

        # Mock an anonymous request.
        self.req.perm = PermissionCache(self.env)
        self.assertEquals([(res, tags) for res, tags in
                           self.tag_s.query(self.req, query='')],
                          [])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(module=tractags.api))
    suite.addTest(unittest.makeSuite(TagSystemTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
