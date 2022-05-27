import os
import ast

from cs50 import SQL
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from supplementary import apology, login_required, lookup, usd, lookup_slug

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///watchlist.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show watchlist"""
    # IF REMOVE BUTTON IS SELECTED, REMOVE FROM WATCHLIST:
    if request.method == "POST":
        if request.form.get("rem_watch"):
            for i in range(len(session["watchlist"])):
                if session["watchlist"][i]["symbol"] == request.form.get("rem_watch"):
                    del session["watchlist"][i]
                    break

            db.execute("DELETE FROM watchlists WHERE user_id = ? and symbols = ?", session["user_id"], request.form.get("rem_watch"))

    data = db.execute("SELECT symbols FROM watchlists WHERE user_id = ?", session["user_id"])

    if data == []:
        return render_template("index.html", no_watchlist="1")

    watchlist = []
    for i in range(len(data)):
        watchlist.append(lookup(data[i]["symbols"]))
        # print(watchlist[i])
        watchlist[i]["price"] = usd(watchlist[i]["price"])

    # SORT WATCHLIST BY MARKET CAP
    swaps = 1
    while swaps > 0:
        swaps = 0
        for i in range(len(watchlist) - 1):
            if int(watchlist[i]["mkt_rank"]) > int(watchlist[i + 1]["mkt_rank"]):
                watchlist[i], watchlist[i + 1] = watchlist[i + 1], watchlist[i]
                swaps += 1

    # Keep in session
    watchlist = {'watchlist':watchlist}
    session.update(watchlist)

    return render_template("index.html", watchlist=session["watchlist"])


