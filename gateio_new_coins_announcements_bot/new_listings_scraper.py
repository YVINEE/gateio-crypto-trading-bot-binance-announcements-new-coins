import ast
import json
import os.path
import random
import re
import string
import time

import requests
from gate_api import ApiClient
from gate_api import SpotApi

import gateio_new_coins_announcements_bot.globals as globals
from gateio_new_coins_announcements_bot.auth.gateio_auth import load_gateio_creds
from gateio_new_coins_announcements_bot.load_config import load_config
from gateio_new_coins_announcements_bot.logger import logger
from gateio_new_coins_announcements_bot.store_order import load_order

config = load_config("config.yml")
client = load_gateio_creds("auth/auth.yml")
spot_api = SpotApi(ApiClient(client))

supported_currencies = None

previously_found_coins = set()

binance_page_size = 0

def get_binance_announcement():
    """
    Retrieves new coin listing announcements

    """
    # Generate random query/params to help prevent caching
    global binance_page_size
    if (binance_page_size >= 50):
        binance_page_size = 1
    else:
        binance_page_size = binance_page_size + 1             
    queries = [
        "type=1",
        "catalogId=48",
        "pageNo=1",
        f"pageSize={str(binance_page_size)}"
    ]
    random.shuffle(queries)
    request_url=f"https://www.binance.com/gateway-api/v1/public/cms/article/list/query?{queries[0]}&{queries[1]}&{queries[2]}&{queries[3]}"

    latest_announcement = requests.get(request_url)
    if latest_announcement.status_code == 200:
        try:
            if ("Miss from cloudfront" not in latest_announcement.headers["X-Cache"]):
                logger.debug(f'X-Cache (Binance): {latest_announcement.headers["X-Cache"]}', extra={"TELEGRAM": "ERROR"})
                logger.debug(f"request_url: {request_url}")
        except KeyError:
            # No X-Cache header was found - great news, we're hitting the source.
            pass

        latest_announcement = latest_announcement.json()
        return latest_announcement["data"]["catalogs"][0]["articles"][0]["title"]
    else:
        logger.error(f"Error pulling binance announcement page: {latest_announcement.status_code}")
        logger.debug(f"request_url: {request_url}")
        return ""


def get_kucoin_announcement():
    """
    Retrieves new coin listing announcements from Kucoin

    """
    # Generate random query/params to help prevent caching
    rand_page_size = random.randint(1, 200)
    letters = string.ascii_letters
    random_string = "".join(random.choice(letters) for i in range(random.randint(10, 20)))
    random_number = random.randint(1, 99999999999999999999)
    queries = [
        "page=1",
        f"pageSize={str(rand_page_size)}",
        "category=listing",
        "lang=en_US",
        f"rnd={str(time.time())}",
        f"{random_string}={str(random_number)}",
    ]
    random.shuffle(queries)
    
    request_url = (
        f"https://www.kucoin.com/_api/cms/articles?"
        f"?{queries[0]}&{queries[1]}&{queries[2]}&{queries[3]}&{queries[4]}&{queries[5]}")

    latest_announcement = requests.get(request_url)
    if latest_announcement.status_code == 200:
        try:
            if ("Miss from cloudfront" not in latest_announcement.headers["X-Cache"]):
                logger.debug(f'X-Cache (Kucoin): {latest_announcement.headers["X-Cache"]}', extra={"TELEGRAM": "ERROR"})
                logger.debug(f"request_url: {request_url}")                
        except KeyError:
            # No X-Cache header was found - great news, we're hitting the source.
            pass

        latest_announcement = latest_announcement.json()
        return latest_announcement["items"][0]["title"]
    else:
        logger.error(f"Error pulling kucoin announcement page: {latest_announcement.status_code}")
        logger.debug(f"request_url: {request_url}")
        return ""


