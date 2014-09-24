import json, signal, os, logging, re, webbrowser, requests
from sys import exit, argv
from multiprocessing import Process
from time import sleep, time

import tornado.ioloop
import tornado.web
import tornado.httpserver

from mako.template import Template

from api import UnveillanceAPI
from Models.uv_annex_watcher import UnveillanceFSEHandler

from lib.Core.vars import Result
from lib.Core.Utils.funcs import startDaemon, stopDaemon, parseRequestEntity, generateSecureNonce

from conf import DEBUG
from conf import getConfig, MONITOR_ROOT, BASE_DIR, ANNEX_DIR, API_PORT, NUM_PROCESSES, WEB_TITLE, UV_COOKIE_SECRET, buildServerURL

def terminationHandler(signal, frame): exit(0)
signal.signal(signal.SIGINT, terminationHandler)

class UnveillanceFrontend(tornado.web.Application, UnveillanceAPI, UnveillanceFSEHandler):
	def __init__(self):
		self.api_pid_file = os.path.join(MONITOR_ROOT, "frontend.pid.txt")
		self.api_log_file = os.path.join(MONITOR_ROOT, "frontend.log.txt")
		
		self.reserved_routes = ["frontend", "web", "files", "statuses"]
		self.routes = [
			(r"/frontend/", self.FrontendHandler),
			(r"/web/([a-zA-Z0-9\-\._/]+)", self.WebAssetHandler),
			(r"/auth/(user|annex|drive)/", self.AuthHandler),
			(r"/files/(.+)", self.FileHandler),
			(r"/task/", self.TaskHandler)]
		
		self.default_on_loads = [
			"/web/js/models/unveillance_document.js"
		]
		self.on_loads_by_status = [[] for i in range(4)]
		self.on_loads = {}
		
		from vars import MIME_TYPES, ASSET_TAGS, MIME_TYPE_TASKS
		self.init_vars = {
			'MIME_TYPES' : MIME_TYPES,
			'ASSET_TAGS' : ASSET_TAGS,
			'MIME_TYPE_TASKS' : MIME_TYPE_TASKS
		}
		
		UnveillanceAPI.__init__(self)
	
	class AuthHandler(tornado.web.RequestHandler):
		@tornado.web.asynchronous
		def get(self, auth_type):
			endpoint = "/"
			
			if auth_type == "annex":
				if self.application.do_get_status(self) == 3:
					from lib.Frontend.Models.uv_fabric_process import UnveillanceFabricProcess
					from lib.Frontend.Utils.fab_api import linkLocalRemote
					
					p = UnveillanceFabricProcess(linkLocalRemote)
					p.join()
					
					try:
						endpoint = "/#linked_remote_%s" % p.output
					except AttributeError as e:
						if DEBUG: print e
					
			self.redirect(endpoint)
		
		@tornado.web.asynchronous
		def post(self, auth_type):
			res = Result()
			
			if auth_type == "drive" and self.do_get_status in [3,4]:
				status_check = "get_drive_status"
			elif auth_type == "user":
				status_check = "get_user_status"
			
			if status_check is not None:
				res = self.application.routeRequest(res, status_check, self)
			
			if DEBUG: print res.emit()
			
			self.set_status(res.result)
			self.finish(res.emit())
	
	class WebAssetHandler(tornado.web.RequestHandler):	# TODO: secure this better.
		@tornado.web.asynchronous
		def get(self, uri):
			if uri == "conf.json":					
				self.finish(json.dumps(self.application.init_vars))
				return
			
			static_path = os.path.join(BASE_DIR, "web")
			asset = os.path.join(static_path, uri)
			
			if not os.path.exists(asset):
				asset = os.path.join(static_path, "extras", uri)
			
			if not os.path.exists(asset):
				res = Result()
				
				self.set_status(res.result)
				self.finish(res.emit())
				return
			
			with open(asset, 'rb') as a: self.finish(a.read())
				
	class FrontendHandler(tornado.web.RequestHandler):
		@tornado.web.asynchronous
		def get(self):
			res = Result()
			query = parseRequestEntity(self.request.query)
			
			if DEBUG : 
				print self.request.query
				print query
			
			if query is not None:
				try:
					r = query['req']
					del query['req']
					
					res = self.application.routeRequest(res, r, query)
				except KeyError as e: print e				
				
			self.set_status(res.result)
			self.finish(res.emit())
	
	class FileHandler(tornado.web.RequestHandler):
		@tornado.web.asynchronous
		def get(self, file):
			url = "%s%s" % (buildServerURL(), self.request.uri)
			if DEBUG: print url
			
			r = requests.get(url, verify=False)
			self.finish(r.content)
		
	class TaskHandler(tornado.web.RequestHandler):
		@tornado.web.asynchronous
		def post(self):
			res = Result()
			res.result = 412
			
			query = parseRequestEntity(self.request.body)				
			if query is None or len(query.keys()) != 1 or '_id' not in query.keys(): 
				self.set_status(res.result)
				self.finish(res.emit())
				return
							
			r = requests.post("%stask/" % buildServerURL(), 
				data={ '_id' : query['_id'] }, verify=False)
			
			try:
				res.data = json.loads(r.content)['data']
				res.result = 200
			except Exception as e:
				if DEBUG: print e
			
			self.set_status(res.result)
			self.finish(res.emit())
		
		@tornado.web.asynchronous
		def get(self):
			res = Result()
			res.result = 412
			
			res.data = self.application.passToAnnex(self, uri="tasks/")
			if res.data is None:
				del res.data
			elif res.data: res.result = 200
			
			self.set_status(res.result)
			self.finish(res.emit())
			
	class RouteHandler(tornado.web.RequestHandler):	
		@tornado.web.asynchronous
		def get(self, route):
			static_path = os.path.join(BASE_DIR, "web")
			module = "main"
			header = None
			footer = None

			if hasattr(self.application, "WEB_TITLE"): 
				web_title = self.application.WEB_TITLE
			else: web_title = WEB_TITLE
			
			if route is None:
				if hasattr(self.application, "INDEX_HEADER"):
					header = self.application.INDEX_HEADER
				if hasattr(self.application, "INDEX_FOOTER"):
					footer = self.application.INDEX_FOOTER
				
				idx = Template(filename=os.path.join(static_path, "index.html"))
					
			else:
				route = [r for r in route.split("/") if r != '']
				module = route[0]
				if hasattr(self.application, "MODULE_HEADER"):
					header = self.application.MODULE_HEADER
				if hasattr(self.application, "MODULE_FOOTER"):
					footer = self.application.MODULE_FOOTER
			
				idx = Template(filename=os.path.join(static_path, "module.html"))
				web_title = "%s : %s" % (web_title, module)
				
			layout = os.path.join(static_path, "layout", "%s.html" % module)
			
			if DEBUG : print (module, layout)
				
			if not os.path.exists(layout):
				# try the externals...
				layout = os.path.join(static_path, "extras", "layout", "%s.html" % module)
				if DEBUG: 
					print "could not find layout at web root.  trying externals:"
					print layout
				
			if not os.path.exists(layout):
				res = Result()
				
				self.set_status(res.result)
				self.finish(res.emit())
				return

			content = Template(filename=layout).render()

			if header is not None: header = Template(filename=header).render()
			else: header = ""
			
			if footer is not None: footer = Template(filename=footer).render()
			else: footer = ""
			
			self.finish(idx.render(web_title=web_title, 
				on_loader=self.getOnLoad(module, self.application.do_get_status(self)),
				content=content, header=header, footer=footer,
				x_token=generateSecureNonce(bottom_range=24, top_range=44)))
	
		def getOnLoad(self, module, with_status=0):
			on_loads = []
			if hasattr(self.application, "default_on_loads"):
				on_loads.extend(self.application.default_on_loads)
			
			if DEBUG: print "GETTING ONLOADS FOR STATUS %d" % with_status
			
			if hasattr(self.application, "on_loads_by_status"):
				try:
					on_loads.extend(self.application.on_loads_by_status[with_status])
				except Exception as e:
					if DEBUG: print e
					pass
				
			js = '<script type="text/javascript" src="%s?t=%d"></script>'
			if module in [k for k,v in self.application.on_loads.iteritems()]:
				on_loads.extend(self.application.on_loads[module])
			
			return "".join([js % (v, time() * 1000) for v in on_loads])

		@tornado.web.asynchronous
		def post(self, route):
			print "GETTING A ROUTE %s" % route
			res = Result()
		
			if route is not None:
				route = [r_ for r_ in route.split("/") if r_ != '']
				res = self.application.routeRequest(res, route[0], self)
						
			self.set_status(res.result)					
			self.finish(res.emit())
	
	def passToAnnex(self, handler, uri=None):
		if handler.request.body != "":
			ref = "?%s" % handler.request.body
		else:
			ref = handler.request.headers['Referer']
		query = ""
		try:
			query += ref[ref.index("?"):]
		except ValueError as e: pass

		if uri is None: uri = handler.request.uri
		url = "%s%s%s" % (buildServerURL(), uri, query)

		# TODO: verify=False ... hmm.... no.
		# TODO: also, some other xsrf stuff
		if DEBUG: print "SENDING REQUEST TO %s" % url
		r = requests.get(url, verify=False)
		
		try:
			return json.loads(r.content)['data']
		except Exception as e:
			if DEBUG: print e
		
		return None

	def routeRequest(self, result_obj, func_name, handler):
		func_name = "do_%s" % func_name
		if hasattr(self, func_name):
			if DEBUG : print "doing %s" % func_name
			func = getattr(self, func_name)
			
			result_obj.result = 200
			result_obj.data = func(handler)
		else:
			if DEBUG : print "could not find function %s" % func_name
		
		try:
			if result_obj.data is None: 
				del result_obj.data
				result_obj.result = 412
			elif 'result' in result_obj.data.keys():
				result_obj.result = result_obj.data['result']
				del result_obj.data['result']
				
		except AttributeError as e: pass

		return result_obj

	def checkForAdminParty(self):
		from conf import USER_ROOT

		has_admin = False
		for _, _, files in os.walk(USER_ROOT):
			for f in files:
				if DEBUG: print "userfile: %s" % f
				has_admin = True
				break

		if not has_admin:
			from fabric.operations import prompt
			from Utils.funcs import createNewUser

			print "WAIT: THERE IS NO ADMINISTRATOR.  LET'S FIX THIS NOW:"
			admin_username = prompt("Enter your username: ")
			admin_pwd = prompt("Enter your password: ")

			if not createNewUser(admin_username, admin_pwd, as_admin=True):
				print "SORRY, WE COULD NOT CREATE USER %s" % admin_username
		
			sleep(3)
	
	def startup(self, openurl=False):
		self.checkForAdminParty()
		UnveillanceFSEHandler.__init__(self)

		p = Process(target=self.startRESTAPI)
		p.start()

		p = Process(target=self.startAnnexObserver)
		p.start()
		
		if openurl:
			url = "http://localhost:%d/" % API_PORT
			webbrowser.open(url)
		
	def shutdown(self):
		self.stopRESTAPI()

		if hasattr(self, "annex_observer"): self.stopAnnexObserver()
	
	def startRESTAPI(self):
		if DEBUG: print "Starting REST API on port %d" % API_PORT
				
		rr_group = r"/(?:(?!%s))([a-zA-Z0-9_/]*/$)?" % "|".join(self.reserved_routes)		
		self.routes.append((re.compile(rr_group).pattern, self.RouteHandler))

		tornado.web.Application.__init__(self, self.routes,
			**{ 'cookie_secret' : UV_COOKIE_SECRET})
		
		startDaemon(self.api_log_file, self.api_pid_file)
		
		server = tornado.httpserver.HTTPServer(self)
		server.bind(API_PORT)
		server.start(NUM_PROCESSES)

		tornado.ioloop.IOLoop.instance().start()
	
	def stopRESTAPI(self):
		if DEBUG : print "shutting down REST API"
		stopDaemon(self.api_pid_file, extra_pids_port=API_PORT)

if __name__ == "__main__":
	unveillance_frontend = UnveillanceFrontend()
	openurl = False
	
	if len(argv) == 3 and argv[2] == "-webapp":
		openurl = True
		arvg.pop()
		
	if len(argv) != 2: exit("Usage: unveillance_frontend.py [-start, -stop]")
	
	if argv[1] == "-start" or argv[1] == "-firstuse":
		unveillance_frontend.startup(openurl)
	elif argv[1] == "-stop":
		unveillance_frontend.shutdown()