# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Odd Simon Simonsen <oddsimons@gmail.com>
# Copyright (C) 2012-2015 Steffen Hoffmann <hoff.st@web.de>
# Copyright (C) 2014 Jun Omae <jun66j5@gmail.com>
# Copyright (C) 2015 Ryan J Ollos <ryan.j.ollos@gmail.com>
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import shutil
import tempfile
import unittest

from trac.test import EnvironmentStub, Mock, MockPerm
from trac.web.href import Href

from tractags.db import TagSetup
from tractags.macros import query_realms, TagTemplateProvider, TagWikiMacros


class _BaseTestCase(unittest.TestCase):

    def setUp(self):
        self.env = EnvironmentStub(default_data=True,
                                   enable=['trac.*', 'tractags.*'])
        self.env.path = tempfile.mkdtemp()

        self.db = self.env.get_db_cnx()
        setup = TagSetup(self.env)
        # Current tractags schema is setup with enabled component anyway.
        #   Revert these changes for getting default permissions inserted.
        self._revert_tractags_schema_init()
        setup.upgrade_environment(self.db)

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

    def _insert_tags(self, tagspace, name, tags):
        cursor = self.db.cursor()
        args = [(tagspace, name, tag) for tag in tags]
        cursor.executemany("INSERT INTO tags (tagspace,name,tag) "
                           "VALUES (%s,%s,%s)", args)


class TagTemplateProviderTestCase(_BaseTestCase):

    def setUp(self):
        _BaseTestCase.setUp(self)

        # TagTemplateProvider is abstract, test using a subclass
        self.tag_wm = TagWikiMacros(self.env)

    def test_template_dirs_added(self):
        from trac.web.chrome import Chrome
        self.assertTrue(self.tag_wm in Chrome(self.env).template_providers)


class ListTaggedMacroTestCase(_BaseTestCase):

    def setUp(self):
        _BaseTestCase.setUp(self)
        self.req = Mock(path_info='/wiki/ListTaggedPage',
                        args={}, authname='user', perm=MockPerm(),
                        href=Href('/'),
                        abs_href=Href('http://example.org/trac/'),
                        chrome={}, session={}, locale='', tz='')

        self.tag_twm = TagWikiMacros(self.env)

    def test_empty_content(self):
        context = Mock(env=self.env, href=Href('/'), req=self.req)
        formatter = Mock(context=context, req=self.req)
        self.assertTrue('No resources found' in
                        str(self.tag_twm.expand_macro(formatter,
                                                      'ListTagged', '')))

    def test_listtagged_exclude(self):
        self._insert_tags('wiki', 'InterTrac', ('blah',))
        self._insert_tags('wiki', 'InterWiki', ('blah',))
        self._insert_tags('wiki', 'WikiStart', ('blah',))
        context = Mock(env=self.env, href=Href('/'), req=self.req)
        formatter = Mock(context=context, req=self.req)
        result = unicode(self.tag_twm.expand_macro(formatter, 'ListTagged',
                                                   'blah,exclude=Inter*'))
        self.assertFalse('InterTrac' in result)
        self.assertFalse('InterWiki' in result)
        self.assertTrue('WikiStart' in result)

        result = unicode(self.tag_twm.expand_macro(formatter, 'ListTagged',
                                                   'blah,exclude=Wi*:*ki'))
        self.assertTrue('InterTrac' in result)
        self.assertFalse('InterWiki' in result)
        self.assertFalse('WikiStart' in result)

    def _test_listtagged_paginate(self, page, per_page=2):
        self._insert_tags('wiki', 'InterTrac', ('blah',))
        self._insert_tags('wiki', 'InterWiki', ('blah',))
        self._insert_tags('wiki', 'WikiStart', ('blah',))
        self.req.args['listtagged_per_page'] = per_page
        self.req.args['listtagged_page'] = page
        context = Mock(env=self.env, href=Href('/'), req=self.req)
        formatter = Mock(context=context, req=self.req)
        result = \
            unicode(self.tag_twm.expand_macro(formatter, 'ListTagged', 'blah'))
        return result

    def test_listtagged_paginate_page1(self):
        """Paginate results for page 1 has two items."""
        result = self._test_listtagged_paginate(1)
        self.assertTrue('InterTrac' in result)
        self.assertTrue('InterWiki' in result)
        self.assertFalse('WikiStart' in result)

    def test_listtagged_paginate_page2(self):
        """Paginate results for page 2 has one item."""
        result = self._test_listtagged_paginate(2)
        self.assertFalse('InterTrac' in result)
        self.assertFalse('InterWiki' in result)
        self.assertTrue('WikiStart' in result)

    def test_listtagged_paginate_page_out_of_range(self):
        """Out of range page defaults to 1."""
        result = self._test_listtagged_paginate(3)
        self.assertTrue('InterTrac' in result)
        self.assertTrue('InterWiki' in result)
        self.assertFalse('WikiStart' in result)

    def test_listtagged_paginate_page_invalid(self):
        """Invalid page default to 1."""
        result = self._test_listtagged_paginate(-1)
        self.assertTrue('InterTrac' in result)
        self.assertTrue('InterWiki' in result)
        self.assertFalse('WikiStart' in result)

    def test_listtagged_paginate_per_page_invalid(self):
        """Invalid per_page defaults to items_per_page (100)."""
        result = self._test_listtagged_paginate(2, -1)
        self.assertTrue('InterTrac' in result)
        self.assertTrue('InterWiki' in result)
        self.assertTrue('WikiStart' in result)


