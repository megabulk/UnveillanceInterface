import os, requests, json, re
from subprocess import Popen, PIPE

from lib.Core.vars import Result
from lib.Core.Utils.funcs import parseRequestEntity

from conf import BASE_DIR, buildServerURL, DEBUG, SSH_ROOT, SERVER_HOST, CONF_ROOT, getConfig

class UnveillanceAPI():
	def __init__(self):
		print "Stock Unveillance Frontend API started..."

	def do_documents(self, handler): return self.passToAnnex(handler)

	def do_list(self, handler): return self.passToAnnex(handler)

	def do_cluster(self, handler): return self.passToAnnex(handler)
	
	def do_num_views(self, query):
		views = 0
		path = os.path.join(BASE_DIR, "web", "layout", "views", query['view_root'])
		path_e = os.path.join(BASE_DIR, "web", "extras", "layout",
			"views", query['view_root'])
			
		if DEBUG: print "GETTIN NUM VIEWS IN %s" % path
		
		for dir in [path, path_e]:			
			if os.path.exists(dir):
				for _, _, files in os.walk(dir):
					views += len(files)
					break
				
		if views != 0: return views
		else: return None
	
	def do_post_batch(self, handler, save_local=False, save_to=None):		
		# just bounce request to server/post_batch/tmp_id
		url = "%s%s" % (buildServerURL(), handler.request.uri)

		if DEBUG:
			print "POST BATCH"
			print url
		
		if not save_local:
			try:
				r = requests.post(url, files=handler.request.files)
				if DEBUG:
					print "BOUNCE:"
					print r.content
			
				return json.loads(r.content)
	
			except requests.exceptions.ConnectionError as e: print e
		else:
			data = {'addedFiles' :  []}
			for f in handler.request.files.iteritems():
				name = f[0]
				for i, file in enumerate(f[1]):
					n = name
					if i != 0: n = "%s_%d" % (n, i)
					
					if save_to is None: save_to = os.path.join(BASE_DIR, "tmp", n)
					else: save_to = os.path.join(save_to, n)
					
					data['addedFiles'].append({file['filename']: n})
					with open(save_to, "wb+") as added_file:
						added_file.write(file['body'])
			
			return data

		return None
	
	def do_init_synctask(self, handler):
		"""
		if we have a file, this is the first build step
		if we dont, and we just have a body, this is the second build step
		"""		
		if len(handler.request.files.keys()) > 0:
			return self.do_post_batch(handler, save_local=True)
		else:
			synctask = parseRequestEntity(handler.request.body)
			
			if DEBUG: print synctask
			if synctask is None: return None
			
			"""
			script and data get rsynced directly to git annex
			"""
						
		return None
	
	def do_init_annex(self, handler):
		if DEBUG:
			print "INIT ANNEX (Stock Context)"
			print handler.request
		
		credentials = parseRequestEntity(handler.request.body)
		if DEBUG: print credentials
		if credentials is None: return False
		
		"""
			1. run init_local_remote.sh
		"""
		credential_keys = ['unveillance.local_remote.folder',
			'unveillance.local_remote.password', 'unveillance.local_remote.hostname',
			'unveillance.local_remote.port', 'unveillance.local_remote.user',
			'unveillance.local_remote.remote_path', 'unveillance.local_remote.uv_uuid']
		
		cmd = [os.path.join(BASE_DIR, "init_local_remote.sh")]	
		for key in credential_keys:
			if key not in credentials.keys():
				credentials[key] = None
			cmd.append(credentials[key])
		
		if DEBUG: print cmd
		
		cmd.extend([SSH_ROOT, CONF_ROOT])		
		p = Popen(cmd, stdout=PIPE, close_fds=True)
		p_result = bool(p.stdout.read().strip())
		p.stdout.close()
		
		return p_result
	
	def do_send_public_key(self, handler):
		if DEBUG:
			print "SENDING PUBLIC KEY (stock context)"
			print handler.request