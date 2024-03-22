import torch
from torch.distributions.categorical import Categorical

_ZERO_SIZE = torch.Size()


def categorical(probs: torch.tensor, size: torch.tensor = _ZERO_SIZE) -> torch.tensor:
    return Categorical(probs).sample(size)
