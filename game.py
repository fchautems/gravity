from ursina import *					# Import the ursina engine
from star import Star
from tree import Tree
import random
from math import *
import gc

sys.setrecursionlimit(1000)
gc.enable()

app = Ursina()						  # Initialise your Ursina app
print("execute")
max=15

listStar=[]
n=200
s=0.02

t=Tree(root=True)
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
	vx=random.uniform(-0.5, 0.5)
	vy=random.uniform(-0.5, 0.5)
	vz=random.uniform(-0.5, 0.5)
	m=random.uniform(0.01, 2.0)
	listStar.append(Star(x,y,z,vx,vy,vz,m))
	t.addStar(listStar[i])
	newcircle = Entity(model='circle', color=color.white, position=(x, y, z), scale=(s,s,s))
	circles.append(newcircle)

print(sx/n,sy/n,sz/n)

s1=Star(7.5,7.5,7.5,0,0,0,1000)
# s2=Star(1,1,1,0.1,0,0,2)
t.addStar(s1)
#t.addStar(s2)
listStar.append(s1)
# listStar.append(s2)
newcircle = Entity(model='sphere', color=color.red, position=(5,5,5), scale=(10*s,10*s,10*s))
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
		#print("1")
		t.parcoursBH()
		t.parcoursCalcul()
		
		#rint("N : ",n)
		if(listStar==None):
			print("None")
		for j in range (0,n+1):
			#print(j)
			circles[j].position=(listStar[j].getCoord()[0],listStar[j].getCoord()[1],listStar[j].getCoord()[2])
		
		#print("un")
		delete=False
		for j in range(0,n+1):
			if not(listStar[j].getCoord()[0]>50 or listStar[j].getCoord()[1]>50 or listStar[j].getCoord()[2]>50 or listStar[j].getCoord()[0]<-50 or listStar[j].getCoord()[1]<-50 or listStar[j].getCoord()[2]<-50):
				#rint("append")
				l.append(listStar[j])
				c.append(circles[j])
			else:
				delete=True
				#listeIndice.append(j)
				n=n-1
		if delete:
			print("remove",n)
		listStar=l
		circles=c
		del l
		del c
				
	except:
		print("exception")
		sys.exit()
	try:
		#print("3")
		#t=None
		#print(sys.getrefcount(t))
		#gc.collect()
		t.kill()
		t=Tree(root=True)
		for j in range (0,n+1):
			t.addStar(listStar[j])
		#print("4")
	except RecursionError:
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