from flask import Flask, render_template, request, jsonify, session
from math import pow
import re
import requests
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "loanbot_secret"

# =========================
# CONFIG
# =========================
GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL = "grok-2"

# =========================
# LOAN RULES
# =========================
LOANS = {
    "personal": {"rate": 12, "min_score": 650},
    "auto": {"rate": 9, "min_score": 600},
    "mortgage": {"rate": 7, "min_score": 700}
}

# =========================
# HELPERS
# =========================
def estimate_credit_score(income, debts):
    score = 750
    score += min(income // 10000, 50)
    score -= debts // 5000
    return max(300, min(score, 850))

def emi(amount, rate, years):
    r = rate / (12 * 100)
    n = years * 12
    return round(amount * r * pow(1 + r, n) / (pow(1 + r, n) - 1), 2)

def confidence_bar(score):
    if score >= 750:
        return "██████████ 100%"
    if score >= 700:
        return "████████░░ 80%"
    if score >= 650:
        return "██████░░░░ 60%"
    return "████░░░░░░ 40%"

def creative_summary(loan, income, debts, amount, years, emi_val, score):
    return (
        f"💡 **Loan Summary Card**\n\n"
        f"🏦 Loan Type: {loan.title()} Loan\n"
        f"💰 Monthly Income: ₹{income}\n"
        f"📉 Existing Debts: ₹{debts}\n"
        f"📄 Loan Amount: ₹{amount}\n"
        f"⏳ Tenure: {years} years\n\n"
        f"📊 Credit Confidence:\n"
        f"{confidence_bar(score)}\n\n"
        f"✅ Status: Eligible\n"
        f"💸 Estimated EMI: ₹{emi_val} / month\n\n"
        f"🕒 Checked on: {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
        f"🔁 Click RESET to try another loan."
    )

def grok_reply(user_message):
    try:
        response = requests.post(
            GROK_API_URL,
            headers={
                "Authorization": f"Bearer {GROK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": GROK_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a loan assistant. "
                            "Do NOT calculate EMI or eligibility. "
                            "Only guide the user politely."
                        )
                    },
                    {"role": "user", "content": user_message}
                ]
            },
            timeout=10
        )
        return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return "Please continue with the loan details."

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    msg = data.get("message", "").lower()

    # Loan selection
    for loan in LOANS:
        if loan in msg:
            session.clear()
            session["loan"] = loan
            session["state"] = "income"
            return jsonify({"reply": f"{loan.title()} loan selected. Enter monthly income:"})

    # Income
    if session.get("state") == "income":
        nums = re.findall(r"\d+", msg)
        if not nums:
            return jsonify({"reply": "Enter income as a number."})
        session["income"] = int(nums[0])
        session["state"] = "debts"
        return jsonify({"reply": "Enter total debts:"})

    # Debts
    if session.get("state") == "debts":
        nums = re.findall(r"\d+", msg)
        if not nums:
            return jsonify({"reply": "Enter debts as a number."})
        session["debts"] = int(nums[0])
        session["state"] = "amount"
        return jsonify({"reply": "Enter loan amount:"})

    # Amount
    if session.get("state") == "amount":
        nums = re.findall(r"\d+", msg)
        if not nums:
            return jsonify({"reply": "Enter loan amount as a number."})
        session["amount"] = int(nums[0])
        session["state"] = "tenure"
        return jsonify({"reply": "Enter tenure in years:"})

    # Tenure + Final Card
    if session.get("state") == "tenure":
        nums = re.findall(r"\d+", msg)
        if not nums:
            return jsonify({"reply": "Enter tenure in years."})

        years = int(nums[0])
        loan_key = session["loan"]
        rule = LOANS[loan_key]

        income = session["income"]
        debts = session["debts"]
        amount = session["amount"]

        score = estimate_credit_score(income, debts)
        if score < rule["min_score"]:
            session.clear()
            return jsonify({"reply": f"❌ Credit score {score}. Not eligible."})

        emi_val = emi(amount, rule["rate"], years)
        summary = creative_summary(
            loan_key, income, debts, amount, years, emi_val, score
        )

        session.clear()
        return jsonify({"reply": summary})

    # AI fallback
    return jsonify({"reply": grok_reply(msg)})

@app.route("/reset", methods=["POST"])
def reset():
    session.clear()
    return jsonify({"reply": "🔄 Chat reset. Choose: personal loan / auto loan / mortgage"})

if __name__ == "__main__":
    app.run()