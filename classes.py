# %load classes.py
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
        try:
           placeIndex = self.openSides.index(placement)
        except ValueError:
            return False  # Item not found in the iterable
        trainSide = self.openSides[placeIndex]
        if(trainSide in domino.sides):
            if(domino.isDouble):
                self.openSides.pop(placeIndex)
                self.openSides.append(domino.sides[0])
                self.openSides.append(domino.sides[0])
                self.openSides.append(domino.sides[0])
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
    def __init__(self,boneYard:BoneYard=None):
        if boneYard is not None:
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
        selfTrain = False
        played = False
        if train is None: 
            train = self.train
            selfTrain = True
        if firstDouble: 
            self.hand.remove(domino)
            played = True
        elif train.add(placement, domino) != False:
            self.hand.remove(domino)
            if selfTrain: self.train.trainUp = False
            played = True
        if len(self.hand) <= 0: return None
        else: return played
        

    def pointsInHand(self):
        return functools.reduce(lambda acc, domino: acc + domino.calc_points(), self.hand, 0)
    def pickup(self,boneYard:BoneYard):
        domino = boneYard.draw()
        if domino is not False:
            self.hand.append(domino)
        return domino
    def __str__(self):
        return f"id:{self.id} train:{self.train.id}"
    @staticmethod
    def fromHandAndTrain(hand:list[Domino],train:Train):
        player = Player()
        player.hand = hand
        player.train = train
        return player



class Game():
    def __init__(self,numPlayers:int):
        self.boneyard = BoneYard()
        self.players = []
        self.trains = []
        self.done = False
        self.numPlayers = numPlayers
        self.unsastifiedDouble = None
        if(numPlayers<= 4): Player.handSize = 15
        elif(numPlayers<=6): Player.handSize = 12
        elif(numPlayers<=8): Player.handSize = 10
        Player.nextID = 0
        for _ in range(numPlayers): 
            self.players.append(Player(self.boneyard))
        doubles = [player.highestDouble() for player in self.players]
        highestDouble = max(doubles)
        if highestDouble != -1:
            firstPlayer = doubles.index(highestDouble)
            firstDomino = self.players[firstPlayer].getDominoFromSides(highestDouble,highestDouble)
        else:
            while highestDouble == -1: 
                for player in self.players:
                    domino = player.pickup(self.boneyard)
                    if domino.isDouble:
                        highestDouble = domino.sides[0]
                        firstDomino = domino
                        firstPlayer = self.players.index(player)
        for player in self.players: 
            player.intializeTrain()
            self.trains.append(player.train)
        if (len(self.players)<8): self.mexican = Train(8)
        else: self.mexican = None
        self.centerDouble = max(doubles)
        Train.startingSide = self.centerDouble
        self.players[firstPlayer].play(firstDomino,0,firstDouble=True) #removing first double
        self.startingPlayer = self.nextPlayer(firstPlayer)
        self.prevPlayer = None
        self.winner = None
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
    def nextPlayer(self, currPlayer:int):
        return (currPlayer +1) % self.numPlayers
    def end(self, winner:int=None):
        self.done = True
        self.winner = winner

class BoardState():
    def __init__(self, trains:list[Train],centerDouble:int, mexican:Train|None = None,unsastifiedDouble=None):
        self.mexican = mexican
        self.trains = trains
        self.unsastifiedDouble = unsastifiedDouble
    #train up returns only sides that are on trains with thier trains up
    #maybe this signature should be changed to just take a list of trains? and let caller deal with filtering?
    def getPlacements(self, trainUp: bool=False,include:list[Train]=[], exclude:list[Train]=[]):
        trains = [*self.trains]
        if self.mexican is not None: trains.append(self.mexican)
        placements = []
        if trainUp:
            for train in trains:
                if (train in include or train.trainUp) and train not in exclude:
                    for side in train.openSides: 
                        placements.append((train.id,side))
        else:
            for train in trains: 
                if train not in exclude:
                    for side in train.openSides: 
                        placements.append((train.id,side))
        return placements
    def getTrain(self, id):
        for train in self.trains:
            if train.id == id: return train
    def availablePlays(self, player:Player,placements:list|None=None):
        plays = []
        places = []
        if self.unsastifiedDouble is not None:
            places = [self.unsastifiedDouble]
        elif placements is not None:
            places = placements
        elif player.train.trainUp:
            places = [(player.id, side) for side in player.train.openSides]
        else: 
            places = self.getPlacements(trainUp=True, include=[player.train])
        for placement in places:
            if placement is None:print("none placement")
            for domino in player.hand:
                eval = domino.evalute_side(placement[1])
                if( eval is not None): plays.append((domino.sides, placement))
        return plays
    def isValidPlay(self, player:Player, action:list[list]):
        valid = False
        plays = self.availablePlays(player)
        if len(plays)==0: valid = None
        for play in plays:
            tuplist = [tuple(list) for list in action]
            if tuple(tuplist) == play:
                valid = True
        return valid
    @staticmethod
    def fromGame(game:Game):
        return BoardState(game.trains,game.centerDouble, game.mexican,game.unsastifiedDouble)
