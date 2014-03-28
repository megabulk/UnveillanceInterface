import os

from lib.Core.Utils.funcs import parseRequestEntity
from conf import BASE_DIR

class UnveillanceAPI():
	def __init__(self):
		print "Stock Unveillance Frontend API started..."
	
	def do_num_views(self, query):
		path = os.path.join(BASE_DIR, "web", "layout", "views", query['view_root'])
		print "GETTIN NUM VIEWS IN %s" % path
		
		if os.path.exists(path):
			for _, _, files in os.walk(path): return len(files)
				
		return None
	
	def do_post_batch(self, request):
		print "POST BATCH"
		print request
		
		# just bouce request to server/post_batch/tmp_id
	
		return None
	
	def do_init_annex(self, request):
		print "INIT ANNEX (Stock Context)"
		print request
		
		credentials = parseRequestEntity(request.body)	
		if credentials is None: return None
		
		from subprocess import Popen
		from conf import SSH_ROOT, BASE_DIR, SERVER_HOST
		from lib.Core.Utils.funcs import hashEntireFile
		
		try:
			# 1. create keypair
			password = credentials['unveillance.local_remote.key.password']
			del credentials['unveillance.local_remote.key.password']
			
			folder = credentials['unveillance.local_remote.folder']
			del credentials['unveillance.local_remote.folder']
			
			cmd = ["ssh-keygen", "-f", 
				os.path.join(SSH_ROOT, "unveillance.local_remote.key"),
				"-t", "rsa", "-b", "4096", "-N", password]
		
			p = Popen(cmd)
			p.wait()
		
			# 2. create uuid 
			# (uuid is hash of public key)
			credentials['uuid'] = hashEntireFile(os.path.join(SSH_ROOT,
				"unveillance.local_remote.key.pub"))
			
			# 3. copy public key into batch_root
			# (so it can be picked up later)
			with open(
				os.path.join(SSH_ROOT, "unveillance.local_remote.key.pub"), 'rb') as PK:
				self.do_post_batch({
					'files' : [("unveillance.local_remote.key.pub", PK.read())],
					'url' : "http://%s/post_batch/%s/" % (SERVER_HOST,
						credentials['batch_root'])
				})
			
			# 4. save password, folder to config
			from Utils.funcs import updateConfig
			updateConfig({
				'unveillance.local_remote.key.password' : password,
				'unveillance.local_remote.folder' : folder
			})
						
		except Exception as e:
			print e
			return None
		
		return None