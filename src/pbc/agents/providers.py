"""Provider selection: the one configuration value, and how to switch it.

The harness knows a provider by one configuration value, ``PROVIDER`` below.
To switch provider:

1. Write ``src/pbc/agents/clients/<name>.py`` with a function ``make_client()``
   that returns an object of the shape ``pbc.agents.messages.ModelClient``:
   a ``model`` attribute, a ``secrets`` attribute, and a ``complete`` method.
   Read the key from the provider's own environment variable with
   ``pbc.agents.secrets.Secret``, expose it in ``secrets`` so that the harness
   can remove it from what the model returns, and import the provider's SDK
   only inside that module.
2. Change ``PROVIDER`` to ``"<name>"``.

Nothing else imports a provider SDK or names a provider's key variable, and
the replay client and the tests do not depend on any of them.
"""

import importlib
import re

from pbc.agents.messages import ModelClient

PROVIDER = "openai"

_NAME = re.compile(r"[a-z][a-z0-9_]*")


def load_client(provider: str = PROVIDER) -> ModelClient:
    """The live client of ``provider``, built from the key in the environment."""
    if not _NAME.fullmatch(provider):
        raise ValueError(f"{provider!r} is not a provider name")
    module = importlib.import_module(f"pbc.agents.clients.{provider}")
    return module.make_client()
