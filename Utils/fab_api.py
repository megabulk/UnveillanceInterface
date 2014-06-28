from __future__ import with_statement

import os
from time import time
from fabric.api import *

from conf import DEBUG, SERVER_HOST, getSecrets

def netcat(file, save_as=None, remote_path=None):
	if DEBUG: print "NETCATTING FILE"
	
	if type(file) is str:
		if save_as is None: save_as = os.path.basename(file)
	else:
		if save_as is None: save_as = "uv_document_%d" % time()
		
	cmd = ".git/hooks/post-receive \"%s\"" % save_as
	print cmd
	
	if SERVER_HOST != "127.0.0.1":
	
		env.key_filename = [getSecrets('ssh_key_pub')]
		env.password = getSecrets('ssh_key_pwd')
		# TODO: port if not 22?
	
		annex_base = getSecrets('annex_remote')
	
		if len(remote_path) is not None:
			remote_path = os.path.join(annex_base, remote_path)
	
		res = put(file, os.path.join(remote_path, save_as))
	
		with cd(annex_base):
			res = run(cmd)
	else:
		annex_base = getSecrets('annex_local')
		
		if len(remote_path) is not None:
			remote_path = os.path.join(annex_base, remote_path)
		
		with open(os.path.join(remote_path, save_as), 'wb+') as NEW_FILE:
			NEW_FILE.write(file)
		
		this_dir = os.getcwd()
		with settings(warn_only=True):
			os.chdir(annex_base)
			res = local(cmd)
			os.chdir(this_dir)
			
	if DEBUG:
		print "*************\n\n%s\n\n*************" % res
		print "returning"
	
	return res
	