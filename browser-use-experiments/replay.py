import asyncio
from src.replicator import Replicator
import glob
import os


async def main():
    list_of_files = glob.glob("./traversals/*.json")
    latest_replay_file = max(list_of_files, key=os.path.getctime)

    replicator = Replicator(
        json_path=latest_replay_file,
        secrets={
            "credential_email": "feligaf715@lewou.com",
            "credential_password": "9945504JA",
            "new_username": "almafa",
        },
    )
    await replicator.run()


if __name__ == "__main__":
    asyncio.run(main())