@app.route("/portfolio", methods=["GET", "POST"])
@login_required
def portfolio():
    """Show portfolio of cryptos"""
    # GET BALANCE
    rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    balance = rows[0]["cash"]

    # CALCULATE PORTFOLIO
    transactions = db.execute("SELECT * FROM transactions WHERE user_id = ? GROUP BY symbols", session["user_id"]) # THE 'GROUP BY' makes symbols DISTINCT

    # IF THERE ARE NO TRANSACTIONS FOR THE USER
    if transactions == []:

        # TOTAL PORTFOLIO VALUE
        holding_sums = 0
        total = balance + holding_sums
        user_vals = {'total':total, 'holding_sum':holding_sums}
        uports = {'user_vals':user_vals}
        session.update(uports)

        # KEEP TABLE IN COOKIES
        udata = {'user_data':transactions}
        session.update(udata)

        return render_template("portfolio.html", balance=usd(balance), empty_portfolio="1", total=usd(total), holding_total=usd(holding_sums))

    # CREATES DUPS - A LIST OF DICTIONARIES THAT ONLY CONTAIN SYMBOLS THAT APPEAR MORE THAN ONCE, AND HOW OFTEN THEY APPEAR, FOR LATER COMPARISON
    dups = db.execute("SELECT COUNT(symbols), symbols FROM transactions WHERE user_id = ? GROUP BY symbols;", session["user_id"])
    length = len(dups)
    finished = 1

    while finished != 0:
        finished = 0
        for i in range(length):
            if dups[i]["COUNT(symbols)"] < 2:
                del dups[i]
                finished += 1
                break
        length = len(dups)

    # INTRODUCE VARIABLES
    avgprs = 0 # avgprs = AVERAGE /BUY/ PRICE
    holding_sums = 0 # sum of the value of ALL HOLDINGS (no cash)

    for i in range(len(transactions)): # FOR EVERY ENTRY IN THE TRANSACTIONS LIST

        # HANDLE THE DUPLICATE + CASES
        for j in range(len(dups)):
            if dups[j]["symbols"] == transactions[i]["symbols"]:
                agg = db.execute("SELECT * FROM transactions WHERE user_id = ? AND symbols = ?;", session["user_id"], dups[j]["symbols"])

                tcost = 0
                bqty = 0
                agg_qty = 0

                for k in range(len(agg)):
                    if agg[k]["qtys"] > 0:
                        tcost = tcost + (agg[k]["prices"] * agg[k]["qtys"])
                        bqty = bqty + agg[k]["qtys"]

                    agg_qty = agg_qty + agg[k]["qtys"]

                # UPDATE DICTIONARY VALUES FOR AVERAGE BUY PRICE AND QUANTITY.
                if agg_qty != 0:
                    avgprs = tcost / bqty
                    transactions[i]["prices"] = avgprs
                    transactions[i]["qtys"] = agg_qty

                elif agg_qty == 0:
                    transactions[i]["qtys"] = 0

        # HEREON APPLIES TO ALL CASES - INSERT CURRENT PRICE
        quote = lookup(transactions[i]["symbols"])
        current_prices = quote["price"]
        cprices = {'cprices': usd(current_prices)}
        transactions[i].update(cprices)

        # FOR NAMES
        name = {'name': quote["name"]}
        transactions[i].update(name)

        # ADD 'CURRENT VALUES' ENTRIES // WITHOUT CONVERTING IT FOR DISPLAY
        currentval = {'cvalues': float(current_prices * transactions[i]["qtys"])}
        transactions[i].update(currentval)

        # ADD 24hr CHANGE
        pcchange24h = {'pcchange24h': quote["pcchange24h"]}
        transactions[i].update(pcchange24h)

        # %CHANGE ENTRIES (PNL)
        changes = round(((current_prices - transactions[i]["prices"]) / transactions[i]["prices"]) * 100, 2)
        changes_str = f"{changes}%"
        pnl = {'pnl': changes_str}
        transactions[i].update(pnl)

        # FOR SLUG LINK
        slug = {'slug': quote["slug"]}
        transactions[i].update(slug)

        # FOR CALCULATING TOTAL PORTFOLIO
        holding_sums = holding_sums + (current_prices * transactions[i]["qtys"])

        # PRICES AND QUANTITIES FOR DISPLAY PURPOSES
        transactions[i]["prices"] = usd(transactions[i]["prices"])
        transactions[i]["qtys"] = round(transactions[i]["qtys"], 6)

    # REMOVE NET QTY's of ZERO OR LESS from TABLE
    length = len(transactions)
    finished = 1
    while finished != 0:
        finished = 0
        for i in range(length):
            if float(transactions[i]["qtys"]) < 0.0001 or float(transactions[i]["cvalues"]) < 0.01:
                del transactions[i]
                finished += 1
                break

        length = len(transactions)

    #CVALUES ARE CONVERTED FOR DISPLAY HERE
    for i in range(len(transactions)):
        transactions[i]["cvalues"] = usd(transactions[i]["cvalues"])

    if round(holding_sums, 2) == 0:
        return render_template("portfolio.html", balance=usd(balance), empty_portfolio="1")

    # TOTAL PORTFOLIO VALUE
    total = balance + holding_sums
    user_vals = {'total':total, 'holding_sum':holding_sums}
    uports = {'user_vals':user_vals}
    session.update(uports)

    # KEEP TABLE IN COOKIES
    udata = {'user_data':transactions}
    session.update(udata)

    return render_template("portfolio.html", balance=usd(balance), entries=transactions, total=usd(total), holding_total=usd(holding_sums))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    balance = rows[0]["cash"]

    if request.method == "POST":

        # HANDLE ERROR: BOTH QTY AND FIAT FIELDS ARE FILLED
        if request.form.get("qty") and request.form.get("qty_in_fiat"):
            return render_template("buy.html", balance=usd(balance), buy_err="1")

        quote = lookup(request.form.get("symbol"))

        # HANDLE ERROR: SYMBOL/NAME DOESNT EXIST
        if not quote:
            quote = lookup_slug(request.form.get("symbol"))
            if not quote:
                return render_template("buy.html", balance=usd(balance), buy_err="2")


        # INTRODUCE VARIABLES
        cost = 0
        bqty = 0
        bsymbol = quote["symbol"]
        bprice = quote["price"]

        if request.form.get("qty"):
            bqty = float(request.form.get("qty"))
            cost = bprice * bqty

        elif request.form.get("qty_in_fiat"):
            cost = float(request.form.get("qty_in_fiat"))
            bqty = round(cost / bprice, 8)

        newbalance = balance - cost

        # HANDLE ERROR: NOT ENOUGH MONEY
        if newbalance < 0:
            return render_template("buy.html", balance=usd(balance), buy_err="3")

        # SEND TO CONFIRMATION
        txn_data = {'user_id':session["user_id"], 'symbols':bsymbol, 'prices':bprice, 'qtys':bqty, 'init_balance':balance, 'newbalance':newbalance, 'size':cost}
        return render_template("confirm.html", txn_data=txn_data, action="buy")

    else:
        return render_template("buy.html", balance=usd(balance))


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    balance = rows[0]["cash"]

    # GET TABLE
    data = db.execute("SELECT id, symbols, prices, qtys, times FROM transactions WHERE user_id = ? ORDER BY id DESC", session["user_id"])

    # IF TRANSACTION HISTORY IS EMPTY
    if data == []:
        return render_template("history.html", balance=usd(balance), history_err="1")

    for i in range(len(data)):
        # CALCULATE VALUE
        value = float(data[i]["qtys"]) * float(data[i]["prices"])

        # ADD ACTION COLUMN AND EDIT VALUE COLUMN
        if float(data[i]["qtys"]) < 0:
            adder = {'action':'Sell'}
            data[i].update(adder)
            value = "-" + usd(value * (-1))
            data[i]["qtys"] = float(data[i]["qtys"]) * (-1)
        elif float(data[i]["qtys"]) > 0:
            adder = {'action': 'Buy'}
            data[i].update(adder)
            value = usd(value)

        # CONVERT TICKER TO NAME + (SYMBOL)
        data[i]["symbols"] = str(lookup(data[i]["symbols"])["name"] + " (" + data[i]["symbols"] + ")")

        # ADD VALUE COLUMN
        addval = {'value':value}
        data[i].update(addval)

        # CONVERT PRICE COLUMN FROM INT TO USD
        data[i]["prices"] = usd(data[i]["prices"])

    return render_template("history.html", balance=usd(balance), entries=data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()
    success = 0

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username") or not request.form.get("password"):
            return render_template("login.html", login_errs="a")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("login.html", login_errs="b")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        watchlist = {'watchlist':[]}
        session.update(watchlist)

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get for crypto quote."""
    if request.method == "POST":

        # CASE OF ADDING TO WATCHLIST
        if request.form.get("add_watch"):

            # MAKE SURE IT ISNT ALREADY IN THE WATCHLIST
            current_watchlist = db.execute("SELECT symbols FROM watchlists WHERE user_id = ?", session["user_id"])
            for row in current_watchlist:
                if row["symbols"] == request.form.get("add_watch"):
                    quote = ast.literal_eval(request.form.get("previous_quotes"))
                    return render_template("quote.html", quote=quote, quote_status="1", add_watch="0")

            # PUT IN WATCHLIST DATABASE
            db.execute("INSERT INTO watchlists (user_id, symbols) VALUES (?, ?)", session["user_id"], request.form.get("add_watch"))

            # USE COOKIES TO CARRY THIS OVER TO HOMEPAGE
            temp = lookup(request.form.get("add_watch"))
            temp["price"] = usd(temp["price"])
            session["watchlist"].append(temp)

            return render_template("index.html", watchlist=session["watchlist"])

        # CASE OF PREV QUOTES (SECOND + TRIES)
        if int(request.form.get("case")) == 2:

            # INTRODUCE VARIABLES
            quote = ast.literal_eval(request.form.get("previous_quotes"))
            newq = lookup(request.form.get("next_symbol"))

            # CHECK EXISTENCE OF NEW SYMBOL/NAME
            if not newq:
                newq = lookup_slug(request.form.get("next_symbol"))
                if not newq:
                    return render_template("quote.html", quote=quote, quote_status="1", not_found="1")

            # HANDLE DUPLICATE
            for i in range(len(quote)):
                if newq["symbol"] == quote[i]["symbol"]:
                    return render_template("quote.html", quote=quote, quote_status="1", double_req="1")

            # Add newq to prev.
            newq["price"] = usd(newq["price"])
            quote.append(newq)

            return render_template("quote.html", quote=quote, quote_status="1")


        # CASE OF LOOKUP (FIRST TRY)
        if int(request.form.get("case")) == 1:
            data = lookup(request.form.get("symbol"))
            if not data:
                data = lookup_slug(request.form.get("symbol"))
                if not data:
                    return render_template("quote.html", not_found="1")

            data["price"] = usd(data["price"])
            quote = []
            quote.append(data)

            return render_template("quote.html", quote=quote, quote_status="1")

    else:
        return render_template("quote.html", first_quote="1")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
         # Ensure username AND password was submitted
        if not request.form.get("username") or not request.form.get("password"):
            return render_template("register.html", reg_errs="a")

        # Check passowrds match
        if request.form.get("password") != request.form.get("confirmation"):
            return render_template("register.html", reg_errs="b")

        newusername = request.form.get("username")
        checker = db.execute("SELECT username FROM users WHERE username = ?;", newusername)

        if not checker:
            # INSERT THEM INTO DATABASE -- THIS IS THE SUCCESSFUL CASE.
            phashed = generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?);", newusername, phashed)
            return render_template("login.html", new_reg="a")

        elif newusername == checker[0]["username"]:
            return render_template("register.html", reg_errs="c")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell currency"""
    # GET CURRENT BALANCE
    rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    balance = rows[0]["cash"]

    # ONLY ALLOW VALID SALES OF SYMBOLS TO BE RENDERED TO PAGE
    valid_sells = []
    boughtdic = db.execute("SELECT symbols FROM transactions WHERE user_id = ? GROUP BY symbols HAVING SUM(qtys) > 0.000001;", session["user_id"]) # Convert this to a list

    for i in range(len(boughtdic)):
        valid_sells.append(boughtdic[i]["symbols"])

    if request.method == "POST":

        # HANDLE ERROR OF MALICIOUS HTML CHANGE
        if request.form.get("symbol") not in valid_sells:
            return render_template("sell.html", valid_sells=valid_sells, balance=usd(balance), sell_err="3")

        # HANDLE ERROR FOR DOUBLE ENTRY
        if request.form.get("qty") and request.form.get("qty_in_fiat"):
            return render_template("sell.html", valid_sells=valid_sells, balance=usd(balance), sell_err="1")

        # DECLARE VARIABLES
        ssymbol = request.form.get("symbol")
        stemp = lookup(ssymbol)
        sname = stemp["name"]
        sprice = stemp["price"]

        # FIND OUT HOW MANY OF REQUESTED SYMBOL THEY HAVE
        qtot = db.execute("SELECT SUM(qtys) FROM transactions WHERE user_id = ? AND symbols = ?;", session["user_id"], request.form.get("symbol"))

        # FOR QTY FIELD
        if request.form.get("qty"):

            # HANDLE ERROR FOR LACK OF TOKENS
            if float(request.form.get("qty")) > float(qtot[0]["SUM(qtys)"]):
                return render_template("sell.html", valid_sells=valid_sells, balance=usd(balance), sell_err="2")

            # CALCULATE NEW BALANCE, YOU NEED NEWBALANCE AND SQTY
            sqty = float(request.form.get("qty"))
            profit = round(sprice * sqty, 2)
            newbalance = balance + profit

        # FOR QTY_IN_FIAT FIELD
        elif request.form.get("qty_in_fiat"):

            # HANDLE ERROR FOR LACK OF FUNDS IN FIAT
            if float(request.form.get("qty_in_fiat")) > float(qtot[0]["SUM(qtys)"]) * sprice:
                return render_template("sell.html", valid_sells=valid_sells, balance=usd(balance), sell_err="2")

            # CALCULATE NEW BALANCE, YOU NEED NEWBALANCE AND SQTY
            profit = float(request.form.get("qty_in_fiat"))
            newbalance = balance + profit
            sqty = round(profit / sprice, 8)

        # SALE QUANTITIES ARE LOGGED IN DATABASE AS NEGATIVE.
        sqty = sqty * (-1)

        # SEND TO CONFIRMATION
        txn_data = {'user_id':session["user_id"], 'symbols':ssymbol, 'prices':sprice, 'qtys':sqty, 'init_balance':balance, 'newbalance':newbalance, 'size':profit}
        return render_template("confirm.html", txn_data=txn_data, action="sell")

    else:
        return render_template("sell.html", valid_sells=valid_sells, balance=usd(balance))


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add cash to account"""
    rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    balance = rows[0]["cash"]

    if request.method =="POST":
        newbalance = float(request.form.get("cash")) + balance
        db.execute("UPDATE users SET cash = ? WHERE id = ?", newbalance, session["user_id"])

        total = session["user_vals"]["holding_sum"] + newbalance
        holding_total = session["user_vals"]["holding_sum"]

        if holding_total == 0:
            return render_template("portfolio.html", balance=usd(newbalance), entries=session["user_data"], total=usd(total), holding_total=usd(holding_total), empty_portfolio="1")

        return render_template("portfolio.html", balance=usd(newbalance), entries=session["user_data"], total=usd(total), holding_total=usd(holding_total))

    else:
        return render_template("add.html", balance=usd(balance))


@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    """Remove cash to account"""
    rows = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    balance = rows[0]["cash"]

    if request.method =="POST":
        newbalance = balance - float(request.form.get("cash"))
        if newbalance < 0:
            return render_template("withdraw.html", balance=usd(balance), withdraw_errs="1")

        db.execute("UPDATE users SET cash = ? WHERE id = ?", newbalance, session["user_id"])

        total = session["user_vals"]["holding_sum"] + newbalance
        holding_total = session["user_vals"]["holding_sum"]

        if holding_total == 0:
            return render_template("portfolio.html", balance=usd(newbalance), entries=session["user_data"], total=usd(total), holding_total=usd(holding_total), empty_portfolio="1")

        return render_template("portfolio.html", balance=usd(newbalance), entries=session["user_data"], total=usd(total), holding_total=usd(holding_total))

    else:
        return render_template("withdraw.html", balance=usd(balance))


@app.route("/confirm", methods=["POST"])
@login_required
def confirm():
    """Confirm the user's buy or sell transaction and update database"""
    # CONVERT THE STRING DATA TO DICTIONARY
    txn_data = ast.literal_eval(request.form.get("trans_conf"))

    db.execute("INSERT INTO transactions (user_id, symbols, prices, qtys) VALUES (?, ?, ?, ?)", session["user_id"], txn_data["symbols"], txn_data["prices"], txn_data["qtys"])
    db.execute("UPDATE users SET cash = ? WHERE id = ?", txn_data["newbalance"], session["user_id"])

    return redirect("/portfolio")


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Show and execute available settings to the user"""
    if request.method == "POST":
        #Settings - Delete Account or Change Password options...
        return render_template("settings.html")

    else:
        #Just display the page (GET request case)
        return render_template("settings.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)

# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
