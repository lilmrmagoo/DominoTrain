from classes import Game, BoardState, Train, Player, Domino
import gymnasium as gym
from gymnasium import Env
from gymnasium.spaces import Dict, Discrete , MultiDiscrete, Box, Sequence, utils, Tuple
import numpy as np
import random
class DominoTrainEnv(Env):
    def __init__(self,numPlayers:int, maxFails:int):
        # Actions we can take, 13,13 for possible domino sides, [9,13] for possible domino placements
        #action space needed to be changed as it would cause an unknown issue with 
        #self.action_space = MultiDiscrete(np.array([[13, 13], [9, 13]])) 
        self.action_space = Box(low=np.array([[0, 0], [0, 0]]), high=np.array([[12, 12], [8, 12]]), dtype=np.int8 )
        # observation space
        obsv =  {
        "hand": Box(high=np.array([[13, 13]*79]), dtype=np.int8,low=np.array([[-1, -1]*79])),
        "placements": Box(high=np.array([[9, 13]*208]), dtype=np.int8,low=np.array([[-1,-1]*208])),
        "trains": Box(high=np.array([[9, 2]*8]), dtype=np.int8,low=np.array([[-1,-1]*8]))
        }
        self.observation_space = Dict(obsv)
        #setup game
        self.game = Game(numPlayers)
        self.logs = ""
        self.player = self.game.getPlayer(0)
        state = self.getState()
        self.state = state
        self.fails = 0
        self.maxFails = maxFails
        if self.game.startingPlayer != 0:
            bs = BoardState.fromGame(self.game)
            self.playOthers(bs,self.game.startingPlayer)
    def playOthers(self, bs:BoardState, start_index):
        stateChanged = False
        players = self.game.players
        for i in range(start_index, len(players)):
            player = players[i]
            posActions = bs.availablePlays(player)
            self.log(f"current turn: {player}, plays: {posActions}")
            if len(posActions)<=0:
                if not player.pickup(self.game.boneyard): self.game.end()
                posActions = bs.availablePlays(player)
            if len(posActions)>0:
                ranIndex = 0
                if len(posActions)>1: ranIndex = random.randint(0, len(posActions)-1)
                ranAction = posActions[ranIndex]
                ranDomino = player.getDominoFromSides(*ranAction[0])
                self._play(ranDomino,ranAction[1],player,bs)
                stateChanged = True
        return stateChanged
    @staticmethod
    def _padArray(array,len:int):
        return np.pad(array,((0,len),(0,0)),mode='constant',constant_values=-1)
    def getState(self):
        bs = BoardState.fromGame(self.game)
        handarray = np.array([domino.sides for domino in self.player.hand], dtype=np.int8)
        placements = np.array(bs.getPlacements(), dtype=np.int8)
        train_info = np.array([[train.id, int(train.trainUp)] for train in [*bs.trains,bs.mexican]], dtype=np.int8)
        self.log(handarray.shape)
        hand_padding = DominoTrainEnv._padArray(handarray, 79-len(handarray))
        placement_padding = DominoTrainEnv._padArray(placements, 208-len(placements))
        train_padding = DominoTrainEnv._padArray(train_info, 8-len(train_info))
        state =  {
            "hand": hand_padding.ravel().reshape((1,158)),
            "placements": placement_padding.ravel().reshape((1,416)),
            "trains": train_padding.ravel().reshape((1,16))
        }
        self.log(state)
        return state
    def _play(self,domino:Domino, placement,player:Player, bs:BoardState):
        self.log(f"attempting to play {domino} on {placement} from {player}")
        game = self.game
        played = False
        if domino is not None:
            train = game.getTrain(placement[0])
            if player.play(domino,placement[1],train) is not False:
                played = True   
                if domino.isDouble:
                    self.log("double played")
                    players = game.players
                    start_index = players.index(player)
                    #loop through all players at "table" starting with person who played double
                    for i in range(len(players)):
                        index = (start_index + i) % len(players)
                        loop_player = players[index] 
                        newPlacement = (placement[0],domino.sides[0])
                        plays = bs.availablePlays(loop_player, placements=[placement])
                        self.log(f"checking if {loop_player} can play on {newPlacement}\n, plays {plays}")
                        #if player can't play on double
                        if len(plays)<=0:
                            pickupDomino = loop_player.pickup(self.game.boneyard)
                            #if a domino was actually picked up
                            if pickupDomino:
                                self.log(f"{loop_player} pickedup {pickupDomino}")
                                plays = bs.availablePlays(loop_player, placements=[newPlacement])
                                if len(plays)<=0: 
                                    self.log("player can't play pickup")
                                    loop_player.train.trainUp = True
                                    continue
                                #if possible to play pickup
                                else:
                                    self.log(f"attepmting to play pickup on {newPlacement}, train {train}")
                                    if loop_player.play(pickupDomino,newPlacement[1],train) is None:
                                        game.done = True
                                    break
                                    
                            # no domino was pickedup, meaning boneyard is empty and end of game
                            else:
                                game.done = True
                                break
                        #if player only has one choice to play
                        elif len(plays) == 1:
                            play = plays[0]
                            ranDomino = loop_player.getDominoFromSides(*play[0])
                            self.log(f"attempting to play {ranDomino} on {newPlacement}, player.train: {player.train}")
                            if loop_player.play(ranDomino,newPlacement[1],train) is None:
                                game.done = True
                            break
                        #if player has many choices to play
                        else:
                            #if ai player
                            if loop_player.id == 0:
                                self.log(f"letting ai make choice for double play")
                                self.game.unsastifiedDouble = (train.id,domino.sides[0])
                                self.game.prevPlayer = player.id
                                break
                            #if other players, random choice
                            else:
                                self.log(player.train)
                                play = plays[random.randint(0, len(plays) - 1)]
                                ranDomino = loop_player.getDominoFromSides(*play[0])
                                self.log(f"attempting to play {ranDomino} on {newPlacement}, player.train: {player.train}\n available plays: {plays}")
                                if loop_player.play(ranDomino,newPlacement[1],train) is None:
                                    game.done = True
                            break
            else:
                self.log("Invalid Placement")
        else:
            self.log("Invlaid Domino")
        if played and len(player.hand) == 0:
            self.game.end(player.id)
        return played

    def convertAction(self, action):
        return action
    def step(self, action):
        action = self.convertAction(action)
        stateChanged = False
        reward = 0
        bs= BoardState.fromGame(self.game)
        if bs.isValidPlay(self.player,action):
            if bs.unsastifiedDouble is not None:
                domino = action[0]
                domino = self.player.getDominoFromSides(*domino)
                self._play(domino,action[1],self.player,bs)
                reward += domino.calc_points()
                stateChanged = True
                bs.unsastifiedDouble = None #probably a better way of doing this
                self.game.unsastifiedDouble = None
            else:    
                player = self.player
                posActions = bs.availablePlays(player)
                #if no action available
                if len(posActions)<=0:
                    if not self.player.pickup(self.game.boneyard): self.game.end()
                    posActions = bs.availablePlays(self.player)
                    if len(posActions)>0:
                        ranAction = posActions[0]
                        ranDomino = self.player.getDominoFromSides(*ranAction[0])
                        self._play(ranDomino,ranAction[1],self.player,bs)
                        stateChanged = True
                else:
                    # Apply action
                    domino = action[0]
                    domino = self.player.getDominoFromSides(*domino)
                    self._play(domino,action[1],self.player,bs)
                    reward += domino.calc_points()
                    stateChanged = True
            if stateChanged: bs = BoardState.fromGame(self.game)
            self.playOthers(bs=bs,start_index=self.game.nextPlayer(self.player.id))
            reward += 10 
        #invalid action
        else: 
            self.log("Invalid Action from step call")
            reward += -50
            self.fails +=1
        done = self.game.done
        if stateChanged and not done:    
            self.state = self.getState()
        truncated = False
        #hard limit on game length since, the ai can make invalid plays which could loop forever
        if self.fails >=self.maxFails:
            done = True
            truncated = True
        elif done:
            # add negative reward for points remaining in hand at game end
            reward += -1*self.player.pointsInHand() 
            if self.game.winner ==0:
                reward += 100
        
        # Set placeholder for info
        info = {}
        
        # Return step information
        return self.state, reward, done,truncated, info
    def render(self):
        # Implement viz
        print(self.logs)
        self.logs = ""
    def log(self, log):
        self.logs += str(log)+ "\n"
    def log_to_file(self, filename='log.txt'):
        try:
            with open(filename, 'a') as file:
                file.write(self.logs + '\n\n\n')
        except Exception as e:
            print(f"Error: {e}")
    def reset(self, seed=None, options=None):
        self.game = Game(self.game.numPlayers)
        self.player = self.game.getPlayer(0)
        self.state = self.getState()
        self.fails = 0
        self.log("------RESET------")
        self.log_to_file()
        self.logs = ""
        random.seed(seed)
        np.random.seed(seed)
        return self.state, {}
