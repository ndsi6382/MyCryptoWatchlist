# My Crypto Watchlist
## CS50x 2021 Final Project

***NOTE:*** *This is project was created for the final assignment for the CS50x course, and is here for archival purposes only. 
A video demonstration from its time of submission can be found [HERE.](https://youtu.be/l64mEMuxof8)*

## Description
This is a basic cryptocurrency watchlist web application, inspired by the CS50x 'finance' problem set and then further expanded upon.
As well as a watchlist, there is the ability to make virtual trades in a virtual portfolio, to test trading strategies.
The data is pulled directly via an API from CoinMarketCap.

#### Login / Register / Logout
Users can register and log in/out to the website. An error notification is passed into the HTML of the webpage if there is a user-made error.
Usernames, Passwords and IDs are hashed and stored in an SQL table.

#### Navigation Bar
The navigation bar contains links to the homepage (watchlist), get prices (quote), and the virtual portfolio, within which you can buy, sell and view your transaction history.
Options for account settings will be updated soon, and logout is present in the top right corner.

## Homepage / Watchlist
This is the default homepage of the website. It contains the watchlist of the user, by default this is empty and an alternative message appears.
At the bottom is an option to add to the watchlist, which brings you to the quote/get prices page.
The watchlist is stored in another SQL table, and partially in the session itself (cookies). This allows for the watchlist to be checked against for errors in the adding process.
When users add to the watchlist, a table displaying the rank, name/symbol, price, %change in 24h, 7d and 30d time frames, and its market dominance % is generated.
Additionally, the name/symbol field will link to the currency's entry on CoinMarketCap.com. Options appear to the right of each entry in the table to remove them from the watchlist.

#### Get Prices
Generates a quote using an API request for a symbol input by the user. Errors are handled by dynamically changing the HTML through Jinja2.
The quote will display its rank, name/symbol, price, %change in 24h, 7d and 30d time frames, and its market dominance %.
After a quote is successfully made, an option appears to view its link on CoinMarketCap and/or to add it to the watchlist (this is achieved by putting in the user's session/cookies)

## Virtual Portfolio
Each user has the opportunity to make virtual trades with real data in real time. This can be used for fun, or to test strategies.
By default, each user begins with US$10,000.00 however funds can be added or subtracted at will through the two buttons at the bottom of the portfolio page. The balance is displayed at the bottom.
By default, the portfolio is empty, and instead displays a message inviting the user to use the 'buy' page.

#### Buy
Users will 'buy' their currencies here. They have the choice of buying in terms of quantity, or value (in USD).
Errors are handled within the HTML of the webpage using variables from Python passed into Jinja. A successful buy will redirect the user to the virtual portfolio screen, where their purchase will appear.

#### Sell
Users will 'sell' their currencies here. They also have the choice here of selling in terms of quantity, or value (in USD).
Users can only sell currencies they own, and must choose this from a dropdown menu, the list of which is passed into the HTML of the webpage.
Errors are handled by passing variables into Jinja. A successful sale will redirect the user to the virtual portfolio screen, where the change in quantity or value should be reflected.
In the case that the user owns less than US$0.01 of a currency, this will not show up in the table at all.

#### History
This screen will display the entire transaction history of a user.
The cash balance is also displayed at the top.
The table reflects the transaction ID, action (buy or sell), name, price, qty, value, and timestamp.
