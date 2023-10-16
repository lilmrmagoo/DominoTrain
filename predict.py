import numpy as np
from classes import Train,Domino,BoardState,Player
from sb3_contrib import MaskablePPO
import argparse
import traceback
parser = argparse.ArgumentParser(description="Command line arguments parser")
parser.add_argument("--traceback", action="store_true", help="Boolean to override if a model has the same name (default: false)")
args = parser.parse_args()
usetraceback = args.traceback

class rlGame():
    def __init__(self,numofplayers,highestdouble):
        self.centerdouble = highestdouble
        Train.startingSide = highestdouble
        self.trains = []
        for i in range(0,numofplayers):
            self.trains.append(Train(i))
        if numofplayers<8:
            global mexican
            mexican = Train(8)
            mexican.trainUp=True
        global aiTrain
        train = self.trains[0]
        hand = []
        self.player = Player.fromHandAndTrain(hand,train)
        self.player.id = 0
        self.unsatisfieddouble = None
        self.actions = []
        allDominos = [(side1,side2) for side1 in range(0,13) for side2 in range(0,13)]
        placements = [(train,side) for side in range(0,13) for train in range(0,9)]
        for domino in allDominos:
           for placement in placements:
               self.actions.append((domino,placement))
        self.actions = tuple(self.actions)

    def makeBoardstate(self):
        return BoardState(self.trains,mexican=mexican,centerDouble=self.centerdouble,unsastifiedDouble=self.unsatisfieddouble)

    def getDominoFromHand(self,s1,s2):
        for domino in self.player.hand:
            if (domino.sides == (s1,s2) or domino.sides == (s2,s1)):
                return domino
    def play(self, domino:Domino, placement:int, train:Train|None=None):
        return self.player.play(domino=domino,placement=placement,train=train)
    def addHand(self,s1,s2):
        self.player.hand.append(Domino(s1,s2))

    def trainAdd(self,trainid,placement, s1,s2,):
        train = self.trains[trainid]
        if s1 == s2: self.unsatisfieddouble = s1
        return train.add(placement,self.getDominoFromHand(s1,s2))
    def toggleUpTrain(self,trainid):
        train = self.trains[trainid]
        train.trainUp = not train.trainUp
        return train.trainUp
    @staticmethod
    def _padArray(array,len:int):
        return np.pad(array,((0,len),(0,0)),mode='constant',constant_values=-1)
    def getState(self):
        bs= self.makeBoardstate()
        handarray = np.array([domino.sides for domino in self.player.hand], dtype=np.int8)
        placements = np.array(bs.getPlacements(), dtype=np.int8)
        train_info = np.array([[train.id, int(train.trainUp)] for train in [*bs.trains,bs.mexican]], dtype=np.int8)
        hand_padding = rlGame._padArray(handarray, 79-len(handarray))
        placement_padding = rlGame._padArray(placements, 208-len(placements))
        train_padding = rlGame._padArray(train_info, 8-len(train_info))
        state =  {
            "hand": hand_padding.ravel().reshape((1,158)),
            "placements": placement_padding.ravel().reshape((1,416)),
            "trains": train_padding.ravel().reshape((1,16))
        }
        return state
    def getMaskMultiDiscrete(self):
        #[[[0-1x13],[0-1x13]],[[0-1x8],[0-1x13]]]
        #[[13],[13],[9],[13]]
        bs = self.makeBoardstate()
        mask = []
        plays = bs.availablePlays(self.player)
        if len(plays)==0:
            ones13 =  np.ones(13,dtype=bool)
            ones9 = np.ones(9,dtype=bool)
            mask = [ones13,ones13,ones9,ones13]
        else:
            zero13 =  np.zeros(13,dtype=bool)
            zero9 = np.zeros(9,dtype=bool)
            mask = [zero13,zero13,zero9,zero13]
            for action in plays:
                domino = action[0]
                placement = action[1]
                mask[0][domino[0]] = True
                mask[1][domino[1]] = True
                mask[2][placement[0]] = True
                mask[3][placement[1]] = True
        return mask
    def getMaskDiscrete(self):
        bs = self.makeBoardstate()
        mask = np.zeros(19773)
        for action in bs.availablePlays(self.player):
            index = self.actions.index(action)
            mask[index] = 1
        return mask
    def convertAction(self, action):
        return self.actions[action] # converts index into action
        #return [[action[0],action[1]],[action[2],action[3]]]  

try:
    game = rlGame(int(input("How many Players?: ")),int(input("highest double?: ")))
    model_name = input("Model_name: ")
    model = MaskablePPO.load(model_name)
except ValueError:
    print("invalid input")
except Exception as e:
    print(e)
while True: 
    try:
        entered = input("command: ")
        args = entered.split(" ")
        command = args.pop(0)
        if command == "predict" or command == "n":
            observation = game.getState()
            mask = game.getMaskDiscrete()
            action, _states = model.predict(observation=observation,action_masks=mask)
            action = game.convertAction(action)
            bs = game.makeBoardstate()
            while not bs.isValidPlay(game.player,action):
                action, _states = model.predict(observation=observation,action_masks=mask)
                action = game.convertAction(action)
            print(f"place {action[0]} on {action[1]}")
        elif command == "add" or command == "a":
            s1 = int(args[0])
            s2 = int(args[1])
            game.addHand(s1,s2)
        elif command == "play" or command == "p":
            trainid = int(args[0])
            placement = int(args[1])
            s1 = int(args[2])
            s2 = int(args[3])
            success = game.trainAdd(trainid,placement,s1,s2)
            print(success)
        elif command == "self" or command == "s":
            trainid = int(args[2])
            placement = int(args[3])
            s1 = int(args[0])
            s2 = int(args[1])
            train = game.trains[trainid]
            domino = game.getDominoFromHand(s1,s2)
            success = game.play(domino,placement,train)
            print(success)
        elif command == "trainup":
            game.toggleUpTrain(int(args[0]))
        elif command == "mask":
            print(np.count_nonzero(game.getMaskDiscrete()))
        elif command == "state":
            print(game.getState())
        else: print("invalid command")
    except Exception as e:
        if usetraceback: traceback.print_exception(e)
        else: print(e)
    