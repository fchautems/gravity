from ursina import *					# Import the ursina engine
from gravityT import GravityT
import sys
# 0.16
# amelioration distance : 0.12
# retour calcA remplace par calcul direct : 0.95
# plus d'appel a addA : 0.85

#a=marshal.load(open("camera.txt", "rb")) ## Rechargement du dictionnaire
#print(a)
#sys.exit()

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
	
thread=GravityT()
thread.__init__()

circles=[]

s=0.02

b=True
while b:
	a=thread.getListCoord()
	if a is not None:
		b=False


app = Ursina()

window.title = 'My Game'				# The window title
window.borderless = False			   # Show a border
window.fullscreen = False			   # Do not go Fullscreen
window.exit_button.visible = False	  # Do not show the in-game red X that loses the window
window.fps_counter.enabled = True 

cx=3
cy=4
cz=-20
camera.position = (cx,cy,cz)	

cpt=0

Sky(color=color.black)
	
def update():
	global cpt
	global thread
	#gc.collect()

	col=Color(0, 0, 0.25, 1)	
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
	if cpt==0:
		thread.start()
	cpt+=1
	
	
	for i in a:
		newcircle = Entity(model='circle', color=Color(1,1,1,1), position=(i[0], i[1], i[2]), scale=(s,s,s))
		circles.append(newcircle)
	
	# # affichage des cercles
	# for j in range (0,n):
		# self.circles[j].position=(self.listStar[j].getCoord()[0],self.listStar[j].getCoord()[1],self.listStar[j].getCoord()[2])
		# self.circles[j].color=Color(1*bright(self.listStar[j].getCoord()[2]),1*bright(self.listStar[j].getCoord()[2]),1*bright(self.listStar[j].getCoord()[2]),1)

	
	#thread.stop()
				
app.run()
