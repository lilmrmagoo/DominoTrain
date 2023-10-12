from classes import Game, BoardState, Train, Player, Domino
import gymnasium as gym
from gymnasium import Env
from gymnasium.spaces import Dict, Discrete , MultiDiscrete, Box, Sequence, utils
import numpy as np
class DominoTrainEnv(Env):
    def __init__(self,numPlayers:int):
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
        self.player = self.game.getPlayer(0)
        bs = BoardState.fromGame(self.game)
        handarray = [domino.sides for domino in self.player.hand]
        placements = bs.getPlacements()
        state = self.getState()
        self.state = state
        self.fails = 0
    @staticmethod
    def __padArray(array,len:int):
        return np.pad(array,((0,len),(0,0)),mode='constant',constant_values=-1)
    def getState(self):
        bs = BoardState.fromGame(self.game)
        handarray = np.array([domino.sides for domino in self.player.hand], dtype=np.int8)
        placements = np.array(bs.getPlacements(), dtype=np.int8)
        train_info = np.array([[train.id, int(train.trainUp)] for train in bs.trains], dtype=np.int8)
        
        hand_padding = DominoTrainEnv.__padArray(handarray, 79-len(handarray))
        placement_padding = DominoTrainEnv.__padArray(placements, 208-len(placements))
        train_padding = DominoTrainEnv.__padArray(train_info, 8-len(train_info))
        state =  {
            "hand": hand_padding.ravel().reshape((1,158)),
            "placements": placement_padding.ravel().reshape((1,416)),
            "trains": train_padding.ravel().reshape((1,16))
        }
        return state
    def play(self,domino:Domino, placement,player:Player, bs:BoardState):
        print(f"attempting to play {domino} on {placement} from {player}")
        game = self.game
        played = False
        if domino is not None:
            train = game.getTrain(placement[0])
            if player.play(domino,placement[1],train):
                played = True   
                if domino.isDouble:
                    print("double played")
                    players = game.players
                    start_index = players.index(player)
                    #loop through all players at "table" starting with person who played double
                    for i in range(len(players)):
                        index = (start_index + i) % len(players)
                        loop_player = players[index] 
                        newPlacement = (placement[0],domino.sides[0])
                        plays = bs.availablePlays(loop_player, placements=[placement])
                        print(f"checking if {loop_player} can play on {newPlacement}\n, plays {plays}")
                        #if player can't play on double
                        if len(plays)<=0:
                            pickupDomino = loop_player.pickup(self.game.boneyard)
                            #if a domino was actually picked up
                            if pickupDomino:
                                print(f"{loop_player} pickedup {pickupDomino}")
                                plays = bs.availablePlays(loop_player, placements=[newPlacement])
                                if len(plays)<=0: 
                                    print("player can't play pickup")
                                    loop_player.train.trainUp = True
                                    continue
                                #if possible to play pickup
                                else:
                                    print(f"attepmting to play pickup on {newPlacement}, train {train}")
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
                            print(f"attempting to play {ranDomino} on {newPlacement}, player.train: {player.train}")
                            if loop_player.play(ranDomino,newPlacement[1],train) is None:
                                game.done = True
                            break
                        #if player has many choices to play
                        else:
                            #if ai player
                            if loop_player.id == 0:
                                print(f"letting ai make choice for double play")
                                self.game.unsastifiedDouble = (train.id,domino.sides[0])
                                self.game.prevPlayer = player.id
                                break
                            #if other players, random choice
                            else:
                                print(player.train)
                                play = plays[random.randint(0, len(plays) - 1)]
                                ranDomino = loop_player.getDominoFromSides(*play[0])
                                print(f"attempting to play {ranDomino} on {newPlacement}, player.train: {player.train}\n available plays: {plays}")
                                if loop_player.play(ranDomino,newPlacement[1],train) is None:
                                    game.done = True
                            break
            else:
                   print("Invalid Placement")
        else:
            print("Invlaid Domino")
        return played
    def maskAction(self,availablActions):
        pass
    def step(self, action):
        start_index = self.game.startingPlayer
        players = self.game.players
        length = len(players)
        stateChanged = False
        reward = 0
        bs= BoardState.fromGame(self.game)
        if bs.isValidPlay(self.player,action):
            if bs.unsastifiedDouble is not None:
                domino = action[0]
                domino = self.player.getDominoFromSides(*domino)
                self.play(domino,action[1],self.player,bs)
                reward += domino.calc_points()
                stateChanged = True
                start_index = self.game.nextPlayer(self.player.id)
                length = length - 1
                bs.unsastifiedDouble = None #probably a better way of doing this
                self.game.unsastifiedDouble = None
            if stateChanged or bs.unsastifiedDouble is None:    
                for i in range(length):
                    index = (start_index + i) % length
                    player = players[index]
                    posActions = bs.availablePlays(player)
                    #if current turn is ai
                    if player.id == 0:
                        #if no action available
                        if len(posActions)<=0:
                            self.player.pickup(self.game.boneyard)
                            posActions = bs.availablePlays(self.player)
                            if len(posActions)>0:
                                ranAction = posActions[0]
                                ranDomino = self.player.getDominoFromSides(*ranAction[0])
                                self.play(ranDomino,ranAction[1],self.player,bs)
                                stateChanged = True
                            # Check if action is valid
                        else:
                            # Apply action
                            domino = action[0]
                            domino = self.player.getDominoFromSides(*domino)
                            self.play(domino,action[1],self.player,bs)
                            reward += domino.calc_points() + 60
                            stateChanged = True
                        #invalid action   
                        
                    else:
                        print(f"current turn: {player}, plays: {posActions}")
                        if len(posActions)<=0:
                            player.pickup(self.game.boneyard)
                            posActions = bs.availablePlays(player)
                        if len(posActions)>0:
                            ranIndex = 0
                            if len(posActions)>1: ranIndex = random.randint(0, len(posActions)-1)
                            ranAction = posActions[ranIndex]
                            ranDomino = player.getDominoFromSides(*ranAction[0])
                            self.play(ranDomino,ranAction[1],player,bs)
                            stateChanged = True
        else: 
            reward += -50
            self.fails +=1
        if stateChanged:    
            self.state = self.getState()
        
        done = self.game.done
        #hard limit on game length since, the ai can make invalid plays which could loop forever
        if self.fails >=10: done = True
        elif done:
            # add negative reward for points remaining in hand at game end
            reward += -1*self.player.pointsInHand()  
        
        # Set placeholder for info
        info = {}
        
        # Return step information
        return self.state, reward, done,False, info

    def render(self):
        # Implement viz
        pass
    
    def reset(self, seed=None):
        self.game = Game(self.game.numPlayers)
        self.player = self.game.getPlayer(0)
        self.state = self.getState()
        self.fails = 0
        return self.state, {}
    