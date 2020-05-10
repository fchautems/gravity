from ursina import *					# Import the ursina engine
from star import Star
from tree import Tree
import random
from math import *
import gc
import timeit

# 0.16
# amelioration distance : 0.12
# retour calcA remplace par calcul direct : 0.95
# plus d'appel a addA : 0.85

sys.setrecursionlimit(1000)
gc.enable()

app = Ursina()						  # Initialise your Ursina app
print("execute")
print(timeit.timeit('output = 10*5'))
max=15

sizeC=30

listStar=[]
n=200
s=0.02

a=[0.0,0.0,0.0]

b=[3.0,3.0,3.0]

starttime = timeit.default_timer()
for k in range (0,100000):
	for i in range(0,3):
		a[i]=1.0
		
#print(a)
print("Temps de boucle :", timeit.default_timer() - starttime)


starttime = timeit.default_timer()
for k in range (0,100000):
	a[0]=2
	a[1]=2
	a[2]=2
		
#print(a)
print("Temps de boucle :", timeit.default_timer() - starttime)

sa=Tree()
sa.setCoord(1.0,2.0,3.0)

sb=Tree()
sb.setCoord(4.0,-5.0,1.0)

def d1(self,node):
	x1=node.coord[0]
	y1=node.coord[1]
	z1=node.coord[2]
		
	x2=self.coord[0]
	y2=self.coord[1]
	z2=self.coord[2]
	
	d=sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
	
	return sqrt((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)
	
def d2(self,node):
	return sqrt((node.coord[0]-self.coord[0])**2+(node.coord[1]-self.coord[1])**2+(node.coord[2]-self.coord[2])**2)

asdf=0.0

starttime = timeit.default_timer()
for k in range (0,100000):
	asdf=d1(sa,sb)
print("Temps de boucle :", timeit.default_timer() - starttime)

starttime = timeit.default_timer()
for k in range (0,100000):
	asdf=d2(sa,sb)
print("Temps de boucle :", timeit.default_timer() - starttime)

a1=0.0
b1=1.0
c1=2.3
starttime = timeit.default_timer()
for k in range (0,100000):
	a1=b1/c1**3
print("Temps de boucle :", timeit.default_timer() - starttime)

starttime = timeit.default_timer()
for k in range (0,100000):
	a1=b1/c1/c1/c1
print("Temps de boucle :", timeit.default_timer() - starttime)


#sys.exit()

def BH(t): 
    t.parcoursBH()
	
def calcul(t):
	t.parcoursCalcul()

t=Tree(None,[-sizeC,-sizeC,-sizeC],[sizeC,sizeC,sizeC],root=True)
circles=[]

window.title = 'My Game'				# The window title
window.borderless = False			   # Show a border
window.fullscreen = False			   # Do not go Fullscreen
window.exit_button.visible = False	  # Do not show the in-game red X that loses the window
window.fps_counter.enabled = True 

sx=0
sy=0
sz=0

for i in range (0,n):
	d=random.uniform(0.0, 1.0)
	a=random.uniform(0.0, 2*pi)
	b=random.uniform(0.0, 2*pi)
	x1=cos(b)*d
	z=sin(b)*d
	x=cos(a)*x1
	y=sin(a)*x1
	x=max*(x+1)/2
	y=max*(y+1)/2
	z=max*(z+1)/2
	print(x,y,z)
	sx+=x
	sy+=y
	sz+=z
	vx=random.uniform(-0.03, 0.03)
	vy=random.uniform(-0.03, 0.03)
	vz=random.uniform(-0.03, 0.03)
	m=random.uniform(0.001, 0.002)
	listStar.append(Star(x,y,z,vx,vy,vz,m))
	t.addStar(listStar[i])
	newcircle = Entity(model='circle', color=color.white, position=(x, y, z), scale=(s,s,s))
	circles.append(newcircle)

print(sx/n,sy/n,sz/n)

s1=Star(7.5,7.5,7.5,0,0,0,0.002)
# s2=Star(1,1,1,0.1,0,0,2)
t.addStar(s1)
#t.addStar(s2)
listStar.append(s1)
# listStar.append(s2)
newcircle = Entity(model='sphere', color=color.white, position=(5,5,5), scale=(1*s,1*s,1*s))
circles.append(newcircle)                                    
# newcircle = Entity(model='circle', color=color.red, position=(1,1,1), scale=(s,s,s))
# circles.append(newcircle)

camera.position = (7.5,7.5,-20)	
print(camera.position)
		
def update():
	global t
	global circles
	global n
	global listStar
	#if held_keys['f']:                          
	# camera.position -= (0,0, 0.5)            # zoom out
	#print(camera.position)
	#print("BOUCLE :")
	
	#if held_keys['f']:
	#print("rien")
	
	if held_keys['w']:                           
		camera.position += (0, 0.1, 0)           # move up verticallyq
		# print(camera.position)
	if held_keys['s']:                           
		camera.position -= (0, 0.1, 0)           # move down vertically
		# print(camera.position)
	if held_keys['a']:                           
		camera.position -= (0.1, 0, 0)           # move left
		# print(camera.position)
	if held_keys['d']:                           
		camera.position += (0.1, 0, 0)           # move right
		# print(camera.position)
	if held_keys['r']:                          
		camera.position += (0,0, 0.3)            # zoom in
		# print(camera.position)
	if held_keys['f']:                          
		camera.position -= (0,0, 0.3)            # zoom in
		# print(camera.position)
	
	try:
		l=[]
		c=[]

		# t.parcoursBH()
		# t.parcoursCalcul()
		
		starttime = timeit.default_timer()
		#print("The start time is :",starttime)
		BH(t)
		print("Temps de parcoursBH :", timeit.default_timer() - starttime)

		starttime = timeit.default_timer()
		#print("The start time is :",starttime)
		calcul(t)
		print("Temps de parcoursCalcul :", timeit.default_timer() - starttime)
			
		starttime = timeit.default_timer()
		for j in range (0,n+1):
			#print(j)
			circles[j].position=(listStar[j].getCoord()[0],listStar[j].getCoord()[1],listStar[j].getCoord()[2])
		print("Temps d'affichage des cercle is :", timeit.default_timer() - starttime)
		
		#print("un")
		starttime = timeit.default_timer()
		delete=False
		for j in range(0,n+1):
			if not(listStar[j].getCoord()[0]>sizeC or listStar[j].getCoord()[1]>sizeC or listStar[j].getCoord()[2]>sizeC or listStar[j].getCoord()[0]<-sizeC or listStar[j].getCoord()[1]<-sizeC or listStar[j].getCoord()[2]<-sizeC):
				#rint("append")
				l.append(listStar[j])
				c.append(circles[j])
			else:
				delete=True
				#listeIndice.append(j)
				n=n-1
		print("Temps suppression :", timeit.default_timer() - starttime)
		if delete:
			print("remove",n)
		listStar=l
		circles=c
		del l
		del c
		starttime = timeit.default_timer()
		t.kill()
		print("Kill :", timeit.default_timer() - starttime)
		t=t=Tree(None,[-sizeC,-sizeC,-sizeC],[sizeC,sizeC,sizeC],root=True)
		
		starttime = timeit.default_timer()
		for j in range (0,n+1):
			t.addStar(listStar[j])
		print("Temps de création du nouvel arbre :", timeit.default_timer() - starttime)
	except:
		#t=Tree(root=True)
		for j in range (0,n+1):
			print(listStar[j].getCoord())
		print(t.parcours())
		print("AUREVOIR")
		sys.exit()
				
app.run()

#class Game(object):
# def __init__(self):
	# t=Tree(root=True)
		
#def main():
		
# if __name__ == '__main__':
	# main()