def get_last_coin():
    """
    Returns new Symbol when appropriate
    """
    # scan Binance Announcement
    binance_announcement = get_binance_announcement()
    binance_coin = re.findall(r"\(([^)]+)", binance_announcement)
    found_coin = None
    exchange_found_coin = None
    # returns nothing if it's an old coin or it's not an actual coin listing
    if (
        "Will List" not in binance_announcement
        or binance_coin[0] == globals.latest_listing
        or binance_coin[0] in previously_found_coins
    ):
        # enable Kucoin Announcements if True in config
        if config["TRADE_OPTIONS"]["KUCOIN_ANNOUNCEMENTS"]:
            kucoin_announcement = get_kucoin_announcement()
            kucoin_coin = re.findall(r"\(([^)]+)", kucoin_announcement)
            # if the latest Binance announcement is not a new coin listing,
            # or the listing has already been returned, check kucoin
            if ("Gets Listed" in kucoin_announcement
            and len(kucoin_coin) > 0
            and kucoin_coin[0] != globals.latest_listing
            and kucoin_coin[0] not in previously_found_coins
            ):
                if len(kucoin_coin) == 1:
                        found_coin = kucoin_coin[0]
                        exchange_found_coin = "Kucoin"
                        previously_found_coins.add(found_coin)
                        logger.info("New Kucoin coin detected: " + found_coin)
                if len(kucoin_coin) != 1:
                        found_coin = None
                        exchange_found_coin = None
    else:
        if len(binance_coin) == 1:
            found_coin = binance_coin[0]
            exchange_found_coin = "Binance"
            previously_found_coins.add(found_coin)
            logger.info("New Binance coin detected: " + found_coin)
        if len(binance_coin) != 1:
            found_coin = None
            exchange_found_coin = None

    return found_coin, exchange_found_coin


def store_new_listing(listing, exchange):
    """
    Only store a new listing if different from existing value
    """
    if listing and not listing == globals.latest_listing:
        logger.info("New listing detected")
        globals.latest_listing = listing
        globals.latest_exchange_listing = exchange
        globals.buy_ready.set()


def search_and_update():
    """
    Pretty much our main func
    """
    while not globals.stop_threads:
        sleep_time = 3
        for x in range(sleep_time):
            time.sleep(1)
            if globals.stop_threads:
                break
        try:
            latest_coin, exchange_latest_coin = get_last_coin()
            if latest_coin:
                store_new_listing(latest_coin, exchange_latest_coin)
            elif os.path.isfile("test_new_listing.json"):
                store_new_listing(load_order("test_new_listing.json"), "test")
                if os.path.isfile("test_new_listing.json.used"):
                    os.remove("test_new_listing.json.used")
                os.rename("test_new_listing.json", "test_new_listing.json.used")
        except Exception as e:
            logger.error(e)
    else:
        logger.info("while loop in search_and_update() has stopped.")


def get_all_currencies(single=False):
    """
    Get a list of all currencies supported on gate io
    :return:
    """
    global supported_currencies
    while not globals.stop_threads:
        logger.info("Getting the list of supported currencies from gate io")
        all_currencies = ast.literal_eval(str(spot_api.list_currencies()))
        currency_list = [currency["currency"] for currency in all_currencies]
        with open("currencies.json", "w") as f:
            json.dump(currency_list, f, indent=4)
            logger.info(
                "List of gate io currencies saved to currencies.json. Waiting 5 " "minutes before refreshing list..."
            )
        supported_currencies = currency_list
        if single:
            return supported_currencies
        else:
            for x in range(300):
                time.sleep(1)
                if globals.stop_threads:
                    break
    else:
        logger.info("while loop in get_all_currencies() has stopped.")


def load_old_coins():
    if os.path.isfile("old_coins.json"):
        with open("old_coins.json") as json_file:
            data = json.load(json_file)
            logger.debug("Loaded old_coins from file")
            return data
    else:
        return []


def store_old_coins(old_coin_list):
    with open("old_coins.json", "w") as f:
        json.dump(old_coin_list, f, indent=2)
        logger.debug("Wrote old_coins to file")
