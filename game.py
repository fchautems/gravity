from ursina import *  # Import the ursina engine
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

app = Ursina()  # Initialise your Ursina app
print("execute")
print(timeit.timeit('output = 10*5'))
max = 15

sizeC = 30

listStar: [Star] = []
n = 200
s = 0.02

a = [0.0, 0.0, 0.0]

b = [3.0, 3.0, 3.0]

starttime = timeit.default_timer()
for k in range(0, 100000):
    for i in range(0, 3):
        a[i] = 1.0

print("Temps de boucle :", timeit.default_timer() - starttime)

starttime = timeit.default_timer()
for k in range(0, 100000):
    a[0] = 2
    a[1] = 2
    a[2] = 2

# print(a)
print("Temps de boucle :", timeit.default_timer() - starttime)

sa = Tree()
sa.setCoord(1.0, 2.0, 3.0)

sb = Tree()
sb.setCoord(4.0, -5.0, 1.0)


# calcul la distance entre noeud courant et noeud passé en paramètres
def dist(s1: Star, s2: Star):
    x1 = s1.getCoord()[0]
    y1 = s1.getCoord()[1]
    z1 = s1.getCoord()[2]

    x2 = s2.getCoord()[0]
    y2 = s2.getCoord()[1]
    z2 = s2.getCoord()[2]

    return sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)


def d1(self, node):
    x1 = node.coord[0]
    y1 = node.coord[1]
    z1 = node.coord[2]

    x2 = self.coord[0]
    y2 = self.coord[1]
    z2 = self.coord[2]

    return sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)


def d2(self, node):
    return sqrt((node.coord[0] - self.coord[0]) ** 2 + (node.coord[1] - self.coord[1]) ** 2 + (
            node.coord[2] - self.coord[2]) ** 2)


def BH(t):
    t.parcoursBH()


def calcul(t):
    t.parcoursCalcul()


t = Tree(None, [-sizeC, -sizeC, -sizeC], [sizeC, sizeC, sizeC], root=True)
circles = []

window.title = 'My Game'  # The window title
window.borderless = False  # Show a border
window.fullscreen = False  # Do not go Fullscreen
window.exit_button.visible = False  # Do not show the in-game red X that loses the window
window.fps_counter.enabled = True

sx = 0
sy = 0
sz = 0

for i in range(0, n):
    d = random.uniform(0.0, 1.0)
    a = random.uniform(0.0, 2 * pi)
    b = random.uniform(0.0, 2 * pi)
    x1 = cos(b) * d
    z = sin(b) * d
    x = cos(a) * x1
    y = sin(a) * x1
    x = max * (x + 1) / 2
    y = max * (y + 1) / 2
    z = max * (z + 1) / 2
    print(x, y, z)
    sx += x
    sy += y
    sz += z
    vx = random.uniform(-0.03, 0.03)
    vy = random.uniform(-0.03, 0.03)
    vz = random.uniform(-0.03, 0.03)
    m = random.uniform(0.001, 0.002)
    listStar.append(Star(x, y, z, vx, vy, vz, m))
    t.addStar(listStar[i])
    newcircle = Entity(model='circle', color=color.white, position=(x, y, z), scale=(s, s, s))
    circles.append(newcircle)

camera.position = (7.5, 7.5, -20)
print("asdf")

def update():
    global t
    global circles
    global n
    global listStar

    if held_keys['w']:
        camera.position += (0, 0.1, 0)  # move up vertically
    if held_keys['s']:
        camera.position -= (0, 0.1, 0)  # move down vertically
    if held_keys['a']:
        camera.position -= (0.1, 0, 0)  # move left
    if held_keys['d']:
        camera.position += (0.1, 0, 0)  # move right
    if held_keys['r']:
        camera.position += (0, 0, 0.3)  # zoom in
    if held_keys['f']:
        camera.position -= (0, 0, 0.3)  # zoom in

    try:
        print("BONjour")
        l = []
        c = []

        starttime = timeit.default_timer()
        # print("The start time is :",starttime)
        t.parcoursBH()
        print("Temps de parcoursBH :", timeit.default_timer() - starttime)

        starttime = timeit.default_timer()
        # print("The start time is :",starttime)
        t.parcoursCalcul()
        print("Temps de parcoursCalcul :", timeit.default_timer() - starttime)

        starttime = timeit.default_timer()
        for j in range(0, n):
            # print(j)
            circles[j].position = (listStar[j].getCoord()[0], listStar[j].getCoord()[1], listStar[j].getCoord()[2])
        print("Temps d'affichage des cercle is :", timeit.default_timer() - starttime)

        starttime = timeit.default_timer()
        delete = False
        for j in range(0, n):
            if not (listStar[j].getCoord()[0] > sizeC or listStar[j].getCoord()[1] > sizeC or listStar[j].getCoord()[
                2] > sizeC or listStar[j].getCoord()[0] < -sizeC or listStar[j].getCoord()[1] < -sizeC or
                    listStar[j].getCoord()[2] < -sizeC):
                l.append(listStar[j])
                c.append(circles[j])
            else:
                delete = True
                n = n - 1
        print("Temps suppression :", timeit.default_timer() - starttime)
        if delete:
            print("remove", n)
        listStar = l
        circles = c
        del l
        del c
        l = []
        c = []

        starttime = timeit.default_timer()
        for j in range(0, n):
            fusion = False
            m = listStar[j].getMass()
            v = listStar[j].getV()
            v[0] = v[0] * m
            v[1] = v[1] * m
            v[2] = v[2] * m
            for k in range(j + 1, n):
                if dist(listStar[j], listStar[k]) < 0.05:
                    print("FUSION")
                    mk = listStar[k].getMass()
                    vk = listStar[j].getV()
                    v[0] += vk[0] * mk
                    v[1] += vk[1] * mk
                    v[2] += vk[2] * mk
                    m += mk
                    fusion = True
                    listStar[k].kill()
            if fusion:
                listStar[j].setMass(m)
                listStar[j].setV(v)
                listStar[j].mulV(1 / m)

            if listStar[j].exists():
                l.append(listStar[j])
                c.append(circles[j])
        print("Temps fusion :", timeit.default_timer() - starttime)

        starttime = timeit.default_timer()
        t.kill()
        print("Kill :", timeit.default_timer() - starttime)
        t = t = Tree(None, [-sizeC, -sizeC, -sizeC], [sizeC, sizeC, sizeC], root=True)

        starttime = timeit.default_timer()
        for j in range(0, n):
            t.addStar(listStar[j])
        print("Temps de création du nouvel arbre :", timeit.default_timer() - starttime)
    except:
        # t=Tree(root=True)
        for j in range(0, n):
            print(listStar[j].getCoord())
        print(t.parcours())
        print("AUREVOIR")
        sys.exit()

app.run()
