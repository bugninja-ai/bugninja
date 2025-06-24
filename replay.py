import asyncio
import glob
import os

from src.replicator_run import ReplicatorRun


async def main():
    list_of_files = glob.glob("./traversals/*.json")
    latest_replay_file = max(list_of_files, key=os.path.getctime)

    replicator = ReplicatorRun(json_path=latest_replay_file)
    await replicator.start()


if __name__ == "__main__":
    asyncio.run(main())
