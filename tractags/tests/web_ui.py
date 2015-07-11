# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Odd Simon Simonsen <oddsimons@gmail.com>
# Copyright (C) 2012 Ryan J Ollos <ryan.j.ollos@gmail.com>
# Copyright (C) 2012-2014 Steffen Hoffmann <hoff.st@web.de>
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#

import shutil
import tempfile
import unittest

from trac.test import EnvironmentStub, Mock, MockPerm
from trac.perm import PermissionSystem, PermissionCache, PermissionError
from trac.util.datefmt import utc
from trac.web.api import RequestDone
from trac.web.href import Href
from trac.web.main import RequestDispatcher
from trac.web.session import DetachedSession

from tractags.api import TagSystem
from tractags.db import TagSetup
from tractags.web_ui import TagInputAutoComplete, TagRequestHandler
from tractags.web_ui import TagTimelineEventFilter, TagTimelineEventProvider


class _BaseTestCase(unittest.TestCase):

    def setUp(self):
        self.env = EnvironmentStub(
                enable=['trac.*', 'tractags.*'])
        self.env.path = tempfile.mkdtemp()
        self.db = self.env.get_db_cnx()
        setup = TagSetup(self.env)
        # Current tractags schema is setup with enabled component anyway.
        #   Revert these changes for getting a clean setup.
        self._revert_tractags_schema_init()
        setup.upgrade_environment(self.db)

        self.tag_s = TagSystem(self.env)
        self.tag_rh = TagRequestHandler(self.env)

        perms = PermissionSystem(self.env)
        # Revoke default permissions, because more diversity is required here.
        perms.revoke_permission('anonymous', 'TAGS_VIEW')
        perms.revoke_permission('authenticated', 'TAGS_MODIFY')
        perms.grant_permission('reader', 'TAGS_VIEW')
        perms.grant_permission('writer', 'TAGS_MODIFY')
        perms.grant_permission('admin', 'TAGS_ADMIN')

        self.href = Href('/trac')
        self.abs_href = Href('http://example.org/trac')

    def tearDown(self):
        self.db.close()
        # Really close db connections.
        self.env.shutdown()
        shutil.rmtree(self.env.path)

    # Helpers

    def _create_request(self, authname='anonymous', **kwargs):
        kw = {'perm': PermissionCache(self.env, authname), 'args': {},
              'callbacks': {}, 'path_info': '', 'form_token': None,
              'href': self.env.href, 'abs_href': self.env.abs_href,
              'tz': utc, 'locale': None, 'lc_time': None,
              'session': DetachedSession(self.env, authname),
              'authname': authname, 'chrome': {'notices': [], 'warnings': []},
              'method': None, 'get_header': lambda v: None, 'is_xhr': False}
        kw.update(kwargs)
        def send(self, content, content_type='text/html', status=200):
            raise RequestDone
        return Mock(send=send, **kw)

    def _revert_tractags_schema_init(self):
        cursor = self.db.cursor()
        cursor.execute("DROP TABLE IF EXISTS tags")
        cursor.execute("DROP TABLE IF EXISTS tags_change")
        cursor.execute("DELETE FROM system WHERE name='tags_version'")
        cursor.execute("DELETE FROM permission WHERE action %s"
                       % self.db.like(), ('TAGS_%',))


class TagInputAutoCompleteTestCase(_BaseTestCase):

    def setUp(self):
        _BaseTestCase.setUp(self)
        self.req = Mock()
        self.req.perm = MockPerm()
        self.tac = TagInputAutoComplete(self.env)

    # Tests

    def test_separtor_is_default(self):
        self.assertEqual(' ', self.tac.separator_opt)

    def test_separator_is_empty_quotes(self):
        self.env.config.set('tags', 'separator', "''")
        self.assertEqual(' ', self.tac.separator)

    def test_separator_is_comma(self):
        self.env.config.set('tags', 'separator', ',')
        self.assertEqual(',', self.tac.separator)

    def test_separator_is_quoted_strip_quotes(self):
        self.env.config.set('tags', 'separator', "','")
        self.assertEqual(',', self.tac.separator)

    def test_separator_is_quoted_whitespace_strip_quotes(self):
        self.env.config.set('tags', 'separator', "' '")
        self.assertEqual(' ', self.tac.separator)

    def test_get_keywords_no_keywords(self): 
        self.assertEqual('', self.tac._get_keywords_string(self.req))

    def test_get_keywords_define_in_config(self):
        self.env.config.set('tags', 'complete_sticky_tags',
                            'tag1, tag2, tag3')
        self.assertEqual("'tag1','tag2','tag3'",
                         self.tac._get_keywords_string(self.req))

    def test_keywords_are_sorted(self):
        self.env.config.set('tags', 'complete_sticky_tags',
                            'tagb, tagc, taga')
        self.assertEqual("'taga','tagb','tagc'",
                         self.tac._get_keywords_string(self.req))
    
    def test_keywords_duplicates_removed(self):
        self.env.config.set('tags', 'complete_sticky_tags',
                            'tag1, tag1, tag2')
        self.assertEqual("'tag1','tag2'",
                         self.tac._get_keywords_string(self.req))

    def test_keywords_quoted_for_javascript(self):
        self.env.config.set('tags', 'complete_sticky_tags', 'it\'s, "this"')
        self.assertEqual('\'\\"this\\"\',\'it\\\'s\'',
                         self.tac._get_keywords_string(self.req))

    def test_implements_irequestfilter(self):
        from trac.web.main import RequestDispatcher
        self.assertTrue(self.tac in RequestDispatcher(self.env).filters)

    def test_implements_itemplateprovider(self):
        from trac.web.chrome import Chrome
        self.assertTrue(self.tac in Chrome(self.env).template_providers)

    def test_implements_itemplatestreamfilter(self):
        from trac.web.chrome import Chrome
        self.assertTrue(self.tac in Chrome(self.env).stream_filters)


