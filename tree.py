from math import *
import timeit
#import numpy

class Tree(object):
	liste=[]
	teta=0.6
	G=0.015
	t=0.1
	
	def __init__(self, s=None,min=[-500.0,-500.0,-500.0],max=[500.0,500.0,500.0],root=False,rootTree=None):
		self.root=root
		if root:
			##print("c'est le root !")
			self.rootTree=self
		else:
			##print("une feuille")
			self.rootTree=rootTree
		
		self.star=s
		self.min=min
		self.max=max
		self.leaf=[None,None,None,None,None,None,None,None]
		self.m=0
		
		#accélération
		self.a=[0.0,0.0,0.0]
		self.v=[0.0,0.0,0.0]
		self.coord=[.0,.0,.0]

		# la masse d'un noeud est la somme de tout ce qui se trouve en dessous.
		# les coordonnées sont équivalent au centre de gravité.
		# le tout est initialisé à zéro, sauf s'il y a une étoile (noeud final)
		if s is not None:
			self.m=s.getMass()
			for i in range(0,3):
				self.coord[i]=s.getCoord()[i]
			#print("initialisation coordonnées : ",s.getCoord())
		else:
			self.m=0
			self.coord=[.0,.0,.0]
			
	def setCoord(self,x,y,z):
		self.coord[0]=x
		self.coord[1]=y
		self.coord[2]=z
		
	def kill(self):
		del self.root
		del self.star
		del self.min
		del self.max
		del self.m
		del self.a
		del self.v
		del self.coord
		#del self.star
		vide=True
		for i in range(0,8):
			if self.leaf[i] is not None:
				vide=False
				self.leaf[i].kill()
		if vide:
			del self.leaf
	
	# retourne le cadre dans lequel se trouve une étoile	
	def frameNumber(self,s=None):
		if s is None:
			p=self.star.getCoord()
		else:
			p=s.getCoord()
		f=0
		for i in range(0,3):
			if p[i]>((self.max[i]-self.min[i])/2.0+self.min[i]):
				f=f+2**i
		return f

	# calcul les coordonnées min du cadre
	def newMin(self,f):
		m=[.0,.0,.0]
		a=[self.min[0],self.min[1],self.min[2]]
		b=[(self.max[0]-self.min[0])/2.0+self.min[0],(self.max[1]-self.min[1])/2.0+self.min[1],(self.max[2]-self.min[2])/2.0+self.min[2]]

		def f0():
			return [a[0],a[1],a[2]]
		def f1():
			return [b[0],a[1],a[2]]
		def f2():
			return [a[0],b[1],a[2]]
		def f3():
			return [b[0],b[1],a[2]]
		def f4():
			return [a[0],a[1],b[2]]
		def f5():
			return [b[0],a[1],b[2]]
		def f6():
			return [a[0],b[1],b[2]]
		def f7():
			return [b[0],b[1],b[2]]

		# map the inputs to the function blocks
		options = {0 : f0,
				   1 : f1,
				   2 : f2,
				   3 : f3,
				   4 : f4,
				   5 : f5,
				   6 : f6,
				   7 : f7,
		}

		m=options[f]()
		#OPTIMISATION
		# if f==0:
			# m=[a[0],a[1],a[2]]
		# if f==1:
			# m=[b[0],a[1],a[2]]
		# if f==2:
			# m=[a[0],b[1],a[2]]
		# if f==3:
			# m=[b[0],b[1],a[2]]
		# if f==4:
			# m=[a[0],a[1],b[2]]
		# if f==5:
			# m=[b[0],a[1],b[2]]
		# if f==6:
			# m=[a[0],b[1],b[2]]
		# if f==7:
			# m=[b[0],b[1],b[2]]
		##print("f : ",f," min : ",m, " a : ", a, " b : ", b)
		return m
	
	# calcul les coordonnées max du cadre
	def newMax(self,f):
		m=[.0,.0,.0]
		a=[(self.max[0]-self.min[0])/2.0+self.min[0],(self.max[1]-self.min[1])/2.0+self.min[1],(self.max[2]-self.min[2])/2.0+self.min[2]]
		b=[self.max[0],self.max[1],self.max[2]]
		
		def f0():
			return [a[0],a[1],a[2]]
		def f1():
			return [b[0],a[1],a[2]]
		def f2():
			return [a[0],b[1],a[2]]
		def f3():
			return [b[0],b[1],a[2]]
		def f4():
			return [a[0],a[1],b[2]]
		def f5():
			return [b[0],a[1],b[2]]
		def f6():
			return [a[0],b[1],b[2]]
		def f7():
			return [b[0],b[1],b[2]]

		# map the inputs to the function blocks
		options = {0 : f0,
				   1 : f1,
				   2 : f2,
				   3 : f3,
				   4 : f4,
				   5 : f5,
				   6 : f6,
				   7 : f7,
		}

		m=options[f]()
		
		#OPTIMISATION
		# if f==0:
			# m=[a[0],a[1],a[2]]
		# if f==1:
			# m=[b[0],a[1],a[2]]
		# if f==2:
			# m=[a[0],b[1],a[2]]
		# if f==3:
			# m=[b[0],b[1],a[2]]
		# if f==4:
			# m=[a[0],a[1],b[2]]
		# if f==5:
			# m=[b[0],a[1],b[2]]
		# if f==6:
			# m=[a[0],b[1],b[2]]
		# if f==7:
			# m=[b[0],b[1],b[2]]
			
		##print("f : ",f," max : ",m, " a : ", a, " b : ", b)
		return m
		
	# calcul la distance entre noeud courant et noeud passé en paramètres
	def distance(self,node):
		x1=node.coord[0]
		y1=node.coord[1]
		z1=node.coord[2]
			
		x2=self.coord[0]
		y2=self.coord[1]
		z2=self.coord[2]
		
		return sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
	
	def calcA(self,node,f,d):
		a=[.0,.0,.0]
		
		a[0]=f*(self.coord[0]-node.coord[0])/d
		a[1]=f*(self.coord[1]-node.coord[1])/d
		a[2]=f*(self.coord[2]-node.coord[2])/d
		
		return a
		
	def addA(self,a1,a2=None):
		if a2 is None:
			self.a[0]+=a1[0]
			self.a[1]+=a1[1]
			self.a[2]+=a1[2]
		else:
			a1[0]+=a2[0]
			a1[1]+=a2[1]
			a1[2]+=a2[2]
	
	def parcoursBH(self):
		if self.star is not None:
			a=self.rootTree.barnesHut(self)
			self.a[0]+=a[0]
			self.a[1]+=a[1]
			self.a[2]+=a[2]
			#OPTIMISATION
			#self.addA(self.rootTree.barnesHut(self))
		else:
			#print("et oui")
			for i in range(0,8):
				if self.leaf[i] is not None:
					self.leaf[i].parcoursBH()
					
	def barnesHut(self,node):
		a=[0.0,0.0,0.0]
		
		# c'est le même noeud donc pas de calcul de force
		if self==node:
			return a
		
		d=sqrt((node.coord[0]-self.coord[0])**2+(node.coord[1]-self.coord[1])**2+(node.coord[2]-self.coord[2])**2)
		#OPTIMISATION
		#d=self.distance(node)
		if d==0.0:
			return a
		
		# ce n'est pas un noeuf final
		if self.star is None:
			s=(self.max[0]-self.min[0])
			# le rapport s/d est < 0.5 on s'arrête là
			print(s,d)
			if (s/d)<Tree.teta:
				#OPTIMISATION
				#return self.calcA(node,Tree.G*self.m/d**2,d)
				return [(self.coord[0]-node.coord[0])*Tree.G*self.m/d/d/d,(self.coord[1]-node.coord[1])*Tree.G*self.m/d/d/d,(self.coord[2]-node.coord[2])*Tree.G*self.m/d/d/d]
			#parcourir les feuilles et sommer
			else:
				for i in range(0,8):
					if self.leaf[i] is not None:
						a2=self.leaf[i].barnesHut(node)
						a[0]+=a2[0]
						a[1]+=a2[1]
						a[2]+=a2[2]
						# OPTIMISATION
						# self.addA(a,self.leaf[i].barnesHut(node))

			return a
		# c'est un noeud final
		else:
			#print("LA MASSE : ",self.star.getMass(),self.m)
			return [(self.coord[0]-node.coord[0])*Tree.G*self.m/d/d/d,(self.coord[1]-node.coord[1])*Tree.G*self.m/d/d/d,(self.coord[2]-node.coord[2])*Tree.G*self.m/d/d/d]
			#OPTIMISATION
			#return [(self.coord[0]-node.coord[0])*Tree.G*self.star.getMass()/d/d/d,(self.coord[1]-node.coord[1])*Tree.G*self.star.getMass()/d/d/d,(self.coord[2]-node.coord[2])*Tree.G*self.star.getMass()/d/d/d]
			#return self.calcA(node,Tree.G*self.star.getMass()/d**2,d) #Tree.G*self.star.getMass()/d**2
	
	def parcoursCalcul(self,n=0):
		if self.star is not None:
			for i in range(0,3):
				self.v[i]=self.a[i]*Tree.t+self.star.getV()[i]
				self.coord[i]=self.v[i]*Tree.t+self.coord[i]
			
			self.star.setV(self.v)
			self.star.setCoord(self.coord)
				
		for i in range(0,8):
			if self.leaf[i] is not None:
				self.leaf[i].parcoursCalcul(n+1)
				
	def parcours(self,n=0):
		print("parcours")
		print(n,"adresse coord :",id(self.coord))
		if self.star is not None:
			print(n, self, "a :",self.a, "coord :", self.coord,self.star.getCoord(),self.m, self.star.getMass())
		for i in range(0,8):
			if self.leaf[i] is not None:
				self.leaf[i].parcours(n+1)
				
	def addStar(self,s):
		#si l'arbre est vide la racine prend les coordonnées et la masse de la première star
		if self.m==0:
			self.m=s.getMass()
			for i in range(0,3):
				self.coord[i]=s.getCoord()[i]
		#sinon la masse est ajoutée et le nouveau centre de gravité est calculé
		else:
			for i in range(0,3):
				#print("barycentre : ",(s.getCoord()[i]*s.getMass()+self.coord[i]*self.m)/(s.getMass()+self.m))
				#print(s.getCoord()[i],s.getMass(),self.coord[i],self.m,s.getMass(),self.m)
				#print("fin barycentre")
				self.coord[i]=(s.getCoord()[i]*s.getMass()+self.coord[i]*self.m)/(s.getMass()+self.m)
			self.m+=s.getMass()
			
		#si c'est la racine
		if self.root:
			#print("c'est la racine : ",self.star)
			#le numéro du cadre où se trouve la star
			newStarF=self.frameNumber(s)
			#print("newStar :",newStarF)
			#s'il n'y a pas d'étoile dans ce cadre (branche vide)
			if self.leaf[newStarF] is None:
				#print("pas d'étoile dans le cadre")
				t=Tree(s,self.newMin(newStarF),self.newMax(newStarF),rootTree=self.rootTree)
				Tree.liste.append(t)
				self.leaf[newStarF]=t
			else:
				#print("déjà une étoile")
				self.leaf[newStarF].addStar(s)
		else:
			#print("c'est pas la racine")
			#print("m : ",self.m,"coord : ",self.coord)
			newStarF=self.frameNumber(s)

			if self.star is not None:
				#print("NOEUD FINAL")
				currentStarF=self.frameNumber()
				#print("c : ",currentStarF," n : ",newStarF) 
				if self.leaf[currentStarF] is None:
					#print("|1|")
					t=Tree(self.star,self.newMin(currentStarF),self.newMax(currentStarF),rootTree=self.rootTree)
					Tree.liste.append(t)
					self.leaf[currentStarF]=t
				else:
					#print("|2|")
					self.leaf[currentStarF].addStar(self.star)
				self.star=None
				Tree.liste.pop(-1)
				
			#print(" n : ",newStarF)
			if self.leaf[newStarF] is None:
				#print("|3|")
				t=Tree(s,self.newMin(newStarF),self.newMax(newStarF),rootTree=self.rootTree)
				Tree.liste.append(t)
				self.leaf[newStarF]=t
			else:
				#print("|4|")
				self.leaf[newStarF].addStar(s)