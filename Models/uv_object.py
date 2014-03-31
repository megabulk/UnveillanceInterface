import os
from json import dumps

from lib.Core.Models.uv_object import UnveillanceObject as UVO_Stub
from conf import ANNEX_DIR, DEBUG

class UnveillanceObject(UVO_Stub):
	def __init__(self, **args):			
		super(UnveillanceObject, self).__init__(**args)

	def save(self):
		if DEBUG: print "SAVING FROM FRONTEND"
		try:
			asset_path = os.path.join(ANNEX_DIR, self.base_path, self.file_name)
			with open(asset_path, 'wb+') as file: file.write(self.emit())
			return True
		except Exception as e: print e
		
		return False
	
	def addAsset(self, data, file_name, as_literal=True, **metadata):
		if DEBUG: print "ADDING ASSET FROM FRONTEND"
		asset_path = os.path.join(ANNEX_DIR, self.base_path, file_name)
		
		return super(UnveillanceObject, self).addAsset(data, file_name, asset_path,
			as_literal=as_literal, **metadata)