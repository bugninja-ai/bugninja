import base64
import cv2
import numpy as np
from playwright.async_api import async_playwright


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()

        session = await context.new_cdp_session(page)
        await session.send(
            "Page.startScreencast",
            {"format": "jpeg", "quality": 80, "maxWidth": 1280, "maxHeight": 720},
        )

        # Setup OpenCV video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter("custom_recording.mp4", fourcc, 15.0, (1280, 720))

        async def on_frame(frame):
            data = base64.b64decode(frame["data"])
            np_arr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            out.write(img)

            # Acknowledge frame, otherwise Chrome stops sending
            await session.send("Page.screencastFrameAck", {"sessionId": frame["sessionId"]})

        # Register callback properly
        session.on("Page.screencastFrame", on_frame)

        await page.goto("https://example.com")
        await page.wait_for_timeout(5000)  # record for 5 sec

        # Stop recording
        await session.send("Page.stopScreencast")
        out.release()
        await browser.close()


import asyncio

asyncio.run(run())
