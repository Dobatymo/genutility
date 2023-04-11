import torch
from torch.distributions.categorical import Categorical


def categorical(probs: torch.tensor, size: torch.tensor = torch.Size()) -> torch.tensor:
    return Categorical(probs).sample(size)
