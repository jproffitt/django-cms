# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

from django.core.urlresolvers import reverse
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import force_text

from cms.constants import PAGE_USERNAME_MAX_LENGTH
from cms.utils import get_current_site
from cms.utils.conf import get_cms_setting
from cms.utils.moderator import use_draft


APPEND_TO_SLUG = "-copy"
COPY_SLUG_REGEX = re.compile(r'^.*-copy(?:-(\d+)*)?$')


def get_page_template_from_request(request):
    """
    Gets a valid template from different sources or falls back to the default
    template.
    """
    templates = get_cms_setting('TEMPLATES')
    template_names = frozenset(pair[0] for pair in templates)

    if len(templates) == 1:
        # there's only one template
        # avoid any further computation
        return templates[0][0]

    manual_template = request.GET.get('template')

    if manual_template and manual_template in template_names:
        return manual_template

    if request.current_page:
        return request.current_page.get_template()
    return get_cms_setting('TEMPLATES')[0][0]


def get_clean_username(user):
    try:
        username = force_text(user)
    except AttributeError:
        # AnonymousUser may not have USERNAME_FIELD
        username = "anonymous"
    else:
        # limit changed_by and created_by to avoid problems with Custom User Model
        if len(username) > PAGE_USERNAME_MAX_LENGTH:
            username = u'{0}... (id={1})'.format(
                username[:PAGE_USERNAME_MAX_LENGTH - 15],
                user.pk,
            )
    return username


def get_node_queryset(site, published=False):
    from cms.models import PageNode

    if published:
        return PageNode.objects.published(site)
    return PageNode.objects.get_for_site(site)


def get_page_queryset(site, draft=True):
    from cms.models import Page

    if draft:
        return Page.objects.drafts().filter(nodes__site=site)
    return Page.objects.public().filter(publisher_public__nodes__site=site)


def get_page_from_path(site, path, preview=False, draft=False):
    """
    Resolves a url path to a single page object.
    Returns None if page does not exist
    """
    from cms.models import PageNode, Title

    titles = Title.objects.select_related('page')
    published_only = (not draft and not preview)

    if draft:
        titles = titles.filter(publisher_is_draft=True)
    elif preview:
        titles = titles.filter(publisher_is_draft=False)
    else:
        titles = titles.filter(published=True, publisher_is_draft=False)
    titles = titles.filter(path=(path or ''))

    for title in titles.iterator():
        if published_only and not title.page.is_reachable():
            continue

        try:
            # fetches the node and caches it on the page
            title.page.get_node_object(site)
        except PageNode.DoesNotExist:
            continue

        title.page.title_cache = {title.language: title}
        return title.page
    return


def get_pages_from_path(site, path, preview=False, draft=False):
    """ Returns a queryset of pages corresponding to the path given
    """
    pages = get_page_queryset(site, draft=draft)

    if not (draft or preview):
        pages = pages.published()

    if path:
        # title_set__path=path should be clear, get the pages where the path of the
        # title object is equal to our path.
        return pages.filter(title_set__path=path).distinct()
    # if there is no path (slashes stripped) and we found a home, this is the
    # home page.
    return pages.filter(is_home=True).distinct()


def get_page_from_request(request, use_path=None, clean_path=None):
    """
    Gets the current page from a request object.

    URLs can be of the following form (this should help understand the code):
    http://server.whatever.com/<some_path>/"pages-root"/some/page/slug

    <some_path>: This can be anything, and should be stripped when resolving
        pages names. This means the CMS is not installed at the root of the
        server's URLs.
    "pages-root" This is the root of Django urls for the CMS. It is, in essence
        an empty page slug (slug == '')

    The page slug can then be resolved to a Page model object
    """
    from cms.utils.page_permissions import user_can_view_page_draft

    if hasattr(request, '_current_page_cache'):
        # The following is set by CurrentPageMiddleware
        return request._current_page_cache

    if clean_path is None:
        clean_path = not bool(use_path)

    draft = use_draft(request)
    preview = 'preview' in request.GET
    path = request.path_info if use_path is None else use_path

    if clean_path:
        pages_root = reverse("pages-root")

        if path.startswith(pages_root):
            path = path[len(pages_root):]

        # strip any final slash
        if path.endswith("/"):
            path = path[:-1]

    site = get_current_site()
    page = get_page_from_path(site, path, preview, draft)

    if draft and page and not user_can_view_page_draft(request.user, page):
        page = get_page_from_path(site, path, preview, draft=False)

    # For public pages, check if any parent is hidden due to published dates
    # In this case the selected page is not reachable
    if page and not draft:
        now = timezone.now()
        node = page.get_node_object(site)
        unpublished_ancestors = (
            node
            .get_ancestors()
            .filter(
                Q(page__publication_date__gt=now)
                | Q(page__publication_end_date__lt=now),
            )
        )
        if unpublished_ancestors.exists():
            page = None
    return page


def get_all_pages_from_path(site, path, language):
    path = path.strip('/')
    pages = get_pages_from_path(site, path, draft=True)
    pages |= get_pages_from_path(site, path, preview=True, draft=False)
    return pages.filter(title_set__language=language)


def get_available_slug(site, path, language):
    """
    Generates slug for path.
    If path is used, appends the value of APPEND_TO_SLUG to the end.
    """
    base, _, slug = path.rpartition('/')
    pages = get_all_pages_from_path(site, path, language)

    if pages.exists():
        # first is -copy, then -copy-2, -copy-3, ....
        match = COPY_SLUG_REGEX.match(slug)
        if match:
            try:
                next_id = int(match.groups()[0]) + 1
                slug = "-".join(slug.split('-')[:-1]) + "-%d" % next_id
            except TypeError:
                slug += "-2"
        else:
            slug += APPEND_TO_SLUG
        path = '%s/%s' % (base, slug) if base else slug
        return get_available_slug(site, path, language)
    return slug
