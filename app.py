from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List

app = FastAPI(title="Sports Betting Simulator API")

# Mock In-Memory Databases
USERS = {
    "user_001": {"username": "JohnDoe", "wallet_balance": 5000.0}  # Balance in Kes/USD
}

MATCHES = {
    "match_101": {
        "teams": "Gor Mahia vs AFC Leopards",
        "status": "LIVE",
        "odds": {"home": 1.85, "draw": 3.40, "away": 4.20},
        "outcome": None
    },
    "match_102": {
        "teams": "Arsenal vs Chelsea",
        "status": "COMPLETED",
        "odds": {"home": 2.10, "draw": 3.10, "away": 3.50},
        "outcome": "home"  # Arsenal won
    }
}

BETS = {}
bet_counter = 0

# Data Models for Request validation
class BetPlacementRequest(BaseModel):
    user_id: str
    match_id: str
    selection: str  # 'home', 'draw', or 'away'
    stake: float

class SettleBetRequest(BaseModel):
    match_id: str
    winning_outcome: str  # 'home', 'draw', or 'away'

# --- API ENDPOINTS ---

@app.get("/matches")
def get_active_matches():
    """Retrieve all matches and their current live odds."""
    return {"matches": MATCHES}

@app.get("/user/{user_id}")
def get_user_balance(user_id: str):
    """Check user's wallet balance."""
    if user_id not in USERS:
        raise HTTPException(status_code=404, detail="User not found")
    return USERS[user_id]

@app.post("/bet/place")
def place_bet(request: BetPlacementRequest):
    """Core logic to validate and place a single bet."""
    global bet_counter
    
    # 1. Validate User
    if request.user_id not in USERS:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = USERS[request.user_id]
    
    # 2. Validate Match and Odds
    if request.match_id not in MATCHES:
        raise HTTPException(status_code=404, detail="Match not found")
    
    match = MATCHES[request.match_id]
    if match["status"] != "LIVE":
        raise HTTPException(status_code=400, detail="Betting is closed for this match")
        
    if request.selection not in match["odds"]:
        raise HTTPException(status_code=400, detail="Invalid selection. Choose 'home', 'draw', or 'away'")

    # 3. Check Wallet Funds
    if request.stake <= 0:
        raise HTTPException(status_code=400, detail="Stake must be greater than 0")
        
    if user["wallet_balance"] < request.stake:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")

    # 4. Deduct Stake & Calculate Potential Payout
    selected_odds = match["odds"][request.selection]
    potential_payout = round(request.stake * selected_odds, 2)
    user["wallet_balance"] -= request.stake

    # 5. Record the Bet
    bet_counter += 1
    bet_id = f"BET_{bet_counter:04d}"
    
    BETS[bet_id] = {
        "bet_id": bet_id,
        "user_id": request.user_id,
        "match_id": request.match_id,
        "selection": request.selection,
        "odds": selected_odds,
        "stake": request.stake,
        "potential_payout": potential_payout,
        "status": "PENDING"
    }

    return {
        "message": "Bet placed successfully", 
        "bet_details": BETS[bet_id],
        "remaining_balance": user["wallet_balance"]
    }

@app.post("/admin/settle-match")
def settle_match_and_bets(request: SettleBetRequest):
    """Admin function to end a match and auto-payout winning tickets."""
    if request.match_id not in MATCHES:
        raise HTTPException(status_code=404, detail="Match not found")
    
    match = MATCHES[request.match_id]
    match["status"] = "COMPLETED"
    match["outcome"] = request.winning_outcome

    settled_bets_summary = []

    # Scan all bets to calculate winnings
    for bet_id, bet in BETS.items():
        if bet["match_id"] == request.match_id and bet["status"] == "PENDING":
            if bet["selection"] == request.winning_outcome:
                # User Won: Credit wallet with potential payout
                bet["status"] = "WON"
                USERS[bet["user_id"]]["wallet_balance"] += bet["potential_payout"]
            else:
                # User Lost
                bet["status"] = "LOST"
            
            settled_bets_summary.append({
                "bet_id": bet_id, 
                "status": bet["status"], 
                "new_user_balance": USERS[bet["user_id"]]["wallet_balance"]
            })

    return {
        "message": f"Match settled with outcome: {request.winning_outcome}",
        "settled_bets": settled_bets_summary
    }
