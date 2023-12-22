import requests
import random
import threading
import time

from simple_chalk import green, red, yellow, magenta, cyan, blueBright

WORKERS = 1_000

DISCORD_TOKEN_REDEEM_URL = "https://discord.com/billing/partner-promotions/1180231712274387115/{}"
TOKEN_URL = "https://api.discord.gx.games/v1/direct-fulfillment"
BODY = "{\"partnerUserId\":\"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\"}"
HEADERS = {
  "accept": "*/*",
  "accept-language": "en-US,en;q=0.9",
  "content-type": "application/json",
  "sec-ch-ua": "\"Opera GX\";v=\"105\", \"Chromium\";v=\"119\", \"Not?A_Brand\";v=\"24\"",
  "sec-ch-ua-mobile": "?0",
  "sec-ch-ua-platform": "\"macOS\"",
  "sec-fetch-dest": "empty",
  "sec-fetch-mode": "cors",
  "sec-fetch-site": "cross-site"
}

PROXIES = []
OUT_FILE = "tokens.txt"
STATS_FILE = "stats.txt"
INFORMATION_FILE = "information.txt"

MAX_RETRIES = 10

PROXY_FETCH_DELAY = 60

FORK_AMOUNT = 5

# Keep track of the retries
# Add the proxy to the list if it fails
retries = {}

# For proxies that are working either by getting a ratelimit and or a token
exceptions = {}

# Keep track of the stats
stats = {}

# Status bar text
status_bar_text = ""

# Tokens per second/minutes/hour
tps = 0
tpm = 0
tph = 0
tpd = 0

# Tokens added
tokens_added = 0

# Time started
time_started = time.time()

def add_retry(proxy: str):
  retries[proxy] = retries.get(proxy, 0) + 1

def add_exception(proxy: str):
  exceptions[proxy] = True

def stats_add(proxy: str):
  stats[proxy] = stats.get(proxy, 0) + 1

def generate_stats():
  with open(STATS_FILE, "w") as f:
    f.write("\n".join([f"{proxy}: {count}" for proxy, count in stats.items()]))
    f.close()

def remove_proxy(proxy: str):
  if proxy in PROXIES:
    PROXIES.remove(proxy)
  print(magenta(f"Removed proxy: {proxy}"))

def get_proxies():
  print(yellow("Getting proxies..."))

  try:
    request = requests.get("https://api.proxyscrape.com/?request=getproxies&proxytype=http&timeout=10000&country=all&ssl=all&anonymity=all")

    if request.status_code != 200:
      print(red(f"Unable to get proxies: {request.status_code} for the reason of {request.reason}"))
      return
  
    new_proxies = request.text.splitlines()
    PROXIES.extend(new_proxies)
    print(blueBright(f"Got {len(new_proxies)} proxies. Total: {len(PROXIES)}"))
  except Exception as e:
    print(red(f"Some error occurred when fetching proxies | {e}"))

def worker_get_proxies():
  get_proxies()
  threading.Timer(PROXY_FETCH_DELAY, worker_get_proxies).start()

def request_token(proxy: str):
  global tokens_added

  print(yellow(f"Attempting to get token using proxy: {proxy}"))

  try:
    request = requests.post(
      TOKEN_URL, 
      headers=HEADERS, 
      data=BODY, 
      proxies={"https": proxy},
      timeout=20
    )

    if request.status_code == 429:
      print(cyan(f"Proxy: {proxy} has been ratelimited."))
      return
    
    if request.status_code != 200:
      print(red(f"Unable to get token: {request.status_code} for the reason of {request.reason}"))
      raise Exception("Not OK")
      
    token = request.json()["token"]

    stats_add(proxy)
    add_exception(proxy)
    generate_stats()
    print(green(f"Gotten token: {token} using proxy: {proxy}"))

    tokens_added += 1
    
    with open(OUT_FILE, "a") as f:
      f.write(DISCORD_TOKEN_REDEEM_URL.format(token) + "\n")
      f.close()

    print(magenta("Trying to exhaust the proxy..."))

    for _ in range(FORK_AMOUNT):
      threading.Thread(target=request_token, args=(proxy,)).start()
  except Exception as e:
    print(red(f"Unable to get token using proxy: {proxy} which rased an error of {e}."))
    add_retry(proxy)

    if proxy in exceptions:
      print(magenta(f"Proxy: {proxy} was exceptioned"))
      return

    if retries.get(proxy, 0) >= MAX_RETRIES:
      print(magenta(f"Proxy: {proxy} has reached the max retries of {MAX_RETRIES}. Removing"))
      remove_proxy(proxy)
      return

def worker_request_token():
  while True:
    try:
      request_token(random.choice(PROXIES))
    except:
      pass

def show_information():
  while True:
    with open(INFORMATION_FILE, "w") as f:
      ten_thousand_tps = 0 if tps == 0 else 10_000 / tps

      f.write(f"Proxies: {len(PROXIES)} | Retries: {len(retries)} | Exceptions: {len(exceptions)} | TP(S,M,H,D): {tps:.0f}/s, {tpm:.0f}/m, {tph:.0f}/h, {tpd:.0f}/d | Tokens gotten in total: {tokens_added} | 10k tokens per {ten_thousand_tps:.0f} seconds | Current threads: {threading.active_count()}\n")
      f.close()
    time.sleep(.1)

def worker_tokens_per_second():
  global tps
  global tpm
  global tph
  global tpd

  while True:
    tps = tokens_added / (time.time() - time_started)
    tpm = tps * 60
    tph = tpm * 60
    tpd = tph * 24

    time.sleep(1)

def main():
  try:
    get_proxies()
    threading.Timer(PROXY_FETCH_DELAY, worker_get_proxies).start()
    for _ in range(WORKERS):
      threading.Thread(target=worker_request_token).start()
    threading.Thread(target=show_information).start()
    threading.Thread(target=worker_tokens_per_second).start()
  except KeyboardInterrupt:
    pass

if __name__ == "__main__":
  main()