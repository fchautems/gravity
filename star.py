class Star(object):
	def __init__(self,x,y,z,vx,vy,vz,m):
		self.p=[x,y,z]
		self.v=[vx,vy,vz]
		self.m=m
		#print("constructeur V :",self.v[0],self.v[1],self.v[2],id(self.p))
	
	def getCoord(self):
		return self.p
		
	def getMass(self):
		return self.m
		
	def getV(self):
		return self.v
		
	def setCoord(self,p):
		for i in range(0,3):
			self.p[i]=p[i]
		
	def setMass(self,m):
		self.m=m
		
	def setV(self,v):
		for i in range(0,3):
			self.v[i]=v[i]
			#print("Star.setV ",self.v[i])

	def kill(self):
		del self.p
		del self.v
		del self.m
		gc.collect()