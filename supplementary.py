import os
import requests

from flask import redirect, render_template, session
from functools import wraps
from requests import Session
import json

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""
    symbol = symbol.upper()
    symbol = symbol.strip()
    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

        parameters = {
            'symbol':symbol
        }

        headers = {
            'Accepts':'application/json',
            'X-CMC_PRO_API_KEY':f'{api_key}'
        }

        session = Session()
        session.headers.update(headers)
        response = requests.get(url)

    except requests.RequestException:
        return None

    # Parse response
    try:
        response = session.get(url, params=parameters)
        quote = json.loads(response.text)

        #for ease of processing the string for the slug
        tempslug = str(quote["data"][symbol]["slug"])

        return {
            "name": quote["data"][symbol]["name"],
            "price": float(quote["data"][symbol]["quote"]["USD"]["price"]),
            "symbol": quote["data"][symbol]["symbol"],
            "pcchange24h": str(round(quote["data"][symbol]["quote"]["USD"]["percent_change_24h"], 2)) + "%",
            "pcchange7d": str(round(quote["data"][symbol]["quote"]["USD"]["percent_change_7d"], 2)) + "%",
            "pcchange30d": str(round(quote["data"][symbol]["quote"]["USD"]["percent_change_30d"], 2)) + "%",
            "mkt_rank": quote["data"][symbol]["cmc_rank"],
            "mkt_dom": str(round(quote["data"][symbol]["quote"]["USD"]["market_cap_dominance"], 2)) + "%",
            "slug": f"https://coinmarketcap.com/currencies/{tempslug}/",
        }

    except (KeyError, TypeError, ValueError):
        return None


def lookup_slug(name):
    """Look up quote for symbol."""
    # String Manipulation
    name = name.strip()
    name = name.replace(" ", "-")
    name = name.replace(".", "-")
    name = name.lower()
    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

        parameters = {
            'slug':name
        }

        headers = {
            'Accepts':'application/json',
            'X-CMC_PRO_API_KEY':f'{api_key}'
        }

        session = Session()
        session.headers.update(headers)
        response = requests.get(url)

    except requests.RequestException:
        return None

    # Parse response
    try:
        response = session.get(url, params=parameters)
        quote = json.loads(response.text)
        code = str(list(quote["data"].keys())[0])

        #for ease of processing the string for the slug
        tempslug = str(quote["data"][code]["slug"])

        return {
            "name": quote["data"][code]["name"],
            "price": float(quote["data"][code]["quote"]["USD"]["price"]),
            "symbol": quote["data"][code]["symbol"],
            "pcchange24h": str(round(quote["data"][code]["quote"]["USD"]["percent_change_24h"], 2)) + "%",
            "pcchange7d": str(round(quote["data"][code]["quote"]["USD"]["percent_change_7d"], 2)) + "%",
            "pcchange30d": str(round(quote["data"][code]["quote"]["USD"]["percent_change_30d"], 2)) + "%",
            "mkt_rank": quote["data"][code]["cmc_rank"],
            "mkt_dom": str(round(quote["data"][code]["quote"]["USD"]["market_cap_dominance"], 2)) + "%",
            "slug": f"https://coinmarketcap.com/currencies/{tempslug}/",
        }

    except (KeyError, TypeError, ValueError):
        return None

def usd(value):
    """Format value as USD."""
    return f"US${value:,.2f}"

def percent(value):
    """Format as percentage to 2bp."""
    return f"{value:,.2f}%"
