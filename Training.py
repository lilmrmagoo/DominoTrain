import numpy as np
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
#from stable_baselines3.common.evaluation import evaluate_policy
from sb3_contrib import MaskablePPO
from sb3_contrib.common.maskable.evaluation import evaluate_policy
from sb3_contrib.common.wrappers import ActionMasker
#from sb3_contrib.ppo_mask import MaskablePPO
from sb3_contrib.common.maskable.policies import  MaskableMultiInputActorCriticPolicy
from DominoEnv import DominoTrainEnv, DominoTrainEnvMaskable
import argparse
import os
import torch
import traceback

# Specify the GPU device you want to use (e.g., GPU 1)
gpu_id = 0

# Set the GPU device
os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

# Check if CUDA (GPU support) is available
if torch.cuda.is_available():
    # Set the device for PyTorch
    torch.cuda.set_device(gpu_id)


# Create the argument parser
parser = argparse.ArgumentParser(description="Command line arguments parser")

# Add the command line arguments
parser.add_argument("--players", type=int, default=6,choices=range(2, 9), help="Number of players (2-8)")
parser.add_argument("--name", type=str,default="", help="Name to save the model under deafult: PPO_DominoTrain-\{num_players\}p-v\{version\}")
parser.add_argument("--loadPath", type=str, default="", help="the path to the model to load, default is model name in current folder")
parser.add_argument("--savePath", type=str, default="", help="the file path where the model will be saved, default is current folder")
parser.add_argument("--NoSave", action="store_false", help="Will stop the training from saving")
parser.add_argument("--NoLoad", action="store_false", help="will disable the attempt to load previous model with matching name")
parser.add_argument("--verbose", action="store_true", help="enables verbose (default: false)")
parser.add_argument("--version", type=str, default="1", help="a version to append to the model name, default: 1")
parser.add_argument("--LoadVersion", type=str, default="1", help="the version of the model to load, default: 1")
parser.add_argument("--time", type=int, default=int(5e5), help="number of timesteps to train for, default: 5e5")
parser.add_argument("--fails", type=int, default=10, help="max number of invalid moves before ending the episode, default: 10")
parser.add_argument("--progress", action="store_false", help="wheteher or not to show progress bar default: true")
parser.add_argument("--device", type=str, default="auto",choices=('cuda','auto','cpu'), help="the device to use")
parser.add_argument("--randomplayers", action="store_true", help="will randomise the number of players for each episode, overrides --player")

# Parse the command line arguments
args = parser.parse_args()

# Assign the parsed arguments to variables
num_players = args.players
random_players = args.randomplayers
model_name = args.name
should_save = args.NoSave
should_load = args.NoLoad
save_path = args.savePath
load_path = args.loadPath
version = args.version
load_version = args.LoadVersion
progress = args.progress
device = args.device
verbose = int(args.verbose)
time = args.time
time = int(time)
max_fails = args.fails




if model_name == "": model_name = f"PPO_DominoTrain-{num_players}p"
save_name = model_name + f"-v{version}"
model_name += f"-v{load_version}"
if load_path == "": load_path = model_name
# You can now use these variables in your code
print("Number of Players:", num_players)
print("Model Name:", model_name)
print("Version: ", version)
print("Load Path: ", load_path)
print("Load Version: ", version)
print("Saving to: ", save_path + save_name)
print("Should Load:", should_load)
print("Should Save:", should_save)
print("Time:", time)

def mask_fn(env: gym.Env) -> np.ndarray:
    return env.getMaskDiscrete()


env = DominoTrainEnvMaskable(num_players, max_fails,random_players)  # Initialize env
env = ActionMasker(env, mask_fn)  # Wrap to enable masking


if should_load: 
    model = MaskablePPO.load(load_path)
    model.set_env(env)
else: 
    model = MaskablePPO(MaskableMultiInputActorCriticPolicy, env,verbose=verbose, device=device)
try:
    model.learn(total_timesteps=time, progress_bar=progress)
except KeyboardInterrupt:  # Graceful interrupt with Ctrl+C
    print("Training interrupted. Saving model and logs...")
    model.save("interrupted_model")
except Exception as e:
    traceback.print_exc()
    env.unwrapped.log_to_file("crash.txt")
if should_save: model.save(save_path+save_name)

# Evaluate the agent
# NOTE: If you use wrappers with your environment that modify rewards,
#       this will be reflected here. To evaluate with original rewards,
#       wrap environment in a "Monitor" wrapper before other wrappers.
mean_reward, std_reward = evaluate_policy(model, model.get_env(), n_eval_episodes=10)
print("Wval -  Mean Reward: ", mean_reward,"Standard Deviation of Reward: ", std_reward)
# Load the saved model
#model = PPO.load("PPO_DominoTrain")