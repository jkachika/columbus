"""columbus URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.views import logout
from pyedf.views import *

admin.autodiscover()

urlpatterns = [
    url(r'^$', NLHome.as_view()),
    url(r'^login$', Login.as_view()),
    url(r'^logout/$', logout, {'next_page': '/login'}),
    url(r'^verify$', verify),
    url(r'^test$', Test.as_view()),
    url(r'^home$', ensure_csrf_cookie(Home.as_view())),
    url(r'^workspace$', Workspace.as_view()),
    url(r'^history$', History.as_view()),
    url(r'^history/$', History.as_view()),
    url(r'^hasync/$', HistoryAsync.as_view()),
    url(r'^download/$', Download.as_view()),
    url(r'^delete/$', DeleteAsync.as_view()),
    url(r'^constraints$', WorkspaceAsync.as_view()),
    url(r'^elements/$', WorkspaceAsync.as_view()),
    url(r'^schedule$', WorkspaceAsync.as_view()),
    url(r'^startflow$', StartFlow.as_view()),
    url(r'^myaccount$', MyAccount.as_view()),
    url(r'^updateac', UpdateAccount.as_view()),
    url(r'^featureset$', Featureset.as_view()),
    url(r'^savepolygon$', SavePolygon.as_view()),
    url(r'^usercode/$', CodeReader.as_view()),
    url(r'^getchain/$', BuildChain.as_view()),
    url(r'^peekflow/$', PeekFlow.as_view()),
    url(r'^peekdata/$', PeekFlowData.as_view()),
    url(r'^oauth2callback/$', OAuth2Handler.as_view()),
    url(r'^data/$', DatasourceAsync.as_view()),
    url(r'^service/$', ColumbusService.as_view()),
    url(r'^admin', include(admin.site.urls))
]
