import discord
from discord.ext import commands, tasks
import aiohttp
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
from discord import Embed
import os

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 1374668441818234970))
PREFERENCES_CHANNEL_ID = 1375022714737397791

if not TOKEN:
    print("❌ TOKEN is not loaded from .env! Exiting.")
    exit()

# Database Setup
def create_database():
    conn = sqlite3.connect('pokemon_scraper.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            store TEXT,
            url TEXT UNIQUE,
            last_alert_time TIMESTAMP,
            stock_status TEXT,
            last_snapshot TEXT
        )
    ''')
    conn.commit()
    conn.close()

create_database()

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

ALERT_CHANNEL_IDS = {
    "Target": 1375022844932788295,
    "Walmart": 1375022872342298665,
    "Pokemon Center": 1375022931402424342,
    "Costco": 1376159495327059988,
    "Best Buy": 1378096400243621998,
    "Gamestop": 1377925895360348180,
    "Amazon": 1375022894395953164
}

ROLE_MAP = {
    "Target": 1375019423366123520,
    "Walmart": 1375020154978701383,
    "Pokemon Center": 1375020489327640617,
    "Amazon": 1375020367021736007,
    "Costco": 1376159294562635876,
    "Gamestop": 1377921654461566976,
    "151": 1375021890082701322,
    "Obsidian Flames": 1375021946336444467,
    "Prismatic Evolutions": 1375022126335004752,
    "Black Bolt": 1376147726600765460,
    "White Flare": 1376147970524975195,
    "Best Buy": 1378096222765715566
}

SV_PRODUCTS = {
    "Prismatic Evolutions": [
        {
            "name": "Prismatic Evolutions Super Premium Collection - Pokémon Center",
            "store": "Pokemon Center",
            "url": "https://www.pokemoncenter.com/product/10-10027-101/pokemon-tcg-scarlet-and-violet-prismatic-evolutions-super-premium-collection"
        },
        {
            "name": "Costco - Prismatic Evolutions ETB & Booster Bundle (SKU 1898462)",
            "store": "Costco",
            "url": "https://www.costco.com/.product.1898462.html"
        }
    ],
    "Black Bolt": [
        {
            "name": "Black Bolt Elite Trainer Box",
            "store": "Pokemon Center",
            "url": "https://www.pokemoncenter.com/product/10-10037-107"
        }
    ],
    "White Flare": [
        {
            "name": "White Flare Elite Trainer Box",
            "store": "Pokemon Center",
            "url": "https://www.pokemoncenter.com/product/10-10037-112"
        }
    ],
    "151": [
        {
            "name": "151 Elite Trainer Box",
            "store": "Pokemon Center",
            "url": "https://www.pokemoncenter.com/product/290-85604/pokemon-tcg-scarlet-violet-151-elite-trainer-box"
        },
        {
            "name": "151 Poster Collection",
            "store": "Pokemon Center",
            "url": "https://www.pokemoncenter.com/product/290-85602"
        }
    ],
    "Obsidian Flames": [
        {
            "name": "Obsidian Flames Elite Trainer Box",
            "store": "Pokemon Center",
            "url": "https://www.pokemoncenter.com/product/290-85375"
        }
    ],
    "Paradox Rift": [
        {
            "name": "Paradox Rift Elite Trainer Box",
            "store": "Pokemon Center",
            "url": "https://www.pokemoncenter.com/product/290-85434"
        }
    ],
    "Temporal Forces": [
        {
            "name": "Temporal Forces Elite Trainer Box",
            "store": "Pokemon Center",
            "url": "https://www.pokemoncenter.com/product/290-85507"
        }
    ],
    "Twilight Masquerade": [
        {
            "name": "Twilight Masquerade Elite Trainer Box",
            "store": "Pokemon Center",
            "url": "https://www.pokemoncenter.com/product/290-85691"
        }
    ],
    "Shrouded Fable": [
        {
            "name": "Shrouded Fable Elite Trainer Box",
            "store": "Pokemon Center",
            "url": "# TODO: Add official product URL when live"
        }
    ]
}

PRODUCTS = []
for set_name, items in SV_PRODUCTS.items():
    for item in items:
        item.setdefault("sets", []).append(set_name)
        PRODUCTS.append(item)

# Database Helpers
def get_product_status(url):
    conn = sqlite3.connect('pokemon_scraper.db')
    cursor = conn.cursor()
    cursor.execute('SELECT stock_status, last_alert_time, last_snapshot FROM products WHERE url = ?', (url,))
    result = cursor.fetchone()
    conn.close()
    return result if result else (None, None, None)

def update_product_status(url, stock_status, html_snapshot=""):
    conn = sqlite3.connect('pokemon_scraper.db')
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute('''
        INSERT INTO products (url, stock_status, last_alert_time, last_snapshot)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET stock_status = ?, last_alert_time = ?, last_snapshot = ?
    ''', (url, stock_status, now, html_snapshot, stock_status, now, html_snapshot))
    conn.commit()
    conn.close()

# Alert Embed Function
async def send_product_alert_embed(channel, product, role_mentions):
    product_name = product["name"]
    product_url = product["url"]
    product_price = product.get("price", "N/A")
    product_image = product.get("image")

    embed = Embed(
        title=product_name,
        url=product_url,
        description=f"**New Item**\n\n**Price:** ${product_price}\n\nNo ATC links available",
        color=discord.Color.blue()
    )

    embed.add_field(name="Website", value=f"[{product['store']}]({product_url})", inline=False)
    embed.add_field(
        name="Links",
        value=(
            "[eBay](https://www.ebay.com) - [Amazon](https://www.amazon.com) - "
            "[Walmart](https://www.walmart.com) - [Keepa](https://keepa.com) - "
            "[SellerAmp](https://selleramp.com) - "
            f"[Google](https://google.com/search?q={product_name.replace(' ', '+')})"
        ),
        inline=False
    )

    if product_image:
        embed.set_thumbnail(url=product_image)

    embed.set_footer(text=f"Phoenix Monitors • {datetime.now().strftime('%I:%M:%S.%f %p EST')}")
    await channel.send(embed=embed)
    await channel.send(f"{role_mentions} | **{product_name}**")

# Product Checking Task
@tasks.loop(seconds=60)
async def check_products():
    await bot.wait_until_ready()
    async with aiohttp.ClientSession() as session:
        for product in PRODUCTS:
            try:
                current_status, last_alert_time, last_snapshot = get_product_status(product["url"])
                async with session.get(product["url"]) as resp:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    image = None
                    price = None

                    img_tag = soup.find("img")
                    if img_tag and img_tag.has_attr("src"):
                        image = img_tag["src"].strip()

                    price_tag = soup.find(string=lambda t: "$" in t)
                    if price_tag:
                        price = price_tag.strip().split(" ")[0].replace("$", "")

                    if image:
                        product["image"] = image
                    if price:
                        product["price"] = price

                    if "costco.com" in product["url"]:
                        current_snapshot = soup.get_text().strip()
                        changed = last_snapshot != current_snapshot
                        in_stock = changed
                    else:
                        add_to_cart = soup.find("button", string=lambda t: t and "add to cart" in t.lower())
                        in_stock = add_to_cart and not add_to_cart.has_attr("disabled")
                        current_snapshot = ""

                if in_stock:
                    update_product_status(product["url"], "in stock", current_snapshot)
                    now = datetime.now()
                    if not last_alert_time or (now - datetime.strptime(last_alert_time, "%Y-%m-%d %H:%M:%S.%f")).total_seconds() > 600:
                        channel_id = ALERT_CHANNEL_IDS[product["store"]]
                        channel = bot.get_channel(channel_id)
                        if channel:
                            role_mentions = []
                            store_role_id = ROLE_MAP.get(product["store"])
                            if store_role_id:
                                role_mentions.append(f"<@&{store_role_id}>")
                            for set_name in product["sets"]:
                                role_id = ROLE_MAP.get(set_name)
                                if role_id:
                                    role_mentions.append(f"<@&{role_id}>")
                            role_mentions_str = " ".join(role_mentions)
                            await send_product_alert_embed(channel, product, role_mentions_str)
            except Exception as e:
                print(f"❌ Error checking {product['name']}: {e}")

# Bot Events
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    check_products.start()

@bot.command(name="testalert")
async def test_alert(ctx, *, product_name: str = None):
    if not product_name:
        await ctx.send("❌ Please specify the product name (or part of it).")
        return
    match = next((p for p in PRODUCTS if product_name.lower() in p["name"].lower()), None)
    if not match:
        await ctx.send("❌ No product found matching that name.")
        return
    channel_id = ALERT_CHANNEL_IDS.get(match["store"])
    if not channel_id:
        await ctx.send(f"❌ Store not supported: {match['store']}")
        return
    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.send(f"❌ Couldn't find alert channel for {match['store']}")
        return
    role_mentions = []
    store_role_id = ROLE_MAP.get(match["store"])
    if store_role_id:
        role_mentions.append(f"<@&{store_role_id}>")
    for set_name in match["sets"]:
        role_id = ROLE_MAP.get(set_name)
        if role_id:
            role_mentions.append(f"<@&{role_id}>")
    role_mentions_str = " ".join(role_mentions)
    await send_product_alert_embed(channel, match, role_mentions_str)
    await ctx.send("✅ Test alert sent.")

bot.run(TOKEN)
