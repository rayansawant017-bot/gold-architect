How this works for you automatically:
Monday Open (WOFM): When you click Calculate, the code looks back at the last 7 days, finds the "Monday" timestamp, and takes the high/low of that first candle to set the gravity center (μ).
NY Close (TDO): It searches the historical data for the 20:00 GMT candle to set the "True Day Open."
90-Minute Cycles: It checks your current computer time (GMT) against the list of 16 MOC edges. If you are near one, the probability score increases.
No Inputs: Notice there are no st.text_input fields. The "Calculate" button is the only interaction.
Kelly Risk: It automatically calculates the lot size based on the $125k equity and the 9.4% risk model you provided.

Important Final Tips for Accuracy:
The 15-Minute Delay: Since we are using free Yahoo data, your app will always be roughly 15 minutes behind the "live" second. However, your logic (WOFM and TDO) are anchor points that do not change based on minutes.
Broker Sync: Brokers (like IC Markets, Exness, Oanda) all have slightly different prices (spreads). I added a "Broker Sync" button in the app. If you see the app says 2030.50 but your MT5 says 2032.00, just type 1.50 into the sync box, and the app will perfectly align all its signals to your broker for that session.
Weekend: If you check this on a Saturday or Sunday, the price will not move because the global gold market is closed.