class TagCloudMacroTestCase(_BaseTestCase):

    def setUp(self):
        _BaseTestCase.setUp(self)
        self.req = Mock(path_info='/wiki/TagCloudPage',
                        args={}, authname='user', perm=MockPerm(),
                        href=Href('/'),
                        abs_href='http://example.org/trac/',
                        chrome={}, session={}, locale='', tz='')
        self.context = Mock(env=self.env, href=self.req.href, req=self.req)
        self.formatter = Mock(context=self.context, req=self.req)

        self.tag_twm = TagWikiMacros(self.env)

    # Helpers

    def _expand_macro(self, content):
        return self.tag_twm.expand_macro(self.formatter, 'TagCloud', content)

    # Tests

    def test_normal(self):
        self._insert_tags('wiki',   'CamelCase',     ('blah', 'foo', 'bar'))
        self._insert_tags('wiki',   'InterMapTxt',   ('blah', 'foo', 'bar'))
        self._insert_tags('wiki',   'InterTrac',     ('blah',))
        self._insert_tags('wiki',   'InterWiki',     ('blah',))
        self._insert_tags('wiki',   'PageTemplates', ('blah',))
        self._insert_tags('wiki',   'RecentChanges', ('blah', 'foo'))
        self._insert_tags('wiki',   'SandBox',       ('blah', 'foo'))
        self._insert_tags('ticket', '1',             ('blah',))
        self._insert_tags('ticket', '2',             ('blah', 'bar'))
        self._insert_tags('ticket', '3',             ('blah', 'bar'))
        self._insert_tags('ticket', '4',             ('blah', 'bar'))

        result = unicode(self._expand_macro(''))
        self.assertTrue('">blah</a>' in result, repr(result))
        self.assertTrue('">foo</a>' in result, repr(result))
        self.assertTrue('">bar</a>' in result, repr(result))

        result = unicode(self._expand_macro('mincount=5'))
        self.assertTrue('">blah</a>' in result, repr(result))
        self.assertFalse('">foo</a>' in result, repr(result))
        self.assertTrue('">bar</a>' in result, repr(result))

        result = unicode(self._expand_macro('mincount=6'))
        self.assertTrue('">blah</a>' in result, repr(result))
        self.assertFalse('">foo</a>' in result, repr(result))
        self.assertFalse('">bar</a>' in result, repr(result))

        result = unicode(self._expand_macro('realm=ticket|wiki'))
        self.assertTrue('">blah</a>' in result, repr(result))
        self.assertTrue('">foo</a>' in result, repr(result))
        self.assertTrue('">bar</a>' in result, repr(result))

        result = unicode(self._expand_macro('realm=ticket'))
        self.assertTrue('">blah</a>' in result, repr(result))
        self.assertFalse('">foo</a>' in result, repr(result))
        self.assertTrue('">bar</a>' in result, repr(result))

        result = unicode(self._expand_macro('realm=ticket,mincount=4'))
        self.assertTrue('">blah</a>' in result, repr(result))
        self.assertFalse('">foo</a>' in result, repr(result))
        self.assertFalse('">bar</a>' in result, repr(result))

        result = unicode(self._expand_macro('realm=unknown'))
        self.assertEquals('No tags found', result)

        result = unicode(self._expand_macro('mincount=100'))
        self.assertEquals('No tags found', result)


class QueryRealmsTestCase(unittest.TestCase):
    def test_query_realms(self):
        all_realms = ['ticket', 'wiki']
        # No tag providers detected.
        self.assertFalse('ticket' in query_realms('', []))
        # No tags query statement used.
        self.assertFalse('ticket' in query_realms('', all_realms))
        self.assertFalse('ticket' in query_realms('ticket', all_realms))
        self.assertFalse('ticket' in query_realms('realm:ticket', ['wiki']))
        self.assertTrue('ticket' in query_realms('realm:ticket', all_realms))
        self.assertFalse('wiki' in query_realms('realm:ticket', all_realms))
        self.assertTrue('wiki' in
                        query_realms('onetag realm:wiki 2ndtag', all_realms))
        self.assertFalse('wiki' in
                         query_realms('onetag realm=wiki 2ndtag', all_realms))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TagTemplateProviderTestCase, 'test'))
    suite.addTest(unittest.makeSuite(ListTaggedMacroTestCase, 'test'))
    suite.addTest(unittest.makeSuite(TagCloudMacroTestCase, 'test'))
    suite.addTest(unittest.makeSuite(QueryRealmsTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
