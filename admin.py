
from google.appengine.ext.webapp.util import run_wsgi_app
import logging
from webapp2_extras import jinja2

from google.appengine.api import namespace_manager
from vertnet.service.model import IndexJob

from mapreduce import control as mrc
from mapreduce import input_readers
from google.appengine.api import files
from google.appengine.api import urlfetch
import urllib
import os
import webapp2

IS_DEV = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

# App routes:
routes = [
    webapp2.Route(r'/mr/<name>/<resource>', handler='app.AppHandler:mapreduce', name='mapreduce'),
    webapp2.Route(r'/mr/finalize', handler='app.AppHandler:mapreduce_finalize', name='mapreduce_finalize'),
    webapp2.Route(r'/mr/indexall', handler='app.AppHandler:index', name='index'),
    webapp2.Router(r'/admin/sync-publishers', handler='admin.AdminHandler:sync_publishers'),
]

def apikey():
    """Return credentials file as a JSON object."""
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'vertnet', 'service', 'cdbkey.txt')
    key = open(path, "r").read()
    return key

cdb_url = "http://vertnet.cartodb.com/api/v2/sql?%s"

class AppHandler(webapp2.RequestHandler):

    @webapp2.cached_property
    def jinja2(self):
        this = jinja2.get_jinja2(app=self.app)
        this.environment.filters['static'] = self.static
        return this

    def render_template(self, template_name, template_values={}):
        self.response.write(self.jinja2.render_template(template_name, 
            **template_values))

    def static(self, foo):
        if IS_DEV:
            return ''
        else:
            return '/' + '1.0' 


    def sync_publishers(self):
        sql = 'SELECT * FROM resource'
        rpc = urlfetch.create_rpc()
        url = cdb_url % (urllib.urlencode(dict(q=sql, api_key=apikey())))
        urlfetch.make_fetch_call(rpc, url)
        try:
            response = rpc.get_result()
        except urlfetch.DownloadError:
            logging.error("Error logging API - %s" % (sql))
        if not response:
            return   

    def mapreduce_finalize(self):
        logging.info('HEADERS %s' % self.request.headers)
        mrid = self.request.headers.get('Mapreduce-Id')
        namespace = namespace_manager.get_namespace()
        job = IndexJob.get_by_id(mrid, namespace=namespace)
        if not job:
            logging.error('WTF no job for mrid:%s' % mrid)
            return
        logging.info('Finalizing index job for resource %s' % job.resource)
        files.finalize(job.write_path)
        job.done = True
        job.put()
        logging.info('Index job finalized for resource %s' % job.resource)

    def index(self):
        input_class = (input_readers.__name__ + "." + input_readers.FileInputReader.__name__)
        path = self.request.get('path')
        shard_count = self.request.get_range('shard_count', default=8)
        processing_rate = self.request.get_range('processing_rate', default=100)
        files_pattern = '/gs/%s' % path

        # Create file on GCS to log any failed index puts:
        namespace = namespace_manager.get_namespace()
        filename = '/gs/vn-staging/errors/failures-%s-all.csv' % namespace
        write_path = files.gs.create(filename, mime_type='text/tab-separated-values', acl='public-read')

        mrid = mrc.start_map(
            path,
            "vertnet.service.search.build_search_index",
            input_class,
            {
                "input_reader": dict(
                    files=[files_pattern], 
                    format='lines'),
                "resource": path,
                "write_path": write_path,
                "processing_rate": processing_rate,
                "shard_count": shard_count
            },
            mapreduce_parameters={'done_callback': '/mr/finalize'},
            shard_count=shard_count)

        IndexJob(id=mrid, namespace=namespace, resource=path, write_path=write_path, failed_logs=['NONE']).put()

    def mapreduce(self, name, resource):
        input_class = (input_readers.__name__ + "." + input_readers.FileInputReader.__name__)
        files_pattern = '/gs/vn-staging/data/2013-08-08/%s/part*' % resource

        # Create file on GCS to log any failed index puts:
        namespace = namespace_manager.get_namespace()
        filename = '/gs/vn-staging/errors/failures-%s-%s.csv' % (namespace, resource)
        write_path = files.gs.create(filename, mime_type='text/tab-separated-values', acl='public-read')

        mrid = mrc.start_map(
            name,
            "vertnet.service.search.build_search_index",
            input_class,
            {
                "input_reader": dict(
                    files=[files_pattern], 
                    format='lines'),
                "resource": resource,
                "write_path": write_path,
                "processing_rate": 150,
                "shard_count": 16
            },
            mapreduce_parameters={'done_callback': '/mr/finalize'},
            shard_count=16)

        IndexJob(id=mrid, namespace=namespace, resource=resource, write_path=write_path, failed_logs=['NONE']).put()

    def search(self):
        """Render the explore page."""
        self.render_template('search.html')
    
    def about(self):
        """Render the about page."""
        self.render_template('about.html')        

    def publishers(self):
        """Render the publishers page."""
        self.render_template('publishers.html')        

    def feedback(self):
        """Render the feedback page."""
        self.render_template('feedback.html')        

    def home(self):
        """Render page html."""
        self.render_template('home.html')

    def occ(self, publisher, resource):
        self.render_template('occurrence.html')        

handler = webapp2.WSGIApplication(routes, debug=IS_DEV)
         
def main():
    run_wsgi_app(handler)
