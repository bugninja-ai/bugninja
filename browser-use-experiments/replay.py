import asyncio
from src.replicator import Replicator


async def main():
    # Example usage
    replicator = Replicator("./traversals/traverse_20250607_094538_roacl3r7vz3vqxfinu52l915.json")
    await replicator.run(can_be_skipped_steps_list=[5, 6, 7, 8])


if __name__ == "__main__":
    asyncio.run(main())
