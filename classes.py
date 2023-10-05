import functools
import random
class Domino():
    def __init__(self, s1:int,s2:int):
        self.sides = (s1,s2)
        self.isDouble = (s1 == s2)
    def evalute_side(self, side: int):
        if(self.sides[0] == side): return 0
        elif (self.sides[1] == side): return 1
    def calc_points(self):
        return self.sides[0] + self.sides[1]
    def __str__(self):
        return str(self.sides)


class BoneYard():
    def __init__(self):
        self.dominos = []
        self.build()
        self.shuffle()
    def build(self):
        for i in range(0,13):
            for j in range(i,13):
                self.dominos.append(Domino(i,j))
    def shuffle(self):
        random.shuffle(self.dominos)
    def draw(self):
        if len(self.dominos) == 0: return False
        return self.dominos.pop()


class Train():
    startingSide = 12
    def __init__(self, id):
        self.openSides = [Train.startingSide]
        self.trainUp = False
        self.id = id
    def add(self,placement,domino):
        placeIndex = self.openSides.index(placement)
        trainSide = self.openSides[placeIndex]
        if(trainSide in domino.sides):
            if(domino.isDouble):
                self.openSides.pop(placeIndex)
                self.openSides.append(domino.sides[0])
                self.openSides.append(domino.sides[1])
            else:
                self.openSides.pop(placeIndex)
                self.openSides.append(domino.sides[1-domino.evalute_side(trainSide)])
        else:
            return False
    def __str__(self):
        return f"id: {self.id} trainUp?:{self.trainUp} openSides: {self.openSides}"
        

class Player():
    handSize = 12
    nextID = 0 
    def __init__(self,boneYard:BoneYard):
        self.id = Player.nextID
        Player.nextID +=1
        self.hand = []
        for _ in range(Player.handSize): self.hand.append(boneYard.draw()) 
    def highestDouble(self):
        highest = -1
        for domino in self.hand:
            if(domino.isDouble and domino.sides[0] > highest): highest = domino.sides[0]
        return highest
    def intializeTrain(self):
        if not hasattr(self,"train"):
            self.train = Train(self.id)
        return self.train
    def getDominoFromSides(self,s1:int,s2:int):
        for domino in self.hand:
            if (domino.sides == (s1,s2) or domino.sides == (s2,s1)):
                return domino
    def play(self, domino:Domino, placement:int, train:Train|None=None,firstDouble:bool=False):
        if train is None: train = self.train
        if firstDouble: 
            self.hand.remove(domino)
            return
        if train.add(placement, domino) != False:
            self.hand.remove(domino)
            return True
        else: return False
    def pointsInHand(self):
        return functools.reduce(lambda acc, domino: acc + domino.calc_points(), self.hand, 0)
    def pickup(self,boneYard:BoneYard):
        self.hand.append(boneYard.draw())
    def __str__(self):
        return f"id:{self.id} train:{self.train.id}"
    



class Game():
    def __init__(self,numPlayers:int):
        self.boneyard = BoneYard()
        self.players = []
        self.trains = []
        self.numPlayers = numPlayers
        if(numPlayers<= 4): Player.handSize = 15
        elif(numPlayers<=6): Player.handSize = 12
        elif(numPlayers<=8): Player.handSize = 10
        Player.nextID = 0
        for _ in range(numPlayers): 
            self.players.append(Player(self.boneyard))
        doubles = [player.highestDouble() for player in self.players]
        highestDouble = max(doubles)
        firstPlayer = doubles.index(highestDouble)
        self.currentPlayer = firstPlayer
        firstDomino = self.players[firstPlayer].getDominoFromSides(highestDouble,highestDouble)
        for player in self.players: 
            player.intializeTrain()
            self.trains.append(player.train)
        if (len(self.players)<8): self.mexican = Train(8)
        Train.startingSide = max(doubles)
        self.players[firstPlayer].play(firstDomino,0,firstDouble=True) #removing first double
        self.stepPlayer() #first player skiping turn
    def stepPlayer(self):
        self.currentPlayer += 1 
        if (self.currentPlayer>=self.numPlayers): self.currentPlayer = 0# looping if its not an actual player
    def getTrain(self,id:int):
        if id == 8: return self.mexican
        else:
            for t in self.trains:
                if t.id==id:
                    return t
            else:
                return None
    def getPlayer(self,id:int):
        if id > 7: return None
        else: 
            for p in self.players:
                if p.id==id:
                    return p
            else:
                return None

class BoardState():
    def __init__(self, game:Game):
        self.mexican: Train = game.mexican
        self.trains: list[Train] = game.trains
    #train up returns only sides that are on trains with thier trains up
    #maybe this signature should be changed to just take a list of trains? and let caller deal with filtering?
    def getPlacements(self, trainUp: bool,include:list[Train]=[], exclude:list[Train]=[]):
        trains = [*self.trains,self.mexican]
        sides = []
        if trainUp:
            for train in trains:
                if (train in include or train.trainUp) and train not in exclude:
                    for side in train.openSides: 
                        sides.append((train.id,side))
        else:
            for train in trains: 
                if train not in exclude:
                    for side in train.openSides: sides.append((train.id,side))
        return sides
    def getTrain(self, id):
        for train in self.trains:
            if train.id == id: return train
    def availablePlays(self, player:Player):
        plays = [] 
        if player.train.trainUp:
            for side in player.train.openSides:
                for domino in player.hand:
                    eval = domino.evalute_side(side)
                    if( eval is not None): plays.append((domino.sides, (player.train.id,side))) 
        else:
            for placement in self.getPlacements(trainUp=True, include=[player.train]):
                for domino in player.hand:
                    eval = domino.evalute_side(placement[1])
                    if( eval is not None): plays.append((domino.sides, placement))
        return plays

