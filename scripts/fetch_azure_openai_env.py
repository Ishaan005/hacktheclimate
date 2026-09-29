"""Write the team's Azure OpenAI settings from Key Vault to git-ignored .env.

Works on macOS, Linux and Windows after Azure CLI login to the hackathon
tenant. Secret values are captured in memory and never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def az(*args: str) -> str:
    result = subprocess.run(
        ["az", *args], capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team", type=int, default=12)
    args = parser.parse_args()

    resource_group = f"rg-hack-team{args.team}-swc"
    vaults = json.loads(az("keyvault", "list", "-g", resource_group, "-o", "json"))
    if not vaults:
        raise SystemExit(f"No Key Vault found in {resource_group}. Check your Azure login and team access.")
    vault = vaults[0]["name"]
    endpoint = az("keyvault", "secret", "show", "--vault-name", vault,
                  "-n", "azure-openai-endpoint", "--query", "value", "-o", "tsv")
    key = az("keyvault", "secret", "show", "--vault-name", vault,
             "-n", "azure-openai-key", "--query", "value", "-o", "tsv")
    if not endpoint or not key:
        raise SystemExit("Azure OpenAI endpoint or key is missing from Key Vault.")

    env_path = ROOT / ".env"
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(env_path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
        file.write(
            f"AZURE_OPENAI_ENDPOINT={endpoint}\n"
            f"AZURE_OPENAI_API_KEY={key}\n"
            "AZURE_OPENAI_DEPLOYMENT=gpt-4.1\n"
            "AZURE_OPENAI_API_VERSION=2024-10-21\n"
        )
    print(f"Wrote git-ignored {env_path} from Key Vault {vault} (secret values not printed).")


if __name__ == "__main__":
    main()
