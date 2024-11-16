import asyncio
import json
import uuid
import ssl
import random
import sys
import time
from datetime import datetime, timedelta

from loguru import logger
import aiohttp

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<white>{time:HH:mm:ss}</white> | {level} | {message}",
    level="DEBUG",  # Set to DEBUG for detailed logs, change to INFO for less verbosity
    colorize=True
)

# Rate limit settings
RATE_LIMIT = {
    'requests_per_connection': 100, 
    'min_request_delay': 5,  # Minimum delay between requests (seconds)
    'max_request_delay': 20,  # Maximum delay between requests (seconds)
    'cooldown_time': 100,     # Cooldown after reaching rate limit (seconds)
}

async def connect_to_wss(user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, "no_proxy"))
    logger.info(f"[*] Starting WebSocket client with Device ID: {device_id}")

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    urilist = ["wss://proxy.wynd.network:4444/", "wss://proxy.wynd.network:4650/"]

    while True:  # Reconnection loop
        uri = random.choice(urilist)
        logger.info(f"[*] Attempting to connect to {uri}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(uri, ssl=ssl_context, timeout=10) as websocket:
                    logger.success("[+] Successfully connected to WebSocket")

                    # Ping sender
                    async def send_ping():
                        request_count = 0
                        while True:
                            if request_count >= RATE_LIMIT['requests_per_connection']:
                                logger.warning("[!] Reached request limit, cooling down...")
                                await asyncio.sleep(RATE_LIMIT['cooldown_time'])
                                request_count = 0
                                continue

                            delay = random.uniform(
                                RATE_LIMIT['min_request_delay'], 
                                RATE_LIMIT['max_request_delay']
                            )
                            await asyncio.sleep(delay)

                            send_message = json.dumps(
                                {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}}
                            )
                            await websocket.send_str(send_message)
                            request_count += 1
                            logger.success(f"[+] PING sent [{request_count}/{RATE_LIMIT['requests_per_connection']}]")

                            if request_count % 10 == 0:
                                cool_time = random.randint(30, 60)
                                logger.info(f"[~] Mini cooldown for {cool_time}s after 10 requests")
                                await asyncio.sleep(cool_time)

                    # Start the ping sender as a background task
                    asyncio.create_task(send_ping())

                    # Listen for responses
                    while True:
                        response = await websocket.receive()

                        if response.type == aiohttp.WSMsgType.TEXT:
                            try:
                                message = json.loads(response.data)
                                logger.info(f"[+] Received message: {message}")
                            except json.JSONDecodeError:
                                logger.warning("[!] Received invalid JSON message")
                        elif response.type in [aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR]:
                            logger.error("[!] WebSocket connection closed or error occurred")
                            break
                        else:
                            logger.warning("[!] Received unsupported message type")
        except Exception as e:
            logger.error(f"[!] Exception occurred: {e}")

        # Reconnect after 5 seconds
        logger.info("[*] Reconnecting in 5 seconds...")
        await asyncio.sleep(5)

async def main():
    user_id = "test_user"  # Replace with dynamic user ID if needed
    await connect_to_wss(user_id)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Script terminated unexpectedly: {e}")
