import json
import base64

from restless.dj import DjangoResource
from restless.resources import skip_prepare

from django.conf.urls import patterns,  url
try:
    from django.utils.encoding import smart_text
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text

from django.contrib import auth

from harvest.models import Job
from tablemanager.models import Publish
from harvest.jobstatemachine import JobStatemachine
from borg_utils.hg_batch_push import try_set_push_owner, try_clear_push_owner, try_push_to_repository
from borg_utils.jobintervals import Triggered

class BasicHttpAuthMixin(object):
    """
    :py:class:`restless.views.Endpoint` mixin providing user authentication
    based on HTTP Basic authentication.
    """

    def authenticate(self, request):
        if 'HTTP_AUTHORIZATION' in request.META:
            authdata = request.META['HTTP_AUTHORIZATION'].split()
            if len(authdata) == 2 and authdata[0].lower() == "basic":
                try:
                    raw = authdata[1].encode('ascii')
                    auth_parts = base64.b64decode(raw).split(b':')
                except:
                    return
                try:
                    uname, passwd = (smart_text(auth_parts[0]),
                        smart_text(auth_parts[1]))
                except DjangoUnicodeDecodeError:
                    return

                user = auth.authenticate(username=uname, password=passwd)
                if user is not None and user.is_active:
                    # We don't user auth.login(request, user) because
                    # may be running without session
                    request.user = user
        return request.user.is_authenticated()


class JobResource(DjangoResource,BasicHttpAuthMixin):
    def is_authenticated(self):
        if self.request.user.is_authenticated():
            return True
        else:
            return self.authenticate(self.request)

    @staticmethod
    def urls():
        return patterns('',
            url(r'^/?$',JobResource.as_list(),name='api_job_create'),
        )
     
    @skip_prepare
    def create(self):
        job_batch_id = Triggered.instance().job_batch_id()
        resp = {"status":True}
        result = None
        for name in self.data.get('publishes') or []:
            resp[name] = {}
            result = JobStatemachine.create_job_by_name(name,Triggered.instance(),job_batch_id)
            if result[0]:
                resp[name]["status"] = True
                resp[name]["job_id"] = result[1]
                resp[name]["message"] = "Succeed"
            else:
                resp["status"] = False
                resp[name]["status"] = False
                resp[name]["message"] = result[1]
        return resp

class MetaResource(DjangoResource,BasicHttpAuthMixin):
    def is_authenticated(self):
        if self.request.user.is_authenticated():
            return True
        else:
            return self.authenticate(self.request)

    @staticmethod
    def urls():
        return patterns('',
            url(r'^/?$',MetaResource.as_list(),name='api_meta_create'),
        )
     
    @skip_prepare
    def create(self):
        resp = {"status":True}
        result = None
        try_set_push_owner("meta_resource")
        try:
            for name in self.data.get('publishes') or []:
                resp[name] = {}
                try:
                    pub = Publish.objects.get(name=name)
                except Publish.DoesNotExist:
                    resp["status"] = False
                    resp[name]["status"] = False
                    resp[name]["message"] = "Does not exist.".format(name)
                    continue
                try:
                    pub.publish_meta_data()
                    resp[name]["status"] = True
                    resp[name]["message"] = "Succeed."
                except Exception as e:
                    resp["status"] = False
                    resp[name]["status"] = False
                    resp[name]["message"] = "Publish failed!{}".format(e)
                    continue
            try:
                try_push_to_repository('meta_resource',enforce=True)
            except Exception as e:
                resp["status"] = False
                for name in self.data.get('published') or []:
                    if resp[name]["status"]:
                        #publish succeed but push failed
                        resp[name]["status"] = False
                        resp[name]["message"] = "Push to repository failed!{}".format(e)
        finally:
            try_clear_push_owner("meta_resource")
            
        return resp