class TagRequestHandlerTestCase(_BaseTestCase):

    def setUp(self):
        _BaseTestCase.setUp(self)
        self.anonymous = PermissionCache(self.env)
        self.reader = PermissionCache(self.env, 'reader')
        self.writer = PermissionCache(self.env, 'writer')
        self.admin = PermissionCache(self.env, 'admin')

    # Tests

    def test_matches(self):
        req = Mock(path_info='/tags',
                   authname='reader',
                   perm=self.reader
                  )
        self.assertEquals(True, self.tag_rh.match_request(req))

    def test_get_main_page(self):
        req = Mock(path_info='/tags',
                   args={},
                   authname='reader',
                   perm=self.reader,
                   href=self.href,
                   method='GET',
                   chrome=dict(static_hash='hashme!'),
                   session=DetachedSession(self.env, 'reader'),
                   locale='',
                   tz=''
                )
        template, data, content_type = self.tag_rh.process_request(req)
        self.assertEquals('tag_view.html', template)
        self.assertEquals(None, content_type)
        self.assertEquals(['checked_realms', 'mincount', 'page_title',
                           'tag_body', 'tag_query', 'tag_realms'],
                           sorted(data.keys()))

    def test_get_main_page_no_permission(self):
        req = Mock(path_info='/tags',
                   args={},
                   authname='anonymous',
                   perm=self.anonymous,
                   href=self.href,
                   chrome=dict(static_hash='hashme!'),
                   locale='',
                   tz=''
                )
        self.assertRaises(PermissionError, self.tag_rh.process_request, req)


class TagTimelineEventFilterTestCase(_BaseTestCase):

    def setUp(self):
        _BaseTestCase.setUp(self)
        self.tef = TagTimelineEventFilter(self.env)
        self.tep = TagTimelineEventProvider(self.env)

    # Tests

    def test_implements_irequestfilter(self):
        from trac.web.main import RequestDispatcher
        self.assertTrue(self.tef in RequestDispatcher(self.env).filters)

    def test_implements_itemplatestreamfilter(self):
        from trac.web.chrome import Chrome
        self.assertTrue(self.tef in Chrome(self.env).stream_filters)

    def test_tag_query_save(self):
        """Save timeline tag query string in session."""
        self.assertEqual('tag_query', self.tef.key)

        from trac.timeline.web_ui import TimelineModule
        TimelineModule(self.env)
        perms = PermissionSystem(self.env)
        perms.grant_permission('anonymous', 'TAGS_VIEW')
        perms.grant_permission('anonymous', 'TIMELINE_VIEW')

        req = self._create_request(args=dict(tag_query='query_str'),
                                   path_info='/timeline', method='GET')
        dispatcher = RequestDispatcher(self.env)
        self.assertRaises(RequestDone, dispatcher.dispatch, req)
        self.assertEqual('query_str', req.session['timeline.tag_query'])


class TagTimelineEventProviderTestCase(_BaseTestCase):

    def setUp(self):
        _BaseTestCase.setUp(self)
        self.tep = TagTimelineEventProvider(self.env)

    # Tests

    def test_implements_itimelineeventsprovider(self):
        from trac.timeline.web_ui import TimelineModule
        self.assertTrue(self.tep in TimelineModule(self.env).event_providers)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TagInputAutoCompleteTestCase, 'test'))
    suite.addTest(unittest.makeSuite(TagRequestHandlerTestCase, 'test'))
    suite.addTest(unittest.makeSuite(TagTimelineEventFilterTestCase, 'test'))
    suite.addTest(unittest.makeSuite(TagTimelineEventProviderTestCase,
                                     'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
