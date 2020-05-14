from threading import Thread
import random
from star import Star
from tree import Tree
from math import *
import gc
import timeit
import marshal
import time
import sys
from ursina import *


def bright(x):
	if x<-5:
		return 1
		print("ca arrive")
	if x>10:
		print("la aussi")
		return 0.1
	a=0.004
	b=0.04
	c=0.2
	return a*x**2+b*x+c

class GravityT(Thread):

	def __init__(self):
		#self.stopped = False
		Thread.__init__(self)		
		sys.setrecursionlimit(1000)
		gc.enable()
		
		print("un")
		self.sizeC=30
		self.t=Tree(None,[-self.sizeC,-self.sizeC,-self.sizeC],[self.sizeC,self.sizeC,self.sizeC],root=True)
		self.circles=[]
		self.l=[]
		self.c=[]
		self.listStar=[]
		self.n=100
		print("deux")
		
		s=0.02
		max=15
		
		col=Color(0, 0, 0.25, 1)

		sx=0
		sy=0
		sz=0

		for i in range (0,1):
			d=random.uniform(0.0, 1.0)
			a=random.uniform(0.0, 2*pi)
			b=random.uniform(0.0, 2*pi)
			x1=cos(b)*d
			z=sin(b)*d
			x=cos(a)*x1
			y=sin(a)*x1
			x=max*(x+1)/3
			y=max*(y+1)/3+2
			z=max*(z+1)/3
			sx+=x
			sy+=y
			sz+=z
			
			R=random.uniform(-1, 1)
			
			if R<0:
				pq=-1
			else:
				pq=1
			
			vx=random.uniform(0, 0.0*pq)
			vy=random.uniform(0, 0.0*pq)
			vz=random.uniform(0, 0.0*pq)
			m=random.uniform(0.1, 0.1)
			self.listStar.append(Star(x,y,z,vx,vy,vz,m))
			self.t.addStar(self.listStar[i])
			print("1")
			newcircle = Entity(model='circle', color=Color(1,1,1,bright(z)), position=(x, y, z), scale=(s,s,s))
			self.circles.append(newcircle)
			
			
		for i in range (1,self.n):
			d=random.uniform(0.0, 1.0)
			a=random.uniform(0.0, 2*pi)
			b=random.uniform(0.0, 2*pi)
			x1=cos(b)*d
			z=sin(b)*d
			x=cos(a)*x1
			y=sin(a)*x1
			x=max*(x+1)/3
			y=max*(y+1)/3+2
			z=max*(z+1)/3
			sx+=x
			sy+=y
			sz+=z
			vx=random.uniform(-0.03, 0.03)
			vy=random.uniform(0.03, 0.03)
			vz=random.uniform(-0.03, 0.03)
			m=random.uniform(0.0000001, 0.0000001)
			self.listStar.append(Star(x,y,z,vx,vy,vz,m))
			self.t.addStar(self.listStar[i])
			newcircle = Entity(model='circle', color=col, position=(x, y, z), scale=(s,s,s))
			self.circles.append(newcircle)

		#print(sx/n,sy/n,sz/n)

		s1=Star(7.5,7.5,7.5,0,0,0,0.002)
		self.t.addStar(s1)
		self.listStar.append(s1)
		newcircle = Entity(model='sphere', color=col, position=(5,5,5), scale=(1*s,1*s,1*s))
		self.circles.append(newcircle)                                    
		
	def run(self):
		# global col
		# global n
		# #global listStar
		# #global t
		# global self.l=[]
		# global self.c=[]
		
		n=100
		#try:

		for k in range (1,1000):
			starttime = timeit.default_timer()
			print("2")
			self.t.parcoursBH()
			print("Temps de parcoursBH :", timeit.default_timer() - starttime)

			starttime = timeit.default_timer()
			self.t.parcoursCalcul()
			print("Temps de parcoursCalcul :", timeit.default_timer() - starttime)
				
			# minZ=100
			# maxZ=-100
			# mean=0
			# for j in range (0,n+1):
				# if listStar[j].getCoord()[2]>maxZ:
					# maxZ=listStar[j].getCoord()[2]
				# if listStar[j].getCoord()[2]<minZ:
					# minZ=listStar[j].getCoord()[2]
				# mean+=listStar[j].getCoord()[2]
			# mean=mean/(n+1)				
			# print("print :",minZ,maxZ,mean)
			
			starttime = timeit.default_timer()
			for j in range (0,n+1):
				self.circles[j].position=(self.listStar[j].getCoord()[0],self.listStar[j].getCoord()[1],self.listStar[j].getCoord()[2])
				self.circles[j].color=Color(1*bright(self.listStar[j].getCoord()[2]),1*bright(self.listStar[j].getCoord()[2]),1*bright(self.listStar[j].getCoord()[2]),1)
			print("Temps d'affichage des cercle is :", timeit.default_timer() - starttime)
			
			starttime = timeit.default_timer()
			delete=False
			for j in range(0,n+1):
				if not(self.listStar[j].getCoord()[0]>self.sizeC or self.listStar[j].getCoord()[1]>self.sizeC or self.listStar[j].getCoord()[2]>self.sizeC or self.listStar[j].getCoord()[0]<-self.sizeC or self.listStar[j].getCoord()[1]<-self.sizeC or self.listStar[j].getCoord()[2]<-self.sizeC):
					self.l.append(self.listStar[j])
					self.c.append(self.circles[j])
				else:
					delete=True
					n=n-1
			if delete:
				print("remove",n)
			self.listStar=self.l
			self.circles=self.c
			del self.l
			del self.c
			self.t.kill()
			self.t=Tree(None,[-self.sizeC,-self.sizeC,-self.sizeC],[self.sizeC,self.sizeC,self.sizeC],root=True)
					
			etat=[]
			#print("asdfdsfasdfasdfasdfsdaf")
			# creation du nouvel arbre
			for j in range (0,n+1):
				self.t.addStar(self.listStar[j])
				etat.append(self.listStar[j].getCoord())
			
			#sauvegarde des coordonnees dans un fichier
			marshal.dump(etat, open("etat", 'wb')) 
			#del etat
				
			# except Exception as e:
				# print(e)
				# # for j in range (0,n+1):
					# # print(listStar[j].getCoord())
				# #print(t.parcours())
				# print("AUREVOIR")
				# sys.exit()