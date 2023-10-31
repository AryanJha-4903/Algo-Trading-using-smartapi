# Package import statements
from SmartApi import SmartConnect
import pyotp
from datetime import datetime, time, timedelta
import time

# ------------------ user input -------------------
EntryDiffPrice  = 2     # in Rs , to buy
ExitDiffPrice   = 2     # in Rs , to sell
minBuyQty       = 1     # min qty to buy
MaxOpenPosition = 3     # Max Qty 
StopLossInRs    = 10    # in rs , to book stop loss
duration        = 1     # in min
#------------------ user input till here ------------

# API credentials
api_key     = ''#enter api id
clientId    = '' #enter client id
pwd         = ''#enter password
token       = "" # enter token

# Initialize SmartConnect
smartApi = SmartConnect(api_key)
totp = pyotp.TOTP(token).now()
correlation_id = "abc123"

# Login API call
data = smartApi.generateSession(clientId, pwd, totp)
authToken = data['data']['jwtToken']
refreshToken = data['data']['refreshToken']

# Fetch the feed token
feedToken = smartApi.getfeedToken()
#=============================================================

# Fetch user profile (if needed)
# res = smartApi.getProfile(refreshToken)
time.sleep(0.4)
# Initialize sell order parameters
buyOrderParams = {
    "variety": "NORMAL",
    "tradingsymbol": "SBIN-EQ",
    "symboltoken": "3045",
    "transactiontype": "BUY",
    "exchange": "NSE",
    "ordertype": "MARKET",
    "producttype": "INTRADAY",
    "duration": "DAY",
    "price": "0",
    "squareoff": "0",
    "stoploss": "0",
    "quantity": minBuyQty
}
sellOrderParams = {
    "variety": "NORMAL",
    "tradingsymbol": "SBIN-EQ",
    "symboltoken": "3045",
    "transactiontype": "SELL",
    "exchange": "NSE",
    "ordertype": "MARKET",
    "producttype": "INTRADAY",
    "duration": "DAY",
    "price": "0",
    "squareoff": "0",
    "stoploss": "0",
    "quantity": minBuyQty
}


# Initial cash check
initialCash = smartApi.rmsLimit().get("data").get("availablecash")
time.sleep(0.4)
if initialCash is None:
    initialCash = 0
print("Initial available Cash =", initialCash)

start_time = datetime.now()
EndTime = start_time + timedelta(minutes=duration)
print("EndTime:", EndTime)

#===================   start Algo trade =====================
smartApi.placeOrder(buyOrderParams)    # buy first order
time.sleep(0.4)
orderbook = smartApi.orderBook()
time.sleep(0.4)
for item in orderbook.get('data'):
    obStatus = item.get('orderstatus')
    obText = item.get('text')
    print("Orderbook Status=", obStatus, ", text=", obText)
time.sleep(0.4)

#----------------- check current position -------------
position = smartApi.position()
time.sleep(0.4)
data = position.get('data') 
qty = 0;
for item in data:
        qty = item.get("netqty")
        buyprice = item.get("avgnetprice")
        print("Quantity:", qty)
        print("Average Net Price:", buyprice)
#print("Initial Holding position QTY =", position)
if qty is None:
    qty = 0
print("Initial Holding position QTY =", qty)

# todo: use tradebook api to check last order buy price
tradebook=smartApi.tradeBook()
print(tradebook)
# Main loop
while True:
    sellOrderParams["quantity"] = minBuyQty
    # Fetch LTP data
    time.sleep(1)
    x = smartApi.ltpData("NSE", "SBIN-EQ", "3045")
    time.sleep(0.4)
    ltp = float(x.get('data').get('ltp'))
    print("LTP =", ltp)

    # Get position
    time.sleep(0.4)
    position = smartApi.position()
    time.sleep(0.4)
    data = position.get('data') 
    for item in data:
        qty = item.get("netqty")
        buyprice = item.get("avgnetprice")
        print("Quantity:", qty)
        print("Average Net Price:", buyprice)
    
        if qty is None:
            qty = 0
        if buyprice is None:
            buyprice = 0
        
        # calculate avgPrice 
    if ltp < float(buyprice) - float(StopLossInRs):
        sellOrderParams["quantity"] = qty
        time.sleep(0.4)
        smartApi.placeOrder(sellOrderParams)
        time.sleep(0.4)
        print("Stop loss hit : ", qty, "qty sold at market price")
        break

    if ltp > (float(buyprice) + float(ExitDiffPrice)) and (float(qty) > 0):   # book profit
        time.sleep(0.4)
        smartApi.placeOrder(sellOrderParams)
        time.sleep(0.4)
        print("Profit booked : ", qty, "qty sold at =",ltp," market price, buyprice=",buyprice,"ExitDiffPrice=",ExitDiffPrice)

    if (ltp < (float(buyprice) - float(EntryDiffPrice))) and (float(qty) <= float(MaxOpenPosition)):
        time.sleep(0.4)
        smartApi.placeOrder(buyOrderParams)
        time.sleep(0.4)
        print("Purchased ", qty, "at ", ltp)

    # check end time
    current_time = datetime.now()
    if current_time > EndTime:
        timespent = current_time - start_time
        print("timespent:", timespent, "start time:",start_time,"current_time:",current_time)
        # Place sell order for all QTY
        time.sleep(0.4)
        position = smartApi.position()
        time.sleep(0.4)
        data = position.get('data') 
        for item in data:
            qty = item.get("netqty")
            buyprice = item.get("avgnetprice")
            print("Quantity:", qty)
            print("Average Net Price:", buyprice)

        if qty is None:
            qty = 0

        if float(qty) > 0:
            sellOrderParams["quantity"] = qty
            sellOrderResponse = smartApi.placeOrder(sellOrderParams)
            time.sleep(0.4)
            if sellOrderResponse is not None and 'data' in sellOrderResponse and 'orderid' in sellOrderResponse['data']:
                order_id = sellOrderResponse['data']['orderid']
                print("End time reached , Sell order placed successfully. Order ID:", order_id)
            else:
                print("End time reached , Failed to place sell order.")
        else:
            print("End time reached , No quantity to sell.")
        break

    # Add a delay between iterations to avoid overwhelming the API
    time.sleep(1)

# End of loop
time.sleep(1)
balanceCash = smartApi.rmsLimit().get("data").get("availablecash")
time.sleep(0.4)
if balanceCash is None:
    balanceCash = 0

print("Balance Cash =", balanceCash)

# Calculate profit
balanceCash = float(balanceCash)
initialCash = float(initialCash)
profit = balanceCash - initialCash
print("Total profit =", profit)

time.sleep(1)
# Logout
try:
    logout = smartApi.terminateSession(clientId)
    time.sleep(0.4)
    print("Logout Successful")
except Exception as e:
    print("Logout failed: {}".format(e.message))
