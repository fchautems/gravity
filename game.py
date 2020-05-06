from ursina import *					# Import the ursina engine
from star import Star
from tree import Tree
import random
from math import *

app = Ursina()						  # Initialise your Ursina app
print("execute")
max=5

listStar=[]
n=2
s=0.02

t=Tree(root=True)
circles=[]

window.title = 'My Game'				# The window title
window.borderless = False			   # Show a border
window.fullscreen = False			   # Do not go Fullscreen
window.exit_button.visible = False	  # Do not show the in-game red X that loses the window
window.fps_counter.enabled = True 

# for i in range (0,n):
	# d=random.uniform(0.0, 1.0)
	# a=random.uniform(0.0, 2*pi)
	# b=random.uniform(0.0, 2*pi)
	# x1=cos(b)*d
	# z=sin(b)*d
	# x=cos(a)*x1
	# y=sin(a)*x1
	# x=max*(x+1)/2
	# y=max*(y+1)/2
	# z=max*(z+1)/2
	# print(x,y,z)
	# vx=random.uniform(-0.001, 0.001)
	# vy=random.uniform(-0.001, 0.001)
	# vz=random.uniform(-0.001, 0.001)
	# m=random.uniform(0.01, 0.1)
	# listStar.append(Star(x,y,z,vx,vy,vz,m))
	# t.addStar(listStar[i])
	# newcircle = Entity(model='circle', color=color.red, position=(x, y, z), scale=(s,s,s))
	# circles.append(newcircle)
	

s1=Star(5,2,1,-0,0,0,2)
s2=Star(1,1,1,0,5,5,2)
t.addStar(s1)
t.addStar(s2)
listStar.append(s1)
listStar.append(s2)
newcircle = Entity(model='circle', color=color.red, position=(5,2,1), scale=(s,s,s))
circles.append(newcircle)                                    
newcircle = Entity(model='circle', color=color.red, position=(1,1,1), scale=(s,s,s))
circles.append(newcircle)

camera.position = (4.5,4.5,-20)	
print(camera.position)

	# if held_keys['w']:                           
		# camera.position += (0, 0.5, 0)           # move up verticallyq
		# print(camera.position)
	# if held_keys['s']:                           
		# camera.position -= (0, 0.5, 0)           # move down vertically
		# print(camera.position)
	# if held_keys['a']:                           
		# camera.position += (0.5, 0, 0)           # move left
		# print(camera.position)
	# if held_keys['d']:                           
		# camera.position -= (0.5, 0, 0)           # move right
		# print(camera.position)
	# if held_keys['r']:                          
		# camera.position += (0,0, 0.5)            # zoom in
		# print(camera.position)
		
def update():
	global t
	global circles
	global n
	#if held_keys['f']:                          
	# camera.position -= (0,0, 0.5)            # zoom out
	#print(camera.position)
	#print("BOUCLE :")
	
	if held_keys['f']:
		print("rien")
		
	t.parcoursBH()
	t.parcoursCalcul()
	for j in range (0,n):
		#print(circles[j].position)
		circles[j].position=(listStar[j].getCoord()[0],listStar[j].getCoord()[1],listStar[j].getCoord()[2])
		#print("POSITION :",listStar[j].getCoord()[0],listStar[j].getCoord()[1],listStar[j].getCoord()[2])
		#print("VITESSE :",listStar[j].getV()[0],listStar[j].getV()[1],listStar[j].getV()[2])
		#print("POSITION :",listStar[j].getCoord()[0],listStar[j].getCoord()[1],listStar[j].getCoord()[2])
	
	t=Tree(root=True)
	for j in range (0,n):
		t.addStar(listStar[j])
				
app.run()

#class Game(object):
# def __init__(self):
	# t=Tree(root=True)
		
#def main():
		
# if __name__ == '__main__':
	# main()