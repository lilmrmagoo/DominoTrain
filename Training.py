import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.evaluation import evaluate_policy
from DominoEnv import DominoTrainEnv
import argparse
import os
import torch

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
parser.add_argument("--name", type=str,default="", help="Name to save the model under (optional)")
parser.add_argument("--save", type=bool, default=True, help="Boolean to determine if it should save (default: true)")
parser.add_argument("--override", action="store_true", help="Boolean to override if a model has the same name (default: false)")
parser.add_argument("--version", type=str, default="1", help="a version to append to the model name")
parser.add_argument("--time", type=int, default=int(5e5), help="number of timesteps to train for, default: 5e5")
parser.add_argument("--progress", type=bool, default=True, help="wheteher or not to show progress bar")

# Parse the command line arguments
args = parser.parse_args()

# Assign the parsed arguments to variables
num_players = args.players
model_name = args.name
should_save = args.save
override = args.override
version = args.version
progress = args.progress
time = args.time
time = int(time)

if model_name == "":
    model_name = f"PPO_DominoTrain-p{num_players}"
model_name += f"-v{version}"

# You can now use these variables in your code
print("Number of Players:", num_players)
print("Model Name:", model_name)
print("Should Save:", should_save)
print("Override:", override)
print("Time:", time)

env = DominoTrainEnv(num_players)

# Initialize the PPO agent
#model = PPO("MultiInputPolicy", env,verbose=1)

# Train the agent

# Save the trained model

# Load the trained agent
# NOTE: if you have loading issue, you can pass `print_system_info=True`
# to compare the system on which the model was trained vs the current one
# model = DQN.load("dqn_lunar", env=env, print_system_info=True)
if not override: model = PPO.load(model_name, env=env,verbose=1)
else: model = PPO("MultiInputPolicy", env,verbose=1)
model.learn(total_timesteps=time, progress_bar=progress)
if should_save: model.save(model_name)

# Evaluate the agent
# NOTE: If you use wrappers with your environment that modify rewards,
#       this will be reflected here. To evaluate with original rewards,
#       wrap environment in a "Monitor" wrapper before other wrappers.
mean_reward, std_reward = evaluate_policy(model, model.get_env(), n_eval_episodes=10)
print(mean_reward, std_reward)
# Load the saved model
#model = PPO.load("PPO_DominoTrain")