class DominoTrainEnvMaskable(DominoTrainEnv):
    def __init__(self,numPlayers:int,maxFails:int):
        # Actions we can take, 13,13 for possible domino sides, [9,13] for possible domino placements
        super().__init__(numPlayers,maxFails)
        self.actions = []
        allDominos = [(side1,side2) for side1 in range(0,13) for side2 in range(0,13)]
        placements = [(train,side) for side in range(0,13) for train in range(0,9)]
        for domino in allDominos:
           for placement in placements:
               self.actions.append((domino,placement))
        self.actions = tuple(self.actions)
        self.action_space = Discrete(19773)
        #self.action_space = MultiDiscrete([13, 13, 9, 13], dtype=np.int8)
    def getMaskMultiDiscrete(self):
        #[[[0-1x13],[0-1x13]],[[0-1x8],[0-1x13]]]
        #[[13],[13],[9],[13]]
        bs = BoardState.fromGame(self.game)
        mask = []
        plays = bs.availablePlays(self.player)
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
    def getMaskDiscrete(self):
        bs = BoardState.fromGame(self.game)
        mask = np.zeros(19773)
        for action in bs.availablePlays(self.player):
            index = self.actions.index(action)
            mask[index] = 1
        return mask
    def convertAction(self, action):
        return self.actions[action] # converts index into action
        #return [[action[0],action[1]],[action[2],action[3]]]    
    
    #def getState(self):
    #    bs = BoardState.fromGame(self.game)
    #    handarray = np.array([domino.sides for domino in self.player.hand], dtype=np.int8)
    #    placements = np.array(bs.getPlacements(), dtype=np.int8)
    #   train_info = np.array([[train.id, int(train.trainUp)] for train in bs.trains], dtype=np.int8)
    #    
    #   hand_padding = DominoTrainEnv._padArray(handarray, 79-len(handarray))
    #    placement_padding = DominoTrainEnv._padArray(placements, 208-len(placements))
    #    train_padding = DominoTrainEnv._padArray(train_info, 8-len(train_info))
    #    state =  (
    #        hand_padding.ravel().reshape((1,158)),
    #        placement_padding.ravel().reshape((1,416)),
    #        train_padding.ravel().reshape((1,16))
    #    )
     #   return state