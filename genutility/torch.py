from typing import TYPE_CHECKING

import torch
from torch.distributions.categorical import Categorical

if TYPE_CHECKING:
	from torch import tensor

def categorical(probs, size=torch.Size()):
	# type: (tensor, tensor) -> tensor

	return Categorical(probs).sample(size)
