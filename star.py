class Star(object):
    def __init__(self, x, y, z, vx, vy, vz, m):
        self.p = [x, y, z]
        self.v = [vx, vy, vz]
        self.m = m
        self.exist = True

    # print("constructeur V :",self.v[0],self.v[1],self.v[2],id(self.p))

    def getCoord(self):
        return self.p

    def getMass(self):
        return self.m

    def getV(self):
        return self.v

    def getV_val(self,v):
        v[0] = self.v[0]
        v[1] = self.v[1]
        v[2] = self.v[2]

    def setCoord(self, p):
        for i in range(0, 3):
            self.p[i] = p[i]

    def setMass(self, m):
        self.m = m

    def addMass(self, m):
        self.m += m

    def mulV(self, x):
        for i in range(0, 3):
            self.v[i] = self.v[i]*x

    def addV(self, v):
        for i in range(0, 3):
            self.v[i] += v[i]

    def setV(self, v):
        for i in range(0, 3):
            self.v[i] = v[i]

    def exists(self):
        return self.exist

    def kill(self):
        self.exist = False
