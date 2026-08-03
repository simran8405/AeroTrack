import random
import string
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for
from bson.objectid import ObjectId

from database import baggage_collection, lostfound_collection

app = Flask(__name__)


@app.template_filter("fmt_time")
def fmt_time(value):
    if not value:
        return ""
    return value.strftime("%b %d, %I:%M %p").upper()

# =========================
# CONSTANTS
# =========================

STATUS_ORDER = [
    "Checked In",
    "Security Screening",
    "Loaded on Aircraft",
    "In Transit",
    "Arrived",
    "On Carousel",
    "Claimed",
]

FINAL_STATUSES = {"Claimed", "Mishandled"}

AIRPORTS = [
    ("JFK", "New York JFK"),
    ("LHR", "London LHR"),
    ("DXB", "Dubai DXB"),
    ("CDG", "Paris CDG"),
    ("FRA", "Frankfurt FRA"),
    ("SIN", "Singapore SIN"),
    ("HND", "Tokyo HND"),
    ("LAX", "Los Angeles LAX"),
    ("SYD", "Sydney SYD"),
]

REPORT_TYPES = ["Lost Baggage", "Delayed Baggage", "Damaged Baggage"]


# =========================
# HELPERS
# =========================

def generate_tag_id():
    while True:
        tag_id = "BG" + "".join(random.choices(string.digits, k=8))
        if not baggage_collection.find_one({"tag_id": tag_id}):
            return tag_id


def generate_case_id():
    while True:
        case_id = "LF" + "".join(
            random.choices(string.ascii_uppercase + string.digits, k=5)
        )
        if not lostfound_collection.find_one({"case_id": case_id}):
            return case_id


def add_history(bag, status):
    bag.setdefault("history", [])
    bag["history"].append({"status": status, "time": datetime.utcnow()})


# =========================
# LANDING / TRACK
# =========================

@app.route("/")
def home():
    return redirect(url_for("track"))


@app.route("/landing")
def landing():
    return redirect(url_for("track"))


@app.route("/track")
def track():
    return render_template("track.html", bag=None, error=None, query="")


@app.route("/track", methods=["POST"])
def track_search():
    tag_id = request.form.get("tag_id", "").strip().upper()
    return redirect(url_for("track_result", tag_id=tag_id))


@app.route("/track/<tag_id>")
def track_result(tag_id):
    tag_id = tag_id.strip().upper()
    bag = baggage_collection.find_one({"tag_id": tag_id})

    if bag is None:
        return render_template("track.html", bag=None, error=tag_id, query=tag_id)

    return render_template("track.html", bag=bag, error=None, query=tag_id)


# =========================
# OPERATIONS CONSOLE
# =========================

@app.route("/operations")
def operations():
    bags = list(baggage_collection.find().sort("created_at", -1))

    total_bags = len(bags)
    in_transit = sum(1 for b in bags if b.get("status") == "In Transit")
    claimed = sum(1 for b in bags if b.get("status") == "Claimed")
    mishandled = sum(1 for b in bags if b.get("status") == "Mishandled")
    open_reports = lostfound_collection.count_documents({"status": "Open"})

    on_time_rate = 100.0
    if total_bags:
        on_time_rate = round((total_bags - mishandled) / total_bags * 100, 1)

    # 7-day throughput (bags checked in per day)
    today = datetime.utcnow().date()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    throughput = []
    for day in days:
        count = sum(
            1
            for b in bags
            if b.get("created_at") and b["created_at"].date() == day
        )
        throughput.append({"label": day.strftime("%a"), "count": count})

    # Status distribution
    all_statuses = STATUS_ORDER + ["Mishandled"]
    distribution = [
        {"label": s, "count": sum(1 for b in bags if b.get("status") == s)}
        for s in all_statuses
    ]

    return render_template(
        "operations.html",
        bags=bags,
        total_bags=total_bags,
        in_transit=in_transit,
        claimed=claimed,
        mishandled=mishandled,
        on_time_rate=on_time_rate,
        open_reports=open_reports,
        throughput=throughput,
        distribution=distribution,
        statuses=STATUS_ORDER,
    )


