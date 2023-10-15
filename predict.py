import numpy as np
from classes import Train,Domino,BoardState,Player
from sb3_contrib import MaskablePPO

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
        self.train = self.trains[0]
        self.hand = []

    def makeBoardstate(self):
        return BoardState(self.trains,mexican,self.centerdouble,)

    def getDominoFromHand(self,s1,s2):
        for domino in self.hand:
            if (domino.sides == (s1,s2) or domino.sides == (s2,s1)):
                return domino

    def addHand(self,s1,s2):
        self.hand.append(Domino(s1,s2))

    def trainAdd(self,trainid,placement, s1,s2,):
        train = self.trains[trainid]
        train.add(placement,self.getDominoFromHand(s1,s2))
    def toggleUpTrain(self,trainid):
        train = self.trains[trainid]
        train.trainUp = not train.trainUp
    def padArray(array,len:int):
        return np.pad(array,((0,len),(0,0)),mode='constant',constant_values=-1)
    def getState(self):
        bs= self.makeBoardstate()
        handarray = np.array([domino.sides for domino in self.hand], dtype=np.int8)
        placements = np.array(bs.getPlacements(), dtype=np.int8)
        train_info = np.array([[train.id, int(train.trainUp)] for train in [*bs.trains,bs.mexican]], dtype=np.int8)
        hand_padding = self.padArray(handarray, 79-len(handarray))
        placement_padding = self.padArray(placements, 208-len(placements))
        train_padding = self.padArray(train_info, 8-len(train_info))
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
        plays = bs.availablePlays(Player.fromHandAndTrain(self.hand,self.train))
        if len(plays)==0:
            ones13 =  np.ones(13,dtype=np.bool)
            ones9 = np.ones(9,dtype=np.bool)
            mask = [ones13,ones13,ones9,ones13]
        else:
            zero13 =  np.zeros(13,dtype=np.bool)
            zero9 = np.zeros(9,dtype=np.bool)
            mask = [zero13,zero13,zero9,zero13]
            for action in plays:
                domino = action[0]
                placement = action[1]
                mask[0][domino[0]-1] = True
                mask[1][domino[1]-1] = True
                mask[2][placement[0]-1] = True
                mask[3][placement[1]-1] = True
        return mask
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
        entered = input("action: ")
        args = entered.split(" ")
        action = args.pop(0)
        if action == "predict":
           action = model.predict(observation=game.getState(),action_masks=game.getMaskMultiDiscrete())
           print("action: ",action)
        elif action == "add":
            game.addHand(*args)
        elif action == "play":
            game.trainAdd(*args)
        elif action == "trainup":
            game.toggleUpTrain(args[0])
    except Exception as e:
        print(e)
        

