from math import *
class Tree(object):
	liste=[]
	teta=0.5
	G=0.1
	t=0.1
	
	def __init__(self, s=None,min=[.0,.0,.0],max=[1000.0,1000.0,1000.0],root=False,rootTree=None):
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

		if f==0:
			m=[a[0],a[1],a[2]]
		if f==1:
			m=[b[0],a[1],a[2]]
		if f==2:
			m=[a[0],b[1],a[2]]
		if f==3:
			m=[b[0],b[1],a[2]]
		if f==4:
			m=[a[0],a[1],b[2]]
		if f==5:
			m=[b[0],a[1],b[2]]
		if f==6:
			m=[a[0],b[1],b[2]]
		if f==7:
			m=[b[0],b[1],b[2]]
		##print("f : ",f," min : ",m, " a : ", a, " b : ", b)
		return m
	
	# calcul les coordonnées max du cadre
	def newMax(self,f):
		m=[.0,.0,.0]
		a=[(self.max[0]-self.min[0])/2.0+self.min[0],(self.max[1]-self.min[1])/2.0+self.min[1],(self.max[2]-self.min[2])/2.0+self.min[2]]
		b=[self.max[0],self.max[1],self.max[2]]
		
		if f==0:
			m=[a[0],a[1],a[2]]
		if f==1:
			m=[b[0],a[1],a[2]]
		if f==2:
			m=[a[0],b[1],a[2]]
		if f==3:
			m=[b[0],b[1],a[2]]
		if f==4:
			m=[a[0],a[1],b[2]]
		if f==5:
			m=[b[0],a[1],b[2]]
		if f==6:
			m=[a[0],b[1],b[2]]
		if f==7:
			m=[b[0],b[1],b[2]]
			
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
		
		#print("NODE : ",node,node.coord,node.star)
		#print("SELF : ",self,self.coord,self.star)
		
		return sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
	
	def calcA(self,node,f,d):
		a=[.0,.0,.0]

		x=-(node.coord[0]-self.coord[0])
		y=-(node.coord[1]-self.coord[1])
		z=-(node.coord[2]-self.coord[2])
		
		a[0]=f*x/d
		a[1]=f*y/d
		a[2]=f*z/d
		
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
			self.addA(self.rootTree.barnesHut(self))
			#self.a=
			#if self==self.rootTree:
				#print("BONJOUR :",self.a)
			#else:
				#print("AUREVOIR :",self.a)
		else:
			#print("et oui")
			for i in range(0,8):
				if self.leaf[i] is not None:
					self.leaf[i].parcoursBH()
					
	def barnesHut(self,node):
		#print("BH self :",self.star, self.root)
		#print("BH node :",node.star, node.root)
		
		a=[0.0,0.0,0.0]
		
		# c'est le même noeud donc pas de calcul de force
		if self==node:
			return a
			
		s=(self.max[0]-self.min[0])
		d=self.distance(node)
		
		# ce n'est pas un noeuf final
		if self.star is None:
			# le rapport s/d est < 0.5 on s'arrête là
			if (s/d)<Tree.teta:
				#print("S/D < TETA")
				return self.calcA(node,Tree.G*self.m/d**2,d)
			#parcourir les feuilles et sommer
			else:
				#print("AUTRE")
				for i in range(0,8):
					if self.leaf[i] is not None:
						self.addA(a,self.leaf[i].barnesHut(node))
						#a+=self.leaf[i].barnesHut(node)
			return a
		# c'est un noeud final
		else:
			return self.calcA(node,Tree.G*self.star.getMass()/d**2,d) #Tree.G*self.star.getMass()/d**2
	
	def parcoursCalcul(self,n=0):
		#print("========================== CALCUL =======================================")
		if self.star is not None:
			for i in range(0,3):
				print(i," Tree.V : ", self.v[i],"Star.V",self.star.getV()[i])
				self.v[i]=self.a[i]*Tree.t+self.star.getV()[i]
				self.coord[i]=self.v[i]*Tree.t+self.coord[i]
				self.star.setV(self.v)
				self.star.setCoord(self.coord)
				print(i," Tree.V : ", self.v[i],"Star.V",self.star.getV()[i])
				#print(n, "a :",self.a, "coord :", self.coord, "vitesse :", self.v)
				
			print("==========================")
				
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
		#print("========================== DEBUT =======================================")
		#si l'arbre est vide la racine prend les coordonnées et la masse de la première star
		if self.m==0:
			self.m=s.getMass()
			for i in range(0,3):
				self.coord[i]=s.getCoord()[i]
			#print("première :",self.coord,self.m)
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
					#Tree.liste.remove(Tree.liste[-1])
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
				
		#print("adresse coord :",id(self.coord))
		#print("========================== FIN =======================================")