@app.route("/operations/advance/<tag_id>", methods=["POST"])
def advance_baggage(tag_id):
    bag = baggage_collection.find_one({"tag_id": tag_id})

    if bag and bag.get("status") not in FINAL_STATUSES:
        current = bag.get("status", STATUS_ORDER[0])
        if current in STATUS_ORDER:
            idx = STATUS_ORDER.index(current)
        else:
            idx = -1

        if idx + 1 < len(STATUS_ORDER):
            new_status = STATUS_ORDER[idx + 1]
            history = bag.get("history", [])
            history.append({"status": new_status, "time": datetime.utcnow()})
            baggage_collection.update_one(
                {"tag_id": tag_id},
                {"$set": {"status": new_status, "history": history}},
            )

    return redirect(url_for("operations"))


@app.route("/operations/flag/<tag_id>", methods=["POST"])
def flag_baggage(tag_id):
    bag = baggage_collection.find_one({"tag_id": tag_id})

    if bag and bag.get("status") not in FINAL_STATUSES:
        history = bag.get("history", [])
        history.append({"status": "Mishandled", "time": datetime.utcnow()})
        baggage_collection.update_one(
            {"tag_id": tag_id},
            {"$set": {"status": "Mishandled", "mishandled": True, "history": history}},
        )

    return redirect(url_for("operations"))


@app.route("/operations/delete/<tag_id>", methods=["POST"])
def delete_baggage_by_tag(tag_id):
    baggage_collection.delete_one({"tag_id": tag_id})
    return redirect(url_for("operations"))


# =========================
# CHECK-IN DESK
# =========================

@app.route("/checkin", methods=["GET", "POST"])
def checkin():
    generated = None

    if request.method == "POST":
        tag_id = generate_tag_id()

        origin = request.form.get("origin", "")
        destination = request.form.get("destination", "")
        origin_code, origin_name = origin.split("|") if "|" in origin else (origin, origin)
        dest_code, dest_name = destination.split("|") if "|" in destination else (destination, destination)

        bag = {
            "tag_id": tag_id,
            "passenger_name": request.form.get("passenger_name", ""),
            "flight_number": request.form.get("flight_number", ""),
            "origin_code": origin_code,
            "origin_name": origin_name,
            "destination_code": dest_code,
            "destination_name": dest_name,
            "airline": request.form.get("airline", "AeroTrack Airways"),
            "weight": request.form.get("weight", ""),
            "priority_handling": bool(request.form.get("priority_handling")),
            "status": "Checked In",
            "mishandled": False,
            "created_at": datetime.utcnow(),
            "history": [{"status": "Checked In", "time": datetime.utcnow()}],
        }

        baggage_collection.insert_one(bag)
        generated = bag

    return render_template("checkin.html", airports=AIRPORTS, generated=generated)


# =========================
# LOST & FOUND
# =========================

@app.route("/lostfound", methods=["GET", "POST"])
def lostfound():
    if request.method == "POST":
        report = {
            "case_id": generate_case_id(),
            "filer": request.form.get("full_name", ""),
            "contact": request.form.get("contact", ""),
            "tag_id": request.form.get("tag_id", "").strip().upper(),
            "report_type": request.form.get("report_type", "Lost Baggage"),
            "color": request.form.get("color", ""),
            "brand": request.form.get("brand", ""),
            "description": request.form.get("description", ""),
            "status": "Open",
            "created_at": datetime.utcnow(),
        }
        lostfound_collection.insert_one(report)
        return redirect(url_for("lostfound"))

    cases = list(lostfound_collection.find().sort("created_at", -1))
    return render_template("lostfound.html", cases=cases, report_types=REPORT_TYPES)


# =========================
# LEGACY / EDIT (kept for compatibility)
# =========================

@app.route("/edit/<id>")
def edit_baggage(id):
    bag = baggage_collection.find_one({"_id": ObjectId(id)})
    return render_template("edit.html", bag=bag)


@app.route("/update/<id>", methods=["POST"])
def update_baggage(id):
    baggage_collection.update_one(
        {"_id": ObjectId(id)},
        {
            "$set": {
                "passenger_name": request.form["passenger_name"],
                "flight_number": request.form["flight_number"],
                "weight": request.form["weight"],
                "status": request.form["status"],
            }
        },
    )
    return redirect(url_for("operations"))


@app.route("/delete/<id>")
def delete_baggage(id):
    baggage_collection.delete_one({"_id": ObjectId(id)})
    return redirect(url_for("operations"))


# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":
    app.run(debug=True)
