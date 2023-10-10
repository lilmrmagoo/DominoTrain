# %load DominoEnv.py
from gym import Env
from gym.spaces import Dict, Discrete , MultiDiscrete, Box, Sequence
import numpy as np
class DominoTrainEnv(Env):
    def __init__(self,numPlayers:int):
        # Actions we can take, 13,13 for possible domino sides, [9,13] for possible domino placements
        self.action_space = MultiDiscrete(np.array([[13, 13], [9, 13]]))
        # Temperature array
        obsv =  {
        "hand": Sequence(MultiDiscrete(np.array([13, 13]), dtype=np.int8)),
        "placements": Sequence(MultiDiscrete(np.array([9, 13]), dtype=np.int8)),
        "available-actions": Sequence(MultiDiscrete(np.array([[13, 13], [9, 13]]), dtype=np.int8)),
        "trains": Sequence(MultiDiscrete(np.array([9, 2]), dtype=np.int8))
        }
        self.observation_space = Dict(obsv)
        #setup game
        self.game = Game(numPlayers)
        self.player = self.game.getPlayer(0)
        bs = BoardState.fromGame(self.game)
        handarray = [domino.sides for domino in self.player.hand]
        placements = bs.getPlacements()
        state = {
            "hand": handarray,
            "placements": placements,
            "available-actions": bs.availablePlays(self.player),
            "trains": [[train.id,train.trainUp]for train in bs.trains]
        }
        self.state = state
        self.fails = 0
        
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
                            reward += domino.calc_points()
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
            reward += -500
            self.fails +=1
        if stateChanged:    
            #assigning state
            handarray = [domino.sides for domino in self.player.hand]
            placements = bs.getPlacements()
            state = {
                "hand": handarray,
                "placements": placements,
                "available-actions": bs.availablePlays(self.player),
                "trains": [[train.id,train.trainUp]for train in bs.trains]
            }
            self.state = state
        
        done = self.game.done
        #hard limit on game length since, the ai can make invalid plays which could loop forever
        if self.fails >=10000: done = True
        if done:
            # add negative reward for points remaining in hand at game end
            reward += -1*self.player.pointsInHand()  
        
        # Set placeholder for info
        info = {}
        
        # Return step information
        return self.state, reward, done, info

    def render(self):
        # Implement viz
        pass
    
    def reset(self):
        self.game = Game(self.game.numPlayers)
        self.player = self.game.getPlayer(0)
        bs = BoardState.fromGame(self.game)
        handarray = [domino.sides for domino in self.player.hand]
        placements = bs.getPlacements()
        state = {
            "hand": handarray,
            "placements": placements,
            "available-actions": bs.availablePlays(self.player),
            "trains": [[train.id,train.trainUp]for train in bs.trains]
        }
        self.state = state
        self.fails = 0
        return self.state
    