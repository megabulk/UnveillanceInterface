import threading, os
from subprocess import Popen, PIPE
from fabric.api import execute

from conf import BASE_DIR, DEBUG, getConfig

class UnveillanceFabricProcess(threading.Thread):
	def __init__(self, func, args=None, op_dir=None):
		self.func = func
		
		if args is not None: self.args = args
		else: self.args = {}
		
		self.output = None
		self.error = None
		
		uv = "unveillance.local_remote"
		uv_user = getConfig("%s.user" % uv)
		hostname = getConfig("%s.hostname" % uv)
		port = getConfig("%s.port" % uv)
		
		port_prefix = ""
		if port != 22:
			port_prefix += ":%d" % port
			
		self.args.update({
			'hosts' : ["%s@%s%s" % (uv_user, hostname, port_prefix)]
		})
		
		print self.args
		
		if op_dir is not None:
			self.return_dir = os.getcwd()
			os.chdir(op_dir)
		
		threading.Thread.__init__(self)
		self.start()
	
	def run(self):
		try:
			self.output = execute(self.func, **self.args)
		except Exception as e:			
			self.error = e
			
		if hasattr(self, "return_dir"): os.chdir(self.return_dir)
		
		